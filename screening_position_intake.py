"""Import explicitly mapped long-form CSV reviewer positions, never screening decisions."""
import argparse
import base64
import binascii
import copy
import hashlib
import json
from pathlib import Path
import re

from challenge_intake import _normalized, REVIEW_FIELDS, digest
from csv_export_parser import parse_export
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes
from reviewed_intake_safety import validate_import_review, replay_application
from screening_links import validate_review_assertions
from screening_sheet import _write_new
from screening_sheet_intake import _read
import screening_review

MAX_INPUT_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_POSITIONS = 100
COLUMNS = {'record_id', 'decision', 'reviewer', 'reviewed_at', 'rationale', 'source_locator'}
BOUNDARY = (
    'Operator-prepared long-form UTF-8 CSV and explicit literal column/label mappings only; '
    'not a Rayyan, Covidence or EndNote compatibility claim. Supplied reviewer positions, '
    'not canonical screening decisions, votes, consensus or eligibility judgement. Source '
    'basis hashes come from the supplied pre-review template, never refreshed on import. '
    'The claim that reviewers saw that template, and that it predates review, is unverified; '
    'hashes cannot establish chronology, identity or authenticity. Stale sources fail closed. '
    'A label such as Consensus is just a label. No fuzzy ID matching, date conversion, '
    'formula execution, escape removal or dialect inference. Separate import review authorizes '
    'recording only. Unsigned consistently reauthored records can replay. Locators are inert '
    'and never opened. No network or model calls. Keep real CSVs and retained review text '
    'outside the public repository; hashes and receipts do not grant redistribution rights.'
)
NEGATIVE_CLAIMS = dict(canonical_screening_changed=False, adjudication='NOT_PERFORMED',
    reviewer_identity_verification='NOT_ESTABLISHED', reading='NOT_ESTABLISHED',
    source_authenticity='NOT_VERIFIED', census_claim='NOT_ESTABLISHED',
    conclusion_readiness='NOT_READY', external_calls=0)


def _hashes():
    root = Path(__file__).resolve().parent
    names = ('screening_position_intake.py', 'screening_review.py', 'screening_sheet.py',
             'screening_sheet_intake.py', 'csv_export_parser.py', 'challenge_intake.py',
             'nbib_intake.py', 'reviewed_intake_safety.py')
    return dict(engine_hashes(), **{name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def _basis(template):
    template = _normalized(template, MAX_INPUT_BYTES, 'basis template')
    if (not isinstance(template, dict) or type(template.get('schema_version')) is not int
            or template['schema_version'] != 1 or not isinstance(template.get('protocol_sha256'), str)
            or re.fullmatch('[0-9a-f]{64}', template['protocol_sha256']) is None
            or not isinstance(template.get('record_targets'), list)):
        raise ValueError('basis template requires schema1, protocol_sha256 and record_targets')
    targets = {}
    for row in template['record_targets']:
        if (not isinstance(row, dict) or set(row) != {'record_id', 'source_basis', 'source_basis_sha256'}
                or not isinstance(row['record_id'], str) or not row['record_id'].strip()
                or not isinstance(row['source_basis'], dict)
                or row['source_basis'].get('record_id') != row['record_id']
                or row['source_basis_sha256'] != digest(row['source_basis'])
                or row['record_id'] in targets):
            raise ValueError('invalid, inconsistent or duplicate template source target')
        targets[row['record_id']] = row
    return dict(schema_version=1, protocol_sha256=template['protocol_sha256'],
                record_targets=copy.deepcopy(template['record_targets'])), targets


def preview(protocol, raw, basis_template, columns, labels):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    current = screening_review.review(protocol)
    compact, targets = _basis(basis_template)
    if (not isinstance(columns, dict) or set(columns) not in (COLUMNS, COLUMNS | {'review_id'})
            or any(not isinstance(v, str) or not v.strip() for v in columns.values())
            or len(set(columns.values())) != len(columns)):
        raise ValueError('explicit distinct nonblank column names required')
    if (not isinstance(labels, dict) or not labels or not set(labels) <= {'include', 'exclude', 'unclear'}
            or any(not isinstance(v, str) or not v.strip() for v in labels.values())
            or len(set(labels.values())) != len(labels)):
        raise ValueError('explicit unique canonical=literal labels required')
    inverse = {value:key for key, value in labels.items()}
    if not isinstance(raw, bytes) or len(raw) > MAX_INPUT_BYTES:
        raise ValueError('CSV must be bounded bytes')
    parsed = parse_export(raw, id_column=columns['record_id'], locator_column=columns['source_locator'])
    if not set(columns.values()) <= set(parsed['headers']):
        raise ValueError('mapped column absent from CSV')
    if not 1 <= len(parsed['record_rows']) <= MAX_POSITIONS:
        raise ValueError('CSV must contain 1 to 100 position rows')
    known = {r['record_id'] for r in current['record_targets']}
    export_hash = hashlib.sha256(raw).hexdigest()
    existing = protocol.get('screening_reviews', [])
    ids = {r['review_id'] for r in existing}
    pairs = {(r['record_id'],r['reviewer']) for r in existing}
    rows, blocked = [], []
    for index, item in enumerate(parsed['record_rows'], 1):
        cells = item['original_values']
        row = {key:cells[column] for key, column in columns.items()}
        row.setdefault('review_id', 'csv-row-'+str(index).zfill(6)+'@'+export_hash)
        row['decision'] = inverse.get(row['decision'], row['decision'])
        errors = []
        if cells[columns['decision']] not in inverse:
            errors.append('unmapped_decision_label')
        target = targets.get(row['record_id'])
        row['source_basis_sha256'] = target['source_basis_sha256'] if target else ''
        if target is None:
            errors.append('missing_template_record')
        if row['record_id'] not in known:
            errors.append('unknown_current_record')
        try:
            validate_review_assertions([row], known)
        except ValueError as error:
            errors.append(str(error))
        pair = (row['record_id'], row['reviewer'])
        if row['review_id'] in ids or pair in pairs:
            errors.append('duplicate_review_id_or_record_reviewer')
        ids.add(row['review_id']); pairs.add(pair)
        rows.append(row)
        if errors:
            blocked.append(dict(row_index=index, source_span=item['source_span'], reasons=errors))
    provenance = dict(export_base64=base64.b64encode(raw).decode('ascii'), export_sha256=export_hash,
        export_bytes=len(raw), columns=copy.deepcopy(columns), labels=copy.deepcopy(labels),
        basis_template=compact, parsed_rows=parsed['record_rows'],
        header_source_span=parsed['header_source_span'], ignored_blank_spans=parsed['ignored_blank_spans'])
    return _normalized(dict(schema_version=1, screening_reviews=rows, blocked_rows=blocked,
        provenance=provenance, boundary=BOUNDARY, **NEGATIVE_CLAIMS), MAX_APPLICATION_BYTES, 'candidate document')


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_APPLICATION_BYTES, 'candidate document')
    if not isinstance(document, dict) or not isinstance(document.get('provenance'), dict):
        raise ValueError('candidate document requires retained CSV provenance')
    source = document['provenance']
    try:
        raw = base64.b64decode(source['export_base64'], validate=True)
        replay = preview(protocol, raw, source['basis_template'], source['columns'], source['labels'])
    except (KeyError, TypeError, binascii.Error) as error:
        raise ValueError('invalid CSV provenance') from error
    if canonical_json_bytes(replay) != canonical_json_bytes(document):
        raise ValueError('candidate document differs from original CSV/template/mapping replay')
    if document['blocked_rows']:
        raise ValueError('blocked CSV rows must be resolved by the operator before target')
    before = screening_review.review(protocol)
    current = {row['record_id']:row['source_basis_sha256'] for row in before['record_targets']}
    if any(current[row['record_id']] != row['source_basis_sha256'] for row in document['screening_reviews']):
        raise ValueError('source basis is stale; regenerate the template and re-examine, never refresh hashes alone')
    candidate = copy.deepcopy(protocol)
    candidate.setdefault('screening_reviews', []).extend(copy.deepcopy(document['screening_reviews']))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after = screening_review.review(candidate)
    target = dict(schema_version=1, target_type='screening_position_csv_intake',
        input_protocol_sha256=digest(protocol), candidate_document_sha256=digest(document),
        export_sha256=source['export_sha256'], basis_template_protocol_sha256=source['basis_template']['protocol_sha256'],
        appended_positions=copy.deepcopy(document['screening_reviews']), stale_rows=0,
        protocol_candidate_sha256=digest(candidate), before_review_cues=before['record_review_ledger'],
        after_review_cues=after['record_review_ledger'], engine_sha256=_hashes(),
        boundary=BOUNDARY, negative_claims=copy.deepcopy(NEGATIVE_CLAIMS))
    target['target_sha256'] = digest(target)
    return target, candidate


def prepare(protocol, document):
    target, _ = _prepare(protocol, document)
    assertion = {key:None for key in sorted(REVIEW_FIELDS)}
    assertion.update(schema_version=1, target_sha256=target['target_sha256'], decision='import_screening_positions')
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_IMPORT_REVIEW', target=target,
        review_document=assertion, protocol_changed=False, boundary=BOUNDARY, **NEGATIVE_CLAIMS),
        MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, document, assertion):
    assertion = validate_import_review(assertion, 'import_screening_positions', MAX_INPUT_BYTES)
    target, candidate = _prepare(protocol, document)
    if assertion['target_sha256'] != target['target_sha256']:
        raise ValueError('import review target differs; no automatic rebase')
    receipt = dict(schema_version=1, target=target, assertion=assertion,
        candidate_document=copy.deepcopy(document), boundary=BOUNDARY, **NEGATIVE_CLAIMS)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_screening_position_csv', receipt=receipt,
        protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application')


def verify(protocol, application):
    record = replay_application(protocol, application, 'detached_screening_position_csv', assemble, MAX_APPLICATION_BYTES)
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_sha256=record['receipt']['receipt_sha256'], protocol_candidate_sha256=digest(record['protocol_candidate']),
        protocol_changed=False, boundary=BOUNDARY, **NEGATIVE_CLAIMS)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('preview', 'target', 'assemble', 'verify'):
        sub = commands.add_parser(name)
        sub.add_argument('protocol', type=Path)
        sub.add_argument('input', type=Path)
        if name == 'preview':
            sub.add_argument('--basis-template', type=Path, required=True)
            for field in sorted(COLUMNS):
                sub.add_argument('--'+field.replace('_','-')+'-column', required=True)
            sub.add_argument('--review-id-column')
            sub.add_argument('--label', action='append', required=True, metavar='DECISION=LITERAL')
        if name == 'assemble':
            sub.add_argument('review', type=Path)
        outputs = sub.add_mutually_exclusive_group()
        outputs.add_argument('--output', type=Path)
        if name == 'verify':
            outputs.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        protocol = parse_json(_read(args.protocol, MAX_PROTOCOL_BYTES))
        raw = _read(args.input, MAX_INPUT_BYTES if args.command == 'preview' else MAX_APPLICATION_BYTES)
        if args.command == 'preview':
            columns = {key:getattr(args,key+'_column') for key in COLUMNS}
            if args.review_id_column is not None:
                columns['review_id'] = args.review_id_column
            labels = {}
            for value in args.label:
                key, separator, label = value.partition('=')
                if not separator or key in labels:
                    raise ValueError('labels must be unique DECISION=LITERAL pairs')
                labels[key] = label
            result = preview(protocol, raw, parse_json(_read(args.basis_template, MAX_INPUT_BYTES)), columns, labels)
        elif args.command == 'target':
            result = prepare(protocol, parse_json(raw))
        elif args.command == 'assemble':
            result = assemble(protocol, parse_json(raw), parse_json(_read(args.review, MAX_INPUT_BYTES)))
        else:
            application = parse_json(raw)
            result = verify(protocol, application)
        if getattr(args, 'protocol_output', None) is not None:
            result = application['protocol_candidate']
        encoded = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
        if len(encoded) > MAX_APPLICATION_BYTES:
            raise ValueError('serialized output exceeds byte limit')
        destination = args.output or getattr(args, 'protocol_output', None)
        if destination is not None:
            _write_new(destination, encoded)
        else:
            print(encoded.decode('utf-8'), end='')
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as error:
        parser.exit(2, 'screening position intake: '+quoted_display(str(error))+'\n')


if __name__ == '__main__':
    main()
