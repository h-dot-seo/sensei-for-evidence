#!/usr/bin/env python3
"""Validate mechanical SENSEI state invariants; never infer scientific adequacy."""
import argparse
import json
from pathlib import Path


def validate(state):
    if not isinstance(state, dict):
        return ['state must be an object']
    errors = []
    required = ('project_id', 'research_question', 'run_id', 'phase', 'gate',
                'evidence_sufficiency', 'conclusion_readiness', 'next_action')
    for key in required:
        if not state.get(key):
            errors.append(f'missing state field: {key}')
    for idx, search in enumerate(state.get('searches', [])):
        tag = f'search[{idx}]'
        if not search.get('query'):
            errors.append(f'{tag}: exact query missing')
        ids = search.get('enumerated_ids', [])
        if len(ids) != len(set(ids)):
            errors.append(f'{tag}: duplicate enumerated IDs')
        if search.get('complete'):
            if search.get('has_more') or search.get('pagination_limited'):
                errors.append(f'{tag}: incomplete paging marked complete')
            if search.get('field_pages_pending') or search.get('truncated'):
                errors.append(f'{tag}: unresolved truncation marked complete')
            if search.get('total_count') != len(ids):
                errors.append(f'{tag}: complete census count mismatch')
    screening = state.get('screening', {})
    groups = [('identified', 'duplicates', 'screened'),
              ('screened', 'excluded', 'advanced')]
    for total, left, right in groups:
        if all(k in screening for k in (total, left, right)):
            if any(not isinstance(screening[k], int) or screening[k] < 0
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
