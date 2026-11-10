"""Render supplied-data status as Markdown, not a review or readiness judgement."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from json_io import configure_utf8_stdio, parse_json, quoted_display
from research_status import BOUNDARY as STATUS_BOUNDARY, status

MAX_BYTES = 16 * 1024 * 1024
SCHEMA = 'sensei.status-markdown.v1'
BOUNDARY = (
    'Read-only rendering of research_status.status over supplied data; '
    'not a PRISMA diagram, final review, scientific judgement or readiness decision. '
    'No model call, network, source authentication or clock read. '
    'Census: NOT_ESTABLISHED. Conclusion: NOT_READY. '
    'PRIVATE FILE: supplied text, identifiers and pointers are retained without redaction; '
    'keep real outputs outside the public repository and share only with authorization.'
)
# These are program-owned labels, never keys taken from a supplied protocol.
QUEUE_KEYS = (
    'statements_without_evidence_positions', 'statements_with_unresolved_positions',
    'units_without_outcome_statistics', 'units_with_statistics_review_cues',
    'units_without_outcome_sampling', 'units_with_unresolved_sampling',
    'evidence_without_experimental_unit', 'units_with_unresolved_conditions',
    'pending_synthesis_statement_reviews', 'stale_synthesis_statement_reviews',
    'evidence_without_statement_citation', 'statements_without_independent_challenge',
    'challenges_with_open_material_gaps', 'unresolved_challenges', 'stale_challenge_bindings',
    'work_without_planning_assertion', 'work_with_stale_planning_assertion',
    'missing_planned_searches', 'incomplete_searches', 'records_pending_screening',
    'record_level_extraction_pending', 'unmapped_included_records',
    'reports_pending_retrieval', 'reports_not_retrieved', 'reports_pending_assessment',
    'included_reports_without_extraction', 'context_review_pending',
    'evidence_without_recorded_appraisal', 'dependency_unblocked_planned_work',
    'blocked_work', 'work_in_progress', 'completed_work_without_source_binding',
    'completed_work_with_stale_source_binding', 'completed_work_assertions',
    'report_study_memberships_without_results', 'records_with_screening_review_cues',
    'reports_with_review_cues', 'study_memberships_with_review_cues',
    'inventory_candidates_with_review_cues',
)
STATUS_FIELDS = (
    'question', 'protocol_version', 'protocol_sha256', 'hash_scope', 'engine_sha256',
    'search_plan_status', 'report_stage', 'deduplication_scope',
    'record_identity_verification', 'record_extraction_scope', 'extraction_completeness',
    'census_claim', 'conclusion_readiness', 'boundary', 'readiness',
    'report_study_inventory', 'report_study_inventory_review', 'report_study_review',
    'screening_decision_history',
)
READINESS_COUNTS = ('open_gates', 'closed_gates', 'not_applicable_gates',
                    'supplied_assertions', 'current_assertions', 'stale_assertions')


class _Markdown:
    """Bound the complete UTF-8 document before opening any output path."""
    def __init__(self):
        self.raw = bytearray()

    def line(self, text=''):
        raw = (text + '\n').encode('utf-8')
        if len(self.raw) + len(raw) > MAX_BYTES:
            raise ValueError('status Markdown exceeds size limit; narrow the supplied protocol')
        self.raw.extend(raw)

    def block(self, value, items=False):
        # Each displayed value occupies one physical line. JSON quoting escapes
        # embedded newlines; quoted_display also escapes Cc/Cf/Zl/Zp characters.
        values = value if items and value else [value]
        lines = [quoted_display(item) for item in values]
        longest = max((len(run) for line in lines for run in re.findall(r'`+', line)), default=0)
        fence = '`' * max(3, longest + 1)
        self.line(fence)
        for line in lines:
            self.line(line)
        self.line(fence)
        self.line()


def _count(value):
    if value is None:
        return 'not supplied'
    if type(value) is not int or value < 0:
        raise ValueError('status count must be a nonnegative integer or null')
    return str(value)


def render_status(result):
    """Render every existing status field; no joins, decisions or input pointers added."""
    if set(result) - (set(STATUS_FIELDS) | {'counts', 'queues'}):
        raise ValueError('unsupported status fields; update the renderer before exporting')
    counts, queues = result['counts'], result['queues']
    if set(counts) != set(queues) or set(queues) - set(QUEUE_KEYS):
        raise ValueError('unsupported status queues; update the renderer before exporting')
    if set(result['readiness']['counts']) != set(READINESS_COUNTS):
        raise ValueError('unsupported readiness counts; update the renderer before exporting')
    document = _Markdown()
    document.line('# Supplied-data research status')
    document.line()
    document.line(BOUNDARY)
    document.line()
    document.line('## Review queue counts')
    document.line()
    document.line('Labels are program-defined. Unknown or not-supplied counts are not zero. '
                  'Rows are separate queues, not a total or priority ranking.')
    document.line()
    document.line('| Queue | Count |')
    document.line('| --- | --- |')
    for key in QUEUE_KEYS:
        if key in counts:
            rows = queues[key]
            if rows is not None and type(rows) is not list:
                raise ValueError('status queue must be a list or null')
            if counts[key] != (None if rows is None else len(rows)):
                raise ValueError('status count differs from its queue')
            document.line('| ' + key + ' | ' + _count(counts[key]) + ' |')
    document.line()
    document.line('## Readiness bookkeeping counts')
    document.line()
    document.line('Closed gates and supplied assertions do not establish evidence sufficiency.')
    document.line()
    document.line('| Bookkeeping | Count |')
    document.line('| --- | --- |')
    for key in READINESS_COUNTS:
        document.line('| ' + key + ' | ' + _count(result['readiness']['counts'][key]) + ' |')
    document.line()
    document.line('## Status fields')
    document.line()
    document.line('Each fenced line is a quoted JSON value from status(), including its scopes, '
                  'boundaries, hashes and optional retrospective records. null means not supplied '
                  'or unknown; [] means an available empty list. Omitted optional sections remain omitted.')
    document.line()
    for key in STATUS_FIELDS:
        if key in result:
            document.line('### ' + key)
            document.line()
            document.block(result[key])
    document.line('## Review queue items')
    document.line()
    document.line('Each fenced line is one supplied-status queue item, with nested fields and '
                  'any existing input pointers preserved. No new pointer or item is inferred.')
    document.line()
    for key in QUEUE_KEYS:
        if key in queues:
            document.line('### ' + key)
            document.line()
            document.block(queues[key], items=True)
    document.line('## Boundary')
    document.line()
    document.line(STATUS_BOUNDARY)
    document.line()
    document.line(BOUNDARY)
    document.line()
    document.line('Census: NOT_ESTABLISHED')
    document.line('Conclusion: NOT_READY')
    return bytes(document.raw)


def export_status(protocol):
    """Return a small receipt and detached Markdown without changing the protocol."""
    result = status(protocol)
    raw = render_status(result)
    hashes = dict(result['engine_sha256'])
    root = Path(__file__).resolve().parent
    for name in ('views_export.py', 'prisma_audit.py'):
        hashes[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    receipt = dict(schema=SCHEMA, status='RENDERED', protocol_sha256=result['protocol_sha256'],
                   hash_scope=result['hash_scope'], engine_sha256=hashes,
                   markdown=dict(encoding='utf-8', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
                   queue_count=len(result['queues']), counts=dict(result['counts']),
                   readiness_counts=dict(result['readiness']['counts']),
                   external_calls=0, protocol_changed=False, census_claim='NOT_ESTABLISHED',
                   conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    return receipt, raw


def render_text(receipt):
    lines = ['Supplied-data status Markdown receipt']
    lines.extend(key + ': ' + quoted_display(receipt[key]) for key in sorted(receipt))
    return '\n'.join(lines) + '\n'


def _write_new(path, raw):
    """Refuse existing entries, including dangling links on Windows, then create.

    Stable paths are required. Concurrent replacement and ancestor aliases are not
    a security boundary. An OS write failure may leave an incomplete new file.
    """
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError('output directory entry already exists')
    with path.open('xb') as target:
        target.write(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('status', help='save supplied-data status Markdown')
    command.add_argument('protocol', type=Path)
    command.add_argument('--output', type=Path, required=True, metavar='NEW_MD')
    command.add_argument('--text', action='store_true', help='print a quoted receipt instead of JSON')
    args = parser.parse_args()
    try:
        with args.protocol.open('rb') as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('protocol exceeds size limit')
        receipt, markdown = export_status(parse_json(raw))
        stdout = (render_text(receipt) if args.text else json.dumps(
            receipt, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
        if len(stdout) > MAX_BYTES:
            raise ValueError('status receipt exceeds size limit; narrow the supplied protocol')
        # Both complete serializations pass before the only output is created.
        _write_new(args.output, markdown)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'Status Markdown error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
