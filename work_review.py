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


def review_packets(protocol, work_package_id=None, include_prerequisites=False):
    if type(include_prerequisites) is not bool:
        raise ValueError("include_prerequisites must be a boolean")
    if include_prerequisites and work_package_id is None:
        raise ValueError("prerequisite review requires a selected work package")
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
    completion = {row['work_package_id']:row for row in research['planning']['completion_ledger']}
    planning_targets = {row['work_package_id']: row for row in research['planning']['review_targets']}
    experiment_links = {row['evidence_id']: row['experiment_id'] for row in research['experiments']['evidence_links']}
    planned_searches = {row['search_id']:row for row in research['search_plan_audit']['search_plan_ledger']}
    search_indices_by_id = {}
    for index,row in enumerate(research['search_ledger']):
        if isinstance(row.get('search_id'),str): search_indices_by_id.setdefault(row['search_id'],[]).append(index)
    result_ids_by_record = {}
    for row in research['evidence']: result_ids_by_record.setdefault(row['record_id'],[]).append(row['evidence_id'])
    selected = [work_package_id] if work_package_id is not None else sorted(work)
    if include_prerequisites:
        closure=set();pending=[work_package_id]
        while pending:
            wid=pending.pop()
            if wid in closure:continue
            closure.add(wid);pending.extend(work[wid]['depends_on'])
        selected=[wid for wid in research['execution_order'] if wid in closure]
    selected_set=set(selected)
    dependency_scope=dict(
        include_prerequisites=include_prerequisites,packet_work_ids=selected[:],
        edges=[dict(work_package_id=wid,depends_on=dep,prerequisite_packet_included=dep in selected_set,
                    supplied_prerequisite_status=work[dep]['status'],
                    prerequisite_completion_source_status=completion[dep]['source_match_status'])
               for wid in selected for dep in work[wid]['depends_on']],
        omitted_direct_prerequisite_ids=sorted({dep for wid in selected for dep in work[wid]['depends_on'] if dep not in selected_set}),
        order_scope=('Supplied dependency-first traversal, not priority or scientific readiness'
                     if include_prerequisites else 'Selected work or lexical work ID order; not execution order'),
        boundary=('Only explicit transitive depends_on links are expanded. Completed prerequisites remain visible. '
                  'Shared evidence, context or ranks do not add dependencies. No work is executed, approved or reprioritized. '
                  'A dependency-unblocked task may retain source, experimental, clinical and appraisal gaps. '
                  'Direct prerequisite completion-source labels are not recursive acceptance certificates and do not change blocking.'))
    packets = []
    for wid in selected:
        item = work[wid]
        evidence_ids = set(item['evidence_ids'])
        result_rows, source_indices = [], set()
        source_inputs = []
        for ref in item.get('source_refs', []):
            if ref['kind'] == 'planned_search':
                planned = planned_searches[ref['search_id']]
                indices = copy.deepcopy(search_indices_by_id.get(ref['search_id'],[]))
                source_indices.update(indices)
                source_inputs.append(dict(reference=copy.deepcopy(ref), planned_search=copy.deepcopy(planned),
                                          observed_search_indices=indices, scope='declared_search_not_source_completion'))
            else:
                rid = ref['record_id']
                occurrences = copy.deepcopy(provenance[rid])
                source_indices.update(row['search_index'] for row in occurrences)
                source_inputs.append(dict(reference=copy.deepcopy(ref), search_occurrences=occurrences,
                                          screening=copy.deepcopy(screening.get(rid)),report=copy.deepcopy(report_by_record.get(rid)),
                                          existing_result_ids=sorted(result_ids_by_record.get(rid,[])),
                                          scope='enumerated_record_not_eligibility_or_extraction_approval'))
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
            work_type=item.get('work_type','evidence_review'),source_review_inputs=source_inputs,
            source_input_counts=dict(planned_searches=sum(ref['kind']=='planned_search' for ref in item.get('source_refs',[])),
                                     enumerated_records=sum(ref['kind']=='record' for ref in item.get('source_refs',[]))),
            completion_review=copy.deepcopy(completion[wid]), planning_assertion=copy.deepcopy(planning[wid]), planning_review_target=copy.deepcopy(planning_targets[wid]),
            dependencies=[copy.deepcopy(work[dependency]) for dependency in item['depends_on']],
            direct_prerequisite_completion_reviews=[dict(copy.deepcopy(completion[dependency]),
                supplied_work_status=work[dependency]['status']) for dependency in item['depends_on']],
            results=result_rows, sources=source_rows, contexts=context_rows, appraisals=appraisal_rows,
            synthesis_stage=research['synthesis']['stage'],
            claim_positions=[dict(statement=copy.deepcopy(statement),
                                  work_evidence_ids=sorted(evidence_ids.intersection(statement['evidence_ids'])),
                                  other_statement_evidence_ids=sorted(set(statement['evidence_ids'])-evidence_ids),
                                  work_positions=[copy.deepcopy(position) for position in statement.get('evidence_positions', []) if position['evidence_id'] in evidence_ids],
                                  position_stage='SUPPLIED' if 'evidence_positions' in statement else 'NOT_SUPPLIED',
                                  scope='full_statement_review_with_only_work_linked_positions_selected')
                             for statement in research['synthesis']['statement_ledger'] if evidence_ids.intersection(statement['evidence_ids'])],
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
                source_review_missing_searches=sorted(row['reference']['search_id'] for row in source_inputs if row['reference']['kind']=='planned_search' and not row['observed_search_indices']),
                units_without_outcome_statistics=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if 'outcome_statistics' not in unit and evidence_ids.intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else None,
                units_with_statistics_review_cues=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if (unit.get('statistics_review', {}).get('missing_fields') or unit.get('statistics_review', {}).get('literal_label_differences')) and evidence_ids.intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else None,
                units_without_outcome_sampling=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if 'outcome_sampling' not in unit and evidence_ids.intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else None,
                units_with_unresolved_sampling=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if unit.get('sampling_review', {}).get('unresolved_fields') and evidence_ids.intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else None,
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
                engine_sha256=implementation, selection=work_package_id, dependency_review=dependency_scope,
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



def navigation_summary(result):
    """Compact projection of existing packet assertions, never generated priorities."""
    groups={'unblocked_planned':[], 'unblocked_in_progress':[], 'blocked_unfinished':[], 'completed_assertions':[]}
    rows=[]
    for packet in result['packets']:
        work=packet['work_package'];wid=work['work_package_id']
        group=('completed_assertions' if work['status']=='COMPLETE' else
               'blocked_unfinished' if work['blocked_by'] else
               'unblocked_in_progress' if work['status']=='IN_PROGRESS' else 'unblocked_planned')
        groups[group].append(wid)
        gaps=copy.deepcopy(packet['recorded_review_gaps'])
        # Retain null vs empty: absent stages are not zero outstanding work.
        rows.append(dict(work_package_id=wid,work_type=packet['work_type'],status=work['status'],
                         question=work['question'],deliverable=work['deliverable'],acceptance_criterion=work['acceptance_criterion'],
                         depends_on=copy.deepcopy(work['depends_on']),blocked_by=copy.deepcopy(work['blocked_by']),
                         artifact_locator=work.get('artifact_locator'),acceptance_verified=work.get('acceptance_verified'),
                         planning=copy.deepcopy(packet['planning_assertion']),completion_review=copy.deepcopy(packet['completion_review']),recorded_review_gaps=gaps,
                         source_review_inputs=copy.deepcopy(packet['source_review_inputs']),
                         direct_prerequisite_completion_reviews=[{key:row[key] for key in
                             ('work_package_id','supplied_work_status','source_match_status')}
                             for row in packet['direct_prerequisite_completion_reviews']],
                         statement_review_statuses=[dict(statement_id=row['statement']['statement_id'],
                             source_match_status=row['statement']['source_match_status'],support_status=row['statement']['support_status'],
                             position_stage=row['position_stage'],
                             work_positions=[{key:p[key] for key in ('evidence_id','claim_component','aspect','relation')} for p in row['work_positions']],
                             other_statement_evidence_ids=copy.deepcopy(row['other_statement_evidence_ids'])) for row in packet['claim_positions']],
                         scope_counts=copy.deepcopy(packet['scope_counts'])))
    return dict(selection=result['selection'],dependency_review=copy.deepcopy(result['dependency_review']),
                work_state_groups={key:sorted(ids) for key,ids in groups.items()},work=rows,
                global_search_plan_audit=copy.deepcopy(result['global_search_plan_audit']),
                protocol_sha256=result['protocol_sha256'],
                boundary=('Packet-scope navigation only; group names describe recorded status and dependencies, not a next-task recommendation. '
                          'No ranking, ownership, deadlines, clinical readiness or acceptance assessment is inferred. '
                          'Completed work may still have evidence gaps or stale prerequisite assertions. Direct prerequisite labels are not recursive acceptance. Empty cues are omitted from brief text, not a completeness finding. '
                          'Full supplied evidence, context and experimental details remain in the normal packet output.'))


def render_brief(result):
    summary=navigation_summary(result);show=quoted_display
    lines=['Work review navigation (no automated next-task decision)',
           'Protocol SHA-256: '+summary['protocol_sha256'],
           'Selected packet scope: '+show(summary['dependency_review']),
           'Recorded work-state groups (IDs sorted, not ranked): '+show(summary['work_state_groups']),
           'Protocol-wide search plan status: '+show({key:summary['global_search_plan_audit'].get(key) for key in ('plan_status','missing_search_ids','incomplete_search_ids')})]
    for row in summary['work']:
        lines.extend(['', 'Work: '+show(row['work_package_id'])+'; supplied status: '+show(row['status']),
                      'Work type: '+show(row['work_type']), 'Question: '+show(row['question']), 'Deliverable: '+show(row['deliverable']),
                      'Acceptance criterion: '+show(row['acceptance_criterion']),
                      'Depends on: '+show(row['depends_on'])+'; blocked by: '+show(row['blocked_by']),
                      'Supplied artifact/acceptance (not checked): '+show(dict(artifact_locator=row['artifact_locator'],acceptance_verified=row['acceptance_verified'])),
                      'Completion source status (not acceptance): '+show(row['completion_review']['source_match_status']),
                      'Direct prerequisite completion sources (not acceptance): '+show(row['direct_prerequisite_completion_reviews']),
                      'Planning source status: '+show(row['planning']['source_match_status'])])
        assertion=row['planning']['assertion']
        if assertion is not None:
            lines.append('Supplied planning rationale/uncertainty: '+show({key:assertion[key] for key in ('rationale','uncertainty')}))
            lines.append('Supplied rationale statement IDs (not support): '+show(assertion.get('rationale_statement_ids')))
        lines.append('Recorded nonempty review cues: '+show({k:v for k,v in row['recorded_review_gaps'].items() if v}))
        lines.append('Review cue stages not supplied: '+show([k for k,v in row['recorded_review_gaps'].items() if v is None]))
        for source in row['source_review_inputs']:
            if source['reference']['kind']=='planned_search':
                lines.append('Source reference/supplied search indices: '+show(dict(reference=source['reference'],observed_search_indices=source['observed_search_indices'])))
            else:
                lines.append('Source record stage assertions: '+show(dict(reference=source['reference'],screening=source['screening'],report=source['report'],existing_result_ids=source['existing_result_ids'])))
        lines.append('Statement review assertions (not support): '+show(row['statement_review_statuses']))
    lines.extend(['',summary['boundary'],'Census: NOT_ESTABLISHED','Conclusion: NOT_READY'])
    return '\n'.join(lines)+'\n'


def render_text(result):
    show = quoted_display
    plan_supplied = result['global_search_plan_audit']['plan_status'] != 'NOT_SUPPLIED'
    lines = ['Work-package review packets', 'Question: ' + show(result['question']),
             'Protocol version: ' + show(result['protocol_version']),
             'Dependency review scope: ' + show(result['dependency_review']),
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
                      'Completion source binding (not acceptance): ' + show(packet['completion_review']),
                      'Direct prerequisite completion sources (not acceptance): ' + show(packet['direct_prerequisite_completion_reviews']),
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
        lines.append('Work type: ' + packet['work_type'])
        lines.append('Source review inputs (not extracted evidence): ' + show(packet['source_review_inputs']))
        lines.append('Source input counts, separate from result scope: ' + show(packet['source_input_counts']))
        lines.append('Supplied synthesis stage: ' + packet['synthesis_stage'])
        lines.append('Supplied claim positions and linkage scope: ' + show(packet['claim_positions']))
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
    parser.add_argument('--include-prerequisites', action='store_true', help='include all explicit transitive prerequisites of the selected work in dependency-first order')
    formatting=parser.add_mutually_exclusive_group()
    formatting.add_argument('--text', action='store_true', help='render a detailed text review packet')
    formatting.add_argument('--brief', action='store_true', help='render compact work-state, deliverable and review-cue navigation')
    args = parser.parse_args()
    try:
        result = review_packets(parse_json(args.protocol.read_bytes()), args.work_package, args.include_prerequisites)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(render_brief(result) if args.brief else render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2), end='' if args.text or args.brief else '\n')


if __name__ == '__main__':
    main()
