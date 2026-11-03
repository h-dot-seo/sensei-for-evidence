"""Context amendments are routed to explicit work, without clinical conclusions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from compare_runs import compare_protocols
ROOT=Path(__file__).resolve().parent

def fixture(name):return json.loads((ROOT/'examples'/name).read_text())

class ContextWorkImpactTests(unittest.TestCase):
    def setUp(self):self.before=fixture('translation-review.json');self.after=copy.deepcopy(self.before)
    def rows(self):return {r['context_id']:r for r in compare_protocols(self.before,self.after)['context_work_impact']['contexts']}
    def test_unchanged_context_is_not_approval(self):
        for row in self.rows().values():
            self.assertEqual(row['comparison_cues'],[]);self.assertEqual(row['work_ids_for_manual_comparison'],[])
            self.assertEqual(row['review_validity'],'NOT_VERIFIED');self.assertEqual(row['change_significance'],'NOT_ASSESSED')
    def test_amendment_preserves_distinct_dates_and_retained_review_warning(self):
        self.after=fixture('context-amendment.json');rows=self.rows();dev=rows['ctx-development'];guideline=rows['ctx-guideline']
        self.assertIn('REVIEW_LABEL_RETAINED_AFTER_INPUT_CHANGE',dev['comparison_cues'])
        self.assertEqual(dev['work_ids_for_manual_comparison'],['WP-MECHANISM','WP-TRANSLATION'])
        self.assertEqual(guideline['after']['date_roles']['accessed_at'],'2026-02-02')
        self.assertIsNone(guideline['after']['date_roles']['recorded_reviewed_at'])
        self.assertEqual(guideline['after']['date_roles']['publication_or_effective_date_assessment'],'NOT_PERFORMED')
        self.assertIn('population_or_setting',guideline['changed_context_assertion_fields'])
    def test_result_change_flags_only_contexts_explicitly_linked_to_result(self):
        self.after['evidence'][1]['result']='Revised fictional assertion'
        rows=self.rows();self.assertEqual(rows['ctx-guideline']['comparison_cues'],[])
        self.assertIn('LINKED_RESULT_ASSERTIONS_CHANGED',rows['ctx-development']['comparison_cues'])
        self.assertIn('REVIEW_LABEL_RETAINED_AFTER_INPUT_CHANGE',rows['ctx-development']['comparison_cues'])
    def test_review_metadata_change_is_not_source_change_or_reassessment_proof(self):
        d=self.after['contexts'][1];d['reviewed_at']='2026-02-03'
        row=self.rows()['ctx-development'];self.assertEqual(row['changed_context_assertion_fields'],[])
        self.assertEqual(row['comparison_cues'],['REVIEW_METADATA_CHANGED'])
        d['version']='new';row=self.rows()['ctx-development']
        self.assertNotIn('REVIEW_LABEL_RETAINED_AFTER_INPUT_CHANGE',row['comparison_cues'])
        self.assertEqual(row['review_validity'],'NOT_VERIFIED')
    def test_removing_context_preserves_old_work_and_deliverable(self):
        self.after['contexts']=self.after['contexts'][:1]
        self.after['gaps'][1]['context_ids']=['ctx-guideline'];self.after['gaps'][0]['context_ids']=[]
        row=self.rows()['ctx-development'];self.assertIsNone(row['after'])
        self.assertEqual(row['work_links_removed'],['WP-MECHANISM','WP-TRANSLATION'])
        self.assertEqual(row['before']['work_links'][1]['work_package']['deliverable'],self.before['gaps'][1]['deliverable'])
    def test_work_sharing_result_without_context_id_is_not_implicitly_impacted(self):
        self.after['contexts'][0]['version']='new'
        row=self.rows()['ctx-guideline'];self.assertEqual(row['work_ids_for_manual_comparison'],['WP-TRANSLATION'])
        self.assertNotIn('WP-MECHANISM',[w['work_package']['work_package_id'] for w in row['after']['work_links']])
    def test_removed_work_context_link_and_scope_partition(self):
        self.after['gaps'][1]['context_ids']=['ctx-development']
        rows=self.rows();g=rows['ctx-guideline'];d=rows['ctx-development']
        self.assertEqual(g['work_links_removed'],['WP-TRANSLATION'])
        link=d['after']['work_links'][0]
        self.assertEqual(link['shared_evidence_ids'],['e2']);self.assertEqual(link['other_work_evidence_ids'],['e1'])
        self.assertEqual(link['other_context_evidence_ids'],[])
    def test_added_context_and_unassigned_context_are_explicit(self):
        c=copy.deepcopy(self.after['contexts'][0]);c['context_id']='unassigned';self.after['contexts'].append(c)
        row=self.rows()['unassigned'];self.assertIsNone(row['before']);self.assertEqual(row['after']['work_links'],[])
        self.assertEqual(row['work_ids_for_manual_comparison'],[]);self.assertIn('CONTEXT_ADDED',row['comparison_cues'])
    def test_no_contexts_and_invalid_protocol_failures(self):
        for p in (self.before,self.after):
            p.pop('contexts')
            for w in p['gaps']:w.pop('context_ids',None)
        self.assertEqual(self.rows(),{})
        self.after['gaps'][1]['context_ids']=['unknown']
        with self.assertRaises(ValueError):self.rows()
    def test_mutation_isolated_and_work_progress_not_context_change(self):
        self.after['gaps'][1]['status']='IN_PROGRESS';original=copy.deepcopy(self.after)
        row=self.rows()['ctx-development'];self.assertEqual(row['changed_context_assertion_fields'],[])
        self.assertEqual(row['comparison_cues'],['LINKED_WORK_ASSERTIONS_CHANGED'])
        row['after']['context']['title']='mutated';self.assertEqual(self.after,original)
    def test_full_comparison_still_reports_out_of_scope_search_changes(self):
        self.after['searches'][0]['searched_at']='2026-02-02'
        r=compare_protocols(self.before,self.after)
        self.assertIn('searches',r['changed_protocol_fields'])
        self.assertTrue(all(not row['comparison_cues'] for row in r['context_work_impact']['contexts']))
        self.assertIn('outside this focused view',r['context_work_impact']['boundary'])
    def test_context_evidence_scope_change_is_not_a_work_assertion_change(self):
        self.after['contexts'][0]['evidence_ids']=['e1','e2']
        row=self.rows()['ctx-guideline']
        self.assertIn('CONTEXT_ASSERTIONS_CHANGED',row['comparison_cues'])
        self.assertEqual(row['changed_linked_work_ids'],[])
        self.assertNotIn('LINKED_WORK_ASSERTIONS_CHANGED',row['comparison_cues'])
        self.assertEqual(row['after']['work_links'][0]['shared_evidence_ids'],['e1','e2'])

    def test_real_cli_and_hash_determinism(self):
        cmd=[sys.executable,str(ROOT/'compare_runs.py'),str(ROOT/'examples/translation-review.json'),str(ROOT/'examples/context-amendment.json')]
        a=subprocess.run(cmd,capture_output=True,check=True).stdout;b=subprocess.run(cmd,capture_output=True,check=True).stdout
        self.assertEqual(a,b);r=json.loads(a);self.assertEqual(r['conclusion_readiness'],'NOT_READY')
        self.assertEqual(len(r['context_work_impact']['contexts']),2)

if __name__=='__main__':unittest.main()
