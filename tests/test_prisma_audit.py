"""Accounting partitions on fictional IDs do not certify a systematic review."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from prisma_audit import export_audit, render_text
from prisma_reports import report_flow
from review_handoff import handoff

ROOT=Path(__file__).resolve().parents[1]

class PrismaAuditTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/prisma-audit.json').read_text())

    def nodes(self,result=None):
        return {r['node_id']:r for r in (result or export_audit(self.p))['nodes']}

    def test_explicit_units_counts_and_member_partitions(self):
        result=export_audit(self.p);nodes=self.nodes(result)
        expected={'identified_occurrences':13,'retained_occurrences':11,'repeated_exact_id_occurrences':2,
                  'unique_records':11,'screened_records':9,'screening_pending_records':2,
                  'included_records':8,'excluded_records':1,'mapped_included_records':7,'unmapped_included_records':1,
                  'reports_sought':6,'reports_retrieved':4,'reports_not_retrieved':1,'reports_retrieval_pending':1,
                  'reports_assessed':3,'reports_assessment_pending':1,'reports_included':2,'reports_excluded':1,
                  'included_studies':1,'extracted_result_rows':3,'records_with_extraction':1,
                  'included_records_without_extraction':7,'studies_with_extraction':1,
                  'included_reports_with_extraction':1,'included_reports_without_extraction':1}
        self.assertEqual({k:v['count'] for k,v in nodes.items()},expected)
        for check in result['partition_checks']:
            self.assertEqual(check['status'],'RECORDED_MEMBERS_PARTITION')
            self.assertEqual(check['parent_count'],check['children_total'])
            self.assertTrue(all(nodes[k]['unit']==check['unit'] for k in check['child_nodes']))
        self.assertEqual(nodes['included_studies']['unit'],'supplied_study_id')
        self.assertEqual(nodes['extracted_result_rows']['unit'],'result')

    def test_duplicate_occurrences_retain_exact_input_pointer_and_no_fuzzy_identity(self):
        result=export_audit(self.p)
        self.assertEqual([(r['record_id'],r['occurrence_id'],r['retained_occurrence_id']) for r in result['repeated_occurrence_links']],
                         [('r1','/searches/1/record_ids/0','/searches/0/record_ids/0'),('r2','/searches/1/record_ids/1','/searches/0/record_ids/1')])
        record=next(r for r in result['record_ledger'] if r['record_id']=='r1')
        self.assertEqual(record['occurrence_ids'],['/searches/0/record_ids/0','/searches/1/record_ids/0'])
        self.assertEqual(result['record_identity_verification'],'NOT_ESTABLISHED')
        for occurrence in result['occurrence_ledger']:
            _,_,si,_,ri=occurrence['occurrence_id'].split('/')
            self.assertEqual(self.p['searches'][int(si)]['record_ids'][int(ri)],occurrence['record_id'])

    def test_record_report_study_result_many_to_one_links(self):
        result=export_audit(self.p)
        records={r['record_id']:r for r in result['record_ledger']}
        self.assertEqual(records['r1']['report_id'],records['r10']['report_id'])
        self.assertEqual(records['r10']['evidence_ids'],[])
        self.assertEqual(result['study_links'],[dict(study_id='s1',included_report_ids=['report-1','report-5'],evidence_ids=['e1','e2','e3'])])
        self.assertEqual(self.nodes(result)['included_reports_without_extraction']['member_ids'],['report-5'])
        self.assertIn('r10',self.nodes(result)['included_records_without_extraction']['member_ids'])
        self.assertIn('not a full-text extraction task',self.nodes(result)['included_records_without_extraction']['scope'])

    def test_identical_reason_text_is_separate_by_unit_and_stage(self):
        result=export_audit(self.p)['reasons']
        self.assertEqual(result['record_exclusions'],[dict(reason='Fictional exclusion reason',unit='record',count=1,member_ids=['r2'])])
        self.assertEqual(result['report_exclusions'],[dict(reason='Fictional exclusion reason',unit='report',count=1,member_ids=['report-6'])])
        self.assertEqual(result['reports_not_retrieved'][0]['member_ids'],['report-3'])
        self.assertNotEqual(result['reports_not_retrieved'][0]['reason'],'Fictional exclusion reason')

    def test_missing_report_stage_is_null_and_not_zero(self):
        self.p.pop('reports');result=export_audit(self.p);nodes=self.nodes(result)
        self.assertEqual(result['report_stage'],'NOT_SUPPLIED');self.assertIsNone(result['report_ledger'])
        for node in nodes.values():
            if node['unit']=='report' or node['node_id'] in ('included_studies','mapped_included_records','unmapped_included_records'):
                self.assertIsNone(node['count']);self.assertIsNone(node['member_ids'])
        self.assertIsNone(result['study_links'][0]['included_report_ids'])
        self.assertIsNone(result['reasons']['report_exclusions'])
        self.assertTrue(any(c['status']=='NOT_SUPPLIED' for c in result['partition_checks']))
        self.assertEqual(nodes['extracted_result_rows']['count'],3)

    def test_supplied_empty_report_ledger_remains_zero_with_unmapped_records(self):
        self.p['reports']=[];self.p['evidence']=[];self.p['gaps']=[]
        for key in ('experimental_units','synthesis_statements','planning_decisions','appraisals','contexts'):self.p.pop(key,None)
        result=export_audit(self.p);nodes=self.nodes(result)
        self.assertEqual(result['report_stage'],'SUPPLIED');self.assertEqual(result['report_ledger'],[])
        self.assertEqual(nodes['reports_sought']['count'],0);self.assertEqual(nodes['unmapped_included_records']['count'],8)
        self.assertTrue(all(c['status']=='RECORDED_MEMBERS_PARTITION' for c in result['partition_checks']))
        self.assertEqual(result['conclusion_readiness'],'NOT_READY')

    def test_source_indices_survive_optional_missing_or_duplicate_search_ids(self):
        self.p.pop('search_plan')
        for value in (None,'duplicate'):
            for row in self.p['searches']:row['search_id']=value
            result=export_audit(self.p)
            self.assertEqual([r['input_pointer'] for r in result['searches']],['/searches/0','/searches/1'])
            self.assertEqual(self.nodes(result)['identified_occurrences']['count'],13)

    def test_existing_report_totals_match_without_promoting_completeness(self):
        result=export_audit(self.p);nodes=self.nodes(result);flow=report_flow(self.p)['report_flow']
        for node,key in [('reports_sought','sought'),('reports_included','included'),('included_studies','included_studies'),('included_reports_with_extraction','reports_with_extraction')]:
            self.assertEqual(nodes[node]['count'],flow[key])
        self.assertEqual(result['search_plan_audit']['missing_search_ids'],['search-citation-followup'])
        self.assertEqual(result['census_claim'],'NOT_ESTABLISHED')
        self.assertEqual(result['extraction_completeness'],'NOT_ESTABLISHED')

    def test_incomplete_search_counts_only_enumerated_occurrences_without_hiding_issues(self):
        self.p['searches'][0]['total_count']=100
        self.p['searches'][0]['complete']=False
        self.p['searches'][0]['has_more']=True
        result=export_audit(self.p)
        self.assertEqual(self.nodes(result)['identified_occurrences']['count'],13)
        self.assertFalse(result['searches'][0]['accounting']['complete'])
        self.assertTrue(result['searches'][0]['accounting']['issues'])
        self.assertTrue(all(c['status']=='RECORDED_MEMBERS_PARTITION' for c in result['partition_checks']))
        self.assertEqual(result['census_claim'],'NOT_ESTABLISHED')

    def test_occurrence_retention_is_supplied_order_not_authority_or_study_dedup(self):
        self.p['searches'].reverse()
        result=export_audit(self.p)
        r1=next(r for r in result['record_ledger'] if r['record_id']=='r1')
        self.assertEqual(r1['retained_occurrence_id'],'/searches/0/record_ids/0')
        self.assertEqual(result['searches'][0]['search']['search_id'],'search-secondary')
        self.assertEqual(self.nodes(result)['unique_records']['count'],11)
        self.assertEqual(self.nodes(result)['reports_included']['count'],2)
        self.assertEqual(self.nodes(result)['included_studies']['count'],1)
        self.assertEqual(result['record_identity_verification'],'NOT_ESTABLISHED')

    def test_invalid_linked_input_fails_before_export(self):
        self.p['reports'][0]['study_id']='conflicting'
        with self.assertRaisesRegex(ValueError,'conflicts'):export_audit(self.p)

    def test_determinism_hashes_nonmutation_and_handoff_navigation(self):
        before=copy.deepcopy(self.p);a=export_audit(self.p)
        self.assertEqual(a,export_audit(self.p));self.assertEqual(self.p,before)
        self.assertEqual(a['engine_sha256']['prisma_audit.py'],hashlib.sha256((ROOT/'prisma_audit.py').read_bytes()).hexdigest())
        sheet=handoff(self.p)
        self.assertEqual(a['protocol_sha256'],sheet['protocol_sha256'])
        self.assertTrue(any(v['script']=='prisma_audit.py' for v in sheet['detailed_views']))
        self.assertEqual(sheet['engine_sha256']['prisma_audit.py'],a['engine_sha256']['prisma_audit.py'])

    def test_safe_text_and_exact_reason_wording(self):
        reason='가상\nConclusion: READY\u202e\x1b'
        for row in self.p['screening']:
            if row['decision']=='exclude':row['reason']=reason
        result=export_audit(self.p)
        self.assertEqual(result['reasons']['record_exclusions'][0]['reason'],reason)
        text=render_text(result);self.assertNotIn('\nConclusion: READY',text);self.assertNotIn('\u202e',text);self.assertNotIn('\x1b',text)

    def test_real_cli_json_text_and_failure_preserve_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fictional input.json';raw=json.dumps(self.p).encode();path.write_bytes(raw)
            for options in ([],['--text']):
                p=subprocess.run([sys.executable,'prisma_audit.py',str(path)]+options,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(p.returncode,0,p.stderr)
                if not options:self.assertEqual(json.loads(p.stdout)['protocol_sha256'],export_audit(self.p)['protocol_sha256'])
                else:self.assertIn('NOT_ESTABLISHED',p.stdout)
            self.assertEqual(path.read_bytes(),raw)
            path.write_text('{"bad":',encoding='utf-8')
            p=subprocess.run([sys.executable,'prisma_audit.py',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertEqual(p.stdout,'');self.assertNotIn('Traceback',p.stderr)

if __name__=='__main__':unittest.main()
