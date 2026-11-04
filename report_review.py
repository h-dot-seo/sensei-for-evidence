"""Inspect supplied full-text review positions or draft unfilled source/review assertions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes
from prisma_reports import report_flow
from report_review_links import link_report_reviews, _counts

TEMPLATE_WARNING = (
    'Separate unfilled scaffolds only, not a protocol or an approved review. Supply human fields '
    'and preserve the exact source hash actually reviewed. Existing human fields and hashes are '
    'never copied, refreshed or replaced. Source scaffolds require regeneration before binding '
    'a review. DOCUMENT_BYTES_UNBOUND means at least one document digest is missing; no digest '
    'is invented or computed from a locator. Even SUPPLIED_DIGESTS are unverified. A source-basis '
    'hash does not prove a document was available or read. Pending/not-retrieved reports have no '
    'new full-text assertion scaffold. No canonical decision is written.'
)


def review(protocol, report_id=None):
    """Validate the entire input before selecting a detached report view."""
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    result = link_report_reviews(protocol, research.get('bibliographic_collection'))
    complete_counts = copy.deepcopy(result['counts'])
    if report_id is not None:
        if not isinstance(report_id, str) or report_id not in {row['report_id'] for row in result['report_targets']}:
            raise ValueError('unknown report review report_id selection')
        result['report_targets'] = [row for row in result['report_targets'] if row['report_id'] == report_id]
        result['source_ledger'] = [row for row in result['source_ledger'] if row['source']['report_id'] == report_id]
        result['review_ledger'] = [row for row in result['review_ledger'] if row['review']['report_id'] == report_id]
        result['report_review_ledger'] = [row for row in result['report_review_ledger'] if row['report_id'] == report_id]
        result['reports_with_review_cues'] = [rid for rid in result['reports_with_review_cues'] if rid == report_id]
        records = {item['record_id'] for target in result['report_targets'] for item in target['source_basis']['mapped_records']}
        result['record_targets'] = [row for row in result['record_targets'] if row['record_id'] in records]
        searches = {item['search_index'] for target in result['record_targets'] for item in target['source_basis']['occurrences']}
        result['source_contexts'] = [row for row in result['source_contexts'] if row['search_index'] in searches]
        result['counts'] = _counts(result)
    implementation = dict(engine_hashes())
    implementation['report_review.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    implementation['report_review_links.py'] = hashlib.sha256(Path(__file__).with_name('report_review_links.py').read_bytes()).hexdigest()
    result.update(schema_version=1, protocol_version=copy.deepcopy(protocol['version']),
                  protocol_sha256=hashlib.sha256(canonical_json_bytes(protocol)).hexdigest(),
                  engine_sha256=implementation,
                  hash_scope='Sorted compact UTF-8 supplied JSON; object key order ignored, list order retained; not authentication.',
                  selection=dict(scope='ALL_ENUMERATED_REPORTS' if report_id is None else 'EXACT_REPORT_ID',
                                 report_id=report_id, counts_scope='SELECTED_REPORTS', validation_scope='ENTIRE_PROTOCOL'),
                  protocol_counts=complete_counts, protocol_changed=False, external_calls=0)
    return result


def template(protocol, report_id=None):
    """Offer blank human assertions only where supplied retrieval/source context permits."""
    result = review(protocol, report_id)
    result['supplied_review_stage'] = result['review_stage']
    result['stage'] = 'AWAITING_SUPPLIED_REVIEWS'
    result['template_warning'] = TEMPLATE_WARNING
    result['report_sources'], result['report_reviews'] = [], []
    for target in result['report_targets']:
        if target['retrieval'] != 'retrieved':
            continue
        if target['source_binding_state'] == 'SOURCE_NOT_SUPPLIED':
            result['report_sources'].append(dict(source_id=None, report_id=target['report_id'],
                                                  source_locator=None, document_version=None, document_sha256=None))
        else:
            result['report_reviews'].append(dict(review_id=None, report_id=target['report_id'], reviewer=None,
                                                  reviewed_at=None, decision=None, rationale=None, reviewed_locator=None,
                                                  source_basis_sha256=target['source_basis_sha256']))
    return result


def render_text(result):
    show = quoted_display
    lines = ['Supplied full-text report review', 'Stage: ' + result['stage'],
             'Selection: ' + show(result['selection']), 'Counts: ' + show(result['counts']),
             'Protocol SHA-256: ' + show(result['protocol_sha256'])]
    for key, label in [('report_review_ledger', 'Report comparison'), ('review_ledger', 'Supplied assertion'),
                       ('source_ledger', 'Supplied document declaration'), ('source_contexts', 'Supplied source context'),
                       ('record_targets', 'Exact record source target'), ('report_targets', 'Exact report source target')]:
        for row in result[key]:
            lines.append(label + ': ' + show(row))
    if 'report_reviews' in result:
        lines.extend([result['template_warning'], 'Unfilled source declarations: ' + show(result['report_sources']),
                      'Unfilled new assertions: ' + show(result['report_reviews'])])
    lines.extend(['Document bytes verification: NOT_PERFORMED; source authenticity: NOT_VERIFIED.',
                  'Reviewer identity and independence: NOT_ESTABLISHED.',
                  'Eligibility correctness: NOT_ASSESSED; adjudication: NOT_PERFORMED.', result['boundary']])
    return '\n'.join(lines) + '\n'


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('--report-id')
    parser.add_argument('--template', action='store_true')
    parser.add_argument('--text', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        protocol = parse_json(args.protocol.read_bytes())
        result = (template if args.template else review)(protocol, args.report_id)
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        rendered = render_text(result) if args.text else encoded
        encoded.encode('utf-8')
        rendered.encode('utf-8')
        if args.output is not None:
            with args.output.open('x', encoding='utf-8', newline='\n') as output:
                output.write(encoded)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        parser.exit(1, 'report review error: ' + quoted_display(str(error)) + '\n')
    print(rendered, end='')


if __name__ == '__main__':
    main()
