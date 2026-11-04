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
from report_links import report_study_ids

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
    'completed_work_without_source_binding': ('gaps', 'Inspect the supplied completion criteria, artifact and evidence scope; no hash-bound completion basis was supplied. Do not copy a target hash as acceptance.'),
    'completed_work_with_stale_source_binding': ('gaps', 'Compare changed work/evidence/context or artifact locator and reassess completion manually. Recorded COMPLETE/dependencies are not automatically changed.'),
    'completed_work_assertions': ('gaps', 'Inspect the supplied artifact locator and acceptance assertion. This tool does not open artifacts or certify acceptance.'),
}
OPTIONAL_SPECS = {
    'inventory_candidates_with_review_cues': ('reports report_sources report_study_inventory report_study_inventory_reviews', 'Inspect the exact described candidate, all supplied descriptions and separate human positions. Selected inventory/source IDs do not prove reading, identity or eligibility. Do not include a report merely to review its candidates, infer consensus, renew stale hashes or turn positions into canonical selection. Retained orphan assertions are retrospective context, not pending tasks.'),
    'study_memberships_with_review_cues': ('reports report_sources report_study_reviews evidence', 'Inspect the exact report-study pair, human-selected source IDs and separate positions. Report inclusion is not per-study eligibility; differing source-ID sets do not prove different reading or equivalent coverage. No canonical selection, evidence filtering, identity inference or automatic consensus occurs.'),
    'reports_with_review_cues': ('reports report_sources report_reviews', 'Inspect the supplied document versions, page/section coverage and separate human full-text positions. A matching supplied digest does not verify bytes, reading, authenticity or eligibility. Retrieve only through authorized access; never infer consensus, per-study eligibility or renew stale hashes automatically.'),
    'report_study_memberships_without_results': ('reports evidence', 'Read the exact included report-study membership and record traceable results if in scope. A result for this study in another report does not fill this membership; presence is not exhaustive extraction or study independence.'),
    'records_with_screening_review_cues': ('screening_reviews screening searches', 'Inspect each supplied reviewer position, source binding and any differing or unclear labels. Resolve eligibility outside this tool if appropriate; never choose a majority, authenticate reviewers or renew hashes automatically. Canonical screening remains a separate supplied decision.'),
}
OPTIONAL_QUEUE_DOMAINS = {'inventory_candidates_with_review_cues': 'inventory_candidate_review',
                        'study_memberships_with_review_cues': 'report_study_review',
                        'reports_with_review_cues': 'report',
                        'report_study_memberships_without_results': 'report_study',
                        'records_with_screening_review_cues': 'record'}

BOUNDARY = ('Read-only navigation and supplied-data handoff, not a generated scientific report. '
            'Queues are protocol-wide even when a work package is selected. Optional missing stages '
            'need a scope decision, not invented data. Empty queues are not proof of completeness. '
            'No search, source reading, AI inference, appraisal, claim adjudication, work execution, '
            'review renewal or clinical decision is performed. Commands are argument arrays to inspect, not executed actions.')

# Static discovery, never derived applicability or an executable research plan.
SUPPLIED_INPUT_WORKFLOW_SCOPE = (
    'Static protocol-independent catalog, not queue-based eligibility or a recommended execution order. '
    'The same routes are shown for every protocol and work selection. Entry points display parser help '
    'only; the handoff does not execute them, fill IDs, inspect external files or validate prospective '
    'inputs. Read each guide, supply actual human decisions and use the operation-specific validators. '
    'The legacy manual_input_workflow remains a separate mock receipt rehearsal, not the only input route.'
)
SUPPLIED_INPUT_WORKFLOWS = [
    dict(workflow_id='native_collection', title='Supplied native citation files and explicit collection review',
         guide_paths=['docs/PUBMED_NBIB_INTAKE.md', 'docs/PUBMED_NBIB_BATCH.md', 'docs/RIS_INTAKE.md', 'docs/BIBLIOGRAPHIC_REVIEW.md', 'docs/BATCH_TO_EVIDENCE.md'],
         entrypoints=[dict(script='nbib_intake.py', arguments=['preview', '--help']),
                      dict(script='nbib_intake.py', arguments=['verify', '--help']),
                      dict(script='nbib_batch_intake.py', arguments=['preview', '--help']),
                      dict(script='nbib_batch_intake.py', arguments=['verify', '--help']),
                      dict(script='ris_intake.py', arguments=['preview', '--help']),
                      dict(script='ris_intake.py', arguments=['verify', '--help']),
                      dict(script='bibliographic_review.py', arguments=['template', '--help']),
                      dict(script='bibliographic_review.py', arguments=['target', '--help']),
                      dict(script='bibliographic_review.py', arguments=['assemble', '--help'])],
         required_human_inputs=['Explicit local files, declared search and supplied search occasion; batch grouping is a human assertion.',
                                'Row-level identity/non-promotion choices and separate exact-target collection review.',
                                'The documented ledger-free common base and an unused declared search; never erase existing research to make a base.'],
         boundary='No retrieval, file discovery, identity merging, screening or completeness inference. Native wrappers and original bytes must be retained separately from the CSV derivative. RIS support is a documented subset; its file-occurrence labels are not publication identity and existing NBIB archives do not accept RIS wrappers.'),
    dict(workflow_id='screening_decision', title='Separate supplied screening positions and canonical decisions',
         guide_paths=['docs/SCREENING_REVIEWS.md', 'docs/SCREENING_DECISIONS.md'],
         entrypoints=[dict(script='screening_review.py', arguments=['--help']),
                      dict(script='screening_decision.py', arguments=['target', '--help']),
                      dict(script='screening_decision.py', arguments=['assemble', '--help']),
                      dict(script='screening_decision.py', arguments=['inspect', '--help'])],
         required_human_inputs=['Explicit enumerated record ID and actual source review.',
                                'Human eligibility choice, reason, adjudicator, date, rationale and source locator.'],
         boundary='Collection promotion is not screening. Reviewer positions do not infer consensus or alter canonical screening; supplied decision history is not authenticated chronology.'),
    dict(workflow_id='report_registration', title='Register explicitly mapped new reports',
         guide_paths=['docs/MANUAL_REPORT_INTAKE.md'],
         entrypoints=[dict(script='report_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')],
         required_human_inputs=['Explicit included, unmapped record selection and human report identity/grouping.',
                                'Supplied retrieval state, optional document declarations and separate registration review.'],
         boundary='No report grouping is selected here. New decisions stay pending. Mock-adapter contexts and legacy evidence without a report ledger are unsupported by this intake; no provenance is erased.'),
    dict(workflow_id='report_retrieval', title='Record supplied retrieval outcomes for existing reports',
         guide_paths=['docs/REPORT_RETRIEVAL_UPDATES.md'],
         entrypoints=[dict(script='report_retrieval.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')],
         required_human_inputs=['Explicit unassessed pending/unavailable report selection and a supported supplied transition.',
                                'Locator/reason, optional new source declarations and separate exact-target review.'],
         boundary='No file is acquired or read. Mock contexts, already retrieved reports, same-state edits and reversals are unsupported. Source changes can stale retained assertions; no review is renewed.'),
    dict(workflow_id='report_source_declarations', title='Append reviewed source declarations without replacing prior versions',
         guide_paths=['docs/MANUAL_SOURCE_DECLARATIONS.md', 'docs/REPORT_REVIEWS.md', 'docs/REPORT_SOURCE_CHECK.md'],
         entrypoints=[dict(script='report_source_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')] +
                     [dict(script='report_source_check.py', arguments=[command, '--help'])
                      for command in ('template', 'check')],
         required_human_inputs=['Existing retrieved report, new explicit source IDs, literal descriptors, declaration metadata and separate exact-input import review.',
                                'For a separate local byte check: a non-null supplied digest, explicit file mapping and trusted root; source inspection requires supported POSIX access.'],
         boundary='Declarations do not retrieve or authenticate documents, replace old descriptors, select a preferred version or change counts/membership. New same-report sources can stale retained reviews and document-bound work without renewal. Old null digests remain unbound. Local byte checking is separate and native Windows fails closed; no source locator is followed automatically.'),
    dict(workflow_id='descriptive_inventory', title='Append supplied candidate-study descriptions before inclusion',
         guide_paths=['docs/MANUAL_INVENTORY_INTAKE.md', 'docs/REPORT_STUDY_INVENTORY.md', 'docs/INVENTORY_CANDIDATE_REVIEWS.md'],
         entrypoints=[dict(script='inventory_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')],
         required_human_inputs=['Explicit retrieved report and human candidate-study label, completed description, recorder/date and selected same-report source IDs.',
                                'Current supplied inventory source basis and separate exact-input import review.'],
         boundary='Descriptive inventory is not inclusion, eligibility, study independence or result extraction. New stale assertions and mock-adapter inputs are rejected. Existing descriptions and reviews remain; additional same-pair descriptions can stale earlier candidate positions without renewal.'),
    dict(workflow_id='full_text_decision', title='Apply a separate supplied full-text eligibility choice',
         guide_paths=['docs/REPORT_DECISIONS.md', 'docs/REPORT_REVIEWS.md'],
         entrypoints=[dict(script='report_decision.py', arguments=[command, '--help'])
                      for command in ('target', 'assemble', 'verify')],
         required_human_inputs=['Explicit already retrieved report and actual full-text assessment.',
                                'Human choice/reason and explicit study declaration for inclusion; existing downstream links must remain valid.'],
         boundary='Retrieval is not inclusion. No report-study membership, majority decision, reading or eligibility correctness is inferred. Existing validators decide input compatibility.'),
    dict(workflow_id='result_intake', title='Append explicitly supplied traceable result rows',
         guide_paths=['docs/MANUAL_RESULT_INTAKE.md', 'docs/EXTRACTION_WORKSHEETS.md'],
         entrypoints=[dict(script='result_extraction.py', arguments=['--help'])] +
                     [dict(script='result_intake.py', arguments=[command, '--help'])
                      for command in ('target', 'assemble', 'verify')],
         required_human_inputs=['Explicit included/retrieved report, mapped record, declared study and selected document references.',
                                'Source-linked human result rows, extraction metadata and separate import review.'],
         boundary='Mock-adapter inputs are unsupported for manual result intake. No result, effect size, independent study, complete extraction or scientific acceptance is generated.'),
    dict(workflow_id='result_review_continuation', title='Compare later result-source context and separately review text corrections',
         guide_paths=['docs/RESULT_SOURCE_REVIEW.md', 'docs/RESULT_CORRECTIONS.md'],
         entrypoints=[dict(script='result_source_review.py', arguments=['--help'])] +
                     [dict(script='result_correction.py', arguments=[command, '--help'])
                      for command in ('target', 'assemble', 'verify')],
         required_human_inputs=['For comparison: the actual original protocol, retained manual-result intake application and explicit current protocol.',
                                'For correction: existing explicit result IDs, human-supplied result/limitations changes, selected source references and separate exact-target review.',
                                'Retain original inputs, detached records and their recorded implementation; do not re-import a corrected copy under a new ID.'],
         boundary='Comparison replays the original intake before comparing literal current context, not historical lineage or approval. Correction changes only result/limitations text, preserving IDs, row order and counts. It does not renew earlier reviews, repair associations or reassess all downstream assertions; changed context never selects a correction automatically.'),
    dict(workflow_id='condition_intake', title='Append supplied descriptive nonclinical context',
         guide_paths=['docs/MANUAL_CONDITION_INTAKE.md', 'docs/EXPERIMENT_CONDITIONS.md'],
         entrypoints=[dict(script='condition_intake.py', arguments=[command, '--help'])
                      for command in ('target', 'assemble', 'verify')],
         required_human_inputs=['Explicit report/result IDs and supplied document references.',
                                'Descriptive condition context with honest unknown/not-reported fields and separate import review.'],
         boundary='No concentration, exposure, timing, comparator, causal interpretation or experimental procedure is invented. Optional missing stages are not automatically required work.'),
    dict(workflow_id='appraisal_intake', title='Record supplied result-linked appraisals with separate import review',
         guide_paths=['docs/MANUAL_APPRAISAL_INTAKE.md', 'docs/APPRAISAL_SOURCE_REVIEW.md', 'docs/SYNTHESIS_REVIEW.md', 'docs/WORK_REVIEW.md'],
         entrypoints=[dict(script='appraisal_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')]
                     + [dict(script='appraisal_source_review.py', arguments=['--help'])],
         required_human_inputs=['Exact existing result IDs within one supplied study per appraisal; authored method, domain judgements and provenance',
                                'Separate exact-target import review; no method or judgement is generated'],
         boundary='Only new supplied appraisal records are appended. Conflicting positions remain separate; no score, consensus or method suitability is inferred. Mapped source catalogs are context, not proof of reading. Existing planning/synthesis/completion hashes are not renewed; derived source-status cues may change.'),
    dict(workflow_id='context_intake', title='Record supplied unassigned guideline and development contexts',
         guide_paths=['docs/MANUAL_CONTEXT_INTAKE.md', 'docs/SOURCE_CONTEXTS.md'],
         entrypoints=[dict(script='context_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')],
         required_human_inputs=['Explicit domain/scope and source or result links, complete supplied context assertions and own review status',
                                'Separate exact-input import review; no scientific, clinical or regulatory judgement is generated'],
         boundary='Only new contexts append and remain unassigned. Import review never changes context review_status or authorship. Existing work/synthesis links and planning/completion bases stay unchanged. Source links do not promote eligibility or evidence; no guideline currency or regulatory validity is established.'),
    dict(workflow_id='source_review_work', title='Append explicit source-review work proposals',
         guide_paths=['docs/SOURCE_WORK_INTAKE.md', 'docs/SOURCE_REVIEW_WORK.md'],
         entrypoints=[dict(script='source_work_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')],
         required_human_inputs=['Explicit typed planned-search/record references.',
                                'Human question, deliverable, acceptance criterion, dependencies and separate proposal review.'],
         boundary='Only supplied PLANNED source-review work is appended. No task, priority, dependency, execution or completion is inferred from queues or from this catalog.'),
    dict(workflow_id='evidence_review_work', title='Append explicit result-linked review work and deliverables',
         guide_paths=['docs/EVIDENCE_WORK_INTAKE.md', 'docs/SOURCE_REVIEW_WORK.md', 'docs/WORK_DOCUMENT_SOURCES.md'],
         entrypoints=[dict(script='evidence_work_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')],
         required_human_inputs=['Exact existing normalized result IDs, authored question/deliverable/acceptance criterion, explicit dependencies and proposal metadata.',
                                'Separate exact-input review; optional evidence-scoped contexts must satisfy existing overlap rules.'],
         boundary='Only new PLANNED evidence-review work is appended. No result, scientific task, dependency, priority or completion is generated. Source-review work is not converted, and own source_refs/document_source_ids are rejected. Existing raw identity defaults and planning/completion assertions remain unchanged; direct dependencies are not recursive source approval.'),
    dict(workflow_id='work_completion', title='Record one supplied work completion after exact-target review',
         guide_paths=['docs/WORK_COMPLETION_INTAKE.md', 'docs/COMPLETION_BINDING.md', 'docs/LOCAL_ARTIFACT_REVIEW.md'],
         entrypoints=[dict(script='work_completion_intake.py', arguments=[command, '--help'])
                      for command in ('template', 'target', 'assemble', 'verify')],
         required_human_inputs=['Exact existing unfinished work ID, supplied artifact locator and true acceptance assertion',
                                'Completer/date/note and a separate exact-target completion review'],
         boundary='Only one unfinished work completion is recorded; no artifact access, acceptance assessment or scientific approval. Existing COMPLETE assertions cannot be renewed or reopened. Stale/unbound prerequisite completions remain visible and unchanged; derived dependency blocking may change.'),
    dict(workflow_id='collection_archives', title='Preserve protocol snapshots and selected native source bindings',
         guide_paths=['docs/COLLECTION_BUNDLES.md', 'docs/BATCH_COLLECTION_BUNDLES.md', 'docs/NATIVE_COLLECTION_BUNDLES.md', 'docs/BATCH_TO_EVIDENCE.md'],
         entrypoints=[dict(script=script, arguments=[command, '--help'])
                      for script in ('research_bundle.py', 'collection_bundle.py', 'batch_collection_bundle.py', 'native_collection_bundle.py')
                      for command in ('create', 'verify')],
         required_human_inputs=['An explicit protocol snapshot and new output path.',
                                'For native collection bundles, explicitly selected wrapper files and historical import indices; the typed archive also requires explicit ris, nbib or nbib_batch format.'],
         boundary='Ordinary bundles do not retain detached application history. Native formats and wrappers are not inferred. Native archives preserve selected source/import associations, not full research history or authenticated sources.'),
    dict(workflow_id='report_transition_archive', title='Preserve a contiguous supplied report-transition segment',
         guide_paths=['docs/REPORT_TRANSITION_BUNDLES.md'],
         entrypoints=[dict(script='report_transition_bundle.py', arguments=[command, '--help'])
                      for command in ('create', 'verify')],
         required_human_inputs=['Exact original and endpoint protocols, explicitly ordered supported application files and a new archive path.'],
         boundary='Only registration, retrieval-update and full-text applications are replayed as steps. Search, screening, result and condition operations are outside this segment; earlier/later history is unassessed. No embedded code is loaded or executed.'),
    dict(workflow_id='extraction_transition_archive', title='Preserve a contiguous supplied extraction-transition segment',
         guide_paths=['docs/EXTRACTION_TRANSITION_BUNDLES.md'],
         entrypoints=[dict(script='extraction_transition_bundle.py', arguments=[command, '--help'])
                      for command in ('create', 'verify')],
         required_human_inputs=['Exact initial/endpoint protocols, explicitly ordered supported result/condition applications and a new archive path.',
                                'Separately retain the recorded implementation; each historical source association belongs to its recorded step context.'],
         boundary='Only result intake, result-text correction and descriptive condition intake are replayed as steps. No earlier review is renewed or downstream work reassessed. Other operations and earlier/later history are outside this segment. No source documents or code are embedded; complete history and extraction completeness remain unestablished.'),
    dict(workflow_id='work_transition_archive', title='Preserve a supplied contiguous work-history segment',
         guide_paths=['docs/WORK_TRANSITION_BUNDLES.md'],
         entrypoints=[dict(script='work_transition_bundle.py', arguments=[command, '--help'])
                      for command in ('create', 'verify')],
         required_human_inputs=['Actual initial/endpoint protocols and explicitly ordered source-work, evidence-work or completion application records',
                                'Recorded implementation; retained assertions apply to their recorded step context'],
         boundary='Only source-work intake, evidence-work intake and single-work completion steps are replayed. No review/completion is renewed, artifact inspected or acceptance assessed. Explicit step IDs do not enumerate all derived impacts. Earlier/later and complete project history remain unestablished.'),
    dict(workflow_id='appraisal_transition_archive', title='Preserve a supplied contiguous appraisal-import segment',
         guide_paths=['docs/APPRAISAL_TRANSITION_BUNDLES.md'],
         entrypoints=[dict(script='appraisal_transition_bundle.py', arguments=[command, '--help'])
                      for command in ('create', 'verify')],
         required_human_inputs=['Actual initial/endpoint protocol bytes and explicitly ordered appraisal intake application records',
                                'Separately retained recorded implementation; original assertions keep their historical step context'],
         boundary='Only detached appraisal intake steps are replayed. No method or judgement is generated, review renewed or validity assessed. Read-only comparison is not a transition. The selected segment does not establish complete appraisal history, independent reviewers or source reading.'),
]


QUEUE_DOMAINS = {
    **dict.fromkeys(('missing_planned_searches',), 'search'),
    **dict.fromkeys(('records_pending_screening','unmapped_included_records','record_level_extraction_pending'), 'record'),
    **dict.fromkeys(('reports_pending_retrieval','reports_not_retrieved','reports_pending_assessment','included_reports_without_extraction'), 'report'),
    **dict.fromkeys(('evidence_without_experimental_unit','evidence_without_recorded_appraisal','evidence_without_statement_citation'), 'evidence'),
    **dict.fromkeys(('units_with_unresolved_conditions','units_without_outcome_sampling','units_with_unresolved_sampling','units_without_outcome_statistics','units_with_statistics_review_cues'), 'experiment'),
    **dict.fromkeys(('statements_without_evidence_positions','statements_with_unresolved_positions','pending_synthesis_statement_reviews','stale_synthesis_statement_reviews'), 'statement'),
    **dict.fromkeys(('work_without_planning_assertion','work_with_stale_planning_assertion','dependency_unblocked_planned_work','blocked_work','work_in_progress','completed_work_assertions','completed_work_without_source_binding','completed_work_with_stale_source_binding'), 'work_package'),
    'context_review_pending': 'context', 'incomplete_searches': 'search_index',
}


def input_locations(protocol, queue, sections, items):
    """Resolve typed IDs and authoritative search indices, not arbitrary ID strings."""
    domain={**QUEUE_DOMAINS, **OPTIONAL_QUEUE_DOMAINS}[queue]
    if domain == 'search_index':
        return list(dict.fromkeys('/searches/' + str(item['search_index']) for item in items or []))
    if domain == 'inventory_candidate_review':
        pairs = {(item['report_id'], item['study_id']) for item in items or []}
        report_ids = {rid for rid, _ in pairs}
        paths = [f'/reports/{index}' for index, row in enumerate(protocol.get('reports', []))
                 if row['report_id'] in report_ids]
        paths += [f'/report_sources/{index}' for index, row in enumerate(protocol.get('report_sources', []))
                  if row['report_id'] in report_ids]
        for section in ('report_study_inventory', 'report_study_inventory_reviews'):
            paths += [f'/{section}/{index}' for index, row in enumerate(protocol.get(section, []))
                      if (row['report_id'], row['study_id']) in pairs]
        return paths
    if domain == 'report_study_review':
        pairs = {(item['report_id'], item['study_id']) for item in items or []}
        report_ids = {rid for rid, _ in pairs}
        report_for_record = {record: row['report_id'] for row in protocol.get('reports', [])
                             for record in row['record_ids']}
        paths = [f'/reports/{index}' for index, row in enumerate(protocol.get('reports', []))
                 if any((row['report_id'], sid) in pairs for sid in report_study_ids(row))]
        paths += [f'/report_sources/{index}' for index, row in enumerate(protocol.get('report_sources', []))
                  if row['report_id'] in report_ids]
        paths += [f'/report_study_reviews/{index}' for index, row in enumerate(protocol.get('report_study_reviews', []))
                  if (row['report_id'], row['study_id']) in pairs]
        paths += [f'/evidence/{index}' for index, row in enumerate(protocol['evidence'])
                  if (report_for_record.get(row['record_id']), row['study_id']) in pairs]
        return paths
    if domain == 'report_study':
        pairs = {(item['report_id'], item['study_id']) for item in items or []}
        return [f'/reports/{index}' for index, row in enumerate(protocol.get('reports', []))
                if any((row['report_id'], study_id) in pairs for study_id in report_study_ids(row))]
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
                elif section in ('screening','evidence','screening_reviews'): values=[row.get('record_id')]
            elif domain=='evidence':
                if section=='evidence': values=[row.get('evidence_id',row.get('record_id'))]
                elif section in ('appraisals','experimental_units','synthesis_statements'): values=row.get('evidence_ids',[])
            elif domain=='work_package':
                if section=='gaps': values=[row.get('work_package_id',f'WP-{index+1:03}')]
                elif section=='planning_decisions': values=[row.get('work_package_id')]
            else:
                fields={'search':('search_plan','searches'), 'report':('reports','report_sources','report_reviews'),
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
    active_specs = dict(SPECS)
    active_specs.update({key:value for key,value in OPTIONAL_SPECS.items() if key in state['queues']})
    if (set(state['queues']) != set(active_specs) or set(SPECS) != set(QUEUE_DOMAINS)
            or set(OPTIONAL_SPECS) != set(OPTIONAL_QUEUE_DOMAINS)):
        raise ValueError('handoff queue guidance is out of date')
    steps = []
    for queue, (sections, task) in active_specs.items():
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
                             work_type=packet['work_type'],source_review_inputs=copy.deepcopy(packet['source_review_inputs']),
                             source_input_counts=copy.deepcopy(packet['source_input_counts']),
                             planning=copy.deepcopy(packet['planning_assertion']),completion_review=copy.deepcopy(packet['completion_review']),
                             direct_prerequisite_completion_reviews=copy.deepcopy(packet['direct_prerequisite_completion_reviews']),
                             claim_positions=copy.deepcopy(packet['claim_positions']),
                             contexts=[copy.deepcopy(row['context']) for row in packet['contexts']],
                             recorded_review_gaps=copy.deepcopy(packet['recorded_review_gaps']),
                             scope='selected_work_with_full_statement_and_condition_review_scope'))
        source_links = [dict(context_id=row['context']['context_id'],
                             **{key:copy.deepcopy(row[key]) for key in
                                ('shared_source_refs','other_context_source_refs','other_work_source_refs','linkage_scope')})
                        for row in packet['contexts'] if row['context'].get('context_scope') == 'source_review']
        if source_links:
            summaries[-1]['source_context_links'] = source_links
        if 'report_study_coverage' in packet:
            summaries[-1]['report_study_coverage'] = copy.deepcopy(packet['report_study_coverage'])
        for key in ('document_source_context', 'direct_dependency_document_sources', 'document_source_boundary'):
            if key in packet:
                summaries[-1][key] = copy.deepcopy(packet[key])
    implementation = dict(synthesis['engine_sha256'], **works['engine_sha256'])
    implementation['review_handoff.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    implementation['prisma_audit.py'] = hashlib.sha256(Path(__file__).with_name('prisma_audit.py').read_bytes()).hexdigest()
    implementation['search_manifest.py'] = hashlib.sha256(Path(__file__).with_name('search_manifest.py').read_bytes()).hexdigest()
    implementation['receipt_intake.py'] = hashlib.sha256(Path(__file__).with_name('receipt_intake.py').read_bytes()).hexdigest()
    result = dict(schema_version=1, question=state['question'], protocol_version=state['protocol_version'],
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
                prerequisite_review_view=None if work_package_id is None else dict(script='work_review.py',arguments=['PROTOCOL.json','--work-package='+work_package_id,'--include-prerequisites','--text'],purpose='Selected work plus explicit transitive prerequisite packets; no scientific approval'),
                manual_input_workflow=dict(precondition='Use a separate declared-plan base with empty searches/evidence and no adapter receipts; do not erase current research',
                    template_arguments=['receipt_intake.py','template','BASE_PROTOCOL.json'],
                    check_arguments=['receipt_intake.py','check','BASE_PROTOCOL.json','FILLED_MOCK_RECEIPTS.json','--text'],
                    scope='Synthetic entry rehearsal only; null template fields need supplied facts, checks never approve receipts'),
                supplied_input_workflows=copy.deepcopy(SUPPLIED_INPUT_WORKFLOWS),
                supplied_input_workflow_scope=SUPPLIED_INPUT_WORKFLOW_SCOPE,
                manual_work_remaining=['Authorized literature and full-text retrieval', 'Human eligibility and extraction',
                                       'Guideline currency and applicability review', 'Scientific appraisal and claim adjudication',
                                       'Work execution and independent deliverable acceptance'],
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    if 'report_study_inventory' in state:
        result['report_study_inventory'] = copy.deepcopy(state['report_study_inventory'])
        result['engine_sha256']['report_study_inventory.py'] = hashlib.sha256(Path(__file__).with_name('report_study_inventory.py').read_bytes()).hexdigest()
        result['detailed_views'].append(dict(script='report_study_inventory.py', arguments=['PROTOCOL.json','--text'],
                                            purpose='Supplied candidate descriptions before full-text inclusion, not selected studies or required tasks'))
    if 'report_study_inventory_review' in state:
        result['report_study_inventory_review'] = copy.deepcopy(state['report_study_inventory_review'])
        result['engine_sha256']['report_study_inventory_review.py'] = hashlib.sha256(Path(__file__).with_name('report_study_inventory_review.py').read_bytes()).hexdigest()
        result['detailed_views'].append(dict(script='report_study_inventory_review.py', arguments=['PROTOCOL.json','--text'],
                                            purpose='Human positions on described candidates before inclusion; not canonical selection or verified reading'))
    if 'report_study_review' in state:
        result['report_study_review'] = copy.deepcopy(state['report_study_review'])
        result['engine_sha256']['report_study_review.py'] = hashlib.sha256(Path(__file__).with_name('report_study_review.py').read_bytes()).hexdigest()
        result['detailed_views'].append(dict(script='report_study_review.py', arguments=['PROTOCOL.json','--text'],
                                            purpose='Exact report-study human positions and explicit source selections; orphan assertions are retrospective, not canonical eligibility'))
    if 'report_sources' in protocol or 'report_reviews' in protocol:
        result['engine_sha256']['report_review.py'] = hashlib.sha256(Path(__file__).with_name('report_review.py').read_bytes()).hexdigest()
        result['detailed_views'].append(dict(script='report_review.py', arguments=['PROTOCOL.json','--text'],
                                            purpose='Supplied full-text document versions and separate human positions; no verified reading, bytes or adjudication'))
    if 'screening_reviews' in protocol:
        result['engine_sha256']['screening_review.py'] = hashlib.sha256(Path(__file__).with_name('screening_review.py').read_bytes()).hexdigest()
        result['detailed_views'].append(dict(script='screening_review.py', arguments=['PROTOCOL.json','--text'],
                                            purpose='Exact source targets and separate supplied screening reviewer positions; no automatic adjudication'))
    if 'screening_decision_history' in state:
        result['screening_decision_history'] = copy.deepcopy(state['screening_decision_history'])
        result['engine_sha256']['screening_decision.py'] = hashlib.sha256(Path(__file__).with_name('screening_decision.py').read_bytes()).hexdigest()
        result['detailed_views'].append(dict(script='screening_decision.py', arguments=['inspect','PROTOCOL.json','--text'],
                                            purpose='Retained supplied decisions and source/reviewer snapshots; retrospective differences are not pending tasks'))
    return result


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
        lines.extend(['Work: ' + show(item['work_package']), 'Work type: ' + item['work_type'],
                      'Source review inputs (not extracted evidence): ' + show(item['source_review_inputs']),
                      'Source input counts: ' + show(item['source_input_counts']), 'Supplied planning: ' + show(item['planning']),
                      'Completion source binding (not acceptance): ' + show(item['completion_review']),
                      'Direct prerequisite completion sources (not acceptance): ' + show(item['direct_prerequisite_completion_reviews']),
                      'Guideline/development context: ' + show(item['contexts'])])
        if 'source_context_links' in item:
            lines.append('Pre-extraction typed context links (not applicability): ' + show(item['source_context_links']))
        if 'report_study_coverage' in item:
            lines.append('Linked-report study memberships (not work requirements): ' + show(item['report_study_coverage']))
        for key in ('document_source_context', 'direct_dependency_document_sources', 'document_source_boundary'):
            if key in item:
                lines.append(key + ' (not byte verification or acceptance): ' + show(item[key]))
        for claim in item['claim_positions']:
            statement=claim['statement']
            lines.append('Claim: ' + show(dict(statement_id=statement['statement_id'],text=statement['text'],
                source_match_status=statement['source_match_status'],support_status=statement['support_status'],
                position_stage=claim['position_stage'],work_evidence_ids=claim['work_evidence_ids'],
                other_statement_evidence_ids=claim['other_statement_evidence_ids'],positions=claim['work_positions'],scope=claim['scope'])))
    lines.append('\nSupplied-input workflow discovery (static, not a recommended task order):')
    lines.append(result['supplied_input_workflow_scope'])
    for workflow in result['supplied_input_workflows']:
        lines.extend(['Workflow: ' + show(workflow['workflow_id']) + ': ' + show(workflow['title']),
                      'Guides: ' + show(workflow['guide_paths']),
                      'Parser-help entry points (not executed): ' + show(workflow['entrypoints']),
                      'Required human inputs: ' + show(workflow['required_human_inputs']),
                      'Limits: ' + show(workflow['boundary'])])
    lines.extend(['', 'Detailed read-only views (replace the PROTOCOL.json placeholder; arguments are not shell commands):',
                  show(result['detailed_views']), 'Optional prerequisite packet view: ' + show(result['prerequisite_review_view']), 'Separate mock receipt rehearsal (not for overwriting this protocol): ' + show(result['manual_input_workflow']),
                  'Manual work not performed: ' + show(result['manual_work_remaining']),
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
