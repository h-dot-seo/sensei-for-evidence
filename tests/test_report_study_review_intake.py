"""Synthetic exact-pair positions, explicit source subsets and reviewed append/replay."""
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
import report_study_review
import report_study_review_intake as intake

ROOT=Path(__file__).resolve().parents[1]


def protocol():return json.loads((ROOT/'examples/report-study-reviews.json').read_bytes())


def document(p,rid='report-one',sid='study-A',sources=None):
    row=report_study_review.template(p,rid,sid)['report_study_reviews'][0]
    row.update(review_id='synthetic-pair-new',reviewer='Synthetic pair reader',reviewed_at='2026-11-14',decision='exclude',
               rationale='Synthetic supplied exclusion position only.',reviewed_locator='synthetic:page-1',
               reviewed_source_ids=['source-main'] if sources is None else sources)
    return dict(schema_version=1,report_study_reviews=[row])


def review(p,doc):
    return dict(intake.prepare(p,doc)['review_document'],receipt_id='synthetic-pair-import',reviewer='Synthetic importer',
                reviewed_at='2026-11-14',rationale='Record supplied exact pair positions only.')


class ReportStudyReviewIntakeTests(unittest.TestCase):
    def setUp(self):self.p=protocol();self.doc=document(self.p);self.review=review(self.p,self.doc)

    def test_exact_pair_append_preserves_results_membership_and_orphans(self):
        original=copy.deepcopy(self.p);before=report_study_review.review(self.p)
        self.assertTrue(before['orphan_review_assertions'])
        with patch('socket.socket',side_effect=AssertionError('no network')):
            app=intake.assemble(self.p,self.doc,self.review);verified=intake.verify(self.p,app)
        self.assertTrue(verified['valid']);self.assertEqual(self.p,original)
        candidate=app['protocol_candidate'];prefix=len(self.p['report_study_reviews'])
        self.assertEqual(candidate['report_study_reviews'][:prefix],self.p['report_study_reviews'])
        self.assertEqual(candidate['report_study_reviews'][prefix:],self.doc['report_study_reviews'])
        self.assertEqual({k:v for k,v in candidate.items() if k!='report_study_reviews'},{k:v for k,v in self.p.items() if k!='report_study_reviews'})
        self.assertEqual(run(candidate)['flow'],run(original)['flow'])
        self.assertEqual(report_flow(candidate)['report_flow'],report_flow(original)['report_flow'])
        after=report_study_review.review(candidate)
        self.assertEqual(before['orphan_review_assertions'],after['orphan_review_assertions'])
        self.assertEqual(before['review_ledger'],after['review_ledger'][:prefix])
        pair=next(r for r in after['membership_review_ledger'] if (r['report_id'],r['study_id'])==('report-one','study-A'))
        self.assertIn('CURRENT_EXCLUDE_POSITION_WITH_RESULT_ROWS',pair['comparison_cues'])
        self.assertEqual(app,intake.assemble(self.p,self.doc,self.review))

    def test_source_subset_must_be_explicit_same_report_never_selected(self):
        blank=report_study_review.template(self.p,'report-one','study-A')['report_study_reviews'][0]
        self.assertIsNone(blank['reviewed_source_ids'])
        for sources in [None,[],['source-main','source-main'],['missing'],['source-unbound'],[None],[True],'source-main']:
            doc=copy.deepcopy(self.doc);doc['report_study_reviews'][0]['reviewed_source_ids']=sources
            with self.subTest(sources=sources),self.assertRaises(ValueError):intake.prepare(self.p,doc)
        doc=document(self.p,sources=['source-supplement','source-main']);app=intake.assemble(self.p,doc,review(self.p,doc))
        self.assertEqual(app['protocol_candidate']['report_study_reviews'][-1]['reviewed_source_ids'],['source-supplement','source-main'])

    def test_unknown_orphan_and_source_absence_rejected(self):
        targets={(t['report_id'],t['study_id']):t for t in report_study_review.review(self.p)['membership_targets']}
        for sid in ['study-C','unknown']:
            doc=copy.deepcopy(self.doc);doc['report_study_reviews'][0]['study_id']=sid
            if ('report-one',sid) in targets:doc['report_study_reviews'][0]['source_basis_sha256']=targets[('report-one',sid)]['source_basis_sha256']
            with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        p=copy.deepcopy(self.p);p['report_sources']=[]
        basis=next(t for t in report_study_review.review(p)['membership_targets'] if (t['report_id'],t['study_id'])==('report-one','study-A'))['source_basis_sha256']
        doc=copy.deepcopy(self.doc);doc['report_study_reviews'][0]['source_basis_sha256']=basis
        with self.assertRaises(ValueError):intake.prepare(p,doc)

    def test_unbound_document_remains_unbound_and_report_snapshot_retained_once(self):
        doc=document(self.p,'report-two','study-A',['source-unbound']);target=intake.prepare(self.p,doc)['target']
        self.assertEqual(target['selected_membership_targets'][0]['source_binding_state'],'DOCUMENT_BYTES_UNBOUND')
        self.assertIsNone(target['selected_report_targets'][0]['source_basis']['report_sources'][0]['document_sha256'])
        doc=copy.deepcopy(self.doc);other=document(self.p,'report-one','study-B')['report_study_reviews'][0];other.update(review_id='synthetic-b',reviewer='Synthetic reader B');doc['report_study_reviews'].append(other)
        target=intake.prepare(self.p,doc)['target'];self.assertEqual(len(target['selected_membership_targets']),2);self.assertEqual(len(target['selected_report_targets']),1)

    def test_source_drift_not_renewed_and_unselected_source_still_binds(self):
        p=copy.deepcopy(self.p);p['report_sources'][1]['document_version']='changed unselected supplement'
        with self.assertRaises(ValueError):intake.prepare(p,self.doc)
        doc=copy.deepcopy(self.doc);doc['report_study_reviews'][0]['source_basis_sha256']='0'*64
        with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        p=copy.deepcopy(self.p);p['version']='unrelated'
        self.assertTrue(intake.prepare(p,self.doc))
        with self.assertRaises(ValueError):intake.assemble(p,self.doc,self.review)

    def test_duplicate_tuple_no_supersession_and_literal_identifiers(self):
        app=intake.assemble(self.p,self.doc,self.review);p=app['protocol_candidate']
        with self.assertRaises(ValueError):intake.prepare(p,self.doc)
        changed=copy.deepcopy(self.doc);changed['report_study_reviews'][0]['review_id']='new-id'
        with self.assertRaises(ValueError):intake.prepare(p,changed)
        changed['report_study_reviews'][0]['reviewer']='Synthetic different reader';self.assertTrue(intake.prepare(p,changed))
        changed['report_study_reviews'][0]['study_id']=' study-A'
        with self.assertRaises(ValueError):intake.prepare(self.p,changed)

    def test_partial_schema_dates_choices_and_limits(self):
        for key,value in [('rationale',''),('decision','accept'),('reviewed_at','2026-02-30'),('reviewed_at','11/14/2026')]:
            doc=copy.deepcopy(self.doc);doc['report_study_reviews'][0][key]=value
            with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        for doc in [dict(self.doc,extra=True),dict(self.doc,schema_version=True),dict(schema_version=1,report_study_reviews=[])]:
            with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        doc=copy.deepcopy(self.doc);doc['report_study_reviews']=[dict(self.doc['report_study_reviews'][0],review_id='synthetic-'+str(i),reviewer='Synthetic '+str(i)) for i in range(100)]
        self.assertEqual(len(intake.prepare(self.p,doc)['target']['appended_positions']),100)
        doc['report_study_reviews'].append(copy.deepcopy(doc['report_study_reviews'][0]))
        with self.assertRaises(ValueError):intake.prepare(self.p,doc)
        for name in ('MAX_PROTOCOL_BYTES','MAX_CANDIDATE_BYTES','MAX_APPLICATION_BYTES'):
            with patch.object(intake,name,10),self.assertRaises(ValueError):intake.prepare(self.p,self.doc)

    def test_first_ledger_append_and_explicit_empty(self):
        for explicit in (False,True):
            p=copy.deepcopy(self.p)
            if explicit:p['report_study_reviews']=[]
            else:p.pop('report_study_reviews')
            original=copy.deepcopy(p);doc=document(p);app=intake.assemble(p,doc,review(p,doc))
            self.assertTrue(intake.verify(p,app)['valid']);self.assertEqual(p,original)
            self.assertEqual(app['protocol_candidate']['report_study_reviews'],doc['report_study_reviews'])

    def test_shared_import_review_and_exact_replay(self):
        for bad in [intake.prepare(self.p,self.doc)['review_document'],dict(self.review,decision='import_report_reviews'),dict(self.review,schema_version=True),dict(self.review,target_sha256='0'*64),dict(self.review,extra='x')]:
            with self.assertRaises(ValueError):intake.assemble(self.p,self.doc,bad)
        app=intake.assemble(self.p,self.doc,self.review)
        for mutate in [lambda a:a['protocol_candidate'].update(version='changed'),lambda a:a['receipt']['assertion'].update(rationale='changed'),
                       lambda a:a['receipt']['candidate_document']['report_study_reviews'][0].update(reviewed_source_ids=['source-supplement']),
                       lambda a:a['receipt']['target'].update(input_protocol_sha256='0'*64),lambda a:a.update(schema_version=True),lambda a:a.update(extra='x')]:
            changed=copy.deepcopy(app);mutate(changed)
            with self.assertRaises(ValueError):intake.verify(self.p,changed)
        with patch.object(intake,'_hashes',return_value={'changed':'implementation'}),self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_whole_validator_failure_preserves_input(self):
        original=copy.deepcopy(self.p);actual=report_study_review.review
        def fail_candidate(p,*args,**kwargs):
            if len(p.get('report_study_reviews',[]))>len(self.p['report_study_reviews']):raise ValueError('synthetic candidate guard')
            return actual(p,*args,**kwargs)
        with patch.object(intake.report_study_review,'review',side_effect=fail_candidate),self.assertRaises(ValueError):intake.assemble(self.p,self.doc,self.review)
        self.assertEqual(self.p,original)

    def test_cli_replay_and_failed_output_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);p=d/'p.json';p.write_text(json.dumps(self.p),encoding='utf-8');doc=d/'positions.json';doc.write_text(json.dumps(self.doc),encoding='utf-8');rev=d/'review.json';rev.write_text(json.dumps(self.review),encoding='utf-8')
            def call(*args):return subprocess.run([sys.executable,str(ROOT/'report_study_review_intake.py'),*map(str,args)],capture_output=True)
            app=d/'application.json';result=call('assemble',p,doc,rev,'--output',app);self.assertEqual(result.returncode,0,result.stderr)
            out=d/'new.json';result=call('verify',p,app,'--protocol-output',out);self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['valid'])
            saved=out.read_bytes();self.assertNotEqual(call('verify',p,app,'--protocol-output',out).returncode,0);self.assertEqual(out.read_bytes(),saved)
            a=d/'a.json';b=d/'b.json';self.assertNotEqual(call('verify',p,app,'--protocol-output',a,'--output',b).returncode,0);self.assertFalse(a.exists());self.assertFalse(b.exists())
            bad=json.loads(app.read_bytes());bad['protocol_candidate']['version']='changed';app.write_text(json.dumps(bad),encoding='utf-8');self.assertNotEqual(call('verify',p,app,'--protocol-output',a).returncode,0);self.assertFalse(a.exists())
            bad=copy.deepcopy(self.doc);bad['report_study_reviews'][0]['reviewed_source_ids']=[];doc.write_text(json.dumps(bad),encoding='utf-8');self.assertNotEqual(call('target',p,doc,'--output',a).returncode,0);self.assertFalse(a.exists())
            self.assertEqual(json.loads(p.read_bytes()),self.p)

    def test_documented_commands_verbatim(self):
        guide=(ROOT/'docs/REPORT_STUDY_REVIEW_INTAKE.md').read_text(encoding='utf-8');blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory() as tmp:
            for line in blocks[0].splitlines():
                args=shlex.split(line);self.assertIn(args[1],['report_study_review.py','report_study_review_intake.py']);args=[str(Path(tmp)/x[7:]) if x.startswith('OUTPUT/') else x for x in args]
                result=subprocess.run([sys.executable,*args[1:]],cwd=ROOT,capture_output=True);self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid']);self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),['application.json','protocol.json','scaffold.json','target.json'])
        tokens=shlex.split('python tool.py OUTPUT/x.json');replaced=[str(Path(r'C:\synthetic space')/x[7:]) if x.startswith('OUTPUT/') else x for x in tokens];self.assertIn(r'C:\synthetic space',replaced[-1])


if __name__=='__main__':unittest.main()
