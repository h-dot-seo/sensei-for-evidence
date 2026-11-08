"""Trace supplied synthesis statements without judging entailment or writing conclusions."""
import copy
from context_links import id_list, iso_date, nonempty_text
from planning_links import digest

BOUNDARY = ('Statements and review labels are supplied assertions. Linked citations do not '
            'establish entailment, causal validity, evidence adequacy or clinical suitability. '
            'Source matching is not reviewer authentication. Uncited results are visible but '
            'are not automatically omission errors. No synthesis text or conclusions are generated.')



def position_groups(rows, refs, statement_text):
    """Group supplied positions, not assess claim support or combine evidence."""
    if not isinstance(rows, list):
        raise ValueError('evidence_positions must be a list')
    required = {'evidence_id', 'claim_component', 'aspect', 'relation', 'rationale',
                'source_locator', 'source_excerpt', 'limitations', 'recorded_by', 'recorded_at'}
    seen, covered, groups = set(), set(), {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != required or any(not nonempty_text(row[k]) for k in required):
            raise ValueError('evidence position requires exact nonempty textual fields')
        eid = row['evidence_id']
        if eid not in refs:
            raise ValueError('evidence position must reference a cited result')
        if row['claim_component'] not in statement_text:
            raise ValueError('claim_component must be an exact supplied statement substring')
        if row['aspect'] not in ('observation', 'causal', 'clinical_applicability', 'other'):
            raise ValueError('invalid supplied claim aspect')
        if row['relation'] not in ('supports', 'challenges', 'mixed', 'unclear', 'not_assessed'):
            raise ValueError('invalid supplied evidence relation')
        iso_date(row['recorded_at'], 'position recorded_at')
        key = (row['claim_component'], row['aspect'])
        identity = (eid,) + key
        if identity in seen:
            raise ValueError('duplicate position for the same result, claim component and aspect')
        seen.add(identity); covered.add(eid)
        groups.setdefault(key, []).append(copy.deepcopy(row))
    if covered != set(refs):
        raise ValueError('evidence_positions must explicitly cover every cited result; use not_assessed when needed')
    return [dict(claim_component=key[0], aspect=key[1],
                 positions=sorted(groups[key], key=lambda r:r['evidence_id']),
                 assessment='NOT_PERFORMED') for key in sorted(groups)]

def link_synthesis(protocol, evidence, context, appraisal, experiments=None):
    if 'experimental_units' in protocol and (not isinstance(experiments, dict) or experiments.get('stage') != 'SUPPLIED'):
        raise ValueError('supplied experimental units require validated experiment binding')
    supplied = protocol.get('synthesis_statements', [])
    if not isinstance(supplied, list):
        raise ValueError('synthesis_statements must be a list')
    known = {row['evidence_id']: row for row in evidence}
    contexts = {row['context_id']: row for row in context['context_ledger']}
    scope = {key: protocol.get(key) for key in ('question', 'inclusion_criteria', 'exclusion_criteria',
                                              'search_plan', 'searches', 'screening', 'reports')}
    source_hash = digest(scope)
    ledger, targets, used = {}, {}, set()
    allowed = {'statement_id', 'text', 'limitations', 'evidence_ids', 'context_ids',
               'review_status', 'reviewer', 'reviewed_at', 'basis_sha256', 'evidence_positions'}
    for row in supplied:
        if not isinstance(row, dict) or set(row) - allowed:
            raise ValueError('synthesis statement must be an object with known fields')
        for field in ('statement_id', 'text', 'limitations'):
            if not nonempty_text(row.get(field)):
                raise ValueError('synthesis statement requires ' + field)
        sid = row['statement_id']
        if sid in ledger:
            raise ValueError('duplicate synthesis statement ID')
        try:
            refs = id_list(row.get('evidence_ids'), 'evidence_ids')
        except ValueError as error:
            raise ValueError('statement ' + ascii(sid) + ': ' + str(error)) from error
        if not refs:
            raise ValueError('statement ' + ascii(sid) + ' requires at least one evidence citation')
        unknown = [eid for eid in refs if eid not in known]
        if unknown:
            raise ValueError('statement ' + ascii(sid) + ' has unknown evidence citations: ' + ascii(unknown))
        try:
            cids = id_list(row.get('context_ids', []), 'context_ids')
        except ValueError as error:
            raise ValueError('statement ' + ascii(sid) + ': ' + str(error)) from error
        unknown_contexts = [cid for cid in cids if cid not in contexts]
        if unknown_contexts:
            raise ValueError('statement ' + ascii(sid) + ' has unknown contexts: ' + ascii(unknown_contexts))
        for cid in cids:
            if not set(contexts[cid]['evidence_ids']).intersection(refs):
                raise ValueError('statement ' + ascii(sid) + ' context ' + ascii(cid) + ' must share cited evidence')
        review = row.get('review_status', 'pending')
        if review not in ('pending', 'reviewed'):
            raise ValueError('synthesis review_status must be pending or reviewed')
        if review == 'reviewed' and not all(field in row for field in ('reviewer', 'reviewed_at', 'basis_sha256')):
            raise ValueError('reviewed synthesis requires reviewer, reviewed_at and basis_sha256')
        if 'reviewer' in row and not nonempty_text(row['reviewer']):
            raise ValueError('synthesis reviewer must be a nonempty string')
        if 'reviewed_at' in row:
            iso_date(row['reviewed_at'], 'reviewed_at')
        if 'basis_sha256' in row:
            value = row['basis_sha256']
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('synthesis basis must be lowercase SHA-256 hex')
        basis = dict(schema_version=1, source_scope_sha256=source_hash,
                     statement={key: copy.deepcopy(row[key]) for key in ('statement_id', 'text', 'limitations', 'evidence_ids')},
                     context_ids=copy.deepcopy(cids), evidence=[copy.deepcopy(known[eid]) for eid in refs],
                     contexts=[copy.deepcopy(contexts[cid]) for cid in cids],
                     appraisals=[copy.deepcopy(item) for item in appraisal['appraisal_ledger'] if set(refs).intersection(item['evidence_ids'])])
        if experiments is not None and experiments['stage'] == 'SUPPLIED':
            basis['experimental_context'] = dict(stage='SUPPLIED', units=[copy.deepcopy(item) for item in experiments['experimental_unit_ledger'] if set(refs).intersection(item['evidence_ids'])])
        groups = None
        if 'evidence_positions' in row:
            groups = position_groups(row['evidence_positions'], refs, row['text'])
            basis['evidence_positions'] = copy.deepcopy(row['evidence_positions'])
        current_hash = digest(basis)
        match = ('PENDING_REVIEW' if review == 'pending' else
                 'CURRENT_SOURCE' if row['basis_sha256'] == current_hash else 'STALE_SOURCE')
        targets[sid] = dict(statement_id=sid, basis=basis, basis_sha256=current_hash)
        ledger[sid] = dict(copy.deepcopy(row), context_ids=copy.deepcopy(cids), review_status=review,
                           source_match_status=match, current_basis_sha256=current_hash,
                           support_status='NOT_ASSESSED')
        if groups is not None:
            ledger[sid]['position_comparison'] = dict(stage='SUPPLIED', groups=groups,
                unresolved_evidence_ids=sorted({item['evidence_id'] for item in row['evidence_positions'] if item['relation'] in ('unclear', 'not_assessed')}),
                aspect_coverage='only_explicit_components_and_aspects_not_exhaustive',
                boundary='Positions, source excerpts and author labels are unverified supplied assertions. A position is not a study or independent vote. No stance, refutation, causality, ranking or consensus is inferred. Statement source matching is not support assessment.')
        used.update(refs)
    return dict(schema_version=1, stage='SUPPLIED' if 'synthesis_statements' in protocol else 'NOT_SUPPLIED',
                source_scope_fields=list(scope), source_scope_sha256=source_hash,
                statement_ledger=[ledger[sid] for sid in sorted(ledger)],
                review_targets=[targets[sid] for sid in sorted(targets)],
                pending_statement_ids=sorted(sid for sid, row in ledger.items() if row['source_match_status'] == 'PENDING_REVIEW'),
                stale_statement_ids=sorted(sid for sid, row in ledger.items() if row['source_match_status'] == 'STALE_SOURCE'),
                statements_without_evidence_positions=sorted(sid for sid,row in ledger.items() if 'evidence_positions' not in row) if 'synthesis_statements' in protocol else None,
                statements_with_unresolved_positions=sorted(sid for sid,row in ledger.items() if row.get('position_comparison', {}).get('unresolved_evidence_ids')) if 'synthesis_statements' in protocol else None,
                evidence_without_statement_citation=sorted(set(known)-used), boundary=BOUNDARY)
