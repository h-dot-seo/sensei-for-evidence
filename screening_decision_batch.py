"""Preview exact supplied decision sheets and draft blank import review, without applying them."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from challenge_intake import _normalized, REVIEW_FIELDS
from csv_export_parser import parse_export
from csv_safety import safe_csv_cell
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes
import screening_decision
import screening_decision_links
import screening_decision_sheet
import screening_review
import screening_sheet

MAX_DECISIONS = 100
MAX_PROTOCOL_BYTES = 50_000_000
MAX_TARGET_BYTES = 50_000_000
BOUNDARY = (
    'READ_ONLY_TARGET_PREVIEW: supplied human decision rows are simulated in sheet order, not applied '
    'or approved. Canonical screening, protocol and stored receipt history remain unchanged. No candidate '
    'protocol or application file is exported; assemble/verify is not implemented by this preview CLI; a separate reviewed application tool is required. Preview step '
    'hashes and projected rows describe a hypothetical ordinary receipt chain, not executed decisions. '
    'A future separate import review must bind this exact target, sheet, original protocol and implementation; '
    'the blank review document is not approval. No decision, reason, winner, vote or adjudication is inferred. '
    'Every existing read-only cell and export-time source/protocol/review snapshot must match exactly. '
    'Never refresh stale hashes or automatically rebase. Fully blank human rows are explicitly skipped; '
    'partial rows and ambiguous formula/escape prefixes fail. Supplied reviewer positions are not imported '
    'or renewed. Exact byte hashes and snapshots are integrity bookkeeping, not authenticity, chronology, '
    'eligibility correctness, reviewer identity or source reading. Locators are inert and never opened. '
    'Keep real sheets and preview records outside the public repository. Adjudication NOT_PERFORMED; '
    'reading and identity NOT_ESTABLISHED; readiness NOT_READY; no network or model calls.'
)
NEGATIVE_CLAIMS = dict(protocol_changed=False, canonical_screening_changed=False,
    stored_history_changed=False, application_exported=False, approval_granted=False,
    preview_cli_assemble_verify='NOT_IMPLEMENTED', adjudication='NOT_PERFORMED',
    reviewer_identity='NOT_ESTABLISHED', reading='NOT_ESTABLISHED', external_calls=0,
    conclusion_readiness='NOT_READY')


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _hashes():
    root = Path(__file__).resolve().parent
    names = ('screening_decision_batch.py', 'screening_decision_sheet.py', 'screening_sheet.py',
             'screening_review.py', 'screening_decision.py', 'csv_export_parser.py', 'csv_safety.py',
             'challenge_intake.py', 'nbib_intake.py', 'screening_decision_batch_apply.py')
    return dict(engine_hashes(), **{name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def _parse(protocol, raw):
    parsed = parse_export(raw, id_column='record_id', locator_column='source_basis_sha256')
    if not 1 <= len(parsed['record_rows']) <= MAX_DECISIONS:
        raise ValueError('decision sheet must contain 1 to 100 rows')
    displays = [name[len('readonly_display:'):] for name in parsed['headers'] if name.startswith('readonly_display:')]
    reviews = screening_review.review(protocol)
    known = {row['source_basis_sha256']: row['record_id'] for row in reviews['record_targets']}
    ids, seen = [], set()
    for row in parsed['record_rows']:
        basis = row['original_values']['source_basis_sha256']
        if basis not in known:
            raise ValueError('unknown or stale source basis; no automatic refresh')
        if basis in seen:
            raise ValueError('duplicate decision-sheet record/source basis')
        seen.add(basis)
        ids.append(known[basis])
    expected_raw, _ = screening_decision_sheet.export_sheet(protocol, ids, displays)
    expected = parse_export(expected_raw, id_column='record_id', locator_column='source_basis_sha256')
    if parsed['headers'] != expected['headers']:
        raise ValueError('decision-sheet headers differ from exact export contract')
    readonly = [key for key in parsed['headers'] if key not in screening_decision_sheet.HUMAN_COLUMNS]
    rows, skipped, provenance = [], [], []
    for supplied, exported, rid in zip(parsed['record_rows'], expected['record_rows'], ids):
        cells = supplied['original_values']
        if any(cells[key] != exported['original_values'][key] for key in readonly):
            raise ValueError('changed read-only cell or stale original protocol/review context; export and review again')
        human = {key: cells[key] for key in screening_decision_sheet.HUMAN_COLUMNS}
        item = dict(record_id=rid, human_cells=human, source_span=supplied['source_span'],
                    source_basis_sha256=cells['source_basis_sha256'])
        provenance.append(item)
        if all(value == '' for value in human.values()):
            skipped.append(copy.deepcopy(item))
            continue
        if any(not value.strip() for value in human.values()):
            raise ValueError('partial decision row; all human fields must be nonblank')
        if any(value.startswith("'") or safe_csv_cell(value) != value for value in human.values()):
            raise ValueError('ambiguous formula/escape prefix; no automatic unescaping')
        # Validate choices/dates/field shape before simulation; the dummy hash is not an approval target.
        document = dict(schema_version=1, record_id=rid, target_sha256='0'*64, **human)
        screening_decision_links.validate_document(document)
        rows.append(dict(record_id=rid, **human))
    if not rows:
        raise ValueError('decision sheet has no completed human decision rows')
    old_ids = {receipt['receipt_id'] for receipt in protocol.get('screening_decision_history', {}).get('receipts', [])}
    new_ids = [row['receipt_id'] for row in rows]
    if len(set(new_ids)) != len(new_ids) or old_ids.intersection(new_ids):
        raise ValueError('duplicate new or existing receipt_id; no replacement')
    if len(old_ids) + len(rows) > screening_decision_links.MAX_RECEIPTS:
        raise ValueError('hypothetical chain would exceed existing lifetime receipt limit')
    return parsed, rows, skipped, provenance


def _simulate(protocol, raw):
    """Shared exact simulation; candidate is internal, never exported by the preview CLI."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    parsed, rows, skipped, provenance = _parse(protocol, raw)
    candidate = copy.deepcopy(protocol)
    plans = []
    planned_bytes = 0
    before, before_reports = screening_decision._validate(protocol)
    for index, row in enumerate(rows):
        prepared = screening_decision.prepare(candidate, row['record_id'])
        document = dict(prepared['decision_document'], **{key: row[key] for key in screening_decision_sheet.HUMAN_COLUMNS})
        # Public assembly performs the complete before/after workflow guard, not merely chain validation.
        assembled = screening_decision.assemble(candidate, document)
        next_candidate = _normalized(assembled['protocol_candidate'], MAX_PROTOCOL_BYTES, 'simulated candidate')
        receipt = assembled['appended_receipt']
        plan = dict(preview_index=index, record_id=row['record_id'], supplied_decision=copy.deepcopy(row),
            hypothetical_target=copy.deepcopy(receipt['target']), hypothetical_receipt_sha256=receipt['receipt_sha256'],
            projected_screening_row=copy.deepcopy(receipt['result_screening']),
            projected_protocol_sha256=digest(next_candidate), applied=False)
        planned_bytes += len(canonical_json_bytes(plan))
        if planned_bytes > MAX_TARGET_BYTES:
            raise ValueError('hypothetical step previews exceed target byte limit')
        plans.append(plan)
        candidate = next_candidate
    after, after_reports = screening_decision._validate(candidate)
    preserved = {key: value for key, value in candidate.items() if key not in ('screening', 'screening_decision_history')}
    original = {key: value for key, value in protocol.items() if key not in ('screening', 'screening_decision_history')}
    if canonical_json_bytes(preserved) != canonical_json_bytes(original):
        raise ValueError('simulation changed fields outside canonical screening/history')
    target = dict(schema_version=1, target_type='screening_decision_batch_preview',
        input_protocol_sha256=digest(protocol), sheet_sha256=hashlib.sha256(raw).hexdigest(), sheet_bytes=len(raw),
        parsed_human_rows=provenance, skipped_blank_human_rows=skipped,
        header_source_span=parsed['header_source_span'], ignored_blank_spans=parsed['ignored_blank_spans'],
        hypothetical_steps=plans, projected_protocol_sha256=digest(candidate),
        before_flow=copy.deepcopy(before['flow']), projected_after_flow=copy.deepcopy(after['flow']),
        before_report_flow=None if before_reports is None else copy.deepcopy(before_reports['report_flow']),
        projected_after_report_flow=None if after_reports is None else copy.deepcopy(after_reports['report_flow']),
        engine_sha256=_hashes(), **NEGATIVE_CLAIMS, boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    target = _normalized(target, MAX_TARGET_BYTES, 'target')
    return target, candidate


def prepare(protocol, raw):
    """Return only a detached preview and blank review, never a protocol candidate."""
    target, _ = _simulate(protocol, raw)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'], decision='apply_screening_decisions')
    return _normalized(dict(schema_version=1, status='READ_ONLY_TARGET_PREVIEW', target=target,
        review_document=review, **NEGATIVE_CLAIMS, boundary=BOUNDARY), MAX_TARGET_BYTES, 'target preview')


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    target = commands.add_parser('target')
    target.add_argument('protocol', type=Path)
    target.add_argument('sheet', type=Path)
    target.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        def read(path, limit):
            with path.open('rb') as stream:
                raw = stream.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('input exceeds byte limit')
            return raw
        result = prepare(parse_json(read(args.protocol, MAX_PROTOCOL_BYTES)), read(args.sheet, screening_decision_sheet.MAX_OUTPUT_BYTES))
        encoded = (json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode('utf-8')
        if len(encoded) > MAX_TARGET_BYTES:
            raise ValueError('serialized target exceeds byte limit')
        if args.output is not None:
            screening_sheet._write_new(args.output, encoded)
        else:
            print(encoded.decode('utf-8'), end='')
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'screening decision batch preview: '+quoted_display(str(error))+'\n')


if __name__ == '__main__':
    main()
