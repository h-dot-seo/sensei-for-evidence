"""Harness contract and small real-process guards; no scientific input or network."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests._cli import ROOT, run_cli


class CliHarnessTests(unittest.TestCase):
    def compare(self, script, *args, cwd=None, stdin=b'', encoding='utf-8'):
        env=dict(os.environ, PYTHONIOENCODING=encoding, COLUMNS='80')
        with patch.dict(os.environ, {'COLUMNS':'80'}):
            actual=run_cli(script,*args,cwd=cwd,stdin=stdin,encoding=encoding)
        expected=subprocess.run([sys.executable,str((ROOT/script).resolve()),*map(str,args)],
            cwd=cwd,input=stdin,capture_output=True,env=env,timeout=30)
        self.assertEqual((actual.returncode,actual.stdout,actual.stderr),
                         (expected.returncode,expected.stdout,expected.stderr))
        return actual

    def test_real_root_subcommand_help_and_parser_error_match_process(self):
        with tempfile.TemporaryDirectory() as cwd:
            self.compare('report_study_inventory_review_intake.py','--help',cwd=cwd)
            self.compare('report_study_inventory_review_intake.py','verify','--help',cwd=cwd)
            self.compare('report_study_inventory_review_intake.py','not-a-command',cwd=cwd)
            self.compare('evidence_workflow.py','--help',cwd=cwd)
            self.assertEqual(list(Path(cwd).iterdir()),[])

    def test_exit_and_bytes_semantics_match_process(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'synthetic_cli.py'
            for statement in ('pass','raise SystemExit()','raise SystemExit(0)','raise SystemExit(2)',
                              'raise SystemExit("synthetic error")'):
                p.write_text('import sys\nprint("ordinary output")\n'+statement+'\n',encoding='utf-8')
                with self.subTest(statement=statement):self.compare(p)
            p.write_text('import sys\nsys.stdout.buffer.write(sys.stdin.buffer.read())\nsys.stderr.buffer.write(b"error bytes\\x00")\n',encoding='utf-8')
            self.compare(p,stdin=b'line1\r\nline2\n\x00')

    def test_ascii_stream_reconfiguration_matches_real_process(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'synthetic_unicode.py'
            # Explicit root insertion is also supplied to the actual subprocess.
            p.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom json_io import configure_utf8_stdio\nconfigure_utf8_stdio()\nprint("합성 근거")\nprint("합성 오류",file=sys.stderr)\n',encoding='utf-8')
            self.compare(p,encoding='ascii')

    def test_surfaces_restored_after_success_exit_and_exception(self):
        argv,path=sys.argv,sys.path;before_argv=list(argv);before_path=list(path)
        streams=sys.stdin,sys.stdout,sys.stderr;cwd=os.getcwd();env=dict(os.environ)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'synthetic_state.py'
            prefix='import sys,os\nsys.argv.append("mutation")\nsys.path.append("mutation")\nos.environ["SYNTHETIC_CLI_HARNESS"]="mutation"\nos.chdir('+repr(td)+')\n'
            for ending in ('pass','raise SystemExit(2)','raise ValueError("synthetic failure")'):
                p.write_text(prefix+ending+'\n',encoding='utf-8')
                result=run_cli(p)
                self.assertIs(sys.argv,argv);self.assertIs(sys.path,path)
                self.assertEqual(sys.argv,before_argv);self.assertEqual(sys.path,before_path)
                self.assertEqual((sys.stdin,sys.stdout,sys.stderr),streams)
                self.assertEqual(os.getcwd(),cwd);self.assertEqual(dict(os.environ),env)
                if 'ValueError' in ending:
                    self.assertEqual(result.returncode,1)
                    self.assertIn(b'Traceback (most recent call last):',result.stderr)
                    self.assertTrue(result.stderr.rstrip().endswith(b'ValueError: synthetic failure'))
                    # Traceback frames intentionally differ from a new interpreter.

    def test_keyboard_interrupt_and_setup_failure_restore_surfaces(self):
        argv,path=sys.argv,sys.path;streams=sys.stdin,sys.stdout,sys.stderr;cwd=os.getcwd();env=dict(os.environ)
        with patch('runpy.run_path',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):
            run_cli('evidence_workflow.py')
        with tempfile.TemporaryDirectory() as td,self.assertRaises(FileNotFoundError):
            run_cli('evidence_workflow.py',cwd=Path(td)/'missing')
        self.assertIs(sys.argv,argv);self.assertIs(sys.path,path)
        self.assertEqual((sys.stdin,sys.stdout,sys.stderr),streams)
        self.assertEqual(os.getcwd(),cwd);self.assertEqual(dict(os.environ),env)

    def test_benchmark_contract_checks_equivalence_and_limits(self):
        from tests.benchmark_cli_help import measure
        result=measure([dict(script='report_study_inventory_review_intake.py',arguments=['--help'])],1)
        self.assertTrue(result['equivalent']);self.assertEqual(result['entries'],1)
        self.assertEqual(set(result['samples_seconds'][0]),{'repeat','subprocess','in_process'})
        for invalid in (0,11,True):
            with self.assertRaises(ValueError):measure([],invalid)

    def test_sequential_calls_do_not_reuse_captured_bytes(self):
        first=run_cli('report_study_inventory_review_intake.py','--help')
        second=run_cli('report_study_inventory_review_intake.py','not-a-command')
        third=run_cli('report_study_inventory_review_intake.py','--help')
        self.assertEqual((first.returncode,first.stdout,first.stderr),(third.returncode,third.stdout,third.stderr))
        self.assertEqual(second.returncode,2);self.assertFalse(second.stdout);self.assertTrue(second.stderr)


if __name__=='__main__':unittest.main()
