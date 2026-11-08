"""Append supplied source/evidence-linked contexts through separate exact-input review."""
import argparse
import copy
import datetime
import errno
import hashlib
import json
from pathlib import Path
import re

from context_links import COMMON_FIELDS, DOMAIN_FIELDS, validate_source_refs
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
MAX_CONTEXTS = 100
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Append only explicitly supplied guideline/development context assertions after separate exact-input '
    'import review. No applicability, guideline currency, recommendation strength, evidence certainty, '
    'development stage, regulatory status or scientific judgement is generated or verified. Import review '
    'does not change the supplied pending/reviewed status or establish source reading. '
    'Source-review contexts keep exact typed planned-search/record links without evidence or study '
    'promotion. Evidence contexts link only explicitly supplied existing normalized result IDs. '
    'No new context is assigned to existing work packages or synthesis statements. All original raw '
    'context rows, work links, source data, evidence, planning, synthesis and completion assertions '
    'remain unchanged. New contexts remain unassigned; their existence is not an applicability decision. '
    'Selected source/result snapshots are detached context, not proof that a locator was opened or '
    'supports a statement. Reviewer/issuer identities, dates, source authenticity, clinical applicability '
    'and regulatory validity remain unverified. Exact unsigned replay is not authentication or chronology. '
    'No external call, model call, source reading, clinical recommendation or procedure is performed. '
    'Keep real inputs outside this public repository; supplied private text is retained without redaction.'
)
NEGATIVE_CLAIMS = dict(external_calls=0, source_reading='NOT_PERFORMED',
    scientific_assessment='NOT_PERFORMED', clinical_applicability='NOT_ASSESSED',
    guideline_currency='NOT_VERIFIED', regulatory_status_verification='NOT_PERFORMED',
    reviewer_identity='NOT_VERIFIED', review_renewal='NOT_PERFORMED',
    existing_work_assignment='NOT_PERFORMED', source_authenticity='NOT_VERIFIED')


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
                                   for name in ('nbib_intake.py', 'context_intake.py')})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return research, reports


def _report_counts(reports):
    return copy.deepcopy(reports['report_flow']) if reports is not None else None


def _references(protocol, research, row):
    scope = row['context_scope']
    _ids(row['evidence_ids'], 'evidence_ids', nonempty=scope == 'extracted_evidence')
    if scope == 'source_review':
        if row['evidence_ids']:
            raise ValueError('source_review contexts require empty evidence_ids')
        validate_source_refs(row['source_refs'],
            {p['search_id'] for p in protocol.get('search_plan', []) or []},
            {rid for search in protocol['searches'] for rid in search['record_ids']})
    else:
        known = {r['evidence_id'] for r in research['evidence']}
        if not set(row['evidence_ids']) <= known:
            raise ValueError('context evidence_ids must select exact existing normalized results')


def _context_fields(domain, scope):
    fields = set(COMMON_FIELDS) | set(DOMAIN_FIELDS[domain]) | {
        'domain', 'context_scope', 'evidence_ids', 'review_status'}
    if scope == 'source_review':
        fields.add('source_refs')
    return fields


def _domain_scope(row):
    if not isinstance(row.get('domain'), str) or row['domain'] not in DOMAIN_FIELDS:
        raise ValueError('domain must be clinical_guideline or drug_development')
    if row.get('context_scope') not in ('source_review', 'extracted_evidence'):
        raise ValueError('explicit context_scope must be source_review or extracted_evidence')


def template(protocol, reference_document):
    """Copy only explicit domain/scope/links; all context assertions remain blank."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    if not isinstance(refs, dict):
        raise ValueError('reference document must be an object')
    _domain_scope(refs)
    fields = {'schema_version', 'domain', 'context_scope', 'evidence_ids'}
    if refs['context_scope'] == 'source_review':
        fields.add('source_refs')
    _schema(refs, fields, 'reference document')
    research, _ = _validate(protocol)
    _references(protocol, research, refs)
    row = {field: None for field in sorted(_context_fields(refs['domain'], refs['context_scope']))}
    row.update({key: copy.deepcopy(value) for key, value in refs.items() if key != 'schema_version'})
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_CONTEXTS',
        candidate_document=dict(schema_version=1, contexts=[row]),
        protocol_sha256=digest(protocol), engine_sha256=_implementation_hashes(),
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Only explicit domain, scope and links are copied. Fill every context assertion, including review_status, honestly; no applicability or review is inferred.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'contexts'}, 'candidate document')
    rows = document['contexts']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CONTEXTS:
        raise ValueError('contexts must contain between 1 and 100 supplied rows')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('context must be an object')
        _domain_scope(row)
        required = _context_fields(row['domain'], row['context_scope'])
        optional = {'reviewer', 'reviewed_at'}
        if not required <= set(row) or set(row) - required - optional:
            raise ValueError('context has unknown or missing fields')
        if any(not _text(row[key]) for key in set(COMMON_FIELDS) | set(DOMAIN_FIELDS[row['domain']])):
            raise ValueError('all context text must be explicitly supplied and nonblank')
        _date(row['accessed_at'], 'accessed_at')
        if row['review_status'] not in ('pending', 'reviewed'):
            raise ValueError('review_status must be explicitly pending or reviewed')
        if row['review_status'] == 'reviewed' and not optional <= set(row):
            raise ValueError('reviewed contexts require reviewer and reviewed_at')
        if 'reviewer' in row and not _text(row['reviewer']):
            raise ValueError('supplied reviewer must be nonblank')
        if 'reviewed_at' in row:
            _date(row['reviewed_at'], 'reviewed_at')
        if row['context_id'] in seen:
            raise ValueError('duplicate candidate context_id')
        seen.add(row['context_id'])
        _ids(row['evidence_ids'], 'evidence_ids', nonempty=row['context_scope'] == 'extracted_evidence')
        if row['context_scope'] == 'source_review' and row['evidence_ids']:
            raise ValueError('source_review contexts require empty evidence_ids')


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_contexts':
        raise ValueError('review decision must be import_contexts')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _same(a, b, label):
    if canonical_json_bytes(a) != canonical_json_bytes(b):
        raise ValueError('context intake must preserve ' + label)


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    old_ids = {row['context_id'] for row in before['context']['context_ledger']}
    new_ids = [row['context_id'] for row in document['contexts']]
    if old_ids.intersection(new_ids):
        raise ValueError('new context_id collides with an existing context; no replacement or merge')
    for row in document['contexts']:
        _references(protocol, before, row)
    candidate = copy.deepcopy(protocol)
    prefix = len(protocol.get('contexts', []))
    candidate.setdefault('contexts', []).extend(copy.deepcopy(document['contexts']))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    if 'contexts' in protocol:
        restored['contexts'] = restored['contexts'][:prefix]
    else:
        restored.pop('contexts')
    _same(restored, protocol, 'every original raw field and context prefix')
    _same(before['flow'], after['flow'], 'record flow')
    _same(_report_counts(before_reports), _report_counts(after_reports), 'report flow')
    for key in ('search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit',
                'work_packages', 'execution_order', 'appraisal', 'experiments', 'planning', 'synthesis'):
        _same(before[key], after[key], key)
    _same(before['context']['context_ledger'],
          [row for row in after['context']['context_ledger'] if row['context_id'] in old_ids],
          'existing normalized contexts')
    _same(before['context']['work_package_context'], after['context']['work_package_context'], 'existing work context links')
    records = prepare_targets(protocol, before.get('bibliographic_collection'))
    reports = prepare_report_targets(protocol, before.get('bibliographic_collection'))
    record_targets = {row['record_id']: row for row in records['record_targets']}
    plans = {row['search_id']: (index, row) for index, row in enumerate(protocol.get('search_plan', []) or [])}
    normalized = {row['evidence_id']: (index, row) for index, row in enumerate(before['evidence'])}
    selected_evidence, selected_sources, selected_record_ids = [], [], set()
    for index, row in enumerate(document['contexts']):
        for eid in row['evidence_ids']:
            evidence_index, evidence = normalized[eid]
            raw = protocol['evidence'][evidence_index]
            selected_evidence.append(dict(candidate_index=index, context_id=row['context_id'],
                evidence_id=eid, input_pointer=f'/evidence/{evidence_index}',
                identity_origin='EXPLICIT_EVIDENCE_ID' if 'evidence_id' in raw else 'LEGACY_RECORD_ID',
                raw_evidence=copy.deepcopy(raw), normalized_evidence=copy.deepcopy(evidence)))
            selected_record_ids.add(evidence['record_id'])
        for ref in row.get('source_refs', []):
            source = dict(candidate_index=index, context_id=row['context_id'], source_ref=copy.deepcopy(ref))
            if ref['kind'] == 'planned_search':
                plan_index, plan = plans[ref['search_id']]
                source.update(input_pointer=f'/search_plan/{plan_index}', planned_search=copy.deepcopy(plan))
            else:
                source['record_target'] = copy.deepcopy(record_targets[ref['record_id']])
                selected_record_ids.add(ref['record_id'])
            selected_sources.append(source)
    target = dict(schema_version=1, target_type='manual_context_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document),
        appended_contexts=[dict(candidate_index=i, output_pointer=f'/contexts/{prefix+i}',
                               context=copy.deepcopy(row)) for i, row in enumerate(document['contexts'])],
        selected_evidence=selected_evidence, selected_sources=selected_sources,
        selected_record_targets=[copy.deepcopy(row) for row in records['record_targets']
                                 if row['record_id'] in selected_record_ids],
        mapped_report_source_targets=[copy.deepcopy(row) for row in reports['report_targets']
                                      if selected_record_ids.intersection(row['recorded_report']['record_ids'])],
        source_context_scope='MAPPED_CATALOG_CONTEXT_NOT_SELECTED_OR_READ_DOCUMENTS',
        before_unassigned_context_ids=copy.deepcopy(before['context']['unassigned_context_ids']),
        after_unassigned_context_ids=copy.deepcopy(after['context']['unassigned_context_ids']),
        before_pending_context_ids=copy.deepcopy(before['context']['review_pending']),
        after_pending_context_ids=copy.deepcopy(after['context']['review_pending']),
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Prepare a blank import review without judging their clinical or development applicability."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_CONTEXT_IMPORT_REVIEW',
        target=target, review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Fill all human review fields after inspecting the exact proposed records, links and unassigned context scope. Import review does not endorse clinical or development assertions or change context review status.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed supplied records without renewing any older assertions."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, contexts and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_context_count=len(before['context']['context_ledger']),
        after_context_count=len(after['context']['context_ledger']),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=_report_counts(before_reports), after_report_flow=_report_counts(after_reports),
        engine_sha256=_implementation_hashes(), boundary=BOUNDARY, **copy.deepcopy(NEGATIVE_CLAIMS))
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_context_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Replay the full application; do not validate scientific context adequacy."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_context_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached context intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied context rows, import review and recorded implementation; not authentication, clinical applicability, guideline currency or regulatory assessment.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied context intake\n' + '\n'.join(
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
        parser.exit(1, 'context intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
