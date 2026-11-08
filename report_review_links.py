"""Pure supplied full-text source/review links; never retrieve or adjudicate."""
import copy
import datetime
import hashlib
import re

from json_io import canonical_json_bytes
from report_links import validate_reports, validate_evidence_membership, report_study_ids
from screening_links import prepare_targets as prepare_record_targets

SOURCE_FIELDS = {'source_id', 'report_id', 'source_locator', 'document_version', 'document_sha256'}
REVIEW_FIELDS = {'review_id', 'report_id', 'reviewer', 'reviewed_at', 'decision',
                 'rationale', 'reviewed_locator', 'source_basis_sha256'}
BOUNDARY = (
    'Supplied full-text source declarations and human review positions only. Every supplied document '
    'digest is unverified; source hashes bind supplied context, not document bytes or authenticity. '
    'All descriptors are source context, not a claim every file was read. No preferred or current '
    'document version is inferred. Current positions do not establish retrieval, reading, scientific '
    'quality or eligibility correctness. Reviewer identity and independence are not established. '
    'No majority, quorum, consensus or adjudication is inferred. Stale assertions are retained and '
    'never refreshed automatically. Reviews do not change canonical decisions, counts, evidence, '
    'work or study memberships. Empty comparison cues do not prove reading, completeness or quality. '
    'Locators are inert supplied text; no fetching or execution occurs.'
)


def _digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _validate_ledgers(protocol, reports):
    sources, reviews = protocol.get('report_sources', []), protocol.get('report_reviews', [])
    if not isinstance(sources, list):
        raise ValueError('report_sources must be a list')
    if not isinstance(reviews, list):
        raise ValueError('report_reviews must be a list')
    ids = set()
    for row in sources:
        if not isinstance(row, dict) or set(row) != SOURCE_FIELDS:
            raise ValueError('report source has unknown or missing fields')
        if any(not _text(row[key]) for key in SOURCE_FIELDS - {'document_sha256'}):
            raise ValueError('report source text fields must be nonblank literal strings')
        if row['report_id'] not in reports:
            raise ValueError('unknown report source report_id')
        if row['source_id'] in ids:
            raise ValueError('duplicate report source_id')
        if row['document_sha256'] is not None and not _hash(row['document_sha256']):
            raise ValueError('document_sha256 must be null or 64 lowercase hex characters')
        ids.add(row['source_id'])
    ids, pairs = set(), set()
    for row in reviews:
        if not isinstance(row, dict) or set(row) != REVIEW_FIELDS:
            raise ValueError('report review has unknown or missing fields')
        if any(not _text(row[key]) for key in REVIEW_FIELDS):
            raise ValueError('report review fields must be nonblank literal strings')
        if row['report_id'] not in reports:
            raise ValueError('unknown report review report_id')
        pair = (row['report_id'], row['reviewer'])
        if row['review_id'] in ids or pair in pairs:
            raise ValueError('duplicate report review_id or report/reviewer pair')
        if row['decision'] not in ('include', 'exclude', 'unclear'):
            raise ValueError('report review decision must be include, exclude or unclear')
        if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', row['reviewed_at']) is None:
            raise ValueError('report reviewed_at must be YYYY-MM-DD')
        try:
            datetime.date.fromisoformat(row['reviewed_at'])
        except ValueError as error:
            raise ValueError('invalid report reviewed_at date') from error
        if not _hash(row['source_basis_sha256']):
            raise ValueError('report source_basis_sha256 must be 64 lowercase hex characters')
        ids.add(row['review_id'])
        pairs.add(pair)
    return sources, reviews


def prepare_targets(protocol, bibliographic_collection=None):
    """Validate every supplied report/membership and return detached source targets."""
    if 'reports' not in protocol:
        _validate_ledgers(protocol, {})
        return dict(stage='SUPPLIED' if 'report_sources' in protocol or 'report_reviews' in protocol else 'NOT_SUPPLIED',
                    report_stage='NOT_SUPPLIED',
                    source_stage='SUPPLIED' if 'report_sources' in protocol else 'NOT_SUPPLIED',
                    review_stage='SUPPLIED' if 'report_reviews' in protocol else 'NOT_SUPPLIED',
                    source_contexts=[], record_targets=[],
                    source_ledger=[], report_targets=[])
    included = {row['record_id'] for row in protocol['screening'] if row['decision'] == 'include'}
    reports, by_record = validate_reports(protocol['reports'], included)
    for evidence in protocol['evidence']:
        validate_evidence_membership(evidence, by_record)
    sources, _ = _validate_ledgers(protocol, reports)
    prepared = prepare_record_targets(protocol, bibliographic_collection)
    records = {row['record_id']: row for row in prepared['record_targets']}
    source_ledger, by_report, source_pointers = [], {}, {}
    for index, source in enumerate(sources):
        source_ledger.append(dict(source=copy.deepcopy(source), input_pointer=f'/report_sources/{index}'))
        by_report.setdefault(source['report_id'], []).append(source)
        source_pointers.setdefault(source['report_id'], []).append(f'/report_sources/{index}')
    targets = []
    for index, row in enumerate(protocol['reports']):
        rid = row['report_id']
        descriptors = by_report.get(rid, [])
        state = ('SOURCE_NOT_SUPPLIED' if not descriptors else
                 'SUPPLIED_DIGESTS' if all(s['document_sha256'] is not None for s in descriptors)
                 else 'DOCUMENT_BYTES_UNBOUND')
        locator = dict(supplied='locator' in row)
        if 'locator' in row:
            locator['value'] = copy.deepcopy(row['locator'])
        basis = dict(schema_version=1, scope='full_text_supplied_context', report_id=rid,
                     question=copy.deepcopy(protocol['question']),
                     inclusion_criteria=copy.deepcopy(protocol['inclusion_criteria']),
                     exclusion_criteria=copy.deepcopy(protocol['exclusion_criteria']),
                     mapped_records=[dict(record_id=record, source_basis_sha256=records[record]['source_basis_sha256'])
                                     for record in row['record_ids']], retrieval=row['retrieval'],
                     report_locator=locator, report_sources=copy.deepcopy(descriptors))
        targets.append(dict(report_id=rid, input_pointer=f'/reports/{index}', source_basis=basis,
                            source_basis_sha256=_digest(basis), retrieval=row['retrieval'],
                            source_binding_state=state, recorded_report=copy.deepcopy(row),
                            supplied_study_ids=report_study_ids(row),
                            source_input_pointers=copy.deepcopy(source_pointers.get(rid, []))))
    return dict(stage='SUPPLIED' if 'report_sources' in protocol or 'report_reviews' in protocol else 'NOT_SUPPLIED',
                report_stage='SUPPLIED',
                source_stage='SUPPLIED' if 'report_sources' in protocol else 'NOT_SUPPLIED',
                review_stage='SUPPLIED' if 'report_reviews' in protocol else 'NOT_SUPPLIED',
                **prepared, source_ledger=source_ledger, report_targets=targets)


def _counts(result):
    current = sum(item['source_match_status'] == 'CURRENT_SOURCE' for item in result['review_ledger'])
    return dict(reports=len(result['report_targets']), source_descriptors=len(result['source_ledger']),
                review_assertions=len(result['review_ledger']), current_source_reviews=current,
                stale_source_reviews=len(result['review_ledger']) - current,
                reports_with_review_cues=len(result['reports_with_review_cues']))


def link_report_reviews(protocol, bibliographic_collection=None):
    """Compare literal supplied positions without altering canonical full-text rows."""
    prepared = prepare_targets(protocol, bibliographic_collection)
    targets = {row['report_id']: row for row in prepared['report_targets']}
    ledger, grouped = [], {}
    for index, row in enumerate(protocol.get('report_reviews', [])):
        target = targets[row['report_id']]
        digest = target['source_basis_sha256']
        item = dict(review=copy.deepcopy(row), input_pointer=f'/report_reviews/{index}',
                    source_match_status='CURRENT_SOURCE' if row['source_basis_sha256'] == digest else 'STALE_SOURCE',
                    current_source_basis_sha256=digest,
                    matches_recorded_decision=(None if row['decision'] == 'unclear'
                                              or target['recorded_report'].get('decision', 'pending') == 'pending'
                                              else row['decision'] == target['recorded_report']['decision']))
        ledger.append(item)
        grouped.setdefault(row['report_id'], []).append(item)
    report_ledger, cue_ids = [], []
    for target in prepared['report_targets']:
        rid = target['report_id']
        items = grouped.get(rid, [])
        current = [item['review'] for item in items if item['source_match_status'] == 'CURRENT_SOURCE']
        stale = [item['review'] for item in items if item['source_match_status'] == 'STALE_SOURCE']
        decisions = sorted({row['decision'] for row in current})
        cues = []
        if target['retrieval'] != 'retrieved':
            cues.append('REPORT_NOT_RETRIEVED' if target['retrieval'] == 'not_retrieved' else 'RETRIEVAL_PENDING')
        if target['source_binding_state'] != 'SUPPLIED_DIGESTS':
            cues.append(target['source_binding_state'])
        if not current:
            cues.append('NO_CURRENT_SOURCE_REVIEW')
        if stale:
            cues.append('STALE_REVIEW_ASSERTIONS')
        if 'unclear' in decisions:
            cues.append('UNCLEAR_CURRENT_POSITION')
        if len(decisions) > 1:
            cues.append('DIFFERING_CURRENT_POSITIONS')
        if (target['recorded_report'].get('decision', 'pending') != 'pending'
                and any(value != target['recorded_report']['decision'] for value in decisions if value != 'unclear')):
            cues.append('CURRENT_POSITION_DIFFERS_FROM_RECORDED')
        if cues:
            cue_ids.append(rid)
        report_ledger.append(dict(report_id=rid, recorded_report=copy.deepcopy(target['recorded_report']),
                                  supplied_study_ids=copy.deepcopy(target['supplied_study_ids']),
                                  retrieval=target['retrieval'], source_binding_state=target['source_binding_state'],
                                  review_ids=[item['review']['review_id'] for item in items],
                                  current_review_ids=[row['review_id'] for row in current],
                                  stale_review_ids=[row['review_id'] for row in stale], current_decisions=decisions,
                                  current_reviewer_labels=sorted({row['reviewer'] for row in current}),
                                  comparison_cues=cues))
    result = dict(**prepared, review_ledger=ledger, report_review_ledger=report_ledger,
                  reports_with_review_cues=cue_ids, document_bytes_verification='NOT_PERFORMED',
                  source_authenticity='NOT_VERIFIED', reviewer_identity_verification='NOT_ESTABLISHED',
                  reviewer_independence='NOT_ESTABLISHED', adjudication='NOT_PERFORMED',
                  eligibility_correctness='NOT_ASSESSED', boundary=BOUNDARY)
    result['counts'] = _counts(result)
    return result
