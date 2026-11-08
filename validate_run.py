#!/usr/bin/env python3
"""Validate mechanical SENSEI state invariants; never infer scientific adequacy."""
import argparse
import json
from pathlib import Path
from json_io import parse_json, configure_utf8_stdio
from search_audit import completion_issues, page_audit


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
        try:
            page_audit(dict(search, record_ids=ids))
        except ValueError as error:
            errors.append(f'{tag}: {error}')
            continue
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
            try:
                issues = completion_issues(dict(search, record_ids=ids))
            except ValueError as error:
                errors.append(f'{tag}: {error}')
                continue
            for issue in issues:
                errors.append(f'{tag}: {messages.get(issue, issue)}')
    screening = state.get('screening', {})
    if not isinstance(screening, dict):
        errors.append('screening must be an object')
        screening = {}
    groups = [('identified', 'duplicates', 'screened'),
              ('screened', 'excluded', 'advanced')]
    count_keys = {key for group in groups for key in group}
    invalid_counts = {key for key in count_keys if key in screening and
                      (type(screening[key]) is not int or screening[key] < 0)}
    for key in sorted(invalid_counts):
        errors.append(f'screening: {key} counts must be nonnegative integers')
    for total, left, right in groups:
        if all(k in screening for k in (total, left, right)) and not invalid_counts.intersection((total, left, right)):
            if screening[total] != screening[left] + screening[right]:
                errors.append(f'screening: {total} != {left} + {right}')
    refs = state.get('references', [])
    if not isinstance(refs, list):
        errors.append('references must be a list')
        refs = []
    valid_refs = []
    for ref in refs:
        if not isinstance(ref, dict):
            errors.append('reference must be an object')
            continue
        number = ref.get('reference_no')
        if type(number) is not int or number < 1:
            errors.append('reference_no must be a positive integer')
            continue
        valid_refs.append(ref)
        for flag in ('included_in_report', 'verified', 'text_complete', 'text_truncated'):
            if flag in ref and type(ref[flag]) is not bool:
                errors.append(f'reference {number}: {flag} must be boolean')
        if ref.get('text_complete') is True and ref.get('text_truncated') is True:
            errors.append(f'reference {number}: truncated text marked complete')
    refs = valid_refs
    ref_ids = [r['reference_no'] for r in refs]
    if len(ref_ids) != len(set(ref_ids)):
        errors.append('references: duplicate reference_no')
    release = state.get('release', {})
    if not isinstance(release, dict):
        errors.append('release must be an object')
        release = {}
    cited = release.get('cited_reference_numbers', [])
    if not isinstance(cited, list) or any(type(n) is not int or n < 1 for n in cited):
        errors.append('release: cited_reference_numbers must be a list of positive integers')
        cited = []
    elif len(cited) != len(set(cited)):
        errors.append('release: duplicate cited reference number')
    required_artifacts = release.get('required_artifacts', [])
    if not isinstance(required_artifacts, list) or any(not isinstance(t, str) or not t.strip() for t in required_artifacts):
        errors.append('release: required_artifacts must be a list of nonempty strings')
        required_artifacts = []
    artifacts = release.get('artifacts', [])
    if not isinstance(artifacts, list):
        errors.append('release: artifacts must be a list')
        artifacts = []
    artifact_types = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            errors.append('release: artifact must be an object')
            continue
        kind = artifact.get('type')
        if not isinstance(kind, str) or not kind.strip():
            errors.append('release: artifact type must be a nonempty string')
            continue
        if 'exists' in artifact and type(artifact['exists']) is not bool:
            errors.append('release: artifact exists must be boolean')
        if artifact.get('exists') is True:
            artifact_types.add(kind)
    if release.get('status') == 'COMPLETE':
        if state.get('evidence_sufficiency') != 'SUFFICIENT':
            errors.append('release: evidence sufficiency not established')
        if state.get('blockers'):
            errors.append('release: unresolved blockers')
        if state.get('conclusion_readiness') != 'READY':
            errors.append('release: conclusion not ready')
        if release.get('qa_passed') is not True:
            errors.append('release: QA missing/failed')
        if release.get('storage_verified') is not True:
            errors.append('release: storage not verified')
        for ref in refs:
            if (ref.get('included_in_report') or ref.get('reference_no') in cited) and ref.get('verified') is not True:
                errors.append('release: unverified cited reference')
        known = set(ref_ids)
        if any(r not in known for r in cited):
            errors.append('release: unmatched citation')
        for kind in required_artifacts:
            if kind not in artifact_types:
                errors.append(f'release: required {kind} missing')
    return errors


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    args = parser.parse_args()
    try:
        state = parse_json(args.state.read_text(encoding='utf-8'))
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
