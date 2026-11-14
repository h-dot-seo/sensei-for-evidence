"""Inspect an explicitly supplied patent ledger outside the research engine."""
import copy
import datetime
import hashlib
from pathlib import Path
import re

from evidence_workflow import run
from json_io import canonical_json_bytes, parse_json, quoted_display
from research_bundle import engine_hashes
from search_manifest import manifest as search_manifest

MAX_PROTOCOL_BYTES = 50_000_000
MAX_CANDIDATE_BYTES = 10_000_000
MAX_OUTPUT_BYTES = 50_000_000
MAX_CANDIDATE_ROWS = 100
QUESTION_FIELDS = {'jurisdictions', 'as_of_date', 'intended_output', 'technical_question', 'claim_feature_scope'}
LEDGERS = {
    'patent_publications': ('publication_id', {'publication_id', 'jurisdiction', 'kind_code', 'publication_date', 'locator', 'basis_sha256'}),
    'patent_applications': ('application_id', {'application_id', 'jurisdiction', 'filing_date', 'publication_ids', 'basis_sha256'}),
    'patent_families': ('family_id', {'family_id', 'family_definition_label', 'member_ids', 'grouping_basis', 'asserted_by', 'asserted_at', 'basis_sha256'}),
    'patent_legal_status_observations': ('observation_id', {'observation_id', 'application_id', 'jurisdiction', 'observed_at', 'source', 'status_text', 'basis_sha256'}),
}
FIELDS = {'patent_question', *LEDGERS}
BOUNDARY = (
    'Supplied patent-information ledger only, not legal advice, an FTO opinion, a legal-rights '
    'determination or a patent search backend. Publication/application IDs, jurisdictions, kind codes, '
    'family membership and legal-status text are exact supplied labels, not authenticated records. '
    'No legal-status observation means only that none is supplied, not a legal-status finding. '
    'CURRENT_SOURCE means exact question/search basis equality, not currency, validity, completeness '
    'or acceptance. Family co-occurrence is exact supplied membership only, not inferred families or '
    'independent search confirmation. Existing run(), the 12 literature gates and research bundles do '
    'not validate this ledger; bundle preservation of fields is not patent verification. Only ordinary '
    'supplied protocols are supported; adapter and bibliographic import histories are rejected. '
    'No locator is opened and no model or network is called. Review labels and dates are unauthenticated '
    'supplied assertions. Real/private material belongs outside the public repository; output is not anonymized.'
)
NEGATIVE = dict(legal_opinion='NOT_PROVIDED', legal_status_currency='NOT_VERIFIED',
    publication_identity_verification='NOT_ESTABLISHED', family_grouping_inference='NOT_PERFORMED',
    priority_validity='NOT_ASSESSED', claim_mapping='NOT_SUPPLIED', census_claim='NOT_ESTABLISHED',
    conclusion_readiness='NOT_READY', external_calls=0)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def normalize(value, limit):
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 128:
            raise ValueError('depth limit')
        if isinstance(item, dict):
            if any(type(key) is not str for key in item):
                raise ValueError('JSON object keys must be strings')
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError('JSON values only')
    raw = canonical_json_bytes(value)
    if len(raw) > limit:
        raise ValueError('byte limit')
    result = parse_json(raw)
    pending = [(result, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 128:
            raise ValueError('depth limit')
        if isinstance(item, dict):
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
    return result


def read(path, limit):
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('byte limit')
    return normalize(parse_json(raw), limit)


def obj(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('exact fields required')


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonblank supplied text required')


def date(value):
    text(value)
    if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError('date shape')
    datetime.date.fromisoformat(value)


def ids(value, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError('ID list required')
    for item in value:
        text(item)
    if len(set(value)) != len(value):
        raise ValueError('duplicate ID')


def question(value):
    obj(value, QUESTION_FIELDS)
    ids(value['jurisdictions'], True)
    date(value['as_of_date'])
    for key in ('technical_question', 'claim_feature_scope'):
        text(value[key])
    if value['intended_output'] not in ('SEARCH_INVENTORY', 'LANDSCAPE', 'PRIOR_ART_SCREEN'):
        raise ValueError('unsupported output label')


def protocol(value):
    value = normalize(value, MAX_PROTOCOL_BYTES)
    if not isinstance(value, dict):
        raise ValueError('protocol object')
    if 'adapter_receipts' in value or 'bibliographic_imports' in value:
        raise ValueError('unsupported import history')
    for key in ('searches', 'evidence'):
        if isinstance(value.get(key), list) and any(isinstance(r, dict) and 'adapter_provenance' in r for r in value[key]):
            raise ValueError('unsupported adapter provenance')
    research = run(value)
    present = FIELDS.intersection(value)
    if present and present != FIELDS:
        raise ValueError('all patent sections required together')
    if present:
        validate_sections({k: value[k] for k in FIELDS})
    return value, research


def basis(value, supplied_question):
    question(supplied_question)
    # Exact supplied search plan/receipts, not derived estimates or inferred windows.
    return digest(dict(patent_question=supplied_question, search_plan=value.get('search_plan'), searches=value.get('searches')))


def validate_sections(sections):
    obj(sections, FIELDS)
    question(sections['patent_question'])
    indexes = {}
    for name, (id_key, fields) in LEDGERS.items():
        rows = sections[name]
        if not isinstance(rows, list):
            raise ValueError('ledger list required')
        indexes[name] = {}
        for row in rows:
            obj(row, fields)
            text(row[id_key])
            if row[id_key] in indexes[name]:
                raise ValueError('duplicate ledger ID')
            indexes[name][row[id_key]] = row
            if not isinstance(row['basis_sha256'], str) or re.fullmatch('[0-9a-f]{64}', row['basis_sha256']) is None:
                raise ValueError('basis digest required')
            if name == 'patent_publications':
                for key in ('jurisdiction', 'kind_code', 'locator'):
                    text(row[key])
                date(row['publication_date'])
            elif name == 'patent_applications':
                text(row['jurisdiction']); date(row['filing_date']); ids(row['publication_ids'])
            elif name == 'patent_families':
                text(row['family_definition_label']); ids(row['member_ids'], True)
                if row['grouping_basis'] == 'MANUAL_ASSERTION':
                    text(row['asserted_by']); date(row['asserted_at'])
                elif row['grouping_basis'] == 'SUPPLIED_FAMILY_IDENTIFIER':
                    if row['asserted_by'] is not None or row['asserted_at'] is not None:
                        raise ValueError('manual assertion fields not applicable')
                else:
                    raise ValueError('unknown grouping basis')
            else:
                for key in ('application_id', 'jurisdiction', 'source', 'status_text'):
                    text(row[key])
                date(row['observed_at'])
    for row in sections['patent_applications']:
        if any(i not in indexes['patent_publications'] for i in row['publication_ids']):
            raise ValueError('unknown publication reference')
    for row in sections['patent_legal_status_observations']:
        if row['application_id'] not in indexes['patent_applications']:
            raise ValueError('unknown application reference')
    # Outside family members are explicitly reported, not guessed or silently removed.
    return indexes


def implementation_hashes():
    root = Path(__file__).resolve().parent
    return dict(engine_hashes(), **{name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ('patent_links.py', 'patent_intake.py', 'patent_review.py', 'search_manifest.py')})


def review(value):
    value, research = protocol(value)
    if not FIELDS.issubset(value):
        raise ValueError('patent ledger required')
    sections = {k: value[k] for k in FIELDS}
    indexes = validate_sections(sections)
    current = basis(value, value['patent_question'])
    publications = indexes['patent_publications']
    observations = value['patent_legal_status_observations']
    search = search_manifest(value)
    seen = set()
    occurrence = {}
    for i, row in enumerate(value.get('searches', [])):
        for rid in row.get('record_ids', []):
            seen.add(rid); occurrence.setdefault(rid, set()).add(i)
    memberships = {}
    family_views = []
    for row in value['patent_families']:
        by_search = {}
        for member in row['member_ids']:
            memberships.setdefault((row['family_definition_label'], member), []).append(row['family_id'])
            for i in occurrence.get(member, ()):
                by_search.setdefault(i, []).append(member)
        family_views.append(dict(family_id=row['family_id'], family_definition_label=row['family_definition_label'],
            search_occurrences=[dict(search_index=i, publication_ids=sorted(by_search[i])) for i in sorted(by_search)],
            occurs_in_multiple_supplied_searches=len(by_search) > 1))
    listed = {i for row in value['patent_families'] for i in row['member_ids']}
    rows = {name: [dict(record=copy.deepcopy(row), source_status='CURRENT_SOURCE' if row['basis_sha256'] == current else 'STALE_SOURCE')
                  for row in value[name]] for name in LEDGERS}
    return dict(schema_version=1, kind='patent_ledger_review', protocol_sha256=digest(value),
        basis_sha256=current, implementation_sha256=implementation_hashes(),
        patent_question=copy.deepcopy(value['patent_question']), rows=rows,
        queues=dict(publications_not_in_any_search=sorted(set(publications)-seen),
            search_record_ids_without_publication_row=sorted(seen-set(publications)),
            publications_not_listed_in_any_supplied_family=sorted(set(publications)-listed),
            family_member_ids_without_ledger_row=sorted(listed-set(publications)),
            applications_without_supplied_legal_status_observation=sorted(set(indexes['patent_applications'])-{r['application_id'] for r in observations}),
            legal_status_observations_after_as_of_date=[r['observation_id'] for r in observations if r['observed_at'] > value['patent_question']['as_of_date']]),
        supplied_family_cooccurrence=family_views,
        multiple_supplied_families_with_same_definition=[dict(family_definition_label=label, publication_id=member, family_ids=sorted(families))
            for (label, member), families in sorted(memberships.items()) if len(families)>1],
        search_accounting=dict(cross_search_overlap=search['cross_search_overlap'], source_coverage=search['source_coverage']),
        literature_readiness=copy.deepcopy(research['readiness']),
        readiness_scope='Unchanged literature gates, not patent readiness; no patent gate added',
        boundary=BOUNDARY, **NEGATIVE)


def render_text(result):
    lines = ['Supplied patent ledger (not legal advice or FTO):']
    for key in ('patent_question', 'rows', 'queues', 'supplied_family_cooccurrence', 'multiple_supplied_families_with_same_definition', 'search_accounting'):
        lines.append(key + ': ' + quoted_display(result[key]))
    lines.extend([result['readiness_scope'], result['boundary']])
    return '\n'.join(lines) + '\n'
