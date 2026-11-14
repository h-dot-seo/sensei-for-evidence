"""Synthetic append-only full-text review intake with exact review/replay gates."""
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

from evidence_workflow import run
from prisma_reports import report_flow
import report_review
import report_review_intake as intake

ROOT=Path(__file__).resolve().parents[1]


def protocol():return json.loads((ROOT/'examples/report-reviews.json').read_bytes())


def document(p,rid='report-one'):
    row=report_review.template(p,rid)['report_reviews'][0]
    row.update(review_id='synthetic-new-position',reviewer='Synthetic new reader',reviewed_at='2026-11-14',
               decision='unclear',rationale='Synthetic supplied position, not an eligibility decision.',
               reviewed_locator='synthetic:page-1 supplied coverage')
    return dict(schema_version=1,report_reviews=[row])


def review(p,doc):
    return dict(intake.prepare(p,doc)['review_document'],receipt_id='synthetic-import',reviewer='Synthetic importer',
                reviewed_at='2026-11-14',rationale='Record exact supplied synthetic positions only.')


class ReportReviewIntakeTests(unittest.TestCase):
    def setUp(self):self.p=protocol();self.doc=document(self.p);self.review=review(self.p,self.doc)

    def test_append_exact_replay_and_all_original_fields_preserved(self):
        original=copy.deepcopy(self.p);supplied=copy.deepcopy(self.doc)
        with patch('socket.socket',side_effect=AssertionError('no network')):
            app=intake.assemble(self.p,self.doc,self.review);result=intake.verify(self.p,app)
        self.assertTrue(result['valid']);self.assertEqual(self.p,original);self.assertEqual(self.doc,supplied)
        candidate=app['protocol_candidate'];prefix=len(original['report_reviews'])
        self.assertEqual(candidate['report_reviews'][:prefix],original['report_reviews'])
        self.assertEqual(candidate['report_reviews'][prefix:],self.doc['report_reviews'])
        self.assertEqual({k:v for k,v in candidate.items() if k!='report_reviews'},{k:v for k,v in original.items() if k!='report_reviews'})
        self.assertEqual(run(candidate)['flow'],run(original)['flow'])
        self.assertEqual(report_flow(candidate)['report_flow'],report_flow(original)['report_flow'])
        self.assertEqual(app,intake.assemble(self.p,self.doc,self.review))
        self.assertEqual(result['protocol_candidate_sha256'],intake.digest(candidate))

    def test_first_append_without_prior_ledger_and_explicit_empty(self):
        for explicit in (False,True):
            p=copy.deepcopy(self.p)
            if explicit:p['report_reviews']=[]
            else:p.pop('report_reviews')
            original=copy.deepcopy(p);doc=document(p)
            app=intake.assemble(p,doc,review(p,doc))
            self.assertTrue(intake.verify(p,app)['valid'])
            self.assertEqual(p,original)
            self.assertEqual(app['protocol_candidate']['report_reviews'],doc['report_reviews'])

    def test_null_document_digest_remains_explicit_unbound(self):
        doc=document(self.p,'report-two');result=intake.prepare(self.p,doc)
        target=result['target']['selected_report_targets'][0]
        self.assertEqual(target['source_binding_state'],'DOCUMENT_BYTES_UNBOUND')
        self.assertTrue(any(s['document_sha256'] is None for s in target['source_basis']['report_sources']))
        app=intake.assemble(self.p,doc,review(self.p,doc))
        self.assertEqual(app['protocol_candidate']['report_sources'],self.p['report_sources'])
        self.assertEqual(result['document_bytes_verification'],'NOT_PERFORMED')

    def test_no_descriptor_pending_unavailable_and_unknown_rejected(self):
        targets={t['report_id']:t for t in report_review.review(self.p)['report_targets']}
        for rid in ['report-three','report-four','report-five','unknown']:
            doc=copy.deepcopy(self.doc);doc['report_reviews'][0].update(report_id=rid,source_basis_sha256=targets[rid]['source_basis_sha256'] if rid in targets else '0'*64)
            with self.subTest(rid=rid),self.assertRaises(ValueError):intake.prepare(self.p,doc)

    def test_source_drift_stale_hash_rejected_not_refreshed(self):
        mutations=[lambda p:p['report_sources'][0].update(document_version='changed'),
                   lambda p:p['report_sources'][0].update(document_sha256='b'*64),
                   lambda p:p['inclusion_criteria'].append('changed'),lambda p:p['searches'][0].update(query='changed')]
        for mutate in mutations:
            p=copy.deepcopy(self.p);mutate(p);original=copy.deepcopy(p)
            with self.assertRaises(ValueError):intake.prepare(p,self.doc)
            self.assertEqual(p,original)
        bad=copy.deepcopy(self.doc);bad['report_reviews'][0]['source_basis_sha256']='0'*64
        with self.assertRaises(ValueError):intake.prepare(self.p,bad)

    def test_existing_stale_positions_preserved_and_no_supersession(self):
        before=report_review.review(self.p)['review_ledger']
        self.assertTrue(any(row['source_match_status']=='STALE_SOURCE' for row in before))
        app=intake.assemble(self.p,self.doc,self.review)
        after=report_review.review(app['protocol_candidate'])['review_ledger']
        self.assertEqual(before,after[:len(before)])
        with self.assertRaises(ValueError):intake.prepare(app['protocol_candidate'],self.doc)
        changed=copy.deepcopy(self.doc);changed['report_reviews'][0]['review_id']='new-id'
        with self.assertRaises(ValueError):intake.prepare(app['protocol_candidate'],changed)

    def test_candidate_schema_partial_dates_choices_and_duplicates(self):
        for key,value in [('rationale',''),('reviewer',' '),('decision','accept'),('reviewed_at','11/14/2026'),('reviewed_at','2026-02-30')]:
            doc=copy.deepcopy(self.doc);doc['report_reviews'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):intake.prepare(self.p,doc)
        for doc in [dict(self.doc,extra=True),dict(self.doc,schema_version=True),dict(schema_version=1,report_reviews=[]),dict(schema_version=1,report_reviews=[None])]:
            with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        duplicate=copy.deepcopy(self.doc);duplicate['report_reviews']*=2
        with self.assertRaises(ValueError):intake.prepare(self.p,duplicate)
        doc=copy.deepcopy(self.doc);doc['report_reviews'][0]['extra']='unknown'
        with self.assertRaises(ValueError):intake.prepare(self.p,doc)

    def test100_limit_and_byte_budgets(self):
        doc=copy.deepcopy(self.doc);doc['report_reviews']=[]
        for i in range(100):
            row=dict(self.doc['report_reviews'][0],review_id='synthetic-'+str(i),reviewer='Synthetic reader '+str(i));doc['report_reviews'].append(row)
        self.assertEqual(len(intake.prepare(self.p,doc)['target']['appended_positions']),100)
        doc['report_reviews'].append(dict(doc['report_reviews'][-1],review_id='extra',reviewer='extra'))
        with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        for name in ('MAX_PROTOCOL_BYTES','MAX_CANDIDATE_BYTES','MAX_APPLICATION_BYTES'):
            with patch.object(intake,name,10),self.assertRaises(ValueError):intake.prepare(self.p,self.doc)

    def test_separate_review_blank_wrong_stale_implementation_and_protocol(self):
        blank=intake.prepare(self.p,self.doc)['review_document']
        for doc in [blank,dict(self.review,decision='approve'),dict(self.review,target_sha256='0'*64),dict(self.review,schema_version=True),dict(self.review,reviewed_at='bad'),dict(self.review,extra=True)]:
            with self.assertRaises(ValueError):intake.assemble(self.p,self.doc,doc)
        p=copy.deepcopy(self.p);p['version']='changed unrelated input'
        # Source still matches, but an old import approval must not rebase to the new protocol.
        self.assertTrue(intake.prepare(p,self.doc))
        with self.assertRaises(ValueError):intake.assemble(p,self.doc,self.review)
        with patch.object(intake,'_hashes',return_value={'changed':'implementation'}),self.assertRaises(ValueError):intake.assemble(self.p,self.doc,self.review)

    def test_whole_protocol_validator_gate_is_not_bypassed(self):
        p=copy.deepcopy(self.p);p['reports'][3]['retrieval']='invalid'
        with self.assertRaises(ValueError):intake.prepare(p,self.doc)
        original=copy.deepcopy(self.p)
        actual=report_review.review
        def fail_candidate(p,*args,**kwargs):
            if len(p.get('report_reviews',[]))>len(self.p['report_reviews']):raise ValueError('synthetic candidate guard failure')
            return actual(p,*args,**kwargs)
        with patch.object(intake.report_review,'review',side_effect=fail_candidate),self.assertRaises(ValueError):intake.assemble(self.p,self.doc,self.review)
        self.assertEqual(self.p,original)

    def test_replay_detects_all_mutations(self):
        app=intake.assemble(self.p,self.doc,self.review)
        mutations=[lambda a:a['protocol_candidate'].update(version='changed'),lambda a:a['receipt']['assertion'].update(rationale='changed'),
                   lambda a:a['receipt']['candidate_document']['report_reviews'][0].update(rationale='changed'),
                   lambda a:a['receipt']['target'].update(input_protocol_sha256='0'*64),lambda a:a['receipt'].update(receipt_sha256='0'*64),
                   lambda a:a.update(schema_version=True),lambda a:a.update(extra='unknown')]
        for mutate in mutations:
            changed=copy.deepcopy(app);mutate(changed)
            with self.assertRaises(ValueError):intake.verify(self.p,changed)
        with patch.object(intake,'_hashes',return_value={'changed':'implementation'}),self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_cli_no_overwrite_no_invalid_output_and_single_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);p=d/'p.json';p.write_text(json.dumps(self.p),encoding='utf-8');doc=d/'positions.json';doc.write_text(json.dumps(self.doc),encoding='utf-8');rev=d/'review.json';rev.write_text(json.dumps(self.review),encoding='utf-8')
            def call(*args):return subprocess.run([sys.executable,str(ROOT/'report_review_intake.py'),*map(str,args)],capture_output=True)
            app=d/'application.json';result=call('assemble',p,doc,rev,'--output',app);self.assertEqual(result.returncode,0,result.stderr)
            out=d/'new.json';result=call('verify',p,app,'--protocol-output',out);self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['valid'])
            saved=out.read_bytes();self.assertNotEqual(call('verify',p,app,'--protocol-output',out).returncode,0);self.assertEqual(out.read_bytes(),saved)
            a=d/'a.json';b=d/'b.json';self.assertNotEqual(call('verify',p,app,'--protocol-output',a,'--output',b).returncode,0);self.assertFalse(a.exists());self.assertFalse(b.exists())
            bad=json.loads(app.read_bytes());bad['protocol_candidate']['version']='changed';app.write_text(json.dumps(bad),encoding='utf-8')
            self.assertNotEqual(call('verify',p,app,'--protocol-output',a).returncode,0);self.assertFalse(a.exists())
            bad=copy.deepcopy(self.doc);bad['report_reviews'][0]['rationale']='';doc.write_text(json.dumps(bad),encoding='utf-8')
            self.assertNotEqual(call('target',p,doc,'--output',a).returncode,0);self.assertFalse(a.exists())
            self.assertEqual(json.loads(p.read_bytes()),self.p)

    def test_documented_commands_verbatim(self):
        guide=(ROOT/'docs/REPORT_REVIEW_INTAKE.md').read_text(encoding='utf-8');blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory() as tmp:
            for line in blocks[0].splitlines():
                args=shlex.split(line);self.assertIn(args[1],['report_review.py','report_review_intake.py']);args=[str(Path(tmp)/x[7:]) if x.startswith('OUTPUT/') else x for x in args]
                result=subprocess.run([sys.executable,*args[1:]],cwd=ROOT,capture_output=True);self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid']);self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),['application.json','protocol.json','scaffold.json','target.json'])
        tokens=shlex.split('python tool.py OUTPUT/x.json');replaced=[str(Path(r'C:\synthetic space')/x[7:]) if x.startswith('OUTPUT/') else x for x in tokens];self.assertIn(r'C:\synthetic space',replaced[-1])


if __name__=='__main__':unittest.main()
