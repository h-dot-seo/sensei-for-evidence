"""Build deterministic report retrieval/full-text screening ledgers from supplied records."""
import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path
from evidence_workflow import run
from context_links import nonempty_text
from csv_safety import safe_csv_cell


def report_flow(protocol):
    baseline = run(protocol)
    included_records = {r['record_id'] for r in protocol['screening'] if r['decision']=='include'}
    reports, linked = {}, set()
    if not isinstance(protocol['reports'], list):
        raise ValueError('reports must be a list')
    for report in protocol['reports']:
        if not isinstance(report, dict):
            raise ValueError('report must be an object')
        rid = report.get('report_id')
        if not nonempty_text(rid) or rid in reports:
            raise ValueError('unique report IDs required')
        record_ids = report['record_ids']
        if (not isinstance(record_ids,list) or not record_ids
                or any(not isinstance(r,str) or r not in included_records for r in record_ids)
                or len(record_ids) != len(set(record_ids))):
            raise ValueError('reports must link to included screening records')
        if linked.intersection(record_ids):
            raise ValueError('record mapped to multiple reports')
        linked.update(record_ids)
        retrieval = report['retrieval']
        if retrieval not in ('retrieved','not_retrieved','pending'):
            raise ValueError('invalid report retrieval state')
        decision = report.get('decision','pending')
        if decision not in ('include','exclude','pending'):
            raise ValueError('invalid full-text decision')
        if retrieval != 'retrieved' and decision != 'pending':
            raise ValueError('unretrieved report cannot have full-text decision')
        if retrieval == 'retrieved' and not nonempty_text(report.get('locator')):
            raise ValueError('retrieved report requires locator')
        if (retrieval == 'not_retrieved' or decision == 'exclude') and not nonempty_text(report.get('reason')):
            raise ValueError('retrieval failure/full-text exclusion requires reason')
        if decision == 'include' and not nonempty_text(report.get('study_id')):
            raise ValueError('included report requires study ID')
        reports[rid] = report
    report_by_record = {record: report for report in reports.values() for record in report['record_ids']}
    extracted_report_ids = set()
    for evidence in protocol['evidence']:
        report = report_by_record.get(evidence['record_id'])
        if report is None or report.get('decision') != 'include' or report['retrieval'] != 'retrieved':
            raise ValueError('extracted evidence requires an included retrieved report; reconcile screening first')
        extracted_report_ids.add(report['report_id'])
        if evidence['study_id'] != report['study_id']:
            raise ValueError('extracted evidence study ID conflicts with included report')
    counts=Counter(r['retrieval'] for r in reports.values())
    assessed=[r for r in reports.values() if r['retrieval']=='retrieved' and r.get('decision') in ('include','exclude')]
    included=[r for r in assessed if r['decision']=='include']
    excluded=[r for r in assessed if r['decision']=='exclude']
    output=io.StringIO(newline='')
    writer=csv.writer(output,lineterminator='\n')
    writer.writerow(['report_id','record_ids','retrieval','decision','reason','study_id','locator'])
    for rid,r in sorted(reports.items()):
        writer.writerow([safe_csv_cell(rid),safe_csv_cell(';'.join(r['record_ids'])),r['retrieval'],r.get('decision','pending'),
                         safe_csv_cell(r.get('reason','')),safe_csv_cell(r.get('study_id','')),safe_csv_cell(r.get('locator',''))])
    return dict(search_plan_audit=baseline['search_plan_audit'], record_flow=baseline['flow'], report_flow=dict(sought=len(reports),retrieved=counts['retrieved'],
                not_retrieved=counts['not_retrieved'],retrieval_pending=counts['pending'],assessed=len(assessed),
                assessment_pending=counts['retrieved']-len(assessed),excluded=len(excluded),included=len(included),
                included_studies=len({r['study_id'] for r in included}),
                reports_with_extraction=len(extracted_report_ids)),
                extraction_pending_reports=sorted(r['report_id'] for r in included
                                                  if r['report_id'] not in extracted_report_ids),
                unmapped_records=sorted(included_records-linked),
                exclusion_reasons=dict(sorted(Counter(r['reason'] for r in excluded).items())),
                report_ledger=[reports[k] for k in sorted(reports)], report_csv=output.getvalue(),
                work_packages=baseline['work_packages'], context=baseline['context'], appraisal=baseline['appraisal'],
                evidence=baseline['evidence'], extraction_completeness=baseline['extraction_completeness'],
                boundary='PRISMA-oriented supplied-data ledger; not a claim of full PRISMA compliance or complete search')


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('protocol',type=Path)
    a=p.parse_args()
    try: result=report_flow(json.loads(a.protocol.read_text(encoding='utf-8')))
    except (ValueError,OSError,KeyError,TypeError) as e: p.exit(1,str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
