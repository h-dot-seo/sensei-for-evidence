"""Exact reversal of the recorded first-stage CLI presentation/hash additions."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prior_bytes(name):
    raw=(ROOT/name).read_bytes()
    changes=json.loads((ROOT/'tests/cli_error_source_changes.json').read_bytes())
    if name in changes:
        assert raw==changes[name]['new'].encode(), name
        return changes[name]['old'].encode()
    return raw

def prior_fixture_bytes(name):
    raw=(ROOT/name).read_bytes()
    proof=ROOT/'tests/cli_error_fixture_changes.json'
    changes=json.loads(proof.read_bytes()) if proof.exists() else []
    for row in changes:
        if row['path']==name:
            old,new=row['old'].encode(),row['new'].encode()
            assert raw.count(new)==1,name
            raw=raw.replace(new,old,1)
    return raw
