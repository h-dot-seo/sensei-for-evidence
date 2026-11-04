"""Read-only supplied human eligibility positions for exact report-study pairs."""
import copy
import datetime
import re

from report_links import report_study_ids
from report_review_links import prepare_targets as prepare_report_targets, _digest, _hash, _text

REVIEW_FIELDS = {'review_id', 'report_id', 'study_id', 'reviewer', 'reviewed_at',
                'decision', 'rationale', 'reviewed_locator', 'reviewed_source_ids',
                'source_basis_sha256'}
BOUNDARY = (
    'Supplied human positions on exact report-study pairs only, not canonical study selection. '
    'Memberships exist only where currently declared on included retrieved reports. Retained '
    'orphan assertions are unverified supplied retrospective context, not proof of valid history '
    'or a pending selection queue. Source hashes bind supplied context, not document bytes, '
    'authenticity, reading or eligibility correctness. Reviewed source IDs are literal human '
    'selections; differing sets do not establish different coverage. Reviewer identity, '
    'authentication and independence are not established. No voting, consensus, adjudication, '
    'study identity or independence is inferred. Reviews never alter canonical reports, '
    'memberships, results, counts or work. An exclude-position/result-presence cue is a literal ' 
    'comparison, not an invalid-result verdict or a filtering instruction. Stale assertions are never refreshed automatically. '
    'Locators are inert text; no opening, fetching or execution occurs.'
)


def _validate_reviews(protocol, reports):
    reviews = protocol.get('report_study_reviews', [])
    if not isinstance(reviews, list):
        raise ValueError('report_study_reviews must be a list')
    ids, triples = set(), set()
    for row in reviews:
        if not isinstance(row, dict) or set(row) != REVIEW_FIELDS:
            raise ValueError('report study review has unknown or missing fields')
        if any(not _text(row[key]) for key in REVIEW_FIELDS - {'reviewed_source_ids'}):
            raise ValueError('report study review scalar fields must be nonblank literal strings')
        if row['report_id'] not in reports:
            raise ValueError('unknown report study review report_id')
        sources = row['reviewed_source_ids']
        if (not isinstance(sources, list) or not sources or any(not _text(s) for s in sources)
                or len(sources) != len(set(sources))):
            raise ValueError('reviewed_source_ids must be nonempty unique literal strings')
        triple = (row['report_id'], row['study_id'], row['reviewer'])
        if row['review_id'] in ids or triple in triples:
            raise ValueError('duplicate report study review_id or report/study/reviewer tuple')
        if row['decision'] not in ('include', 'exclude', 'unclear'):
            raise ValueError('report study review decision must be include, exclude or unclear')
        if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', row['reviewed_at']) is None:
            raise ValueError('report study reviewed_at must be YYYY-MM-DD')
        try:
            datetime.date.fromisoformat(row['reviewed_at'])
        except ValueError as error:
            raise ValueError('invalid report study reviewed_at date') from error
        if not _hash(row['source_basis_sha256']):
            raise ValueError('report study source_basis_sha256 must be 64 lowercase hex characters')
        ids.add(row['review_id'])
        triples.add(triple)
    return reviews


def prepare_targets(protocol, bibliographic_collection=None):
    """Validate complete supplied context, retaining only explicitly asserted orphans."""
    prepared = prepare_report_targets(protocol, bibliographic_collection)
    reports = {row['report_id']: row for row in prepared['report_targets']}
    reviews = _validate_reviews(protocol, reports)
    pairs, pointers = [], {}
    for target in prepared['report_targets']:
        row = target['recorded_report']
        for index, sid in enumerate(report_study_ids(row)):
            pair = (target['report_id'], sid)
            pairs.append(pair)
            pointers[pair] = (target['input_pointer'] + f'/study_ids/{index}' if 'study_ids' in row
                              else target['input_pointer'] + '/study_id')
    seen = set(pairs)
    for row in reviews:
        pair = (row['report_id'], row['study_id'])
        if pair not in seen:
            pairs.append(pair)
            seen.add(pair)
    report_for_record = {rid: row['report_id'] for row in prepared['report_targets']
                         for rid in row['recorded_report']['record_ids']}
    results = {}
    for row in protocol.get('evidence', []):
        pair = (report_for_record.get(row['record_id']), row['study_id'])
        results.setdefault(pair, []).append(row.get('evidence_id', row['record_id']))
    targets = []
    for pair in pairs:
        rid, sid = pair
        report = reports[rid]
        current = pair in pointers
        basis = dict(schema_version=1, scope='report_study_supplied_eligibility_context',
                     report_id=rid, study_id=sid,
                     report_source_basis_sha256=report['source_basis_sha256'],
                     membership_currently_declared=current)
        evidence_ids = sorted(results.get(pair, []))
        targets.append(dict(report_id=rid, study_id=sid, input_pointer=pointers.get(pair),
                            membership_currently_declared=current, source_basis=basis,
                            source_basis_sha256=_digest(basis), evidence_ids=evidence_ids,
                            has_result_rows=bool(evidence_ids), retrieval=report['retrieval'],
                            source_binding_state=report['source_binding_state']))
    by_pair = {(row['report_id'], row['study_id']): row for row in targets}
    source_reports = {row['source']['source_id']: row['source']['report_id']
                      for row in prepared['source_ledger']}
    for row in reviews:
        target = by_pair[(row['report_id'], row['study_id'])]
        matching = row['source_basis_sha256'] == target['source_basis_sha256']
        for sid in row['reviewed_source_ids']:
            if sid in source_reports and source_reports[sid] != row['report_id']:
                raise ValueError('reviewed source ID belongs to another report')
            if matching and sid not in source_reports:
                raise ValueError('current report study review requires existing same-report reviewed source IDs')
        if matching and not target['membership_currently_declared']:
            raise ValueError('current report study review requires a currently declared membership')
    prepared.update(stage='SUPPLIED' if 'report_study_reviews' in protocol else 'NOT_SUPPLIED',
                    review_stage='SUPPLIED' if 'report_study_reviews' in protocol else 'NOT_SUPPLIED',
                    membership_targets=targets)
    return prepared


def _counts(result):
    targets = result['membership_targets']
    current = sum(row['source_match_status'] == 'CURRENT_SOURCE' for row in result['review_ledger'])
    active = sum(row['membership_currently_declared'] for row in targets)
    return dict(reports=len(result['report_targets']), pair_views=len(targets),
                current_memberships=active, orphan_pair_views=len(targets) - active,
                source_descriptors=len(result['source_ledger']), review_assertions=len(result['review_ledger']),
                current_source_reviews=current, stale_source_reviews=len(result['review_ledger']) - current,
                orphan_review_assertions=len(result['orphan_review_assertions']),
                current_memberships_with_review_cues=len(result['current_memberships_with_review_cues']))


def link_report_study_reviews(protocol, bibliographic_collection=None):
    """Project literal positions without adjudicating or filtering any evidence."""
    prepared = prepare_targets(protocol, bibliographic_collection)
    targets = {(row['report_id'], row['study_id']): row for row in prepared['membership_targets']}
    sources = {row['source']['source_id'] for row in prepared['source_ledger']}
    ledger, grouped = [], {}
    for index, row in enumerate(protocol.get('report_study_reviews', [])):
        pair = (row['report_id'], row['study_id'])
        target = targets[pair]
        item = dict(review=copy.deepcopy(row), input_pointer=f'/report_study_reviews/{index}',
                    current_source_basis_sha256=target['source_basis_sha256'],
                    source_match_status=('CURRENT_SOURCE' if row['source_basis_sha256'] == target['source_basis_sha256']
                                         else 'STALE_SOURCE'),
                    membership_currently_declared=target['membership_currently_declared'],
                    unresolved_reviewed_source_ids=[sid for sid in row['reviewed_source_ids'] if sid not in sources])
        ledger.append(item)
        grouped.setdefault(pair, []).append(item)
    memberships, queue = [], []
    for pair, target in targets.items():
        items = grouped.get(pair, [])
        current = [item['review'] for item in items if item['source_match_status'] == 'CURRENT_SOURCE']
        stale = [item['review'] for item in items if item['source_match_status'] == 'STALE_SOURCE']
        decisions = sorted({row['decision'] for row in current})
        source_sets = sorted({tuple(sorted(row['reviewed_source_ids'])) for row in current})
        unresolved = sorted({sid for item in items for sid in item['unresolved_reviewed_source_ids']})
        cues = []
        if not target['membership_currently_declared']:
            cues.append('MEMBERSHIP_NOT_CURRENTLY_DECLARED')
        elif not current:
            cues.append('NO_CURRENT_SOURCE_REVIEW')
        if target['retrieval'] != 'retrieved':
            cues.append('REPORT_NOT_RETRIEVED' if target['retrieval'] == 'not_retrieved' else 'RETRIEVAL_PENDING')
        if target['source_binding_state'] != 'SUPPLIED_DIGESTS':
            cues.append(target['source_binding_state'])
        if stale:
            cues.append('STALE_REVIEW_ASSERTIONS')
        if 'unclear' in decisions:
            cues.append('UNCLEAR_CURRENT_POSITION')
        if len(decisions) > 1:
            cues.append('DIFFERING_CURRENT_POSITIONS')
        if 'exclude' in decisions and target['has_result_rows']:
            cues.append('CURRENT_EXCLUDE_POSITION_WITH_RESULT_ROWS')
        if len(source_sets) > 1:
            cues.append('DIFFERING_CURRENT_REVIEWED_SOURCE_ID_SETS')
        if unresolved:
            cues.append('UNRESOLVED_REVIEWED_SOURCE_IDS')
        memberships.append(dict(report_id=pair[0], study_id=pair[1], input_pointer=target['input_pointer'],
                                membership_currently_declared=target['membership_currently_declared'],
                                retrieval=target['retrieval'], source_binding_state=target['source_binding_state'],
                                review_ids=[item['review']['review_id'] for item in items],
                                current_review_ids=[row['review_id'] for row in current],
                                stale_review_ids=[row['review_id'] for row in stale],
                                current_decisions=decisions, stale_decisions=sorted({row['decision'] for row in stale}),
                                current_reviewer_labels=sorted({row['reviewer'] for row in current}),
                                stale_reviewer_labels=sorted({row['reviewer'] for row in stale}),
                                current_reviewed_source_id_sets=[list(ids) for ids in source_sets],
                                unresolved_reviewed_source_ids=unresolved,
                                evidence_ids=copy.deepcopy(target['evidence_ids']),
                                has_result_rows=target['has_result_rows'], comparison_cues=cues))
        if cues and target['membership_currently_declared']:
            queue.append(dict(report_id=pair[0], study_id=pair[1]))
    result = dict(**prepared, review_ledger=ledger, membership_review_ledger=memberships,
                  current_memberships_with_review_cues=queue,
                  orphan_review_assertions=[copy.deepcopy(row) for row in ledger if not row['membership_currently_declared']],
                  canonical_study_selection='NOT_MODELED', eligibility_correctness='NOT_ASSESSED',
                  document_bytes_verification='NOT_PERFORMED', source_authenticity='NOT_VERIFIED',
                  reviewer_identity_verification='NOT_ESTABLISHED', reviewer_authentication='NOT_ESTABLISHED',
                  reviewer_independence='NOT_ESTABLISHED', study_identity_verification='NOT_ESTABLISHED',
                  study_independence='NOT_ESTABLISHED', adjudication='NOT_PERFORMED', boundary=BOUNDARY)
    result['counts'] = _counts(result)
    return result
