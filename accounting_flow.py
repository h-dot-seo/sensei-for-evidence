"""Serialize fixed supplied-accounting labels as Mermaid text, without a renderer."""
import hashlib
from pathlib import Path
import re

from prisma_audit import BOUNDARY as AUDIT_BOUNDARY, export_audit

MAX_BYTES = 16 * 1024 * 1024
BOUNDARY = ('Supplied-data accounting flow. Repeated node labels in separate partitions '
            'are the same accounting quantities, not additive totals. '
            'No model call, network or clock read. Census: NOT_ESTABLISHED. '
            'Conclusion: NOT_READY. Counts and fingerprints may be private; '
            'exporting does not authorize sharing. ' + AUDIT_BOUNDARY)
NODE_UNITS = {
    **dict.fromkeys(('identified_occurrences', 'retained_occurrences',
                     'repeated_exact_id_occurrences'), 'record_occurrence'),
    **dict.fromkeys(('unique_records', 'screened_records', 'screening_pending_records',
                     'included_records', 'excluded_records', 'mapped_included_records',
                     'unmapped_included_records', 'records_with_extraction',
                     'included_records_without_extraction'), 'record'),
    **dict.fromkeys(('reports_sought', 'reports_retrieved', 'reports_not_retrieved',
                     'reports_retrieval_pending', 'reports_assessed',
                     'reports_assessment_pending', 'reports_included', 'reports_excluded',
                     'included_reports_with_extraction',
                     'included_reports_without_extraction'), 'report'),
    **dict.fromkeys(('included_studies', 'studies_with_extraction'), 'supplied_study_id'),
    'extracted_result_rows': 'result',
    **dict.fromkeys(('included_report_study_memberships',
                     'report_study_memberships_with_results',
                     'report_study_memberships_without_results'), 'report_study_membership'),
}
BRIDGES = (('retained_occurrences', 'unique_records'),
           ('mapped_included_records', 'reports_sought'))
BRIDGE_LABEL = 'explicit supplied mapping; different unit; counts not conserved'


def _count(value):
    if value is None:
        return 'not supplied'
    if type(value) is not int or value < 0:
        raise ValueError('flow count must be a nonnegative integer or null')
    return str(value)


def render_flow(audit, hashes):
    """Use only fixed vocabulary and counts, never supplied labels or member IDs."""
    raw = bytearray()

    def line(value):
        encoded = (value + '\n').encode('utf-8')
        if len(raw) + len(encoded) > MAX_BYTES:
            raise ValueError('accounting flow exceeds size limit')
        raw.extend(encoded)

    nodes = {}
    for node in audit['nodes']:
        name = node['node_id']
        if name not in NODE_UNITS or node['unit'] != NODE_UNITS[name] or name in nodes:
            raise ValueError('unsupported accounting node')
        if node['stage'] != ('NOT_SUPPLIED' if node['count'] is None else 'SUPPLIED'):
            raise ValueError('accounting node stage/count mismatch')
        nodes[name] = name + ' | ' + NODE_UNITS[name] + ' | ' + _count(node['count'])
    plan = audit['search_plan_audit']
    if plan['plan_status'] not in ('NOT_SUPPLIED', 'INCOMPLETE', 'ASSERTED_ACCOUNTED'):
        raise ValueError('unsupported search plan status')
    line('flowchart TD')
    for name, digest in [('protocol_sha256', audit['protocol_sha256'])] + sorted(hashes.items()):
        if not re.fullmatch(r'[A-Za-z0-9_.]+', name) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('unsupported implementation fingerprint')
        line('%% ' + name + ': ' + digest)
    line('title["Supplied-data accounting flow"]')
    line('boundary["' + BOUNDARY + '"]')
    missing = None if plan['plan_status'] == 'NOT_SUPPLIED' else len(plan['missing_search_ids'])
    incomplete = None if plan['plan_status'] == 'NOT_SUPPLIED' else len(plan['incomplete_search_ids'])
    line('plan["search plan | ' + plan['plan_status'] + ' | missing: ' +
         _count(missing) + ' | incomplete: ' + _count(incomplete) + '"]')
    used = set()
    for index, part in enumerate(audit['partition_checks']):
        names = [part['parent_node']] + part['child_nodes']
        if len(names) != len(set(names)) or len(names) < 2:
            raise ValueError('invalid accounting partition')
        if any(name not in nodes or NODE_UNITS[name] != part['unit'] for name in names):
            raise ValueError('unsupported accounting partition unit')
        if part['status'] not in ('RECORDED_MEMBERS_PARTITION', 'NOT_SUPPLIED'):
            raise ValueError('unsupported accounting partition status')
        prefix = 'p' + str(index)
        line('subgraph ' + prefix + '["Partition ' + str(index + 1) + ' | ' +
             part['unit'] + ' | ' + part['status'] + ' | separate bookkeeping"]')
        for number, name in enumerate(names):
            line(prefix + 'n' + str(number) + '["' + nodes[name] + '"]')
        for number in range(1, len(names)):
            line(prefix + 'n0 --> ' + prefix + 'n' + str(number))
        line('end')
        used.update(names)
    for index, (parent, child) in enumerate(BRIDGES):
        if parent not in nodes or child not in nodes:
            raise ValueError('missing accounting bridge node')
        prefix = 'b' + str(index)
        line('subgraph ' + prefix + '["Unit bridge | not a count partition"]')
        line(prefix + 'a["' + nodes[parent] + '"]')
        line(prefix + 'b["' + nodes[child] + '"]')
        line(prefix + 'a -. "' + BRIDGE_LABEL + '" .-> ' + prefix + 'b')
        line('end')
        used.update((parent, child))
    # Study/result counts outside partitions stay detached, not invented flows.
    for index, name in enumerate(sorted(set(nodes) - used)):
        line('d' + str(index) + '["' + nodes[name] + '"]')
    return bytes(raw)


def export_flow(protocol):
    audit = export_audit(protocol)
    root = Path(__file__).resolve().parent
    hashes = dict(audit['engine_sha256'])
    for name in ('accounting_flow.py', 'views_export.py', 'research_status.py'):
        hashes[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    raw = render_flow(audit, hashes)
    receipt = dict(schema='sensei.accounting-flow.v1', status='RENDERED', format='mermaid',
                   protocol_sha256=audit['protocol_sha256'], hash_scope=audit['hash_scope'],
                   engine_sha256=hashes,
                   document=dict(encoding='utf-8', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
                   node_count=len(audit['nodes']), partition_count=len(audit['partition_checks']),
                   unit_bridge_count=len(BRIDGES), external_calls=0, protocol_changed=False,
                   contains_supplied_text=False, census_claim='NOT_ESTABLISHED',
                   conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    return receipt, raw
