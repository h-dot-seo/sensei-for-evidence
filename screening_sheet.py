"""Export a blank, formula-safe screening-position transcription sheet offline.

This exports a new scaffold only. It does not import edited cells, replace review
assertions, perform screening or create canonical decisions. Original protocols
and retained native wrappers remain the provenance authority, not this view.
"""
import argparse
import csv
import errno
import hashlib
import io
import json
from pathlib import Path

from bibliographic_intake import read_bounded
from csv_safety import safe_csv_cell
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from nbib_intake import _strict_json
import screening_review

MAX_INPUT_BYTES = 50_000_000
MAX_OUTPUT_BYTES = 10_000_000
MAX_ROWS = 10_000
MAX_DISPLAY_COLUMNS = 16
HUMAN_COLUMNS = ('review_id', 'reviewer', 'reviewed_at', 'decision', 'rationale', 'source_locator')
BASE_COLUMNS = ('record_id', 'source_basis_sha256', 'readonly_record_id_json',
                'readonly_export_protocol_sha256', 'readonly_retained_locators_json')
BOUNDARY = (
    'Blank transcription scaffold only, not screening performed, import approval or a canonical decision. '
    'Human assertion cells are empty even when prior reviews exist. Reviewer supersession is not implemented. '
    'Source hashes describe the export-time supplied context; they do not establish currentness after edits. '
    'Never refill or replace an old source hash to make a stale sheet appear current. '
    'Record IDs may be spreadsheet-escaped; readonly_record_id_json preserves the literal ID. '
    'Display columns are selected literal retained values, possibly incomplete, not interpreted titles or abstracts. '
    'Locators and attachment values are inert text, never opened. No network calls or protocol changes. '
    'Reviewer identity and reading: NOT_ESTABLISHED; source authenticity: NOT_VERIFIED; adjudication: NOT_PERFORMED. '
    'No search completion, scientific correctness or conclusion readiness is established. '
    'Edited-sheet intake is not implemented here. Keep real sheets and source material outside the public repository.'
)


def _json(value):
    return canonical_json_bytes(value).decode('utf-8')


def export_sheet(protocol, display_columns=()):
    """Return exact CSV bytes and a detached descriptive receipt, never review approval."""
    _strict_json(protocol)
    if type(protocol) is not dict:
        raise ValueError('protocol must be an object')
    if type(display_columns) not in (tuple, list):
        raise ValueError('display_columns must be a list or tuple')
    if len(display_columns) > MAX_DISPLAY_COLUMNS:
        raise ValueError('too many display columns')
    if any(type(name) is not str or not name.strip() or len(name) > 128
           or any(ord(ch) < 32 or ord(ch) == 127 for ch in name) for name in display_columns):
        raise ValueError('display columns must be nonblank literal names without control characters')
    if len(set(display_columns)) != len(display_columns):
        raise ValueError('duplicate display column selection')
    draft = screening_review.template(protocol)
    if len(draft['screening_reviews']) > MAX_ROWS:
        raise ValueError('screening sheet exceeds row limit')
    # Use the existing engine targets, never synthesize or reinterpret a basis.
    targets = {row['source_basis_sha256']: row for row in draft['record_targets']}
    display_headers = ['readonly_display:' + name for name in display_columns]
    headers = [*BASE_COLUMNS, *display_headers, *HUMAN_COLUMNS]
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    rows_without_retained_values = 0
    for assertion in draft['screening_reviews']:
        target = targets[assertion['source_basis_sha256']]
        retained = target['source_basis']['bibliographic_rows']
        if not retained:
            rows_without_retained_values += 1
        # Each selected original column remains explicit; no tag parsing or guessed fallback.
        values = []
        for name in display_columns:
            selected = [dict(source_pointer=row['source_pointer'], value=row['original_values'][name])
                        for row in retained if name in row['original_values']]
            values.append(_json(selected) if selected else '')
        locators = [dict(source_pointer=row['source_pointer'], value=row['source_locator']) for row in retained]
        writer.writerow([safe_csv_cell(assertion['record_id']), assertion['source_basis_sha256'],
                         _json(assertion['record_id']), draft['protocol_sha256'],
                         safe_csv_cell(_json(locators)) if locators else '',
                         *[safe_csv_cell(value) for value in values], *[''] * len(HUMAN_COLUMNS)])
    raw = out.getvalue().encode('utf-8')
    if b'\x00' in raw:
        raise ValueError('screening sheet cells must not contain NUL')
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError('screening sheet exceeds output byte limit')
    receipt = dict(schema_version=1, mode='blank_screening_position_sheet_export',
                   protocol_sha256=draft['protocol_sha256'], sheet_sha256=hashlib.sha256(raw).hexdigest(),
                   sheet_bytes=len(raw), record_rows=len(draft['screening_reviews']),
                   rows_without_retained_values=rows_without_retained_values,
                   headers=headers, display_columns=[dict(header=header, original_column=name)
                       for header, name in zip(display_headers, display_columns)],
                   protocol_changed=False, existing_review_assertions_copied=False,
                   edited_sheet_intake='NOT_IMPLEMENTED', screening_performed=False,
                   adjudication='NOT_PERFORMED', reviewer_identity='NOT_ESTABLISHED',
                   reading='NOT_ESTABLISHED', external_calls=0, conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    return raw, receipt


def _write_new(path, raw):
    """Refuse observed final entries; not a race or ancestor-alias security boundary."""
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(errno.EEXIST, 'output directory entry already exists', str(path))
    with path.open('xb') as output:
        output.write(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('protocol', type=Path)
    export.add_argument('--display-column', action='append', default=[])
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        protocol = parse_json(read_bounded(args.protocol, MAX_INPUT_BYTES))
        raw, receipt = export_sheet(protocol, args.display_column)
        rendered = ('Blank screening-position sheet exported\n' +
                    'Recorded rows: ' + str(receipt['record_rows']) + '\n' +
                    'Export protocol SHA-256: ' + receipt['protocol_sha256'] + '\n' +
                    'Sheet SHA-256: ' + receipt['sheet_sha256'] + '\n' + BOUNDARY + '\n'
                    if args.text else json.dumps(receipt, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
        rendered.encode('utf-8')  # Preflight stdout before creating the output.
        _write_new(args.output, raw)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'screening sheet error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
