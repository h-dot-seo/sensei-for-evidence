"""Append supplied exact described-candidate positions through separate exact-target import review and replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from challenge_intake import _normalized, _schema, REVIEW_FIELDS
from reviewed_intake_safety import validate_import_review, replay_application
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes
from screening_decision_batch_apply import _read, _encode, _write_new
import report_study_inventory_review
import report_study_inventory_review_links

MAX_PROTOCOL_BYTES = 50_000_000
MAX_CANDIDATE_BYTES = 10_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_POSITIONS = 100
BOUNDARY = (
    'Append-only supplied human positions on currently described candidate report-study pairs. '
    'Not membership positions or canonical study selection. Both reviewed_inventory_ids and '
    'reviewed_source_ids are explicit human subsets, never inferred or equated. New rows require '
    'a retrieved source-declared report, currently described exact pair and exact current candidate '
    'review basis, including all ordered same-pair descriptions. Pending/excluded report eligibility '
    'is permitted; unavailable retrieval is not. A current position can cite a stale description '
    'without upgrading its source status. Null digests remain unbound; other digests unverified. '
    'Existing stale/orphan positions, inventory descriptions, sources, memberships, report decisions '
    'and evidence remain unchanged. Duplicate IDs or report/study/reviewer tuples fail. No renewal, '
    'supersession, voting, reading, identity, authenticity, coverage or adjudication is inferred. '
    'Separate import review authorizes recording only, not scientific endorsement. Exact replay '
    'binds original, supplied rows, review and implementation, not authentication or chronology. '
    'Locators are inert; no fetching/model/network calls. Detached import IDs are not globally '
    'verified. Keep real inputs/applications outside this public repository.'
)

NEGATIVE_CLAIMS = dict(original_protocol_changed=False, canonical_reports_changed=False, memberships_changed=False, inventory_descriptions_changed=False, canonical_study_selection='NOT_MODELED',
    source_declarations_changed=False, document_bytes_verification='NOT_PERFORMED',
    source_authenticity='NOT_VERIFIED', reviewer_identity='NOT_ESTABLISHED', reading='NOT_ESTABLISHED',
    adjudication='NOT_PERFORMED', conclusion_readiness='NOT_READY', external_calls=0)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _hashes():
    root = Path(__file__).resolve().parent
    names = ('report_study_inventory_review_intake.py','report_study_inventory_review.py','report_study_inventory_review_links.py',
             'challenge_intake.py','nbib_intake.py','screening_decision_batch_apply.py','reviewed_intake_safety.py')
    return dict(engine_hashes(), **{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate positions')
    _schema(document, {'schema_version','report_study_inventory_reviews'}, 'candidate positions')
    rows = document['report_study_inventory_reviews']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_POSITIONS:
        raise ValueError('candidate positions must contain 1 to 100 rows')
    before = report_study_inventory_review.review(protocol)
    known = {(row['report_id'],row['study_id']):row for row in before['candidate_targets']}
    reports = {row['report_id']:row for row in before['report_targets']}
    selected_report_ids = set()
    selected = []
    selected_bytes = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != report_study_inventory_review_links.REVIEW_FIELDS:
            raise ValueError('candidate review has unknown or missing fields')
        if any(not isinstance(row[key],str) or not row[key].strip() for key in report_study_inventory_review_links.REVIEW_FIELDS - {'reviewed_source_ids','reviewed_inventory_ids'}):
            raise ValueError('candidate review fields must be supplied nonblank literal strings')
        target = known.get((row['report_id'],row['study_id']))
        if target is None:
            raise ValueError('unknown candidate report/study pair')
        if (not target['inventory_currently_described'] or target['retrieval'] != 'retrieved'
                or target['source_binding_state'] == 'SOURCE_NOT_SUPPLIED'):
            raise ValueError('new pair positions require a currently described candidate, retrieved report and source descriptors')
        if row['source_basis_sha256'] != target['source_basis_sha256']:
            raise ValueError('stale source_basis_sha256; re-examine context, never refresh automatically')
        sources = row['reviewed_source_ids']
        if (not isinstance(sources,list) or not sources or any(not isinstance(sid,str) or not sid.strip() for sid in sources)
                or len(set(sources)) != len(sources)):
            raise ValueError('reviewed_source_ids must be an explicit nonempty unique list')
        same_report = {source['source_id'] for source in reports[row['report_id']]['source_basis']['report_sources']}
        if any(sid not in same_report for sid in sources):
            raise ValueError('reviewed_source_ids must select existing same-report descriptors')
        inventory_ids = row['reviewed_inventory_ids']
        if (not isinstance(inventory_ids,list) or not inventory_ids
                or any(not isinstance(iid,str) or not iid.strip() for iid in inventory_ids)
                or len(set(inventory_ids)) != len(inventory_ids)):
            raise ValueError('reviewed_inventory_ids must be an explicit nonempty unique list')
        if any(iid not in target['inventory_ids'] for iid in inventory_ids):
            raise ValueError('reviewed_inventory_ids must select existing exact-pair descriptions')
        selected_bytes += len(canonical_json_bytes(target))
        if row['report_id'] not in selected_report_ids:
            selected_bytes += len(canonical_json_bytes(reports[row['report_id']]))
            selected_report_ids.add(row['report_id'])
        if selected_bytes > MAX_APPLICATION_BYTES:
            raise ValueError('selected source snapshots exceed target byte budget')
        selected.append(copy.deepcopy(target))
    candidate = copy.deepcopy(protocol)
    candidate.setdefault('report_study_inventory_reviews', []).extend(copy.deepcopy(rows))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    # Reuse the complete existing validator for dates, choices and old/new duplicate IDs/tuples.
    after = report_study_inventory_review.review(candidate)
    prefix = len(protocol.get('report_study_inventory_reviews', []))
    restored = copy.deepcopy(candidate)
    if 'report_study_inventory_reviews' in protocol:
        restored['report_study_inventory_reviews'] = restored['report_study_inventory_reviews'][:prefix]
    else:
        restored.pop('report_study_inventory_reviews')
    if canonical_json_bytes(restored) != canonical_json_bytes(protocol):
        raise ValueError('intake changed original fields or old review prefix')
    target = dict(schema_version=1, target_type='report_study_inventory_review_positions_intake',
        input_protocol_sha256=digest(protocol), candidate_document_sha256=digest(document),
        candidate_document=document, selected_candidate_targets=selected,
        selected_report_targets=[copy.deepcopy(reports[rid]) for rid in sorted(selected_report_ids)],
        appended_positions=[dict(candidate_index=i, output_pointer=f'/report_study_inventory_reviews/{prefix+i}',review=copy.deepcopy(row))
                            for i,row in enumerate(rows)],
        before_review_cues=before['candidate_review_ledger'], after_review_cues=after['candidate_review_ledger'],
        protocol_candidate_sha256=digest(candidate), engine_sha256=_hashes(),
        **NEGATIVE_CLAIMS, boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return _normalized(target, MAX_APPLICATION_BYTES, 'target'), candidate


def prepare(protocol, document):
    target, _ = _prepare(protocol, document)
    review = {key:None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1,target_sha256=target['target_sha256'],decision='import_report_study_inventory_reviews')
    return _normalized(dict(schema_version=1,status='AWAITING_SUPPLIED_IMPORT_REVIEW',target=target,
        review_document=review, **NEGATIVE_CLAIMS,boundary=BOUNDARY),MAX_APPLICATION_BYTES,'prepared target')


def assemble(protocol, document, review_document):
    review = validate_import_review(review_document, 'import_report_study_inventory_reviews', MAX_CANDIDATE_BYTES)
    target, candidate = _prepare(protocol, document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review does not match exact original, positions and implementation; no automatic rebase')
    receipt = dict(schema_version=1,receipt_id=review['receipt_id'],assertion=review,target=target,
        candidate_document=target['candidate_document'],input_protocol_sha256=target['input_protocol_sha256'],
        protocol_candidate_sha256=digest(candidate),engine_sha256=target['engine_sha256'],
        **NEGATIVE_CLAIMS,boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1,kind='detached_report_study_inventory_review_positions_intake',
        receipt=receipt,protocol_candidate=candidate),MAX_APPLICATION_BYTES,'application')


def verify(protocol, application):
    replay = replay_application(protocol, application, 'detached_report_study_inventory_review_positions_intake', assemble, MAX_APPLICATION_BYTES)
    return dict(schema_version=1,valid=True,status='EXACT_REPLAY_MATCH',
        receipt_id=replay['receipt']['receipt_id'],receipt_sha256=replay['receipt']['receipt_sha256'],
        input_protocol_sha256=replay['receipt']['input_protocol_sha256'],
        protocol_candidate_sha256=digest(replay['protocol_candidate']),
        **NEGATIVE_CLAIMS,boundary=BOUNDARY)


def main():
    configure_utf8_stdio()
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('target','assemble','verify'):
        sub=commands.add_parser(name)
        sub.add_argument('protocol',type=Path)
        sub.add_argument('input',type=Path,help='candidate positions, or application for verify')
        if name=='assemble':sub.add_argument('review',type=Path)
        if name=='verify':
            outputs=sub.add_mutually_exclusive_group()
            outputs.add_argument('--output',type=Path)
            outputs.add_argument('--protocol-output',type=Path)
        else:sub.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        protocol=parse_json(_read(args.protocol,MAX_PROTOCOL_BYTES))
        supplied=parse_json(_read(args.input,MAX_APPLICATION_BYTES if args.command=='verify' else MAX_CANDIDATE_BYTES))
        if args.command=='target':result=prepare(protocol,supplied)
        elif args.command=='assemble':result=assemble(protocol,supplied,parse_json(_read(args.review,MAX_CANDIDATE_BYTES)))
        else:result=verify(protocol,supplied)
        encoded=_encode(result,MAX_APPLICATION_BYTES)
        if args.command=='verify' and args.protocol_output is not None:
            raw=_encode(supplied['protocol_candidate'],MAX_PROTOCOL_BYTES)
            _write_new(args.protocol_output,raw)
            print(encoded.decode('utf-8'),end='')
        elif args.output is not None:_write_new(args.output,encoded)
        else:print(encoded.decode('utf-8'),end='')
    except (ValueError,OSError,KeyError,TypeError,UnicodeError,RecursionError) as error:
        parser.exit(1,'report study inventory review intake: '+quoted_display(str(error))+'\n')


if __name__=='__main__':main()
