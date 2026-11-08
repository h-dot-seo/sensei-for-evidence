"""Pure integrity checks for explicit supplied screening decisions, not adjudication."""
import copy
import datetime
import hashlib
import re
from json_io import canonical_json_bytes
from screening_links import prepare_targets, link_screening_reviews, validate_review_assertions

MAX_HISTORY_BYTES = 50_000_000
MAX_RECEIPTS = 1000
HISTORY_KEY = 'screening_decision_history'
DOCUMENT_FIELDS = {'schema_version', 'receipt_id', 'record_id', 'decision', 'reason', 'adjudicator', 'decided_at', 'rationale', 'source_locator', 'target_sha256'}
TARGET_FIELDS = {'schema_version', 'target_type', 'record_id', 'input_protocol_sha256', 'receipt_index', 'previous_receipt_sha256', 'prior_screening', 'source_target', 'source_context_refs', 'review_stage', 'review_snapshots', 'target_sha256'}
RECEIPT_FIELDS = {'receipt_id', 'receipt_index', 'previous_receipt_sha256', 'target', 'assertion', 'result_screening', 'receipt_sha256'}
BASIS_FIELDS = {'schema_version', 'scope', 'record_id', 'question', 'inclusion_criteria', 'exclusion_criteria', 'occurrences', 'bibliographic_rows'}
BOUNDARY = ('Explicit supplied human choices only; adjudication validity is NOT_ASSESSED and reviewer identity is NOT_ESTABLISHED. '
            'Hashes establish supplied-data integrity, not authentication, append-only storage or chronology. '
            'Historical full protocols are not retained or reconstructed. Dates never select a winner. '
            'Retrospective comparison cues are not pending tasks; no receipt is inferred active. '
            'Mapped bibliographic rows are supplied snapshot fragments, not reverified exports. '
            'Source locators are inert; no external calls or clinical judgments occur.')


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def same(a, b):
    return canonical_json_bytes(a) == canonical_json_bytes(b)


def schema(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(label + ' has unknown or missing fields')


def version(value):
    if type(value) is not int or value != 1:
        raise ValueError('screening decision schema_version must be integer 1')


def text(value):
    return isinstance(value, str) and bool(value.strip())


def hash_value(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('screening decision hash must be 64 lowercase hex characters')


def _no_nested_history(value):
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if HISTORY_KEY in item or 'bibliographic_imports' in item:
                raise ValueError('screening decision snapshots cannot nest protocol histories')
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def _canonical_row(row, rid):
    if (not isinstance(row, dict) or row.get('record_id') != rid or
            row.get('decision') not in ('include', 'exclude') or not text(row.get('reason'))):
        raise ValueError('invalid retained canonical screening row')


def validate_document(document):
    schema(document, DOCUMENT_FIELDS, 'screening decision document')
    version(document['schema_version'])
    if any(not text(document[key]) for key in DOCUMENT_FIELDS - {'schema_version'}):
        raise ValueError('all decision fields must be supplied nonblank literal strings')
    if document['decision'] not in ('include', 'exclude'):
        raise ValueError('screening decision must be include or exclude')
    if re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', document['decided_at']) is None:
        raise ValueError('decided_at must be YYYY-MM-DD')
    try:
        datetime.date.fromisoformat(document['decided_at'])
    except ValueError as error:
        raise ValueError('invalid decided_at date') from error
    hash_value(document['target_sha256'])


def _result(prior, assertion):
    result = copy.deepcopy(prior) if prior is not None else {'record_id': assertion['record_id']}
    result.update(decision=assertion['decision'], reason=assertion['reason'])
    return result


def _validate_target(target, catalog, index, previous):
    schema(target, TARGET_FIELDS, 'screening decision target')
    version(target['schema_version'])
    rid = target['record_id']
    if not text(rid) or target['target_type'] != 'screening_decision':
        raise ValueError('invalid screening decision target identity')
    if type(target['receipt_index']) is not int or target['receipt_index'] != index or target['previous_receipt_sha256'] != previous:
        raise ValueError('broken screening decision target chain')
    hash_value(target['input_protocol_sha256'])
    hash_value(target['target_sha256'])
    if digest({k: v for k, v in target.items() if k != 'target_sha256'}) != target['target_sha256']:
        raise ValueError('screening decision target hash mismatch')
    if target['prior_screening'] is not None:
        _canonical_row(target['prior_screening'], rid)
    source = target['source_target']
    schema(source, {'record_id', 'source_basis', 'source_basis_sha256'}, 'retained source target')
    basis = source['source_basis']
    schema(basis, BASIS_FIELDS, 'retained source basis')
    version(basis['schema_version'])
    if source['record_id'] != rid or basis['record_id'] != rid or basis['scope'] != 'title_abstract_supplied_context':
        raise ValueError('retained source basis identity mismatch')
    if any(not basis[key] for key in ('question', 'inclusion_criteria', 'exclusion_criteria')):
        raise ValueError('missing retained source basis context')
    hash_value(source['source_basis_sha256'])
    if digest(basis) != source['source_basis_sha256']:
        raise ValueError('retained source basis hash mismatch')
    refs = target['source_context_refs']
    if not isinstance(refs, list) or not refs:
        raise ValueError('retained source context refs required')
    ref_by_index = {}
    for ref in refs:
        schema(ref, {'search_index', 'input_pointer', 'search_context_sha256'}, 'source context ref')
        si = ref['search_index']
        if type(si) is not int or si < 0 or si in ref_by_index or ref['input_pointer'] != f'/searches/{si}':
            raise ValueError('invalid or duplicate retained search index/pointer')
        hash_value(ref['search_context_sha256'])
        if ref['search_context_sha256'] not in catalog:
            raise ValueError('missing retained source context')
        ref_by_index[si] = ref
    if list(ref_by_index) != sorted(ref_by_index):
        raise ValueError('source context refs must retain search index order')
    expected = []
    for si, ref in ref_by_index.items():
        search = catalog[ref['search_context_sha256']]['search']
        for ri, item in enumerate(search['record_ids']):
            if item == rid:
                expected.append(dict(input_pointer=f'/searches/{si}/record_ids/{ri}', search_index=si,
                                     record_index=ri, search_context_sha256=ref['search_context_sha256']))
        if rid not in search['record_ids']:
            raise ValueError('retained context does not enumerate target record')
    if not same(basis['occurrences'], expected):
        raise ValueError('retained occurrence membership or pointer mismatch')
    if not isinstance(basis['bibliographic_rows'], list):
        raise ValueError('retained bibliographic rows must be a list')
    seen_fragments = set()
    for row in basis['bibliographic_rows']:
        schema(row, {'candidate_id', 'record_id', 'source_locator', 'original_values', 'source_span',
                     'resolution', 'import_index', 'source_pointer'}, 'supplied bibliographic row snapshot')
        if any(not text(row[k]) for k in ('candidate_id', 'record_id', 'source_locator', 'source_pointer')):
            raise ValueError('invalid supplied bibliographic row text')
        if type(row['import_index']) is not int or row['import_index'] < 0:
            raise ValueError('invalid supplied bibliographic import index')
        match = re.fullmatch(r'/bibliographic_imports/imports/(0|[1-9][0-9]*)/intake/parsed_export/record_rows/(0|[1-9][0-9]*)', row['source_pointer'])
        if match is None or int(match[1]) != row['import_index'] or row['source_pointer'] in seen_fragments:
            raise ValueError('invalid or duplicate supplied bibliographic pointer')
        seen_fragments.add(row['source_pointer'])
        values = row['original_values']
        if not isinstance(values, dict) or not values or any(not text(k) or not isinstance(v, str) for k, v in values.items()):
            raise ValueError('invalid supplied bibliographic original values')
        span = row['source_span']
        schema(span, {'line_start', 'line_end', 'byte_start', 'byte_end', 'sha256'}, 'supplied bibliographic span')
        if any(type(span[k]) is not int for k in ('line_start', 'line_end', 'byte_start', 'byte_end')):
            raise ValueError('invalid supplied bibliographic span integers')
        if not (1 <= span['line_start'] <= span['line_end'] and 0 <= span['byte_start'] < span['byte_end']):
            raise ValueError('invalid supplied bibliographic span bounds')
        hash_value(span['sha256'])
        resolution = row['resolution']
        schema(resolution, {'candidate_id', 'disposition', 'record_id', 'rationale'}, 'supplied bibliographic resolution')
        if (resolution['candidate_id'] != row['candidate_id'] or not text(resolution['rationale']) or
                resolution['record_id'] != rid or resolution['disposition'] not in ('new_record', 'same_record')):
            raise ValueError('bibliographic snapshot must map to target record')
    if target['review_stage'] not in ('SUPPLIED', 'NOT_SUPPLIED'):
        raise ValueError('invalid review snapshot stage')
    validate_review_assertions(target['review_snapshots'], {rid})
    if target['review_stage'] == 'NOT_SUPPLIED' and target['review_snapshots']:
        raise ValueError('unsupplied review stage cannot contain assertions')
    return set(ref['search_context_sha256'] for ref in refs)


def _history(protocol):
    history = protocol.get(HISTORY_KEY, dict(schema_version=1, source_contexts=[], receipts=[]))
    schema(history, {'schema_version', 'source_contexts', 'receipts'}, 'screening decision history')
    version(history['schema_version'])
    if not isinstance(history['source_contexts'], list) or not isinstance(history['receipts'], list):
        raise ValueError('screening decision history catalogs must be lists')
    if len(history['receipts']) > MAX_RECEIPTS or len(canonical_json_bytes(history)) > MAX_HISTORY_BYTES:
        raise ValueError('screening decision history exceeds retention limit')
    _no_nested_history(history)
    catalog = {}
    for item in history['source_contexts']:
        schema(item, {'search_context_sha256', 'search'}, 'retained search context')
        key = item['search_context_sha256']
        hash_value(key)
        if key in catalog or digest(item['search']) != key:
            raise ValueError('duplicate or mismatched retained search context hash')
        search = item['search']
        if not isinstance(search, dict) or any(not text(search.get(k)) for k in ('source', 'query', 'searched_at', 'window')):
            raise ValueError('invalid retained search context')
        ids = search.get('record_ids')
        if not isinstance(ids, list) or any(not text(i) for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('invalid retained search record IDs')
        catalog[key] = item
    seen, referenced, previous = set(), set(), None
    for index, receipt in enumerate(history['receipts']):
        schema(receipt, RECEIPT_FIELDS, 'screening decision receipt')
        if type(receipt['receipt_index']) is not int or receipt['receipt_index'] != index or receipt['previous_receipt_sha256'] != previous:
            raise ValueError('broken screening decision receipt chain')
        validate_document(receipt['assertion'])
        if receipt['receipt_id'] != receipt['assertion']['receipt_id'] or receipt['receipt_id'] in seen:
            raise ValueError('duplicate or mismatched screening decision receipt_id')
        seen.add(receipt['receipt_id'])
        referenced.update(_validate_target(receipt['target'], catalog, index, previous))
        target, assertion = receipt['target'], receipt['assertion']
        if assertion['record_id'] != target['record_id'] or assertion['target_sha256'] != target['target_sha256']:
            raise ValueError('decision assertion target mismatch')
        _canonical_row(receipt['result_screening'], target['record_id'])
        if not same(receipt['result_screening'], _result(target['prior_screening'], assertion)):
            raise ValueError('decision result differs from exact supplied choice')
        hash_value(receipt['receipt_sha256'])
        if digest({k: v for k, v in receipt.items() if k != 'receipt_sha256'}) != receipt['receipt_sha256']:
            raise ValueError('screening decision receipt hash mismatch')
        previous = receipt['receipt_sha256']
    if referenced != set(catalog):
        raise ValueError('unreferenced screening decision source context')
    return history


def prepare_target(protocol, record_id, bibliographic_collection=None):
    """Prepare context from a workflow-validated input, without creating a choice."""
    history = _history(protocol)
    prepared = prepare_targets(protocol, bibliographic_collection)
    reviews = link_screening_reviews(protocol, bibliographic_collection)
    selected = next((row for row in prepared['record_targets'] if row['record_id'] == record_id), None)
    if selected is None:
        raise ValueError('unknown screening decision record_id')
    indices = {row['search_index'] for row in selected['source_basis']['occurrences']}
    contexts = [row for row in prepared['source_contexts'] if row['search_index'] in indices]
    target = dict(schema_version=1, target_type='screening_decision', record_id=record_id,
                  input_protocol_sha256=digest(protocol), receipt_index=len(history['receipts']),
                  previous_receipt_sha256=history['receipts'][-1]['receipt_sha256'] if history['receipts'] else None,
                  prior_screening=copy.deepcopy(next((r for r in protocol['screening'] if r['record_id'] == record_id), None)),
                  source_target=selected,
                  source_context_refs=[{k: v for k, v in row.items() if k != 'search'} for row in contexts],
                  review_stage=reviews['stage'],
                  review_snapshots=copy.deepcopy([r for r in protocol.get('screening_reviews', []) if r['record_id'] == record_id]))
    target['target_sha256'] = digest(target)
    catalog = {row['search_context_sha256']: dict(search_context_sha256=row['search_context_sha256'], search=row['search']) for row in contexts}
    return dict(target=target, source_contexts=list(catalog.values()))


def build_candidate(protocol, document, bibliographic_collection=None):
    """Build a detached candidate; the public API validates full before/after workflows.

    This pure helper checks receipt integrity, not report/evidence consistency.
    Use screening_decision.assemble for the complete operational guard.
    """
    validate_document(document)
    prepared = prepare_target(protocol, document['record_id'], bibliographic_collection)
    target = prepared['target']
    if document['target_sha256'] != target['target_sha256']:
        raise ValueError('decision target differs from exact current protocol; no automatic rebase')
    candidate = copy.deepcopy(protocol)
    history = candidate.setdefault(HISTORY_KEY, dict(schema_version=1, source_contexts=[], receipts=[]))
    if any(row['receipt_id'] == document['receipt_id'] for row in history['receipts']):
        raise ValueError('duplicate screening decision receipt_id')
    known = {row['search_context_sha256'] for row in history['source_contexts']}
    history['source_contexts'].extend(copy.deepcopy([r for r in prepared['source_contexts'] if r['search_context_sha256'] not in known]))
    result = _result(target['prior_screening'], document)
    receipt = dict(receipt_id=document['receipt_id'], receipt_index=target['receipt_index'],
                   previous_receipt_sha256=target['previous_receipt_sha256'], target=target,
                   assertion=copy.deepcopy(document), result_screening=copy.deepcopy(result))
    receipt['receipt_sha256'] = digest(receipt)
    history['receipts'].append(receipt)
    for index, row in enumerate(candidate['screening']):
        if row['record_id'] == document['record_id']:
            candidate['screening'][index] = result
            break
    else:
        candidate['screening'].append(result)
    _history(candidate)
    return dict(protocol_candidate=candidate, appended_receipt=copy.deepcopy(receipt))


def link_screening_decisions(protocol, bibliographic_collection=None):
    history = _history(protocol)
    targets = {r['record_id']: r for r in prepare_targets(protocol, bibliographic_collection)['record_targets']}
    current = {r['record_id']: r for r in protocol['screening']}
    ledger, grouped, previous_by_record = [], {}, {}
    for index, receipt in enumerate(history['receipts']):
        target = receipt['target']
        rid = target['record_id']
        source_status = ('RECORD_NOT_ENUMERATED' if rid not in targets else 'CURRENT_SOURCE'
                         if targets[rid]['source_basis_sha256'] == target['source_target']['source_basis_sha256'] else 'STALE_SOURCE')
        snapshots = [r for r in protocol.get('screening_reviews', []) if r['record_id'] == rid]
        review_match = same(snapshots, target['review_snapshots']) and target['review_stage'] == ('SUPPLIED' if 'screening_reviews' in protocol else 'NOT_SUPPLIED')
        match = same(current.get(rid), receipt['result_screening'])
        prior_match = None if rid not in previous_by_record else same(target['prior_screening'], previous_by_record[rid])
        cues = []
        if source_status != 'CURRENT_SOURCE': cues.append(source_status)
        if not review_match: cues.append('CHANGED_REVIEW_ASSERTIONS')
        if not match: cues.append('RESULT_DIFFERS_FROM_CURRENT_SCREENING')
        if prior_match is False: cues.append('PRIOR_ROW_DIFFERS_FROM_PRECEDING_RECORD_RESULT')
        item = dict(receipt=copy.deepcopy(receipt), input_pointer=f'/{HISTORY_KEY}/receipts/{index}',
                    current_source_match_status=source_status,
                    current_source_basis_sha256=targets[rid]['source_basis_sha256'] if rid in targets else None,
                    review_snapshot_match_status='CURRENT_ASSERTIONS' if review_match else 'CHANGED_ASSERTIONS',
                    matches_current_screening=match, prior_row_matches_preceding_record_result=prior_match,
                    comparison_cues=cues)
        ledger.append(item)
        grouped.setdefault(rid, []).append(item)
        previous_by_record[rid] = receipt['result_screening']
    cue_ids = sorted(rid for rid, rows in grouped.items() if any(row['comparison_cues'] for row in rows))
    records = [dict(record_id=rid, receipt_ids=[row['receipt']['receipt_id'] for row in grouped[rid]],
                    current_screening=copy.deepcopy(current.get(rid))) for rid in sorted(grouped)]
    return dict(stage='SUPPLIED' if HISTORY_KEY in protocol else 'NOT_SUPPLIED',
                source_contexts=copy.deepcopy(history['source_contexts']), receipt_ledger=ledger,
                record_history=records, records_with_history_cues=cue_ids,
                counts=dict(receipts=len(ledger), source_contexts=len(history['source_contexts']),
                            records_with_history=len(records), records_with_history_cues=len(cue_ids)),
                adjudication_validity='NOT_ASSESSED', reviewer_identity_verification='NOT_ESTABLISHED',
                historical_protocol_reconstruction='NOT_PERFORMED', boundary=BOUNDARY)
