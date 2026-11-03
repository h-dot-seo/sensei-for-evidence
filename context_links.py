"""Validate supplied guideline/development context links without judging their validity."""
from datetime import date

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


def link_context(protocol, evidence, work_packages):
    supplied = protocol.get('contexts', [])
    if not isinstance(supplied, list):
        raise ValueError('contexts must be a list')
    known_evidence = {row['record_id']: row for row in evidence}
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
        if not links or any(eid not in known_evidence for eid in links):
            raise ValueError('context must link to known extracted evidence')
        review = row.get('review_status', 'pending')
        if review not in ('pending', 'reviewed'):
            raise ValueError('context review_status must be pending or reviewed')
        if review == 'reviewed':
            if not nonempty_text(row.get('reviewer')):
                raise ValueError('reviewed context requires reviewer')
            iso_date(row.get('reviewed_at'), 'reviewed_at')
        contexts[cid] = dict(row, review_status=review,
                             linked_study_ids=sorted({known_evidence[eid]['study_id'] for eid in links}))
    work_links = []
    used = set()
    for work in work_packages:
        refs = id_list(work.get('context_ids', []), 'work package context_ids')
        if any(cid not in contexts for cid in refs):
            raise ValueError('work package references unknown context')
        for cid in refs:
            if not set(contexts[cid]['evidence_ids']).intersection(work['evidence_ids']):
                raise ValueError('work package context must share a linked evidence ID')
        used.update(refs)
        work_links.append(dict(work_package_id=work['work_package_id'], context_ids=refs,
                               context_review_pending=sorted(cid for cid in refs
                                                             if contexts[cid]['review_status'] == 'pending')))
    return dict(context_ledger=[contexts[cid] for cid in sorted(contexts)],
                work_package_context=work_links,
                review_pending=sorted(cid for cid in contexts if contexts[cid]['review_status'] == 'pending'),
                unassigned_context_ids=sorted(set(contexts) - used),
                boundary=BOUNDARY)
