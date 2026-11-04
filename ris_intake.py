"""Prepare a lossless strict-subset RIS wrapper around unreviewed CSV intake.

Retain this wrapper for full-file, separator and BOM provenance. Ordinary CSV
review/audit preserves native record text and fields, but the unchanged core sees
a CSV derivative and cannot independently verify this native wrapper.
"""
import argparse
import copy
import csv
import errno
import hashlib
import io
import json
import math
from pathlib import Path

import bibliographic_intake
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from ris_export_parser import MAX_EXPORT_BYTES, parse_export
from prisma_reports import report_flow

MAX_ARTIFACT_BYTES = 50_000_000
HEADERS = ('record_id', 'source_locator', 'ris_occurrence_id',
           'ris_original_export_sha256', 'ris_record_type', 'ris_record_span_json',
           'ris_fields_json', 'ris_record_text')
BOUNDARY = (
    'Local unreviewed preparation for the documented fixed-column UTF-8 RIS subset, not universal RIS compatibility. '
    'No network retrieval, origin authentication, human authentication, publication identity verification or search completeness is established. '
    'Generated IDs and locators identify a native file occurrence only, not a publication, DOI, database ID, URL or stable cross-file identity. '
    'All repeated tags and record occurrences remain ordered and separate; no DOI, title, accession, ID or URL is selected or merged. '
    'URL and attachment fields are inert text, never opened. The unchanged core sees a CSV derivative, not native RIS. '
    'Retain this wrapper for exact full-file, separator and BOM provenance; ordinary review/bundles do not independently verify it. '
    'Existing NBIB collection archives do not accept RIS wrappers. '
    'No protocol, search, screening decision, report, study or evidence is created or changed. '
    'Supplied text is retained without redaction; store real exports and outputs outside the public repository.'
)


def _strict_json(value):
    """Reject Python-only containers, keys, numbers and coercible scalar types."""
    pending = [(value, False)]
    active = set()
    while pending:
        item, leaving = pending.pop()
        kind = type(item)
        if leaving:
            active.remove(id(item))
            continue
        if kind in (dict, list):
            if id(item) in active:
                raise ValueError('JSON containers must not be cyclic')
            active.add(id(item))
            pending.append((item, True))
        if kind is dict:
            if any(type(key) is not str for key in item):
                raise ValueError('JSON object keys must be strings')
            pending.extend((child, False) for child in item.keys())
            pending.extend((child, False) for child in item.values())
        elif kind is list:
            pending.extend((child, False) for child in item)
        elif kind is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise ValueError('JSON strings must not contain unpaired surrogates')
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError('JSON numbers must be finite')
        elif kind not in (int, bool, type(None)):
            raise ValueError('value is not a strict JSON type')


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return dict(bibliographic_intake.implementation_hashes(), **{
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ('ris_export_parser.py', 'ris_intake.py')})


def artifact_bytes(artifact):
    _strict_json(artifact)
    raw = (json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError('RIS artifact or output exceeds size limit')
    return raw


def _csv_bytes(parsed, original_sha256):
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow(HEADERS)
    for row in parsed['records']:
        occurrence = original_sha256 + ':' + row['candidate_id']
        writer.writerow(['ris-occurrence:' + occurrence,
            'supplied-ris-sha256:' + original_sha256 + '#' + row['candidate_id'],
            row['candidate_id'], original_sha256, row['record_type'],
            canonical_json_bytes(row['source_span']).decode('utf-8'),
            canonical_json_bytes(row['fields']).decode('utf-8'), row['raw_text']])
    return out.getvalue().encode('utf-8')


def prepare(protocol, raw, search_id, searched_at):
    """Build a detached wrapper and exact CSV derivative; never supply a timestamp."""
    _strict_json(protocol)
    if type(protocol) is not dict:
        raise ValueError('protocol must be an object')
    if (type(search_id) is not str or not search_id.strip()
            or type(searched_at) is not str or not searched_at.strip()):
        raise ValueError('explicit search_id and supplied searched_at are required')
    run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    parsed = parse_export(raw)
    original_sha = hashlib.sha256(raw).hexdigest()
    csv_raw = _csv_bytes(parsed, original_sha)
    nested = bibliographic_intake.prepare(protocol, csv_raw, search_id, searched_at)
    result = dict(schema_version=1, mode='local_ris_preparation',
        collection_status='UNREVIEWED_LOCAL_EXPORT',
        protocol_snapshot=copy.deepcopy(protocol), protocol_sha256=digest(protocol),
        search_request=copy.deepcopy(nested['search_request']),
        source_export=dict(format='strict_fixed_column_utf8_ris_subset', encoding='utf-8',
                           bytes=len(raw), sha256=original_sha, text=raw.decode('utf-8')),
        parsed_export=parsed, csv_intake=nested,
        derivation=dict(format='comma_delimited_csv', headers=list(HEADERS),
            record_id_convention='ris-occurrence:<original file SHA-256>:<positional ris-record ID>',
            source_locator_convention='supplied-ris-sha256:<original file SHA-256>#<positional ris-record ID>',
            identity_status='FILE_OCCURRENCE_ONLY_NOT_PUBLICATION_IDENTITY',
            csv_sha256=hashlib.sha256(csv_raw).hexdigest(), csv_bytes=len(csv_raw),
            canonical_json_columns=['ris_record_span_json', 'ris_fields_json'],
            full_file_provenance_requires_wrapper=True,
            ordinary_bundle_independently_verifies_native_wrapper=False,
            boundary=BOUNDARY),
        engine_sha256=implementation_hashes(),
        query_export_association='SUPPLIED_NOT_VERIFIED',
        review_status='NOT_PERFORMED', search_completion='NOT_ESTABLISHED',
        source_authenticity='NOT_VERIFIED', human_authenticity='NOT_VERIFIED',
        record_identity_verification='NOT_ESTABLISHED',
        effects=dict(protocol_changed=False, new_searches=0, new_screening_decisions=0,
                     new_reports=0, new_studies=0, new_evidence_rows=0),
        external_calls=0, census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY',
        boundary=BOUNDARY)
    result['review_target'] = dict(target_type='ris_preparation', target_id=search_id,
        target_sha256=digest(result),
        scope='Exact retained RIS bytes, native parsing, deterministic CSV derivative, supplied protocol and current implementation; not review approval or authentication')
    artifact_bytes(result)
    return result


def verify(artifact):
    """Reconstruct the whole wrapper and compare canonical JSON including extra keys."""
    artifact_bytes(artifact)
    if type(artifact) is not dict or type(artifact.get('schema_version')) is not int or artifact['schema_version'] != 1:
        raise ValueError('unsupported RIS artifact schema')
    source, request = artifact.get('source_export'), artifact.get('search_request')
    if (type(source) is not dict or type(source.get('text')) is not str
            or type(request) is not dict):
        raise ValueError('invalid retained RIS export or search request')
    raw = source['text'].encode('utf-8')
    if (type(source.get('bytes')) is not int or source['bytes'] != len(raw)
            or source.get('sha256') != hashlib.sha256(raw).hexdigest()):
        raise ValueError('retained RIS length or SHA-256 mismatch')
    if artifact.get('engine_sha256') != implementation_hashes():
        raise ValueError('RIS implementation bytes differ; use the recorded implementation')
    expected = prepare(artifact.get('protocol_snapshot'), raw,
                       request.get('search_id'), request.get('searched_at'))
    if canonical_json_bytes(artifact) != canonical_json_bytes(expected):
        raise ValueError('RIS artifact differs from regenerated supplied inputs')
    bibliographic_intake.verify(artifact['csv_intake'])
    return dict(valid=True, artifact_sha256=digest(artifact),
        source_export_sha256=source['sha256'], source_export_bytes=source['bytes'],
        record_rows=len(expected['parsed_export']['records']),
        review_target=copy.deepcopy(expected['review_target']),
        csv_review_target=copy.deepcopy(expected['csv_intake']['review_target']),
        verification_scope='Exact retained UTF-8 bytes, current implementation and deterministic derived fields; not authentication or acceptance',
        review_status='NOT_PERFORMED', search_completion='NOT_ESTABLISHED',
        source_authenticity='NOT_VERIFIED', human_authenticity='NOT_VERIFIED',
        record_identity_verification='NOT_ESTABLISHED', external_calls=0,
        census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def render_text(result):
    if result.get('valid') is True:
        lines = ['RIS internal byte/derivation consistency: true',
            'Original export SHA-256: ' + result['source_export_sha256'],
            'Recorded occurrences (not search total): ' + str(result['record_rows']),
            'Review target (not approval): ' + quoted_display(result['review_target'])]
    else:
        lines = ['Unreviewed local RIS preparation',
            'Original export SHA-256: ' + result['source_export']['sha256'],
            'Recorded occurrences (not search total): ' + str(len(result['parsed_export']['records'])),
            'Supplied search association: ' + quoted_display(result['search_request']),
            'Identity scope: file occurrences only; DOI/ID/URL values are retained, not resolved or merged.',
            'Review target (not approval): ' + quoted_display(result['review_target']),
            'CSV review target (separate explicit human choices required): ' + quoted_display(result['csv_intake']['review_target'])]
    return '\n'.join(lines + ['External calls: 0', 'Census: NOT_ESTABLISHED',
                             'Conclusion: NOT_READY', BOUNDARY]) + '\n'


def _write_new(path, raw):
    """Refuse observed final entries; not a race or ancestor-alias security boundary."""
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(errno.EEXIST, 'output directory entry already exists', str(path))
    with path.open('xb') as output:
        output.write(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preview = commands.add_parser('preview')
    preview.add_argument('protocol', type=Path)
    preview.add_argument('export', type=Path)
    preview.add_argument('--search-id', required=True)
    preview.add_argument('--searched-at', required=True)
    preview.add_argument('--output', type=Path)
    preview.add_argument('--text', action='store_true')
    check = commands.add_parser('verify')
    check.add_argument('artifact', type=Path)
    outputs = check.add_mutually_exclusive_group()
    outputs.add_argument('--intake-output', type=Path)
    outputs.add_argument('--csv-output', type=Path)
    check.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        output_path = None
        output_bytes = None
        if args.command == 'preview':
            protocol = parse_json(bibliographic_intake.read_bounded(args.protocol, MAX_ARTIFACT_BYTES))
            raw = bibliographic_intake.read_bounded(args.export, MAX_EXPORT_BYTES)
            result = prepare(protocol, raw, args.search_id, args.searched_at)
            if args.output is not None:
                output_path, output_bytes = args.output, artifact_bytes(result)
        else:
            artifact = parse_json(bibliographic_intake.read_bounded(args.artifact, MAX_ARTIFACT_BYTES))
            result = verify(artifact)
            if args.intake_output is not None:
                output_path, output_bytes = args.intake_output, artifact_bytes(artifact['csv_intake'])
            elif args.csv_output is not None:
                output_path = args.csv_output
                output_bytes = artifact['csv_intake']['source_export']['text'].encode('utf-8')
        # Preflight every serialization, including stdout, before exclusive output.
        stdout = render_text(result).encode('utf-8') if args.text else artifact_bytes(result)
        if len(stdout) > MAX_ARTIFACT_BYTES or (output_bytes is not None and len(output_bytes) > MAX_ARTIFACT_BYTES):
            raise ValueError('RIS artifact or output exceeds size limit')
        if output_path is not None:
            _write_new(output_path, output_bytes)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'RIS intake error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
