"""Explicit bounded PubMed EFetch MEDLINE-text acquisition; no evidence promotion.

The reused fixed-column NBIB parser accepts only its documented compatible
subset, not every MEDLINE response. Native response bytes remain authoritative.
"""
import argparse
import base64
import copy
import csv
import hashlib
import http.client
import io
import json
import math
from pathlib import Path
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import bibliographic_intake
import nbib_intake
from nbib_export_parser import parse_export
import pubmed_discovery
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json

ENDPOINT = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
MAX_BODY_BYTES = 262_144
MAX_ARTIFACT_BYTES = 50_000_000
MAX_PARSE_LINES = 1000
MAX_PARSE_FIELDS = 500
MAX_PARSE_RECORDS = 40
MAX_PARSED_RESPONSE_BYTES = 1_000_000
MAX_SELECTED = 100
MAX_BATCH_IDS = 20
MAX_REQUESTS = 10
REQUEST_TIMEOUT = 10.0
OVERALL_TIMEOUT = 60.0
SAFE_HEADERS = {'content-type', 'content-length', 'transfer-encoding', 'date', 'retry-after'}
ERRORS = {None, 'network_error', 'tls_error', 'timeout', 'body_too_large', 'incomplete_body', 'elapsed_limit'}
FORMAT = 'efetch_medline_text_fixed_column_compatible_subset'
GROUPING = ('Exact literal PMID grouping in first-selected order only reduces outgoing IDs. '
            'Every selected discovery occurrence is retained; no publication identity deduplication.')
BOUNDARY = (
    'Explicit selected-ID EFetch acquisition using db=pubmed, rettype=medline, retmode=text. '
    'The existing fixed-column NBIB parser covers a compatible subset, not all MEDLINE grammar. '
    'Only complete error-free HTTP 200 bodies are parsed; unsupported content is retained without fallback. '
    'TI and AB are unreviewed candidate metadata; absent AB means not present, not a retrieval failure. '
    'Returned IDs are reconciled literally, not positionally; no publication identity deduplication. '
    'Neither a completed selection nor unsigned deterministic replay establishes search completeness, '
    'an authenticated retrieval, publication identity, query adequacy or an index snapshot. '
    'Consistently reauthored records can replay. No full text, screening, evidence or clinical claims. '
    'The process-local throttle is shared with discovery; it is not shared-IP pacing or a hard wall-clock guarantee. '
    'No redirects, proxy, credentials, cookies, history, retries, fallback provider or model calls. '
    'No protocol or declared search-plan changes. An ordinary CSV intake verifies its own derivative, '
    'not this acquisition; retain this native artifact for full-response, separator and occurrence provenance. '
    'Retained queries and native responses are not redacted; keep real outputs outside public repositories.'
)
HEADERS = (
    'record_id', 'source_locator', 'metadata_acquisition_sha256', 'metadata_request_id',
    'metadata_acquisition_status', 'metadata_stop_reason', 'metadata_candidate_id',
    'discovery_sha256', 'discovery_request_id', 'selected_discovery_occurrence_indices_json',
    'selected_discovery_occurrences_json', 'response_index', 'response_sha256', 'response_started_at',
    'response_record_index', 'native_format', 'native_record_span_json', 'native_fields_json',
    'native_record_text', 'candidate_title_fields_json', 'candidate_abstract_fields_json', 'abstract_status',
)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return dict(pubmed_discovery.implementation_hashes(), **nbib_intake.implementation_hashes(), **{
        'pubmed_metadata.py': hashlib.sha256((root / 'pubmed_metadata.py').read_bytes()).hexdigest()})


def artifact_bytes(value):
    nbib_intake._strict_json(value)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError('metadata JSON exceeds byte bound')
    return raw


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def validate_selection(discovery, selection):
    nbib_intake._strict_json(discovery)
    pubmed_discovery.verify(discovery)
    nbib_intake._strict_json(selection)
    keys = {'schema_version', 'request_id', 'occurrence_indices', 'batch_size', 'max_requests'}
    if (type(selection) is not dict or set(selection) != keys
            or type(selection['schema_version']) is not int or selection['schema_version'] != 1):
        raise ValueError('invalid metadata selection fields or schema')
    request = selection['request_id']
    if type(request) is not str or not request.strip() or '\x00' in request or len(request.encode('utf-8')) > 200:
        raise ValueError('invalid bounded metadata request_id')
    indices = selection['occurrence_indices']
    rows = discovery['derived']['occurrences']
    if (type(indices) is not list or not 1 <= len(indices) <= MAX_SELECTED
            or any(not _integer(index, 0, len(rows) - 1) for index in indices)
            or len(set(indices)) != len(indices)):
        raise ValueError('select 1 to 100 distinct zero-based discovery occurrence indices')
    if (not _integer(selection['batch_size'], 1, MAX_BATCH_IDS)
            or not _integer(selection['max_requests'], 1, MAX_REQUESTS)):
        raise ValueError('invalid metadata batch or request bound')
    return copy.deepcopy(selection)


def parameters(pmids):
    return dict(db='pubmed', rettype='medline', retmode='text', id=','.join(pmids))


def preview(discovery, selection):
    selection = validate_selection(discovery, selection)
    groups = {}
    selected = []
    for position, index in enumerate(selection['occurrence_indices']):
        row = discovery['derived']['occurrences'][index]
        groups.setdefault(row['pmid'], []).append(index)
        selected.append(dict(selection_position=position, discovery_occurrence=copy.deepcopy(row)))
    pmids = list(groups)
    batches = [pmids[start:start + selection['batch_size']] for start in range(0, len(pmids), selection['batch_size'])]
    request_indices = {pmid: index for index, batch in enumerate(batches) for pmid in batch}
    for row in selected:
        row['request_index'] = request_indices[row['discovery_occurrence']['pmid']]
        row['scheduled_within_request_limit'] = row['request_index'] < selection['max_requests']
    requests = [dict(response_index=index, pmids=batch, parameters=parameters(batch))
                for index, batch in enumerate(batches[:selection['max_requests']])]
    result = dict(schema_version=1, mode='pubmed_metadata_preview', selection=selection,
        discovery_sha256=digest(discovery), discovery_request_id=discovery['spec']['request_id'],
        endpoint=ENDPOINT, method='GET', native_format=FORMAT, grouping=GROUPING,
        selected_occurrences=selected,
        literal_pmid_groups=[dict(pmid=pmid, selected_occurrence_indices=indices) for pmid, indices in groups.items()],
        planned_batch_count=len(batches), request_batches=requests,
        request_timeout_seconds=REQUEST_TIMEOUT, overall_timeout_seconds=OVERALL_TIMEOUT,
        max_response_bytes=MAX_BODY_BYTES, max_artifact_bytes=MAX_ARTIFACT_BYTES,
        max_parse_physical_lines=MAX_PARSE_LINES, max_parse_fields=MAX_PARSE_FIELDS,
        max_parse_records=MAX_PARSE_RECORDS, max_parsed_response_bytes=MAX_PARSED_RESPONSE_BYTES,
        max_selected_occurrences=MAX_SELECTED,
        max_ids_per_batch=MAX_BATCH_IDS, max_requests=MAX_REQUESTS,
        minimum_request_interval_seconds=1, implementation_sha256=implementation_hashes(),
        external_calls=0, boundary=BOUNDARY)
    result['preview_sha256'] = digest(result)
    artifact_bytes(result)
    return result


def _complete_framing(headers, size):
    """Fail closed on ambiguous framing, including comma-joined duplicate headers."""
    length, encoding = headers.get('content-length'), headers.get('transfer-encoding')
    if length is not None:
        if encoding is not None or re.fullmatch(r'[0-9]{1,20}', length) is None or int(length) != size:
            return False
    return encoding is None or encoding.lower() == 'chunked'


def _attempt(record):
    keys = {'parameters', 'status', 'headers', 'started_at', 'elapsed_seconds', 'body_base64', 'body_complete', 'error'}
    if type(record) is not dict or set(record) != keys:
        raise ValueError('invalid metadata attempt fields')
    pubmed_discovery._timestamp(record['started_at'])
    elapsed = record['elapsed_seconds']
    if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError('invalid elapsed seconds')
    status = record['status']
    if status is not None and not _integer(status, 100, 599):
        raise ValueError('invalid HTTP status')
    headers = record['headers']
    if (type(headers) is not dict or not set(headers) <= SAFE_HEADERS
            or any(type(value) is not str or len(value) > 1000 for value in headers.values())):
        raise ValueError('invalid safe response headers')
    error = record['error']
    if type(record['body_complete']) is not bool or (error is not None and type(error) is not str) or error not in ERRORS:
        raise ValueError('invalid completeness or transport error')
    if error is None and status is None:
        raise ValueError('error-free attempt must have an HTTP status')
    encoded = record['body_base64']
    if type(encoded) is not str or len(encoded) > 4 * ((MAX_BODY_BYTES + 2) // 3):
        raise ValueError('invalid bounded base64 body')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ValueError('invalid base64 response body') from None
    if len(raw) > MAX_BODY_BYTES or base64.b64encode(raw).decode('ascii') != encoded:
        raise ValueError('invalid bounded canonical base64 body')
    if record['body_complete'] and not _complete_framing(headers, len(raw)):
        raise ValueError('complete body contradicts retained response framing')
    return raw


def _native(raw):
    # Preflight bounds before the parser allocates ordered field/span structures.
    lines = re.split(b'\r\n|\r|\n', raw)
    if lines and lines[-1] == b'':
        lines.pop()
    fields = sum(bool(line) and not line.startswith(b'      ') for line in lines)
    records = sum(line.startswith(b'PMID- ') or (index == 0 and line.startswith(b'\xef\xbb\xbfPMID- '))
                  for index, line in enumerate(lines))
    if len(lines) > MAX_PARSE_LINES or fields > MAX_PARSE_FIELDS or records > MAX_PARSE_RECORDS:
        return None, 'native_expansion_limit'
    try:
        parsed = parse_export(raw)
        if len(artifact_bytes(parsed)) > MAX_PARSED_RESPONSE_BYTES:
            return None, 'native_expansion_limit'
        return parsed, None
    except (ValueError, UnicodeError, RecursionError):
        return None, 'unsupported_native_response'


def _candidate(native, response_index, record_index, group):
    def fields(tag):
        return [dict(field_index=index, unfolded_text=' '.join(field['value_lines']))
                for index, field in enumerate(native['fields']) if field['tag'] == tag]
    title, abstract = fields('TI'), fields('AB')
    return dict(candidate_id=f'metadata-response-{response_index + 1:03d}-record-{record_index + 1:03d}',
        pmid=native['pmid'], response_index=response_index, response_record_index=record_index,
        selected_discovery_occurrence_indices=list(group), title_fields=title, abstract_fields=abstract,
        abstract_status='PRESENT' if abstract else 'NOT_PRESENT', metadata_status='UNREVIEWED_CANDIDATE')


def _analyze(prepared, attempts):
    responses, candidates = [], []
    stop = None
    groups = {row['pmid']: row['selected_occurrence_indices'] for row in prepared['literal_pmid_groups']}
    request_batches = prepared['request_batches']
    for index, record in enumerate(attempts):
        if stop is not None or index >= len(request_batches):
            raise ValueError('attempt recorded after required stop or request limit')
        raw = _attempt(record)
        expected = request_batches[index]
        if record['parameters'] != expected['parameters']:
            raise ValueError('attempt parameters differ from explicit bounded selection')
        response = dict(response_index=index, response_sha256=hashlib.sha256(raw).hexdigest(),
            response_bytes=len(raw), requested_pmids=list(expected['pmids']), returned_pmids=[],
            parsed_export=None, reconciliation=None, diagnostic=None)
        if record['error'] is not None:
            stop = record['error']
        elif record['status'] != 200:
            stop = 'http_status'
        elif not record['body_complete']:
            stop = 'incomplete_body'
        else:
            parsed, stop = _native(raw)
            response['parsed_export'] = parsed
            if parsed is not None:
                returned = [row['pmid'] for row in parsed['records']]
                response['returned_pmids'] = returned
                duplicates = list(dict.fromkeys(pmid for pmid in returned if returned.count(pmid) > 1))
                missing = [pmid for pmid in expected['pmids'] if pmid not in returned]
                unexpected = list(dict.fromkeys(pmid for pmid in returned if pmid not in expected['pmids']))
                response['reconciliation'] = dict(duplicate_pmids=duplicates, missing_pmids=missing,
                    unexpected_pmids=unexpected, exact_literal_id_match=not (duplicates or missing or unexpected))
                if duplicates:
                    stop = 'duplicate_returned_pmid'
                elif unexpected:
                    stop = 'unexpected_returned_pmid'
                elif missing:
                    stop = 'missing_returned_pmid'
                else:
                    candidates.extend(_candidate(row, index, native_index, groups[row['pmid']])
                                      for native_index, row in enumerate(parsed['records']))
        response['diagnostic'] = stop
        responses.append(response)
        if stop is None and index + 1 == prepared['planned_batch_count']:
            stop = 'selected_ids_received'
        elif stop is None and index + 1 == prepared['selection']['max_requests']:
            stop = 'max_requests'
    by_pmid = {row['pmid']: row for row in candidates}
    mapping = []
    for selected in prepared['selected_occurrences']:
        row = copy.deepcopy(selected)
        candidate = by_pmid.get(row['discovery_occurrence']['pmid'])
        row['candidate_id'] = candidate['candidate_id'] if candidate else None
        row['metadata_status'] = ('AVAILABLE_UNREVIEWED' if candidate else
            'RESPONSE_DIAGNOSTIC' if row['request_index'] < len(responses) else 'NOT_REQUESTED')
        mapping.append(row)
    return dict(responses=responses, candidates=candidates, selected_occurrence_mapping=mapping,
        selected_occurrence_count=len(mapping), unique_literal_pmid_count=len(groups),
        received_native_record_count=len(candidates), mapped_selected_occurrence_count=sum(row['candidate_id'] is not None for row in mapping),
        acquisition_status='SELECTED_IDS_RECEIVED' if stop == 'selected_ids_received' else 'INCOMPLETE',
        stop_reason=stop)


def from_responses(discovery, selection, execution):
    """Regenerate unsigned supplied records offline; does not prove a request occurred."""
    prepared = preview(discovery, selection)
    nbib_intake._strict_json(execution)
    if type(execution) is not dict or set(execution) != {'started_at', 'attempts', 'stop_reason'}:
        raise ValueError('invalid execution fields')
    started = pubmed_discovery._timestamp(execution['started_at'])
    attempts = execution['attempts']
    if type(attempts) is not list or len(attempts) > len(prepared['request_batches']):
        raise ValueError('invalid bounded attempts')
    derived = _analyze(prepared, attempts)
    last = started
    for record in attempts:
        when = pubmed_discovery._timestamp(record['started_at'])
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
            raise ValueError('execution must reach a selection, bound or diagnostic')
        derived['stop_reason'] = 'elapsed_limit'
    elif execution['stop_reason'] != derived['stop_reason']:
        raise ValueError('recorded stop differs from regenerated stop')
    result = dict(schema_version=1, mode='pubmed_metadata', native_format=FORMAT,
        discovery_artifact=copy.deepcopy(discovery), discovery_sha256=prepared['discovery_sha256'],
        selection=prepared['selection'], preview_sha256=prepared['preview_sha256'],
        execution=copy.deepcopy(execution), derived=derived, grouping=GROUPING,
        implementation_sha256=implementation_hashes(), search_completeness='NOT_ESTABLISHED',
        census='NOT_ESTABLISHED', conclusion='NOT_READY', source_authenticity='NOT_VERIFIED',
        publication_identity='NOT_VERIFIED', query_adequacy='NOT_VERIFIED', index_snapshot='NOT_VERIFIED',
        review_status='NOT_PERFORMED', protocol_changed=False, boundary=BOUNDARY)
    artifact_bytes(result)
    return result


_NoRedirect = pubmed_discovery._NoRedirect


def _utcnow():
    return pubmed_discovery._utcnow()


def _transport(params, timeout):
    """Fixed HTTPS GET with normal TLS; read1 retains bounded raw/error bytes."""
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=ssl.create_default_context()),
                    urllib.request.HTTPDefaultErrorHandler(), _NoRedirect(), urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    request = urllib.request.Request(ENDPOINT + '?' + urllib.parse.urlencode(params), method='GET')
    begin = time.monotonic()
    result = dict(parameters=copy.deepcopy(params), status=None, headers={}, started_at=_utcnow(),
        elapsed_seconds=0, body_base64='', body_complete=False, error=None)
    raw, response = b'', None
    try:
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        result['status'] = response.code
        for key, value in response.headers.items():
            key = key.lower()
            if key in SAFE_HEADERS:
                previous = result['headers'].get(key)
                result['headers'][key] = ((previous + ', ' + value) if previous is not None else value)[:1000]
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
            result['error'], result['body_complete'] = 'body_too_large', False
        if result['body_complete'] and not _complete_framing(result['headers'], len(raw)):
            result['error'], result['body_complete'] = 'incomplete_body', False
    except http.client.IncompleteRead as error:
        raw = (raw + error.partial)[:MAX_BODY_BYTES]
        result['error'], result['body_complete'] = 'incomplete_body', False
    except TimeoutError:
        result['error'] = 'timeout'
    except ssl.SSLError:
        result['error'] = 'tls_error'
    except urllib.error.URLError as error:
        result['error'] = ('tls_error' if isinstance(error.reason, ssl.SSLError) else
                           'timeout' if isinstance(error.reason, TimeoutError) else 'network_error')
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


def fetch(discovery, selection, preview_sha256, transport=None):
    """Explicit digest-bound live invocation; injected transport is for offline tests."""
    discovery, selection = copy.deepcopy(discovery), copy.deepcopy(selection)
    prepared = preview(discovery, selection)
    if type(preview_sha256) is not str or preview_sha256 != prepared['preview_sha256']:
        raise ValueError('preview digest mismatch; preview exact current discovery, selection and implementation first')
    transport = _transport if transport is None else transport
    execution = dict(started_at=_utcnow(), attempts=[], stop_reason=None)
    begin = time.monotonic()
    while execution['stop_reason'] is None:
        # Reuse discovery's actual module state without changing its source bytes.
        with pubmed_discovery._LOCK:
            now = time.monotonic()
            last = pubmed_discovery._LAST_REQUEST
            delay = max(0, 1 - (now - last)) if last is not None else 0
            if OVERALL_TIMEOUT - (now - begin) - delay <= 0:
                execution['stop_reason'] = 'elapsed_limit'
                break
            if delay:
                time.sleep(delay)
            now = time.monotonic()
            remaining = OVERALL_TIMEOUT - (now - begin)
            if remaining <= 0:
                execution['stop_reason'] = 'elapsed_limit'
                break
            pubmed_discovery._LAST_REQUEST = now
        params = prepared['request_batches'][len(execution['attempts'])]['parameters']
        execution['attempts'].append(transport(copy.deepcopy(params), min(REQUEST_TIMEOUT, remaining)))
        execution['stop_reason'] = _analyze(prepared, execution['attempts'])['stop_reason']
        if execution['stop_reason'] is None and time.monotonic() - begin >= OVERALL_TIMEOUT:
            execution['stop_reason'] = 'elapsed_limit'
    return from_responses(discovery, selection, execution)


def verify(artifact):
    artifact_bytes(artifact)
    if type(artifact) is not dict or artifact.get('implementation_sha256') != implementation_hashes():
        raise ValueError('metadata implementation mismatch')
    expected = from_responses(artifact.get('discovery_artifact'), artifact.get('selection'), artifact.get('execution'))
    if canonical_json_bytes(artifact) != canonical_json_bytes(expected):
        raise ValueError('metadata artifact differs from deterministic regeneration')
    return dict(valid=True, artifact_sha256=digest(artifact), discovery_sha256=artifact['discovery_sha256'],
        acquisition_status=expected['derived']['acquisition_status'],
        mapped_selected_occurrences=expected['derived']['mapped_selected_occurrence_count'],
        received_native_records=expected['derived']['received_native_record_count'], external_calls=0,
        verification_scope='Unsigned supplied discovery, selection, native bytes and deterministic derivation only; not proof of retrieval',
        search_completeness='NOT_ESTABLISHED', census='NOT_ESTABLISHED', conclusion='NOT_READY')


def to_intake(artifact, protocol, search_id):
    """Explicit unreviewed CSV derivative; native acquisition remains separately required."""
    verify(artifact)
    nbib_intake._strict_json(protocol)
    if (type(protocol) is not dict or type(protocol.get('search_plan')) is not list
            or any(type(row) is not dict for row in protocol['search_plan'])):
        raise ValueError('protocol must contain a declared search plan')
    matches = [row for row in protocol['search_plan'] if row.get('search_id') == search_id]
    if len(matches) != 1 or set(matches[0]) != {'search_id', 'source', 'query', 'window'}:
        raise ValueError('one exact existing search plan without uninterpreted fields is required')
    discovery = artifact['discovery_artifact']
    spec, dates = discovery['spec'], discovery['spec']['date_filter']
    window = 'query_defined' if dates is None else dates['datetype'] + ':' + dates['mindate'] + '..' + dates['maxdate']
    if matches[0] != dict(search_id=search_id, source='pubmed', query=spec['query'], window=window):
        raise ValueError('existing query, source or date window does not match discovery')
    candidates = artifact['derived']['candidates']
    if not candidates:
        raise ValueError('no fully reconciled native metadata records available for intake')
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow(HEADERS)
    sha = digest(artifact)
    for candidate in candidates:
        index = candidate['response_index']
        response = artifact['derived']['responses'][index]
        native = response['parsed_export']['records'][candidate['response_record_index']]
        indices = candidate['selected_discovery_occurrence_indices']
        occurrences = [discovery['derived']['occurrences'][position] for position in indices]
        writer.writerow(['pubmed:' + candidate['pmid'], 'https://pubmed.ncbi.nlm.nih.gov/' + candidate['pmid'] + '/',
            sha, artifact['selection']['request_id'], artifact['derived']['acquisition_status'], artifact['derived']['stop_reason'],
            candidate['candidate_id'], artifact['discovery_sha256'], spec['request_id'],
            canonical_json_bytes(indices).decode('utf-8'), canonical_json_bytes(occurrences).decode('utf-8'),
            index, response['response_sha256'], artifact['execution']['attempts'][index]['started_at'],
            candidate['response_record_index'], FORMAT, canonical_json_bytes(native['source_span']).decode('utf-8'),
            canonical_json_bytes(native['fields']).decode('utf-8'), native['raw_text'],
            canonical_json_bytes(candidate['title_fields']).decode('utf-8'),
            canonical_json_bytes(candidate['abstract_fields']).decode('utf-8'), candidate['abstract_status']])
    return bibliographic_intake.prepare(protocol, out.getvalue().encode('utf-8'), search_id,
                                        discovery['execution']['started_at'])


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
        if name in ('preview', 'fetch', 'from-responses'):
            sub.add_argument('selection', type=Path)
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
            result = preview(value, _read(args.selection))
        elif args.command == 'fetch':
            result = fetch(value, _read(args.selection), args.preview_sha256)
        elif args.command == 'from-responses':
            result = from_responses(value, _read(args.selection), _read(args.execution))
        elif args.command == 'verify':
            result = verify(value)
        else:
            result = to_intake(value, _read(args.protocol), args.search_id)
        rendered = artifact_bytes(result)
        if output is not None:
            with output.open('xb') as handle:
                handle.write(rendered)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, RecursionError):
        parser.exit(1, 'pubmed metadata error: invalid input, output, execution or digest; no retry performed\n')
    print(rendered.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
