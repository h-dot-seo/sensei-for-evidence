"""Append explicitly supplied descriptive study inventory through reviewed exact replay."""
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
from report_study_inventory_links import (INVENTORY_FIELDS, link_report_study_inventory,
                                          prepare_candidate_target)
from research_bundle import engine_hashes

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_CANDIDATES = 100
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicit supplied descriptions of candidate report-study pairs and exact-input replay only. '
    'Only completed supplied inventory assertions are appended; all prior raw fields are retained. '
    'Retrieved reports may be pending, included or excluded. Description intake never selects '
    'canonical membership, changes eligibility, adds results, resolves study identity or establishes '
    'independence or inventory/extraction/search completeness. No description, study label, source '
    'selection, recorder, date, locator or human review is invented. '
    'New assertions must match current supplied source context; old assertions and reviews are '
    'neither replaced nor renewed. Additional descriptions can stale existing candidate eligibility '
    'reviews; no winner, consensus, reassessment or automatic review renewal is inferred. '
    'Source hashes bind supplied context, not document bytes, actual reading or description truth. '
    'All locators and source text remain inert; no source is opened, fetched or executed. '
    'Supplied digests, people and dates are unverified. This editable unsigned detached record is '
    'not authentication, chronology or proof of execution; consistently reauthored assertions can replay. '
    'Inventory rows and source context hashes persist in the candidate; import-review assertions and '
    'selected source snapshots remain in this detached application. Ordinary bundles do not retain '
    'the application or original input. Keep those and the recorded implementation separately. '
    'No prior scientific, work, planning or completion assertion is changed or renewed, and not all '
    'downstream assertions are source-bound or automatically assessed. '
    'Keep private source data and generated artifacts outside the public repository.'
)
NEGATIVE_CLAIMS = dict(source_authenticity='NOT_VERIFIED', document_bytes_verification='NOT_PERFORMED',
    reading='NOT_ESTABLISHED', description_correctness='NOT_ASSESSED',
    study_identity='NOT_ESTABLISHED', study_independence='NOT_ESTABLISHED',
    inventory_completeness='NOT_ESTABLISHED', extraction_completeness='NOT_ESTABLISHED',
    eligibility_assessment='NOT_PERFORMED', canonical_study_selection='NOT_PERFORMED',
    recorder_identity_verification='NOT_ESTABLISHED', reviewer_identity_verification='NOT_ESTABLISHED',
    existing_review_renewal='NOT_PERFORMED', downstream_reassessment='NOT_PERFORMED',
    source_snapshot_scope='DETACHED_RECORD_ONLY', import_review_scope='DETACHED_RECORD_ONLY',
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
        'inventory_intake.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def _validate(protocol):
    if type(protocol) is not dict or 'reports' not in protocol:
        raise ValueError('inventory intake requires a protocol with explicit reports')
    if 'adapter_receipts' in protocol:
        raise ValueError('mock adapter_receipts inputs are unsupported for inventory intake')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False)
    inventory = link_report_study_inventory(protocol, research.get('bibliographic_collection'))
    return research, reports, inventory


def _new_target(protocol, report_id, study_id, research):
    target = prepare_candidate_target(protocol, report_id, study_id, research.get('bibliographic_collection'))
    if target['retrieval'] != 'retrieved':
        raise ValueError('new descriptive inventory requires an already retrieved report')
    if target['source_binding_state'] == 'SOURCE_NOT_SUPPLIED':
        raise ValueError('new descriptive inventory requires existing report source descriptors')
    return target


def template(protocol, report_id, study_id):
    """Scaffold explicit IDs and a current source basis, never human assertions."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    research, _, _ = _validate(protocol)
    target = _new_target(protocol, report_id, study_id, research)
    row = {key: None for key in sorted(INVENTORY_FIELDS)}
    row.update(report_id=report_id, study_id=study_id, source_basis_sha256=target['source_basis_sha256'])
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_INVENTORY',
        candidate_document=dict(schema_version=1, candidates=[row]), proposed_target=target,
        protocol_sha256=digest(protocol), engine_sha256=implementation_hashes(),
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Incomplete descriptive assertion only. Supply every null field honestly, including source_ids. A source basis hash is not review approval. No membership or study identity is inferred.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'candidates'}, 'candidate document')
    rows = document['candidates']
    if type(rows) is not list or not 1 <= len(rows) <= MAX_CANDIDATES:
        raise ValueError('candidates must be a nonempty list of at most 100 rows')
    for row in rows:
        _schema(row, INVENTORY_FIELDS, 'inventory candidate')
        if any(not _text(row[key]) for key in INVENTORY_FIELDS - {'source_ids'}):
            raise ValueError('inventory candidate scalar fields must be supplied nonblank literal strings')
        _date(row['recorded_at'], 'recorded_at')
        if re.fullmatch(r'[0-9a-f]{64}', row['source_basis_sha256']) is None:
            raise ValueError('source_basis_sha256 must be 64 lowercase hexadecimal characters')
        sources = row['source_ids']
        if (type(sources) is not list or not sources or any(not _text(s) for s in sources)
                or len(sources) != len(set(sources))):
            raise ValueError('source_ids require explicit nonempty unique literal strings')


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_descriptive_inventory':
        raise ValueError('review decision must be import_descriptive_inventory')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports, before_inventory = _validate(protocol)
    reports = {row['report_id']: row for row in before_inventory['report_targets']}
    sources = {row['source']['source_id']: row for row in before_inventory['source_ledger']}
    selected_targets, selected_report_ids, selected_sources = [], [], []
    for index, row in enumerate(document['candidates']):
        target = _new_target(protocol, row['report_id'], row['study_id'], before)
        if row['source_basis_sha256'] != target['source_basis_sha256']:
            raise ValueError('new inventory source basis must match current context; no automatic renewal')
        selected_targets.append(dict(candidate_index=index, inventory_id=row['inventory_id'], target=target))
        if row['report_id'] not in selected_report_ids:
            selected_report_ids.append(row['report_id'])
        for source_id in row['source_ids']:
            source = sources.get(source_id)
            if source is None or source['source']['report_id'] != row['report_id']:
                raise ValueError('source_id must identify a known descriptor for the same report')
            selected_sources.append(dict(candidate_index=index, inventory_id=row['inventory_id'],
                source=copy.deepcopy(source['source']), input_pointer=source['input_pointer']))
    candidate = copy.deepcopy(protocol)
    candidate.setdefault('report_study_inventory', []).extend(copy.deepcopy(document['candidates']))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    # Reuse full validation for duplicate IDs/recorder tuples and downstream consistency.
    after, after_reports, after_inventory = _validate(candidate)
    if (canonical_json_bytes(before['flow']) != canonical_json_bytes(after['flow']) or
            canonical_json_bytes(before_reports['report_flow']) != canonical_json_bytes(after_reports['report_flow'])):
        raise ValueError('inventory intake must preserve record/report flows and eligibility')
    restored = copy.deepcopy(candidate)
    if 'report_study_inventory' in protocol:
        restored['report_study_inventory'] = restored['report_study_inventory'][:len(protocol['report_study_inventory'])]
    else:
        del restored['report_study_inventory']
    if canonical_json_bytes(restored) != canonical_json_bytes(protocol):
        raise ValueError('inventory intake must preserve every existing input field')
    record_ids = {rid for report_id in selected_report_ids for rid in reports[report_id]['recorded_report']['record_ids']}
    target = dict(schema_version=1, target_type='descriptive_inventory_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document), selected_candidate_targets=selected_targets,
        selected_report_targets=[copy.deepcopy(reports[rid]) for rid in selected_report_ids],
        selected_record_targets=[copy.deepcopy(row) for row in before_inventory['record_targets']
                                 if row['record_id'] in record_ids],
        selected_sources=selected_sources, engine_sha256=implementation_hashes())
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, before_inventory, after, after_reports, after_inventory


def prepare(protocol, candidate_document):
    """Validate completed descriptions and offer a separate blank review document."""
    protocol, document, target, *_ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_INVENTORY_REVIEW', target=target,
        review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Completed descriptions are supplied assertions. Fill every human review field honestly; this is not inclusion, study selection or scientific approval.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed descriptions only, leaving prior rows and all other fields intact."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    (protocol, document, target, candidate, before, before_reports, before_inventory,
     after, after_reports, after_inventory) = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target differs from exact input, candidates and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=copy.deepcopy(before_reports['report_flow']),
        after_report_flow=copy.deepcopy(after_reports['report_flow']),
        before_inventory_summary=dict(stage=before_inventory['inventory_stage'], **copy.deepcopy(before_inventory['counts'])),
        after_inventory_summary=dict(stage=after_inventory['inventory_stage'], **copy.deepcopy(after_inventory['counts'])),
        engine_sha256=implementation_hashes(), **NEGATIVE_CLAIMS, boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_inventory_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Compare the entire replayed record, not just its editable checksum."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_inventory_intake' or type(record['receipt']) is not dict
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached inventory intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied descriptions and review, and recorded implementation; not authentication or scientific validation.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def _encode(value):
    _strict_json(value)
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_APPLICATION_BYTES:
        raise ValueError('serialized output exceeds byte limit')
    return raw


def render_text(result):
    _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    text = 'Supplied descriptive inventory intake\n' + '\n'.join(
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
    scaffold.add_argument('--study-id', required=True)
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
            result = template(protocol, args.report_id, args.study_id)
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
        parser.exit(1, 'inventory intake error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
