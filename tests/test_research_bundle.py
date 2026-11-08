import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path
from research_bundle import build_bundle, create, verify


class BundleTests(unittest.TestCase):
    def test_reproducible_create_verify_and_no_overwrite(self):
        source=Path('examples/report-protocol.json')
        self.assertEqual(build_bundle(source.read_bytes()),build_bundle(source.read_bytes()))
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report.zip'
            receipt=create(source,output)
            self.assertEqual(receipt['sha256'],hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertTrue(verify(output)['valid'])
            with self.assertRaises(FileExistsError): create(source,output)
            result=subprocess.run([sys.executable,'research_bundle.py','verify',str(output)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_build_and_verify_share_inclusive_uncompressed_limit(self):
        raw = Path('examples/report-protocol.json').read_bytes()
        data = build_bundle(raw)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            total = sum(entry.file_size for entry in archive.infolist())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.zip'
            path.write_bytes(data)
            with patch('research_bundle.MAX_BUNDLE_BYTES', total):
                self.assertEqual(build_bundle(raw), data)
                self.assertTrue(verify(path)['valid'])
            with patch('research_bundle.MAX_BUNDLE_BYTES', total - 1):
                with self.assertRaisesRegex(ValueError, 'size limit'):
                    build_bundle(raw)
                with self.assertRaisesRegex(ValueError, 'size limit'):
                    verify(path)

    def test_oversized_create_does_not_leave_output_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.zip'
            with patch('research_bundle.MAX_BUNDLE_BYTES', 1):
                with self.assertRaisesRegex(ValueError, 'size limit'):
                    create(Path('examples/report-protocol.json'), path)
            self.assertFalse(path.exists())

    def test_zip_creator_platform_is_fixed(self):
        raw = Path('examples/report-protocol.json').read_bytes()
        baseline = build_bundle(raw)
        with patch('zipfile.sys.platform', 'win32'):
            simulated_windows = build_bundle(raw)
        self.assertEqual(baseline, simulated_windows)
        with zipfile.ZipFile(io.BytesIO(baseline)) as archive:
            self.assertTrue(all(entry.create_system == 3 for entry in archive.infolist()))

    def test_tampered_derivation_even_with_updated_hash(self):
        raw=build_bundle(Path('examples/report-protocol.json').read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            data={n:archive.read(n) for n in archive.namelist()}
        data['summary.md']=b'Fabricated completed census'
        manifest=json.loads(data['manifest.json'])
        for item in manifest['files']:
            if item['path']=='summary.md':
                item.update(bytes=len(data['summary.md']),sha256=hashlib.sha256(data['summary.md']).hexdigest())
        data['manifest.json']=json.dumps(manifest).encode()
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'tampered.zip'
            with zipfile.ZipFile(output,'w') as archive:
                for name,value in data.items(): archive.writestr(name,value)
            with self.assertRaisesRegex(ValueError,'derived artifacts'): verify(output)

    def test_invalid_protocol_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'bad.json'; output=root/'result.zip'
            source.write_text('{}')
            with self.assertRaises(ValueError): create(source,output)
            self.assertFalse(output.exists())

class IntegratedBundleTests(unittest.TestCase):
    def setUp(self):
        self.raw = Path('examples/report-protocol.json').read_bytes()

    def entries(self, raw=None):
        with zipfile.ZipFile(io.BytesIO(build_bundle(self.raw if raw is None else raw))) as archive:
            return {n: archive.read(n) for n in archive.namelist()}

    def verify_entries(self, entries):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'bundle.zip'
            with zipfile.ZipFile(output, 'w') as archive:
                for name, value in entries.items():
                    archive.writestr(name, value)
            return verify(output)

    def test_exact_input_preserved_and_bounded_readiness(self):
        entries = self.entries()
        self.assertEqual(entries['protocol.json'], self.raw)
        result = self.verify_entries(entries)
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(json.loads(entries['research.json'])['execution_order'], ['WP-001'])

    def test_record_only_pending_is_visible(self):
        protocol = json.loads(self.raw)
        protocol.pop('reports')
        protocol['searches'][0]['has_more'] = True
        entries = self.entries(json.dumps(protocol).encode())
        self.assertIsNone(json.loads(entries['reports.json']))
        self.assertIn(b'Included reports: not supplied', entries['summary.md'])
        self.assertFalse(json.loads(entries['research.json'])['coverage'][0]['complete'])
        self.assertTrue(self.verify_entries(entries)['valid'])

    def test_strict_json(self):
        for raw in (b'null', b'[]', b'"invalid"', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                build_bundle(raw)

    def test_engine_drift_rejected(self):
        entries = self.entries()
        manifest = json.loads(entries['manifest.json'])
        manifest['engine_sha256']['research_bundle.py'] = '0' * 64
        entries['manifest.json'] = json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError, 'engine bytes differ'):
            self.verify_entries(entries)

    def test_wrong_schema_rejected(self):
        entries = self.entries()
        manifest = json.loads(entries['manifest.json'])
        manifest['schema_version'] = 1
        entries['manifest.json'] = json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError, 'unsupported bundle schema'):
            self.verify_entries(entries)

    def test_tamper_missing_and_traversal_entries(self):
        entries = self.entries()
        entries['summary.md'] = b'changed'
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.verify_entries(entries)
        entries = self.entries()
        entries.pop('summary.md')
        with self.assertRaisesRegex(ValueError, 'archive entries'):
            self.verify_entries(entries)
        entries = self.entries()
        entries['../outside'] = b'not extracted'
        with self.assertRaisesRegex(ValueError, 'archive entries'):
            self.verify_entries(entries)

    def test_full_text_reconciliation(self):
        protocol = json.loads(self.raw)
        protocol['reports'][0].update(decision='exclude', reason='wrong model')
        with self.assertRaisesRegex(ValueError, 'reconcile screening first'):
            build_bundle(json.dumps(protocol).encode())

    def test_work_package_formula_escaping(self):
        protocol = json.loads(self.raw)
        protocol['gaps'][0]['question'] = '=1+1'
        entries = self.entries(json.dumps(protocol).encode())
        self.assertIn(b"'=1+1", entries['work-packages.csv'])
