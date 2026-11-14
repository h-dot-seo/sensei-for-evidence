"""Exact separate import review, replay and complete exclusive file publication."""
import base64
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import screening_decision_batch as preview
import screening_decision_batch_apply as apply
import screening_decision_sheet as sheet
from tests.test_screening_decision_batch import fill
from tests.test_screening_sheet_intake import rewrite
from tests.test_screening_reviews import protocol

ROOT=Path(__file__).resolve().parents[1]


def review(p,raw):
    return dict(preview.prepare(p,raw)['review_document'],receipt_id='synthetic-batch-import',
                reviewer='Synthetic importer',reviewed_at='2026-11-14',rationale='Record exact supplied synthetic choices only.')


class DecisionBatchApplyTests(unittest.TestCase):
    def setUp(self):
        self.p=protocol();self.raw=rewrite(sheet.export_sheet(self.p,['r2','pending'])[0],fill)
        self.review=review(self.p,self.raw)

    def test_exact_review_then_replay_preserves_original_and_other_fields(self):
        original=copy.deepcopy(self.p)
        with patch('socket.socket',side_effect=AssertionError('no network')):
            app=apply.assemble(self.p,self.raw,self.review)
            verified=apply.verify(self.p,app)
        self.assertTrue(verified['valid']);self.assertEqual(self.p,original)
        self.assertEqual(base64.b64decode(app['receipt']['sheet_base64']),self.raw)
        candidate=app['protocol_candidate'];history=candidate['screening_decision_history']['receipts']
        self.assertEqual(len(history),2)
        self.assertEqual(history[1]['previous_receipt_sha256'],history[0]['receipt_sha256'])
        self.assertEqual({k:v for k,v in candidate.items() if k not in ('screening','screening_decision_history')},
                         {k:v for k,v in original.items() if k!='screening'})
        self.assertEqual(app,apply.assemble(self.p,self.raw,self.review))
        self.assertEqual(verified['protocol_candidate_sha256'],apply.digest(candidate))

    def test_blank_wrong_missing_extra_review_and_dates_rejected(self):
        bads=[preview.prepare(self.p,self.raw)['review_document'],dict(self.review,decision='approve'),
              dict(self.review,reviewed_at='2026-02-30'),dict(self.review,schema_version=True),
              dict(self.review,extra='unexpected'),dict(self.review,target_sha256='0'*64)]
        for key in ('receipt_id','reviewer','rationale'):
            bads.append(dict(self.review,**{key:' '}))
        for bad in bads:
            with self.subTest(bad=bad),self.assertRaises(ValueError):apply.assemble(self.p,self.raw,bad)

    def test_original_sheet_and_implementation_drift_refuse_old_review(self):
        p=copy.deepcopy(self.p);p['version']='changed'
        with self.assertRaises(ValueError):apply.assemble(p,self.raw,self.review)
        changed=rewrite(self.raw,lambda rows:rows[0].update(reason='Changed supplied choice'))
        with self.assertRaises(ValueError):apply.assemble(self.p,changed,self.review)
        with patch.object(preview,'_hashes',return_value={'changed':'implementation'}),self.assertRaises(ValueError):
            apply.assemble(self.p,self.raw,self.review)

    def test_replay_detects_all_receipt_candidate_target_and_raw_tampering(self):
        app=apply.assemble(self.p,self.raw,self.review)
        mutations=[lambda a:a['protocol_candidate'].update(version='changed'),
                   lambda a:a['receipt']['assertion'].update(rationale='changed'),
                   lambda a:a['receipt']['target'].update(sheet_sha256='0'*64),
                   lambda a:a['receipt'].update(receipt_sha256='0'*64),
                   lambda a:a.update(extra=True),lambda a:a.update(schema_version=True),
                   lambda a:a['receipt'].update(sheet_base64=a['receipt']['sheet_base64']+'?'),
                   lambda a:a['receipt'].update(sheet_base64=base64.b64encode(self.raw+b'\n').decode())]
        for mutate in mutations:
            changed=copy.deepcopy(app);mutate(changed)
            with self.assertRaises(ValueError):apply.verify(self.p,changed)
        p=copy.deepcopy(self.p);p['version']='changed'
        with self.assertRaises(ValueError):apply.verify(p,app)
        with patch.object(preview,'_hashes',return_value={'changed':'implementation'}),self.assertRaises(ValueError):apply.verify(self.p,app)

    def test_shared_guard_partial_duplicate_limits_budget_and_later_failure(self):
        for edit in [lambda rows:rows[0].update(reason=''),lambda rows:rows[1].update(receipt_id=rows[0]['receipt_id'])]:
            with self.assertRaises(ValueError):apply.assemble(self.p,rewrite(self.raw,edit),self.review)
        with patch.object(preview,'MAX_DECISIONS',1),self.assertRaises(ValueError):apply.assemble(self.p,self.raw,self.review)
        with patch.object(preview,'MAX_TARGET_BYTES',10),self.assertRaises(ValueError):apply.assemble(self.p,self.raw,self.review)
        with patch.object(apply,'MAX_APPLICATION_BYTES',10),self.assertRaises(ValueError):apply.assemble(self.p,self.raw,self.review)
        p=json.loads((ROOT/'examples/report-protocol.json').read_bytes());original=copy.deepcopy(p)
        raw=rewrite(sheet.export_sheet(p,['r2','r1'])[0],fill);raw=rewrite(raw,lambda rows:rows[1].update(decision='exclude'))
        with patch.object(preview.screening_decision,'assemble',wraps=preview.screening_decision.assemble) as guard:
            with self.assertRaises(ValueError):apply.assemble(p,raw,self.review)
            self.assertEqual(guard.call_count,2)
        self.assertEqual(p,original)

    def test_existing_history_is_prefix_and_cannot_reuse_sheet_or_receipt(self):
        app=apply.assemble(self.p,self.raw,self.review);candidate=app['protocol_candidate']
        with self.assertRaises(ValueError):apply.assemble(candidate,self.raw,self.review)
        raw=rewrite(sheet.export_sheet(candidate,['r1'])[0],fill)
        with self.assertRaises(ValueError):preview.prepare(candidate,raw)
        raw=rewrite(raw,lambda rows:rows[0].update(receipt_id='synthetic-new'))
        next_app=apply.assemble(candidate,raw,review(candidate,raw))
        self.assertEqual(next_app['protocol_candidate']['screening_decision_history']['receipts'][:2],candidate['screening_decision_history']['receipts'])

    def test_atomic_exclusive_writer_and_cleanup_on_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);out=d/'out.json';apply._write_new(out,b'complete')
            with self.assertRaises(FileExistsError):apply._write_new(out,b'other')
            self.assertEqual(out.read_bytes(),b'complete')
            other=d/'other.json'
            with patch.object(apply.os,'fsync',side_effect=OSError('synthetic write failure')),self.assertRaises(OSError):apply._write_new(other,b'not published')
            self.assertFalse(other.exists());self.assertEqual([p.name for p in d.iterdir()],['out.json'])
            with patch.object(apply.os,'link',side_effect=OSError('synthetic unsupported hardlink')),self.assertRaises(OSError):apply._write_new(other,b'not published')
            self.assertFalse(other.exists());self.assertEqual([p.name for p in d.iterdir()],['out.json'])
            with self.assertRaises(OSError):apply._write_new(d/'missing'/'out',b'none')
            try:link=d/'link';link.symlink_to(d/'absent')
            except (OSError,NotImplementedError):return
            with self.assertRaises(FileExistsError):apply._write_new(link,b'none')
            self.assertFalse((d/'absent').exists())

    def test_cli_verified_protocol_only_and_failed_actions_leave_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);p=d/'p.json';p.write_text(json.dumps(self.p),encoding='utf-8');s=d/'s.csv';s.write_bytes(self.raw)
            rev=d/'review.json';rev.write_text(json.dumps(self.review),encoding='utf-8');app=d/'app.json';out=d/'new.json'
            def command(*args):return subprocess.run([sys.executable,str(ROOT/'screening_decision_batch_apply.py'),*map(str,args)],capture_output=True)
            self.assertEqual(command('assemble',p,s,rev,'--output',app).returncode,0)
            result=command('verify',p,app,'--protocol-output',out);self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid']);self.assertEqual(json.loads(out.read_bytes()),json.loads(app.read_bytes())['protocol_candidate'])
            original=out.read_bytes();self.assertNotEqual(command('verify',p,app,'--protocol-output',out).returncode,0);self.assertEqual(out.read_bytes(),original)
            first=d/'a.json';second=d/'b.json';self.assertNotEqual(command('verify',p,app,'--protocol-output',first,'--output',second).returncode,0);self.assertFalse(first.exists());self.assertFalse(second.exists())
            changed=json.loads(app.read_bytes());changed['protocol_candidate']['version']='changed';app.write_text(json.dumps(changed),encoding='utf-8')
            self.assertNotEqual(command('verify',p,app,'--protocol-output',first).returncode,0);self.assertFalse(first.exists())
            rev.write_text(json.dumps(dict(self.review,target_sha256='0'*64)),encoding='utf-8')
            self.assertNotEqual(command('assemble',p,s,rev,'--output',first).returncode,0);self.assertFalse(first.exists())
            self.assertEqual(json.loads(p.read_bytes()),self.p)

    def test_documented_commands_verbatim(self):
        guide=(ROOT/'docs/SCREENING_DECISION_BATCH_APPLICATION.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory() as tmp:
            for line in blocks[0].splitlines():
                args=shlex.split(line);self.assertIn(args[1],['screening_decision_batch.py','screening_decision_batch_apply.py'])
                args=[str(Path(tmp)/x[7:]) if x.startswith('OUTPUT/') else x for x in args]
                result=subprocess.run([sys.executable,*args[1:]],cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(result.stdout);self.assertTrue(report['valid'])
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),['application.json','protocol.json','target.json'])
        tokens=shlex.split('python tool.py OUTPUT/x.json');replaced=[str(Path(r'C:\synthetic space')/x[7:]) if x.startswith('OUTPUT/') else x for x in tokens];self.assertIn(r'C:\synthetic space',replaced[-1])


if __name__=='__main__':unittest.main()
