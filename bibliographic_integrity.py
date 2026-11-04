"""Validate flat, supplied-review bibliographic import history without trusting identity.

The ledger is an integrity record, not an authenticated review or source receipt.
This module deliberately does not import workflow or intake entry points.
"""
import copy
import datetime
import hashlib
import re

from json_io import canonical_json_bytes

MAX_PROTOCOL_BYTES = 50_000_000
MAX_IMPORTS = 100
ENRICHMENT_FIELDS = {
    'searches', 'screening', 'reports', 'evidence', 'gaps', 'contexts',
    'appraisals', 'version', 'planning_decisions', 'synthesis_statements',
    'experimental_units', 'bibliographic_imports',
}
ENTRY_FIELDS = {
    'intake', 'prior_protocol_body', 'prior_prefix_count', 'resolutions',
    'reconciliation_target', 'review', 'sha256',
}
BOUNDARY = (
    'Supplied export-level review permits collection for screening only. '
    'Reviewer identity and review assertions are not authenticated. '
    'Source authenticity and publication identity are not verified. '
    'Literal locator conflicts remain in the original export; reconciliation choices do not authenticate identity. '
    'Withheld rows are retained, not screening exclusions. '
    'CSV end-of-file and row counts do not establish search completeness or a search total. '
    'Collection counts are not PRISMA occurrence counts or evidence of scientific conclusions.'
)


def digest(value):
    """Hash canonical JSON, preserving list order and exact supplied strings."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _same(left, right):
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _schema(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(label + ' has unknown or missing fields')


def _record_ids(protocol):
    searches = protocol.get('searches')
    if not isinstance(searches, list):
        raise ValueError('bibliographic protocol searches must be a list')
    ids = set()
    for search in searches:
        if not isinstance(search, dict) or not isinstance(search.get('record_ids'), list):
            raise ValueError('invalid bibliographic protocol search')
        for record_id in search['record_ids']:
            if not _text(record_id):
                raise ValueError('search record IDs must be nonblank strings')
            ids.add(record_id)
    return ids


def normalize_resolutions(artifact, rows, existing_ids):
    """Require one explicit disposition per candidate; return original CSV order."""
    if not isinstance(artifact, dict) or not isinstance(artifact.get('parsed_export'), dict):
        raise ValueError('invalid bibliographic intake artifact')
    candidates = artifact['parsed_export'].get('record_rows')
    if not isinstance(candidates, list) or not isinstance(rows, list):
        raise ValueError('candidates and resolutions must be lists')
    candidate_ids = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or not _text(candidate.get('candidate_id')):
            raise ValueError('invalid bibliographic candidate')
        candidate_ids.append(candidate['candidate_id'])
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError('duplicate bibliographic candidate IDs')
    expected = set(candidate_ids)
    existing = set(existing_ids)
    resolved, new_ids = {}, set()
    for row in rows:
        _schema(row, {'candidate_id', 'disposition', 'record_id', 'rationale'}, 'resolution')
        cid = row['candidate_id']
        if not _text(cid) or cid not in expected or cid in resolved:
            raise ValueError('unknown or duplicate resolution candidate')
        if not _text(row['rationale']):
            raise ValueError('each resolution requires a nonblank rationale')
        disposition, rid = row['disposition'], row['record_id']
        if disposition not in ('new_record', 'same_record', 'do_not_promote'):
            raise ValueError('unknown bibliographic disposition')
        if disposition == 'do_not_promote':
            if rid is not None:
                raise ValueError('do_not_promote requires null record_id')
        elif not _text(rid):
            raise ValueError('promoted resolution requires nonblank record_id')
        elif disposition == 'new_record':
            if rid in existing or rid in new_ids:
                raise ValueError('new_record ID already exists or is declared more than once')
            new_ids.add(rid)
        resolved[cid] = copy.deepcopy(row)
    if set(resolved) != expected:
        raise ValueError('every parsed candidate requires exactly one resolution')
    available_ids = existing | new_ids
    for row in resolved.values():
        if row['disposition'] == 'same_record' and row['record_id'] not in available_ids:
            raise ValueError('same_record must reference an existing or batch-declared new record')
    return [resolved[cid] for cid in candidate_ids]


def reconciliation_target(artifact, current_protocol, normalized_rows):
    """Bind the exact intake, current protocol and explicit ordered decisions."""
    target = dict(
        schema_version=1, target_type='bibliographic_reconciliation',
        intake_sha256=digest(artifact),
        intake_review_target_sha256=artifact['review_target']['target_sha256'],
        current_protocol_sha256=digest(current_protocol),
        resolutions_sha256=digest(normalized_rows),
    )
    target['target_sha256'] = digest(target)
    return target


def validate_review(review, target):
    """Validate a supplied assertion, without authenticating reviewer identity."""
    fields = {'target_sha256', 'reviewer', 'reviewed_at', 'rationale', 'decision'}
    _schema(review, fields, 'bibliographic review')
    if any(not _text(review[key]) for key in fields):
        raise ValueError('bibliographic review fields must be nonblank strings')
    if review['target_sha256'] != target.get('target_sha256'):
        raise ValueError('bibliographic review target hash mismatch')
    date = review['reviewed_at']
    if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date) is None:
        raise ValueError('bibliographic reviewed_at must be YYYY-MM-DD')
    try:
        datetime.date.fromisoformat(date)
    except ValueError as error:
        raise ValueError('invalid bibliographic reviewed_at date') from error
    if review['decision'] != 'import_for_screening':
        raise ValueError('bibliographic review decision must be import_for_screening')
    return copy.deepcopy(review)


def normalized_search(artifact, entry, index):
    """A CSV import never asserts pagination, total count or search completion."""
    request = artifact['search_request']
    search = {key: copy.deepcopy(request[key]) for key in
              ('search_id', 'source', 'query', 'window', 'searched_at')}
    ids, seen = [], set()
    for row in entry['resolutions']:
        if row['disposition'] != 'do_not_promote' and row['record_id'] not in seen:
            ids.append(row['record_id'])
            seen.add(row['record_id'])
    search.update(record_ids=ids, complete=False, total_count=None, has_more=None)
    search['bibliographic_provenance'] = dict(
        receipt_sha256=entry['sha256'], import_index=index,
        intake_sha256=digest(artifact), source_export_sha256=artifact['source_export']['sha256'],
        source_authenticity='NOT_VERIFIED', record_identity_verification='NOT_ESTABLISHED',
        review=copy.deepcopy(entry['review']),
    )
    return search


def _check_context(protocol, base):
    if not isinstance(protocol, dict):
        raise ValueError('bibliographic protocol body must be an object')
    if 'adapter_receipts' in protocol:
        raise ValueError('bibliographic imports cannot mix with mock adapter receipts')
    for key in ('searches', 'evidence'):
        values = protocol.get(key, [])
        if isinstance(values, list) and any(isinstance(row, dict) and 'adapter_provenance' in row for row in values):
            raise ValueError('bibliographic imports cannot mix with mock adapter provenance')
    if not _same({k: v for k, v in protocol.items() if k not in ENRICHMENT_FIELDS},
                 {k: v for k, v in base.items() if k not in ENRICHMENT_FIELDS}):
        raise ValueError('bibliographic immutable protocol context changed')


def validate_protocol(protocol, verify_artifact_callback):
    """Validate the common base and every exact historical import, or return None.

    The callback must verify a reconstructed full intake artifact. It receives
    only the common base snapshot, which cannot contain this ledger, avoiding
    recursive verification through workflow entry points.
    """
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    if 'bibliographic_imports' not in protocol:
        searches = protocol.get('searches', [])
        if isinstance(searches, list) and any(isinstance(s, dict) and 'bibliographic_provenance' in s for s in searches):
            raise ValueError('bibliographic provenance requires its import ledger')
        return None
    if len(canonical_json_bytes(protocol)) > MAX_PROTOCOL_BYTES:
        raise ValueError('bibliographic protocol exceeds size limit')
    if not callable(verify_artifact_callback):
        raise ValueError('bibliographic ledger requires an intake verification callback')
    ledger = protocol['bibliographic_imports']
    _schema(ledger, {'schema_version', 'base_protocol', 'imports'}, 'bibliographic ledger')
    if type(ledger['schema_version']) is not int or ledger['schema_version'] != 1:
        raise ValueError('unsupported bibliographic ledger schema')
    base, entries = ledger['base_protocol'], ledger['imports']
    if not isinstance(base, dict) or 'bibliographic_imports' in base or 'adapter_receipts' in base:
        raise ValueError('bibliographic common base must have no import or mock ledger')
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_IMPORTS:
        raise ValueError('bibliographic ledger requires between 1 and 100 imports')
    _check_context(base, base)
    _check_context(protocol, base)
    _record_ids(base)
    expected_searches = copy.deepcopy(base['searches'])
    if any('bibliographic_provenance' in search for search in expected_searches):
        raise ValueError('bibliographic common base contains orphan provenance')
    summary = dict(
        collection_status='SUPPLIED_REVIEWED_LOCAL_EXPORTS', imports=[], row_ledger=[],
        counts=dict(raw_rows=0, promoted_row_occurrences=0, withheld_rows=0,
                    canonical_search_memberships=0), review_status='SUPPLIED_ASSERTION_NOT_AUTHENTICATED',
        source_authenticity='NOT_VERIFIED', record_identity_verification='NOT_ESTABLISHED',
        search_completion='NOT_ESTABLISHED', census_claim='NOT_ESTABLISHED',
        conclusion_readiness='NOT_READY', boundary=BOUNDARY,
    )
    for index, entry in enumerate(entries):
        _schema(entry, ENTRY_FIELDS, 'bibliographic import entry')
        if type(entry['prior_prefix_count']) is not int or entry['prior_prefix_count'] != index:
            raise ValueError('bibliographic import prefix count mismatch')
        if entry['sha256'] != digest({k: v for k, v in entry.items() if k != 'sha256'}):
            raise ValueError('bibliographic import receipt hash mismatch')
        compact = entry['intake']
        if not isinstance(compact, dict) or 'protocol_snapshot' in compact:
            raise ValueError('bibliographic intake must use the compact common-base form')
        artifact = copy.deepcopy(compact)
        artifact['protocol_snapshot'] = copy.deepcopy(base)
        verify_artifact_callback(artifact)
        body = entry['prior_protocol_body']
        if not isinstance(body, dict) or 'bibliographic_imports' in body:
            raise ValueError('prior protocol body must omit the import ledger')
        _check_context(body, base)
        if index == 0 and not _same(body, base):
            raise ValueError('first prior protocol body must equal the common base')
        if not _same(body.get('searches'), expected_searches):
            raise ValueError('historical searches differ from base plus earlier imports')
        prior = copy.deepcopy(body)
        if index:
            prior['bibliographic_imports'] = dict(schema_version=1, base_protocol=base, imports=entries[:index])
        search_id = artifact['search_request']['search_id']
        if any(s.get('search_id') == search_id for s in expected_searches):
            raise ValueError('bibliographic selected search ID has already been executed')
        rows = normalize_resolutions(artifact, entry['resolutions'], _record_ids(body))
        if not _same(rows, entry['resolutions']):
            raise ValueError('stored resolutions must follow original CSV row order')
        target = reconciliation_target(artifact, prior, rows)
        if not _same(entry['reconciliation_target'], target):
            raise ValueError('bibliographic reconciliation target mismatch')
        validate_review(entry['review'], target)
        search = normalized_search(artifact, entry, index)
        expected_searches.append(search)
        retained = []
        for row_index, (original, resolution) in enumerate(zip(artifact['parsed_export']['record_rows'], rows)):
            item = copy.deepcopy(original)
            item['resolution'] = copy.deepcopy(resolution)
            item['import_index'] = index
            item['source_pointer'] = f'/bibliographic_imports/imports/{index}/intake/parsed_export/record_rows/{row_index}'
            retained.append(item)
        withheld = sum(row['disposition'] == 'do_not_promote' for row in rows)
        imported = dict(import_index=index, receipt_sha256=entry['sha256'], search_id=search_id,
                        intake_sha256=digest(artifact), source_export_sha256=artifact['source_export']['sha256'],
                        review=copy.deepcopy(entry['review']),
                        raw_rows=len(rows), promoted_row_occurrences=len(rows) - withheld,
                        withheld_rows=withheld, canonical_search_memberships=len(search['record_ids']))
        summary['imports'].append(imported)
        summary['row_ledger'].extend(retained)
        for key in ('raw_rows', 'promoted_row_occurrences', 'withheld_rows', 'canonical_search_memberships'):
            summary['counts'][key] += imported[key]
    if not _same(protocol.get('searches'), expected_searches):
        raise ValueError('current searches differ from exact base plus normalized bibliographic imports')
    return summary
