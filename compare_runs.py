"""Compare validated supplied protocols without inferring scientific meaning from changes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from evidence_workflow import run
from context_links import nonempty_text, iso_date, id_list, source_context_linkage
from json_io import configure_utf8_stdio, parse_json, quoted_display, canonical_json_bytes as canonical
from prisma_reports import report_flow
from report_links import has_plural_studies, report_study_coverage, report_study_ids
from research_bundle import engine_hashes

_NO_AMENDMENT = object()

BOUNDARY = ('Mechanical comparison of supplied inputs; both ledgers are recomputed with the current implementation, not replayed historical engines. '
            'Version labels do not authenticate amendment history or justify changes. '
            'No search, scientific reassessment or conclusion promotion is performed.')


def changed_fields(before, after):
    return sorted(field for field in set(before) | set(after)
                  if field not in before or field not in after
                  or canonical(before[field]) != canonical(after[field]))


def entity_changes(before, after, id_field):
    left = {row[id_field]: row for row in before}
    right = {row[id_field]: row for row in after}
    shared = set(left) & set(right)
    changed = [dict(id=identifier, fields=changed_fields(left[identifier], right[identifier]))
               for identifier in sorted(shared)
               if canonical(left[identifier]) != canonical(right[identifier])]
    return dict(added_ids=sorted(set(right) - set(left)),
                removed_ids=sorted(set(left) - set(right)), changed=changed,
                unchanged_count=len(shared) - len(changed))


def report_study_comparison(before, after, left, right, left_reports, right_reports):
    """Compare exact declared pairs, never positional pointers or guessed identities.

    Inputs and normalized rows have already passed the workflow/report validators.
    Scalar declarations are projected on both sides when either side opts in.
    """
    def snapshot(protocol, research, reports):
        if reports is None:
            return 'NOT_SUPPLIED', None, {}
        by_id = {row['report_id']: row for row in reports['report_ledger']}
        evidence = {row['evidence_id']: row for row in research['evidence']}
        positions = {row['report_id']: i for i, row in enumerate(protocol['reports'])}
        coverage = report_study_coverage(protocol, by_id, research['evidence'])
        pairs = {}
        for row in coverage['membership_ledger']:
            report = by_id[row['report_id']]
            pairs[(row['report_id'], row['study_id'])] = dict(
                report=copy.deepcopy(report), input_pointer=row['input_pointer'],
                report_input_pointer=f"/reports/{positions[row['report_id']]}",
                declaration_form='study_ids' if 'study_ids' in report else 'study_id',
                declared_study_ids=report_study_ids(report),
                evidence_ids=copy.deepcopy(row['evidence_ids']),
                linked_evidence=[copy.deepcopy(evidence[eid]) for eid in row['evidence_ids']],
                has_result_rows=row['has_result_rows'])
        return 'SUPPLIED', coverage['counts'], pairs

    left_stage, left_counts, old = snapshot(before, left, left_reports)
    right_stage, right_counts, new = snapshot(after, right, right_reports)
    rows = []
    for report_id, study_id in sorted(set(old) | set(new)):
        key = (report_id, study_id)
        a, b = old.get(key), new.get(key)
        retained = a is not None and b is not None
        fields = changed_fields({} if a is None else a['report'],
                                {} if b is None else b['report'])
        evidence = entity_changes([] if a is None else a['linked_evidence'],
                                  [] if b is None else b['linked_evidence'], 'evidence_id')
        pointer_changed = a['input_pointer'] != b['input_pointer'] if retained else None
        cues = []
        if a is None:
            cues.append('MEMBERSHIP_ADDED')
        elif b is None:
            cues.append('MEMBERSHIP_REMOVED')
        else:
            if set(fields) - {'study_id', 'study_ids'}:
                cues.append('REPORT_ASSERTIONS_CHANGED')
            if a['declaration_form'] != b['declaration_form']:
                cues.append('DECLARATION_FORM_CHANGED')
            if a['declared_study_ids'] != b['declared_study_ids']:
                cues.append('DECLARED_STUDY_ORDER_OR_SET_CHANGED')
            if pointer_changed:
                cues.append('INPUT_LOCATION_CHANGED')
            if a['has_result_rows'] != b['has_result_rows']:
                cues.append('RESULT_PRESENCE_CHANGED')
        if evidence['added_ids'] or evidence['removed_ids'] or evidence['changed']:
            cues.append('LINKED_RESULT_ASSERTIONS_CHANGED')
        rows.append(dict(report_id=report_id, study_id=study_id,
                         membership_status='RETAINED' if retained else ('ADDED' if a is None else 'REMOVED'),
                         before=a, after=b, changed_report_fields=fields,
                         linked_evidence_changes=evidence, input_pointer_changed=pointer_changed,
                         comparison_cues=cues))
    return dict(
        before_report_ledger_stage=left_stage, after_report_ledger_stage=right_stage,
        before_counts=left_counts, after_counts=right_counts,
        added_memberships=[dict(report_id=rid, study_id=sid) for rid, sid in sorted(set(new) - set(old))],
        removed_memberships=[dict(report_id=rid, study_id=sid) for rid, sid in sorted(set(old) - set(new))],
        retained_count=len(set(old) & set(new)),
        unchanged_count=sum(canonical(old[key]) == canonical(new[key]) for key in set(old) & set(new)),
        memberships=rows, change_significance='NOT_ASSESSED',
        study_identity_verification='NOT_ESTABLISHED', study_eligibility_assessment='NOT_PERFORMED',
        extraction_completeness='NOT_ESTABLISHED',
        boundary=('Exact supplied (report_id, study_id) pairs only. Input pointers locate rows within each snapshot; '
                  'they are not longitudinal identities. Scalar-to-singleton conversion and reordering retain exact pairs. '
                  'Changed literal IDs are additions/removals, not inferred renames, merges or splits. '
                  'Retained pairs mean matching supplied labels, not verified source/study identity or independence. '
                  'Report and attached-result snapshots expose changed assertions, not verified source contents. '
                  'Unchanged count requires identical pair snapshots including locations, declaration order and linked results; '
                  'empty cues are not scientific acceptance. Result presence is not complete extraction or study-level eligibility. '
                  'This focused view excludes search, screening, context, appraisal and work changes; inspect the full comparison. '
                  'No scientific, clinical or regulatory significance is determined.'))



def context_work_impact(left, right):
    """Compare exact context/evidence/work assertions, not clinical change significance."""
    review_fields={'review_status','reviewer','reviewed_at'}
    def snapshot(research):
        evidence={r['evidence_id']:r for r in research['evidence']}
        contexts={r['context_id']:r for r in research['context']['context_ledger']}
        work={cid:[] for cid in contexts}
        for item in research['work_packages']:
            for cid in item.get('context_ids',[]):
                refs=set(contexts[cid]['evidence_ids']);own=set(item['evidence_ids'])
                work[cid].append(dict(work_package=copy.deepcopy(item),
                    shared_evidence_ids=sorted(refs & own),
                    other_context_evidence_ids=sorted(refs-own),other_work_evidence_ids=sorted(own-refs)))
                if contexts[cid].get('context_scope') == 'source_review':
                    work[cid][-1].update(source_context_linkage(contexts[cid], item))
        return {cid:dict(context=copy.deepcopy(row),
                        date_roles=dict(accessed_at=row['accessed_at'],recorded_reviewed_at=row.get('reviewed_at'),
                                        publication_or_effective_date_assessment='NOT_PERFORMED'),
                        linked_evidence=[copy.deepcopy(evidence[eid]) for eid in sorted(row['evidence_ids'])],
                        work_links=sorted(work[cid],key=lambda r:r['work_package']['work_package_id']))
                for cid,row in contexts.items()}
    before,after=snapshot(left),snapshot(right);rows=[]
    for cid in sorted(set(before)|set(after)):
        a=before.get(cid);b=after.get(cid)
        ac={} if a is None else a['context'];bc={} if b is None else b['context']
        fields=changed_fields(ac,bc)
        source_fields=[f for f in fields if f not in review_fields and f!='linked_study_ids']
        evidence=entity_changes([] if a is None else a['linked_evidence'],[] if b is None else b['linked_evidence'],'evidence_id')
        evidence_changed=bool(evidence['added_ids'] or evidence['removed_ids'] or evidence['changed'])
        aw={} if a is None else {r['work_package']['work_package_id']:r for r in a['work_links']}
        bw={} if b is None else {r['work_package']['work_package_id']:r for r in b['work_links']}
        changed_work=sorted(wid for wid in set(aw)&set(bw) if canonical(aw[wid]['work_package'])!=canonical(bw[wid]['work_package']))
        retained=(a is not None and b is not None and ac['review_status']=='reviewed' and bc['review_status']=='reviewed'
                  and canonical({k:ac.get(k) for k in review_fields})==canonical({k:bc.get(k) for k in review_fields}))
        cues=[]
        if a is None:cues.append('CONTEXT_ADDED')
        if b is None:cues.append('CONTEXT_REMOVED')
        if source_fields:cues.append('CONTEXT_ASSERTIONS_CHANGED')
        if set(fields)&review_fields:cues.append('REVIEW_METADATA_CHANGED')
        if evidence_changed:cues.append('LINKED_RESULT_ASSERTIONS_CHANGED')
        if set(aw)!=set(bw):cues.append('EXPLICIT_WORK_LINKS_CHANGED')
        if changed_work:cues.append('LINKED_WORK_ASSERTIONS_CHANGED')
        if retained and (source_fields or evidence_changed):cues.append('REVIEW_LABEL_RETAINED_AFTER_INPUT_CHANGE')
        rows.append(dict(context_id=cid,before=a,after=b,changed_context_fields=fields,
                         changed_context_assertion_fields=source_fields,linked_evidence_changes=evidence,
                         work_links_added=sorted(set(bw)-set(aw)),work_links_removed=sorted(set(aw)-set(bw)),
                         changed_linked_work_ids=changed_work,work_ids_for_manual_comparison=sorted(set(aw)|set(bw)) if cues else [],
                         comparison_cues=cues,change_significance='NOT_ASSESSED',review_validity='NOT_VERIFIED'))
    return dict(contexts=rows,
                boundary=('Exact supplied context, linked result and explicitly context-linked work comparison only. '
                          'Access dates and recorded review dates are not publication/effective dates or currency checks. '
                          'Review-label retention flags unchanged reviewer/date/status assertions, not a finding that review is invalid. '
                          'A new review label/date does not prove reassessment. Shared results do not implicitly link other work. '
                          'Search/report/appraisal/experiment changes are outside this focused view; inspect the full comparison. '
                          'No clinical applicability, recommendation, regulatory status, stage transition or priority is determined.'))


def completion_work_impact(before, after, left, right):
    """Locate differences between recomputed work bases, not original acceptance reasons."""
    def snapshots(research):
        work = {row['work_package_id']: row for row in research['work_packages']}
        completion = {row['work_package_id']: row for row in research['planning']['completion_ledger']}
        bases = {row['work_package_id']: row['basis'] for row in research['planning']['review_targets']}
        packets = {wid: dict(work_package=copy.deepcopy(row), completion_review=copy.deepcopy(completion[wid]),
                            direct_prerequisite_completion_sources=[dict(work_package_id=dep,
                                supplied_work_status=work[dep]['status'],
                                source_match_status=completion[dep]['source_match_status']) for dep in row['depends_on']])
                   for wid, row in work.items()}
        return packets, bases

    old, old_bases = snapshots(left)
    new, new_bases = snapshots(right)
    source_fields = sorted(set(left['planning']['source_scope_fields']) | set(right['planning']['source_scope_fields']))
    source_changes = changed_fields({key: before.get(key) for key in source_fields},
                                    {key: after.get(key) for key in source_fields})
    rows = []
    for wid in sorted(set(old) | set(new)):
        a, b = old.get(wid), new.get(wid)
        shared = a is not None and b is not None
        details = None
        basis_fields = None
        fields = changed_fields({} if a is None else a['work_package'], {} if b is None else b['work_package'])
        prerequisite_changes = entity_changes([] if a is None else a['direct_prerequisite_completion_sources'],
                                              [] if b is None else b['direct_prerequisite_completion_sources'], 'work_package_id')
        before_ids = [] if a is None else [row['work_package_id'] for row in a['direct_prerequisite_completion_sources']]
        after_ids = [] if b is None else [row['work_package_id'] for row in b['direct_prerequisite_completion_sources']]
        prerequisite_changes.update(before_ids=before_ids, after_ids=after_ids, order_changed=before_ids != after_ids)
        cues = []
        if a is None:
            cues.append('WORK_ADDED')
        if b is None:
            cues.append('WORK_REMOVED')
        if shared:
            ab, bb = old_bases[wid], new_bases[wid]
            basis_fields = changed_fields(a['completion_review']['basis'], b['completion_review']['basis'])
            details = dict(changed_sections=changed_fields(ab, bb),
                           shared_source_fields_changed=copy.deepcopy(source_changes),
                           work_scope_fields_changed=changed_fields(ab['work_scope'], bb['work_scope']),
                           direct_dependency_scope_changes=entity_changes(ab['direct_dependency_scopes'], bb['direct_dependency_scopes'], 'work_package_id'),
                           evidence_changes=entity_changes(ab['evidence'], bb['evidence'], 'evidence_id'),
                           context_changes=entity_changes(ab['contexts'], bb['contexts'], 'context_id'),
                           appraisal_changes=entity_changes(ab['appraisals'], bb['appraisals'], 'appraisal_id'),
                           experimental_unit_changes=entity_changes(ab.get('experimental_context', {}).get('units', []),
                                                                    bb.get('experimental_context', {}).get('units', []), 'experiment_id'),
                           rationale_statement_changes=entity_changes(ab.get('rationale_statements', []),
                                                                       bb.get('rationale_statements', []), 'statement_id'))
            if basis_fields:
                cues.append('RECOMPUTED_COMPLETION_BASIS_CHANGED')
            if a['completion_review']['source_match_status'] != b['completion_review']['source_match_status']:
                cues.append('COMPLETION_SOURCE_LABEL_CHANGED')
            if any(field in fields for field in ('status', 'blocked_by')):
                cues.append('RECORDED_WORK_STATE_CHANGED')
            if any(field in fields for field in ('artifact_locator', 'acceptance_verified', 'completion_basis_sha256')):
                cues.append('SUPPLIED_COMPLETION_FIELDS_CHANGED')
            if basis_fields and a['work_package']['status'] == b['work_package']['status'] == 'COMPLETE':
                cues.append('RECORDED_COMPLETE_STATUS_RETAINED_AFTER_BASIS_CHANGE')
        if prerequisite_changes['added_ids'] or prerequisite_changes['removed_ids'] or prerequisite_changes['changed'] or prerequisite_changes['order_changed']:
            cues.append('DIRECT_PREREQUISITE_COMPLETION_ROWS_CHANGED')
        rows.append(dict(work_package_id=wid, before=a, after=b,
                         changed_work_fields=fields, changed_completion_basis_fields=basis_fields,
                         work_source_changes=details, direct_prerequisite_completion_changes=prerequisite_changes,
                         comparison_cues=cues, change_significance='NOT_ASSESSED', acceptance_assessment='NOT_PERFORMED'))
    return dict(work_packages=rows,
                boundary=('Both supplied snapshots are recomputed with the current engine; changes are not historical acceptance reasons or causal attribution. '
                          'Work/source details reuse the documented planning scope, including shared search/report context and only direct dependency work scopes. '
                          'Own artifact locator changes are separate from work/source changes; artifact bytes are not inspected. '
                          'Direct prerequisite completion labels do not recursively certify acceptance and may change without changing the dependent basis. '
                          'An already-stale assertion may remain stale with no new changes. Retained COMPLETE status or a new supplied hash proves no reassessment. '
                          'Added/removed work has null two-sided basis details. Positional-ID warnings still apply. '
                          'No work is reopened, hash renewed, acceptance verified or scientific/clinical significance inferred.'))



def amendment_review(assertion, before, after, left, right):
    """Match an external supplied change note to exact inputs; never approve it."""
    if assertion is _NO_AMENDMENT:return dict(stage='NOT_SUPPLIED',assertion=None)
    required={'schema_version','before_sha256','after_sha256','from_version','to_version','reason','authored_by','authored_at','scope_fields'}
    if not isinstance(assertion,dict) or set(assertion)!=required or type(assertion['schema_version']) is not int or assertion['schema_version']!=1:
        raise ValueError('amendment requires exact schema_version 1 fields')
    for key in ('before_sha256','after_sha256'):
        value=assertion[key]
        if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('amendment requires lowercase SHA-256 input hashes')
    for key in ('from_version','to_version','reason','authored_by'):
        if not nonempty_text(assertion[key]):raise ValueError('amendment requires '+key)
    iso_date(assertion['authored_at'],'amendment authored_at')
    scope=id_list(assertion['scope_fields'],'amendment scope_fields')
    actual=changed_fields(before,after)
    hashes=dict(before=assertion['before_sha256']==hashlib.sha256(canonical(before)).hexdigest(),
                after=assertion['after_sha256']==hashlib.sha256(canonical(after)).hexdigest())
    versions=dict(before=canonical(assertion['from_version'])==canonical(before['version']),
                  after=canonical(assertion['to_version'])==canonical(after['version']))
    missing=sorted(set(actual)-set(scope));unexpected=sorted(set(scope)-set(actual))
    def transitions(a,b,key,fields):
        a={r[key]:{f:copy.deepcopy(r[f]) for f in fields} for r in a}
        b={r[key]:{f:copy.deepcopy(r[f]) for f in fields} for r in b}
        return [dict(id=k,before=a.get(k),after=b.get(k)) for k in sorted(set(a)|set(b))
                if k not in a or k not in b or canonical(a[k])!=canonical(b[k])]
    changes=dict(
        completion=transitions(left['planning']['completion_ledger'],right['planning']['completion_ledger'],'work_package_id',('source_match_status',)),
        planning=transitions(left['planning']['planning_ledger'],right['planning']['planning_ledger'],'work_package_id',('source_match_status','current_priority_rank')),
        synthesis=transitions(left['synthesis']['statement_ledger'],right['synthesis']['statement_ledger'],'statement_id',('source_match_status','support_status')),
        work=transitions(left['work_packages'],right['work_packages'],'work_package_id',('status','blocked_by')),
        search_plan=dict(before={k:copy.deepcopy(left['search_plan_audit'][k]) for k in ('plan_status','missing_search_ids','incomplete_search_ids')},
                         after={k:copy.deepcopy(right['search_plan_audit'][k]) for k in ('plan_status','missing_search_ids','incomplete_search_ids')}))
    return dict(stage='SUPPLIED',assertion=copy.deepcopy(assertion),
                assertion_sha256=hashlib.sha256(canonical(assertion)).hexdigest(),
                input_hash_matches=hashes,version_matches=versions,
                actual_changed_fields=actual,undeclared_changed_fields=missing,declared_but_unchanged_fields=unexpected,
                binding_status='RECORDED_INPUTS_AND_SCOPE_MATCH' if all(hashes.values()) and all(versions.values()) and not missing and not unexpected else 'MISMATCH',
                observed_state_transitions=changes,
                boundary=('A supplied external change note, not approval or verified authorship. Hashes bind the exact supplied snapshots; '
                          'scope matching compares top-level field names only, not semantic scope or reason adequacy. '
                          'Transitions are recomputed from the actual before/after inputs even if the note mismatches; they are not causal attribution. '
                          'No planning/synthesis assertion is renewed and no work, scientific, clinical or regulatory decision is made.'))


def compare_protocols(before, after, amendment=_NO_AMENDMENT):
    left, right = run(before), run(after)
    left_reports = report_flow(before) if 'reports' in before else None
    right_reports = report_flow(after) if 'reports' in after else None
    left_bytes, right_bytes = canonical(before), canonical(after)
    changed = left_bytes != right_bytes
    version_changed = canonical(before['version']) != canonical(after['version'])
    old_records = {rid for row in before['searches'] for rid in row['record_ids']}
    new_records = {rid for row in after['searches'] for rid in row['record_ids']}
    positional_ids = {
        'before': [work['work_package_id'] for source, work in zip(before['gaps'], left['work_packages']) if 'work_package_id' not in source],
        'after': [work['work_package_id'] for source, work in zip(after['gaps'], right['work_packages']) if 'work_package_id' not in source],
    }
    identity_warnings = (['Work-package IDs were generated from list positions; insertion or reordering can change apparent identity. Use explicit stable IDs for longitudinal tracking.']
                         if positional_ids['before'] or positional_ids['after'] else [])
    entities = {
        'experimental_units': entity_changes(before.get('experimental_units', []), after.get('experimental_units', []), 'experiment_id'),
        'synthesis_statements': entity_changes(before.get('synthesis_statements', []), after.get('synthesis_statements', []), 'statement_id'),
        'planning_decisions': entity_changes(before.get('planning_decisions', []), after.get('planning_decisions', []), 'work_package_id'),
        'screening': entity_changes(left['screening_ledger'], right['screening_ledger'], 'record_id'),
        'evidence': entity_changes(left['evidence'], right['evidence'], 'evidence_id'),
        'work_packages': entity_changes(left['work_packages'], right['work_packages'], 'work_package_id'),
        'contexts': entity_changes(left['context']['context_ledger'], right['context']['context_ledger'], 'context_id'),
        'appraisals': entity_changes(left['appraisal']['appraisal_ledger'], right['appraisal']['appraisal_ledger'], 'appraisal_id'),
        'reports': entity_changes(left_reports['report_ledger'] if left_reports else [],
                                  right_reports['report_ledger'] if right_reports else [], 'report_id'),
        'search_plan': entity_changes(left['search_plan_audit']['search_plan_ledger'],
                                      right['search_plan_audit']['search_plan_ledger'], 'search_id'),
    }
    implementation = dict(engine_hashes(), **{'compare_runs.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    result = dict(engine_sha256=implementation, before_protocol_sha256=hashlib.sha256(left_bytes).hexdigest(),
                after_protocol_sha256=hashlib.sha256(right_bytes).hexdigest(),
                hash_scope='sorted compact UTF-8 JSON inputs; object key order ignored, list order retained; not authentication',
                has_changes=changed, before_version=before['version'], after_version=after['version'],
                version_changed=version_changed, unversioned_change=changed and not version_changed,
                changed_protocol_fields=changed_fields(before, after),
                record_ids_added=sorted(new_records - old_records), record_ids_removed=sorted(old_records - new_records),
                entity_changes=entities, amendment_review=amendment_review(amendment,before,after,left,right), context_work_impact=context_work_impact(left,right),
                completion_work_impact=completion_work_impact(before,after,left,right), positional_work_package_ids=positional_ids,
                identity_warnings=identity_warnings,
                before_counts=left['flow'], after_counts=right['flow'],
                before_report_counts=left_reports['report_flow'] if left_reports else None,
                after_report_counts=right_reports['report_flow'] if right_reports else None,
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    if has_plural_studies(before) or has_plural_studies(after):
        result['report_study_comparison'] = report_study_comparison(
            before, after, left, right, left_reports, right_reports)
    return result


def render_text(result):
    """Project the comparison without hiding unchanged stale completion assertions."""
    show = quoted_display
    lines = ['Supplied protocol comparison (not scientific reassessment)',
             'Before version: ' + show(result['before_version']),
             'After version: ' + show(result['after_version']),
             'Before protocol SHA-256: ' + result['before_protocol_sha256'],
             'After protocol SHA-256: ' + result['after_protocol_sha256'],
             'Hash scope: ' + result['hash_scope'],
             'Implementation SHA-256 fingerprints (not authentication): ' + show(result['engine_sha256']),
             'Input change flags: ' + show({key: result[key] for key in ('has_changes', 'version_changed', 'unversioned_change')}),
             'Changed protocol fields: ' + show(result['changed_protocol_fields']),
             'Identity warnings: ' + show(result['identity_warnings']),
             'Record IDs added: ' + show(result['record_ids_added']),
             'Record IDs removed: ' + show(result['record_ids_removed']),
             'Before record/result counts: ' + show(result['before_counts']),
             'After record/result counts: ' + show(result['after_counts']),
             'Before report counts (null means not supplied): ' + show(result['before_report_counts']),
             'After report counts (null means not supplied): ' + show(result['after_report_counts'])]
    note = result['amendment_review']
    lines.extend(['', 'Supplied amendment note stage: ' + note['stage']])
    if note['stage'] == 'SUPPLIED':
        lines.extend(['Note binding (not approval): ' + note['binding_status'],
                      'Supplied note: ' + show(note['assertion']),
                      'Note input hash matches: ' + show(note['input_hash_matches']),
                      'Note version matches: ' + show(note['version_matches']),
                      'Actual changed fields: ' + show(note['actual_changed_fields']),
                      'Undeclared changed fields: ' + show(note['undeclared_changed_fields']),
                      'Declared but unchanged fields: ' + show(note['declared_but_unchanged_fields']),
                      'Observed transitions (not causal attribution): ' + show(note['observed_state_transitions']),
                      note['boundary']])
    lines.extend(['', 'Changed entity rows (field names only; not change significance):'])
    changed_entities = False
    for name, changes in sorted(result['entity_changes'].items()):
        if changes['added_ids'] or changes['removed_ids'] or changes['changed']:
            changed_entities = True
            lines.append(name + ': ' + show(changes))
    if not changed_entities:
        lines.append('No changed entity rows; inspect changed protocol fields for other input changes.')
    if 'report_study_comparison' in result:
        pairs = result['report_study_comparison']
        lines.extend(['', 'Explicit report-study comparison (exact supplied pairs, not verified identity):',
                      'Before/after report ledger stage: ' + show(dict(before=pairs['before_report_ledger_stage'], after=pairs['after_report_ledger_stage'])),
                      'Before/after pair counts (null means reports not supplied): ' + show(dict(before=pairs['before_counts'], after=pairs['after_counts'])),
                      'Added pairs: ' + show(pairs['added_memberships']),
                      'Removed pairs: ' + show(pairs['removed_memberships']),
                      'Retained / identical pair snapshots: ' + show(dict(retained=pairs['retained_count'], unchanged=pairs['unchanged_count']))])
        for row in pairs['memberships']:
            def pair_state(snapshot):
                return None if snapshot is None else {key: snapshot[key] for key in (
                    'input_pointer', 'report_input_pointer', 'declaration_form', 'declared_study_ids',
                    'evidence_ids', 'has_result_rows')}
            lines.extend(['Pair: ' + show(dict(report_id=row['report_id'], study_id=row['study_id'])),
                          'Membership status: ' + row['membership_status'],
                          'Before/after supplied membership: ' + show(dict(before=pair_state(row['before']), after=pair_state(row['after']))),
                          'Pair cues: ' + show(row['comparison_cues']),
                          'Changed report fields: ' + show(row['changed_report_fields']),
                          'Linked result changes: ' + show(row['linked_evidence_changes'])])
        lines.extend(['Pair verification boundaries: ' + show({key: pairs[key] for key in (
            'change_significance', 'study_identity_verification', 'study_eligibility_assessment', 'extraction_completeness')}), pairs['boundary']])
    lines.extend(['', 'Context comparison (all supplied context IDs):'])
    for row in result['context_work_impact']['contexts']:
        def context_state(snapshot):
            return None if snapshot is None else dict(review_status=snapshot['context']['review_status'],
                                                      date_roles=snapshot['date_roles'])
        lines.extend(['Context: ' + show(row['context_id']),
                      'Before/after supplied review: ' + show(dict(before=context_state(row['before']), after=context_state(row['after']))),
                      'Context cues: ' + show(row['comparison_cues']),
                      'Changed context fields: ' + show(row['changed_context_fields']),
                      'Linked evidence changes: ' + show(row['linked_evidence_changes']),
                      'Explicit work IDs for manual comparison: ' + show(row['work_ids_for_manual_comparison'])])
        def source_links(snapshot):
            if snapshot is None or snapshot['context'].get('context_scope') != 'source_review':
                return None
            return dict(source_refs=snapshot['context']['source_refs'], linked_study_ids=snapshot['context']['linked_study_ids'],
                        work_links=[dict(work_package_id=link['work_package']['work_package_id'],
                                         **{key:link[key] for key in ('shared_source_refs','other_context_source_refs','other_work_source_refs')})
                                    for link in snapshot['work_links']])
        before_sources, after_sources = source_links(row['before']), source_links(row['after'])
        if before_sources is not None or after_sources is not None:
            lines.append('Before/after pre-extraction typed links (not applicability): '
                         + show(dict(before=before_sources, after=after_sources)))
    lines.extend(['', 'Completion comparison (all work IDs; unchanged stale/unbound assertions remain visible):'])
    for row in result['completion_work_impact']['work_packages']:
        def work_state(snapshot):
            if snapshot is None:
                return None
            work, review = snapshot['work_package'], snapshot['completion_review']
            return dict(status=work['status'], blocked_by=work['blocked_by'],
                        completion_source_status=review['source_match_status'],
                        supplied_basis_sha256=review['supplied_basis_sha256'],
                        current_basis_sha256=review['current_basis_sha256'])
        lines.extend(['Work: ' + show(row['work_package_id']),
                      'Before supplied state: ' + show(work_state(row['before'])),
                      'After supplied state: ' + show(work_state(row['after'])),
                      'Completion cues: ' + show(row['comparison_cues']),
                      'Changed work fields: ' + show(row['changed_work_fields']),
                      'Changed completion-basis fields (null means no two-sided basis): ' + show(row['changed_completion_basis_fields'])])
        details = row['work_source_changes']
        if details is None:
            lines.append('Work/source comparison: no two-sided basis for added/removed work.')
        else:
            lines.append('Changed work/source sections: ' + show(details['changed_sections']))
            for name, value in details.items():
                if name == 'changed_sections':
                    continue
                if ((isinstance(value, list) and value)
                        or (isinstance(value, dict) and (value['added_ids'] or value['removed_ids'] or value['changed']))):
                    lines.append(name + ': ' + show(value))
        for side in ('before', 'after'):
            snapshot = row[side]
            lines.append(side.capitalize() + ' direct prerequisite source labels: ' +
                         show(None if snapshot is None else snapshot['direct_prerequisite_completion_sources']))
        lines.append('Direct prerequisite changes/order: ' + show(row['direct_prerequisite_completion_changes']))
    lines.extend(['', 'Empty change cues are not acceptance or completeness; no sources or artifact bytes were verified.',
                  'Full assertion snapshots and unchanged entity details remain in the default JSON output.',
                  result['context_work_impact']['boundary'], result['completion_work_impact']['boundary'],
                  result['boundary'], 'Census: ' + result['census_claim'], 'Conclusion: ' + result['conclusion_readiness']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--amendment',type=Path,help='optional supplied change-note JSON; checked, never approved')
    parser.add_argument('--text', action='store_true', help='read-only comparison summary; default remains full JSON')
    args = parser.parse_args()
    try:
        result = compare_protocols(parse_json(args.before.read_text(encoding='utf-8')),
                                   parse_json(args.after.read_text(encoding='utf-8')),
                                   parse_json(args.amendment.read_bytes()) if args.amendment else _NO_AMENDMENT)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
    if args.text:
        print(render_text(result), end='')
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    if args.amendment and result['amendment_review']['binding_status']=='MISMATCH':parser.exit(1)


if __name__ == '__main__':
    main()
