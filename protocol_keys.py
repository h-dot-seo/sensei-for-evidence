"""List declared protocol-root fields or report names outside that inventory, without values."""
import argparse
import hashlib
import json
from pathlib import Path

from json_io import configure_utf8_stdio, parse_json, quoted_display

MAX_BYTES = 50_000_000
KNOWN_TOP_LEVEL_KEYS = (
    'adapter_receipts', 'appraisals', 'bibliographic_imports', 'challenges', 'contexts',
    'evidence', 'exclusion_criteria', 'experimental_units', 'gaps', 'inclusion_criteria',
    'planning_decisions', 'question', 'readiness_assertions', 'report_reviews',
    'report_sources', 'report_study_inventory', 'report_study_inventory_reviews',
    'report_study_reviews', 'reports', 'screening', 'screening_decision_history',
    'screening_reviews', 'search_plan', 'searches', 'synthesis_statements', 'version',
)
BOUNDARY = (
    'Names-only protocol-root field inventory, not schema or research validation. '
    'Known means declared as a protocol field in this checkout, not required, accepted '
    'in every workflow, correctly populated or scientifically appropriate. Unknown '
    'names are reported, never rejected, renamed, corrected or treated as an inferred '
    'typo. No fuzzy suggestions or gate/queue decisions. Generic hashing/comparison '
    'may still retain fields outside this inventory. Nested keys and values are not '
    'reported or validated; no protocol digest is emitted. Caller selects a protocol '
    'object, not a candidate, review, detached application or legacy agent-state file. '
    'Input names themselves may be private: this is not anonymization. No data is '
    'changed, no scripts are executed, no output files are created and no network is used.'
)


def _common():
    root=Path(__file__).resolve().parent
    return dict(schema_version=1, status='KEY_INVENTORY_ONLY', boundary=BOUNDARY,
        inventory_scope='DECLARED_PROTOCOL_ROOT_FIELDS_THIS_CHECKOUT',
        schema_validation='NOT_PERFORMED', typo_detection='NOT_PERFORMED',
        value_inspection='NOT_PERFORMED', protocol_changed=False, external_calls=0,
        census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY',
        implementation_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                               for name in ('protocol_keys.py','json_io.py')})


def inventory():
    return dict(_common(), known_top_level_keys=list(KNOWN_TOP_LEVEL_KEYS))


def inspect_keys(document):
    if type(document) is not dict or any(type(key) is not str for key in document):
        raise ValueError('input must be a JSON object with string keys')
    # Deliberately do not iterate, validate, serialize, hash or include any value.
    names=set(document)
    known=set(KNOWN_TOP_LEVEL_KEYS)
    return dict(_common(), recognized_top_level_keys=sorted(names & known),
                unrecognized_top_level_keys=sorted(names-known))


def render_text(result):
    lines=['Protocol root key inventory only']
    for field in ('known_top_level_keys','recognized_top_level_keys','unrecognized_top_level_keys'):
        if field in result:
            lines.append(field+': '+quoted_display(result[field]))
    lines.extend(['No schema validation or typo judgement; no values or protocol digest.',
                  'Census: NOT_ESTABLISHED; conclusion: NOT_READY.',result['boundary']])
    return '\n'.join(lines)+'\n'


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    listing=commands.add_parser('list');listing.add_argument('--text',action='store_true')
    inspecting=commands.add_parser('inspect');inspecting.add_argument('protocol',type=Path)
    inspecting.add_argument('--text',action='store_true')
    args=parser.parse_args()
    try:
        if args.command=='list':
            result=inventory()
        else:
            with args.protocol.open('rb') as stream:
                raw=stream.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError('input exceeds byte limit')
            result=inspect_keys(parse_json(raw))
        # ASCII JSON also visibly escapes control/format characters in supplied names.
        encoded=json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n'
        rendered=render_text(result) if args.text else encoded
        if len(rendered.encode('utf-8'))>MAX_BYTES:raise ValueError('report exceeds byte limit')
    except (ValueError,OSError,TypeError,RecursionError):
        # Do not echo parser fragments, paths or values in an error message.
        parser.exit(2,'protocol keys: cannot inspect bounded strict UTF-8 JSON object or render inventory\n')
    print(rendered,end='')


if __name__=='__main__':
    main()
