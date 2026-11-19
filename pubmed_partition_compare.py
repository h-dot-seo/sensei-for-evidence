"""Compare two sets of retained PubMed discovery observations against one explicit plan offline."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
import pubmed_partition as partition
from pubmed_discovery import digest


def _positions(report):
    by_window = defaultdict(dict)
    for row in report['occurrences']:
        occurrence = row['occurrence']
        positions = by_window[row['request_id']].setdefault(occurrence['pmid'], [])
        positions.append(occurrence['occurrence_index'])
    return by_window


def _observation(window):
    if window['observation'] == 'MISSING':
        return None
    fields = ('discovery_sha256', 'started_at', 'stop_reason', 'occurrence_count',
              'initial_reported_count', 'observed_reported_count_accounted_for',
              'reported_count_exceeds_local_record_cap', 'reported_count_exceeds_pubmed_10000_limit')
    summary = {field: window[field] for field in fields}
    summary['pages'] = [
        {key: page[key] for key in ('response_index', 'retstart', 'retmax', 'count', 'querytranslation')}
        for page in window['pages']
    ]
    return summary


def _pmid_changes(before, after):
    # Use first-seen order from the supplied pages, including duplicate positions.
    changed = []
    for pmid in dict.fromkeys((*before, *after)):
        old, new = before.get(pmid, []), after.get(pmid, [])
        if old == new:
            continue
        if not old:
            change = 'after_only'
        elif not new:
            change = 'before_only'
        elif len(old) != len(new):
            change = 'multiplicity_changed'
        else:
            change = 'position_changed'
        changed.append(dict(pmid=pmid, change=change, before_positions=old, after_positions=new))
    return changed


def _changed_fields(before, after):
    if before is None or after is None:
        return None
    changed = [key for key in before if key not in ('discovery_sha256', 'pages') and before[key] != after[key]]
    for key in ('count', 'querytranslation', 'retstart', 'retmax'):
        if [page[key] for page in before['pages']] != [page[key] for page in after['pages']]:
            changed.append('pages.' + key)
    return changed


def compare(plan, before=(), after=()):
    """Replay both sides and compare only observations of the same planned window."""
    for side in (before, after):
        if type(side) not in (list, tuple) or len(side) > partition.MAX_WINDOWS:
            raise ValueError('invalid discovery count')
    if len(canonical_json_bytes(dict(plan=plan, before=before, after=after))) > partition.MAX_BYTES:
        raise ValueError('aggregate input exceeds byte bound')
    first = partition.review(plan, before)
    second = partition.review(plan, after)
    old_positions, new_positions = _positions(first), _positions(second)
    counts = dict(missing_both=0, before_only=0, after_only=0, same_artifact=0, different_artifact=0)
    windows = []
    for spec, previous, current in zip(first['plan']['specs'], first['windows'], second['windows']):
        key = previous['request_id']
        old, new = _observation(previous), _observation(current)
        if old is None:
            status = 'missing_both' if new is None else 'after_only'
        elif new is None:
            status = 'before_only'
        elif old['discovery_sha256'] == new['discovery_sha256']:
            status = 'same_artifact'
        else:
            status = 'different_artifact'
        counts[status] += 1
        changes = None
        if old and new and old['pages'] and new['pages']:
            changes = _pmid_changes(old_positions[key], new_positions[key])
        windows.append(dict(request_id=key, date_filter=spec['date_filter'], status=status,
                            before=old, after=new, changed_fields=_changed_fields(old, new),
                            pmid_position_changes=changes))
    hashes = dict(first['implementation_sha256'])
    hashes['pubmed_partition_compare.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = dict(schema_version=1, mode='pubmed_partition_comparison', plan_sha256=first['plan_sha256'],
                  before_review_sha256=digest(first), after_review_sha256=digest(second),
                  implementation_sha256=hashes, window_counts=counts, windows=windows,
                  external_calls=0, census='NOT_ESTABLISHED', search_completeness='NOT_ESTABLISHED',
                  conclusion='NOT_READY', boundary='Before and after are supplied labels. Differences describe '
                  'retained observations only. Source authenticity, database changes and chronology are unverified.')
    if len(canonical_json_bytes(result)) > partition.MAX_BYTES:
        raise ValueError('comparison exceeds byte bound')
    return result


def verify(plan, report, before=(), after=()):
    supplied = canonical_json_bytes(report)
    if len(supplied) > partition.MAX_BYTES or supplied != canonical_json_bytes(compare(plan, before, after)):
        raise ValueError('comparison differs from replay')
    return dict(valid=True, comparison_sha256=digest(report), external_calls=0, conclusion='NOT_READY')


def render_text(report):
    """Compact per-window accounting with quoted, user-supplied request IDs."""
    counts = report['window_counts']
    lines = ['Observed PubMed window comparison',
             'Windows: ' + ', '.join(f'{name}={value}' for name, value in counts.items())]
    for window in report['windows']:
        dates = window['date_filter']
        lines.append(f'{quoted_display(window["request_id"])}  {dates["datetype"]} '
                     f'{dates["mindate"]}..{dates["maxdate"]}  {window["status"]}')
        for label in ('before', 'after'):
            side = window[label]
            if side is None:
                lines.append(f'  {label}: missing')
            else:
                initial = side['initial_reported_count']
                lines.append(f'  {label}: reported={initial if initial is not None else "unknown"}, '
                             f'occurrences={side["occurrence_count"]}, stop={side["stop_reason"]}')
        if window['changed_fields']:
            lines.append('  Changed observation fields: ' + ', '.join(window['changed_fields']))
        changes = window['pmid_position_changes']
        if changes is None:
            lines.append('  PMID positions: unavailable')
        elif changes:
            tally = Counter(row['change'] for row in changes)
            lines.append('  Changed PMIDs: ' + ', '.join(f'{name}={tally[name]}' for name in sorted(tally)))
        else:
            lines.append('  PMID positions: identical')
    lines.append('Search completeness: ' + report['search_completeness'])
    return '\n'.join(lines) + '\n'


def _read(path, remaining):
    with path.open('rb') as stream:
        raw = stream.read(remaining + 1)
    if len(raw) > remaining:
        raise ValueError('aggregate input exceeds byte bound')
    return parse_json(raw), remaining - len(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('compare', 'verify'):
        command = commands.add_parser(name)
        command.add_argument('plan', type=Path)
        if name == 'verify':
            command.add_argument('report', type=Path)
        command.add_argument('--before', action='append', type=Path, default=[], help='retained discovery (repeatable)')
        command.add_argument('--after', action='append', type=Path, default=[], help='retained discovery (repeatable)')
        if name == 'compare':
            command.add_argument('--output', type=Path, help='create a new comparison JSON file')
            command.add_argument('--text', action='store_true', help='print a compact per-window summary')
    args = parser.parse_args()
    try:
        if max(len(args.before), len(args.after)) > partition.MAX_WINDOWS:
            raise ValueError('too many discovery paths')
        output = getattr(args, 'output', None)
        if output is not None and (output.exists() or output.is_symlink()):
            raise ValueError('output exists')
        plan, remaining = _read(args.plan, partition.MAX_BYTES)
        sides = []
        for paths in (args.before, args.after):
            side = []
            for path in paths:
                item, remaining = _read(path, remaining)
                side.append(item)
            sides.append(side)
        if args.command == 'verify':
            report, _ = _read(args.report, partition.MAX_BYTES)
            result = verify(plan, report, *sides)
        else:
            result = compare(plan, *sides)
        raw = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        if len(raw) > partition.MAX_BYTES:
            raise ValueError('output exceeds byte bound')
        display = render_text(result).encode('utf-8') if getattr(args, 'text', False) else raw
        if len(display) > partition.MAX_BYTES:
            raise ValueError('display exceeds byte bound')
        if output is not None:
            with output.open('xb') as handle:
                handle.write(raw)
        sys.stdout.buffer.write(display)
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, RecursionError):
        parser.exit(1, 'pubmed partition comparison error: invalid input, output or replay\n')


if __name__ == '__main__':
    main()
