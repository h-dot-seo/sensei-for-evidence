"""Exact declared source/display reversal for historical tests, never artifact migration."""
import ast
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def prior_bytes(name):
    raw=(ROOT/name).read_bytes()
    changes=json.loads((ROOT/'tests/native_continuation_source_changes.json').read_bytes())
    if name in changes:
        assert raw==changes[name]['new'].encode(),name
        return changes[name]['old'].encode()
    return raw


def prior_handoff_display(raw):
    """Only the named native_collection workflow boundary, not arbitrary normalization."""
    assert type(raw) is bytes
    change=json.loads((ROOT/'tests/native_continuation_source_changes.json').read_bytes())['review_handoff.py']
    values=[]
    for key in ['old','new']:
        matches=[n.value.value for n in ast.walk(ast.parse(change[key])) if isinstance(n,ast.keyword)
                 and n.arg=='boundary' and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)
                 and 'The separately declared continuation dialect' in n.value.value]
        assert len(matches)==1
        values.append(matches[0].encode())
    old,new=values
    assert old!=new and raw.count(new)<=1
    return raw.replace(new,old,1)
