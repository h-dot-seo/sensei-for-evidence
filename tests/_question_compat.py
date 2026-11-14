"""Exact named optional question additions; never replace historical baseline data."""
import hashlib
import inspect
from tests._disclosure_compat import prior_bytes, prior_builder_source as pre_disclosure_builder_source
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def prior_builder_source(module):
    block=json.loads((ROOT/'tests/question_source_additions.json').read_bytes())['bundle_summary']
    source=pre_disclosure_builder_source(module)
    assert source.count(block)==1
    return source.replace(block,'',1)

def prior_workflow_bytes():
    block=json.loads((ROOT/'tests/question_source_additions.json').read_bytes())['engine_hook'].encode()
    source=prior_bytes('evidence_workflow.py')
    assert source.count(block)==1
    return source.replace(block,b'',1)
