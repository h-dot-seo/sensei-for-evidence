"""Trace supplied synthesis statements without judging entailment or writing conclusions."""
import copy
from context_links import id_list, iso_date, nonempty_text
from planning_links import digest

BOUNDARY = ('Statements and review labels are supplied assertions. Linked citations do not '
            'establish entailment, causal validity, evidence adequacy or clinical suitability. '
            'Source matching is not reviewer authentication. Uncited results are visible but '
            'are not automatically omission errors. No synthesis text or conclusions are generated.')


def link_synthesis(protocol, evidence, context, appraisal):
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
               'review_status', 'reviewer', 'reviewed_at', 'basis_sha256'}
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
        current_hash = digest(basis)
        match = ('PENDING_REVIEW' if review == 'pending' else
                 'CURRENT_SOURCE' if row['basis_sha256'] == current_hash else 'STALE_SOURCE')
        targets[sid] = dict(statement_id=sid, basis=basis, basis_sha256=current_hash)
        ledger[sid] = dict(copy.deepcopy(row), context_ids=copy.deepcopy(cids), review_status=review,
                           source_match_status=match, current_basis_sha256=current_hash,
                           support_status='NOT_ASSESSED')
        used.update(refs)
    return dict(schema_version=1, stage='SUPPLIED' if 'synthesis_statements' in protocol else 'NOT_SUPPLIED',
                source_scope_fields=list(scope), source_scope_sha256=source_hash,
                statement_ledger=[ledger[sid] for sid in sorted(ledger)],
                review_targets=[targets[sid] for sid in sorted(targets)],
                pending_statement_ids=sorted(sid for sid, row in ledger.items() if row['source_match_status'] == 'PENDING_REVIEW'),
                stale_statement_ids=sorted(sid for sid, row in ledger.items() if row['source_match_status'] == 'STALE_SOURCE'),
                evidence_without_statement_citation=sorted(set(known)-used), boundary=BOUNDARY)
