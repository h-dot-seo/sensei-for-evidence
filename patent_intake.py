"""Record supplied patent rows after a separate exact-input import review."""
import argparse
import copy
import errno
import json
from pathlib import Path

from json_io import canonical_json_bytes, configure_utf8_stdio
import patent_links as links

_NO_QUESTION = object()

REVIEW_FIELDS = {'schema_version', 'target_sha256', 'decision', 'reviewer', 'reviewed_at', 'rationale'}


def template(value, supplied_question=_NO_QUESTION):
    value, _ = links.protocol(value)
    if supplied_question is not _NO_QUESTION:
        supplied_question = links.normalize(supplied_question, links.MAX_CANDIDATE_BYTES)
        links.question(supplied_question)
        if 'patent_question' in value and supplied_question != value['patent_question']:
            raise ValueError('append does not amend existing question')
    else:
        supplied_question = value.get('patent_question')
    return dict(schema_version=1, kind='patent_intake_template',
        draft=dict(schema_version=1, patent_question=copy.deepcopy(supplied_question),
                   **{name: [] for name in links.LEDGERS}),
        question_template={field: None for field in sorted(links.QUESTION_FIELDS)},
        row_templates={name: {field: None for field in sorted(fields)} for name, (_, fields) in links.LEDGERS.items()},
        current_basis_sha256=links.basis(value, supplied_question) if supplied_question is not None else None,
        review_template={field: 1 if field == 'schema_version' else None for field in sorted(REVIEW_FIELDS)},
        boundary='Drafts and review templates are incomplete; supply all assertions explicitly. ' + links.BOUNDARY,
        **links.NEGATIVE)


def _prepare(value, candidates):
    value, _ = links.protocol(value)
    candidates = links.normalize(candidates, links.MAX_CANDIDATE_BYTES)
    links.obj(candidates, {'schema_version', *links.FIELDS})
    if type(candidates['schema_version']) is not int or candidates['schema_version'] != 1:
        raise ValueError('schema version')
    links.question(candidates['patent_question'])
    if 'patent_question' in value and candidates['patent_question'] != value['patent_question']:
        raise ValueError('append does not amend existing question')
    current = links.basis(value, candidates['patent_question'])
    merged = copy.deepcopy(value)
    merged['patent_question'] = copy.deepcopy(candidates['patent_question'])
    count = 0
    for name, (_, fields) in links.LEDGERS.items():
        if not isinstance(candidates[name], list):
            raise ValueError('candidate list required')
        count += len(candidates[name])
        for row in candidates[name]:
            links.obj(row, fields)
            if row['basis_sha256'] != current:
                raise ValueError('new row requires current supplied basis')
        merged[name] = copy.deepcopy(value.get(name, [])) + copy.deepcopy(candidates[name])
    if not 1 <= count <= links.MAX_CANDIDATE_ROWS:
        raise ValueError('candidate batch requires 1 to 100 rows')
    links.protocol(merged)
    return value, candidates, merged, current


def target(value, candidates):
    value, candidates, merged, current = _prepare(value, candidates)
    receipt = dict(input_protocol_sha256=links.digest(value), candidate_document_sha256=links.digest(candidates),
                   protocol_candidate_sha256=links.digest(merged), basis_sha256=current,
                   implementation_sha256=links.implementation_hashes())
    return dict(schema_version=1, kind='patent_intake_target', target_sha256=links.digest(receipt),
        receipt=receipt, review_template=dict(schema_version=1, target_sha256=links.digest(receipt),
            decision=None, reviewer=None, reviewed_at=None, rationale=None),
        boundary='Separate supplied review covers recording this exact batch only, not legal or scientific endorsement. ' + links.BOUNDARY,
        **links.NEGATIVE)


def assemble(value, candidates, assertion):
    value, candidates, merged, _ = _prepare(value, candidates)
    current = target(value, candidates)
    assertion = links.normalize(assertion, links.MAX_CANDIDATE_BYTES)
    links.obj(assertion, REVIEW_FIELDS)
    if type(assertion['schema_version']) is not int or assertion['schema_version'] != 1:
        raise ValueError('review schema')
    if assertion['target_sha256'] != current['target_sha256']:
        raise ValueError('stale review target')
    if assertion['decision'] != 'accept':
        raise ValueError('only supplied acceptance records this batch')
    for key in ('reviewer', 'rationale'):
        links.text(assertion[key])
    links.date(assertion['reviewed_at'])
    result = dict(schema_version=1, kind='detached_patent_intake',
        target=copy.deepcopy(current), candidate_document=copy.deepcopy(candidates),
        assertion=copy.deepcopy(assertion), protocol_candidate=merged,
        boundary='Append-only candidate; original input unchanged. Retain original, candidate document and detached application for replay. ' + links.BOUNDARY,
        **links.NEGATIVE)
    return links.normalize(result, links.MAX_OUTPUT_BYTES)


def verify(original, application):
    application = links.normalize(application, links.MAX_OUTPUT_BYTES)
    if not isinstance(application, dict) or not {'candidate_document', 'assertion'} <= set(application):
        raise ValueError('application required')
    expected = assemble(original, application['candidate_document'], application['assertion'])
    valid = canonical_json_bytes(expected) == canonical_json_bytes(application)
    return dict(schema_version=1, kind='patent_intake_replay_check', valid=valid,
        verification='EXACT_CURRENT_IMPLEMENTATION_REPLAY' if valid else 'REPLAY_MISMATCH',
        expected_application_sha256=links.digest(expected), recorded_application_sha256=links.digest(application),
        boundary='Current implementation and original input replay only; consistently reauthored assertions can replay. ' + links.BOUNDARY,
        **links.NEGATIVE)


def encode(result):
    encoded = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(encoded) > links.MAX_OUTPUT_BYTES:
        raise ValueError('output byte limit')
    return encoded


def write_new(path, encoded):
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(errno.EEXIST, 'existing output entry')
    with path.open('xb') as stream:
        stream.write(encoded)


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('template', 'target', 'assemble', 'verify'):
        sub = commands.add_parser(name)
        sub.add_argument('protocol', type=Path)
        if name == 'template':
            sub.add_argument('--question', type=Path)
        if name in ('target', 'assemble'):
            sub.add_argument('candidates', type=Path)
        if name == 'assemble':
            sub.add_argument('review', type=Path)
        if name == 'verify':
            sub.add_argument('application', type=Path)
        else:
            sub.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        value = links.read(args.protocol, links.MAX_PROTOCOL_BYTES)
        if args.command == 'template':
            result = template(value, links.read(args.question, links.MAX_CANDIDATE_BYTES)) if args.question is not None else template(value)
        elif args.command == 'verify':
            result = verify(value, links.read(args.application, links.MAX_OUTPUT_BYTES))
        else:
            candidates = links.read(args.candidates, links.MAX_CANDIDATE_BYTES)
            result = target(value, candidates) if args.command == 'target' else assemble(value, candidates, links.read(args.review, links.MAX_CANDIDATE_BYTES))
        encoded = encode(result)
        if getattr(args, 'output', None) is not None:
            write_new(args.output, encoded)
        print(encoded.decode('utf-8'), end='')
        return int(args.command == 'verify' and not result['valid'])
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError, OverflowError):
        parser.exit(1, 'patent intake error: invalid, oversized or unreadable input, or unavailable new output; details withheld\n')


if __name__ == '__main__':
    raise SystemExit(main())
