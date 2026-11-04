"""Explicit, digest-bound, bounded PubMed ESearch ID discovery; no evidence promotion."""
import argparse
import base64
import copy
import csv
import datetime as dt
import hashlib
import io
import http.client
import json
import math
from pathlib import Path
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import bibliographic_intake
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json

ENDPOINT = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
MAX_BODY_BYTES = 65_536
MAX_ARTIFACT_BYTES = 20_000_000
REQUEST_TIMEOUT = 10.0
OVERALL_TIMEOUT = 60.0
SAFE_HEADERS = {'content-type', 'content-length', 'date', 'retry-after'}
ERRORS = {None, 'network_error', 'tls_error', 'timeout', 'body_too_large', 'incomplete_body', 'elapsed_limit'}
_LOCK = threading.Lock()
_LAST_REQUEST = None
BOUNDARY = ('ESearch returns IDs only, not bibliography, abstracts or full text. Newest publication-date sort affects capped results. '
            'Reported count accounting is not an authenticated index snapshot or search completeness. '
            'Source authenticity, publication identity, query adequacy and index snapshot are unverified. '
            'Offline verification regenerates unsigned supplied records; it does not prove requests happened. '
            'Consistently reauthored records can replay. Limits are not hard resource or shared-IP rate enforcement. '
            'No protocol, screening, study or evidence changes. Retain native discovery alongside any CSV intake. '
            'Retained queries and native responses are not redacted; keep real outputs outside public repositories.')


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ('pubmed_discovery.py', 'json_io.py')}


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate_spec(spec):
    keys = {'schema_version', 'request_id', 'query', 'sort', 'date_filter', 'page_size', 'max_records', 'max_requests'}
    if type(spec) is not dict or set(spec) != keys or type(spec['schema_version']) is not int or spec['schema_version'] != 1:
        raise ValueError('invalid discovery spec fields or schema')
    for name, limit in [('request_id', 200), ('query', 4000)]:
        value = spec[name]
        if type(value) is not str or not value.strip() or len(value.encode('utf-8')) > limit or '\x00' in value:
            raise ValueError('invalid bounded request_id or query')
    if spec['sort'] != 'pub_date':
        raise ValueError('sort must be explicitly pub_date')
    for name, upper in [('page_size', 100), ('max_records', 1000), ('max_requests', 10)]:
        if not _integer(spec[name], 1, upper):
            raise ValueError('invalid integer discovery bound')
    dates = spec['date_filter']
    if dates is not None:
        if type(dates) is not dict or set(dates) != {'datetype', 'mindate', 'maxdate'} or dates['datetype'] not in ('pdat', 'edat', 'mdat'):
            raise ValueError('invalid explicit paired date filter')
        for name in ('mindate', 'maxdate'):
            if type(dates[name]) is not str or not re.fullmatch(r'[0-9]{4}/[0-9]{2}/[0-9]{2}', dates[name]):
                raise ValueError('date must be real YYYY/MM/DD')
            try:
                dt.datetime.strptime(dates[name], '%Y/%m/%d')
            except ValueError:
                raise ValueError('date must be real YYYY/MM/DD') from None
        if dates['mindate'] > dates['maxdate']:
            raise ValueError('date range is reversed')
    return copy.deepcopy(spec)


def parameters(spec, offset, remaining):
    result = dict(db='pubmed', retmode='json', term=spec['query'], sort='pub_date',
                  retstart=str(offset), retmax=str(min(spec['page_size'], remaining, 10000 - offset)))
    if spec['date_filter'] is not None:
        result.update(spec['date_filter'])
    return result


def preview(spec):
    spec = validate_spec(spec)
    result = dict(schema_version=1, mode='pubmed_discovery_preview', spec=spec, endpoint=ENDPOINT,
                  method='GET', first_request_parameters=parameters(spec, 0, spec['max_records']),
                  paging='retstart increases by returned ID occurrences; retmax bounded by remaining cap; no history',
                  request_timeout_seconds=REQUEST_TIMEOUT, overall_timeout_seconds=OVERALL_TIMEOUT,
                  max_response_bytes=MAX_BODY_BYTES, minimum_request_interval_seconds=1,
                  implementation_sha256=implementation_hashes(), external_calls=0, boundary=BOUNDARY)
    result['preview_sha256'] = digest(result)
    return result


def _timestamp(value):
    if type(value) is not str:
        raise ValueError('timestamp must be UTC ISO8601')
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('timestamp must be UTC ISO8601') from None
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise ValueError('timestamp must be UTC ISO8601')
    return parsed


def _attempt(record):
    keys = {'parameters', 'status', 'headers', 'started_at', 'elapsed_seconds', 'body_base64', 'body_complete', 'error'}
    if type(record) is not dict or set(record) != keys:
        raise ValueError('invalid attempt fields')
    _timestamp(record['started_at'])
    elapsed = record['elapsed_seconds']
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError('invalid elapsed seconds')
    if record['status'] is not None and not _integer(record['status'], 100, 599):
        raise ValueError('invalid HTTP status')
    headers = record['headers']
    if type(headers) is not dict or not set(headers) <= SAFE_HEADERS or any(type(v) is not str or len(v) > 1000 for v in headers.values()):
        raise ValueError('invalid safe response headers')
    if type(record['body_complete']) is not bool or record['error'] not in ERRORS:
        raise ValueError('invalid body completeness or error')
    try:
        raw = base64.b64decode(record['body_base64'], validate=True)
    except (ValueError, TypeError):
        raise ValueError('invalid base64 response body') from None
    if len(raw) > MAX_BODY_BYTES or base64.b64encode(raw).decode('ascii') != record['body_base64']:
        raise ValueError('invalid bounded canonical base64 body')
    return raw


def _page(raw):
    try:
        native = parse_json(raw)
    except (ValueError, UnicodeError, RecursionError):
        return None, 'malformed_response'
    if type(native) is not dict:
        return None, 'unsupported_response_shape'
    page = native.get('esearchresult')
    if any(native.get(key) for key in ('error', 'errors', 'errorlist', 'warninglist')):
        return None, 'provider_error'
    if type(page) is not dict:
        return None, 'unsupported_response_shape'
    for key in ('count', 'retstart', 'retmax'):
        if type(page.get(key)) is not str or not re.fullmatch(r'[0-9]{1,15}', page[key]):
            return None, 'unsupported_response_shape'
    ids = page.get('idlist')
    if type(ids) is not list or any(type(x) is not str or not re.fullmatch(r'[1-9][0-9]{0,19}', x) for x in ids) or type(page.get('querytranslation')) is not str:
        return None, 'unsupported_response_shape'
    error = 'provider_error_or_warning' if any(page.get(key) for key in ('error', 'errors', 'errorlist', 'warninglist')) else None
    return dict(count=int(page['count']), retstart=int(page['retstart']), retmax=int(page['retmax']),
                ids=ids, querytranslation=page['querytranslation']), error


def _analyze(spec, attempts):
    rows, pages, seen = [], [], set()
    count = translation = None
    offset = 0
    stop = None
    for index, record in enumerate(attempts):
        if stop is not None:
            raise ValueError('attempt recorded after required stop')
        raw = _attempt(record)
        if record['parameters'] != parameters(spec, offset, spec['max_records'] - len(rows)):
            raise ValueError('attempt parameters differ from bounded request sequence')
        if record['error']:
            stop = record['error']
        elif record['status'] != 200:
            stop = 'http_status'
        elif not record['body_complete']:
            stop = 'incomplete_body'
        else:
            page, error = _page(raw)
            if page is None:
                stop = error
            else:
                ids = page['ids']
                pages.append(dict(response_index=index, response_sha256=hashlib.sha256(raw).hexdigest(), **page))
                # Preserve every valid occurrence even when count or paging diagnostics stop collection.
                for position, pmid in enumerate(ids):
                    rows.append(dict(pmid=pmid, occurrence_index=len(rows), response_index=index,
                                     response_occurrence_index=position, response_sha256=hashlib.sha256(raw).hexdigest()))
                requested = int(record['parameters']['retmax'])
                if error:
                    stop = error
                elif page['retstart'] != offset:
                    stop = 'unexpected_offset'
                elif page['retmax'] != len(ids) or len(ids) > requested:
                    stop = 'retmax_or_list_mismatch'
                elif count is not None and page['count'] != count:
                    stop = 'reported_count_changed'
                elif translation is not None and translation != page['querytranslation']:
                    stop = 'query_translation_changed'
                elif any(pmid in seen for pmid in ids) or len(set(ids)) != len(ids):
                    stop = 'duplicate_or_paging_overlap'
                elif page['count'] < offset or len(ids) != min(requested, max(0, page['count'] - offset)):
                    stop = 'count_or_page_length_mismatch'
                if count is None:
                    count, translation = page['count'], page['querytranslation']
                offset += len(ids)
                seen.update(ids)
                if stop is None and offset >= count:
                    stop = 'reported_count_reached'
                elif stop is None and len(rows) >= spec['max_records']:
                    stop = 'max_records'
        if stop is None and index + 1 >= spec['max_requests']:
            stop = 'max_requests'
    return dict(occurrences=rows, pages=pages, initial_reported_count=count, query_translation=translation,
                reported_count_exceeds_pubmed_10000_limit=count is not None and count > 10000,
                observed_reported_count_accounted_for=stop == 'reported_count_reached', stop_reason=stop)


def from_responses(spec, execution):
    """Reconstruct an artifact from supplied execution records; makes no network calls."""
    spec = validate_spec(spec)
    if type(execution) is not dict or set(execution) != {'started_at', 'attempts', 'stop_reason'}:
        raise ValueError('invalid execution fields')
    started = _timestamp(execution['started_at'])
    attempts = execution['attempts']
    if type(attempts) is not list or len(attempts) > spec['max_requests']:
        raise ValueError('invalid bounded attempts')
    derived = _analyze(spec, attempts)
    last = started
    for record in attempts:
        when = _timestamp(record['started_at'])
        if when < last:
            raise ValueError('attempt timestamps are not ordered')
        remaining = OVERALL_TIMEOUT - (when - started).total_seconds()
        if remaining <= 0:
            raise ValueError('attempt starts beyond recorded overall time bound')
        if record['error'] is None and record['elapsed_seconds'] >= min(REQUEST_TIMEOUT, remaining):
            raise ValueError('error-free attempt contradicts recorded time bound')
        last = when
    if derived['stop_reason'] is None:
        if execution['stop_reason'] != 'elapsed_limit':
            raise ValueError('execution must reach a bound, diagnostic or reported count')
        derived['stop_reason'] = 'elapsed_limit'
    elif execution['stop_reason'] != derived['stop_reason']:
        raise ValueError('recorded stop differs from regenerated stop')
    result = dict(schema_version=1, mode='pubmed_discovery', spec=spec, preview_sha256=preview(spec)['preview_sha256'],
                  execution=copy.deepcopy(execution), derived=derived, implementation_sha256=implementation_hashes(),
                  search_completeness='NOT_ESTABLISHED', census='NOT_ESTABLISHED', conclusion='NOT_READY',
                  source_authenticity='NOT_VERIFIED', publication_identity='NOT_VERIFIED', query_adequacy='NOT_VERIFIED',
                  index_snapshot='NOT_VERIFIED', review_status='NOT_PERFORMED', protocol_changed=False, boundary=BOUNDARY)
    artifact_bytes(result)
    return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _transport(params, timeout):
    """Fixed HTTPS GET; no proxy credentials, cookies, redirects, retries or auth handlers."""
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context()),
                    urllib.request.HTTPDefaultErrorHandler(), _NoRedirect(), urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    request = urllib.request.Request(ENDPOINT + '?' + urllib.parse.urlencode(params), method='GET')
    begin = time.monotonic()
    result = dict(parameters=copy.deepcopy(params), status=None, headers={}, started_at=_utcnow(), elapsed_seconds=0,
                  body_base64='', body_complete=False, error=None)
    raw = b''
    response = None
    try:
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        result['status'] = response.code
        result['headers'] = {key.lower(): value[:1000] for key, value in response.headers.items() if key.lower() in SAFE_HEADERS}
        while len(raw) <= MAX_BODY_BYTES:
            if time.monotonic() - begin >= timeout:
                result['error'] = 'timeout'
                break
            chunk = response.read1(min(65536, MAX_BODY_BYTES + 1 - len(raw)))
            if not chunk:
                result['body_complete'] = True
                break
            raw += chunk
        if len(raw) > MAX_BODY_BYTES:
            raw = raw[:MAX_BODY_BYTES]
            result['error'] = 'body_too_large'
            result['body_complete'] = False
        length = result['headers'].get('content-length')
        if result['body_complete'] and length is not None and (not re.fullmatch(r'[0-9]+', length) or int(length) != len(raw)):
            result['body_complete'] = False
            result['error'] = 'incomplete_body'
    except http.client.IncompleteRead as error:
        raw = (raw + error.partial)[:MAX_BODY_BYTES]
        result['error'] = 'incomplete_body'
    except (TimeoutError,):
        result['error'] = 'timeout'
    except ssl.SSLError:
        result['error'] = 'tls_error'
    except urllib.error.URLError as error:
        result['error'] = 'tls_error' if isinstance(error.reason, ssl.SSLError) else 'timeout' if isinstance(error.reason, TimeoutError) else 'network_error'
    except (OSError, ValueError, http.client.HTTPException):
        result['error'] = 'network_error'
    finally:
        if response is not None:
            try:
                response.close()
            except (OSError, http.client.HTTPException):
                result['error'] = result['error'] or 'network_error'
        result['elapsed_seconds'] = max(0, time.monotonic() - begin)
        if result['elapsed_seconds'] >= timeout and result['error'] is None:
            result['error'] = 'timeout'
        result['body_base64'] = base64.b64encode(raw).decode('ascii')
    return result


def fetch(spec, preview_sha256, transport=None):
    """Explicit live invocation; injected transport is for offline tests only."""
    global _LAST_REQUEST
    prepared = preview(spec)
    if type(preview_sha256) is not str or preview_sha256 != prepared['preview_sha256']:
        raise ValueError('preview digest mismatch; preview the exact current spec and implementation first')
    spec = prepared['spec']
    transport = _transport if transport is None else transport
    execution = dict(started_at=_utcnow(), attempts=[], stop_reason=None)
    begin = time.monotonic()
    while execution['stop_reason'] is None:
        with _LOCK:
            now = time.monotonic()
            delay = max(0, 1 - (now - _LAST_REQUEST)) if _LAST_REQUEST is not None else 0
            remaining = OVERALL_TIMEOUT - (now - begin) - delay
            if remaining <= 0:
                execution['stop_reason'] = 'elapsed_limit'
                break
            if delay:
                time.sleep(delay)
            now = time.monotonic()
            remaining = OVERALL_TIMEOUT - (now - begin)
            if remaining <= 0:
                execution['stop_reason'] = 'elapsed_limit'
                break
            _LAST_REQUEST = now
        derived = _analyze(spec, execution['attempts'])
        offset = len(derived['occurrences'])
        record = transport(parameters(spec, offset, spec['max_records'] - offset), min(REQUEST_TIMEOUT, remaining))
        execution['attempts'].append(record)
        execution['stop_reason'] = _analyze(spec, execution['attempts'])['stop_reason']
        if execution['stop_reason'] is None and time.monotonic() - begin >= OVERALL_TIMEOUT:
            execution['stop_reason'] = 'elapsed_limit'
    return from_responses(spec, execution)


def verify(artifact):
    artifact_bytes(artifact)
    if type(artifact) is not dict or artifact.get('implementation_sha256') != implementation_hashes():
        raise ValueError('discovery implementation mismatch')
    expected = from_responses(artifact.get('spec'), artifact.get('execution'))
    if canonical_json_bytes(expected) != canonical_json_bytes(artifact):
        raise ValueError('discovery artifact differs from deterministic regeneration')
    return dict(valid=True, artifact_sha256=digest(artifact), external_calls=0,
                verification_scope='Unsigned retained spec, execution and response derivation only; not proof of retrieval',
                search_completeness='NOT_ESTABLISHED', census='NOT_ESTABLISHED', conclusion='NOT_READY')


def to_intake(artifact, protocol, search_id):
    verify(artifact)
    if type(protocol) is not dict or type(protocol.get('search_plan')) is not list or any(type(row) is not dict for row in protocol['search_plan']):
        raise ValueError('protocol must contain a declared search plan')
    matches = [row for row in protocol['search_plan'] if row.get('search_id') == search_id]
    if len(matches) != 1 or set(matches[0]) != {'search_id', 'source', 'query', 'window'}:
        raise ValueError('one exact existing search plan without uninterpreted fields is required')
    spec = artifact['spec']
    dates = spec['date_filter']
    window = 'query_defined' if dates is None else dates['datetype'] + ':' + dates['mindate'] + '..' + dates['maxdate']
    if matches[0] != dict(search_id=search_id, source='pubmed', query=spec['query'], window=window):
        raise ValueError('existing query, source or date window does not match discovery')
    if not artifact['derived']['occurrences']:
        if artifact['derived']['observed_reported_count_accounted_for']:
            raise ValueError('zero-hit discovery stays in native artifact; no row provenance available for intake')
        raise ValueError('error-only discovery cannot be converted to intake')
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow(['record_id', 'source_locator', 'discovery_sha256', 'discovery_request_id', 'response_index', 'response_sha256',
                     'occurrence_index', 'response_occurrence_index'])
    for row in artifact['derived']['occurrences']:
        writer.writerow(['pubmed:' + row['pmid'], 'https://pubmed.ncbi.nlm.nih.gov/' + row['pmid'] + '/',
                         digest(artifact), spec['request_id'], row['response_index'], row['response_sha256'], row['occurrence_index'], row['response_occurrence_index']])
    return bibliographic_intake.prepare(protocol, out.getvalue().encode('utf-8'), search_id, artifact['execution']['started_at'])


def artifact_bytes(value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError('discovery JSON exceeds byte bound')
    return raw


def _read(path):
    with path.open('rb') as handle:
        raw = handle.read(MAX_ARTIFACT_BYTES + 1)
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError('input exceeds byte bound')
    return parse_json(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('preview', 'fetch', 'from-responses', 'verify', 'to-intake'):
        sub = commands.add_parser(name)
        sub.add_argument('input', type=Path)
        if name == 'from-responses':
            sub.add_argument('execution', type=Path)
        if name == 'fetch':
            sub.add_argument('--preview-sha256', required=True)
        if name == 'to-intake':
            sub.add_argument('protocol', type=Path)
            sub.add_argument('--search-id', required=True)
        if name != 'verify':
            sub.add_argument('--output', type=Path, required=name != 'preview')
    args = parser.parse_args()
    try:
        output = getattr(args, 'output', None)
        if output is not None and (output.exists() or output.is_symlink()):
            raise ValueError('output already exists or is a symbolic link')
        value = _read(args.input)
        if args.command == 'preview':
            result = preview(value)
        elif args.command == 'fetch':
            result = fetch(value, args.preview_sha256)
        elif args.command == 'from-responses':
            result = from_responses(value, _read(args.execution))
        elif args.command == 'verify':
            result = verify(value)
        else:
            result = to_intake(value, _read(args.protocol), args.search_id)
        rendered = artifact_bytes(result)
        if output is not None:
            with output.open('xb') as handle:
                handle.write(rendered)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, RecursionError) as error:
        safe = {'zero-hit discovery stays in native artifact; no row provenance available for intake',
                'error-only discovery cannot be converted to intake',
                'preview digest mismatch; preview the exact current spec and implementation first',
                'output already exists or is a symbolic link'}
        message = str(error) if str(error) in safe else 'invalid input, output, execution or digest; no retry performed'
        parser.exit(1, 'pubmed discovery error: ' + message + '\n')
    print(rendered.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
