"""Compare supplied searches with a declared search plan, without running searches."""

MATCH_FIELDS = ('source', 'query', 'window')
BOUNDARY = ('Declared-plan accounting and supplied search assertions only; no source '
            'receipt authentication, query adequacy assessment or complete-census claim.')


def page_audit(search):
    """Reconcile optional supplied pages, not independently authenticated receipts."""
    if 'pages' not in search:
        return dict(status='NOT_SUPPLIED', page_count=None, record_occurrences=None,
                    unique_records=None, issues=[])
    pages = search['pages']
    if not isinstance(pages, list) or not pages:
        raise ValueError('search pages must be a nonempty list')
    numbers, known_numbers, seen, occurrences = [], set(), set(), 0
    overlap = False
    page_errors = False
    unresolved_flags = set()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError('search page must be an object')
        number = page.get('page_number')
        if type(number) is not int or number < 1 or number in known_numbers:
            raise ValueError('page numbers must be unique positive integers')
        numbers.append(number)
        known_numbers.add(number)
        ids = page.get('record_ids')
        if (not isinstance(ids, list) or any(not isinstance(rid, str) or not rid.strip() for rid in ids)
                or len(ids) != len(set(ids))):
            raise ValueError('page record_ids must be unique nonblank strings')
        overlap = overlap or bool(seen.intersection(ids))
        seen.update(ids)
        occurrences += len(ids)
        page_errors = page_errors or bool(page.get('error'))
        for flag in ('truncated', 'pagination_limited', 'field_pages_pending'):
            if flag in page and page[flag] is not False:
                unresolved_flags.add(flag)
    issues = []
    if numbers != list(range(1, len(pages) + 1)):
        issues.append('page_sequence_unresolved')
    if (any(page.get('has_more') is not True for page in pages[:-1])
            or pages[-1].get('has_more') is not False):
        issues.append('page_pagination_unresolved')
    if overlap:
        issues.append('page_record_overlap')
    if seen != set(search['record_ids']):
        issues.append('page_record_set_mismatch')
    if page_errors:
        issues.append('page_error_recorded')
    issues.extend('page_' + flag + '_unresolved' for flag in sorted(unresolved_flags))
    return dict(status='UNRESOLVED' if issues else 'RECONCILED', page_count=len(pages),
                record_occurrences=occurrences, unique_records=len(seen), issues=issues)


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
    issues.extend(page_audit(search)['issues'])
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
                           enumerated_records=None if search is None else len(search['record_ids']),
                           page_audit=None if search is None else page_audit(search), issues=issues))
    missing = [row['search_id'] for row in ledger if row['status'] == 'MISSING']
    incomplete = [row['search_id'] for row in ledger if row['status'] == 'INCOMPLETE']
    complete = len(ledger) - len(missing) - len(incomplete)
    accounted = not missing and not incomplete
    return dict(plan_status='ASSERTED_ACCOUNTED' if accounted else 'INCOMPLETE',
                all_planned_searches_accounted_for=accounted,
                planned=len(ledger), completed=complete, missing_search_ids=missing,
                incomplete_search_ids=incomplete, search_plan_ledger=ledger, boundary=BOUNDARY)
