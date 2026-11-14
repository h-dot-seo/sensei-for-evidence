"""Draft and check an operator-supplied ledger-free starting protocol."""
import argparse
import hashlib
import json
from pathlib import Path

from challenge_intake import _normalized
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from receipt_intake import fresh_base
from research_bundle import engine_hashes
from screening_sheet import _write_new
from screening_sheet_intake import _read

MAX_BYTES = 10_000_000
TEXT_FIELDS = ('question', 'version')
CRITERIA_FIELDS = ('inclusion_criteria', 'exclusion_criteria')
PLAN_FIELDS = ('search_id', 'source', 'query', 'window')
LEDGERS = ('searches', 'screening', 'evidence', 'gaps')
FIELDS = set(TEXT_FIELDS + CRITERIA_FIELDS + ('search_plan',) + LEDGERS)
BOUNDARY = (
    'Starting-document scaffold and mechanical shape checks only. All question, criteria, '
    'search IDs, source labels, queries and windows must be supplied by the operator. '
    'No research question, criterion, query, decision, timestamp, result or approval is '
    'invented. Passing means a recommended ledger-free starting shape, not plan or query '
    'adequacy, protocol lock, ethics approval, search execution or evidence sufficiency. '
    'Keep the original common base unchanged for later imports; never clear existing '
    'research to make a base. Real research text belongs outside the public repository. '
    'No network or model calls. Python validators remain authoritative; this is not a '
    'JSON Schema validator or an assertion that every valid protocol must have this shape.'
)
NEGATIVE_CLAIMS = dict(plan_adequacy='NOT_ASSESSED', query_adequacy='NOT_ASSESSED',
    protocol_approval='NOT_ESTABLISHED', search_execution='NOT_PERFORMED',
    census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', external_calls=0)


def _hashes():
    root = Path(__file__).resolve().parent
    names = ('protocol_scaffold.py', 'receipt_intake.py', 'challenge_intake.py',
             'nbib_intake.py', 'screening_sheet.py', 'screening_sheet_intake.py')
    return dict(engine_hashes(), **{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def template():
    draft = dict(question=None, version=None, inclusion_criteria=[], exclusion_criteria=[],
        search_plan=[{key:None for key in PLAN_FIELDS}], searches=[], screening=[], evidence=[], gaps=[])
    return dict(schema_version=1, status='AWAITING_SUPPLIED_STARTING_PROTOCOL', draft=draft,
        template_warning='Fill every required field in the separate draft, not this wrapper. '
        'Null and empty criteria are not agreement or an adequate search plan.',
        boundary=BOUNDARY, engine_sha256=_hashes(), **NEGATIVE_CLAIMS)


def check(draft):
    draft = _normalized(draft, MAX_BYTES, 'draft')
    hints = []
    def hint(pointer, kind):
        hints.append(dict(input_pointer=pointer, kind=kind))
    def text(value):
        return isinstance(value, str) and bool(value.strip())
    if not isinstance(draft, dict):
        hint('', 'expected_object')
    else:
        for key in sorted(FIELDS-set(draft)):
            hint('/'+key, 'required_field_missing')
        for key in sorted(set(draft)-FIELDS):
            hint('/'+key.replace('~','~0').replace('/','~1'), 'unknown_field_not_a_starting_protocol')
        for key in TEXT_FIELDS:
            if key in draft and not text(draft[key]):
                hint('/'+key, 'required_nonblank_text')
        for key in CRITERIA_FIELDS:
            if key not in draft:
                continue
            values = draft[key]
            if not isinstance(values, list) or not values:
                hint('/'+key, 'required_nonempty_text_list')
            else:
                for i, value in enumerate(values):
                    if not text(value):hint('/'+key+'/'+str(i), 'required_nonblank_text')
        if 'search_plan' in draft:
            plan = draft['search_plan']
            if not isinstance(plan, list) or not plan:
                hint('/search_plan', 'required_nonempty_plan')
            else:
                seen = set()
                for i, row in enumerate(plan):
                    pointer='/search_plan/'+str(i)
                    if not isinstance(row, dict) or set(row) != set(PLAN_FIELDS):
                        hint(pointer, 'exact_four_field_plan_object_required')
                        continue
                    for key in PLAN_FIELDS:
                        if not text(row[key]):hint(pointer+'/'+key, 'required_nonblank_text')
                    if text(row['search_id']):
                        if row['search_id'] in seen:hint(pointer+'/search_id', 'duplicate_search_id')
                        seen.add(row['search_id'])
        for key in LEDGERS:
            if key in draft and draft[key] != []:
                hint('/'+key, 'must_be_empty_list_never_clear_existing_research')
    validation_error = None
    if not hints:
        try:
            fresh_base(draft)
            run(draft)
        except (ValueError, TypeError, KeyError) as error:
            validation_error = str(error)
    valid = not hints and validation_error is None
    result = dict(schema_version=1, valid=valid,
        status='VALID_STARTING_SHAPE_ONLY' if valid else 'STARTING_PROTOCOL_BLOCKED',
        missing_hints=hints, validator_error=validation_error,
        draft_sha256=hashlib.sha256(canonical_json_bytes(draft)).hexdigest(),
        hash_scope='Sorted compact supplied JSON; object key order ignored, list order retained; not authentication.',
        protocol_changed=False, boundary=BOUNDARY, engine_sha256=_hashes(), **NEGATIVE_CLAIMS)
    return result


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    draft_command=commands.add_parser('template')
    draft_command.add_argument('--draft-output',type=Path)
    check_command=commands.add_parser('check')
    check_command.add_argument('draft',type=Path)
    check_command.add_argument('--protocol-output',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='template':
            result=template();value=result['draft'];destination=args.draft_output
        else:
            value=parse_json(_read(args.draft,MAX_BYTES));result=check(value)
            destination=args.protocol_output if result['valid'] else None
        encoded=json_bytes(result)
        if len(encoded)>MAX_BYTES:raise ValueError('report exceeds byte limit')
        if destination is not None:
            output=json_bytes(value)
            if len(output)>MAX_BYTES:raise ValueError('serialized draft/protocol exceeds byte limit')
            _write_new(destination,output)
        print(encoded.decode('utf-8'),end='')
        if args.command=='check' and not result['valid']:
            raise SystemExit(2)
    except (ValueError,OSError,TypeError,KeyError,RecursionError) as error:
        parser.exit(2,'protocol scaffold: '+quoted_display(str(error))+'\n')


if __name__=='__main__':
    main()
