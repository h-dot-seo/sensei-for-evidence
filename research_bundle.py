"""Create and verify deterministic offline research bundles without extracting archives."""
import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from evidence_workflow import run
from prisma_reports import report_flow

ENGINE_FILES = ('evidence_workflow.py', 'prisma_reports.py', 'context_links.py', 'search_audit.py', 'research_bundle.py')

def engine_hashes():
    root = Path(__file__).resolve().parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ENGINE_FILES}

def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('invalid JSON numeric constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)

PAYLOADS={'protocol.json','research.json','reports.json','reports.csv','work-packages.csv','summary.md'}


def json_bytes(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')


def build_bundle(raw):
    protocol=parse_json(raw.decode('utf-8'))
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be a JSON object')
    research=run(protocol)
    reports=report_flow(protocol) if 'reports' in protocol else None
    csv_text=reports.pop('report_csv') if reports is not None else 'report_id,record_ids,retrieval,decision,reason,study_id,locator\n'
    out=io.StringIO(newline=''); writer=csv.writer(out,lineterminator='\n')
    columns=['work_package_id','status','question','deliverable','acceptance_criterion','evidence_ids','depends_on','blocked_by','context_ids']
    writer.writerow(columns)
    def safe(value):
        text=json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else str(value)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    for wp in sorted(research['work_packages'],key=lambda w:w['work_package_id']):
        writer.writerow([safe(wp.get(c,'')) for c in columns])
    summary=('Research bundle\n===============\n\n'
             'Supplied-data bookkeeping only; not independently verified research.\n'
             f"Identified records: {research['flow']['identified']}\n"
             f"Screening pending: {research['flow']['pending']}\n"
             f"Declared search plan: {research['search_plan_audit']['plan_status']}\n"
             f"Missing planned searches: {len(research['search_plan_audit']['missing_search_ids'])}\n"
             f"Incomplete planned searches: {len(research['search_plan_audit']['incomplete_search_ids'])}\n"
             f"Included reports: {reports['report_flow']['included'] if reports is not None else 'not supplied'}\n"
             f"Included studies: {reports['report_flow']['included_studies'] if reports is not None else 'not supplied'}\n"
             f"Work packages: {len(research['work_packages'])}\n"
             f"Context review pending: {len(research['context']['review_pending'])}\n"
             'Census: NOT_ESTABLISHED\nConclusion: NOT_READY\n')
    payloads={'protocol.json':raw,'research.json':json_bytes(research),'reports.json':json_bytes(reports),
              'reports.csv':csv_text.encode(),'work-packages.csv':out.getvalue().encode(),'summary.md':summary.encode()}
    manifest=dict(schema_version=2,engine_sha256=engine_hashes(),input_sha256=hashlib.sha256(raw).hexdigest(),
        files=[dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in sorted(payloads.items())])
    payloads['manifest.json']=json_bytes(manifest)
    target=io.BytesIO()
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,data in sorted(payloads.items()):
            entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            entry.external_attr=0o100600 << 16
            archive.writestr(entry,data)
    return target.getvalue()


def create(protocol_path, destination):
    data=build_bundle(Path(protocol_path).read_bytes())
    # Exclusive creation: never replace a previous research receipt.
    with Path(destination).open('xb') as stream:
        stream.write(data)
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),files=len(PAYLOADS)+1)


def verify(path):
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist(); names=[e.filename for e in entries]
        if len(names)!=len(set(names)) or set(names)!=PAYLOADS|{'manifest.json'}:
            raise ValueError('unexpected, missing or duplicate archive entries')
        if sum(e.file_size for e in entries)>50_000_000:
            raise ValueError('bundle exceeds verification size limit')
        manifest=parse_json(archive.read('manifest.json'))
        if manifest.get('schema_version')!=2:
            raise ValueError('unsupported bundle schema')
        if manifest.get('engine_sha256') != engine_hashes():
            raise ValueError('engine bytes differ; verify using the recorded implementation')
        listed=[r['path'] for r in manifest['files']]
        if len(listed)!=len(PAYLOADS) or set(listed)!=PAYLOADS:
            raise ValueError('invalid manifest file set')
        for item in manifest['files']:
            data=archive.read(item['path'])
            if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
                raise ValueError('bundle payload hash mismatch: '+item['path'])
        raw=archive.read('protocol.json')
        if hashlib.sha256(raw).hexdigest()!=manifest['input_sha256']:
            raise ValueError('input hash mismatch')
        # Recompute derived outputs, not just attacker-editable manifest hashes.
        expected=build_bundle(raw)
        with zipfile.ZipFile(io.BytesIO(expected)) as rebuilt:
            if any(archive.read(name)!=rebuilt.read(name) for name in PAYLOADS):
                raise ValueError('derived artifacts disagree with protocol')
    return dict(valid=True,files=len(names),census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',scope='internal hashes and deterministic derivation; no source authenticity attestation')


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('create'); c.add_argument('protocol',type=Path); c.add_argument('output',type=Path)
    v=sub.add_parser('verify'); v.add_argument('bundle',type=Path)
    a=p.parse_args()
    try: result=create(a.protocol,a.output) if a.command=='create' else verify(a.bundle)
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,zipfile.BadZipFile) as e: p.exit(1,str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
