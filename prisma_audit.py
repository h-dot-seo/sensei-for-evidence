"""Export auditable supplied-data accounting, not a certified PRISMA flow diagram."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from collections import defaultdict
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import engine_hashes
from report_links import report_study_ids
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display

BOUNDARY = ('PRISMA-oriented supplied-data accounting export, not a PRISMA-standard interchange '
            'format, compliance certificate or final systematic review. Occurrences, exact record IDs, '
            'reports, supplied study IDs and result rows are distinct units. Matching partitions prove '
            'only bookkeeping over supplied inputs, not search completeness, identity, full-text access, '
            'independence, evidence adequacy or clinical validity. No sources are retrieved or authenticated.')



def work_traceability(research, record_ids, report_rows, report_supplied):
    """Reverse only explicit typed links; never expand search work into record work."""
    planned=defaultdict(set); records=defaultdict(set); results=defaultdict(set)
    evidence_records=defaultdict(set); work=[]
    evidence_by_id={row['evidence_id']:row for row in research['evidence']}
    for index,item in enumerate(research['work_packages']):
        wid=item['work_package_id']
        for ref in item.get('source_refs',[]):
            if ref['kind']=='planned_search':planned[ref['search_id']].add(wid)
            else:records[ref['record_id']].add(wid)
        for eid in item['evidence_ids']:
            results[eid].add(wid)
            evidence_records[evidence_by_id[eid]['record_id']].add(wid)
        work.append(dict(work_package=copy.deepcopy(item),input_pointer=f'/gaps/{index}',
                         work_type=item.get('work_type','evidence_review'),
                         artifact_status='LOCATOR_SUPPLIED' if item.get('artifact_locator') else 'NOT_SUPPLIED',
                         artifact_verification='NOT_PERFORMED',acceptance_assessment='NOT_PERFORMED'))
    indices=defaultdict(list)
    for i,row in enumerate(research['search_ledger']):
        if isinstance(row.get('search_id'),str):indices[row['search_id']].append(i)
    plan=research['search_plan_audit']
    return dict(
        work_packages=work,
        planned_search_links=None if plan['plan_status']=='NOT_SUPPLIED' else [
            dict(search_id=row['search_id'],observed_search_indices=indices[row['search_id']],
                 direct_source_work_ids=sorted(planned[row['search_id']])) for row in plan['search_plan_ledger']],
        record_links=[dict(record_id=rid,direct_source_work_ids=sorted(records[rid]),
                           via_result_work_ids=sorted(evidence_records[rid])) for rid in sorted(record_ids)],
        result_links=[dict(evidence_id=eid,direct_evidence_work_ids=sorted(results[eid])) for eid in sorted(evidence_by_id)],
        report_links=None if not report_supplied else [
            dict(report_id=row['report_id'],record_links=[
                dict(record_id=rid,via_record_source_work_ids=sorted(records[rid]),
                     via_record_result_work_ids=sorted(evidence_records[rid])) for rid in sorted(row['record_ids'])])
            for row in sorted(report_rows,key=lambda row:row['report_id'])],
        boundary=('Explicit work references and supplied artifact assertions only. Report links are indirect via named records. '
                  'Planned-search work is not inherited by its records; record-source work is not evidence-result work. '
                  'Empty links mean no such supplied reference, not a required or completed task. Artifact locators are not opened '
                  'or authenticated. COMPLETE and acceptance_verified do not approve receipts, screening, extraction or science. '
                  'No task coverage, source completeness or deliverable adequacy is assessed.'))


def export_audit(protocol):
    research=run(protocol)
    reports=report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    occurrences=[]; retained=[]; repeated=[]; first={}; occurrences_by_record=defaultdict(list)
    for si,search in enumerate(protocol['searches']):
        for ri,rid in enumerate(search['record_ids']):
            pointer=f'/searches/{si}/record_ids/{ri}'
            item=dict(occurrence_id=pointer,record_id=rid,search_index=si,search_id=search.get('search_id'),source=search['source'])
            occurrences.append(item)
            occurrences_by_record[rid].append(pointer)
            if rid in first: repeated.append(dict(item,retained_occurrence_id=first[rid]))
            else: first[rid]=pointer;retained.append(item)
    screening={row['record_id']:dict(row,input_pointer=f'/screening/{i}') for i,row in enumerate(protocol['screening'])}
    report_rows=[] if reports is None else [dict(copy.deepcopy(row),input_pointer=f'/reports/{i}') for i,row in enumerate(protocol['reports'])]
    by_record={rid:row for row in report_rows for rid in row['record_ids']}
    evidence=[dict(evidence_id=row['evidence_id'],record_id=row['record_id'],study_id=row['study_id'],locator=row['locator'],input_pointer=f'/evidence/{i}') for i,row in enumerate(research['evidence'])]
    evidence_by_record=defaultdict(list); evidence_by_study=defaultdict(list); reports_by_study=defaultdict(list)
    for row in evidence:
        evidence_by_record[row['record_id']].append(row['evidence_id'])
        evidence_by_study[row['study_id']].append(row['evidence_id'])
    for row in report_rows:
        for study_id in report_study_ids(row): reports_by_study[study_id].append(row['report_id'])
    all_records=set(first); included={rid for rid,row in screening.items() if row['decision']=='include'}
    excluded={rid for rid,row in screening.items() if row['decision']=='exclude'}
    extracted_reports={by_record[row['record_id']]['report_id'] for row in evidence} if reports is not None else set()
    nodes=[]
    def node(name,unit,members,scope):
        nodes.append(dict(node_id=name,unit=unit,stage='NOT_SUPPLIED' if members is None else 'SUPPLIED',
                          count=None if members is None else len(members),member_ids=None if members is None else sorted(members),scope=scope))
    node('identified_occurrences','record_occurrence',[r['occurrence_id'] for r in occurrences],'All supplied search-row occurrences, not all existing literature')
    node('retained_occurrences','record_occurrence',[r['occurrence_id'] for r in retained],'First occurrence in supplied search order for each exact record ID; not verified publication identity')
    node('repeated_exact_id_occurrences','record_occurrence',[r['occurrence_id'] for r in repeated],'Repeated identical supplied IDs only; no fuzzy deduplication')
    node('unique_records','record',all_records,'Distinct exact supplied record IDs')
    node('screened_records','record',set(screening),'Supplied title/abstract eligibility decisions')
    node('screening_pending_records','record',all_records-set(screening),'Supplied records without a screening decision')
    node('included_records','record',included,'Title/abstract-included records, not full-text included reports')
    node('excluded_records','record',excluded,'Title/abstract-excluded records with supplied reasons')
    node('mapped_included_records','record',set(by_record) if reports is not None else None,'Included records explicitly mapped to reports')
    node('unmapped_included_records','record',included-set(by_record) if reports is not None else None,'Included records lacking report identity mapping')
    selectors={
        'reports_sought': lambda r:True,
        'reports_retrieved': lambda r:r['retrieval']=='retrieved',
        'reports_not_retrieved': lambda r:r['retrieval']=='not_retrieved',
        'reports_retrieval_pending': lambda r:r['retrieval']=='pending',
        'reports_assessed': lambda r:r['retrieval']=='retrieved' and r.get('decision','pending') in ('include','exclude'),
        'reports_assessment_pending': lambda r:r['retrieval']=='retrieved' and r.get('decision','pending')=='pending',
        'reports_included': lambda r:r.get('decision','pending')=='include',
        'reports_excluded': lambda r:r.get('decision','pending')=='exclude',
        'included_reports_with_extraction': lambda r:r['report_id'] in extracted_reports,
        'included_reports_without_extraction': lambda r:r.get('decision','pending')=='include' and r['report_id'] not in extracted_reports,
    }
    for name,predicate in selectors.items():
        node(name,'report',{r['report_id'] for r in report_rows if predicate(r)} if reports is not None else None,'Supplied report ledger; missing/default decisions remain pending')
    included_studies={sid for r in report_rows for sid in report_study_ids(r)} if reports is not None else None
    node('included_studies','supplied_study_id',included_studies,'Distinct study IDs on included reports, not independently verified study identity')
    node('extracted_result_rows','result',{r['evidence_id'] for r in evidence},'Distinct result IDs, not studies or independent observations')
    node('records_with_extraction','record',{r['record_id'] for r in evidence},'Records with at least one supplied result, not exhaustive extraction')
    node('included_records_without_extraction','record',included-set(evidence_by_record),'Title/abstract-included records without result rows; not a full-text extraction task list')
    node('studies_with_extraction','supplied_study_id',{r['study_id'] for r in evidence},'Supplied study IDs represented by at least one result')
    membership_coverage = reports.get('report_study_coverage') if reports is not None else None
    if membership_coverage is not None:
        memberships = membership_coverage['membership_ledger']
        for name, selected in (
                ('included_report_study_memberships', memberships),
                ('report_study_memberships_with_results', [r for r in memberships if r['has_result_rows']]),
                ('report_study_memberships_without_results', [r for r in memberships if not r['has_result_rows']])):
            node(name, 'report_study_membership', [r['membership_id'] for r in selected],
                 'Explicit supplied report-study pair; any result presence is not exhaustive extraction or study independence')
    nodes_by_id={r['node_id']:r for r in nodes}
    checks=[]
    partitions = [('identified_occurrences',['retained_occurrences','repeated_exact_id_occurrences']),
                            ('unique_records',['screened_records','screening_pending_records']),
                            ('screened_records',['included_records','excluded_records']),
                            ('included_records',['mapped_included_records','unmapped_included_records']),
                            ('included_records',['records_with_extraction','included_records_without_extraction']),
                            ('reports_sought',['reports_retrieved','reports_not_retrieved','reports_retrieval_pending']),
                            ('reports_retrieved',['reports_assessed','reports_assessment_pending']),
                            ('reports_assessed',['reports_included','reports_excluded']),
                            ('reports_included',['included_reports_with_extraction','included_reports_without_extraction'])]
    if membership_coverage is not None:
        partitions.append(('included_report_study_memberships', ['report_study_memberships_with_results','report_study_memberships_without_results']))
    for parent,children in partitions:
        whole=nodes_by_id[parent];parts=[nodes_by_id[k] for k in children]
        available=whole['count'] is not None and all(p['count'] is not None for p in parts)
        if available:
            members=[member for part in parts for member in part['member_ids']]
            matched=(all(part['unit']==whole['unit'] for part in parts) and len(members)==len(set(members)) and set(members)==set(whole['member_ids']))
            if not matched:raise ValueError('internal supplied-membership partition mismatch: '+parent)
        checks.append(dict(parent_node=parent,child_nodes=children,unit=whole['unit'],
                           status='RECORDED_MEMBERS_PARTITION' if available else 'NOT_SUPPLIED',
                           parent_count=whole['count'],children_total=sum(p['count'] for p in parts) if available else None,
                           scope='Disjoint member-ID partition only; not a readiness or scientific check'))
    def reasons(rows,unit,id_key):
        groups=defaultdict(list)
        for row in rows:groups[row['reason']].append(row[id_key])
        return [dict(reason=reason,unit=unit,count=len(ids),member_ids=sorted(ids)) for reason,ids in sorted(groups.items())]
    record_ledger=[dict(record_id=rid,retained_occurrence_id=first[rid],
                        occurrence_ids=copy.deepcopy(occurrences_by_record[rid]),
                        screening=copy.deepcopy(screening.get(rid)),report_id=by_record[rid]['report_id'] if rid in by_record else None,
                        evidence_ids=sorted(evidence_by_record[rid])) for rid in sorted(all_records)]
    studies=sorted(set(r['study_id'] for r in evidence)|(included_studies or set()))
    study_links=[dict(study_id=sid,included_report_ids=None if reports is None else sorted(reports_by_study[sid]),
                      evidence_ids=sorted(evidence_by_study[sid])) for sid in studies]
    implementation=dict(engine_hashes(),**{'prisma_audit.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    result = dict(schema_version=1,question=research['question'],protocol_version=research['protocol_version'],
                protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                hash_scope='Canonical supplied JSON; key order ignored, list order retained; not source authenticity',engine_sha256=implementation,
                report_stage='NOT_SUPPLIED' if reports is None else 'SUPPLIED',nodes=nodes,partition_checks=checks,
                search_plan_audit=copy.deepcopy(research['search_plan_audit']),
                searches=[dict(search_index=i,input_pointer=f'/searches/{i}',search=copy.deepcopy(row),accounting=copy.deepcopy(research['coverage'][i])) for i,row in enumerate(research['search_ledger'])],
                occurrence_ledger=occurrences,repeated_occurrence_links=repeated,record_ledger=record_ledger,
                report_ledger=None if reports is None else report_rows,evidence_links=evidence,study_links=study_links,
                work_traceability=work_traceability(research,all_records,report_rows,reports is not None),
                reasons=dict(record_exclusions=reasons([r for r in screening.values() if r['decision']=='exclude'],'record','record_id'),
                             report_exclusions=None if reports is None else reasons([r for r in report_rows if r.get('decision')=='exclude'],'report','report_id'),
                             reports_not_retrieved=None if reports is None else reasons([r for r in report_rows if r['retrieval']=='not_retrieved'],'report','report_id')),
                extraction_completeness='NOT_ESTABLISHED',record_identity_verification='NOT_ESTABLISHED',
                census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',boundary=BOUNDARY)
    if 'bibliographic_collection' in research:
        result['bibliographic_collection'] = copy.deepcopy(research['bibliographic_collection'])
        collection_rows = result['bibliographic_collection']['row_ledger']
        for row in result['record_ledger']:
            row['bibliographic_row_pointers'] = [item['source_pointer'] for item in collection_rows
                                                if item['resolution']['record_id'] == row['record_id']]
    context_pointers = {row['context_id']:f'/contexts/{index}' for index,row in enumerate(protocol.get('contexts', []))}
    source_contexts = [dict(context=copy.deepcopy(row), input_pointer=context_pointers[row['context_id']],
                            explicit_work_ids=sorted(work['work_package_id'] for work in research['work_packages']
                                                     if row['context_id'] in work.get('context_ids', [])),
                            scope='explicit_source_context_links_not_result_or_work_coverage')
                       for row in research['context']['context_ledger'] if row.get('context_scope') == 'source_review']
    if source_contexts:
        result['source_context_ledger'] = source_contexts
    if membership_coverage is not None:
        result['report_study_coverage'] = copy.deepcopy(membership_coverage)
    if 'screening_review' in research:
        result['screening_review'] = copy.deepcopy(research['screening_review'])
    if 'report_review' in research:
        result['report_review'] = copy.deepcopy(research['report_review'])
    if 'report_study_review' in research:
        result['report_study_review'] = copy.deepcopy(research['report_study_review'])
    if 'report_study_inventory' in research:
        result['report_study_inventory'] = copy.deepcopy(research['report_study_inventory'])
    if 'report_study_inventory_review' in research:
        result['report_study_inventory_review'] = copy.deepcopy(research['report_study_inventory_review'])
    if 'screening_decision_history' in research:
        result['screening_decision_history'] = copy.deepcopy(research['screening_decision_history'])
    return result


def render_text(result):
    show=quoted_display
    lines=['Supplied-data PRISMA accounting audit', 'Question: '+show(result['question']),
           'Protocol SHA-256: '+result['protocol_sha256'],'Report stage: '+result['report_stage']]
    for node in result['nodes']:
        lines.append(node['node_id']+' ['+node['unit']+']: '+('not supplied' if node['count'] is None else str(node['count'])))
    if 'bibliographic_collection' in result:
        lines.extend(['Local CSV collection rows (distinct from search-membership occurrence nodes): '
                      + show(result['bibliographic_collection']['counts']),
                      'Full collection row provenance, supplied identity choices and withheld rows remain in JSON; identity is not verified.'])
    if 'source_context_ledger' in result:
        lines.append('Pre-extraction source contexts (not evidence or applicability): ' + show(result['source_context_ledger']))
    if 'report_study_coverage' in result:
        lines.append('Explicit report-study membership coverage (not exhaustive extraction): ' + show(result['report_study_coverage']))
    if 'screening_review' in result:
        lines.extend(['Supplied screening reviewer positions (not adjudication): ' + show(result['screening_review']['record_review_ledger']),
                      result['screening_review']['boundary']])
    if 'report_study_inventory' in result:
        lines.extend(['Supplied descriptive study inventory (not inclusion or pending work): '
                      + show(result['report_study_inventory']['pair_inventory_ledger']),
                      result['report_study_inventory']['boundary']])
    if 'report_study_review' in result:
        lines.extend(['Supplied report-study human positions (not canonical study selection): '
                      + show(result['report_study_review']['membership_review_ledger']),
                      result['report_study_review']['boundary']])
    if 'report_study_inventory_review' in result:
        lines.extend(['Supplied inventory-candidate positions (not canonical study selection): '
                      + show(result['report_study_inventory_review']['candidate_review_ledger']),
                      result['report_study_inventory_review']['boundary']])
    if 'report_review' in result:
        lines.extend(['Supplied full-text report review positions (not document verification): '
                      + show(result['report_review']['report_review_ledger']),
                      result['report_review']['boundary']])
    if 'screening_decision_history' in result:
        lines.extend(['Supplied screening decision history (retrospective comparisons, not pending tasks): '
                      + show(result['screening_decision_history']['record_history']),
                      result['screening_decision_history']['boundary']])
    lines.extend(['Partition checks (not completeness): '+show(result['partition_checks']),
                  'Reason groups: '+show(result['reasons']),'Declared search accounting: '+show(result['search_plan_audit']),
                  'Work and deliverable traceability (not task coverage): '+show(result['work_traceability']),
                  'Full member IDs, input pointers and link ledgers are available in default JSON output.',
                  'Census: NOT_ESTABLISHED','Conclusion: NOT_READY',result['boundary']])
    return '\n'.join(lines)+'\n'


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol',type=Path);parser.add_argument('--text',action='store_true')
    args=parser.parse_args()
    try:result=export_audit(parse_json(args.protocol.read_text(encoding='utf-8')))
    except (ValueError,OSError,KeyError,TypeError) as error:parser.exit(1,str(error)+'\n')
    print(render_text(result) if args.text else json.dumps(result,ensure_ascii=False,indent=2),end='' if args.text else '\n')

if __name__=='__main__':main()
