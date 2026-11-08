import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from research_status import status, render_text


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/review-demo.json').read_text())

    def test_combined_demo_queues_and_bounds(self):
        result = status(self.protocol)
        self.assertEqual(result['queues']['missing_planned_searches'], ['search-secondary'])
        self.assertEqual(result['queues']['incomplete_searches'], [])
        self.assertEqual(result['queues']['context_review_pending'], ['ctx-guideline'])
        self.assertEqual(result['queues']['evidence_without_recorded_appraisal'], ['e2'])
        self.assertEqual(result['queues']['dependency_unblocked_planned_work'], ['WP-MECHANISM'])
        self.assertEqual(result['queues']['blocked_work'][0]['blocked_by'], ['WP-MECHANISM'])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertIn('research_status.py', result['engine_sha256'])

    def test_absent_plan_and_report_are_not_zero(self):
        self.protocol.pop('search_plan')
        self.protocol.pop('reports')
        result = status(self.protocol)
        self.assertIsNone(result['counts']['missing_planned_searches'])
        self.assertIsNone(result['queues']['reports_pending_retrieval'])
        self.assertIsNone(result['counts']['included_reports_without_extraction'])
        self.assertIn('Report retrieval pending: not supplied', render_text(result))

    def test_unresolved_pages_surface_as_incomplete_source(self):
        self.protocol['searches'][0]['pages'][1]['has_more'] = True
        result = status(self.protocol)
        self.assertEqual(result['counts']['incomplete_searches'], 1)
        self.assertIn('page_pagination_unresolved', result['queues']['incomplete_searches'][0]['issues'])

    def test_screening_pending_is_identifier_based(self):
        self.protocol['screening'].pop()
        result = status(self.protocol)
        self.assertEqual(result['queues']['records_pending_screening'], ['r2'])

    def empty_extraction(self):
        for key in ('evidence','gaps','contexts','appraisals'):
            self.protocol[key] = []

    def test_report_stage_queues_are_separate(self):
        self.empty_extraction()
        self.protocol['reports'][0].update(retrieval='pending',decision='pending')
        result = status(self.protocol)
        self.assertEqual(result['queues']['reports_pending_retrieval'], ['report-1'])
        self.assertEqual(result['queues']['included_reports_without_extraction'], [])
        self.protocol['reports'][0].update(retrieval='retrieved',decision='pending')
        result = status(self.protocol)
        self.assertEqual(result['queues']['reports_pending_assessment'], ['report-1'])
        self.protocol['reports'][0].pop('decision')
        self.assertEqual(status(self.protocol)['queues']['reports_pending_assessment'], ['report-1'])
        self.protocol['reports'][0].update(decision='include')
        self.assertEqual(status(self.protocol)['queues']['included_reports_without_extraction'], ['report-1'])
        self.protocol['reports'][0].update(decision='exclude', reason='synthetic wrong scope')
        self.assertEqual(status(self.protocol)['queues']['included_reports_without_extraction'], [])

    def test_unretrieved_and_unmapped_are_visible(self):
        self.empty_extraction()
        self.protocol['reports'][0].update(retrieval='not_retrieved',decision='pending',reason='synthetic unavailable')
        self.assertEqual(status(self.protocol)['queues']['reports_not_retrieved'], ['report-1'])
        self.protocol['reports'] = []
        self.assertEqual(status(self.protocol)['queues']['unmapped_included_records'], ['r1'])

    def test_complete_dependency_does_not_promote_readiness(self):
        self.protocol['gaps'][1]['status'] = 'IN_PROGRESS'
        result = status(self.protocol)
        self.assertEqual(result['queues']['work_in_progress'], ['WP-TRANSLATION'])
        self.assertEqual(result['queues']['blocked_work'][0]['work_package_id'], 'WP-TRANSLATION')
        self.protocol['gaps'][1]['status'] = 'PLANNED'
        self.protocol['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://artifact', acceptance_verified=True)
        result = status(self.protocol)
        self.assertEqual(result['queues']['dependency_unblocked_planned_work'], ['WP-TRANSLATION'])
        self.assertEqual(result['queues']['completed_work_assertions'], ['WP-MECHANISM'])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_no_mutation_and_reproducible_status(self):
        original = copy.deepcopy(self.protocol)
        self.assertEqual(status(self.protocol), status(self.protocol))
        self.assertEqual(self.protocol, original)
        from compare_runs import compare_protocols
        self.assertEqual(status(self.protocol)['protocol_sha256'], compare_protocols(self.protocol, self.protocol)['before_protocol_sha256'])

    def test_cli_json_text_and_strict_input(self):
        args = [sys.executable,'research_status.py','examples/review-demo.json']
        result = subprocess.run(args,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['counts']['missing_planned_searches'],1)
        result = subprocess.run(args+['--text'],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Missing planned searches: 1',result.stdout)
        self.assertIn('Conclusion: NOT_READY',result.stdout)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.json';path.write_text('{"question":1,"question":2}')
            result=subprocess.run([sys.executable,'research_status.py',str(path)],capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('Traceback',result.stderr)
