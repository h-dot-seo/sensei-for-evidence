"""The remaining roadmap CLI inputs are bounded before parsing, not a total resource cap."""
import ast
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
from archive_safety import read_bounded
from tests._cli import run_cli
from tests._cli_input_compat import prior_bytes
ROOT=Path(__file__).resolve().parents[1]
CHANGES=json.loads((ROOT/'tests/cli_input_source_changes.json').read_bytes())
LIMIT=50_000_000

def arguments(name,p,extra=None):
    if name=='receipt_intake.py':return ['template',p] if extra is None else ['check',p,extra]
    if name=='report_decision.py':return ['target',p,'--report-id','report-one'] if extra is None else ['assemble',p,extra]
    if name=='screening_decision.py':return ['target',p,'--record-id','record-one'] if extra is None else ['assemble',p,extra]
    return [p]

class CliInputBoundsTests(unittest.TestCase):
    def test_exact_source_changes_and_all_input_sites(self):
        baseline=json.loads((ROOT/'tests/cli_input_prior_sources.json').read_bytes())
        self.assertEqual(set(CHANGES),set(baseline['changed']))
        self.assertEqual(sum(len(v)-1 for v in CHANGES.values()),19)
        for name,sha in baseline['changed'].items():
            self.assertEqual(hashlib.sha256(prior_bytes(name)).hexdigest(),sha)
            tree=ast.parse((ROOT/name).read_bytes())
            constants=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MAX_CLI_INPUT_BYTES' for t in n.targets)]
            self.assertEqual(constants,[LIMIT])
            for n in ast.walk(tree):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('read_bytes','read_text'):
                    self.assertFalse(isinstance(n.func.value,ast.Attribute) and isinstance(n.func.value.value,ast.Name) and n.func.value.value.id in ('args','a'))
        from tests._exclusive_output_compat import prior_bytes as pre_output_bytes
        for name,sha in baseline['unchanged'].items():self.assertEqual(hashlib.sha256(pre_output_bytes(name)).hexdigest(),sha,name)

    def test_all_fifteen_protocols_reject_actual_overlimit_before_json(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'supplied-secret.json';p.write_bytes(b'!'+b' ' * LIMIT)
            for name in CHANGES:
                with self.subTest(name=name):
                    r=run_cli(name,*arguments(name,p));self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b'')
                    self.assertIn(b'input exceeds size limit',r.stderr);self.assertNotIn(b'supplied-secret',r.stderr);self.assertNotIn(b'Traceback',r.stderr)

    def test_all_secondary_inputs_are_bounded_before_parse_and_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'protocol.json';p.write_bytes(b'{}');q=Path(td)/'secret.json';q.write_bytes(b'!'+b' ' * LIMIT)
            cases=[('receipt_intake.py',['check',p,q]),('report_decision.py',['assemble',p,q]),('report_decision.py',['verify',p,q]),('screening_decision.py',['assemble',p,q])]
            for name,args in cases:
                with self.subTest(name=name,args=args[0]):
                    r=run_cli(name,*args);self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b'');self.assertIn(b'input exceeds size limit',r.stderr)

    def test_utf8_inclusive_limit_and_partial_stream_ownership(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.json';p.write_bytes('"한"'.encode()+b' '*(LIMIT-5))
            self.assertEqual(len(read_bounded(p,LIMIT)),LIMIT)
            with p.open('ab') as f:f.write(b' ')
            with self.assertRaisesRegex(ValueError,'size limit'):read_bounded(p,LIMIT)
        class Partial(io.BytesIO):
            def read(self,size=-1):return super().read(min(size,3))
        s=Partial('한글'.encode());s.seek(2);self.assertEqual(read_bounded(s,6),'한글'.encode());self.assertEqual(s.tell(),2)
        with self.assertRaises(ValueError):read_bounded(s,5)
        self.assertEqual(s.tell(),2);self.assertFalse(s.closed)

    def test_native_real_process_equals_harness_for_size_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.json';p.write_bytes(b'!'+b' '*LIMIT)
            for name in ('evidence_workflow.py','report_decision.py','screening_decision.py'):
                args=arguments(name,p);real=subprocess.run([sys.executable,str(ROOT/name),*map(str,args)],cwd=ROOT,capture_output=True)
                h=run_cli(name,*args);self.assertEqual((real.returncode,real.stdout,real.stderr),(h.returncode,h.stdout,h.stderr))

    def test_legacy_text_newline_and_error_positions_preserved(self):
        cases=[b'{\r\n "a":\r\n !}',b'{\r "a":\r !}',b'{"a":"bad\r\nvalue"}',b'{"a":1,"a":2}',b'\xff']
        baseline=json.loads((ROOT/'tests/cli_input_error_baselines.json').read_bytes())
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input.json'
            for case in baseline:
                p.write_bytes(bytes.fromhex(case['input_hex']))
                changes=json.loads((ROOT/'tests/cli_error_source_changes.json').read_bytes())
                if case['script'] in changes:
                    # Historical error text is intentionally superseded by round57.
                    # Execute the preserved previous CLI to retain the newline/offset proof;
                    # current category/label/channel behavior is tested in test_cli_error_contract.
                    import types
                    module=types.ModuleType('previous_cli');module.__file__=str(ROOT/case['script'])
                    exec(compile(changes[case['script']]['old'],module.__file__,'exec'),module.__dict__)
                    output,error=io.StringIO(),io.StringIO()
                    with patch.object(sys,'argv',[module.__file__,*map(str,arguments(case['script'],p))]),patch.object(sys,'stdout',output),patch.object(sys,'stderr',error):
                        with self.assertRaises(SystemExit) as stopped:module.main()
                    r=subprocess.CompletedProcess([],stopped.exception.code,output.getvalue().replace('\n',os.linesep).encode(),error.getvalue().replace('\n',os.linesep).encode())
                else:r=run_cli(case['script'],*arguments(case['script'],p))
                stderr=bytes.fromhex(case['stderr_hex']).replace(b'\n',os.linesep.encode())
                self.assertEqual((r.returncode,r.stdout,r.stderr),(case['returncode'],bytes.fromhex(case['stdout_hex']),stderr))

    def test_actual_previous_all_fifteen_cli_bytes_with_exact_selfhash_exceptions(self):
        cases=json.loads((ROOT/'tests/cli_input_legacy_baselines.json').read_bytes())
        self.assertEqual({c['args'][0] for c in cases},set(CHANGES))
        for case in cases:
            expected=case['stdout']
            for name,row in case['exact_selfhash_replacements'].items():
                self.assertIn(name,CHANGES);self.assertEqual(expected.count(row['prior_sha256']),row['occurrences'])
                expected=expected.replace(row['prior_sha256'],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
            from tests._json_depth_compat import prior_bytes as pre_depth_bytes
            # Exactly five depth-source fields plus the shared-preflight ENGINE field.
            for name in ('json_io.py','research_status.py','compare_runs.py','review_handoff.py','validate_run.py','archive_safety.py'):
                oldfield='"'+name+'": "'+hashlib.sha256(pre_depth_bytes(name)).hexdigest()+'"'
                newfield='"'+name+'": "'+hashlib.sha256((ROOT/name).read_bytes()).hexdigest()+'"'
                expected=expected.replace(oldfield,newfield)
            # Round57 adds one named non-engine helper key to adopted review maps.
            error_changes=json.loads((ROOT/'tests/cli_error_source_changes.json').read_bytes())
            if case['args'][0] in error_changes and case['args'][0] not in ('receipt_intake.py',):
                document=json.loads(expected)
                if 'engine_sha256' in document:
                    for name,change in error_changes.items():
                        if name in document['engine_sha256']:
                            document['engine_sha256'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                    # Tuple-built maps insert the helper before their local names.
                    hashes=document['engine_sha256'];ordered={}
                    tuple_names={'report_study_inventory.py','report_study_inventory_review.py','report_study_review.py','synthesis_review.py'}
                    anchor=case['args'][0] if case['args'][0] in tuple_names else None
                    for name,value in hashes.items():
                        if name==anchor:ordered['cli_errors.py']=hashlib.sha256((ROOT/'cli_errors.py').read_bytes()).hexdigest()
                        ordered[name]=value
                    if anchor is None:
                        # Five original reviewers add output_io after their own hash.
                        ordered={}
                        for name,value in hashes.items():
                            ordered[name]=value
                            if name==case['args'][0]:ordered['cli_errors.py']=hashlib.sha256((ROOT/'cli_errors.py').read_bytes()).hexdigest()
                    document['engine_sha256']=ordered
                    expected=json.dumps(document,ensure_ascii=False,indent=2)+'\n'
            expected=expected.replace('\n',os.linesep).encode()
            r=subprocess.run([sys.executable,*case['args']],cwd=ROOT,capture_output=True)
            stdout=r.stdout
            if case['args'][0] in ('report_review.py','report_study_inventory.py','report_study_inventory_review.py','report_study_review.py','screening_review.py'):
                helper_line=('    "output_io.py": "'+hashlib.sha256((ROOT/'output_io.py').read_bytes()).hexdigest()+'",'+os.linesep).encode()
                self.assertEqual(stdout.count(helper_line),1)
                stdout=stdout.replace(helper_line,b'',1)
            self.assertEqual((r.returncode,stdout,r.stderr),(case['returncode'],expected,case['stderr'].replace('\n',os.linesep).encode()),case['args'])

    def test_inclusive_multibyte_json_reaches_parser_for_all_fifteen(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'at-limit.json';p.write_bytes('"한"'.encode()+b' '*(LIMIT-5))
            for name in CHANGES:
                r=run_cli(name,*arguments(name,p))
                self.assertNotIn(b'input exceeds size limit',r.stderr,name)
                self.assertNotIn(b'JSONDecodeError',r.stderr,name)
