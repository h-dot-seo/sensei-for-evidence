"""Summarize mechanical review queues from a validated supplied protocol."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from evidence_workflow import run
from json_io import configure_utf8_stdio, parse_json, canonical_json_bytes
from prisma_reports import report_flow
from research_bundle import engine_hashes

BOUNDARY = ('Queues describe supplied data and operator assertions only. Dependency-unblocked '
            'work is not scientifically or clinically approved work. Missing appraisal is '
            'not a poor-quality judgement; no readiness, priority or source authenticity is inferred.')


def status(protocol):
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    records = {rid for row in protocol['searches'] for rid in row['record_ids']}
    screened = {row['record_id'] for row in protocol['screening']}
    plan = research['search_plan_audit']
    report_ledger = reports['report_ledger'] if reports is not None else []
    work = research['work_packages']
    queues = dict(
        statements_without_evidence_positions=research['synthesis']['statements_without_evidence_positions'],
        statements_with_unresolved_positions=research['synthesis']['statements_with_unresolved_positions'],
        units_without_outcome_statistics=research['experiments']['units_without_outcome_statistics'],
        units_with_statistics_review_cues=research['experiments']['units_with_statistics_review_cues'],
        units_without_outcome_sampling=research['experiments']['units_without_outcome_sampling'],
        units_with_unresolved_sampling=research['experiments']['units_with_unresolved_sampling'],
        evidence_without_experimental_unit=research['experiments']['evidence_without_experimental_unit'] if research['experiments']['stage'] == 'SUPPLIED' else None,
        units_with_unresolved_conditions=research['experiments']['units_with_unresolved_conditions'] if research['experiments']['stage'] == 'SUPPLIED' else None,
        pending_synthesis_statement_reviews=research['synthesis']['pending_statement_ids'] if research['synthesis']['stage'] == 'SUPPLIED' else None,
        stale_synthesis_statement_reviews=research['synthesis']['stale_statement_ids'] if research['synthesis']['stage'] == 'SUPPLIED' else None,
        evidence_without_statement_citation=research['synthesis']['evidence_without_statement_citation'] if research['synthesis']['stage'] == 'SUPPLIED' else None,
        work_without_planning_assertion=research['planning']['work_without_planning_assertion'],
        work_with_stale_planning_assertion=research['planning']['work_with_stale_planning_assertion'],
        missing_planned_searches=plan['missing_search_ids'] if plan['plan_status'] != 'NOT_SUPPLIED' else None,
        incomplete_searches=[dict(search_index=index, search_id=row['search_id'], source=row['source'], issues=row['issues'])
                             for index, row in enumerate(research['coverage']) if not row['complete']],
        records_pending_screening=sorted(records - screened),
        record_level_extraction_pending=research['extraction_pending'],
        unmapped_included_records=reports['unmapped_records'] if reports is not None else None,
        reports_pending_retrieval=sorted(row['report_id'] for row in report_ledger if row['retrieval'] == 'pending') if reports is not None else None,
        reports_not_retrieved=sorted(row['report_id'] for row in report_ledger if row['retrieval'] == 'not_retrieved') if reports is not None else None,
        reports_pending_assessment=sorted(row['report_id'] for row in report_ledger if row['retrieval'] == 'retrieved' and row.get('decision','pending') == 'pending') if reports is not None else None,
        included_reports_without_extraction=reports['extraction_pending_reports'] if reports is not None else None,
        context_review_pending=research['context']['review_pending'],
        evidence_without_recorded_appraisal=research['appraisal']['evidence_without_recorded_appraisal'],
        dependency_unblocked_planned_work=sorted(row['work_package_id'] for row in work if row['status'] == 'PLANNED' and not row['blocked_by']),
        blocked_work=[dict(work_package_id=row['work_package_id'], blocked_by=row['blocked_by']) for row in sorted(work,key=lambda row:row['work_package_id']) if row['blocked_by']],
        work_in_progress=sorted(row['work_package_id'] for row in work if row['status'] == 'IN_PROGRESS'),
        completed_work_without_source_binding=sorted(row['work_package_id'] for row in research['planning']['completion_ledger'] if row['source_match_status']=='UNBOUND_COMPLETION'),
        completed_work_with_stale_source_binding=sorted(row['work_package_id'] for row in research['planning']['completion_ledger'] if row['source_match_status']=='STALE_SOURCE'),
        completed_work_assertions=sorted(row['work_package_id'] for row in work if row['status'] == 'COMPLETE'),
    )
    if reports is not None and 'report_study_coverage' in reports:
        queues['report_study_memberships_without_results'] = copy.deepcopy(
            reports['report_study_coverage']['missing_report_study_memberships'])
    if 'screening_review' in research:
        queues['records_with_screening_review_cues'] = copy.deepcopy(
            research['screening_review']['records_with_review_cues'])
    if 'report_review' in research:
        queues['reports_with_review_cues'] = copy.deepcopy(
            research['report_review']['reports_with_review_cues'])
    if 'report_study_review' in research:
        queues['study_memberships_with_review_cues'] = copy.deepcopy(
            research['report_study_review']['current_memberships_with_review_cues'])
    if 'report_study_inventory_review' in research:
        queues['inventory_candidates_with_review_cues'] = copy.deepcopy(
            research['report_study_inventory_review']['current_candidates_with_review_cues'])
    counts = {key: None if rows is None else len(rows) for key, rows in queues.items()}
    implementation = dict(engine_hashes(), **{'research_status.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    result = dict(question=research['question'], protocol_version=research['protocol_version'],
                protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                hash_scope='sorted compact UTF-8 JSON; object key order ignored, list order retained; not an exact-byte receipt',
                engine_sha256=implementation, search_plan_status=plan['plan_status'],
                report_stage='SUPPLIED' if reports is not None else 'NOT_SUPPLIED',
                deduplication_scope=research['deduplication_scope'],
                record_identity_verification=research['record_identity_verification'],
                counts=counts, queues=queues,
                record_extraction_scope=research['extraction_pending_scope'],
                extraction_completeness='NOT_ESTABLISHED', census_claim='NOT_ESTABLISHED',
                conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    if 'report_study_inventory' in research:
        inventory = research['report_study_inventory']
        result['report_study_inventory'] = dict(
            stage=inventory['stage'], counts=copy.deepcopy(inventory['counts']),
            scope='supplied_descriptions_not_included_memberships_or_pending_tasks', boundary=inventory['boundary'])
    if 'report_study_inventory_review' in research:
        review = research['report_study_inventory_review']
        result['report_study_inventory_review'] = dict(
            stage=review['stage'], counts=copy.deepcopy(review['counts']),
            orphan_review_assertions=copy.deepcopy(review['orphan_review_assertions']),
            orphan_scope='unverified_retained_assertions_not_pending_tasks', boundary=review['boundary'])
    if 'report_study_review' in research:
        review = research['report_study_review']
        result['report_study_review'] = dict(
            stage=review['stage'], counts=copy.deepcopy(review['counts']),
            orphan_review_assertions=copy.deepcopy(review['orphan_review_assertions']),
            orphan_scope='unverified_retained_assertions_not_pending_tasks', boundary=review['boundary'])
    if 'screening_decision_history' in research:
        history = research['screening_decision_history']
        result['screening_decision_history'] = dict(
            stage=history['stage'], counts=copy.deepcopy(history['counts']),
            record_history=copy.deepcopy(history['record_history']),
            records_with_history_cues=copy.deepcopy(history['records_with_history_cues']),
            scope='retrospective_comparisons_not_pending_tasks', boundary=history['boundary'])
    return result


def render_text(result):
    def count(key):
        value = result['counts'][key]
        return 'not supplied' if value is None else str(value)
    labels = [
        ('Results without supplied comparison conditions', 'evidence_without_experimental_unit'),
        ('Condition records with unresolved fields', 'units_with_unresolved_conditions'),
        ('Condition records without outcome sampling metadata', 'units_without_outcome_sampling'),
        ('Condition records with unresolved sampling metadata', 'units_with_unresolved_sampling'),
        ('Condition records without outcome statistics metadata', 'units_without_outcome_statistics'),
        ('Condition records with statistics review cues', 'units_with_statistics_review_cues'),
        ('Statements without supplied evidence positions', 'statements_without_evidence_positions'),
        ('Statements with unclear or unassessed positions', 'statements_with_unresolved_positions'),
        ('Pending supplied synthesis reviews', 'pending_synthesis_statement_reviews'),
        ('Stale supplied synthesis reviews', 'stale_synthesis_statement_reviews'),
        ('Results without statement citations', 'evidence_without_statement_citation'),
        ('Work without supplied planning ranks', 'work_without_planning_assertion'),
        ('Work with stale planning source bindings', 'work_with_stale_planning_assertion'),
        ('Missing planned searches', 'missing_planned_searches'),
        ('Incomplete supplied searches', 'incomplete_searches'),
        ('Unscreened records', 'records_pending_screening'),
        ('Included records without a report mapping', 'unmapped_included_records'),
        ('Report retrieval pending', 'reports_pending_retrieval'),
        ('Reports not retrieved', 'reports_not_retrieved'),
        ('Full-text decisions pending', 'reports_pending_assessment'),
        ('Included reports without extraction', 'included_reports_without_extraction'),
        ('Context reviews pending', 'context_review_pending'),
        ('Result rows without recorded appraisal', 'evidence_without_recorded_appraisal'),
        ('Dependency-unblocked planned work', 'dependency_unblocked_planned_work'),
        ('Dependency-blocked work', 'blocked_work'),
        ('Work in progress', 'work_in_progress'),
        ('Completed work assertions', 'completed_work_assertions'),
        ('Completed work without source binding', 'completed_work_without_source_binding'),
        ('Completed work with stale source binding', 'completed_work_with_stale_source_binding'),
    ]
    lines = ['Supplied research status', 'Search plan: ' + result['search_plan_status']]
    lines.extend(label + ': ' + count(key) for label, key in labels)
    if 'report_study_memberships_without_results' in result['queues']:
        lines.append('Included report-study memberships without result rows: '
                     + count('report_study_memberships_without_results'))
        lines.append('Membership presence is not exhaustive extraction or independent study verification.')
    if 'records_with_screening_review_cues' in result['queues']:
        lines.append('Records with supplied screening-review cues: ' + count('records_with_screening_review_cues'))
        lines.append('Reviewer assertions do not adjudicate eligibility or replace recorded screening decisions.')
    if 'report_study_inventory' in result:
        lines.append('Supplied descriptive study inventory: '
                     + json.dumps(result['report_study_inventory']['counts'], sort_keys=True, ensure_ascii=True))
        lines.append('Inventory descriptions do not add included memberships, eligibility decisions or pending tasks.')
    if 'study_memberships_with_review_cues' in result['queues']:
        lines.append('Current report-study memberships with review cues: ' + count('study_memberships_with_review_cues'))
        lines.append('Retained orphan assertions: ' + str(len(result['report_study_review']['orphan_review_assertions']))
                     + '; retrospective supplied records, not proof of past membership or pending tasks.')
        lines.append('Study positions do not adjudicate report decisions or filter extracted results.')
    if 'inventory_candidates_with_review_cues' in result['queues']:
        lines.append('Described inventory candidates with supplied review cues: ' + count('inventory_candidates_with_review_cues'))
        lines.append('Retained orphan candidate assertions: '
                     + str(len(result['report_study_inventory_review']['orphan_review_assertions']))
                     + '; retrospective context, not pending selection tasks.')
        lines.append('Candidate positions do not create included memberships or verify descriptions, reading or eligibility.')
    if 'reports_with_review_cues' in result['queues']:
        lines.append('Reports with supplied full-text review cues: ' + count('reports_with_review_cues'))
        lines.append('Source digests and human positions are supplied assertions, not verified document bytes, reading or eligibility.')
    if 'screening_decision_history' in result:
        lines.append('Recorded screening decision history: '
                     + json.dumps(result['screening_decision_history']['counts'], sort_keys=True, ensure_ascii=True))
        lines.append('Historical differences are retrospective comparisons, not automatically unfinished work or invalid prior decisions.')
    if result['report_stage'] == 'NOT_SUPPLIED':
        lines.append('Title/abstract-included records without any result row: ' + count('record_level_extraction_pending'))
    lines.append('Record identity: exact supplied IDs only; identities not independently verified.')
    lines.extend(['Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY', result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--text', action='store_true', help='print a concise human-readable summary')
    args = parser.parse_args()
    try:
        result = status(parse_json(args.protocol.read_text(encoding='utf-8')))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
    print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2), end='' if args.text else '\n')


if __name__ == '__main__':
    main()
