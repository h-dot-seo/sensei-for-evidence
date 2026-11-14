"""Preserve supplied result basis labels without reading documents or judging findings."""
import copy
from collections import Counter

from context_links import id_list, iso_date, nonempty_text
from experiment_links import measurement
from json_io import canonical_json_bytes

MAX_LEDGER_BYTES = 50_000_000
FIELDS = {'evidence_id', 'text_access', 'value_origin', 'finding_kind', 'uncertainty',
          'document_source_ids', 'declared_by', 'declared_at', 'limitations'}
TEXT_ACCESS = ('ABSTRACT_ONLY', 'FULL_TEXT', 'UNKNOWN')
VALUE_ORIGIN = ('REPORTED_NUMERIC', 'REPORTED_TEXT', 'FIGURE_VISUAL_ESTIMATE', 'NOT_APPLICABLE')
FINDING_KIND = ('DIFFERENCE_REPORTED', 'NO_DIFFERENCE_REPORTED', 'MIXED', 'UNCLEAR',
                'OUTCOME_NOT_REPORTED', 'NOT_MEASURED_STATED')
BOUNDARY = (
    'Labels, uncertainty and document selections are unverified supplied declarations, not '
    'source-file observations, reading evidence, quality scores or scientific judgments. '
    'Document hashes do not authenticate bytes or authors. Figure/statistics coexistence is '
    'a review cue, not a rejection or exactness assessment. No numeric interpretation, effect, '
    'significance, equivalence or absence-of-effect inference is made. Unreported and stated '
    'unmeasured outcomes still count as supplied extracted rows. No gate or acceptance policy '
    'is added. Related label changes can stale existing source-bound reviews; no review is renewed.'
)


def selected_basis(protocol, refs, linked):
    """Return exact declarations and selected document descriptors for an existing basis."""
    if 'evidence_bases' not in protocol:
        return None
    if not isinstance(linked, dict) or linked.get('stage') != 'SUPPLIED':
        raise ValueError('supplied evidence bases require validated binding')
    selected = set(refs)
    return [copy.deepcopy(row) for row in linked['basis_ledger'] if row['evidence_id'] in selected]


def link_evidence_bases(protocol, evidence, experiments=None, bibliographic_collection=None):
    rows = protocol.get('evidence_bases', [])
    if not isinstance(rows, list):
        raise ValueError('evidence_bases must be a list')
    if len(canonical_json_bytes(rows)) > MAX_LEDGER_BYTES:
        raise ValueError('evidence_bases exceeds byte budget')
    known = {row['evidence_id']: row for row in evidence}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('evidence basis requires exact fields')
        if any(not nonempty_text(row[k]) for k in FIELDS - {'uncertainty', 'document_source_ids'}):
            raise ValueError('evidence basis requires nonblank text')
        eid = row['evidence_id']
        if eid not in known or eid in seen:
            raise ValueError('unknown or duplicate evidence basis ID')
        seen.add(eid)
        if row['text_access'] not in TEXT_ACCESS or row['value_origin'] not in VALUE_ORIGIN or row['finding_kind'] not in FINDING_KIND:
            raise ValueError('invalid supplied evidence basis label')
        iso_date(row['declared_at'], 'basis declared_at')
        measurement(row['uncertainty'], 'basis uncertainty', with_unit=False)
        id_list(row['document_source_ids'], 'document_source_ids')
    sources, targets = {}, {}
    if any(row['document_source_ids'] for row in rows):
        # This helper validates report membership and descriptors, not source bytes.
        from report_review_links import prepare_targets
        prepared = prepare_targets(protocol, bibliographic_collection)
        sources = {r['source']['source_id']: r['source'] for r in prepared['source_ledger']}
        targets = {r['report_id']: r for r in prepared['report_targets']}
    ledger = []
    for row in sorted(rows, key=lambda r: r['evidence_id']):
        documents = []
        for sid in row['document_source_ids']:
            if sid not in sources:
                raise ValueError('unknown evidence basis document source')
            source = sources[sid]
            target = targets[source['report_id']]
            if known[row['evidence_id']]['record_id'] not in target['recorded_report']['record_ids']:
                raise ValueError('evidence basis document requires the same report record')
            documents.append(dict(source=copy.deepcopy(source),
                                  document_binding='DOCUMENT_BYTES_UNBOUND' if source['document_sha256'] is None else 'DECLARED_HASH_UNVERIFIED'))
        ledger.append(dict(copy.deepcopy(row), document_sources=documents))
    abstract = sorted(r['evidence_id'] for r in rows if r['text_access'] == 'ABSTRACT_ONLY')
    figures = sorted(r['evidence_id'] for r in rows if r['value_origin'] == 'FIGURE_VISUAL_ESTIMATE')
    statistics = set()
    if experiments is not None:
        for unit in experiments['experimental_unit_ledger']:
            for stat in unit.get('outcome_statistics', []):
                cells = [stat[arm][key] for arm in ('treatment', 'comparator') for key in ('value', 'dispersion')]
                cells += [stat['contrast'][key] for key in ('estimate', 'uncertainty')]
                if any(cell['status'] == 'reported' for cell in cells):
                    statistics.add(stat['evidence_id'])
    return dict(schema_version=1, stage='SUPPLIED' if 'evidence_bases' in protocol else 'NOT_SUPPLIED',
                basis_ledger=ledger, evidence_without_basis=sorted(set(known)-seen),
                abstract_only_results=abstract, figure_estimate_results=figures,
                figure_estimate_results_with_reported_statistics=sorted(set(figures) & statistics),
                finding_kind_counts=dict(sorted(Counter(r['finding_kind'] for r in rows).items())),
                boundary=BOUNDARY)


def statement_cues(research):
    """Explicit intersections only; never fill citation-integrity findings."""
    labels = research['evidence_bases']
    return [dict(statement_id=row['statement_id'],
                 abstract_only_citations=sorted(set(row['evidence_ids']) & set(labels['abstract_only_results'])),
                 figure_estimate_citations=sorted(set(row['evidence_ids']) & set(labels['figure_estimate_results'])))
            for row in research['synthesis']['statement_ledger']]
