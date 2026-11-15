"""Bound binary archive input and preflight stored entries without extraction."""
import os
import stat
import zipfile


def _read_stream(stream, limit):
    chunks, size = [], 0
    while True:
        chunk = stream.read(min(65_536, limit + 1 - size))
        if type(chunk) is not bytes:
            raise ValueError('archive input must be a binary stream')
        if not chunk:
            return b''.join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise ValueError('input exceeds size limit')


def read_bounded(source, limit):
    """Read paths or seekable binary streams from zero, preserving caller ownership/position.

    This bounds raw input bytes, not all memory/CPU spent by Python's ZIP parser.
    Streams returning partial reads are supported. No path is extracted or followed
    from an archive member name; filesystem paths are explicitly caller supplied.
    """
    if type(limit) is not int or limit < 0:
        raise ValueError('invalid input size limit')
    if isinstance(source, (str, os.PathLike)):
        with open(source, 'rb') as stream:
            return _read_stream(stream, limit)
    position = source.tell()
    try:
        source.seek(0)
        return _read_stream(source, limit)
    finally:
        source.seek(position)


def check_stored_entries(archive, allowed_names, max_total):
    """Reject unexpected metadata before payload reads; canonical comparison follows."""
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    if len(names) != len(allowed_names) or len(set(names)) != len(names) or set(names) != set(allowed_names):
        raise ValueError('unexpected, missing or duplicate archive entries')
    if sum(entry.file_size for entry in entries) > max_total:
        raise ValueError('bundle exceeds verification size limit')
    for entry in entries:
        if (entry.is_dir() or entry.flag_bits & 1 or entry.compress_type != zipfile.ZIP_STORED
                or entry.compress_size != entry.file_size or entry.create_system != 3
                or not stat.S_ISREG(entry.external_attr >> 16)):
            raise ValueError('unexpected archive path, type, encryption or compression')
    return names


def check_dynamic_stored_entries(archive, allowed, max_entries, size_check):
    """Inspect metadata only, preserving caller policies and diagnostic ordering.

    allowed and size_check are trusted implementation callbacks, not supplied code.
    Required members and full canonical/semantic replay remain the caller's job.
    """
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    if len(entries) > max_entries or len(set(names)) != len(names):
        raise ValueError('unexpected or duplicate archive entries')
    size_check(sum(entry.file_size for entry in entries))
    for entry in entries:
        if (not allowed(entry.filename) or entry.is_dir() or entry.flag_bits & 1
                or entry.compress_type != zipfile.ZIP_STORED
                or entry.compress_size != entry.file_size
                or entry.create_system != 3
                or not stat.S_ISREG(entry.external_attr >> 16)):
            raise ValueError('unexpected archive path, type, encryption or compression')
    return names
