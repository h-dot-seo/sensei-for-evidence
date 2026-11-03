"""Assemble mock provider receipts and reviewed extraction candidates, without network access."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from evidence_workflow import run
from prisma_reports import report_flow
from search_audit import completion_issues
from adapter_integrity import prepare_exchange, review_decisions
from json_io import configure_utf8_stdio, parse_json

BOUNDARY = ('Mock provider responses are unverified candidates. Review entries are supplied '
            'operator assertions, not independent source verification or scientific appraisal. '
            'No external search, model call, identity matching or census claim is performed.')


def assemble(protocol, fixture, reviews=None):
    """Normalize a versioned mock exchange; never execute provider-supplied instructions."""
    protocol_sha256, targets, searches, candidates, search_by_request, provider = prepare_exchange(protocol, fixture)
    assembled = copy.deepcopy(protocol)
    if reviews is None:
        reviews = []
    decisions = review_decisions(reviews, targets)
    for search in searches:
        key = ('search', search['search_id'])
        review = decisions.get(key)
        search['complete'] = review is not None and review['decision'] == 'accept'
        if search['complete'] and completion_issues(search):
            raise ValueError('cannot accept search receipt with unresolved page/count issues')
        search['adapter_provenance'] = dict(receipt_sha256=targets[key]['sha256'], provider=provider,
                                            source_verification='UNVERIFIED_PROVIDER_RESPONSE', review=review)
    for receipt in candidates:
        key = ('extraction', receipt['target_id'])
        review = decisions.get(key)
        if review is not None and review['decision'] == 'accept':
            candidate = receipt['candidate']
            search_review = decisions.get(('search', search_by_request[candidate['request_id']]))
            if search_review is None or search_review['decision'] != 'accept':
                raise ValueError('accepted extraction requires an accepted search receipt review')
            row = copy.deepcopy(candidate['proposal'])
            row['record_id'] = candidate['record_id']
            row['adapter_provenance'] = dict(candidate_id=receipt['target_id'], receipt_sha256=receipt['sha256'],
                                            search_receipt_sha256=receipt['search_receipt_sha256'], provider=provider,
                                            source_verification='UNVERIFIED_PROVIDER_RESPONSE', review=review)
            assembled['evidence'].append(row)
    assembled['searches'] = searches
    assembled['adapter_receipts'] = dict(schema_version=1, provider=provider, base_protocol_sha256=protocol_sha256,
        base_protocol=copy.deepcopy(protocol),
        adapter_engine_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        receipts=list(targets.values()), reviews=copy.deepcopy(reviews), boundary=BOUNDARY)
    research = run(assembled)
    reports = report_flow(assembled) if 'reports' in assembled else None
    pending = [dict(target_type=kind, target_id=tid, target_sha256=receipt['sha256'])
               for (kind, tid), receipt in targets.items() if (kind, tid) not in decisions]
    return dict(protocol=assembled, research=research, reports=reports, review_pending=pending,
                rejected=[dict(target_type=k[0], target_id=k[1]) for k, r in decisions.items() if r['decision'] == 'reject'],
                adapter_mode='mock', external_calls=0, census_claim='NOT_ESTABLISHED',
                conclusion_readiness='NOT_READY', boundary=BOUNDARY)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--reviews', type=Path)
    parser.add_argument('--protocol-output', type=Path, help='write the assembled protocol exclusively; never overwrite')
    args = parser.parse_args()
    try:
        result = assemble(parse_json(args.protocol.read_bytes()), parse_json(args.fixture.read_bytes()),
                          parse_json(args.reviews.read_bytes()) if args.reviews else None)
        if args.protocol_output is not None:
            with args.protocol_output.open('x', encoding='utf-8', newline='\n') as output:
                output.write(json.dumps(result['protocol'], ensure_ascii=False, indent=2) + '\n')
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
