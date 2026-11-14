"""Record supplied research-output disclosures, never publish or assess release readiness."""
import copy
from context_links import nonempty_text, iso_date

TEXT_FIELDS = {'release_id', 'released_by', 'released_at', 'scope_statement', 'coverage_disclosure',
               'limitations_disclosure', 'supplied_relevance_statement', 'supplied_confidence_label'}
CANDIDATE_FIELDS = TEXT_FIELDS | {'kind', 'unresolved_issues', 'assumptions', 'supplied_recommendation_strength',
    'readiness_assertion_id', 'gates_sha256', 'required_artifacts', 'release_readiness'}
ATTACHMENT_FIELDS = {'artifact_observation_sha256', 'bundle_manifest_sha256', 'bundle_bytes_sha256'}
FIELDS = CANDIDATE_FIELDS | {'attachment_bindings'}
MAX_ROWS = 100
NEGATIVE_CLAIMS = dict(mechanical_release_readiness='NOT_RELEASED', actual_publication_performed=False,
    disclosure_assessment='NOT_PERFORMED', source_authenticity='NOT_ESTABLISHED',
    artifact_acceptance='NOT_ASSESSED', recorded_observations_rechecked=False,
    scientific_closure='NOT_ASSESSED', census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')
BOUNDARY = ('Supplied research-output disclosure labels only, not repository releases, actual publication, '
    'permission to publish, scientific closure or mechanical release readiness. RELEASED_WITHIN_SCOPE '
    'can coexist with NOT_READY/INSUFFICIENT assertions and open gates; this is displayed, not adjudicated '
    'or blocked. Exact gate/item ID naming does not assess disclosure adequacy. Current gate and readiness '
    'context is recomputed, not a historical snapshot or authenticated author/reviewer record. Attachment '
    'hashes identify retained supplied material; no artifact bytes or external records are read here. '
    'Pre-disclosure bundle pointers cannot identify the resulting self-containing bundle. Existing gates '
    'and records are not changed, renewed or promoted. Mechanical release readiness remains NOT_RELEASED.')


def _hex(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def validate_candidate(row):
    if not isinstance(row,dict) or set(row)!=CANDIDATE_FIELDS:
        raise ValueError('output disclosure requires exact candidate fields')
    if any(not nonempty_text(row[k]) for k in TEXT_FIELDS):
        raise ValueError('output disclosure text fields must be supplied')
    iso_date(row['released_at'],'released_at')
    if row['kind']!='research_output_disclosure' or row['release_readiness'] not in ('RELEASED_WITHIN_SCOPE','WITHHELD'):
        raise ValueError('unknown supplied research-output label')
    if not nonempty_text(row['readiness_assertion_id']) or not _hex(row['gates_sha256']):
        raise ValueError('output disclosure requires readiness ID and gate hash')
    if row['supplied_recommendation_strength'] is not None and not nonempty_text(row['supplied_recommendation_strength']):
        raise ValueError('supplied recommendation strength must be null or text')
    assumptions=row['assumptions']
    if not isinstance(assumptions,list) or len(assumptions)>100 or any(not nonempty_text(v) for v in assumptions):
        raise ValueError('assumptions must be at most 100 supplied strings')
    issues=row['unresolved_issues']
    if not isinstance(issues,list) or len(issues)>100:
        raise ValueError('unresolved issues must be at most 100 exact gate/item statements')
    seen=set()
    for item in issues:
        if not isinstance(item,dict) or set(item)!={'gate_id','item_id','statement'} or any(not nonempty_text(v) for v in item.values()):
            raise ValueError('invalid unresolved issue fields')
        pair=(item['gate_id'],item['item_id'])
        if pair in seen: raise ValueError('duplicate unresolved issue pair')
        seen.add(pair)
    artifacts=row['required_artifacts']
    if not isinstance(artifacts,list) or len(artifacts)>100:
        raise ValueError('required artifacts must be a list of at most 100')
    seen=set()
    for item in artifacts:
        if not isinstance(item,dict) or set(item)!={'work_package_id','artifact_locator','sha256'}:
            raise ValueError('invalid required artifact fields')
        if not nonempty_text(item['work_package_id']) or not nonempty_text(item['artifact_locator']) or not _hex(item['sha256']):
            raise ValueError('invalid required artifact values')
        if item['work_package_id'] in seen: raise ValueError('duplicate required work artifact')
        seen.add(item['work_package_id'])


def link_disclosures(protocol, readiness, work):
    supplied=protocol.get('output_disclosures',[])
    if not isinstance(supplied,list) or len(supplied)>MAX_ROWS:
        raise ValueError('output_disclosures must be at most 100 records')
    assertions={r['assertion_id']:r for r in readiness['assertion_ledger']}
    gates={r['gate_id'] for r in readiness['gate_ledger']}
    open_items={(r['gate_id'],item) for r in readiness['gate_ledger'] if r['status']=='OPEN' for item in r['open_items']}
    works={r['work_package_id']:r for r in work}
    ledger={}
    for row in supplied:
        if not isinstance(row,dict) or set(row)!=FIELDS: raise ValueError('output disclosure requires exact stored fields')
        validate_candidate({k:v for k,v in row.items() if k!='attachment_bindings'})
        rid=row['release_id']
        if rid in ledger: raise ValueError('duplicate output disclosure ID')
        aid=row['readiness_assertion_id']
        if aid not in assertions: raise ValueError('unknown output disclosure readiness assertion')
        bindings=row['attachment_bindings']
        if not isinstance(bindings,dict) or set(bindings)!=ATTACHMENT_FIELDS or any(v is not None and not _hex(v) for v in bindings.values()):
            raise ValueError('invalid output disclosure attachment bindings')
        if (bindings['bundle_manifest_sha256'] is None)!=(bindings['bundle_bytes_sha256'] is None):
            raise ValueError('bundle bindings must be present together')
        for item in row['required_artifacts']:
            if item['work_package_id'] not in works: raise ValueError('unknown required work artifact')
        for item in row['unresolved_issues']:
            if item['gate_id'] not in gates: raise ValueError('unknown disclosure gate ID')
        current=readiness['gates_sha256']==row['gates_sha256']
        named={(i['gate_id'],i['item_id']) for i in row['unresolved_issues']}
        assertion=assertions[aid]
        ledger[rid]=dict(copy.deepcopy(row),source_match_status='CURRENT_GATES' if current else 'STALE_GATES',
            current_gates_sha256=readiness['gates_sha256'], current_readiness_assertion=copy.deepcopy(assertion),
            open_items_not_named_in_disclosure=[dict(gate_id=g,item_id=i) for g,i in sorted(open_items-named)],
            named_items_not_currently_open=[dict(gate_id=g,item_id=i) for g,i in sorted(named-open_items)],
            disclosure_comparison_scope='CURRENT_GATE_ITEMS_NOT_HISTORICAL_RELEASE_FINDINGS',
            released_with_not_ready_assertion=(row['release_readiness']=='RELEASED_WITHIN_SCOPE' and
                (assertion['conclusion_readiness']!='READY' or assertion['evidence_sufficiency']!='SUFFICIENT')),
            **NEGATIVE_CLAIMS)
    rows=[ledger[k] for k in sorted(ledger)]
    return dict(schema_version=1,stage='SUPPLIED' if 'output_disclosures' in protocol else 'NOT_SUPPLIED',
        disclosure_ledger=rows, stale_disclosure_ids=[r['release_id'] for r in rows if r['source_match_status']=='STALE_GATES'],
        released_with_not_ready_assertion=[r['release_id'] for r in rows if r['released_with_not_ready_assertion']],
        disclosures_with_unnamed_current_open_items=[r['release_id'] for r in rows if r['open_items_not_named_in_disclosure']],
        **NEGATIVE_CLAIMS,boundary=BOUNDARY)
