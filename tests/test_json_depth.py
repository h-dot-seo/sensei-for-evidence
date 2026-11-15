from tests._native_archive_compat import prior_handoff_display
"""Explicit container count, fixed error provenance and old in-range behavior."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

import json_io
from json_io import JsonNestingError, parse_json
from tests._json_depth_compat import prior_bytes
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]
CHANGED={'json_io.py','research_status.py','compare_runs.py','review_handoff.py','validate_run.py'}


def nested(count, kind='array', leaf='0'):
    left=[];right=[]
    for index in range(count):
        obj=kind=='object' or kind=='mixed' and index%2
        left.append('{"x":' if obj else '[');right.append('}' if obj else ']')
    return ''.join(left)+leaf+''.join(reversed(right))


class JsonDepthTests(unittest.TestCase):
    def test_exact_container_boundary_and_scalar_leaves(self):
        self.assertEqual(json_io.MAX_CONTAINER_DEPTH,128)
        for raw in ('0','null','true','"[[[{{{]}}"','"합성 😀"','1.5'):
            self.assertEqual(parse_json(raw),json.loads(raw))
        for kind in ('array','object','mixed'):
            for leaf in ('0','null','"[[[{{{]}}"','"\\ud83d\\ude00"'):
                self.assertEqual(parse_json(nested(128,kind,leaf)),json.loads(nested(128,kind,leaf)))
                with self.assertRaises(JsonNestingError) as caught:parse_json(nested(129,kind,leaf))
                self.assertEqual(caught.exception.reason,'container_limit')
            # Empty containers count too; scalar leaves and object keys do not.
            for leaf in ('[]','{}'):
                parse_json(nested(127,kind,leaf))
                with self.assertRaises(JsonNestingError):parse_json(nested(128,kind,leaf))
        for raw in (nested(129),nested(129).encode(),bytearray(nested(129).encode())):
            with self.assertRaises(JsonNestingError):parse_json(raw)

    def test_decoder_capacity_has_separate_fixed_reason_and_no_payload(self):
        with patch.object(json_io.json,'loads',side_effect=RecursionError('private supplied marker')):
            with self.assertRaises(JsonNestingError) as caught:parse_json('[]')
        self.assertEqual(caught.exception.reason,'decoder_capacity')
        self.assertEqual(str(caught.exception),'JSON nesting exceeds parser capacity')
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertNotIn('private',str(caught.exception))
        # Real input can reach either the explicit walk or the interpreter decoder cap.
        with self.assertRaises(JsonNestingError) as caught:parse_json(nested(100000))
        self.assertIn(caught.exception.reason,('container_limit','decoder_capacity'))

    def test_in_range_values_and_existing_error_text_exactly_equal_prior(self):
        old=types.ModuleType('prior_json_io');exec(compile(prior_bytes('json_io.py'),'prior_json_io','exec'),old.__dict__)
        accepted=['null','0','-3','true','"합성"','"\\ud83d\\ude00"','"\\uffff"','9007199254740993',nested(128,'mixed')]
        rejected=['{"a":1,"a":2}','{"'+('x'*200)+'":1,"'+('x'*200)+'":2}',
                  'NaN','Infinity','-Infinity','1e999','"\\ud800"','{"\\ud800":1}','\ufeff{}','{bad',b'\xff','{}'.encode('utf-16')]
        for raw in accepted:self.assertEqual(parse_json(raw),old.parse_json(raw))
        for raw in rejected:
            outcomes=[]
            for loader in (old.parse_json,parse_json):
                try:loader(raw)
                except Exception as e:outcomes.append((type(e).__name__,str(e)))
                else:self.fail('expected rejection')
            self.assertEqual(outcomes[0],outcomes[1])
        for value in [None,{'한글':['[]',0,False]},[1,2.5]]:
            self.assertEqual(json_io.canonical_json_bytes(value),old.canonical_json_bytes(value))

    def test_four_existing_private_channels_preserve_reason_classification(self):
        import research_status,compare_runs,review_handoff,validate_run
        for module in (research_status,compare_runs,review_handoff,validate_run):
            for reason,phrase in [('decoder_capacity','parser capacity'),('container_limit','128 levels')]:
                with self.subTest(module=module.__name__,reason=reason),tempfile.TemporaryDirectory() as td:
                    source=Path(td)/'private-name.json';source.write_bytes(b'{}')
                    out=io.StringIO()
                    with patch.object(module,'parse_json',side_effect=JsonNestingError(reason)),redirect_stderr(out),self.assertRaises(SystemExit) as caught:
                        module._read_cli_input(source,'protocol',argparse.ArgumentParser())
                    self.assertEqual(caught.exception.code,1)
                    self.assertIn('input-too-complex: protocol:',out.getvalue())
                    self.assertIn(phrase,out.getvalue());self.assertNotIn('private-name',out.getvalue())
                    self.assertNotIn('input-not-json',out.getvalue())

    def test_actual_deep_cli_and_harness_match_without_traceback_or_output(self):
        commands=[('evidence_workflow.py',),('prisma_reports.py',),('prisma_audit.py',),
                  ('search_manifest.py',),('research_status.py',),('validate_run.py',),
                  ('compare_runs.py',),('review_handoff.py',),('research_bundle.py','create')]
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'private-input.json';target=Path(td)/'new.zip'
            for depth in (129,100000):
                raw=('{"opaque":'+nested(depth)+'}').encode();source.write_bytes(raw)
                for command in commands:
                    args=[*command[1:],str(source)]
                    if command[0]=='compare_runs.py':args.append(str(source))
                    if command[0]=='research_bundle.py':args.append(str(target))
                    with self.subTest(command=command,depth=depth):
                        actual=subprocess.run([sys.executable,str(ROOT/command[0]),*args],cwd=ROOT,capture_output=True,timeout=30)
                        replay=run_cli(command[0],*args)
                        self.assertEqual((actual.returncode,actual.stdout,actual.stderr),(replay.returncode,replay.stdout,replay.stderr))
                        self.assertEqual((actual.returncode,actual.stdout),(1,b''),actual.stderr)
                        self.assertTrue(actual.stderr);self.assertNotIn(b'Traceback',actual.stderr)
                        self.assertFalse(target.exists());self.assertEqual(source.read_bytes(),raw)

    def test_exact_five_source_changes_all_other_root_bytes_and_example_runs(self):
        proof=json.loads((ROOT/'tests/json_depth_prior_sources.json').read_bytes())
        changes=json.loads((ROOT/'tests/json_depth_source_changes.json').read_bytes())
        self.assertEqual(set(changes),CHANGED)
        self.assertEqual(set(proof),{p.name for p in ROOT.glob('*.py') if p.name not in ('cli_errors.py','retained_bundle_describe.py','amendment_links.py','amendment_intake.py')})
        for name,digest in proof.items():self.assertEqual(hashlib.sha256(prior_bytes(name)).hexdigest(),digest,name)
        from evidence_workflow import run
        cases=json.loads((ROOT/'tests/evidence_basis_legacy_baselines.json').read_bytes())['cases']
        self.assertEqual(len(cases),44)
        for case in cases:
            raw=(ROOT/case['path']).read_bytes();value=parse_json(raw)
            self.assertEqual(hashlib.sha256(json_io.canonical_json_bytes(value)).hexdigest(),case['input_sha256'])
            self.assertEqual(hashlib.sha256(json_io.canonical_json_bytes(run(value))).hexdigest(),case['run_sha256'])

    def test_actual_prior_and_current_in_range_primary_cli_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            old=Path(td)/'old';old.mkdir()
            for source in ROOT.glob('*.py'):(old/source.name).write_bytes(prior_bytes(source.name))
            base=json.loads((ROOT/'examples/report-protocol.json').read_bytes())
            # Root object plus 127 array containers = exactly128; leaf depth128 is permitted.
            raw=json.dumps(base)[:-1]+',"opaque":'+nested(127)+'}'
            source=Path(td)/'protocol.json';source.write_bytes(raw.encode())
            for script in ('evidence_workflow.py','prisma_reports.py','prisma_audit.py','search_manifest.py'):
                a=subprocess.run([sys.executable,'-B',str(old/script),str(source)],cwd=old,capture_output=True,timeout=30)
                b=subprocess.run([sys.executable,'-B',str(ROOT/script),str(source)],cwd=ROOT,capture_output=True,timeout=30)
                expected=a.stdout
                if script in ('prisma_audit.py','search_manifest.py'):
                    for name in ('json_io.py','archive_safety.py',script):
                        oldhash=hashlib.sha256(prior_bytes(name)).hexdigest()
                        newhash=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                        oldfield=('"'+name+'": "'+oldhash+'"').encode()
                        newfield=('"'+name+'": "'+newhash+'"').encode()
                        self.assertEqual(expected.count(oldfield),1)
                        self.assertEqual(b.stdout.count(newfield),1)
                        expected=expected.replace(oldfield,newfield,1)
                    document=json.loads(expected)
                    document['engine_sha256']['cli_errors.py']=hashlib.sha256((ROOT/'cli_errors.py').read_bytes()).hexdigest()
                    # Exact round60 ENGINE revision exceptions; preserve every other
                    # field and the actual declared implementation-map order.
                    actual_document=json.loads(b.stdout)
                    current_map=actual_document['engine_sha256']
                    changes=json.loads((ROOT/'tests/amendment_source_changes.json').read_bytes())
                    for name in set(changes)&set(document['engine_sha256']):
                        self.assertEqual(document['engine_sha256'][name],hashlib.sha256(prior_bytes(name)).hexdigest())
                        document['engine_sha256'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                    document['engine_sha256']['amendment_links.py']=hashlib.sha256((ROOT/'amendment_links.py').read_bytes()).hexdigest()
                    self.assertEqual(document['engine_sha256'],current_map)
                    document['engine_sha256']={name:document['engine_sha256'][name] for name in current_map}
                    expected=(json.dumps(document,ensure_ascii=False,indent=2)+'\n').replace('\n',os.linesep).encode()
                self.assertEqual((a.returncode,expected,a.stderr),(b.returncode,prior_handoff_display(b.stdout),b.stderr))
                self.assertEqual(b.returncode,0,b.stderr)


if __name__=='__main__':unittest.main()
