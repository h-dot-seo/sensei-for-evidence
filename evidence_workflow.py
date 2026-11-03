"""Reconcile supplied search records, screening, evidence and follow-up work packages."""
import argparse
import json
from pathlib import Path
from context_links import link_context
from search_audit import audit_search_plan, completion_issues


def run(protocol):
    for key in ('question', 'version', 'inclusion_criteria', 'exclusion_criteria'):
        if not protocol.get(key):
            raise ValueError('missing protocol field: ' + key)
    records = {}
    identified = 0
    coverage = []
    if not isinstance(protocol['searches'], list):
        raise ValueError('searches must be a list')
    for search in protocol['searches']:
        if not isinstance(search, dict):
            raise ValueError('search must be an object')
        for key in ('source', 'query', 'searched_at', 'window'):
            if not isinstance(search.get(key), str) or not search[key].strip():
                raise ValueError('search requires ' + key)
        ids = search['record_ids']
        if not isinstance(ids, list) or any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('invalid or duplicate IDs within search')
        identified += len(ids)
        for rid in ids:
            records.setdefault(rid, []).append(search['source'])
        issues = completion_issues(search)
        coverage.append(dict(source=search['source'], search_id=search.get('search_id'),
                             enumerated=len(ids), complete=not issues, issues=issues))
    search_plan_audit = audit_search_plan(protocol)
    decisions = {}
    for row in protocol['screening']:
        rid = row['record_id']
        if rid not in records or rid in decisions:
            raise ValueError('unknown or duplicate screening record')
        if row['decision'] not in ('include', 'exclude') or not row.get('reason'):
            raise ValueError('screening decision and reason required')
        decisions[rid] = row
    evidence = []
    seen = set()
    for row in protocol['evidence']:
        rid = row['record_id']
        if rid in seen or decisions.get(rid, {}).get('decision') != 'include':
            raise ValueError('evidence must link uniquely to included record')
        seen.add(rid)
        for field in ('study_id', 'locator', 'model', 'intervention', 'comparator', 'endpoint', 'result', 'limitations'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError('evidence requires ' + field)
        if row.get('mechanism_basis') not in ('association', 'intervention', 'unknown'):
            raise ValueError('explicit mechanism_basis required')
        evidence.append(row)
    work = []
    for gap in protocol['gaps']:
        if not gap.get('question') or not gap.get('deliverable') or not gap.get('acceptance_criterion'):
            raise ValueError('gap requires question, deliverable and acceptance criterion')
        if any(i not in seen for i in gap['evidence_ids']):
            raise ValueError('gap references unknown evidence')
        work.append(dict(gap, work_package_id=gap.get('work_package_id', f'WP-{len(work)+1:03}'),
                         depends_on=gap.get('depends_on', []), status=gap.get('status', 'PLANNED')))
    known = {w['work_package_id']: w for w in work}
    if len(known) != len(work) or any(not isinstance(k, str) or not k for k in known):
        raise ValueError('work package IDs must be unique nonempty strings')
    visiting, visited, order = set(), set(), []
    def visit(wid):
        if wid in visiting:
            raise ValueError('cyclic work package dependencies')
        if wid in visited:
            return
        if wid not in known:
            raise ValueError('unknown work package dependency')
        visiting.add(wid)
        w = known[wid]
        if w['status'] not in ('PLANNED', 'IN_PROGRESS', 'COMPLETE'):
            raise ValueError('invalid work package status')
        if not isinstance(w['depends_on'], list) or any(not isinstance(d, str) for d in w['depends_on']):
            raise ValueError('depends_on must be a list of IDs')
        for dep in w['depends_on']:
            visit(dep)
        if w['status'] == 'COMPLETE':
            if not w.get('artifact_locator') or w.get('acceptance_verified') is not True:
                raise ValueError('complete work requires artifact locator and verified acceptance')
            if any(known[d]['status'] != 'COMPLETE' for d in w['depends_on']):
                raise ValueError('complete work has unfinished dependency')
        w['blocked_by'] = [d for d in w['depends_on'] if known[d]['status'] != 'COMPLETE']
        visiting.remove(wid); visited.add(wid); order.append(wid)
    for wid in known:
        visit(wid)
    context = link_context(protocol, evidence, work)
    included = sum(d['decision'] == 'include' for d in decisions.values())
    return dict(question=protocol['question'], protocol_version=protocol['version'],
                search_ledger=protocol['searches'], screening_ledger=protocol['screening'], coverage=coverage,
                search_plan_audit=search_plan_audit,
                flow=dict(identified=identified, duplicates=identified-len(records), unique_records=len(records),
                          screened=len(decisions), pending=len(records)-len(decisions),
                          excluded=len(decisions)-included, included=included, extracted=len(evidence)),
                evidence=evidence, work_packages=work, execution_order=order, context=context,
                extraction_pending=sorted(r for r, d in decisions.items() if d['decision'] == 'include' and r not in seen),
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY',
                boundary='Record-level screening ledger; not a full PRISMA report or scientific appraisal')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('protocol', type=Path)
    a = p.parse_args()
    try:
        result = run(json.loads(a.protocol.read_text(encoding='utf-8')))
    except (ValueError, OSError, KeyError, TypeError) as e:
        p.exit(1, str(e) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
