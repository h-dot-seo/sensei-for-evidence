"""Review and replay supplied manual result rows without interpreting source material."""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from report_review_links import prepare_targets
from research_bundle import engine_hashes

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_CANDIDATES = 100
CANDIDATE_FIELDS = {'report_id', 'evidence', 'source_references', 'extracted_by',
                    'extracted_at', 'extraction_note'}
EVIDENCE_FIELDS = {'evidence_id', 'record_id', 'study_id', 'locator', 'model',
                   'intervention', 'comparator', 'endpoint', 'result', 'limitations',
                   'mechanism_basis'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicit supplied human result entry and exact-input replay only. No source is opened, '
    'fetched or read; locators and extraction locations are inert supplied text. Source digests, '
    'including non-null digests, are unverified declarations, not document-byte verification. '
    'Source/result correctness, scientific acceptance, eligibility correctness, extraction '
    'completeness and reviewer/extractor identity or authority are not established. No scientific '
    'inference or experiment is performed. This editable unsigned detached record is not '
    'authenticated history or proof of execution. Source associations exist only in this detached '
    'record, not as durable bindings after further protocol edits. Bundles do not retain this '
    'receipt or original protocol. Retain the original input and recorded implementation for '
    'replay. Only supplied evidence rows are appended; reports, eligibility and all other input '
    'fields remain unchanged.'
)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalized(value, limit, label):
    raw = canonical_json_bytes(value)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _date(value, label):
    if not _text(value) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError(label + ' must be YYYY-MM-DD')
    try:
        datetime.date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(label + ' must be a real calendar date') from error


def _schema(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(label + ' has unknown or missing fields')
    if 'schema_version' in fields and (type(value['schema_version']) is not int or value['schema_version'] != 1):
        raise ValueError(label + ' schema_version must be integer 1')


def _implementation_hashes():
    return dict(engine_hashes(), **{
        'result_intake.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    if 'adapter_receipts' in protocol:
        raise ValueError('mock adapter_receipts inputs are not supported for manual result intake')
    if 'reports' not in protocol:
        raise ValueError('manual result intake requires explicit reports')
    research = run(protocol)
    # Required even for legacy scalar study declarations: run alone is insufficient.
    reports = report_flow(protocol, include_csv=False)
    return research, reports


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'candidates'}, 'candidate document')
    rows = document['candidates']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CANDIDATES:
        raise ValueError('candidates must be a nonempty list of at most 100 rows')
    seen = set()
    for row in rows:
        _schema(row, CANDIDATE_FIELDS, 'candidate')
        if any(not _text(row[key]) for key in CANDIDATE_FIELDS - {'evidence', 'source_references'}):
            raise ValueError('candidate text fields must be nonblank literal strings')
        _date(row['extracted_at'], 'extracted_at')
        evidence = row['evidence']
        _schema(evidence, EVIDENCE_FIELDS, 'candidate evidence')
        if any(not _text(evidence[key]) for key in EVIDENCE_FIELDS):
            raise ValueError('all candidate evidence fields require nonblank literal strings and explicit IDs')
        if evidence['mechanism_basis'] not in ('association', 'intervention', 'unknown'):
            raise ValueError('mechanism_basis must be association, intervention or unknown')
        if evidence['evidence_id'] in seen:
            raise ValueError('duplicate candidate evidence_id')
        seen.add(evidence['evidence_id'])
        refs = row['source_references']
        if not isinstance(refs, list) or not refs:
            raise ValueError('source_references must be a nonempty list')
        source_ids = set()
        for ref in refs:
            _schema(ref, {'source_id', 'extraction_locator'}, 'source reference')
            if any(not _text(ref[key]) for key in ref):
                raise ValueError('source references require nonblank literal strings')
            if ref['source_id'] in source_ids:
                raise ValueError('duplicate source_id within candidate source_references')
            source_ids.add(ref['source_id'])


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_results':
        raise ValueError('review decision must be import_results')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    prepared = prepare_targets(protocol, before.get('bibliographic_collection'))
    reports = {row['report_id']: row for row in prepared['report_targets']}
    sources = {row['source']['source_id']: row for row in prepared['source_ledger']}
    existing = {row['evidence_id'] for row in before['evidence']}
    selected_report_ids, selected_sources = [], []
    for index, row in enumerate(document['candidates']):
        report = reports.get(row['report_id'])
        if report is None:
            raise ValueError('unknown candidate report_id')
        recorded = report['recorded_report']
        if recorded.get('decision') != 'include' or report['retrieval'] != 'retrieved':
            raise ValueError('candidate requires an explicitly included retrieved report')
        evidence = row['evidence']
        if evidence['record_id'] not in recorded['record_ids']:
            raise ValueError('candidate record_id is not mapped to its explicit report_id')
        if evidence['study_id'] not in report['supplied_study_ids']:
            raise ValueError('candidate study_id is not declared by its explicit report')
        if evidence['evidence_id'] in existing:
            raise ValueError('candidate evidence_id collides with existing explicit or implicit evidence ID')
        if row['report_id'] not in selected_report_ids:
            selected_report_ids.append(row['report_id'])
        for reference in row['source_references']:
            source = sources.get(reference['source_id'])
            if source is None or source['source']['report_id'] != row['report_id']:
                raise ValueError('source_id must identify a known descriptor for the same report')
            selected_sources.append(dict(candidate_index=index, report_id=row['report_id'],
                evidence_id=evidence['evidence_id'], source=copy.deepcopy(source['source']),
                input_pointer=source['input_pointer'], extraction_locator=reference['extraction_locator']))
    candidate = copy.deepcopy(protocol)
    candidate['evidence'].extend(copy.deepcopy(row['evidence']) for row in document['candidates'])
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    record_ids = {rid for report_id in selected_report_ids
                  for rid in reports[report_id]['recorded_report']['record_ids']}
    target = dict(schema_version=1, target_type='manual_result_intake',
        input_protocol_sha256=digest(protocol),
        candidate_document=copy.deepcopy(document), candidate_document_sha256=digest(document),
        selected_report_targets=[copy.deepcopy(reports[rid]) for rid in selected_report_ids],
        selected_record_targets=[copy.deepcopy(row) for row in prepared['record_targets']
                                 if row['record_id'] in record_ids],
        selected_sources=selected_sources, engine_sha256=_implementation_hashes())
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Validate completed candidate rows and prepare a blank human review."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_RESULT_REVIEW', target=target,
        review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, external_calls=0,
        template_warning='Completed candidate rows are supplied input. Fill every human review field honestly; no review decision or identity is inferred.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed rows to a detached candidate, preserving all other fields."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, candidates and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'],
        candidate_document=document, assertion=review, target=target,
        input_protocol_sha256=digest(protocol), protocol_candidate_sha256=digest(candidate),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=copy.deepcopy(before_reports['report_flow']),
        after_report_flow=copy.deepcopy(after_reports['report_flow']),
        engine_sha256=_implementation_hashes(), source_authenticity='NOT_VERIFIED',
        document_bytes_verification='NOT_PERFORMED', reading='NOT_ESTABLISHED',
        source_result_correctness='NOT_ASSESSED', scientific_acceptance='NOT_ASSESSED',
        eligibility_correctness='NOT_ASSESSED', extraction_completeness='NOT_ESTABLISHED',
        reviewer_identity_verification='NOT_ESTABLISHED', extractor_identity_verification='NOT_ESTABLISHED',
        source_association_scope='DETACHED_RECORD_ONLY', external_calls=0, boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    result = dict(schema_version=1, kind='detached_result_intake', receipt=receipt,
                  protocol_candidate=candidate)
    return _normalized(result, MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Recompute the entire record; this is replay, not authentication."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_result_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached result intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied candidates, human review and current recorded implementation; not authentication or scientific validation.',
        protocol_changed=False, external_calls=0, boundary=BOUNDARY)


def render_text(result):
    return 'Supplied manual result intake\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'


def _encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def _read(path, limit, label):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    target = commands.add_parser('target')
    assembly = commands.add_parser('assemble')
    replay = commands.add_parser('verify')
    for command in (target, assembly, replay):
        command.add_argument('protocol', type=Path)
        command.add_argument('--text', action='store_true')
    for command in (target, assembly):
        command.add_argument('candidate_document', type=Path)
        command.add_argument('--output', required=True, type=Path)
    assembly.add_argument('review_document', type=Path)
    replay.add_argument('application_record', type=Path)
    replay.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        protocol = _read(args.protocol, MAX_PROTOCOL_BYTES, 'original protocol')
        if args.command == 'verify':
            record = _read(args.application_record, MAX_APPLICATION_BYTES, 'application record')
            result = verify(protocol, record)
            destination, artifact = args.protocol_output, record['protocol_candidate']
        else:
            document = _read(args.candidate_document, MAX_CANDIDATE_BYTES, 'candidate document')
            result = (prepare(protocol, document) if args.command == 'target' else
                      assemble(protocol, document, _read(args.review_document, MAX_CANDIDATE_BYTES, 'review document')))
            destination, artifact = args.output, result
        encoded = _encode(artifact) if destination is not None else None
        rendered = render_text(result) if args.text else _encode(result)
        rendered.encode('utf-8')
        if encoded is not None:
            raw = encoded.encode('utf-8')
            limit = MAX_PROTOCOL_BYTES if args.command == 'verify' else MAX_APPLICATION_BYTES
            if len(raw) > limit:
                raise ValueError('output exceeds byte limit')
        if destination is not None:
            with destination.open('x', encoding='utf-8', newline='\n') as output:
                output.write(encoded)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'result intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
