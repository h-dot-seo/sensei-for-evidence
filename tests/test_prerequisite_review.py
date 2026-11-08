"""Explicit prerequisite packets reuse evidence, context and planning assertions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from work_review import review_packets,render_text
from review_handoff import handoff
ROOT=Path(__file__).resolve().parents[1]

class PrerequisiteReviewTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/'examples/prerequisite-review.json').read_text())
    def review(self):return review_packets(self.p,'WP-TRANSLATION',True)
    def test_mixed_work_chain_has_existing_packets_in_dependency_order(self):
        r=self.review();ids=[p['work_package']['work_package_id'] for p in r['packets']]
        self.assertEqual(ids,['WP-RECEIPT-REVIEW','WP-EXTRACTION-REVIEW','WP-MECHANISM','WP-TRANSLATION'])
        self.assertEqual(r['dependency_review']['omitted_direct_prerequisite_ids'],[])
        self.assertEqual(len(r['dependency_review']['edges']),3)
        for packet in r['packets']:
            self.assertEqual(packet,review_packets(self.p,packet['work_package']['work_package_id'])['packets'][0])
        self.assertTrue(r['packets'][-1]['experimental_units'])
        self.assertEqual(r['packets'][-1]['linked_context_domains'],['clinical_guideline','drug_development'])
        self.assertEqual(r['packets'][-1]['planning_assertion']['source_match_status'],'STALE_SOURCE')
        self.assertEqual(r['conclusion_readiness'],'NOT_READY')
    def test_default_does_not_expand_and_discloses_omitted_packet(self):
        r=review_packets(self.p,'WP-TRANSLATION')
        self.assertEqual(len(r['packets']),1)
        self.assertEqual(r['dependency_review']['omitted_direct_prerequisite_ids'],['WP-MECHANISM'])
        self.assertFalse(r['dependency_review']['edges'][0]['prerequisite_packet_included'])
    def test_requires_selector_and_strict_boolean(self):
        for value in (True,):
            with self.assertRaises(ValueError):review_packets(self.p,include_prerequisites=value)
        for value in (1,None,'true',[],{}):
            with self.assertRaises(ValueError):review_packets(self.p,'WP-TRANSLATION',value)
        with self.assertRaises(ValueError):review_packets(self.p,'unknown',True)
    def test_diamond_deduplicates_shared_prerequisite(self):
        middle=copy.deepcopy(self.p['gaps'][1]);middle.update(work_package_id='WP-ALTERNATE')
        self.p['gaps'].append(middle);self.p['gaps'][2]['depends_on'].append('WP-ALTERNATE')
        r=self.review();ids=r['dependency_review']['packet_work_ids']
        self.assertEqual(len(ids),5);self.assertEqual(ids.count('WP-RECEIPT-REVIEW'),1)
        order={wid:i for i,wid in enumerate(ids)}
        for e in r['dependency_review']['edges']:self.assertLess(order[e['depends_on']],order[e['work_package_id']])
    def test_completed_prerequisite_remains_visible_without_receipt_approval(self):
        self.p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic://note',acceptance_verified=True)
        r=self.review();self.assertEqual(len(r['packets']),4)
        self.assertEqual(r['packets'][1]['work_package']['blocked_by'],[])
        self.assertEqual(r['global_search_plan_audit']['missing_search_ids'],['search-secondary'])
        self.assertEqual(r['census_claim'],'NOT_ESTABLISHED')
    def test_unrelated_shared_evidence_and_descendant_work_not_added(self):
        extra=copy.deepcopy(self.p['gaps'][-1]);extra.update(work_package_id='WP-DESCENDANT',depends_on=['WP-TRANSLATION'])
        self.p['gaps'].append(extra)
        self.assertNotIn('WP-DESCENDANT',self.review()['dependency_review']['packet_work_ids'])
    def test_no_input_mutation_and_returned_scope_copy(self):
        before=copy.deepcopy(self.p);r=self.review();self.assertEqual(before,self.p)
        r['dependency_review']['packet_work_ids'].append('mutation');self.assertEqual(before,self.p)
        self.assertEqual(len(r['packets']),4)
    def test_deep_chain_uses_iterative_traversal(self):
        p=json.loads((ROOT/'examples/source-work-protocol.json').read_text());template=copy.deepcopy(p['gaps'][0]);p['gaps']=[]
        for i in range(1050):
            w=copy.deepcopy(template);w.update(work_package_id=f'W{i}',depends_on=[] if i==0 else [f'W{i-1}'])
            p['gaps'].append(w)
        p['gaps'].reverse();r=review_packets(p,'W1049',True)
        self.assertEqual(len(r['packets']),1050);self.assertEqual(r['dependency_review']['packet_work_ids'][0],'W0')
    def test_cycle_and_invalid_unselected_work_still_fail(self):
        self.p['gaps'][0]['depends_on']=['WP-TRANSLATION']
        with self.assertRaisesRegex(ValueError,'cyclic'):self.review()
    def test_handoff_discovery_and_leading_dash_selector(self):
        self.assertIsNone(handoff(self.p)['prerequisite_review_view'])
        old=self.p['gaps'][-1]['work_package_id'];self.p['gaps'][-1]['work_package_id']='-target'
        self.p['planning_decisions']=[d for d in self.p['planning_decisions'] if d['work_package_id']!=old]
        view=handoff(self.p,'-target')['prerequisite_review_view']
        self.assertIn('--work-package=-target',view['arguments']);self.assertIn('--include-prerequisites',view['arguments'])
    def test_real_cli_and_text_boundaries(self):
        cmd=[sys.executable,str(ROOT/'work_review.py'),str(ROOT/'examples/prerequisite-review.json'),'--work-package=WP-TRANSLATION','--include-prerequisites']
        r=json.loads(subprocess.run(cmd,capture_output=True,check=True).stdout)
        self.assertEqual(r['dependency_review'],self.review()['dependency_review'])
        text=render_text(r);self.assertIn('not priority or scientific readiness',text)
        self.assertEqual(text.count('Work package: '),4)
        invalid=subprocess.run(cmd[:3]+['--include-prerequisites'],capture_output=True);self.assertNotEqual(invalid.returncode,0)

if __name__=='__main__':unittest.main()
