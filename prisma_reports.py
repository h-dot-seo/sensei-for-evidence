"""Build deterministic report retrieval/full-text screening ledgers from supplied records."""
import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path
from evidence_workflow import run


def report_flow(protocol):
    baseline = run(protocol)
    included_records = {r['record_id'] for r in protocol['screening'] if r['decision']=='include'}
    reports, linked = {}, set()
    for report in protocol['reports']:
        rid = report['report_id']
        if not isinstance(rid,str) or not rid or rid in reports:
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
        if retrieval == 'retrieved' and not report.get('locator'):
            raise ValueError('retrieved report requires locator')
        if (retrieval == 'not_retrieved' or decision == 'exclude') and not report.get('reason'):
            raise ValueError('retrieval failure/full-text exclusion requires reason')
        if decision == 'include' and not report.get('study_id'):
            raise ValueError('included report requires study ID')
        reports[rid] = report
    report_by_record = {record: report for report in reports.values() for record in report['record_ids']}
    for evidence in protocol['evidence']:
        report = report_by_record.get(evidence['record_id'])
        if report is None or report.get('decision') != 'include' or report['retrieval'] != 'retrieved':
            raise ValueError('extracted evidence requires an included retrieved report; reconcile screening first')
        if evidence['study_id'] != report['study_id']:
            raise ValueError('extracted evidence study ID conflicts with included report')
    counts=Counter(r['retrieval'] for r in reports.values())
    assessed=[r for r in reports.values() if r['retrieval']=='retrieved' and r.get('decision') in ('include','exclude')]
    included=[r for r in assessed if r['decision']=='include']
    excluded=[r for r in assessed if r['decision']=='exclude']
    output=io.StringIO(newline='')
    writer=csv.writer(output,lineterminator='\n')
    writer.writerow(['report_id','record_ids','retrieval','decision','reason','study_id','locator'])
    def cell(value):
        text=str(value)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    for rid,r in sorted(reports.items()):
        writer.writerow([cell(rid),cell(';'.join(r['record_ids'])),r['retrieval'],r.get('decision','pending'),
                         cell(r.get('reason','')),cell(r.get('study_id','')),cell(r.get('locator',''))])
    return dict(record_flow=baseline['flow'], report_flow=dict(sought=len(reports),retrieved=counts['retrieved'],
                not_retrieved=counts['not_retrieved'],retrieval_pending=counts['pending'],assessed=len(assessed),
                assessment_pending=counts['retrieved']-len(assessed),excluded=len(excluded),included=len(included),
                included_studies=len({r['study_id'] for r in included})),
                unmapped_records=sorted(included_records-linked),
                exclusion_reasons=dict(sorted(Counter(r['reason'] for r in excluded).items())),
                report_ledger=[reports[k] for k in sorted(reports)], report_csv=output.getvalue(),
                work_packages=baseline['work_packages'],
                boundary='PRISMA-oriented supplied-data ledger; not a claim of full PRISMA compliance or complete search')


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('protocol',type=Path)
    a=p.parse_args()
    try: result=report_flow(json.loads(a.protocol.read_text(encoding='utf-8')))
    except (ValueError,OSError,KeyError,TypeError) as e: p.exit(1,str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
