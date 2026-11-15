"""Append a supplied amendment after separate exact two-snapshot review; never close gates."""
import argparse
import copy
import json
from pathlib import Path
import hashlib
from evidence_workflow import run
from prisma_reports import report_flow
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json
from archive_safety import read_bounded
from output_io import write_new
from nbib_intake import _strict_json
from context_links import nonempty_text, iso_date
import research_bundle
from amendment_links import FIELDS, MAX_ROWS, BOUNDARY, NEGATIVE_CLAIMS, digest, validate_row, paired_observation

MAX_PROTOCOL_BYTES=50_000_000
MAX_DOCUMENT_BYTES=10_000_000
MAX_APPLICATION_BYTES=50_000_000
REVIEW_FIELDS={'schema_version','receipt_id','target_sha256','decision','reviewer','reviewed_at','rationale'}
INTAKE_BOUNDARY=BOUNDARY+(' The target binds the exact BEFORE, human-edited AFTER, supplied row and implementation. '
    'The embedded row has no after hash, avoiding self-reference; the detached receipt binds both snapshots '
    'and the appended protocol. All older rows and every other AFTER value are preserved. Supplied review '
    'is not authenticated permission. Hash-consistent reauthored unsigned records can replay. Old records '
    'require their original implementation. Outputs are exclusive, not an atomic multi-file transaction; '
    'earlier or partial files may remain after a later write failure.')


def _normal(value,limit):
    _strict_json(value);raw=canonical_json_bytes(value)
    if len(raw)>limit:raise ValueError('input or output byte limit exceeded')
    return parse_json(raw)


def _shape(value,fields):
    if type(value) is not dict or set(value)!=fields:raise ValueError('exact fields required')
    if type(value.get('schema_version')) is not int or value['schema_version']!=1:raise ValueError('schema_version 1 required')


def _validate(protocol):
    result=run(protocol)
    if 'reports' in protocol:report_flow(protocol,include_csv=False)
    return result


def _inputs(before,after):
    before=_normal(before,MAX_PROTOCOL_BYTES);after=_normal(after,MAX_PROTOCOL_BYTES)
    _validate(before);research=_validate(after)
    if canonical_json_bytes(before.get('amendments',[]))!=canonical_json_bytes(after.get('amendments',[])):
        raise ValueError('human-edited AFTER must preserve all older amendment rows')
    if any(not nonempty_text(p['version']) for p in (before,after)):
        raise ValueError('amendment recording requires supplied nonblank version strings')
    return before,after,research


def _hashes():
    return dict(research_bundle.engine_hashes(),**{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ('amendment_intake.py','nbib_intake.py','output_io.py')})


def template(before,after):
    before,after,_=_inputs(before,after)
    row={k:None for k in sorted(FIELDS)}
    row.update(before_protocol_sha256=digest(before),from_version=before['version'],to_version=after['version'])
    return dict(schema_version=1,status='AWAITING_SUPPLIED_AMENDMENT',candidate_document=dict(schema_version=1,amendment=row),
        observed_changed_fields=sorted(k for k in set(before)|set(after) if k!='amendments' and
            (k not in before or k not in after or canonical_json_bytes(before[k])!=canonical_json_bytes(after[k]))),
        protocol_changed=False,template_warning='Supply the ID, reason, author/date, scope and references. Null fields are not a valid candidate; no human judgment is generated.',
        **NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY)


def _prepare(before,after,document):
    before,after,research=_inputs(before,after);document=_normal(document,MAX_DOCUMENT_BYTES)
    _shape(document,{'schema_version','amendment'});row=document['amendment'];validate_row(row)
    if row['amendment_id'] in {r['amendment_id'] for r in after.get('amendments',[])}:raise ValueError('append cannot replace an amendment')
    observation=paired_observation(before,after,row)
    if observation['binding_status']!='RECORDED_BEFORE_AND_SCOPE_MATCH':raise ValueError('supplied amendment does not match the exact BEFORE/AFTER and scope')
    candidate=copy.deepcopy(after);candidate.setdefault('amendments',[]).append(copy.deepcopy(row))
    candidate=_normal(candidate,MAX_PROTOCOL_BYTES);result=_validate(candidate)
    clean=lambda r:{k:v for k,v in r.items() if k!='amendments'}
    if canonical_json_bytes(clean(research))!=canonical_json_bytes(clean(result)):
        raise ValueError('recording amendment changed existing AFTER research results')
    target=dict(schema_version=1,target_type='supplied_amendment',before_protocol_sha256=digest(before),
        after_input_protocol_sha256=digest(after),candidate_document=copy.deepcopy(document),
        candidate_protocol_sha256=digest(candidate),paired_observation=observation,
        appended_context=copy.deepcopy(result['amendments']['amendment_ledger'][-1]),engine_sha256=_hashes(),
        **NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY)
    target['target_sha256']=digest(target)
    return before,after,document,candidate,target


def prepare(before,after,document):
    *_,target=_prepare(before,after,document)
    review={k:None for k in sorted(REVIEW_FIELDS)};review.update(schema_version=1,target_sha256=target['target_sha256'])
    return _normal(dict(schema_version=1,status='AWAITING_SUPPLIED_AMENDMENT_REVIEW',target=target,review_document=review,
        protocol_changed=False,**NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY),MAX_APPLICATION_BYTES)


def assemble(before,after,document,review):
    review=_normal(review,MAX_DOCUMENT_BYTES);_shape(review,REVIEW_FIELDS)
    if any(not nonempty_text(review[k]) for k in REVIEW_FIELDS-{'schema_version'}):raise ValueError('review fields must be supplied')
    iso_date(review['reviewed_at'],'reviewed_at')
    before,after,document,candidate,target=_prepare(before,after,document)
    if review['decision']!='record_supplied_amendment' or review['target_sha256']!=target['target_sha256']:
        raise ValueError('review does not bind this exact amendment target')
    receipt=dict(schema_version=1,candidate_document=document,assertion=review,target=target,
        before_protocol_sha256=digest(before),after_input_protocol_sha256=digest(after),protocol_candidate_sha256=digest(candidate),
        engine_sha256=_hashes(),**NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY)
    receipt['receipt_sha256']=digest(receipt)
    return _normal(dict(schema_version=1,kind='detached_amendment',receipt=receipt,protocol_candidate=candidate),MAX_APPLICATION_BYTES)


def verify(before,after,application):
    application=_normal(application,MAX_APPLICATION_BYTES);_shape(application,{'schema_version','kind','receipt','protocol_candidate'})
    if application['kind']!='detached_amendment' or type(application['receipt']) is not dict:raise ValueError('wrong application kind')
    receipt=application['receipt'];replay=assemble(before,after,receipt['candidate_document'],receipt['assertion'])
    if canonical_json_bytes(replay)!=canonical_json_bytes(application):raise ValueError('application differs from exact replay')
    return dict(schema_version=1,valid=True,status='EXACT_REPLAY_MATCH',receipt_sha256=receipt['receipt_sha256'],
        protocol_changed=False,**NEGATIVE_CLAIMS,boundary=INTAKE_BOUNDARY)


def _write(path,value):
    value=_normal(value,MAX_APPLICATION_BYTES)
    write_new(path,(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def main():
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('template','target','assemble','verify'):
        sub=commands.add_parser(name);sub.add_argument('before',type=Path);sub.add_argument('after',type=Path);sub.add_argument('--output',type=Path)
        if name in ('target','assemble'):sub.add_argument('candidate_document',type=Path)
        if name=='assemble':sub.add_argument('review_document',type=Path)
        if name=='verify':sub.add_argument('application_record',type=Path);sub.add_argument('--protocol-output',type=Path)
    args=parser.parse_args()
    try:
        before=parse_json(read_bounded(args.before,MAX_PROTOCOL_BYTES));after=parse_json(read_bounded(args.after,MAX_PROTOCOL_BYTES))
        if args.command=='template':result=template(before,after)
        elif args.command=='verify':
            app=parse_json(read_bounded(args.application_record,MAX_APPLICATION_BYTES));result=verify(before,after,app)
            if args.protocol_output:_write(args.protocol_output,app['protocol_candidate'])
        else:
            document=parse_json(read_bounded(args.candidate_document,MAX_DOCUMENT_BYTES))
            result=prepare(before,after,document) if args.command=='target' else assemble(before,after,document,parse_json(read_bounded(args.review_document,MAX_DOCUMENT_BYTES)))
        result=_normal(result,MAX_APPLICATION_BYTES)
        if args.output:_write(args.output,result)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    except (OSError,ValueError,TypeError,KeyError,OverflowError,RecursionError,AttributeError):
        parser.exit(1,'amendment_intake: invalid supplied inputs or unavailable output\n')


if __name__=='__main__':main()
