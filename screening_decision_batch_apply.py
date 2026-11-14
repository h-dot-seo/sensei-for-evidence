"""Assemble separately reviewed decision batches and replay before exclusive new-protocol export."""
import argparse
import base64
import binascii
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

from challenge_intake import _date, _normalized, _schema, REVIEW_FIELDS
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
import screening_decision_batch as preview
import screening_decision_sheet

MAX_APPLICATION_BYTES = 50_000_000
MAX_REVIEW_BYTES = 10_000_000
BOUNDARY = (
    'Exact separately supplied human import review only. The review authorizes recording the exact supplied '
    'decision sheet, not endorsing scientific reasoning or adjudication validity. No choices or review fields '
    'are generated. Ordinary chained decisions are produced by the existing full operational guards. '
    'Original protocol and files remain unchanged; assembly produces a detached application, not an overwrite. '
    'The candidate changes only supplied canonical screening rows and appends ordinary history receipts; '
    'existing reviewer positions and all other fields are preserved. Verify replays original protocol, '
    'exact CSV bytes, review, target and implementation before any new protocol export. No automatic rebase. '
    'Batch provenance is detached: retain this application alongside the new protocol. Exact unsigned hashes '
    'are not authentication or chronology; consistently reauthored records can replay. Review identity and '
    'reading NOT_ESTABLISHED; scientific validity NOT_ASSESSED; no adjudication performed by this tool. '
    'Locators are inert and never opened. No network/model calls. Keep real sheets/applications private.'
)
NEGATIVE_CLAIMS = dict(original_protocol_changed=False, reviewer_positions_changed=False,
    review_identity='NOT_ESTABLISHED', reading='NOT_ESTABLISHED', adjudication='NOT_PERFORMED',
    scientific_validity='NOT_ASSESSED', external_calls=0, conclusion_readiness='NOT_READY')


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def assemble(protocol, raw, review_document):
    """Produce a detached candidate only after exact separate import-review validation."""
    review = _normalized(review_document, MAX_REVIEW_BYTES, 'import review')
    _schema(review, REVIEW_FIELDS, 'import review')
    if any(not isinstance(review[key], str) or not review[key].strip() for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all import-review human fields must be nonblank literal strings')
    if review['decision'] != 'apply_screening_decisions':
        raise ValueError('import review decision must be apply_screening_decisions')
    _date(review['reviewed_at'], 'import reviewed_at')
    target, candidate = preview._simulate(protocol, raw)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target differs from exact sheet/original/implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], assertion=review, target=target,
        sheet_base64=base64.b64encode(raw).decode('ascii'), input_protocol_sha256=target['input_protocol_sha256'],
        protocol_candidate_sha256=digest(candidate), engine_sha256=target['engine_sha256'],
        import_review_scope='EXACT_SUPPLIED_BATCH_RECORDING_ONLY', **NEGATIVE_CLAIMS, boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_reviewed_screening_decision_batch',
        receipt=receipt, protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application')


def verify(protocol, application):
    """Replay all recorded input and candidate bytes semantically; no input writes."""
    record = _normalized(application, MAX_APPLICATION_BYTES, 'application')
    _schema(record, {'schema_version','kind','receipt','protocol_candidate'}, 'application')
    if (record['kind'] != 'detached_reviewed_screening_decision_batch' or not isinstance(record['receipt'], dict)
            or not {'sheet_base64','assertion'} <= set(record['receipt'])
            or not isinstance(record['receipt']['sheet_base64'], str)):
        raise ValueError('invalid detached decision-batch application')
    encoded = record['receipt']['sheet_base64']
    if len(encoded) > 4 * ((screening_decision_sheet.MAX_OUTPUT_BYTES + 2) // 3):
        raise ValueError('recorded sheet exceeds byte limit')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('invalid recorded sheet encoding') from error
    replayed = assemble(protocol, raw, record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application differs from exact original-input replay')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact supplied original protocol, raw CSV bytes, separate import review and implementation; not authentication.',
        **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def _write_new(path, raw):
    """Publish one complete same-directory temporary file with atomic exclusive hard-link creation."""
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError('output directory entry already exists')
    # Close before linking for native Windows. Link never replaces an existing entry.
    fd, name = tempfile.mkstemp(prefix='.screening-batch-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink()


def _read(path, limit):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('input exceeds byte limit')
    return raw


def _encode(value, limit):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode('utf-8')
    if len(raw) > limit:
        raise ValueError('serialized output exceeds byte limit')
    return raw


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    assembled = commands.add_parser('assemble')
    assembled.add_argument('protocol', type=Path)
    assembled.add_argument('sheet', type=Path)
    assembled.add_argument('review', type=Path)
    assembled.add_argument('--output', type=Path, required=True)
    verified = commands.add_parser('verify')
    verified.add_argument('protocol', type=Path)
    verified.add_argument('application', type=Path)
    outputs = verified.add_mutually_exclusive_group()
    outputs.add_argument('--output', type=Path, help='new verification report only')
    outputs.add_argument('--protocol-output', type=Path, help='new verified protocol only; report remains on stdout')
    args = parser.parse_args()
    try:
        protocol = parse_json(_read(args.protocol, preview.MAX_PROTOCOL_BYTES))
        if args.command == 'assemble':
            result = assemble(protocol, _read(args.sheet, screening_decision_sheet.MAX_OUTPUT_BYTES),
                              parse_json(_read(args.review, MAX_REVIEW_BYTES)))
            raw = _encode(result, MAX_APPLICATION_BYTES)
            _write_new(args.output, raw)
        else:
            application = parse_json(_read(args.application, MAX_APPLICATION_BYTES))
            result = verify(protocol, application)
            report = _encode(result, MAX_APPLICATION_BYTES)
            if args.protocol_output is not None:
                candidate = _encode(application['protocol_candidate'], preview.MAX_PROTOCOL_BYTES)
                _write_new(args.protocol_output, candidate)
                print(report.decode('utf-8'), end='')
            elif args.output is not None:
                _write_new(args.output, report)
            else:
                print(report.decode('utf-8'), end='')
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError) as error:
        parser.exit(1, 'screening decision batch application: '+quoted_display(str(error))+'\n')


if __name__ == '__main__':
    main()
