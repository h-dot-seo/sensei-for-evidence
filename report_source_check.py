"""Opt-in detached local report-source byte observations; never review or retrieval."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

from artifact_review import (MAX_ARTIFACTS, MAX_FILE_BYTES, MAX_TOTAL_BYTES,
                             check_file, open_root, read_input, safe_relative,
                             secure_open_supported)
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow
from report_review_links import prepare_targets
from research_bundle import engine_hashes

BOUNDARY = (
    'Local byte consistency only against a supplied document digest and explicit manifest mapping. '
    'No source contents are returned, interpreted or transmitted. A match does not establish '
    'retrieval, reading, authorship, source authenticity, scientific validity or eligibility. '
    'Supplied retrieval is retained without inference or change. No canonical status, review, '
    'queue, evidence, bundle or protocol is changed. This detached local observation can be edited '
    'or forged and is not persistent proof or authentication. Use a dedicated, trusted, quiescent '
    'directory. This is not a security boundary against a privileged concurrent filesystem attacker.'
)
TEMPLATE_WARNING = (
    'Unfilled manifest scaffold only. Supply relative paths and exact byte counts yourself. '
    'Paths are never inferred from locators; no byte count or document digest is invented. '
    'A source with a null document_sha256 needs a supplied source declaration with a non-null '
    'document digest first, then a newly generated template. This tool does not write that declaration.'
)
SOURCE_FIRST = 'Supply a non-null document_sha256 in the source declaration first, then regenerate the template.'
MANIFEST_FIELDS = {'source_id', 'report_id', 'source_descriptor_sha256', 'path', 'bytes'}


class SourceCheckError(ValueError):
    """Location-free operational diagnostics that are safe to display verbatim."""


def _digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _prepare(protocol):
    # Canonical serialization and strict decoding reject invalid JSON values before
    # even implementation files are read. Keep returned observations detached.
    protocol = parse_json(canonical_json_bytes(protocol))
    research = run(protocol)
    if 'reports' in protocol:
        report_flow(protocol, include_csv=False)
    prepared = prepare_targets(protocol, research.get('bibliographic_collection'))
    sources = {row['source']['source_id']: row['source'] for row in prepared['source_ledger']}
    reports = {row['report_id']: row for row in prepared['report_targets']}
    return protocol, sources, reports


def _source_context(source, reports):
    target = reports[source['report_id']]
    return dict(source_id=source['source_id'], report_id=source['report_id'],
                supplied_source=copy.deepcopy(source),
                source_descriptor_sha256=_digest(source),
                current_source_basis_sha256=target['source_basis_sha256'],
                retrieval=target['retrieval'])


def _implementation_hashes():
    result = dict(engine_hashes())
    for name in ('report_source_check.py', 'artifact_review.py'):
        result[name] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
    return result


def _base(protocol, manifest, sources, selected, scope):
    return dict(schema_version=1, protocol_sha256=_digest(protocol), manifest_sha256=_digest(manifest),
                engine_sha256=_implementation_hashes(),
                hash_scope='Sorted compact UTF-8 supplied JSON; object key order ignored, list order retained; not authentication.',
                selection=dict(scope=scope, source_ids=list(selected), validation_scope='ENTIRE_PROTOCOL_AND_MANIFEST'),
                uninspected_source_ids=sorted(set(sources) - set(selected)),
                inspection_scope='Explicit manifest entries only; unlisted sources are not inspected.',
                source_authenticity='NOT_VERIFIED', authorship='NOT_ASSESSED',
                retrieval_assessment='NOT_PERFORMED', reading='NOT_ESTABLISHED',
                scientific_validity='NOT_ASSESSED', eligibility_correctness='NOT_ASSESSED',
                protocol_changed=False, external_calls=0,
                observation_kind='DETACHED_LOCAL_BYTE_OBSERVATION', boundary=BOUNDARY)


def template(protocol, source_id=None):
    """Return a detached blank manifest and supplied context; never inspect source bytes."""
    protocol, sources, reports = _prepare(protocol)
    if source_id is not None and (not isinstance(source_id, str) or source_id not in sources):
        raise ValueError('unknown report source_id selection')
    selected = list(sources) if source_id is None else [source_id]
    rows, contexts, guidance = [], [], []
    for sid in selected:
        source = sources[sid]
        contexts.append(_source_context(source, reports))
        if source['document_sha256'] is None:
            guidance.append(dict(source_id=sid, report_id=source['report_id'], guidance=SOURCE_FIRST))
        else:
            rows.append(dict(source_id=sid, report_id=source['report_id'],
                             source_descriptor_sha256=_digest(source), path=None, bytes=None))
    manifest = dict(schema_version=1, sources=rows)
    result = _base(protocol, manifest, sources, [], 'ALL_ENUMERATED_SOURCES' if source_id is None else 'EXACT_SOURCE_ID')
    result['selection'].update(source_ids=selected, validation_scope='ENTIRE_PROTOCOL')
    result.update(stage='AWAITING_EXPLICIT_LOCAL_MANIFEST', manifest=manifest, sources=contexts,
                  source_first_guidance=guidance, template_warning=TEMPLATE_WARNING,
                  document_bytes_verification='NOT_PERFORMED', all_requested_bytes_match=False)
    return result


def _validate_manifest(manifest, sources):
    if (not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'sources'}
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or not isinstance(manifest['sources'], list)):
        raise ValueError('source manifest requires exactly schema_version 1 and sources list')
    if len(manifest['sources']) > MAX_ARTIFACTS:
        raise ValueError('too many source manifest entries')
    rows, seen, paths, total = [], set(), set(), 0
    for entry in manifest['sources']:
        if not isinstance(entry, dict) or set(entry) != MANIFEST_FIELDS:
            raise ValueError('invalid source manifest entry fields')
        sid = entry['source_id']
        if not isinstance(sid, str) or sid not in sources or sid in seen:
            raise ValueError('manifest source_id must be known and unique')
        source = sources[sid]
        if not isinstance(entry['report_id'], str) or entry['report_id'] != source['report_id']:
            raise ValueError('manifest report_id must exactly match the supplied source')
        if (not isinstance(entry['source_descriptor_sha256'], str)
                or entry['source_descriptor_sha256'] != _digest(source)):
            raise ValueError('manifest source descriptor hash must match the entire current source declaration')
        if source['document_sha256'] is None:
            raise ValueError(SOURCE_FIRST)
        parts = safe_relative(entry['path'])
        if entry['path'].casefold() in paths:
            raise ValueError('duplicate source manifest path')
        if type(entry['bytes']) is not int or not 0 <= entry['bytes'] <= MAX_FILE_BYTES:
            raise ValueError('source size outside supported byte limit')
        total += entry['bytes']
        if total > MAX_TOTAL_BYTES:
            raise ValueError('source total exceeds byte limit')
        rows.append((entry, parts))
        seen.add(sid)
        paths.add(entry['path'].casefold())
    return rows


def check_sources(protocol, manifest, root):
    """Validate all metadata first, then inspect only explicitly mapped local bytes."""
    protocol, sources, reports = _prepare(protocol)
    manifest = parse_json(canonical_json_bytes(manifest))
    rows = _validate_manifest(manifest, sources)
    if not isinstance(root, (str, Path)) or not str(root):
        raise SourceCheckError('an explicit dedicated local source directory is required; no sources inspected')
    if not secure_open_supported():
        raise SourceCheckError('secure descriptor-relative no-follow file access unavailable; no sources inspected. Native Windows byte checks are unsupported')
    # Finish metadata serialization before touching any source directory or file.
    selected = [entry['source_id'] for entry, _ in rows]
    contexts = [_source_context(sources[sid], reports) for sid in selected]
    canonical_json_bytes(contexts)
    try:
        root_fd = open_root(root)
    except (OSError, ValueError, TypeError):
        raise ValueError('source root unreadable or unsafe; no sources inspected') from None
    results = []
    try:
        for (entry, parts), context in zip(rows, contexts):
            expectation = dict(bytes=entry['bytes'], sha256=sources[entry['source_id']]['document_sha256'])
            results.append(dict(context, manifest_mapping=copy.deepcopy(entry),
                                **check_file(root_fd, parts, expectation)))
    finally:
        os.close(root_fd)
    result = _base(protocol, manifest, sources, selected, 'EXPLICIT_MANIFEST_ENTRIES')
    result.update(stage='LOCAL_BYTE_OBSERVATION', sources=results,
                  document_bytes_verification='EXPLICIT_MANIFEST_ONLY',
                  all_requested_bytes_match=bool(results) and all(row['status'] == 'BYTES_MATCH' for row in results))
    return result


def render_text(result):
    """Render all metadata through control-safe quoting, including supplied labels."""
    lines = ['Local report-source byte observation']
    for key, value in result.items():
        lines.append(quoted_display(key) + ': ' + quoted_display(value))
    return '\n'.join(lines) + '\n'


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse errors can otherwise echo untrusted paths/control characters.
        self.exit(2, 'report source check argument error; use --help for usage\n')


def main():
    configure_utf8_stdio()
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('template', 'check'):
        child = commands.add_parser(command)
        child.add_argument('protocol', type=Path)
        if command == 'template':
            child.add_argument('--source-id')
        else:
            child.add_argument('manifest', type=Path)
            child.add_argument('--root', type=Path, required=True,
                               help='explicit dedicated local source directory; never inferred from a locator')
        child.add_argument('--output', type=Path, help='write JSON to a new file only')
        child.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        protocol = read_input(args.protocol)
        result = (template(protocol, args.source_id) if args.command == 'template' else
                  check_sources(protocol, read_input(args.manifest), args.root))
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        rendered = render_text(result) if args.text else encoded
        # Do not leave output files behind for an unserializable result.
        encoded.encode('utf-8')
        rendered.encode('utf-8')
        if args.output is not None:
            with args.output.open('x', encoding='utf-8', newline='\n') as output:
                output.write(encoded)
    except SourceCheckError as error:
        parser.exit(1, 'report source check error: ' + quoted_display(str(error)) + '\n')
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError,
            RecursionError, OverflowError):
        # Generic input/output diagnostics never repeat a filesystem exception,
        # document contents, source locator, absolute root or malicious CLI value.
        parser.exit(1, 'report source check error: ' + quoted_display(
            'Invalid input metadata, unsupported secure access, or unreadable/unsafe input, root or new output. '
            'Check source declarations, manifest fields and dedicated directory; null digests require source-first declarations.') + '\n')
    print(rendered, end='')
    if args.command == 'check' and not result['all_requested_bytes_match']:
        parser.exit(1)


if __name__ == '__main__':
    main()
