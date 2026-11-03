"""Compare validated supplied protocols without inferring scientific meaning from changes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from evidence_workflow import run
from context_links import nonempty_text, iso_date, id_list
from json_io import configure_utf8_stdio, parse_json, canonical_json_bytes as canonical
from prisma_reports import report_flow
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
    return dict(engine_sha256=implementation, before_protocol_sha256=hashlib.sha256(left_bytes).hexdigest(),
                after_protocol_sha256=hashlib.sha256(right_bytes).hexdigest(),
                hash_scope='sorted compact UTF-8 JSON inputs; object key order ignored, list order retained; not authentication',
                has_changes=changed, before_version=before['version'], after_version=after['version'],
                version_changed=version_changed, unversioned_change=changed and not version_changed,
                changed_protocol_fields=changed_fields(before, after),
                record_ids_added=sorted(new_records - old_records), record_ids_removed=sorted(old_records - new_records),
                entity_changes=entities, amendment_review=amendment_review(amendment,before,after,left,right), context_work_impact=context_work_impact(left,right), positional_work_package_ids=positional_ids,
                identity_warnings=identity_warnings,
                before_counts=left['flow'], after_counts=right['flow'],
                before_report_counts=left_reports['report_flow'] if left_reports else None,
                after_report_counts=right_reports['report_flow'] if right_reports else None,
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--amendment',type=Path,help='optional supplied change-note JSON; checked, never approved')
    args = parser.parse_args()
    try:
        result = compare_protocols(parse_json(args.before.read_text(encoding='utf-8')),
                                   parse_json(args.after.read_text(encoding='utf-8')),
                                   parse_json(args.amendment.read_bytes()) if args.amendment else _NO_AMENDMENT)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    if args.amendment and result['amendment_review']['binding_status']=='MISMATCH':parser.exit(1)


if __name__ == '__main__':
    main()
