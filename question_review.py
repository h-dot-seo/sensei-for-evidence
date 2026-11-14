"""Inspect supplied question labels and bindings without assessing answers."""
import argparse
import copy
import json
from pathlib import Path
from evidence_workflow import run
from question_links import link_questions, BOUNDARY, NEGATIVE_CLAIMS
from json_io import configure_utf8_stdio, parse_json, quoted_display
from archive_safety import read_bounded
from question_intake import MAX_PROTOCOL_BYTES, _write


def review(protocol):
    research = run(protocol)
    ledger = research.get('question_ledger')
    if ledger is None:
        ledger = link_questions(protocol, research['synthesis'], research['challenge'], research['readiness'], research['work_packages'])
    return dict(schema_version=1, question=research['question'], supplied_questions=copy.deepcopy(ledger),
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def context_lines(ledger):
    return ['Supplied questions: open ' + str(len(ledger['open_question_ids'])) + ', unresolved ' + str(len(ledger['unresolved_question_ids'])),
            'Stale question statement bindings: ' + str(len(ledger['stale_question_bindings'])) + '; changed root-question origins: ' + str(len(ledger['changed_protocol_question_origins'])),
            'Question labels are supplied assertions, not assessed answers, new gates or closure decisions.']


def render_text(result):
    ledger = result['supplied_questions']
    lines = ['Supplied question record review', 'Root question: ' + quoted_display(result['question'])] + context_lines(ledger)
    lines += [quoted_display(row) for row in ledger['question_ledger']]
    return '\n'.join(lines + [BOUNDARY]) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--text', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = review(parse_json(read_bounded(args.protocol, MAX_PROTOCOL_BYTES)))
        if args.output:
            _write(args.output, result)
        print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2), end='' if args.text else '\n')
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, AttributeError):
        parser.exit(1, 'question_review: invalid input or unavailable output\n')


if __name__ == '__main__':
    main()
