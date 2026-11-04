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
from csv_safety import safe_csv_cell
from json_io import parse_json, configure_utf8_stdio

ENGINE_FILES = ('evidence_workflow.py', 'prisma_reports.py', 'context_links.py', 'search_audit.py', 'csv_safety.py', 'appraisal_links.py', 'json_io.py', 'adapter_integrity.py', 'offline_adapter.py', 'planning_links.py', 'synthesis_links.py', 'experiment_links.py', 'research_bundle.py', 'bibliographic_integrity.py', 'csv_export_parser.py', 'bibliographic_intake.py', 'bibliographic_review.py', 'report_links.py', 'screening_links.py')

def engine_hashes():
    root = Path(__file__).resolve().parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ENGINE_FILES}

MAX_BUNDLE_BYTES = 50_000_000  # Sum of uncompressed entry bytes, including manifest.

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
    columns=['work_package_id','status','question','deliverable','acceptance_criterion','evidence_ids','depends_on','blocked_by','context_ids','context_review_pending','appraisal_ids','evidence_without_recorded_appraisal','supplied_priority_rank','current_priority_rank','planning_source_status','planning_rationale','planning_uncertainty','planner','planned_at','planning_basis_sha256','current_planning_basis_sha256','experimental_unit_ids','evidence_without_experimental_unit','experimental_stage','units_without_outcome_sampling','units_with_unresolved_sampling','units_without_outcome_statistics','units_with_statistics_review_cues','linked_synthesis_statement_ids','work_type','source_refs']
    columns += ['supplied_artifact_locator','supplied_acceptance_verified','completion_source_status',
                'supplied_completion_basis_sha256','current_completion_basis_sha256',
                'completion_acceptance_assessment','completion_artifact_content_verification',
                'direct_prerequisite_completion_sources']
    writer.writerow(columns)
    def safe(value):
        text=json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else str(value)
        return safe_csv_cell(text)
    context_by_work = {row['work_package_id']: row for row in research['context']['work_package_context']}
    appraisal_by_work = {row['work_package_id']: row for row in research['appraisal']['work_package_appraisals']}
    planning_by_work = {row['work_package_id']: row for row in research['planning']['planning_ledger']}
    completion_by_work = {row['work_package_id']: row for row in research['planning']['completion_ledger']}
    work_by_id = {row['work_package_id']: row for row in research['work_packages']}
    for wp in sorted(research['work_packages'],key=lambda w:w['work_package_id']):
        wid = wp['work_package_id']
        exported = dict(wp, work_type=wp.get('work_type','evidence_review'), source_refs=wp.get('source_refs',[]), context_review_pending=context_by_work[wid]['context_review_pending'],
                        appraisal_ids=appraisal_by_work[wid]['appraisal_ids'],
                        evidence_without_recorded_appraisal=appraisal_by_work[wid]['evidence_without_recorded_appraisal'])
        completion = completion_by_work[wid]
        exported.update(supplied_artifact_locator=wp.get('artifact_locator', ''),
                        supplied_acceptance_verified=wp.get('acceptance_verified', ''),
                        completion_source_status=completion['source_match_status'],
                        supplied_completion_basis_sha256=completion['supplied_basis_sha256'] or '',
                        current_completion_basis_sha256=completion['current_basis_sha256'],
                        completion_acceptance_assessment=completion['acceptance_assessment'],
                        completion_artifact_content_verification=completion['artifact_content_verification'],
                        direct_prerequisite_completion_sources=[dict(work_package_id=dep,
                            supplied_work_status=work_by_id[dep]['status'],
                            source_match_status=completion_by_work[dep]['source_match_status']) for dep in wp['depends_on']])
        planning = planning_by_work[wid]
        assertion = planning['assertion'] or {}
        exported.update(supplied_priority_rank=assertion.get('priority_rank', ''),
                        current_priority_rank=planning['current_priority_rank'] if planning['current_priority_rank'] is not None else '',
                        planning_source_status=planning['source_match_status'],
                        planning_rationale=assertion.get('rationale', ''), planning_uncertainty=assertion.get('uncertainty', ''),
                        planner=assertion.get('planner', ''), planned_at=assertion.get('planned_at', ''),
                        planning_basis_sha256=assertion.get('basis_sha256', ''),
                        current_planning_basis_sha256=planning['current_basis_sha256'],
                        linked_synthesis_statement_ids=sorted(statement['statement_id'] for statement in research['synthesis']['statement_ledger'] if set(wp['evidence_ids']).intersection(statement['evidence_ids'])) if research['synthesis']['stage'] == 'SUPPLIED' else 'not supplied',
                        experimental_stage=research['experiments']['stage'],
                        units_without_outcome_statistics=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if 'outcome_statistics' not in unit and set(wp['evidence_ids']).intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else 'not supplied',
                        units_with_statistics_review_cues=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if (unit.get('statistics_review', {}).get('missing_fields') or unit.get('statistics_review', {}).get('literal_label_differences')) and set(wp['evidence_ids']).intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else 'not supplied',
                        units_without_outcome_sampling=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if 'outcome_sampling' not in unit and set(wp['evidence_ids']).intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else 'not supplied',
                        units_with_unresolved_sampling=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if unit.get('sampling_review', {}).get('unresolved_fields') and set(wp['evidence_ids']).intersection(unit['evidence_ids'])) if research['experiments']['stage'] == 'SUPPLIED' else 'not supplied',
                        experimental_unit_ids=sorted(unit['experiment_id'] for unit in research['experiments']['experimental_unit_ledger'] if set(wp['evidence_ids']).intersection(unit['evidence_ids'])),
                        evidence_without_experimental_unit=sorted(set(wp['evidence_ids']).intersection(research['experiments']['evidence_without_experimental_unit'])) if research['experiments']['stage'] == 'SUPPLIED' else 'not supplied')
        writer.writerow([safe(exported.get(c,'')) for c in columns])
    summary=('Research bundle\n===============\n\n'
             'Supplied-data bookkeeping only; not independently verified research.\n'
             f"Identified record occurrences: {research['flow']['identified']}\n"
             f"Distinct supplied record IDs: {research['flow']['unique_records']}\n"
             f"Repeated exact-ID occurrences: {research['flow']['duplicates']}\n"
             'Deduplication: exact supplied IDs only; identities not independently verified.\n'
             f"Screening pending: {research['flow']['pending']}\n"
             f"Declared search plan: {research['search_plan_audit']['plan_status']}\n"
             f"Missing planned searches: {len(research['search_plan_audit']['missing_search_ids'])}\n"
             f"Incomplete planned searches: {len(research['search_plan_audit']['incomplete_search_ids'])}\n"
             f"Included reports: {reports['report_flow']['included'] if reports is not None else 'not supplied'}\n"
             f"Included studies: {reports['report_flow']['included_studies'] if reports is not None else 'not supplied'}\n"
             f"Included reports without extraction: {len(reports['extraction_pending_reports']) if reports is not None else 'not supplied'}\n"
             f"Extracted result rows: {research['flow']['extracted']}\n"
             f"Source records with extraction: {research['flow']['extracted_records']}\n"
             f"Study IDs with extraction: {research['flow']['extracted_studies']}\n"
             f"Structured comparison condition stage: {research['experiments']['stage']}\n"
             f"Supplied condition records: {len(research['experiments']['experimental_unit_ledger']) if research['experiments']['stage'] == 'SUPPLIED' else 'not supplied'}\n"
             'Condition records are not independent replicate counts; causal assessment is not performed.\n'
             'Sampling queues in work-packages.csv cover full intersecting condition records, including sibling outcomes.\n'
             'Reported n values are not pooled or validated; independence and numeric consistency are not assessed.\n'
             'Statistics queues cover full intersecting condition records; literal label differences are not incompatibility findings.\n'
             'Effect direction and statistical claims are supplied text, not computed or assessed.\n'
             f"Synthesis statement stage: {research['synthesis']['stage']}\n"
             f"Pending supplied statement reviews: {len(research['synthesis']['pending_statement_ids']) if research['synthesis']['stage'] == 'SUPPLIED' else 'not supplied'}\n"
             f"Stale supplied statement reviews: {len(research['synthesis']['stale_statement_ids']) if research['synthesis']['stage'] == 'SUPPLIED' else 'not supplied'}\n"
             'Citation links do not establish support for supplied synthesis statements.\n'
             'Supplied claim positions are not votes or inferred support, refutation or causality.\n'
             'Source-review work may precede extraction; its completion assertion does not approve a receipt or establish scientific readiness.\n'
             f"Work packages: {len(research['work_packages'])}\n"
             f"Completed work without source binding: {sum(row['source_match_status'] == 'UNBOUND_COMPLETION' for row in completion_by_work.values())}\n"
             f"Completed work with stale source binding: {sum(row['source_match_status'] == 'STALE_SOURCE' for row in completion_by_work.values())}\n"
             'Completion-source matches are not artifact-byte verification or acceptance; recorded work states are unchanged.\n'
             'CSV prerequisite completion-source labels cover direct supplied links only, not recursive acceptance.\n'
             f"Work without supplied planning ranks: {len(research['planning']['work_without_planning_assertion'])}\n"
             f"Work with stale planning source bindings: {len(research['planning']['work_with_stale_planning_assertion'])}\n"
             'Planning ranks are supplied assertions, not advice; dependencies remain separate.\n'
             f"Context review pending: {len(research['context']['review_pending'])}\n"
             f"Result rows without recorded appraisal: {len(research['appraisal']['evidence_without_recorded_appraisal'])}\n"
             'Census: NOT_ESTABLISHED\nConclusion: NOT_READY\n')
    payloads={'protocol.json':raw,'research.json':json_bytes(research),'reports.json':json_bytes(reports),
              'reports.csv':csv_text.encode(),'work-packages.csv':out.getvalue().encode(),'summary.md':summary.encode()}
    manifest=dict(schema_version=2,engine_sha256=engine_hashes(),input_sha256=hashlib.sha256(raw).hexdigest(),
        files=[dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in sorted(payloads.items())])
    payloads['manifest.json']=json_bytes(manifest)
    if sum(len(data) for data in payloads.values()) > MAX_BUNDLE_BYTES:
        raise ValueError('bundle exceeds verification size limit')
    target=io.BytesIO()
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,data in sorted(payloads.items()):
            entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            entry.create_system=3  # Fixed creator metadata across Windows and Unix.
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
        if sum(e.file_size for e in entries)>MAX_BUNDLE_BYTES:
            raise ValueError('bundle exceeds verification size limit')
        manifest=parse_json(archive.read('manifest.json'))
        if not isinstance(manifest, dict):
            raise ValueError('bundle manifest must be an object')
        if type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 2:
            raise ValueError('unsupported bundle schema')
        if manifest.get('engine_sha256') != engine_hashes():
            raise ValueError('engine bytes differ; verify using the recorded implementation')
        files = manifest.get('files')
        if not isinstance(files, list) or any(not isinstance(row, dict) for row in files):
            raise ValueError('manifest files must be a list of objects')
        for row in files:
            if (not isinstance(row.get('path'), str) or type(row.get('bytes')) is not int
                    or row['bytes'] < 0 or not isinstance(row.get('sha256'), str)):
                raise ValueError('invalid manifest file metadata')
        listed=[r['path'] for r in files]
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
    configure_utf8_stdio()
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('create'); c.add_argument('protocol',type=Path); c.add_argument('output',type=Path)
    v=sub.add_parser('verify'); v.add_argument('bundle',type=Path)
    a=p.parse_args()
    try: result=create(a.protocol,a.output) if a.command=='create' else verify(a.bundle)
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,zipfile.BadZipFile) as e: p.exit(1,str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
