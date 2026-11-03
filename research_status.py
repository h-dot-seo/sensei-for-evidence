"""Summarize mechanical review queues from a validated supplied protocol."""
import argparse
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
    reports = report_flow(protocol) if 'reports' in protocol else None
    records = {rid for row in protocol['searches'] for rid in row['record_ids']}
    screened = {row['record_id'] for row in protocol['screening']}
    plan = research['search_plan_audit']
    report_ledger = reports['report_ledger'] if reports is not None else []
    work = research['work_packages']
    queues = dict(
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
        completed_work_assertions=sorted(row['work_package_id'] for row in work if row['status'] == 'COMPLETE'),
    )
    counts = {key: None if rows is None else len(rows) for key, rows in queues.items()}
    implementation = dict(engine_hashes(), **{'research_status.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return dict(question=research['question'], protocol_version=research['protocol_version'],
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


def render_text(result):
    def count(key):
        value = result['counts'][key]
        return 'not supplied' if value is None else str(value)
    labels = [
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
    ]
    lines = ['Supplied research status', 'Search plan: ' + result['search_plan_status']]
    lines.extend(label + ': ' + count(key) for label, key in labels)
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
