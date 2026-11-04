"""Build deterministic report retrieval/full-text screening ledgers from supplied records."""
import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path
from json_io import parse_json, configure_utf8_stdio
from evidence_workflow import run
from csv_safety import safe_csv_cell
from report_links import has_plural_studies, report_study_ids, validate_reports, validate_evidence_membership


def report_flow(protocol, *, include_csv=True):
    """Validate and project reports; callers not exporting CSV may omit it.

    CSV construction is presentation, not validation. Keeping it optional avoids
    imposing a runtime's CSV character restrictions on JSON-only consumers.
    """
    if type(include_csv) is not bool:
        raise ValueError('include_csv must be Boolean')
    baseline = run(protocol)
    included_records = {r['record_id'] for r in protocol['screening'] if r['decision']=='include'}
    reports, report_by_record = validate_reports(protocol['reports'], included_records)
    linked = set(report_by_record)
    extracted_report_ids = set()
    for evidence in protocol['evidence']:
        report = validate_evidence_membership(evidence, report_by_record)
        extracted_report_ids.add(report['report_id'])
    counts=Counter(r['retrieval'] for r in reports.values())
    assessed=[r for r in reports.values() if r['retrieval']=='retrieved' and r.get('decision') in ('include','exclude')]
    included=[r for r in assessed if r['decision']=='include']
    excluded=[r for r in assessed if r['decision']=='exclude']
    plural_studies = has_plural_studies(protocol)
    csv_text = None
    if include_csv:
        output=io.StringIO(newline='')
        writer=csv.writer(output,lineterminator='\n')
        columns = ['report_id','record_ids','retrieval','decision','reason','study_id','locator']
        if plural_studies:
            columns.append('declared_study_ids')
        writer.writerow(columns)
        for rid,r in sorted(reports.items()):
            values = [safe_csv_cell(rid),safe_csv_cell(';'.join(r['record_ids'])),r['retrieval'],r.get('decision','pending'),
                      safe_csv_cell(r.get('reason','')),safe_csv_cell(r.get('study_id','')),safe_csv_cell(r.get('locator',''))]
            if plural_studies:
                values.append(safe_csv_cell(json.dumps(report_study_ids(r), ensure_ascii=False)))
            writer.writerow(values)
        csv_text = output.getvalue()
    result = dict(experiments=baseline['experiments'], synthesis=baseline['synthesis'], planning=baseline['planning'], record_provenance=baseline['record_provenance'],
                deduplication_scope=baseline['deduplication_scope'],
                record_identity_verification=baseline['record_identity_verification'],
                search_ledger=baseline['search_ledger'],
                search_coverage=baseline['coverage'], search_plan_audit=baseline['search_plan_audit'], record_flow=baseline['flow'], report_flow=dict(sought=len(reports),retrieved=counts['retrieved'],
                not_retrieved=counts['not_retrieved'],retrieval_pending=counts['pending'],assessed=len(assessed),
                assessment_pending=counts['retrieved']-len(assessed),excluded=len(excluded),included=len(included),
                included_studies=len({sid for r in included for sid in report_study_ids(r)}),
                reports_with_extraction=len(extracted_report_ids)),
                extraction_pending_reports=sorted(r['report_id'] for r in included
                                                  if r['report_id'] not in extracted_report_ids),
                unmapped_records=sorted(included_records-linked),
                exclusion_reasons=dict(sorted(Counter(r['reason'] for r in excluded).items())),
                report_ledger=[reports[k] for k in sorted(reports)], report_csv=csv_text,
                work_packages=baseline['work_packages'], context=baseline['context'], appraisal=baseline['appraisal'],
                evidence=baseline['evidence'], extraction_completeness=baseline['extraction_completeness'],
                boundary='PRISMA-oriented supplied-data ledger; not a claim of full PRISMA compliance or complete search')
    if plural_studies:
        result['report_study_coverage'] = baseline['report_study_coverage']
    if 'screening_review' in baseline:
        result['screening_review'] = baseline['screening_review']
    if not include_csv:
        del result['report_csv']
    return result


def main():
    configure_utf8_stdio()
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('protocol',type=Path)
    a=p.parse_args()
    try: result=report_flow(parse_json(a.protocol.read_text(encoding='utf-8')))
    except (ValueError,OSError,KeyError,TypeError) as e: p.exit(1,str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
