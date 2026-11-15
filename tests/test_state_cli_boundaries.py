"""Legacy findings remain reports; operational failures do not masquerade as findings."""
import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import validate_run
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]

class StateCliBoundaryTests(unittest.TestCase):
    def invoke(self,path,real=False):
        if real:
            result=subprocess.run([sys.executable,str(ROOT/'validate_run.py'),str(path)],cwd=ROOT,capture_output=True,timeout=30)
        else:
            result=run_cli('validate_run.py',path,cwd=ROOT)
        # Decode only: never apply subprocess universal-newline conversion.
        # Both paths must preserve the platform's original output bytes.
        result.stdout=result.stdout.decode('utf-8');result.stderr=result.stderr.decode('utf-8')
        return result

    def failure(self,result,category):
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,'')
        self.assertTrue(result.stderr.startswith('state validation error: '+category+': state: '),result.stderr)
        self.assertEqual(len(result.stderr.splitlines()),1)
        for value in ('sensitive-marker','Traceback',str(ROOT)):
            self.assertNotIn(value,result.stderr)

    def test_strict_json_and_read_failures_real_and_harness_equal(self):
        with tempfile.TemporaryDirectory(prefix='sensitive-marker ') as td:
            p=Path(td)/'sensitive-marker.json'
            cases=[(None,'input-unreadable'),(b'not JSON sensitive-marker','input-not-json'),(b'\xff','input-not-json'),
                   (b'{"x":1,"x":2}','input-not-json'),(b'{"x":NaN}','input-not-json'),(b'[]','input-invalid'),
                   (b'null','input-invalid'),(b'{"x":'+b'['*150+b'0'+b']'*150+b'}','input-too-complex'),
                   (b'{"x":'+b'['*2000+b'0'+b']'*2000+b'}','input-too-complex')]
            for raw,category in cases:
                if raw is not None:p.write_bytes(raw)
                a=self.invoke(p);b=self.invoke(p,True)
                self.failure(a,category);self.failure(b,category)
                self.assertEqual((a.returncode,a.stdout,a.stderr),(b.returncode,b.stdout,b.stderr))
                self.assertNotIn(td,a.stderr)

    def test_normal_reports_have_exact_existing_bytes_and_codes(self):
        state=json.loads((ROOT/'examples/state.json').read_bytes())
        bad=copy.deepcopy(state);bad['release']={'status':'COMPLETE','required_artifacts':['synthetic-kind']}
        for doc in (state,{},bad,dict(state,references=[None]),dict(state,screening=0)):
            errors=validate_run.validate(doc)
            expected=json.dumps({'valid':not errors,'errors':errors},ensure_ascii=False)+os.linesep
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/'state.json';p.write_bytes(json.dumps(doc).encode('utf-8'))
                for real in (False,True):
                    result=self.invoke(p,real);self.assertEqual(result.returncode,int(bool(errors)))
                    self.assertEqual(result.stdout,expected);self.assertEqual(result.stderr,'')

    def test_byte_limit_inclusive_and_single_bounded_read(self):
        import argparse
        parser=argparse.ArgumentParser()
        for raw,good in [(b'{}'+b' '*30,True),(b'{}'+b' '*31,False)]:
            stream=io.BytesIO(raw)
            with patch.object(validate_run,'MAX_CLI_INPUT_BYTES',32),patch.object(Path,'open',return_value=stream) as opened,patch.object(sys,'stderr',io.StringIO()) as err:
                if good:self.assertEqual(validate_run._read_cli_input(Path('sensitive-marker'),'state',parser),{})
                else:
                    with self.assertRaises(SystemExit) as caught:validate_run._read_cli_input(Path('sensitive-marker'),'state',parser)
                    self.assertEqual(caught.exception.code,1);self.assertIn('input-too-large',err.getvalue())
                opened.assert_called_once_with('rb')
        class Bounded(io.BytesIO):
            def read(self,n=-1):
                self.request=n;return super().read(n)
        stream=Bounded(b'{}')
        with patch.object(Path,'open',return_value=stream):
            self.assertEqual(validate_run._read_cli_input(Path('unused'),'state',parser),{})
        self.assertEqual(stream.request,50_000_001)

    def test_real_cli_production_byte_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'
            with path.open('wb') as stream:
                stream.write(b'{}');stream.write(b' '*(50_000_000-2))
            accepted=self.invoke(path,True)
            self.assertEqual(accepted.returncode,1)
            self.assertFalse(json.loads(accepted.stdout)['valid'])
            self.assertEqual(accepted.stderr,'')
            with path.open('ab') as stream:stream.write(b' ')
            self.failure(self.invoke(path,True),'input-too-large')

    def test_nesting_boundary_and_caught_exception_are_distinct_from_findings(self):
        import argparse
        parser=argparse.ArgumentParser()
        for count,good in [(127,True),(128,False)]:
            raw=b'{"extra":'+b'['*count+b'0'+b']'*count+b'}'
            with patch.object(Path,'open',return_value=io.BytesIO(raw)),patch.object(sys,'stderr',io.StringIO()):
                if good:self.assertIsInstance(validate_run._read_cli_input(Path('unused'),'state',parser),dict)
                else:
                    with self.assertRaises(SystemExit):validate_run._read_cli_input(Path('unused'),'state',parser)
        with patch.object(validate_run,'_read_cli_input',return_value={}),patch.object(validate_run,'validate',side_effect=KeyError('sensitive-marker')),patch.object(sys,'argv',['validate_run.py','sensitive-marker']),patch.object(sys,'stdout',io.StringIO()) as out,patch.object(sys,'stderr',io.StringIO()) as err:
            with self.assertRaises(SystemExit) as caught:validate_run.main()
            self.assertEqual(caught.exception.code,1);self.assertEqual(out.getvalue(),'')
            self.assertIn('input-invalid: state:',err.getvalue());self.assertNotIn('sensitive-marker',err.getvalue())

    def test_contract_still_unreviewed_and_source_binding_is_current(self):
        registry=json.loads((ROOT/'docs/command_contract.json').read_bytes())
        self.assertEqual(registry['implementation_sha256']['validate_run.py'],hashlib.sha256((ROOT/'validate_run.py').read_bytes()).hexdigest())
        entry=next(x for x in registry['commands'] if x['script']=='validate_run.py')
        self.assertIsNone(entry['effects'])
        self.assertEqual(sum(x['effects'] is None for x in registry['commands']),156)

    def test_usage_remains_exit_two(self):
        result=run_cli('validate_run.py',cwd=ROOT)
        self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'')
