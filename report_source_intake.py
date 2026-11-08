"""Append supplied source declarations to retrieved reports through reviewed exact replay."""
import argparse
import copy
import datetime
import errno
import hashlib
import json
import math
from pathlib import Path
import re

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from report_review_links import SOURCE_FIELDS, prepare_targets
from research_bundle import engine_hashes

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_CANDIDATES = 100
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
CANDIDATE_FIELDS = {'source', 'declared_by', 'declared_at', 'declaration_note'}
BOUNDARY = (
    'Explicit supplied source-declaration append and exact-input replay only. New declarations '
    'require an already retrieved report; pending, included and excluded full-text decisions are '
    'supported without changing retrieval, eligibility, memberships, evidence or research counts. '
    'No existing descriptor is edited, replaced, removed or designated the preferred/current version. '
    'Distinct supplied source IDs are preserved even if locators or digests match; identity is not inferred. '
    'A document digest is a supplied unverified assertion, and null remains explicitly unbound. '
    'No file, URL or source locator is opened, fetched, hashed or authenticated. No source content, '
    'reading, coverage, publication identity, scientific quality or completeness is established. '
    'Adding to a report source catalog can stale retained report/study/inventory/work assertions. '
    'Existing rows, hashes, opinions, decisions and completion states are retained without renewal; '
    'not every downstream assertion is source-bound or automatically reassessed. '
    'Declaration and review metadata are supplied human assertions, not verified identity, chronology '
    'or proof of execution. Consistently reauthored unsigned records can still replay. '
    'Source descriptors persist in the candidate protocol; declaration/review assertions and before/after '
    'contexts stay in this detached record. Ordinary bundles do not retain the original input or this '
    'application. Keep them with the recorded implementation. Source-byte checks remain separate. '
    'No scientific, clinical or experimental inference is performed. Keep private inputs outside the '
    'public repository.'
)
NEGATIVE_CLAIMS = dict(source_authenticity='NOT_VERIFIED', document_bytes_verification='NOT_PERFORMED',
    reading='NOT_ESTABLISHED', source_identity='NOT_ESTABLISHED', preferred_source_selection='NOT_PERFORMED',
    source_coverage='NOT_ESTABLISHED', declaration_correctness='NOT_ASSESSED',
    eligibility_assessment='NOT_PERFORMED', scientific_acceptance='NOT_ASSESSED',
    declarer_identity_verification='NOT_ESTABLISHED', reviewer_identity_verification='NOT_ESTABLISHED',
    existing_review_renewal='NOT_PERFORMED', downstream_reassessment='NOT_PERFORMED',
    declaration_assertion_scope='DETACHED_RECORD_ONLY', import_review_scope='DETACHED_RECORD_ONLY',
    census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', external_calls=0)


def _strict_json(value):
    pending, active = [(value, False)], set()
    while pending:
        item, leaving = pending.pop()
        kind = type(item)
        if leaving:
            active.remove(id(item))
            continue
        if kind in (dict, list):
            if id(item) in active:
                raise ValueError('JSON containers must not be cyclic')
            active.add(id(item))
            pending.append((item, True))
        if kind is dict:
            if any(type(key) is not str for key in item):
                raise ValueError('JSON object keys must be strings')
            pending.extend((child, False) for child in item.keys())
            pending.extend((child, False) for child in item.values())
        elif kind is list:
            pending.extend((child, False) for child in item)
        elif kind is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise ValueError('JSON strings must not contain unpaired surrogates')
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError('JSON numbers must be finite')
        elif kind not in (int, bool, type(None)):
            raise ValueError('value is not a strict JSON type')


def digest(value):
    _strict_json(value)
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalized(value, limit, label):
    _strict_json(value)
    raw = canonical_json_bytes(value)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _schema(value, fields, label):
    if type(value) is not dict or set(value) != fields:
        raise ValueError(label + ' has unknown or missing fields')
    if 'schema_version' in fields and (type(value['schema_version']) is not int or value['schema_version'] != 1):
        raise ValueError(label + ' schema_version must be integer 1')


def _text(value):
    return type(value) is str and bool(value.strip())


def _date(value, label):
    if not _text(value) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError(label + ' must be YYYY-MM-DD')
    try:
        datetime.date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(label + ' must be a real calendar date') from error


def implementation_hashes():
    return dict(engine_hashes(), **{
        'report_source_intake.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def _validate(protocol):
    if type(protocol) is not dict or 'reports' not in protocol:
        raise ValueError('source declaration intake requires a protocol with explicit reports')
    if 'adapter_receipts' in protocol:
        raise ValueError('mock adapter_receipts inputs are unsupported for source declaration intake')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False)
    prepared = prepare_targets(protocol, research.get('bibliographic_collection'))
    return research, reports, prepared


def _new_report(prepared, report_id):
    if not _text(report_id):
        raise ValueError('report_id must be an explicit nonblank literal string')
    target = next((row for row in prepared['report_targets'] if row['report_id'] == report_id), None)
    if target is None:
        raise ValueError('unknown report_id for new source declaration')
    if target['retrieval'] != 'retrieved':
        raise ValueError('new source declarations require an already retrieved report')
    return target


def template(protocol, report_id):
    """Scaffold only an explicitly selected report ID; no source or human facts."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    _, _, prepared = _validate(protocol)
    target = _new_report(prepared, report_id)
    source = {key: None for key in sorted(SOURCE_FIELDS)}
    source['report_id'] = report_id
    row = dict(source=source, declared_by=None, declared_at=None, declaration_note=None)
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_SOURCE_DECLARATIONS',
        candidate_document=dict(schema_version=1, candidates=[row]), proposed_report_target=target,
        protocol_sha256=digest(protocol), engine_sha256=implementation_hashes(),
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Incomplete declaration only. Supply every missing field honestly. document_sha256 may remain explicit null for unbound bytes; a supplied digest is not measured or verified. No source ID, version, locator, human label or approval is inferred.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'candidates'}, 'candidate document')
    rows = document['candidates']
    if type(rows) is not list or not 1 <= len(rows) <= MAX_CANDIDATES:
        raise ValueError('candidates must be a nonempty list of at most 100 rows')
    for row in rows:
        _schema(row, CANDIDATE_FIELDS, 'source declaration candidate')
        if any(not _text(row[key]) for key in CANDIDATE_FIELDS - {'source'}):
            raise ValueError('declaration metadata must be supplied nonblank literal strings')
        _date(row['declared_at'], 'declared_at')
        source = row['source']
        _schema(source, SOURCE_FIELDS, 'source descriptor')
        if any(not _text(source[key]) for key in SOURCE_FIELDS - {'document_sha256'}):
            raise ValueError('source descriptor text fields must be supplied nonblank literal strings')
        value = source['document_sha256']
        if value is not None and (type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None):
            raise ValueError('document_sha256 must be explicit null or 64 lowercase hexadecimal characters')


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'append_source_declarations':
        raise ValueError('review decision must be append_source_declarations')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _source_summary(prepared):
    sources = [row['source'] for row in prepared['source_ledger']]
    return dict(stage=prepared['source_stage'], source_declarations=len(sources),
        reports_with_declarations=len({row['report_id'] for row in sources}),
        declarations_without_byte_digest=sum(row['document_sha256'] is None for row in sources),
        document_bytes_verification='NOT_PERFORMED')


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports, before_sources = _validate(protocol)
    reports = {row['report_id']: row for row in before_sources['report_targets']}
    selected_report_ids = []
    for row in document['candidates']:
        report_id = row['source']['report_id']
        _new_report(before_sources, report_id)
        if report_id not in selected_report_ids:
            selected_report_ids.append(report_id)
    candidate = copy.deepcopy(protocol)
    first_index = len(candidate.get('report_sources', []))
    candidate.setdefault('report_sources', []).extend(copy.deepcopy(row['source']) for row in document['candidates'])
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    # Existing full validation rejects duplicate source IDs and invalid downstream links.
    after, after_reports, after_sources = _validate(candidate)
    if (canonical_json_bytes(before['flow']) != canonical_json_bytes(after['flow']) or
            canonical_json_bytes(before_reports['report_flow']) != canonical_json_bytes(after_reports['report_flow'])):
        raise ValueError('source declaration intake must preserve record/report flows and eligibility')
    restored = copy.deepcopy(candidate)
    if 'report_sources' in protocol:
        restored['report_sources'] = restored['report_sources'][:first_index]
    else:
        del restored['report_sources']
    if canonical_json_bytes(restored) != canonical_json_bytes(protocol):
        raise ValueError('source declaration intake must preserve every existing input field')
    record_ids = {rid for report_id in selected_report_ids for rid in reports[report_id]['recorded_report']['record_ids']}
    after_by_report = {row['report_id']: row for row in after_sources['report_targets']}
    target = dict(schema_version=1, target_type='report_source_declaration_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document),
        selected_report_targets=[copy.deepcopy(reports[rid]) for rid in selected_report_ids],
        candidate_report_targets=[copy.deepcopy(after_by_report[rid]) for rid in selected_report_ids],
        selected_record_targets=[copy.deepcopy(row) for row in before_sources['record_targets']
                                 if row['record_id'] in record_ids],
        appended_sources=[dict(candidate_index=index, output_pointer='/report_sources/%d' % (first_index + index),
                               source=copy.deepcopy(row['source'])) for index, row in enumerate(document['candidates'])],
        engine_sha256=implementation_hashes())
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, before_sources, after, after_reports, after_sources


def prepare(protocol, candidate_document):
    """Validate completed source declarations and offer a separate blank review document."""
    protocol, document, target, *_ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_SOURCE_DECLARATION_REVIEW', target=target,
        review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Completed source declarations are supplied assertions. Fill every human review field honestly; this is not document-byte verification, source authentication or scientific approval.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed source declarations only, leaving prior rows and all other fields intact."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    (protocol, document, target, candidate, before, before_reports, before_sources,
     after, after_reports, after_sources) = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target differs from exact input, candidates and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=copy.deepcopy(before_reports['report_flow']),
        after_report_flow=copy.deepcopy(after_reports['report_flow']),
        before_source_summary=_source_summary(before_sources),
        after_source_summary=_source_summary(after_sources),
        engine_sha256=implementation_hashes(), **NEGATIVE_CLAIMS, boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_report_source_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Compare the entire replayed record, not just its editable checksum."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_report_source_intake' or type(record['receipt']) is not dict
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached source declaration intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied declarations and review, and recorded implementation; not authentication or scientific validation.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def _encode(value):
    _strict_json(value)
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_APPLICATION_BYTES:
        raise ValueError('serialized output exceeds byte limit')
    return raw


def render_text(result):
    _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    text = 'Supplied report source declaration intake\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'
    if len(text.encode('utf-8')) > MAX_APPLICATION_BYTES:
        raise ValueError('text output exceeds byte limit')
    return text


def _read(path, limit, label):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _write_new(path, raw):
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(errno.EEXIST, 'output directory entry already exists', str(path))
    with path.open('xb') as output:
        output.write(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    scaffold = commands.add_parser('template')
    target = commands.add_parser('target')
    assembly = commands.add_parser('assemble')
    replay = commands.add_parser('verify')
    for command in (scaffold, target, assembly, replay):
        command.add_argument('protocol', type=Path)
        command.add_argument('--text', action='store_true')
    scaffold.add_argument('--report-id', required=True)
    scaffold.add_argument('--candidate-output', required=True, type=Path)
    for command in (target, assembly):
        command.add_argument('candidate_document', type=Path)
        command.add_argument('--output', required=True, type=Path)
    assembly.add_argument('review_document', type=Path)
    replay.add_argument('application_record', type=Path)
    replay.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        protocol = _read(args.protocol, MAX_PROTOCOL_BYTES, 'original protocol')
        if args.command == 'template':
            result = template(protocol, args.report_id)
            destination, artifact = args.candidate_output, result['candidate_document']
        elif args.command == 'verify':
            record = _read(args.application_record, MAX_APPLICATION_BYTES, 'application record')
            result = verify(protocol, record)
            destination, artifact = args.protocol_output, record['protocol_candidate']
        else:
            document = _read(args.candidate_document, MAX_CANDIDATE_BYTES, 'candidate document')
            result = (prepare(protocol, document) if args.command == 'target' else
                      assemble(protocol, document, _read(args.review_document, MAX_CANDIDATE_BYTES, 'review document')))
            destination, artifact = args.output, result
        stdout = render_text(result).encode('utf-8') if args.text else _encode(result)
        if len(stdout) > MAX_APPLICATION_BYTES:
            raise ValueError('stdout exceeds byte limit')
        if destination is not None:
            output = _encode(artifact)
            limit = (MAX_PROTOCOL_BYTES if args.command == 'verify' else
                     MAX_CANDIDATE_BYTES if args.command == 'template' else MAX_APPLICATION_BYTES)
            if len(output) > limit:
                raise ValueError('output exceeds byte limit')
            _write_new(destination, output)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'source declaration intake error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
