"""Exact approved CI-budget reversal for historical byte proofs, not a runtime change."""
import hashlib

OLD_SHA256 = 'e319eb63977085cf15c2adcb7641c730c7b09b4030dc11fa457b49c29c9f0ebe'
NEW_SHA256 = '1a4ebfe91bf7dcbc45ba11de26f481f553d498df2221b7aedb16b6a14c93f528'


def prior_workflow_bytes(raw):
    assert type(raw) is bytes
    assert hashlib.sha256(raw).hexdigest() == NEW_SHA256
    assert raw.count(b'    timeout-minutes: 20\n') == 1
    restored = raw.replace(b'    timeout-minutes: 20\n', b'    timeout-minutes: 10\n', 1)
    assert hashlib.sha256(restored).hexdigest() == OLD_SHA256
    return restored
