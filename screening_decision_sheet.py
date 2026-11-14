"""Export blank, bounded human-decision sheets without creating screening decisions."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from bibliographic_intake import read_bounded
from csv_export_parser import parse_export
from csv_safety import safe_csv_cell
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from nbib_intake import _strict_json
import screening_review
import screening_sheet

MAX_ROWS = 100
MAX_INPUT_BYTES = 50_000_000
MAX_OUTPUT_BYTES = 10_000_000
HUMAN_COLUMNS = ('receipt_id', 'decision', 'reason', 'adjudicator', 'decided_at', 'rationale', 'source_locator')
CONTEXT_COLUMNS = ('readonly_prior_screening_json', 'readonly_review_context_json',
                   'readonly_export_review_context_sha256')
BOUNDARY = (
    'Blank human-decision transcription sheet only. No decision, reason, adjudicator, date, rationale, '
    'locator or receipt ID is inferred or copied into human fields. Supplied prior screening and reviewer '
    'assertions are read-only context, not recommended choices or verified evidence. No vote, consensus, '
    'adjudication or reviewer-position import occurs. Existing protocol, canonical screening and history '
    'remain unchanged. Export-time source, protocol and review-context hashes bind supplied snapshots, '
    'not currentness after editing, authentication or human approval. They are not sequential per-record '
    'decision targets. Edited decision-sheet target/assemble/verify intake is NOT_IMPLEMENTED. Never use '
    'this sheet with the positions intake, refresh old hashes or automatically rebase human assertions. '
    'Future batch intake must review the exact sheet and compute chained ordinary targets internally. '
    'Locators and retained display values are inert; nothing is opened, fetched, inferred or executed. '
    'Keep real sheets and sources outside this public repository. Reviewer identity and reading are '
    'NOT_ESTABLISHED; source authenticity NOT_VERIFIED; adjudication NOT_PERFORMED; readiness NOT_READY.'
)


def _json(value):
    return canonical_json_bytes(value).decode('utf-8')


def export_sheet(protocol, record_ids=None, display_columns=()):
    """Reuse existing source targets and render explicitly selected blank choices."""
    _strict_json(protocol)
    if len(canonical_json_bytes(protocol)) > MAX_INPUT_BYTES:
        raise ValueError('protocol exceeds byte limit')
    if record_ids is not None:
        if (type(record_ids) not in (list, tuple) or not 1 <= len(record_ids) <= MAX_ROWS
                or any(type(rid) is not str or not rid.strip() for rid in record_ids)
                or len(set(record_ids)) != len(record_ids)):
            raise ValueError('record_ids must select 1 to 100 unique literal IDs')
    # The existing export validates the entire protocol and preserves literal retained columns.
    position_raw, position_receipt = screening_sheet.export_sheet(protocol, display_columns)
    source = parse_export(position_raw, id_column='record_id', locator_column='source_basis_sha256')
    source_rows = {parse_json(row['original_values']['readonly_record_id_json'].encode('utf-8')):
                   row['original_values'] for row in source['record_rows']}
    selected = list(source_rows) if record_ids is None else list(record_ids)
    if len(selected) > MAX_ROWS:
        raise ValueError('select at most 100 records; this is not a high-volume decisions tool')
    if any(rid not in source_rows for rid in selected):
        raise ValueError('unknown record_id selection')
    reviews = screening_review.review(protocol)
    records = {row['record_id']: row for row in reviews['record_review_ledger']}
    grouped = {rid: [] for rid in selected}
    for item in reviews['review_ledger']:
        rid = item['review']['record_id']
        if rid in grouped:
            grouped[rid].append(item)
    readonly_headers = [name for name in position_receipt['headers'] if name not in screening_sheet.HUMAN_COLUMNS]
    headers = [*readonly_headers, *CONTEXT_COLUMNS, *HUMAN_COLUMNS]
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow(headers)
    for rid in selected:
        prior = records[rid]['recorded_screening']
        context = dict(review_stage=reviews['stage'], supplied_review_ledger=grouped[rid],
                       record_review_cues=records[rid])
        writer.writerow([*[source_rows[rid][name] for name in readonly_headers],
            safe_csv_cell(_json(prior)), safe_csv_cell(_json(context)),
            hashlib.sha256(canonical_json_bytes(context)).hexdigest(), *[''] * len(HUMAN_COLUMNS)])
    raw = out.getvalue().encode('utf-8')
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError('decision sheet exceeds output byte limit')
    # Same strict CSV consumer limits, NUL/UTF-8 and physical-row rules as later supplied-file intake.
    parse_export(raw, id_column='record_id', locator_column='source_basis_sha256')
    receipt = dict(schema_version=1, mode='blank_screening_decision_sheet_export',
        protocol_sha256=position_receipt['protocol_sha256'], sheet_sha256=hashlib.sha256(raw).hexdigest(),
        sheet_bytes=len(raw), record_rows=len(selected), selection_scope='ALL_ENUMERATED_RECORDS' if record_ids is None else 'EXPLICIT_ORDERED_RECORD_IDS',
        selected_record_ids=selected, headers=headers, display_columns=position_receipt['display_columns'],
        validation_scope='ENTIRE_PROTOCOL', protocol_changed=False, human_decisions_prefilled=False,
        decision_history_changed=False, screening_performed=False, adjudication='NOT_PERFORMED',
        edited_sheet_intake='NOT_IMPLEMENTED', sequential_decision_targets_created=False,
        reviewer_identity='NOT_ESTABLISHED', reading='NOT_ESTABLISHED', external_calls=0,
        conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    return raw, receipt


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('protocol', type=Path)
    export.add_argument('--record-id', action='append')
    export.add_argument('--display-column', action='append', default=[])
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        protocol = parse_json(read_bounded(args.protocol, MAX_INPUT_BYTES))
        raw, receipt = export_sheet(protocol, args.record_id, args.display_column)
        rendered = ('Blank screening-decision sheet exported\nRows: '+str(receipt['record_rows'])+
                    '\nSheet SHA-256: '+receipt['sheet_sha256']+'\n'+BOUNDARY+'\n' if args.text else
                    json.dumps(receipt, ensure_ascii=False, allow_nan=False, indent=2)+'\n')
        rendered.encode('utf-8')
        screening_sheet._write_new(args.output, raw)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'screening decision sheet error: '+quoted_display(str(error))+'\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
