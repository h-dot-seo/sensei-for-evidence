"""Read recorded research-bundle context without verifying or replaying its research."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import zipfile

from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes, PAYLOADS, MAX_BUNDLE_BYTES

# The engine's limit covers entry bytes, not ZIP headers. Fixed-entry metadata is
# separately bounded here; noncanonical archives can be readable, not verified.
MAX_ARCHIVE_BYTES = MAX_BUNDLE_BYTES + 1_000_000
MAX_REPORT_BYTES = 16_000_000
BOUNDARY = ('Recorded values are unverified supplied data. No payload hash comparison, '
            'derivation replay, approval, source authentication or scientific assessment. '
            'Use the matching trusted implementation and original verifier separately.')


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def describe(raw):
    if type(raw) is not bytes or len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError('archive byte limit')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != 7 or set(names) != PAYLOADS | {'manifest.json'}:
            raise ValueError('only the seven-entry research archive is supported')
        if sum(entry.file_size for entry in entries) > MAX_BUNDLE_BYTES:
            raise ValueError('entry byte limit')
        for entry in entries:
            if (entry.is_dir() or entry.flag_bits & 1 or entry.compress_type != zipfile.ZIP_STORED
                    or entry.compress_size != entry.file_size or entry.create_system != 3
                    or not stat.S_ISREG(entry.external_attr >> 16)):
                raise ValueError('unsupported archive entry')
        manifest = parse_json(archive.read('manifest.json'))
        protocol = parse_json(archive.read('protocol.json'))
        research = parse_json(archive.read('research.json'))
    if not all(isinstance(value, dict) for value in (manifest, protocol, research)):
        raise ValueError('JSON objects required')
    if set(manifest) != {'schema_version','engine_sha256','input_sha256','files'} or type(manifest['schema_version']) is not int or manifest['schema_version'] != 2:
        raise ValueError('unsupported research manifest')
    recorded = manifest['engine_sha256']
    if not isinstance(recorded, dict) or not recorded or any(
            re.fullmatch('[A-Za-z0-9_]+\\.py', name) is None or not _digest(value)
            for name,value in recorded.items()):
        raise ValueError('invalid recorded implementation map')
    if not _digest(manifest['input_sha256']):
        raise ValueError('invalid recorded input hash')
    files = manifest['files']
    if not isinstance(files, list) or len(files) != len(PAYLOADS):
        raise ValueError('invalid manifest inventory')
    paths=[]
    for row in files:
        if (not isinstance(row, dict) or set(row) != {'path','bytes','sha256'}
                or not isinstance(row['path'], str) or type(row['bytes']) is not int
                or row['bytes'] < 0 or not _digest(row['sha256'])):
            raise ValueError('invalid manifest row')
        paths.append(row['path'])
    if set(paths) != PAYLOADS:
        raise ValueError('invalid payload names')
    if any(not isinstance(protocol.get(key),str) for key in ('question','version')):
        raise ValueError('question and version strings required')
    flow = research.get('flow')
    if flow is not None and not isinstance(flow,dict):
        raise ValueError('flow must be an object or absent')
    readiness=research.get('readiness')
    if readiness is not None and not isinstance(readiness,dict):
        raise ValueError('readiness must be an object or absent')
    gates = None if readiness is None else readiness.get('gates_sha256')
    opened = None if readiness is None else readiness.get('open_gate_ids')
    if gates is not None and not _digest(gates):
        raise ValueError('invalid recorded gates hash')
    if opened is not None and (not isinstance(opened,list) or any(not isinstance(x,str) for x in opened)):
        raise ValueError('invalid recorded gate IDs')
    current=engine_hashes()
    differing=sorted(name for name in set(recorded)|set(current) if recorded.get(name)!=current.get(name))
    return dict(schema_version=1, bundle_sha256=hashlib.sha256(raw).hexdigest(),
                describer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                manifest=dict(schema_version=2, input_sha256=manifest['input_sha256'], engine_sha256=recorded),
                protocol=dict(question=protocol['question'],version=protocol['version'],
                              protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest()),
                hash_scope='bundle_sha256 hashes supplied ZIP bytes; protocol_sha256 is computed canonical JSON, not a recorded verification result.',
                recorded_unverified=dict(flow=flow,gates_sha256=gates,open_gate_ids=opened),
                missing_value_scope='null means absent or explicitly null, never zero or no open gates.',
                implementation_match='DIFFERS' if differing else 'MATCH',differing_engine_files=differing,
                verification='NOT_PERFORMED',payload_hash_verification='NOT_PERFORMED',derivation_replay='NOT_PERFORMED',
                census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',boundary=BOUNDARY)


def render_text(result):
    return '\n'.join(['Recorded research bundle (unverified)',
        'Question: '+quoted_display(result['protocol']['question']),
        'Version: '+quoted_display(result['protocol']['version']),
        'Bundle SHA-256: '+result['bundle_sha256'],
        'Computed canonical protocol SHA-256: '+result['protocol']['protocol_sha256'],
        'Recorded values: '+quoted_display(result['recorded_unverified']),
        'Implementation: '+result['implementation_match'],
        'Differing files: '+quoted_display(result['differing_engine_files']),
        'Verification: NOT_PERFORMED', 'Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY',
        result['missing_value_scope'], result['boundary']])+'\n'


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--text',action='store_true')
    args=parser.parse_args()
    try:
        with args.bundle.open('rb') as stream:
            raw=stream.read(MAX_ARCHIVE_BYTES+1)
        result=describe(raw)
        output=render_text(result) if args.text else json.dumps(result,ensure_ascii=True,indent=2)+'\n'
        if len(output.encode('utf-8')) > MAX_REPORT_BYTES:
            raise ValueError('report byte limit')
    except (OSError,ValueError,TypeError,KeyError,RecursionError,RuntimeError,NotImplementedError,EOFError,zipfile.BadZipFile):
        parser.exit(1,'research bundle description error: "Unable to describe this input within the supported archive and JSON bounds."\n')
    print(output,end='')


if __name__=='__main__':main()
