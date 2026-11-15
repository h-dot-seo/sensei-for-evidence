"""Inspect unverified manifests of seven retained collection/transition ZIP families."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from archive_safety import check_dynamic_stored_entries, read_bounded
from json_io import configure_utf8_stdio, parse_json, quoted_display
from output_io import write_new
import collection_bundle
import batch_collection_bundle
import native_collection_bundle
import report_transition_bundle
import extraction_transition_bundle
import appraisal_transition_bundle
import work_transition_bundle

MAX_BYTES = 50_000_000
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 10_104
COLLECTION_FIXED = {'research.zip', 'bindings.json', 'summary.txt', 'manifest.json'}
TRANSITION_FIXED = {'protocols/initial.json', 'protocols/endpoint.json', 'chain.json', 'summary.txt', 'manifest.json'}
FAMILIES = {
    'explicit_native_collection_bundle': collection_bundle,
    'explicit_nbib_batch_collection_bundle': batch_collection_bundle,
    'explicit_typed_native_collection_bundle': native_collection_bundle,
    'explicit_report_transition_bundle': report_transition_bundle,
    'explicit_extraction_transition_bundle': extraction_transition_bundle,
    'explicit_appraisal_transition_bundle': appraisal_transition_bundle,
    'explicit_work_transition_bundle': work_transition_bundle,
}
BOUNDARY = ('Unverified recorded manifest navigation only. No payload SHA-256 comparison, '
    'protocol validation, derivation replay, canonical ZIP validation, source identity or authenticity '
    'check is performed. Manifest parsing includes ZIP CRC checking of that member only. '
    'Internal ZIPs, protocols, application records, bindings and source text are not opened. '
    'A matching implementation map is not a verified bundle or reviewer. Use the separately '
    'retained recorded implementation for the existing verifier; no code is loaded from this archive. '
    'No extraction, network, research action or renewal of supplied decisions occurs. '
    'Recorded manifest text may contain private information and is retained without redaction.')


def _size(size):
    if type(size) is not int or not 0 <= size <= MAX_BYTES:
        raise ValueError('archive or declared entry bytes exceed the supported limit')


def _safe_name(name):
    return name in COLLECTION_FIXED | TRANSITION_FIXED or re.fullmatch(
        r'(?:native/import-[0-9]{6}(?:\.json|/source-[0-9]{6}\.(?:nbib|ris))|applications/step-[0-9]{6}\.json)', name) is not None


def _sha(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _text(value):
    return type(value) is str and len(value) <= 4096


def _family_inventory(mode, names):
    module = FAMILIES[mode]
    if 'transition' in mode:
        fixed = TRANSITION_FIXED
        allowed = lambda name: name in fixed or re.fullmatch(r'applications/step-[0-9]{6}\.json', name) is not None
        limit = module.MAX_STEPS + len(fixed)
    else:
        fixed = COLLECTION_FIXED
        suffix = r'\.json' if module is collection_bundle else r'(?:\.json|/source-[0-9]{6}\.nbib)' if module is batch_collection_bundle else r'(?:\.json|/source-[0-9]{6}\.(?:nbib|ris))'
        allowed = lambda name: name in fixed or re.fullmatch(r'native/import-[0-9]{6}' + suffix, name) is not None
        limit = module.MAX_BINDINGS + (0 if module is collection_bundle else module.MAX_NATIVE_SOURCES) + len(fixed)
    if len(names) > limit or not fixed.issubset(names) or not all(allowed(name) for name in names):
        raise ValueError('entry inventory does not match the explicit supported family')
    return module


def _manifest(value, entries):
    if type(value) is not dict or type(value.get('schema_version')) is not int or value['schema_version'] != 1:
        raise ValueError('only exact schema1 collection/transition manifests are supported')
    mode = value.get('mode')
    if type(mode) is not str or mode not in FAMILIES:
        raise ValueError('unsupported retained bundle family; ordinary research ZIP uses its separate describer')
    module = _family_inventory(mode, set(entries))
    claims = module._claims() if 'transition' in mode else module._negative_claims()
    required = {'schema_version', 'mode', 'engine_sha256', 'files', 'boundary'} | set(claims)
    if 'transition' not in mode:required.add('input_sha256')
    if set(value) != required or not _text(value['boundary']):
        raise ValueError('manifest has unknown, missing or malformed fields')
    for name,example in claims.items():
        supplied = value[name]
        if type(supplied) is not type(example) or (type(supplied) is str and not _text(supplied)):
            raise ValueError('malformed recorded manifest assertion')
    if 'input_sha256' in value and not _sha(value['input_sha256']):
        raise ValueError('malformed recorded input hash')
    engines = value['engine_sha256']
    if type(engines) is not dict or not 1 <= len(engines) <= 512:
        raise ValueError('malformed recorded implementation map')
    for name,digest in engines.items():
        if type(name) is not str or len(name) > 128 or re.fullmatch(r'[a-z][a-z0-9_]*\.py', name) is None or not _sha(digest):
            raise ValueError('malformed recorded implementation field')
    files = value['files']
    if type(files) is not list or len(files) != len(entries)-1:
        raise ValueError('recorded file inventory differs from ZIP metadata')
    observed = set()
    for row in files:
        if type(row) is not dict or set(row) != {'path','bytes','sha256'}:
            raise ValueError('malformed recorded file row')
        name = row['path']
        if type(name) is not str or name == 'manifest.json' or name not in entries or name in observed:
            raise ValueError('duplicate or unknown recorded file path')
        _size(row['bytes'])
        if row['bytes'] != entries[name].file_size or not _sha(row['sha256']):
            raise ValueError('malformed recorded file size or hash')
        observed.add(name)
    if observed != set(entries)-{'manifest.json'}:
        raise ValueError('incomplete recorded file inventory')
    return module


def _bounded_output(result):
    raw = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
    if len(raw) > MAX_OUTPUT_BYTES:raise ValueError('descriptor exceeds output byte limit')
    return raw


def describe(raw):
    """Read only manifest.json; hashes of other payloads remain supplied assertions."""
    if type(raw) is not bytes:raise ValueError('archive input must be bytes')
    _size(len(raw))
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        # Generic safe-name/size/type/duplicate preflight precedes the only member read.
        check_dynamic_stored_entries(archive, _safe_name, MAX_ENTRIES, _size)
        if any(entry.orig_filename != entry.filename for entry in archive.infolist()):
            raise ValueError('ambiguous archive entry name')
        entries = {entry.filename:entry for entry in archive.infolist()}
        if 'manifest.json' not in entries:raise ValueError('manifest is required')
        manifest = parse_json(archive.read('manifest.json'))
        module = _manifest(manifest, entries)
    recorded = manifest['engine_sha256']
    current = module.implementation_hashes()
    differing = sorted(name for name in set(recorded)|set(current) if recorded.get(name) != current.get(name))
    root = Path(__file__).resolve().parent
    reader_hashes = {name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                     for name in ('retained_bundle_describe.py','archive_safety.py','json_io.py','output_io.py')}
    result = dict(schema_version=1, kind='retained_bundle_manifest_descriptor',
        bundle_sha256=hashlib.sha256(raw).hexdigest(), bundle_bytes=len(raw),
        hash_scope='Exact supplied ZIP bytes; not authentication, payload verification or canonical-format validation.',
        family=manifest['mode'], recorded_unverified=copy.deepcopy(manifest),
        implementation_match='DIFFERS' if differing else 'MATCH', differing_engine_files=differing,
        current_implementation_sha256=current, describer_sha256=reader_hashes,
        verification='NOT_PERFORMED', payload_hash_verification='NOT_PERFORMED',
        derivation_replay='NOT_PERFORMED', canonical_zip_verification='NOT_PERFORMED',
        verifier_command=['python',module.__name__+'.py','verify','BUNDLE.zip'],
        command_scope='Static inspection aid with a placeholder; not executed or authorized by this descriptor.',
        external_calls=0, protocol_changed=False, census_claim='NOT_ESTABLISHED',
        conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    _bounded_output(result)
    return result


def render_text(result):
    text='Retained bundle manifest (UNVERIFIED)\n'+'\n'.join(
        quoted_display(key)+': '+quoted_display(value) for key,value in result.items())+'\n'
    if len(text.encode('utf-8')) > MAX_OUTPUT_BYTES:raise ValueError('descriptor exceeds output byte limit')
    return text


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--text',action='store_true')
    parser.add_argument('--output',type=Path,help='write the JSON descriptor exclusively; never overwrite')
    args=parser.parse_args()
    try:
        result=describe(read_bounded(args.bundle,MAX_BYTES))
        raw=_bounded_output(result)
        rendered=render_text(result) if args.text else raw.decode('utf-8')
        if args.output is not None:write_new(args.output,raw)
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,RecursionError,OverflowError,zipfile.BadZipFile):
        parser.exit(1,'retained bundle descriptor error: unsupported or malformed archive/input/output; no verification performed\n')
    print(rendered,end='')


if __name__=='__main__':main()
