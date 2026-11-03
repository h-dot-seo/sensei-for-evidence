#!/usr/bin/env python3
"""Validate mechanical SENSEI state invariants; never infer scientific adequacy."""
import argparse
import json
from pathlib import Path
from search_audit import completion_issues


def validate(state):
    if not isinstance(state, dict):
        return ['state must be an object']
    errors = []
    required = ('project_id', 'research_question', 'run_id', 'phase', 'gate',
                'evidence_sufficiency', 'conclusion_readiness', 'next_action')
    for key in required:
        if not state.get(key):
            errors.append(f'missing state field: {key}')
    searches = state.get('searches', [])
    if not isinstance(searches, list):
        errors.append('searches must be a list')
        searches = []
    for idx, search in enumerate(searches):
        tag = f'search[{idx}]'
        if not isinstance(search, dict):
            errors.append(f'{tag}: search must be an object')
            continue
        if not isinstance(search.get('query'), str) or not search['query'].strip():
            errors.append(f'{tag}: exact query missing')
        ids = search.get('enumerated_ids', [])
        if not isinstance(ids, list) or any(not isinstance(i, str) or not i.strip() for i in ids):
            errors.append(f'{tag}: enumerated IDs must be a list of nonempty strings')
            continue
        if len(ids) != len(set(ids)):
            errors.append(f'{tag}: duplicate enumerated IDs')
        if 'complete' in search and type(search['complete']) is not bool:
            errors.append(f'{tag}: complete must be boolean')
        if search.get('complete') is True:
            messages = {
                'total_count_not_nonnegative_integer': 'total count must be a nonnegative integer',
                'total_count_mismatch': 'complete census count mismatch',
                'pagination_unresolved': 'incomplete paging marked complete',
                'pagination_limited_unresolved': 'incomplete paging marked complete',
                'truncated_unresolved': 'unresolved truncation marked complete',
                'field_pages_pending_unresolved': 'unresolved truncation marked complete',
                'search_error_recorded': 'search error marked complete',
            }
            for issue in completion_issues(dict(search, record_ids=ids)):
                errors.append(f'{tag}: {messages.get(issue, issue)}')
    screening = state.get('screening', {})
    groups = [('identified', 'duplicates', 'screened'),
              ('screened', 'excluded', 'advanced')]
    for total, left, right in groups:
        if all(k in screening for k in (total, left, right)):
            if any(type(screening[k]) is not int or screening[k] < 0
                   for k in (total, left, right)):
                errors.append('screening: counts must be nonnegative integers')
            elif screening[total] != screening[left] + screening[right]:
                errors.append(f'screening: {total} != {left} + {right}')
    refs = state.get('references', [])
    ref_ids = [r.get('reference_no') for r in refs]
    if len(ref_ids) != len(set(ref_ids)):
        errors.append('references: duplicate reference_no')
    for ref in refs:
        if ref.get('text_complete') and ref.get('text_truncated'):
            errors.append(f'reference {ref.get("reference_no")}: truncated text marked complete')
    release = state.get('release', {})
    if release.get('status') == 'COMPLETE':
        if state.get('evidence_sufficiency') != 'SUFFICIENT':
            errors.append('release: evidence sufficiency not established')
        if state.get('blockers'):
            errors.append('release: unresolved blockers')
        if state.get('conclusion_readiness') != 'READY':
            errors.append('release: conclusion not ready')
        if not release.get('qa_passed'):
            errors.append('release: QA missing/failed')
        if not release.get('storage_verified'):
            errors.append('release: storage not verified')
        for ref in refs:
            if ref.get('included_in_report') and not ref.get('verified'):
                errors.append('release: unverified cited reference')
        known = set(ref_ids)
        if any(r not in known for r in release.get('cited_reference_numbers', [])):
            errors.append('release: unmatched citation')
        artifact_types = {a.get('type') for a in release.get('artifacts', []) if a.get('exists')}
        for kind in release.get('required_artifacts', []):
            if kind not in artifact_types:
                errors.append(f'release: required {kind} missing')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    args = parser.parse_args()
    try:
        state = json.loads(args.state.read_text())
        if not isinstance(state, dict):
            raise ValueError('state must be an object')
        errors = validate(state)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'valid': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1
    print(json.dumps({'valid': not errors, 'errors': errors}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
