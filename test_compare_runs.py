import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from compare_runs import compare_protocols


class CompareRunsTests(unittest.TestCase):
    def setUp(self):
        self.before = json.loads(Path('examples/report-protocol.json').read_text())
        self.after = copy.deepcopy(self.before)

    def test_identical_inputs_and_object_key_reordering(self):
        self.after = dict(reversed(list(self.after.items())))
        result = compare_protocols(self.before, self.after)
        self.assertIn('compare_runs.py', result['engine_sha256'])
        self.assertIn('evidence_workflow.py', result['engine_sha256'])
        self.assertFalse(result['has_changes'])
        self.assertFalse(result['unversioned_change'])
        self.assertEqual(result['before_protocol_sha256'], result['after_protocol_sha256'])
        self.assertEqual(result['entity_changes']['evidence']['unchanged_count'], 1)
        self.assertEqual(result['positional_work_package_ids']['before'], ['WP-001'])
        self.assertTrue(result['identity_warnings'])
        self.before['gaps'][0]['work_package_id'] = 'stable-wp'
        self.after['gaps'][0]['work_package_id'] = 'stable-wp'
        self.assertEqual(compare_protocols(self.before, self.after)['identity_warnings'], [])

    def test_changed_result_without_version_flagged(self):
        self.after['evidence'][0]['result'] = 'synthetic null result'
        result = compare_protocols(self.before, self.after)
        self.assertTrue(result['unversioned_change'])
        self.assertEqual(result['entity_changes']['evidence']['changed'], [dict(id='r1', fields=['result'])])
        self.assertEqual(result['changed_protocol_fields'], ['evidence'])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_changed_version_is_not_scientific_approval(self):
        self.after['version'] = '2'
        self.after['evidence'][0]['result'] = 'synthetic revised result'
        result = compare_protocols(self.before, self.after)
        self.assertTrue(result['version_changed'])
        self.assertFalse(result['unversioned_change'])
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')

    def test_added_result_does_not_add_record_or_study(self):
        self.after['evidence'].append(dict(self.after['evidence'][0], evidence_id='e2', result='no change observed'))
        result = compare_protocols(self.before, self.after)
        self.assertEqual(result['entity_changes']['evidence']['added_ids'], ['e2'])
        self.assertEqual(result['record_ids_added'], [])
        self.assertEqual(result['after_counts']['extracted_studies'], 1)
        self.assertEqual(result['after_counts']['extracted'], 2)

    def test_exclusion_removals_require_reconciliation(self):
        self.after['reports'][0].update(decision='exclude', reason='wrong model')
        with self.assertRaisesRegex(ValueError, 'reconcile screening first'):
            compare_protocols(self.before, self.after)
        self.after['evidence'] = []
        self.after['gaps'] = []
        result = compare_protocols(self.before, self.after)
        self.assertEqual(result['entity_changes']['evidence']['removed_ids'], ['r1'])
        self.assertEqual(result['entity_changes']['work_packages']['removed_ids'], ['WP-001'])
        self.assertEqual(result['entity_changes']['reports']['changed'][0]['fields'], ['decision', 'reason'])

    def test_new_records_and_screening_decisions(self):
        self.after['searches'][0]['record_ids'].append('r3')
        self.after['searches'][0]['total_count'] = 3
        self.after['screening'].append(dict(record_id='r3', decision='exclude', reason='synthetic outside scope'))
        result = compare_protocols(self.before, self.after)
        self.assertEqual(result['record_ids_added'], ['r3'])
        self.assertEqual(result['entity_changes']['screening']['added_ids'], ['r3'])

    def test_context_appraisal_and_plan_changes_visible(self):
        before = json.loads(Path('examples/appraised-protocol.json').read_text())
        after = copy.deepcopy(before)
        after['appraisals'][0]['domains'][0]['judgement'] = 'different supplied judgement'
        after['contexts'][0]['limitations'] = 'additional synthetic limitation'
        result = compare_protocols(before, after)
        self.assertEqual(result['entity_changes']['appraisals']['changed'][0]['fields'], ['domains'])
        self.assertEqual(result['entity_changes']['contexts']['changed'][0]['fields'], ['limitations'])
        plan = json.loads(Path('examples/planned-protocol.json').read_text())
        after = copy.deepcopy(plan)
        after['searches'][0]['has_more'] = True
        result = compare_protocols(plan, after)
        self.assertEqual(result['entity_changes']['search_plan']['changed'][0]['id'], 'search-primary')
        self.assertIn('status', result['entity_changes']['search_plan']['changed'][0]['fields'])

    def test_no_reports_distinguished_from_zero_counts(self):
        self.before.pop('reports')
        self.after.pop('reports')
        result = compare_protocols(self.before, self.after)
        self.assertIsNone(result['before_report_counts'])
        self.assertIsNone(result['after_report_counts'])

    def test_cli_reproducible_and_strict(self):
        with tempfile.TemporaryDirectory() as folder:
            before = Path(folder)/'before.json'
            after = Path(folder)/'after.json'
            before.write_text(json.dumps(self.before))
            self.after['version'] = '2'
            after.write_text(json.dumps(self.after))
            args = [sys.executable, 'compare_runs.py', str(before), str(after)]
            first = subprocess.run(args, capture_output=True, text=True, timeout=20)
            second = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            after.write_text('{"version":"1","version":"2"}')
            failed = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(failed.returncode, 0)
            self.assertNotIn('Traceback', failed.stderr)
            for field in ('gaps', 'evidence', 'screening'):
                for invalid in ([None], ['invalid'], None, {}):
                    malformed = copy.deepcopy(self.after)
                    malformed[field] = invalid
                    after.write_text(json.dumps(malformed))
                    failed = subprocess.run(args, capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(failed.returncode, 0)
                    self.assertNotIn('Traceback', failed.stderr)
