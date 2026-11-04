"""Direct prerequisite completion cues never gate work or certify acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evidence_workflow import run
from review_handoff import handoff, render_text as render_handoff
from work_review import review_packets, navigation_summary, render_brief, render_text

ROOT = Path(__file__).resolve().parent


class PrerequisiteCompletionTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / 'examples/completion-binding.json').read_text())

    def selected(self):
        return review_packets(self.protocol, 'WP-TRANSLATION')

    def test_current_direct_binding_visible_with_prerequisite_packet_omitted(self):
        result = self.selected()
        self.assertEqual(len(result['packets']), 1)
        packet = result['packets'][0]
        row = packet['direct_prerequisite_completion_reviews'][0]
        self.assertEqual(row['work_package_id'], 'WP-MECHANISM')
        self.assertEqual(row['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['supplied_work_status'], 'COMPLETE')
        self.assertEqual(row['acceptance_assessment'], 'NOT_PERFORMED')
        self.assertEqual(row['artifact_content_verification'], 'NOT_PERFORMED')
        self.assertEqual(packet['completion_review']['source_match_status'], 'NOT_COMPLETE')
        edge = result['dependency_review']['edges'][0]
        self.assertFalse(edge['prerequisite_packet_included'])
        self.assertEqual(edge['supplied_prerequisite_status'], 'COMPLETE')
        self.assertEqual(edge['prerequisite_completion_source_status'], 'CURRENT_SOURCE')
        self.assertEqual(result['dependency_review']['omitted_direct_prerequisite_ids'], ['WP-MECHANISM'])

    def test_stale_prerequisite_does_not_reclassify_unblocked_work(self):
        self.protocol['gaps'][0]['artifact_locator'] = 'synthetic://changed-note'
        result = self.selected()
        packet = result['packets'][0]
        row = packet['direct_prerequisite_completion_reviews'][0]
        self.assertEqual(row['source_match_status'], 'STALE_SOURCE')
        self.assertNotEqual(row['supplied_basis_sha256'], row['current_basis_sha256'])
        self.assertEqual(packet['work_package']['blocked_by'], [])
        self.assertEqual(navigation_summary(result)['work_state_groups']['unblocked_planned'], ['WP-TRANSLATION'])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        for text in (render_text(result), render_brief(result)):
            self.assertIn('STALE_SOURCE', text)
            self.assertIn('Direct prerequisite completion sources (not acceptance)', text)

    def test_legacy_completion_and_unfinished_prerequisites_remain_distinct(self):
        self.protocol['gaps'][0].pop('completion_basis_sha256')
        packet = self.selected()['packets'][0]
        self.assertEqual(packet['direct_prerequisite_completion_reviews'][0]['source_match_status'], 'UNBOUND_COMPLETION')
        self.assertEqual(packet['work_package']['blocked_by'], [])
        self.protocol['gaps'][0]['status'] = 'IN_PROGRESS'
        packet = self.selected()['packets'][0]
        row = packet['direct_prerequisite_completion_reviews'][0]
        self.assertEqual(row['source_match_status'], 'NOT_COMPLETE')
        self.assertEqual(row['supplied_work_status'], 'IN_PROGRESS')
        self.assertEqual(packet['work_package']['blocked_by'], ['WP-MECHANISM'])

    def test_only_direct_edges_are_projected_without_claiming_recursive_acceptance(self):
        extra = copy.deepcopy(self.protocol['gaps'][0])
        extra.update(work_package_id='WP-EARLIER', artifact_locator='synthetic://earlier')
        extra.pop('completion_basis_sha256')
        self.protocol['gaps'].append(extra)
        self.protocol['gaps'][0]['depends_on'] = ['WP-EARLIER']
        basis = next(row for row in run(self.protocol)['planning']['completion_ledger']
                     if row['work_package_id'] == 'WP-MECHANISM')
        self.protocol['gaps'][0]['completion_basis_sha256'] = basis['current_basis_sha256']
        selected = self.selected()
        rows = selected['packets'][0]['direct_prerequisite_completion_reviews']
        self.assertEqual([row['work_package_id'] for row in rows], ['WP-MECHANISM'])
        self.assertEqual(rows[0]['source_match_status'], 'CURRENT_SOURCE')
        self.assertIn('not recursive acceptance', selected['dependency_review']['boundary'])
        expanded = review_packets(self.protocol, 'WP-TRANSLATION', True)
        middle = next(p for p in expanded['packets'] if p['work_package']['work_package_id'] == 'WP-MECHANISM')
        self.assertEqual(middle['direct_prerequisite_completion_reviews'][0]['source_match_status'], 'UNBOUND_COMPLETION')
        self.assertEqual(expanded['packets'][-1], selected['packets'][0])

    def test_unrelated_work_and_shared_evidence_do_not_become_prerequisites(self):
        unrelated = copy.deepcopy(self.protocol['gaps'][0])
        unrelated.update(work_package_id='WP-UNRELATED', completion_basis_sha256='0' * 64)
        self.protocol['gaps'].append(unrelated)
        rows = self.selected()['packets'][0]['direct_prerequisite_completion_reviews']
        self.assertEqual([row['work_package_id'] for row in rows], ['WP-MECHANISM'])
        self.assertEqual(rows[0]['source_match_status'], 'CURRENT_SOURCE')
        root = review_packets(self.protocol, 'WP-MECHANISM')['packets'][0]
        self.assertEqual(root['direct_prerequisite_completion_reviews'], [])

    def test_handoff_retains_exact_direct_review_without_reopening_work(self):
        self.protocol['gaps'][0]['deliverable'] = 'Changed fictional requirement'
        result = handoff(self.protocol, 'WP-TRANSLATION')
        rows = result['selected_work'][0]['direct_prerequisite_completion_reviews']
        self.assertEqual(rows, self.selected()['packets'][0]['direct_prerequisite_completion_reviews'])
        self.assertIn('STALE_SOURCE', render_handoff(result))
        self.assertEqual(result['selected_work'][0]['work_package']['blocked_by'], [])
        self.assertEqual(self.protocol['gaps'][0]['status'], 'COMPLETE')

    def test_no_protocol_mutation_or_shared_summary_rows(self):
        before = copy.deepcopy(self.protocol)
        result = self.selected()
        self.assertEqual(before, self.protocol)
        snapshot = copy.deepcopy(result)
        summary = navigation_summary(result)
        summary['work'][0]['direct_prerequisite_completion_reviews'][0]['source_match_status'] = 'mutation'
        self.assertEqual(snapshot, result)
        result['packets'][0]['direct_prerequisite_completion_reviews'][0]['basis']['artifact_locator'] = 'mutation'
        self.assertEqual(before, self.protocol)

    def test_source_review_dependencies_and_cli_are_supported(self):
        protocol = json.loads((ROOT / 'examples/prerequisite-review.json').read_text())
        protocol['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://receipt-note', acceptance_verified=True)
        result = review_packets(protocol, 'WP-EXTRACTION-REVIEW')
        row = result['packets'][0]['direct_prerequisite_completion_reviews'][0]
        self.assertEqual(row['work_package_id'], 'WP-RECEIPT-REVIEW')
        self.assertEqual(row['source_match_status'], 'UNBOUND_COMPLETION')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'protocol.json'
            path.write_text(json.dumps(protocol), encoding='utf-8')
            output = subprocess.run([sys.executable, str(ROOT / 'work_review.py'), str(path),
                                     '--work-package=WP-EXTRACTION-REVIEW', '--brief'],
                                    check=True, capture_output=True).stdout.decode('utf-8')
            self.assertIn('UNBOUND_COMPLETION', output)
            self.assertIn('not acceptance', output)

    def test_multiple_prerequisites_preserve_explicit_order_and_determinism(self):
        extra = copy.deepcopy(self.protocol['gaps'][0])
        extra.update(work_package_id='WP-EARLIER', artifact_locator='synthetic://earlier')
        extra.pop('completion_basis_sha256')
        self.protocol['gaps'].append(extra)
        self.protocol['gaps'][1]['depends_on'] = ['WP-MECHANISM', 'WP-EARLIER']
        result = self.selected()
        rows = result['packets'][0]['direct_prerequisite_completion_reviews']
        self.assertEqual([row['work_package_id'] for row in rows], ['WP-MECHANISM', 'WP-EARLIER'])
        self.assertEqual([row['source_match_status'] for row in rows], ['CURRENT_SOURCE', 'UNBOUND_COMPLETION'])
        self.assertEqual([row['depends_on'] for row in result['dependency_review']['edges']], ['WP-MECHANISM', 'WP-EARLIER'])
        self.assertEqual(result, self.selected())

    def test_nested_prerequisite_rows_do_not_alias_other_packets(self):
        result = review_packets(self.protocol, 'WP-TRANSLATION', True)
        root, dependent = result['packets']
        original = copy.deepcopy(root['completion_review'])
        dependent['direct_prerequisite_completion_reviews'][0]['basis']['artifact_locator'] = 'mutation'
        self.assertEqual(root['completion_review'], original)
        self.assertEqual(self.selected()['packets'][0]['direct_prerequisite_completion_reviews'][0]['basis'], original['basis'])


if __name__ == '__main__':
    unittest.main()
