"""Verify the complete published inventory against exact checkout bytes."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
from json_io import configure_utf8_stdio, parse_json

MANIFEST = 'PUBLICATION_MANIFEST.json'
IGNORED_PARTS = {'.git', '__pycache__'}


def link_like(path):
    """Reject both symlinks and Windows reparse-point/junction paths."""
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, 'st_file_attributes', 0)
        & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))


def verify(root):
    root = Path(root).absolute()
    if any(link_like(path) for path in (root, *root.parents)) or link_like(root / MANIFEST):
        return ['publication root and manifest must not be symlinks']
    if not (root / MANIFEST).is_file():
        return ['manifest must be a regular file']
    try:
        manifest = parse_json((root / MANIFEST).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError) as error:
        return ['manifest unreadable or invalid: ' + str(error)]
    if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), list):
        return ['manifest must contain a files list']
    errors, listed, portable_names = [], set(), set()
    for row in manifest['files']:
        if not isinstance(row, dict):
            errors.append('manifest file entry must be an object')
            continue
        name = row.get('path')
        if not isinstance(name, str) or not name or '\\' in name or ':' in name or any(ord(character) < 32 or ord(character) == 127 for character in name):
            errors.append('unsafe manifest path')
            continue
        relative = PurePosixPath(name)
        if (relative.is_absolute() or '..' in relative.parts or not relative.parts
                or relative.as_posix() != name or set(relative.parts) & IGNORED_PARTS
                or name == MANIFEST):
            errors.append('unsafe manifest path')
            continue
        if name in listed:
            errors.append('duplicate manifest path: ' + name)
        if name.casefold() in portable_names:
            errors.append('case-insensitive manifest path collision: ' + name)
        listed.add(name)
        portable_names.add(name.casefold())
        if (type(row.get('bytes')) is not int or row['bytes'] < 0
                or not isinstance(row.get('sha256'), str)
                or re.fullmatch('[0-9a-f]{64}', row['sha256']) is None):
            errors.append(name + ': invalid size/hash metadata')
            continue
        candidate = root
        unsafe_link = False
        for part in relative.parts:
            candidate /= part
            if link_like(candidate):
                unsafe_link = True
                break
        if unsafe_link:
            errors.append(name + ': symlink not allowed')
            continue
        if not candidate.is_file():
            errors.append(name + (': nonregular file not allowed' if candidate.exists() else ': missing'))
            continue
        try:
            raw = candidate.read_bytes()
        except OSError as error:
            errors.append(name + ': unreadable: ' + str(error))
            continue
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            errors.append(name + ': size/hash mismatch')
    if type(manifest.get('file_count')) is not int or manifest['file_count'] != len(listed):
        errors.append('file count mismatch')
    actual = set()
    try:
        pending = [root]
        while pending:
            directory = pending.pop()
            if link_like(directory):
                errors.append(str(directory.relative_to(root)) + ': symlink not allowed')
                continue
            for path in directory.iterdir():
                relative = path.relative_to(root)
                if set(relative.parts) & IGNORED_PARTS:
                    continue
                if link_like(path):
                    errors.append(relative.as_posix() + ': symlink not allowed')
                    continue
                if path.is_dir():
                    pending.append(path)
                elif path.is_file() and relative.as_posix() != MANIFEST:
                    actual.add(relative.as_posix())
                elif relative.as_posix() != MANIFEST:
                    errors.append(relative.as_posix() + ': nonregular filesystem entry not allowed')
    except OSError as error:
        errors.append('inventory unreadable: ' + str(error))
    errors.extend(name + ': unlisted file' for name in sorted(actual - listed))
    return errors


if __name__ == '__main__':
    configure_utf8_stdio()
    errors = verify(Path(__file__).resolve().parent)
    print(json.dumps(dict(valid=not errors, errors=errors), ensure_ascii=False))
    raise SystemExit(bool(errors))
