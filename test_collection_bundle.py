"""Synthetic native collection portability, exact ledger binding and hostile ZIPs."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

import bibliographic_intake
import bibliographic_review
import collection_bundle as bundle
from evidence_workflow import run
import nbib_intake
import research_bundle

ROOT = Path(__file__).resolve().parent


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


class CollectionBundleTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / 'examples/bibliographic-base.json').read_bytes())
        self.native = ('\ufeffPMID- 999999999999991\r\nTI  - Fictional 합성\r\n'
                       '      folded title\r\nAU  - Fictional A\r\nAU  - Fictional B\r\n\r\n').encode()
        self.wrapper = nbib_intake.prepare(self.base, self.native, 'local-primary', 'supplied synthetic time')
        self.protocol = self.imported(self.base, self.wrapper['csv_intake'], 'fictional-A')
        self.bindings = [dict(import_index=0, nbib_artifact=self.wrapper)]

    def imported(self, current, intake, rid):
        choices = bibliographic_review.template(intake)
        for index, row in enumerate(choices['resolutions']):
            row.update(disposition='new_record', record_id=rid + (str(index) if index else ''),
                       rationale='Explicit fictional software-test identity assertion')
        doc = bibliographic_review.prepare_review(current, intake, choices)['review_document']
        doc['review'].update(reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                             rationale='Synthetic collection only', decision='import_for_screening')
        return bibliographic_review.assemble(current, intake, doc)['protocol_candidate']

    def build(self, protocol=None, bindings=None):
        return bundle.build_bundle(encoded(self.protocol if protocol is None else protocol),
                                   self.bindings if bindings is None else bindings)

    def payloads(self, raw=None):
        with zipfile.ZipFile(io.BytesIO(self.build() if raw is None else raw)) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def repack(self, entries, overrides=None, duplicates=None, compression=zipfile.ZIP_STORED):
        target = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(target, 'w', compression=compression) as archive:
                for name, data in list(sorted(entries.items())) + (duplicates or []):
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
        return subprocess.run([sys.executable, str(ROOT / 'collection_bundle.py'), *map(str, args)],
            cwd=ROOT, capture_output=True, timeout=60,
            env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_deterministic_exact_protocol_native_bytes_and_no_mutation(self):
        before = copy.deepcopy((self.protocol, self.bindings))
        raw = self.build()
        self.assertEqual(raw, self.build())
        self.assertEqual((self.protocol, self.bindings), before)
        checked = bundle.verify_bundle(raw)
        self.assertTrue(checked['valid'])
        self.assertEqual(checked['covered_import_indices'], [0])
        self.assertEqual(checked['uncovered_import_indices'], [])
        self.assertEqual(checked['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(checked['conclusion_readiness'], 'NOT_READY')
        self.assertFalse(checked['protocol_changed'])
        self.assertEqual(checked['external_calls'], 0)
        entries = self.payloads(raw)
        self.assertEqual(set(entries), {'research.zip', 'bindings.json', 'summary.txt', 'manifest.json',
                                        'native/import-000000.json'})
        self.assertEqual(entries['research.zip'], research_bundle.build_bundle(encoded(self.protocol)))
        self.assertTrue(research_bundle.verify(io.BytesIO(entries['research.zip']))['valid'])
        with zipfile.ZipFile(io.BytesIO(entries['research.zip'])) as ordinary:
            self.assertEqual(ordinary.read('protocol.json'), encoded(self.protocol))
        retained = json.loads(entries['native/import-000000.json'])
        self.assertEqual(retained, self.wrapper)
        self.assertEqual(retained['source_export']['text'].encode(), self.native)
        self.assertTrue(nbib_intake.verify(retained)['valid'])
        self.assertEqual(run(self.protocol)['flow']['pending'], 1)
        self.assertEqual(self.protocol['screening'], [])

    def test_full_exact_binding_hashes_and_unverified_status(self):
        data = json.loads(self.payloads()['bindings.json'])
        self.assertEqual(data['covered_import_indices'], [0])
        self.assertEqual(data['uncovered_import_indices'], [])
        row = data['imports'][0]
        self.assertEqual(row['status'], 'NATIVE_WRAPPER_BOUND')
        self.assertEqual(row['receipt_sha256'], self.protocol['bibliographic_imports']['imports'][0]['sha256'])
        self.assertEqual(row['canonical_intake_sha256'], nbib_intake.digest(self.wrapper['csv_intake']))
        self.assertEqual(row['canonical_wrapper_sha256'], nbib_intake.digest(self.wrapper))
        self.assertEqual(row['native_export_sha256'], hashlib.sha256(self.native).hexdigest())
        self.assertEqual(row['wrapper_archive_path'], 'native/import-000000.json')
        self.assertEqual(data['search_completion'], 'NOT_ESTABLISHED')

    def test_mixed_csv_and_nbib_imports_expose_partial_attachment(self):
        plain = bibliographic_intake.prepare(self.base, b'record_id,source_locator\nx,synthetic:csv\n',
                                               'local-secondary', 'supplied synthetic second time')
        current = self.imported(self.protocol, plain, 'fictional-B')
        raw = self.build(current)
        checked = bundle.verify_bundle(raw)
        self.assertEqual(checked['covered_import_indices'], [0])
        self.assertEqual(checked['uncovered_import_indices'], [1])
        rows = json.loads(self.payloads(raw)['bindings.json'])['imports']
        self.assertEqual([row['status'] for row in rows], ['NATIVE_WRAPPER_BOUND', 'NO_NATIVE_WRAPPER_SUPPLIED'])
        self.assertNotIn('wrapper_archive_path', rows[1])
        self.assertEqual(checked['total_imports'], 2)
        self.assertEqual(checked['bound_native_wrappers'], 1)

    def test_reversed_selections_same_native_bytes_and_missing_wrapper(self):
        other = nbib_intake.prepare(self.base, self.native, 'local-secondary', 'supplied synthetic time')
        current = self.imported(self.protocol, other['csv_intake'], 'fictional-B')
        selected = self.bindings + [dict(import_index=1, nbib_artifact=other)]
        raw = self.build(current, selected)
        self.assertEqual(raw, self.build(current, list(reversed(selected))))
        self.assertEqual(bundle.verify_bundle(raw)['covered_import_indices'], [0, 1])
        self.assertEqual(bundle.verify_bundle(self.build(current))['uncovered_import_indices'], [1])
        self.assertEqual(other['source_export']['sha256'], self.wrapper['source_export']['sha256'])
        with self.assertRaises(ValueError):
            self.build(current, [dict(import_index=1, nbib_artifact=self.wrapper)])

    def test_later_enrichment_uses_historical_common_base(self):
        current = copy.deepcopy(self.protocol)
        current['version'] = 'fictional-enriched-v2'
        current['screening'] = [dict(record_id='fictional-A', decision='include', reason='Fictional eligibility choice')]
        current['gaps'] = [dict(question='Fictional document review?', evidence_ids=[], deliverable='Fictional note',
            acceptance_criterion='Explicit source inspection', context='Fictional only', work_type='source_review',
            source_refs=[dict(kind='record', record_id='fictional-A')])]
        self.assertNotEqual(current, self.wrapper['protocol_snapshot'])
        checked = bundle.verify_bundle(self.build(current))
        self.assertTrue(checked['valid'])
        self.assertEqual(current['bibliographic_imports']['base_protocol'], self.base)

    def test_invalid_selections_and_schema_types_rejected(self):
        invalid = [None, {}, (), [], [self.bindings[0], self.bindings[0]],
                   [dict(import_index=0)], [dict(import_index=0, nbib_artifact=self.wrapper, extra=True)],
                   [dict(import_index=0, nbib_artifact=[])]]
        invalid += [[dict(import_index=index, nbib_artifact=self.wrapper)]
                    for index in [True, False, 0.0, -1, 1, '0', None, [], {}]]
        for selected in invalid:
            with self.subTest(selected=str(selected)[:100]), self.assertRaises(ValueError):
                bundle.build_bundle(encoded(self.protocol), selected)
        with patch.object(bundle, 'MAX_BINDINGS', 0), self.assertRaises(ValueError): self.build()

    def test_unmatched_intake_same_search_and_changed_timestamp_fail(self):
        alternatives = [nbib_intake.prepare(self.base, self.native, 'local-primary', 'different time')]
        changed = copy.deepcopy(self.base); changed['question'] = 'Different fictional question?'
        alternatives.append(nbib_intake.prepare(changed, self.native, 'local-primary', 'supplied synthetic time'))
        alternatives.append(nbib_intake.prepare(self.base, self.native + b'\n', 'local-primary', 'supplied synthetic time'))
        for artifact in alternatives:
            self.assertTrue(nbib_intake.verify(artifact)['valid'])
            with self.subTest(hash=artifact['review_target']['target_sha256']), self.assertRaises(ValueError):
                self.build(bindings=[dict(import_index=0, nbib_artifact=artifact)])

    def test_entire_protocol_and_historical_receipts_validated(self):
        mutations = [lambda p: p['bibliographic_imports']['base_protocol'].update(question='changed'),
                     lambda p: p['bibliographic_imports']['imports'][0].update(sha256='0'*64),
                     lambda p: p.update(reports=[dict(report_id='bad', record_ids=['unknown'], retrieval='retrieved',
                                                     decision='include', study_id='fictional-study')])]
        for mutate in mutations:
            current = copy.deepcopy(self.protocol); mutate(current)
            with self.assertRaises(ValueError): self.build(current)
        with self.assertRaises(ValueError): self.build(self.base)
        for raw in [b'null', b'[]', b'{}', b'\xff', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError): bundle.build_bundle(raw, self.bindings)
        for raw in [None, '', bytearray(encoded(self.protocol))]:
            with self.assertRaises(ValueError): bundle.build_bundle(raw, self.bindings)

    def test_native_tampering_rejected_even_with_resealed_outer_hashes(self):
        entries = self.payloads()
        wrapper = json.loads(entries['native/import-000000.json'])
        wrapper['parsed_export']['records'][0]['fields'][1]['value_lines'] = ['Forged value']
        wrapper['review_target']['target_sha256'] = nbib_intake.digest({k:v for k,v in wrapper.items() if k != 'review_target'})
        entries['native/import-000000.json'] = encoded(wrapper)
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))

    def test_derived_payload_tampering_and_unknown_keys_rejected(self):
        original = self.payloads()
        for path in ['summary.txt', 'bindings.json', 'manifest.json']:
            entries = copy.deepcopy(original)
            if path == 'summary.txt': entries[path] = b'Complete verified census\n'
            else:
                value = json.loads(entries[path]); value['unrecognized_approval'] = True; entries[path] = encoded(value)
            with self.subTest(path=path), self.assertRaises(ValueError):
                bundle.verify_bundle(self.repack(self.reseal(entries)))
        for mutation in [lambda b: b['imports'][0].update(receipt_sha256='0'*64),
                         lambda b: b['imports'][0].update(canonical_intake_sha256='0'*64),
                         lambda b: b['imports'][0].update(import_index=True),
                         lambda b: b.update(covered_import_indices=[]),
                         lambda b: b.update(census_claim='ESTABLISHED')]:
            entries = copy.deepcopy(original); value = json.loads(entries['bindings.json']); mutation(value)
            entries['bindings.json'] = encoded(value)
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))

    def test_manifest_engine_and_schema_drift_rejected(self):
        for mutation in [lambda m: m.update(schema_version=True), lambda m: m.update(schema_version=1.0),
                         lambda m: m['engine_sha256'].update({'collection_bundle.py':'0'*64}),
                         lambda m: m['files'][0].update(bytes=True)]:
            entries = self.payloads(); value = json.loads(entries['manifest.json']); mutation(value)
            entries['manifest.json'] = encoded(value)
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries))

    def test_archive_allowlist_duplicates_and_noncanonical_metadata(self):
        entries = self.payloads()
        for name in ['../outside', '/absolute', 'native/../escape', 'unexpected', 'directory/']:
            changed = dict(entries); changed[name] = b'never extracted'
            with self.subTest(name=name), self.assertRaises(ValueError): bundle.verify_bundle(self.repack(changed))
        missing = dict(entries); missing.pop('native/import-000000.json')
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(missing))
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries, duplicates=[('bindings.json', entries['bindings.json'])]))
        for override in [dict(create_system=0), dict(date_time=(2020,1,1,0,0,0)),
                         dict(external_attr=(stat.S_IFLNK | 0o777) << 16), dict(comment=b'changed')]:
            with self.subTest(override=override), self.assertRaises(ValueError):
                bundle.verify_bundle(self.repack(entries, overrides={'bindings.json':override}))
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries, compression=zipfile.ZIP_DEFLATED))
        raw = self.build()
        for value in [b'prefix'+raw, raw+b'trailer', raw[:-1], b'not a ZIP', b'', None, bytearray(raw)]:
            with self.subTest(kind=type(value)), self.assertRaises((ValueError, zipfile.BadZipFile)):
                bundle.verify_bundle(value)

    def test_nested_research_archive_tampering_rejected(self):
        entries = self.payloads()
        with zipfile.ZipFile(io.BytesIO(entries['research.zip'])) as nested:
            data = {name:nested.read(name) for name in nested.namelist()}
        data['summary.md'] = b'Forged ordinary summary'
        manifest = json.loads(data['manifest.json'])
        for row in manifest['files']:
            if row['path'] == 'summary.md': row.update(bytes=len(data['summary.md']),sha256=hashlib.sha256(data['summary.md']).hexdigest())
        data['manifest.json'] = encoded(manifest)
        entries['research.zip'] = self.repack(data)
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))

    def test_nested_archive_entry_attacks_and_no_extraction(self):
        original = self.payloads()
        with zipfile.ZipFile(io.BytesIO(original['research.zip'])) as nested:
            data = {name:nested.read(name) for name in nested.namelist()}
        bad = dict(data); bad['../outside'] = b'never extracted'
        attacks = [self.repack(bad), self.repack(data, duplicates=[('protocol.json',data['protocol.json'])]),
                   self.repack(data, compression=zipfile.ZIP_DEFLATED),
                   self.repack(data, overrides={'protocol.json':dict(external_attr=(stat.S_IFLNK|0o777)<<16)})]
        for nested in attacks:
            entries = dict(original); entries['research.zip'] = nested
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))
        with patch.object(zipfile.ZipFile,'extract',side_effect=AssertionError('must not extract')), \
             patch.object(zipfile.ZipFile,'extractall',side_effect=AssertionError('must not extract')):
            self.assertTrue(bundle.verify_bundle(self.build())['valid'])

    def test_encrypted_crc_and_declared_size_attacks_fail_closed(self):
        raw = self.build()
        # Mutate the first local and central headers directly; ZipFile.writestr
        # deliberately clears encryption flags and cannot make this fixture.
        encrypted = bytearray(raw)
        local = encrypted.index(b'PK\x03\x04'); central = encrypted.index(b'PK\x01\x02')
        for offset in [local+6,central+8]:
            flags = struct.unpack_from('<H',encrypted,offset)[0]
            struct.pack_into('<H',encrypted,offset,flags|1)
        with self.assertRaises(ValueError): bundle.verify_bundle(bytes(encrypted))
        oversized = bytearray(raw)
        for offset in [central+20,central+24]: struct.pack_into('<I',oversized,offset,50_000_001)
        with self.assertRaises(ValueError): bundle.verify_bundle(bytes(oversized))
        bad_crc = bytearray(raw)
        name_len,extra_len=struct.unpack_from('<HH',bad_crc,local+26)
        bad_crc[local+30+name_len+extra_len] ^= 1
        with self.assertRaises(ValueError): bundle.verify_bundle(bytes(bad_crc))

    def test_inclusive_size_bound_and_no_output_on_overflow(self):
        raw = self.build()
        with patch.object(bundle, 'MAX_BUNDLE_BYTES', len(raw)):
            self.assertEqual(self.build(), raw)
            self.assertTrue(bundle.verify_bundle(raw)['valid'])
        with patch.object(bundle, 'MAX_BUNDLE_BYTES', len(raw)-1):
            with self.assertRaises(ValueError): self.build()
            with self.assertRaises(ValueError): bundle.verify_bundle(raw)
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'p', Path(folder)/'out'
            source.write_bytes(encoded(self.protocol))
            with patch.object(bundle, 'MAX_BUNDLE_BYTES', 1), self.assertRaises(ValueError):
                bundle.create(source, output, self.bindings)
            self.assertFalse(output.exists())

    def test_platform_metadata_fixed_and_wrapper_key_order_normalized(self):
        baseline = self.build()
        with patch('zipfile.sys.platform', 'win32'):
            self.assertEqual(self.build(), baseline)
        reversed_wrapper = dict(reversed(list(self.wrapper.items())))
        self.assertEqual(self.build(bindings=[dict(import_index=0, nbib_artifact=reversed_wrapper)]), baseline)
        with zipfile.ZipFile(io.BytesIO(baseline)) as archive:
            self.assertTrue(all(e.create_system == 3 and e.compress_type == zipfile.ZIP_STORED for e in archive.infolist()))
        compact = json.dumps(self.protocol,separators=(',',':')).encode()
        other = bundle.build_bundle(compact,self.bindings)
        self.assertNotEqual(other, baseline)
        self.assertTrue(bundle.verify_bundle(other)['valid'])

    def test_cli_roundtrip_and_exclusive_output_with_equals_in_input_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source=root/'protocol.json'; native=root/'native=one.json'; output=root/'out.zip'
            source.write_bytes(encoded(self.protocol)); native.write_bytes(encoded(self.wrapper))
            args = ['create',source,output,'--nbib','0='+str(native)]
            result = self.invoke(*args)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])
            raw=output.read_bytes(); self.assertEqual(raw,self.build())
            self.assertNotIn(str(root).encode(),raw)
            verified=self.invoke('verify',output,'--text')
            self.assertEqual(verified.returncode,0,verified.stderr)
            self.assertIn(b'NOT_ESTABLISHED',verified.stdout)
            self.assertNotEqual(self.invoke(*args).returncode,0)
            self.assertEqual(output.read_bytes(),raw)
            target=root/'unchanged'; target.write_bytes(b'unchanged'); link=root/'link'
            try: link.symlink_to(target)
            except (OSError,NotImplementedError): pass
            else:
                self.assertNotEqual(self.invoke('create',source,link,'--nbib','0='+str(native)).returncode,0)
                self.assertEqual(target.read_bytes(),b'unchanged')

    def test_cli_invalid_input_no_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'protocol'; native=root/'native'; output=root/'out'
            source.write_bytes(encoded(self.protocol)); native.write_bytes(encoded(self.wrapper))
            for selection in ['-1='+str(native),'1.0='+str(native),'true='+str(native),'none',
                              '1='+str(native),'0='+str(root/'absent')]:
                result=self.invoke('create',source,output,'--nbib',selection)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(output.exists())
                self.assertNotIn(b'Traceback',result.stderr)
            for raw in [b'\xff', b'{}', b'null', b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}']:
                native.write_bytes(raw)
                result=self.invoke('create',source,output,'--nbib','0='+str(native))
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(output.exists())
                self.assertNotIn(b'Traceback',result.stderr)
            malformed=root/'bad.zip';malformed.write_bytes(b'not ZIP')
            checked=self.invoke('verify',malformed)
            self.assertNotEqual(checked.returncode,0)
            self.assertNotIn(b'Traceback',checked.stderr)

    def test_cli_stdout_preflight_prevents_partial_creation(self):
        raw=self.build()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'protocol'; native=root/'native'; output=root/'out'
            source.write_bytes(encoded(self.protocol)); native.write_bytes(encoded(self.wrapper))
            argv=['collection_bundle.py','create',str(source),str(output),'--nbib','0='+str(native),'--text']
            for render in [lambda _: (_ for _ in ()).throw(ValueError('synthetic rendering failure')),
                           lambda _: '\ud800']:
                with patch.object(sys,'argv',argv), patch.object(bundle,'configure_utf8_stdio'), \
                     patch.object(sys,'stdout',io.StringIO()), patch.object(sys,'stderr',io.StringIO()), \
                     patch.object(bundle,'build_bundle',return_value=raw), \
                     patch.object(bundle,'render_text',side_effect=render):
                    with self.assertRaises(SystemExit): bundle.main()
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
