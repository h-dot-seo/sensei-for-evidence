"""Reverse only the exact recorded CLI input reads, not arbitrary source differences."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def prior_bytes(name):
    source=(ROOT/name).read_bytes()
    changes=json.loads((ROOT/'tests/cli_input_source_changes.json').read_bytes())
    for old,new in reversed(changes.get(name,[])):
        old,new=old.encode(),new.encode()
        assert source.count(new)==1,(name,new)
        source=source.replace(new,old,1)
    return source
