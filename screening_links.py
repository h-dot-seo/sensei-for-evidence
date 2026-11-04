"""Link supplied screening assertions without adjudicating canonical decisions.

Pure supplied-data helpers: no workflow imports, retrieval or locator following.
"""
import copy
import datetime
import hashlib
import re

from json_io import canonical_json_bytes

BOUNDARY = (
    'Supplied title/abstract review assertions only; reviewer identity and independence are not established. '
    'Matching hashes bind supplied context, not source authenticity or eligibility correctness. '
    'Stale assertions are retained and never renewed automatically. No majority, consensus or adjudication '
    'is inferred. Reviews never alter canonical screening, PRISMA counts, evidence or conclusion readiness. '
    'Locators are inert supplied text; no retrieval or code execution occurs.'
)
REVIEW_FIELDS = {'review_id', 'record_id', 'reviewer', 'reviewed_at', 'decision',
                 'rationale', 'source_locator', 'source_basis_sha256'}


def _digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def prepare_targets(protocol, bibliographic_collection=None):
    """Build detached source targets from a validated protocol in linear catalog space."""
    contexts, occurrences = [], {}
    for index, search in enumerate(protocol['searches']):
        context_digest = _digest(search)
        contexts.append(dict(search_index=index, input_pointer=f'/searches/{index}',
                             search_context_sha256=context_digest, search=copy.deepcopy(search)))
        for record_index, rid in enumerate(search['record_ids']):
            occurrences.setdefault(rid, []).append(dict(
                input_pointer=f'/searches/{index}/record_ids/{record_index}',
                search_index=index, record_index=record_index,
                search_context_sha256=context_digest))
    mapped = {}
    if bibliographic_collection is not None:
        for row in bibliographic_collection['row_ledger']:
            resolution = row['resolution']
            if resolution['disposition'] != 'do_not_promote':
                mapped.setdefault(resolution['record_id'], []).append(row)
    targets = []
    for rid in sorted(occurrences):
        basis = dict(schema_version=1, scope='title_abstract_supplied_context', record_id=rid,
                     question=copy.deepcopy(protocol['question']),
                     inclusion_criteria=copy.deepcopy(protocol['inclusion_criteria']),
                     exclusion_criteria=copy.deepcopy(protocol['exclusion_criteria']),
                     occurrences=occurrences[rid], bibliographic_rows=copy.deepcopy(mapped.get(rid, [])))
        targets.append(dict(record_id=rid, source_basis=basis, source_basis_sha256=_digest(basis)))
    return dict(source_contexts=contexts, record_targets=targets)


def link_screening_reviews(protocol, bibliographic_collection=None):
    """Validate exact assertions and expose comparison cues, never decisions."""
    prepared = prepare_targets(protocol, bibliographic_collection)
    targets = {row['record_id']: row for row in prepared['record_targets']}
    supplied = 'screening_reviews' in protocol
    reviews = protocol.get('screening_reviews', [])
    if not isinstance(reviews, list):
        raise ValueError('screening_reviews must be a list')
    canonical = {row['record_id']: row for row in protocol['screening']}
    seen_ids, seen_pairs, ledger, grouped = set(), set(), [], {}
    for index, row in enumerate(reviews):
        if not isinstance(row, dict) or set(row) != REVIEW_FIELDS:
            raise ValueError('screening review has unknown or missing fields')
        if any(not isinstance(row[key], str) or not row[key].strip() for key in REVIEW_FIELDS):
            raise ValueError('screening review fields must be nonblank literal strings')
        rid = row['record_id']
        if rid not in targets:
            raise ValueError('unknown screening review record_id')
        pair = (rid, row['reviewer'])
        if row['review_id'] in seen_ids or pair in seen_pairs:
            raise ValueError('duplicate screening review_id or record/reviewer pair')
        if row['decision'] not in ('include', 'exclude', 'unclear'):
            raise ValueError('screening review decision must be include, exclude or unclear')
        if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', row['reviewed_at']) is None:
            raise ValueError('screening reviewed_at must be YYYY-MM-DD')
        try:
            datetime.date.fromisoformat(row['reviewed_at'])
        except ValueError as error:
            raise ValueError('invalid screening reviewed_at date') from error
        if re.fullmatch(r'[0-9a-f]{64}', row['source_basis_sha256']) is None:
            raise ValueError('screening source_basis_sha256 must be 64 lowercase hex characters')
        seen_ids.add(row['review_id'])
        seen_pairs.add(pair)
        current_digest = targets[rid]['source_basis_sha256']
        recorded = canonical.get(rid)
        item = dict(review=copy.deepcopy(row), input_pointer=f'/screening_reviews/{index}',
                    source_match_status='CURRENT_SOURCE' if row['source_basis_sha256'] == current_digest else 'STALE_SOURCE',
                    current_source_basis_sha256=current_digest,
                    matches_recorded_decision=None if recorded is None or row['decision'] == 'unclear'
                    else row['decision'] == recorded['decision'])
        ledger.append(item)
        grouped.setdefault(rid, []).append(item)
    records, cue_ids = [], []
    for rid in sorted(targets):
        items = grouped.get(rid, [])
        current = [item['review'] for item in items if item['source_match_status'] == 'CURRENT_SOURCE']
        stale = [item['review'] for item in items if item['source_match_status'] == 'STALE_SOURCE']
        decisions = sorted({row['decision'] for row in current})
        recorded = canonical.get(rid)
        cues = []
        if supplied:
            if not current:
                cues.append('NO_CURRENT_SOURCE_REVIEW')
            if len(decisions) > 1:
                cues.append('DIFFERING_CURRENT_POSITIONS')
            if 'unclear' in decisions:
                cues.append('UNCLEAR_CURRENT_POSITION')
            if stale:
                cues.append('STALE_REVIEW_ASSERTIONS')
            if recorded is not None and any(value != recorded['decision'] for value in decisions if value != 'unclear'):
                cues.append('CURRENT_POSITION_DIFFERS_FROM_RECORDED')
        if cues:
            cue_ids.append(rid)
        records.append(dict(record_id=rid, review_ids=[item['review']['review_id'] for item in items],
                            current_review_ids=[row['review_id'] for row in current],
                            stale_review_ids=[row['review_id'] for row in stale], current_decisions=decisions,
                            current_reviewer_labels=sorted({row['reviewer'] for row in current}),
                            recorded_screening=copy.deepcopy(recorded), comparison_cues=cues))
    current_count = sum(item['source_match_status'] == 'CURRENT_SOURCE' for item in ledger)
    return dict(stage='SUPPLIED' if supplied else 'NOT_SUPPLIED', **prepared,
                review_ledger=ledger, record_review_ledger=records, records_with_review_cues=cue_ids,
                counts=dict(records=len(targets), review_assertions=len(ledger),
                            current_source_reviews=current_count, stale_source_reviews=len(ledger)-current_count,
                            records_with_review_cues=len(cue_ids)),
                reviewer_identity_verification='NOT_ESTABLISHED', source_authenticity='NOT_VERIFIED',
                eligibility_correctness='NOT_ASSESSED', adjudication='NOT_PERFORMED', boundary=BOUNDARY)
