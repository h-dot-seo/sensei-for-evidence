"""Append supplied independent challenges to synthesis statements through separate exact-input review."""
import argparse
import copy
import datetime
import errno
import hashlib
import json
from pathlib import Path
import re

from challenge_links import CONCLUSION_WIDTHS, OUTCOMES, challenge_basis, reviewer_labels
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from nbib_intake import _strict_json
from prisma_reports import report_flow
from research_bundle import engine_hashes

MAX_CANDIDATE_BYTES = 10_000_000
MAX_PROTOCOL_BYTES = 50_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_CHALLENGES = 100
CHALLENGE_FIELDS = {'challenge_id', 'challenger', 'challenged_at', 'statement_ids', 'alternative_explanation',
                    'missing_discriminating_evidence', 'citation_integrity_findings', 'conclusion_width',
                    'outcome', 'reopening', 'limitations', 'independence_declaration', 'basis_sha256'}
TEXT_FIELDS = {'challenge_id', 'challenger', 'challenged_at', 'alternative_explanation',
               'limitations', 'independence_declaration'}
FINDING_FIELDS = {'evidence_id', 'finding'}
REVIEW_FIELDS = {'schema_version', 'receipt_id', 'target_sha256', 'decision',
                 'reviewer', 'reviewed_at', 'rationale'}
APPLICATION_FIELDS = {'schema_version', 'kind', 'receipt', 'protocol_candidate'}
BOUNDARY = (
    'Explicitly supplied independent-challenge assertions and exact-input replay only. No alternative '
    'explanation, missing-evidence item, citation-integrity finding, conclusion-width label, outcome or '
    'reopening is selected, generated, scored or adjudicated. Each new challenge is bound to the current '
    'bases of its explicitly listed existing synthesis statements; the binding detects later statement, '
    'evidence or appraisal changes and does not establish that any statement is supported or refuted. '
    'A challenger label distinct from the recorded reviewer, position-recorder and appraiser labels is '
    'a mechanical check, not verified independence, identity or competence. A MATERIAL_GAP outcome must '
    'name existing reopening work or an amendment note; it does not start work, change a work state or '
    'alter any statement, review, appraisal or planning assertion. Existing challenges and all other raw '
    'research, source, work, planning, synthesis and completion assertions remain unchanged. The separate '
    'import review authorizes only recording the supplied challenges, not endorsing their reasoning. '
    'Unsigned editable records do not authenticate people, chronology or globally unique IDs; consistently '
    'reauthored assertions can replay. Challenge rows persist in the candidate; import review and selected '
    'snapshots remain detached. No completeness, scientific acceptance or conclusion readiness is established.'
)
NEGATIVE_CLAIMS = dict(challenge_execution='NOT_PERFORMED', alternative_explanation_assessment='NOT_PERFORMED',
    statement_adjudication='NOT_PERFORMED', citation_integrity_verification='NOT_PERFORMED',
    independence_verification='LABEL_DISTINCT_ONLY', reviewer_identity_verification='NOT_ESTABLISHED',
    source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED', existing_review_renewal='NOT_PERFORMED',
    reopening_work_started='NOT_PERFORMED', import_review_scope='DETACHED_RECORD_ONLY',
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
                                   for name in ('nbib_intake.py', 'challenge_intake.py')})


def _validate(protocol):
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    research = run(protocol)
    if research['synthesis']['stage'] != 'SUPPLIED':
        raise ValueError('challenges require supplied synthesis statements')
    reports = report_flow(protocol, include_csv=False) if 'reports' in protocol else None
    return research, reports


def _report_counts(reports):
    return copy.deepcopy(reports['report_flow']) if reports is not None else None


def _statements(research, statement_ids):
    _ids(statement_ids, 'statement_ids', nonempty=True)
    known = {row['statement_id'] for row in research['synthesis']['statement_ledger']}
    if any(sid not in known for sid in statement_ids):
        raise ValueError('statement_ids must select exact existing synthesis statement IDs')


def template(protocol, reference_document):
    """Select existing statements and bind their current bases; leave every challenge judgement blank."""
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    refs = _normalized(reference_document, MAX_CANDIDATE_BYTES, 'reference document')
    _schema(refs, {'schema_version', 'statement_ids'}, 'reference document')
    research, _ = _validate(protocol)
    _statements(research, refs['statement_ids'])
    challenge = {key: None for key in sorted(CHALLENGE_FIELDS)}
    challenge.update(statement_ids=copy.deepcopy(refs['statement_ids']),
                     basis_sha256=challenge_basis(research['synthesis'], refs['statement_ids']),
                     missing_discriminating_evidence=[], citation_integrity_findings=[], reopening=None)
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_CHALLENGES',
        candidate_document=dict(schema_version=1, challenges=[challenge]),
        recorded_labels_on_selected_statements=sorted(reviewer_labels(research['synthesis'], refs['statement_ids'])),
        protocol_sha256=digest(protocol), engine_sha256=_implementation_hashes(), protocol_changed=False,
        **NEGATIVE_CLAIMS,
        template_warning='Only the statement selection and its current basis hash are mechanical. The challenger, '
                         'alternative explanation, missing discriminating evidence, citation-integrity findings, '
                         'conclusion width, outcome, reopening, limitations and independence declaration must be '
                         'supplied by a human whose label differs from every recorded label listed here.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'template')


def validate_candidate_document(document):
    _schema(document, {'schema_version', 'challenges'}, 'candidate document')
    rows = document['challenges']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CHALLENGES:
        raise ValueError('challenges must be a nonempty list of at most 100 rows')
    seen = set()
    for row in rows:
        _schema(row, CHALLENGE_FIELDS, 'challenge')
        if any(not _text(row[key]) for key in TEXT_FIELDS):
            raise ValueError('challenge text fields must be supplied nonblank literal strings')
        _date(row['challenged_at'], 'challenged_at')
        _ids(row['statement_ids'], 'statement_ids', nonempty=True)
        if row['challenge_id'] in seen:
            raise ValueError('duplicate candidate challenge_id')
        seen.add(row['challenge_id'])
        missing = row['missing_discriminating_evidence']
        if not isinstance(missing, list) or len(missing) > MAX_CHALLENGES or any(not _text(item) for item in missing):
            raise ValueError('missing_discriminating_evidence must be a list of at most 100 nonblank strings')
        findings = row['citation_integrity_findings']
        if not isinstance(findings, list) or len(findings) > MAX_CHALLENGES:
            raise ValueError('citation_integrity_findings must be a list of at most 100 rows')
        for finding in findings:
            _schema(finding, FINDING_FIELDS, 'citation integrity finding')
            if any(not _text(finding[key]) for key in FINDING_FIELDS):
                raise ValueError('citation integrity finding fields must be supplied nonblank literal strings')
        if row['conclusion_width'] not in CONCLUSION_WIDTHS:
            raise ValueError('conclusion_width must be one of ' + ', '.join(CONCLUSION_WIDTHS))
        if row['outcome'] not in OUTCOMES:
            raise ValueError('outcome must be one of ' + ', '.join(OUTCOMES))
        reopening = row['reopening']
        if reopening is not None and (not isinstance(reopening, dict) or len(reopening) != 1
                                      or not {'work_package_id', 'amendment_note'} & set(reopening)
                                      or not _text(next(iter(reopening.values())))):
            raise ValueError('reopening must be null or exactly one nonblank work_package_id or amendment_note')
        if re.fullmatch(r'[0-9a-f]{64}', row['basis_sha256'] or '') is None:
            raise ValueError('basis_sha256 must be 64 lowercase hexadecimal characters')


def validate_review_document(document):
    _schema(document, REVIEW_FIELDS, 'review document')
    if any(not _text(document[key]) for key in REVIEW_FIELDS - {'schema_version'}):
        raise ValueError('all review text fields must be supplied nonblank literal strings')
    if document['decision'] != 'import_challenges':
        raise ValueError('review decision must be import_challenges')
    if re.fullmatch(r'[0-9a-f]{64}', document['target_sha256']) is None:
        raise ValueError('target_sha256 must be 64 lowercase hexadecimal characters')
    _date(document['reviewed_at'], 'reviewed_at')


def _same(a, b, label):
    if canonical_json_bytes(a) != canonical_json_bytes(b):
        raise ValueError('challenge intake must preserve ' + label)


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate document')
    validate_candidate_document(document)
    before, before_reports = _validate(protocol)
    old_ids = {row['challenge_id'] for row in before['challenge']['challenge_ledger']}
    new_ids = [row['challenge_id'] for row in document['challenges']]
    if old_ids.intersection(new_ids):
        raise ValueError('candidate challenge_id collides with an existing challenge; no replacement or merge')
    for row in document['challenges']:
        _statements(before, row['statement_ids'])
        if row['basis_sha256'] != challenge_basis(before['synthesis'], row['statement_ids']):
            raise ValueError('challenge basis does not match the current challenged statements; '
                             'regenerate the template and re-examine before recording')
    candidate = copy.deepcopy(protocol)
    prefix = len(protocol.get('challenges', []))
    candidate.setdefault('challenges', []).extend(copy.deepcopy(document['challenges']))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    after, after_reports = _validate(candidate)
    restored = copy.deepcopy(candidate)
    if 'challenges' in protocol:
        restored['challenges'] = restored['challenges'][:prefix]
    else:
        restored.pop('challenges')
    _same(restored, protocol, 'every original raw field and challenge prefix')
    _same(before['flow'], after['flow'], 'record flow')
    _same(_report_counts(before_reports), _report_counts(after_reports), 'report flow')
    for key in ('search_ledger', 'screening_ledger', 'evidence', 'search_plan_audit', 'work_packages',
                'execution_order', 'context', 'experiments', 'appraisal', 'synthesis', 'planning'):
        _same(before[key], after[key], key)
    _same(before['challenge']['challenge_ledger'],
          [row for row in after['challenge']['challenge_ledger'] if row['challenge_id'] in old_ids],
          'existing normalized challenges')
    statements = {row['statement_id']: (index, row) for index, row in enumerate(before['synthesis']['statement_ledger'])}
    targets = {row['statement_id']: row for row in before['synthesis']['review_targets']}
    evidence = {row['evidence_id']: row for row in before['evidence']}
    selected_statements, selected_evidence_ids = [], set()
    for index, row in enumerate(document['challenges']):
        for sid in row['statement_ids']:
            statement_index, statement = statements[sid]
            selected_statements.append(dict(candidate_index=index, challenge_id=row['challenge_id'],
                statement_id=sid, input_pointer=f'/synthesis_statements/{statement_index}',
                raw_statement=copy.deepcopy(protocol['synthesis_statements'][statement_index]),
                normalized_statement=copy.deepcopy(statement),
                current_statement_basis_sha256=targets[sid]['basis_sha256']))
            selected_evidence_ids.update(statement['evidence_ids'])
    appended = [row for row in after['challenge']['challenge_ledger'] if row['challenge_id'] in new_ids]
    target = dict(schema_version=1, target_type='manual_challenge_intake',
        input_protocol_sha256=digest(protocol), candidate_document=copy.deepcopy(document),
        candidate_document_sha256=digest(document),
        appended_challenges=[dict(candidate_index=i, output_pointer=f'/challenges/{prefix + i}',
            challenge=copy.deepcopy(row)) for i, row in enumerate(document['challenges'])],
        normalized_appended_challenges=copy.deepcopy(appended),
        selected_statements=selected_statements,
        selected_evidence=[copy.deepcopy(evidence[eid]) for eid in sorted(selected_evidence_ids)],
        recorded_labels_on_selected_statements=sorted(
            reviewer_labels(before['synthesis'], sorted({sid for row in document['challenges'] for sid in row['statement_ids']}))),
        statement_context_scope='CITED_RESULT_ROWS_AND_CURRENT_BASES_NOT_READ_DOCUMENTS',
        before_statements_without_challenge=copy.deepcopy(before['challenge']['statements_without_challenge']),
        after_statements_without_challenge=copy.deepcopy(after['challenge']['statements_without_challenge']),
        after_challenges_with_open_material_gaps=copy.deepcopy(after['challenge']['challenges_with_open_material_gaps']),
        engine_sha256=_implementation_hashes(), negative_claims=copy.deepcopy(NEGATIVE_CLAIMS), boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return protocol, document, target, candidate, before, before_reports, after, after_reports


def prepare(protocol, candidate_document):
    """Prepare a blank import review without judging the supplied challenges."""
    protocol, document, target, _, _, _, _, _ = _prepare(protocol, candidate_document)
    review = {key: None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1, target_sha256=target['target_sha256'])
    return _normalized(dict(schema_version=1, status='AWAITING_SUPPLIED_CHALLENGE_IMPORT_REVIEW',
        target=target, review_document=review, protocol_sha256=digest(protocol),
        candidate_document_sha256=digest(document), engine_sha256=target['engine_sha256'],
        protocol_changed=False, **NEGATIVE_CLAIMS,
        template_warning='Fill all human review fields after inspecting the exact proposed records, challenged '
                         'statements and recorded labels. Import review does not endorse the challenge reasoning '
                         'or its outcome.',
        boundary=BOUNDARY), MAX_APPLICATION_BYTES, 'prepared target')


def assemble(protocol, candidate_document, review_document):
    """Append reviewed supplied challenges without renewing any older assertions."""
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'review document')
    validate_review_document(review)
    protocol, document, target, candidate, before, before_reports, after, after_reports = _prepare(protocol, candidate_document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review target does not match exact original input, challenges and implementation; no automatic rebase')
    receipt = dict(schema_version=1, receipt_id=review['receipt_id'], candidate_document=document,
        assertion=review, target=target, input_protocol_sha256=digest(protocol),
        protocol_candidate_sha256=digest(candidate), candidate_document_sha256=digest(document),
        before_challenge_count=len(before['challenge']['challenge_ledger']),
        after_challenge_count=len(after['challenge']['challenge_ledger']),
        before_flow=copy.deepcopy(before['flow']), after_flow=copy.deepcopy(after['flow']),
        before_report_flow=_report_counts(before_reports), after_report_flow=_report_counts(after_reports),
        engine_sha256=_implementation_hashes(), boundary=BOUNDARY, **copy.deepcopy(NEGATIVE_CLAIMS))
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1, kind='detached_challenge_intake', receipt=receipt,
                            protocol_candidate=candidate), MAX_APPLICATION_BYTES, 'application record')


def verify(original_protocol, application_record):
    """Replay the full application; do not assess whether any challenge is sound."""
    record = _normalized(application_record, MAX_APPLICATION_BYTES, 'application record')
    _schema(record, APPLICATION_FIELDS, 'application record')
    if (record['kind'] != 'detached_challenge_intake' or not isinstance(record['receipt'], dict)
            or not {'candidate_document', 'assertion'} <= set(record['receipt'])):
        raise ValueError('invalid detached challenge intake application record')
    replayed = assemble(original_protocol, record['receipt']['candidate_document'], record['receipt']['assertion'])
    if canonical_json_bytes(replayed) != canonical_json_bytes(record):
        raise ValueError('application record differs from exact replay of original input and recorded implementation')
    receipt = replayed['receipt']
    return dict(schema_version=1, valid=True, status='EXACT_REPLAY_MATCH',
        receipt_id=receipt['receipt_id'], receipt_sha256=receipt['receipt_sha256'],
        input_protocol_sha256=receipt['input_protocol_sha256'],
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        engine_sha256=copy.deepcopy(receipt['engine_sha256']),
        verification_scope='Exact original input, supplied challenge rows, import review and recorded implementation; '
                           'not authentication, independence verification or scientific assessment.',
        protocol_changed=False, **NEGATIVE_CLAIMS, boundary=BOUNDARY)


def render_text(result):
    result = _normalized(result, MAX_APPLICATION_BYTES, 'text rendering input')
    rendered = 'Supplied independent challenge intake\n' + '\n'.join(
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
        parser.exit(1, 'challenge intake error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
