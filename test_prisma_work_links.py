"""Synthetic reverse source/result work links do not attest task coverage."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from prisma_audit import export_audit, render_text
from offline_adapter import assemble
ROOT=Path(__file__).resolve().parent

def fixture(name):
    return json.loads((ROOT/'examples'/name).read_text(encoding='utf-8'))

class PrismaWorkLinksTests(unittest.TestCase):
    def setUp(self):self.p=fixture('source-work-protocol.json')
    def trace(self,p=None):return export_audit(self.p if p is None else p)['work_traceability']
    def accepted(self):
        p=assemble(fixture('adapter-protocol.json'),fixture('adapter-fixture.json'),fixture('adapter-reviews.json'))['protocol']
        p['gaps']=copy.deepcopy(self.p['gaps'])
        p['gaps'].append(dict(work_package_id='WP-EVIDENCE',evidence_ids=['e1'],depends_on=['WP-EXTRACTION-REVIEW'],question='Fictional question',deliverable='Fictional evidence note',acceptance_criterion='Record limits'))
        return p
    def test_missing_search_has_task_without_observed_receipt(self):
        t=self.trace();p={r['search_id']:r for r in t['planned_search_links']}
        self.assertEqual(p['search-secondary']['observed_search_indices'],[])
        self.assertEqual(p['search-secondary']['direct_source_work_ids'],['WP-RECEIPT-REVIEW'])
        self.assertEqual(p['search-primary']['observed_search_indices'],[0])
    def test_search_links_do_not_expand_into_record_links(self):
        r={r['record_id']:r for r in self.trace()['record_links']}
        self.assertEqual(r['r1']['direct_source_work_ids'],['WP-EXTRACTION-REVIEW'])
        self.assertEqual(r['r2']['direct_source_work_ids'],[])
        self.assertEqual(r['r1']['via_result_work_ids'],[])
    def test_source_record_work_does_not_link_results(self):
        t=self.trace(self.accepted());r={r['evidence_id']:r for r in t['result_links']}
        self.assertEqual(r['e1']['direct_evidence_work_ids'],['WP-EVIDENCE'])
        self.assertEqual(r['e2']['direct_evidence_work_ids'],[])
        rr=next(r for r in t['record_links'] if r['record_id']=='r1')
        self.assertEqual(rr['via_result_work_ids'],['WP-EVIDENCE'])
        report=t['report_links'][0]['record_links'][0]
        self.assertEqual(report['via_record_source_work_ids'],['WP-EXTRACTION-REVIEW'])
        self.assertEqual(report['via_record_result_work_ids'],['WP-EVIDENCE'])
    def test_completion_artifact_does_not_change_prisma_or_receipts(self):
        before=export_audit(self.p)
        self.p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic://review-note',acceptance_verified=True)
        after=export_audit(self.p);w=after['work_traceability']['work_packages'][0]
        self.assertEqual(w['artifact_status'],'LOCATOR_SUPPLIED')
        self.assertEqual(w['artifact_verification'],'NOT_PERFORMED')
        self.assertEqual(w['acceptance_assessment'],'NOT_PERFORMED')
        self.assertEqual(w['work_package']['artifact_locator'],'synthetic://review-note')
        for k in ('nodes','partition_checks','reasons','search_plan_audit','census_claim','conclusion_readiness'):
            self.assertEqual(before[k],after[k])
        self.assertEqual(self.p['adapter_receipts']['reviews'],[])
        self.assertFalse(self.p['searches'][0]['complete'])
    def test_no_work_preserves_inventory_not_task_requirement(self):
        self.p['gaps']=[];t=self.trace()
        self.assertEqual(t['work_packages'],[])
        self.assertTrue(all(r['direct_source_work_ids']==[] for r in t['record_links']))
        self.assertIn('not a required or completed task',t['boundary'])
    def test_absent_plan_and_report_differ_from_empty_report(self):
        p=fixture('multi-result-protocol.json');p.pop('reports',None);p.pop('search_plan',None)
        t=self.trace(p);self.assertIsNone(t['report_links']);self.assertIsNone(t['planned_search_links'])
        p['evidence']=[];p['gaps']=[];p['reports']=[];p.pop('contexts',None)
        t=self.trace(p);self.assertEqual(t['report_links'],[])
    def test_multiple_records_per_report_keep_indirect_links_separate(self):
        p=fixture('prisma-audit.json');p['gaps']=[];p.pop('planning_decisions',None)
        report=next(r for r in p['reports'] if len(r['record_ids'])>1)
        rid=report['record_ids'][0]
        w=copy.deepcopy(self.p['gaps'][1]);w.pop('depends_on');w['source_refs']=[dict(kind='record',record_id=rid)]
        p['gaps']=[w];t=self.trace(p)
        rows=next(r for r in t['report_links'] if r['report_id']==report['report_id'])['record_links']
        self.assertEqual(sum(bool(r['via_record_source_work_ids']) for r in rows),1)
    def test_input_pointers_default_work_ids_and_nonmutation(self):
        p=self.accepted();p['gaps'][-1].pop('work_package_id');original=copy.deepcopy(p)
        t=self.trace(p);self.assertEqual(p,original)
        for i,w in enumerate(t['work_packages']):self.assertEqual(w['input_pointer'],f'/gaps/{i}')
        self.assertEqual(t['result_links'][0]['direct_evidence_work_ids'],['WP-003'])
        t['work_packages'][0]['work_package']['question']='mutation';self.assertEqual(p,original)
    def test_text_escapes_supplied_artifact_control_characters(self):
        self.p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic://\x1b[31m\u202eevil',acceptance_verified=True)
        text=render_text(export_audit(self.p));self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
    def test_real_cli_reproducible_source_work_export(self):
        cmd=[sys.executable,str(ROOT/'prisma_audit.py'),str(ROOT/'examples/source-work-protocol.json')]
        a=subprocess.run(cmd,capture_output=True,check=True).stdout
        b=subprocess.run(cmd,capture_output=True,check=True).stdout
        self.assertEqual(a,b);self.assertEqual(json.loads(a)['work_traceability'],self.trace())

if __name__=='__main__':unittest.main()
