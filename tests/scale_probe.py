"""Explicit opt-in synthetic scale observations, never a performance or safety guarantee."""
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import time

ROOT=Path(__file__).resolve().parents[1]
PROFILES={
    'smoke':dict(records=200,results=50,work=20,searches=2,statement_width=4),
    'moderate':dict(records=4000,results=1000,work=300,searches=4,statement_width=4),
    'large':dict(records=40000,results=10000,work=3000,searches=4,statement_width=4),
}
MAX_INPUT_BYTES=50_000_000
MAX_OUTPUT_BYTES=50_000_000
MAX_RECEIPT_BYTES=1_000_000
BOUNDARY=('One opt-in local synthetic observation in this process, not a performance SLA, general linearity, '
    'memory/CPU safety, scientific validation or external interoperability result. Shape fixes one result '
    'per included record, one evidence link per work package, disjoint statements of at most four results, '
    'and no contexts, units, appraisals, report stage or external data. Wider cross-links can grow '
    'quadratically and are outside this envelope. Times exclude imports and vary by environment; '
    'generation, input serialization, product computation and output serialization are measured separately. '
    'Output budgets apply after a product has computed its result, not before allocation. Only complete '
    'outputs have full byte counts/hashes. No product limit, schema, gate, file or supplied review is changed.')


def generate(shape):
    if type(shape) is not dict or set(shape)!=set(PROFILES['smoke']):raise ValueError('exact shape fields required')
    if any(type(value) is not int for value in shape.values()):raise ValueError('integer shape required')
    n,r,w,s,width=(shape[k] for k in ('records','results','work','searches','statement_width'))
    if not (1<=n<=40000 and 1<=r<=min(n,10000) and 0<=w<=min(r,3000) and 1<=s<=min(n,4) and 1<=width<=4):
        raise ValueError('shape exceeds the explicit narrow synthetic budget')
    seed=json.loads((ROOT/'examples/review-demo.json').read_bytes())
    value={k:copy.deepcopy(seed[k]) for k in ('question','version','inclusion_criteria','exclusion_criteria')}
    value['question']='Fictional bounded scale rehearsal only';value['version']='synthetic-scale-v1'
    ids=['synthetic-r'+str(i) for i in range(n)]
    value['searches']=[dict(source='synthetic',query='fictional local records',searched_at='2026-01-01',window='synthetic',
        record_ids=ids[i::s],total_count=len(ids[i::s]),complete=True,has_more=False) for i in range(s)]
    value['screening']=[dict(record_id=rid,decision='include' if i<r else 'exclude',reason='synthetic only') for i,rid in enumerate(ids)]
    value['evidence']=[]
    for i in range(r):
        row=copy.deepcopy(seed['evidence'][0]);row.update(record_id=ids[i],evidence_id='synthetic-e'+str(i),study_id='synthetic-s'+str(i));value['evidence'].append(row)
    value['gaps']=[dict(work_package_id='synthetic-w'+str(i),question='fictional',evidence_ids=['synthetic-e'+str(i)],
        deliverable='synthetic only',acceptance_criterion='supplied human review required',context='fictional') for i in range(w)]
    value['synthesis_statements']=[dict(statement_id='synthetic-statement'+str(i),text='Fictional bounded statement',limitations='Synthetic only',
        evidence_ids=['synthetic-e'+str(j) for j in range(i,min(i+width,r))],review_status='pending') for i in range(0,r,width)]
    return value


def output_observation(value,limit=MAX_OUTPUT_BYTES):
    """Hash only a fully encoded output; an over-budget observation is not a full hash."""
    if type(limit) is not int or not 0<=limit<=MAX_OUTPUT_BYTES:raise ValueError('invalid output budget')
    h=hashlib.sha256();count=0
    chunks=(value,) if type(value) is bytes else (piece.encode('utf-8') for piece in json.JSONEncoder(ensure_ascii=False,indent=2,allow_nan=False).iterencode(value))
    for chunk in chunks:
        count+=len(chunk)
        if count>limit:return dict(status='OUTPUT_BUDGET_EXCEEDED',bytes=None,sha256=None,observed_at_least_bytes=count)
        h.update(chunk)
    if type(value) is not bytes:
        count+=1
        if count>limit:return dict(status='OUTPUT_BUDGET_EXCEEDED',bytes=None,sha256=None,observed_at_least_bytes=count)
        h.update(b'\n')
    return dict(status='COMPLETE',bytes=count,sha256=h.hexdigest(),observed_at_least_bytes=count)


def _operations(protocol,raw):
    from evidence_workflow import run
    from research_status import status
    from synthesis_review import snapshot
    from work_review import review_packets
    from review_handoff import handoff
    from compare_runs import compare_protocols
    from research_bundle import build_bundle,verify_bytes
    retained={}
    def build():
        result=build_bundle(raw);retained['bundle']=result;return result
    def verify():return verify_bytes(retained['bundle'])
    return [('engine',lambda:run(protocol)),('status',lambda:status(protocol)),('synthesis',lambda:snapshot(protocol)),
        ('work',lambda:review_packets(protocol)),('handoff',lambda:handoff(protocol)),
        ('self_comparison',lambda:compare_protocols(protocol,protocol)),('bundle_create',build),('bundle_verify',verify)]


def measure(profile,*,output_limit=MAX_OUTPUT_BYTES):
    if profile not in PROFILES:raise ValueError('unknown fixed profile')
    if type(output_limit) is not int or not 0<=output_limit<=MAX_OUTPUT_BYTES:raise ValueError('invalid output budget')
    # Load imports before timing product calls; these are warm-process observations.
    from json_io import canonical_json_bytes
    import research_bundle
    shape=copy.deepcopy(PROFILES[profile]);started=time.perf_counter();protocol=generate(shape);generation=time.perf_counter()-started
    started=time.perf_counter();raw=canonical_json_bytes(protocol);input_serialization=time.perf_counter()-started
    input_hash=hashlib.sha256(raw).hexdigest()
    receipt=dict(schema_version=1,kind='synthetic_scale_observation',observed_at_utc=datetime.now(timezone.utc).isoformat(),
        profile=profile,shape=shape,shape_details=dict(evidence_per_included_record=1,evidence_per_work=1,statement_groups='disjoint',
            contexts=0,experimental_units=0,appraisals=0,reports=0),
        environment=dict(python=platform.python_version(),implementation=platform.python_implementation(),system=platform.system(),release=platform.release(),machine=platform.machine()),
        input=dict(bytes=len(raw),sha256=input_hash,hash_scope='canonical compact UTF-8 JSON',budget_bytes=MAX_INPUT_BYTES),
        generation_seconds=generation,input_serialization_seconds=input_serialization,output_budget_bytes=output_limit,
        output_hash_scope='complete UTF-8 indented JSON plus LF, or exact ZIP bytes; no platform newline translation',
        measurements=[],input_unchanged=None,external_calls=0,scientific_assessment='NOT_PERFORMED',boundary=BOUNDARY)
    names={path.name for path in ROOT.glob('*.py')}
    receipt['implementation_hash_scope']='All root Python files in this checkout; inventory, not dependency tracing or authentication'
    receipt['resource_measurements']='PEAK_MEMORY_AND_CPU_NOT_MEASURED'
    receipt['implementation_sha256']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(names)}
    receipt['probe_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    receipt['seed_sha256']=hashlib.sha256((ROOT/'examples/review-demo.json').read_bytes()).hexdigest()
    if len(raw)>MAX_INPUT_BYTES:
        receipt['status']='INPUT_BUDGET_EXCEEDED';return receipt
    failed_build=False
    for name,operation in _operations(protocol,raw):
        if name=='bundle_verify' and failed_build:
            receipt['measurements'].append(dict(operation=name,status='NOT_RUN_PREREQUISITE_FAILED',computation_seconds=None,serialization_seconds=None,output=None));continue
        start=time.perf_counter()
        try:value=operation()
        except (ValueError,TypeError,KeyError,OSError,RecursionError,OverflowError) as error:
            elapsed=time.perf_counter()-start
            receipt['measurements'].append(dict(operation=name,status='PRODUCT_REFUSED',computation_seconds=elapsed,serialization_seconds=None,output=None,error_type=type(error).__name__))
            if name=='bundle_create':failed_build=True
            continue
        computation=time.perf_counter()-start;start=time.perf_counter()
        try:observation=output_observation(value,output_limit)
        except (ValueError,TypeError,RecursionError,OverflowError) as error:
            receipt['measurements'].append(dict(operation=name,status='SERIALIZATION_REFUSED',computation_seconds=computation,serialization_seconds=time.perf_counter()-start,output=None,error_type=type(error).__name__))
            continue
        receipt['measurements'].append(dict(operation=name,status=observation['status'],computation_seconds=computation,serialization_seconds=time.perf_counter()-start,output=observation))
        del value
    receipt['input_unchanged']=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest()==input_hash
    receipt['status']='COMPLETE' if receipt['input_unchanged'] and all(r['status']=='COMPLETE' for r in receipt['measurements']) else 'INCOMPLETE_OBSERVATION'
    return receipt


def main():
    from json_io import configure_utf8_stdio
    from output_io import write_new
    configure_utf8_stdio();parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',required=True,help='explicitly opt in to local synthetic computation')
    parser.add_argument('--profile',choices=sorted(PROFILES),required=True)
    parser.add_argument('--output',type=Path,help='optional exclusive observation receipt; no payload files')
    args=parser.parse_args()
    try:
        result=measure(args.profile);raw=(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
        if len(raw)>MAX_RECEIPT_BYTES:raise ValueError('receipt budget exceeded')
        if args.output is not None:write_new(args.output,raw)
    except (OSError,ValueError,TypeError,KeyError,RecursionError,OverflowError):
        parser.exit(1,'scale probe: invalid local observation or unavailable output\n')
    print(raw.decode('utf-8'),end='')
    if result['status']!='COMPLETE':parser.exit(1)


if __name__=='__main__':main()
