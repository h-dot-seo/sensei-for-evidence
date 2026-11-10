"""Export a native supplied-count crosswalk CSV, not an external PRISMA template."""
import argparse
import copy
import csv
import hashlib
import io
import json
from pathlib import Path

from csv_safety import safe_csv_cell
from json_io import configure_utf8_stdio, parse_json, quoted_display
from prisma_audit import export_audit

MAX_BYTES = 16 * 1024 * 1024
SCHEMA = 'sensei.prisma-flow-crosswalk.v1'
HEADERS = ('schema', 'template_key', 'search_index', 'label', 'count', 'unit',
           'mapped_node', 'scope', 'boundary', 'census_claim', 'conclusion_readiness')
BOUNDARY = (
    'Native supplied-count crosswalk only; not an official PRISMA template, '
    'import-compatible interchange format, certified diagram or completed review. '
    'Exact supplied record-ID repeats are not publication deduplication. '
    'Downstream totals cover all supplied searches, not method-specific arms. '
    'Blank means not mapped, withheld or not supplied, never inferred zero. '
    'No model call, network, source authentication or scientific judgement. '
    'Census: NOT_ESTABLISHED. Conclusion: NOT_READY. '
    'PRIVATE FILE: supplied source labels and reasons are retained; keep real outputs '
    'outside the public repository and do not share without authorization.'
)
NODE_MAPPINGS = (
    ('duplicates', 'repeated_exact_id_occurrences'),
    ('records_screened', 'screened_records'),
    ('records_excluded', 'excluded_records'),
    ('dbr_sought_reports', 'reports_sought'),
    ('dbr_notretrieved_reports', 'reports_not_retrieved'),
    ('dbr_assessed', 'reports_assessed'),
    ('dbr_excluded', 'reports_excluded'),
    ('new_studies', 'included_studies'),
    ('new_reports', 'reports_included'),
)
UNSUPPORTED_KEYS = (
    'website_results', 'organisation_results', 'citation_search_results',
    'automation_excluded', 'other_records_removed', 'previous_studies',
    'previous_reports', 'other_sought_reports', 'other_notretrieved_reports',
    'other_assessed', 'other_excluded',
)
PENDING_NODES = ('screening_pending_records', 'unmapped_included_records',
                 'reports_retrieval_pending', 'reports_assessment_pending')


def _check_arms(arms, count):
    if type(arms) is not dict:
        raise ValueError('search arms must be an index-to-arm object')
    for index, arm in arms.items():
        if type(index) is not int or not 0 <= index < count:
            raise ValueError('search arm index is outside the supplied searches')
        if type(arm) is not str or arm not in ('databases', 'registers'):
            raise ValueError('search arm must be databases or registers')


def parse_search_arms(values):
    """Reject duplicate indices, noncanonical indices and inferred classifications."""
    result = {}
    for value in values:
        index, separator, arm = value.partition('=')
        if not separator or not index.isascii() or not index.isdecimal():
            raise ValueError('search arm must use INDEX=databases or INDEX=registers')
        number = int(index)
        if str(number) != index or number in result:
            raise ValueError('search arm indices must be canonical and unique')
        if arm not in ('databases', 'registers'):
            raise ValueError('search arm must be databases or registers')
        result[number] = arm
    return result


def _csv_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n', quoting=csv.QUOTE_ALL)
    output = bytearray()
    for values in [HEADERS] + [tuple(row[key] for key in HEADERS) for row in rows]:
        stream.seek(0)
        stream.truncate(0)
        writer.writerow([safe_csv_cell('' if value is None else value) for value in values])
        raw = stream.getvalue().encode('utf-8')
        if len(output) + len(raw) > MAX_BYTES:
            raise ValueError('crosswalk output exceeds size limit; narrow the supplied protocol')
        output.extend(raw)
    return bytes(output)


def export_crosswalk(protocol, search_arms=None, include_exact_id_accounting=False):
    """Derive an unchanged audit into a detached CSV and complete mapping receipt."""
    arms = {} if search_arms is None else search_arms
    if type(include_exact_id_accounting) is not bool:
        raise ValueError('exact-ID accounting option must be boolean')
    audit = export_audit(protocol)
    _check_arms(arms, len(audit['searches']))
    nodes = {node['node_id']: node for node in audit['nodes']}
    rows = []

    def add(key, count, unit='', node='', scope='', label='', search_index=None):
        rows.append(dict(schema=SCHEMA, template_key=key, search_index=search_index,
                         label=label, count=count, unit=unit, mapped_node=node,
                         scope=scope, boundary=BOUNDARY, census_claim='NOT_ESTABLISHED',
                         conclusion_readiness='NOT_READY'))

    search_ledger = []
    for item in audit['searches']:
        index = item['search_index']
        arm = arms.get(index)
        key = {'databases': 'database_results', 'registers': 'register_results'}.get(arm)
        count = item['accounting']['enumerated']
        add(key or 'unassigned_search', count if arm else None, 'record_occurrence',
            'identified_occurrences',
            'Per-input search index; enumerated occurrences only; no label aggregation '
            'or inferred search classification' if arm else 'Search arm not supplied; count withheld',
            item['search']['source'], index)
        search_ledger.append(dict(search_index=index, supplied_arm=arm,
                                  input_pointer=item['input_pointer'],
                                  source=item['search']['source'],
                                  search_id=item['search'].get('search_id'),
                                  supplied_total_count=item['search']['total_count'],
                                  supplied_complete=item['search']['complete'],
                                  supplied_has_more=item['search']['has_more'],
                                  accounting=copy.deepcopy(item['accounting'])))
    for arm, key in (('databases', 'database_results'), ('registers', 'register_results')):
        if arm not in arms.values():
            add(key, None, 'record_occurrence', scope='No search explicitly assigned to this arm')
    for key, node_id in NODE_MAPPINGS:
        node = nodes[node_id]
        withheld = key in ('duplicates', 'records_screened') and not include_exact_id_accounting
        scope = node['scope'] + '; all supplied searches, not a method-specific partition'
        if key == 'duplicates':
            scope = 'Exact supplied record-ID repeats only; not deduplication; all supplied searches'
        if withheld:
            scope += '; withheld without --include-exact-id-accounting'
        add(key, None if withheld else node['count'], node['unit'], node_id, scope)
    for reason in audit['reasons']['report_exclusions'] or []:
        add('dbr_excluded_reason', reason['count'], reason['unit'], 'reports_excluded',
            'Separate supplied reason group; not an additional report total; all supplied searches',
            reason['reason'])
    for key in UNSUPPORTED_KEYS:
        add(key, None, scope='No corresponding method-specific supplied accounting; not zero')
    raw = _csv_bytes(rows)

    def transition(name, minuend, subtract, residual):
        ids = [minuend] + subtract + residual
        available = all(nodes[key]['count'] is not None for key in ids)
        return dict(name=name, minuend=minuend, subtracted_nodes=subtract,
                    residual_nodes=residual, status='RECORDED_COUNT_DIFFERENCE' if available else 'NOT_SUPPLIED',
                    difference=nodes[minuend]['count'] - sum(nodes[key]['count'] for key in subtract) if available else None,
                    residual_count=sum(nodes[key]['count'] for key in residual) if available else None,
                    scope='Mechanical supplied count difference only; no PRISMA transition or readiness judgement')

    root = Path(__file__).resolve().parent
    hashes = dict(audit['engine_sha256'])
    for name in ('prisma_flow_template.py', 'csv_safety.py'):
        hashes[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    result = dict(schema=SCHEMA, protocol_sha256=audit['protocol_sha256'], engine_sha256=hashes,
                  csv=dict(encoding='utf-8', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                           headers=list(HEADERS), row_count=len(rows), external_template_compatibility='NOT_ESTABLISHED'),
                  include_exact_id_accounting=include_exact_id_accounting,
                  mapping_ledger=rows, search_ledger=search_ledger,
                  unassigned_search_indices=[row['search_index'] for row in search_ledger if row['supplied_arm'] is None],
                  search_plan_audit=copy.deepcopy(audit['search_plan_audit']),
                  outside_flow_nodes=[copy.deepcopy(nodes[key]) for key in PENDING_NODES],
                  transition_differences=[
                      transition('identified_to_screened', 'identified_occurrences',
                                 ['repeated_exact_id_occurrences', 'screened_records'], ['screening_pending_records']),
                      transition('included_records_to_mapping', 'included_records', ['mapped_included_records'],
                                 ['unmapped_included_records']),
                      transition('sought_to_assessed', 'reports_sought', ['reports_not_retrieved', 'reports_assessed'],
                                 ['reports_retrieval_pending', 'reports_assessment_pending'])],
                  partition_checks=copy.deepcopy(audit['partition_checks']),
                  report_stage=audit['report_stage'], external_calls=0, protocol_changed=False,
                  census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    return result, raw


def render_text(result):
    lines = ['Native supplied-count crosswalk CSV', BOUNDARY,
             'Protocol SHA-256: ' + result['protocol_sha256'],
             'CSV: ' + quoted_display(result['csv'])]
    for key in ('mapping_ledger', 'search_ledger', 'unassigned_search_indices', 'search_plan_audit',
                'outside_flow_nodes', 'transition_differences', 'partition_checks', 'engine_sha256'):
        lines.append(key + ': ' + quoted_display(result[key]))
    return '\n'.join(lines + ['Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY', BOUNDARY]) + '\n'


def _write_new(path, raw):
    """Reject existing entries before exclusive creation, including Windows links.

    Like the other intake writers, this assumes stable paths. It is not a
    race-proof defense against concurrent replacement or ancestor aliases.
    """
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError('output directory entry already exists')
    with path.open('xb') as target:
        target.write(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--search-arm', action='append', default=[], metavar='INDEX=ARM')
    parser.add_argument('--include-exact-id-accounting', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        with args.protocol.open('rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('protocol exceeds size limit')
        result, output = export_crosswalk(parse_json(raw), parse_search_arms(args.search_arm),
                                          args.include_exact_id_accounting)
        stdout = (render_text(result) if args.text else json.dumps(
            result, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        if len(stdout) > MAX_BYTES:
            raise ValueError('crosswalk receipt exceeds size limit; narrow the supplied protocol')
        # Preflight both complete serializations before creating the only output.
        _write_new(args.output, output)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'PRISMA crosswalk error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
