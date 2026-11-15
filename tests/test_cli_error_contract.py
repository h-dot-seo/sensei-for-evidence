"""Synthetic remaining first-stage CLI errors and exact prior-release comparisons."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tests._cli import run_cli
from tests._shared_analysis_compat import prior_bytes as pre_analysis_bytes
import cli_errors

ROOT = Path(__file__).resolve().parents[1]
DIRECT = 'appraisal_source_review prisma_audit readiness_review receipt_intake report_review report_study_inventory report_study_inventory_review report_study_review screening_review search_manifest synthesis_review work_review'.split()
INDIRECT = 'views_export protocol_scaffold patent_links report_review_intake report_study_review_intake report_study_inventory_review_intake screening_sheet_intake screening_position_intake screening_decision_batch'.split()
CHANGES = json.loads((ROOT/'tests/cli_error_source_changes.json').read_bytes())


def args_for(name, path):
    if name == 'appraisal_source_review': return [path, path, path]
    if name == 'receipt_intake': return ['template', path]
    return [path]


def actual(root, name, args):
    return subprocess.run([sys.executable, str(root/(name+'.py')), *map(str,args)], capture_output=True, cwd=root)


class CliErrorContractTests(unittest.TestCase):
    def test_missing_parse_shape_and_usage_all_twelve(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'PRIVATE_PATH.json'
            for raw, category in [(None,'input-unreadable'),(b'{PRIVATE_PAYLOAD','input-not-json'),(b'\xffPRIVATE_PAYLOAD','input-not-json'),(b'null','input-invalid')]:
                if raw is not None:p.write_bytes(raw)
                for name in DIRECT:
                    with self.subTest(name=name,raw=raw):
                        result=run_cli(name+'.py',*args_for(name,p))
                        self.assertEqual(result.returncode,1)
                        self.assertEqual(result.stdout,b'')
                        self.assertIn((name.replace('_',' ')+' error: '+category+': ').encode(),result.stderr)
                        self.assertNotIn(b'PRIVATE_PATH',result.stderr)
                        self.assertNotIn(b'PRIVATE_PAYLOAD',result.stderr)
                        self.assertNotIn(b'Traceback',result.stderr)
                        self.assertEqual(len(result.stderr.splitlines()),1)
            for name in DIRECT:
                result=run_cli(name+'.py')
                self.assertEqual(result.returncode,2)
                self.assertEqual(result.stdout,b'')

    def test_all_appraisal_positions_and_receipt_fixture_static_labels(self):
        with tempfile.TemporaryDirectory() as td:
            good=Path(td)/'good.json';good.write_bytes(b'{}')
            bad=Path(td)/'PRIVATE_PATH.json';bad.write_bytes(b'{')
            for i,label in enumerate(['original protocol','application record','current protocol']):
                args=[good]*3;args[i]=bad
                result=run_cli('appraisal_source_review.py',*args)
                self.assertIn(('input-not-json: '+label+': ').encode(),result.stderr)
                self.assertEqual(result.stdout,b'')
            result=run_cli('receipt_intake.py','check',good,bad)
            self.assertIn(b'input-not-json: fixture:',result.stderr)
            self.assertEqual(result.stdout,b'')

    def test_prior_actual_success_negative_and_output_bytes(self):
        from tests.test_appraisal_source_review import AppraisalSourceReviewTests
        fixture=AppraisalSourceReviewTests();fixture.setUp()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old=root/'prior';old.mkdir()
            for p in ROOT.glob('*.py'):
                if p.name!='cli_errors.py':
                    data=CHANGES[p.name]['old'].encode() if p.name in CHANGES else pre_analysis_bytes(p.name)
                    (old/p.name).write_bytes(data)
            paths=[]
            for i,value in enumerate([fixture.original,fixture.application,fixture.current]):
                p=root/('appraisal'+str(i)+'.json');p.write_text(json.dumps(value));paths.append(p)
            protocol=ROOT/'examples/synthesis-review.json'
            for name in DIRECT:
                args=paths if name=='appraisal_source_review' else ['template',ROOT/'examples/adapter-protocol.json'] if name=='receipt_intake' else [protocol]
                for text in [False,True]:
                    if name=='receipt_intake' and text:continue
                    options=[*args,*(['--text'] if text else [])]
                    output_name = name in ('appraisal_source_review','report_review','report_study_inventory','report_study_inventory_review','report_study_review','screening_review') and not text
                    old_options=options
                    new_options=options
                    if output_name:
                        old_dest=root/('old-'+name+'.json');new_dest=root/('new-'+name+'.json')
                        old_options=[*options,'--output',old_dest];new_options=[*options,'--output',new_dest]
                    before=actual(old,name,old_options);after=actual(ROOT,name,new_options)
                    if output_name:
                        self.assertEqual(old_dest.read_bytes(),before.stdout.replace(os.linesep.encode(),b'\n'))
                        self.assertEqual(new_dest.read_bytes(),after.stdout.replace(os.linesep.encode(),b'\n'))
                    with self.subTest(name=name,text=text):
                        self.assertEqual(before.returncode,0,before.stderr)
                        self.assertEqual((after.returncode,after.stderr),(before.returncode,before.stderr))
                        if text:
                            if name == 'appraisal_source_review':
                                # Only the named top-level engine_sha256 display line differs.
                                prefix=b'"engine_sha256": '
                                a=before.stdout.splitlines(keepends=True);b=after.stdout.splitlines(keepends=True)
                                indices=[i for i,line in enumerate(a) if line.startswith(prefix)]
                                self.assertEqual(len(indices),1)
                                i=indices[0]
                                self.assertTrue(b[i].startswith(prefix))
                                self.assertIn(b'cli_errors.py',b[i])
                                b[i]=a[i];self.assertEqual(b,a)
                            else:self.assertEqual(after.stdout,before.stdout)
                        else:
                            left=json.loads(before.stdout);right=json.loads(after.stdout)
                            touched=[]
                            def restore(a,b,path=()):
                                if isinstance(a,dict) and isinstance(b,dict):
                                    if path and path[-1]=='engine_sha256':
                                        if 'cli_errors.py' in b:
                                            self.assertEqual(b.pop('cli_errors.py'),hashlib.sha256((ROOT/'cli_errors.py').read_bytes()).hexdigest());touched.append(path+('cli_errors.py',))
                                        for key in set(CHANGES)|{'research_status.py','review_handoff.py'}:
                                            if key in b:
                                                self.assertEqual(b[key],hashlib.sha256((ROOT/key).read_bytes()).hexdigest())
                                                self.assertEqual(a[key],hashlib.sha256(CHANGES[key]['old'].encode() if key in CHANGES else pre_analysis_bytes(key)).hexdigest())
                                                b[key]=a[key];touched.append(path+(key,))
                                    for key in a:
                                        if key in b:restore(a[key],b[key],path+(key,))
                                elif isinstance(a,list) and isinstance(b,list):
                                    for i,(x,y) in enumerate(zip(a,b)):restore(x,y,path+(i,))
                            restore(left,right)
                            self.assertEqual(right,left)
                            # Re-serialization preserves exact formatting and native newlines.
                            self.assertEqual((json.dumps(right,ensure_ascii=False,indent=2)+'\n').replace('\n',os.linesep).encode(),before.stdout)
            negative=root/'negative.json';negative.write_bytes(b'{}')
            args=['check',protocol,negative]
            a=actual(old,'receipt_intake',args);b=actual(ROOT,'receipt_intake',args)
            self.assertEqual((a.returncode,a.stdout,a.stderr),(b.returncode,b.stdout,b.stderr))
            self.assertEqual((b.returncode,b.stderr),(1,b''));self.assertTrue(b.stdout)
            for name in ['report_review','report_study_review','report_study_inventory','report_study_inventory_review','screening_review','appraisal_source_review']:
                dest=root/'PRIVATE_OUTPUT';dest.write_bytes(b'preserve')
                args=paths if name=='appraisal_source_review' else [protocol]
                result=actual(ROOT,name,[*args,'--output',dest])
                self.assertEqual(result.returncode,1,result.stderr)
                self.assertEqual(result.stdout,b'')
                self.assertIn(b'output-exists: output:',result.stderr)
                self.assertNotIn(b'PRIVATE_OUTPUT',result.stderr)
                self.assertEqual(dest.read_bytes(),b'preserve')

    def test_only_main_and_hash_changes_and_no_global_engine_change(self):
        expected=json.loads((ROOT/'tests/cli_error_prior_sources.json').read_bytes())
        self.assertEqual(set(CHANGES),{n+'.py' for n in DIRECT+INDIRECT})
        for name,digest in expected.items():
            data=CHANGES[name]['old'].encode() if name in CHANGES else pre_analysis_bytes(name)
            self.assertEqual(hashlib.sha256(data).hexdigest(),digest,name)
        for name,change in CHANGES.items():
            self.assertEqual(pre_analysis_bytes(name).decode(),change['new'])
            self.assertIn("'cli_errors.py'",change['new'])
            old=ast.parse(change['old']);new=ast.parse(change['new'])
            funcs=lambda t:{n.name:ast.get_source_segment(change['old'] if t is old else change['new'],n) for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
            a,b=funcs(old),funcs(new)
            for fn in a:
                if a[fn]!=b[fn] and fn!='main':
                    self.assertIn('cli_errors.py',b[fn],(name,fn))
        tree=ast.parse((ROOT/'cli_errors.py').read_text())
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('open','read_bytes','read_text','loads') for n in ast.walk(tree)))

    def test_transitive_export_maps_and_read_parse_call_order(self):
        import accounting_flow
        import records_csv
        import importlib
        import types
        from unittest.mock import patch
        from tests.test_report_reviews import protocol
        expected=hashlib.sha256((ROOT/'cli_errors.py').read_bytes()).hexdigest()
        for fn in (accounting_flow.export_flow,records_csv.export_records):
            receipt,raw=fn(protocol())
            self.assertEqual(receipt['engine_sha256']['cli_errors.py'],expected)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input.json';p.write_bytes(b'null')
            for name in DIRECT:
                if name=='appraisal_source_review':continue
                results=[]
                for old in (True,False):
                    module=types.ModuleType('observed_'+name)
                    module.__file__=str(ROOT/(name+'.py'))
                    source=CHANGES[name+'.py']['old' if old else 'new']
                    exec(compile(source,module.__file__,'exec'),module.__dict__)
                    events=[]
                    read,parse=module.read_bounded,module.parse_json
                    def traced_read(*args,**kwargs):
                        events.append(('read',args,kwargs));return read(*args,**kwargs)
                    def traced_parse(*args,**kwargs):
                        events.append(('parse',args,kwargs));return parse(*args,**kwargs)
                    module.read_bounded=traced_read;module.parse_json=traced_parse
                    import io
                    with patch.object(sys,'argv',[module.__file__,*map(str,args_for(name,p))]), patch.object(sys,'stdout',io.StringIO()),patch.object(sys,'stderr',io.StringIO()):
                        with self.assertRaises(SystemExit):module.main()
                    results.append(events)
                self.assertEqual(results[0],results[1],name)
                self.assertEqual([row[0] for row in results[1]],['read','parse'],name)

    def test_fixed_error_text_and_real_process_harness_equality(self):
        class Parser:
            def exit(self,code,message):raise RuntimeError(code,message)
        for error in [FileNotFoundError('PRIVATE_PATH'),KeyError('PRIVATE_KEY'),UnicodeError('PRIVATE_PAYLOAD')]:
            with self.assertRaises(RuntimeError) as caught:cli_errors.fail(Parser(),'tool','input','protocol',error)
            self.assertNotIn('PRIVATE_',str(caught.exception))
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'PRIVATE.json';p.write_bytes(b'{\r\n')
            for name in DIRECT:
                a=actual(ROOT,name,args_for(name,p));b=run_cli(name+'.py',*args_for(name,p))
                self.assertEqual((a.returncode,a.stdout,a.stderr),(b.returncode,b.stdout,b.stderr))


if __name__=='__main__':unittest.main()
