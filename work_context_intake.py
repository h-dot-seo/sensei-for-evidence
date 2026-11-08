"""Append explicit existing context links to named work through exact-input review."""
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
MAX_ASSIGNMENTS = 100
MAX_CONTEXT_IDS = 100
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Append only explicitly selected existing context IDs to explicitly named existing work packages '
    'after separate exact-input review. No context, source link, work meaning, clinical applicability '
    'or scientific judgement is generated. Existing raw work fields stay unchanged except the appended '
    'context_ids suffix; absent versus empty prior fields are preserved in before/after snapshots. '
    'Context rows and their supplied review statuses remain unchanged. Matching evidence/source links '
    'are structural consistency, not applicable guidance or an endorsed development decision. '
    'Existing planning ranks, completion status, artifact locators, acceptance assertions and review '
    'hashes are preserved. Derived source bases can change for selected work and direct dependents; '
    'stale cues are shown without renewing review, changing priority, reopening work or withdrawing '
    'completion. COMPLETE still satisfies the existing dependency rule even with stale source bindings. '
    'No context is automatically assigned to dependent work and no clinical or regulatory decision '
    'is made. Exact replay is not authentication, chronology, actual review or source reading. '
    'Import metadata and source-basis snapshots remain detached, not a durable approval ledger. '
    'Keep the original input, application and recorded implementation; ordinary bundles retain only '
    'the resulting protocol. No source path, artifact or locator is read and no external/model call '
    'is made. Supplied private text is retained without redaction; keep real inputs outside this repo.'
)
NEGATIVE_CLAIMS = dict(external_calls=0, source_reading='NOT_PERFORMED',
    scientific_assessment='NOT_PERFORMED', clinical_applicability='NOT_ASSESSED',
    reviewer_identity='NOT_VERIFIED', review_renewal='NOT_PERFORMED',
    completion_renewal='NOT_PERFORMED', priority_generation='NOT_PERFORMED',
    source_authenticity='NOT_VERIFIED', work_execution='NOT_PERFORMED',
    source_snapshot_scope='RECORDED_STEP_CONTEXT_ONLY')


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
                                   for name in ('nbib_intake.py', 'work_context_intake.py')})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return research, reports


def _report_counts(reports):
    return copy.deepcopy(reports['report_flow']) if reports is not None else None


def _selected(protocol, research, work_id):
    if not _text(work_id):
        raise ValueError('work_package_id must be a nonblank explicit existing ID')
    for index, raw in enumerate(protocol['gaps']):
        if raw.get('work_package_id') == work_id:
            return index, research['work_packages'][index]
    raise ValueError('work_package_id must match an explicit raw existing work ID; positional fallback IDs are unsupported')


def template(protocol, reference_document):
    """Select explicit work IDs, leaving context selection blank for the operator."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    _schema(refs, {'schema_version', 'work_package_ids'}, 'reference document')
    _ids(refs['work_package_ids'], 'work_package_ids', nonempty=True)
    if len(refs['work_package_ids']) > MAX_ASSIGNMENTS:
        raise ValueError('too many explicit work IDs')
    research, _ = _validate(protocol)
    selected = []
    for wid in refs['work_package_ids']:
        index, work = _selected(protocol, research, wid)
        selected.append(dict(input_pointer=f'/gaps/{index}', raw_work=copy.deepcopy(protocol['gaps'][index]),
                             normalized_work=copy.deepcopy(work)))
    document = dict(schema_version=1, assignments=[dict(work_package_id=wid, context_ids=None)
                                                  for wid in refs['work_package_ids']])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_WORK_CONTEXT_LINKS',
        candidate_document=document, selected_work=selected,
        available_contexts=copy.deepcopy(research['context']['context_ledger']),
        context_catalog_scope='ALL_SUPPLIED_CONTEXTS_NOT_SELECTED_OR_RECOMMENDED',
        protocol_sha256=digest(protocol), engine_sha256=_implementation_hashes(),
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Only explicit work IDs are copied. Choose exact context IDs separately; the catalog is not a compatibility filter or an applicability recommendation.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'assignments'}, 'candidate document')
    rows = document['assignments']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ASSIGNMENTS:
        raise ValueError('assignments must contain between 1 and 100 rows')
    seen = set()
    for row in rows:
        _schema(row, {'work_package_id', 'context_ids'}, 'assignment')
        if not _text(row['work_package_id']) or row['work_package_id'] in seen:
            raise ValueError('assignment work_package_id must be nonblank and unique')
        seen.add(row['work_package_id'])
        _ids(row['context_ids'], 'context_ids', nonempty=True)
        if len(row['context_ids']) > MAX_CONTEXT_IDS:
            raise ValueError('each assignment supports at most 100 context IDs')


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'append_work_contexts':
        raise ValueError('review decision must be append_work_contexts')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _same(a, b, label):
    if canonical_json_bytes(a) != canonical_json_bytes(b):
        raise ValueError('work context assignment must preserve ' + label)


def _source_status_changes(before, after):
    changes = {}
    for label in ('planning_ledger', 'completion_ledger'):
        previous = {row['work_package_id']: row for row in before['planning'][label]}
        changes[label] = []
        for row in after['planning'][label]:
            old = previous[row['work_package_id']]
            fields = ('source_match_status', 'current_basis_sha256')
            left, right = ({key: copy.deepcopy(value[key]) for key in fields} for value in (old, row))
            if canonical_json_bytes(left) != canonical_json_bytes(right):
                changes[label].append(dict(work_package_id=row['work_package_id'], before=left, after=right))
    return changes


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    contexts = {row['context_id']: row for row in before['context']['context_ledger']}
    raw_contexts = {row['context_id']: (index, row) for index, row in enumerate(protocol.get('contexts', []))}
    candidate = copy.deepcopy(protocol)
    selections = []
    for index, row in enumerate(document['assignments']):
        work_index, work = _selected(protocol, before, row['work_package_id'])
        if any(cid not in contexts for cid in row['context_ids']):
            raise ValueError('all selected context IDs must already exist')
        existing = protocol['gaps'][work_index].get('context_ids', [])
        if set(existing).intersection(row['context_ids']):
            raise ValueError('selected context is already assigned; replacements, repeated links and no-ops are unsupported')
        candidate['gaps'][work_index].setdefault('context_ids', []).extend(copy.deepcopy(row['context_ids']))
        selections.append((index, work_index, row))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    for _, work_index, _ in selections:
        if 'context_ids' in protocol['gaps'][work_index]:
            restored['gaps'][work_index]['context_ids'] = copy.deepcopy(protocol['gaps'][work_index]['context_ids'])
        else:
            restored['gaps'][work_index].pop('context_ids')
    _same(restored, protocol, 'every original raw field except explicitly appended context-ID suffixes')
    _same(before['flow'], after['flow'], 'record flow')
    _same(_report_counts(before_reports), _report_counts(after_reports), 'report flow')
    for key in ('search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit',
                'execution_order', 'appraisal', 'experiments', 'synthesis'):
        _same(before[key], after[key], key)
    _same(before['context']['context_ledger'], after['context']['context_ledger'], 'all context assertions')
    for old, new in zip(before['work_packages'], after['work_packages']):
        _same({k:v for k,v in old.items() if k != 'context_ids'},
              {k:v for k,v in new.items() if k != 'context_ids'}, 'all work meaning, status and dependency fields')
    for label, fields in (('planning_ledger', ('assertion',)), ('completion_ledger', ('supplied_basis_sha256',))):
        for old, new in zip(before['planning'][label], after['planning'][label]):
            _same({key:old[key] for key in fields}, {key:new[key] for key in fields}, 'stored planning/completion assertions')
    old_targets = {row['work_package_id']: row for row in before['planning']['review_targets']}
    new_targets = {row['work_package_id']: row for row in after['planning']['review_targets']}
    selected_ids = {row['work_package_id'] for row in document['assignments']}
    changed_targets = [dict(work_package_id=wid, explicitly_selected=wid in selected_ids,
                            before=copy.deepcopy(old_targets[wid]), after=copy.deepcopy(new_targets[wid]))
                       for wid in sorted(old_targets)
                       if canonical_json_bytes(old_targets[wid]) != canonical_json_bytes(new_targets[wid])]
    work_snapshots, context_snapshots = [], []
    for candidate_index, work_index, row in selections:
        work_snapshots.append(dict(candidate_index=candidate_index, work_package_id=row['work_package_id'],
            input_pointer=f'/gaps/{work_index}', before_raw=copy.deepcopy(protocol['gaps'][work_index]),
            after_raw=copy.deepcopy(candidate['gaps'][work_index]),
            before_normalized=copy.deepcopy(before['work_packages'][work_index]),
            after_normalized=copy.deepcopy(after['work_packages'][work_index])))
        for cid in row['context_ids']:
            ci, raw = raw_contexts[cid]
            context_snapshots.append(dict(candidate_index=candidate_index, work_package_id=row['work_package_id'],
                context_id=cid, input_pointer=f'/contexts/{ci}', raw_context=copy.deepcopy(raw),
                normalized_context=copy.deepcopy(contexts[cid])))
    target = dict(schema_version=1, target_type='manual_work_context_assignment',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document), selected_work=work_snapshots,
        selected_contexts=context_snapshots, changed_work_source_targets=changed_targets,
        derived_source_status_changes=_source_status_changes(before, after),
        before_unassigned_context_ids=copy.deepcopy(before['context']['unassigned_context_ids']),
        after_unassigned_context_ids=copy.deepcopy(after['context']['unassigned_context_ids']),
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Prepare a blank assignment review without judging clinical or development applicability."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_WORK_CONTEXT_REVIEW',
        target=target, review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Fill every review field after inspecting exact assignments and changed work/dependent source bases. Assignment review does not endorse applicability or renew existing planning/completion assertions.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed context-ID suffixes without renewing any prior assertions."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, work/context assignments and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        assignment_count=len(document['assignments']),
        derived_source_status_changes=copy.deepcopy(target['derived_source_status_changes']),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=_report_counts(before_reports), after_report_flow=_report_counts(after_reports),
        engine_sha256=_implementation_hashes(), boundary=BOUNDARY, **copy.deepcopy(NEGATIVE_CLAIMS))
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_work_context_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Replay exact assignments; do not validate applicability or renew completion."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_work_context_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached work context assignment application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied work/context assignments, assignment review and recorded implementation; not authentication, clinical applicability, guideline currency or regulatory assessment.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied work context assignment\n' + '\n'.join(
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
        parser.exit(1, 'work context assignment error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
