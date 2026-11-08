"""Record and replay an explicit human full-text decision without inferring agreement."""
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

DOCUMENT_FIELDS = {'schema_version', 'receipt_id', 'report_id', 'target_sha256',
                   'decision', 'reason', 'adjudicator', 'decided_at', 'rationale',
                   'source_locator', 'study_declaration'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicit supplied human choice and exact-input replay only. Source/reviewer/inventory '
    'snapshots are supplied context, not proof the person read or relied on them. No voting, '
    'consensus, eligibility correctness, clinical validity, reading, source authenticity or '
    'document-byte verification is performed. Study labels declare memberships, not independent '
    'or eligible studies. Identity and authority of the named person are not authenticated. '
    'This editable detached application record is not an immutable history, authenticated receipt, '
    'chronology, globally unique identifier registry or evidence of execution. Retain the original '
    'protocol and recorded implementation for replay; snapshots do not reconstruct the whole input. '
    'Only the selected report decision, reason and explicitly supplied membership declaration can '
    'change. Conflicting downstream links are rejected, never deleted or repaired automatically. '
    'Locators remain inert; no source is fetched and no biological experiment is executed.'
)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _normalized(value):
    return parse_json(canonical_json_bytes(value))


def _validate(protocol):
    protocol = _normalized(protocol)
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return protocol, research, reports


def _implementation_hashes():
    return dict(engine_hashes(), **{
        'report_decision.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def _target(protocol, report_id, research):
    if not _text(report_id):
        raise ValueError('report decision requires a nonblank literal report_id')
    prepared = prepare_targets(protocol, research.get('bibliographic_collection'))
    source = next((r for r in prepared['report_targets'] if r['report_id'] == report_id), None)
    if source is None:
        raise ValueError('unknown report decision report_id')
    if source['retrieval'] != 'retrieved':
        raise ValueError('report decision requires an already retrieved report; retrieval is not changed')
    target = dict(schema_version=1, target_type='report_decision', report_id=report_id,
                  input_protocol_sha256=digest(protocol), prior_report=copy.deepcopy(source['recorded_report']),
                  report_source_target=copy.deepcopy(source))
    for key, prefix in [('report_reviews', 'report_review'), ('report_study_reviews', 'study_review'),
                        ('report_study_inventory', 'inventory')]:
        target[prefix+'_stage'] = 'SUPPLIED' if key in protocol else 'NOT_SUPPLIED'
        target[prefix+'_snapshots'] = copy.deepcopy([r for r in protocol.get(key, []) if r['report_id'] == report_id])
    if 'report_study_inventory_reviews' in protocol:
        target['inventory_review_stage'] = 'SUPPLIED'
        target['inventory_review_snapshots'] = copy.deepcopy(
            [r for r in protocol['report_study_inventory_reviews'] if r['report_id'] == report_id])
    target['target_sha256'] = digest(target)
    return target


def prepare(protocol, report_id):
    """Prepare a detached exact-input target; all human choices remain blank."""
    protocol, research, _ = _validate(protocol)
    target = _target(protocol, report_id, research)
    document = {key: None for key in sorted(DOCUMENT_FIELDS)}
    document.update(schema_version=1, report_id=report_id, target_sha256=target['target_sha256'])
    return dict(schema_version=1, status='AWAITING_SUPPLIED_REPORT_DECISION', target=target,
                decision_document=document, protocol_sha256=digest(protocol),
                engine_sha256=_implementation_hashes(), protocol_changed=False, external_calls=0,
                template_warning='Fill every human field honestly. Include requires an explicit scalar or plural study declaration; exclude requires null and removes both controlled membership fields. No current membership or review winner is copied into the decision.',
                boundary=BOUNDARY)


def validate_document(document):
    if not isinstance(document, dict) or set(document) != DOCUMENT_FIELDS:
        raise ValueError('report decision document has unknown or missing fields')
    if type(document['schema_version']) is not int or document['schema_version'] != 1:
        raise ValueError('report decision schema_version must be integer 1')
    if any(not _text(document[k]) for k in DOCUMENT_FIELDS - {'schema_version', 'study_declaration'}):
        raise ValueError('all report decision text fields must be supplied nonblank literal strings')
    if document['decision'] not in ('include', 'exclude'):
        raise ValueError('report decision must be include or exclude')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', document['decided_at']) is None:
        raise ValueError('decided_at must be YYYY-MM-DD')
    try:
        datetime.date.fromisoformat(document['decided_at'])
    except ValueError as error:
        raise ValueError('invalid report decision date') from error
    declaration = document['study_declaration']
    if document['decision'] == 'exclude':
        if declaration is not None:
            raise ValueError('exclude requires an explicit null study_declaration')
    elif not isinstance(declaration, dict):
        raise ValueError('include requires an explicit study declaration object')
    elif set(declaration) == {'study_id'}:
        if not _text(declaration['study_id']):
            raise ValueError('study_id must be a nonblank literal string')
    elif set(declaration) == {'study_ids'}:
        ids = declaration['study_ids']
        if (not isinstance(ids, list) or not ids or any(not _text(sid) for sid in ids)
                or len(ids) != len(set(ids))):
            raise ValueError('study_ids must be nonempty unique literal strings')
    else:
        raise ValueError('study declaration requires exactly study_id or study_ids')


def assemble(protocol, document):
    """Build a detached record; no files or original protocol are changed."""
    protocol, before, before_reports = _validate(protocol)
    document = _normalized(document)
    validate_document(document)
    target = _target(protocol, document['report_id'], before)
    if document['target_sha256'] != target['target_sha256']:
        raise ValueError('decision target does not match the entire current input; no automatic rebase')
    candidate = copy.deepcopy(protocol)
    selected = next(r for r in candidate['reports'] if r['report_id'] == document['report_id'])
    selected.update(decision=document['decision'], reason=document['reason'])
    selected.pop('study_id', None)
    selected.pop('study_ids', None)
    if document['decision'] == 'include':
        selected.update(copy.deepcopy(document['study_declaration']))
    # This full post-validation also covers scalar-only inputs lacking optional ledgers.
    candidate, after, after_reports = _validate(candidate)
    result_report = next(r for r in candidate['reports'] if r['report_id'] == document['report_id'])
    receipt = dict(schema_version=1, receipt_id=document['receipt_id'], target=target,
                   assertion=copy.deepcopy(document), result_report=copy.deepcopy(result_report),
                   input_protocol_sha256=digest(protocol), protocol_candidate_sha256=digest(candidate),
                   before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
                   before_report_flow=copy.deepcopy(before_reports['report_flow']),
                   after_report_flow=copy.deepcopy(after_reports['report_flow']),
                   engine_sha256=_implementation_hashes(), review_assertions_changed=False,
                   source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED',
                   document_bytes_verification='NOT_PERFORMED', eligibility_correctness='NOT_ASSESSED',
                   reviewer_identity_verification='NOT_ESTABLISHED', adjudication_validity='NOT_ASSESSED',
                   historical_protocol_reconstruction='NOT_PERFORMED', external_calls=0, boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return dict(schema_version=1, kind='detached_report_decision', receipt=receipt,
                protocol_candidate=candidate)


def verify(protocol, application_record):
    """Replay against retained original input and implementation, not authenticate a choice."""
    record = _normalized(application_record)
    if (not isinstance(record, dict) or set(record) != APPLICATION_FIELDS
            or type(record['schema_version']) is not int or record['schema_version'] != 1
            or record['kind'] != 'detached_report_decision' or not isinstance(record['receipt'], dict)
            or 'assertion' not in record['receipt']):
        raise ValueError('invalid detached report decision application record')
    replayed = assemble(protocol, record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
                receipt_id=receipt['receipt_id'], report_id=receipt['assertion']['report_id'],
                receipt_sha256=receipt['receipt_sha256'], input_protocol_sha256=receipt['input_protocol_sha256'],
                protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
                engine_sha256=copy.deepcopy(receipt['engine_sha256']),
                verification_scope='Exact supplied original input, human document, candidate and current recorded implementation only; not authentication or scientific validation.',
                protocol_changed=False, external_calls=0, boundary=BOUNDARY)


def render_text(result):
    return 'Explicit supplied full-text report decision\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'


def _encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


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
    target.add_argument('--report-id', required=True)
    target.add_argument('--output', type=Path)
    assembly.add_argument('decision_document', type=Path)
    assembly.add_argument('--output', type=Path, help='new detached application record, not a protocol')
    replay.add_argument('application_record', type=Path)
    replay.add_argument('--protocol-output', type=Path, help='new protocol only after exact replay succeeds')
    args = parser.parse_args()
    try:
        protocol = parse_json(args.protocol.read_bytes())
        destination = None
        artifact = None
        if args.command == 'target':
            result = prepare(protocol, args.report_id)
            destination, artifact = args.output, result
        elif args.command == 'assemble':
            result = assemble(protocol, parse_json(args.decision_document.read_bytes()))
            destination, artifact = args.output, result
        else:
            record = parse_json(args.application_record.read_bytes())
            result = verify(protocol, record)
            destination, artifact = args.protocol_output, record['protocol_candidate']
        encoded = _encode(artifact) if destination is not None else None
        rendered = render_text(result) if args.text else _encode(result)
        rendered.encode('utf-8')
        if encoded is not None:
            encoded.encode('utf-8')
        if destination is not None:
            with destination.open('x', encoding='utf-8', newline='\n') as output:
                output.write(encoded)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'report decision error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
