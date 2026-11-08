"""Read-only local UTF-8 passage location/transcription observations for manual results."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePath
import stat

from artifact_review import open_root, read_input, safe_relative, secure_open_supported
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
import result_intake

MAX_SOURCE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 5_000_000
MAX_SOURCES = 20
MAX_PASSAGES = 200
MAX_QUOTE_BYTES = 32_768
MAX_MANIFEST_BYTES = 10_000_000
MAX_OUTPUT_BYTES = 50_000_000
MAX_CATALOG_LINES_PER_SOURCE = 5_000
MAX_CATALOG_LINES_TOTAL = 20_000
EVIDENCE_FIELDS = ('model', 'intervention', 'comparator', 'endpoint', 'result',
                   'limitations', 'mechanism_basis')
MANIFEST_FIELDS = {'schema_version', 'protocol_sha256', 'candidate_document_sha256',
                   'sources', 'passages'}
SOURCE_FIELDS = {'source_id', 'report_id', 'source_descriptor_sha256', 'path', 'bytes'}
PASSAGE_FIELDS = {'passage_id', 'candidate_index', 'evidence_field', 'source_id',
                  'byte_start', 'byte_end', 'quote'}
PROTECTED_COMPONENTS = {'.git', '.aws', '.codex', '.agents'}
BOUNDARY = (
    'Mechanical local byte-location and exact transcription observations only. Human-supplied '
    'field/passage associations do not establish that the passage supports, entails or explains '
    'the field value. No semantic extraction, scientific inference, causality, source authenticity, '
    'review, reading, eligibility, extraction completeness or scientific acceptance is established. '
    'Protocol, candidates, source declarations and separate blank intake review remain unchanged. '
    'Only explicitly mapped local paths are opened; URLs and locators are inert. Check returns '
    'selected quotes only; catalog explicitly returns verified UTF-8 source text. This editable '
    'unsigned detached observation is not authentication or durable proof. Retain original inputs, '
    'source files and recorded implementation and rerun this checker for reproducibility. Use a '
    'dedicated, trusted, quiescent root. This is not a security boundary against a privileged '
    'concurrent filesystem attacker. Native Windows secure source access is unsupported and '
    'fails closed before opening the root or source files.'
)
TEMPLATE_WARNING = (
    'No sources or passages are selected automatically. Copy a source shape, explicitly choose '
    'a candidate-selected source with a non-null declared document_sha256, and supply its path '
    'and exact byte count. Catalog only explicitly mapped sources, then supply passage offsets '
    'and exact quotes yourself. Byte offsets are zero-based half-open UTF-8 byte ranges, not '
    'character positions. No digest, offset, quote, date, reviewer or scientific judgment is inferred.'
)


class PassageCheckError(ValueError):
    """Operational diagnostics without local exception text or absolute paths."""


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _normalize(value, cap, label):
    pending, active, visited = [(value, False)], set(), set()
    while pending:
        item, leaving = pending.pop()
        if leaving:
            active.remove(id(item)); continue
        if type(item) in (dict, list):
            identity = id(item)
            if identity in active:
                raise ValueError(label + ' must not contain circular JSON containers')
            if identity in visited:
                continue
            visited.add(identity); active.add(identity)
            pending.append((item, True))
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError(label + ' requires literal JSON string keys')
                pending.extend((child, False) for child in item.values())
            else:
                pending.extend((child, False) for child in item)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError(label + ' requires literal JSON types without normalization')
    raw = canonical_json_bytes(value)
    if len(raw) > cap:
        raise ValueError(label + ' exceeds byte limit')
    return parse_json(raw)


def _prepare(protocol, candidates):
    # The entire original protocol and completed candidate document are validated,
    # even if only a narrow subset will be inspected. Never assemble/import.
    protocol = _normalize(protocol, result_intake.MAX_PROTOCOL_BYTES, 'protocol')
    candidates = _normalize(candidates, result_intake.MAX_CANDIDATE_BYTES, 'candidate document')
    prepared = result_intake.prepare(protocol, candidates)
    sources = {}
    for selected in prepared['target']['selected_sources']:
        source = selected['source']
        sources[source['source_id']] = source
    return protocol, candidates, prepared, sources


def _hashes(prepared):
    result = dict(prepared['engine_sha256'])
    for name in ('result_passage_check.py', 'artifact_review.py'):
        result[name] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
    return result


def _base(protocol, candidates, prepared):
    return dict(schema_version=1, protocol_sha256=digest(protocol),
                candidate_document_sha256=digest(candidates),
                manual_intake_target_sha256=prepared['target']['target_sha256'],
                engine_sha256=_hashes(prepared),
                hash_scope='Sorted compact UTF-8 JSON; object key order ignored, list order and literal values retained; not authentication.',
                limits=dict(source_bytes=MAX_SOURCE_BYTES, total_source_bytes=MAX_TOTAL_BYTES,
                            sources=MAX_SOURCES, passages=MAX_PASSAGES, quote_utf8_bytes=MAX_QUOTE_BYTES,
                            manifest_bytes=MAX_MANIFEST_BYTES, output_bytes=MAX_OUTPUT_BYTES,
                            catalog_lines_per_source=MAX_CATALOG_LINES_PER_SOURCE,
                            catalog_lines_total=MAX_CATALOG_LINES_TOTAL),
                observation_kind='DETACHED_LOCAL_PASSAGE_OBSERVATION',
                source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED',
                scientific_acceptance='NOT_ASSESSED', field_meaning_assessment='NOT_PERFORMED',
                extraction_completeness='NOT_ESTABLISHED', protocol_changed=False,
                candidate_document_changed=False, external_calls=0, boundary=BOUNDARY)


def _available(candidates, prepared, sources):
    rows = []
    for index, candidate in enumerate(candidates['candidates']):
        rows.append(dict(candidate_index=index, report_id=candidate['report_id'],
                         evidence_id=candidate['evidence']['evidence_id'],
                         evidence_fields={key: candidate['evidence'][key] for key in EVIDENCE_FIELDS},
                         source_references=copy.deepcopy(candidate['source_references'])))
    available_sources = [dict(source_id=sid, report_id=source['report_id'],
                              source_descriptor_sha256=digest(source),
                              supplied_source=copy.deepcopy(source),
                              selectable=source['document_sha256'] is not None)
                         for sid, source in sources.items()]
    return dict(available_candidates=rows, available_sources=available_sources)


def _encoding_size(value, cap):
    # Count before joining: repeated large supplied fields must not first build
    # a many-hundred-MB JSON string merely to discover it exceeds the cap.
    size = 1  # final LF
    encoder = json.JSONEncoder(ensure_ascii=False, indent=2, allow_nan=False)
    for chunk in encoder.iterencode(value):
        size += len(chunk.encode('utf-8'))
        if size > cap:
            raise ValueError('passage observation exceeds output byte limit')
    return size


def _finish(result):
    _encoding_size(result, MAX_OUTPUT_BYTES)
    return result


def template(protocol, candidates):
    """Return available supplied context and separate blank shapes; read no source."""
    protocol, candidates, prepared, sources = _prepare(protocol, candidates)
    result = _base(protocol, candidates, prepared)
    manifest = dict(schema_version=1, protocol_sha256=result['protocol_sha256'],
                    candidate_document_sha256=result['candidate_document_sha256'], sources=[], passages=[])
    result.update(stage='AWAITING_EXPLICIT_PASSAGE_MANIFEST', manifest=manifest,
                  blank_source={key: None for key in sorted(SOURCE_FIELDS)},
                  blank_passage={key: None for key in sorted(PASSAGE_FIELDS)},
                  template_warning=TEMPLATE_WARNING,
                  **_available(candidates, prepared, sources))
    return _finish(result)


def _relative(value):
    parts = safe_relative(value)
    if any(part.casefold() in PROTECTED_COMPONENTS for part in parts):
        raise ValueError('protected metadata paths are not supported')
    return parts


def _validate_manifest(manifest, protocol, candidates, sources, require_passages):
    if (not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1):
        raise ValueError('passage manifest has unknown or missing fields or schema version')
    for key, value in (('protocol_sha256', protocol), ('candidate_document_sha256', candidates)):
        if not isinstance(manifest[key], str) or manifest[key] != digest(value):
            raise ValueError('manifest input hash does not match exact supplied input')
    if not isinstance(manifest['sources'], list) or not 1 <= len(manifest['sources']) <= MAX_SOURCES:
        raise ValueError('sources must be a nonempty bounded list')
    if (not isinstance(manifest['passages'], list) or len(manifest['passages']) > MAX_PASSAGES
            or (require_passages and not manifest['passages'])):
        raise ValueError('check requires a nonempty bounded passage list; catalog permits empty passages')
    mappings, paths, total = {}, set(), 0
    for entry in manifest['sources']:
        if not isinstance(entry, dict) or set(entry) != SOURCE_FIELDS:
            raise ValueError('source mapping has unknown or missing fields')
        sid = entry['source_id']
        if not isinstance(sid, str) or sid not in sources or sid in mappings:
            raise ValueError('source_id must be candidate-selected, known and unique')
        source = sources[sid]
        if not isinstance(entry['report_id'], str) or entry['report_id'] != source['report_id']:
            raise ValueError('source report_id must match its entire supplied descriptor')
        if (not isinstance(entry['source_descriptor_sha256'], str)
                or entry['source_descriptor_sha256'] != digest(source)):
            raise ValueError('source descriptor hash must match its entire supplied declaration')
        if source['document_sha256'] is None:
            raise ValueError('source requires a non-null declared document_sha256; no digest is supplied by this tool')
        parts = _relative(entry['path'])
        if entry['path'].casefold() in paths:
            raise ValueError('source paths must be unique, including casefolded aliases')
        if type(entry['bytes']) is not int or not 0 <= entry['bytes'] <= MAX_SOURCE_BYTES:
            raise ValueError('source bytes must be a bounded nonnegative integer')
        total += entry['bytes']
        if total > MAX_TOTAL_BYTES:
            raise ValueError('total declared source bytes exceeds limit')
        mappings[sid] = (entry, parts)
        paths.add(entry['path'].casefold())
    passage_ids, anchors, used = set(), set(), set()
    for passage in manifest['passages']:
        if not isinstance(passage, dict) or set(passage) != PASSAGE_FIELDS:
            raise ValueError('passage has unknown or missing fields')
        pid = passage['passage_id']
        if not isinstance(pid, str) or not pid.strip() or pid in passage_ids:
            raise ValueError('passage_id must be a nonblank unique literal string')
        index = passage['candidate_index']
        if type(index) is not int or not 0 <= index < len(candidates['candidates']):
            raise ValueError('candidate_index must be a valid zero-based integer')
        field = passage['evidence_field']
        if not isinstance(field, str) or field not in EVIDENCE_FIELDS:
            raise ValueError('passage evidence_field must be one of the seven supported fields')
        sid = passage['source_id']
        if not isinstance(sid, str) or sid not in mappings:
            raise ValueError('passage source must be explicitly mapped')
        candidate = candidates['candidates'][index]
        if (sid not in {ref['source_id'] for ref in candidate['source_references']}
                or sources[sid]['report_id'] != candidate['report_id']):
            raise ValueError('passage source must be selected by this candidate for the same report')
        start, end = passage['byte_start'], passage['byte_end']
        if (type(start) is not int or type(end) is not int
                or not 0 <= start < end <= mappings[sid][0]['bytes']
                or end - start > MAX_QUOTE_BYTES):
            raise ValueError('passage range must be nonempty, bounded, zero-based half-open bytes')
        quote = passage['quote']
        if not isinstance(quote, str) or not quote or len(quote.encode('utf-8')) > MAX_QUOTE_BYTES:
            raise ValueError('passage quote must be nonempty bounded literal UTF-8 text')
        anchor = (index, field, sid, start, end)
        if anchor in anchors:
            raise ValueError('duplicate candidate/field/source/byte-range anchor')
        passage_ids.add(pid); anchors.add(anchor); used.add(sid)
    if require_passages and used != set(mappings):
        raise ValueError('check source mappings must each be used by a supplied passage')
    return list(mappings.values())


def _validate_root(root):
    if not isinstance(root, (str, Path)) or not str(root):
        raise PassageCheckError('an explicit dedicated source root is required; no source inspected')
    # CLI keeps the raw string spelling so aliases are rejected before Path can
    # collapse them. API Path objects have already lost that spelling. PurePath
    # is only for component checks, never resolve/follow/expand a supplied path.
    raw = str(root)
    if ('\\' in raw or '\x00' in raw or any(ord(c) < 32 or ord(c) == 127 for c in raw)
            or '..' in PurePath(raw).parts
            or any(p.casefold() in PROTECTED_COMPONENTS for p in PurePath(raw).parts)
            or raw in ('.', '/', '//') or '//' in raw or '/./' in raw or raw.startswith('./')
            or raw.endswith('/.')):
        raise PassageCheckError('source root is unsafe or aliases a protected/root location; no source inspected')
    if not secure_open_supported():
        raise PassageCheckError('secure no-follow descriptor-relative source access unavailable; native Windows unsupported; no source inspected')


def _signature(metadata):
    return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns,
            metadata.st_ctime_ns, metadata.st_nlink)


def _read_source(root_fd, parts, expected):
    """One descriptor-bound bounded read supplies both digest and passage bytes.

    Narrow counterpart of artifact_review.check_file; do not replace this with a
    hash followed by a pathname reopen. Failed observations never return content.
    """
    directory = os.dup(root_fd)
    fd = None
    def observation(status, count=None, sha=None):
        return dict(status=status, observed_bytes=count, observed_sha256=sha), None
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = nxt
        listed = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(listed.st_mode) or listed.st_nlink != 1:
            return observation('REJECTED_FILE_TYPE')
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or (listed.st_dev, listed.st_ino) != (before.st_dev, before.st_ino)):
            return observation('REJECTED_FILE_TYPE')
        if before.st_size > MAX_SOURCE_BYTES or before.st_size != expected['bytes']:
            return observation('SIZE_MISMATCH', before.st_size)
        chunks, count = [], 0
        while True:
            chunk = os.read(fd, min(65536, expected['bytes'] - count + 1))
            if not chunk:
                break
            count += len(chunk)
            if count > expected['bytes']:
                return observation('CHANGED_DURING_READ', count)
            chunks.append(chunk)
        after = os.fstat(fd)
        if count != expected['bytes'] or _signature(before) != _signature(after):
            return observation('CHANGED_DURING_READ', count)
        body = b''.join(chunks)
        sha = hashlib.sha256(body).hexdigest()
        if sha != expected['sha256']:
            return observation('HASH_MISMATCH', count, sha)
        return dict(status='BYTES_MATCH', observed_bytes=count, observed_sha256=sha), body
    except FileNotFoundError:
        return observation('MISSING')
    except OSError:
        return observation('UNREADABLE_OR_UNSAFE_PATH')
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory)


def _decode(body):
    try:
        text = body.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        return 'INVALID_UTF8', None
    if any((ord(c) < 32 and c not in '\t\r\n') or ord(c) == 127 for c in text):
        return 'UNSUPPORTED_BINARY_OR_CONTROL_TEXT', None
    return 'UTF8_TEXT', text


def _line_count(body):
    return (body.count(b'\n') + body.count(b'\r') - body.count(b'\r\n')
            + (1 if body and body[-1] not in (10, 13) else 0))


def _physical_lines(body):
    # Physical lines are LF/CRLF/CR only, not Unicode splitlines separators.
    # Keep terminators and a UTF-8 BOM in text and byte counts without decoding
    # with utf-8-sig or normalizing newlines.
    if _line_count(body) > MAX_CATALOG_LINES_PER_SOURCE:
        raise PassageCheckError('catalog physical line count exceeds per-source limit; no partial catalog returned')
    lines, start, index = [], 0, 0
    while index < len(body):
        if body[index] in (10, 13):
            end = index + (2 if body[index:index + 2] == b'\r\n' else 1)
            lines.append(dict(line_number=len(lines) + 1, byte_start=start, byte_end=end,
                              text=body[start:end].decode('utf-8')))
            start = end; index = end
        else:
            index += 1
    if start < len(body):
        lines.append(dict(line_number=len(lines) + 1, byte_start=start, byte_end=len(body),
                          text=body[start:].decode('utf-8')))
    return lines


def _passage_observation(passage, candidates, source_result, body):
    candidate = candidates['candidates'][passage['candidate_index']]
    result = {key: copy.deepcopy(value) for key, value in passage.items() if key != 'quote'}
    result.update(report_id=candidate['report_id'], evidence_id=candidate['evidence']['evidence_id'],
                  field_value=candidate['evidence'][passage['evidence_field']],
                  expected_quote=passage['quote'], observed_quote=None,
                  path=source_result['manifest_mapping']['path'],
                  source_descriptor_sha256=source_result['source_descriptor_sha256'],
                  declared_source_sha256=source_result['supplied_source']['document_sha256'],
                  observed_source_sha256=source_result['observed_sha256'],
                  field_meaning_assessment='NOT_PERFORMED')
    if source_result['status'] != 'BYTES_MATCH':
        result['status'] = 'SOURCE_BYTES_NOT_MATCHED'
    elif source_result['text_status'] != 'UTF8_TEXT':
        result['status'] = 'SOURCE_' + source_result['text_status']
    else:
        try:
            # Decoding the slice alone checks BOTH codepoint boundaries. The
            # whole source was already strictly decoded before any quote check.
            observed = body[passage['byte_start']:passage['byte_end']].decode('utf-8')
        except UnicodeDecodeError:
            result['status'] = 'INVALID_UTF8_BOUNDARY'
        else:
            result.update(observed_quote=observed,
                          status='TEXT_MATCH' if observed == passage['quote'] else 'QUOTE_MISMATCH')
    return result


def _inspect(protocol, candidates, manifest, root, *, catalog_mode):
    protocol, candidates, prepared, sources = _prepare(protocol, candidates)
    manifest = _normalize(manifest, MAX_MANIFEST_BYTES, 'manifest')
    rows = _validate_manifest(manifest, protocol, candidates, sources, not catalog_mode)
    # Serialize all declared context and ALL passages before opening root/source.
    result = _base(protocol, candidates, prepared)
    result.update(manifest_sha256=digest(manifest),
                  stage='LOCAL_SOURCE_CATALOG' if catalog_mode else 'LOCAL_PASSAGE_OBSERVATION',
                  selection=dict(source_ids=[entry['source_id'] for entry, _ in rows],
                                 validation_scope='ENTIRE_PROTOCOL_CANDIDATES_AND_MANIFEST'),
                  inspection_scope='Explicit manifest paths only; other references are not inspected.')
    inspected = {entry['source_id'] for entry, _ in rows}
    anchored = {(p['candidate_index'], p['evidence_field']) for p in manifest['passages']}
    result.update(uninspected_source_references=[dict(candidate_index=i, report_id=c['report_id'],
                                                     source_id=r['source_id'])
        for i, c in enumerate(candidates['candidates']) for r in c['source_references']
        if r['source_id'] not in inspected],
        unanchored_fields=[dict(candidate_index=i, evidence_field=field)
            for i in range(len(candidates['candidates'])) for field in EVIDENCE_FIELDS
            if (i, field) not in anchored],
        association_scope='Supplied labels/ranges only; unanchored does not mean unextracted, and matched does not mean supported.')
    # Preflight duplicated metadata and conservative text expansion BEFORE any
    # source read. Each selected span is independently bounded. The reserve also
    # covers observed quotes' JSON escaping and line/catalog record overhead.
    source_preview = {}
    for entry, _ in rows:
        sid = entry['source_id']
        source_preview[sid] = dict(source_id=sid, report_id=sources[sid]['report_id'],
            source_descriptor_sha256=digest(sources[sid]), supplied_source=copy.deepcopy(sources[sid]),
            manifest_mapping=copy.deepcopy(entry), status='BYTES_MATCH', text_status='UTF8_TEXT',
            observed_bytes=entry['bytes'], observed_sha256=sources[sid]['document_sha256'])
    preview = dict(result, sources=list(source_preview.values()),
        passages=[_passage_observation(p, candidates, dict(source_preview[p['source_id']],
                    status='PREFLIGHT_ONLY'), None) for p in manifest['passages']])
    quote_reserve = sum(6 * (p['byte_end'] - p['byte_start']) + 1024 for p in manifest['passages'])
    catalog_reserve = (6 * sum(entry['bytes'] for entry, _ in rows) + 256 * MAX_CATALOG_LINES_TOTAL
                       if catalog_mode else 0)
    # All potentially large supplied aggregate labels are already in result.
    metadata_reserve = 4096  # fixed aggregate flags and final status labels
    _encoding_size(preview, MAX_OUTPUT_BYTES - quote_reserve - catalog_reserve - metadata_reserve)
    _validate_root(root)
    try:
        root_fd = open_root(root)
    except (OSError, ValueError, TypeError):
        raise PassageCheckError('source root unreadable or unsafe; no source inspected') from None
    observations, bodies = {}, {}
    try:
        for entry, parts in rows:
            sid = entry['source_id']; source = sources[sid]
            observed, body = _read_source(root_fd, parts,
                                          dict(bytes=entry['bytes'], sha256=source['document_sha256']))
            context = dict(source_id=sid, report_id=source['report_id'],
                           source_descriptor_sha256=digest(source), supplied_source=copy.deepcopy(source),
                           manifest_mapping=copy.deepcopy(entry), **observed)
            context['text_status'] = 'NOT_INSPECTED'
            if body is not None:
                context['text_status'], _ = _decode(body)
                if context['text_status'] == 'UTF8_TEXT':
                    bodies[sid] = body

            observations[sid] = context
    finally:
        os.close(root_fd)
    passages = [_passage_observation(p, candidates, observations[p['source_id']], bodies.get(p['source_id']))
                for p in manifest['passages']]
    if catalog_mode:
        counts = [_line_count(body) for body in bodies.values()]
        if any(n > MAX_CATALOG_LINES_PER_SOURCE for n in counts) or sum(counts) > MAX_CATALOG_LINES_TOTAL:
            raise PassageCheckError('catalog physical line count exceeds supported limit; no partial catalog returned')
        for sid, body in bodies.items():
            observations[sid]['physical_lines'] = _physical_lines(body)
    result.update(sources=list(observations.values()), passages=passages,
                  all_requested_bytes_match=all(s['status'] == 'BYTES_MATCH' for s in observations.values()),
                  all_requested_text_decodable=all(s['text_status'] == 'UTF8_TEXT' for s in observations.values()),
                  all_requested_passages_match=bool(passages) and all(p['status'] == 'TEXT_MATCH' for p in passages))
    return _finish(result)


def catalog(protocol, candidates, manifest, root):
    """Explicitly return only verified UTF-8 sources with physical line byte ranges."""
    return _inspect(protocol, candidates, manifest, root, catalog_mode=True)


def check_passages(protocol, candidates, manifest, root):
    """Observe exact supplied ranges and quotes without changing any input or status."""
    return _inspect(protocol, candidates, manifest, root, catalog_mode=False)


def render_text(result):
    """Control-safe human view: literal manual field beside expected/observed quote."""
    lines, size = [], 0
    def append(line):
        nonlocal size
        size += len(line.encode('utf-8')) + 1
        if size > MAX_OUTPUT_BYTES:
            raise ValueError('text observation exceeds output byte limit')
        lines.append(line)
    append('Local manual-result passage observation')
    append('Stage: ' + quoted_display(result['stage']))
    for key in ('protocol_sha256', 'candidate_document_sha256', 'manual_intake_target_sha256',
                'manifest_sha256', 'engine_sha256', 'hash_scope'):
        if key in result:
            append(key + ': ' + quoted_display(result[key]))
    if 'manifest' in result:
        for key in ('available_candidates', 'available_sources', 'manifest', 'blank_source',
                    'blank_passage', 'template_warning'):
            append(key + ': ' + quoted_display(result[key]))
    for source in result.get('sources', []):
        append('Source: ' + quoted_display({key: value for key, value in source.items() if key != 'physical_lines'}))
        for line in source.get('physical_lines', []):
            append('  Physical line ' + str(line['line_number']) + ' bytes [' + str(line['byte_start']) +
                         ', ' + str(line['byte_end']) + '): ' + quoted_display(line['text']))
    for passage in result.get('passages', []):
        append('Passage: ' + quoted_display({key: value for key, value in passage.items()
                     if key not in ('field_value', 'expected_quote', 'observed_quote')}))
        append('  Manual field value: ' + quoted_display(passage['field_value']))
        append('  Expected quote:     ' + quoted_display(passage['expected_quote']))
        append('  Observed quote:     ' + quoted_display(passage['observed_quote']))
    for key in ('all_requested_bytes_match', 'all_requested_text_decodable', 'all_requested_passages_match',
                'uninspected_source_references', 'unanchored_fields', 'limits', 'boundary'):
        if key in result:
            append(key + ': ' + quoted_display(result[key]))
    return '\n'.join(lines) + '\n'


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'result passage check argument error; use --help for usage\n')


def _preflight_output(path):
    if path is not None and os.path.lexists(path):
        raise PassageCheckError('output must be a new file, not an existing or dangling path; no source inspected')


def main():
    configure_utf8_stdio()
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('template', 'catalog', 'check'):
        command = commands.add_parser(name)
        command.add_argument('protocol', type=Path)
        command.add_argument('candidates', type=Path)
        if name != 'template':
            command.add_argument('manifest', type=Path)
            command.add_argument('--root', required=True,
                                 help='dedicated trusted quiescent root; only explicit manifest paths opened')
        command.add_argument('--output', type=Path, help='write JSON to a new file only, never overwrite')
        command.add_argument('--text', action='store_true', help='control-safe fields/quotes or physical line catalog')
    args = parser.parse_args()
    try:
        # Including dangling output symlinks: fail before source root/files, and
        # even before reading supplied JSON files. Exclusive create still applies
        # after encoding; this is not an atomic race/security claim.
        _preflight_output(args.output)
        protocol, candidates = read_input(args.protocol), read_input(args.candidates)
        if args.command == 'template':
            result = template(protocol, candidates)
        else:
            function = catalog if args.command == 'catalog' else check_passages
            result = function(protocol, candidates, read_input(args.manifest), args.root)
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        rendered = render_text(result) if args.text else encoded
        encoded.encode('utf-8'); rendered.encode('utf-8')
        if args.output is not None:
            with args.output.open('x', encoding='utf-8', newline='\n') as output:
                output.write(encoded)
    except PassageCheckError as error:
        parser.exit(1, 'result passage check error: ' + quoted_display(str(error)) + '\n')
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError, OverflowError):
        parser.exit(1, 'result passage check error: invalid input metadata, unsupported secure access, '
                    'or unreadable/unsafe input, root or new output; no absolute paths or source exception text shown\n')
    print(rendered, end='')
    if args.command == 'check' and not result['all_requested_passages_match']:
        parser.exit(1)
    if args.command == 'catalog' and not (result['all_requested_bytes_match'] and result['all_requested_text_decodable']):
        parser.exit(1)


if __name__ == '__main__':
    main()
