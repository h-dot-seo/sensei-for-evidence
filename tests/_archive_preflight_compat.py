"""Reverse only recorded shared-preflight additions and fixed fictional target fields."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prior_bytes(name):
    source=(ROOT/name).read_bytes()
    changes=json.loads((ROOT/'tests/archive_preflight_source_changes.json').read_bytes())
    for old,new in reversed(changes.get(name,[])):
        old,new=old.encode(),new.encode();assert source.count(new)==1,(name,new)
        source=source.replace(new,old,1)
    return source

def prior_fixture_bytes(name):
    source=(ROOT/name).read_bytes()
    changes=json.loads((ROOT/'tests/archive_preflight_fixture_changes.json').read_bytes())
    for row in changes:
        if row['path']!=name:continue
        old,new=row['old'].encode(),row['new'].encode();assert source.count(new)==1
        source=source.replace(new,old,1)
    return source
