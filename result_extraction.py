"""Prepare blank manual extraction worksheets without reading or interpreting documents."""
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
from result_intake import EVIDENCE_FIELDS

MAX_INPUT_BYTES = 50_000_000
MAX_OUTPUT_BYTES = 50_000_000
TEMPLATE_WARNING = (
    'This unfinished draft is intentionally rejected by manual result intake. Only the three '
    'caller-selected report, study and record IDs are prefilled. Supply a new extraction ID, '
    'every result field, human extractor/date/note, and explicitly selected source IDs with '
    'locations. No source, scientific value, mechanism label, date or review is chosen for you. '
    'Then use result_intake target, assemble and verify against the actual current protocol. '
    'This worksheet is not an acceptance target and does not renew any earlier review.'
)
BOUNDARY = (
    'Read-only manual extraction preparation from supplied data, not extraction or source reading. '
    'Available source declarations are not selected evidence or verified documents. Digests and '
    'locators remain unverified and are never opened. Existing results span only the exact selected '
    'report-study pair across its mapped records, not verified study identity or independent findings. '
    'Existing-result presence is not complete extraction. Contexts are shown only for exact supplied '
    'links: selected-record source references or existing pair-result IDs. Their full assertions may '
    'also reference other items; no applicability to the new candidate is inferred. Planned-search '
    'membership does not inherit a source context. No eligibility decision, source authenticity, '
    'scientific or clinical correctness, reviewer identity, census or conclusion is established. '
    'No protocol field, human assertion, completion status or source review is changed or renewed. '
    'The draft is not a scientific finding, approved review or bound correction. Real/private inputs '
    'and outputs must stay outside the public repository; nothing is uploaded.'
)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalized(value, limit, label):
    raw = canonical_json_bytes(value)
    if len(raw) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _implementation_hashes():
    result = dict(engine_hashes())
    for filename in ('result_extraction.py', 'result_intake.py'):
        result[filename] = hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
    return result


def worksheet(protocol, report_id, study_id, record_id):
    """Join exact supplied context and a deliberately unfinished intake candidate."""
    protocol = _normalized(protocol, MAX_INPUT_BYTES, 'protocol')
    if not isinstance(protocol, dict):
        raise ValueError('protocol must be an object')
    if 'adapter_receipts' in protocol:
        raise ValueError('mock adapter_receipts inputs are not supported for manual extraction worksheets')
    if 'reports' not in protocol:
        raise ValueError('manual extraction worksheet requires explicit reports')
    research = run(protocol)
    report_flow(protocol, include_csv=False)
    prepared = prepare_targets(protocol, research.get('bibliographic_collection'))
    for label, value in (('report_id', report_id), ('study_id', study_id), ('record_id', record_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(label + ' must be an explicit nonblank literal selection')
    report = next((row for row in prepared['report_targets'] if row['report_id'] == report_id), None)
    if report is None:
        raise ValueError('unknown report_id selection')
    recorded = report['recorded_report']
    if report['retrieval'] != 'retrieved' or recorded.get('decision') != 'include':
        raise ValueError('manual extraction requires an explicitly included retrieved report')
    if record_id not in recorded['record_ids']:
        raise ValueError('selected record_id is not mapped to the selected report')
    if study_id not in report['supplied_study_ids']:
        raise ValueError('selected study_id is not declared by the selected report')
    selected_record = next(row for row in prepared['record_targets'] if row['record_id'] == record_id)
    search_indices = {row['search_index'] for row in selected_record['source_basis']['occurrences']}
    sources = [row for row in prepared['source_ledger'] if row['source']['report_id'] == report_id]
    existing = []
    for index, row in enumerate(protocol['evidence']):
        if row['record_id'] in recorded['record_ids'] and row['study_id'] == study_id:
            existing.append(dict(evidence=copy.deepcopy(row), input_pointer=f'/evidence/{index}',
                normalized_evidence_id=row.get('evidence_id', row['record_id']),
                evidence_id_origin='EXPLICIT' if 'evidence_id' in row else 'IMPLICIT_RECORD_ID',
                selected_record=row['record_id'] == record_id))
    pair_ids = {row['normalized_evidence_id'] for row in existing}
    source_contexts, result_contexts = [], []
    for index, context in enumerate(protocol.get('contexts', [])):
        if context.get('context_scope') == 'source_review':
            matched = [ref for ref in context['source_refs']
                       if ref['kind'] == 'record' and ref['record_id'] == record_id]
            if matched:
                source_contexts.append(dict(context=copy.deepcopy(context), input_pointer=f'/contexts/{index}',
                                            matched_source_refs=copy.deepcopy(matched)))
        else:
            matched = [eid for eid in context['evidence_ids'] if eid in pair_ids]
            if matched:
                result_contexts.append(dict(context=copy.deepcopy(context), input_pointer=f'/contexts/{index}',
                                            matched_evidence_ids=matched))
    evidence = {key: None for key in sorted(EVIDENCE_FIELDS)}
    evidence.update(record_id=record_id, study_id=study_id)
    candidate = dict(schema_version=1, candidates=[dict(report_id=report_id, evidence=evidence,
        source_references=[], extracted_by=None, extracted_at=None, extraction_note=None)])
    result = dict(schema_version=1, kind='manual_result_extraction_worksheet',
        preparation_status='DRAFT_REQUIRES_HUMAN_INPUT' if sources else 'SOURCE_DESCRIPTORS_REQUIRED',
        protocol_sha256=digest(protocol), protocol_version=copy.deepcopy(protocol['version']),
        question=copy.deepcopy(protocol['question']),
        inclusion_criteria=copy.deepcopy(protocol['inclusion_criteria']),
        exclusion_criteria=copy.deepcopy(protocol['exclusion_criteria']),
        selection=dict(report_id=report_id, study_id=study_id, record_id=record_id,
            existing_results_scope='EXACT_REPORT_STUDY_ALL_MAPPED_RECORDS', validation_scope='ENTIRE_PROTOCOL'),
        report_target=copy.deepcopy(report), selected_record_target=copy.deepcopy(selected_record),
        source_contexts=[copy.deepcopy(row) for row in prepared['source_contexts']
                         if row['search_index'] in search_indices],
        source_stage='SUPPLIED' if 'report_sources' in protocol else 'NOT_SUPPLIED',
        available_sources=copy.deepcopy(sources),
        available_sources_scope='WHOLE_REPORT_DECLARATIONS_NOT_SELECTED_OR_VERIFIED',
        existing_results=existing,
        source_record_contexts=source_contexts, existing_result_contexts=result_contexts,
        context_scope='EXPLICIT_SELECTED_RECORD_OR_EXISTING_PAIR_RESULT_LINKS_ONLY_NOT_NEW_CANDIDATE_APPLICABILITY',
        counts=dict(existing_pair_results=len(existing),
                    existing_selected_record_results=sum(row['selected_record'] for row in existing),
                    available_source_descriptors=len(sources)),
        candidate_document=candidate, candidate_is_complete=False,
        source_reference_template=dict(source_id=None, extraction_locator=None),
        template_warning=TEMPLATE_WARNING, engine_sha256=_implementation_hashes(),
        protocol_changed=False, external_calls=0, source_authenticity='NOT_VERIFIED',
        document_bytes_verification='NOT_PERFORMED', reading='NOT_ESTABLISHED',
        scientific_correctness='NOT_ASSESSED', clinical_correctness='NOT_ASSESSED',
        extraction_completeness='NOT_ESTABLISHED', census_claim='NOT_ESTABLISHED',
        conclusion_readiness='NOT_READY', boundary=BOUNDARY)
    return _normalized(result, MAX_OUTPUT_BYTES, 'worksheet')


def render_text(result):
    result = _normalized(result, MAX_OUTPUT_BYTES, 'text rendering input')
    rendered = 'Manual result extraction worksheet\n' + '\n'.join(
        quoted_display(key) + ': ' + quoted_display(value) for key, value in result.items()) + '\n'
    if len(rendered.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('text output exceeds byte limit')
    return rendered


def _encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def _read(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('protocol exceeds byte limit')
    return parse_json(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    for name in ('report-id', 'study-id', 'record-id'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--text', action='store_true')
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument('--output', type=Path, help='exclusively save the entire worksheet as JSON')
    outputs.add_argument('--candidate-output', type=Path, help='exclusively save the deliberately unfinished candidate as JSON')
    args = parser.parse_args()
    try:
        result = worksheet(_read(args.protocol), args.report_id, args.study_id, args.record_id)
        encoded = _encode(result)
        rendered = render_text(result) if args.text else encoded
        destination = args.output if args.output is not None else args.candidate_output
        artifact = _encode(result['candidate_document']) if args.candidate_output is not None else encoded
        for value in (encoded, rendered, artifact):
            if len(value.encode('utf-8')) > MAX_OUTPUT_BYTES:
                raise ValueError('output exceeds byte limit')
        if destination is not None:
            with destination.open('x', encoding='utf-8', newline='\n') as output:
                output.write(artifact)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError, OverflowError) as error:
        parser.exit(1, 'extraction worksheet error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
