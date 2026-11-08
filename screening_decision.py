"""Prepare, assemble and inspect explicit supplied human screening decisions offline."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import engine_hashes
from json_io import configure_utf8_stdio, parse_json, quoted_display
from screening_links import link_screening_reviews
from screening_decision_links import (BOUNDARY, DOCUMENT_FIELDS, digest, prepare_target,
                                      build_candidate, link_screening_decisions)


def _validate(protocol):
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    # Explicitly validate even before integration into the main workflow.
    link_screening_decisions(protocol, research.get('bibliographic_collection'))
    return research, reports


def _metadata(protocol):
    implementation = dict(engine_hashes())
    implementation['screening_decision.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return dict(schema_version=1, protocol_version=copy.deepcopy(protocol['version']),
                protocol_sha256=digest(protocol), engine_sha256=implementation,
                hash_scope='Sorted compact UTF-8 supplied JSON; object key order ignored, list order retained; not authentication.',
                adjudication_validity='NOT_ASSESSED', reviewer_identity_verification='NOT_ESTABLISHED',
                historical_protocol_reconstruction='NOT_PERFORMED', external_calls=0, boundary=BOUNDARY)


def prepare(protocol, record_id):
    research, _ = _validate(protocol)
    result = prepare_target(protocol, record_id, research.get('bibliographic_collection'))
    document = {key: None for key in sorted(DOCUMENT_FIELDS)}
    document.update(schema_version=1, record_id=record_id, target_sha256=result['target']['target_sha256'])
    result.update(_metadata(protocol))
    result.update(status='AWAITING_SUPPLIED_DECISION', decision_document=document, protocol_changed=False,
                  template_warning='All human fields remain null. Supply the exact human decision, reason, adjudicator, date, rationale, locator and unique receipt ID. No review winner is inferred.')
    return result


def assemble(protocol, document):
    before, before_reports = _validate(protocol)
    result = build_candidate(protocol, document, before.get('bibliographic_collection'))
    candidate = result['protocol_candidate']
    after, after_reports = _validate(candidate)
    result.update(_metadata(protocol))
    result.update(status='SUPPLIED_DECISION_ASSEMBLED', protocol_changed=True,
                  protocol_candidate_sha256=digest(candidate),
                  before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
                  before_report_flow=None if before_reports is None else copy.deepcopy(before_reports['report_flow']),
                  after_report_flow=None if after_reports is None else copy.deepcopy(after_reports['report_flow']),
                  screening_review_before=link_screening_reviews(protocol, before.get('bibliographic_collection')),
                  screening_review_after=link_screening_reviews(candidate, after.get('bibliographic_collection')),
                  screening_decisions=link_screening_decisions(candidate, after.get('bibliographic_collection')),
                  review_assertions_changed=False)
    return result


def inspect(protocol, record_id=None):
    research, _ = _validate(protocol)
    result = link_screening_decisions(protocol, research.get('bibliographic_collection'))
    complete_counts = copy.deepcopy(result['counts'])
    if record_id is not None:
        known = {rid for search in protocol['searches'] for rid in search['record_ids']}
        known.update(row['record_id'] for row in result['record_history'])
        if not isinstance(record_id, str) or record_id not in known:
            raise ValueError('unknown screening decision record_id selection')
        result['receipt_ledger'] = [r for r in result['receipt_ledger'] if r['receipt']['target']['record_id'] == record_id]
        result['record_history'] = [r for r in result['record_history'] if r['record_id'] == record_id]
        result['records_with_history_cues'] = [r for r in result['records_with_history_cues'] if r == record_id]
        refs = {ref['search_context_sha256'] for row in result['receipt_ledger'] for ref in row['receipt']['target']['source_context_refs']}
        result['source_contexts'] = [r for r in result['source_contexts'] if r['search_context_sha256'] in refs]
        result['counts'] = dict(receipts=len(result['receipt_ledger']), source_contexts=len(result['source_contexts']),
                               records_with_history=len(result['record_history']),
                               records_with_history_cues=len(result['records_with_history_cues']))
    result.update(_metadata(protocol))
    result.update(status='SCREENING_DECISION_HISTORY_INSPECTED', protocol_changed=False,
                  protocol_counts=complete_counts,
                  selection=dict(scope='ALL_HISTORY' if record_id is None else 'EXACT_RECORD_ID', record_id=record_id,
                                 counts_scope='SELECTED_HISTORY', validation_scope='ENTIRE_PROTOCOL',
                                 source_catalog_scope='REFERENCED_BY_SELECTED_RECEIPTS'))
    return result


def render_text(result):
    lines = ['Supplied screening decision', 'Status: ' + result['status']]
    for key, value in result.items():
        if key not in ('boundary', 'status'):
            lines.append(key + ': ' + quoted_display(value))
    lines.append(result['boundary'])
    return '\n'.join(lines) + '\n'


def _encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    target = commands.add_parser('target')
    accepted = commands.add_parser('assemble')
    inspection = commands.add_parser('inspect')
    for command in (target, accepted, inspection):
        command.add_argument('protocol', type=Path)
        command.add_argument('--text', action='store_true')
    target.add_argument('--record-id', required=True)
    target.add_argument('--output', type=Path)
    accepted.add_argument('decision_document', type=Path)
    accepted.add_argument('--protocol-output', type=Path)
    inspection.add_argument('--record-id')
    args = parser.parse_args()
    try:
        protocol = parse_json(args.protocol.read_bytes())
        destination = None
        output = None
        if args.command == 'target':
            result = prepare(protocol, args.record_id)
            destination, output = args.output, result
        elif args.command == 'assemble':
            result = assemble(protocol, parse_json(args.decision_document.read_bytes()))
            destination, output = args.protocol_output, result['protocol_candidate']
        else:
            result = inspect(protocol, args.record_id)
        rendered = render_text(result) if args.text else _encode(result)
        encoded = _encode(output) if destination is not None else None
        if destination is not None:
            with destination.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write(encoded)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        parser.exit(1, 'screening decision error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
