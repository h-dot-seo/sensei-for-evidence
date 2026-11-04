"""Inspect supplied title/abstract review positions or draft unfilled assertions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes
from prisma_reports import report_flow
from screening_links import link_screening_reviews

TEMPLATE_WARNING = (
    'Unfilled new assertion scaffold, not a protocol or an approved review. Supply each missing field '
    'and preserve the exact source hash reviewed. Existing assertions are not copied, refreshed or replaced. '
    'For a record with existing assertions this is a separate blank draft; one active assertion per '
    'exact record/reviewer label is allowed. No canonical decision is written.'
)


def review(protocol, record_id=None):
    """Validate the entire protocol before returning a detached, optionally selected view."""
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    result = link_screening_reviews(protocol, research.get('bibliographic_collection'))
    complete_counts = copy.deepcopy(result['counts'])
    if record_id is not None:
        if not isinstance(record_id, str) or record_id not in {row['record_id'] for row in result['record_targets']}:
            raise ValueError('unknown screening review record_id selection')
        result['record_targets'] = [row for row in result['record_targets'] if row['record_id'] == record_id]
        result['review_ledger'] = [row for row in result['review_ledger'] if row['review']['record_id'] == record_id]
        result['record_review_ledger'] = [row for row in result['record_review_ledger'] if row['record_id'] == record_id]
        result['records_with_review_cues'] = [rid for rid in result['records_with_review_cues'] if rid == record_id]
        referenced = {item['search_index'] for target in result['record_targets']
                      for item in target['source_basis']['occurrences']}
        result['source_contexts'] = [row for row in result['source_contexts'] if row['search_index'] in referenced]
        current = sum(row['source_match_status'] == 'CURRENT_SOURCE' for row in result['review_ledger'])
        result['counts'] = dict(records=1, review_assertions=len(result['review_ledger']),
                               current_source_reviews=current,
                               stale_source_reviews=len(result['review_ledger'])-current,
                               records_with_review_cues=len(result['records_with_review_cues']))
    implementation = dict(engine_hashes())
    implementation['screening_review.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result.update(schema_version=1, protocol_version=copy.deepcopy(protocol['version']),
                  protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                  engine_sha256=implementation,
                  hash_scope='Sorted compact UTF-8 supplied JSON; object key order ignored, list order retained; not authentication.',
                  selection=dict(scope='ALL_ENUMERATED_RECORDS' if record_id is None else 'EXACT_RECORD_ID',
                                 record_id=record_id, counts_scope='SELECTED_RECORDS',
                                 validation_scope='ENTIRE_PROTOCOL'),
                  protocol_counts=complete_counts, protocol_changed=False, external_calls=0)
    return result


def template(protocol, record_id=None):
    """Return blank separate assertions; never recycle reviewer labels or dates."""
    result = review(protocol, record_id)
    result['supplied_review_stage'] = result['stage']
    result['stage'] = 'AWAITING_SUPPLIED_REVIEWS'
    result['template_warning'] = TEMPLATE_WARNING
    result['screening_reviews'] = [dict(review_id=None, record_id=target['record_id'], reviewer=None,
                                        reviewed_at=None, decision=None, rationale=None, source_locator=None,
                                        source_basis_sha256=target['source_basis_sha256'])
                                   for target in result['record_targets']]
    return result


def render_text(result):
    show = quoted_display
    lines = ['Supplied title/abstract screening review', 'Stage: ' + result['stage'],
             'Selection: ' + show(result['selection']), 'Counts: ' + show(result['counts']),
             'Protocol SHA-256: ' + show(result['protocol_sha256'])]
    for row in result['record_review_ledger']:
        lines.append('Record comparison: ' + show(row))
    for row in result['review_ledger']:
        lines.append('Supplied assertion: ' + show(row))
    for row in result['source_contexts']:
        lines.append('Supplied source context: ' + show(row))
    for row in result['record_targets']:
        lines.append('Exact source target: ' + show(row))
    if 'screening_reviews' in result:
        lines.extend([result['template_warning'], 'Unfilled new assertions: ' + show(result['screening_reviews'])])
    lines.extend(['Reviewer identity: NOT_ESTABLISHED; source authenticity: NOT_VERIFIED.',
                  'Eligibility correctness: NOT_ASSESSED; adjudication: NOT_PERFORMED.', result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--record-id')
    parser.add_argument('--template', action='store_true')
    parser.add_argument('--text', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        protocol = parse_json(args.protocol.read_bytes())
        result = (template if args.template else review)(protocol, args.record_id)
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        rendered = render_text(result) if args.text else encoded
        if args.output is not None:
            with args.output.open('x', encoding='utf-8', newline='\n') as output:
                output.write(encoded)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        parser.exit(1, 'screening review error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
