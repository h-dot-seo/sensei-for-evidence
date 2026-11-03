"""Compare supplied searches with a declared search plan, without running searches."""

MATCH_FIELDS = ('source', 'query', 'window')
BOUNDARY = ('Declared-plan accounting and supplied search assertions only; no source '
            'receipt authentication, query adequacy assessment or complete-census claim.')


def completion_issues(search):
    issues = []
    if search.get('complete') is not True:
        issues.append('completion_not_asserted')
    total = search.get('total_count')
    if type(total) is not int or total < 0:
        issues.append('total_count_not_nonnegative_integer')
    elif total != len(search['record_ids']):
        issues.append('total_count_mismatch')
    if search.get('has_more') is not False:
        issues.append('pagination_unresolved')
    for flag in ('truncated', 'pagination_limited', 'field_pages_pending'):
        if flag in search and search[flag] is not False:
            issues.append(flag + '_unresolved')
    if search.get('error'):
        issues.append('search_error_recorded')
    return issues


def audit_search_plan(protocol):
    searches = protocol['searches']
    if not isinstance(searches, list):
        raise ValueError('searches must be a list')
    plan = protocol.get('search_plan')
    if plan is None:
        return dict(plan_status='NOT_SUPPLIED', all_planned_searches_accounted_for=False,
                    planned=0, completed=0, missing_search_ids=[], incomplete_search_ids=[],
                    search_plan_ledger=[], boundary=BOUNDARY)
    if not isinstance(plan, list) or not plan:
        raise ValueError('search_plan must be a nonempty list')
    planned = {}
    for item in plan:
        if not isinstance(item, dict):
            raise ValueError('search plan item must be an object')
        for field in ('search_id', *MATCH_FIELDS):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError('search plan requires ' + field)
        sid = item['search_id']
        if sid in planned:
            raise ValueError('duplicate planned search ID')
        planned[sid] = item
    executed = {}
    for search in searches:
        sid = search.get('search_id')
        if not isinstance(sid, str) or sid not in planned:
            raise ValueError('search must reference a declared search ID')
        if sid in executed:
            raise ValueError('duplicate executed search ID; retain attempts under a revised plan')
        if any(search[field] != planned[sid][field] for field in MATCH_FIELDS):
            raise ValueError('search differs from planned source/query/window; reconcile protocol version')
        executed[sid] = search
    ledger = []
    for sid, item in sorted(planned.items()):
        search = executed.get(sid)
        issues = ['search_not_supplied'] if search is None else completion_issues(search)
        ledger.append(dict(item, status='MISSING' if search is None else ('INCOMPLETE' if issues else 'ASSERTED_COMPLETE'),
                           enumerated_records=None if search is None else len(search['record_ids']), issues=issues))
    missing = [row['search_id'] for row in ledger if row['status'] == 'MISSING']
    incomplete = [row['search_id'] for row in ledger if row['status'] == 'INCOMPLETE']
    complete = len(ledger) - len(missing) - len(incomplete)
    accounted = not missing and not incomplete
    return dict(plan_status='ASSERTED_ACCOUNTED' if accounted else 'INCOMPLETE',
                all_planned_searches_accounted_for=accounted,
                planned=len(ledger), completed=complete, missing_search_ids=missing,
                incomplete_search_ids=incomplete, search_plan_ledger=ledger, boundary=BOUNDARY)
