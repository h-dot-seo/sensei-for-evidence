"""Append supplied screening-sheet positions after separate exact-input import review."""
import argparse
import base64
import binascii
import copy
import hashlib
import json
from pathlib import Path

from challenge_intake import _date, _normalized, _schema, REVIEW_FIELDS
from csv_export_parser import parse_export
from csv_safety import safe_csv_cell
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes
import screening_review
import screening_sheet

MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_POSITIONS = 100
BOUNDARY = (
    'Append-only supplied reviewer positions, not canonical screening decisions. No vote, adjudication, '
    'reviewer supersession, eligibility judgement or review renewal is performed. Blank human rows are '
    'skipped explicitly; partial rows, changed read-only cells, stale protocol/source hashes and duplicate '
    'review IDs or record/reviewer pairs fail closed. Import review authorizes recording only, not '
    'endorsement. CSV human cells are literal, never unescaped; formula-like prefixes and leading '
    'apostrophes are rejected rather than guessed. Exact replay binds original CSV bytes, protocol and '
    'implementation, not authenticity, chronology or identity. Consistently reauthored unsigned records '
    'can replay. Locators and retained display text are inert and never opened. Real sheets must stay '
    'outside the public repository. No network, model calls or scientific conclusions.'
)
NEGATIVE_CLAIMS = dict(adjudication='NOT_PERFORMED', reviewer_identity_verification='NOT_ESTABLISHED',
    reading='NOT_ESTABLISHED', source_authenticity='NOT_VERIFIED', conclusion_readiness='NOT_READY',
    canonical_screening_changed=False, external_calls=0)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _hashes():
    root = Path(__file__).resolve().parent
    names = ('screening_sheet_intake.py', 'screening_sheet.py', 'screening_review.py',
             'csv_export_parser.py', 'csv_safety.py', 'challenge_intake.py', 'nbib_intake.py')
    return dict(engine_hashes(), **{name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def _prepare(protocol, raw):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    parsed = parse_export(raw, id_column='record_id', locator_column='source_basis_sha256')
    headers = parsed['headers']
    displays = [name[len('readonly_display:'):] for name in headers if name.startswith('readonly_display:')]
    expected_raw, _ = screening_sheet.export_sheet(protocol, displays)
    expected = parse_export(expected_raw, id_column='record_id', locator_column='source_basis_sha256')
    if headers != expected['headers']:
        raise ValueError('sheet headers must match an exported screening sheet exactly')
    if len(parsed['record_rows']) > screening_sheet.MAX_ROWS:
        raise ValueError('sheet exceeds exported record limit')
    known = {row['source_locator']: row['original_values'] for row in expected['record_rows']}
    readonly = [key for key in headers if key not in screening_sheet.HUMAN_COLUMNS]
    seen, appended, skipped, provenance = set(), [], [], []
    for row in parsed['record_rows']:
        cells = row['original_values']
        basis = cells['source_basis_sha256']
        if basis in seen:
            raise ValueError('duplicate sheet source_basis_sha256')
        seen.add(basis)
        if basis not in known:
            raise ValueError('unknown or stale source_basis_sha256; never automatically refreshed')
        if any(cells[key] != known[basis][key] for key in readonly):
            raise ValueError('changed read-only sheet cell or stale export protocol; export and review again')
        rid = parse_json(cells['readonly_record_id_json'].encode('utf-8'))
        human = {key: cells[key] for key in screening_sheet.HUMAN_COLUMNS}
        item = dict(record_id=rid, source_basis_sha256=basis, source_span=row['source_span'], human_cells=human)
        provenance.append(item)
        if all(value == '' for value in human.values()):
            skipped.append(copy.deepcopy(item))
            continue
        if any(not value.strip() for value in human.values()):
            raise ValueError('partly filled human row; every human field must be nonblank')
        if any(value.startswith("'") or safe_csv_cell(value) != value for value in human.values()):
            raise ValueError('ambiguous formula/escape prefix in human cell; no automatic unescaping')
        appended.append(dict(record_id=rid, source_basis_sha256=basis, **human))
    if not 1 <= len(appended) <= MAX_POSITIONS:
        raise ValueError('sheet must contain 1 to 100 completed positions')
    before = screening_review.review(protocol)
    candidate = copy.deepcopy(protocol)
    candidate.setdefault('screening_reviews', []).extend(copy.deepcopy(appended))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    # Reuse the engine's complete assertions validator, including old/new collisions.
    after = screening_review.review(candidate)
    target = dict(schema_version=1, target_type='screening_sheet_positions_intake',
        input_protocol_sha256=digest(protocol), sheet_sha256=hashlib.sha256(raw).hexdigest(),
        sheet_bytes=len(raw), parsed_human_rows=provenance, skipped_blank_human_rows=skipped,
        ignored_blank_spans=parsed['ignored_blank_spans'], header_source_span=parsed['header_source_span'],
        appended_positions=appended, protocol_candidate_sha256=digest(candidate),
        before_review_cues=before['record_review_ledger'], after_review_cues=after['record_review_ledger'],
        engine_sha256=_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return target, candidate


def prepare(protocol, raw):
    target, _ = _prepare(protocol, raw)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'], decision='import_screening_reviews')
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_IMPORT_REVIEW', target=target,
        review_document=review, protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY),
        MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, raw, review_document):
    review = _normalized(review_document, screening_sheet.MAX_OUTPUT_BYTES, 'import review')
    _schema(review, REVIEW_FIELDS, 'import review')
    if any(not isinstance(review[key], str) or not review[key].strip() for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('import review fields must be nonblank literal strings')
    if review['decision'] != 'import_screening_reviews':
        raise ValueError('import review decision must be import_screening_reviews')
    _date(review['reviewed_at'], 'import reviewed_at')
    target, candidate = _prepare(protocol, raw)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('import review target differs from exact input/implementation; no automatic rebase')
    receipt = dict(schema_version=1, target=target, assertion=review,
        sheet_base64=base64.b64encode(raw).decode('ascii'), boundary=BOUNDARY, **NEGATIVE_CLAIMS)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_screening_sheet_positions',
        receipt=receipt, protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application')


def verify(protocol, application):
    record = _normalized(application, MAX_APPLICATION_BYTES, 'application')
    _schema(record, {'schema_version', 'kind', 'receipt', 'protocol_candidate'}, 'application')
    if (record['kind'] != 'detached_screening_sheet_positions' or not isinstance(record['receipt'], dict)
            or not {'sheet_base64', 'assertion'} <= set(record['receipt'])
            or not isinstance(record['receipt']['sheet_base64'], str)):
        raise ValueError('invalid screening sheet application')
    try:
        raw = base64.b64decode(record['receipt']['sheet_base64'], validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('invalid recorded sheet encoding') from error
    replay = assemble(protocol, raw, record['receipt']['assertion'])
    if canonical_json_bytes(replay) != canonical_json_bytes(record):
        raise ValueError('application differs from exact replay')
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_sha256=record['receipt']['receipt_sha256'],
        protocol_candidate_sha256=digest(record['protocol_candidate']), protocol_changed=False,
        **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def _read(path, limit):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('input exceeds byte limit')
    return raw


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('target', 'assemble', 'verify'):
        sub = commands.add_parser(name)
        sub.add_argument('protocol', type=Path)
        sub.add_argument('input', type=Path, help='edited sheet for target/assemble, application for verify')
        if name == 'assemble':
            sub.add_argument('review', type=Path)
        sub.add_argument('--output', type=Path)
        if name == 'verify':
            sub.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        protocol = parse_json(_read(args.protocol, MAX_PROTOCOL_BYTES))
        raw = _read(args.input, MAX_APPLICATION_BYTES if args.command == 'verify' else screening_sheet.MAX_OUTPUT_BYTES)
        candidate_bytes = None
        if args.command == 'target':
            result = prepare(protocol, raw)
        elif args.command == 'assemble':
            result = assemble(protocol, raw, parse_json(_read(args.review, screening_sheet.MAX_OUTPUT_BYTES)))
        else:
            application = parse_json(raw)
            result = verify(protocol, application)
            if args.protocol_output is not None:
                candidate_bytes = (json.dumps(application['protocol_candidate'], ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
        encoded = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
        if len(encoded) > MAX_APPLICATION_BYTES:
            raise ValueError('serialized output exceeds byte limit')
        destinations = [path for path in (args.output, getattr(args, 'protocol_output', None)) if path is not None]
        if len({path.resolve() for path in destinations}) != len(destinations):
            raise ValueError('output paths must be distinct')
        for path in destinations:
            try:
                path.lstat()
            except FileNotFoundError:
                pass
            else:
                raise ValueError('output path already exists')
            if not path.parent.is_dir():
                raise ValueError('output parent must exist')
        if candidate_bytes is not None:
            if len(candidate_bytes) > MAX_PROTOCOL_BYTES:
                raise ValueError('serialized candidate exceeds byte limit')
            screening_sheet._write_new(args.protocol_output, candidate_bytes)
        if args.output is not None:
            screening_sheet._write_new(args.output, encoded)
        else:
            print(encoded.decode('utf-8'), end='')
    except (ValueError, OSError, TypeError, RecursionError) as error:
        parser.exit(2, 'screening sheet intake: '+quoted_display(str(error))+'\n')


if __name__ == '__main__':
    main()
