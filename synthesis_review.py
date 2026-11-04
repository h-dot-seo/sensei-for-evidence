"""Create a PRISMA-oriented supplied-data and synthesis-citation review snapshot."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from prisma_reports import report_flow
from research_status import status
from research_bundle import engine_hashes
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display

BOUNDARY = ('PRISMA-oriented supplied-data snapshot, not a final systematic review or claim '
            'of PRISMA compliance. Record occurrences, reports, supplied study IDs and result '
            'rows are different units. Citations are result-level links, not verified bibliography '
            'or proof that a statement is supported. Missing stages and review limits remain '
            'explicit; empty queues do not establish census, exhaustive extraction or clinical validity.')


def snapshot(protocol):
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    queues = status(protocol)
    synthesis = research['synthesis']
    supplied = synthesis['stage'] == 'SUPPLIED'
    screening = {row['record_id']: row for row in research['screening_ledger']}
    occurrences = {row['record_id']: row['occurrences'] for row in research['record_provenance']}
    report_by_record = {rid: report for report in reports['report_ledger'] for rid in report['record_ids']} if reports else {}
    appraisal_links = {row['evidence_id']: row['appraisal_ids'] for row in research['appraisal']['evidence_appraisal_links']}
    contexts = {row['context_id']: row for row in research['context']['context_ledger']}
    candidate_receipts = {row['sha256']: row for row in protocol.get('adapter_receipts', {}).get('receipts', [])
                          if row['target_type'] == 'extraction'}
    experiment_links = {row['evidence_id']: row['experiment_id'] for row in research['experiments']['evidence_links']}
    citations = {}
    for evidence in research['evidence']:
        eid, rid = evidence['evidence_id'], evidence['record_id']
        candidate = candidate_receipts.get(evidence.get('adapter_provenance', {}).get('receipt_sha256'), {}).get('candidate')
        support = None if candidate is None else {key: candidate[key] for key in
            ('candidate_id', 'request_id', 'source_locator', 'supporting_quote', 'extractor_id', 'extractor_version')}
        citations[eid] = dict(evidence=copy.deepcopy(evidence), experiment_id=experiment_links[eid], adapter_candidate_support=support, screening=copy.deepcopy(screening[rid]),
            report=copy.deepcopy(report_by_record.get(rid)),
            search_sources=[dict(occurrence=copy.deepcopy(row),
                                 search=copy.deepcopy(research['search_ledger'][row['search_index']]),
                                 accounting=copy.deepcopy(research['coverage'][row['search_index']])) for row in occurrences[rid]],
            appraisal_ids=copy.deepcopy(appraisal_links[eid]),
            work_package_ids=sorted(work['work_package_id'] for work in research['work_packages'] if eid in work['evidence_ids']))
    statements = []
    for statement in synthesis['statement_ledger']:
        refs = set(statement['evidence_ids'])
        statements.append(dict(statement=copy.deepcopy(statement),
            citations=[copy.deepcopy(citations[eid]) for eid in statement['evidence_ids']],
            experimental_gap_scope='full_intersecting_condition_records_including_other_outcomes',
            experimental_units=[dict(experimental_unit=copy.deepcopy(unit),
                                     cited_evidence_ids=sorted(refs.intersection(unit['evidence_ids'])),
                                     other_experiment_evidence_ids=sorted(set(unit['evidence_ids'])-refs))
                                for unit in research['experiments']['experimental_unit_ledger'] if refs.intersection(unit['evidence_ids'])],
            contexts=[dict(context=copy.deepcopy(contexts[cid]),
                           cited_evidence_ids=sorted(refs.intersection(contexts[cid]['evidence_ids'])),
                           other_context_evidence_ids=sorted(set(contexts[cid]['evidence_ids'])-refs)) for cid in statement['context_ids']],
            appraisals=[dict(appraisal=copy.deepcopy(row),
                             cited_evidence_ids=sorted(refs.intersection(row['evidence_ids'])),
                             other_appraisal_evidence_ids=sorted(set(row['evidence_ids'])-refs))
                        for row in research['appraisal']['appraisal_ledger'] if refs.intersection(row['evidence_ids'])]))
    implementation = dict(engine_hashes())
    for name in ('synthesis_review.py', 'research_status.py'):
        implementation[name] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
    result = dict(schema_version=1, question=research['question'], protocol_version=research['protocol_version'],
        protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
        hash_scope='sorted compact UTF-8 JSON; object key order ignored and list order retained; not authentication',
        engine_sha256=implementation,
        search_ledger=copy.deepcopy(research['search_ledger']), search_coverage=copy.deepcopy(research['coverage']),
        screening_ledger=copy.deepcopy(research['screening_ledger']),
        report_ledger=copy.deepcopy(reports['report_ledger']) if reports is not None else None,
        record_extraction_scope=research['extraction_pending_scope'],
        record_flow=copy.deepcopy(research['flow']), report_stage='SUPPLIED' if reports is not None else 'NOT_SUPPLIED',
        report_flow=copy.deepcopy(reports['report_flow']) if reports is not None else None,
        full_text_exclusion_reasons=copy.deepcopy(reports['exclusion_reasons']) if reports is not None else None,
        search_plan_audit=copy.deepcopy(research['search_plan_audit']),
        review_queues=copy.deepcopy(queues['queues']), synthesis_stage=synthesis['stage'], statements=statements,
        statement_review_targets=copy.deepcopy(synthesis['review_targets']),
        evidence_citation_index=[citations[eid] for eid in sorted(citations)],
        evidence_without_statement_citation=None if not supplied else copy.deepcopy(synthesis['evidence_without_statement_citation']),
        experimental_stage=research['experiments']['stage'],
        experimental_unit_ledger=copy.deepcopy(research['experiments']['experimental_unit_ledger']),
        experiment_boundary=research['experiments']['boundary'],
        context_ledger=copy.deepcopy(research['context']['context_ledger']),
        appraisal_ledger=copy.deepcopy(research['appraisal']['appraisal_ledger']),
        deduplication_scope=research['deduplication_scope'], record_identity_verification='NOT_ESTABLISHED',
        extraction_completeness='NOT_ESTABLISHED', census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY',
        synthesis_boundary=synthesis['boundary'], boundary=BOUNDARY)
    if reports is not None and 'report_study_coverage' in reports:
        result['report_study_coverage'] = copy.deepcopy(reports['report_study_coverage'])
    if 'screening_review' in research:
        result['screening_review'] = copy.deepcopy(research['screening_review'])
    if 'screening_decision_history' in research:
        result['screening_decision_history'] = copy.deepcopy(research['screening_decision_history'])
    return result


def render_text(result):
    show = quoted_display
    records = result['record_flow']
    lines = ['PRISMA-oriented supplied-data and synthesis review snapshot',
             'Question: ' + show(result['question']), 'Protocol version: ' + show(result['protocol_version']),
             'Search-record occurrences: ' + str(records['identified']),
             'Distinct supplied record IDs: ' + str(records['unique_records']),
             'Repeated exact-ID occurrences: ' + str(records['duplicates']),
             'Screened records: ' + str(records['screened']),
             'Record screening pending: ' + str(records['pending']),
             'Excluded screening records: ' + str(records['excluded']),
             'Included screening records: ' + str(records['included']),
             'Extracted result rows: ' + str(records['extracted']),
             'Source records with extraction: ' + str(records['extracted_records']),
             'Supplied study IDs with extraction: ' + str(records['extracted_studies']),
             'Report/full-text stage: ' + result['report_stage']]
    if result['report_flow'] is not None:
        lines.append('Report counts (report units except included_studies): ' + show(result['report_flow']))
        lines.append('Full-text exclusion reasons (supplied report counts): ' + show(result['full_text_exclusion_reasons']))
    lines.append('Declared search plan accounting: ' + show(result['search_plan_audit']))
    lines.append('Supplied search receipts/accounting: ' + show(dict(searches=result['search_ledger'], coverage=result['search_coverage'])))
    lines.append('Record screening ledger: ' + show(result['screening_ledger']))
    lines.append('Report retrieval/full-text ledger: ' + show(result['report_ledger']))
    lines.append('Record-level extraction queue scope: ' + result['record_extraction_scope'])
    lines.append('Review queues (null means stage not supplied): ' + show(result['review_queues']))
    lines.append('Supplied synthesis stage: ' + result['synthesis_stage'])
    for item in result['statements']:
        lines.extend(['', 'Supplied synthesis statement: ' + show(item['statement']),
                      'Cited extraction/source trace: ' + show(item['citations']),
                      'Unresolved condition scope: ' + item['experimental_gap_scope'],
                      'Supplied comparison conditions and linkage scope: ' + show(item['experimental_units']),
                      'Explicit context linkage scope: ' + show(item['contexts']),
                      'Appraisal linkage scope: ' + show(item['appraisals'])])
    lines.append('Results without explicit statement citations: ' + show(result['evidence_without_statement_citation']))
    uncited = set(result['evidence_without_statement_citation'] or [])
    for row in result['evidence_citation_index']:
        if row['evidence']['evidence_id'] in uncited:
            lines.append('Uncited result/source trace: ' + show(row))
        elif result['synthesis_stage'] == 'NOT_SUPPLIED':
            lines.append('Result inventory (synthesis stage not supplied): ' + show(row))
    lines.append('Structured condition stage: ' + result['experimental_stage'])
    lines.append('Supplied condition record inventory (not replicate counts): ' + show(result['experimental_unit_ledger']))
    if 'report_study_coverage' in result:
        lines.append('Declared report-study membership coverage (not exhaustive extraction): '
                     + show(result['report_study_coverage']))
    if 'screening_review' in result:
        lines.extend(['Supplied screening reviewer positions (not adjudication): '
                      + show(result['screening_review']['record_review_ledger']),
                      result['screening_review']['boundary']])
    if 'screening_decision_history' in result:
        lines.extend(['Supplied screening decision history (not authenticated chronology): '
                      + show(result['screening_decision_history']['record_history']),
                      result['screening_decision_history']['boundary']])
    lines.extend(['Recorded context inventory: ' + show(result['context_ledger']),
                  'Recorded appraisal inventory: ' + show(result['appraisal_ledger']),
                  'Record identity: NOT_ESTABLISHED; exact supplied IDs only.',
                  'Extraction completeness: NOT_ESTABLISHED', 'Census: NOT_ESTABLISHED',
                  'Conclusion: NOT_READY', result['experiment_boundary'], result['synthesis_boundary'], result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        result = snapshot(parse_json(args.protocol.read_bytes()))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2), end='' if args.text else '\n')


if __name__ == '__main__':
    main()
