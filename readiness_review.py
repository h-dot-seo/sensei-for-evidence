"""Show the mechanical conclusion-readiness gate ledger and supplied readiness assertions without assessing sufficiency."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from research_bundle import engine_hashes

BOUNDARY = ('Read-only view of mechanical gate bookkeeping and supplied readiness assertions. A gate closes when '
            'its listed supplied items are empty; closing every gate is necessary bookkeeping, not evidence '
            'sufficiency, census or conclusion readiness. Supplied sufficiency and readiness labels are human '
            'assertions bound to a gate snapshot by hash; this view does not assess, adjudicate or promote them, '
            'performs no search, source reading or model call, and changes no record. '
            'Mechanical conclusion readiness stays NOT_READY.')


def review(protocol):
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    readiness = research['readiness']
    implementation = dict(engine_hashes(), **{'readiness_review.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return dict(schema_version=1, question=research['question'], protocol_version=research['protocol_version'],
                protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                hash_scope='sorted compact UTF-8 JSON; object key order ignored, list order retained; not authentication',
                engine_sha256=implementation,
                gate_ledger=copy.deepcopy(readiness['gate_ledger']), gates_sha256=readiness['gates_sha256'],
                gates_hash_scope='canonical gate ledger rows only; a protocol change that moves no gate item leaves it unchanged',
                open_gate_ids=copy.deepcopy(readiness['open_gate_ids']),
                closed_gate_ids=copy.deepcopy(readiness['closed_gate_ids']),
                not_applicable_gate_ids=copy.deepcopy(readiness['not_applicable_gate_ids']),
                open_items={row['gate_id']: copy.deepcopy(row['open_items'])
                            for row in readiness['gate_ledger'] if row['status'] == 'OPEN'},
                mechanical_conclusion_readiness='NOT_READY', gate_scope=readiness['gate_scope'],
                assertion_stage=readiness['stage'], assertion_ledger=copy.deepcopy(readiness['assertion_ledger']),
                current_assertion_ids=copy.deepcopy(readiness['current_assertion_ids']),
                stale_assertion_ids=copy.deepcopy(readiness['stale_assertion_ids']),
                assertion_scope='supplied human assertions bound to a gate snapshot; not mechanical conclusions',
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY',
                readiness_boundary=readiness['boundary'], boundary=BOUNDARY)


def render_text(result):
    show = quoted_display
    lines = ['Conclusion readiness gate review (mechanical bookkeeping, not sufficiency)',
             'Question: ' + show(result['question']), 'Protocol version: ' + show(result['protocol_version']),
             'Protocol SHA-256: ' + result['protocol_sha256'], 'Gate ledger SHA-256: ' + result['gates_sha256'],
             'Open gates: ' + show(result['open_gate_ids']), 'Closed gates: ' + show(result['closed_gate_ids']),
             'Not applicable gates: ' + show(result['not_applicable_gate_ids']), '']
    for row in result['gate_ledger']:
        lines.append('Gate ' + show(row['gate_id']) + ': ' + row['status'] + '; open items: ' + show(row['open_items'])
                     + '; basis: ' + show(row['basis']))
    lines.extend(['', 'Supplied readiness assertion stage: ' + result['assertion_stage'],
                  'Supplied readiness assertions (human assertions bound to a gate snapshot, not mechanical conclusions): '
                  + show(result['assertion_ledger']),
                  'Assertions bound to the current gates: ' + show(result['current_assertion_ids']),
                  'Assertions bound to stale gates: ' + show(result['stale_assertion_ids']),
                  'Mechanical conclusion readiness: NOT_READY', 'Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY',
                  result['gate_scope'], result['readiness_boundary'], result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--text', action='store_true', help='print a human-readable gate and assertion summary')
    args = parser.parse_args()
    try:
        result = review(parse_json(args.protocol.read_bytes()))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2), end='' if args.text else '\n')


if __name__ == '__main__':
    main()
