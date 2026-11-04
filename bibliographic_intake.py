"""Inspect local bibliographic CSV bytes as unreviewed, traceable collection candidates."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from context_links import nonempty_text
from csv_export_parser import MAX_EXPORT_BYTES, parse_export
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from research_bundle import engine_hashes

MAX_ARTIFACT_BYTES = 50_000_000
BOUNDARY = (
    'Local user-supplied CSV collection candidates, not mock provider execution or verified literature retrieval. '
    'The operator associates the export with a declared query; that association and the supplied search timestamp are not authenticated. '
    'File rows and end-of-file do not establish a search total, terminal page, complete search or publication identity. '
    'No search, screening decision, report, extraction or scientific/clinical conclusion is promoted into the protocol. '
    'Duplicate occurrences and conflicting literal locators remain unresolved. No source, URL or artifact referenced by a field is opened. '
    'The artifact retains supplied text without redaction; store real exports and outputs outside the public repository.'
)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return dict(engine_hashes(), **{name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                  for name in ('csv_export_parser.py', 'bibliographic_intake.py')})


def artifact_bytes(artifact):
    raw = (json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError('bibliographic intake artifact exceeds size limit')
    return raw


def prepare(protocol, export_bytes, search_id, searched_at,
            id_column='record_id', locator_column='source_locator'):
    """Prepare a detached collection artifact without modifying the research protocol."""
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol)
    if not nonempty_text(search_id) or not nonempty_text(searched_at):
        raise ValueError('explicit search_id and supplied searched_at are required')
    plan = protocol.get('search_plan')
    if not isinstance(plan, list) or not plan:
        raise ValueError('bibliographic intake requires an existing declared search plan')
    matches = [(index, row) for index, row in enumerate(plan) if row['search_id'] == search_id]
    if len(matches) != 1:
        raise ValueError('search_id must identify one existing declared search')
    index, selected = matches[0]
    parsed = parse_export(export_bytes, id_column=id_column, locator_column=locator_column)
    existing_ids = {rid for row in protocol['searches'] for rid in row['record_ids']}
    imported_ids = {row['record_id'] for row in parsed['record_rows']}
    result = dict(schema_version=1, mode='local_export', collection_status='UNREVIEWED_LOCAL_EXPORT',
                  protocol_snapshot=copy.deepcopy(protocol), protocol_sha256=digest(protocol),
                  protocol_hash_scope='Canonical supplied JSON; object key order ignored and list order retained; not authentication',
                  selected_plan_pointer=f'/search_plan/{index}', selected_plan_entry=copy.deepcopy(selected),
                  search_request=dict(**{key: selected[key] for key in ('search_id', 'source', 'query', 'window')},
                                      searched_at=searched_at),
                  query_export_association='SUPPLIED_NOT_VERIFIED',
                  uninterpreted_plan_fields=sorted(set(selected) - {'search_id', 'source', 'query', 'window'}),
                  column_mapping=dict(id_column=id_column, locator_column=locator_column),
                  source_export=dict(format='comma_delimited_csv', encoding='utf-8',
                                     bytes=len(export_bytes), sha256=hashlib.sha256(export_bytes).hexdigest(),
                                     text=export_bytes.decode('utf-8')),
                  parsed_export=parsed,
                  existing_protocol=dict(observed_search_indices=[i for i, row in enumerate(protocol['searches'])
                                                                   if row.get('search_id') == search_id],
                                         exact_record_overlap_ids=sorted(existing_ids & imported_ids),
                                         record_flow=copy.deepcopy(research['flow'])),
                  review_status='NOT_PERFORMED', search_completion='NOT_ESTABLISHED',
                  source_authenticity='NOT_VERIFIED', record_identity_verification='NOT_ESTABLISHED',
                  effects=dict(protocol_changed=False, new_searches=0, new_screening_decisions=0,
                               new_reports=0, new_evidence_rows=0),
                  engine_sha256=implementation_hashes(), external_calls=0,
                  census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    result['review_target'] = dict(target_type='bibliographic_export', target_id=search_id,
                                 target_sha256=digest(result),
                                 scope='Embedded export bytes, explicit column mapping, selected plan, full protocol snapshot and importer implementation; not review approval')
    artifact_bytes(result)  # Enforce the same bound before writing or returning the artifact.
    return result


def verify(artifact):
    """Reparse retained bytes and compare every derived field; never authenticate an export."""
    if not isinstance(artifact, dict) or type(artifact.get('schema_version')) is not int or artifact['schema_version'] != 1:
        raise ValueError('unsupported bibliographic intake artifact schema')
    artifact_bytes(artifact)
    source = artifact.get('source_export')
    mapping = artifact.get('column_mapping')
    request = artifact.get('search_request')
    if (not isinstance(source, dict) or not isinstance(source.get('text'), str)
            or not isinstance(mapping, dict) or set(mapping) != {'id_column', 'locator_column'}
            or not isinstance(request, dict)):
        raise ValueError('invalid retained export, column mapping or request')
    raw = source['text'].encode('utf-8')
    if type(source.get('bytes')) is not int or source['bytes'] != len(raw) or source.get('sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('retained export byte length or SHA-256 mismatch')
    if artifact.get('engine_sha256') != implementation_hashes():
        raise ValueError('importer implementation bytes differ; use the recorded implementation')
    expected = prepare(artifact.get('protocol_snapshot'), raw, request.get('search_id'), request.get('searched_at'),
                       mapping['id_column'], mapping['locator_column'])
    if canonical_json_bytes(artifact) != canonical_json_bytes(expected):
        raise ValueError('bibliographic intake artifact differs from regenerated supplied inputs')
    return dict(valid=True, artifact_sha256=digest(artifact),
                source_export_sha256=source['sha256'], source_export_bytes=source['bytes'],
                record_rows=len(expected['parsed_export']['record_rows']),
                review_target=copy.deepcopy(expected['review_target']),
                verification_scope='Exact retained UTF-8 bytes, current implementation and deterministic derived fields; not authenticity or acceptance',
                review_status='NOT_PERFORMED', search_completion='NOT_ESTABLISHED',
                source_authenticity='NOT_VERIFIED', external_calls=0,
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def render_text(result):
    show = quoted_display
    if 'valid' in result:
        return '\n'.join(['Local bibliographic intake verification',
                          'Internal byte/derivation consistency: ' + show(result['valid']),
                          'Export SHA-256: ' + result['source_export_sha256'],
                          'Recorded CSV rows (not a search total): ' + str(result['record_rows']),
                          'Review target (not approval): ' + show(result['review_target']),
                          result['verification_scope'], result['boundary'],
                          'Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY']) + '\n'
    parsed = result['parsed_export']
    lines = ['Unreviewed local bibliographic export', 'Status: ' + result['collection_status'],
             'Protocol SHA-256: ' + result['protocol_sha256'],
             'Export bytes/SHA-256: ' + show({key: result['source_export'][key] for key in ('bytes', 'sha256')}),
             'Supplied search association (not verified): ' + show(result['search_request']),
             'Uninterpreted plan fields: ' + show(result['uninterpreted_plan_fields']),
             'Explicit column mapping: ' + show(result['column_mapping']),
             'Recorded CSV rows (not a search total): ' + str(len(parsed['record_rows'])),
             'Existing search indices (never overwritten): ' + show(result['existing_protocol']['observed_search_indices']),
             'Exact-ID overlap with existing protocol (not publication matching): ' + show(result['existing_protocol']['exact_record_overlap_ids']),
             'Duplicate ID occurrences (not merged): ' + show(parsed['duplicate_record_ids']),
             'Conflicting literal locators (not resolved): ' + show(parsed['locator_conflicts']),
             'Ignored empty row spans: ' + show(parsed['ignored_blank_spans'])]
    for row in parsed['record_rows']:
        lines.append('Unreviewed row: ' + show({key: row[key] for key in ('candidate_id', 'record_id', 'source_locator', 'source_span')}))
    lines.extend(['Review target (not approval or a mock-adapter review): ' + show(result['review_target']),
                  'Protocol effects: ' + show(result['effects']),
                  'Original column values and exact retained export text remain in JSON; no full-text or result extraction was performed.',
                  'Imported rows remain outside existing PRISMA/evidence counts until a separately supported review/integration step.',
                  'External calls: 0', 'Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY', result['boundary']])
    return '\n'.join(lines) + '\n'


def read_bounded(path, limit):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('input file exceeds size limit')
    return raw


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preview = commands.add_parser('preview')
    preview.add_argument('protocol', type=Path)
    preview.add_argument('export', type=Path)
    preview.add_argument('--search-id', required=True)
    preview.add_argument('--searched-at', required=True)
    preview.add_argument('--id-column', default='record_id')
    preview.add_argument('--locator-column', default='source_locator')
    preview.add_argument('--output', type=Path, help='save a new unreviewed artifact exclusively; never overwrite')
    preview.add_argument('--text', action='store_true')
    check = commands.add_parser('verify')
    check.add_argument('artifact', type=Path)
    check.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'preview':
            protocol = parse_json(read_bounded(args.protocol, MAX_ARTIFACT_BYTES))
            result = prepare(protocol, read_bounded(args.export, MAX_EXPORT_BYTES), args.search_id, args.searched_at,
                             args.id_column, args.locator_column)
            if args.output is not None:
                serialized = artifact_bytes(result)
                with args.output.open('xb') as output:
                    output.write(serialized)
        else:
            result = verify(parse_json(read_bounded(args.artifact, MAX_ARTIFACT_BYTES)))
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        parser.exit(1, 'bibliographic intake error: ' + quoted_display(str(error)) + '\n')
    print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
          end='' if args.text else '\n')


if __name__ == '__main__':
    main()
