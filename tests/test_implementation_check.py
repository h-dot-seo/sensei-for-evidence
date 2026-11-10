"""Synthetic read-only implementation diagnostics and executable guide checks."""
import ast
import hashlib
import io
import importlib
import json
import lzma
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib
import implementation_check as check
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


class ImplementationCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic implementation ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'synthetic.py'
        self.source.write_bytes(b'raise RuntimeError("must never execute")\n')
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.artifact = self.root / 'artifact.json'
        self.write({'engine_sha256': {'synthetic.py': self.digest}})

    def write(self, value):
        self.artifact.write_text(json.dumps(value), encoding='utf-8')

    def inspect(self):
        return check.inspect_artifact(self.artifact, self.root)

    def test_match_never_executes_and_preserves_inputs(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = self.inspect()
        self.assertEqual(result['status'], 'MATCH')
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_differs_and_missing(self):
        self.source.write_bytes(b'# synthetic changed\n')
        self.assertEqual(self.inspect()['files'][0]['status'], 'DIFFERS')
        self.source.unlink()
        self.assertEqual(self.inspect()['files'][0]['status'], 'MISSING')

    def test_nested_shapes_and_pointers(self):
        self.write({'a/b~c': [{'target': {'engine_sha256': {'synthetic.py': self.digest}},
                    'receipt': {'implementation_sha256': {'synthetic.py': self.digest}}}],
                    'adapter_receipts': {'adapter_engine_sha256': self.digest}})
        result = self.inspect()
        self.assertEqual(len(result['files']), 3)
        self.assertTrue(any('/a~1b~0c/0/target/' in row['pointer'] for row in result['files']))
        self.assertIn('offline_adapter.py', [row['file'] for row in result['files']])

    def test_bad_names_and_hashes_never_read(self):
        for name, digest in [('../outside.py', self.digest), ('/outside.py', self.digest),
                             ('a\\b.py', self.digest), ('bad.py', 'A' * 64), ('bad.py', 1)]:
            with self.subTest(name=name, digest=digest):
                self.write({'engine_sha256': {name: digest}})
                self.assertEqual(self.inspect()['status'], 'INVALID')

    def test_empty_and_malformed_maps(self):
        for value in ({}, [], None, 'invalid'):
            self.write({'engine_sha256': value})
            self.assertEqual(self.inspect()['status'], 'INVALID')
        self.write({'fictional': True})
        self.assertEqual(self.inspect()['status'], 'NO_HASHES')

    def test_conflicting_declarations_preserved(self):
        self.write({'engine_sha256': {'synthetic.py': self.digest},
                    'target': {'engine_sha256': {'synthetic.py': '0' * 64}}})
        self.assertEqual([row['status'] for row in self.inspect()['files']], ['MATCH', 'DIFFERS'])

    def test_strict_json(self):
        for raw in (b'{"engine_sha256":{},"engine_sha256":{}}', b'{"x":NaN}',
                    b'{"x":1e999}', b'\xef\xbb\xbf{}', b'{"x":"\\ud800"}'):
            self.artifact.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.inspect()

    def test_limits(self):
        with patch.object(check, 'MAX_INPUT_BYTES', 3):
            with self.assertRaises(ValueError):
                self.inspect()
        with patch.object(check, 'MAX_SOURCE_BYTES', 3):
            with self.assertRaises(ValueError):  # checker itself also exceeds this bound
                self.inspect()
        with patch.object(check, 'MAX_NODES', 1):
            with self.assertRaises(ValueError):
                check.recorded_hashes({'nested': {'x': 1}})
        with patch.object(check, 'MAX_HASHES', 0):
            with self.assertRaises(ValueError):
                check.recorded_hashes({'engine_sha256': {'synthetic.py': self.digest}})

    def test_zip_only_manifest_no_extraction(self):
        archive = self.root / 'bundle.zip'
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('manifest.json', self.artifact.read_bytes())
            stream.writestr('../never-created.py', 'raise RuntimeError()')
        self.assertEqual(check.inspect_artifact(archive, self.root)['status'], 'MATCH')
        self.assertFalse((self.root.parent / 'never-created.py').exists())
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('nested/manifest.json', '{}')
        with self.assertRaises(ValueError):
            check.inspect_artifact(archive, self.root)

    def test_zip_duplicate_and_bounded_manifest(self):
        archive = self.root / 'bundle.zip'
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(archive, 'w') as stream:
                stream.writestr('manifest.json', '{}')
                stream.writestr('manifest.json', '{}')
        with self.assertRaises(ValueError):
            check.artifact_json(archive)
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as stream:
            stream.writestr('manifest.json', ' ' * 1000)
        with patch.object(check, 'MAX_JSON_BYTES', 100):
            with self.assertRaises(ValueError):
                check.artifact_json(archive)

    def test_zip_supported_compression(self):
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED,
                            zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA):
            with self.subTest(compression=compression):
                archive = self.root / 'synthetic-compressed.zip'
                with zipfile.ZipFile(archive, 'w', compression=compression) as stream:
                    stream.writestr('manifest.json', self.artifact.read_bytes())
                self.assertEqual(check.inspect_artifact(archive, self.root)['status'], 'MATCH')

    def assert_corrupt_manifest_report(self, compression, decoder_error, input_error):
        archive = self.root / 'synthetic-corrupt.zip'
        with zipfile.ZipFile(archive, 'w', compression=compression) as stream:
            stream.writestr('manifest.json', self.artifact.read_bytes())
        raw = bytearray(archive.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as stream:
            entry = stream.getinfo('manifest.json')
        name_size, extra_size = struct.unpack_from('<HH', raw, entry.header_offset + 26)
        start = entry.header_offset + 30 + name_size + extra_size
        # Corrupt only compressed data, leaving a valid ZIP directory and headers.
        if compression == zipfile.ZIP_LZMA:
            properties_size = struct.unpack_from('<H', raw, start + 2)[0]
            raw[start + 4 + properties_size] = 255
        else:
            raw[start] = 6 if compression == zipfile.ZIP_DEFLATED else 0
        archive.write_bytes(raw)
        self.assertTrue(zipfile.is_zipfile(archive))
        with zipfile.ZipFile(archive) as stream:
            self.assertEqual(stream.namelist(), ['manifest.json'])
            with self.assertRaises(decoder_error):
                stream.read('manifest.json')
        with self.assertRaises(input_error):
            check.artifact_json(archive)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        expected = dict(status='INVALID', error='Input unreadable, malformed or outside inspection limits.',
                        boundary=check.BOUNDARY, census_claim='NOT_ESTABLISHED',
                        conclusion_readiness='NOT_READY')
        for text in (False, True):
            with self.subTest(text=text):
                command = [sys.executable, str(ROOT / 'implementation_check.py'), 'inspect',
                           str(archive), '--engine-root', str(self.root)]
                if text:
                    command.append('--text')
                result = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8')
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stderr, '')
                if text:
                    self.assertEqual(result.stdout, ''.join(
                        key + ': ' + check.quoted_display(value) + '\n' for key, value in expected.items()))
                else:
                    self.assertEqual(json.loads(result.stdout), expected)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_zip_corrupt_deflate_manifest(self):
        self.assert_corrupt_manifest_report(zipfile.ZIP_DEFLATED, zlib.error, ValueError)

    def test_zip_corrupt_lzma_manifest(self):
        self.assert_corrupt_manifest_report(zipfile.ZIP_LZMA, lzma.LZMAError, ValueError)

    def test_zip_corrupt_bzip2_manifest(self):
        self.assert_corrupt_manifest_report(zipfile.ZIP_BZIP2, OSError, OSError)

    def test_symlink_and_dangling_source_rejected(self):
        self.source.unlink()
        try:
            self.source.symlink_to(self.root / 'missing')
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        self.assertEqual(self.inspect()['files'][0]['status'], 'INVALID')
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            check.inspect_artifact(self.artifact, alias)

    def test_reparse_rejection_uses_shared_guard(self):
        with patch.object(check, 'link_like', side_effect=lambda path: path.name == 'synthetic.py'):
            self.assertEqual(self.inspect()['files'][0]['status'], 'INVALID')

    def test_manifest_candidates(self):
        manifest = self.root / 'publication.json'
        value = {'release': 'synthetic-release', 'date': '2026-11-10',
                 'files': [{'path': 'synthetic.py', 'sha256': self.digest}]}
        manifest.write_text(json.dumps(value))
        result = check.inspect_artifact(self.artifact, self.root, [manifest])
        self.assertEqual(result['manifests'][0]['status'], 'MATCH')
        with patch.object(check, 'link_like', side_effect=lambda path: path.name == 'synthetic.py'):
            rejected = check.inspect_artifact(self.artifact, self.root, [manifest])
            self.assertEqual(rejected['status'], 'INVALID')
            self.assertEqual(rejected['manifests'][0]['status'], 'MATCH')
        value['files'][0]['sha256'] = '0' * 64
        manifest.write_text(json.dumps(value))
        self.assertEqual(check.inspect_artifact(self.artifact, self.root, [manifest])['manifests'][0]['status'], 'DIFFERS')
        self.assertEqual(check.inspect_artifact(self.artifact, self.root, [self.root / 'absent'])['manifests'][0]['status'], 'INVALID')

    def test_cli_report_before_failure_and_text_quoting(self):
        self.source.write_bytes(b'# changed\n')
        output = io.StringIO()
        with patch('sys.stdout', output):
            code = check.main(['inspect', str(self.artifact), '--engine-root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['status'], 'DIFFERS')
        self.write({'engine_sha256': {'bad\nname.py': self.digest}})
        with patch('sys.stdout', io.StringIO()) as output:
            self.assertEqual(check.main(['inspect', str(self.artifact), '--text']), 1)
            self.assertNotIn('bad\nname.py', output.getvalue())

    def test_self_inclusion_and_checker_outside_engine(self):
        self.assertNotIn('implementation_check.py', research_bundle.ENGINE_FILES)
        self.assertIn('research_bundle.py', research_bundle.engine_hashes())
        # Only current repository modules are imported here, never --engine-root data.
        for path in ROOT.glob('*.py'):
            tree = ast.parse(path.read_bytes())
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name in ('implementation_hashes', '_implementation_hashes'):
                    module = importlib.import_module(path.stem)
                    self.assertIn(path.name, getattr(module, node.name)(), path.name)

    def test_documented_commands(self):
        guide = (ROOT / 'docs/IMPLEMENTATION_REVISIONS.md').read_text()
        lines = [line for block in re.findall(r'```sh\n(.*?)```', guide, re.S)
                 for line in block.splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            tokens = shlex.split(line)
            result = subprocess.run([sys.executable] + [arg.replace('OUTPUT', str(self.root)) for arg in tokens[1:]],
                                    cwd=ROOT, capture_output=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'MATCH')
        self.assertIn('python research_bundle.py verify [-h] bundle', report['candidate_verify_usage'])
        # The copied source changes only in this synthetic test, not in the guide.
        engine = self.root / 'engine'
        engine.mkdir()
        for name in research_bundle.ENGINE_FILES:
            (engine / name).write_bytes((ROOT / name).read_bytes())
        (engine / 'research_bundle.py').write_bytes(b'# fictional drift\n')
        report = check.inspect_artifact(self.root / 'review-demo.zip', engine)
        self.assertEqual(report['status'], 'DIFFERS')
