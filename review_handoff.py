"""Build a read-only operator handoff from existing supplied-data review tools."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from json_io import configure_utf8_stdio, parse_json, quoted_display
from research_status import status
from work_review import review_packets
from synthesis_review import snapshot

# Display order is a navigation aid, never a scientific priority or execution order.
SPECS = {
    'missing_planned_searches': ('search_plan searches', 'Obtain authorized search receipts for the listed plan entries, or document a scope change. No search is performed here.'),
    'incomplete_searches': ('searches', 'Inspect supplied pagination/count/error receipts; retrieve or correct source records manually. Do not assert completeness from counts alone.'),
    'records_pending_screening': ('searches screening', 'Read each source and record the human eligibility decision and exclusion reason where applicable.'),
    'unmapped_included_records': ('screening reports', 'Determine the report identity for each included record and add an explicit mapping. Do not merge identities by inference.'),
    'reports_pending_retrieval': ('reports', 'Obtain full text through authorized access or record an unavailable/pending state; no full text is fetched.'),
    'reports_not_retrieved': ('reports', 'Review unavailable reports and document limitations or authorized follow-up. Do not treat unavailable reports as assessed.'),
    'reports_pending_assessment': ('reports', 'Read the retrieved report and record full-text eligibility and a reason for exclusions.'),
    'included_reports_without_extraction': ('reports evidence', 'Read the included report and supply traceable result rows; an empty extraction does not prove no relevant results.'),
    'record_level_extraction_pending': ('screening reports evidence', 'Review title/abstract-included records without result rows. This queue is not a full-text extraction task list; reconcile with report decisions.'),
    'evidence_without_experimental_unit': ('evidence experimental_units', 'Decide whether a result can be assigned to one supplied condition pair. Leave aggregate or unassignable results explicit; do not invent a condition.'),
    'units_with_unresolved_conditions': ('experimental_units', 'Read the cited condition details and retain unknown/not-reported fields where sources do not resolve them.'),
    'units_without_outcome_sampling': ('experimental_units', 'Decide whether outcome-level sampling metadata is in scope; if so record n semantics and independence wording from sources, not inferred sample sizes.'),
    'units_with_unresolved_sampling': ('experimental_units', 'Review missing n, analysis-unit and independence descriptions in sampling_review. Do not equate readings with independent samples.'),
    'units_without_outcome_statistics': ('experimental_units', 'Decide whether statistical reporting is in scope; preserve source values, units and direction wording without calculating effects.'),
    'units_with_statistics_review_cues': ('experimental_units', 'Review statistics_review missing fields and literal label differences against sources. A label difference is not a statistical inconsistency verdict.'),
    'context_review_pending': ('contexts', 'Check guideline/development source currency, population, applicability and limits manually; supplied labels are not verified guidance.'),
    'evidence_without_recorded_appraisal': ('evidence appraisals', 'Choose an appropriate appraisal method and record source-linked human judgments, or explain the unassessed scope. No appraisal is performed here.'),
    'statements_without_evidence_positions': ('synthesis_statements', 'Decide whether claim-position comparison is needed; explicitly record source-linked positions without treating results as independent votes.'),
    'statements_with_unresolved_positions': ('synthesis_statements', 'Review unclear/not-assessed positions and their exact claim components. Do not auto-resolve causal or contradictory interpretations.'),
    'pending_synthesis_statement_reviews': ('synthesis_statements', 'Inspect claim wording, exact citations, positions and source limitations before recording a human review. Do not copy a target hash as scientific approval.'),
    'stale_synthesis_statement_reviews': ('synthesis_statements', 'Compare changed statement sources and reassess the supplied review; do not renew the basis hash automatically.'),
    'evidence_without_statement_citation': ('evidence synthesis_statements', 'Decide whether each uncited result belongs in a statement; uncited does not itself mean an omission error.'),
    'work_without_planning_assertion': ('gaps planning_decisions', 'Decide whether a supplied planning rank is useful. Record rationale and uncertainty; no rank is generated.'),
    'work_with_stale_planning_assertion': ('gaps planning_decisions', 'Review changed evidence/work scope before re-recording a planning assertion. Ranks never override prerequisites.'),
    'dependency_unblocked_planned_work': ('gaps', 'Review the proposed deliverable and acceptance criterion. Unblocked means only that recorded dependencies are complete, not scientific approval.'),
    'blocked_work': ('gaps', 'Inspect the recorded prerequisite work; no dependency is bypassed or work automatically started.'),
    'work_in_progress': ('gaps', 'Review the supplied progress assertion and remaining deliverable work; no progress is inferred.'),
    'completed_work_assertions': ('gaps', 'Inspect the supplied artifact locator and acceptance assertion. This tool does not open artifacts or certify acceptance.'),
}

BOUNDARY = ('Read-only navigation and supplied-data handoff, not a generated scientific report. '
            'Queues are protocol-wide even when a work package is selected. Optional missing stages '
            'need a scope decision, not invented data. Empty queues are not proof of completeness. '
            'No search, source reading, AI inference, appraisal, claim adjudication, work execution, '
            'review renewal or clinical decision is performed. Commands are argument arrays to inspect, not executed actions.')


QUEUE_DOMAINS = {
    **dict.fromkeys(('missing_planned_searches',), 'search'),
    **dict.fromkeys(('records_pending_screening','unmapped_included_records','record_level_extraction_pending'), 'record'),
    **dict.fromkeys(('reports_pending_retrieval','reports_not_retrieved','reports_pending_assessment','included_reports_without_extraction'), 'report'),
    **dict.fromkeys(('evidence_without_experimental_unit','evidence_without_recorded_appraisal','evidence_without_statement_citation'), 'evidence'),
    **dict.fromkeys(('units_with_unresolved_conditions','units_without_outcome_sampling','units_with_unresolved_sampling','units_without_outcome_statistics','units_with_statistics_review_cues'), 'experiment'),
    **dict.fromkeys(('statements_without_evidence_positions','statements_with_unresolved_positions','pending_synthesis_statement_reviews','stale_synthesis_statement_reviews'), 'statement'),
    **dict.fromkeys(('work_without_planning_assertion','work_with_stale_planning_assertion','dependency_unblocked_planned_work','blocked_work','work_in_progress','completed_work_assertions'), 'work_package'),
    'context_review_pending': 'context', 'incomplete_searches': 'search_index',
}


def input_locations(protocol, queue, sections, items):
    """Resolve typed IDs and authoritative search indices, not arbitrary ID strings."""
    domain=QUEUE_DOMAINS[queue]
    if domain == 'search_index':
        return list(dict.fromkeys('/searches/' + str(item['search_index']) for item in items or []))
    ids={item if isinstance(item,str) else item[domain + '_id'] for item in items or []}
    matches=[]
    for section in sections:
        entries=protocol.get(section, [])
        if not isinstance(entries,list): continue
        for index,row in enumerate(entries):
            if not isinstance(row,dict): continue
            values=[]
            if domain=='record':
                if section in ('searches','reports'): values=row.get('record_ids',[])
                elif section in ('screening','evidence'): values=[row.get('record_id')]
            elif domain=='evidence':
                if section=='evidence': values=[row.get('evidence_id',row.get('record_id'))]
                elif section in ('appraisals','experimental_units','synthesis_statements'): values=row.get('evidence_ids',[])
            elif domain=='work_package':
                if section=='gaps': values=[row.get('work_package_id',f'WP-{index+1:03}')]
                elif section=='planning_decisions': values=[row.get('work_package_id')]
            else:
                fields={'search':('search_plan','searches'), 'report':('reports',),
                        'experiment':('experimental_units',), 'statement':('synthesis_statements',),
                        'context':('contexts',)}
                if section in fields[domain]: values=[row.get(domain + '_id')]
            if isinstance(values,list) and any(isinstance(value,str) and value in ids for value in values):
                matches.append('/' + section + '/' + str(index))
    return matches


def handoff(protocol, work_package_id=None):
    state = status(protocol)
    works = review_packets(protocol, work_package_id)
    synthesis = snapshot(protocol)
    if set(state['queues']) != set(SPECS) or set(SPECS) != set(QUEUE_DOMAINS):
        raise ValueError('handoff queue guidance is out of date')
    steps = []
    for queue, (sections, task) in SPECS.items():
        items = state['queues'][queue]
        sections = sections.split()
        steps.append(dict(queue=queue, state='NOT_SUPPLIED' if items is None else 'RECORDED_ITEMS' if items else 'NO_RECORDED_ITEMS',
                          item_count=None if items is None else len(items), items=copy.deepcopy(items),
                          input_sections=['/' + name for name in sections],
                          matching_input_rows=input_locations(protocol, queue, sections, items),
                          operator_task=task,
                          scope='protocol_wide_not_selected_work_only'))
    summaries = []
    for packet in works['packets']:
        summaries.append(dict(work_package=copy.deepcopy(packet['work_package']),
                             planning=copy.deepcopy(packet['planning_assertion']),
                             claim_positions=copy.deepcopy(packet['claim_positions']),
                             contexts=[copy.deepcopy(row['context']) for row in packet['contexts']],
                             recorded_review_gaps=copy.deepcopy(packet['recorded_review_gaps']),
                             scope='selected_work_with_full_statement_and_condition_review_scope'))
    implementation = dict(synthesis['engine_sha256'], **works['engine_sha256'])
    implementation['review_handoff.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    implementation['prisma_audit.py'] = hashlib.sha256(Path(__file__).with_name('prisma_audit.py').read_bytes()).hexdigest()
    implementation['search_manifest.py'] = hashlib.sha256(Path(__file__).with_name('search_manifest.py').read_bytes()).hexdigest()
    return dict(schema_version=1, question=state['question'], protocol_version=state['protocol_version'],
                protocol_sha256=state['protocol_sha256'], engine_sha256=implementation,
                hash_scope=state['hash_scope'], work_selection=works['selection'],
                record_flow=copy.deepcopy(synthesis['record_flow']), report_stage=synthesis['report_stage'],
                report_flow=copy.deepcopy(synthesis['report_flow']), synthesis_stage=synthesis['synthesis_stage'],
                manual_review_steps=steps, selected_work=summaries,
                detailed_views=[dict(script='search_manifest.py',arguments=['PROTOCOL.json'],purpose='Exact planned query specifications and source-wise receipt/interruption/overlap accounting'),
                                dict(script='prisma_audit.py',arguments=['PROTOCOL.json'],purpose='Machine-readable accounting members, reason groups and record/report/study/result links'),
                                dict(script='research_status.py',arguments=['PROTOCOL.json','--text'],purpose='Protocol-wide queues'),
                                dict(script='synthesis_review.py',arguments=['PROTOCOL.json','--text'],purpose='Full result/source/condition/n/statistics/claim traces'),
                                dict(script='work_review.py',arguments=['PROTOCOL.json']+(['--work-package='+work_package_id] if work_package_id is not None else [])+['--text'],purpose='Detailed work evidence and applicability packet')],
                manual_work_remaining=['Authorized literature and full-text retrieval', 'Human eligibility and extraction',
                                       'Guideline currency and applicability review', 'Scientific appraisal and claim adjudication',
                                       'Work execution and independent deliverable acceptance'],
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def render_text(result):
    show = quoted_display
    lines = ['Operator review handoff (supplied data only)', 'Question: ' + show(result['question']),
             'Protocol version: ' + show(result['protocol_version']), 'Protocol SHA-256: ' + result['protocol_sha256'],
             'Work selection: ' + show(result['work_selection']),
             'Queue scope: whole protocol, not only the selected work package.',
             'Record/result accounting: ' + show(result['record_flow']),
             'Report stage: ' + result['report_stage'], 'Report accounting: ' + show(result['report_flow']),
             'Synthesis stage: ' + result['synthesis_stage'], '',
             'Manual review navigation (not ranked tasks; absent stages require a scope decision):',
             'NO_RECORDED_ITEMS steps are omitted from text, retained in JSON; this is not a completeness finding.']
    for step in result['manual_review_steps']:
        if step['state'] == 'NO_RECORDED_ITEMS': continue
        lines.extend(['', step['queue'] + ': ' + step['state'], 'Items: ' + show(step['items']),
                      'Input sections: ' + show(step['input_sections']),
                      'Matching rows: ' + show(step['matching_input_rows']), 'Operator: ' + step['operator_task']])
    lines.append('\nSelected work deliverables and applicability context:')
    for item in result['selected_work']:
        lines.extend(['Work: ' + show(item['work_package']), 'Supplied planning: ' + show(item['planning']),
                      'Guideline/development context: ' + show(item['contexts'])])
        for claim in item['claim_positions']:
            statement=claim['statement']
            lines.append('Claim: ' + show(dict(statement_id=statement['statement_id'],text=statement['text'],
                source_match_status=statement['source_match_status'],support_status=statement['support_status'],
                position_stage=claim['position_stage'],work_evidence_ids=claim['work_evidence_ids'],
                other_statement_evidence_ids=claim['other_statement_evidence_ids'],positions=claim['work_positions'],scope=claim['scope'])))
    lines.extend(['', 'Detailed read-only views (replace the PROTOCOL.json placeholder; arguments are not shell commands):',
                  show(result['detailed_views']), 'Manual work not performed: ' + show(result['manual_work_remaining']),
                  'Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY', result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol',type=Path)
    parser.add_argument('--work-package')
    parser.add_argument('--text',action='store_true')
    args=parser.parse_args()
    try:
        result=handoff(parse_json(args.protocol.read_text(encoding='utf-8')),args.work_package)
    except (ValueError,OSError,KeyError,TypeError) as error:
        parser.exit(1,str(error)+'\n')
    print(render_text(result) if args.text else json.dumps(result,ensure_ascii=False,indent=2),end='' if args.text else '\n')

if __name__=='__main__':main()
