"""Join supplied evidence, context and appraisal into work-package review packets."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import engine_hashes
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display

BOUNDARY = ('A review packet joins supplied assertions and mechanical gaps only. It does not '
            'judge source authenticity, clinical applicability, guideline currency, regulatory status, causal validity, '
            'evidence quality or development readiness. Work status and reviewer labels are not '
            'independently verified. Missing appraisal is not a poor-quality judgement; no priority, '
            'recommendation or go/no-go decision is generated.')


def review_packets(protocol, work_package_id=None):
    research = run(protocol)
    reports = report_flow(protocol) if 'reports' in protocol else None
    work = {row['work_package_id']: row for row in research['work_packages']}
    if work_package_id is not None and work_package_id not in work:
        raise ValueError('unknown work package ID')
    screening = {row['record_id']: row for row in research['screening_ledger']}
    evidence = {row['evidence_id']: row for row in research['evidence']}
    provenance = {row['record_id']: row['occurrences'] for row in research['record_provenance']}
    report_by_record = {rid: report for report in reports['report_ledger'] for rid in report['record_ids']} if reports else {}
    context = {row['context_id']: row for row in research['context']['context_ledger']}
    appraisals = {row['appraisal_id']: row for row in research['appraisal']['appraisal_ledger']}
    appraisal_links = {row['evidence_id']: row['appraisal_ids'] for row in research['appraisal']['evidence_appraisal_links']}
    candidate_receipts = {row['sha256']: row for row in protocol.get('adapter_receipts', {}).get('receipts', [])
                          if row['target_type'] == 'extraction'}
    planning = {row['work_package_id']: row for row in research['planning']['planning_ledger']}
    planning_targets = {row['work_package_id']: row for row in research['planning']['review_targets']}
    experiment_links = {row['evidence_id']: row['experiment_id'] for row in research['experiments']['evidence_links']}
    selected = [work_package_id] if work_package_id is not None else sorted(work)
    packets = []
    for wid in selected:
        item = work[wid]
        evidence_ids = set(item['evidence_ids'])
        result_rows, source_indices = [], set()
        for eid in sorted(evidence_ids):
            row = evidence[eid]
            occurrences = copy.deepcopy(provenance[row['record_id']])
            source_indices.update(occurrence['search_index'] for occurrence in occurrences)
            receipt_hash = row.get('adapter_provenance', {}).get('receipt_sha256')
            candidate = candidate_receipts.get(receipt_hash, {}).get('candidate')
            support = None if candidate is None else {
                key: candidate[key] for key in ('candidate_id', 'request_id', 'source_locator',
                                                'supporting_quote', 'extractor_id', 'extractor_version')}
            result_rows.append(dict(evidence=copy.deepcopy(row), experiment_id=experiment_links[eid], screening=copy.deepcopy(screening[row['record_id']]),
                                    search_occurrences=occurrences,
                                    report=copy.deepcopy(report_by_record.get(row['record_id'])),
                                    appraisal_ids=copy.deepcopy(appraisal_links[eid]),
                                    adapter_candidate_support=support))
        context_rows = []
        for cid in sorted(item.get('context_ids', [])):
            row = context[cid]
            context_rows.append(dict(context=copy.deepcopy(row),
                work_evidence_ids=sorted(evidence_ids.intersection(row['evidence_ids'])),
                other_context_evidence_ids=sorted(set(row['evidence_ids']) - evidence_ids)))
        appraisal_ids = sorted({aid for eid in evidence_ids for aid in appraisal_links[eid]})
        appraisal_rows = [dict(appraisal=copy.deepcopy(appraisals[aid]),
                              work_evidence_ids=sorted(evidence_ids.intersection(appraisals[aid]['evidence_ids'])),
                              other_appraisal_evidence_ids=sorted(set(appraisals[aid]['evidence_ids']) - evidence_ids))
                          for aid in appraisal_ids]
        source_rows = [dict(search_index=index, search=copy.deepcopy(research['search_ledger'][index]),
                            accounting=copy.deepcopy(research['coverage'][index])) for index in sorted(source_indices)]
        packets.append(dict(work_package=copy.deepcopy(item),
            planning_assertion=copy.deepcopy(planning[wid]), planning_review_target=copy.deepcopy(planning_targets[wid]),
            dependencies=[copy.deepcopy(work[dependency]) for dependency in item['depends_on']],
            results=result_rows, sources=source_rows, contexts=context_rows, appraisals=appraisal_rows,
            experimental_stage=research['experiments']['stage'],
            experimental_gap_scope='full_intersecting_condition_records_including_other_outcomes',
            experimental_units=[dict(experimental_unit=copy.deepcopy(unit),
                                     work_evidence_ids=sorted(evidence_ids.intersection(unit['evidence_ids'])),
                                     other_experiment_evidence_ids=sorted(set(unit['evidence_ids'])-evidence_ids))
                                for unit in research['experiments']['experimental_unit_ledger'] if evidence_ids.intersection(unit['evidence_ids'])],
            scope_counts=dict(result_rows=len(result_rows),
                source_records=len({row['evidence']['record_id'] for row in result_rows}),
                supplied_study_ids=len({row['evidence']['study_id'] for row in result_rows}),
                linked_reports=None if reports is None else len({row['report']['report_id'] for row in result_rows if row['report'] is not None})),
            linked_context_domains=sorted({row['context']['domain'] for row in context_rows}),
            context_link_status='SUPPLIED' if context_rows else 'NO_CONTEXT_LINKS_SUPPLIED',
            report_stage='SUPPLIED' if reports is not None else 'NOT_SUPPLIED',
            recorded_review_gaps=dict(
                evidence_without_experimental_unit=sorted(eid for eid in evidence_ids if experiment_links[eid] is None) if research['experiments']['stage'] == 'SUPPLIED' else None,
                units_with_unresolved_conditions=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if unit['unresolved_fields'] and evidence_ids.intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else None,
                pending_context_ids=sorted(row['context']['context_id'] for row in context_rows if row['context']['review_status'] == 'pending'),
                evidence_without_recorded_appraisal=sorted(eid for eid in evidence_ids if not appraisal_links[eid]),
                source_indices_with_unresolved_accounting=[row['search_index'] for row in source_rows if not row['accounting']['complete']]),
            decision_status='NO_AUTOMATED_DECISION'))
    implementation = dict(engine_hashes(), **{'work_review.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return dict(schema_version=1, question=research['question'], protocol_version=research['protocol_version'],
                protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                hash_scope='sorted compact UTF-8 JSON; object key order ignored, list order retained; not authentication',
                engine_sha256=implementation, selection=work_package_id,
                experiment_boundary=research['experiments']['boundary'],
                planning_boundary=research['planning']['boundary'],
                planning_source_scope_fields=research['planning']['source_scope_fields'],
                planning_source_scope_sha256=research['planning']['source_scope_sha256'],
                global_current_rank_groups=copy.deepcopy(research['planning']['current_rank_groups']),
                rank_groups_scope=research['planning']['current_rank_groups_scope'],
                global_search_plan_audit=copy.deepcopy(research['search_plan_audit']),
                deduplication_scope=research['deduplication_scope'],
                record_identity_verification=research['record_identity_verification'],
                packets=packets, extraction_completeness=research['extraction_completeness'],
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY',
                boundary=BOUNDARY)


def render_text(result):
    show = quoted_display
    plan_supplied = result['global_search_plan_audit']['plan_status'] != 'NOT_SUPPLIED'
    lines = ['Work-package review packets', 'Question: ' + show(result['question']),
             'Protocol version: ' + show(result['protocol_version']),
             'Global search plan: ' + show(result['global_search_plan_audit']['plan_status']),
             'Missing planned searches: ' + (show(result['global_search_plan_audit']['missing_search_ids']) if plan_supplied else 'not supplied'),
             'Incomplete planned searches: ' + (show(result['global_search_plan_audit']['incomplete_search_ids']) if plan_supplied else 'not supplied')]
    if not result['packets']:
        lines.append('No work packages supplied.')
    for packet in result['packets']:
        work = packet['work_package']
        lines.extend(['', 'Work package: ' + show(work['work_package_id']),
                      'Supplied status: ' + show(work['status']),
                      'Question: ' + show(work['question']), 'Deliverable: ' + show(work['deliverable']),
                      'Acceptance criterion: ' + show(work['acceptance_criterion']),
                      'Dependencies: ' + show(work['depends_on']), 'Blocked by: ' + show(work['blocked_by']),
                      'Scope counts: ' + show(packet['scope_counts']),
                      'Supplied planning assertion: ' + show(packet['planning_assertion']),
                      'Current planning basis hash (review target only): ' + show(packet['planning_review_target']['basis_sha256']),
                      'Recorded review gaps: ' + show(packet['recorded_review_gaps']),
                      'Report stage: ' + show(packet['report_stage']),
                      'Context links: ' + show(packet['context_link_status'])])
        for field in ('artifact_locator', 'acceptance_verified'):
            if field in work:
                lines.append('Supplied ' + field + ': ' + show(work[field]))
        for dependency in packet['dependencies']:
            lines.append('Dependency assertion: ' + show(dependency))
        for row in packet['results']:
            lines.append('Result assertion: ' + show(row['evidence']))
            lines.append('Screening assertion: ' + show(row['screening']))
            lines.append('Report source: ' + show(row['report']))
            lines.append('Search occurrences: ' + show(row['search_occurrences']))
            if row['adapter_candidate_support'] is not None:
                lines.append('Unverified mock candidate support: ' + show(row['adapter_candidate_support']))
        for source in packet['sources']:
            lines.append('Search source/accounting: ' + show(source))
        lines.append('Structured condition stage: ' + packet['experimental_stage'])
        lines.append('Unresolved condition scope: ' + packet['experimental_gap_scope'])
        for unit in packet['experimental_units']:
            lines.append('Supplied comparison condition and linkage scope: ' + show(unit))
        for context in packet['contexts']:
            lines.append('Context assertion and linkage scope: ' + show(context))
        for appraisal in packet['appraisals']:
            lines.append('Appraisal assertion and linkage scope: ' + show(appraisal))
        lines.append('Decision: NO_AUTOMATED_DECISION')
    lines.extend(['', 'Record identity: NOT_ESTABLISHED; exact supplied IDs only.',
                  'Extraction completeness: NOT_ESTABLISHED', 'Census: NOT_ESTABLISHED',
                  'Conclusion: NOT_READY', result['experiment_boundary'], result['planning_boundary'], result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--work-package', help='select one exact supplied work-package ID')
    parser.add_argument('--text', action='store_true', help='render a text review packet')
    args = parser.parse_args()
    try:
        result = review_packets(parse_json(args.protocol.read_bytes()), args.work_package)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2), end='' if args.text else '\n')


if __name__ == '__main__':
    main()
