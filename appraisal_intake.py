"""Append supplied result-linked appraisals through separate exact-input review."""
import argparse
import copy
import datetime
import errno
import hashlib
import json
from pathlib import Path
import re

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from nbib_intake import _strict_json
from prisma_reports import report_flow
from research_bundle import engine_hashes
from screening_links import prepare_targets
from report_review_links import prepare_targets as prepare_report_targets

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_APPRAISALS = 100
MAX_DOMAINS = 100
APPRAISAL_FIELDS = {'appraisal_id', 'method', 'method_version', 'method_locator', 'reviewer',
                    'assessed_at', 'limitations', 'evidence_ids', 'domains'}
DOMAIN_FIELDS = {'name', 'judgement', 'rationale', 'source_locator'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicitly supplied result-linked appraisal assertions and exact-input replay only. '
    'No method, rubric, domain, judgement, rationale, score, consensus or clinical recommendation '
    'is selected, generated or validated. Each new appraisal stays within one supplied study ID '
    'and its explicit existing normalized result IDs; this does not establish real study identity '
    'or independence and never extends appraisal to uncited sibling results. Different supplied '
    'judgements remain separate records, not votes or adjudicated consensus. Existing appraisals '
    'and all other raw research, source, work, planning, synthesis and completion assertions remain '
    'unchanged. Existing derived planning/synthesis/completion bases or source-status cues may '
    'change without renewing stored hashes or changing work completion. Fewer result rows without '
    'recorded appraisal means only recorded coverage, not better quality or adequate appraisal. '
    'Selected raw/normalized evidence and mapped record/report source catalogs are retained as '
    'detached context, not a claim that any descriptor or document was read or supports a judgement. '
    'Method/domain locators remain literal text; no lookup, matching, artifact access or retrieval '
    'is performed. Appraisal methods, versions, dates and reviewer identities are unverified. '
    'The separate import review authorizes only recording the supplied appraisals, not endorsing '
    'their quality or conclusions. Unsigned editable records do not authenticate people, chronology '
    'or globally unique review IDs; consistently reauthored assertions can replay. Appraisal rows '
    'persist in the candidate; import review and selected snapshots remain detached. This does not '
    'add a current/stale source-validity label to appraisal rows after later input changes. Keep the '
    'original, application and recorded implementation separately. No completeness, source '
    'acceptance, scientific/clinical approval or development readiness is established.'
)
NEGATIVE_CLAIMS = dict(appraisal_execution='NOT_PERFORMED', current_appraisal_validity='NOT_ASSESSED',
    method_suitability='NOT_ASSESSED',
    rubric_validation='NOT_PERFORMED', judgement_generation='NOT_PERFORMED', quality_scoring='NOT_PERFORMED',
    consensus='NOT_INFERRED', source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED',
    scientific_acceptance='NOT_ASSESSED', clinical_applicability='NOT_ASSESSED',
    existing_review_renewal='NOT_PERFORMED', reviewer_identity_verification='NOT_ESTABLISHED',
    retained_source_snapshot_scope='DETACHED_CONTEXT_ONLY', import_review_scope='DETACHED_RECORD_ONLY',
    census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', external_calls=0)


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
                                   for name in ('nbib_intake.py', 'appraisal_intake.py')})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return research, reports


def _report_counts(reports):
    return copy.deepcopy(reports['report_flow']) if reports is not None else None


def _references(research, evidence_ids):
    _ids(evidence_ids, 'evidence_ids', nonempty=True)
    known = {row['evidence_id']: row for row in research['evidence']}
    if any(eid not in known for eid in evidence_ids):
        raise ValueError('evidence_ids must select exact existing normalized result IDs')
    studies = {known[eid]['study_id'] for eid in evidence_ids}
    if len(studies) != 1:
        raise ValueError('one appraisal must stay within one supplied study ID')
    return next(iter(studies))


def template(protocol, reference_document):
    """Select existing results only; leave every appraisal judgement and method blank."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    _schema(refs, {'schema_version', 'evidence_ids'}, 'reference document')
    research, _ = _validate(protocol)
    study_id = _references(research, refs['evidence_ids'])
    appraisal = {key: None for key in sorted(APPRAISAL_FIELDS)}
    appraisal.update(evidence_ids=copy.deepcopy(refs['evidence_ids']),
                     domains=[{key: None for key in sorted(DOMAIN_FIELDS)}])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_APPRAISALS',
        candidate_document=dict(schema_version=1, appraisals=[appraisal]),
        selected_supplied_study_id=study_id, protocol_sha256=digest(protocol),
        engine_sha256=_implementation_hashes(), protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='All appraisal fields and domain content must be supplied by the human; even domain names and judgement choices remain blank. A single supplied study ID is not identity verification.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'appraisals'}, 'candidate document')
    rows = document['appraisals']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_APPRAISALS:
        raise ValueError('appraisals must be a nonempty list of at most 100 rows')
    seen = set()
    for row in rows:
        _schema(row, APPRAISAL_FIELDS, 'appraisal')
        if any(not _text(row[key]) for key in APPRAISAL_FIELDS - {'evidence_ids', 'domains'}):
            raise ValueError('appraisal text fields must be supplied nonblank literal strings')
        _date(row['assessed_at'], 'assessed_at')
        _ids(row['evidence_ids'], 'evidence_ids', nonempty=True)
        if row['appraisal_id'] in seen:
            raise ValueError('duplicate candidate appraisal_id')
        seen.add(row['appraisal_id'])
        domains = row['domains']
        if not isinstance(domains, list) or not 1 <= len(domains) <= MAX_DOMAINS:
            raise ValueError('domains must be a nonempty list of at most 100 supplied rows')
        names = set()
        for domain in domains:
            _schema(domain, DOMAIN_FIELDS, 'appraisal domain')
            if any(not _text(domain[key]) for key in DOMAIN_FIELDS):
                raise ValueError('domain fields must be supplied nonblank literal strings')
            if domain['name'] in names:
                raise ValueError('duplicate appraisal domain name')
            names.add(domain['name'])


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_appraisals':
        raise ValueError('review decision must be import_appraisals')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _same(a, b, label):
    if canonical_json_bytes(a) != canonical_json_bytes(b):
        raise ValueError('appraisal intake must preserve ' + label)


def _source_status_changes(before, after):
    changes = {}
    for label, left, right, id_field in (
        ('planning', before['planning']['planning_ledger'], after['planning']['planning_ledger'], 'work_package_id'),
        ('completion', before['planning']['completion_ledger'], after['planning']['completion_ledger'], 'work_package_id'),
        ('synthesis', before['synthesis']['statement_ledger'], after['synthesis']['statement_ledger'], 'statement_id')):
        previous = {row[id_field]: row for row in left}
        changes[label] = []
        for row in right:
            old = previous[row[id_field]]
            fields = ('source_match_status', 'current_basis_sha256')
            a, b = ({key: copy.deepcopy(value[key]) for key in fields} for value in (old, row))
            if canonical_json_bytes(a) != canonical_json_bytes(b):
                changes[label].append({id_field: row[id_field], 'before': a, 'after': b})
    return changes


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    old_ids = {row['appraisal_id'] for row in before['appraisal']['appraisal_ledger']}
    new_ids = [row['appraisal_id'] for row in document['appraisals']]
    if old_ids.intersection(new_ids):
        raise ValueError('candidate appraisal_id collides with an existing appraisal; no replacement or merge')
    for row in document['appraisals']:
        _references(before, row['evidence_ids'])
    candidate = copy.deepcopy(protocol)
    prefix = len(protocol.get('appraisals', []))
    candidate.setdefault('appraisals', []).extend(copy.deepcopy(document['appraisals']))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    if 'appraisals' in protocol:
        restored['appraisals'] = restored['appraisals'][:prefix]
    else:
        restored.pop('appraisals')
    _same(restored, protocol, 'every original raw field and appraisal prefix')
    _same(before['flow'], after['flow'], 'record flow')
    _same(_report_counts(before_reports), _report_counts(after_reports), 'report flow')
    for key in ('search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit',
                'work_packages', 'execution_order', 'context', 'experiments'):
        _same(before[key], after[key], key)
    _same(before['appraisal']['appraisal_ledger'],
          [row for row in after['appraisal']['appraisal_ledger'] if row['appraisal_id'] in old_ids],
          'existing normalized appraisals')
    records = prepare_targets(protocol, before.get('bibliographic_collection'))
    reports = prepare_report_targets(protocol, before.get('bibliographic_collection'))
    normalized = {row['evidence_id']: (index, row) for index, row in enumerate(before['evidence'])}
    selected_evidence, selected_record_ids = [], set()
    for index, row in enumerate(document['appraisals']):
        for eid in row['evidence_ids']:
            evidence_index, evidence = normalized[eid]
            raw = protocol['evidence'][evidence_index]
            selected_evidence.append(dict(candidate_index=index, appraisal_id=row['appraisal_id'],
                evidence_id=eid, input_pointer=f'/evidence/{evidence_index}',
                identity_origin='EXPLICIT_EVIDENCE_ID' if 'evidence_id' in raw else 'LEGACY_RECORD_ID',
                raw_evidence=copy.deepcopy(raw), normalized_evidence=copy.deepcopy(evidence)))
            selected_record_ids.add(evidence['record_id'])
    target = dict(schema_version=1, target_type='manual_appraisal_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document),
        appended_appraisals=[dict(candidate_index=i, output_pointer=f'/appraisals/{prefix + i}',
            appraisal=copy.deepcopy(row)) for i, row in enumerate(document['appraisals'])],
        selected_evidence=selected_evidence,
        selected_record_targets=[copy.deepcopy(row) for row in records['record_targets']
                                 if row['record_id'] in selected_record_ids],
        mapped_report_source_targets=[copy.deepcopy(row) for row in reports['report_targets']
                                      if selected_record_ids.intersection(row['recorded_report']['record_ids'])],
        source_context_scope='MAPPED_CATALOG_CONTEXT_NOT_SELECTED_OR_READ_DOCUMENTS',
        derived_source_status_changes=_source_status_changes(before, after),
        before_unappraised_evidence_ids=copy.deepcopy(before['appraisal']['evidence_without_recorded_appraisal']),
        after_unappraised_evidence_ids=copy.deepcopy(after['appraisal']['evidence_without_recorded_appraisal']),
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Prepare a blank import review without judging the supplied appraisals."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_APPRAISAL_IMPORT_REVIEW',
        target=target, review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Fill all human review fields after inspecting the exact proposed records, links and changed source-status cues. Import review does not endorse the method or domain judgements.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed supplied records without renewing any older assertions."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, appraisals and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_appraisal_count=len(before['appraisal']['appraisal_ledger']),
        after_appraisal_count=len(after['appraisal']['appraisal_ledger']),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=_report_counts(before_reports), after_report_flow=_report_counts(after_reports),
        derived_source_status_changes=copy.deepcopy(target['derived_source_status_changes']),
        engine_sha256=_implementation_hashes(), boundary=BOUNDARY, **copy.deepcopy(NEGATIVE_CLAIMS))
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_appraisal_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Replay the full application; do not validate scientific appraisal adequacy."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_appraisal_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached appraisal intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied appraisal rows, import review and recorded implementation; not authentication, method validation or scientific assessment.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied appraisal intake\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'
    if len(rendered.encode('utf-8')) > MAX_APPLICATION_BYTES:
        raise ValueError('text output exceeds byte limit')
    return rendered


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
        parser.exit(1, 'appraisal intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
