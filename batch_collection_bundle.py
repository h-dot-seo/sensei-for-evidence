"""Portable batch-native collection ZIP with exact historical import associations.

Verification compares the entire canonical ZIP, not merely editable hashes.
Re-zipping, including changing archive metadata, invalidates this byte receipt.
No archive is extracted and no network or locator resolution is performed.
"""
import argparse
import hashlib
import io
import re
import stat
import zipfile
from pathlib import Path

import bibliographic_intake
import nbib_intake
import nbib_batch_intake
import research_bundle
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow

MAX_BUNDLE_BYTES = 50_000_000
MAX_BINDINGS = 100
MAX_NATIVE_SOURCES = 10_000
ENGINE_FILES = tuple(sorted(set(research_bundle.ENGINE_FILES) |
    set(nbib_batch_intake.implementation_hashes()) | {'batch_collection_bundle.py'}))
BOUNDARY = (
    'Internal byte consistency and exact explicit ledger association only. '
    'Coverage counts describe supplied batch wrappers and source occurrences, not literature or search completeness. '
    'Uncovered imports may be CSV, single-file native, or unsupplied batch imports; format is not inferred. '
    'No source authenticity, human authenticity, publication identity, search completeness, '
    'PRISMA compliance or scientific/clinical validity is established. '
    'No review is performed or renewed, and no protocol or scientific decision is changed. '
    'Batch wrapper JSON is normalized; every exact original UTF-8 NBIB file is separately retained at a generated archive path. '
    'Exact protocol bytes and the unchanged ordinary research ZIP are retained. Duplicate source bytes and repeated identifiers are not removed. '
    'Re-zipping or changing ZIP metadata invalidates this canonical byte receipt. '
    'Supplied private text is retained without redaction; keep real inputs and outputs outside the public repository.'
)


def _negative_claims():
    return dict(review_status='NOT_PERFORMED', search_completion='NOT_ESTABLISHED',
        source_authenticity='NOT_VERIFIED', human_authenticity='NOT_VERIFIED',
        record_identity_verification='NOT_ESTABLISHED', external_calls=0,
        protocol_changed=False, census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return {name: _sha((root / name).read_bytes()) for name in ENGINE_FILES}


def _json_bytes(value):
    nbib_intake._strict_json(value)
    raw = research_bundle.json_bytes(value)
    _size(len(raw))
    return raw


def _size(size):
    if size > MAX_BUNDLE_BYTES:
        raise ValueError('batch collection bundle exceeds size limit')


def _archive_size(payloads):
    # Stored ZIP, ASCII derived paths, no extras/comments/ZIP64 at this limit.
    return 22 + sum(len(raw) + 76 + 2 * len(name.encode('ascii'))
                    for name, raw in payloads.items())


def _add(payloads, name, raw):
    _size(sum(map(len, payloads.values())) + len(raw))
    payloads[name] = raw
    _size(_archive_size(payloads))


def _selection(bindings):
    if type(bindings) is not list or not 1 <= len(bindings) <= MAX_BINDINGS:
        raise ValueError('bindings require between 1 and 100 explicit selections')
    selected = {}
    for binding in bindings:
        if type(binding) is not dict or set(binding) != {'import_index', 'nbib_batch_artifact'}:
            raise ValueError('binding requires exactly import_index and nbib_batch_artifact')
        index = binding['import_index']
        if type(index) is not int or index < 0 or index in selected:
            raise ValueError('import_index must be a unique nonnegative integer')
        if type(binding['nbib_batch_artifact']) is not dict:
            raise ValueError('nbib_batch_artifact must be an object')
        selected[index] = binding['nbib_batch_artifact']
    return selected


def _summary(bindings, raw=None, files=None):
    result = dict(schema_version=1, valid=True,
        total_imports=len(bindings['imports']),
        bound_batch_wrappers=len(bindings['covered_import_indices']),
        bound_native_sources=sum(len(row.get('native_sources', [])) for row in bindings['imports']),
        covered_import_indices=list(bindings['covered_import_indices']),
        uncovered_import_indices=list(bindings['uncovered_import_indices']),
        verification_scope='Exact canonical archive bytes, retained artifacts and explicit CSV-ledger association; not authentication or acceptance',
        **_negative_claims(), boundary=BOUNDARY)
    if raw is not None:
        result.update(bytes=len(raw), sha256=_sha(raw), files=files)
    return result


def render_text(result):
    return ('Batch collection bundle internal byte/derivation consistency: true\n'
        'Total supplied imports: ' + str(result['total_imports']) + '\n'
        'Bound batch wrappers: ' + str(result['bound_batch_wrappers']) + '\n'
        'Bound original source occurrences: ' + str(result['bound_native_sources']) + '\n'
        'Covered import indices: ' + quoted_display(result['covered_import_indices']) + '\n'
        'Uncovered import indices: ' + quoted_display(result['uncovered_import_indices']) + '\n'
        'External calls: 0\nCensus: NOT_ESTABLISHED\nConclusion: NOT_READY\n' + BOUNDARY + '\n')


def build_bundle(protocol_raw, bindings):
    """Bind exact selected historical CSV intakes, never infer a native format."""
    if type(protocol_raw) is not bytes:
        raise ValueError('protocol_raw must be bytes')
    _size(len(protocol_raw))
    selected = _selection(bindings)
    protocol = parse_json(protocol_raw)
    if type(protocol) is not dict or 'bibliographic_imports' not in protocol:
        raise ValueError('protocol requires a valid bibliographic_imports ledger')
    nbib_intake._strict_json(protocol)
    # Preflight retained components before expensive regenerated nested outputs.
    payloads = {}
    for index, artifact in sorted(selected.items()):
        _add(payloads, 'native/import-%06d.json' % index, _json_bytes(artifact))
    _size(_archive_size(payloads) + len(protocol_raw))
    run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    ledger = protocol['bibliographic_imports']
    entries = ledger['imports']
    if any(index >= len(entries) for index in selected):
        raise ValueError('selected import_index does not exist')
    rows = []
    native_count = 0
    for index, entry in enumerate(entries):
        intake = dict(entry['intake'], protocol_snapshot=ledger['base_protocol'])
        row = dict(import_index=index, receipt_sha256=entry['sha256'],
            canonical_intake_sha256=_sha(canonical_json_bytes(intake)),
            search_id=intake['search_request']['search_id'],
            status='NO_BATCH_WRAPPER_SUPPLIED', **_negative_claims())
        if index in selected:
            artifact = selected[index]
            nbib_batch_intake.verify(artifact)
            if canonical_json_bytes(artifact['csv_intake']) != canonical_json_bytes(intake):
                raise ValueError('batch wrapper CSV intake differs from selected ledger import')
            native_count += len(artifact['source_exports'])
            if native_count > MAX_NATIVE_SOURCES:
                raise ValueError('too many retained native source occurrences')
            sources = []
            for source in artifact['source_exports']:
                source_index = source['source_index']
                name = 'native/import-%06d/source-%06d.nbib' % (index, source_index)
                native = source['source_export']
                _add(payloads, name, native['text'].encode('utf-8'))
                sources.append(dict(source_index=source_index, source_id=source['source_id'],
                    native_export_sha256=native['sha256'], native_export_bytes=native['bytes'],
                    record_rows=len(source['parsed_export']['records']), native_archive_path=name))
            row.update(status='NBIB_BATCH_WRAPPER_BOUND',
                canonical_wrapper_sha256=_sha(canonical_json_bytes(artifact)),
                native_sources=sources,
                source_count=len(sources), record_rows=artifact['source_grouping']['recorded_occurrences'],
                wrapper_archive_path='native/import-%06d.json' % index)
        rows.append(row)
    binding_document = dict(schema_version=1, imports=rows,
        covered_import_indices=sorted(selected),
        uncovered_import_indices=[i for i in range(len(entries)) if i not in selected],
        **_negative_claims(), boundary=BOUNDARY)
    _add(payloads, 'bindings.json', _json_bytes(binding_document))
    _add(payloads, 'summary.txt', render_text(_summary(binding_document)).encode('utf-8'))
    _size(_archive_size(payloads) + len(protocol_raw))
    _add(payloads, 'research.zip', research_bundle.build_bundle(protocol_raw))
    manifest = dict(schema_version=1, mode='explicit_nbib_batch_collection_bundle',
        engine_sha256=implementation_hashes(), input_sha256=_sha(protocol_raw),
        files=[dict(path=name, bytes=len(raw), sha256=_sha(raw))
               for name, raw in sorted(payloads.items())],
        **_negative_claims(), boundary=BOUNDARY)
    _add(payloads, 'manifest.json', _json_bytes(manifest))
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(payloads.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            archive.writestr(entry, raw)
    result = output.getvalue()
    _size(len(result))
    return result


def _check_entries(archive, allowed, max_entries):
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    if len(entries) > max_entries or len(set(names)) != len(names):
        raise ValueError('unexpected or duplicate archive entries')
    _size(sum(entry.file_size for entry in entries))
    for entry in entries:
        if (not allowed(entry.filename) or entry.is_dir() or entry.flag_bits & 1
                or entry.compress_type != zipfile.ZIP_STORED
                or entry.compress_size != entry.file_size
                or entry.create_system != 3
                or not stat.S_ISREG(entry.external_attr >> 16)):
            raise ValueError('unexpected archive path, type, encryption or compression')
    return names


def verify_bundle(raw):
    """Verify without extraction; re-serialization or re-zipping is not accepted."""
    if type(raw) is not bytes:
        raise ValueError('bundle input must be bytes')
    _size(len(raw))
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            fixed = {'research.zip', 'bindings.json', 'summary.txt', 'manifest.json'}
            names = _check_entries(archive, lambda name: name in fixed or
                re.fullmatch(r'native/import-[0-9]{6}(?:\.json|/source-[0-9]{6}\.nbib)', name) is not None,
                MAX_BINDINGS + MAX_NATIVE_SOURCES + 4)
            if not fixed.issubset(names):
                raise ValueError('missing batch collection archive entries')
            # Strict JSON decoding rejects duplicate keys and invalid UTF-8 too.
            manifest = parse_json(archive.read('manifest.json'))
            binding_document = parse_json(archive.read('bindings.json'))
            if type(manifest) is not dict or type(binding_document) is not dict:
                raise ValueError('manifest and bindings must be objects')
            if manifest.get('engine_sha256') != implementation_hashes():
                raise ValueError('batch collection implementation bytes differ; use the recorded implementation')
            rows = binding_document.get('imports')
            if type(rows) is not list or not 1 <= len(rows) <= 100:
                raise ValueError('invalid binding import rows')
            selections = []
            declared_sources = set()
            for index, row in enumerate(rows):
                if type(row) is not dict or type(row.get('import_index')) is not int or row['import_index'] != index:
                    raise ValueError('binding import rows must have consecutive explicit indices')
                if row.get('status') == 'NBIB_BATCH_WRAPPER_BOUND':
                    name = 'native/import-%06d.json' % index
                    if row.get('wrapper_archive_path') != name or name not in names:
                        raise ValueError('invalid derived native wrapper archive path')
                    sources = row.get('native_sources')
                    if type(sources) is not list or not 1 <= len(sources) <= nbib_batch_intake.MAX_SOURCES:
                        raise ValueError('invalid bound native source list')
                    for source_index, source in enumerate(sources):
                        source_name = 'native/import-%06d/source-%06d.nbib' % (index, source_index)
                        if (type(source) is not dict or type(source.get('source_index')) is not int
                                or source['source_index'] != source_index
                                or source.get('native_archive_path') != source_name or source_name not in names):
                            raise ValueError('invalid consecutive native source index or derived archive path')
                        declared_sources.add(source_name)
                    selections.append(dict(import_index=index, nbib_batch_artifact=parse_json(archive.read(name))))
                elif row.get('status') != 'NO_BATCH_WRAPPER_SUPPLIED':
                    raise ValueError('invalid native wrapper status')
            _selection(selections)
            actual_sources = {name for name in names if name.endswith('.nbib')}
            if actual_sources != declared_sources or len(declared_sources) > MAX_NATIVE_SOURCES:
                raise ValueError('native source entries differ from explicit bindings')
            research_raw = archive.read('research.zip')
            _size(len(research_raw))
            with zipfile.ZipFile(io.BytesIO(research_raw)) as nested:
                expected_names = research_bundle.PAYLOADS | {'manifest.json'}
                nested_names = _check_entries(nested, lambda name: name in expected_names, len(expected_names))
                if set(nested_names) != expected_names:
                    raise ValueError('invalid ordinary research archive entries')
                protocol_raw = nested.read('protocol.json')
            research_bundle.verify(io.BytesIO(research_raw))
            expected = build_bundle(protocol_raw, selections)
            if raw != expected:
                raise ValueError('batch collection archive differs from canonical regenerated bytes')
            return _summary(binding_document, raw, len(names))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError, EOFError) as error:
        raise ValueError('invalid batch collection ZIP: ' + str(error)) from error


def _built_summary(raw):
    # Only used with our freshly built bytes; avoids another expensive rebuild.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return _summary(parse_json(archive.read('bindings.json')), raw, len(archive.infolist()))


def create(protocol_path, destination, bindings):
    raw = build_bundle(bibliographic_intake.read_bounded(Path(protocol_path), MAX_BUNDLE_BYTES), bindings)
    result = _built_summary(raw)
    _json_bytes(result)
    _write_new(Path(destination), raw)
    return result


def _write_new(path, raw):
    """Use the batch intake's final-entry inspection and exclusive creation guard."""
    nbib_batch_intake._write_new(path, raw)


def _cli_binding(value):
    index, separator, path = value.partition('=')
    if not separator or not path or re.fullmatch(r'[0-9]+', index) is None:
        raise ValueError('--batch requires ASCII decimal INDEX=PATH')
    return dict(import_index=int(index), nbib_batch_artifact=parse_json(
        bibliographic_intake.read_bounded(Path(path), min(MAX_BUNDLE_BYTES, nbib_batch_intake.MAX_ARTIFACT_BYTES))))


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('create')
    make.add_argument('protocol', type=Path)
    make.add_argument('output', type=Path)
    make.add_argument('--batch', action='append', required=True, metavar='INDEX=PATH')
    make.add_argument('--text', action='store_true')
    check = commands.add_parser('verify')
    check.add_argument('bundle', type=Path)
    check.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        output = None
        if args.command == 'create':
            if len(args.batch) > MAX_BINDINGS:
                raise ValueError('too many native wrapper bindings')
            bindings = []
            retained_bytes = 0
            for value in args.batch:
                binding = _cli_binding(value)
                retained_bytes += len(_json_bytes(binding['nbib_batch_artifact']))
                _size(retained_bytes)
                bindings.append(binding)
            output = build_bundle(bibliographic_intake.read_bounded(args.protocol, MAX_BUNDLE_BYTES), bindings)
            result = _built_summary(output)
        else:
            result = verify_bundle(bibliographic_intake.read_bounded(args.bundle, MAX_BUNDLE_BYTES))
        stdout = render_text(result).encode('utf-8') if args.text else _json_bytes(result)
        _size(len(stdout))
        if output is not None:
            _write_new(args.output, output)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError,
            zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError, EOFError) as error:
        parser.exit(1, 'Batch collection bundle error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
