"""Inspect described candidate study review positions or draft unfilled human assertions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from research_bundle import engine_hashes
from report_study_inventory_review_links import link_report_study_inventory_reviews, _counts

TEMPLATE_WARNING = (
    'Separate unfilled human assertion scaffolds, not a protocol or approved review. '
    'Supply all human fields and explicitly select reviewed_inventory_ids and reviewed_source_ids; '
    'no inventory or source subset is chosen automatically. Preserve the exact source hash '
    'actually reviewed. Existing assertions are never copied, renewed or replaced. Only '
    'currently described candidate pairs on retrieved reports with supplied source descriptors '
    'receive scaffolds, regardless of report eligibility or membership. Supply source descriptors '
    'or establish retrieval first when indicated; never include a report just to obtain a scaffold. '
    'Orphans receive no fresh scaffold. Current review context never upgrades stale descriptions '
    'or verifies document bytes, reading, correctness or canonical study selection.'
)


def review(protocol, report_id=None, study_id=None):
    """Validate the entire protocol before filtering exact identifiers."""
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    result = link_report_study_inventory_reviews(protocol, research.get('bibliographic_collection'))
    complete_counts = copy.deepcopy(result['counts'])
    if study_id is not None and report_id is None:
        raise ValueError('study_id selection requires report_id')
    if report_id is not None:
        if not isinstance(report_id, str) or report_id not in {row['report_id'] for row in result['report_targets']}:
            raise ValueError('unknown report study inventory review report_id selection')
        if study_id is not None and (not isinstance(study_id, str) or
                                    (report_id, study_id) not in {(row['report_id'], row['study_id'])
                                                                for row in result['candidate_targets']}):
            raise ValueError('unknown report study inventory review exact pair selection')
        def selected(row):
            return row['report_id'] == report_id and (study_id is None or row['study_id'] == study_id)
        result['report_targets'] = [row for row in result['report_targets'] if row['report_id'] == report_id]
        result['source_ledger'] = [row for row in result['source_ledger'] if row['source']['report_id'] == report_id]
        for key in ('candidate_targets', 'candidate_review_ledger', 'current_candidates_with_review_cues',
                    'inventory_candidate_targets', 'pair_inventory_ledger'):
            result[key] = [row for row in result[key] if selected(row)]
        for key in ('review_ledger', 'orphan_review_assertions'):
            result[key] = [row for row in result[key] if selected(row['review'])]
        result['inventory_ledger'] = [row for row in result['inventory_ledger'] if selected(row['inventory'])]
        records = {item['record_id'] for target in result['report_targets'] for item in target['source_basis']['mapped_records']}
        result['record_targets'] = [row for row in result['record_targets'] if row['record_id'] in records]
        searches = {item['search_index'] for target in result['record_targets'] for item in target['source_basis']['occurrences']}
        result['source_contexts'] = [row for row in result['source_contexts'] if row['search_index'] in searches]
        result['counts'] = _counts(result)
    implementation = dict(engine_hashes())
    for filename in ('report_study_inventory_review.py', 'report_study_inventory_review_links.py'):
        implementation[filename] = hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
    result.update(schema_version=1, protocol_version=copy.deepcopy(protocol['version']),
                  protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                  engine_sha256=implementation,
                  hash_scope='Sorted compact UTF-8 supplied JSON; object key order ignored, list order retained; not authentication.',
                  selection=dict(scope=('ALL_DESCRIBED_OR_REFERENCED_PAIRS' if report_id is None else
                                        'EXACT_REPORT_ID' if study_id is None else 'EXACT_REPORT_STUDY_PAIR'),
                                 report_id=report_id, study_id=study_id, counts_scope='SELECTED_PAIR_VIEWS',
                                 validation_scope='ENTIRE_PROTOCOL'),
                  protocol_counts=complete_counts, protocol_changed=False, external_calls=0)
    return result


def template(protocol, report_id=None, study_id=None):
    """Blank human fields and source selection; never renew a supplied assertion."""
    result = review(protocol, report_id, study_id)
    result['supplied_review_stage'] = result['review_stage']
    result['stage'] = 'AWAITING_SUPPLIED_REVIEWS'
    result['template_warning'] = TEMPLATE_WARNING
    result['report_study_inventory_reviews'] = []
    result['source_first_candidates'], result['retrieval_required_candidates'] = [], []
    for target in result['candidate_targets']:
        if not target['inventory_currently_described']:
            continue
        pair = dict(report_id=target['report_id'], study_id=target['study_id'])
        if target['retrieval'] != 'retrieved':
            result['retrieval_required_candidates'].append(pair)
        if target['source_binding_state'] == 'SOURCE_NOT_SUPPLIED':
            result['source_first_candidates'].append(pair)
        if target['retrieval'] != 'retrieved' or target['source_binding_state'] == 'SOURCE_NOT_SUPPLIED':
            continue
        result['report_study_inventory_reviews'].append(dict(
            review_id=None, report_id=target['report_id'], study_id=target['study_id'],
            reviewer=None, reviewed_at=None, decision=None, rationale=None, reviewed_locator=None,
            reviewed_inventory_ids=None, reviewed_source_ids=None,
            source_basis_sha256=target['source_basis_sha256']))
    return result


def render_text(result):
    show = quoted_display
    lines = ['Supplied candidate-study eligibility review', 'Stage: ' + result['stage'],
             'Selection: ' + show(result['selection']), 'Counts: ' + show(result['counts']),
             'Protocol SHA-256: ' + show(result['protocol_sha256'])]
    for key, label in [('candidate_review_ledger', 'Candidate comparison'), ('review_ledger', 'Supplied assertion'),
                       ('inventory_ledger', 'Supplied inventory assertion'),
                       ('pair_inventory_ledger', 'Inventory source comparison'),
                       ('source_ledger', 'Supplied document declaration'), ('source_contexts', 'Supplied source context'),
                       ('record_targets', 'Exact record source target'), ('report_targets', 'Exact report source target'),
                       ('candidate_targets', 'Exact report-study source target'),
                       ('orphan_review_assertions', 'Retrospective orphan assertion')]:
        for row in result[key]:
            lines.append(label + ': ' + show(row))
    lines.append('Current candidate review cues: ' + show(result['current_candidates_with_review_cues']))
    if 'report_study_inventory_reviews' in result:
        lines.extend([result['template_warning'], 'Source descriptors required first: ' + show(result['source_first_candidates']),
                      'Retrieval required first: ' + show(result['retrieval_required_candidates']),
                      'Unfilled new assertions: ' + show(result['report_study_inventory_reviews'])])
    lines.extend(['Canonical study selection: NOT_MODELED; eligibility correctness: NOT_ASSESSED.',
                  'Document bytes verification: NOT_PERFORMED; source authenticity: NOT_VERIFIED.',
                  'Reviewer identity, authentication and independence: NOT_ESTABLISHED.', result['boundary']])
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
        parser.exit(1, 'report study inventory review error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
