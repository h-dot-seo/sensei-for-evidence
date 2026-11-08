"""Register explicitly supplied reports and document declarations before eligibility.

This bridges included screening records to pending full-text assessment without
inferring report identity, retrieval, study membership or extracted evidence.
"""
import argparse
import copy
import hashlib
from pathlib import Path
import re

from json_io import canonical_json_bytes, configure_utf8_stdio, quoted_display
from report_review_links import SOURCE_FIELDS, prepare_targets as report_targets
from screening_links import prepare_targets as record_targets
import source_work_intake as helpers

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_CANDIDATES = 100
MAX_SOURCE_DECLARATIONS = 1_000
CANDIDATE_FIELDS = {'report', 'source_declarations', 'registered_by', 'registered_at', 'registration_note'}
REPORT_FIELDS = {'report_id', 'record_ids', 'retrieval', 'decision', 'locator', 'reason'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision', 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicit supplied report registration and exact-input replay only. Report identity, record grouping, '
    'retrieval state, locators and document versions are human assertions, not verified acquisition or reading. '
    'Every new report has pending full-text assessment; no study IDs, eligibility choices, results, '
    'nonclinical parameters or scientific conclusions are generated. No report or document is opened, '
    'downloaded, hashed from a file or authenticated. Supplied non-null document digests remain unverified. '
    'Only new report rows and explicitly supplied source declarations are appended. Existing raw fields, '
    'screening, evidence, review assertions, work and hashes are retained without renewal. '
    'Sources in this intake must belong to its new reports; existing report retrieval states or sources '
    'are not edited. Existing checks may expose changed source context, not automatic reassessment. '
    'PRISMA-oriented counts describe supplied records and reports, not publication identity, search '
    'completeness, full PRISMA compliance or evidence sufficiency. An unavailable report is not a '
    'full-text exclusion. This editable unsigned detached record is not authenticated history, '
    'chronology, reviewer identity or proof of execution. Retain the original input and recorded '
    'implementation for replay. Ordinary bundles retain the candidate protocol, not this detached '
    'registration/review receipt or original input. All text is retained without redaction.'
)
NEGATIVE_CLAIMS = dict(source_authenticity='NOT_VERIFIED', document_bytes_verification='NOT_PERFORMED',
    retrieval_verification='NOT_PERFORMED', reading='NOT_ESTABLISHED',
    report_identity_verification='NOT_ESTABLISHED', study_identity_verification='NOT_ESTABLISHED',
    eligibility_correctness='NOT_ASSESSED', scientific_acceptance='NOT_ASSESSED',
    extraction_completeness='NOT_ESTABLISHED', reviewer_identity_verification='NOT_ESTABLISHED',
    registrar_identity_verification='NOT_ESTABLISHED', existing_review_renewal='NOT_PERFORMED',
    registration_review_scope='DETACHED_RECORD_ONLY', external_calls=0,
    census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')


def digest(value):
    return helpers.digest(value)


def _normalized(value, limit, label):
    return helpers._normalized(value, limit, label)


def _implementation_hashes():
    return dict(helpers._implementation_hashes(), **{
        'report_intake.py': hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()})


def _validate(protocol):
    if isinstance(protocol, dict) and 'adapter_receipts' in protocol:
        raise ValueError('mock adapter context locks report declarations; manual report intake cannot change it or erase its receipts')
    research, reports = helpers._validate(protocol)
    if 'reports' not in protocol and protocol['evidence']:
        raise ValueError('cannot introduce pending-only reports over existing legacy evidence; reconcile its report memberships separately')
    return research, reports


def _selected_records(protocol, ids, already_selected=None):
    helpers._ids(ids, 'record_ids', nonempty=True)
    included = {row['record_id'] for row in protocol['screening'] if row['decision'] == 'include'}
    mapped = {rid for row in protocol.get('reports', []) for rid in row['record_ids']}
    if any(rid not in included for rid in ids):
        raise ValueError('every selected record must have an explicit included screening decision')
    if mapped.intersection(ids) or (already_selected is not None and already_selected.intersection(ids)):
        raise ValueError('selected records must be unmapped and cannot occur in multiple candidate reports')


def template(protocol, reference_document):
    """Scaffold one caller-selected record group without choosing report identity."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    helpers._schema(refs, {'schema_version', 'record_ids'}, 'reference document')
    _validate(protocol)
    _selected_records(protocol, refs['record_ids'])
    report = {key: None for key in sorted(REPORT_FIELDS)}
    report.update(record_ids=copy.deepcopy(refs['record_ids']), decision='pending')
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_REPORT_REGISTRATION',
        candidate_document=dict(schema_version=1, candidates=[dict(report=report,
            source_declarations=None, registered_by=None, registered_at=None, registration_note=None)]),
        protocol_sha256=digest(protocol), protocol_changed=False, external_calls=0,
        template_warning='Incomplete draft: supply report identity, retrieval, applicable locator/reason, explicit source_declarations list and human metadata. The chosen record group is a caller assertion; pending is a fixed no-eligibility restriction, not a review outcome.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    helpers._schema(document, {'schema_version', 'candidates'}, 'candidate document')
    rows = document['candidates']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CANDIDATES:
        raise ValueError('candidates must be a nonempty list of at most 100 rows')
    report_ids, source_ids = set(), set()
    count = 0
    for row in rows:
        helpers._schema(row, CANDIDATE_FIELDS, 'candidate')
        for key in ('registered_by', 'registered_at', 'registration_note'):
            if not helpers._text(row[key]):
                raise ValueError('registration fields must be supplied nonblank literal strings')
        helpers._date(row['registered_at'], 'registered_at')
        report = row['report']
        helpers._schema(report, REPORT_FIELDS, 'candidate report')
        if not helpers._text(report['report_id']) or report['report_id'] in report_ids:
            raise ValueError('new report_id values must be nonblank and unique')
        report_ids.add(report['report_id'])
        helpers._ids(report['record_ids'], 'record_ids', nonempty=True)
        if report['decision'] != 'pending':
            raise ValueError('new reports must have explicit pending full-text assessment')
        if report['retrieval'] not in ('pending', 'not_retrieved', 'retrieved'):
            raise ValueError('retrieval must be an explicit supported state')
        for key in ('locator', 'reason'):
            if report[key] is not None and not helpers._text(report[key]):
                raise ValueError('report locator/reason must be nonblank text or explicit null')
        if report['retrieval'] == 'retrieved' and not helpers._text(report['locator']):
            raise ValueError('retrieved report requires a supplied locator')
        if report['retrieval'] == 'not_retrieved' and not helpers._text(report['reason']):
            raise ValueError('not_retrieved report requires a supplied reason')
        sources = row['source_declarations']
        if not isinstance(sources, list):
            raise ValueError('source_declarations must be an explicit list, possibly empty')
        count += len(sources)
        if count > MAX_SOURCE_DECLARATIONS:
            raise ValueError('candidate source declarations exceed aggregate limit')
        for source in sources:
            helpers._schema(source, SOURCE_FIELDS, 'source declaration')
            if any(not helpers._text(source[key]) for key in SOURCE_FIELDS - {'document_sha256'}):
                raise ValueError('source declaration text fields must be nonblank')
            if source['report_id'] != report['report_id']:
                raise ValueError('source declaration must refer to its candidate report')
            if source['source_id'] in source_ids:
                raise ValueError('candidate source_id values must be globally unique')
            source_ids.add(source['source_id'])
            sha = source['document_sha256']
            if sha is not None and (not isinstance(sha, str) or re.fullmatch(r'[0-9a-f]{64}', sha) is None):
                raise ValueError('document_sha256 must be explicit null or 64 lowercase hex characters')


def validate_review_document(document):
    helpers._schema(document, REVIEW_FIELDS, 'review document')
    if any(not helpers._text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_reports':
        raise ValueError('review decision must be import_reports')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    helpers._date(document['reviewed_at'], 'reviewed_at')


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    existing_reports = {row['report_id'] for row in protocol.get('reports', [])}
    existing_sources = {row['source_id'] for row in protocol.get('report_sources', [])}
    chosen_records = set()
    for row in document['candidates']:
        if row['report']['report_id'] in existing_reports:
            raise ValueError('candidate report_id already exists; registration never edits an existing report')
        _selected_records(protocol, row['report']['record_ids'], chosen_records)
        chosen_records.update(row['report']['record_ids'])
        if any(source['source_id'] in existing_sources for source in row['source_declarations']):
            raise ValueError('candidate source_id collides with an existing document declaration')
    candidate = copy.deepcopy(protocol)
    report_prefix = len(protocol.get('reports', []))
    source_prefix = len(protocol.get('report_sources', []))
    candidate.setdefault('reports', []).extend(copy.deepcopy(row['report']) for row in document['candidates'])
    new_sources = [copy.deepcopy(source) for row in document['candidates'] for source in row['source_declarations']]
    if new_sources:
        candidate.setdefault('report_sources', []).extend(new_sources)
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    for key, prefix in [('reports', report_prefix), ('report_sources', source_prefix)]:
        if key in protocol:
            restored[key] = restored[key][:prefix]
        else:
            restored.pop(key, None)
    if canonical_json_bytes(restored) != canonical_json_bytes(protocol):
        raise ValueError('report intake must preserve every existing raw input field')
    for key in ('flow', 'search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit', 'experiments'):
        if canonical_json_bytes(before[key]) != canonical_json_bytes(after[key]):
            raise ValueError('report intake must preserve existing ' + key)
    old_targets = record_targets(protocol, before.get('bibliographic_collection'))
    selected_targets = [copy.deepcopy(row) for row in old_targets['record_targets'] if row['record_id'] in chosen_records]
    new_ids = {row['report']['report_id'] for row in document['candidates']}
    new_targets = report_targets(candidate, after.get('bibliographic_collection'))
    target = dict(schema_version=1, target_type='manual_report_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document), selected_record_targets=selected_targets,
        proposed_report_targets=[copy.deepcopy(row) for row in new_targets['report_targets'] if row['report_id'] in new_ids],
        proposed_source_declarations=[copy.deepcopy(row) for row in new_targets['source_ledger']
                                      if row['source']['report_id'] in new_ids],
        before_report_stage='SUPPLIED' if 'reports' in protocol else 'NOT_SUPPLIED',
        before_source_stage='SUPPLIED' if 'report_sources' in protocol else 'NOT_SUPPLIED',
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_REPORT_REGISTRATION_REVIEW', target=target,
        review_document=review, protocol_sha256=digest(protocol), candidate_document_sha256=digest(document),
        engine_sha256=target['engine_sha256'], protocol_changed=False, external_calls=0,
        template_warning='Supply all human review fields honestly; no identity, decision or authority is inferred.', boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target differs from exact original, candidates and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=helpers._report_counts(before_reports), after_report_flow=helpers._report_counts(after_reports),
        added_reports=len(document['candidates']),
        added_source_declarations=sum(len(row['source_declarations']) for row in document['candidates']),
        engine_sha256=_implementation_hashes(), **copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_report_intake', receipt=receipt,
        protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    helpers._schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_report_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached report intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'], protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied reports/sources, human review and recorded implementation; not acquisition, reading or scientific validation.',
        protocol_changed=False, external_calls=0, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied manual report registration\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'
    if len(rendered.encode('utf-8')) > MAX_APPLICATION_BYTES:
        raise ValueError('text output exceeds byte limit')
    return rendered


def _write_new(path, raw):
    helpers._write_new(path, raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    draft = commands.add_parser('template')
    target = commands.add_parser('target')
    assembly = commands.add_parser('assemble')
    replay = commands.add_parser('verify')
    for command in (draft, target, assembly, replay):
        command.add_argument('protocol', type=Path)
        command.add_argument('--text', action='store_true')
    draft.add_argument('reference_document', type=Path)
    draft.add_argument('--output', type=Path)
    for command in (target, assembly):
        command.add_argument('candidate_document', type=Path)
        command.add_argument('--output', type=Path, required=True)
    assembly.add_argument('review_document', type=Path)
    replay.add_argument('application_record', type=Path)
    replay.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        protocol = helpers._read(args.protocol, MAX_PROTOCOL_BYTES, 'original protocol')
        if args.command == 'template':
            result = template(protocol, helpers._read(args.reference_document, MAX_CANDIDATE_BYTES, 'reference document'))
            destination, artifact = args.output, result['candidate_document']
        elif args.command == 'verify':
            record = helpers._read(args.application_record, MAX_APPLICATION_BYTES, 'application record')
            result = verify(protocol, record)
            destination, artifact = args.protocol_output, record['protocol_candidate']
        else:
            document = helpers._read(args.candidate_document, MAX_CANDIDATE_BYTES, 'candidate document')
            result = (prepare(protocol, document) if args.command == 'target' else
                assemble(protocol, document, helpers._read(args.review_document, MAX_CANDIDATE_BYTES, 'review document')))
            destination, artifact = args.output, result
        rendered = render_text(result) if args.text else helpers._encode(result)
        stdout = rendered.encode('utf-8')
        if len(stdout) > MAX_APPLICATION_BYTES:
            raise ValueError('rendered output exceeds byte limit')
        raw = None if destination is None else helpers._encode(artifact).encode('utf-8')
        limit = MAX_PROTOCOL_BYTES if args.command == 'verify' else MAX_APPLICATION_BYTES
        if raw is not None and len(raw) > limit:
            raise ValueError('output exceeds byte limit')
        if destination is not None:
            _write_new(destination, raw)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'report intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
