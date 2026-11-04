"""Append explicitly authored result-linked review work through detached exact-input replay."""
import argparse
import copy
import datetime
import errno
import hashlib
import json
from pathlib import Path
import re

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from nbib_intake import _strict_json
from prisma_reports import report_flow
from research_bundle import engine_hashes
from screening_links import prepare_targets

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_CANDIDATES = 100
CANDIDATE_FIELDS = {'work_package', 'proposed_by', 'proposed_at', 'proposal_note'}
WORK_FIELDS = {'work_package_id', 'work_type', 'question', 'deliverable',
               'acceptance_criterion', 'evidence_ids', 'depends_on', 'status'}
OPTIONAL_WORK_FIELDS = {'context', 'context_ids'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicit human-authored evidence-review work metadata and exact-input replay only. '
    'Only new PLANNED work with explicitly selected existing result IDs is appended. '
    'No scientific task, question, deliverable, acceptance criterion, dependency, priority, '
    'context applicability, completion or experimental procedure is generated or inferred. '
    'Selected evidence IDs follow the existing engine: an absent raw evidence_id uses the exact '
    'legacy record_id. This is exposed in snapshots, not guessed identity or a rewrite of raw rows. '
    'Source-review work is not converted, results are not invented, and record/report/study IDs '
    'cannot replace an existing explicit result ID. Source refs and own document_source_ids are '
    'not supported on evidence work. Explicit source-work dependencies keep their existing direct '
    'document-context semantics; no recursive source binding or approval is inferred. '
    'Existing raw work, normalized IDs, research, reviews, planning/completion assertions and '
    'hashes are retained without renewal. Selected results, context and planning bases are supplied '
    'metadata, not scientific support, verified reading, clinical applicability or execution. '
    'No source or artifact locator is opened, fetched, read or executed. This editable unsigned '
    'record is not authentication, chronology or a globally unique review ID; consistently '
    'reauthored assertions can replay. Persisted work IDs, result/context links and dependencies '
    'remain in the candidate. Proposal/review assertions and selected snapshots remain detached; '
    'ordinary bundles do not retain this application or original input. Keep them and the recorded '
    'implementation separately. No task is executed and no source acceptance or readiness is established.'
)
NEGATIVE_CLAIMS = dict(source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED',
    source_correctness='NOT_ASSESSED', scientific_acceptance='NOT_ASSESSED',
    clinical_applicability='NOT_ASSESSED', eligibility_correctness='NOT_ASSESSED',
    scientific_task_generation='NOT_PERFORMED', priority_generation='NOT_PERFORMED',
    completion_generation='NOT_PERFORMED', execution='NOT_PERFORMED', existing_review_renewal='NOT_PERFORMED',
    reviewer_identity_verification='NOT_ESTABLISHED', proposer_identity_verification='NOT_ESTABLISHED',
    retained_evidence_snapshot_scope='DETACHED_RECORD_ONLY', proposal_review_scope='DETACHED_RECORD_ONLY',
    census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', external_calls=0)


def digest(value):
    _strict_json(value)
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalized(value, limit, label):
    _strict_json(value)
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


def _ids(value, label, nonempty=False):
    if (not isinstance(value, list) or (nonempty and not value)
            or any(not _text(item) for item in value) or len(value) != len(set(value))):
        raise ValueError(label + ' must be an explicit list of unique nonblank IDs')


def _implementation_hashes():
    root = Path(__file__).resolve().parent
    return dict(engine_hashes(), **{name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                   for name in ('nbib_intake.py', 'evidence_work_intake.py')})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return research, reports


def _report_counts(reports):
    return copy.deepcopy(reports['report_flow']) if reports is not None else None


def _references(research, evidence_ids):
    _ids(evidence_ids, 'evidence_ids', nonempty=True)
    known = {row['evidence_id'] for row in research['evidence']}
    if any(eid not in known for eid in evidence_ids):
        raise ValueError('evidence_ids must select exact existing normalized result IDs')


def template(protocol, reference_document):
    """Draft structure and explicit result selection only, never a research task."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    _schema(refs, {'schema_version', 'evidence_ids'}, 'reference document')
    research, _ = _validate(protocol)
    _references(research, refs['evidence_ids'])
    work = {key: None for key in sorted(WORK_FIELDS)}
    work.update(work_type='evidence_review', evidence_ids=copy.deepcopy(refs['evidence_ids']), status='PLANNED')
    document = dict(schema_version=1, candidates=[dict(work_package=work,
        proposed_by=None, proposed_at=None, proposal_note=None)])
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_EVIDENCE_WORK',
        candidate_document=document, protocol_sha256=digest(protocol), engine_sha256=_implementation_hashes(),
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Incomplete template: explicitly supply every null field, including depends_on. No task meaning, human approval or empty-dependency assertion is inferred. Selected IDs are existing normalized result IDs, not evidence of reading or independent studies.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'candidates'}, 'candidate document')
    rows = document['candidates']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CANDIDATES:
        raise ValueError('candidates must be a nonempty list of at most 100 rows')
    seen = set()
    for row in rows:
        _schema(row, CANDIDATE_FIELDS, 'candidate')
        if any(not _text(row[key]) for key in CANDIDATE_FIELDS - {'work_package'}):
            raise ValueError('proposal fields must be supplied nonblank literal strings')
        _date(row['proposed_at'], 'proposed_at')
        work = row['work_package']
        if (not isinstance(work, dict) or not WORK_FIELDS <= set(work)
                or set(work) - WORK_FIELDS - OPTIONAL_WORK_FIELDS):
            raise ValueError('work_package has unknown or missing fields')
        for field in ('work_package_id', 'question', 'deliverable', 'acceptance_criterion'):
            if not _text(work[field]):
                raise ValueError('work_package requires nonblank ' + field)
        if work['work_type'] != 'evidence_review' or work['status'] != 'PLANNED':
            raise ValueError('new work must be explicit evidence_review with PLANNED status')
        _ids(work['evidence_ids'], 'evidence_ids', nonempty=True)
        _ids(work['depends_on'], 'depends_on')
        if 'context' in work and not _text(work['context']):
            raise ValueError('context must be a nonblank literal string')
        for field in ('context_ids',):
            if field in work:
                _ids(work[field], field, nonempty=True)
        if work['work_package_id'] in seen:
            raise ValueError('duplicate candidate work_package_id')
        seen.add(work['work_package_id'])


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_evidence_work':
        raise ValueError('review decision must be import_evidence_work')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _same(a, b, label):
    if canonical_json_bytes(a) != canonical_json_bytes(b):
        raise ValueError('evidence work intake must preserve ' + label)


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    existing_ids = {row['work_package_id'] for row in before['work_packages']}
    new_ids = [row['work_package']['work_package_id'] for row in document['candidates']]
    if existing_ids.intersection(new_ids):
        raise ValueError('candidate ID collides with an existing normalized work_package_id')
    for row in document['candidates']:
        _references(before, row['work_package']['evidence_ids'])
    candidate = copy.deepcopy(protocol)
    prefix = len(protocol['gaps'])
    candidate['gaps'].extend(copy.deepcopy(row['work_package']) for row in document['candidates'])
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    restored['gaps'] = restored['gaps'][:prefix]
    _same(restored, protocol, 'every existing raw input field')
    _same(before['flow'], after['flow'], 'record flow')
    _same(_report_counts(before_reports), _report_counts(after_reports), 'report flow')
    _same(before['work_packages'], after['work_packages'][:prefix], 'existing normalized work')
    for key in ('search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit'):
        _same(before[key], after[key], key)
    for key in ('review_targets', 'planning_ledger', 'completion_ledger'):
        _same(before['planning'][key],
              [row for row in after['planning'][key] if row['work_package_id'] in existing_ids],
              'existing planning and completion assertions and bases')
    prepared = prepare_targets(protocol, before.get('bibliographic_collection'))
    normalized = {row['evidence_id']: (index, row) for index, row in enumerate(before['evidence'])}
    selected_evidence, work_snapshots, selected_record_ids = [], [], set()
    for index, row in enumerate(document['candidates']):
        work = row['work_package']
        work_snapshots.append(dict(candidate_index=index, input_pointer=f'/gaps/{prefix + index}',
                                   work_package=copy.deepcopy(work)))
        for evidence_id in work['evidence_ids']:
            evidence_index, evidence = normalized[evidence_id]
            raw = protocol['evidence'][evidence_index]
            selected_evidence.append(dict(candidate_index=index, work_package_id=work['work_package_id'],
                evidence_id=evidence_id, input_pointer=f'/evidence/{evidence_index}',
                identity_origin='EXPLICIT_EVIDENCE_ID' if 'evidence_id' in raw else 'LEGACY_RECORD_ID',
                raw_evidence=copy.deepcopy(raw), normalized_evidence=copy.deepcopy(evidence)))
            selected_record_ids.add(evidence['record_id'])
    target = dict(schema_version=1, target_type='manual_evidence_work_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document), candidate_work_packages=work_snapshots,
        selected_evidence=selected_evidence,
        selected_record_targets=[copy.deepcopy(row) for row in prepared['record_targets']
                                 if row['record_id'] in selected_record_ids],
        selected_planning_targets=[copy.deepcopy(row) for row in after['planning']['review_targets']
                                   if row['work_package_id'] in set(new_ids)],
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Validate supplied work and prepare a blank human review."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    result = dict(schema_version=1, status='AWAITING_SUPPLIED_EVIDENCE_WORK_REVIEW', target=target,
        review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Fill every human review field honestly; no decision or identity is inferred.',
        boundary=BOUNDARY)
    return _normalized(result, MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed work to a detached candidate without renewing existing assertions."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, candidates and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_work_count=len(before['work_packages']), after_work_count=len(after['work_packages']),
        before_execution_order=copy.deepcopy(before['execution_order']),
        after_execution_order=copy.deepcopy(after['execution_order']),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=_report_counts(before_reports),
        after_report_flow=_report_counts(after_reports),
        engine_sha256=_implementation_hashes(), boundary=BOUNDARY, **copy.deepcopy(NEGATIVE_CLAIMS))
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_evidence_work_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Recompute the entire record; exact replay is not authentication."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_evidence_work_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached evidence work intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied candidates, human review and recorded implementation; not authentication or scientific validation.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied evidence work intake\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'
    if len(rendered.encode('utf-8')) > MAX_APPLICATION_BYTES:
        raise ValueError('text output exceeds byte limit')
    return rendered


def _encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def _read(path, limit, label):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _write_new(path, raw):
    """Reject existing final entries, including Windows dangling symlinks.

    Exclusive creation remains required after this check. This is not a
    race-proof defense against concurrent path replacement or ancestor aliases.
    """
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
    draft = commands.add_parser('template')
    target = commands.add_parser('target')
    assembly = commands.add_parser('assemble')
    replay = commands.add_parser('verify')
    for command in (draft, target, assembly, replay):
        command.add_argument('protocol', type=Path)
        command.add_argument('--text', action='store_true')
    draft.add_argument('reference_document', type=Path)
    draft.add_argument('--candidate-output', type=Path)
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
            result = template(protocol, _read(args.reference_document, MAX_CANDIDATE_BYTES, 'reference document'))
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
        encoded = _encode(artifact).encode('utf-8') if destination is not None else None
        rendered = render_text(result) if args.text else _encode(result)
        for output in (_encode(result), rendered):
            if len(output.encode('utf-8')) > MAX_APPLICATION_BYTES:
                raise ValueError('stdout exceeds byte limit')
        if encoded is not None:
            limit = (MAX_PROTOCOL_BYTES if args.command == 'verify' else
                     MAX_CANDIDATE_BYTES if args.command == 'template' else MAX_APPLICATION_BYTES)
            if len(encoded) > limit:
                raise ValueError('output exceeds byte limit')
        if destination is not None:
            _write_new(destination, encoded)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'evidence work intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
