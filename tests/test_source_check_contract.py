"""Local observations may return negative reports and write files; never permission."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import artifact_review as ar
import report_source_check as sc
import result_passage_check as pc
import command_contract

ROOT=Path(__file__).resolve().parents[1]


class SourceContractTests(unittest.TestCase):
    def cases(self, folder):
        root=Path(folder)/'sources';root.mkdir()
        files=[('examples/local-artifacts/receipt-review.txt','receipt-review.txt'),
               ('examples/local-sources/fictional-report.txt','fictional-report.txt'),
               ('examples/result-passage-source.txt','result-passage-source.txt')]
        for source,name in files:shutil.copyfile(ROOT/source,root/name)
        protocol=lambda name:str(ROOT/'examples'/name)
        a=[protocol('artifact-review-protocol.json'),protocol('artifact-review-manifest.json'),'--root',str(root)]
        s=['check',protocol('report-source-check-protocol.json'),protocol('report-source-check-manifest.json'),'--root',str(root)]
        p=[protocol('result-passage-protocol.json'),protocol('result-passage-candidates.json'),protocol('result-passage-manifest.json'),'--root',str(root)]
        return root,[(ar,None,a),(sc,'check',s),(pc,'catalog',['catalog',*p]),(pc,'check',['check',*p])]

    def cli(self,module,args):
        return subprocess.run([sys.executable,'-B',str(ROOT/(module.__name__+'.py')),*map(str,args)],capture_output=True,timeout=30)

    def test_exact_six_profiles_and_unknown_remainder(self):
        result=command_contract.contract();rows=[r for r in result['commands'] if r['script'] in ('artifact_review.py','report_source_check.py','result_passage_check.py')]
        self.assertEqual(len(rows),6);self.assertEqual(result['coverage']['reviewed_effects'],32)
        self.assertEqual(sum(r['effect_status']=='NOT_REVIEWED' for r in result['commands']),143)
        for row in rows:
            e=row['effects'];self.assertEqual(e['network'],'none')
            self.assertEqual('--root' in e['inputs'],row['subcommand']!='template')
            self.assertEqual(bool(e['outputs']),row['script']!='artifact_review.py')
            self.assertEqual(e['negative_report'] is None,row['subcommand']=='template')
            if e['negative_report']:
                self.assertEqual(e['negative_report']['exit_code'],1)
                self.assertIn('fail closed',e['notes'])
                self.assertIn('Locators are inert',e['notes'])

    def test_templates_create_new_metadata_only_without_source_access(self):
        for module,inputs in [(sc,['report-source-check-protocol.json']),(pc,['result-passage-protocol.json','result-passage-candidates.json'])]:
            for text in (False,True):
                with tempfile.TemporaryDirectory() as td:
                    output=Path(td)/'new.json';args=['template',*[str(ROOT/'examples'/n) for n in inputs],'--output',str(output)]+(['--text'] if text else [])
                    stdout=io.StringIO();stderr=io.StringIO()
                    with patch.object(sys,'argv',[module.__name__+'.py',*args]), patch.object(module,'open_root',side_effect=AssertionError('template must not read sources')), contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                        module.main()
                    self.assertTrue(output.is_file());json.loads(output.read_bytes());self.assertTrue(stdout.getvalue());self.assertEqual(stderr.getvalue(),'')
                    before=output.read_bytes();again=self.cli(module,args)
                    self.assertEqual(again.returncode,1);self.assertEqual(again.stdout,b'');self.assertEqual(output.read_bytes(),before)

    def test_real_source_results_output_and_platform_refusal_channels(self):
        for mismatch in (False,True):
            with tempfile.TemporaryDirectory(prefix='source contract ') as td:
                root,cases=self.cases(td)
                if mismatch:
                    for path in root.iterdir():path.write_bytes(b'synthetic changed bytes')
                before={p.name:p.read_bytes() for p in root.iterdir()}
                for index,(module,sub,args) in enumerate(cases):
                    for text in ((False,) if module is ar else (False,True)):
                        output=Path(td)/('out'+str(index)+str(text)+'.json')
                        command=args+([] if module is ar else ['--output',str(output)])+(['--text'] if text else [])
                        with self.subTest(module=module.__name__,sub=sub,mismatch=mismatch,text=text):
                            result=self.cli(module,command)
                            if not ar.secure_open_supported():
                                self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertTrue(result.stderr);self.assertFalse(output.exists())
                            else:
                                self.assertEqual(result.returncode,1 if mismatch else 0,result.stderr)
                                self.assertEqual(result.stderr,b'');self.assertTrue(result.stdout)
                                report=json.loads(result.stdout) if module is ar else json.loads(output.read_bytes())
                                field='all_requested_passages_match' if module is pc and sub=='check' else 'all_requested_bytes_match'
                                self.assertEqual(report[field],not mismatch)
                                if not text and module is not ar:self.assertEqual(json.loads(result.stdout),report)
                self.assertEqual({p.name:p.read_bytes() for p in root.iterdir()},before)

    def test_secure_access_unavailable_refuses_before_root_on_every_platform(self):
        with tempfile.TemporaryDirectory() as td:
            root,cases=self.cases(td)
            for index,(module,sub,args) in enumerate(cases):
                output=Path(td)/('new'+str(index)+'.json')
                command=args+([] if module is ar else ['--output',str(output)])
                stdout=io.StringIO();stderr=io.StringIO()
                with patch.object(sys,'argv',[module.__name__+'.py',*command]), patch.object(module,'secure_open_supported',return_value=False),patch.object(module,'open_root',side_effect=AssertionError('no source root access')),contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr),self.assertRaises(SystemExit) as caught:
                    module.main()
                self.assertEqual(caught.exception.code,1);self.assertEqual(stdout.getvalue(),'');self.assertTrue(stderr.getvalue());self.assertFalse(output.exists())

    def test_caught_input_error_is_not_negative_report_or_created_file(self):
        with tempfile.TemporaryDirectory() as td:
            _,cases=self.cases(td);bad=Path(td)/'bad.json';bad.write_bytes(b'{')
            for index,(module,sub,args) in enumerate(cases):
                args=list(args);args[0 if module is ar else 1]=str(bad)
                output=Path(td)/('bad-out'+str(index)+'.json')
                if module is not ar:args += ['--output',str(output)]
                result=self.cli(module,args)
                self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertTrue(result.stderr);self.assertFalse(output.exists())

    def test_changed_checker_bytes_make_the_contract_stale(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'docs').mkdir()
            for p in ROOT.glob('*.py'):shutil.copyfile(p,root/p.name)
            shutil.copyfile(ROOT/command_contract.REGISTRY,root/command_contract.REGISTRY)
            with patch.object(command_contract,'ROOT',root):
                for name in ('artifact_review.py','report_source_check.py','result_passage_check.py'):
                    path=root/name;raw=path.read_bytes();path.write_bytes(raw+b'\n')
                    with self.assertRaises(ValueError):command_contract.contract()
                    path.write_bytes(raw)
                self.assertEqual(command_contract.contract()['coverage']['reviewed_effects'],32)
