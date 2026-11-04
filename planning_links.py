"""Track supplied planning ranks and source staleness without generating priorities."""
import copy
import hashlib
from context_links import nonempty_text, iso_date, id_list
from json_io import canonical_json_bytes

BOUNDARY = ('Ranks, rationale and planner labels are supplied assertions, not independently '
            'verified priorities or advice. Source matching is content consistency, not planning '
            'quality. Stale ranks are historical and excluded from current rank groups. '
            'Optional statement links are supplied rationale references, not support or refutation judgments. '
            'Dependency order and scientific/clinical readiness are not changed.')
PROGRESS_FIELDS = {'status', 'blocked_by', 'artifact_locator', 'acceptance_verified', 'completion_basis_sha256'}


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def link_planning(protocol, evidence, work, context, appraisal, experiments=None, synthesis=None):
    if 'experimental_units' in protocol and (not isinstance(experiments, dict) or experiments.get('stage') != 'SUPPLIED'):
        raise ValueError('supplied experimental units require validated experiment binding')
    supplied = protocol.get('planning_decisions', [])
    if not isinstance(supplied, list):
        raise ValueError('planning_decisions must be a list')
    work_by_id = {row['work_package_id']: row for row in work}
    evidence_by_id = {row['evidence_id']: row for row in evidence}
    context_by_id = {row['context_id']: row for row in context['context_ledger']}
    # Shared source context is hashed once, not once per work package.
    source_scope = {key: protocol.get(key) for key in
                    ('question', 'inclusion_criteria', 'exclusion_criteria', 'search_plan', 'searches', 'screening', 'reports')}
    source_hash = digest(source_scope)
    scope_by_id = {wid: {k: copy.deepcopy(v) for k, v in row.items() if k not in PROGRESS_FIELDS}
                   for wid, row in work_by_id.items()}
    source_result_ids = {}
    for item in evidence: source_result_ids.setdefault(item['record_id'],[]).append(item['evidence_id'])
    for wid,row in work_by_id.items():
        if row.get('work_type') == 'source_review':
            record_refs = {ref['record_id'] for ref in row['source_refs'] if ref['kind']=='record'}
            scope_by_id[wid]['source_result_inventory'] = [dict(record_id=rid,evidence_ids=sorted(source_result_ids.get(rid,[]))) for rid in sorted(record_refs)]
    statement_by_id = ({row['statement_id']:row for row in synthesis['statement_ledger']}
                       if isinstance(synthesis,dict) and synthesis.get('stage')=='SUPPLIED' else {})
    decisions = {}
    for decision in supplied:
        if not isinstance(decision, dict):
            raise ValueError('planning decision must be an object')
        for field in ('work_package_id', 'rationale', 'uncertainty', 'planner', 'planned_at', 'basis_sha256'):
            if not nonempty_text(decision.get(field)):
                raise ValueError('planning decision requires ' + field)
        wid = decision['work_package_id']
        if wid not in work_by_id or wid in decisions:
            raise ValueError('unknown or duplicate planning work package')
        rank = decision.get('priority_rank')
        if type(rank) is not int or rank < 1:
            raise ValueError('supplied priority_rank must be a positive integer')
        value = decision['basis_sha256']
        if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('planning basis_sha256 must be lowercase SHA-256 hex')
        iso_date(decision['planned_at'], 'planned_at')
        if 'rationale_statement_ids' in decision:
            refs=id_list(decision['rationale_statement_ids'],'rationale_statement_ids')
            if not refs:raise ValueError('rationale_statement_ids must be nonempty when supplied')
            if not isinstance(synthesis,dict) or synthesis.get('stage')!='SUPPLIED':
                raise ValueError('planning rationale references require validated synthesis binding')
            if any(sid not in statement_by_id for sid in refs):raise ValueError('planning rationale references unknown statement')
            if any(not set(statement_by_id[sid]['evidence_ids']).intersection(work_by_id[wid]['evidence_ids']) for sid in refs):
                raise ValueError('planning rationale statement must share work evidence')
        decisions[wid] = copy.deepcopy(decision)
    targets = {}
    for wid, row in work_by_id.items():
        refs = set(row['evidence_ids'])
        basis = dict(schema_version=1, source_scope_sha256=source_hash,
            work_scope=scope_by_id[wid],
            direct_dependency_scopes=[scope_by_id[dep] for dep in row['depends_on']],
            evidence=[copy.deepcopy(evidence_by_id[eid]) for eid in sorted(refs)],
            contexts=[copy.deepcopy(context_by_id[cid]) for cid in sorted(row.get('context_ids', []))],
            appraisals=[copy.deepcopy(item) for item in appraisal['appraisal_ledger'] if refs.intersection(item['evidence_ids'])])
        if experiments is not None and experiments['stage'] == 'SUPPLIED':
            basis['experimental_context'] = dict(stage='SUPPLIED', units=[copy.deepcopy(item) for item in experiments['experimental_unit_ledger'] if refs.intersection(item['evidence_ids'])])
        if 'rationale_statement_ids' in decisions.get(wid,{}):
            basis['rationale_statements']=[copy.deepcopy(statement_by_id[sid]) for sid in sorted(decisions[wid]['rationale_statement_ids'])]
        targets[wid] = dict(work_package_id=wid, basis=basis, basis_sha256=digest(basis))
    ledger, groups, missing, stale = [], {}, [], []
    for wid in sorted(work_by_id):
        decision = decisions.get(wid)
        match = ('NOT_SUPPLIED' if decision is None else
                 'CURRENT_SOURCE' if decision['basis_sha256'] == targets[wid]['basis_sha256'] else 'STALE_SOURCE')
        if match == 'NOT_SUPPLIED': missing.append(wid)
        if match == 'STALE_SOURCE': stale.append(wid)
        if match == 'CURRENT_SOURCE': groups.setdefault(decision['priority_rank'], []).append(wid)
        ledger.append(dict(work_package_id=wid, source_match_status=match, assertion=decision,
                           current_priority_rank=decision['priority_rank'] if match == 'CURRENT_SOURCE' else None,
                           current_basis_sha256=targets[wid]['basis_sha256']))
        if decision is not None and 'rationale_statement_ids' in decision:
            ledger[-1]['rationale_statement_links']=[dict(
                statement=copy.deepcopy(statement),
                work_evidence_ids=sorted(set(statement['evidence_ids']) & set(work_by_id[wid]['evidence_ids'])),
                other_statement_evidence_ids=sorted(set(statement['evidence_ids'])-set(work_by_id[wid]['evidence_ids'])),
                rationale_support_assessment='NOT_PERFORMED')
                for statement in targets[wid]['basis']['rationale_statements']]
    completion=[]
    for wid in sorted(work_by_id):
        item=work_by_id[wid]
        if 'completion_basis_sha256' in item:
            supplied_hash=item['completion_basis_sha256']
            if item['status']!='COMPLETE':raise ValueError('completion basis requires COMPLETE work assertion')
            if not isinstance(supplied_hash,str) or len(supplied_hash)!=64 or any(c not in '0123456789abcdef' for c in supplied_hash):
                raise ValueError('completion_basis_sha256 must be lowercase SHA-256 hex')
        basis=dict(schema_version=1,work_source_basis_sha256=targets[wid]['basis_sha256'],artifact_locator=item.get('artifact_locator'))
        current_hash=digest(basis)
        state=('NOT_COMPLETE' if item['status']!='COMPLETE' else
               'UNBOUND_COMPLETION' if 'completion_basis_sha256' not in item else
               'CURRENT_SOURCE' if item['completion_basis_sha256']==current_hash else 'STALE_SOURCE')
        completion.append(dict(work_package_id=wid,source_match_status=state,basis=basis,current_basis_sha256=current_hash,
                               supplied_basis_sha256=item.get('completion_basis_sha256'),acceptance_assessment='NOT_PERFORMED',
                               artifact_content_verification='NOT_PERFORMED'))
    return dict(schema_version=1, source_scope_fields=list(source_scope), source_scope_sha256=source_hash,
                review_targets=[targets[wid] for wid in sorted(targets)], planning_ledger=ledger, completion_ledger=completion,
                completion_boundary='Completion binding reuses the planning work/source basis plus the literal artifact locator. It does not verify artifact bytes, criteria satisfaction or scientific acceptance; recorded status and dependencies are unchanged.',
                current_rank_groups=[dict(supplied_priority_rank=rank, work_package_ids=groups[rank],
                                          tie=len(groups[rank]) > 1) for rank in sorted(groups)],
                work_without_planning_assertion=missing, work_with_stale_planning_assertion=stale,
                current_rank_groups_scope='protocol-wide assertions, including completed work; not an execution queue',
                rank_order_scope='supplied ordinal ranks only; tied IDs are listed lexically, not tie-broken',
                progress_exclusions=sorted(PROGRESS_FIELDS), boundary=BOUNDARY)
