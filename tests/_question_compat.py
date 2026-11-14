"""Exact named optional question additions; never replace historical baseline data."""
import hashlib
import inspect
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def prior_builder_source(module):
    block=json.loads((ROOT/'tests/question_source_additions.json').read_bytes())['bundle_summary']
    source=inspect.getsource(module.build_bundle)
    assert source.count(block)==1
    return source.replace(block,'',1)

def prior_workflow_bytes():
    block=json.loads((ROOT/'tests/question_source_additions.json').read_bytes())['engine_hook'].encode()
    source=(ROOT/'evidence_workflow.py').read_bytes()
    assert source.count(block)==1
    return source.replace(block,b'',1)
