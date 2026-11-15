"""Exclusive byte output with an explicit existing-entry guard, not atomic publication."""
import errno
import hashlib
import os
from pathlib import Path


def implementation_hashes():
    return {'output_io.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def write_new(path, raw):
    """Reject existing entries, then exclusively create; failures can leave a partial file.

    Parent directories must already exist. This does not constrain parent aliases,
    prevent concurrent path replacement, provide no-follow source reading, stage an
    atomic publication, fsync durability or remove partial outputs after failure.
    """
    if type(raw) is not bytes:
        raise TypeError('exclusive output requires bytes')
    path = Path(path)
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(path))
    with path.open('xb') as output:
        output.write(raw)
