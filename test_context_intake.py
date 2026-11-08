"""Synthetic append-only guideline/development context intake regressions."""
import copy
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import context_intake as intake
from evidence_workflow import run
from prisma_reports import report_flow
import research_bundle

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


class ContextIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('source-context-protocol.json')
        self.c = fixture('manual-context-candidates.json')

    def review(self, p=None, c=None):
        p, c = self.p if p is None else p, self.c if c is None else c
        review = intake.prepare(p, c)['review_document']
        review.update(receipt_id='fictional-context-import', reviewer='Fictional import reviewer',
            reviewed_at='2026-11-04', rationale='Record supplied fictional context only.', decision='import_contexts')
        return review

    def assembled(self, p=None, c=None):
        p, c = self.p if p is None else p, self.c if c is None else c
        return intake.assemble(p, c, self.review(p, c))

    def reject(self, c):
        with self.assertRaises((ValueError, TypeError)):
            intake.prepare(self.p, c)

    def evidence_fixture(self):
        p = fixture('review-demo.json')
        contexts = copy.deepcopy(p['contexts'])
        for row in contexts:
            row['context_id'] += '-supplied'
            row['context_scope'] = 'extracted_evidence'
            row.setdefault('review_status', 'pending')
        return p, dict(schema_version=1, contexts=contexts)

    def test_template_preserves_only_explicit_selection_and_leaves_assertions_blank(self):
        refs = fixture('context-references.json')
        result = intake.template(self.p, refs)
        row = result['candidate_document']['contexts'][0]
        self.assertEqual(row['source_refs'], refs['source_refs'])
        self.assertEqual(row['evidence_ids'], [])
        self.assertIsNone(row['review_status'])
        self.assertIsNone(row['applicability'])
        self.assertIsNone(row['recommendation_strength'])
        for key, value in row.items():
            if key not in refs: self.assertIsNone(value)
        self.reject(result['candidate_document'])

    def test_template_evidence_domain_and_links_are_explicit(self):
        p, _ = self.evidence_fixture()
        refs = dict(schema_version=1, domain='drug_development', context_scope='extracted_evidence', evidence_ids=['e2'])
        row = intake.template(p, refs)['candidate_document']['contexts'][0]
        self.assertEqual(row['evidence_ids'], ['e2'])
        self.assertIsNone(row['development_stage'])
        self.assertIsNone(row['regulatory_status'])
        self.assertNotIn('source_refs', row)

    def test_template_rejects_unknown_fields_domains_and_wrong_typed_references(self):
        base = fixture('context-references.json')
        variants = [None, [], {}, dict(base, schema_version=True), dict(base, domain='other'),
                    dict(base, context_scope='unknown'), dict(base, extra=1),
                    dict(base, source_refs=[dict(kind='record', record_id='local-secondary')]),
                    dict(base, source_refs=[]), dict(base, evidence_ids=['invented'])]
        for refs in variants:
            with self.subTest(refs=refs), self.assertRaises((ValueError, TypeError)):
                intake.template(self.p, refs)

    def test_separate_blank_import_review_deterministic_and_nonmutating(self):
        before = copy.deepcopy((self.p, self.c))
        a = intake.prepare(self.p, self.c)
        self.assertEqual(a, intake.prepare(self.p, self.c))
        self.assertEqual(before, (self.p, self.c))
        self.assertTrue(all(v is None for k, v in a['review_document'].items() if k not in ('schema_version','target_sha256')))
        with self.assertRaises(ValueError): intake.assemble(self.p, self.c, a['review_document'])

    def test_source_contexts_append_only_with_no_evidence_study_or_work_promotion(self):
        self.p['opaque'] = {'literal': '합성\n  retained', 'typed': [True, 1, None]}
        old = copy.deepcopy(self.p)
        app = self.assembled(); after = app['protocol_candidate']
        self.assertEqual(after['contexts'][:2], old['contexts'])
        self.assertEqual(after['contexts'][2:], self.c['contexts'])
        self.assertEqual({k:v for k,v in after.items() if k!='contexts'}, {k:v for k,v in old.items() if k!='contexts'})
        self.assertEqual(after['evidence'], [])
        result = run(after)
        new = [r for r in result['context']['context_ledger'] if r['context_id'].endswith('-supplied')]
        self.assertTrue(all(r['linked_study_ids'] == [] for r in new))
        self.assertTrue(set(r['context_id'] for r in new) <= set(result['context']['unassigned_context_ids']))
        self.assertEqual(self.p, old)
        self.assertTrue(intake.verify(old, app)['valid'])

    def test_both_domains_and_scopes_preserve_all_existing_derived_work_and_reviews(self):
        for p, c in [(self.p, self.c), self.evidence_fixture()]:
            with self.subTest(scope=c['contexts'][0]['context_scope']):
                app = self.assembled(p, c)
                before, after = run(p), run(app['protocol_candidate'])
                for key in ('flow','evidence','work_packages','planning','synthesis','appraisal','experiments','execution_order'):
                    self.assertEqual(before[key], after[key], key)
                self.assertEqual(before['context']['work_package_context'], after['context']['work_package_context'])
                self.assertEqual(app['receipt']['before_report_flow'], app['receipt']['after_report_flow'])

    def test_import_reviewer_never_changes_context_review_status_or_authorship(self):
        app = self.assembled()
        new = app['protocol_candidate']['contexts'][2:]
        self.assertEqual(new, self.c['contexts'])
        self.assertEqual(new[0]['review_status'], 'pending')
        self.assertNotIn('reviewer', new[0])
        self.assertEqual(new[1]['review_status'], 'reviewed')
        self.assertNotEqual(new[1]['reviewer'], app['receipt']['assertion']['reviewer'])

    def test_pending_metadata_validated_consistently_for_both_scopes(self):
        for p, c in [(self.p, self.c), self.evidence_fixture()]:
            for field, value in [('reviewer',' '), ('reviewed_at','2026-02-30')]:
                bad = copy.deepcopy(c); bad['contexts'][0][field] = value
                with self.subTest(scope=bad['contexts'][0]['context_scope'],field=field), self.assertRaises(ValueError):
                    intake.prepare(p, bad)
            c['contexts'][0].update(reviewer='Fictional optional attribution', reviewed_at='2026-11-04')
            self.assertEqual(self.assembled(p,c)['protocol_candidate']['contexts'][-2]['review_status'], 'pending')

    def test_reviewed_context_requires_own_reviewer_and_date(self):
        for field in ('reviewer','reviewed_at'):
            bad=copy.deepcopy(self.c); bad['contexts'][1].pop(field); self.reject(bad)

    def test_all_source_links_including_unexecuted_excluded_and_unscreened_remain_literal(self):
        row = self.c['contexts'][0]
        row['source_refs'] = [dict(kind='planned_search',search_id='local-secondary'),
                              dict(kind='record',record_id='synthetic-r1'),dict(kind='record',record_id='synthetic-r2')]
        app = self.assembled()
        selected = app['receipt']['target']['selected_sources']
        self.assertEqual(selected[0]['planned_search'], self.p['search_plan'][1])
        self.assertEqual([r['source_ref'] for r in selected[:3]], row['source_refs'])
        self.assertEqual(app['receipt']['before_flow'], app['receipt']['after_flow'])
        self.assertEqual(app['protocol_candidate']['screening'], self.p['screening'])

    def test_mixed_scopes_are_rejected_without_promotion(self):
        bad=copy.deepcopy(self.c); bad['contexts'][0]['evidence_ids']=['invented']; self.reject(bad)
        p,c=self.evidence_fixture(); c['contexts'][0]['source_refs']=[dict(kind='record',record_id='r1')]
        with self.assertRaises(ValueError): intake.prepare(p,c)

    def test_missing_contexts_key_and_legacy_result_id_preserved(self):
        p=fixture('protocol.json'); self.assertNotIn('contexts',p)
        _,c=self.evidence_fixture(); c['contexts']=c['contexts'][:1]; c['contexts'][0]['evidence_ids']=['r1']
        app=self.assembled(p,c)
        selected=app['receipt']['target']['selected_evidence'][0]
        self.assertEqual(selected['identity_origin'],'LEGACY_RECORD_ID')
        self.assertNotIn('evidence_id',app['protocol_candidate']['evidence'][0])
        self.assertNotIn('contexts',p)

    def test_empty_contexts_key_and_opaque_old_context_metadata_preserved(self):
        p=fixture('protocol.json'); p['contexts']=[]
        _,c=self.evidence_fixture(); c['contexts']=c['contexts'][:1]; c['contexts'][0]['evidence_ids']=['r1']
        self.assertEqual(len(self.assembled(p,c)['protocol_candidate']['contexts']),1)
        self.p['contexts'][0]['opaque']={'retained':True}
        self.assertEqual(self.assembled()['protocol_candidate']['contexts'][0],self.p['contexts'][0])

    def test_collision_and_duplicate_ids_rejected(self):
        bad=copy.deepcopy(self.c);bad['contexts'][0]['context_id']=self.p['contexts'][0]['context_id'];self.reject(bad)
        bad=copy.deepcopy(self.c);bad['contexts'].append(copy.deepcopy(bad['contexts'][0]));self.reject(bad)

    def test_exact_new_schema_rejects_derived_fields_and_assignment_attempts(self):
        for field,value in [('linked_study_ids',[]),('context_ids',[]),('work_package_id','WP-GUIDELINE-SOURCES'),('extra','value')]:
            bad=copy.deepcopy(self.c);bad['contexts'][0][field]=value;self.reject(bad)
        self.reject(dict(self.c,assignments=[]))

    def test_candidate_envelope_types_and_bounds(self):
        for bad in [None,[],{},dict(self.c,schema_version=True),dict(self.c,schema_version=1.0),
                    dict(self.c,contexts=[]),dict(self.c,contexts={}),dict(self.c,contexts=self.c['contexts']*51)]:
            self.reject(bad)
        c=copy.deepcopy(self.c);c['contexts']=[copy.deepcopy(c['contexts'][0]) for _ in range(100)]
        for i,row in enumerate(c['contexts']):row['context_id']='fictional-context-%d'%i
        self.assertEqual(len(intake.prepare(self.p,c)['target']['appended_contexts']),100)

    def test_dates_text_and_reference_validation(self):
        for field,value in [('accessed_at','2026-02-30'),('accessed_at','20261104'),('title',''),
                            ('applicability',None),('evidence_certainty',1),('review_status',None),
                            ('source_refs',[dict(kind='planned_search',search_id='missing')]),
                            ('source_refs',[dict(kind='record',record_id='synthetic-r1',extra=True)])]:
            bad=copy.deepcopy(self.c);bad['contexts'][0][field]=value;self.reject(bad)

    def test_current_input_invalid_unrelated_data_is_not_hidden(self):
        self.p['screening'][0]['decision']='invalid'
        with self.assertRaises(ValueError):intake.prepare(self.p,self.c)

    def test_target_bound_to_entire_original_and_candidates(self):
        review=self.review()
        for p,c in [(dict(self.p,opaque=True),self.c),(self.p,copy.deepcopy(self.c))]:
            if p is self.p:c['contexts'][0]['limitations']+=' Changed'
            with self.assertRaises(ValueError):intake.assemble(p,c,review)

    def test_receipt_output_and_snapshot_tampering_rejected_even_resealed(self):
        app=self.assembled()
        for mutate in [lambda a:a['protocol_candidate']['contexts'][-1].update(title='Changed'),
                       lambda a:a['receipt']['target']['selected_sources'][0].update(extra=True),
                       lambda a:a['receipt'].update(after_context_count=999)]:
            bad=copy.deepcopy(app);mutate(bad)
            bad['receipt']['receipt_sha256']=intake.digest({k:v for k,v in bad['receipt'].items() if k!='receipt_sha256'})
            with self.assertRaises(ValueError):intake.verify(self.p,bad)

    def test_implementation_changes_refuse_replay(self):
        app=self.assembled();hashes=intake._implementation_hashes();hashes['context_intake.py']='0'*64
        with patch.object(intake,'_implementation_hashes',return_value=hashes):
            with self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_offline_bundle_and_prisma_accounting_preserved(self):
        with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            app=self.assembled();after=app['protocol_candidate']
            raw=research_bundle.build_bundle(json.dumps(after).encode())
            self.assertTrue(research_bundle.verify(io.BytesIO(raw))['valid'])
        self.assertEqual(run(self.p)['flow'],run(after)['flow'])
        self.assertEqual(app['receipt']['before_report_flow'],app['receipt']['after_report_flow'])
        self.assertEqual(intake.verify(self.p,app)['clinical_applicability'],'NOT_ASSESSED')

    def test_prisma_partitions_unchanged_and_new_source_contexts_unassigned(self):
        from prisma_audit import export_audit
        after=self.assembled()['protocol_candidate']
        before_audit,after_audit=export_audit(self.p),export_audit(after)
        for key in before_audit:
            if key not in ('source_context_ledger','protocol_sha256'):
                self.assertEqual(before_audit[key],after_audit[key],key)
        new=[row for row in after_audit['source_context_ledger'] if row['context']['context_id'].endswith('-supplied')]
        self.assertEqual(len(new),2)
        self.assertTrue(all(row['explicit_work_ids']==[] for row in new))

    def test_multiple_explicit_result_links_do_not_infer_work_or_study_equivalence(self):
        p,c=self.evidence_fixture()
        c['contexts'][0]['evidence_ids']=['e1','e2']
        app=self.assembled(p,c)
        target=app['receipt']['target']
        self.assertEqual([row['evidence_id'] for row in target['selected_evidence'][:2]],['e1','e2'])
        self.assertEqual(app['protocol_candidate']['gaps'],p['gaps'])

    def test_review_schema_decision_and_dates_rejected(self):
        review=self.review()
        for key,value in [('schema_version',True),('decision','review_contexts'),('reviewer',' '),
                          ('reviewed_at','2026-02-30'),('target_sha256','not-hash'),('extra',True)]:
            bad=dict(review);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):intake.assemble(self.p,self.c,bad)

    def test_cli_rendering_failure_precedes_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'protocol.json';c=root/'candidates.json';out=root/'out.json'
            p.write_text(json.dumps(self.p),encoding='utf-8');c.write_text(json.dumps(self.c),encoding='utf-8')
            args=['context_intake.py','target',str(p),str(c),'--output',str(out),'--text']
            with patch.object(sys,'argv',args),patch.object(intake,'configure_utf8_stdio'), \
                 patch.object(sys,'stdout',io.StringIO()),patch.object(sys,'stderr',io.StringIO()), \
                 patch.object(intake,'render_text',side_effect=ValueError('synthetic render failure')):
                with self.assertRaises(SystemExit):intake.main()
            self.assertFalse(out.exists())

    def test_output_limits_fail_before_return(self):
        for name in ('MAX_PROTOCOL_BYTES','MAX_CANDIDATE_BYTES','MAX_APPLICATION_BYTES'):
            with patch.object(intake,name,1),self.assertRaises(ValueError):intake.prepare(self.p,self.c)

    def test_cli_utf8_exclusive_output_and_strict_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'protocol.json';c=root/'candidates.json';r=root/'review.json';a=root/'app.json';out=root/'after.json'
            for path,value in [(p,self.p),(c,self.c),(r,self.review())]:path.write_text(json.dumps(value),encoding='utf-8')
            def cli(*args):
                return subprocess.run([sys.executable,str(ROOT/'context_intake.py'),*map(str,args)],cwd=ROOT,capture_output=True,timeout=60,
                    env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))
            result=cli('assemble',p,c,r,'--output',a,'--text');self.assertEqual(result.returncode,0,result.stderr)
            result=cli('verify',p,a,'--protocol-output',out);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(out.read_bytes())['contexts'][2:],self.c['contexts'])
            before=a.read_bytes();self.assertNotEqual(cli('assemble',p,c,r,'--output',a).returncode,0);self.assertEqual(a.read_bytes(),before)
            c.write_text('{"schema_version":1,"schema_version":1}',encoding='utf-8')
            result=cli('target',p,c,'--output',root/'bad.json');self.assertNotEqual(result.returncode,0);self.assertFalse((root/'bad.json').exists())
            self.assertNotIn(b'Traceback',result.stderr)

    def test_existing_directory_and_dangling_link_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(OSError):intake._write_new(root,b'bytes')
            target=root/'absent';link=root/'dangling'
            try:link.symlink_to(target)
            except (OSError,NotImplementedError):return
            with self.assertRaises(OSError):intake._write_new(link,b'bytes')
            self.assertFalse(target.exists());self.assertTrue(link.is_symlink())


if __name__=='__main__':unittest.main()
