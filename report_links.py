"""Validate supplied report-study memberships without inferring source identity.

These helpers do not execute the workflow or import the report renderer. Legacy
scalar report rows retain their original values; explicit plural declarations
add memberships, not independently verified studies or exhaustive extraction.
"""
import copy

from context_links import nonempty_text


BOUNDARY = ('Supplied report-study memberships only; not verified study identity, '
            'independence, study-level eligibility decisions or complete extraction.')


def has_plural_studies(protocol):
    """Recognize explicit opt-in, including malformed plural declarations."""
    rows = protocol.get('reports')
    return isinstance(rows, list) and any(
        isinstance(row, dict) and 'study_ids' in row for row in rows)


def report_study_ids(report):
    """Return detached, ordered IDs from an already validated included report."""
    if report.get('decision') != 'include':
        return []
    if 'study_ids' in report:
        return copy.deepcopy(report['study_ids'])
    return [report['study_id']]


def validate_reports(report_rows, included_record_ids):
    """Validate report links, retaining legacy row values and validation messages.

    Both mappings refer to detached copies, never to supplied mutable rows.
    The maps share each report copy so a record resolves to its report directly.
    """
    if not isinstance(report_rows, list):
        raise ValueError('reports must be a list')
    reports, linked = {}, set()
    included_records = set(included_record_ids)
    for report in report_rows:
        if not isinstance(report, dict):
            raise ValueError('report must be an object')
        rid = report.get('report_id')
        if not nonempty_text(rid) or rid in reports:
            raise ValueError('unique report IDs required')
        record_ids = report['record_ids']
        if (not isinstance(record_ids, list) or not record_ids
                or any(not isinstance(r, str) or r not in included_records for r in record_ids)
                or len(record_ids) != len(set(record_ids))):
            raise ValueError('reports must link to included screening records')
        if linked.intersection(record_ids):
            raise ValueError('record mapped to multiple reports')
        linked.update(record_ids)
        retrieval = report['retrieval']
        if retrieval not in ('retrieved', 'not_retrieved', 'pending'):
            raise ValueError('invalid report retrieval state')
        decision = report.get('decision', 'pending')
        if decision not in ('include', 'exclude', 'pending'):
            raise ValueError('invalid full-text decision')
        if retrieval != 'retrieved' and decision != 'pending':
            raise ValueError('unretrieved report cannot have full-text decision')
        if retrieval == 'retrieved' and not nonempty_text(report.get('locator')):
            raise ValueError('retrieved report requires locator')
        if (retrieval == 'not_retrieved' or decision == 'exclude') and not nonempty_text(report.get('reason')):
            raise ValueError('retrieval failure/full-text exclusion requires reason')
        if 'study_ids' in report:
            if 'study_id' in report:
                raise ValueError('report study_id and study_ids are mutually exclusive')
            if decision != 'include' or retrieval != 'retrieved':
                raise ValueError('report study_ids require an included retrieved report')
            study_ids = report['study_ids']
            if (not isinstance(study_ids, list) or not study_ids
                    or any(not nonempty_text(sid) for sid in study_ids)
                    or len(study_ids) != len(set(study_ids))):
                raise ValueError('report study_ids must be a nonempty list of unique nonblank study IDs')
        elif decision == 'include' and not nonempty_text(report.get('study_id')):
            raise ValueError('included report requires study ID')
        reports[rid] = copy.deepcopy(report)
    report_by_record = {record: report for report in reports.values()
                        for record in report['record_ids']}
    return reports, report_by_record


def validate_evidence_membership(evidence, report_by_record):
    """Require exact declared membership; do not infer source/study identity."""
    report = report_by_record.get(evidence['record_id'])
    if report is None or report.get('decision') != 'include' or report['retrieval'] != 'retrieved':
        raise ValueError('extracted evidence requires an included retrieved report; reconcile screening first')
    if evidence['study_id'] not in report_study_ids(report):
        raise ValueError('extracted evidence study ID conflicts with included report')
    return report


def report_study_coverage(protocol, reports_by_id, evidence_rows):
    """Project validated supplied memberships and presence of matching results.

    Absence means no supplied matching result rows, not incomplete extraction.
    The caller chooses whether explicit plural opt-in enables this projection.
    """
    ledger, missing = [], []
    report_for_record = {rid: report['report_id'] for report in reports_by_id.values() for rid in report['record_ids']}
    results_by_membership = {}
    for row in evidence_rows:
        key = (report_for_record.get(row['record_id']), row['study_id'])
        results_by_membership.setdefault(key, []).append(row.get('evidence_id', row['record_id']))
    for i, supplied in enumerate(protocol['reports']):
        report = reports_by_id[supplied['report_id']]
        if report.get('decision') != 'include':
            continue
        for j, study_id in enumerate(report_study_ids(report)):
            pointer = (f'/reports/{i}/study_ids/{j}' if 'study_ids' in report
                       else f'/reports/{i}/study_id')
            evidence_ids = sorted(results_by_membership.get((report['report_id'], study_id), []))
            membership = dict(membership_id=pointer, input_pointer=pointer,
                              report_id=report['report_id'], study_id=study_id,
                              evidence_ids=evidence_ids, has_result_rows=bool(evidence_ids))
            ledger.append(membership)
            if not evidence_ids:
                missing.append(dict(report_id=report['report_id'], study_id=study_id,
                                    membership_id=pointer, input_pointer=pointer))
    return copy.deepcopy(dict(
        membership_ledger=ledger,
        missing_report_study_memberships=missing,
        counts=dict(included_memberships=len(ledger),
                    memberships_with_result_rows=len(ledger) - len(missing),
                    memberships_without_result_rows=len(missing)),
        study_eligibility_assessment='NOT_PERFORMED',
        study_identity_verification='NOT_ESTABLISHED',
        extraction_completeness='NOT_ESTABLISHED',
        boundary=BOUNDARY))
