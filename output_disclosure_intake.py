"""Record supplied output disclosures after exact separate review; never publish anything."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile
from evidence_workflow import run
from prisma_reports import report_flow
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json
from archive_safety import read_bounded
from nbib_intake import _strict_json
import research_bundle
from artifact_review import validate_manifest
from context_links import nonempty_text, iso_date
from output_disclosure_links import CANDIDATE_FIELDS, ATTACHMENT_FIELDS, NEGATIVE_CLAIMS, BOUNDARY, validate_candidate, _hex

MAX_PROTOCOL_BYTES=50_000_000
MAX_DOCUMENT_BYTES=10_000_000
MAX_APPLICATION_BYTES=50_000_000
_ABSENT=object()
REVIEW_FIELDS={'schema_version','receipt_id','target_sha256','decision','reviewer','reviewed_at','rationale'}
OBSERVATION_FIELDS={'schema_version','protocol_sha256','manifest_sha256','engine_sha256','artifacts',
    'uninspected_work_ids','all_requested_bytes_match','inspection_scope','census_claim','conclusion_readiness','boundary'}
MANIFEST_FIELDS={'work_package_id','artifact_locator','path','bytes','sha256'}
OBSERVED_FIELDS=MANIFEST_FIELDS | {'status','observed_bytes','observed_sha256','supplied_work_status',
    'completion_source_status','question','deliverable','acceptance_criterion','supplied_acceptance_verified',
    'depends_on','blocked_by','acceptance_assessment'}
OBSERVED_STATUSES={'BYTES_MATCH','HASH_MISMATCH','CHANGED_DURING_READ','MISSING','REJECTED_FILE_TYPE',
    'SIZE_MISMATCH','UNREADABLE_OR_UNSAFE_PATH'}
INTAKE_BOUNDARY=BOUNDARY + (' Separate review records supplied labels, not permission or actual publication. '
    'Saved artifact observations are untrusted supplied metadata, not live byte checks; their engine '
    'dictionary is displayed, not matched or authenticated. Target/assemble/verify require the same '
    'explicit optional observation and original pre-disclosure bundle. An old application needs its '
    'recorded implementation. Hash-consistent reauthored unsigned assertions can replay. Existing '
    'output-disclosure rows and all original inputs stay unchanged; no automatic rebase. Outputs are '
    'exclusive, not a race-proof ancestor defense or multi-file transaction; earlier files can remain '
    'if a later write fails. No artifact path or external locator is opened.')


def digest(value):return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normal(value,limit):
    _strict_json(value)
    raw=canonical_json_bytes(value)
    if len(raw)>limit:raise ValueError('byte limit exceeded')
    return parse_json(raw)


def _shape(value,fields):
    if not isinstance(value,dict) or set(value)!=fields:raise ValueError('exact fields required')
    if 'schema_version' in fields and (type(value['schema_version']) is not int or value['schema_version']!=1):
        raise ValueError('integer schema_version 1 required')


def _hashes():
    return dict(research_bundle.engine_hashes(),**{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ('output_disclosure_intake.py','artifact_review.py','nbib_intake.py')})


def _validate(protocol):
    result=run(protocol)
    if 'reports' in protocol:report_flow(protocol,include_csv=False)
    return result


def template(protocol,assertion_id):
    protocol=_normal(protocol,MAX_PROTOCOL_BYTES);research=_validate(protocol)
    if not nonempty_text(assertion_id):raise ValueError('readiness assertion ID required')
    assertions={r['assertion_id']:r for r in research['readiness']['assertion_ledger']}
    if assertion_id not in assertions:raise ValueError('unknown readiness assertion')
    row={k:None for k in sorted(CANDIDATE_FIELDS)}
    row.update(kind='research_output_disclosure',readiness_assertion_id=assertion_id,
        gates_sha256=research['readiness']['gates_sha256'],assumptions=[],required_artifacts=[],unresolved_issues=[])
    return dict(schema_version=1,status='AWAITING_SUPPLIED_OUTPUT_DISCLOSURES',
        candidate_document=dict(schema_version=1,output_disclosures=[row]),
        selected_current_assertion=copy.deepcopy(assertions[assertion_id]),
        current_gate_ledger=copy.deepcopy(research['readiness']['gate_ledger']),protocol_changed=False,
        template_warning='Only the selected assertion ID and current gate hash are mechanical. Supply every output label, disclosure, confidence/relevance statement and person/date. No publication or approval is generated.',
        **NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY)


def _observations(protocol,research,document):
    if document is _ABSENT:return None
    document=_normal(document,MAX_PROTOCOL_BYTES);_shape(document,OBSERVATION_FIELDS)
    if document['protocol_sha256']!=digest(protocol):raise ValueError('artifact observation is not bound to original input')
    if not _hex(document['manifest_sha256']):raise ValueError('invalid observation manifest hash')
    engines=document['engine_sha256']
    if not isinstance(engines,dict) or not engines or any(not nonempty_text(k) or not _hex(v) for k,v in engines.items()):
        raise ValueError('invalid recorded implementation dictionary')
    rows=document['artifacts']
    if not isinstance(rows,list) or len(rows)>1000:raise ValueError('invalid observation rows')
    manifest=dict(schema_version=1,artifacts=[])
    for row in rows:
        _shape(row,OBSERVED_FIELDS)
        if row['status'] not in OBSERVED_STATUSES:raise ValueError('unknown recorded observation status')
        if row['observed_bytes'] is not None and (type(row['observed_bytes']) is not int or row['observed_bytes']<0):
            raise ValueError('invalid observed byte count')
        if row['observed_sha256'] is not None and not _hex(row['observed_sha256']):raise ValueError('invalid observed hash')
        if row['status']=='BYTES_MATCH' and (row['observed_sha256']!=row['sha256'] or row['observed_bytes']!=row['bytes']):
            raise ValueError('inconsistent recorded byte match')
        if row['acceptance_assessment']!='NOT_PERFORMED':raise ValueError('observation cannot assert acceptance')
        manifest['artifacts'].append({k:copy.deepcopy(row[k]) for k in MANIFEST_FIELDS})
    work={w['work_package_id']:w for w in research['work_packages']}
    validate_manifest(manifest,work)  # Metadata only; never open_root or check_file.
    if digest(manifest)!=document['manifest_sha256']:raise ValueError('observation manifest metadata mismatch')
    if document['uninspected_work_ids']!=sorted(set(work)-{r['work_package_id'] for r in rows}):raise ValueError('observation scope mismatch')
    matches=bool(rows) and all(r['status']=='BYTES_MATCH' for r in rows)
    if type(document['all_requested_bytes_match']) is not bool or document['all_requested_bytes_match']!=matches:raise ValueError('inconsistent observation summary')
    if document['census_claim']!='NOT_ESTABLISHED' or document['conclusion_readiness']!='NOT_READY':raise ValueError('observation authority cannot be promoted')
    if not nonempty_text(document['boundary']) or not nonempty_text(document['inspection_scope']):raise ValueError('observation scope required')
    return document


def _bundle(protocol,raw):
    if raw is _ABSENT:return None
    research_bundle.verify_bytes(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if canonical_json_bytes(parse_json(archive.read('protocol.json')))!=canonical_json_bytes(protocol):
            raise ValueError('bundle does not contain exact normalized pre-disclosure protocol')
        manifest=archive.read('manifest.json')
    return dict(bundle_manifest_sha256=hashlib.sha256(manifest).hexdigest(),bundle_bytes_sha256=hashlib.sha256(raw).hexdigest(),
        verification_scope='CURRENT_IMPLEMENTATION_INTERNAL_REPLAY_ONLY_NOT_AUTHENTICITY',
        protocol_scope='ORIGINAL_INPUT_BEFORE_THIS_APPEND_NOT_RESULTING_SELF_CONTAINING_BUNDLE')


def _prepare(protocol,document,observations=_ABSENT,bundle=_ABSENT):
    protocol=_normal(protocol,MAX_PROTOCOL_BYTES);document=_normal(document,MAX_DOCUMENT_BYTES)
    _shape(document,{'schema_version','output_disclosures'})
    rows=document['output_disclosures']
    if not isinstance(rows,list) or not 1<=len(rows)<=100:raise ValueError('requires 1 to 100 supplied disclosures')
    before=_validate(protocol)
    observed=_observations(protocol,before,observations);bundle_context=_bundle(protocol,bundle)
    bindings={k:None for k in ATTACHMENT_FIELDS}
    if observed is not None:bindings['artifact_observation_sha256']=digest(observed)
    if bundle_context is not None:
        for k in ('bundle_manifest_sha256','bundle_bytes_sha256'):bindings[k]=bundle_context[k]
    existing={r['release_id'] for r in protocol.get('output_disclosures',[])}
    assertions={r['assertion_id']:r for r in before['readiness']['assertion_ledger']}
    work={r['work_package_id']:r for r in before['work_packages']}
    checked=[]
    for row in rows:
        validate_candidate(row)
        if row['release_id'] in existing:raise ValueError('append cannot replace an existing disclosure')
        aid=row['readiness_assertion_id']
        if aid not in assertions or assertions[aid]['source_match_status']!='CURRENT_GATES' or row['gates_sha256']!=before['readiness']['gates_sha256']:
            raise ValueError('new disclosure must bind a current supplied readiness assertion')
        for required in row['required_artifacts']:
            wid=required['work_package_id']
            if wid not in work or work[wid].get('artifact_locator')!=required['artifact_locator']:
                raise ValueError('required artifact locator must match existing supplied work')
            matches=[] if observed is None else [r for r in observed['artifacts'] if r['work_package_id']==wid]
            if not matches:status='NO_SUPPLIED_OBSERVATION'
            else:
                r=matches[0]
                status=('RECORDED_BYTES_MATCH' if r['artifact_locator']==required['artifact_locator'] and r['sha256']==required['sha256'] and r['observed_sha256']==required['sha256'] and r['status']=='BYTES_MATCH' else 'RECORDED_MISMATCH_OR_UNVERIFIED')
            checked.append(dict(release_id=row['release_id'],required_artifact=copy.deepcopy(required),recorded_observation_status=status,
                live_bytes_checked=False,acceptance_assessment='NOT_PERFORMED'))
    candidate=copy.deepcopy(protocol);candidate.setdefault('output_disclosures',[]).extend(
        dict(copy.deepcopy(row),attachment_bindings=copy.deepcopy(bindings)) for row in rows)
    candidate=_normal(candidate,MAX_PROTOCOL_BYTES);after=_validate(candidate)
    if canonical_json_bytes({k:v for k,v in before.items() if k!='output_disclosures'})!=canonical_json_bytes({k:v for k,v in after.items() if k!='output_disclosures'}):
        raise ValueError('disclosure changed existing research results')
    target=dict(schema_version=1,target_type='supplied_output_disclosure',input_protocol_sha256=digest(protocol),
        candidate_document=copy.deepcopy(document),candidate_protocol_sha256=digest(candidate),
        appended_disclosures=copy.deepcopy(candidate['output_disclosures'][len(protocol.get('output_disclosures',[])):]),
        after_disclosure_context=copy.deepcopy(after['output_disclosures']),
        artifact_checks=checked,artifact_observation_context=None if observed is None else dict(
            supplied_document_sha256=digest(observed),protocol_sha256=observed['protocol_sha256'],
            recorded_engine_sha256=copy.deepcopy(observed['engine_sha256']),recorded_engine_verified=False,
            live_bytes_checked=False,scope='SUPPLIED_OBSERVATION_METADATA_ONLY'),
        bundle_context=bundle_context,engine_sha256=_hashes(),negative_claims=copy.deepcopy(NEGATIVE_CLAIMS),boundary=INTAKE_BOUNDARY)
    target['target_sha256']=digest(target)
    return protocol,document,candidate,target


def prepare(protocol,document,observations=_ABSENT,bundle=_ABSENT):
    _,_,_,target=_prepare(protocol,document,observations,bundle)
    review={k:None for k in sorted(REVIEW_FIELDS)};review.update(schema_version=1,target_sha256=target['target_sha256'])
    return _normal(dict(schema_version=1,status='AWAITING_SUPPLIED_DISCLOSURE_REVIEW',target=target,review_document=review,
        protocol_changed=False,**NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY),MAX_APPLICATION_BYTES)


def assemble(protocol,document,review,observations=_ABSENT,bundle=_ABSENT):
    review=_normal(review,MAX_DOCUMENT_BYTES);_shape(review,REVIEW_FIELDS)
    if any(not nonempty_text(review[k]) for k in REVIEW_FIELDS-{'schema_version'}):raise ValueError('review fields must be supplied')
    iso_date(review['reviewed_at'],'reviewed_at')
    protocol,document,candidate,target=_prepare(protocol,document,observations,bundle)
    if review['decision']!='record_supplied_disclosures' or review['target_sha256']!=target['target_sha256']:
        raise ValueError('review does not authorize this exact record target')
    receipt=dict(schema_version=1,candidate_document=document,assertion=review,target=target,
        input_protocol_sha256=digest(protocol),protocol_candidate_sha256=digest(candidate),
        engine_sha256=_hashes(),**NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY)
    receipt['receipt_sha256']=digest(receipt)
    return _normal(dict(schema_version=1,kind='detached_output_disclosure',receipt=receipt,protocol_candidate=candidate),MAX_APPLICATION_BYTES)


def verify(protocol,application,observations=_ABSENT,bundle=_ABSENT):
    application=_normal(application,MAX_APPLICATION_BYTES);_shape(application,{'schema_version','kind','receipt','protocol_candidate'})
    if application['kind']!='detached_output_disclosure' or not isinstance(application['receipt'],dict):raise ValueError('wrong application kind')
    r=application['receipt'];replayed=assemble(protocol,r['candidate_document'],r['assertion'],observations,bundle)
    if canonical_json_bytes(replayed)!=canonical_json_bytes(application):raise ValueError('application differs from exact replay')
    return dict(schema_version=1,valid=True,status='EXACT_REPLAY_MATCH',receipt_sha256=r['receipt_sha256'],
        protocol_changed=False,**NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY)


def _write(path,value):
    try:path.lstat()
    except FileNotFoundError:pass
    else:raise FileExistsError('output exists')
    with path.open('xb') as stream:stream.write((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('template','target','assemble','verify'):
        sub=commands.add_parser(name);sub.add_argument('protocol',type=Path);sub.add_argument('--output',type=Path)
        if name=='template':sub.add_argument('assertion_id')
        else:
            sub.add_argument('--artifact-observations',type=Path);sub.add_argument('--bundle',type=Path)
        if name in ('target','assemble'):sub.add_argument('candidate_document',type=Path)
        if name=='assemble':sub.add_argument('review_document',type=Path)
        if name=='verify':sub.add_argument('application_record',type=Path);sub.add_argument('--protocol-output',type=Path)
    args=parser.parse_args()
    try:
        protocol=parse_json(read_bounded(args.protocol,MAX_PROTOCOL_BYTES))
        if args.command=='template':result=template(protocol,args.assertion_id)
        else:
            observed=(_ABSENT if args.artifact_observations is None else parse_json(read_bounded(args.artifact_observations,MAX_PROTOCOL_BYTES)))
            bundle=(_ABSENT if args.bundle is None else read_bounded(args.bundle,research_bundle.MAX_BUNDLE_BYTES+research_bundle.ZIP_HEADER_OVERHEAD))
            if args.command=='verify':
                app=parse_json(read_bounded(args.application_record,MAX_APPLICATION_BYTES));result=verify(protocol,app,observed,bundle)
                if args.protocol_output:_write(args.protocol_output,app['protocol_candidate'])
            else:
                document=parse_json(read_bounded(args.candidate_document,MAX_DOCUMENT_BYTES))
                result=(prepare(protocol,document,observed,bundle) if args.command=='target' else assemble(protocol,document,
                    parse_json(read_bounded(args.review_document,MAX_DOCUMENT_BYTES)),observed,bundle))
        if args.output:_write(args.output,result)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    except (OSError,ValueError,TypeError,KeyError,OverflowError,RecursionError,AttributeError,zipfile.BadZipFile,RuntimeError,NotImplementedError,EOFError):
        parser.exit(1,'output_disclosure_intake: invalid input or unavailable output\n')


if __name__=='__main__':main()
