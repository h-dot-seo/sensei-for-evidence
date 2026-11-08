"""Record one explicitly supplied work completion through detached exact-input review."""
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

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
CANDIDATE_FIELDS = {'schema_version', 'work_package_id', 'artifact_locator', 'acceptance_verified',
                    'completed_by', 'completed_at', 'completion_note'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
CHANGED_FIELDS = {'status', 'artifact_locator', 'acceptance_verified', 'completion_basis_sha256'}
BOUNDARY = (
    'One supplied completion assertion for existing unfinished work, with separate exact-input review. '
    'The human explicitly supplies the artifact locator and acceptance_verified true; the tool does not '
    'perform work, open or fetch artifacts, check their bytes, assess acceptance criteria or infer approval. '
    'The current work/source/locator hash is mechanically derived and recorded only with the reviewed '
    'completion. Matching means metadata consistency, not source truth, reading or scientific acceptance. '
    'Existing COMPLETE work cannot be renewed, reopened or replaced here. Existing stale or unbound '
    'prerequisite completions remain unchanged and visible; the original engine still treats their '
    'COMPLETE statuses as satisfied dependencies. Direct prerequisite cues are not recursive acceptance '
    'certificates. Only the selected raw work status, locator, acceptance and completion hash change. '
    'Other raw inputs, work meanings, links, research, planning and reviews are retained without renewal. '
    'Derived blocked_by lists may change without changing dependent raw work. No task priority, clinical '
    'applicability, development-stage decision, source acceptance or readiness is established. '
    'The unsigned editable record does not authenticate completer/reviewer identity, chronology or '
    'globally unique receipts; consistently reauthored assertions can replay. Completion fields persist '
    'in the candidate, but completer/reviewer metadata and before/after snapshots remain detached. '
    'Ordinary bundles do not retain the original input or this application. Keep them and the recorded '
    'implementation separately. No external calls or artifact access are performed.'
)
NEGATIVE_CLAIMS = dict(source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED',
    acceptance_assessment='NOT_PERFORMED', artifact_content_verification='NOT_PERFORMED',
    scientific_acceptance='NOT_ASSESSED', clinical_applicability='NOT_ASSESSED',
    priority_generation='NOT_PERFORMED', execution='NOT_PERFORMED', existing_review_renewal='NOT_PERFORMED',
    reviewer_identity_verification='NOT_ESTABLISHED', completer_identity_verification='NOT_ESTABLISHED',
    completion_metadata_scope='DETACHED_RECORD_ONLY', review_scope='DETACHED_RECORD_ONLY',
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


def _implementation_hashes():
    root = Path(__file__).resolve().parent
    return dict(engine_hashes(), **{name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                   for name in ('nbib_intake.py', 'work_completion_intake.py')})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return research, reports


def _report_counts(reports):
    return copy.deepcopy(reports['report_flow']) if reports is not None else None


def _selected(research, work_package_id):
    if not _text(work_package_id):
        raise ValueError('work_package_id must be a nonblank exact normalized ID')
    for index, row in enumerate(research['work_packages']):
        if row['work_package_id'] == work_package_id:
            if row['status'] == 'COMPLETE':
                raise ValueError('existing COMPLETE work cannot be renewed, reopened or replaced')
            return index, row
    raise ValueError('unknown normalized work_package_id')


def template(protocol, work_package_id):
    """Select only an existing unfinished work ID; never infer acceptance or a locator."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    research, _ = _validate(protocol)
    index, work = _selected(research, work_package_id)
    document = {key: None for key in sorted(CANDIDATE_FIELDS)}
    document.update(schema_version=1, work_package_id=work_package_id)
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_COMPLETION',
        candidate_document=document, input_pointer=f'/gaps/{index}',
        selected_work=copy.deepcopy(work), protocol_sha256=digest(protocol),
        engine_sha256=_implementation_hashes(), protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Incomplete template: supply the locator, exact true acceptance and all completion metadata only after doing and reviewing the work. No completion or reviewer approval is inferred.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, CANDIDATE_FIELDS, 'candidate document')
    if any(not _text(document[key]) for key in CANDIDATE_FIELDS - {'schema_version', 'acceptance_verified'}):
        raise ValueError('completion fields must be supplied nonblank literal strings')
    if document['acceptance_verified'] is not True:
        raise ValueError('acceptance_verified must be explicitly supplied true')
    _date(document['completed_at'], 'completed_at')


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'record_supplied_completion':
        raise ValueError('review decision must be record_supplied_completion')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _same(a, b, label):
    if canonical_json_bytes(a) != canonical_json_bytes(b):
        raise ValueError('work completion intake must preserve ' + label)


def _by_id(rows):
    return {row['work_package_id']: row for row in rows}


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    wid = document['work_package_id']
    index, old_work = _selected(before, wid)
    candidate = copy.deepcopy(protocol)
    selected = candidate['gaps'][index]
    selected.update(status='COMPLETE', artifact_locator=document['artifact_locator'], acceptance_verified=True)
    # Existing completion and dependency guards apply before any binding is generated.
    interim, _ = _validate(candidate)
    completion_target = _by_id(interim['planning']['completion_ledger'])[wid]
    selected['completion_basis_sha256'] = completion_target['current_basis_sha256']
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    restored['gaps'][index] = copy.deepcopy(protocol['gaps'][index])
    _same(restored, protocol, 'every unselected raw input field')
    _same({k: v for k, v in protocol['gaps'][index].items() if k not in CHANGED_FIELDS},
          {k: v for k, v in candidate['gaps'][index].items() if k not in CHANGED_FIELDS},
          'selected work meaning, links, dependencies and raw identity')
    _same(before['flow'], after['flow'], 'record flow')
    _same(_report_counts(before_reports), _report_counts(after_reports), 'report flow')
    for key in ('search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit', 'execution_order'):
        _same(before[key], after[key], key)
    for key in ('review_targets', 'planning_ledger'):
        _same(before['planning'][key], after['planning'][key], 'all planning assertions and bases')
    prior_completions = _by_id(before['planning']['completion_ledger'])
    new_completions = _by_id(after['planning']['completion_ledger'])
    for other_id in prior_completions:
        if other_id != wid:
            _same(prior_completions[other_id], new_completions[other_id], 'unselected completion assertions and bases')
    old_work_by_id, new_work_by_id = _by_id(before['work_packages']), _by_id(after['work_packages'])
    blocking_changes = [dict(work_package_id=other_id,
        before_blocked_by=copy.deepcopy(old_work_by_id[other_id]['blocked_by']),
        after_blocked_by=copy.deepcopy(new_work_by_id[other_id]['blocked_by']))
        for other_id in old_work_by_id
        if old_work_by_id[other_id]['blocked_by'] != new_work_by_id[other_id]['blocked_by']]
    prerequisites = [dict(work_package_id=dep, supplied_status=old_work_by_id[dep]['status'],
        completion_review=copy.deepcopy(prior_completions[dep])) for dep in old_work['depends_on']]
    target = dict(schema_version=1, target_type='manual_work_completion_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document), work_package_id=wid,
        input_pointer=f'/gaps/{index}', output_pointer=f'/gaps/{index}',
        identity_origin='EXPLICIT_WORK_PACKAGE_ID' if 'work_package_id' in protocol['gaps'][index] else 'LEGACY_POSITIONAL_ID',
        before_raw_work=copy.deepcopy(protocol['gaps'][index]),
        proposed_raw_work=copy.deepcopy(candidate['gaps'][index]),
        before_normalized_work=copy.deepcopy(old_work),
        proposed_normalized_work=copy.deepcopy(new_work_by_id[wid]),
        planning_review_target=copy.deepcopy(_by_id(before['planning']['review_targets'])[wid]),
        before_completion_review=copy.deepcopy(prior_completions[wid]),
        proposed_completion_review=copy.deepcopy(new_completions[wid]),
        direct_prerequisite_completion_reviews=prerequisites,
        derived_blocking_changes=blocking_changes,
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Preview a supplied completion, never record it without the separate review."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_COMPLETION_REVIEW', target=target,
        review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Review the proposed completion, criteria, locator, source scope and prerequisite cues. Fill all human review fields honestly; target generation does not record or approve completion.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Record only the explicitly supplied and separately reviewed completion."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, candidate and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_work_count=len(before['work_packages']), after_work_count=len(after['work_packages']),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=_report_counts(before_reports), after_report_flow=_report_counts(after_reports),
        derived_blocking_changes=copy.deepcopy(target['derived_blocking_changes']),
        engine_sha256=_implementation_hashes(), boundary=BOUNDARY, **copy.deepcopy(NEGATIVE_CLAIMS))
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_work_completion_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Recompute the full transition; replay is not proof of actual completion."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_work_completion_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached work completion intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied completion, separate human review and recorded implementation; not authentication, artifact checking or acceptance assessment.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied work completion intake\n' + '\n'.join(
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
    draft.add_argument('--work-package', required=True)
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
            result = template(protocol, args.work_package)
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
        parser.exit(1, 'work completion intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
