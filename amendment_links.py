"""Observe supplied amendment records; never close a gap or approve a change."""
import copy
from context_links import nonempty_text, iso_date, id_list
from json_io import canonical_json_bytes
import hashlib

MAX_ROWS = 100
FIELDS = {'amendment_id', 'before_protocol_sha256', 'from_version', 'to_version',
          'reason', 'authored_by', 'authored_at', 'scope_fields', 'triggered_by'}
BOUNDARY = ('Supplied amendment records, not approval, authenticated authorship, chronology or scientific verification. '
    'A version match is only equality with a supplied version label. Before hashes and historical references '
    'cannot be verified from this single protocol. Retain the original BEFORE and human-edited AFTER plus '
    'the separate application for exact replay. Existing OPEN_AMENDMENT reopening and all gates remain '
    'unchanged; recording an amendment does not resolve a material gap, renew a review or establish completeness.')
NEGATIVE_CLAIMS = dict(assessment='NOT_PERFORMED', amendment_approval='NOT_ESTABLISHED',
    authorship_authentication='NOT_ESTABLISHED', chronology_verification='NOT_PERFORMED',
    external_calls=0, census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')


def digest(value):return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def validate_row(row):
    if type(row) is not dict or set(row) != FIELDS:raise ValueError('amendment requires exact fields')
    for key in ('amendment_id','from_version','to_version','reason','authored_by'):
        if not nonempty_text(row[key]):raise ValueError('amendment requires nonblank supplied text')
    value=row['before_protocol_sha256']
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('amendment requires a lowercase before SHA-256')
    iso_date(row['authored_at'],'authored_at')
    id_list(row['scope_fields'],'scope_fields')
    if len(row['scope_fields'])>100 or 'amendments' in row['scope_fields']:
        raise ValueError('amendment scope is at most 100 fields; amendments is implicit')
    refs=row['triggered_by']
    if type(refs) is not list or len(refs)>100:raise ValueError('triggered_by is at most 100 supplied references')
    seen=set()
    for ref in refs:
        if type(ref) is not dict or set(ref)!={'kind','ref_id'} or ref['kind'] not in ('CHALLENGE','READINESS_ASSERTION') or not nonempty_text(ref['ref_id']):
            raise ValueError('invalid supplied amendment reference')
        key=(ref['kind'],ref['ref_id'])
        if key in seen:raise ValueError('duplicate supplied amendment reference')
        seen.add(key)


def link_amendments(protocol):
    rows=protocol.get('amendments',[])
    if type(rows) is not list or len(rows)>MAX_ROWS:raise ValueError('amendments must be a list of at most 100 rows')
    seen=set();ledger=[]
    for row in rows:
        validate_row(row)
        if row['amendment_id'] in seen:raise ValueError('duplicate amendment ID')
        seen.add(row['amendment_id'])
        ledger.append(dict(record=copy.deepcopy(row),record_sha256=digest(row),
            version_match='CURRENT_VERSION' if canonical_json_bytes(row['to_version'])==canonical_json_bytes(protocol['version']) else 'NOT_CURRENT_VERSION',
            before_hash_verification='NOT_VERIFIED_IN_PLACE',historical_reference_verification='NOT_VERIFIED_IN_PLACE'))
    return dict(stage='SUPPLIED' if 'amendments' in protocol else 'NOT_SUPPLIED',
        amendment_ledger=ledger,recorded_count=len(ledger),**NEGATIVE_CLAIMS,boundary=BOUNDARY)


def paired_observation(before,after,row):
    """Observe one supplied embedded row against two actual snapshots; no gate effect."""
    validate_row(row)
    actual=sorted(k for k in set(before)|set(after) if k!='amendments' and
        (k not in before or k not in after or canonical_json_bytes(before[k])!=canonical_json_bytes(after[k])))
    scope=row['scope_fields']
    references=[]
    for ref in row['triggered_by']:
        field,key=('challenges','challenge_id') if ref['kind']=='CHALLENGE' else ('readiness_assertions','assertion_id')
        found=any(r[key]==ref['ref_id'] for r in before.get(field,[]))
        references.append(dict(reference=copy.deepcopy(ref),present_in_before=found))
    hashes=row['before_protocol_sha256']==digest(before)
    versions=dict(before=canonical_json_bytes(row['from_version'])==canonical_json_bytes(before['version']),
                  after=canonical_json_bytes(row['to_version'])==canonical_json_bytes(after['version']))
    missing=sorted(set(actual)-set(scope));unexpected=sorted(set(scope)-set(actual))
    matched=hashes and all(versions.values()) and not missing and not unexpected and all(r['present_in_before'] for r in references)
    return dict(record=copy.deepcopy(row),before_input_hash_match=hashes,after_hash_verification='NOT_APPLICABLE_EMBEDDED',
        version_matches=versions,actual_changed_fields=actual,undeclared_changed_fields=missing,
        declared_but_unchanged_fields=unexpected,historical_references=references,
        implicit_scope_fields=['amendments'],binding_status='RECORDED_BEFORE_AND_SCOPE_MATCH' if matched else 'MISMATCH',
        **NEGATIVE_CLAIMS,boundary=BOUNDARY)


def context_lines(context):
    from json_io import quoted_display
    return ['Recorded amendments: '+str(context['recorded_count'])+'; before hashes not verified in place',
            'Supplied amendment observations: '+quoted_display(context['amendment_ledger']),BOUNDARY]
