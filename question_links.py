"""Validate supplied question records without generating or answering questions."""
import copy
from context_links import id_list, iso_date, nonempty_text
from planning_links import digest
from challenge_links import validate_reopening

STATUSES = ('OPEN', 'NARROWED', 'ANSWERED_WITHIN_BOUNDS', 'UNRESOLVED')
TERMINAL = ('ANSWERED_WITHIN_BOUNDS', 'UNRESOLVED')
TRANSITIONS = {'OPEN': ('NARROWED', 'ANSWERED_WITHIN_BOUNDS', 'UNRESOLVED'),
               'NARROWED': TERMINAL, 'ANSWERED_WITHIN_BOUNDS': (), 'UNRESOLVED': ()}
FIELDS = {'question_id', 'text', 'status', 'parent_question_id', 'origin', 'statement_ids',
          'basis_sha256', 'recorded_by', 'recorded_at', 'rationale', 'limitations', 'reopening'}
ORIGIN_FIELDS = {'kind', 'ref_id', 'protocol_question_sha256', 'external_record_sha256', 'label'}
KINDS = ('PROTOCOL', 'CHALLENGE', 'READINESS_ASSERTION', 'AMENDMENT', 'CONSULTATION', 'OTHER')
MAX_ROWS = 100
BOUNDARY = ('Supplied question labels and one-way statement links only. ANSWERED_WITHIN_BOUNDS and '
            'UNRESOLVED are recorded assertions, not assessed answers or scientific closure. Parent-child '
            'existence is not semantic narrowing. Statement bindings and the protocol-question hash '
            'identify current supplied metadata, not truth, chronology, authorship or approval. External '
            'hashes are opaque identity declarations; no external record is read or authenticated. '
            'No question is generated, gate is added, readiness is promoted or existing review renewed. '
            'Stale and terminal records are not automatically updated or reopened.')
NEGATIVE_CLAIMS = dict(answer_assessment='NOT_PERFORMED', question_generation='NOT_PERFORMED',
    external_record_access='NOT_PERFORMED', origin_authentication='NOT_ESTABLISHED',
    chronology_verification='NOT_PERFORMED', census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')


def _hex(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def question_basis(synthesis, statement_ids):
    """Hash selected existing statement review bases, or None for no statement links."""
    if not statement_ids:
        return None
    targets = {row['statement_id']: row['basis_sha256'] for row in synthesis['review_targets']}
    if any(sid not in targets for sid in statement_ids):
        raise ValueError('question references unknown synthesis statements')
    return digest(dict(schema_version=1, statement_targets=[
        dict(statement_id=sid, basis_sha256=targets[sid]) for sid in sorted(statement_ids)]))


def validate_row(row):
    if not isinstance(row, dict) or set(row) != FIELDS:
        raise ValueError('question requires exact supplied fields')
    for key in ('question_id', 'text', 'recorded_by', 'rationale', 'limitations'):
        if not nonempty_text(row[key]):
            raise ValueError('question text fields must be nonblank strings')
    iso_date(row['recorded_at'], 'recorded_at')
    if row['status'] not in STATUSES:
        raise ValueError('unknown supplied question status')
    if row['parent_question_id'] is not None and not nonempty_text(row['parent_question_id']):
        raise ValueError('question parent must be null or a nonblank ID')
    sids = row['statement_ids']
    id_list(sids, 'statement_ids')
    if len(sids) > MAX_ROWS:
        raise ValueError('question statement_ids must be unique nonblank IDs, at most 100')
    if row['status'] == 'ANSWERED_WITHIN_BOUNDS' and not sids:
        raise ValueError('supplied answered question requires statement links')
    if (sids and not _hex(row['basis_sha256'])) or (not sids and row['basis_sha256'] is not None):
        raise ValueError('question basis must be SHA-256 for links, null without links')
    origin = row['origin']
    if not isinstance(origin, dict) or set(origin) != ORIGIN_FIELDS or origin['kind'] not in KINDS:
        raise ValueError('question origin requires exact fields and a known kind')
    if not nonempty_text(origin['label']):
        raise ValueError('question origin label must be supplied')
    kind = origin['kind']
    if kind in ('CHALLENGE', 'READINESS_ASSERTION', 'AMENDMENT'):
        if not nonempty_text(origin['ref_id']):
            raise ValueError('question origin requires a supplied reference')
    elif origin['ref_id'] is not None:
        raise ValueError('this question origin has no reference ID')
    if kind == 'PROTOCOL':
        if not _hex(origin['protocol_question_sha256']):
            raise ValueError('protocol origin requires a question hash')
    elif origin['protocol_question_sha256'] is not None:
        raise ValueError('only protocol origin may declare a question hash')
    if origin['external_record_sha256'] is not None and (kind != 'CONSULTATION' or not _hex(origin['external_record_sha256'])):
        raise ValueError('external record hash is optional only for consultation origin')
    if kind == 'CONSULTATION' and row['reopening'] is None:
        raise ValueError('consultation-origin question requires supplied controlled reopening')


def link_questions(protocol, synthesis, challenge, readiness, work):
    supplied = protocol.get('question_records', [])
    if not isinstance(supplied, list) or len(supplied) > MAX_ROWS:
        raise ValueError('question_records must be a list of at most 100 rows')
    ledger = {}
    children = {}
    work_ids = {row['work_package_id'] for row in work}
    challenge_ids = {row['challenge_id'] for row in challenge['challenge_ledger']}
    assertion_ids = {row['assertion_id'] for row in readiness['assertion_ledger']}
    for row in supplied:
        validate_row(row)
        qid = row['question_id']
        if qid in ledger:
            raise ValueError('duplicate question_id')
        origin = row['origin']
        if origin['kind'] == 'CHALLENGE' and origin['ref_id'] not in challenge_ids:
            raise ValueError('unknown question challenge origin')
        if origin['kind'] == 'READINESS_ASSERTION' and origin['ref_id'] not in assertion_ids:
            raise ValueError('unknown question readiness origin')
        validate_reopening(row['reopening'], work_ids)
        current = question_basis(synthesis, row['statement_ids'])
        source_status = ('NOT_LINKED' if current is None else
                         'CURRENT_SOURCE' if current == row['basis_sha256'] else 'STALE_SOURCE')
        origin_status = ('NOT_APPLICABLE' if origin['kind'] != 'PROTOCOL' else
                         'CURRENT_PROTOCOL_QUESTION' if origin['protocol_question_sha256'] == digest(protocol['question'])
                         else 'PROTOCOL_QUESTION_CHANGED')
        ledger[qid] = dict(copy.deepcopy(row), current_basis_sha256=current,
                          source_match_status=source_status, protocol_question_status=origin_status)
        children.setdefault(row['parent_question_id'], []).append(qid)
    for qid, row in ledger.items():
        parent = row['parent_question_id']
        if parent is not None and parent not in ledger:
            raise ValueError('unknown parent question ID')
        if row['status'] == 'NARROWED' and not children.get(qid):
            raise ValueError('NARROWED question requires a supplied child question')
        seen = {qid}
        while parent is not None:
            if parent in seen:
                raise ValueError('cyclic question ancestry')
            seen.add(parent)
            if parent not in ledger:
                raise ValueError('unknown parent question ID')
            parent = ledger[parent]['parent_question_id']
    rows = [ledger[qid] for qid in sorted(ledger)]
    return dict(schema_version=1, stage='SUPPLIED' if 'question_records' in protocol else 'NOT_SUPPLIED',
        question_ledger=rows, open_question_ids=[r['question_id'] for r in rows if r['status'] == 'OPEN'],
        unresolved_question_ids=[r['question_id'] for r in rows if r['status'] == 'UNRESOLVED'],
        questions_without_statement_links=[r['question_id'] for r in rows if not r['statement_ids']],
        stale_question_bindings=[r['question_id'] for r in rows if r['source_match_status'] == 'STALE_SOURCE'],
        changed_protocol_question_origins=[r['question_id'] for r in rows if r['protocol_question_status'] == 'PROTOCOL_QUESTION_CHANGED'],
        questions_with_consultation_origin=[r['question_id'] for r in rows if r['origin']['kind'] == 'CONSULTATION'],
        narrowing_chains=[dict(parent_question_id=r['parent_question_id'], question_id=r['question_id']) for r in rows if r['parent_question_id'] is not None],
        statement_question_links=[dict(statement_id=t['statement_id'], question_ids=[r['question_id'] for r in rows if t['statement_id'] in r['statement_ids']]) for t in synthesis['review_targets']],
        **NEGATIVE_CLAIMS, boundary=BOUNDARY)
