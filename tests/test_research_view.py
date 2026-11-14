"""Passive HTML review contracts, synthetic inputs only."""
import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import research_view as view
ROOT=Path(__file__).resolve().parents[1]

class Passive(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.links=[];self.styles=[];self.instyle=False;self.csp=None
    def handle_starttag(self,tag,attrs):
        assert tag in {'html','head','meta','title','style','body','header','p','h1','h2','h3','nav','ul','li','a','main','section','dl','dt','dd','details','summary','ol','span','div','table','thead','tr','th','tbody','td','pre','footer'}
        for k,v in attrs:
            assert not k.lower().startswith('on') and k not in {'src','style'}
            if k=='id':self.ids.append(v)
            if k=='href':assert v.startswith('#');self.links.append(v[1:])
        d=dict(attrs)
        if tag=='meta' and d.get('http-equiv')=='Content-Security-Policy':self.csp=d['content']
        if tag=='style':self.instyle=True
    def handle_endtag(self,tag):
        if tag=='style':self.instyle=False
    def handle_data(self,data):
        if self.instyle:self.styles.append(data)

class ViewTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/'examples/claim-comparison.json').read_text(encoding='utf-8'))
    def cli(self,*args):return subprocess.run([sys.executable,str(ROOT/'research_view.py'),*map(str,args)],capture_output=True,timeout=60)
    def test_passive_deterministic_and_immutable(self):
        before=copy.deepcopy(self.p)
        with patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.run',side_effect=AssertionError('process')):
            raw,receipt=view.render(self.p);again,_=view.render(self.p)
        self.assertEqual(raw,again);self.assertEqual(before,self.p)
        self.assertEqual(receipt['sha256'],hashlib.sha256(raw).hexdigest());self.assertEqual(receipt['bytes'],len(raw))
        parser=Passive();parser.feed(raw.decode());self.assertEqual(len(parser.ids),len(set(parser.ids)));self.assertTrue(set(parser.links)<=set(parser.ids))
        self.assertEqual(parser.csp,view.CSP);self.assertEqual(''.join(parser.styles),view.STYLE)
        self.assertIn('Census: NOT_ESTABLISHED',raw.decode());self.assertIn('Conclusion: NOT_READY',raw.decode())
    def test_injection_unicode_and_controls(self):
        self.p['question']='한국어 <script>alert(1)</script> <img src=x onerror=x> https://example.invalid \u202e'
        raw,_=view.render(self.p);parser=Passive();parser.feed(raw.decode())
        self.assertIn('한국어',raw.decode());self.assertIn('&lt;script&gt;',raw.decode());self.assertNotIn('\u202e',raw.decode())
    def test_snapshot_bindings_and_work_scope(self):
        a=view.snapshot(self.p);b=view.snapshot(self.p,'WP-TRANSLATION')
        self.assertEqual(a['handoff']['manual_review_steps'],b['handoff']['manual_review_steps'])
        self.assertEqual(a['protocol_sha256'],b['protocol_sha256']);self.assertIn('research_view.py',a['engine_sha256'])
        self.assertEqual(a['census_claim'],'NOT_ESTABLISHED');self.assertEqual(a['conclusion_readiness'],'NOT_READY')
    def test_output_budget_no_file(self):
        with patch.object(view,'MAX_OUTPUT_BYTES',500):
            with self.assertRaisesRegex(ValueError,'16 MiB'):view.render(self.p)
    def test_input_budget(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'p';p.write_bytes(b'12345')
            with patch.object(view,'MAX_PROTOCOL_BYTES',4):
                with self.assertRaisesRegex(ValueError,'byte limit'):view._read(p)
    def test_cli_output_receipt_and_existing_refusal(self):
        with tempfile.TemporaryDirectory(prefix='sensei html ') as td:
            out=Path(td)/'review.html';src=ROOT/'examples/claim-comparison.json';before=src.read_bytes()
            result=self.cli(src,'--output',out);self.assertEqual(result.returncode,0,result.stderr)
            receipt=json.loads(result.stdout);self.assertEqual(receipt['sha256'],hashlib.sha256(out.read_bytes()).hexdigest());self.assertEqual(before,src.read_bytes())
            saved=out.read_bytes();self.assertEqual(self.cli(src,'--output',out).returncode,1);self.assertEqual(saved,out.read_bytes())
    def test_dangling_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'link'
            try:out.symlink_to(Path(td)/'absent')
            except OSError:self.skipTest('symlink unavailable')
            with self.assertRaisesRegex(ValueError,'exists'):view._write_new(out,b'new')
    def test_unknown_work_and_invalid_input_no_output(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'view';src=ROOT/'examples/claim-comparison.json'
            self.assertEqual(self.cli(src,'--work-package','UNKNOWN','--output',out).returncode,1);self.assertFalse(out.exists())
            bad=Path(td)/'bad';bad.write_text('{bad',encoding='utf-8');self.assertEqual(self.cli(bad,'--output',out).returncode,1);self.assertFalse(out.exists())
    def test_stdout_html(self):
        result=self.cli(ROOT/'examples/claim-comparison.json');self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout.startswith(b'<!doctype html>'))
    def test_guide_commands(self):
        text=(ROOT/'docs/REVIEW_VIEWS.md').read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory(prefix='sensei guide ') as td:
            for block in re.findall(r'```sh\n(.*?)```',text,re.S):
                for line in block.strip().splitlines():
                    args=shlex.split(line);args=[a.replace('OUTPUT',td) for a in args];args[0]=sys.executable
                    result=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=60);self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((Path(td)/'claim-review.html').exists())

    def test_supplied_ready_and_challenges_stay_neutral(self):
        import readiness_intake
        p=json.loads((ROOT/'examples/synthesis-review.json').read_text())
        c=json.loads((ROOT/'examples/manual-readiness-candidates.json').read_text())
        c['readiness_assertions'][0].update(conclusion_readiness='READY',evidence_sufficiency='UNASSESSED',reopening=None)
        review=readiness_intake.prepare(p,c)['review_document']
        review.update(receipt_id='fictional-html-review',decision='import_readiness_assertions',reviewer='Fictional reviewer',reviewed_at='2026-11-08',rationale='Supplied fictional assertion only.')
        app=readiness_intake.assemble(p,c,review)
        p=app['protocol_candidate']
        raw,_=view.render(p);text=raw.decode()
        self.assertNotIn('READY',text.split('<section id="assertions">')[0].replace('NOT_READY',''))
        self.assertIn('Supplied human assertions only',text)
        self.assertEqual(view.snapshot(p)['conclusion_readiness'],'NOT_READY')
        challenged=copy.deepcopy(self.p)
        challenged['challenges']=json.loads((ROOT/'examples/manual-challenge-candidates.json').read_text())['challenges']
        raw,_=view.render(challenged);self.assertIn('challenge_ledger',raw.decode())

    def test_main_budget_failure_no_file_or_stdout(self):
        import io
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'not-created.html';capture=io.StringIO()
            with patch.object(sys,'argv',['research_view.py',str(ROOT/'examples/claim-comparison.json'),'--output',str(out)]),patch.object(view,'MAX_OUTPUT_BYTES',500),patch.object(view,'configure_utf8_stdio'),patch('sys.stdout',capture),patch('sys.stderr',io.StringIO()):
                with self.assertRaises(SystemExit) as error:view.main()
            self.assertEqual(error.exception.code,1);self.assertFalse(out.exists());self.assertEqual(capture.getvalue(),'')
