"""Append supplied full-text report positions through separate exact-target import review and replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from challenge_intake import _date, _normalized, _schema, REVIEW_FIELDS
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from research_bundle import engine_hashes
from screening_decision_batch_apply import _read, _encode, _write_new
import report_review
import report_review_links

MAX_PROTOCOL_BYTES = 50_000_000
MAX_CANDIDATE_BYTES = 10_000_000
MAX_APPLICATION_BYTES = 50_000_000
MAX_POSITIONS = 100
BOUNDARY = (
    'Append-only supplied full-text reviewer positions, not canonical report decisions. Use the existing '
    'report_review template and actual human assertions; no opinion, identity, date, rationale or reviewed '
    'coverage is generated, copied from old reviews or inferred. New rows require supplied retrieved '
    'reports, at least one source descriptor and the exact current source basis. Null document digests '
    'remain DOCUMENT_BYTES_UNBOUND; all non-null digests are supplied and unverified. No locator is '
    'opened or converted to a digest. Existing stale assertions remain stale and unchanged. Duplicate '
    'review IDs or report/reviewer pairs fail; reviewer supersession is not implemented. Separate import '
    'review authorizes recording only, not scientific endorsement. Original reports, sources, evidence, '
    'counts, memberships and every old assertion remain unchanged. Exact replay binds original protocol, '
    'supplied candidate rows, import review and implementation; unsigned hashes do not authenticate '
    'people, chronology or reading. Detached import receipt IDs are labels, not a global registry. '
    'Keep real sources, assertions and applications outside this public repository. No vote, consensus, '
    'adjudication, source retrieval, model or network call; conclusion readiness NOT_READY.'
)
NEGATIVE_CLAIMS = dict(original_protocol_changed=False, canonical_reports_changed=False,
    source_declarations_changed=False, document_bytes_verification='NOT_PERFORMED',
    source_authenticity='NOT_VERIFIED', reviewer_identity='NOT_ESTABLISHED', reading='NOT_ESTABLISHED',
    adjudication='NOT_PERFORMED', conclusion_readiness='NOT_READY', external_calls=0)


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _hashes():
    root = Path(__file__).resolve().parent
    names = ('report_review_intake.py','report_review.py','report_review_links.py',
             'challenge_intake.py','nbib_intake.py','screening_decision_batch_apply.py')
    return dict(engine_hashes(), **{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names})


def _prepare(protocol, document):
    protocol = _normalized(protocol, MAX_PROTOCOL_BYTES, 'original protocol')
    document = _normalized(document, MAX_CANDIDATE_BYTES, 'candidate positions')
    _schema(document, {'schema_version','report_reviews'}, 'candidate positions')
    rows = document['report_reviews']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_POSITIONS:
        raise ValueError('candidate positions must contain 1 to 100 rows')
    before = report_review.review(protocol)
    known = {row['report_id']:row for row in before['report_targets']}
    selected = []
    selected_bytes = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != report_review_links.REVIEW_FIELDS:
            raise ValueError('candidate review has unknown or missing fields')
        if any(not isinstance(row[key],str) or not row[key].strip() for key in report_review_links.REVIEW_FIELDS):
            raise ValueError('candidate review fields must be supplied nonblank literal strings')
        target = known.get(row['report_id'])
        if target is None:
            raise ValueError('unknown candidate report_id')
        if target['retrieval'] != 'retrieved' or target['source_binding_state'] == 'SOURCE_NOT_SUPPLIED':
            raise ValueError('new positions require a retrieved report with supplied source descriptors')
        if row['source_basis_sha256'] != target['source_basis_sha256']:
            raise ValueError('stale source_basis_sha256; re-examine context, never refresh automatically')
        selected_bytes += len(canonical_json_bytes(target))
        if selected_bytes > MAX_APPLICATION_BYTES:
            raise ValueError('selected source snapshots exceed target byte budget')
        selected.append(copy.deepcopy(target))
    candidate = copy.deepcopy(protocol)
    candidate.setdefault('report_reviews', []).extend(copy.deepcopy(rows))
    candidate = _normalized(candidate, MAX_PROTOCOL_BYTES, 'candidate protocol')
    # Reuse the complete existing validator for dates, choices and old/new duplicate IDs/pairs.
    after = report_review.review(candidate)
    prefix = len(protocol.get('report_reviews', []))
    restored = copy.deepcopy(candidate)
    if 'report_reviews' in protocol:
        restored['report_reviews'] = restored['report_reviews'][:prefix]
    else:
        restored.pop('report_reviews')
    if canonical_json_bytes(restored) != canonical_json_bytes(protocol):
        raise ValueError('intake changed original fields or old review prefix')
    target = dict(schema_version=1, target_type='report_review_positions_intake',
        input_protocol_sha256=digest(protocol), candidate_document_sha256=digest(document),
        candidate_document=document, selected_report_targets=selected,
        appended_positions=[dict(candidate_index=i, output_pointer=f'/report_reviews/{prefix+i}',review=copy.deepcopy(row))
                            for i,row in enumerate(rows)],
        before_review_cues=before['report_review_ledger'], after_review_cues=after['report_review_ledger'],
        protocol_candidate_sha256=digest(candidate), engine_sha256=_hashes(),
        **NEGATIVE_CLAIMS, boundary=BOUNDARY)
    target['target_sha256'] = digest(target)
    return _normalized(target, MAX_APPLICATION_BYTES, 'target'), candidate


def prepare(protocol, document):
    target, _ = _prepare(protocol, document)
    review = {key:None for key in sorted(REVIEW_FIELDS)}
    review.update(schema_version=1,target_sha256=target['target_sha256'],decision='import_report_reviews')
    return _normalized(dict(schema_version=1,status='AWAITING_SUPPLIED_IMPORT_REVIEW',target=target,
        review_document=review, **NEGATIVE_CLAIMS,boundary=BOUNDARY),MAX_APPLICATION_BYTES,'prepared target')


def assemble(protocol, document, review_document):
    review = _normalized(review_document, MAX_CANDIDATE_BYTES, 'import review')
    _schema(review, REVIEW_FIELDS, 'import review')
    if any(not isinstance(review[key],str) or not review[key].strip() for key in REVIEW_FIELDS-{'schema_version'}):
        raise ValueError('import-review fields must be nonblank supplied strings')
    if review['decision'] != 'import_report_reviews':
        raise ValueError('import review decision must be import_report_reviews')
    _date(review['reviewed_at'],'import reviewed_at')
    target, candidate = _prepare(protocol, document)
    if review['target_sha256'] != target['target_sha256']:
        raise ValueError('review does not match exact original, positions and implementation; no automatic rebase')
    receipt = dict(schema_version=1,receipt_id=review['receipt_id'],assertion=review,target=target,
        candidate_document=target['candidate_document'],input_protocol_sha256=target['input_protocol_sha256'],
        protocol_candidate_sha256=digest(candidate),engine_sha256=target['engine_sha256'],
        **NEGATIVE_CLAIMS,boundary=BOUNDARY)
    receipt['receipt_sha256'] = digest(receipt)
    return _normalized(dict(schema_version=1,kind='detached_report_review_positions_intake',
        receipt=receipt,protocol_candidate=candidate),MAX_APPLICATION_BYTES,'application')


def verify(protocol, application):
    record = _normalized(application,MAX_APPLICATION_BYTES,'application')
    _schema(record,{'schema_version','kind','receipt','protocol_candidate'},'application')
    if (record['kind'] != 'detached_report_review_positions_intake' or not isinstance(record['receipt'],dict)
            or not {'candidate_document','assertion'} <= set(record['receipt'])):
        raise ValueError('invalid report-review application')
    replay = assemble(protocol,record['receipt']['candidate_document'],record['receipt']['assertion'])
    if canonical_json_bytes(replay) != canonical_json_bytes(record):
        raise ValueError('application differs from exact original-input replay')
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
        parser.exit(1,'report review intake: '+quoted_display(str(error))+'\n')


if __name__=='__main__':main()
