"""Bind explicitly selected supplied document descriptors to source-review work."""
import copy

from context_links import id_list, validate_source_refs
from report_review_links import prepare_targets

BOUNDARY = (
    'Explicit supplied document source context only. Document digests are unverified; '
    'hashes bind supplied descriptors and report context, not document bytes or authenticity. '
    'The same-report document catalog is context, not a claim every document was read. '
    'No retrieval, reading, eligibility, acceptance or preferred version is established. '
    'Only exact record source references link documents; planned searches never inherit links. '
    'Direct dependency context does not imply recursive acceptance or change recorded work status.'
)


def selected_document_work(work):
    """Validate opt-in shape without preparing report targets or changing supplied rows."""
    selected = {}
    for row in work:
        if 'document_source_ids' not in row:
            continue
        if row.get('work_type') != 'source_review':
            raise ValueError('document_source_ids are reserved for explicit source_review work')
        ids = id_list(row['document_source_ids'], 'document_source_ids')
        if not ids:
            raise ValueError('document_source_ids must be nonempty when supplied')
        wid = row['work_package_id']
        if wid in selected:
            raise ValueError('duplicate work package ID for document sources')
        selected[wid] = row
    return selected


def link_work_documents(protocol, work, bibliographic_collection=None):
    """Return detached opt-in contexts using one validated report-target preparation.

    The optional bibliographic collection must already have passed intake validation,
    matching the report-review helper contract. Positional navigation pointers are
    deliberately omitted; existing report source hashes retain their own semantics.
    """
    selected = selected_document_work(work)
    if not selected:
        return {}
    prepared = prepare_targets(protocol, bibliographic_collection)
    sources = {row['source']['source_id']: row['source'] for row in prepared['source_ledger']}
    targets = {row['report_id']: row for row in prepared['report_targets']}
    records = {rid for search in protocol['searches'] for rid in search['record_ids']}
    planned = {row['search_id'] for row in protocol.get('search_plan', [])}
    contexts = {}
    for wid, row in selected.items():
        refs = validate_source_refs(row.get('source_refs'), planned, records)
        record_refs = {ref['record_id'] for ref in refs if ref['kind'] == 'record'}
        linked = []
        for sid in row['document_source_ids']:
            if sid not in sources:
                raise ValueError('document_source_ids references unknown report source')
            source = sources[sid]
            target = targets[source['report_id']]
            matched = [rid for rid in target['recorded_report']['record_ids'] if rid in record_refs]
            if not matched:
                raise ValueError('document source requires an exact work record source_ref in its report')
            linked.append(dict(source=copy.deepcopy(source), matched_record_ids=matched,
                               report_id=source['report_id'],
                               report_source_basis_sha256=target['source_basis_sha256']))
        contexts[wid] = dict(schema_version=1, scope='explicit_work_document_sources', sources=linked)
    return contexts
