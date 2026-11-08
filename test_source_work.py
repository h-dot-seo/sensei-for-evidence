"""Pre-extraction work references sources, never fabricated evidence or approval."""
import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from evidence_workflow import run
from work_review import review_packets, render_text
from review_handoff import handoff
from research_status import status
from research_bundle import build_bundle
from receipt_intake import check
from offline_adapter import assemble
ROOT=Path(__file__).resolve().parent

class SourceWorkTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/source-work-protocol.json').read_text())

    def test_pre_extraction_work_has_no_fabricated_results(self):
        research=run(self.p)
        self.assertEqual(research['evidence'],[])
        self.assertEqual(len(research['work_packages']),2)
        self.assertTrue(all(w['work_type']=='source_review' and w['evidence_ids']==[] for w in research['work_packages']))
        work={w['work_package_id']:w for w in research['work_packages']}
        self.assertEqual(work['WP-EXTRACTION-REVIEW']['blocked_by'],['WP-RECEIPT-REVIEW'])
        self.assertEqual(research['conclusion_readiness'],'NOT_READY')

    def test_type_reference_and_identity_validation_remains_strict(self):
        for mutation in ('implicit_empty','bad_type','no_refs','bad_kind','unknown_search','evidence_as_record','extra_field','duplicate','mixed_evidence'):
            p=copy.deepcopy(self.p);w=p['gaps'][0]
            if mutation=='implicit_empty':w.pop('work_type');w.pop('source_refs')
            if mutation=='bad_type':w['work_type']='automatic'
            if mutation=='no_refs':w['source_refs']=[]
            if mutation=='bad_kind':w['source_refs'][0]['kind']='evidence'
            if mutation=='unknown_search':w['source_refs'][0]['search_id']='absent'
            if mutation=='evidence_as_record':w['source_refs']=[dict(kind='record',record_id='e1')]
            if mutation=='extra_field':w['source_refs'][0]['approved']=True
            if mutation=='duplicate':w['source_refs'].append(copy.deepcopy(w['source_refs'][0]))
            if mutation=='mixed_evidence':w['evidence_ids']=['e1']
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):run(p)
        for value in (None,True,[],{},7,''):
            p=copy.deepcopy(self.p);p['gaps'][0]['source_refs'][0]['search_id']=value
            with self.subTest(value=value),self.assertRaises(ValueError):run(p)

    def test_source_type_requires_declared_search_not_ambiguous_observed_id(self):
        p=copy.deepcopy(self.p);p.pop('adapter_receipts')
        for s in p['searches']:s.pop('adapter_provenance',None)
        p.pop('search_plan')
        with self.assertRaisesRegex(ValueError,'declared search'):run(p)
        p['gaps']=p['gaps'][1:];p['gaps'][0].pop('depends_on')
        self.assertEqual(run(p)['work_packages'][0]['source_refs'],[dict(kind='record',record_id='r1')])

    def test_source_review_packet_retains_missing_search_and_record_stage(self):
        packets={r['work_package']['work_package_id']:r for r in review_packets(self.p)['packets']}
        searches=packets['WP-RECEIPT-REVIEW'];record=packets['WP-EXTRACTION-REVIEW']
        self.assertEqual(searches['recorded_review_gaps']['source_review_missing_searches'],['search-secondary'])
        self.assertEqual(searches['source_review_inputs'][1]['observed_search_indices'],[])
        self.assertEqual(searches['source_input_counts'],dict(planned_searches=2,enumerated_records=0))
        self.assertEqual(searches['scope_counts']['result_rows'],0)
        self.assertEqual(record['source_review_inputs'][0]['reference']['record_id'],'r1')
        self.assertEqual(record['source_review_inputs'][0]['report']['report_id'],'report-1')
        self.assertEqual(record['source_review_inputs'][0]['existing_result_ids'],[])
        self.assertEqual(record['source_review_inputs'][0]['screening']['decision'],'include')
        self.assertEqual(record['results'],[])
        self.assertEqual(record['sources'][0]['search_index'],0)

    def test_pending_screening_record_can_be_reviewed_without_eligibility_inference(self):
        p=copy.deepcopy(self.p);p.pop('adapter_receipts')
        for s in p['searches']:s.pop('adapter_provenance',None)
        p['screening']=[];p.pop('reports')
        packet=next(r for r in review_packets(p)['packets'] if r['work_package']['work_package_id']=='WP-EXTRACTION-REVIEW')
        self.assertIsNone(packet['source_review_inputs'][0]['screening'])
        self.assertIsNone(packet['source_review_inputs'][0]['report'])
        self.assertEqual(packet['decision_status'],'NO_AUTOMATED_DECISION')

    def test_completed_source_work_does_not_accept_receipt_or_clear_missing_sources(self):
        self.p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic://receipt-review-note',acceptance_verified=True)
        research=run(self.p);work={w['work_package_id']:w for w in research['work_packages']}
        self.assertEqual(work['WP-EXTRACTION-REVIEW']['blocked_by'],[])
        self.assertFalse(self.p['searches'][0]['complete'])
        self.assertEqual(self.p['adapter_receipts']['reviews'],[])
        self.assertEqual(research['search_plan_audit']['missing_search_ids'],['search-secondary'])
        self.assertEqual(research['census_claim'],'NOT_ESTABLISHED')
        self.assertEqual(research['evidence'],[])

    def test_same_completion_and_dependency_guards_apply_to_source_work(self):
        for mutation in ('no_artifact','false_acceptance','unfinished_dependency','cycle'):
            p=copy.deepcopy(self.p)
            if mutation=='no_artifact':p['gaps'][0].update(status='COMPLETE',acceptance_verified=True)
            if mutation=='false_acceptance':p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic://note',acceptance_verified=False)
            if mutation=='unfinished_dependency':p['gaps'][1].update(status='COMPLETE',artifact_locator='synthetic://note',acceptance_verified=True)
            if mutation=='cycle':p['gaps'][0]['depends_on']=['WP-EXTRACTION-REVIEW']
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):run(p)

    def test_source_refs_bind_planning_but_progress_is_not_scientific_review(self):
        r=run(self.p);target=next(t for t in r['planning']['review_targets'] if t['work_package_id']=='WP-EXTRACTION-REVIEW')
        self.p['planning_decisions']=[dict(work_package_id='WP-EXTRACTION-REVIEW',priority_rank=1,rationale='Supplied fictional rank',uncertainty='No scientific priority established',planner='fictional planner',planned_at='2026-11-03',basis_sha256=target['basis_sha256'])]
        self.assertEqual(run(self.p)['planning']['work_with_stale_planning_assertion'],[])
        self.p['gaps'][1]['source_refs'][0]['record_id']='r2'
        self.assertEqual(run(self.p)['planning']['work_with_stale_planning_assertion'],['WP-EXTRACTION-REVIEW'])

    def test_legacy_bindings_and_evidence_requirements_unchanged(self):
        p=json.loads((ROOT/'examples/experiment-review.json').read_text())
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],[])
        self.assertEqual(run(p)['synthesis']['stale_statement_ids'],[])
        self.assertNotIn('work_type',run(p)['work_packages'][0])
        p['gaps'][0]['source_refs']=[dict(kind='record',record_id='r1')]
        with self.assertRaisesRegex(ValueError,'reserved'):run(p)

    def test_manual_receipt_then_reviewed_extraction_then_mixed_work(self):
        base=json.loads((ROOT/'examples/adapter-protocol.json').read_text())
        f=json.loads((ROOT/'examples/adapter-fixture.json').read_text())
        reviews=json.loads((ROOT/'examples/adapter-reviews.json').read_text())
        search_only=copy.deepcopy(f);search_only['extraction_candidates']=[]
        candidate=check(base,search_only)['protocol_candidate'];candidate['gaps']=copy.deepcopy(self.p['gaps'])
        self.assertEqual(run(candidate)['evidence'],[])
        accepted=assemble(base,f,reviews)['protocol'];accepted['gaps']=copy.deepcopy(self.p['gaps'])
        accepted['gaps'].append(dict(work_package_id='WP-EVIDENCE',evidence_ids=['e1'],depends_on=['WP-EXTRACTION-REVIEW'],question='Which supplied evidence limitations need review?',deliverable='Source-linked fictional evidence review',acceptance_criterion='Human records support limits without inferring causality'))
        r=run(accepted);work={w['work_package_id']:w for w in r['work_packages']}
        self.assertEqual(work['WP-EVIDENCE']['blocked_by'],['WP-EXTRACTION-REVIEW'])
        source=next(p for p in review_packets(accepted)['packets'] if p['work_package']['work_package_id']=='WP-EXTRACTION-REVIEW')
        self.assertEqual(source['source_review_inputs'][0]['existing_result_ids'],['e1','e2'])
        self.assertEqual(source['results'],[])

    def test_record_source_inventory_changes_stale_planning_without_binding_scientific_content(self):
        base=json.loads((ROOT/'examples/adapter-protocol.json').read_text())
        f=json.loads((ROOT/'examples/adapter-fixture.json').read_text())
        reviews=json.loads((ROOT/'examples/adapter-reviews.json').read_text())
        p=assemble(base,f,reviews)['protocol'];p.pop('adapter_receipts')
        for row in p['searches']+p['evidence']:row.pop('adapter_provenance',None)
        p['gaps']=copy.deepcopy(self.p['gaps'])
        target=next(t for t in run(p)['planning']['review_targets'] if t['work_package_id']=='WP-EXTRACTION-REVIEW')
        self.assertEqual(target['basis']['work_scope']['source_result_inventory'],[dict(record_id='r1',evidence_ids=['e1','e2'])])
        p['planning_decisions']=[dict(work_package_id='WP-EXTRACTION-REVIEW',priority_rank=1,rationale='Fictional rank',uncertainty='No scientific rank',planner='fictional',planned_at='2026-11-03',basis_sha256=target['basis_sha256'])]
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],[])
        # The source-only scope sees inventory IDs, not result validity/content.
        p['evidence'][0]['result']='Different unassessed supplied result text'
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],[])
        p['evidence'].append(dict(copy.deepcopy(p['evidence'][0]),evidence_id='new-result'))
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],['WP-EXTRACTION-REVIEW'])
        p['evidence'].pop();p['gaps'][1]['status']='IN_PROGRESS'
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],[])

    def test_source_inventory_stales_direct_dependent_evidence_work(self):
        p=json.loads((ROOT/'examples/multi-result-protocol.json').read_text())
        source=copy.deepcopy(self.p['gaps'][1]);source.pop('depends_on')
        evidence_work=p['gaps'][0];evidence_work.update(work_package_id='WP-EVIDENCE',depends_on=[source['work_package_id']])
        p['gaps']=[source,evidence_work]
        target=next(t for t in run(p)['planning']['review_targets'] if t['work_package_id']=='WP-EVIDENCE')
        self.assertEqual(target['basis']['direct_dependency_scopes'][0]['source_result_inventory'],[dict(record_id='r1',evidence_ids=['e1','e2'])])
        p['planning_decisions']=[dict(work_package_id='WP-EVIDENCE',priority_rank=1,rationale='Fictional rank',uncertainty='Unverified',planner='fictional',planned_at='2026-11-03',basis_sha256=target['basis_sha256'])]
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],[])
        p['evidence'].append(dict(copy.deepcopy(p['evidence'][0]),evidence_id='not-linked-to-evidence-work'))
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],['WP-EVIDENCE'])

    def test_bundle_csv_handoff_and_no_source_mutation(self):
        before=copy.deepcopy(self.p);sheet=handoff(self.p)
        self.assertTrue(all(r['work_type']=='source_review' for r in sheet['selected_work']))
        self.assertTrue(all(r['source_review_inputs'] for r in sheet['selected_work']))
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(self.p).encode()))) as z:
            rows=list(csv.DictReader(io.StringIO(z.read('work-packages.csv').decode())))
        self.assertTrue(all(r['work_type']=='source_review' for r in rows))
        self.assertTrue(all(json.loads(r['source_refs']) for r in rows))
        self.assertTrue(all(json.loads(r['evidence_ids'])==[] for r in rows))
        self.assertEqual(self.p,before)

    def test_real_cli_pre_extraction_work_and_handoff(self):
        path=ROOT/'examples/source-work-protocol.json'
        for script in ('work_review.py','review_handoff.py','research_status.py'):
            args=[sys.executable,script,str(path),'--text']
            if script!='research_status.py':args+=['--work-package','WP-EXTRACTION-REVIEW']
            p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('NOT_READY',p.stdout)
            if script!='research_status.py':self.assertIn('source_review',p.stdout)

if __name__=='__main__':unittest.main()
