"""Pure, descriptive supplied study inventory; no membership or eligibility decisions."""
import copy
import datetime
import re

from report_links import report_study_ids
from report_review_links import prepare_targets as prepare_report_targets, _digest, _hash, _text

INVENTORY_FIELDS = {'inventory_id', 'report_id', 'study_id', 'recorded_by', 'recorded_at',
                    'description', 'source_locator', 'source_ids', 'source_basis_sha256'}
BOUNDARY = (
    'Explicit supplied descriptions of candidate report-study pairs only, including before a '
    'full-text inclusion decision. Reports still require title/abstract-included record links. '
    'Descriptions do not establish study identity, independence, eligibility, inventory completeness '
    'or canonical membership. All people’s descriptions are retained; no preferred description, '
    'date winner, consensus or adjudication is inferred. Current membership and result presence '
    'are separate literal comparisons, never promotion or filtering instructions. Source IDs are '
    'explicit human selections; differing sets do not prove differing coverage. Source hashes '
    'bind supplied context, not document bytes, authenticity, reading or description correctness. '
    'Null document hashes remain unbound and all supplied digests remain unverified. Assertions '
    'are never renewed automatically. Locators are inert text, never opened, fetched or executed.'
)


def _validate_inventory(protocol, reports):
    rows = protocol.get('report_study_inventory', [])
    if not isinstance(rows, list):
        raise ValueError('report_study_inventory must be a list')
    ids, triples = set(), set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != INVENTORY_FIELDS:
            raise ValueError('report study inventory has unknown or missing fields')
        if any(not _text(row[key]) for key in INVENTORY_FIELDS - {'source_ids'}):
            raise ValueError('report study inventory scalar fields must be nonblank literal strings')
        if row['report_id'] not in reports:
            raise ValueError('unknown report study inventory report_id')
        sources = row['source_ids']
        if (not isinstance(sources, list) or not sources or any(not _text(s) for s in sources)
                or len(sources) != len(set(sources))):
            raise ValueError('source_ids must be nonempty unique literal strings')
        triple = (row['report_id'], row['study_id'], row['recorded_by'])
        if row['inventory_id'] in ids or triple in triples:
            raise ValueError('duplicate inventory_id or report/study/recorded_by tuple')
        if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', row['recorded_at']) is None:
            raise ValueError('report study recorded_at must be YYYY-MM-DD')
        try:
            datetime.date.fromisoformat(row['recorded_at'])
        except ValueError as error:
            raise ValueError('invalid report study recorded_at date') from error
        if not _hash(row['source_basis_sha256']):
            raise ValueError('report study source_basis_sha256 must be 64 lowercase hex characters')
        ids.add(row['inventory_id'])
        triples.add(triple)
    return rows


def _catalogs(protocol, prepared):
    reports = {row['report_id']: row for row in prepared['report_targets']}
    memberships, report_for_record = {}, {}
    for rid, target in reports.items():
        report = target['recorded_report']
        memberships[rid] = set(report_study_ids(report))
        report_for_record.update((record, rid) for record in report['record_ids'])
    results = {}
    for row in protocol.get('evidence', []):
        pair = (report_for_record.get(row['record_id']), row['study_id'])
        results.setdefault(pair, []).append(row.get('evidence_id', row['record_id']))
    return reports, memberships, results


def _candidate(report_id, study_id, reports, memberships, results):
    report = reports[report_id]
    basis = dict(schema_version=1, scope='report_study_supplied_inventory_context',
                 report_id=report_id, study_id=study_id,
                 report_source_basis_sha256=report['source_basis_sha256'])
    evidence_ids = sorted(results.get((report_id, study_id), []))
    return dict(report_id=report_id, study_id=study_id, source_basis=basis,
                source_basis_sha256=_digest(basis),
                membership_currently_declared=study_id in memberships[report_id],
                evidence_ids=evidence_ids, has_result_rows=bool(evidence_ids),
                retrieval=report['retrieval'], source_binding_state=report['source_binding_state'])


def prepare_targets(protocol, bibliographic_collection=None):
    """Validate complete report/source/evidence context and explicit inventory pairs."""
    prepared = prepare_report_targets(protocol, bibliographic_collection)
    reports, memberships, results = _catalogs(protocol, prepared)
    rows = _validate_inventory(protocol, reports)
    pairs = dict.fromkeys((row['report_id'], row['study_id']) for row in rows)
    targets = {pair: _candidate(*pair, reports, memberships, results) for pair in pairs}
    source_reports = {item['source']['source_id']: item['source']['report_id']
                      for item in prepared['source_ledger']}
    for row in rows:
        target = targets[(row['report_id'], row['study_id'])]
        matching = row['source_basis_sha256'] == target['source_basis_sha256']
        for sid in row['source_ids']:
            if sid in source_reports and source_reports[sid] != row['report_id']:
                raise ValueError('inventory source ID belongs to another report')
            if matching and sid not in source_reports:
                raise ValueError('current report study inventory requires existing same-report source IDs')
    stage = 'SUPPLIED' if 'report_study_inventory' in protocol else 'NOT_SUPPLIED'
    prepared.update(stage=stage, inventory_stage=stage, candidate_targets=list(targets.values()))
    return prepared


def prepare_candidate_target(protocol, report_id, study_id, bibliographic_collection=None):
    """Return a detached context for an explicit human-supplied new or existing label."""
    prepared = prepare_targets(protocol, bibliographic_collection)
    reports, memberships, results = _catalogs(protocol, prepared)
    if not _text(report_id) or report_id not in reports:
        raise ValueError('unknown report study inventory report_id')
    if not _text(study_id):
        raise ValueError('study_id must be an explicit nonblank human-supplied string')
    return _candidate(report_id, study_id, reports, memberships, results)


def _counts(result):
    ledger = result['inventory_ledger']
    current = sum(row['source_match_status'] == 'CURRENT_SOURCE' for row in ledger)
    return dict(reports=len(result['report_targets']), source_descriptors=len(result['source_ledger']),
                inventory_assertions=len(ledger), described_report_study_pairs=len(result['candidate_targets']),
                current_source_assertions=current, stale_source_assertions=len(ledger) - current)


def link_report_study_inventory(protocol, bibliographic_collection=None):
    """Retain every description and compare its context without selecting studies."""
    prepared = prepare_targets(protocol, bibliographic_collection)
    targets = {(row['report_id'], row['study_id']): row for row in prepared['candidate_targets']}
    sources = {row['source']['source_id'] for row in prepared['source_ledger']}
    ledger, grouped = [], {}
    for index, row in enumerate(protocol.get('report_study_inventory', [])):
        pair = (row['report_id'], row['study_id'])
        target = targets[pair]
        item = dict(inventory=copy.deepcopy(row), input_pointer=f'/report_study_inventory/{index}',
                    current_source_basis_sha256=target['source_basis_sha256'],
                    source_match_status=('CURRENT_SOURCE' if row['source_basis_sha256'] == target['source_basis_sha256']
                                         else 'STALE_SOURCE'),
                    unresolved_source_ids=[sid for sid in row['source_ids'] if sid not in sources])
        ledger.append(item)
        grouped.setdefault(pair, []).append(item)
    pairs = []
    for pair, target in targets.items():
        items = grouped[pair]
        current = [item['inventory'] for item in items if item['source_match_status'] == 'CURRENT_SOURCE']
        stale = [item['inventory'] for item in items if item['source_match_status'] == 'STALE_SOURCE']
        descriptions = sorted({row['description'] for row in current})
        source_sets = sorted({tuple(sorted(row['source_ids'])) for row in current})
        unresolved = sorted({sid for item in items for sid in item['unresolved_source_ids']})
        cues = []
        if not target['membership_currently_declared']:
            cues.append('MEMBERSHIP_NOT_CURRENTLY_DECLARED')
        if target['retrieval'] != 'retrieved':
            cues.append('REPORT_NOT_RETRIEVED' if target['retrieval'] == 'not_retrieved' else 'RETRIEVAL_PENDING')
        if target['source_binding_state'] != 'SUPPLIED_DIGESTS':
            cues.append(target['source_binding_state'])
        if stale:
            cues.append('STALE_INVENTORY_ASSERTIONS')
        if len(descriptions) > 1:
            cues.append('DIFFERING_CURRENT_DESCRIPTIONS')
        if len(source_sets) > 1:
            cues.append('DIFFERING_CURRENT_SOURCE_ID_SETS')
        if unresolved:
            cues.append('UNRESOLVED_SOURCE_IDS')
        pairs.append(dict(report_id=pair[0], study_id=pair[1],
                          inventory_ids=[item['inventory']['inventory_id'] for item in items],
                          current_inventory_ids=[row['inventory_id'] for row in current],
                          stale_inventory_ids=[row['inventory_id'] for row in stale],
                          current_descriptions=descriptions,
                          current_recorder_labels=sorted({row['recorded_by'] for row in current}),
                          stale_recorder_labels=sorted({row['recorded_by'] for row in stale}),
                          current_source_id_sets=[list(ids) for ids in source_sets],
                          unresolved_source_ids=unresolved,
                          membership_currently_declared=target['membership_currently_declared'],
                          evidence_ids=copy.deepcopy(target['evidence_ids']), has_result_rows=target['has_result_rows'],
                          retrieval=target['retrieval'], source_binding_state=target['source_binding_state'],
                          comparison_cues=cues))
    result = dict(**prepared, inventory_ledger=ledger, pair_inventory_ledger=pairs,
                  inventory_completeness='NOT_ESTABLISHED', study_identity='NOT_ESTABLISHED',
                  study_independence='NOT_ESTABLISHED', eligibility_assessment='NOT_PERFORMED',
                  document_bytes_verification='NOT_PERFORMED', source_authenticity='NOT_VERIFIED',
                  recorder_identity_verification='NOT_ESTABLISHED', description_correctness='NOT_ASSESSED',
                  canonical_study_selection='NOT_MODELED', adjudication='NOT_PERFORMED', boundary=BOUNDARY)
    result['counts'] = _counts(result)
    return result
