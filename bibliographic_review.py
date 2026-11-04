"""Apply explicit supplied CSV identity decisions without asserting search completeness."""
import argparse
import copy
import json
from pathlib import Path

from bibliographic_intake import artifact_bytes, read_bounded, verify, MAX_ARTIFACT_BYTES
from bibliographic_integrity import (digest, normalize_resolutions, reconciliation_target,
                                     validate_review, normalized_search)
from evidence_workflow import run
from prisma_reports import report_flow
from json_io import configure_utf8_stdio, parse_json, quoted_display

BOUNDARY = (
    'Explicit supplied collection reconciliation, not authenticated human review or verified publication identity. '
    'CSV rows remain distinct from canonical search memberships and title/abstract decisions. '
    'Withholding a row is collection triage, not a screening exclusion. '
    'Imports append incomplete searches without creating screening, report or evidence decisions. '
    'File EOF, accepted identity mappings and successful byte checks do not establish source authenticity, '
    'search completeness, PRISMA compliance or scientific/clinical validity. No external calls occur. '
    'Artifacts retain supplied private text; keep real inputs and outputs outside the public repository.'
)


def template(artifact):
    verify(artifact)
    return dict(schema_version=1,
                resolutions=[dict(candidate_id=row['candidate_id'], disposition=None, record_id=None, rationale=None)
                             for row in artifact['parsed_export']['record_rows']], review=None)


def check_document(document, reviewed):
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'resolutions', 'review'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1):
        raise ValueError('review document requires exactly schema_version, resolutions and review')
    if not reviewed and document['review'] is not None:
        raise ValueError('target preparation requires review=null; never renew an existing review automatically')


def inputs(protocol, artifact, rows):
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol)
    verify(artifact)
    if 'adapter_receipts' in protocol:
        raise ValueError('local CSV promotion cannot mix with mock adapter receipts; do not erase existing work')
    ledger = protocol.get('bibliographic_imports')
    base = protocol if ledger is None else ledger['base_protocol']
    if 'bibliographic_imports' in artifact['protocol_snapshot'] or 'adapter_receipts' in artifact['protocol_snapshot']:
        raise ValueError('intake must use a ledger-free common base, not an intermediate imported or mock protocol')
    if digest(artifact['protocol_snapshot']) != digest(base):
        raise ValueError('intake snapshot differs from the exact common base; no automatic rebase')
    search_id = artifact['search_request']['search_id']
    if any(row.get('search_id') == search_id for row in protocol['searches']):
        raise ValueError('selected planned search already has a search; never replace or duplicate it')
    existing = {rid for search in protocol['searches'] for rid in search['record_ids']}
    normalized = normalize_resolutions(artifact, rows, existing)
    target = reconciliation_target(artifact, protocol, normalized)
    return research, base, ledger, normalized, target


def prepare_review(protocol, artifact, document):
    check_document(document, reviewed=False)
    research, _, ledger, rows, target = inputs(protocol, artifact, document['resolutions'])
    review = dict(target_sha256=target['target_sha256'], reviewer=None, reviewed_at=None,
                  rationale=None, decision=None)
    return dict(schema_version=1, status='AWAITING_SUPPLIED_REVIEW',
                review_document=dict(schema_version=1, resolutions=rows, review=review),
                reconciliation_target=target,
                artifact_base_version=artifact['protocol_snapshot']['version'],
                current_protocol_version=protocol['version'], current_record_flow=copy.deepcopy(research['flow']),
                preceding_imports=0 if ledger is None else len(ledger['imports']),
                overlap_scope='Resolution checks use the current protocol; intake overlap hints describe only the common base',
                protocol_changed=False, review_status='NOT_PERFORMED',
                external_calls=0, census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def assemble(protocol, artifact, document):
    check_document(document, reviewed=True)
    _, base, ledger, rows, target = inputs(protocol, artifact, document['resolutions'])
    validate_review(document['review'], target)
    index = 0 if ledger is None else len(ledger['imports'])
    entry = dict(intake=copy.deepcopy({key: value for key, value in artifact.items() if key != 'protocol_snapshot'}),
                 prior_protocol_body=copy.deepcopy({key: value for key, value in protocol.items() if key != 'bibliographic_imports'}),
                 prior_prefix_count=index, resolutions=rows, reconciliation_target=target,
                 review=copy.deepcopy(document['review']))
    entry['sha256'] = digest(entry)
    candidate = copy.deepcopy(protocol)
    if ledger is None:
        candidate['bibliographic_imports'] = dict(schema_version=1, base_protocol=copy.deepcopy(base), imports=[])
    candidate['bibliographic_imports']['imports'].append(entry)
    candidate['searches'].append(normalized_search(artifact, entry, index))
    artifact_bytes(candidate)
    research = run(candidate)
    if 'reports' in candidate:
        report_flow(candidate)
    return dict(schema_version=1, status='SUPPLIED_RECONCILIATION_IMPORTED', protocol_candidate=candidate,
                reconciliation_target=target, bibliographic_collection=research['bibliographic_collection'],
                artifact_base_version=base['version'], reviewed_protocol_version=protocol['version'],
                new_searches=1, new_screening_decisions=0, new_reports=0, new_evidence_rows=0,
                search_completion='NOT_ESTABLISHED', source_authenticity='NOT_VERIFIED',
                record_identity_verification='NOT_ESTABLISHED', external_calls=0,
                census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def render_text(result):
    show = quoted_display
    if 'status' not in result:
        return ('Unfilled CSV reconciliation document\n'
                'Supply each row disposition, canonical record ID where applicable, and rationale.\n'
                'No identity choice or export-level review has been supplied.\n'
                + show(result) + '\n' + BOUNDARY + '\n')
    lines = ['Local bibliographic reconciliation', 'Status: ' + result['status'],
             'Exact review target (not authenticated approval): ' + show(result['reconciliation_target']),
             'Artifact common-base version: ' + show(result['artifact_base_version']),
             'Reviewed current version: ' + show(result.get('current_protocol_version', result.get('reviewed_protocol_version')))]
    if 'review_document' in result:
        lines.extend(['Explicit row choices: ' + show(result['review_document']['resolutions']),
                      'Current supplied record flow: ' + show(result['current_record_flow']),
                      result['overlap_scope'], 'No protocol changed; fill the separate review document before assembly.'])
    else:
        lines.extend(['Collection accounting: ' + show(result['bibliographic_collection']['counts']),
                      'One incomplete search appended. Existing work and eligibility/extraction decisions retained.',
                      'Withheld CSV rows remain in the collection ledger; they are not screening exclusions.'])
    lines.extend(['External calls: 0', 'Census: NOT_ESTABLISHED', 'Conclusion: NOT_READY', BOUNDARY])
    return '\n'.join(lines) + '\n'


def load(path):
    return parse_json(read_bounded(path, MAX_ARTIFACT_BYTES))


def write_new(path, value):
    raw = artifact_bytes(value)
    with path.open('xb') as output:
        output.write(raw)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    draft = commands.add_parser('template')
    draft.add_argument('artifact', type=Path)
    draft.add_argument('--review-output', type=Path)
    draft.add_argument('--text', action='store_true')
    target = commands.add_parser('target')
    accepted = commands.add_parser('assemble')
    for command in (target, accepted):
        command.add_argument('protocol', type=Path)
        command.add_argument('artifact', type=Path)
        command.add_argument('review_document', type=Path)
        command.add_argument('--text', action='store_true')
    target.add_argument('--review-output', type=Path)
    accepted.add_argument('--protocol-output', type=Path)
    args = parser.parse_args()
    try:
        artifact = load(args.artifact)
        if args.command == 'template':
            result = template(artifact)
            if args.review_output is not None:
                write_new(args.review_output, result)
        elif args.command == 'target':
            result = prepare_review(load(args.protocol), artifact, load(args.review_document))
            if args.review_output is not None:
                write_new(args.review_output, result['review_document'])
        else:
            result = assemble(load(args.protocol), artifact, load(args.review_document))
            if args.protocol_output is not None:
                write_new(args.protocol_output, result['protocol_candidate'])
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        parser.exit(1, 'bibliographic review error: ' + quoted_display(str(error)) + '\n')
    print(render_text(result) if args.text else json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False),
          end='' if args.text else '\n')


if __name__ == '__main__':
    main()
