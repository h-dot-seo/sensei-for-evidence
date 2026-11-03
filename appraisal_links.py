"""Preserve supplied appraisal methods and domain judgements without scoring evidence."""
from context_links import id_list, iso_date, nonempty_text

BOUNDARY = ('Supplied appraisal provenance only. No appraisal tool is executed, no domain '
            'rubric or method suitability is validated, and no score, consensus or '
            'scientific adequacy is inferred. Missing rows denote absent recorded appraisal, '
            'not a judgement that the underlying study is poor quality.')


def link_appraisals(protocol, evidence, work_packages):
    supplied = protocol.get('appraisals', [])
    if not isinstance(supplied, list):
        raise ValueError('appraisals must be a list')
    known = {row['evidence_id']: row for row in evidence}
    ledger = {}
    by_evidence = {eid: [] for eid in known}
    for row in supplied:
        if not isinstance(row, dict):
            raise ValueError('appraisal must be an object')
        for field in ('appraisal_id', 'method', 'method_version', 'method_locator', 'reviewer', 'assessed_at', 'limitations'):
            if not nonempty_text(row.get(field)):
                raise ValueError('appraisal requires ' + field)
        aid = row['appraisal_id']
        if aid in ledger:
            raise ValueError('duplicate appraisal ID')
        iso_date(row['assessed_at'], 'assessed_at')
        refs = id_list(row.get('evidence_ids'), 'appraisal evidence_ids')
        if not refs or any(eid not in known for eid in refs):
            raise ValueError('appraisal must link to known extracted evidence')
        studies = {known[eid]['study_id'] for eid in refs}
        if len(studies) != 1:
            raise ValueError('one appraisal record must stay within one supplied study ID')
        domains = row.get('domains')
        if not isinstance(domains, list) or not domains:
            raise ValueError('appraisal domains must be a nonempty list')
        names = set()
        for domain in domains:
            if not isinstance(domain, dict):
                raise ValueError('appraisal domain must be an object')
            for field in ('name', 'judgement', 'rationale', 'source_locator'):
                if not nonempty_text(domain.get(field)):
                    raise ValueError('appraisal domain requires ' + field)
            if domain['name'] in names:
                raise ValueError('duplicate appraisal domain name')
            names.add(domain['name'])
        ledger[aid] = dict(row, linked_study_id=next(iter(studies)),
                           scope='listed_extraction_ids_only')
        for eid in refs:
            by_evidence[eid].append(aid)
    missing = sorted(eid for eid, aids in by_evidence.items() if not aids)
    work_links = []
    for work in work_packages:
        refs = work['evidence_ids']
        work_links.append(dict(work_package_id=work['work_package_id'],
                               appraisal_ids=sorted({aid for eid in refs for aid in by_evidence[eid]}),
                               evidence_without_recorded_appraisal=sorted(eid for eid in refs if not by_evidence[eid])))
    return dict(appraisal_ledger=[ledger[aid] for aid in sorted(ledger)],
                evidence_appraisal_links=[dict(evidence_id=eid, appraisal_ids=sorted(by_evidence[eid])) for eid in sorted(known)],
                evidence_without_recorded_appraisal=missing,
                work_package_appraisals=work_links, boundary=BOUNDARY)
