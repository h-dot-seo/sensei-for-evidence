"""Reconcile supplied search records, screening, evidence and follow-up work packages."""
import argparse
import json
from pathlib import Path
from json_io import parse_json, configure_utf8_stdio
from context_links import link_context, id_list, nonempty_text
from search_audit import audit_search_plan, completion_issues, page_audit
from appraisal_links import link_appraisals
from adapter_integrity import validate_adapter_protocol
from planning_links import link_planning


def run(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    validate_adapter_protocol(protocol)
    for key in ('question', 'version', 'inclusion_criteria', 'exclusion_criteria'):
        if not protocol.get(key):
            raise ValueError('missing protocol field: ' + key)
    for key in ('searches', 'screening', 'evidence', 'gaps'):
        if not isinstance(protocol.get(key), list):
            raise ValueError(key + ' must be a list')
    records = {}
    identified = 0
    coverage = []
    if not isinstance(protocol['searches'], list):
        raise ValueError('searches must be a list')
    for search_index, search in enumerate(protocol['searches']):
        if not isinstance(search, dict):
            raise ValueError('search must be an object')
        for key in ('source', 'query', 'searched_at', 'window'):
            if not isinstance(search.get(key), str) or not search[key].strip():
                raise ValueError('search requires ' + key)
        ids = search['record_ids']
        if not isinstance(ids, list) or any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('invalid or duplicate IDs within search')
        identified += len(ids)
        for rid in ids:
            records.setdefault(rid, []).append(dict(search_index=search_index,
                                                    search_id=search.get('search_id'), source=search['source']))
        issues = completion_issues(search)
        coverage.append(dict(source=search['source'], search_id=search.get('search_id'),
                             enumerated=len(ids), complete=not issues, issues=issues, page_audit=page_audit(search)))
    search_plan_audit = audit_search_plan(protocol)
    decisions = {}
    for row in protocol['screening']:
        if not isinstance(row, dict):
            raise ValueError('screening row must be an object')
        rid = row.get('record_id')
        if not nonempty_text(rid) or rid not in records or rid in decisions:
            raise ValueError('unknown or duplicate screening record')
        if row['decision'] not in ('include', 'exclude') or not nonempty_text(row.get('reason')):
            raise ValueError('screening decision and reason required')
        decisions[rid] = row
    evidence = []
    seen = set()
    extracted_records = set()
    record_studies = {}
    for row in protocol['evidence']:
        if not isinstance(row, dict):
            raise ValueError('evidence row must be an object')
        rid = row.get('record_id')
        if not nonempty_text(rid):
            raise ValueError('evidence record_id must be a nonempty string')
        eid = row.get('evidence_id', rid)
        if not nonempty_text(eid) or eid in seen:
            raise ValueError('evidence IDs must be unique nonempty strings')
        if decisions.get(rid, {}).get('decision') != 'include':
            raise ValueError('evidence must link to included record')
        seen.add(eid)
        extracted_records.add(rid)
        for field in ('study_id', 'locator', 'model', 'intervention', 'comparator', 'endpoint', 'result', 'limitations'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError('evidence requires ' + field)
        if rid in record_studies and record_studies[rid] != row['study_id']:
            raise ValueError('evidence study ID conflicts within source record')
        record_studies[rid] = row['study_id']
        if row.get('mechanism_basis') not in ('association', 'intervention', 'unknown'):
            raise ValueError('explicit mechanism_basis required')
        evidence.append(dict(row, evidence_id=eid))
    work = []
    for gap in protocol['gaps']:
        if not isinstance(gap, dict):
            raise ValueError('gap must be an object')
        if any(not nonempty_text(gap.get(field)) for field in ('question', 'deliverable', 'acceptance_criterion')):
            raise ValueError('gap requires question, deliverable and acceptance criterion')
        evidence_ids = id_list(gap.get('evidence_ids'), 'gap evidence_ids')
        if not evidence_ids:
            raise ValueError('gap requires at least one linked evidence ID')
        if any(i not in seen for i in evidence_ids):
            raise ValueError('gap references unknown evidence')
        work.append(dict(gap, work_package_id=gap.get('work_package_id', f'WP-{len(work)+1:03}'),
                         depends_on=gap.get('depends_on', []), status=gap.get('status', 'PLANNED')))
    if any(not nonempty_text(w['work_package_id']) for w in work):
        raise ValueError('work package IDs must be unique nonempty strings')
    known = {w['work_package_id']: w for w in work}
    if len(known) != len(work) or any(not isinstance(k, str) or not k for k in known):
        raise ValueError('work package IDs must be unique nonempty strings')
    visiting, visited, order = set(), set(), []
    for root in known:
        stack = [(root, False)]
        while stack:
            wid, exiting = stack.pop()
            if exiting:
                w = known[wid]
                if w['status'] == 'COMPLETE':
                    if not nonempty_text(w.get('artifact_locator')) or w.get('acceptance_verified') is not True:
                        raise ValueError('complete work requires artifact locator and verified acceptance')
                    if any(known[d]['status'] != 'COMPLETE' for d in w['depends_on']):
                        raise ValueError('complete work has unfinished dependency')
                w['blocked_by'] = [d for d in w['depends_on'] if known[d]['status'] != 'COMPLETE']
                visiting.remove(wid)
                visited.add(wid)
                order.append(wid)
                continue
            if wid in visiting:
                raise ValueError('cyclic work package dependencies')
            if wid in visited:
                continue
            if wid not in known:
                raise ValueError('unknown work package dependency')
            w = known[wid]
            if w['status'] not in ('PLANNED', 'IN_PROGRESS', 'COMPLETE'):
                raise ValueError('invalid work package status')
            if not isinstance(w['depends_on'], list) or any(not isinstance(d, str) for d in w['depends_on']):
                raise ValueError('depends_on must be a list of IDs')
            visiting.add(wid)
            stack.append((wid, True))
            stack.extend((dep, False) for dep in reversed(w['depends_on']))
    context = link_context(protocol, evidence, work)
    appraisal = link_appraisals(protocol, evidence, work)
    planning = link_planning(protocol, evidence, work, context, appraisal)
    included = sum(d['decision'] == 'include' for d in decisions.values())
    return dict(question=protocol['question'], protocol_version=protocol['version'],
                search_ledger=protocol['searches'], screening_ledger=protocol['screening'], coverage=coverage,
                search_plan_audit=search_plan_audit,
                record_provenance=[dict(record_id=rid, occurrences=records[rid]) for rid in sorted(records)],
                deduplication_scope='exact_supplied_record_id_only',
                record_identity_verification='NOT_ESTABLISHED',
                flow=dict(identified=identified, duplicates=identified-len(records), unique_records=len(records),
                          screened=len(decisions), pending=len(records)-len(decisions),
                          excluded=len(decisions)-included, included=included, extracted=len(evidence),
                          extracted_records=len(extracted_records),
                          extracted_studies=len({row['study_id'] for row in evidence})),
                evidence=evidence, work_packages=work, execution_order=order, context=context, appraisal=appraisal, planning=planning,
                extraction_pending=sorted(r for r, d in decisions.items() if d['decision'] == 'include' and r not in extracted_records),
                extraction_pending_scope='title_abstract_included_records_without_any_result_row',
                extraction_completeness='NOT_ESTABLISHED',
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY',
                boundary='Record-level screening ledger; not a full PRISMA report or scientific appraisal')


def main():
    configure_utf8_stdio()
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('protocol', type=Path)
    a = p.parse_args()
    try:
        result = run(parse_json(a.protocol.read_text(encoding='utf-8')))
    except (ValueError, OSError, KeyError, TypeError) as e:
        p.exit(1, str(e) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
