"""Completion source binding does not verify acceptance or execute work."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from evidence_workflow import run
from research_status import status
from work_review import review_packets,render_brief
from review_handoff import handoff
from research_bundle import build_bundle,verify
from compare_runs import compare_protocols
from planning_links import digest
from artifact_review import review_artifacts,secure_open_supported
ROOT=Path(__file__).resolve().parent

class CompletionBindingTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/'examples/completion-binding.json').read_text())
    def binding(self):return next(r for r in run(self.p)['planning']['completion_ledger'] if r['work_package_id']=='WP-MECHANISM')
    def test_match_is_not_artifact_or_acceptance_verification(self):
        r=self.binding();self.assertEqual(r['source_match_status'],'CURRENT_SOURCE')
        self.assertEqual(r['acceptance_assessment'],'NOT_PERFORMED');self.assertEqual(r['artifact_content_verification'],'NOT_PERFORMED')
        self.assertEqual(run(self.p)['work_packages'][1]['blocked_by'],[])
        self.assertEqual(run(self.p)['conclusion_readiness'],'NOT_READY')
    def test_criteria_evidence_context_and_own_locator_edits_stale(self):
        original=copy.deepcopy(self.p)
        for kind in ('criteria','evidence','context','locator'):
            self.p=copy.deepcopy(original)
            if kind=='criteria':self.p['gaps'][0]['acceptance_criterion']='Changed supplied criterion'
            if kind=='evidence':self.p['evidence'][0]['limitations']='Changed supplied evidence limit'
            if kind=='context':self.p['contexts'][1]['version']='Changed supplied context version'
            if kind=='locator':self.p['gaps'][0]['artifact_locator']='synthetic://different-note'
            with self.subTest(kind=kind):self.assertEqual(self.binding()['source_match_status'],'STALE_SOURCE')
    def test_hash_is_not_self_bound_or_rank_basis_change(self):
        original=run(self.p)['planning']['review_targets']
        self.p['gaps'][0]['completion_basis_sha256']='0'*64
        self.assertEqual(run(self.p)['planning']['review_targets'],original)
        self.assertEqual(self.binding()['source_match_status'],'STALE_SOURCE')
    def test_unbound_legacy_completion_keeps_dependency_semantics(self):
        self.p['gaps'][0].pop('completion_basis_sha256')
        self.assertEqual(self.binding()['source_match_status'],'UNBOUND_COMPLETION')
        self.assertEqual(run(self.p)['work_packages'][1]['blocked_by'],[])
        self.assertEqual(status(self.p)['queues']['completed_work_without_source_binding'],['WP-MECHANISM'])
    def test_strict_hash_and_status_contract(self):
        for value in (None,True,1,[],{},'', 'A'*64,'x'*64):
            p=copy.deepcopy(self.p);p['gaps'][0]['completion_basis_sha256']=value
            with self.subTest(value=value),self.assertRaises(ValueError):run(p)
        self.p['gaps'][0]['status']='IN_PROGRESS'
        with self.assertRaisesRegex(ValueError,'COMPLETE'):run(self.p)
    def test_existing_completion_guard_not_bypassed_by_hash(self):
        for field in ('artifact_locator','acceptance_verified'):
            p=copy.deepcopy(self.p);p['gaps'][0].pop(field)
            with self.assertRaises(ValueError):run(p)
        pending=copy.deepcopy(self.p['gaps'][1]);pending.update(work_package_id='WP-OTHER',depends_on=[])
        self.p['gaps'].append(pending);self.p['gaps'][0]['depends_on']=['WP-OTHER']
        with self.assertRaisesRegex(ValueError,'unfinished dependency'):run(self.p)
    def test_target_available_before_completion_with_supplied_locator(self):
        expected=self.binding()['current_basis_sha256']
        self.p['gaps'][0].pop('completion_basis_sha256');self.p['gaps'][0]['status']='IN_PROGRESS'
        self.p['gaps'][0].pop('acceptance_verified')
        r=self.binding();self.assertEqual(r['source_match_status'],'NOT_COMPLETE');self.assertEqual(r['current_basis_sha256'],expected)
    def test_stale_queue_handoff_and_brief_retain_complete_assertion(self):
        self.p['gaps'][0]['deliverable']='Changed fictional deliverable'
        q=status(self.p)['queues'];self.assertEqual(q['completed_work_with_stale_source_binding'],['WP-MECHANISM'])
        self.assertEqual(q['completed_work_assertions'],['WP-MECHANISM'])
        step=next(s for s in handoff(self.p)['manual_review_steps'] if s['queue']=='completed_work_with_stale_source_binding')
        self.assertEqual(step['matching_input_rows'],['/gaps/0'])
        packet=review_packets(self.p,'WP-MECHANISM');self.assertEqual(packet['packets'][0]['completion_review']['source_match_status'],'STALE_SOURCE')
        self.assertIn('STALE_SOURCE',render_brief(packet));self.assertEqual(run(self.p)['work_packages'][1]['blocked_by'],[])
    def test_unrelated_context_change_does_not_stale_unlinked_work_scope(self):
        self.p['contexts'][0]['limitations']='Changed unlinked guideline limit'
        self.assertEqual(self.binding()['source_match_status'],'CURRENT_SOURCE')
    def test_direct_prerequisite_scope_change_stales_completed_dependent(self):
        self.p['gaps'][1].update(status='COMPLETE',artifact_locator='synthetic://translation-note',acceptance_verified=True)
        target=next(r for r in run(self.p)['planning']['completion_ledger'] if r['work_package_id']=='WP-TRANSLATION')
        self.p['gaps'][1]['completion_basis_sha256']=target['current_basis_sha256']
        self.p['gaps'][0]['acceptance_criterion']='Changed predecessor criterion'
        self.assertTrue(all(r['source_match_status']=='STALE_SOURCE' for r in run(self.p)['planning']['completion_ledger']))
    def test_amendment_comparison_shows_completion_source_transition(self):
        before=copy.deepcopy(self.p);self.p['gaps'][0]['deliverable']='Changed fictional deliverable'
        note=dict(schema_version=1,before_sha256=digest(before),after_sha256=digest(self.p),from_version=before['version'],to_version=self.p['version'],reason='Fictional scope change',authored_by='fictional',authored_at='2026-11-03',scope_fields=['gaps'])
        rows=compare_protocols(before,self.p,note)['amendment_review']['observed_state_transitions']['completion']
        self.assertEqual(rows,[dict(id='WP-MECHANISM',before=dict(source_match_status='CURRENT_SOURCE'),after=dict(source_match_status='STALE_SOURCE'))])
    @unittest.skipUnless(secure_open_supported(),'POSIX artifact traversal')
    def test_matching_artifact_bytes_do_not_repair_stale_completion(self):
        p=json.loads((ROOT/'examples/artifact-review-protocol.json').read_text());m=json.loads((ROOT/'examples/artifact-review-manifest.json').read_text())
        p['gaps'][0].update(status='COMPLETE',acceptance_verified=True)
        target=next(r for r in run(p)['planning']['completion_ledger'] if r['work_package_id']=='WP-RECEIPT-REVIEW')
        p['gaps'][0]['completion_basis_sha256']=target['current_basis_sha256'];p['gaps'][0]['deliverable']='Changed fictional note requirement'
        r=review_artifacts(p,m,ROOT/'examples/local-artifacts')
        self.assertTrue(r['all_requested_bytes_match']);self.assertEqual(r['artifacts'][0]['completion_source_status'],'STALE_SOURCE')
        self.assertEqual(r['artifacts'][0]['acceptance_assessment'],'NOT_PERFORMED')

    def test_nonmutation_and_bundle_preservation(self):
        before=copy.deepcopy(self.p);r=run(self.p);self.assertEqual(self.p,before)
        r['planning']['completion_ledger'][0]['basis']['artifact_locator']='mutated';self.assertEqual(self.p,before)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.zip';path.write_bytes(build_bundle(json.dumps(self.p).encode()));self.assertTrue(verify(path)['valid'])

if __name__=='__main__':unittest.main()
