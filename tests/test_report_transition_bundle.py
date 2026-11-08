"""Independent synthetic transition ZIP tests; not scientific or source validation."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

import report_intake
import report_retrieval
import report_decision
import report_transition_bundle as bundle

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


def synthetic_chain():
    initial = fixture('report-intake-base.json')
    initial['synthetic_opaque'] = {'literal': '합성 β\n  spacing ', 'typed': [1, True, None]}
    candidates = fixture('manual-report-candidates.json')
    candidates['candidates'][0]['report']['locator'] = 'file:///never-open-this-document'
    review = report_intake.prepare(initial, candidates)['review_document']
    review.update(receipt_id='bundle-registration', decision='import_reports', reviewer='Fictional reviewer',
                  reviewed_at='2026-11-04', rationale='Synthetic supplied registration only')
    first = report_intake.assemble(initial, candidates, review)
    current = first['protocol_candidate']
    candidates = fixture('manual-retrieval-candidates.json')
    review = report_retrieval.prepare(current, candidates)['review_document']
    review.update(receipt_id='bundle-retrieval', decision='update_retrieval', reviewer='Fictional reviewer',
                  reviewed_at='2026-11-04', rationale='Synthetic supplied retrieval only')
    second = report_retrieval.assemble(current, candidates, review)
    current = second['protocol_candidate']
    decision = report_decision.prepare(current, 'report-B')['decision_document']
    decision.update(receipt_id='bundle-decision', decision='include', reason='Synthetic explicit reason',
                    adjudicator='Fictional human', decided_at='2026-11-04', rationale='Synthetic explicit choice',
                    source_locator='https://invalid.example/never-fetch', study_declaration={'study_id': 'synthetic-study'})
    third = report_decision.assemble(current, decision)
    return initial, [first, second, third], third['protocol_candidate']


class ReportTransitionBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial, cls.applications, cls.endpoint = synthetic_chain()
        cls.initial_raw = encoded(cls.initial)
        cls.application_raws = [encoded(a) for a in cls.applications]
        cls.endpoint_raw = encoded(cls.endpoint)

    def build(self):
        return bundle.build_bundle(self.initial_raw, self.application_raws, self.endpoint_raw)

    def payloads(self, raw=None):
        with zipfile.ZipFile(io.BytesIO(self.build() if raw is None else raw)) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def repack(self, entries, overrides=None, duplicates=(), compression=zipfile.ZIP_STORED, reverse=False, comment=b''):
        target = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(target, 'w') as archive:
                archive.comment = comment
                for name, data in sorted(entries.items(), reverse=reverse) + list(duplicates):
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100600 << 16
                    info.compress_type = compression
                    for key, value in (overrides or {}).get(name, {}).items():
                        setattr(info, key, value)
                    archive.writestr(info, data)
        return target.getvalue()

    def reseal(self, entries):
        manifest = json.loads(entries['manifest.json'])
        for row in manifest['files']:
            if row['path'] in entries:
                raw = entries[row['path']]
                row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        entries['manifest.json'] = encoded(manifest)
        return entries

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'report_transition_bundle.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def files(self, root):
        initial, endpoint = root / 'initial.json', root / 'endpoint.json'
        initial.write_bytes(self.initial_raw); endpoint.write_bytes(self.endpoint_raw)
        paths = []
        for index, raw in enumerate(self.application_raws):
            path = root / ('application=%d.json' % index); path.write_bytes(raw); paths.append(path)
        return initial, endpoint, paths

    def test_deterministic_exact_original_bytes_and_fixed_members(self):
        before = copy.deepcopy((self.initial_raw, self.application_raws, self.endpoint_raw))
        raw = self.build()
        self.assertEqual(raw, self.build())
        self.assertEqual(before, (self.initial_raw, self.application_raws, self.endpoint_raw))
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        entries = self.payloads(raw)
        self.assertEqual(set(entries), {'protocols/initial.json', 'protocols/endpoint.json', 'chain.json',
            'summary.txt', 'manifest.json'} | {'applications/step-%06d.json' % i for i in range(3)})
        self.assertEqual(entries['protocols/initial.json'], self.initial_raw)
        self.assertEqual(entries['protocols/endpoint.json'], self.endpoint_raw)
        for index, original in enumerate(self.application_raws):
            self.assertEqual(entries['applications/step-%06d.json' % index], original)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for info in archive.infolist():
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertFalse(info.extra or info.comment)

    def test_valid_contiguous_suffix_and_prefix_do_not_require_entire_history(self):
        for start, end in [(0, 1), (1, 2), (2, 3), (1, 3)]:
            original = self.initial if start == 0 else self.applications[start-1]['protocol_candidate']
            endpoint = self.applications[end-1]['protocol_candidate']
            raw = bundle.build_bundle(encoded(original), self.application_raws[start:end], encoded(endpoint))
            self.assertTrue(bundle.verify_bundle(raw)['valid'])

    def test_reordered_omitted_duplicate_and_stale_steps_fail(self):
        cases = [list(reversed(self.application_raws)), self.application_raws[1:],
                 self.application_raws[::2], self.application_raws[:2],
                 self.application_raws + self.application_raws[-1:],
                 [self.application_raws[0], self.application_raws[0], self.application_raws[2]]]
        for apps in cases:
            with self.subTest(count=len(apps)), self.assertRaises(ValueError):
                bundle.build_bundle(self.initial_raw, apps, self.endpoint_raw)

    def test_full_protocol_equality_covers_opaque_data_and_json_scalar_types(self):
        for field, value in [('unrelated', 'new'), ('synthetic_opaque', {'typed': [True, 1, None]})]:
            changed = copy.deepcopy(self.endpoint); changed[field] = value
            with self.assertRaises(ValueError): bundle.build_bundle(self.initial_raw, self.application_raws, encoded(changed))
        changed = copy.deepcopy(self.initial); changed['unrelated'] = 'new'
        with self.assertRaises(ValueError): bundle.build_bundle(encoded(changed), self.application_raws, self.endpoint_raw)
        # Python dict equality equates bool/int; canonical JSON equality must not.
        changed = copy.deepcopy(self.endpoint); changed['synthetic_opaque']['typed'][0] = True
        with self.assertRaises(ValueError): bundle.build_bundle(self.initial_raw, self.application_raws, encoded(changed))

    def test_whitespace_and_unicode_are_retained_not_normalized(self):
        start = b' \n' + json.dumps(self.initial, ensure_ascii=False).encode() + b'\r\n'
        end = json.dumps(self.endpoint, ensure_ascii=True, separators=(',', ':')).encode() + b'\n\n'
        apps = [b'\n' + json.dumps(a, ensure_ascii=False).encode() + b'\r\n' for a in self.applications]
        raw = bundle.build_bundle(start, apps, end)
        self.assertNotEqual(raw, self.build())
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        entries = self.payloads(raw)
        self.assertEqual(entries['protocols/initial.json'], start)
        self.assertEqual(entries['protocols/endpoint.json'], end)
        for i, original in enumerate(apps): self.assertEqual(entries['applications/step-%06d.json' % i], original)

    def test_only_three_detached_kinds_dispatch_and_each_verifier_is_used(self):
        with patch.object(report_intake, 'verify', wraps=report_intake.verify) as intake, \
             patch.object(report_retrieval, 'verify', wraps=report_retrieval.verify) as retrieval, \
             patch.object(report_decision, 'verify', wraps=report_decision.verify) as decision:
            self.build()
            for verifier in [intake, retrieval, decision]: self.assertGreaterEqual(verifier.call_count, 1)
        for kind in ['detached_bibliographic_intake', 'detached_report_review', '__import__', None, True, 1, []]:
            changed = copy.deepcopy(self.applications[0]); changed['kind'] = kind
            with self.assertRaises(ValueError):
                bundle.build_bundle(self.initial_raw, [encoded(changed)] + self.application_raws[1:], self.endpoint_raw)

    def test_tampered_application_and_resealed_receipt_fail(self):
        for reseal in [False, True]:
            changed = copy.deepcopy(self.applications[1]); changed['protocol_candidate']['reports'][1]['reason'] = 'changed'
            if reseal:
                changed['receipt']['receipt_sha256'] = report_retrieval.digest(
                    {k: v for k, v in changed['receipt'].items() if k != 'receipt_sha256'})
            with self.assertRaises(ValueError):
                bundle.build_bundle(self.initial_raw, [self.application_raws[0], encoded(changed), self.application_raws[2]], self.endpoint_raw)

    def test_raw_type_strictness_and_empty_or_excess_steps(self):
        for bad in [None, '', bytearray(self.initial_raw), {}, []]:
            with self.assertRaises(ValueError): bundle.build_bundle(bad, self.application_raws, self.endpoint_raw)
            with self.assertRaises(ValueError): bundle.build_bundle(self.initial_raw, self.application_raws, bad)
            with self.assertRaises(ValueError): bundle.verify_bundle(bad)
        for bad in [None, {}, (), [], self.application_raws * 7, [self.applications[0]], [bytearray(self.application_raws[0])]]:
            with self.assertRaises(ValueError): bundle.build_bundle(self.initial_raw, bad, self.endpoint_raw)

    def test_strict_json_all_inputs(self):
        bads = [b'\xff', b'null', b'[]', b'{}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1,"x":1}', b'{"x":"\\ud800"}']
        for bad in bads:
            for position in range(3):
                args = [self.initial_raw, self.application_raws, self.endpoint_raw]
                args[position] = [bad] + self.application_raws[1:] if position == 1 else bad
                with self.subTest(raw=bad, position=position), self.assertRaises(ValueError): bundle.build_bundle(*args)

    def test_implementation_hashes_include_three_verifiers_and_wrapper(self):
        hashes = bundle.implementation_hashes()
        for name in ['report_intake.py', 'report_retrieval.py', 'report_decision.py', 'report_transition_bundle.py']:
            self.assertEqual(hashes[name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
        raw = self.build()
        with patch.object(bundle, 'implementation_hashes', return_value={'changed': 'code'}):
            with self.assertRaises(ValueError): bundle.verify_bundle(raw)

    def test_resealed_payload_chain_summary_and_manifest_tampering_fail(self):
        baseline = self.payloads()
        for member in ['chain.json', 'summary.txt', 'protocols/endpoint.json', 'applications/step-000001.json']:
            entries = dict(baseline)
            if member.endswith('.json'):
                value = json.loads(entries[member]); value['synthetic_tamper'] = True; entries[member] = encoded(value)
            else: entries[member] += b'\nConclusion: READY\n'
            with self.subTest(member=member), self.assertRaises(ValueError):
                bundle.verify_bundle(self.repack(self.reseal(entries)))
        for replacement in [b'null', b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}']:
            entries = dict(baseline); entries['manifest.json'] = replacement
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries))

    def test_member_paths_duplicates_missing_and_embedded_code_rejected(self):
        baseline = self.payloads()
        for name in ['../escape', '/absolute', 'C:/absolute', 'applications\\step-000000.json',
                     'applications/step-000003.json', 'applications/step-0.json', 'report_intake.py', 'directory/']:
            entries = dict(baseline); entries[name] = b'inert malicious content'
            with self.subTest(name=name), self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries))
        for name in baseline:
            entries = dict(baseline); del entries[name]
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries))
        with self.assertRaises(ValueError):
            bundle.verify_bundle(self.repack(baseline, duplicates=[('chain.json', baseline['chain.json'])]))

    def test_zip_metadata_symlink_compression_order_comments_and_trailing_bytes(self):
        entries = self.payloads(); member = 'protocols/initial.json'
        overrides = [{'external_attr': (stat.S_IFLNK | 0o777) << 16}, {'date_time': (2025, 1, 1, 0, 0, 0)},
                     {'create_system': 0}, {'extra': b'\x34\x12\x00\x00'}, {'comment': b'changed'},
                     {'external_attr': 0o100644 << 16}]
        for override in overrides:
            with self.subTest(override=override), self.assertRaises(ValueError):
                bundle.verify_bundle(self.repack(entries, overrides={member: override}))
        for raw in [self.repack(entries, compression=zipfile.ZIP_DEFLATED), self.repack(entries, reverse=True),
                    self.repack(entries, comment=b'changed'), self.build() + b'trailer', b'prefix' + self.build(), b'not ZIP']:
            with self.assertRaises(ValueError): bundle.verify_bundle(raw)

    def test_zip_encryption_crc_and_declared_size_attacks(self):
        raw = self.build(); central = raw.index(b'PK\x01\x02'); local = raw.index(b'PK\x03\x04')
        encrypted = bytearray(raw)
        for offset in [local+6, central+8]:
            flags = struct.unpack_from('<H', encrypted, offset)[0]; struct.pack_into('<H', encrypted, offset, flags | 1)
        oversized = bytearray(raw)
        for offset in [central+20, central+24]: struct.pack_into('<I', oversized, offset, 50_000_001)
        bad_crc = bytearray(raw); name_len, extra_len = struct.unpack_from('<HH', bad_crc, local+26)
        bad_crc[local+30+name_len+extra_len] ^= 1
        for attack in [encrypted, oversized, bad_crc]:
            with self.assertRaises(ValueError): bundle.verify_bundle(bytes(attack))

    def test_inclusive_archive_size_bound(self):
        raw = self.build()
        self.assertEqual(bundle.MAX_BUNDLE_BYTES, 50_000_000)
        with patch.object(bundle, 'MAX_BUNDLE_BYTES', len(raw)):
            self.assertEqual(self.build(), raw)
            self.assertTrue(bundle.verify_bundle(raw)['valid'])
        with patch.object(bundle, 'MAX_BUNDLE_BYTES', len(raw)-1):
            with self.assertRaises(ValueError): self.build()
            with self.assertRaises(ValueError): bundle.verify_bundle(raw)

    def test_exactly_twenty_steps_allowed_twenty_one_refused(self):
        initial = self.applications[1]['protocol_candidate']; current = initial; applications = []
        for i in range(21):
            doc = report_decision.prepare(current, 'report-B')['decision_document']
            doc.update(receipt_id='synthetic-%d' % i, decision='exclude', reason='Synthetic reason %d' % i,
                       adjudicator='Fictional human', decided_at='2026-11-04', rationale='Synthetic sequence',
                       source_locator='synthetic:never-open', study_declaration=None)
            app = report_decision.assemble(current, doc); applications.append(encoded(app)); current = app['protocol_candidate']
            if i == 19: endpoint20 = encoded(current)
        raw = bundle.build_bundle(encoded(initial), applications[:20], endpoint20)
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        with self.assertRaises(ValueError): bundle.build_bundle(encoded(initial), applications, encoded(current))

    def test_offline_inert_locators_no_extraction_or_claim_escalation(self):
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')), \
             patch.object(zipfile.ZipFile, 'extract', side_effect=AssertionError('extraction forbidden')), \
             patch.object(zipfile.ZipFile, 'extractall', side_effect=AssertionError('extraction forbidden')):
            result = bundle.verify_bundle(self.build())
        self.assertEqual(result['external_calls'], 0)
        self.assertFalse(result['protocol_changed'])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        text = bundle.render_text(result)
        self.assertIn('NOT_READY', text)
        self.assertNotIn('\nConclusion: READY', text)

    def test_api_create_verify_relocation_and_no_host_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); initial, endpoint, apps = self.files(root); out = root / 'bundle.zip'
            result = bundle.create(initial, endpoint, out, apps)
            self.assertTrue(result['valid']); self.assertEqual(out.read_bytes(), self.build())
            self.assertNotIn(str(root).encode(), out.read_bytes())
            relocated = root / 'relocated.zip'; out.rename(relocated)
            for path in [initial, endpoint] + apps: path.unlink()
            self.assertTrue(bundle.verify(relocated)['valid'])

    def test_exclusive_output_existing_file_directory_and_dangling_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); initial, endpoint, apps = self.files(root)
            out = root / 'existing'; out.write_bytes(b'untouched')
            with self.assertRaises((OSError, ValueError)): bundle.create(initial, endpoint, out, apps)
            self.assertEqual(out.read_bytes(), b'untouched')
            directory = root / 'directory'; directory.mkdir()
            with self.assertRaises((OSError, ValueError)): bundle.create(initial, endpoint, directory, apps)
            link = root / 'dangling'; target = root / 'absent'
            try: link.symlink_to(target)
            except (OSError, NotImplementedError): return
            with self.assertRaises((OSError, ValueError)): bundle.create(initial, endpoint, link, apps)
            self.assertTrue(link.is_symlink()); self.assertFalse(target.exists())

    def test_cli_roundtrip_text_utf8_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); initial, endpoint, apps = self.files(root); out = root / 'bundle.zip'
            args = ['create', initial, endpoint, out]
            for path in apps: args += ['--application', path]
            result = self.invoke(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid']); self.assertEqual(out.read_bytes(), self.build())
            checked = self.invoke('verify', out, '--text')
            self.assertEqual(checked.returncode, 0, checked.stderr); self.assertIn(b'NOT_READY', checked.stdout)
            raw = out.read_bytes(); self.assertNotEqual(self.invoke(*args).returncode, 0); self.assertEqual(out.read_bytes(), raw)

    def test_cli_invalid_input_leaves_no_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); initial, endpoint, apps = self.files(root); out = root / 'bundle.zip'
            for raw in [b'\xff', b'{}', b'null', b'{"x":1,"x":1}']:
                apps[0].write_bytes(raw)
                result = self.invoke('create', initial, endpoint, out, '--application', apps[0])
                self.assertNotEqual(result.returncode, 0); self.assertFalse(out.exists()); self.assertNotIn(b'Traceback', result.stderr)
            out.write_bytes(b'not ZIP'); result = self.invoke('verify', out)
            self.assertNotEqual(result.returncode, 0); self.assertNotIn(b'Traceback', result.stderr)

    def test_application_schema_types_and_extra_fields_rejected(self):
        for position in range(3):
            for field, value in [('schema_version', True), ('schema_version', 1.0), ('schema_version', '1'),
                                 ('receipt', []), ('protocol_candidate', None), ('unexpected', True)]:
                changed = copy.deepcopy(self.applications[position]); changed[field] = value
                apps = list(self.application_raws); apps[position] = encoded(changed)
                with self.subTest(position=position, field=field, value=value), self.assertRaises(ValueError):
                    bundle.build_bundle(self.initial_raw, apps, self.endpoint_raw)

    def test_summary_explicitly_denies_history_execution_and_authenticity(self):
        result = bundle.verify_bundle(self.build())
        expected = dict(complete_history='NOT_ESTABLISHED', history_before_segment='NOT_ASSESSED',
                        history_after_segment='NOT_ASSESSED', execution_verification='NOT_PERFORMED',
                        review_status='NOT_PERFORMED', review_renewal='NOT_PERFORMED',
                        human_authenticity='NOT_VERIFIED', source_authenticity='NOT_VERIFIED', reading='NOT_ESTABLISHED')
        for key, value in expected.items(): self.assertEqual(result[key], value)
        self.assertEqual(result['supported_steps'], 3)
        self.assertEqual(result['step_kinds'], [app['kind'] for app in self.applications])
        self.assertEqual(result['initial_bytes_sha256'], hashlib.sha256(self.initial_raw).hexdigest())
        self.assertEqual(result['endpoint_bytes_sha256'], hashlib.sha256(self.endpoint_raw).hexdigest())

    def test_api_serialization_limit_and_output_inspection_fail_closed(self):
        raw = self.build()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); initial, endpoint, apps = self.files(root); out = root / 'bundle.zip'
            with patch.object(bundle, 'build_bundle', return_value=raw), \
                 patch.object(bundle, '_json_bytes', side_effect=ValueError('synthetic serialization failure')):
                with self.assertRaises(ValueError): bundle.create(initial, endpoint, out, apps)
            self.assertFalse(out.exists())
            with patch.object(bundle, 'MAX_BUNDLE_BYTES', 1):
                with self.assertRaises(ValueError): bundle.create(initial, endpoint, out, apps)
            self.assertFalse(out.exists())
            for failure in [None, PermissionError('synthetic denied')]:
                with patch.object(Path, 'lstat', return_value=object(), side_effect=failure), patch.object(Path, 'open') as opened:
                    with self.assertRaises(OSError): bundle._write_new(out, b'bytes')
                    opened.assert_not_called()

    def test_cli_rendering_preflight_happens_before_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); initial, endpoint, apps = self.files(root); out = root / 'bundle.zip'
            argv = ['report_transition_bundle.py', 'create', str(initial), str(endpoint), str(out), '--text']
            for path in apps: argv += ['--application', str(path)]
            for render in [lambda _: (_ for _ in ()).throw(ValueError('synthetic render failure')), lambda _: '\ud800']:
                with patch.object(sys, 'argv', argv), patch.object(bundle, 'configure_utf8_stdio'), \
                     patch.object(sys, 'stdout', io.StringIO()), patch.object(sys, 'stderr', io.StringIO()), \
                     patch.object(bundle, 'render_text', side_effect=render):
                    with self.assertRaises(SystemExit): bundle.main()
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
