"""Inspect recorded implementation hashes without executing or verifying an artifact."""
import argparse
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import stat
import zipfile
import zlib
from json_io import configure_utf8_stdio, parse_json, quoted_display
from verify_manifest import link_like

ROOT = Path(__file__).resolve().parent
MAX_INPUT_BYTES = 50_000_000
MAX_JSON_BYTES = 5_000_000
MAX_SOURCE_BYTES = 5_000_000
MAX_NODES = 100_000
MAX_HASHES = 10_000
NAME = re.compile(r'[A-Za-z0-9_]+\.py\Z')
HASH = re.compile(r'[0-9a-f]{64}\Z')
BOUNDARY = ('MATCH means byte identity of recorded files only, not artifact verification, '
            'authentication, release provenance or a signature. Unhashed imports are not covered. '
            'No code from the selected directory is executed, no files are written, and no '
            'network or model call or scientific judgement is made. Input drift is not checked. '
            'Census is NOT_ESTABLISHED; conclusion readiness is NOT_READY.')


def read_bounded(path, limit):
    path = Path(path).absolute()
    if any(link_like(p) for p in (path, *path.parents)):
        raise ValueError('link-like input paths are not allowed')
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('input must be a regular file')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('input exceeds byte limit')
    return raw


def artifact_json(path):
    raw = read_bounded(path, MAX_INPUT_BYTES)
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_NODES:
                raise ValueError('archive has too many entries')
            manifests = [entry for entry in entries if entry.filename == 'manifest.json']
            if len(manifests) != 1:
                raise ValueError('archive must have exactly one top-level manifest.json')
            entry = manifests[0]
            if entry.file_size > MAX_JSON_BYTES or entry.flag_bits & 1:
                raise ValueError('archive manifest is oversized or encrypted')
            try:
                with archive.open(entry) as stream:
                    raw = stream.read(MAX_JSON_BYTES + 1)
            except (zlib.error, lzma.LZMAError):
                raise ValueError('archive manifest cannot be decompressed') from None
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError('JSON exceeds byte limit')
    value = parse_json(raw)
    if not isinstance(value, (dict, list)):
        raise ValueError('artifact must contain a JSON object or array')
    return value


def pointer_part(value):
    return str(value).replace('~', '~0').replace('/', '~1')


def recorded_hashes(value):
    """Yield every recognized declaration, including malformed declarations as INVALID."""
    pending = [(value, '', None)]
    rows = []
    visited = 0
    while pending:
        node, pointer, parent = pending.pop()
        visited += 1
        if visited > MAX_NODES:
            raise ValueError('JSON node limit exceeded')
        if isinstance(node, dict):
            for key, child in node.items():
                location = pointer + '/' + pointer_part(key)
                if key in ('engine_sha256', 'implementation_sha256'):
                    if not isinstance(child, dict) or not child:
                        rows.append(dict(pointer=location, file=None, recorded_sha256=None, status='INVALID'))
                    else:
                        for name, digest in child.items():
                            valid = bool(NAME.fullmatch(name)) and isinstance(digest, str) and bool(HASH.fullmatch(digest))
                            rows.append(dict(pointer=location + '/' + pointer_part(name), file=name,
                                             recorded_sha256=digest if isinstance(digest, str) else None,
                                             status='UNCHECKED' if valid else 'INVALID'))
                elif key == 'adapter_engine_sha256' and parent == 'adapter_receipts':
                    valid = isinstance(child, str) and bool(HASH.fullmatch(child))
                    rows.append(dict(pointer=location, file='offline_adapter.py',
                                     recorded_sha256=child if isinstance(child, str) else None,
                                     status='UNCHECKED' if valid else 'INVALID'))
                else:
                    pending.append((child, location, key))
        elif isinstance(node, list):
            pending.extend((child, pointer + '/' + str(index), parent) for index, child in enumerate(node))
        if len(rows) > MAX_HASHES:
            raise ValueError('recorded hash limit exceeded')
    return sorted(rows, key=lambda row: row['pointer'])


def manifest_match(path, rows):
    result = dict(manifest=str(path), status='INVALID', release=None, date=None)
    try:
        value = parse_json(read_bounded(path, MAX_JSON_BYTES))
        if not isinstance(value, dict) or not isinstance(value.get('files'), list):
            return result
        if not isinstance(value.get('release'), str) or not isinstance(value.get('date'), str):
            return result
        files = {}
        for item in value['files']:
            if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                    or not isinstance(item.get('sha256'), str) or not HASH.fullmatch(item['sha256'])
                    or item['path'] in files):
                return result
            files[item['path']] = item['sha256']
        matches = bool(rows) and all(isinstance(row['file'], str) and NAME.fullmatch(row['file'])
                    and isinstance(row['recorded_sha256'], str) and HASH.fullmatch(row['recorded_sha256'])
                    and files.get(row['file']) == row['recorded_sha256'] for row in rows)
        result.update(status='MATCH' if matches else 'DIFFERS',
                      release=value['release'], date=value['date'])
    except (OSError, ValueError, RecursionError):
        pass
    return result


def inspect_artifact(artifact, engine_root=ROOT, manifests=()):
    rows = recorded_hashes(artifact_json(artifact))
    root = Path(engine_root).absolute()
    if any(link_like(p) for p in (root, *root.parents)) or not root.is_dir():
        raise ValueError('engine root must be a regular non-link directory')
    cache = {}
    for row in rows:
        row['current_sha256'] = None
        if row['status'] == 'INVALID':
            continue
        name = row['file']
        if name not in cache:
            try:
                cache[name] = ('READ', hashlib.sha256(read_bounded(root / name, MAX_SOURCE_BYTES)).hexdigest())
            except FileNotFoundError:
                cache[name] = ('MISSING', None)
            except (OSError, ValueError):
                cache[name] = ('INVALID', None)
        state, digest = cache[name]
        row['current_sha256'] = digest
        row['status'] = ('MATCH' if digest == row['recorded_sha256'] else 'DIFFERS') if state == 'READ' else state
    status = ('INVALID' if any(row['status'] == 'INVALID' for row in rows) else
              'NO_HASHES' if not rows else 'MATCH' if all(row['status'] == 'MATCH' for row in rows) else 'DIFFERS')
    names = {row['file'] for row in rows if row['status'] != 'INVALID'}
    catalog = read_bounded(ROOT / 'docs/COMMANDS.md', MAX_JSON_BYTES).decode('utf-8')
    hints = [usage for usage in re.findall(r'`(python [^`]+)`', catalog)
             if len(usage.split()) > 2 and usage.split()[1] in names and usage.split()[2] == 'verify']
    return dict(schema_version=1, mode='implementation_check', status=status, files=rows,
                candidate_verify_usage=hints,
                manifests=[manifest_match(path, rows) for path in manifests],
                checker_sha256=hashlib.sha256(read_bounded(Path(__file__), MAX_SOURCE_BYTES)).hexdigest(),
                next_step='Read docs/COMMANDS.md for the artifact-specific verify command and required inputs. '
                          'Run it separately from a trusted matching implementation directory; this inspector does not replay it.',
                boundary=BOUNDARY, census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')


def main(argv=None):
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('inspect')
    command.add_argument('artifact')
    command.add_argument('--engine-root', default=str(ROOT))
    command.add_argument('--manifest', action='append', default=[])
    command.add_argument('--text', action='store_true')
    args = parser.parse_args(argv)
    try:
        report = inspect_artifact(args.artifact, args.engine_root, args.manifest)
    except (OSError, ValueError, RecursionError, zipfile.BadZipFile, RuntimeError, NotImplementedError):
        report = dict(status='INVALID', error='Input unreadable, malformed or outside inspection limits.',
                      boundary=BOUNDARY, census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')
    if args.text:
        for key, value in report.items():
            print(key + ': ' + quoted_display(value))
    else:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return int(report['status'] != 'MATCH')


if __name__ == '__main__':
    raise SystemExit(main())
