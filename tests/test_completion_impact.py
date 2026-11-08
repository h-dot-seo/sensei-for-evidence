"""Recomputed completion differences are scoped cues, never acceptance decisions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from compare_runs import compare_protocols, completion_work_impact
from evidence_workflow import run

ROOT = Path(__file__).resolve().parents[1]


def fixture(name='completion-binding.json'):
    return json.loads((ROOT / 'examples' / name).read_text())


class CompletionImpactTests(unittest.TestCase):
    def setUp(self):
        self.before = fixture()
        self.after = copy.deepcopy(self.before)

    def rows(self):
        return {r['work_package_id']: r for r in
                compare_protocols(self.before, self.after)['completion_work_impact']['work_packages']}

    def assert_no_basis_change(self, row):
        self.assertEqual(row['changed_completion_basis_fields'], [])
        self.assertEqual(row['work_source_changes']['changed_sections'], [])
        self.assertNotIn('RECOMPUTED_COMPLETION_BASIS_CHANGED', row['comparison_cues'])

    def test_unchanged_current_and_not_complete_are_not_reassessed(self):
        rows = self.rows()
        self.assertEqual(rows['WP-MECHANISM']['after']['completion_review']['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(rows['WP-TRANSLATION']['after']['completion_review']['source_match_status'], 'NOT_COMPLETE')
        for row in rows.values():
            self.assert_no_basis_change(row)
            self.assertEqual(row['comparison_cues'], [])
            self.assertEqual(row['acceptance_assessment'], 'NOT_PERFORMED')
            self.assertEqual(row['change_significance'], 'NOT_ASSESSED')

    def test_already_stale_unchanged_has_no_new_change_cues(self):
        self.before['gaps'][0]['completion_basis_sha256'] = '0' * 64
        self.after = copy.deepcopy(self.before)
        row = self.rows()['WP-MECHANISM']
        self.assertEqual(row['before']['completion_review']['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(row['after']['completion_review']['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(row['comparison_cues'], [])
        self.assert_no_basis_change(row)

    def test_own_locator_is_separate_from_work_source_scope(self):
        self.after['gaps'][0]['artifact_locator'] = 'synthetic://changed-note'
        row = self.rows()['WP-MECHANISM']
        self.assertEqual(row['changed_work_fields'], ['artifact_locator'])
        self.assertEqual(row['changed_completion_basis_fields'], ['artifact_locator'])
        self.assertEqual(row['work_source_changes']['changed_sections'], [])
        self.assertEqual(row['after']['completion_review']['source_match_status'], 'STALE_SOURCE')
        self.assertIn('SUPPLIED_COMPLETION_FIELDS_CHANGED', row['comparison_cues'])
        self.assertIn('RECORDED_COMPLETE_STATUS_RETAINED_AFTER_BASIS_CHANGE', row['comparison_cues'])

    def test_criterion_change_reports_own_and_direct_dependency_scopes(self):
        self.after['gaps'][0]['acceptance_criterion'] += ' Supplied amendment.'
        rows = self.rows()
        own = rows['WP-MECHANISM']['work_source_changes']
        self.assertEqual(own['changed_sections'], ['work_scope'])
        self.assertEqual(own['work_scope_fields_changed'], ['acceptance_criterion'])
        dep = rows['WP-TRANSLATION']['work_source_changes']
        self.assertEqual(dep['changed_sections'], ['direct_dependency_scopes'])
        self.assertEqual(dep['direct_dependency_scope_changes']['changed'],
                         [dict(id='WP-MECHANISM', fields=['acceptance_criterion'])])
        self.assertEqual(rows['WP-TRANSLATION']['changed_completion_basis_fields'], ['work_source_basis_sha256'])

    def test_linked_evidence_exact_changed_fields(self):
        self.after['evidence'][0]['limitations'] += ' Supplied amendment.'
        for row in self.rows().values():
            details = row['work_source_changes']
            self.assertEqual(details['changed_sections'], ['evidence'])
            self.assertEqual(details['evidence_changes']['changed'], [dict(id='e1', fields=['limitations'])])
            self.assertEqual(details['evidence_changes']['unchanged_count'], 1)
            self.assertEqual(details['shared_source_fields_changed'], [])

    def test_evidence_link_addition_and_removal_are_exact(self):
        self.after['gaps'][0]['evidence_ids'] = ['e2']
        removed = self.rows()['WP-MECHANISM']['work_source_changes']['evidence_changes']
        self.assertEqual(removed, dict(added_ids=[], removed_ids=['e1'], changed=[], unchanged_count=1))
        self.before, self.after = self.after, self.before
        added = self.rows()['WP-MECHANISM']['work_source_changes']['evidence_changes']
        self.assertEqual(added, dict(added_ids=['e1'], removed_ids=[], changed=[], unchanged_count=1))

    def test_context_changes_are_only_explicitly_linked(self):
        self.after['contexts'][0]['version'] = 'changed-version'
        rows = self.rows()
        self.assert_no_basis_change(rows['WP-MECHANISM'])
        details = rows['WP-TRANSLATION']['work_source_changes']
        self.assertEqual(details['changed_sections'], ['contexts'])
        self.assertEqual(details['context_changes']['changed'], [dict(id='ctx-guideline', fields=['version'])])

    def test_appraisal_changes_retain_exact_linked_entity(self):
        self.after['appraisals'][0]['limitations'] += ' Supplied amendment.'
        for row in self.rows().values():
            details = row['work_source_changes']
            self.assertEqual(details['changed_sections'], ['appraisals'])
            self.assertEqual(details['appraisal_changes']['changed'], [dict(id='appraisal-1', fields=['limitations'])])

    def test_shared_search_context_is_distinct_from_result_changes(self):
        self.after['searches'][0]['searched_at'] = '2026-02-02'
        for row in self.rows().values():
            details = row['work_source_changes']
            self.assertEqual(details['changed_sections'], ['source_scope_sha256'])
            self.assertEqual(details['shared_source_fields_changed'], ['searches'])
            self.assertEqual(details['evidence_changes']['changed'], [])
            self.assertEqual(details['work_scope_fields_changed'], [])

    def test_prerequisite_locator_changes_label_but_not_dependent_basis(self):
        self.after['gaps'][0]['artifact_locator'] = 'synthetic://changed-note'
        row = self.rows()['WP-TRANSLATION']
        self.assert_no_basis_change(row)
        self.assertEqual(row['direct_prerequisite_completion_changes']['changed'],
                         [dict(id='WP-MECHANISM', fields=['source_match_status'])])
        self.assertEqual(row['comparison_cues'], ['DIRECT_PREREQUISITE_COMPLETION_ROWS_CHANGED'])
        self.assertEqual(row['after']['work_package']['blocked_by'], [])

    def test_prerequisite_status_changes_blocking_but_not_dependent_basis(self):
        self.after['gaps'][0].pop('completion_basis_sha256')
        self.after['gaps'][0]['status'] = 'IN_PROGRESS'
        row = self.rows()['WP-TRANSLATION']
        self.assert_no_basis_change(row)
        self.assertEqual(row['changed_work_fields'], ['blocked_by'])
        self.assertEqual(row['direct_prerequisite_completion_changes']['changed'],
                         [dict(id='WP-MECHANISM', fields=['source_match_status', 'supplied_work_status'])])
        self.assertEqual(row['after']['work_package']['blocked_by'], ['WP-MECHANISM'])

    def test_prerequisite_order_is_visible_without_inventing_entity_changes(self):
        extra = copy.deepcopy(self.before['gaps'][0])
        extra.update(work_package_id='WP-OTHER', artifact_locator='synthetic://other')
        extra.pop('completion_basis_sha256')
        self.before['gaps'].append(extra)
        self.before['gaps'][1]['depends_on'] = ['WP-MECHANISM', 'WP-OTHER']
        self.after = copy.deepcopy(self.before)
        self.after['gaps'][1]['depends_on'].reverse()
        row = self.rows()['WP-TRANSLATION']
        changes = row['direct_prerequisite_completion_changes']
        self.assertEqual(changes['before_ids'], ['WP-MECHANISM', 'WP-OTHER'])
        self.assertEqual(changes['after_ids'], ['WP-OTHER', 'WP-MECHANISM'])
        self.assertTrue(changes['order_changed'])
        self.assertEqual(changes['changed'], [])
        self.assertEqual(changes['added_ids'], [])
        self.assertEqual(changes['removed_ids'], [])
        self.assertIn('DIRECT_PREREQUISITE_COMPLETION_ROWS_CHANGED', row['comparison_cues'])
        self.assertEqual(row['work_source_changes']['changed_sections'], ['direct_dependency_scopes', 'work_scope'])
        self.assertEqual(row['work_source_changes']['work_scope_fields_changed'], ['depends_on'])
        self.assertEqual(row['changed_completion_basis_fields'], ['work_source_basis_sha256'])

    def test_progress_only_change_does_not_change_work_source_basis(self):
        self.after['gaps'][1]['status'] = 'IN_PROGRESS'
        row = self.rows()['WP-TRANSLATION']
        self.assert_no_basis_change(row)
        self.assertEqual(row['comparison_cues'], ['RECORDED_WORK_STATE_CHANGED'])
        self.assertEqual(row['changed_work_fields'], ['status'])

    def test_hash_change_is_not_self_bound_or_reassessment(self):
        self.after['gaps'][0]['completion_basis_sha256'] = '0' * 64
        row = self.rows()['WP-MECHANISM']
        self.assert_no_basis_change(row)
        self.assertEqual(row['changed_work_fields'], ['completion_basis_sha256'])
        self.assertEqual(row['comparison_cues'], ['COMPLETION_SOURCE_LABEL_CHANGED', 'SUPPLIED_COMPLETION_FIELDS_CHANGED'])
        self.assertEqual(row['after']['work_package']['status'], 'COMPLETE')

    def test_no_automatic_status_or_hash_renewal_after_source_change(self):
        self.after['gaps'][0]['deliverable'] += ' Supplied amendment.'
        original = copy.deepcopy(self.after)
        row = self.rows()['WP-MECHANISM']
        self.assertEqual(self.after, original)
        self.assertEqual(row['after']['work_package']['completion_basis_sha256'], original['gaps'][0]['completion_basis_sha256'])
        self.assertEqual(row['after']['work_package']['status'], 'COMPLETE')
        self.assertNotEqual(row['after']['completion_review']['current_basis_sha256'], row['after']['completion_review']['supplied_basis_sha256'])
        self.assertEqual(row['after']['completion_review']['artifact_content_verification'], 'NOT_PERFORMED')

    def test_explicit_ids_survive_reordering_without_identity_warning(self):
        self.after['gaps'].reverse()
        result = compare_protocols(self.before, self.after)
        self.assertEqual(result['identity_warnings'], [])
        self.assertEqual(result['positional_work_package_ids'], dict(before=[], after=[]))
        for row in result['completion_work_impact']['work_packages']:
            self.assert_no_basis_change(row)
            self.assertEqual(row['comparison_cues'], [])

    def test_positional_ids_keep_full_comparison_identity_warning(self):
        for p in (self.before, self.after):
            for gap in p['gaps']:
                gap.pop('work_package_id')
                gap.pop('depends_on', None)
        result = compare_protocols(self.before, self.after)
        self.assertTrue(result['identity_warnings'])
        self.assertEqual(len(result['positional_work_package_ids']['before']), 2)
        self.assertIn('Positional-ID warnings still apply', result['completion_work_impact']['boundary'])

    def test_added_and_removed_work_have_null_two_sided_details(self):
        self.after['gaps'][1]['work_package_id'] = 'WP-NEW'
        rows = self.rows()
        for wid, missing, cue in [('WP-NEW', 'before', 'WORK_ADDED'), ('WP-TRANSLATION', 'after', 'WORK_REMOVED')]:
            row = rows[wid]
            self.assertIsNone(row[missing])
            self.assertIsNone(row['work_source_changes'])
            self.assertIsNone(row['changed_completion_basis_fields'])
            self.assertIn(cue, row['comparison_cues'])
        self.assertEqual(rows['WP-NEW']['direct_prerequisite_completion_changes']['added_ids'], ['WP-MECHANISM'])
        self.assertEqual(rows['WP-TRANSLATION']['direct_prerequisite_completion_changes']['removed_ids'], ['WP-MECHANISM'])

    def test_output_is_detached_from_inputs_and_other_snapshot(self):
        left, right = run(self.before), run(self.after)
        saved = copy.deepcopy((self.before, self.after, left, right))
        result = completion_work_impact(self.before, self.after, left, right)
        row = result['work_packages'][0]
        old = copy.deepcopy(row['before'])
        row['after']['work_package']['evidence_ids'].append('mutation')
        row['after']['completion_review']['basis']['artifact_locator'] = 'mutation'
        result['work_packages'][1]['after']['direct_prerequisite_completion_sources'][0]['source_match_status'] = 'mutation'
        self.assertEqual(row['before'], old)
        self.assertEqual((self.before, self.after, left, right), saved)

    def test_experimental_units_report_exact_linked_changes(self):
        self.before = fixture('experiment-review.json')
        self.after = copy.deepcopy(self.before)
        self.after['experimental_units'][0]['treatment']['concentration']['value'] = 'synthetic-revised-level'
        rows = self.rows()
        changed = [r['work_source_changes']['experimental_unit_changes']['changed'] for r in rows.values()]
        self.assertTrue(any(changed))
        expected_id = self.before['experimental_units'][0]['experiment_id']
        for changes in changed:
            if changes:
                self.assertEqual(changes, [dict(id=expected_id, fields=['treatment'])])

    def test_only_explicit_rationale_statement_changes_affect_basis(self):
        self.before = fixture('rationale-links.json')
        self.after = copy.deepcopy(self.before)
        self.after['synthesis_statements'][0]['text'] += ' Supplied amendment.'
        for row in self.rows().values():
            details = row['work_source_changes']
            self.assertEqual(details['changed_sections'], ['rationale_statements'])
            self.assertEqual(details['rationale_statement_changes']['changed'], [dict(id='statement-1', fields=['current_basis_sha256', 'text'])])
        self.after = copy.deepcopy(self.before)
        self.after['synthesis_statements'][1]['text'] += ' Unlinked amendment.'
        for row in self.rows().values():
            self.assert_no_basis_change(row)

    def test_already_stale_basis_change_stays_stale_but_reports_new_difference(self):
        self.before['gaps'][0]['completion_basis_sha256'] = '0' * 64
        self.after = copy.deepcopy(self.before)
        self.after['gaps'][0]['acceptance_criterion'] += ' Supplied amendment.'
        row = self.rows()['WP-MECHANISM']
        self.assertEqual(row['before']['completion_review']['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(row['after']['completion_review']['source_match_status'], 'STALE_SOURCE')
        self.assertIn('RECOMPUTED_COMPLETION_BASIS_CHANGED', row['comparison_cues'])
        self.assertNotIn('COMPLETION_SOURCE_LABEL_CHANGED', row['comparison_cues'])

    def test_changed_fixture_cli_locates_multiple_sources_without_amendment(self):
        cmd = [sys.executable, str(ROOT / 'compare_runs.py'),
               str(ROOT / 'examples/completion-binding.json'),
               str(ROOT / 'examples/completion-amendment.json')]
        first = subprocess.run(cmd, check=True, capture_output=True).stdout
        self.assertEqual(first, subprocess.run(cmd, check=True, capture_output=True).stdout)
        result = json.loads(first)
        self.assertEqual(result['amendment_review']['stage'], 'NOT_SUPPLIED')
        rows = {r['work_package_id']: r for r in result['completion_work_impact']['work_packages']}
        own, dep = rows['WP-MECHANISM'], rows['WP-TRANSLATION']
        self.assertEqual(own['before']['completion_review']['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(own['after']['completion_review']['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(own['changed_completion_basis_fields'], ['artifact_locator', 'work_source_basis_sha256'])
        self.assertEqual(own['work_source_changes']['changed_sections'], ['contexts', 'evidence', 'work_scope'])
        self.assertEqual(dep['work_source_changes']['changed_sections'], ['contexts', 'direct_dependency_scopes', 'evidence'])
        self.assertEqual(dep['after']['completion_review']['source_match_status'], 'NOT_COMPLETE')
        self.assertEqual(dep['after']['work_package']['blocked_by'], [])

    def test_default_cli_is_deterministic_without_amendment_note(self):
        path = ROOT / 'examples/completion-binding.json'
        cmd = [sys.executable, str(ROOT / 'compare_runs.py'), str(path), str(path)]
        first = subprocess.run(cmd, check=True, capture_output=True).stdout
        second = subprocess.run(cmd, check=True, capture_output=True).stdout
        self.assertEqual(first, second)
        result = json.loads(first)
        self.assertEqual(result['amendment_review']['stage'], 'NOT_SUPPLIED')
        self.assertEqual(len(result['completion_work_impact']['work_packages']), 2)
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertIn('current engine', result['completion_work_impact']['boundary'])
        self.assertIn('not historical acceptance reasons', result['completion_work_impact']['boundary'])


if __name__ == '__main__':
    unittest.main()
