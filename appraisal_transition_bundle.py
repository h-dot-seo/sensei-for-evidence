"""Preserve an explicitly supplied contiguous appraisal-transition replay segment.

The wrapper never changes protocols, renews reviews, fetches sources or executes
embedded code. The existing appraisal application verifier remains the replay authority.
"""
import argparse
import hashlib
import io
from pathlib import Path
import re
import stat
import zipfile

import bibliographic_intake
import nbib_intake
import appraisal_intake
import research_bundle
from evidence_workflow import run
from json_io import canonical_json_bytes, configure_utf8_stdio, parse_json, quoted_display
from prisma_reports import report_flow

MAX_BUNDLE_BYTES = 50_000_000
MAX_STEPS = 20
VERIFIERS = {'detached_appraisal_intake': appraisal_intake}
FIXED_MEMBERS = {'protocols/initial.json', 'protocols/endpoint.json', 'chain.json', 'summary.txt', 'manifest.json'}
BOUNDARY = (
    'Exact explicitly supplied contiguous appraisal-import segment and canonical archive consistency only. '
    'Every application is replayed through the existing appraisal intake verifier; no new appraisal, '
    'method, judgement, review, protocol mutation or automatic rebase occurs. Exact initial protocol, '
    'application and endpoint bytes retain supplied domain assertions, reviewer metadata, result/source '
    'snapshots and changed downstream review cues. Canonical JSON equality connects steps; whitespace '
    'and key order may differ between equivalent protocol representations. Historical assertions apply '
    'to their recorded step context, not automatically to the endpoint or later inputs. No review, '
    'work completion, synthesis position or planning rank is renewed. No method suitability, consensus, '
    'quality score or current appraisal validity is established. This selected segment may omit earlier '
    'or later imports and is not a complete research or appraisal history. Only detached appraisal '
    'intake applications are supported as steps; corrections, result/condition imports, work transitions '
    'and read-only appraisal comparisons are not replayed as steps. Pre-existing ledgers remain under '
    'their normal validators. No source documents, native citation files, artifact bytes or implementation '
    'code are added. Use separately retained recorded implementation; archive code is never executed. '
    'Editable unsigned assertions do not authenticate people, chronology, source identity, reading, '
    'independent reviewers or scientific validity. Mapped source catalogs are recorded context, not '
    'selected or read documents. Matching hashes/counts do not establish research completeness, '
    'PRISMA compliance, clinical applicability or development readiness. No locator is followed, '
    'file extracted or external call made. Altered ZIP bytes including metadata invalidate this '
    'canonical byte receipt; byte-identical canonical repacking is accepted. Supplied private '
    'text and identities are retained without redaction.'
)


def _claims():
    return dict(review_status='NOT_PERFORMED', review_renewal='NOT_PERFORMED',
        completion_renewal='NOT_PERFORMED', execution_verification='NOT_PERFORMED',
        human_authenticity='NOT_VERIFIED', source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED',
        acceptance_assessment='NOT_PERFORMED', artifact_content_verification='NOT_PERFORMED',
        history_before_segment='NOT_ASSESSED', history_after_segment='NOT_ASSESSED',
        complete_history='NOT_ESTABLISHED', downstream_reassessment='NOT_PERFORMED',
        scientific_acceptance='NOT_ASSESSED', extraction_completeness='NOT_ESTABLISHED',
        appraisal_assertion_scope='RECORDED_STEP_CONTEXT_ONLY', appraisal_validity='NOT_ASSESSED', method_suitability='NOT_ASSESSED', external_calls=0, protocol_changed=False,
        census_claim='NOT_ESTABLISHED', conclusion_readiness='NOT_READY')



def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _size(size):
    if size > MAX_BUNDLE_BYTES:
        raise ValueError('appraisal transition bundle exceeds size limit')


def _json_bytes(value):
    nbib_intake._strict_json(value)
    raw = research_bundle.json_bytes(value)
    _size(len(raw))
    return raw


def implementation_hashes():
    hashes = {}
    for module in VERIFIERS.values():
        hashes.update(module._implementation_hashes())
    # These helpers are used directly here, outside the verifiers' engine maps.
    for helper in (nbib_intake, bibliographic_intake):
        path = Path(helper.__file__).resolve()
        hashes[path.name] = _sha(path.read_bytes())
    hashes['appraisal_transition_bundle.py'] = _sha(Path(__file__).resolve().read_bytes())
    return dict(sorted(hashes.items()))


def _archive_size(payloads):
    return 22 + sum(len(raw) + 76 + 2 * len(name.encode('ascii')) for name, raw in payloads.items())


def _add(payloads, name, raw):
    if type(raw) is not bytes:
        raise ValueError('all retained inputs must be exact bytes')
    _size(sum(map(len, payloads.values())) + len(raw))
    payloads[name] = raw
    _size(_archive_size(payloads))


def _protocol(raw, label):
    value = parse_json(raw)
    nbib_intake._strict_json(value)
    if type(value) is not dict:
        raise ValueError(label + ' must be a protocol object')
    run(value)
    if 'reports' in value:
        report_flow(value, include_csv=False)
    return value


def _summary(chain, raw=None, files=None):
    result = dict(schema_version=1, valid=True, supported_steps=len(chain['steps']),
        step_kinds=[step['kind'] for step in chain['steps']],
        explicit_appraisal_ids_by_step=[step['explicit_appraisal_ids'][:] for step in chain['steps']],
        initial_protocol_sha256=chain['initial']['canonical_protocol_sha256'],
        endpoint_protocol_sha256=chain['endpoint']['canonical_protocol_sha256'],
        initial_bytes_sha256=chain['initial']['raw_sha256'], endpoint_bytes_sha256=chain['endpoint']['raw_sha256'],
        verification_scope='Exact supplied segment replay and canonical archive bytes; not complete history or authentication',
        **_claims(), boundary=BOUNDARY)
    if raw is not None:
        result.update(bytes=len(raw), sha256=_sha(raw), files=files)
    return result


def render_text(result):
    text = ('Supplied appraisal-transition segment consistency: true\n'
        'Supported steps: ' + str(result['supported_steps']) + '\n'
        'Ordered step kinds: ' + quoted_display(result['step_kinds']) + '\n'
        'Explicit appraisal IDs by step: ' + quoted_display(result['explicit_appraisal_ids_by_step']) + '\n'
        'Initial canonical protocol SHA-256: ' + result['initial_protocol_sha256'] + '\n'
        'Endpoint canonical protocol SHA-256: ' + result['endpoint_protocol_sha256'] + '\n'
        'Earlier/later history: NOT_ASSESSED\nComplete history: NOT_ESTABLISHED\n'
        'External calls: 0\nCensus: NOT_ESTABLISHED\nConclusion: NOT_READY\n' + BOUNDARY + '\n')
    _size(len(text.encode('utf-8')))
    return text


def build_bundle(initial_raw, application_raws, endpoint_raw):
    """Retain exact bytes, replay explicit order, then match the supplied endpoint."""
    if type(application_raws) is not list or not 1 <= len(application_raws) <= MAX_STEPS:
        raise ValueError('applications require between 1 and 20 explicitly ordered byte inputs')
    payloads = {}
    _add(payloads, 'protocols/initial.json', initial_raw)
    _add(payloads, 'protocols/endpoint.json', endpoint_raw)
    for index, raw in enumerate(application_raws):
        _add(payloads, 'applications/step-%06d.json' % index, raw)
    current = _protocol(initial_raw, 'initial input')
    endpoint = _protocol(endpoint_raw, 'endpoint input')
    initial_hash = _sha(canonical_json_bytes(current))
    steps = []
    for index, raw in enumerate(application_raws):
        application = parse_json(raw)
        nbib_intake._strict_json(application)
        if type(application) is not dict or type(application.get('kind')) is not str or application['kind'] not in VERIFIERS:
            raise ValueError('unsupported appraisal-transition application kind')
        checked = VERIFIERS[application['kind']].verify(current, application)
        if checked.get('valid') is not True or checked.get('status') != 'EXACT_REPLAY_MATCH':
            raise ValueError('existing appraisal verifier did not confirm exact replay')
        candidate = application['protocol_candidate']
        document = application['receipt']['candidate_document']
        explicit_ids = [row['appraisal_id'] for row in document['appraisals']]
        steps.append(dict(step_index=index, kind=application['kind'],
            application_path='applications/step-%06d.json' % index,
            application_bytes=len(raw), application_raw_sha256=_sha(raw),
            input_protocol_sha256=_sha(canonical_json_bytes(current)),
            candidate_protocol_sha256=_sha(canonical_json_bytes(candidate)),
            receipt_id=application['receipt']['receipt_id'], receipt_sha256=application['receipt']['receipt_sha256'],
            replay_status=checked['status'], explicit_appraisal_ids=explicit_ids))
        current = candidate
    if canonical_json_bytes(current) != canonical_json_bytes(endpoint):
        raise ValueError('supplied endpoint differs from the final replayed candidate protocol')
    chain = dict(schema_version=1, mode='explicit_appraisal_transition_segment',
        initial=dict(path='protocols/initial.json', bytes=len(initial_raw), raw_sha256=_sha(initial_raw),
                     canonical_protocol_sha256=initial_hash),
        endpoint=dict(path='protocols/endpoint.json', bytes=len(endpoint_raw), raw_sha256=_sha(endpoint_raw),
                      canonical_protocol_sha256=_sha(canonical_json_bytes(endpoint))),
        steps=steps, **_claims(), boundary=BOUNDARY)
    _add(payloads, 'chain.json', _json_bytes(chain))
    _add(payloads, 'summary.txt', render_text(_summary(chain)).encode('utf-8'))
    manifest = dict(schema_version=1, mode='explicit_appraisal_transition_bundle',
        engine_sha256=implementation_hashes(),
        files=[dict(path=name, bytes=len(raw), sha256=_sha(raw)) for name, raw in sorted(payloads.items())],
        **_claims(), boundary=BOUNDARY)
    _add(payloads, 'manifest.json', _json_bytes(manifest))
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(payloads.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100600 << 16
            archive.writestr(entry, raw)
    raw = output.getvalue()
    _size(len(raw))
    return raw


def _check_entries(archive):
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    if len(entries) > MAX_STEPS + len(FIXED_MEMBERS) or len(names) != len(set(names)):
        raise ValueError('unexpected or duplicate archive entries')
    _size(sum(entry.file_size for entry in entries))
    for entry in entries:
        allowed = entry.filename in FIXED_MEMBERS or re.fullmatch(r'applications/step-[0-9]{6}\.json', entry.filename)
        if (not allowed or entry.is_dir() or entry.flag_bits & 1 or entry.compress_type != zipfile.ZIP_STORED
                or entry.compress_size != entry.file_size or entry.create_system != 3
                or not stat.S_ISREG(entry.external_attr >> 16)):
            raise ValueError('unexpected archive path, type, encryption or compression')
    if not FIXED_MEMBERS.issubset(names):
        raise ValueError('missing appraisal-transition archive entries')
    return names


def verify_bundle(raw):
    """Replay in memory without extraction, source access or executing archive code."""
    if type(raw) is not bytes:
        raise ValueError('bundle input must be exact bytes')
    _size(len(raw))
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = _check_entries(archive)
            manifest = parse_json(archive.read('manifest.json'))
            chain = parse_json(archive.read('chain.json'))
            if type(manifest) is not dict or type(chain) is not dict:
                raise ValueError('manifest and chain must be objects')
            if manifest.get('engine_sha256') != implementation_hashes():
                raise ValueError('appraisal-transition implementation bytes differ; use the separately recorded implementation')
            rows = chain.get('steps')
            if type(rows) is not list or not 1 <= len(rows) <= MAX_STEPS:
                raise ValueError('invalid appraisal-transition step list')
            expected_names = FIXED_MEMBERS | {'applications/step-%06d.json' % index for index in range(len(rows))}
            if set(names) != expected_names:
                raise ValueError('archive applications differ from consecutive declared steps')
            application_raws = []
            for index, row in enumerate(rows):
                name = 'applications/step-%06d.json' % index
                if (type(row) is not dict or type(row.get('step_index')) is not int or row['step_index'] != index
                        or row.get('application_path') != name):
                    raise ValueError('invalid consecutive step index or derived application path')
                application_raws.append(archive.read(name))
            expected = build_bundle(archive.read('protocols/initial.json'), application_raws,
                                    archive.read('protocols/endpoint.json'))
            if raw != expected:
                raise ValueError('appraisal-transition archive differs from canonical regenerated bytes')
            return _summary(chain, raw, len(names))
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError, EOFError) as error:
        raise ValueError('invalid appraisal-transition ZIP: ' + str(error)) from error


def _built_summary(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return _summary(parse_json(archive.read('chain.json')), raw, len(archive.infolist()))


def _write_new(path, raw):
    appraisal_intake._write_new(Path(path), raw)


def _read_applications(paths):
    if type(paths) is not list or not 1 <= len(paths) <= MAX_STEPS:
        raise ValueError('application paths require between 1 and 20 explicit entries')
    raws = []
    size = 0
    for path in paths:
        raw = bibliographic_intake.read_bounded(Path(path), MAX_BUNDLE_BYTES)
        size += len(raw)
        _size(size)
        raws.append(raw)
    return raws


def create(initial_path, endpoint_path, destination, application_paths):
    initial_raw = bibliographic_intake.read_bounded(Path(initial_path), MAX_BUNDLE_BYTES)
    endpoint_raw = bibliographic_intake.read_bounded(Path(endpoint_path), MAX_BUNDLE_BYTES)
    _size(len(initial_raw) + len(endpoint_raw))
    raw = build_bundle(initial_raw, _read_applications(application_paths), endpoint_raw)
    result = _built_summary(raw)
    _json_bytes(result)
    _write_new(destination, raw)
    return result


def verify(path):
    return verify_bundle(bibliographic_intake.read_bounded(Path(path), MAX_BUNDLE_BYTES))


def main():
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('create')
    make.add_argument('initial', type=Path)
    make.add_argument('endpoint', type=Path)
    make.add_argument('output', type=Path)
    make.add_argument('--application', action='append', required=True, metavar='APPLICATION.json')
    make.add_argument('--text', action='store_true')
    check = commands.add_parser('verify')
    check.add_argument('bundle', type=Path)
    check.add_argument('--text', action='store_true')
    args = parser.parse_args()
    try:
        output = None
        if args.command == 'create':
            initial_raw = bibliographic_intake.read_bounded(args.initial, MAX_BUNDLE_BYTES)
            endpoint_raw = bibliographic_intake.read_bounded(args.endpoint, MAX_BUNDLE_BYTES)
            _size(len(initial_raw) + len(endpoint_raw))
            output = build_bundle(initial_raw, _read_applications(args.application), endpoint_raw)
            result = _built_summary(output)
        else:
            result = verify(args.bundle)
        stdout = render_text(result).encode('utf-8') if args.text else _json_bytes(result)
        _size(len(stdout))
        if output is not None:
            _write_new(args.output, output)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, RecursionError, OverflowError,
            zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError, EOFError) as error:
        parser.exit(1, 'Appraisal transition bundle error: ' + quoted_display(str(error)) + '\n')
    print(stdout.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
