"""Read-only literal drift comparison for replayed detached manual result records."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from report_review_links import prepare_targets
from research_bundle import engine_hashes
import result_intake

MAX_INPUT_BYTES = 50_000_000
MAX_OUTPUT_BYTES = 50_000_000
BOUNDARY = (
    'Literal supplied context comparison only. UNCHANGED does not establish lineage, document '
    'bytes, reading, clinical or scientific correctness, completed extraction, authorship, '
    'identity or renewed human review. Historical extraction locations and attribution are '
    'retained assertions, never inferred or refreshed. Source associations remain '
    'DETACHED_RECORD_ONLY. Digests of documents are unverified declarations. Report source '
    'hashes bind inherited criteria, search/CSV context, retrieval, locator and the ordered '
    'whole report source catalog; reordered bound catalogs or search inputs may change hashes '
    'without changing a selected descriptor. Eligibility decisions and study declarations '
    'are compared separately, not established by source hashes. No source locator, URL or '
    'document path is opened. No external calls or protocol changes are performed. Exact '
    'original replay is not authentication of this editable unsigned detached record.'
)


def _digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalized(value, limit, label):
    raw = canonical_json_bytes(value)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _changed(before, after):
    """Top-level literal fields, distinguishing absent from explicitly null."""
    if after is None:
        return sorted(before)
    return sorted(key for key in set(before) | set(after)
                  if key not in before or key not in after
                  or canonical_json_bytes(before[key]) != canonical_json_bytes(after[key]))


def _status(before, after, supplied=True):
    if not supplied:
        return 'NOT_SUPPLIED'
    if after is None:
        return 'MISSING'
    return 'UNCHANGED' if canonical_json_bytes(before) == canonical_json_bytes(after) else 'CHANGED'


def _counts(values, states):
    return {state: values.count(state) for state in states}


def _implementation_hashes():
    return dict(engine_hashes(), **{
        'result_intake.py': hashlib.sha256(Path(result_intake.__file__).read_bytes()).hexdigest(),
        'result_source_review.py': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def review(original_protocol, application_record, current_protocol):
    """Replay first, validate all current input, then compare only imported explicit IDs."""
    replay = result_intake.verify(original_protocol, application_record)
    original = _normalized(original_protocol, MAX_INPUT_BYTES, 'original protocol')
    record = _normalized(application_record, MAX_INPUT_BYTES, 'application record')
    current = _normalized(current_protocol, MAX_INPUT_BYTES, 'current protocol')
    if not isinstance(current, dict):
        raise ValueError('current protocol must be an object')
    if 'adapter_receipts' in current:
        raise ValueError('mock adapter_receipts inputs are not supported for manual result review')
    research = run(current)
    if 'reports' in current:
        report_flow(current, include_csv=False)
    prepared = prepare_targets(current, research.get('bibliographic_collection'))
    report_supplied = prepared['report_stage'] == 'SUPPLIED'
    source_supplied = prepared['source_stage'] == 'SUPPLIED'
    targets = {row['report_id']: row for row in prepared['report_targets']}
    by_record = {rid: row for row in prepared['report_targets']
                 for rid in row['recorded_report']['record_ids']}
    sources = {row['source']['source_id']: row for row in prepared['source_ledger']}
    explicit = {row['evidence_id']: (index, row) for index, row in enumerate(current['evidence'])
                if 'evidence_id' in row}
    receipt = record['receipt']
    historical = receipt['target']
    comparisons = []
    for before_target in historical['selected_report_targets']:
        report_id = before_target['report_id']
        after_target = targets.get(report_id)
        before_report = before_target['recorded_report']
        after_report = after_target['recorded_report'] if after_target else None
        after_basis = after_target['source_basis'] if after_target else None
        comparisons.append(dict(report_id=report_id,
            recorded_report=dict(status=_status(before_report, after_report, report_supplied),
                before=before_report, after=after_report,
                historical_input_pointer=before_target['input_pointer'],
                historical_pointer_scope='original_protocol', current_pointer_scope='current_protocol',
                current_input_pointer=after_target['input_pointer'] if after_target else None,
                changed_fields=_changed(before_report, after_report) if report_supplied else []),
            source_context=dict(status=_status(before_target['source_basis'], after_basis, report_supplied),
                before_sha256=before_target['source_basis_sha256'],
                after_sha256=after_target['source_basis_sha256'] if after_target else None,
                before=before_target['source_basis'], after=after_basis,
                changed_fields=_changed(before_target['source_basis'], after_basis) if report_supplied else [])))
    comparison_by_id = {row['report_id']: row for row in comparisons}
    selected_by_candidate = {}
    for source in historical['selected_sources']:
        selected_by_candidate.setdefault(source['candidate_index'], []).append(source)
    rows = []
    candidates = receipt['candidate_document']['candidates']
    for index, candidate in enumerate(candidates):
        before = candidate['evidence']
        evidence_id = before['evidence_id']
        matched = explicit.get(evidence_id)
        after = matched[1] if matched else None
        original_report_id = candidate['report_id']
        target = targets.get(original_report_id)
        mapped = by_record.get(before['record_id'])
        original_study_declared = (before['study_id'] in target['supplied_study_ids'] if target else None)
        matched_target = by_record.get(after['record_id']) if after else None
        mapped_id = mapped['report_id'] if mapped else None
        mapping_status = ('NOT_SUPPLIED' if not report_supplied else 'MISSING' if not target
            else 'UNCHANGED' if mapped_id == original_report_id and original_study_declared
                 and target['retrieval'] == 'retrieved' and target['recorded_report'].get('decision') == 'include'
            else 'CHANGED')
        selected = []
        for historical_source in selected_by_candidate[index]:
            before_source = historical_source['source']
            source_id = before_source['source_id']
            now = sources.get(source_id)
            after_source = now['source'] if now else None
            status = _status(before_source, after_source, source_supplied)
            if after_source is not None and before_source['report_id'] != after_source['report_id']:
                status = 'MOVED'
            selected.append(dict(source_id=source_id, status=status, before=before_source, after=after_source,
                historical_input_pointer=historical_source['input_pointer'],
                historical_pointer_scope='original_protocol', current_pointer_scope='current_protocol',
                current_input_pointer=now['input_pointer'] if now else None,
                extraction_locator=historical_source['extraction_locator'],
                changed_fields=_changed(before_source, after_source) if source_supplied else []))
        rows.append(dict(candidate_index=index, evidence_id=evidence_id,
            report_comparison_id=original_report_id,
            result=dict(status=_status(before, after), before=before, after=after,
                recorded_input_pointer=f'/receipt/candidate_document/candidates/{index}/evidence',
                recorded_pointer_scope='application_record', current_pointer_scope='current_protocol',
                current_input_pointer=f'/evidence/{matched[0]}' if matched else None,
                changed_fields=_changed(before, after)),
            historical_extraction={key: copy.deepcopy(candidate[key]) for key in
                ('extracted_by', 'extracted_at', 'extraction_note', 'source_references')},
            report_mapping=dict(status=mapping_status,
                original_report_presence=('NOT_SUPPLIED' if not report_supplied else 'PRESENT' if target else 'MISSING'),
                current_mapping_of_original_record=(dict(report_id=mapped_id,
                    input_pointer=mapped['input_pointer']) if mapped else None),
                current_original_study_declared=original_study_declared,
                current_retrieval=target['retrieval'] if target else None,
                current_decision=target['recorded_report'].get('decision', 'pending') if target else None,
                current_matched_row_link_status=('MISSING' if after is None else 'NOT_SUPPLIED' if not report_supplied
                    else 'UNCHANGED' if after['record_id'] == before['record_id']
                         and after['study_id'] == before['study_id']
                         and matched_target is not None and matched_target['report_id'] == original_report_id
                    else 'CHANGED'),
                current_matched_row_link=(dict(record_id=after['record_id'], study_id=after['study_id'],
                    report_stage=prepared['report_stage'],
                    report_id=matched_target['report_id'] if matched_target else None,
                    report_input_pointer=matched_target['input_pointer'] if matched_target else None) if after else None)),
            source_context_status=comparison_by_id[original_report_id]['source_context']['status'],
            selected_sources=selected))
    basic_states = ('UNCHANGED', 'CHANGED', 'MISSING', 'NOT_SUPPLIED')
    result = dict(schema_version=1, kind='detached_result_source_review',
        original_protocol_sha256=_digest(original),
        protocol_candidate_sha256=receipt['protocol_candidate_sha256'],
        current_protocol_sha256=_digest(current), application_record_sha256=_digest(record),
        original_replay_result=replay, engine_sha256=_implementation_hashes(),
        current_report_stage=prepared['report_stage'], current_source_stage=prepared['source_stage'],
        rows=rows, report_comparisons=comparisons,
        counts=dict(result=_counts([row['result']['status'] for row in rows], basic_states[:3]),
            report_mapping=_counts([row['report_mapping']['status'] for row in rows], basic_states),
            matched_row_link=_counts([row['report_mapping']['current_matched_row_link_status'] for row in rows], basic_states),
            recorded_report=_counts([row['recorded_report']['status'] for row in comparisons], basic_states),
            source_context=_counts([row['source_context']['status'] for row in comparisons], basic_states),
            selected_sources=_counts([source['status'] for row in rows for source in row['selected_sources']],
                                    basic_states + ('MOVED',))),
        scope=dict(result_rows='Only originally imported candidates, in original order; only explicit current evidence_id matches.',
                   report_mapping_counts='Original record/report/study link, separately from a moved current result row.',
                   matched_row_link_counts='Actual matched explicit result row record/report/study link against the imported link.',
                   report_comparisons='One per original selected report ID.',
                   source_context_counts='Unique original report IDs, not candidate rows.',
                   selected_source_counts='Per-candidate selected source references.',
                   unrelated_current_results='NOT_COMPARED'),
        source_association_scope='DETACHED_RECORD_ONLY', lineage='NOT_ESTABLISHED',
        document_bytes_verification='NOT_PERFORMED', reading='NOT_ESTABLISHED',
        source_authenticity='NOT_VERIFIED', source_result_correctness='NOT_ASSESSED',
        clinical_correctness='NOT_ASSESSED', extraction_completeness='NOT_ESTABLISHED',
        reviewer_identity_verification='NOT_ESTABLISHED', extractor_identity_verification='NOT_ESTABLISHED',
        authorship='NOT_ESTABLISHED', renewed_human_review='NOT_PERFORMED', protocol_changed=False, external_calls=0,
        boundary=BOUNDARY)
    return _normalized(result, MAX_OUTPUT_BYTES, 'review output')


def render_text(result):
    return 'Detached result source comparison\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'


def _read(path, label):
    with path.open('rb') as source:
        raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


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
        result = review(_read(args.original_protocol, 'original protocol'),
                        _read(args.application_record, 'application record'),
                        _read(args.current_protocol, 'current protocol'))
        encoded = _encode(result)
        rendered = render_text(result) if args.text else encoded
        # Validate every output and its actual UTF-8 size before exclusive creation.
        for output in (encoded, rendered):
            if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES:
                raise ValueError('output exceeds byte limit')
        if args.output is not None:
            with args.output.open('x', encoding='utf-8', newline='\n') as destination:
                destination.write(encoded)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'result source review error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
