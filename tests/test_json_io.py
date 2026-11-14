import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from json_io import parse_json, configure_utf8_stdio
from tests._cli import run_cli
from tests._json_cli_cases import COMMANDS, REJECTIONS, arguments
from research_bundle import build_bundle, verify


class JsonInputTests(unittest.TestCase):
    def test_duplicate_and_nonfinite_numbers_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":{"x":1,"x":2}}', '{"a":NaN}',
                    '{"a":Infinity}', '{"a":-Infinity}', '{"a":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_json(raw)

    def test_surrogate_values_rejected_with_safe_diagnostics(self):
        for raw in ('{"value":"\\ud800"}', '{"\\udfff":1}', '{"values":["\\ud800"]}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, 'unpaired surrogate'):
                parse_json(raw)
        self.assertEqual(parse_json('"\\ud83d\\ude00"'), '\U0001f600')
        stdout = io.TextIOWrapper(io.BytesIO(), encoding='ascii', errors='strict')
        stderr = io.TextIOWrapper(io.BytesIO(), encoding='ascii', errors='backslashreplace')
        with patch.object(sys, 'stdout', stdout), patch.object(sys, 'stderr', stderr):
            configure_utf8_stdio()
            self.assertEqual(stdout.encoding, 'utf-8')
            self.assertEqual(stdout.errors, 'strict')
            self.assertEqual(stderr.errors, 'backslashreplace')

    def test_valid_unicode_and_finite_numbers(self):
        value = parse_json('{"질문":"합성 근거", "value":1.25, "zero":0, "bool":false}')
        self.assertEqual(value['질문'], '합성 근거')
        self.assertEqual(value['value'], 1.25)
        self.assertIs(value['bool'], False)
        self.assertEqual(parse_json('{"질문":"합성 근거"}'.encode('utf-8')), {'질문': '합성 근거'})
        with self.assertRaises(UnicodeError):
            parse_json('{"value":1}'.encode('utf-16'))

    def test_all_clis_reject_ambiguous_or_nonobject_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'input.json'
            target = Path(folder)/'bundle.zip'
            for raw in REJECTIONS:
                source.write_text(raw, encoding='utf-8')
                for command in COMMANDS:
                    args = arguments(command, source, target)
                    with self.subTest(raw=raw, command=command):
                        result = run_cli(command[0], *args)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn(b'Traceback', result.stderr + result.stdout)
                        self.assertFalse(target.exists())
                        self.assertEqual(source.read_bytes(), raw.encode('utf-8'))

    def test_each_rejection_cli_keeps_real_process_error_smoke(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'input.json';target=Path(folder)/'bundle.zip'
            source.write_text(REJECTIONS[0],encoding='utf-8');original=source.read_bytes()
            for command in COMMANDS:
                args=arguments(command,source,target)
                actual=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/command[0]),*args],
                    capture_output=True,timeout=20)
                replay=run_cli(command[0],*args)
                self.assertEqual((actual.returncode,actual.stdout,actual.stderr),(replay.returncode,replay.stdout,replay.stderr))
                self.assertNotEqual(actual.returncode,0);self.assertNotIn(b'Traceback',actual.stdout+actual.stderr)
                self.assertFalse(target.exists());self.assertEqual(source.read_bytes(),original)

    def test_utf8_protocol_cli_and_bundle_fingerprint(self):
        protocol = json.loads(Path('examples/report-protocol.json').read_text())
        protocol['question'] = '합성 근거 질문'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'input.json'
            path.write_text(json.dumps(protocol, ensure_ascii=False), encoding='utf-8')
            result = subprocess.run([sys.executable,'evidence_workflow.py',str(path)],capture_output=True,encoding='utf-8',timeout=20,env=dict(os.environ, PYTHONIOENCODING='ascii'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['question'], protocol['question'])
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(protocol).encode()))) as archive:
            self.assertIn('json_io.py', json.loads(archive.read('manifest.json'))['engine_sha256'])

    def test_malformed_manifest_shapes_fail_cleanly(self):
        raw = build_bundle(Path('examples/report-protocol.json').read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = {name:archive.read(name) for name in archive.namelist()}
        baseline = json.loads(entries['manifest.json'])
        malformed = [[], None, dict(baseline, schema_version=2.0), dict(baseline, files={})]
        invalid_entry = copy.deepcopy(baseline)
        invalid_entry['files'][0]['bytes'] = True
        malformed.append(invalid_entry)
        for manifest in malformed:
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'invalid.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    for name, data in entries.items():
                        archive.writestr(name, json.dumps(manifest).encode() if name == 'manifest.json' else data)
                with self.assertRaises(ValueError):
                    verify(path)
                result = subprocess.run([sys.executable,'research_bundle.py','verify',str(path)],capture_output=True,text=True,timeout=20)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
