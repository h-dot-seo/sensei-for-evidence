"""Supplied eligibility positions on described candidate studies, never selection."""
import copy
import datetime
import re

from report_study_inventory_links import link_report_study_inventory
from report_review_links import _digest, _hash, _text

REVIEW_FIELDS = {'review_id', 'report_id', 'study_id', 'reviewer', 'reviewed_at',
                'decision', 'rationale', 'reviewed_locator', 'reviewed_inventory_ids',
                'reviewed_source_ids', 'source_basis_sha256'}
BOUNDARY = (
    'Supplied human eligibility positions on described candidate report-study pairs only. '
    'Descriptions and positions never establish canonical inclusion or membership, study identity, '
    'independence, completeness, reading or eligibility correctness. All separately supplied '
    'positions are retained without voting, quorum, consensus or adjudication; reviewer identity, '
    'authentication and independence are not established. Current review context does not upgrade '
    'stale inventory assertions or unbound document bytes. Hashes bind supplied context and all '
    'ordered same-pair inventory assertions, not document bytes, authenticity or correctness. '
    'Reviewed inventory and source IDs are explicit human selections, not inferred coverage. '
    'Retained orphan reviews are unverified retrospective context, not proof of valid history '
    'or a fresh review queue. Assertions are never renewed automatically. Reviews never alter '
    'reports, memberships, evidence, counts or work. Locators are inert text; no fetching or '
    'execution occurs.'
)


def _validate_reviews(protocol, reports):
    reviews = protocol.get('report_study_inventory_reviews', [])
    if not isinstance(reviews, list):
        raise ValueError('report_study_inventory_reviews must be a list')
    ids, triples = set(), set()
    list_fields = {'reviewed_inventory_ids', 'reviewed_source_ids'}
    for row in reviews:
        if not isinstance(row, dict) or set(row) != REVIEW_FIELDS:
            raise ValueError('report study inventory review has unknown or missing fields')
        if any(not _text(row[key]) for key in REVIEW_FIELDS - list_fields):
            raise ValueError('report study inventory review scalar fields must be nonblank literal strings')
        if row['report_id'] not in reports:
            raise ValueError('unknown report study inventory review report_id')
        for key in list_fields:
            values = row[key]
            if (not isinstance(values, list) or not values or any(not _text(s) for s in values)
                    or len(values) != len(set(values))):
                raise ValueError(key + ' must be nonempty unique literal strings')
        triple = (row['report_id'], row['study_id'], row['reviewer'])
        if row['review_id'] in ids or triple in triples:
            raise ValueError('duplicate inventory review_id or report/study/reviewer tuple')
        if row['decision'] not in ('include', 'exclude', 'unclear'):
            raise ValueError('report study inventory review decision must be include, exclude or unclear')
        if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', row['reviewed_at']) is None:
            raise ValueError('report study inventory reviewed_at must be YYYY-MM-DD')
        try:
            datetime.date.fromisoformat(row['reviewed_at'])
        except ValueError as error:
            raise ValueError('invalid report study inventory reviewed_at date') from error
        if not _hash(row['source_basis_sha256']):
            raise ValueError('report study inventory review source_basis_sha256 must be 64 lowercase hex characters')
        ids.add(row['review_id'])
        triples.add(triple)
    return reviews


def prepare_targets(protocol, bibliographic_collection=None):
    """Validate all supplied context and retain explicitly referenced orphan pairs."""
    prepared = link_report_study_inventory(protocol, bibliographic_collection)
    reports = {row['report_id']: row for row in prepared['report_targets']}
    reviews = _validate_reviews(protocol, reports)
    assertions = {}
    for row in protocol.get('report_study_inventory', []):
        assertions.setdefault((row['report_id'], row['study_id']), []).append(row)
    pairs = dict.fromkeys(assertions)
    for row in reviews:
        pairs.setdefault((row['report_id'], row['study_id']), None)
    inventory_pairs = {row['inventory_id']: (row['report_id'], row['study_id'])
                       for rows in assertions.values() for row in rows}
    source_reports = {row['source']['source_id']: row['source']['report_id']
                      for row in prepared['source_ledger']}
    targets = []
    for rid, sid in pairs:
        report = reports[rid]
        described = (rid, sid) in assertions
        rows = assertions.get((rid, sid), [])
        basis = dict(schema_version=1, scope='report_study_inventory_supplied_eligibility_context',
                     report_id=rid, study_id=sid,
                     report_source_basis_sha256=report['source_basis_sha256'],
                     inventory_currently_described=described,
                     report_study_inventory_assertions=copy.deepcopy(rows))
        targets.append(dict(report_id=rid, study_id=sid, inventory_currently_described=described,
                            inventory_ids=[row['inventory_id'] for row in rows],
                            source_basis=basis, source_basis_sha256=_digest(basis),
                            retrieval=report['retrieval'], source_binding_state=report['source_binding_state']))
    by_pair = {(row['report_id'], row['study_id']): row for row in targets}
    for row in reviews:
        pair = (row['report_id'], row['study_id'])
        target = by_pair[pair]
        matching = row['source_basis_sha256'] == target['source_basis_sha256']
        for iid in row['reviewed_inventory_ids']:
            if iid in inventory_pairs and inventory_pairs[iid] != pair:
                raise ValueError('reviewed inventory ID belongs to another report-study pair')
            if matching and iid not in inventory_pairs:
                raise ValueError('current inventory review requires existing same-pair reviewed inventory IDs')
        for sid in row['reviewed_source_ids']:
            if sid in source_reports and source_reports[sid] != row['report_id']:
                raise ValueError('reviewed source ID belongs to another report')
            if matching and sid not in source_reports:
                raise ValueError('current inventory review requires existing same-report reviewed source IDs')
        if matching and not target['inventory_currently_described']:
            raise ValueError('current inventory review requires a currently described candidate pair')
    # Keep inventory status separate from eligibility-review context and stage.
    prepared['inventory_candidate_targets'] = prepared.pop('candidate_targets')
    stage = 'SUPPLIED' if 'report_study_inventory_reviews' in protocol else 'NOT_SUPPLIED'
    prepared.update(stage=stage, review_stage=stage, candidate_targets=targets)
    return prepared


def _counts(result):
    targets = result['candidate_targets']
    current = sum(row['source_match_status'] == 'CURRENT_SOURCE' for row in result['review_ledger'])
    described = sum(row['inventory_currently_described'] for row in targets)
    return dict(reports=len(result['report_targets']), pair_views=len(targets),
                described_candidates=described, orphan_pair_views=len(targets) - described,
                source_descriptors=len(result['source_ledger']), inventory_assertions=len(result['inventory_ledger']),
                review_assertions=len(result['review_ledger']), current_source_reviews=current,
                stale_source_reviews=len(result['review_ledger']) - current,
                orphan_review_assertions=len(result['orphan_review_assertions']),
                current_candidates_with_review_cues=len(result['current_candidates_with_review_cues']))


def link_report_study_inventory_reviews(protocol, bibliographic_collection=None):
    """Project human positions, preserving the separate inventory source status."""
    prepared = prepare_targets(protocol, bibliographic_collection)
    targets = {(row['report_id'], row['study_id']): row for row in prepared['candidate_targets']}
    sources = {row['source']['source_id'] for row in prepared['source_ledger']}
    inventory = {row['inventory']['inventory_id']: row for row in prepared['inventory_ledger']}
    ledger, grouped = [], {}
    for index, row in enumerate(protocol.get('report_study_inventory_reviews', [])):
        pair = (row['report_id'], row['study_id'])
        target = targets[pair]
        item = dict(review=copy.deepcopy(row), input_pointer=f'/report_study_inventory_reviews/{index}',
                    current_source_basis_sha256=target['source_basis_sha256'],
                    source_match_status=('CURRENT_SOURCE' if row['source_basis_sha256'] == target['source_basis_sha256']
                                         else 'STALE_SOURCE'),
                    inventory_currently_described=target['inventory_currently_described'],
                    unresolved_reviewed_inventory_ids=[iid for iid in row['reviewed_inventory_ids'] if iid not in inventory],
                    unresolved_reviewed_source_ids=[sid for sid in row['reviewed_source_ids'] if sid not in sources],
                    reviewed_inventory_source_status=[dict(inventory_id=iid, source_match_status=inventory[iid]['source_match_status'])
                                                      for iid in row['reviewed_inventory_ids'] if iid in inventory])
        ledger.append(item)
        grouped.setdefault(pair, []).append(item)
    candidates, queue = [], []
    for pair, target in targets.items():
        items = grouped.get(pair, [])
        current = [item['review'] for item in items if item['source_match_status'] == 'CURRENT_SOURCE']
        stale = [item['review'] for item in items if item['source_match_status'] == 'STALE_SOURCE']
        decisions = sorted({row['decision'] for row in current})
        source_sets = sorted({tuple(sorted(row['reviewed_source_ids'])) for row in current})
        inventory_sets = sorted({tuple(sorted(row['reviewed_inventory_ids'])) for row in current})
        unresolved_sources = sorted({sid for item in items for sid in item['unresolved_reviewed_source_ids']})
        unresolved_inventory = sorted({iid for item in items for iid in item['unresolved_reviewed_inventory_ids']})
        cues = []
        if not target['inventory_currently_described']:
            cues.append('INVENTORY_NOT_CURRENTLY_DESCRIBED')
        elif not current:
            cues.append('NO_CURRENT_SOURCE_REVIEW')
        if target['retrieval'] != 'retrieved':
            cues.append('REPORT_NOT_RETRIEVED' if target['retrieval'] == 'not_retrieved' else 'RETRIEVAL_PENDING')
        if target['source_binding_state'] != 'SUPPLIED_DIGESTS':
            cues.append(target['source_binding_state'])
        if stale:
            cues.append('STALE_REVIEW_ASSERTIONS')
        if any(inventory[iid]['source_match_status'] == 'STALE_SOURCE' for iid in target['inventory_ids']):
            cues.append('STALE_INVENTORY_ASSERTIONS')
        if 'unclear' in decisions:
            cues.append('UNCLEAR_CURRENT_POSITION')
        if len(decisions) > 1:
            cues.append('DIFFERING_CURRENT_POSITIONS')
        if len(source_sets) > 1:
            cues.append('DIFFERING_CURRENT_REVIEWED_SOURCE_ID_SETS')
        if len(inventory_sets) > 1:
            cues.append('DIFFERING_CURRENT_REVIEWED_INVENTORY_ID_SETS')
        if unresolved_sources:
            cues.append('UNRESOLVED_REVIEWED_SOURCE_IDS')
        if unresolved_inventory:
            cues.append('UNRESOLVED_REVIEWED_INVENTORY_IDS')
        candidates.append(dict(report_id=pair[0], study_id=pair[1],
                               inventory_currently_described=target['inventory_currently_described'],
                               inventory_ids=copy.deepcopy(target['inventory_ids']),
                               retrieval=target['retrieval'], source_binding_state=target['source_binding_state'],
                               review_ids=[item['review']['review_id'] for item in items],
                               current_review_ids=[row['review_id'] for row in current],
                               stale_review_ids=[row['review_id'] for row in stale],
                               current_decisions=decisions, stale_decisions=sorted({row['decision'] for row in stale}),
                               current_reviewer_labels=sorted({row['reviewer'] for row in current}),
                               stale_reviewer_labels=sorted({row['reviewer'] for row in stale}),
                               current_reviewed_source_id_sets=[list(ids) for ids in source_sets],
                               current_reviewed_inventory_id_sets=[list(ids) for ids in inventory_sets],
                               unresolved_reviewed_source_ids=unresolved_sources,
                               unresolved_reviewed_inventory_ids=unresolved_inventory,
                               comparison_cues=cues))
        if cues and target['inventory_currently_described']:
            queue.append(dict(report_id=pair[0], study_id=pair[1]))
    # Replace inventory-only boundary and explicitly separate its non-assessment claim.
    prepared.pop('boundary', None)
    prepared.pop('counts', None)
    prepared.pop('eligibility_assessment', None)
    prepared.update(review_ledger=ledger, candidate_review_ledger=candidates,
                    current_candidates_with_review_cues=queue,
                    orphan_review_assertions=[copy.deepcopy(row) for row in ledger if not row['inventory_currently_described']],
                    canonical_study_selection='NOT_MODELED', eligibility_correctness='NOT_ASSESSED',
                    document_bytes_verification='NOT_PERFORMED', source_authenticity='NOT_VERIFIED',
                    reviewer_identity_verification='NOT_ESTABLISHED', reviewer_authentication='NOT_ESTABLISHED',
                    reviewer_independence='NOT_ESTABLISHED', study_identity_verification='NOT_ESTABLISHED',
                    study_independence='NOT_ESTABLISHED', adjudication='NOT_PERFORMED', boundary=BOUNDARY)
    prepared['counts'] = _counts(prepared)
    return prepared
