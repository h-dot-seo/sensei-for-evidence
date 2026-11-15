"""Reverse only the exact approved amendment source additions and fictional hashes."""
import ast
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prior_bytes(name):
    from tests._native_archive_compat import prior_bytes as pre_native_archive
    raw=pre_native_archive(name)
    changes=json.loads((ROOT/'tests/amendment_source_changes.json').read_bytes())
    if name in changes:
        assert raw==changes[name]['new'].encode(),name
        return changes[name]['old'].encode()
    return raw

def prior_fixture_bytes(name):
    raw=(ROOT/name).read_bytes()
    changes=json.loads((ROOT/'tests/amendment_fixture_changes.json').read_bytes())
    for row in changes:
        if row['path']==name:
            old,new=row['old'].encode(),row['new'].encode();assert raw.count(new)==1,name
            raw=raw.replace(new,old,1)
    return raw

def prior_builder_source():
    source=prior_bytes('research_bundle.py').decode()
    tree=ast.parse(source)
    return ast.get_source_segment(source,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_bundle'))+'\n'
