"""Record supplied independent challenges to synthesis statements without adjudicating them."""
import copy
from context_links import id_list, iso_date, nonempty_text
from planning_links import digest

BOUNDARY = ('Supplied independent-challenge records only. Alternative explanations, missing '
            'discriminating evidence, citation-integrity findings, conclusion-width labels and '
            'outcomes are human assertions bound to the challenged statements, not adjudications. '
            'A distinct challenger label is a mechanical check, not verified independence. No '
            'challenge is generated, scored or resolved, no statement is upheld or refuted, and a '
            'recorded material gap reopens targeted work without changing any statement or review.')

OUTCOMES = ('SURVIVES', 'MATERIAL_GAP', 'UNRESOLVED')
CONCLUSION_WIDTHS = ('WITHIN_CITED_EVIDENCE', 'BROADER_THAN_CITED_EVIDENCE', 'NOT_ASSESSED')
TEXT_FIELDS = ('challenge_id', 'challenger', 'challenged_at', 'alternative_explanation',
               'limitations', 'independence_declaration')
ALLOWED_FIELDS = set(TEXT_FIELDS) | {'statement_ids', 'missing_discriminating_evidence',
                                     'citation_integrity_findings', 'conclusion_width', 'outcome',
                                     'reopening', 'basis_sha256'}
MAX_ROWS = 100  # Per supplied list; a size bound, not a CPU or memory ceiling.


def challenge_basis(synthesis, statement_ids):
    """Bind a challenge to the challenged statements' current review bases."""
    targets = {row['statement_id']: row['basis_sha256'] for row in synthesis['review_targets']}
    unknown = [sid for sid in statement_ids if sid not in targets]
    if unknown:
        raise ValueError('challenge targets unknown synthesis statements: ' + ascii(unknown))
    return digest(dict(schema_version=1, challenged_statements=[
        dict(statement_id=sid, basis_sha256=targets[sid]) for sid in sorted(set(statement_ids))]))


def reviewer_labels(synthesis, statement_ids):
    """Collect reviewer, position-recorder and appraiser labels on the challenged statements."""
    ledger = {row['statement_id']: row for row in synthesis['statement_ledger']}
    targets = {row['statement_id']: row for row in synthesis['review_targets']}
    labels = set()
    for sid in statement_ids:
        statement = ledger[sid]
        if nonempty_text(statement.get('reviewer')):
            labels.add(statement['reviewer'])
        for position in statement.get('evidence_positions', []):
            labels.add(position['recorded_by'])
        for appraisal in targets[sid]['basis']['appraisals']:
            labels.add(appraisal['reviewer'])
    return labels


def _hex(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _text_list(value, field):
    if (not isinstance(value, list) or len(value) > MAX_ROWS
            or any(not nonempty_text(item) for item in value)):
        raise ValueError(field + ' must be a list of at most 100 nonempty strings')
    return value


def validate_reopening(value, work_ids):
    """Return None, 'work_package' or 'amendment'; never invent or select reopening work."""
    if value is None:
        return None
    if not isinstance(value, dict) or len(value) != 1:
        raise ValueError('reopening must be null or an object with exactly work_package_id or amendment_note')
    if 'work_package_id' in value:
        wid = value['work_package_id']
        if not nonempty_text(wid) or wid not in work_ids:
            raise ValueError('reopening work_package_id must name an existing work package')
        return 'work_package'
    if 'amendment_note' in value:
        if not nonempty_text(value['amendment_note']):
            raise ValueError('reopening amendment_note must be a nonempty string')
        return 'amendment'
    raise ValueError('reopening must be null or an object with exactly work_package_id or amendment_note')


def link_challenges(protocol, synthesis, work):
    supplied = protocol.get('challenges', [])
    if not isinstance(supplied, list):
        raise ValueError('challenges must be a list')
    statements = {row['statement_id']: row for row in synthesis['statement_ledger']}
    work_by_id = {row['work_package_id']: row for row in work}
    ledger = {}
    by_statement = {sid: [] for sid in statements}
    for row in supplied:
        if not isinstance(row, dict):
            raise ValueError('challenge must be an object')
        unknown = set(row) - ALLOWED_FIELDS
        if unknown:
            raise ValueError('challenge has unknown fields: ' + ascii(sorted(unknown)))
        for field in TEXT_FIELDS:
            if not nonempty_text(row.get(field)):
                raise ValueError('challenge requires ' + field)
        cid = row['challenge_id']
        if cid in ledger:
            raise ValueError('duplicate challenge ID')
        iso_date(row['challenged_at'], 'challenged_at')
        sids = id_list(row.get('statement_ids'), 'challenge statement_ids')
        if not sids or any(sid not in statements for sid in sids):
            raise ValueError('challenge must link to known synthesis statements')
        cited = set()
        for sid in sids:
            cited.update(statements[sid]['evidence_ids'])
        _text_list(row.get('missing_discriminating_evidence'), 'missing_discriminating_evidence')
        findings = row.get('citation_integrity_findings')
        if not isinstance(findings, list) or len(findings) > MAX_ROWS:
            raise ValueError('citation_integrity_findings must be a list of at most 100 objects')
        for finding in findings:
            if (not isinstance(finding, dict) or set(finding) != {'evidence_id', 'finding'}
                    or not nonempty_text(finding['finding']) or finding['evidence_id'] not in cited):
                raise ValueError('citation integrity finding requires an evidence_id cited by the '
                                 'challenged statements and a nonempty finding')
        if row.get('conclusion_width') not in CONCLUSION_WIDTHS:
            raise ValueError('conclusion_width must be one of ' + ', '.join(CONCLUSION_WIDTHS))
        outcome = row.get('outcome')
        if outcome not in OUTCOMES:
            raise ValueError('outcome must be one of ' + ', '.join(OUTCOMES))
        reopening_kind = validate_reopening(row.get('reopening'), work_by_id)
        if outcome == 'MATERIAL_GAP' and reopening_kind is None:
            raise ValueError('a MATERIAL_GAP outcome must name existing reopening work or an amendment note')
        if outcome == 'SURVIVES' and reopening_kind is not None:
            raise ValueError('a SURVIVES outcome must not record reopening')
        if row['challenger'] in reviewer_labels(synthesis, sids):
            raise ValueError('challenger label matches a reviewer, position recorder or appraiser label '
                             'on a challenged statement; an independent challenge requires a distinct supplied label')
        current = challenge_basis(synthesis, sids)
        if 'basis_sha256' in row:
            if not _hex(row['basis_sha256']):
                raise ValueError('challenge basis must be lowercase SHA-256 hex')
            match = 'CURRENT_SOURCE' if row['basis_sha256'] == current else 'STALE_SOURCE'
        else:
            match = 'UNBOUND_CHALLENGE'
        if reopening_kind is None:
            reopening_status = None
        elif reopening_kind == 'amendment':
            reopening_status = 'OPEN_AMENDMENT'
        elif work_by_id[row['reopening']['work_package_id']]['status'] == 'COMPLETE':
            reopening_status = 'RECORDED_COMPLETE'
        else:
            reopening_status = 'OPEN_WORK'
        ledger[cid] = dict(copy.deepcopy(row), cited_evidence_ids=sorted(cited),
                           source_match_status=match, current_basis_sha256=current,
                           reopening_status=reopening_status,
                           independence_verification='LABEL_DISTINCT_ONLY',
                           assessment='NOT_PERFORMED')
        for sid in sids:
            by_statement[sid].append(cid)
    supplied_stage = 'challenges' in protocol
    synthesis_supplied = synthesis['stage'] == 'SUPPLIED'

    def selected(predicate):
        return sorted(cid for cid, row in ledger.items() if predicate(row)) if supplied_stage else None

    return dict(schema_version=1, stage='SUPPLIED' if supplied_stage else 'NOT_SUPPLIED',
                challenge_ledger=[ledger[cid] for cid in sorted(ledger)],
                statement_challenge_links=[dict(statement_id=sid, challenge_ids=sorted(by_statement[sid]))
                                           for sid in sorted(by_statement)],
                statements_without_challenge=(sorted(sid for sid, cids in by_statement.items() if not cids)
                                              if synthesis_supplied else None),
                challenges_with_open_material_gaps=selected(
                    lambda row: row['outcome'] == 'MATERIAL_GAP'
                    and row['reopening_status'] in ('OPEN_WORK', 'OPEN_AMENDMENT')),
                unresolved_challenge_ids=selected(lambda row: row['outcome'] == 'UNRESOLVED'),
                stale_challenge_ids=selected(lambda row: row['source_match_status'] == 'STALE_SOURCE'),
                unbound_challenge_ids=selected(lambda row: row['source_match_status'] == 'UNBOUND_CHALLENGE'),
                boundary=BOUNDARY)
