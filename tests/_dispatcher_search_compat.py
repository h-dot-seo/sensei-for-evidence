"""Read the exact dispatcher preimage for source proofs predating list search."""
import hashlib
from pathlib import Path


def before_list_search(name, raw):
    if name != 'sensei.py':
        return raw
    if hashlib.sha256(raw).hexdigest() != '3f820f87e2f3c13bc53dbc77f847b5c38f435b18277164f377088e3b8e7824e3':
        raise AssertionError('dispatcher source differs from the reviewed list-search version')
    return Path(__file__).with_name('dispatcher_search_prior_source.txt').read_bytes()
