"""Synthetic reviewed context assignment tests; no clinical applicability inference."""
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

import context_intake
import work_context_intake as intake
from evidence_workflow import run
from prisma_audit import export_audit
import research_bundle

ROOT=Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT/'examples'/name).read_bytes())


def imported_source_contexts():
    p=fixture('source-context-protocol.json');c=fixture('manual-context-candidates.json')
    review=context_intake.prepare(p,c)['review_document']
    review.update(receipt_id='fictional-context-setup',reviewer='Fictional reviewer',reviewed_at='2026-11-04',
                  rationale='Synthetic fixture setup only.',decision='import_contexts')
    return context_intake.assemble(p,c,review)['protocol_candidate']


class WorkContextIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p=imported_source_contexts()
        self.c=dict(schema_version=1,assignments=[dict(work_package_id='WP-GUIDELINE-SOURCES',
                                                     context_ids=['ctx-source-guideline-supplied'])])

    def review(self,p=None,c=None):
        p,c=self.p if p is None else p,self.c if c is None else c
        review=intake.prepare(p,c)['review_document']
        review.update(receipt_id='fictional-work-context-review',reviewer='Fictional link reviewer',
            reviewed_at='2026-11-04',rationale='Explicit synthetic linkage; no applicability finding.',decision='append_work_contexts')
        return review

    def assembled(self,p=None,c=None):
        p,c=self.p if p is None else p,self.c if c is None else c
        return intake.assemble(p,c,self.review(p,c))

    def test_template_copies_only_explicit_work_ids_and_no_context_selection(self):
        refs=dict(schema_version=1,work_package_ids=['WP-GUIDELINE-SOURCES'])
        t=intake.template(self.p,refs)
        self.assertEqual(t['candidate_document']['assignments'],[dict(work_package_id='WP-GUIDELINE-SOURCES',context_ids=None)])
        self.assertEqual(len(t['available_contexts']),4)
        self.assertEqual(t['context_catalog_scope'],'ALL_SUPPLIED_CONTEXTS_NOT_SELECTED_OR_RECOMMENDED')
        with self.assertRaises(ValueError):intake.prepare(self.p,t['candidate_document'])

    def test_template_reference_shape_and_unknown_or_duplicate_work_rejected(self):
        for refs in [None,{},dict(schema_version=True,work_package_ids=['WP-GUIDELINE-SOURCES']),
                     dict(schema_version=1,work_package_ids=[]),dict(schema_version=1,work_package_ids=['missing']),
                     dict(schema_version=1,work_package_ids=['WP-GUIDELINE-SOURCES']*2),
                     dict(schema_version=1,work_package_ids=['WP-GUIDELINE-SOURCES'],extra=True)]:
            with self.subTest(refs=refs),self.assertRaises((ValueError,TypeError)):intake.template(self.p,refs)

    def test_explicit_ids_required_not_positional_normalization(self):
        self.p['gaps'][0].pop('work_package_id')
        self.p['gaps'][1]['depends_on']=['WP-001']
        self.c['assignments'][0]['work_package_id']='WP-001'
        with self.assertRaisesRegex(ValueError,'explicit raw'):intake.prepare(self.p,self.c)
        with self.assertRaisesRegex(ValueError,'explicit raw'):
            intake.template(self.p,dict(schema_version=1,work_package_ids=['WP-001']))

    def test_explicit_work_id_with_default_like_spelling_is_supported(self):
        self.p['gaps'][0]['work_package_id']='WP-001'
        self.p['gaps'][1]['depends_on']=['WP-001']
        self.c['assignments'][0]['work_package_id']='WP-001'
        self.assertTrue(intake.verify(self.p,self.assembled())['valid'])

    def test_basis_changes_do_not_imply_recursive_assignment_or_acceptance(self):
        third=copy.deepcopy(self.p['gaps'][1]);third['work_package_id']='WP-THIRD'
        third['depends_on']=['WP-DEVELOPMENT-SOURCES'];self.p['gaps'].append(third)
        app=self.assembled()
        changed={row['work_package_id'] for row in app['receipt']['target']['changed_work_source_targets']}
        self.assertEqual(changed,{'WP-GUIDELINE-SOURCES','WP-DEVELOPMENT-SOURCES'})
        self.assertEqual(app['protocol_candidate']['gaps'][2],third)

    def test_complete_direct_dependent_binding_stales_without_reopening(self):
        p=fixture('completion-binding.json')
        p['gaps'][1].update(status='COMPLETE',artifact_locator='synthetic:dependent-artifact',acceptance_verified=True)
        current=run(p)
        for raw in p['gaps']:
            raw['completion_basis_sha256']=next(row['current_basis_sha256'] for row in current['planning']['completion_ledger']
                                                if row['work_package_id']==raw['work_package_id'])
        c=dict(schema_version=1,assignments=[dict(work_package_id='WP-MECHANISM',context_ids=['ctx-guideline'])])
        app=self.assembled(p,c);after=run(app['protocol_candidate'])
        self.assertTrue(all(row['status']=='COMPLETE' for row in after['work_packages']))
        self.assertTrue(all(row['source_match_status']=='STALE_SOURCE' for row in after['planning']['completion_ledger']))
        for old,new in zip(p['gaps'],app['protocol_candidate']['gaps']):
            self.assertEqual(old['completion_basis_sha256'],new['completion_basis_sha256'])

    def test_only_selected_context_suffix_changes_and_raw_prefix_preserved(self):
        self.p['opaque']={'literal':'합성\n  unchanged','typed':[True,1,None]}
        old=copy.deepcopy(self.p);app=self.assembled();after=app['protocol_candidate']
        self.assertEqual(after['gaps'][0]['context_ids'],['ctx-source-guideline','ctx-source-guideline-supplied'])
        after_restored=copy.deepcopy(after);after_restored['gaps'][0]['context_ids']=old['gaps'][0]['context_ids']
        self.assertEqual(after_restored,old)
        self.assertEqual(self.p,old)
        self.assertTrue(intake.verify(old,app)['valid'])
        self.assertEqual(after['contexts'],old['contexts'])

    def test_absent_and_empty_context_link_keys_remain_distinct_in_snapshots(self):
        for exists in (False,True):
            p=copy.deepcopy(self.p)
            if exists:p['gaps'][0]['context_ids']=[]
            else:p['gaps'][0].pop('context_ids')
            app=self.assembled(p);snapshot=app['receipt']['target']['selected_work'][0]
            self.assertEqual('context_ids' in snapshot['before_raw'],exists)
            self.assertEqual(snapshot['after_raw']['context_ids'],['ctx-source-guideline-supplied'])
            self.assertEqual('context_ids' in p['gaps'][0],exists)

    def test_import_does_not_change_contexts_own_pending_review_or_identity(self):
        app=self.assembled();after=app['protocol_candidate']
        self.assertEqual(after['contexts'],self.p['contexts'])
        row=next(r for r in after['contexts'] if r['context_id']=='ctx-source-guideline-supplied')
        self.assertEqual(row['review_status'],'pending');self.assertNotIn('reviewer',row)
        self.assertEqual(app['receipt']['target']['selected_contexts'][0]['raw_context'],row)

    def test_direct_dependents_have_changed_bases_without_inherited_assignment(self):
        app=self.assembled();target=app['receipt']['target']
        changes={r['work_package_id']:r for r in target['changed_work_source_targets']}
        self.assertEqual(set(changes),{'WP-GUIDELINE-SOURCES','WP-DEVELOPMENT-SOURCES'})
        self.assertTrue(changes['WP-GUIDELINE-SOURCES']['explicitly_selected'])
        self.assertFalse(changes['WP-DEVELOPMENT-SOURCES']['explicitly_selected'])
        self.assertEqual(app['protocol_candidate']['gaps'][1],self.p['gaps'][1])
        self.assertNotEqual(changes['WP-DEVELOPMENT-SOURCES']['before']['basis_sha256'],changes['WP-DEVELOPMENT-SOURCES']['after']['basis_sha256'])

    def test_completed_work_keeps_completion_and_artifact_but_binding_can_stale(self):
        p=fixture('completion-binding.json')
        c=dict(schema_version=1,assignments=[dict(work_package_id='WP-MECHANISM',context_ids=['ctx-guideline'])])
        before=run(p);app=self.assembled(p,c);after=run(app['protocol_candidate'])
        old=next(r for r in before['planning']['completion_ledger'] if r['work_package_id']=='WP-MECHANISM')
        new=next(r for r in after['planning']['completion_ledger'] if r['work_package_id']=='WP-MECHANISM')
        self.assertEqual(old['source_match_status'],'CURRENT_SOURCE');self.assertEqual(new['source_match_status'],'STALE_SOURCE')
        for key in ('status','artifact_locator','acceptance_verified','completion_basis_sha256'):
            self.assertEqual(app['protocol_candidate']['gaps'][0][key],p['gaps'][0][key])
        self.assertEqual(after['work_packages'][1]['blocked_by'],before['work_packages'][1]['blocked_by'])

    def test_supplied_planning_rank_and_hash_preserved_even_when_no_longer_current(self):
        p=copy.deepcopy(self.p);target=run(p)['planning']['review_targets'][0]
        p['planning_decisions']=[dict(work_package_id=target['work_package_id'],priority_rank=1,
            rationale='Fictional supplied priority',uncertainty='Unassessed',planner='Fictional planner',
            planned_at='2026-11-04',basis_sha256=target['basis_sha256'])]
        before=run(p);app=self.assembled(p);after=run(app['protocol_candidate'])
        self.assertEqual(app['protocol_candidate']['planning_decisions'],p['planning_decisions'])
        ledger=next(row for row in after['planning']['planning_ledger'] if row['work_package_id']==target['work_package_id'])
        self.assertEqual(ledger['source_match_status'],'STALE_SOURCE')
        self.assertEqual(ledger['assertion']['priority_rank'],1);self.assertIsNone(ledger['current_priority_rank'])

    def test_source_partial_overlap_allowed_without_inferred_full_coverage(self):
        self.c['assignments'][0]=dict(work_package_id='WP-DEVELOPMENT-SOURCES',context_ids=['ctx-source-guideline'])
        app=self.assembled()
        self.assertEqual(app['protocol_candidate']['gaps'][1]['context_ids'],['ctx-source-development','ctx-source-guideline'])
        self.assertEqual(app['protocol_candidate']['contexts'],self.p['contexts'])

    def test_source_membership_does_not_replace_exact_shared_reference(self):
        self.c['assignments'][0]['context_ids']=['ctx-source-development-supplied']
        with self.assertRaisesRegex(ValueError,'share an exact typed source'):intake.prepare(self.p,self.c)

    def test_evidence_context_requires_shared_exact_result(self):
        p=fixture('review-demo.json');p['gaps'][0]['evidence_ids']=['e2']
        c=dict(schema_version=1,assignments=[dict(work_package_id='WP-MECHANISM',context_ids=['ctx-guideline'])])
        with self.assertRaisesRegex(ValueError,'share a linked evidence ID'):intake.prepare(p,c)

    def test_source_context_cannot_link_to_evidence_review_work(self):
        p=fixture('review-demo.json')
        source=copy.deepcopy(self.p['contexts'][0]);source['source_refs']=[dict(kind='record',record_id='r1')]
        p['contexts'].append(source)
        c=dict(schema_version=1,assignments=[dict(work_package_id='WP-MECHANISM',context_ids=[source['context_id']])])
        with self.assertRaisesRegex(ValueError,'only to source_review'):intake.prepare(p,c)

    def test_no_op_already_assigned_duplicate_unknown_and_empty_links_rejected(self):
        for ids in [[],['ctx-source-guideline'],['missing'],['ctx-source-guideline-supplied']*2,None]:
            c=copy.deepcopy(self.c);c['assignments'][0]['context_ids']=ids
            with self.subTest(ids=ids),self.assertRaises(ValueError):intake.prepare(self.p,c)

    def test_schema_and_assignment_limits(self):
        for c in [None,{},dict(self.c,schema_version=True),dict(self.c,schema_version=1.0),
                  dict(self.c,assignments=[]),dict(self.c,assignments=self.c['assignments']*101),
                  dict(self.c,extra=True),dict(self.c,assignments=[dict(self.c['assignments'][0],status='COMPLETE')])]:
            with self.assertRaises((ValueError,TypeError)):intake.prepare(self.p,c)
        c=copy.deepcopy(self.c);c['assignments']*=2
        with self.assertRaises(ValueError):intake.prepare(self.p,c)

    def test_assignment_order_preserved_and_never_sorted(self):
        p=copy.deepcopy(self.p)
        extra=copy.deepcopy(p['contexts'][2]);extra['context_id']='a-fictional';p['contexts'].append(extra)
        self.c['assignments'][0]['context_ids']=['ctx-source-guideline-supplied','a-fictional']
        after=self.assembled(p)['protocol_candidate']
        self.assertEqual(after['gaps'][0]['context_ids'],['ctx-source-guideline','ctx-source-guideline-supplied','a-fictional'])

    def test_target_is_blank_deterministic_and_inputs_unmodified(self):
        before=copy.deepcopy((self.p,self.c));a=intake.prepare(self.p,self.c)
        self.assertEqual(a,intake.prepare(self.p,self.c));self.assertEqual(before,(self.p,self.c))
        self.assertTrue(all(v is None for k,v in a['review_document'].items() if k not in ('schema_version','target_sha256')))
        with self.assertRaises(ValueError):intake.assemble(self.p,self.c,a['review_document'])

    def test_review_bound_to_original_candidate_and_implementation(self):
        review=self.review();changed=copy.deepcopy(self.p);changed['opaque']='changed'
        with self.assertRaises(ValueError):intake.assemble(changed,self.c,review)
        app=self.assembled();hashes=intake._implementation_hashes();hashes['work_context_intake.py']='0'*64
        with patch.object(intake,'_implementation_hashes',return_value=hashes):
            with self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_resealed_output_snapshot_and_derived_status_tampering_rejected(self):
        app=self.assembled()
        for mutate in [lambda a:a['protocol_candidate']['gaps'][0].update(status='IN_PROGRESS'),
                       lambda a:a['receipt']['target']['selected_contexts'][0].update(extra=True),
                       lambda a:a['receipt']['target']['changed_work_source_targets'].clear(),
                       lambda a:a['receipt'].update(derived_source_status_changes={})]:
            bad=copy.deepcopy(app);mutate(bad)
            bad['receipt']['receipt_sha256']=intake.digest({k:v for k,v in bad['receipt'].items() if k!='receipt_sha256'})
            with self.assertRaises(ValueError):intake.verify(self.p,bad)

    def test_counts_context_ledger_and_dependency_status_unchanged(self):
        after=self.assembled()['protocol_candidate'];before_r,after_r=run(self.p),run(after)
        for key in ('flow','evidence','execution_order','appraisal','experiments','synthesis'):
            self.assertEqual(before_r[key],after_r[key],key)
        self.assertEqual(before_r['context']['context_ledger'],after_r['context']['context_ledger'])
        for old,new in zip(before_r['work_packages'],after_r['work_packages']):
            self.assertEqual(old['status'],new['status']);self.assertEqual(old['blocked_by'],new['blocked_by'])
        self.assertNotEqual(before_r['context']['unassigned_context_ids'],after_r['context']['unassigned_context_ids'])

    def test_offline_bundle_preserves_result_without_replaying_application_history(self):
        with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            app=self.assembled();raw=research_bundle.build_bundle(json.dumps(app['protocol_candidate']).encode())
            self.assertTrue(research_bundle.verify(io.BytesIO(raw))['valid'])
        result=intake.verify(self.p,app)
        self.assertEqual(result['completion_renewal'],'NOT_PERFORMED');self.assertEqual(result['clinical_applicability'],'NOT_ASSESSED')

    def test_invalid_unrelated_input_and_byte_limits_fail_closed(self):
        p=copy.deepcopy(self.p);p['screening'][0]['decision']='invalid'
        with self.assertRaises(ValueError):intake.prepare(p,self.c)
        for key in ('MAX_PROTOCOL_BYTES','MAX_CANDIDATE_BYTES','MAX_APPLICATION_BYTES'):
            with patch.object(intake,key,1),self.assertRaises(ValueError):intake.prepare(self.p,self.c)

    def test_cli_roundtrip_exclusive_output_and_strict_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'p.json';c=root/'c.json';r=root/'r.json';a=root/'a.json';out=root/'out.json'
            for path,value in [(p,self.p),(c,self.c),(r,self.review())]:path.write_text(json.dumps(value),encoding='utf-8')
            def cli(*args):return subprocess.run([sys.executable,str(ROOT/'work_context_intake.py'),*map(str,args)],cwd=ROOT,
                capture_output=True,timeout=60,env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))
            first=cli('assemble',p,c,r,'--output',a,'--text');self.assertEqual(first.returncode,0,first.stderr)
            second=cli('verify',p,a,'--protocol-output',out);self.assertEqual(second.returncode,0,second.stderr)
            original=a.read_bytes();self.assertNotEqual(cli('assemble',p,c,r,'--output',a).returncode,0);self.assertEqual(a.read_bytes(),original)
            c.write_text('{"schema_version":1,"schema_version":1}',encoding='utf-8')
            bad=cli('target',p,c,'--output',root/'bad.json');self.assertNotEqual(bad.returncode,0);self.assertFalse((root/'bad.json').exists())
            self.assertNotIn(b'Traceback',bad.stderr)

    def test_rendering_failure_and_existing_directory_or_dangling_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'p.json';c=root/'c.json';out=root/'out.json'
            p.write_text(json.dumps(self.p),encoding='utf-8');c.write_text(json.dumps(self.c),encoding='utf-8')
            argv=['work_context_intake.py','target',str(p),str(c),'--output',str(out),'--text']
            with patch.object(sys,'argv',argv),patch.object(intake,'configure_utf8_stdio'),patch.object(sys,'stdout',io.StringIO()), \
                 patch.object(sys,'stderr',io.StringIO()),patch.object(intake,'render_text',side_effect=ValueError('synthetic render failure')):
                with self.assertRaises(SystemExit):intake.main()
            self.assertFalse(out.exists())
            with self.assertRaises(OSError):intake._write_new(root,b'bytes')
            link=root/'dangling';target=root/'absent'
            try:link.symlink_to(target)
            except (OSError,NotImplementedError):return
            with self.assertRaises(OSError):intake._write_new(link,b'bytes')
            self.assertFalse(target.exists())


if __name__=='__main__':unittest.main()
