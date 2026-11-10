"""Serialize existing supplied-record audit ledgers as detached CSV, not findings."""
import csv
import hashlib
import json
from pathlib import Path

from csv_safety import safe_csv_cell
from prisma_audit import BOUNDARY as AUDIT_BOUNDARY, export_audit
from report_links import report_study_ids

MAX_BYTES = 16 * 1024 * 1024
COLUMNS = (
    'record_id', 'retained_occurrence_id', 'occurrence_ids', 'search_indices',
    'search_ids', 'screening_decision', 'screening_reason', 'screening_input_pointer',
    'report_stage', 'report_id', 'report_retrieval', 'report_decision',
    'report_study_ids', 'result_ids', 'result_study_ids', 'screening_review_stage',
)
BOUNDARY = ('Read-only supplied-record CSV; no screening adjudication, scientific judgement, '
            'model call, network or clock read. Census: NOT_ESTABLISHED. Conclusion: NOT_READY. '
            'PRIVATE FILE: supplied identifiers, reasons and pointers are unredacted; keep '
            'real outputs outside the public repository. Exporting does not authorize sharing. '
            + AUDIT_BOUNDARY)


def _safe(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) if isinstance(value, (list, dict)) else str(value)
    # Reject NUL consistently across supported CSV runtimes, rather than silently
    # producing a file that another supported runtime cannot read.
    if '\0' in text:
        raise ValueError('records CSV does not support NUL in scalar cells')
    return safe_csv_cell(text)


class _BoundedCSV:
    def __init__(self):
        self.raw = bytearray()

    def write(self, text):
        raw = text.encode('utf-8')
        if len(self.raw) + len(raw) > MAX_BYTES:
            raise ValueError('records CSV exceeds size limit')
        self.raw.extend(raw)
        return len(text)


def render_records(audit):
    """Flatten existing joins only; occurrence-aligned search labels are display data."""
    columns = list(COLUMNS)
    bibliographic = 'bibliographic_collection' in audit
    review = audit.get('screening_review')
    review_stage = review['stage'] if review is not None else 'NOT_SUPPLIED'
    if bibliographic:
        columns.append('bibliographic_row_pointers')
    if review_stage == 'SUPPLIED':
        columns.append('screening_review_cues')
    occurrences = {row['occurrence_id']: row for row in audit['occurrence_ledger']}
    reports = {row['report_id']: row for row in audit['report_ledger'] or []}
    evidence = {row['evidence_id']: row for row in audit['evidence_links']}
    cues = {} if review is None else {row['record_id']: row['comparison_cues']
                                     for row in review['record_review_ledger']}
    output = _BoundedCSV()
    # QUOTE_ALL also protects embedded carriage returns with an LF terminator.
    writer = csv.writer(output, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow([_safe(name) for name in columns])
    for record in audit['record_ledger']:
        occurrence_rows = [occurrences[key] for key in record['occurrence_ids']]
        screening = record['screening']
        report = reports.get(record['report_id'])
        row = dict(record_id=record['record_id'],
                   retained_occurrence_id=record['retained_occurrence_id'],
                   occurrence_ids=record['occurrence_ids'],
                   search_indices=[item['search_index'] for item in occurrence_rows],
                   search_ids=[item['search_id'] for item in occurrence_rows],
                   screening_decision='pending' if screening is None else screening['decision'],
                   screening_reason='' if screening is None else screening['reason'],
                   screening_input_pointer='' if screening is None else screening['input_pointer'],
                   report_stage=audit['report_stage'],
                   report_id='' if report is None else report['report_id'],
                   report_retrieval='' if report is None else report['retrieval'],
                   report_decision='' if report is None else report.get('decision', 'pending'),
                   report_study_ids=[] if report is None else report_study_ids(report),
                   result_ids=record['evidence_ids'],
                   result_study_ids=[evidence[key]['study_id'] for key in record['evidence_ids']],
                   screening_review_stage=review_stage)
        if bibliographic:
            row['bibliographic_row_pointers'] = record['bibliographic_row_pointers']
        if review_stage == 'SUPPLIED':
            row['screening_review_cues'] = cues[record['record_id']]
        writer.writerow([_safe(row[name]) for name in columns])
    return bytes(output.raw), columns


def export_records(protocol):
    audit = export_audit(protocol)
    raw, columns = render_records(audit)
    hashes = dict(audit['engine_sha256'])
    root = Path(__file__).resolve().parent
    for name in ('records_csv.py', 'views_export.py', 'research_status.py'):
        hashes[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    receipt = dict(schema='sensei.records-csv.v1', status='RENDERED',
                   protocol_sha256=audit['protocol_sha256'], hash_scope=audit['hash_scope'],
                   engine_sha256=hashes,
                   document=dict(encoding='utf-8', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
                   columns=columns, row_count=len(audit['record_ledger']),
                   report_stage=audit['report_stage'],
                   screening_review_stage=audit.get('screening_review', {}).get('stage', 'NOT_SUPPLIED'),
                   external_calls=0, protocol_changed=False, census_claim='NOT_ESTABLISHED',
                   conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    return receipt, raw


def write_records(path, raw):
    """Exclusive file-only output; remove a failed new write on stable paths."""
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError('output directory entry already exists')
    # Opening failures never remove existing entries. Cleanup only follows our
    # successful exclusive creation. Stable paths, not concurrent mutation, apply.
    target = path.open('xb')
    try:
        with target:
            target.write(raw)
    except OSError:
        path.unlink()
        raise
