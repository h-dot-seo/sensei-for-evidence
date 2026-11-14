"""Append supplied evidence basis declarations after a separate exact-input review."""
import argparse
import copy
import datetime
import errno
import hashlib
import json
from pathlib import Path
import re

from evidence_basis_links import FIELDS, BOUNDARY as LABEL_BOUNDARY
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from nbib_intake import _strict_json
from research_bundle import engine_hashes

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = MAX_APPLICATION_BYTES = 50_000_000
MAX_CANDIDATES = 100
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision', 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = LABEL_BOUNDARY + (
    ' Append-only intake; existing labels cannot be corrected here. Import review authorizes recording '
    'declarations only, not their truth. Candidate rows persist but the import review remains detached. '
    'Unsigned editable records can be consistently reauthored; replay does not authenticate people, '
    'chronology or globally unique IDs. Old applications require their recorded trusted implementation. '
    'No observations or result-intake source references are copied into declarations automatically.'
)
NEGATIVE_CLAIMS = dict(label_verification='DECLARED_NOT_VERIFIED', source_authenticity='NOT_VERIFIED',
    scientific_assessment='NOT_PERFORMED', existing_review_renewal='NOT_PERFORMED',
    import_review_scope='DETACHED_RECORD_ONLY', conclusion_readiness='NOT_READY', external_calls=0)

def digest(value):
    _strict_json(value)
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalized(value, limit, label):
    _strict_json(value)
    raw = canonical_json_bytes(value)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _date(value, label):
    if not _text(value) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError(label + ' must be YYYY-MM-DD')
    try:
        datetime.date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(label + ' must be a real calendar date') from error


def _schema(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(label + ' has unknown or missing fields')
    if 'schema_version' in fields and (type(value['schema_version']) is not int or value['schema_version'] != 1):
        raise ValueError(label + ' schema_version must be integer 1')


def _ids(value, label, nonempty=False):
    if (not isinstance(value, list) or (nonempty and not value)
            or any(not _text(item) for item in value) or len(value) != len(set(value))):
        raise ValueError(label + ' must be an explicit list of unique nonblank IDs')


def _implementation_hashes():
    root = Path(__file__).resolve().parent
    return dict(engine_hashes(), **{name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                   for name in ('nbib_intake.py', 'evidence_basis_intake.py')})


def template(protocol, reference_document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    _schema(refs, {'schema_version', 'evidence_ids'}, 'reference document')
    _ids(refs['evidence_ids'], 'evidence_ids', nonempty=True)
    if len(refs['evidence_ids']) > MAX_CANDIDATES:
        raise ValueError('at most 100 candidate IDs')
    research = run(protocol)
    known = {r['evidence_id']: r for r in research['evidence']}
    assigned = {r['evidence_id'] for r in protocol.get('evidence_bases', [])}
    if any(eid not in known or eid in assigned for eid in refs['evidence_ids']):
        raise ValueError('template requires known evidence without an existing basis')
    rows = [dict.fromkeys(sorted(FIELDS)) for eid in refs['evidence_ids']]
    for row, eid in zip(rows, refs['evidence_ids']):
        row['evidence_id'] = eid
    # Catalog is context only: do not choose document IDs or populate human labels.
    reports = {rid: report['report_id'] for report in protocol.get('reports', []) for rid in report['record_ids']}
    catalog = {eid: [copy.deepcopy(s) for s in protocol.get('report_sources', [])
                     if s['report_id'] == reports.get(known[eid]['record_id'])] for eid in refs['evidence_ids']}
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_EVIDENCE_BASES',
        candidate_document=dict(schema_version=1, evidence_bases=rows),
        document_catalog_by_evidence_id=catalog, protocol_sha256=digest(protocol),
        engine_sha256=_implementation_hashes(), protocol_changed=False,
        **NEGATIVE_CLAIMS, boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'template')


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    _schema(document, {'schema_version', 'evidence_bases'}, 'candidate document')
    rows = document['evidence_bases']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CANDIDATES:
        raise ValueError('candidate batch must contain 1 to 100 rows')
    before = run(protocol)
    candidate = copy.deepcopy(protocol)
    candidate.setdefault('evidence_bases', []).extend(copy.deepcopy(rows))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after = run(candidate)  # validates exact shape, duplicates, existing IDs and document membership
    for key in ('flow', 'search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit',
                'work_packages', 'execution_order', 'context', 'experiments', 'appraisal'):
        if canonical_json_bytes(before[key]) != canonical_json_bytes(after[key]):
            raise ValueError('evidence basis intake must preserve original research data')
    target = dict(schema_version=1, target_type='manual_evidence_basis_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document), protocol_candidate_sha256=digest(candidate),
        before_basis_count=len(protocol.get('evidence_bases', [])),
        after_basis_count=len(candidate['evidence_bases']),
        selected_evidence=[copy.deepcopy(r) for r in before['evidence'] if r['evidence_id'] in {row['evidence_id'] for row in rows}],
        after_basis_context=copy.deepcopy(after['evidence_bases']),
        before_stale_statement_ids=before['synthesis']['stale_statement_ids'],
        after_stale_statement_ids=after['synthesis']['stale_statement_ids'],
        before_readiness=copy.deepcopy(before['readiness']), after_readiness=copy.deepcopy(after['readiness']),
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate


def prepare(protocol, candidate_document):
    protocol, document, target, _ = _prepare(protocol, candidate_document)
    review = dict.fromkeys(sorted(REVIEW_FIELDS))
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_EVIDENCE_BASIS_IMPORT_REVIEW',
        target=target, review_document=review, protocol_changed=False,
        **NEGATIVE_CLAIMS, boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'target')


def assemble(protocol, candidate_document, review_document):
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    _schema(review, REVIEW_FIELDS, 'review document')
    if any(not _text(review[k]) for k in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('review fields must be supplied nonblank text')
    if review['decision'] != 'import_evidence_bases':
        raise ValueError('review decision must be import_evidence_bases')
    _date(review['reviewed_at'], 'reviewed_at')
    if re.fullmatch(r'[0-9a-f]{64}', review['target_sha256']) is None:
        raise ValueError('invalid review target digest')
    protocol, document, target, candidate = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact input and implementation; no automatic renewal')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), engine_sha256=_implementation_hashes(),
        **NEGATIVE_CLAIMS, boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_evidence_basis_intake', receipt=receipt,
        protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_evidence_basis_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid evidence basis application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay')
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_sha256=replayed['receipt']['receipt_sha256'], protocol_changed=False,
        **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    return 'Supplied evidence basis intake\n' + '\n'.join(
        quoted_display(k) + ': ' + quoted_display(v) for k, v in result.items()) + '\n'


def _encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def _read(path, limit, label):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _write_new(path, raw):
    """Reject existing final entries, including Windows dangling symlinks.

    Exclusive creation remains required after this check. This is not a
    race-proof defense against concurrent path replacement or ancestor aliases.
    """
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
    draft = commands.add_parser('template')
    target = commands.add_parser('target')
    assembly = commands.add_parser('assemble')
    replay = commands.add_parser('verify')
    for command in (draft, target, assembly, replay):
        command.add_argument('protocol', type=Path)
        command.add_argument('--text', action='store_true')
    draft.add_argument('reference_document', type=Path)
    draft.add_argument('--candidate-output', type=Path)
    for command in (target, assembly):
        command.add_argument('candidate_document', type=Path)
        command.add_argument('--output', required=True, type=Path)
    assembly.add_argument('review_document', type=Path)
    replay.add_argument('application_record', type=Path)
    replay.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        protocol = _read(args.protocol, MAX_PROTOCOL_BYTES, 'original protocol')
        if args.command == 'template':
            result = template(protocol, _read(args.reference_document, MAX_CANDIDATE_BYTES, 'reference document'))
            destination, artifact = args.candidate_output, result['candidate_document']
        elif args.command == 'verify':
            record = _read(args.application_record, MAX_APPLICATION_BYTES, 'application record')
            result = verify(protocol, record)
            destination, artifact = args.protocol_output, record['protocol_candidate']
        else:
            document = _read(args.candidate_document, MAX_CANDIDATE_BYTES, 'candidate document')
            result = (prepare(protocol, document) if args.command == 'target' else
                      assemble(protocol, document, _read(args.review_document, MAX_CANDIDATE_BYTES, 'review document')))
            destination, artifact = args.output, result
        encoded = _encode(artifact).encode('utf-8') if destination is not None else None
        rendered = render_text(result) if args.text else _encode(result)
        for output in (_encode(result), rendered):
            if len(output.encode('utf-8')) > MAX_APPLICATION_BYTES:
                raise ValueError('stdout exceeds byte limit')
        if encoded is not None:
            limit = (MAX_PROTOCOL_BYTES if args.command == 'verify' else
                     MAX_CANDIDATE_BYTES if args.command == 'template' else MAX_APPLICATION_BYTES)
            if len(encoded) > limit:
                raise ValueError('output exceeds byte limit')
        if destination is not None:
            _write_new(destination, encoded)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'evidence basis intake error: invalid input or output\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
