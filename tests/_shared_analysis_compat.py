"""Reverse exactly four recorded non-engine same-call projection changes for tests."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def prior_bytes(name):
    from tests._amendment_compat import prior_bytes as pre_amendment
    raw=pre_amendment(name)
    changes=json.loads((ROOT/'tests/shared_analysis_source_changes.json').read_bytes())
    if name in changes:
        assert raw==changes[name]['new'].encode(),name
        return changes[name]['old'].encode()
    return raw
