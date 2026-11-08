"""Derive mechanical conclusion-readiness gates and record supplied readiness assertions without judging sufficiency."""
import copy
from challenge_links import validate_reopening
from context_links import iso_date, nonempty_text
from planning_links import digest

BOUNDARY = ('Mechanical gate ledger over supplied records plus supplied readiness assertions only. A CLOSED gate '
            'means its bookkeeping items are empty; it does not establish that evidence is sufficient, that '
            'searching was exhaustive or that a conclusion is ready, and every gate can close while the science '
            'stays unsettled. Evidence sufficiency and conclusion readiness labels are human assertions bound by '
            'hash to a gate snapshot, never mechanical conclusions; they are not adjudicated, scored or promoted. '
            'A READY assertion recorded while gates are open is a deliberate human scope closure that stays '
            'visible beside its open gates. A NOT_READY assertion with INSUFFICIENT evidence reopens targeted '
            'work without changing any statement, review or work state. Mechanical conclusion readiness stays NOT_READY.')
GATE_SCOPE = ('Closed gates are necessary mechanical bookkeeping over supplied records, not evidence sufficiency, '
              'census or conclusion readiness; open items are exact supplied IDs or input pointers.')
STATUSES = ('CLOSED', 'OPEN', 'NOT_APPLICABLE')
SUFFICIENCY_LABELS = ('SUFFICIENT', 'INSUFFICIENT', 'UNASSESSED')
READINESS_LABELS = ('READY', 'NOT_READY')
TEXT_FIELDS = ('assertion_id', 'assessor', 'assessed_at', 'scope_statement', 'rationale', 'limitations')
ALLOWED_FIELDS = set(TEXT_FIELDS) | {'evidence_sufficiency', 'conclusion_readiness', 'gates_sha256', 'reopening'}
MAX_ROWS = 100  # Per supplied list; a size bound, not a CPU or memory ceiling.


def _hex(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _gate(gate_id, status, open_items, basis):
    if status not in STATUSES:
        raise ValueError('invalid gate status')
    return dict(gate_id=gate_id, status=status, open_items=list(open_items), basis=basis)


def _checked(gate_id, open_items, basis):
    return _gate(gate_id, 'OPEN' if open_items else 'CLOSED', open_items, basis)


def _report_rows(protocol):
    """Read supplied report rows as recorded; explicit plural declarations were already validated by the workflow.

    Legacy scalar rows are not newly validated here: the workflow alone never enforced
    report rendering rules on them, and the gate must not change what `run` accepts.
    """
    rows = protocol['reports'] if isinstance(protocol['reports'], list) else []
    return [(index, row) for index, row in enumerate(rows) if isinstance(row, dict)]


def _report_identity(index, row):
    rid = row.get('report_id')
    return rid if nonempty_text(rid) else '/reports/' + str(index)


def _report_records(row):
    ids = row.get('record_ids')
    return [rid for rid in ids if isinstance(rid, str)] if isinstance(ids, list) else []


def gate_ledger(protocol, *, search_plan_audit, coverage, record_ids, screened_ids, included_ids, evidence,
                extraction_pending, context, appraisal, synthesis, challenge, work):
    """Project supplied-record bookkeeping into fixed gates; close nothing by inference."""
    rows = []
    plan = search_plan_audit
    if plan['plan_status'] == 'NOT_SUPPLIED':
        rows.append(_gate('search_plan_complete', 'NOT_APPLICABLE', [],
                          'No search plan is declared, so planned-search accounting does not apply.'))
    else:
        missing, incomplete = plan['missing_search_ids'], plan['incomplete_search_ids']
        rows.append(_checked('search_plan_complete', sorted(set(missing) | set(incomplete)),
                             'Planned searches: %d; missing: %d; incomplete: %d.'
                             % (plan['planned'], len(missing), len(incomplete))))
    unresolved = ['/searches/' + str(index) for index, row in enumerate(coverage) if not row['complete']]
    rows.append(_checked('searches_complete', unresolved,
                         'Supplied searches with completion or page issues: %d of %d.' % (len(unresolved), len(coverage))))
    pending = sorted(record_ids - screened_ids)
    rows.append(_checked('screening_complete', pending,
                         'Distinct supplied record IDs without a screening decision: %d of %d.'
                         % (len(pending), len(record_ids))))
    if 'reports' not in protocol:
        rows.append(_gate('reports_resolved', 'NOT_APPLICABLE', [],
                          'No report ledger is supplied, so report resolution does not apply.'))
        rows.append(_checked('extraction_recorded', list(extraction_pending),
                             'Title/abstract-included records without any result row: %d of %d.'
                             % (len(extraction_pending), len(included_ids))))
    else:
        reports = _report_rows(protocol)
        by_record = {}
        for index, row in reports:
            for rid in _report_records(row):
                by_record.setdefault(rid, _report_identity(index, row))
        extracted = {by_record[row['record_id']] for row in evidence if row['record_id'] in by_record}
        pending_retrieval, not_retrieved, unrecognized, pending_assessment, without_extraction = [], [], [], [], []
        for index, row in reports:
            identity = _report_identity(index, row)
            retrieval, decision = row.get('retrieval'), row.get('decision', 'pending')
            if retrieval == 'pending':
                pending_retrieval.append(identity)
            elif retrieval == 'not_retrieved':
                not_retrieved.append(identity)
            elif retrieval != 'retrieved':
                unrecognized.append(identity)
            elif decision not in ('include', 'exclude'):
                pending_assessment.append(identity)
            if decision == 'include' and identity not in extracted:
                without_extraction.append(identity)
        unmapped = sorted(set(included_ids) - set(by_record))
        items = sorted(set(pending_retrieval) | set(not_retrieved) | set(unrecognized) | set(pending_assessment)
                       | set(without_extraction) | set(unmapped))
        basis = ('Supplied reports: %d; pending retrieval: %d; not retrieved: %d; pending full-text '
                 'assessment: %d; included without extraction: %d; included records without a report '
                 'mapping: %d.' % (len(reports), len(pending_retrieval), len(not_retrieved),
                                   len(pending_assessment), len(without_extraction), len(unmapped)))
        if unrecognized:
            basis = basis[:-1] + '; unrecognized retrieval state: %d.' % len(unrecognized)
        rows.append(_checked('reports_resolved', items, basis))
        rows.append(_gate('extraction_recorded', 'NOT_APPLICABLE', [],
                          'A report ledger is supplied, so record-level extraction bookkeeping belongs to reports_resolved.'))
    statements = synthesis['statement_ledger']
    if synthesis['stage'] != 'SUPPLIED':
        rows.append(_gate('cited_results_appraised', 'OPEN', [],
                          'No synthesis statements are supplied, so no cited result can be checked for a recorded appraisal.'))
        rows.append(_gate('statements_reviewed_current', 'OPEN', [],
                          'No synthesis statements are supplied; a conclusion needs reviewed, current statements.'))
        rows.append(_gate('results_cited', 'OPEN', [],
                          'No synthesis statements are supplied, so no extracted result is cited by a statement.'))
        rows.append(_gate('challenges_recorded', 'OPEN', [],
                          'No synthesis statements are supplied, so no statement has a recorded independent challenge.'))
    else:
        cited = sorted({eid for row in statements for eid in row['evidence_ids']})
        unappraised = [eid for eid in cited if eid in set(appraisal['evidence_without_recorded_appraisal'])]
        rows.append(_checked('cited_results_appraised', unappraised,
                             'Results cited by synthesis statements without a recorded appraisal: %d of %d.'
                             % (len(unappraised), len(cited))))
        pending_reviews, stale_reviews = synthesis['pending_statement_ids'], synthesis['stale_statement_ids']
        rows.append(_checked('statements_reviewed_current', sorted(set(pending_reviews) | set(stale_reviews)),
                             'Supplied statements: %d; pending review: %d; stale review: %d.'
                             % (len(statements), len(pending_reviews), len(stale_reviews))))
        uncited = list(synthesis['evidence_without_statement_citation'])
        rows.append(_checked('results_cited', uncited,
                             'Extracted results cited by no statement: %d of %d.' % (len(uncited), len(evidence))))
        without_challenge = list(challenge['statements_without_challenge'])
        rows.append(_checked('challenges_recorded', without_challenge,
                             'Supplied statements without a recorded independent challenge: %d of %d.'
                             % (len(without_challenge), len(statements))))
    if challenge['stage'] != 'SUPPLIED':
        rows.append(_gate('challenges_resolved', 'OPEN', [],
                          'No challenge records are supplied, so no challenge resolution can be checked; '
                          'absence is not resolution.'))
    else:
        gaps = challenge['challenges_with_open_material_gaps']
        unresolved_challenges = challenge['unresolved_challenge_ids']
        stale_challenges = challenge['stale_challenge_ids']
        rows.append(_checked('challenges_resolved',
                             sorted(set(gaps) | set(unresolved_challenges) | set(stale_challenges)),
                             'Recorded challenges: %d; open material gaps: %d; unresolved: %d; stale statement '
                             'bindings: %d.' % (len(challenge['challenge_ledger']), len(gaps),
                                                len(unresolved_challenges), len(stale_challenges))))
    pending_contexts = list(context['review_pending'])
    rows.append(_checked('contexts_reviewed', pending_contexts,
                         'Recorded contexts pending review: %d of %d.'
                         % (len(pending_contexts), len(context['context_ledger']))))
    unfinished = sorted(row['work_package_id'] for row in work if row['status'] in ('PLANNED', 'IN_PROGRESS'))
    rows.append(_checked('work_complete', unfinished,
                         'Work packages still PLANNED or IN_PROGRESS: %d of %d.' % (len(unfinished), len(work))))
    return rows


def link_readiness(protocol, *, search_plan_audit, coverage, record_ids, screened_ids, included_ids, evidence,
                   extraction_pending, context, appraisal, synthesis, challenge, work):
    rows = gate_ledger(protocol, search_plan_audit=search_plan_audit, coverage=coverage, record_ids=record_ids,
                       screened_ids=screened_ids, included_ids=included_ids, evidence=evidence,
                       extraction_pending=extraction_pending, context=context, appraisal=appraisal,
                       synthesis=synthesis, challenge=challenge, work=work)
    gates_sha256 = digest(rows)
    open_ids = [row['gate_id'] for row in rows if row['status'] == 'OPEN']
    supplied = protocol.get('readiness_assertions', [])
    if not isinstance(supplied, list):
        raise ValueError('readiness_assertions must be a list')
    if len(supplied) > MAX_ROWS:
        raise ValueError('readiness_assertions must list at most 100 rows')
    work_by_id = {row['work_package_id']: row for row in work}
    ledger = {}
    for row in supplied:
        if not isinstance(row, dict):
            raise ValueError('readiness assertion must be an object')
        unknown = set(row) - ALLOWED_FIELDS
        if unknown:
            raise ValueError('readiness assertion has unknown fields: ' + ascii(sorted(unknown)))
        for field in TEXT_FIELDS:
            if not nonempty_text(row.get(field)):
                raise ValueError('readiness assertion requires ' + field)
        aid = row['assertion_id']
        if aid in ledger:
            raise ValueError('duplicate readiness assertion ID')
        iso_date(row['assessed_at'], 'assessed_at')
        sufficiency = row.get('evidence_sufficiency')
        if sufficiency not in SUFFICIENCY_LABELS:
            raise ValueError('evidence_sufficiency must be one of ' + ', '.join(SUFFICIENCY_LABELS))
        readiness = row.get('conclusion_readiness')
        if readiness not in READINESS_LABELS:
            raise ValueError('conclusion_readiness must be one of ' + ', '.join(READINESS_LABELS))
        if not _hex(row.get('gates_sha256')):
            raise ValueError('gates_sha256 must be lowercase SHA-256 hex')
        reopening_kind = validate_reopening(row.get('reopening'), work_by_id)
        if readiness == 'NOT_READY' and sufficiency == 'INSUFFICIENT' and reopening_kind is None:
            raise ValueError('a NOT_READY assertion with INSUFFICIENT evidence must name existing reopening work '
                             'or an amendment note')
        if row['gates_sha256'] == gates_sha256:
            match, open_at_assertion, open_scope = 'CURRENT_GATES', list(open_ids), 'RECOMPUTED_FROM_CURRENT_LEDGER'
        else:
            match, open_at_assertion, open_scope = 'STALE_GATES', None, 'UNKNOWN_STALE_GATES'
        if reopening_kind is None:
            reopening_status = None
        elif reopening_kind == 'amendment':
            reopening_status = 'OPEN_AMENDMENT'
        elif work_by_id[row['reopening']['work_package_id']]['status'] == 'COMPLETE':
            reopening_status = 'RECORDED_COMPLETE'
        else:
            reopening_status = 'OPEN_WORK'
        ledger[aid] = dict(copy.deepcopy(row), source_match_status=match, current_gates_sha256=gates_sha256,
                           open_gates_at_assertion=open_at_assertion, open_gates_scope=open_scope,
                           ready_with_open_gates=(None if open_at_assertion is None
                                                  else readiness == 'READY' and bool(open_at_assertion)),
                           reopening_status=reopening_status,
                           assertion_scope='SUPPLIED_HUMAN_ASSERTION_BOUND_TO_GATE_SNAPSHOT',
                           assessment='NOT_PERFORMED')
    supplied_stage = 'readiness_assertions' in protocol

    def selected(predicate):
        return sorted(aid for aid, row in ledger.items() if predicate(row)) if supplied_stage else None

    return dict(schema_version=1, stage='SUPPLIED' if supplied_stage else 'NOT_SUPPLIED',
                gate_ledger=rows, gates_sha256=gates_sha256, open_gate_ids=open_ids,
                closed_gate_ids=[row['gate_id'] for row in rows if row['status'] == 'CLOSED'],
                not_applicable_gate_ids=[row['gate_id'] for row in rows if row['status'] == 'NOT_APPLICABLE'],
                mechanical_conclusion_readiness='NOT_READY', gate_scope=GATE_SCOPE,
                assertion_ledger=[ledger[aid] for aid in sorted(ledger)],
                current_assertion_ids=selected(lambda row: row['source_match_status'] == 'CURRENT_GATES'),
                stale_assertion_ids=selected(lambda row: row['source_match_status'] == 'STALE_GATES'),
                boundary=BOUNDARY)
