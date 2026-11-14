"""CLI-only bounded input diagnostics preserve successful and negative reports."""
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
MODULES=('research_status','review_handoff','compare_runs')


class ViewCLIInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='private sentinel ')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.valid=ROOT/'examples/review-demo.json'

    def run_cli(self, module, args):
        return subprocess.run([sys.executable,str(ROOT/(module+'.py')),*map(str,args)],capture_output=True)

    def arguments(self,module,path):
        return [path,self.valid] if module=='compare_runs' else [path]

    def assert_error(self,result,category,label):
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertEqual(result.stdout,b'')
        self.assertEqual(result.stderr.count(b'\n'),1)
        self.assertIn(('error: '+category+': '+label+':').encode(),result.stderr)
        for private in (str(self.root).encode(),b'private sentinel',b'secret-sentinel',b'Traceback',b'\x1b'):
            self.assertNotIn(private,result.stderr)

    def test_real_cli_invalid_inputs_are_classified_without_echo(self):
        for module in MODULES:
            for raw,category in [(b'not-json secret-sentinel\x1b[31m','input-not-json'),(b'\xff','input-not-json'),(b'{"secret-sentinel":1,"secret-sentinel":2}','input-not-json'),(b'[]','input-invalid'),(b'{}','input-invalid'),(b'{"x":'+b'['*2000+b'0'+b']'*2000+b'}','input-too-complex')]:
                with self.subTest(module=module,category=category):
                    path=self.root/'secret-sentinel.json';path.write_bytes(raw)
                    label='before protocol' if module=='compare_runs' else 'protocol'
                    if raw==b'{}': label='comparison inputs' if module=='compare_runs' else 'protocol or work selection' if module=='review_handoff' else 'protocol'
                    self.assert_error(self.run_cli(module,self.arguments(module,path)),category,label)
            missing=self.root/'absent-secret-sentinel'
            self.assert_error(self.run_cli(module,self.arguments(module,missing)),'input-unreadable','before protocol' if module=='compare_runs' else 'protocol')

    def test_comparison_after_and_amendment_labels(self):
        path=self.root/'secret-sentinel.json';path.write_bytes(b'wrong')
        self.assert_error(self.run_cli('compare_runs',[self.valid,path]),'input-not-json','after protocol')
        self.assert_error(self.run_cli('compare_runs',[self.valid,self.valid,'--amendment',path]),'input-not-json','amendment')

    def test_inclusive_limit_and_single_bounded_read(self):
        class Parser:
            def exit(self,code,message):
                raise ValueError((code,message))
        class Reader(io.BytesIO):
            requested=[]
            def read(self,n=-1):
                self.requested.append(n)
                return super().read(n)
        for name in MODULES:
            module=importlib.import_module(name)
            path=self.root/'input.json';path.write_bytes(b'{}')
            with patch.object(module,'MAX_CLI_INPUT_BYTES',2):
                self.assertEqual(module._read_cli_input(path,'protocol',Parser()),{})
                path.write_bytes(b'{} ')
                with self.assertRaisesRegex(ValueError,'input-too-large'):
                    module._read_cli_input(path,'protocol',Parser())
                reader=Reader(b'{}');reader.requested=[]
                with patch.object(Path,'open',return_value=reader):
                    self.assertEqual(module._read_cli_input(path,'protocol',Parser()),{})
                    self.assertEqual(reader.requested,[3])

    def test_nesting_boundary_is_explicit_across_parser_versions(self):
        class Parser:
            def exit(self,code,message): raise ValueError(message)
        for name in MODULES:
            module=importlib.import_module(name)
            path=self.root/'input.json'
            path.write_bytes(b'{"x":[0]}')
            with patch.object(module,'MAX_CLI_NESTING',2):
                self.assertEqual(module._read_cli_input(path,'protocol',Parser()),{'x':[0]})
                path.write_bytes(b'{"x":[[0]]}')
                with self.assertRaisesRegex(ValueError,'input-too-complex'):
                    module._read_cli_input(path,'protocol',Parser())

    def test_success_outputs_equal_existing_function_results(self):
        protocol=json.loads(self.valid.read_bytes())
        for name in MODULES:
            module=importlib.import_module(name)
            expected=(module.status(protocol) if name=='research_status' else module.handoff(protocol) if name=='review_handoff' else module.compare_protocols(protocol,protocol))
            result=self.run_cli(name,self.arguments(name,self.valid))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stderr,b'')
            self.assertEqual(json.loads(result.stdout),expected)

    def test_invalid_selected_work_does_not_echo_identifier(self):
        self.assert_error(self.run_cli('review_handoff',[self.valid,'--work-package','secret-sentinel\x1b[31m']),'input-invalid','protocol or work selection')
