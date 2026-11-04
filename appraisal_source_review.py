"""Compare replayed supplied appraisals with later literal result/source context."""
import argparse
import hashlib
import json
from pathlib import Path

import appraisal_intake as intake
from json_io import canonical_json_bytes, configure_utf8_stdio, quoted_display
from screening_links import prepare_targets as record_targets
from report_review_links import prepare_targets as report_targets

MAX_BYTES = 50_000_000
BOUNDARY = (
    'Read-only literal comparison of imported appraisal assertions and their historical '
    'result and mapped source context. UNCHANGED does not establish scientific validity, '
    'current applicability, lineage, independent reviewers, chronology or authenticity. '
    'CHANGED is not invalidation or renewed review. Mapped report catalogs are context, '
    'not selected or read documents; source digests remain unverified declarations. '
    'No method, judgement, consensus, clinical recommendation or research completeness '
    'is inferred. No document is opened, no external call made, and no stored appraisal, '
    'work completion, planning rank, PRISMA count or protocol field is changed. '
    'Exact replay of editable unsigned assertions is not authentication. Retain the '
    'original protocol, detached intake and recorded implementation for replay.'
)


def compare(before, after):
    """Compare presence and exact JSON fields, including absent versus null."""
    status = ('NOT_PRESENT_EITHER' if before is None and after is None else
              'ADDED' if before is None else 'MISSING' if after is None else
              'UNCHANGED' if canonical_json_bytes(before) == canonical_json_bytes(after) else 'CHANGED')
    left, right = before or {}, after or {}
    changed = sorted(key for key in set(left) | set(right)
                     if key not in left or key not in right or
                     canonical_json_bytes(left[key]) != canonical_json_bytes(right[key]))
    return dict(status=status, before=before, after=after, changed_fields=changed)


def _report_context(target):
    if target is None:
        return None
    # Array positions are navigation, not scientific or source identity.
    return {key: target[key] for key in ('report_id', 'recorded_report', 'source_basis',
            'source_basis_sha256', 'source_binding_state', 'supplied_study_ids')}


def review(original_protocol, application_record, current_protocol):
    original = intake._normalized(original_protocol, MAX_BYTES, 'original protocol')
    application = intake._normalized(application_record, MAX_BYTES, 'application record')
    current = intake._normalized(current_protocol, MAX_BYTES, 'current protocol')
    replay = intake.verify(original, application)
    research, _ = intake._validate(current)
    historical = application['receipt']['target']
    current_records = record_targets(current, research.get('bibliographic_collection'))
    current_reports = report_targets(current, research.get('bibliographic_collection'))
    records = {row['record_id']: row for row in current_records['record_targets']}
    old_records = {row['record_id']: row for row in historical['selected_record_targets']}
    by_record = {rid: row for row in current_reports['report_targets']
                 for rid in row['recorded_report']['record_ids']}
    old_by_record = {rid: row for row in historical['mapped_report_source_targets']
                     for rid in row['recorded_report']['record_ids']}
    results = {row['evidence_id']: (index, row) for index, row in enumerate(research['evidence'])}
    appraisals = {row['appraisal_id']: (index, row)
                  for index, row in enumerate(current.get('appraisals', []))}
    rows = []
    for supplied in historical['appended_appraisals']:
        before = supplied['appraisal']
        match = appraisals.get(before['appraisal_id'])
        linked = []
        for previous in historical['selected_evidence']:
            if previous['candidate_index'] != supplied['candidate_index']:
                continue
            match_result = results.get(previous['evidence_id'])
            now = match_result[1] if match_result else None
            raw = current['evidence'][match_result[0]] if match_result else None
            rid = previous['normalized_evidence']['record_id']
            original_report = old_by_record.get(rid)
            current_original_report = by_record.get(rid)
            actual_report = by_record.get(now['record_id']) if now else None
            linked.append(dict(evidence_id=previous['evidence_id'],
                raw_result=compare(previous['raw_evidence'], raw),
                normalized_result=compare(previous['normalized_evidence'], now),
                historical_identity_origin=previous['identity_origin'],
                current_identity_origin=('EXPLICIT_EVIDENCE_ID' if 'evidence_id' in raw else 'LEGACY_RECORD_ID') if raw is not None else None,
                historical_input_pointer=previous['input_pointer'],
                current_input_pointer=f'/evidence/{match_result[0]}' if match_result else None,
                original_record_context=compare(old_records.get(rid), records.get(rid)),
                original_record_report_context=compare(_report_context(original_report), _report_context(current_original_report)),
                matched_result_record_context=compare(old_records.get(rid), records.get(now['record_id']) if now else None),
                matched_result_report_context=compare(_report_context(original_report), _report_context(actual_report))))
        rows.append(dict(appraisal_id=before['appraisal_id'], candidate_index=supplied['candidate_index'],
            appraisal=compare(before, match[1] if match else None),
            historical_input_pointer=supplied['output_pointer'],
            current_input_pointer=f'/appraisals/{match[0]}' if match else None,
            historical_pointer_scope='application_protocol_candidate', current_pointer_scope='current_protocol',
            evidence_pointer_scope='original_protocol', linked_results=linked))
    states = ('UNCHANGED', 'CHANGED', 'MISSING', 'ADDED', 'NOT_PRESENT_EITHER')
    dimensions = ('raw_result', 'normalized_result', 'original_record_context',
                  'original_record_report_context', 'matched_result_record_context', 'matched_result_report_context')
    counts = {'appraisal': {state: sum(row['appraisal']['status'] == state for row in rows) for state in states}}
    counts.update({key: {state: sum(link[key]['status'] == state for row in rows for link in row['linked_results'])
                        for state in states} for key in dimensions})
    hashes = dict(intake._implementation_hashes())
    hashes['appraisal_source_review.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = dict(schema_version=1, kind='detached_appraisal_source_review', rows=rows, counts=counts,
        original_replay_result=replay, original_protocol_sha256=intake.digest(original),
        application_record_sha256=intake.digest(application), current_protocol_sha256=intake.digest(current),
        engine_sha256=hashes, current_report_stage=current_reports['report_stage'],
        current_source_stage=current_reports['source_stage'],
        scope='Imported appraisal IDs and their originally cited result IDs only; linked-result counts are per appraisal/result pair, not independent studies. Current added links and unrelated appraisals/results are not expanded.',
        source_context_scope='MAPPED_CATALOG_CONTEXT_NOT_SELECTED_OR_READ_DOCUMENTS',
        appraisal_validity='NOT_ASSESSED', renewed_human_review='NOT_PERFORMED',
        lineage='NOT_ESTABLISHED', source_authenticity='NOT_VERIFIED',
        protocol_changed=False, external_calls=0, boundary=BOUNDARY)
    return intake._normalized(result, MAX_BYTES, 'comparison output')


def render_text(result):
    return 'Detached appraisal source comparison\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_protocol', type=Path)
    parser.add_argument('application_record', type=Path)
    parser.add_argument('current_protocol', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        result = review(*(intake._read(path, MAX_BYTES, label) for path, label in (
            (args.original_protocol, 'original protocol'), (args.application_record, 'application record'),
            (args.current_protocol, 'current protocol'))))
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        rendered = render_text(result) if args.text else encoded
        if any(len(value.encode('utf-8')) > MAX_BYTES for value in (encoded, rendered)):
            raise ValueError('output exceeds byte limit')
        if args.output is not None:
            intake._write_new(args.output, encoded.encode("utf-8"))
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'appraisal source review error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
