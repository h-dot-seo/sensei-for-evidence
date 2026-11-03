"""Reconcile supplied search records, screening, evidence and follow-up work packages."""
import argparse
import json
from pathlib import Path


def run(protocol):
    for key in ('question', 'version', 'inclusion_criteria', 'exclusion_criteria'):
        if not protocol.get(key):
            raise ValueError('missing protocol field: ' + key)
    records = {}
    identified = 0
    coverage = []
    for search in protocol['searches']:
        for key in ('source', 'query', 'searched_at', 'window'):
            if not isinstance(search.get(key), str) or not search[key].strip():
                raise ValueError('search requires ' + key)
        ids = search['record_ids']
        if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('invalid or duplicate IDs within search')
        identified += len(ids)
        for rid in ids:
            records.setdefault(rid, []).append(search['source'])
        complete = (search.get('complete') is True and search.get('total_count') == len(ids)
                    and search.get('has_more') is False and not search.get('error'))
        coverage.append(dict(source=search['source'], enumerated=len(ids), complete=complete))
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
        work.append(dict(work_package_id=f'WP-{len(work)+1:03}', **gap, status='PLANNED'))
    included = sum(d['decision'] == 'include' for d in decisions.values())
    return dict(question=protocol['question'], protocol_version=protocol['version'],
                search_ledger=protocol['searches'], screening_ledger=protocol['screening'], coverage=coverage,
                flow=dict(identified=identified, duplicates=identified-len(records), unique_records=len(records),
                          screened=len(decisions), pending=len(records)-len(decisions),
                          excluded=len(decisions)-included, included=included, extracted=len(evidence)),
                evidence=evidence, work_packages=work,
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
