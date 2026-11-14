"""Record or transition supplied question labels through a separate exact-input review."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import engine_hashes
from question_links import (FIELDS, ORIGIN_FIELDS, TRANSITIONS, NEGATIVE_CLAIMS, BOUNDARY,
                            validate_row, question_basis)
from context_links import iso_date, nonempty_text, id_list
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from archive_safety import read_bounded
from nbib_intake import _strict_json

MAX_PROTOCOL_BYTES = 50_000_000
MAX_DOCUMENT_BYTES = 10_000_000
MAX_APPLICATION_BYTES = 50_000_000
CHANGED_FIELDS = {'status', 'statement_ids', 'basis_sha256', 'recorded_by', 'recorded_at', 'rationale', 'limitations'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision', 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
INTAKE_BOUNDARY = (BOUNDARY + ' Append preserves existing rows. A transition changes only the selected '
    'record status, statement selection/basis, recorder/date, rationale and limitations. Terminal '
    'labels and same-status changes cannot be renewed or reopened here. Separate review is a supplied '
    'assertion, not authenticated human participation or answer endorsement. Unsigned consistently '
    'reauthored records can replay. Keep the original input, application and recorded implementation; '
    'ordinary bundles do not preserve detached review history. Output is exclusive but not multi-file '
    'transactional; failures after a first output may leave that output. No automatic rebase.')


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normal(value, limit):
    _strict_json(value)
    raw = canonical_json_bytes(value)
    if len(raw) > limit:
        raise ValueError('byte limit exceeded')
    return parse_json(raw)


def _shape(value, fields):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('exact fields required')
    if 'schema_version' in fields and (type(value['schema_version']) is not int or value['schema_version'] != 1):
        raise ValueError('integer schema_version 1 required')


def _hashes():
    return dict(engine_hashes(), **{name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('question_intake.py', 'nbib_intake.py')})


def _validate(protocol):
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    return research


def template(protocol, statement_ids=None):
    protocol = _normal(protocol, MAX_PROTOCOL_BYTES)
    research = _validate(protocol)
    selected = [] if statement_ids is None else statement_ids
    id_list(selected, 'statement_ids')
    if len(selected) > 100: raise ValueError('at most 100 statement IDs')
    basis = question_basis(research['synthesis'], selected)
    row = {key: None for key in sorted(FIELDS)}
    row.update(text=protocol['question'], statement_ids=copy.deepcopy(selected), basis_sha256=basis, origin={key: None for key in sorted(ORIGIN_FIELDS)})
    return dict(schema_version=1, candidate_document=dict(schema_version=1, operation='append', question_records=[row]),
        protocol_sha256=digest(protocol), engine_sha256=_hashes(), protocol_changed=False,
        status='AWAITING_SUPPLIED_QUESTION_RECORDS', template_warning='Only the original root text and explicitly selected statement IDs/current basis are mechanical. Supply every identity, status, origin, date, rationale and limitation; no question or approval is generated.',
        **NEGATIVE_CLAIMS, boundary=INTAKE_BOUNDARY)


def transition_template(protocol, question_id, statement_ids=None):
    protocol = _normal(protocol, MAX_PROTOCOL_BYTES)
    research = _validate(protocol)
    rows = {r['question_id']: r for r in protocol.get('question_records', [])}
    if question_id not in rows or not TRANSITIONS[rows[question_id]['status']]:
        raise ValueError('unknown or terminal question cannot transition')
    changes = {key: None for key in sorted(CHANGED_FIELDS)}
    selected = rows[question_id]['statement_ids'] if statement_ids is None else statement_ids
    id_list(selected, 'statement_ids')
    if len(selected) > 100: raise ValueError('at most 100 statement IDs')
    changes.update(statement_ids=copy.deepcopy(selected), basis_sha256=question_basis(research['synthesis'], selected))
    return dict(schema_version=1, candidate_document=dict(schema_version=1, operation='transition',
        question_id=question_id, changes=changes), selected_question=copy.deepcopy(rows[question_id]),
        allowed_supplied_statuses=list(TRANSITIONS[rows[question_id]['status']]),
        protocol_sha256=digest(protocol), engine_sha256=_hashes(), protocol_changed=False,
        status='AWAITING_SUPPLIED_QUESTION_TRANSITION', **NEGATIVE_CLAIMS, boundary=INTAKE_BOUNDARY)


def _prepare(protocol, document):
    protocol = _normal(protocol, MAX_PROTOCOL_BYTES)
    document = _normal(document, MAX_DOCUMENT_BYTES)
    before = _validate(protocol)
    if not isinstance(document, dict):
        raise ValueError('candidate document must be an object')
    candidate = copy.deepcopy(protocol)
    operation = document.get('operation')
    old = protocol.get('question_records', [])
    if operation == 'append':
        _shape(document, {'schema_version', 'operation', 'question_records'})
        rows = document['question_records']
        if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
            raise ValueError('append requires 1 to 100 question records')
        old_ids = {r['question_id'] for r in old}
        for row in rows:
            validate_row(row)
            if row['question_id'] in old_ids:
                raise ValueError('append cannot replace an existing question')
        candidate.setdefault('question_records', []).extend(copy.deepcopy(rows))
        selected = rows
    elif operation == 'transition':
        _shape(document, {'schema_version', 'operation', 'question_id', 'changes'})
        if not nonempty_text(document['question_id']):
            raise ValueError('question ID required')
        changes = document['changes']
        _shape(changes, CHANGED_FIELDS)
        matches = [i for i, row in enumerate(old) if row['question_id'] == document['question_id']]
        if len(matches) != 1:
            raise ValueError('transition requires one existing question')
        index = matches[0]
        if changes['status'] not in TRANSITIONS[old[index]['status']]:
            raise ValueError('supplied transition not allowed; no same-state renewal or terminal reopening')
        candidate['question_records'][index].update(copy.deepcopy(changes))
        selected = [candidate['question_records'][index]]
        validate_row(selected[0])
    else:
        raise ValueError('unknown question operation')
    for row in selected:
        if row['basis_sha256'] != question_basis(before['synthesis'], row['statement_ids']):
            raise ValueError('new question binding must match selected current statement bases')
        if row['origin']['kind'] == 'PROTOCOL' and row['origin']['protocol_question_sha256'] != digest(protocol['question']):
            raise ValueError('new question protocol origin must match current root text')
    candidate = _normal(candidate, MAX_PROTOCOL_BYTES)
    after = _validate(candidate)
    # Optional question context cannot alter any existing run result or gate.
    left = {k: v for k, v in before.items() if k != 'question_ledger'}
    right = {k: v for k, v in after.items() if k != 'question_ledger'}
    if canonical_json_bytes(left) != canonical_json_bytes(right):
        raise ValueError('question operation changed existing research results')
    target = dict(schema_version=1, target_type='supplied_question_' + operation,
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_protocol_sha256=digest(candidate),
        before_question_ledger=copy.deepcopy(before.get('question_ledger')),
        after_question_ledger=copy.deepcopy(after['question_ledger']),
        engine_sha256=_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=INTAKE_BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, candidate, target


def prepare(protocol, document):
    protocol, document, candidate, target = _prepare(protocol, document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normal(dict(schema_version=1, status='AWAITING_SUPPLIED_QUESTION_REVIEW',
        target=target, review_document=review, protocol_changed=False, **NEGATIVE_CLAIMS,
        boundary=INTAKE_BOUNDARY), MAX_APPLICATION_BYTES)


def assemble(protocol, document, review):
    review = _normal(review, MAX_DOCUMENT_BYTES)
    _shape(review, REVIEW_FIELDS)
    for key in REVIEW_FIELDS - {'schema_version'}:
        if not nonempty_text(review[key]):
            raise ValueError('review fields must be supplied')
    iso_date(review['reviewed_at'], 'reviewed_at')
    protocol, document, candidate, target = _prepare(protocol, document)
    if review['decision'] != 'record_supplied_questions' or review['target_sha256'] != target['target_sha256']:
        raise ValueError('review must authorize this exact supplied question target')
    receipt = dict(schema_version=1, candidate_document=document, assertion=review, target=target,
        input_protocol_sha256=digest(protocol), protocol_candidate_sha256=digest(candidate),
        engine_sha256=_hashes(), **NEGATIVE_CLAIMS, boundary=INTAKE_BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normal(dict(schema_version=1, kind='detached_question_intake', receipt=receipt,
        protocol_candidate=candidate), MAX_APPLICATION_BYTES)


def verify(protocol, application):
    application = _normal(application, MAX_APPLICATION_BYTES)
    _shape(application, APPLICATION_FIELDS)
    if application['kind'] != 'detached_question_intake' or not isinstance(application['receipt'], dict):
        raise ValueError('wrong application kind')
    receipt = application['receipt']
    replay = assemble(protocol, receipt['candidate_document'], receipt['assertion'])
    if canonical_json_bytes(replay) != canonical_json_bytes(application):
        raise ValueError('application differs from exact replay')
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_sha256=receipt['receipt_sha256'], protocol_changed=False,
        **NEGATIVE_CLAIMS, boundary=INTAKE_BOUNDARY)


def _write(path, value):
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError('output exists')
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('template', 'transition-template', 'target', 'assemble', 'verify'):
        sub = commands.add_parser(name)
        sub.add_argument('protocol', type=Path)
        sub.add_argument('--output', type=Path)
        if name in ('template', 'transition-template'):
            sub.add_argument('--statement-id', action='append', default=None)
        if name == 'transition-template':
            sub.add_argument('question_id')
        if name in ('target', 'assemble'):
            sub.add_argument('candidate_document', type=Path)
        if name == 'assemble':
            sub.add_argument('review_document', type=Path)
        if name == 'verify':
            sub.add_argument('application_record', type=Path)
            sub.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        protocol = parse_json(read_bounded(args.protocol, MAX_PROTOCOL_BYTES))
        if args.command == 'template':
            result = template(protocol, args.statement_id)
        elif args.command == 'transition-template':
            result = transition_template(protocol, args.question_id, args.statement_id)
        elif args.command in ('target', 'assemble'):
            document = parse_json(read_bounded(args.candidate_document, MAX_DOCUMENT_BYTES))
            result = (prepare(protocol, document) if args.command == 'target' else
                      assemble(protocol, document, parse_json(read_bounded(args.review_document, MAX_DOCUMENT_BYTES))))
        else:
            application = parse_json(read_bounded(args.application_record, MAX_APPLICATION_BYTES))
            result = verify(protocol, application)
            if args.protocol_output:
                _write(args.protocol_output, application['protocol_candidate'])
        if args.output:
            _write(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, AttributeError):
        parser.exit(1, 'question_intake: invalid input or unavailable output\n')


if __name__ == '__main__':
    main()
