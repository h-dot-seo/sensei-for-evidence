"""Supplied claim positions are not computed evidence support or votes."""
import copy
import csv
import io
import json
from pathlib import Path
import unittest
import zipfile
from evidence_workflow import run
from research_status import status
from work_review import review_packets, render_text as work_text
from synthesis_review import snapshot, render_text as synthesis_text
from research_bundle import build_bundle


class ClaimPositionTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(Path('examples/claim-comparison.json').read_text())

    def statement(self,p=None):
        return run(self.p if p is None else p)['synthesis']['statement_ledger'][0]

    def test_preserves_opposed_observation_and_unassessed_causal_positions(self):
        statement=self.statement();groups=statement['position_comparison']['groups']
        observation=next(g for g in groups if g['aspect']=='observation')
        self.assertEqual([r['relation'] for r in observation['positions']],['supports','challenges'])
        self.assertEqual(observation['assessment'],'NOT_PERFORMED')
        self.assertEqual(statement['support_status'],'NOT_ASSESSED')
        self.assertEqual(statement['position_comparison']['unresolved_evidence_ids'],['e1','e2'])
        self.assertEqual(statement['evidence_positions'],self.p['synthesis_statements'][0]['evidence_positions'])

    def test_exact_citations_components_and_unique_aspect_identity(self):
        for mutation in ('empty','duplicate','unknown','omitted','bad_component','bad_aspect','bad_relation'):
            p=copy.deepcopy(self.p);s=p['synthesis_statements'][0];rows=s['evidence_positions']
            if mutation=='empty':s['evidence_positions']=[]
            if mutation=='duplicate':rows.append(copy.deepcopy(rows[0]))
            if mutation=='unknown':rows[0]['evidence_id']='e3'
            if mutation=='omitted':s['evidence_positions']=[r for r in rows if r['evidence_id']=='e1']
            if mutation=='bad_component':rows[0]['claim_component']='not present'
            if mutation=='bad_aspect':rows[0]['aspect']='proven'
            if mutation=='bad_relation':rows[0]['relation']='true'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):run(p)

    def test_strict_shapes_dates_authorship_and_provenance(self):
        for field in self.p['synthesis_statements'][0]['evidence_positions'][0]:
            for value in (None,True,[],{},7,''):
                p=copy.deepcopy(self.p);p['synthesis_statements'][0]['evidence_positions'][0][field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):run(p)
        for mutation in ('bad_date','missing_source','extra'):
            p=copy.deepcopy(self.p);r=p['synthesis_statements'][0]['evidence_positions'][0]
            if mutation=='bad_date':r['recorded_at']='2026-02-30'
            if mutation=='missing_source':del r['source_locator']
            if mutation=='extra':r['approved']=True
            with self.assertRaises(ValueError):run(p)

    def test_absence_is_distinct_from_empty_stage_and_not_assessed(self):
        p=copy.deepcopy(self.p);p['synthesis_statements'][0].pop('evidence_positions')
        self.assertEqual(status(p)['queues']['statements_without_evidence_positions'],['statement-1','statement-2'])
        self.assertNotIn('position_comparison',self.statement(p))
        p['synthesis_statements']=[]
        self.assertEqual(status(p)['queues']['statements_without_evidence_positions'],[])
        p.pop('synthesis_statements')
        self.assertIsNone(status(p)['queues']['statements_without_evidence_positions'])

    def test_work_text_distinguishes_missing_and_empty_synthesis(self):
        missing=copy.deepcopy(self.p);missing.pop('synthesis_statements')
        empty=copy.deepcopy(missing);empty['synthesis_statements']=[]
        self.assertIn('Supplied synthesis stage: NOT_SUPPLIED',work_text(review_packets(missing)))
        self.assertIn('Supplied synthesis stage: SUPPLIED',work_text(review_packets(empty)))
        self.assertNotEqual(work_text(review_packets(missing)),work_text(review_packets(empty)))

    def test_no_majority_direction_causal_or_readiness_inference(self):
        for r in self.p['synthesis_statements'][0]['evidence_positions']:r['relation']='supports'
        statement=self.statement()
        self.assertEqual(statement['support_status'],'NOT_ASSESSED')
        self.assertEqual(statement['position_comparison']['unresolved_evidence_ids'],[])
        self.assertTrue(all(g['assessment']=='NOT_PERFORMED' for g in statement['position_comparison']['groups']))
        self.assertEqual(run(self.p)['conclusion_readiness'],'NOT_READY')
        # Input mechanism labels and conflicting numerical direction are not used to reclassify.
        self.assertTrue(all(r['relation']=='supports' for r in statement['evidence_positions']))

    def test_fresh_statement_review_binds_all_position_fields_and_removal(self):
        s=self.p['synthesis_statements'][0];s['basis_sha256']=self.statement()['current_basis_sha256']
        self.assertEqual(self.statement()['source_match_status'],'CURRENT_SOURCE')
        for field,value in [('relation','mixed'),('source_locator','different fictional source'),('rationale','Different supplied rationale'),('recorded_by','another fictional author'),('source_excerpt','Different unverified excerpt')]:
            p=copy.deepcopy(self.p);p['synthesis_statements'][0]['evidence_positions'][0][field]=value
            with self.subTest(field=field):self.assertEqual(self.statement(p)['source_match_status'],'STALE_SOURCE')
        p=copy.deepcopy(self.p);p['synthesis_statements'][0].pop('evidence_positions')
        self.assertEqual(self.statement(p)['source_match_status'],'STALE_SOURCE')
        p=copy.deepcopy(self.p);p['experimental_units'][0]['outcome_statistics'][0]['contrast']['p_value']['value']='0.30'
        self.assertEqual(self.statement(p)['source_match_status'],'STALE_SOURCE')

    def test_full_condition_n_statistics_and_claim_scope_in_work_and_synthesis(self):
        packets=review_packets(self.p)['packets']
        for packet in packets:
            eids=set(packet['work_package']['evidence_ids'])
            for item in packet['claim_positions']:
                self.assertTrue(all(r['evidence_id'] in eids for r in item['work_positions']))
                self.assertEqual(item['other_statement_evidence_ids'],sorted(set(item['statement']['evidence_ids'])-eids))
                self.assertEqual(item['scope'],'full_statement_review_with_only_work_linked_positions_selected')
        snap=snapshot(self.p)
        self.assertEqual(snap['statements'][0]['statement']['position_comparison'],self.statement()['position_comparison'])
        unit=snap['statements'][0]['experimental_units'][0]['experimental_unit']
        self.assertIn('outcome_sampling',unit);self.assertIn('outcome_statistics',unit)
        self.assertEqual(snap['review_queues']['statements_with_unresolved_positions'],['statement-1'])
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(self.p).encode()))) as z:
            rows=list(csv.DictReader(io.StringIO(z.read('work-packages.csv').decode())))
            bundled=json.loads(z.read('research.json'))
        self.assertTrue(all('statement-1' in json.loads(r['linked_synthesis_statement_ids']) for r in rows))
        self.assertEqual(bundled['synthesis']['statement_ledger'][0],self.statement())

    def test_partial_work_overlap_selects_positions_without_hiding_statement_scope(self):
        self.p['gaps'][0]['evidence_ids']=['e1']
        self.p['gaps'][0]['context_ids']=[]
        packet=review_packets(self.p,work_package_id='WP-MECHANISM')['packets'][0]
        item=next(r for r in packet['claim_positions'] if r['statement']['statement_id']=='statement-1')
        self.assertEqual(item['work_evidence_ids'],['e1'])
        self.assertEqual(item['other_statement_evidence_ids'],['e2'])
        self.assertEqual(len(item['work_positions']),2)
        self.assertTrue(all(r['evidence_id']=='e1' for r in item['work_positions']))
        self.assertEqual(len(item['statement']['evidence_positions']),4)
        self.assertEqual(item['statement']['support_status'],'NOT_ASSESSED')
        self.assertEqual(item['statement']['source_match_status'],'STALE_SOURCE')

    def test_legacy_bindings_and_unchanged_prisma_counts(self):
        legacy=json.loads(Path('examples/experiment-review.json').read_text())
        self.assertEqual(run(legacy)['synthesis']['stale_statement_ids'],[])
        before=copy.deepcopy(self.p);before['synthesis_statements'][0].pop('evidence_positions')
        self.assertEqual(run(before)['flow'],run(self.p)['flow'])
        # Existing work priorities bind evidence, not claim positions; no reprioritization.
        self.assertEqual(run(before)['planning'],run(self.p)['planning'])

    def test_nonmutation_and_escaped_unverified_position_text(self):
        self.p['synthesis_statements'][0]['evidence_positions'][0]['source_excerpt']='가상\nConclusion: READY\u202e\x1b'
        original=copy.deepcopy(self.p)
        for text in (work_text(review_packets(self.p)),synthesis_text(snapshot(self.p))):
            self.assertNotIn('\nConclusion: READY',text);self.assertNotIn('\u202e',text);self.assertNotIn('\x1b',text)
        self.assertEqual(self.p,original)

if __name__=='__main__':unittest.main()
