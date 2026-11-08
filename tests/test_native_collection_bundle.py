"""Synthetic explicitly typed native archives: exact originals, import binding and hostile ZIPs."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import socket
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
import native_collection_bundle as bundle
import ris_intake
import nbib_intake as single_nbib
import collection_bundle
import batch_collection_bundle
from evidence_workflow import run
import nbib_batch_intake as nbib_intake
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


class NativeCollectionBundleTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / 'examples/bibliographic-base.json').read_bytes())
        self.native = ('\ufeffPMID- 999999999999991\r\nTI  - Fictional 합성\r\n'
                       '      folded title\r\nAU  - Fictional A\r\nAU  - Fictional B\r\n\r\n').encode()
        self.sources = [dict(source_id='first synthetic', raw=self.native),
                        dict(source_id='second synthetic', raw=b'PMID- 999999999999992\nTI  - Fictional other\n')]
        self.wrapper = nbib_intake.prepare(self.base, self.sources, 'local-primary', 'supplied synthetic time')
        self.protocol = self.imported(self.base, self.wrapper['csv_intake'], 'fictional-A')
        self.bindings = [dict(import_index=0, format='nbib_batch', artifact=self.wrapper)]

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
        return subprocess.run([sys.executable, str(ROOT / 'native_collection_bundle.py'), *map(str, args)],
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
                                        'native/import-000000.json',
                                        'native/import-000000/source-000000.nbib',
                                        'native/import-000000/source-000001.nbib'})
        self.assertEqual(entries['research.zip'], research_bundle.build_bundle(encoded(self.protocol)))
        self.assertTrue(research_bundle.verify(io.BytesIO(entries['research.zip']))['valid'])
        with zipfile.ZipFile(io.BytesIO(entries['research.zip'])) as ordinary:
            self.assertEqual(ordinary.read('protocol.json'), encoded(self.protocol))
        retained = json.loads(entries['native/import-000000.json'])
        self.assertEqual(retained, self.wrapper)
        for index, source in enumerate(self.sources):
            self.assertEqual(entries[f'native/import-000000/source-{index:06d}.nbib'], source['raw'])
            self.assertEqual(retained['source_exports'][index]['source_export']['text'].encode(), source['raw'])
            for record in retained['source_exports'][index]['parsed_export']['records']:
                span = record['source_span']
                self.assertEqual(source['raw'][span['byte_start']:span['byte_end']], record['raw_text'].encode())
        self.assertTrue(nbib_intake.verify(retained)['valid'])
        self.assertEqual(run(self.protocol)['flow']['pending'], 2)
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
        self.assertEqual(row['native_sources'], [dict(source_index=i, source_id=s['source_id'],
            native_export_sha256=hashlib.sha256(s['raw']).hexdigest(), native_export_bytes=len(s['raw']),
            record_rows=1, native_archive_path=f'native/import-000000/source-{i:06d}.nbib')
            for i, s in enumerate(self.sources)])
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
        other = nbib_intake.prepare(self.base, self.sources, 'local-secondary', 'supplied synthetic time')
        current = self.imported(self.protocol, other['csv_intake'], 'fictional-B')
        selected = self.bindings + [dict(import_index=1, format='nbib_batch', artifact=other)]
        raw = self.build(current, selected)
        self.assertEqual(raw, self.build(current, list(reversed(selected))))
        self.assertEqual(bundle.verify_bundle(raw)['covered_import_indices'], [0, 1])
        self.assertEqual(bundle.verify_bundle(self.build(current))['uncovered_import_indices'], [1])
        self.assertEqual(other['source_exports'][0]['source_export']['sha256'], self.wrapper['source_exports'][0]['source_export']['sha256'])
        with self.assertRaises(ValueError):
            self.build(current, [dict(import_index=1, format='nbib_batch', artifact=self.wrapper)])

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
                   [dict(import_index=0)], [dict(import_index=0, format='nbib_batch', artifact=self.wrapper, extra=True)],
                   [dict(import_index=0, format='nbib_batch', artifact=[])]]
        invalid += [[dict(import_index=index, format='nbib_batch', artifact=self.wrapper)]
                    for index in [True, False, 0.0, -1, 1, '0', None, [], {}]]
        for selected in invalid:
            with self.subTest(selected=str(selected)[:100]), self.assertRaises(ValueError):
                bundle.build_bundle(encoded(self.protocol), selected)
        with patch.object(bundle, 'MAX_BINDINGS', 0), self.assertRaises(ValueError): self.build()

    def test_unmatched_intake_same_search_and_changed_timestamp_fail(self):
        alternatives = [nbib_intake.prepare(self.base, self.sources, 'local-primary', 'different time')]
        changed = copy.deepcopy(self.base); changed['question'] = 'Different fictional question?'
        alternatives.append(nbib_intake.prepare(changed, self.sources, 'local-primary', 'supplied synthetic time'))
        alternatives.append(nbib_intake.prepare(self.base, [dict(source_id='first synthetic', raw=self.native + b'\n')], 'local-primary', 'supplied synthetic time'))
        for artifact in alternatives:
            self.assertTrue(nbib_intake.verify(artifact)['valid'])
            with self.subTest(hash=artifact['review_target']['target_sha256']), self.assertRaises(ValueError):
                self.build(bindings=[dict(import_index=0, format='nbib_batch', artifact=artifact)])

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
        wrapper['source_exports'][0]['parsed_export']['records'][0]['fields'][1]['value_lines'] = ['Forged value']
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
                         lambda m: m['engine_sha256'].update({'native_collection_bundle.py':'0'*64}),
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
             patch.object(zipfile.ZipFile,'extractall',side_effect=AssertionError('must not extract')), \
             patch.object(socket, 'create_connection', side_effect=AssertionError('must stay offline')):
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
        self.assertEqual(self.build(bindings=[dict(import_index=0, format='nbib_batch', artifact=reversed_wrapper)]), baseline)
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
            args = ['create',source,output,'--nbib-batch','0='+str(native)]
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
                self.assertNotEqual(self.invoke('create',source,link,'--nbib-batch','0='+str(native)).returncode,0)
                self.assertEqual(target.read_bytes(),b'unchanged')

    def test_cli_invalid_input_no_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'protocol'; native=root/'native'; output=root/'out'
            source.write_bytes(encoded(self.protocol)); native.write_bytes(encoded(self.wrapper))
            for selection in ['-1='+str(native),'1.0='+str(native),'true='+str(native),'none',
                              '1='+str(native),'0='+str(root/'absent')]:
                result=self.invoke('create',source,output,'--nbib-batch',selection)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(output.exists())
                self.assertNotIn(b'Traceback',result.stderr)
            for raw in [b'\xff', b'{}', b'null', b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}']:
                native.write_bytes(raw)
                result=self.invoke('create',source,output,'--nbib-batch','0='+str(native))
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
            argv=['native_collection_bundle.py','create',str(source),str(output),'--nbib-batch','0='+str(native),'--text']
            for render in [lambda _: (_ for _ in ()).throw(ValueError('synthetic rendering failure')),
                           lambda _: '\ud800']:
                with patch.object(sys,'argv',argv), patch.object(bundle,'configure_utf8_stdio'), \
                     patch.object(sys,'stdout',io.StringIO()), patch.object(sys,'stderr',io.StringIO()), \
                     patch.object(bundle,'build_bundle',return_value=raw), \
                     patch.object(bundle,'render_text',side_effect=render):
                    with self.assertRaises(SystemExit): bundle.main()
                self.assertFalse(output.exists())


    def test_identical_sources_retained_as_separate_original_files(self):
        sources = [dict(source_id='first copy', raw=self.native),
                   dict(source_id='second copy', raw=self.native)]
        wrapper = nbib_intake.prepare(self.base, sources, 'local-primary', 'synthetic time')
        protocol = self.imported(self.base, wrapper['csv_intake'], 'fictional-copy')
        raw = self.build(protocol, [dict(import_index=0, format='nbib_batch', artifact=wrapper)])
        entries = self.payloads(raw)
        rows = json.loads(entries['bindings.json'])['imports'][0]['native_sources']
        self.assertEqual(len(rows), 2)
        self.assertEqual([r['source_id'] for r in rows], ['first copy', 'second copy'])
        self.assertNotEqual(rows[0]['native_archive_path'], rows[1]['native_archive_path'])
        self.assertEqual(rows[0]['native_export_sha256'], rows[1]['native_export_sha256'])
        for row in rows:
            self.assertEqual(entries[row['native_archive_path']], self.native)
        self.assertEqual(bundle.verify_bundle(raw)['bound_native_sources'], 2)

    def test_original_source_tamper_swap_missing_extra_and_paths_rejected(self):
        original = self.payloads()
        a = 'native/import-000000/source-000000.nbib'
        b = 'native/import-000000/source-000001.nbib'
        attacks = []
        altered = dict(original); altered[a] += b'\n'; attacks.append(altered)
        swapped = dict(original); swapped[a], swapped[b] = swapped[b], swapped[a]; attacks.append(swapped)
        missing = dict(original); del missing[a]; attacks.append(missing)
        for path in ['native/import-000000/source-000002.nbib',
                     'native/import-000001/source-000000.nbib',
                     'native/import-000000/source-0.nbib', 'native/import-000000/../source-000000.nbib']:
            renamed = dict(original); renamed[path] = renamed.pop(a); attacks.append(renamed)
        for entries in attacks:
            with self.subTest(names=list(entries)), self.assertRaises(ValueError):
                bundle.verify_bundle(self.repack(self.reseal(entries)))
        for mutate in [lambda row: row.update(source_index=True),
                       lambda row: row.update(source_index=1),
                       lambda row: row.update(source_id='different'),
                       lambda row: row.update(native_export_sha256='0'*64),
                       lambda row: row.update(native_export_bytes=True),
                       lambda row: row.update(record_rows=2),
                       lambda row: row.update(native_archive_path=b)]:
            entries = dict(original)
            document = json.loads(entries['bindings.json'])
            mutate(document['imports'][0]['native_sources'][0])
            entries['bindings.json'] = encoded(document)
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))

    def test_source_order_in_wrapper_and_binding_is_validated(self):
        entries = self.payloads()
        wrapper = json.loads(entries['native/import-000000.json'])
        wrapper['source_exports'].reverse()
        wrapper['review_target']['target_sha256'] = nbib_intake.digest(
            {key: value for key, value in wrapper.items() if key != 'review_target'})
        entries['native/import-000000.json'] = encoded(wrapper)
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))
        entries = self.payloads()
        bindings = json.loads(entries['bindings.json'])
        bindings['imports'][0]['native_sources'].reverse()
        entries['bindings.json'] = encoded(bindings)
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))

    def test_unselected_native_import_is_not_inferred_from_receipt(self):
        other = nbib_intake.prepare(self.base, self.sources, 'local-secondary', 'supplied synthetic time')
        current = self.imported(self.protocol, other['csv_intake'], 'fictional-B')
        checked = bundle.verify_bundle(self.build(current))
        self.assertEqual(checked['uncovered_import_indices'], [1])
        self.assertEqual(checked['bound_native_wrappers'], 1)
        self.assertEqual(checked['bound_native_sources'], 2)
        entries = self.payloads(self.build(current))
        self.assertFalse(any(name.startswith('native/import-000001') for name in entries))

    def test_strict_container_subclasses_rejected(self):
        class ListSubclass(list): pass
        class DictSubclass(dict): pass
        for bindings in [ListSubclass(self.bindings), [DictSubclass(self.bindings[0])],
                         [dict(import_index=0, format='nbib_batch', artifact=DictSubclass(self.wrapper))]]:
            with self.assertRaises(ValueError): self.build(bindings=bindings)

    def test_aggregate_source_quota_and_original_wrapper_limits(self):
        self.assertEqual(bundle.MAX_BINDINGS, 100)
        self.assertEqual(bundle.MAX_NATIVE_SOURCES, 10_000)
        self.assertEqual(bundle.MAX_BUNDLE_BYTES, 50_000_000)
        with patch.object(bundle, 'MAX_NATIVE_SOURCES', 2):
            self.assertTrue(bundle.verify_bundle(self.build())['valid'])
        with patch.object(bundle, 'MAX_NATIVE_SOURCES', 1), self.assertRaises(ValueError): self.build()
        other = nbib_intake.prepare(self.base, self.sources, 'local-secondary', 'synthetic time')
        current = self.imported(self.protocol, other['csv_intake'], 'fictional-B')
        selections = self.bindings + [dict(import_index=1, format='nbib_batch', artifact=other)]
        with patch.object(bundle, 'MAX_NATIVE_SOURCES', 4):
            self.assertEqual(bundle.verify_bundle(self.build(current, selections))['bound_native_sources'], 4)
        with patch.object(bundle, 'MAX_NATIVE_SOURCES', 3), self.assertRaises(ValueError):
            self.build(current, selections)
        with patch.object(nbib_intake, 'MAX_SOURCES', 1), self.assertRaises(ValueError): self.build()
        with patch.object(nbib_intake, 'MAX_TOTAL_EXPORT_BYTES', 1), self.assertRaises(ValueError): self.build()
        with patch.object(nbib_intake, 'verify', wraps=nbib_intake.verify) as validate:
            self.build()
            self.assertTrue(validate.called)

    def test_engine_fingerprints_cover_batch_intake_and_bundle(self):
        hashes = bundle.implementation_hashes()
        for name in ['native_collection_bundle.py', 'nbib_batch_intake.py']:
            self.assertEqual(hashes[name], hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        for name in ['native_collection_bundle.py', 'nbib_batch_intake.py']:
            entries = self.payloads()
            manifest = json.loads(entries['manifest.json'])
            manifest['engine_sha256'][name] = '0'*64
            entries['manifest.json'] = encoded(manifest)
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries))

    def test_create_api_roundtrip_no_overwrite_and_summary_preflight(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'protocol'; output = root/'bundle'
            source.write_bytes(encoded(self.protocol))
            result = bundle.create(source, output, self.bindings)
            self.assertEqual(output.read_bytes(), self.build())
            self.assertEqual(result, bundle.verify_bundle(output.read_bytes()))
            with self.assertRaises((ValueError, OSError)): bundle.create(source, output, self.bindings)
            output.unlink()
            with patch.object(bundle, '_built_summary', return_value={'bad': '\ud800'}):
                with self.assertRaises((ValueError, UnicodeError)): bundle.create(source, output, self.bindings)
            self.assertFalse(output.exists())

    def test_dangling_output_entry_rejected_without_following_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'protocol'; output = root/'bundle'; target = root/'absent'
            source.write_bytes(encoded(self.protocol))
            try: output.symlink_to(target)
            except (OSError, NotImplementedError): self.skipTest('symlink unavailable')
            with self.assertRaises((ValueError, OSError)): bundle.create(source, output, self.bindings)
            self.assertTrue(output.is_symlink())
            self.assertFalse(target.exists())
            # Windows may follow a dangling link even in exclusive-create mode.
            # The entry check must prevent opening it on every platform.
            with patch.object(Path, 'open', side_effect=AssertionError('must reject before open')):
                with self.assertRaises((ValueError, OSError)): bundle._write_new(output, b'synthetic')

    def test_cli_json_summary_preflight_prevents_output(self):
        raw = self.build()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'protocol'; wrapper = root/'wrapper'; output = root/'out'
            source.write_bytes(encoded(self.protocol)); wrapper.write_bytes(encoded(self.wrapper))
            argv = ['native_collection_bundle.py', 'create', str(source), str(output), '--nbib-batch', '0='+str(wrapper)]
            for invalid in [{'bad': '\ud800'}, {'bad': float('nan')}, {'bad': object()}]:
                with patch.object(sys, 'argv', argv), patch.object(bundle, 'configure_utf8_stdio'), \
                     patch.object(sys, 'stdout', io.StringIO()), patch.object(sys, 'stderr', io.StringIO()), \
                     patch.object(bundle, 'build_bundle', return_value=raw), \
                     patch.object(bundle, '_built_summary', return_value=invalid):
                    with self.assertRaises(SystemExit): bundle.main()
                self.assertFalse(output.exists())

    def test_cli_both_rendering_modes_and_repeated_bindings(self):
        other = nbib_intake.prepare(self.base, self.sources, 'local-secondary', 'synthetic time')
        current = self.imported(self.protocol, other['csv_intake'], 'fictional-B')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); protocol = root/'p'; first = root/'a'; second = root/'b'
            protocol.write_bytes(encoded(current)); first.write_bytes(encoded(self.wrapper)); second.write_bytes(encoded(other))
            for mode in [[], ['--text']]:
                output = root/('bundle'+str(len(mode)))
                result = self.invoke('create', protocol, output, '--nbib-batch', '1='+str(second),
                                     '--nbib-batch', '0='+str(first), *mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                if not mode: self.assertEqual(json.loads(result.stdout)['bound_native_sources'], 4)
                else: self.assertIn(b'NOT_ESTABLISHED', result.stdout)
                checked = self.invoke('verify', output, *mode)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                if not mode: self.assertTrue(json.loads(checked.stdout)['valid'])
                self.assertEqual(bundle.verify_bundle(output.read_bytes())['covered_import_indices'], [0, 1])


    def test_identical_canonical_repacking_is_valid(self):
        raw = self.build()
        repacked = self.repack(self.payloads(raw))
        self.assertEqual(repacked, raw)
        self.assertTrue(bundle.verify_bundle(repacked)['valid'])

    def mixed_project(self):
        base = copy.deepcopy(self.base)
        for index in range(2):
            base['search_plan'].append(dict(search_id=f'fictional-extra-{index}',
                source='synthetic-local-export', query=f'fictional query {index}', window='2020-2026'))
        ris_raw = ('\ufeff\r\nTY  - JOUR\r\nTI  - Fictional 합성\nDO  - 10.fictional/repeated\r'
                   'DO  - 10.fictional/conflict\nL1  - file:///never/open\nER  -\r\n\r\n'
                   'TY  - GEN\nTI  - Identifier-free fictional occurrence\nER  -').encode()
        single_raw = b'PMID- 999999999999993\r\nTI  - Fictional single\r\n\r\n'
        sources = [dict(source_id='../unopened=first', raw=self.native),
                   dict(source_id='second identical copy', raw=self.native)]
        wrappers = [('ris', ris_intake.prepare(base, ris_raw, 'local-primary', 'supplied RIS time')),
                    ('nbib', single_nbib.prepare(base, single_raw, 'local-secondary', 'supplied NBIB time')),
                    ('nbib_batch', nbib_intake.prepare(base, sources, 'fictional-extra-0', 'supplied batch time'))]
        current = base
        for index, (_, wrapper) in enumerate(wrappers):
            current = self.imported(current, wrapper['csv_intake'], f'fictional-mixed-{index}-')
        csv_intake = bibliographic_intake.prepare(base, b'record_id,source_locator\nCSV,synthetic:unopened\n',
                                                  'fictional-extra-1', 'supplied CSV time')
        current = self.imported(current, csv_intake, 'fictional-CSV')
        bindings = [dict(import_index=i, format=kind, artifact=artifact)
                    for i, (kind, artifact) in enumerate(wrappers)]
        return base, current, bindings, [ris_raw, single_raw, self.native, self.native]

    def test_ris_single_nbib_batch_and_csv_in_one_portable_archive(self):
        base, protocol, bindings, originals = self.mixed_project()
        raw = self.build(protocol, bindings)
        self.assertEqual(raw, self.build(protocol, list(reversed(bindings))))
        checked = bundle.verify_bundle(raw)
        self.assertEqual(checked['total_imports'], 4)
        self.assertEqual(checked['bound_native_wrappers'], 3)
        self.assertEqual(checked['bound_wrapper_formats'], {'ris':1, 'nbib':1, 'nbib_batch':1})
        self.assertEqual(checked['bound_native_sources'], 4)
        self.assertEqual(checked['covered_import_indices'], [0,1,2])
        self.assertEqual(checked['uncovered_import_indices'], [3])
        entries = self.payloads(raw)
        paths = ['native/import-000000/source-000000.ris', 'native/import-000001/source-000000.nbib',
                 'native/import-000002/source-000000.nbib', 'native/import-000002/source-000001.nbib']
        self.assertEqual([entries[path] for path in paths], originals)
        rows = json.loads(entries['bindings.json'])['imports']
        self.assertEqual([row.get('format') for row in rows], ['ris','nbib','nbib_batch',None])
        for row in rows[:2]: self.assertNotIn('source_id', row['native_sources'][0])
        self.assertEqual(rows[2]['native_sources'][0]['source_id'], '../unopened=first')
        self.assertEqual(rows[3]['status'], 'NO_NATIVE_WRAPPER_SUPPLIED')
        self.assertNotIn('native_sources', rows[3])
        self.assertEqual(protocol['bibliographic_imports']['base_protocol'], base)
        self.assertEqual(protocol['screening'], [])
        self.assertTrue(all(not search['complete'] for search in protocol['searches']))
        self.assertEqual(protocol['evidence'], [])
        self.assertNotIn('../unopened=first', '\n'.join(entries))
        for index, binding in enumerate(bindings):
            row = rows[index]
            self.assertEqual(row['canonical_intake_sha256'], ris_intake.digest(binding['artifact']['csv_intake']))
            self.assertEqual(row['canonical_wrapper_sha256'], ris_intake.digest(binding['artifact']))

    def test_each_single_format_roundtrips_and_dispatches_only_to_selected_verifier(self):
        _, protocol, bindings, _ = self.mixed_project()
        for binding in bindings:
            with self.subTest(kind=binding['format']):
                with patch.object(bundle.FORMATS[binding['format']], 'verify',
                                  wraps=bundle.FORMATS[binding['format']].verify) as validate:
                    raw = self.build(protocol, [binding])
                    checked = bundle.verify_bundle(raw)
                    self.assertGreaterEqual(validate.call_count, 2)
                self.assertEqual(checked['covered_import_indices'], [binding['import_index']])
                rows = json.loads(self.payloads(raw)['bindings.json'])['imports']
                for index, row in enumerate(rows):
                    if index != binding['import_index']:
                        self.assertNotIn('format', row)
                        self.assertNotIn('native_sources', row)

    def test_all_six_wrong_format_wrapper_pairings_fail_closed(self):
        _, protocol, bindings, _ = self.mixed_project()
        for binding in bindings:
            for kind in bundle.FORMATS:
                if kind != binding['format']:
                    wrong = dict(binding, format=kind)
                    with self.subTest(actual=binding['format'], supplied=kind), self.assertRaises(ValueError):
                        self.build(protocol, [wrong])

    def test_strict_format_selection_and_cross_flag_duplicate_indices(self):
        _, protocol, bindings, _ = self.mixed_project()
        class TextSubclass(str): pass
        for kind in ['RIS', 'csv', 'auto', '../ris_intake.py', '', None, True, 0, [], {}, TextSubclass('ris')]:
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.build(protocol, [dict(bindings[0], format=kind)])
        with self.assertRaises(ValueError):
            self.build(protocol, [bindings[0], dict(bindings[1], import_index=0)])
        for mutation in [lambda b: b.pop('format'), lambda b: b.update(guess_format=True)]:
            binding = dict(bindings[0]); mutation(binding)
            with self.assertRaises(ValueError): self.build(protocol, [binding])

    def test_ris_original_bytes_and_parsed_data_tampering_rejected_when_resealed(self):
        _, protocol, bindings, _ = self.mixed_project()
        original = self.payloads(self.build(protocol, [bindings[0]]))
        for mutate in [lambda w: w['parsed_export']['records'].reverse(),
                       lambda w: w['source_export'].update(text=w['source_export']['text'].replace('\r\n','\n')),
                       lambda w: w['csv_intake']['search_request'].update(searched_at='forged'),
                       lambda w: w.update(mode='local_nbib_preparation'),
                       lambda w: w.update(unknown=True),
                       lambda w: w['engine_sha256'].update({'ris_export_parser.py':'0'*64})]:
            entries = dict(original)
            wrapper = json.loads(entries['native/import-000000.json']); mutate(wrapper)
            wrapper['review_target']['target_sha256'] = ris_intake.digest({k:v for k,v in wrapper.items() if k != 'review_target'})
            entries['native/import-000000.json'] = encoded(wrapper)
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))
        entries = dict(original)
        entries['native/import-000000/source-000000.ris'] += b'\n'
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))

    def test_type_source_count_extension_and_format_claim_forgery_rejected(self):
        _, protocol, bindings, _ = self.mixed_project()
        original = self.payloads(self.build(protocol, bindings))
        mutations = [lambda b: b['imports'][0].update(format='nbib'),
                     lambda b: b['imports'][1].update(format='nbib_batch'),
                     lambda b: b['imports'][2].update(format='nbib'),
                     lambda b: b['imports'][0].update(format=[]),
                     lambda b: b['imports'][0].update(source_count=True),
                     lambda b: b['imports'][0].update(record_rows=99),
                     lambda b: b['imports'][0]['native_sources'].append(copy.deepcopy(b['imports'][0]['native_sources'][0])),
                     lambda b: b['imports'][0]['native_sources'][0].update(source_id='invented'),
                     lambda b: b['imports'][0]['native_sources'][0].update(native_archive_path='native/import-000000/source-000000.nbib'),
                     lambda b: b['imports'][3].update(format='csv')]
        for mutate in mutations:
            entries = dict(original); document = json.loads(entries['bindings.json']); mutate(document)
            entries['bindings.json'] = encoded(document)
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))
        for replacement in ['native/import-000000/source-000000.nbib',
                            'native/import-000000/source-000001.ris', 'native/import-000003/source-000000.ris']:
            entries = dict(original)
            entries[replacement] = entries.pop('native/import-000000/source-000000.ris')
            with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(self.reseal(entries)))

    def test_ris_same_bytes_two_searches_not_interchangeable_or_deduplicated(self):
        raw = b'TY  - GEN\nTI  - Fictional repeated source\nER  -\n'
        first = ris_intake.prepare(self.base, raw, 'local-primary', 'first supplied time')
        second = ris_intake.prepare(self.base, raw, 'local-secondary', 'second supplied time')
        current = self.imported(self.base, first['csv_intake'], 'fictional-first')
        current = self.imported(current, second['csv_intake'], 'fictional-second')
        bindings = [dict(import_index=i, format='ris', artifact=wrapper) for i,wrapper in enumerate([first,second])]
        packed = self.build(current, bindings)
        entries = self.payloads(packed)
        self.assertEqual(entries['native/import-000000/source-000000.ris'], raw)
        self.assertEqual(entries['native/import-000001/source-000000.ris'], raw)
        self.assertEqual(bundle.verify_bundle(packed)['bound_native_sources'], 2)
        with self.assertRaises(ValueError): self.build(current, [dict(bindings[0], import_index=1)])
        alternate = ris_intake.prepare(self.base, raw, 'local-primary', 'changed supplied time')
        with self.assertRaises(ValueError): self.build(current, [dict(bindings[0], artifact=alternate)])

    def test_native_formats_are_not_reinterpreted_by_legacy_archive_verifiers(self):
        _, protocol, bindings, _ = self.mixed_project()
        raw = self.build(protocol, bindings)
        for verifier in [collection_bundle.verify_bundle, batch_collection_bundle.verify_bundle]:
            with self.assertRaises(ValueError): verifier(raw)
        for raw in [collection_bundle.build_bundle(encoded(protocol),
                        [dict(import_index=1, nbib_artifact=bindings[1]['artifact'])]),
                    batch_collection_bundle.build_bundle(encoded(protocol),
                        [dict(import_index=2, nbib_batch_artifact=bindings[2]['artifact'])])]:
            with self.assertRaises(ValueError): bundle.verify_bundle(raw)

    def test_mixed_cli_relocation_readonly_sources_and_order_independence(self):
        _, protocol, bindings, _ = self.mixed_project()
        with tempfile.TemporaryDirectory(prefix='sensei mixed archive ') as folder:
            root=Path(folder); source=root/'protocol.json'; source.write_bytes(encoded(protocol))
            input_paths=[]; selections=[]
            for binding in bindings:
                path=root/(binding['format']+'=합성.json'); path.write_bytes(encoded(binding['artifact']))
                input_paths.append(path)
                selections.extend(['--'+binding['format'].replace('_','-'),str(binding['import_index'])+'='+str(path)])
            before={path:path.read_bytes() for path in [source,*input_paths]}
            output=root/'typed.zip'
            made=self.invoke('create',source,output,*selections)
            self.assertEqual(made.returncode,0,made.stderr)
            self.assertEqual(output.read_bytes(),self.build(protocol,bindings))
            self.assertEqual({path:path.read_bytes() for path in before},before)
            for path in before: path.unlink()
            relocated=root/'relocated'; relocated.mkdir(); moved=relocated/'different-name.zip'; output.rename(moved)
            checked=self.invoke('verify',moved)
            self.assertEqual(checked.returncode,0,checked.stderr)
            self.assertEqual(json.loads(checked.stdout)['bound_wrapper_formats'], {'ris':1,'nbib':1,'nbib_batch':1})

    def test_cli_requires_explicit_format_no_guessing_no_duplicate_or_wrong_format(self):
        _, protocol, bindings, _ = self.mixed_project()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'protocol'; source.write_bytes(encoded(protocol))
            wrapper=root/'wrong-extension.nbib'; wrapper.write_bytes(encoded(bindings[0]['artifact']))
            output=root/'new.zip'
            for flags in [[], ['--nbib','0='+str(wrapper)],
                          ['--ris','0='+str(wrapper),'--nbib','0='+str(wrapper)],
                          ['--ris','٠='+str(wrapper)], ['--ris','+0='+str(wrapper)]]:
                result=self.invoke('create',source,output,*flags)
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn(b'Traceback',result.stderr)
                self.assertFalse(output.exists())
            result=self.invoke('create',source,output,'--ris','0='+str(wrapper))
            self.assertEqual(result.returncode,0,result.stderr)

    def test_mixed_archive_verification_does_not_resolve_any_sources(self):
        _, protocol, bindings, _ = self.mixed_project()
        with patch.object(socket,'create_connection',side_effect=AssertionError('no network')), \
             patch.object(zipfile.ZipFile,'extract',side_effect=AssertionError('no extraction')), \
             patch.object(zipfile.ZipFile,'extractall',side_effect=AssertionError('no extraction')):
            checked=bundle.verify_bundle(self.build(protocol,bindings))
            self.assertEqual(checked['external_calls'],0)
            self.assertEqual(checked['review_status'],'NOT_PERFORMED')
            self.assertEqual(checked['search_completion'],'NOT_ESTABLISHED')
            self.assertEqual(checked['source_authenticity'],'NOT_VERIFIED')
            self.assertFalse(checked['protocol_changed'])

    def test_fingerprints_cover_all_dispatch_engines_without_loading_archive_code(self):
        hashes=bundle.implementation_hashes()
        expected=set(research_bundle.ENGINE_FILES)|set(ris_intake.implementation_hashes())|set(nbib_intake.implementation_hashes())|{'native_collection_bundle.py'}
        self.assertEqual(set(hashes),expected)
        for name in ['ris_intake.py','ris_export_parser.py','nbib_intake.py','nbib_batch_intake.py','nbib_export_parser.py']:
            self.assertEqual(hashes[name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        _, protocol, bindings, _ = self.mixed_project()
        raw=self.build(protocol,[bindings[0]])
        entries=self.payloads(raw); entries['native/ris_intake.py']=b'never executed'
        with self.assertRaises(ValueError): bundle.verify_bundle(self.repack(entries))
        with patch.object(bundle,'implementation_hashes',return_value=dict(hashes,**{'nbib_intake.py':'0'*64})):
            with self.assertRaises(ValueError): bundle.verify_bundle(raw)


if __name__ == '__main__':
    unittest.main()
