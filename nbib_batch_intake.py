"""Prepare explicitly grouped local NBIB files as one unreviewed CSV intake.

Every input remains a separate ordered source with its exact bytes and native
spans. Grouping is supplied by the operator, not inferred search pagination.
"""
import argparse
import copy
import csv
import errno
import hashlib
import io
import json
from pathlib import Path

import bibliographic_intake
import nbib_export_parser
import nbib_intake
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display

MAX_SOURCES = 100
MAX_SOURCE_ID_CHARS = 128
MAX_TOTAL_EXPORT_BYTES = 10_000_000
MAX_TOTAL_RECORDS = 100_000
MAX_TOTAL_PHYSICAL_LINES = 200_000
MAX_ARTIFACT_BYTES = 50_000_000
HEADERS = nbib_intake.HEADERS + ('nbib_source_id', 'nbib_source_index',
                               'nbib_batch_occurrence_id')
BOUNDARY = (
    'Local unreviewed preparation of explicitly grouped NBIB files, not verified search pages or a provider connection. '
    'Source order, source labels, query association and search timestamp are supplied and not authenticated. '
    'Each input retains exact native bytes, fields, separators and per-file spans. '
    'Identical files and repeated PMID occurrences remain separate; no publication identity or duplicate resolution is inferred. '
    'One derived CSV intake requires explicit human row choices and a separate exact-context review before one incomplete search can be appended. '
    'Grouping, file EOF, counts and successful replay do not establish search completeness, PRISMA compliance or scientific/clinical validity. '
    'No protocol, search, screening decision, report, study or evidence is created or changed by preparation or verification. '
    'The unchanged core sees CSV provenance, not native NBIB. Retain this batch wrapper for all original files and conversion replay; '
    'ordinary research bundles do not independently verify it, and the single-file collection bundle does not accept it. '
    'No source locator is opened and no external call is made. Supplied text is retained without redaction; '
    'store real exports and outputs outside the public repository.'
)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def implementation_hashes():
    return dict(nbib_intake.implementation_hashes(), **{
        'nbib_batch_intake.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def artifact_bytes(value):
    nbib_intake._strict_json(value)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                      allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError('NBIB batch artifact or output exceeds size limit')
    return raw


def _source_id(value):
    if type(value) is not str or not value.strip() or len(value) > MAX_SOURCE_ID_CHARS:
        raise ValueError('source_id must be nonempty text of at most 128 characters')
    nbib_intake._strict_json(value)
    if '\x00' in value:
        raise ValueError('source_id must not contain NUL')


def _source_inputs(sources):
    if type(sources) is not list or not 1 <= len(sources) <= MAX_SOURCES:
        raise ValueError('sources require between 1 and 100 explicit ordered selections')
    seen = set()
    total = 0
    for source in sources:
        if type(source) is not dict or set(source) != {'source_id', 'raw'}:
            raise ValueError('each source requires exactly source_id and raw')
        _source_id(source['source_id'])
        if source['source_id'] in seen:
            raise ValueError('source_id must be unique within the batch')
        seen.add(source['source_id'])
        if type(source['raw']) is not bytes:
            raise ValueError('each source raw value must be bytes')
        total += len(source['raw'])
        if total > MAX_TOTAL_EXPORT_BYTES:
            raise ValueError('combined native inputs exceed byte limit')
    return total


def _parse_sources(sources):
    retained = []
    records = lines = 0
    for index, source in enumerate(sources):
        raw = source['raw']
        try:
            parsed = nbib_export_parser.parse_export(raw)
        except ValueError as error:
            # Identify the input position without echoing caller labels/content.
            raise ValueError(f'source {index + 1}: {error}') from None
        records += len(parsed['records'])
        lines += parsed['physical_lines']
        if records > MAX_TOTAL_RECORDS:
            raise ValueError('combined native inputs exceed record limit')
        if lines > MAX_TOTAL_PHYSICAL_LINES:
            raise ValueError('combined native inputs exceed physical line limit')
        retained.append(dict(source_index=index, source_id=source['source_id'],
            source_export=dict(format='strict_fixed_column_pubmed_nbib_subset',
                encoding='utf-8', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                text=raw.decode('utf-8')), parsed_export=parsed))
    return retained


def _csv_bytes(sources):
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow(HEADERS)
    occurrences = {}
    for source in sources:
        index = source['source_index']
        for row in source['parsed_export']['records']:
            occurrence = f"source-{index + 1:06d}/" + row['candidate_id']
            writer.writerow(['pubmed:' + row['pmid'],
                'https://pubmed.ncbi.nlm.nih.gov/' + row['pmid'] + '/',
                row['candidate_id'], source['source_export']['sha256'],
                canonical_json_bytes(row['source_span']).decode('utf-8'),
                canonical_json_bytes(row['fields']).decode('utf-8'), row['raw_text'],
                source['source_id'], str(index), occurrence])
            occurrences.setdefault(row['pmid'], []).append(dict(
                source_index=index, source_id=source['source_id'],
                native_candidate_id=row['candidate_id'], batch_candidate_id=occurrence))
    repeated = [dict(pmid=pmid, occurrences=rows)
                for pmid, rows in occurrences.items() if len(rows) > 1]
    return out.getvalue().encode('utf-8'), repeated


def _claims():
    return dict(query_export_association='SUPPLIED_NOT_VERIFIED',
        review_status='NOT_PERFORMED', search_completion='NOT_ESTABLISHED',
        source_authenticity='NOT_VERIFIED', human_authenticity='NOT_VERIFIED',
        record_identity_verification='NOT_ESTABLISHED', external_calls=0,
        census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')


def prepare(protocol, sources, search_id, searched_at):
    """Preserve selected native files separately; never infer grouping or identity."""
    nbib_intake._strict_json(protocol)
    if type(protocol) is not dict:
        raise ValueError('protocol must be an object')
    if (type(search_id) is not str or not search_id.strip()
            or type(searched_at) is not str or not searched_at.strip()):
        raise ValueError('explicit search_id and supplied searched_at are required')
    total = _source_inputs(sources)
    retained = _parse_sources(sources)
    csv_raw, repeated = _csv_bytes(retained)
    nested = bibliographic_intake.prepare(protocol, csv_raw, search_id, searched_at)
    result = dict(schema_version=1, mode='local_nbib_batch_preparation',
        collection_status='UNREVIEWED_LOCAL_EXPORT',
        protocol_snapshot=copy.deepcopy(protocol), protocol_sha256=digest(protocol),
        search_request=copy.deepcopy(nested['search_request']),
        source_exports=retained, csv_intake=nested,
        source_grouping=dict(status='EXPLICIT_SUPPLIED_NOT_VERIFIED',
            source_count=len(retained), total_native_bytes=total,
            recorded_occurrences=sum(len(item['parsed_export']['records']) for item in retained),
            physical_lines=sum(item['parsed_export']['physical_lines'] for item in retained),
            duplicate_pmids=repeated,
            order_scope='Supplied file order followed by native record order; not chronology or verified pagination',
            source_id_scope='Exact caller labels identify input occurrences; not paths, authenticated downloads or stable source identities',
            completeness='NOT_ESTABLISHED'),
        derivation=dict(format='comma_delimited_csv', headers=list(HEADERS),
            record_id_convention='pubmed:<literal PMID>',
            source_locator_convention='https://pubmed.ncbi.nlm.nih.gov/<literal PMID>/',
            batch_occurrence_convention='source-<one-based six-digit index>/<native candidate_id>',
            source_index_convention='Zero-based supplied input order',
            span_scope='Each native span is relative to its individual source file, never the concatenated batch or CSV',
            identity_status='UNVERIFIED_DERIVED_CONVENTIONS',
            csv_sha256=hashlib.sha256(csv_raw).hexdigest(), csv_bytes=len(csv_raw),
            canonical_json_columns=['nbib_record_span_json', 'nbib_fields_json'],
            full_file_provenance_requires_wrapper=True,
            ordinary_bundle_independently_verifies_native_wrapper=False,
            single_file_collection_bundle_accepts_batch_wrapper=False),
        engine_sha256=implementation_hashes(), **_claims(),
        effects=dict(protocol_changed=False, new_searches=0, new_screening_decisions=0,
            new_reports=0, new_studies=0, new_evidence_rows=0), boundary=BOUNDARY)
    result['review_target'] = dict(target_type='nbib_batch_preparation', target_id=search_id,
        target_sha256=digest(result),
        scope='Exact ordered and labeled native inputs, all native parsing, one CSV derivative, supplied protocol and current implementation; not review approval or authentication')
    artifact_bytes(result)
    return result


def verify(artifact):
    """Replay all sources and the complete derivative without renewing a review."""
    artifact_bytes(artifact)
    if (type(artifact) is not dict or type(artifact.get('schema_version')) is not int
            or artifact['schema_version'] != 1):
        raise ValueError('unsupported NBIB batch artifact schema')
    sources, request = artifact.get('source_exports'), artifact.get('search_request')
    if type(sources) is not list or type(request) is not dict:
        raise ValueError('invalid retained NBIB batch sources or search request')
    supplied = []
    for source in sources:
        if type(source) is not dict or type(source.get('source_export')) is not dict:
            raise ValueError('invalid retained NBIB batch source')
        native = source['source_export']
        if type(native.get('text')) is not str:
            raise ValueError('invalid retained NBIB batch text')
        raw = native['text'].encode('utf-8')
        if (type(native.get('bytes')) is not int or native['bytes'] != len(raw)
                or native.get('sha256') != hashlib.sha256(raw).hexdigest()):
            raise ValueError('retained NBIB source length or SHA-256 mismatch')
        supplied.append(dict(source_id=source.get('source_id'), raw=raw))
    if artifact.get('engine_sha256') != implementation_hashes():
        raise ValueError('NBIB batch implementation bytes differ; use the recorded implementation')
    expected = prepare(artifact.get('protocol_snapshot'), supplied,
                       request.get('search_id'), request.get('searched_at'))
    if canonical_json_bytes(artifact) != canonical_json_bytes(expected):
        raise ValueError('NBIB batch artifact differs from regenerated supplied inputs')
    bibliographic_intake.verify(artifact['csv_intake'])
    return dict(valid=True, artifact_sha256=digest(artifact),
        source_exports=[dict(source_index=source['source_index'], source_id=source['source_id'],
            sha256=source['source_export']['sha256'], bytes=source['source_export']['bytes'],
            record_rows=len(source['parsed_export']['records'])) for source in expected['source_exports']],
        record_rows=expected['source_grouping']['recorded_occurrences'],
        review_target=copy.deepcopy(expected['review_target']),
        csv_review_target=copy.deepcopy(expected['csv_intake']['review_target']),
        verification_scope='Exact retained UTF-8 bytes, ordered source labels, current implementation and deterministic derived fields; not authentication or acceptance',
        protocol_changed=False, **_claims(), boundary=BOUNDARY)


def render_text(result):
    if result.get('valid') is True:
        lines = ['NBIB batch internal byte/derivation consistency: true',
            'Supplied source files: ' + quoted_display(result['source_exports']),
            'Recorded occurrences (not search total): ' + str(result['record_rows'])]
    else:
        lines = ['Unreviewed local NBIB batch preparation',
            'Supplied grouping (not verified pagination): ' + quoted_display(result['source_grouping']),
            'Supplied search association: ' + quoted_display(result['search_request'])]
        for source in result['source_exports']:
            lines.append('Native source: ' + quoted_display(dict(
                source_index=source['source_index'], source_id=source['source_id'],
                bytes=source['source_export']['bytes'], sha256=source['source_export']['sha256'],
                record_rows=len(source['parsed_export']['records']))))
    lines.extend(['Review target (not approval): ' + quoted_display(result['review_target']),
        'CSV review target (separate explicit human choices required): ' + quoted_display(
            result['csv_review_target'] if result.get('valid') is True else result['csv_intake']['review_target']),
        'External calls: 0', 'Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY', BOUNDARY])
    return '\n'.join(lines) + '\n'


def _read_sources(selections):
    if not 1 <= len(selections) <= MAX_SOURCES:
        raise ValueError('sources require between 1 and 100 explicit ordered selections')
    paths = []
    seen = set()
    for selection in selections:
        label, separator, path = selection.partition('=')
        if not separator or not path:
            raise ValueError('--export requires SOURCE_ID=PATH')
        _source_id(label)
        if label in seen:
            raise ValueError('source_id must be unique within the batch')
        seen.add(label)
        paths.append((label, Path(path)))
    sources = []
    total = 0
    for label, path in paths:
        raw = bibliographic_intake.read_bounded(path, min(nbib_export_parser.MAX_EXPORT_BYTES,
                                                         MAX_TOTAL_EXPORT_BYTES - total))
        total += len(raw)
        sources.append(dict(source_id=label, raw=raw))
    return sources


def _write_new(path, raw):
    """Reject observed final entries; not a race/ancestor-alias security boundary."""
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
    preview.add_argument('--export', action='append', required=True, help='explicit SOURCE_ID=PATH; repeat in supplied order')
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
        output_path = output_bytes = None
        if args.command == 'preview':
            protocol = parse_json(bibliographic_intake.read_bounded(args.protocol, MAX_ARTIFACT_BYTES))
            result = prepare(protocol, _read_sources(args.export), args.search_id, args.searched_at)
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
        stdout = render_text(result).encode('utf-8') if args.text else artifact_bytes(result)
        if len(stdout) > MAX_ARTIFACT_BYTES or (output_bytes is not None and len(output_bytes) > MAX_ARTIFACT_BYTES):
            raise ValueError('NBIB batch artifact or output exceeds size limit')
        if output_path is not None:
            _write_new(output_path, output_bytes)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'NBIB batch intake error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
