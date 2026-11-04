"""Inspect descriptive candidate inventory or scaffold one explicitly supplied study label."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from research_bundle import engine_hashes
from report_study_inventory_links import link_report_study_inventory, prepare_candidate_target, _counts

TEMPLATE_WARNING = (
    'Separate unfilled descriptive assertion scaffold, not a protocol or eligibility decision. '
    'Supply all human fields and explicitly select source_ids. No source subset is chosen. '
    'Existing assertions are never copied, renewed or replaced. A new human-supplied study label '
    'is only a proposed target, not stored inventory or verified study identity. Retrieved reports '
    'with source descriptors can receive a scaffold regardless of their full-text decision. '
    'Supply source descriptors or establish retrieval first when indicated; do not mark a report '
    'included merely to create a template. Supplied digests remain unverified.'
)


def review(protocol, report_id=None, study_id=None):
    """Validate the entire protocol before filtering exact identifiers."""
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    result = link_report_study_inventory(protocol, research.get('bibliographic_collection'))
    complete_counts = copy.deepcopy(result['counts'])
    if study_id is not None and report_id is None:
        raise ValueError('study_id selection requires report_id')
    if report_id is not None:
        if not isinstance(report_id, str) or report_id not in {row['report_id'] for row in result['report_targets']}:
            raise ValueError('unknown report study inventory report_id selection')
        if study_id is not None and (not isinstance(study_id, str) or
                                    (report_id, study_id) not in {(row['report_id'], row['study_id'])
                                                                for row in result['candidate_targets']}):
            raise ValueError('unknown report study inventory exact pair selection')
        def selected(row):
            return row['report_id'] == report_id and (study_id is None or row['study_id'] == study_id)
        result['report_targets'] = [row for row in result['report_targets'] if row['report_id'] == report_id]
        result['source_ledger'] = [row for row in result['source_ledger'] if row['source']['report_id'] == report_id]
        for key in ('candidate_targets', 'pair_inventory_ledger'):
            result[key] = [row for row in result[key] if selected(row)]
        for key in ('inventory_ledger',):
            result[key] = [row for row in result[key] if selected(row['inventory'])]
        records = {item['record_id'] for target in result['report_targets'] for item in target['source_basis']['mapped_records']}
        result['record_targets'] = [row for row in result['record_targets'] if row['record_id'] in records]
        searches = {item['search_index'] for target in result['record_targets'] for item in target['source_basis']['occurrences']}
        result['source_contexts'] = [row for row in result['source_contexts'] if row['search_index'] in searches]
        result['counts'] = _counts(result)
    implementation = dict(engine_hashes())
    for filename in ('report_study_inventory.py', 'report_study_inventory_links.py'):
        implementation[filename] = hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
    result.update(schema_version=1, protocol_version=copy.deepcopy(protocol['version']),
                  protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                  engine_sha256=implementation,
                  hash_scope='Sorted compact UTF-8 supplied JSON; object key order ignored, list order retained; not authentication.',
                  selection=dict(scope=('ALL_DESCRIBED_PAIRS' if report_id is None else
                                        'EXACT_REPORT_ID' if study_id is None else 'EXACT_REPORT_STUDY_PAIR'),
                                 report_id=report_id, study_id=study_id, counts_scope='SELECTED_STORED_INVENTORY',
                                 validation_scope='ENTIRE_PROTOCOL'),
                  protocol_counts=complete_counts, protocol_changed=False, external_calls=0)
    return result


def template(protocol, report_id=None, study_id=None):
    """Scaffold only one explicit label, without pretending it is a stored assertion."""
    # Full validation precedes selection and all template work.
    result = review(protocol, report_id)
    if report_id is None or study_id is None:
        raise ValueError('template requires explicit report_id and human-supplied study_id')
    # Candidate templates must retain the validated mapped CSV provenance too.
    context = run(protocol)
    target = prepare_candidate_target(protocol, report_id, study_id, context.get('bibliographic_collection'))
    result['candidate_targets'] = [row for row in result['candidate_targets'] if row['study_id'] == study_id]
    result['pair_inventory_ledger'] = [row for row in result['pair_inventory_ledger'] if row['study_id'] == study_id]
    result['inventory_ledger'] = [row for row in result['inventory_ledger'] if row['inventory']['study_id'] == study_id]
    result['counts'] = _counts(result)
    result['selection'].update(scope='EXPLICIT_PROPOSED_REPORT_STUDY_PAIR', study_id=study_id)
    result['supplied_inventory_stage'] = result['inventory_stage']
    result['stage'] = 'AWAITING_SUPPLIED_INVENTORY'
    result['template_warning'] = TEMPLATE_WARNING
    result['proposed_target'] = target
    result['report_study_inventory'] = []
    result['source_first_candidates'] = []
    result['retrieval_required_candidates'] = []
    pair = dict(report_id=report_id, study_id=study_id)
    if target['retrieval'] != 'retrieved':
        result['retrieval_required_candidates'].append(pair)
    if target['source_binding_state'] == 'SOURCE_NOT_SUPPLIED':
        result['source_first_candidates'].append(pair)
    if target['retrieval'] == 'retrieved' and target['source_binding_state'] != 'SOURCE_NOT_SUPPLIED':
        result['report_study_inventory'].append(dict(
            inventory_id=None, report_id=report_id, study_id=study_id, recorded_by=None,
            recorded_at=None, description=None, source_locator=None, source_ids=None,
            source_basis_sha256=target['source_basis_sha256']))
    return result


def render_text(result):
    show = quoted_display
    lines = ['Supplied descriptive report-study inventory', 'Stage: ' + result['stage'],
             'Selection: ' + show(result['selection']), 'Selected stored counts: ' + show(result['counts']),
             'Protocol counts: ' + show(result['protocol_counts']),
             'Protocol SHA-256: ' + show(result['protocol_sha256'])]
    for key, label in [('pair_inventory_ledger', 'Described pair comparison'),
                       ('inventory_ledger', 'Supplied description assertion'),
                       ('source_ledger', 'Supplied document declaration'),
                       ('source_contexts', 'Supplied source context'),
                       ('record_targets', 'Exact record source target'),
                       ('report_targets', 'Exact report source target'),
                       ('candidate_targets', 'Explicitly described pair source target')]:
        for row in result[key]:
            lines.append(label + ': ' + show(row))
    if 'report_study_inventory' in result:
        lines.extend([result['template_warning'], 'Proposed target: ' + show(result['proposed_target']),
                      'Source descriptors required first: ' + show(result['source_first_candidates']),
                      'Retrieval required first: ' + show(result['retrieval_required_candidates']),
                      'Unfilled new assertions: ' + show(result['report_study_inventory'])])
    lines.extend(['Inventory completeness, study identity and independence: NOT_ESTABLISHED.',
                  'Eligibility assessment and document bytes verification: NOT_PERFORMED.',
                  'Source authenticity: NOT_VERIFIED.', result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--report-id')
    parser.add_argument('--study-id')
    parser.add_argument('--template', action='store_true')
    parser.add_argument('--text', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        protocol = parse_json(args.protocol.read_bytes())
        result = (template if args.template else review)(protocol, args.report_id, args.study_id)
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        rendered = render_text(result) if args.text else encoded
        encoded.encode('utf-8')
        rendered.encode('utf-8')
        if args.output is not None:
            with args.output.open('x', encoding='utf-8', newline='\n') as output:
                output.write(encoded)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        parser.exit(1, 'report study inventory error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
