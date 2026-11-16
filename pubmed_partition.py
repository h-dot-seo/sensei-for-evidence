"""Offline review/replay of explicitly supplied PubMed date windows, never a fetch plan executor."""
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path

import pubmed_discovery as discovery
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json

MAX_WINDOWS = 100
MAX_BYTES = 20_000_000
BOUNDARY = ('Calendar coverage is not PMID-set coverage. Publication dates can overlap across records/windows; '
            'counts and translations can change as the index changes. Count equality is not a census or proof of retrieval. '
            'Unsigned supplied records can be consistently reauthored. No source authentication, scientific review, '
            'query adequacy, fetch approval, protocol change, deduplication or merged intake is performed. '
            'Each discovery spec retains its local 1000-occurrence and 10-request caps; these are not PubMed-wide limits. '
            'This tool never partitions queries automatically or executes them. Real queries and retained records '
            'are not redacted: keep them private, outside public repositories. Byte limits are not total memory/CPU guarantees.')


def _bounded(value):
    raw = canonical_json_bytes(value)
    if len(raw) > MAX_BYTES:
        raise ValueError('JSON exceeds byte bound')
    return raw


def _day(value):
    return dt.datetime.strptime(value, '%Y/%m/%d').date().toordinal()


def _date(value):
    date = dt.date.fromordinal(value)
    return f'{date.year:04d}/{date.month:02d}/{date.day:02d}'


def validate_plan(plan):
    _bounded(plan)
    if type(plan) is not dict or set(plan) != {'schema_version', 'query', 'date_filter', 'specs'}:
        raise ValueError('invalid plan fields')
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        raise ValueError('invalid plan schema')
    specs = plan['specs']
    if type(specs) is not list or not 1 <= len(specs) <= MAX_WINDOWS:
        raise ValueError('invalid window count')
    if plan['date_filter'] is None:
        raise ValueError('explicit outer dates required')
    # Reuse the existing exact query/date grammar without changing its caps.
    outer = dict(schema_version=1, request_id='outer', query=plan['query'], sort='pub_date',
                 date_filter=plan['date_filter'], page_size=1, max_records=1, max_requests=1)
    discovery.validate_spec(outer)
    seen = set()
    for spec in specs:
        discovery.validate_spec(spec)
        if spec['request_id'] in seen:
            raise ValueError('duplicate request ID')
        seen.add(spec['request_id'])
        if (spec['query'] != plan['query'] or spec['date_filter'] is None
                or spec['date_filter']['datetype'] != plan['date_filter']['datetype']):
            raise ValueError('window query/date type differs')
    return copy.deepcopy(plan)


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return {**discovery.implementation_hashes(),
            'pubmed_partition.py': hashlib.sha256((root / 'pubmed_partition.py').read_bytes()).hexdigest()}


def _calendar(plan):
    lower, upper = (_day(plan['date_filter'][name]) for name in ('mindate', 'maxdate'))
    intervals = [(spec['request_id'], _day(spec['date_filter']['mindate']),
                  _day(spec['date_filter']['maxdate'])) for spec in plan['specs']]
    outside = [name for name, start, end in intervals if start < lower or end > upper]
    overlaps = []
    for i, (left, start, end) in enumerate(intervals):
        for right, other_start, other_end in intervals[i + 1:]:
            a, b = max(start, other_start), min(end, other_end)
            if a <= b:
                overlaps.append(dict(request_ids=[left, right], mindate=_date(a), maxdate=_date(b)))
    cursor, gaps = lower, []
    for start, end in sorted((max(start, lower), min(end, upper)) for _, start, end in intervals
                             if end >= lower and start <= upper):
        if start > cursor:
            gaps.append(dict(mindate=_date(cursor), maxdate=_date(start - 1)))
        cursor = max(cursor, end + 1)
    if cursor <= upper:
        gaps.append(dict(mindate=_date(cursor), maxdate=_date(upper)))
    return dict(inclusive=True, gaps=gaps, overlaps=overlaps, outside_request_ids=outside,
                covers_outer_calendar=not gaps, exact_nonoverlapping_partition=not (gaps or overlaps or outside))


def review(plan, artifacts=()):
    plan = validate_plan(plan)
    if type(artifacts) not in (list, tuple) or len(artifacts) > MAX_WINDOWS:
        raise ValueError('invalid artifact count')
    _bounded(dict(plan=plan, artifacts=list(artifacts)))
    by_id = {}
    specs = {spec['request_id']: spec for spec in plan['specs']}
    for artifact in artifacts:
        discovery.verify(artifact)
        spec = artifact['spec']
        key = spec['request_id']
        if key in by_id or key not in specs or canonical_json_bytes(spec) != canonical_json_bytes(specs[key]):
            raise ValueError('duplicate, unknown or mismatched discovery spec')
        by_id[key] = artifact
    windows, occurrences, pmids, translations = [], [], {}, []
    for spec in plan['specs']:
        key = spec['request_id']
        artifact = by_id.get(key)
        if artifact is None:
            windows.append(dict(request_id=key, observation='MISSING', discovery_sha256=None))
            continue
        derived = artifact['derived']
        rows = copy.deepcopy(derived['occurrences'])
        count = derived['initial_reported_count']
        translation = derived['query_translation']
        if translation is not None and translation not in translations:
            translations.append(translation)
        windows.append(dict(request_id=key, observation='SUPPLIED_REPLAYED',
                            discovery_sha256=discovery.digest(artifact), started_at=artifact['execution']['started_at'],
                            stop_reason=derived['stop_reason'], initial_reported_count=count,
                            observed_reported_count_accounted_for=derived['observed_reported_count_accounted_for'],
                            reported_count_exceeds_local_record_cap=count is not None and count > spec['max_records'],
                            reported_count_exceeds_pubmed_10000_limit=derived['reported_count_exceeds_pubmed_10000_limit'],
                            query_translation=translation, pages=copy.deepcopy(derived['pages']), occurrence_count=len(rows)))
        for row in rows:
            occurrence = dict(request_id=key, occurrence=row)
            occurrences.append(occurrence)
            pmids.setdefault(row['pmid'], []).append(dict(request_id=key, occurrence_index=row['occurrence_index']))
    result = dict(schema_version=1, mode='pubmed_partition_review', plan=plan,
                  plan_sha256=discovery.digest(plan), implementation_sha256=implementation_hashes(),
                  calendar=_calendar(plan), windows=windows, occurrences=occurrences,
                  repeated_pmids=[dict(pmid=pmid, occurrences=items,
                                       crosses_windows=len({r['request_id'] for r in items}) > 1)
                                  for pmid, items in pmids.items() if len(items) > 1],
                  observed_occurrence_count=len(occurrences), observed_unique_pmid_count=len(pmids),
                  supplied_window_count=len(by_id), all_windows_supplied=len(by_id) == len(specs),
                  all_supplied_counts_accounted_for=bool(by_id) and all(
                      artifact['derived']['observed_reported_count_accounted_for'] for artifact in by_id.values()),
                  differing_supplied_query_translations=len(translations) > 1,
                  search_completeness='NOT_ESTABLISHED', census='NOT_ESTABLISHED',
                  index_snapshot='NOT_VERIFIED', source_authenticity='NOT_VERIFIED',
                  review_status='NOT_PERFORMED', conclusion='NOT_READY', external_calls=0,
                  protocol_changed=False, boundary=BOUNDARY)
    _bounded(result)
    return result


def verify(plan, report, artifacts=()):
    _bounded(report)
    expected = review(plan, artifacts)
    if canonical_json_bytes(expected) != canonical_json_bytes(report):
        raise ValueError('partition report differs from replay')
    return dict(valid=True, report_sha256=discovery.digest(report), external_calls=0,
                verification_scope='Unsigned supplied plan and separately supplied discovery artifacts only',
                search_completeness='NOT_ESTABLISHED', census='NOT_ESTABLISHED', conclusion='NOT_READY')


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('review', 'verify'):
        command = sub.add_parser(name)
        command.add_argument('plan', type=Path)
        if name == 'verify':
            command.add_argument('report', type=Path)
        command.add_argument('--discovery', action='append', default=[], type=Path)
        if name == 'review':
            command.add_argument('--output', type=Path)
    args = parser.parse_args()
    remaining = MAX_BYTES

    def read(path):
        nonlocal remaining
        with path.open('rb') as handle:
            raw = handle.read(remaining + 1)
        if len(raw) > remaining:
            raise ValueError('aggregate input exceeds byte bound')
        remaining -= len(raw)
        return parse_json(raw)

    try:
        if len(args.discovery) > MAX_WINDOWS:
            raise ValueError('too many discoveries')
        output = getattr(args, 'output', None)
        if output is not None and (output.exists() or output.is_symlink()):
            raise ValueError('output exists')
        plan = read(args.plan)
        artifacts = [read(path) for path in args.discovery]
        # Report has its own bound so a retained review can be replayed without
        # consuming the original plan/discovery input budget a second time.
        remaining = MAX_BYTES
        report = read(args.report) if args.command == 'verify' else None
        result = review(plan, artifacts) if args.command == 'review' else verify(plan, report, artifacts)
        raw = (json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
        if len(raw) > MAX_BYTES:
            raise ValueError('output exceeds byte bound')
        if output is not None:
            with output.open('xb') as handle:
                handle.write(raw)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, RecursionError):
        parser.exit(1, 'pubmed partition error: invalid input, output or replay; no external calls performed\n')
    print(raw.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
