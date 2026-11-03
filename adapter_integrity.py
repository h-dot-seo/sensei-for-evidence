"""Check internal mock receipt/review consistency; never authenticate external sources."""
import copy
import hashlib
from pathlib import Path

from context_links import nonempty_text, iso_date
from json_io import canonical_json_bytes
from search_audit import completion_issues


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def text_fields(row, fields, label):
    if not isinstance(row, dict):
        raise ValueError(label + ' must be an object')
    for field in fields:
        if not nonempty_text(row.get(field)):
            raise ValueError(label + ' requires ' + field)


def prepare_exchange(protocol, fixture):
    if not isinstance(protocol, dict) or not isinstance(fixture, dict):
        raise ValueError('protocol and fixture must be objects')
    if type(fixture.get('schema_version')) is not int or fixture['schema_version'] != 1:
        raise ValueError('unsupported adapter fixture schema')
    if fixture.get('mode') != 'mock':
        raise ValueError('only mock adapter execution is implemented')
    text_fields(fixture, ('provider_id', 'adapter_version'), 'fixture')
    for key in ('search_responses', 'extraction_candidates'):
        if not isinstance(fixture.get(key), list):
            raise ValueError(key + ' must be a list')
    if not isinstance(protocol.get('search_plan'), list) or not protocol['search_plan']:
        raise ValueError('adapter requires a nonempty declared search plan')
    assembled = copy.deepcopy(protocol)
    if assembled.get('searches') != [] or assembled.get('evidence') != []:
        raise ValueError('adapter input requires empty searches and evidence; never silently overwrite existing work')
    if 'adapter_receipts' in assembled:
        raise ValueError('adapter_receipts already present')
    protocol_sha256 = digest(protocol)
    targets, searches, records, global_locators = {}, [], {}, {}
    request_ids, response_ids, search_ids = set(), set(), set()
    search_by_request = {}
    provider = {key: fixture[key] for key in ('provider_id', 'adapter_version', 'mode')}
    for exchange in fixture['search_responses']:
        if not isinstance(exchange, dict):
            raise ValueError('search response must be an object')
        request = exchange.get('request')
        text_fields(request, ('request_id', 'search_id', 'source', 'query', 'window', 'searched_at'), 'search request')
        if request['request_id'] in request_ids or request['search_id'] in search_ids:
            raise ValueError('duplicate request or search ID')
        request_ids.add(request['request_id']); search_ids.add(request['search_id'])
        pages = exchange.get('pages')
        if not isinstance(pages, list) or not pages:
            raise ValueError('search response requires nonempty pages')
        for page in pages:
            text_fields(page, ('response_id', 'request_id', 'retrieved_at'), 'page')
            if page['request_id'] != request['request_id'] or page['response_id'] in response_ids:
                raise ValueError('page request mismatch or duplicate response ID')
            response_ids.add(page['response_id'])
            if not isinstance(page.get('records'), list):
                raise ValueError('page records must be a list')
            ids = []
            for record in page['records']:
                text_fields(record, ('record_id', 'source_locator'), 'provider record')
                rid = record['record_id']
                ids.append(rid)
                if rid in global_locators and global_locators[rid] != record['source_locator']:
                    raise ValueError('conflicting source locators across requests; reconcile global record IDs first')
                global_locators[rid] = record['source_locator']
                locators = records.setdefault((request['request_id'], rid), set())
                if locators and record['source_locator'] not in locators:
                    raise ValueError('conflicting source locators for one request record')
                locators.add(record['source_locator'])
        search = normalized_search(exchange)
        receipt = dict(schema_version=1, base_protocol_sha256=protocol_sha256, target_type='search', target_id=request['search_id'], provider=provider,
                       exchange=copy.deepcopy(exchange), verification='UNVERIFIED_PROVIDER_RESPONSE')
        receipt['sha256'] = digest(receipt)
        targets[('search', request['search_id'])] = receipt
        search_by_request[request['request_id']] = request['search_id']
        searches.append(search)
    candidates, proposal_ids = [], set()
    for candidate in fixture['extraction_candidates']:
        text_fields(candidate, ('candidate_id', 'request_id', 'record_id', 'source_locator', 'source_text', 'supporting_quote', 'extraction_request_id',
                                'extractor_id', 'extractor_version', 'instruction'), 'extraction candidate')
        key = ('extraction', candidate['candidate_id'])
        if key in targets:
            raise ValueError('duplicate extraction candidate ID')
        if candidate['source_locator'] not in records.get((candidate['request_id'], candidate['record_id']), set()):
            raise ValueError('candidate must link to a returned record and source locator in its request')
        if candidate['supporting_quote'] not in candidate['source_text']:
            raise ValueError('supporting quote is absent from supplied source text')
        proposal = candidate.get('proposal')
        text_fields(proposal, ('evidence_id', 'study_id', 'locator', 'model', 'intervention', 'comparator', 'endpoint', 'result', 'limitations'), 'extraction proposal')
        if proposal['evidence_id'] in proposal_ids:
            raise ValueError('duplicate proposed evidence ID')
        proposal_ids.add(proposal['evidence_id'])
        if 'record_id' in proposal and proposal['record_id'] != candidate['record_id']:
            raise ValueError('proposal record ID conflicts with candidate')
        if proposal.get('mechanism_basis') not in ('association', 'intervention', 'unknown'):
            raise ValueError('proposal requires explicit mechanism_basis')
        receipt = dict(schema_version=1, base_protocol_sha256=protocol_sha256, target_type='extraction', target_id=candidate['candidate_id'], provider=provider,
                       search_receipt_sha256=targets[('search', search_by_request[candidate['request_id']])]['sha256'],
                       candidate=copy.deepcopy(candidate), verification='UNVERIFIED_PROVIDER_RESPONSE')
        receipt['sha256'] = digest(receipt)
        targets[key] = receipt
        candidates.append(receipt)
    return protocol_sha256, targets, searches, candidates, search_by_request, provider


def normalized_search(exchange):
    request = exchange['request']
    pages, ids, seen = [], [], set()
    for page in exchange['pages']:
        normalized = {key: copy.deepcopy(value) for key, value in page.items() if key != 'records'}
        normalized['record_ids'] = [record['record_id'] for record in page['records']]
        for rid in normalized['record_ids']:
            if rid not in seen:
                seen.add(rid); ids.append(rid)
        if 'total_count' in page and (type(page['total_count']) is not int or page['total_count'] < 0
                                      or page['total_count'] != exchange.get('total_count')):
            normalized['error'] = 'page total differs from declared exchange total or is invalid'
        pages.append(normalized)
    search = {key: request[key] for key in ('search_id', 'source', 'query', 'window', 'searched_at')}
    search.update(record_ids=ids, pages=pages, complete=False,
                  total_count=exchange.get('total_count'), has_more=exchange['pages'][-1].get('has_more'))
    for key in ('truncated', 'pagination_limited', 'field_pages_pending', 'error'):
        if key in exchange:
            search[key] = copy.deepcopy(exchange[key])
    return search


def review_decisions(reviews, targets):
    if not isinstance(reviews, list):
        raise ValueError('reviews must be a list')
    decisions = {}
    for review in reviews:
        fields = {'target_type', 'target_id', 'target_sha256', 'reviewer', 'reviewed_at', 'rationale', 'decision'}
        if not isinstance(review, dict) or set(review) != fields:
            raise ValueError('unknown or missing review fields')
        if any(not nonempty_text(review[key]) for key in fields):
            raise ValueError('review fields must be nonempty strings')
        key = (review['target_type'], review['target_id'])
        if key not in targets or key in decisions:
            raise ValueError('unknown or duplicate review target')
        if review['target_sha256'] != targets[key]['sha256']:
            raise ValueError('review hash does not match exact candidate receipt')
        iso_date(review['reviewed_at'], 'reviewed_at')
        if review['decision'] not in ('accept', 'reject'):
            raise ValueError('review decision must be accept or reject')
        decisions[key] = copy.deepcopy(review)
    return decisions


def validate_adapter_protocol(protocol):
    """Reject stale attached provenance while permitting explicitly scoped later enrichment."""
    if 'adapter_receipts' not in protocol:
        for key in ('searches', 'evidence'):
            rows = protocol.get(key)
            if isinstance(rows, list) and any(isinstance(row, dict) and 'adapter_provenance' in row for row in rows):
                raise ValueError('adapter provenance requires its receipt ledger')
        return
    ledger = protocol['adapter_receipts']
    if not isinstance(ledger, dict) or type(ledger.get('schema_version')) is not int or ledger['schema_version'] != 1:
        raise ValueError('invalid adapter receipt ledger')
    base = ledger.get('base_protocol')
    if not isinstance(base, dict) or digest(base) != ledger.get('base_protocol_sha256'):
        raise ValueError('adapter base protocol hash mismatch')
    if base.get('searches') != [] or base.get('evidence') != [] or 'adapter_receipts' in base:
        raise ValueError('invalid adapter base protocol')
    if not isinstance(base.get('search_plan'), list) or not base['search_plan']:
        raise ValueError('adapter base protocol requires declared search plan')
    # These enrichments do not change what was searched, screened or extracted.
    allowed = {'searches', 'evidence', 'adapter_receipts', 'gaps', 'contexts', 'appraisals', 'version', 'planning_decisions'}
    if digest({k: v for k, v in protocol.items() if k not in allowed}) != digest({k: v for k, v in base.items() if k not in allowed}):
        raise ValueError('reviewed adapter protocol context changed; reassemble and review again')
    provider = ledger.get('provider')
    if not isinstance(provider, dict) or provider.get('mode') != 'mock' or any(not nonempty_text(provider.get(k)) for k in ('provider_id', 'adapter_version')):
        raise ValueError('invalid mock adapter provider')
    engine = hashlib.sha256(Path(__file__).with_name('offline_adapter.py').read_bytes()).hexdigest()
    if ledger.get('adapter_engine_sha256') != engine:
        raise ValueError('adapter engine bytes differ; use the recorded implementation')
    receipts = ledger.get('receipts')
    if not isinstance(receipts, list):
        raise ValueError('adapter receipts must be a list')
    targets, search_targets, candidate_targets = {}, {}, []
    for receipt in receipts:
        if not isinstance(receipt, dict) or receipt.get('target_type') not in ('search', 'extraction') or not nonempty_text(receipt.get('target_id')):
            raise ValueError('invalid adapter receipt target')
        key = (receipt['target_type'], receipt['target_id'])
        if key in targets or digest({k: v for k, v in receipt.items() if k != 'sha256'}) != receipt.get('sha256'):
            raise ValueError('duplicate adapter receipt or receipt hash mismatch')
        if (receipt.get('schema_version') != 1 or receipt.get('provider') != provider or
                receipt.get('base_protocol_sha256') != ledger['base_protocol_sha256'] or
                receipt.get('verification') != 'UNVERIFIED_PROVIDER_RESPONSE'):
            raise ValueError('adapter receipt context mismatch')
        targets[key] = receipt
        if key[0] == 'search':
            exchange = receipt.get('exchange')
            if not isinstance(exchange, dict) or not isinstance(exchange.get('request'), dict):
                raise ValueError('invalid adapter search exchange')
            request = exchange['request']
            if request.get('search_id') != key[1] or not nonempty_text(request.get('request_id')) or request['request_id'] in search_targets:
                raise ValueError('adapter search target mismatch')
            if not isinstance(exchange.get('pages'), list) or not exchange['pages']:
                raise ValueError('adapter search requires pages')
            search_targets[request['request_id']] = receipt
        else:
            candidate_targets.append(receipt)
    fixture = dict(schema_version=1, **provider,
                   search_responses=[r['exchange'] for r in search_targets.values()],
                   extraction_candidates=[r['candidate'] for r in candidate_targets])
    prepared = prepare_exchange(base, fixture)
    if digest(list(prepared[1].values())) != digest(receipts):
        raise ValueError('adapter receipts differ from validated exchange normalization')
    decisions = review_decisions(ledger.get('reviews'), targets)
    searches, evidence = [], []
    for receipt in search_targets.values():
        key = ('search', receipt['target_id'])
        review = decisions.get(key)
        try:
            search = normalized_search(receipt['exchange'])
        except (KeyError, TypeError, AttributeError) as error:
            raise ValueError('malformed adapter search receipt') from error
        search['complete'] = review is not None and review['decision'] == 'accept'
        if search['complete'] and completion_issues(search):
            raise ValueError('accepted adapter search has unresolved page/count issues')
        search['adapter_provenance'] = dict(receipt_sha256=receipt['sha256'], provider=provider,
            source_verification='UNVERIFIED_PROVIDER_RESPONSE', review=review)
        searches.append(search)
    for receipt in candidate_targets:
        candidate = receipt.get('candidate')
        if not isinstance(candidate, dict) or not isinstance(candidate.get('proposal'), dict):
            raise ValueError('invalid adapter extraction candidate')
        search_receipt = search_targets.get(candidate.get('request_id'))
        if search_receipt is None or receipt.get('search_receipt_sha256') != search_receipt['sha256']:
            raise ValueError('adapter candidate search receipt mismatch')
        review = decisions.get(('extraction', receipt['target_id']))
        if review is not None and review['decision'] == 'accept':
            search_review = decisions.get(('search', search_receipt['target_id']))
            if search_review is None or search_review['decision'] != 'accept':
                raise ValueError('accepted extraction requires accepted search review')
            row = copy.deepcopy(candidate['proposal'])
            row['record_id'] = candidate.get('record_id')
            row['adapter_provenance'] = dict(candidate_id=receipt['target_id'], receipt_sha256=receipt['sha256'],
                search_receipt_sha256=receipt['search_receipt_sha256'], provider=provider,
                source_verification='UNVERIFIED_PROVIDER_RESPONSE', review=review)
            evidence.append(row)
    if digest(searches) != digest(protocol.get('searches')) or digest(evidence) != digest(protocol.get('evidence')):
        raise ValueError('promoted adapter search/evidence differs from reviewed receipts')
