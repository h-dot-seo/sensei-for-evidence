"""Append supplied evidence-sufficiency and conclusion-readiness assertions bound to the gate ledger through separate exact-input review."""
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
from readiness_links import READINESS_LABELS, SUFFICIENCY_LABELS
from research_bundle import engine_hashes

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_ASSERTIONS = 100
ASSERTION_FIELDS = {'assertion_id', 'assessor', 'assessed_at', 'evidence_sufficiency', 'conclusion_readiness',
                    'gates_sha256', 'scope_statement', 'rationale', 'limitations', 'reopening'}
TEXT_FIELDS = {'assertion_id', 'assessor', 'assessed_at', 'scope_statement', 'rationale', 'limitations'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicitly supplied readiness assertions and exact-input replay only. No evidence-sufficiency label, '
    'conclusion-readiness label, scope statement, rationale or reopening is selected, generated, scored or '
    'adjudicated. Each new assertion is bound to the current mechanical gate ledger by its hash; the binding '
    'detects later gate changes and does not establish that any gate closure means sufficiency, that any scope '
    'closure is justified or that any conclusion is ready. A READY assertion is permitted while gates are open as '
    'a deliberate human scope closure; the open gates at the asserted snapshot are recorded beside it, not '
    'resolved. A NOT_READY assertion with INSUFFICIENT evidence must name existing reopening work or an amendment '
    'note; it does not start work, change a work state or alter any statement, review, challenge, appraisal or '
    'planning assertion. Existing readiness assertions and all other raw research, source, work, planning, '
    'synthesis, challenge and completion assertions remain unchanged. The separate import review authorizes only '
    'recording the supplied assertions, not endorsing their judgement. Unsigned editable records do not '
    'authenticate people, chronology or globally unique IDs; consistently reauthored assertions can replay. '
    'Assertion rows persist in the candidate; import review and the gate snapshot remain detached. The '
    'mechanical conclusion readiness of every output stays NOT_READY; no census, scientific acceptance or '
    'clinical applicability is established.'
)
NEGATIVE_CLAIMS = dict(readiness_assessment='NOT_PERFORMED', evidence_sufficiency_assessment='NOT_PERFORMED',
    gate_closure_meaning='MECHANICAL_BOOKKEEPING_ONLY', scope_closure_adjudication='NOT_PERFORMED',
    assessor_identity_verification='NOT_ESTABLISHED', reviewer_identity_verification='NOT_ESTABLISHED',
    source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED', existing_review_renewal='NOT_PERFORMED',
    reopening_work_started='NOT_PERFORMED', import_review_scope='DETACHED_RECORD_ONLY',
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
                                   for name in ('nbib_intake.py', 'readiness_intake.py')})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return research, reports


def _report_counts(reports):
    return copy.deepcopy(reports['report_flow']) if reports is not None else None


def _gate_snapshot(readiness):
    return dict(gate_ledger=copy.deepcopy(readiness['gate_ledger']), gates_sha256=readiness['gates_sha256'],
                open_gate_ids=copy.deepcopy(readiness['open_gate_ids']),
                closed_gate_ids=copy.deepcopy(readiness['closed_gate_ids']),
                not_applicable_gate_ids=copy.deepcopy(readiness['not_applicable_gate_ids']))


def template(protocol):
    """Bind the current gate snapshot and list its open gates; leave every readiness judgement blank."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    research, _ = _validate(protocol)
    readiness = research['readiness']
    assertion = {key: None for key in sorted(ASSERTION_FIELDS)}
    assertion.update(gates_sha256=readiness['gates_sha256'], reopening=None)
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_READINESS_ASSERTIONS',
        candidate_document=dict(schema_version=1, readiness_assertions=[assertion]),
        **_gate_snapshot(readiness), mechanical_conclusion_readiness='NOT_READY',
        protocol_sha256=digest(protocol), engine_sha256=_implementation_hashes(), protocol_changed=False,
        **NEGATIVE_CLAIMS,
        template_warning='Only the gate ledger snapshot and its hash are mechanical. The assessor, assessment date, '
                         'evidence sufficiency, conclusion readiness, scope statement, rationale, limitations and any '
                         'reopening must be supplied by a human. Open gates are listed so that a READY assertion closes '
                         'scope deliberately, never by omission; closed gates are not evidence sufficiency.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'readiness_assertions'}, 'candidate document')
    rows = document['readiness_assertions']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ASSERTIONS:
        raise ValueError('readiness_assertions must be a nonempty list of at most 100 rows')
    seen = set()
    for row in rows:
        _schema(row, ASSERTION_FIELDS, 'readiness assertion')
        if any(not _text(row[key]) for key in TEXT_FIELDS):
            raise ValueError('readiness assertion text fields must be supplied nonblank literal strings')
        _date(row['assessed_at'], 'assessed_at')
        if row['assertion_id'] in seen:
            raise ValueError('duplicate candidate assertion_id')
        seen.add(row['assertion_id'])
        if row['evidence_sufficiency'] not in SUFFICIENCY_LABELS:
            raise ValueError('evidence_sufficiency must be one of ' + ', '.join(SUFFICIENCY_LABELS))
        if row['conclusion_readiness'] not in READINESS_LABELS:
            raise ValueError('conclusion_readiness must be one of ' + ', '.join(READINESS_LABELS))
        reopening = row['reopening']
        if reopening is not None and (not isinstance(reopening, dict) or len(reopening) != 1
                                      or not {'work_package_id', 'amendment_note'} & set(reopening)
                                      or not _text(next(iter(reopening.values())))):
            raise ValueError('reopening must be null or exactly one nonblank work_package_id or amendment_note')
        if re.fullmatch(r'[0-9a-f]{64}', row['gates_sha256'] or '') is None:
            raise ValueError('gates_sha256 must be 64 lowercase hexadecimal characters')


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_readiness_assertions':
        raise ValueError('review decision must be import_readiness_assertions')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _same(a, b, label):
    if canonical_json_bytes(a) != canonical_json_bytes(b):
        raise ValueError('readiness intake must preserve ' + label)


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    gates = before['readiness']
    old_ids = {row['assertion_id'] for row in gates['assertion_ledger']}
    new_ids = [row['assertion_id'] for row in document['readiness_assertions']]
    if old_ids.intersection(new_ids):
        raise ValueError('candidate assertion_id collides with an existing readiness assertion; no replacement or merge')
    for row in document['readiness_assertions']:
        if row['gates_sha256'] != gates['gates_sha256']:
            raise ValueError('readiness assertion gates_sha256 does not match the current gate ledger; '
                             'regenerate the template and re-examine the open gates before recording')
    candidate = copy.deepcopy(protocol)
    prefix = len(protocol.get('readiness_assertions', []))
    candidate.setdefault('readiness_assertions', []).extend(copy.deepcopy(document['readiness_assertions']))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    if 'readiness_assertions' in protocol:
        restored['readiness_assertions'] = restored['readiness_assertions'][:prefix]
    else:
        restored.pop('readiness_assertions')
    _same(restored, protocol, 'every original raw field and readiness assertion prefix')
    _same(before['flow'], after['flow'], 'record flow')
    _same(_report_counts(before_reports), _report_counts(after_reports), 'report flow')
    for key in ('search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit', 'work_packages',
                'execution_order', 'context', 'experiments', 'appraisal', 'synthesis', 'planning', 'challenge'):
        _same(before[key], after[key], key)
    _same(gates['gate_ledger'], after['readiness']['gate_ledger'], 'readiness gate ledger')
    _same(gates['gates_sha256'], after['readiness']['gates_sha256'], 'readiness gate hash')
    _same(gates['assertion_ledger'],
          [row for row in after['readiness']['assertion_ledger'] if row['assertion_id'] in old_ids],
          'existing normalized readiness assertions')
    work_by_id = {row['work_package_id']: (index, row) for index, row in enumerate(before['work_packages'])}
    reopening_work = []
    for index, row in enumerate(document['readiness_assertions']):
        reopening = row['reopening']
        if isinstance(reopening, dict) and 'work_package_id' in reopening:
            work_index, work = work_by_id[reopening['work_package_id']]
            reopening_work.append(dict(candidate_index=index, assertion_id=row['assertion_id'],
                work_package_id=reopening['work_package_id'], input_pointer=f'/gaps/{work_index}',
                raw_work=copy.deepcopy(protocol['gaps'][work_index]), normalized_work=copy.deepcopy(work)))
    appended = [row for row in after['readiness']['assertion_ledger'] if row['assertion_id'] in new_ids]
    target = dict(schema_version=1, target_type='manual_readiness_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document),
        appended_assertions=[dict(candidate_index=i, output_pointer=f'/readiness_assertions/{prefix + i}',
            assertion=copy.deepcopy(row)) for i, row in enumerate(document['readiness_assertions'])],
        normalized_appended_assertions=copy.deepcopy(appended),
        **_gate_snapshot(gates), reopening_work=reopening_work,
        gate_context_scope='MECHANICAL_GATE_LEDGER_SNAPSHOT_NOT_SUFFICIENCY_OR_READINESS',
        before_current_assertion_ids=copy.deepcopy(gates['current_assertion_ids']),
        before_stale_assertion_ids=copy.deepcopy(gates['stale_assertion_ids']),
        after_current_assertion_ids=copy.deepcopy(after['readiness']['current_assertion_ids']),
        after_stale_assertion_ids=copy.deepcopy(after['readiness']['stale_assertion_ids']),
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Prepare a blank import review without judging the supplied assertions."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_READINESS_IMPORT_REVIEW',
        target=target, review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Fill all human review fields after inspecting the exact proposed assertions, the bound gate '
                         'snapshot, its open gates and any reopening work. Import review records the supplied assertions; '
                         'it does not endorse their sufficiency or readiness judgement.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed supplied assertions without renewing any older assertions."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, assertions and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_assertion_count=len(before['readiness']['assertion_ledger']),
        after_assertion_count=len(after['readiness']['assertion_ledger']),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=_report_counts(before_reports), after_report_flow=_report_counts(after_reports),
        engine_sha256=_implementation_hashes(), boundary=BOUNDARY, **copy.deepcopy(NEGATIVE_CLAIMS))
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_readiness_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Replay the full application; do not assess whether any assertion is justified."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_readiness_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached readiness intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied assertion rows, import review and recorded implementation; '
                           'not authentication, sufficiency assessment or readiness adjudication.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied readiness assertion intake\n' + '\n'.join(
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
            result = template(protocol)
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
        parser.exit(1, 'readiness intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
