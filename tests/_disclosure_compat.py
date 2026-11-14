"""Remove only explicitly recorded optional disclosure additions for historical regressions."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def prior_bytes(name):
    source=(ROOT/name).read_bytes()
    additions=json.loads((ROOT/'tests/output_disclosure_source_additions.json').read_bytes())
    if name=='evidence_workflow.py':old=additions['engine_hook'].encode();new=b''
    elif name in ('adapter_integrity.py','bibliographic_integrity.py'):
        old=b"'question_records', 'output_disclosures'";new=b"'question_records'"
    elif name=='research_bundle.py':
        old=additions['bundle_summary'].encode();assert source.count(old)==1;source=source.replace(old,b'',1)
        old=b"'question_links.py', 'output_disclosure_links.py')";new=b"'question_links.py')"
    else:raise AssertionError('not an approved disclosure engine addition')
    assert source.count(old)==1
    return source.replace(old,new,1)

def prior_builder_source(module):
    import inspect
    source=inspect.getsource(module.build_bundle)
    block=json.loads((ROOT/'tests/output_disclosure_source_additions.json').read_bytes())['bundle_summary']
    assert source.count(block)==1
    return source.replace(block,'',1)
