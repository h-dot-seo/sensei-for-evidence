"""Replay explicitly supplied retrieval updates for existing unassessed reports.

No document is fetched and no full-text eligibility choice is generated. This
bounded transition never replaces report identity, record grouping or sources.
"""
import argparse
import copy
import hashlib
from pathlib import Path
import re

from json_io import canonical_json_bytes, configure_utf8_stdio, quoted_display
from report_review_links import SOURCE_FIELDS, prepare_targets as report_targets
import source_work_intake as helpers

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_CANDIDATES = 100
MAX_SOURCE_DECLARATIONS = 1_000
CANDIDATE_FIELDS = {'report_id', 'retrieval', 'locator', 'reason', 'source_declarations',
                    'updated_by', 'updated_at', 'update_note'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision', 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
TRANSITIONS = {('pending', 'not_retrieved'), ('pending', 'retrieved'), ('not_retrieved', 'retrieved')}
BOUNDARY = (
    'Explicit supplied retrieval-state updates and exact-input replay only, not verified acquisition '
    'or reading. Only pending to not_retrieved/retrieved and not_retrieved to retrieved are supported '
    'for existing unassessed reports. Report IDs, record mappings, full-text decisions, study declarations, '
    'evidence, searches, work and existing source/review rows are retained. No source is replaced, '
    'preferred document version chosen, review renewed, eligibility decided or nonclinical parameter '
    'generated. New source declarations are append-only, belong to updated reports and have unverified '
    'supplied digests. All locators remain inert; no file is opened, downloaded or hashed as a document. '
    'The changed source context can make retained reviews stale. Retrieval failure is not exclusion. '
    'Prior retrieval/locator/reason values remain in the detached receipt and original protocol, not '
    'as a durable protocol event ledger. This unsigned editable receipt is not authentication, chronology '
    'or proof of execution. Retain the original input, detached receipt and recorded implementation for '
    'replay. Ordinary bundles retain only the candidate protocol. Recorded PRISMA-oriented counts do not '
    'establish complete searching, publication identity, complete extraction, PRISMA compliance or '
    'scientific validity. Supplied text is retained without redaction.'
)
NEGATIVE_CLAIMS = dict(retrieval_verification='NOT_PERFORMED', document_bytes_verification='NOT_PERFORMED',
    source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED', eligibility_correctness='NOT_ASSESSED',
    reviewer_identity_verification='NOT_ESTABLISHED', updater_identity_verification='NOT_ESTABLISHED',
    existing_review_renewal='NOT_PERFORMED', review_assertions_changed=False,
    historical_retrieval_scope='DETACHED_RECEIPT_AND_ORIGINAL_ONLY', external_calls=0,
    census_claim='NOT_ESTABLISHED', extraction_completeness='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')


def digest(value):
    return helpers.digest(value)


def _normalized(value, limit, label):
    return helpers._normalized(value, limit, label)


def _implementation_hashes():
    return dict(helpers._implementation_hashes(), **{
        'report_retrieval.py': hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()})


def _validate(protocol):
    if isinstance(protocol, dict) and 'adapter_receipts' in protocol:
        raise ValueError('mock adapter context locks report declarations; retrieval updates cannot change it or erase its receipts')
    research, reports = helpers._validate(protocol)
    if reports is None:
        raise ValueError('retrieval updates require an existing report ledger')
    return research, reports


def _selected(protocol, ids):
    helpers._ids(ids, 'report_ids', nonempty=True)
    rows = {row['report_id']: row for row in protocol['reports']}
    selected = []
    for rid in ids:
        if rid not in rows:
            raise ValueError('unknown report_id for retrieval update')
        row = rows[rid]
        if row['retrieval'] not in ('pending', 'not_retrieved') or row.get('decision', 'pending') != 'pending':
            raise ValueError('retrieval updates require an unassessed pending or not_retrieved report')
        selected.append(row)
    return selected


def template(protocol, reference_document):
    """Scaffold caller-selected reports, leaving all retrieval assertions blank."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    helpers._schema(refs, {'schema_version', 'report_ids'}, 'reference document')
    _validate(protocol)
    selected = _selected(protocol, refs['report_ids'])
    if len(selected) > MAX_CANDIDATES:
        raise ValueError('too many selected reports')
    candidates = []
    for row in selected:
        candidate = {key: None for key in sorted(CANDIDATE_FIELDS)}
        candidate['report_id'] = row['report_id']
        candidates.append(candidate)
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_RETRIEVAL_UPDATE',
        candidate_document=dict(schema_version=1, candidates=candidates),
        protocol_sha256=digest(protocol), protocol_changed=False, external_calls=0,
        template_warning='Incomplete draft: supply the new retrieval state, applicable locator/reason, explicit source_declarations list and human metadata. No prior outcome is copied as a new assertion.',
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
        if not helpers._text(row['report_id']) or row['report_id'] in report_ids:
            raise ValueError('candidate report_id values must be nonblank and unique')
        report_ids.add(row['report_id'])
        for key in ('updated_by', 'updated_at', 'update_note'):
            if not helpers._text(row[key]):
                raise ValueError('update fields must be supplied nonblank literal strings')
        helpers._date(row['updated_at'], 'updated_at')
        if row['retrieval'] not in ('not_retrieved', 'retrieved'):
            raise ValueError('new retrieval must be not_retrieved or retrieved')
        for key in ('locator', 'reason'):
            if row[key] is not None and not helpers._text(row[key]):
                raise ValueError('locator/reason must be nonblank text or explicit null')
        if row['retrieval'] == 'retrieved' and not helpers._text(row['locator']):
            raise ValueError('retrieved requires a supplied locator')
        if row['retrieval'] == 'not_retrieved' and not helpers._text(row['reason']):
            raise ValueError('not_retrieved requires a supplied reason')
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
            if source['report_id'] != row['report_id']:
                raise ValueError('source declaration must belong to its updated report')
            if source['source_id'] in source_ids:
                raise ValueError('candidate source_id values must be globally unique')
            source_ids.add(source['source_id'])
            sha = source['document_sha256']
            if sha is not None and (not isinstance(sha, str) or re.fullmatch(r'[0-9a-f]{64}', sha) is None):
                raise ValueError('document_sha256 must be null or 64 lowercase hexadecimal characters')


def validate_review_document(document):
    helpers._schema(document, REVIEW_FIELDS, 'review document')
    if any(not helpers._text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review fields must be supplied nonblank literal strings')
    if document['decision'] != 'update_retrieval':
        raise ValueError('review decision must be update_retrieval')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    helpers._date(document['reviewed_at'], 'reviewed_at')


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    selected = _selected(protocol, [row['report_id'] for row in document['candidates']])
    existing_sources = {row['source_id'] for row in protocol.get('report_sources', [])}
    for prior, row in zip(selected, document['candidates']):
        if (prior['retrieval'], row['retrieval']) not in TRANSITIONS:
            raise ValueError('unsupported retrieval transition; no same-state, reversal or existing-document update')
        if any(source['source_id'] in existing_sources for source in row['source_declarations']):
            raise ValueError('source_id collides with an existing declaration; sources cannot be replaced')
    candidate = copy.deepcopy(protocol)
    updates = {row['report_id']: row for row in document['candidates']}
    for report in candidate['reports']:
        if report['report_id'] in updates:
            report.update({key: copy.deepcopy(updates[report['report_id']][key])
                           for key in ('retrieval', 'locator', 'reason')})
    new_sources = [copy.deepcopy(source) for row in document['candidates'] for source in row['source_declarations']]
    if new_sources:
        candidate.setdefault('report_sources', []).extend(new_sources)
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    for i, report in enumerate(protocol['reports']):
        if report['report_id'] in updates:
            for key in ('retrieval', 'locator', 'reason'):
                if key in report:
                    restored['reports'][i][key] = copy.deepcopy(report[key])
                else:
                    restored['reports'][i].pop(key, None)
    if 'report_sources' in protocol:
        restored['report_sources'] = restored['report_sources'][:len(protocol['report_sources'])]
    else:
        restored.pop('report_sources', None)
    if canonical_json_bytes(restored) != canonical_json_bytes(protocol):
        raise ValueError('retrieval updates must preserve every uncontrolled raw input field')
    for key in ('flow', 'search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit', 'experiments'):
        if canonical_json_bytes(before[key]) != canonical_json_bytes(after[key]):
            raise ValueError('retrieval updates must preserve existing ' + key)
    for key in ('sought', 'assessed', 'included', 'excluded', 'included_studies', 'reports_with_extraction'):
        if before_reports['report_flow'][key] != after_reports['report_flow'][key]:
            raise ValueError('retrieval updates must preserve report ' + key)
    old = report_targets(protocol, before.get('bibliographic_collection'))
    new = report_targets(candidate, after.get('bibliographic_collection'))
    target = dict(schema_version=1, target_type='manual_report_retrieval_update',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document),
        prior_report_targets=[copy.deepcopy(row) for row in old['report_targets'] if row['report_id'] in updates],
        proposed_report_targets=[copy.deepcopy(row) for row in new['report_targets'] if row['report_id'] in updates],
        retained_review_assertions=[copy.deepcopy(row) for row in protocol.get('report_reviews', [])
                                    if row['report_id'] in updates],
        before_source_stage='SUPPLIED' if 'report_sources' in protocol else 'NOT_SUPPLIED',
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_RETRIEVAL_UPDATE_REVIEW',
        target=target, review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, external_calls=0,
        template_warning='Supply review fields honestly after inspecting original and proposed retrieval/source context. No review or human identity is inferred.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target differs from exact input, candidates and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=helpers._report_counts(before_reports), after_report_flow=helpers._report_counts(after_reports),
        updated_reports=len(document['candidates']), added_source_declarations=sum(len(row['source_declarations']) for row in document['candidates']),
        engine_sha256=_implementation_hashes(), **copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_report_retrieval_update', receipt=receipt,
        protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    helpers._schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_report_retrieval_update' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached retrieval update application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH', receipt_id=receipt['receipt_id'],
        receipt_sha256=receipt['receipt_sha256'], input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'], engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied retrieval/source updates, human review and recorded implementation; not acquisition or reading.',
        protocol_changed=False, external_calls=0, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied report retrieval update\n' + '\n'.join(
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
        if len(rendered.encode('utf-8')) > MAX_APPLICATION_BYTES:
            raise ValueError('rendered output exceeds byte limit')
        raw = None if destination is None else helpers._encode(artifact).encode('utf-8')
        limit = MAX_PROTOCOL_BYTES if args.command == 'verify' else MAX_APPLICATION_BYTES
        if raw is not None and len(raw) > limit:
            raise ValueError('output exceeds byte limit')
        if destination is not None:
            _write_new(destination, raw)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'report retrieval error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
