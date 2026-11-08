"""Explicit planning rationale citations are not scientific decisions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from evidence_workflow import run
from work_review import review_packets,render_text
from review_handoff import handoff
from research_bundle import build_bundle,verify
from planning_links import link_planning
ROOT=Path(__file__).resolve().parents[1]

class RationaleLinksTests(unittest.TestCase):
    def setUp(self):self.p=json.loads((ROOT/'examples/rationale-links.json').read_text())
    def planning(self):return run(self.p)['planning']
    def refresh(self):
        targets={r['work_package_id']:r for r in self.planning()['review_targets']}
        for d in self.p['planning_decisions']:d['basis_sha256']=targets[d['work_package_id']]['basis_sha256']
    def test_links_keep_supplied_challenges_and_unknowns_without_judging_rationale(self):
        p=self.planning();self.assertEqual(p['work_with_stale_planning_assertion'],[])
        for row in p['planning_ledger']:
            links=row['rationale_statement_links'];self.assertEqual(len(links),1)
            self.assertEqual(links[0]['rationale_support_assessment'],'NOT_PERFORMED')
            statement=links[0]['statement'];self.assertEqual(statement['support_status'],'NOT_ASSESSED')
            relations={r['relation'] for r in statement['evidence_positions']}
            self.assertIn('challenges',relations);self.assertIn('not_assessed',relations)
        self.assertEqual(run(self.p)['conclusion_readiness'],'NOT_READY')
    def test_unknown_duplicate_empty_and_wrong_types_rejected(self):
        for value in ([],None,True,'statement-1',['unknown'],['statement-1','statement-1'],[1]):
            p=copy.deepcopy(self.p);p['planning_decisions'][0]['rationale_statement_ids']=value
            with self.subTest(value=value),self.assertRaises(ValueError):run(p)
    def test_reference_requires_shared_work_evidence(self):
        self.p['gaps'][0]['evidence_ids']=['e3'];self.p['gaps'][0]['context_ids']=[]
        # statement-1 cites e1/e2, not e3.
        with self.assertRaisesRegex(ValueError,'share work evidence'):self.planning()
    def test_source_only_work_cannot_claim_statement_rationale_evidence(self):
        w=self.p['gaps'][0];w.update(work_type='source_review',evidence_ids=[],source_refs=[dict(kind='record',record_id='r1')],context_ids=[])
        with self.assertRaisesRegex(ValueError,'share work evidence'):self.planning()
    def test_statement_text_or_position_changes_stale_linked_ranks(self):
        base=copy.deepcopy(self.p)
        self.p['synthesis_statements'][0]['text']+=' Fictional amendment.'
        self.assertEqual(len(self.planning()['work_with_stale_planning_assertion']),2)
        self.p=copy.deepcopy(base);self.p['synthesis_statements'][0]['evidence_positions'][0]['rationale']='Changed fictional uncertainty'
        self.assertEqual(len(self.planning()['work_with_stale_planning_assertion']),2)
    def test_other_statement_change_does_not_change_rationale_basis(self):
        before={r['work_package_id']:r['basis_sha256'] for r in self.planning()['review_targets']}
        self.p['synthesis_statements'][1]['text']+=' Unrelated fictional note.'
        after={r['work_package_id']:r['basis_sha256'] for r in self.planning()['review_targets']}
        self.assertEqual(before,after)
    def test_sibling_result_in_linked_statement_is_bound_without_becoming_work_evidence(self):
        for w in self.p['gaps']:w.update(evidence_ids=['e1'],context_ids=['ctx-guideline'])
        self.refresh();rows=self.planning()['planning_ledger']
        for row in rows:
            link=row['rationale_statement_links'][0]
            self.assertEqual(link['work_evidence_ids'],['e1']);self.assertEqual(link['other_statement_evidence_ids'],['e2'])
        self.p['evidence'][1]['result']='Changed sibling assertion'
        self.assertEqual(len(self.planning()['work_with_stale_planning_assertion']),2)
    def test_direct_helper_requires_validated_synthesis(self):
        r=run(self.p)
        with self.assertRaisesRegex(ValueError,'validated synthesis'):
            link_planning(self.p,r['evidence'],r['work_packages'],r['context'],r['appraisal'],r['experiments'])
    def test_no_reference_legacy_targets_do_not_bind_synthesis(self):
        for d in self.p['planning_decisions']:d.pop('rationale_statement_ids')
        before=self.planning()['review_targets']
        self.p['synthesis_statements'][0]['text']+=' Changed statement without explicit rationale link.'
        self.assertEqual(before,self.planning()['review_targets'])
        self.assertTrue(all('rationale_statements' not in t['basis'] for t in before))
    def test_rank_and_work_progress_do_not_generate_or_renew_support(self):
        before=copy.deepcopy(self.p);self.p['gaps'][0]['status']='IN_PROGRESS'
        self.assertEqual(self.planning()['work_with_stale_planning_assertion'],[])
        self.assertEqual(self.p['planning_decisions'],before['planning_decisions'])
        self.assertEqual(self.planning()['planning_ledger'][0]['rationale_statement_links'][0]['rationale_support_assessment'],'NOT_PERFORMED')
    def test_packets_handoff_bundle_and_copy_isolation(self):
        before=copy.deepcopy(self.p)
        packet=review_packets(self.p,'WP-TRANSLATION')['packets'][0]
        self.assertIn('rationale_statement_links',packet['planning_assertion'])
        self.assertIn('rationale_statement_links',handoff(self.p,'WP-TRANSLATION')['selected_work'][0]['planning'])
        self.assertIn('challenges',render_text(review_packets(self.p,'WP-TRANSLATION')))
        packet['planning_assertion']['rationale_statement_links'][0]['statement']['text']='mutated';self.assertEqual(before,self.p)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'p.json';target=Path(tmp)/'run.zip';source.write_text(json.dumps(self.p),encoding='utf-8')
            target.write_bytes(build_bundle(source.read_bytes()));self.assertTrue(verify(target)['valid'])

if __name__=='__main__':unittest.main()
