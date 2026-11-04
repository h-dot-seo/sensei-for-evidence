"""Validate supplied guideline/development context links without judging their validity."""
from datetime import date
import copy

COMMON_FIELDS = ('context_id', 'title', 'issuer', 'locator', 'version', 'accessed_at',
                 'population_or_setting', 'relevance_statement', 'applicability', 'limitations')
DOMAIN_FIELDS = {
    'clinical_guideline': ('recommendation_strength', 'evidence_certainty'),
    'drug_development': ('development_stage', 'regulatory_status'),
}
BOUNDARY = ('Supplied context assertions only; no guideline retrieval, currency check, '
            'clinical recommendation, regulatory determination or scientific appraisal. '
            'A reviewed status records an operator assertion, not independent verification.')


def nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def iso_date(value, field):
    if not nonempty_text(value):
        raise ValueError('context requires ' + field)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(field + ' must be an ISO date (YYYY-MM-DD)') from None
    if parsed.isoformat() != value:
        raise ValueError(field + ' must be an ISO date (YYYY-MM-DD)')


def id_list(value, field):
    if (not isinstance(value, list) or any(not nonempty_text(v) for v in value)
            or len(set(value)) != len(value)):
        raise ValueError(field + ' must be a list of unique nonempty IDs')
    return value


def source_ref_key(ref):
    return (ref['kind'], ref['search_id'] if ref['kind'] == 'planned_search' else ref['record_id'])


def validate_source_refs(refs, planned_ids, record_ids):
    """Validate exact typed source identity without inferring containment links."""
    if not isinstance(refs, list) or not refs:
        raise ValueError('source_review requires nonempty source_refs')
    seen = set()
    for ref in refs:
        if not isinstance(ref, dict) or ref.get('kind') not in ('planned_search', 'record'):
            raise ValueError('source reference kind must be planned_search or record')
        key = 'search_id' if ref['kind'] == 'planned_search' else 'record_id'
        if set(ref) != {'kind', key} or not nonempty_text(ref.get(key)):
            raise ValueError('source reference requires exact fields and nonempty ID')
        if ref[key] not in (planned_ids if key == 'search_id' else record_ids):
            raise ValueError('source reference must identify a declared search or enumerated record')
        identity = source_ref_key(ref)
        if identity in seen:
            raise ValueError('duplicate source reference')
        seen.add(identity)
    return refs


def source_context_linkage(context, work):
    """Project already validated exact references; no search-to-record inheritance."""
    context_refs = {source_ref_key(ref): ref for ref in context['source_refs']}
    work_refs = {source_ref_key(ref): ref for ref in work.get('source_refs', [])}
    shared = set(context_refs) & set(work_refs)
    return dict(shared_source_refs=[copy.deepcopy(context_refs[key]) for key in sorted(shared)],
                other_context_source_refs=[copy.deepcopy(context_refs[key]) for key in sorted(set(context_refs) - shared)],
                other_work_source_refs=[copy.deepcopy(work_refs[key]) for key in sorted(set(work_refs) - shared)],
                linkage_scope='exact_typed_source_reference_not_evidence_or_applicability')


def link_context(protocol, evidence, work_packages):
    supplied = protocol.get('contexts', [])
    if not isinstance(supplied, list):
        raise ValueError('contexts must be a list')
    known_evidence = {row.get('evidence_id', row['record_id']): row for row in evidence}
    source_ids = None
    contexts = {}
    for row in supplied:
        if not isinstance(row, dict):
            raise ValueError('context must be an object')
        for field in COMMON_FIELDS:
            if not nonempty_text(row.get(field)):
                raise ValueError('context requires ' + field)
        cid = row['context_id']
        if cid in contexts:
            raise ValueError('duplicate context ID')
        domain = row.get('domain')
        if not isinstance(domain, str) or domain not in DOMAIN_FIELDS:
            raise ValueError('context domain must be clinical_guideline or drug_development')
        for field in DOMAIN_FIELDS[domain]:
            if not nonempty_text(row.get(field)):
                raise ValueError('context requires ' + field + '; use unknown when unassessed')
        iso_date(row['accessed_at'], 'accessed_at')
        links = id_list(row.get('evidence_ids'), 'context evidence_ids')
        scope = row.get('context_scope', 'extracted_evidence')
        if scope not in ('extracted_evidence', 'source_review'):
            raise ValueError('context_scope must be extracted_evidence or source_review')
        if scope == 'source_review':
            if links:
                raise ValueError('source_review context requires empty evidence_ids; no extracted evidence is implied')
            if source_ids is None:
                source_ids = ({item['search_id'] for item in protocol.get('search_plan', []) or []},
                              {rid for item in protocol.get('searches', []) for rid in item['record_ids']})
            planned_ids, record_ids = source_ids
            validate_source_refs(row.get('source_refs'), planned_ids, record_ids)
        else:
            if 'source_refs' in row:
                raise ValueError('context source_refs require explicit source_review scope')
            if not links or any(eid not in known_evidence for eid in links):
                raise ValueError('context must link to known extracted evidence')
        review = row.get('review_status', 'pending')
        if review not in ('pending', 'reviewed'):
            raise ValueError('context review_status must be pending or reviewed')
        if scope == 'source_review':
            if 'reviewer' in row and not nonempty_text(row['reviewer']):
                raise ValueError('source_review context supplied reviewer must be nonblank')
            if 'reviewed_at' in row:
                iso_date(row['reviewed_at'], 'reviewed_at')
        if review == 'reviewed':
            if not nonempty_text(row.get('reviewer')):
                raise ValueError('reviewed context requires reviewer')
            iso_date(row.get('reviewed_at'), 'reviewed_at')
        contexts[cid] = dict(copy.deepcopy(row), review_status=review,
                             linked_study_ids=sorted({known_evidence[eid]['study_id'] for eid in links}))
    work_links = []
    used = set()
    for work in work_packages:
        refs = id_list(work.get('context_ids', []), 'work package context_ids')
        if any(cid not in contexts for cid in refs):
            raise ValueError('work package references unknown context')
        for cid in refs:
            if contexts[cid].get('context_scope') == 'source_review':
                if work.get('work_type') != 'source_review':
                    raise ValueError('source_review context may link only to source_review work')
                if not source_context_linkage(contexts[cid], work)['shared_source_refs']:
                    raise ValueError('source_review context and work must share an exact typed source reference')
            elif not set(contexts[cid]['evidence_ids']).intersection(work['evidence_ids']):
                raise ValueError('work package context must share a linked evidence ID')
        used.update(refs)
        work_links.append(dict(work_package_id=work['work_package_id'], context_ids=copy.deepcopy(refs),
                               context_review_pending=sorted(cid for cid in refs
                                                             if contexts[cid]['review_status'] == 'pending')))
    return dict(context_ledger=[contexts[cid] for cid in sorted(contexts)],
                work_package_context=work_links,
                review_pending=sorted(cid for cid in contexts if contexts[cid]['review_status'] == 'pending'),
                unassigned_context_ids=sorted(set(contexts) - used),
                boundary=BOUNDARY)
