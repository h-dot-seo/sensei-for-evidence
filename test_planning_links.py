"""Supplied planning assertions, never automatic priority or development advice."""
import copy
import csv
import io
import zipfile
import json
from pathlib import Path
import unittest

from evidence_workflow import run
from work_review import review_packets, render_text
from research_status import status
from compare_runs import compare_protocols
from research_bundle import build_bundle, verify
from offline_adapter import assemble
import tempfile


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(Path('examples/planning-review.json').read_text())

    def refresh(self, protocol):
        targets = {r['work_package_id']: r for r in run(protocol)['planning']['review_targets']}
        for decision in protocol['planning_decisions']:
            decision['basis_sha256'] = targets[decision['work_package_id']]['basis_sha256']

    def test_supplied_rank_does_not_bypass_dependencies_or_generate_approval(self):
        research = run(self.p)
        self.assertEqual(research['planning']['current_rank_groups'][0]['work_package_ids'], ['WP-TRANSLATION'])
        self.assertEqual(research['execution_order'], ['WP-MECHANISM', 'WP-TRANSLATION'])
        self.assertEqual(status(self.p)['queues']['dependency_unblocked_planned_work'], ['WP-MECHANISM'])
        packet = review_packets(self.p, 'WP-TRANSLATION')['packets'][0]
        self.assertEqual(packet['work_package']['blocked_by'], ['WP-MECHANISM'])
        self.assertEqual(packet['planning_assertion']['current_priority_rank'], 1)
        self.assertEqual(packet['decision_status'], 'NO_AUTOMATED_DECISION')

    def test_missing_and_tied_assertions_are_explicit(self):
        self.p.pop('planning_decisions')
        planning = run(self.p)['planning']
        self.assertEqual(planning['work_without_planning_assertion'], ['WP-MECHANISM', 'WP-TRANSLATION'])
        self.assertEqual(planning['current_rank_groups'], [])
        self.p = json.loads(Path('examples/planning-review.json').read_text())
        self.p['planning_decisions'][1]['priority_rank'] = 1
        groups = run(self.p)['planning']['current_rank_groups']
        self.assertEqual(groups, [dict(supplied_priority_rank=1,work_package_ids=['WP-MECHANISM','WP-TRANSLATION'],tie=True)])
        self.p['planning_decisions'].pop()
        self.assertEqual(run(self.p)['planning']['work_without_planning_assertion'], ['WP-MECHANISM'])

    def test_rank_shape_and_duplicate_unknown_targets_rejected(self):
        for value in (True, 0, -1, 1.0, '1', None):
            p = copy.deepcopy(self.p); p['planning_decisions'][0]['priority_rank'] = value
            with self.assertRaises(ValueError): run(p)
        for mutate in (lambda p: p['planning_decisions'].append(copy.deepcopy(p['planning_decisions'][0])),
                       lambda p: p['planning_decisions'][0].update(work_package_id='unknown'),
                       lambda p: p['planning_decisions'][0].update(basis_sha256='bad'),
                       lambda p: p['planning_decisions'][0].update(uncertainty=''),
                       lambda p: p.update(planning_decisions={})):
            p = copy.deepcopy(self.p); mutate(p)
            with self.assertRaises(ValueError): run(p)

    def test_stale_source_assertions_are_historical_not_current_ranks(self):
        before = copy.deepcopy(self.p)
        self.p['evidence'][0]['result'] = 'Changed supplied result'
        planning = run(self.p)['planning']
        self.assertEqual(planning['current_rank_groups'], [])
        self.assertEqual(planning['work_with_stale_planning_assertion'], ['WP-MECHANISM', 'WP-TRANSLATION'])
        self.assertTrue(all(row['current_priority_rank'] is None for row in planning['planning_ledger']))
        self.assertEqual(planning['planning_ledger'][1]['assertion']['priority_rank'], 1)
        self.assertEqual(status(self.p)['counts']['work_with_stale_planning_assertion'], 2)
        self.assertIn('STALE_SOURCE', render_text(review_packets(self.p)))
        self.assertTrue(compare_protocols(before, self.p)['has_changes'])
        self.assertNotEqual(planning['review_targets'][0]['basis_sha256'], before['planning_decisions'][1]['basis_sha256'])

    def test_scope_context_appraisal_and_sources_invalidate_binding(self):
        changes = [lambda p: p['gaps'][1].update(acceptance_criterion='Changed completion criterion'),
                   lambda p: p['contexts'][0].update(applicability='Changed supplied applicability'),
                   lambda p: p['appraisals'][0]['domains'][0].update(judgement='Changed assertion'),
                   lambda p: p['searches'][0].update(searched_at='different receipt date'),
                   lambda p: p['reports'][0].update(locator='synthetic://updated'),
                   lambda p: p['screening'][0].update(reason='Changed source eligibility rationale'),
                   lambda p: p.update(question='Changed planning scope?')]
        for change in changes:
            p = copy.deepcopy(self.p); change(p)
            with self.subTest(change=change):
                self.assertIn('WP-TRANSLATION', run(p)['planning']['work_with_stale_planning_assertion'])

    def test_progress_and_version_updates_do_not_renew_or_stale_sources(self):
        self.p['version'] = 'next-synthetic-version'
        self.p['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://done', acceptance_verified=True)
        planning = run(self.p)['planning']
        self.assertEqual(planning['work_with_stale_planning_assertion'], [])
        self.assertEqual(status(self.p)['queues']['dependency_unblocked_planned_work'], ['WP-TRANSLATION'])
        self.assertEqual(run(self.p)['conclusion_readiness'], 'NOT_READY')
        self.assertIn('WP-MECHANISM', [wid for group in planning['current_rank_groups'] for wid in group['work_package_ids']])
        self.assertIn('including completed work', review_packets(self.p)['rank_groups_scope'])

    def test_unrelated_work_scope_does_not_stale_existing_assertions(self):
        extra = copy.deepcopy(self.p['gaps'][0]); extra['work_package_id'] = 'WP-UNRANKED'
        extra['depends_on'] = []
        self.p['gaps'].append(extra)
        planning = run(self.p)['planning']
        self.assertEqual(planning['work_with_stale_planning_assertion'], [])
        self.assertEqual(planning['work_without_planning_assertion'], ['WP-UNRANKED'])

    def test_canonical_object_order_is_ignored_and_boolean_edits_are_not(self):
        baseline = run(self.p)['planning']['review_targets']
        reordered = {key: self.p[key] for key in reversed(list(self.p))}
        self.assertEqual(baseline, run(reordered)['planning']['review_targets'])
        self.p['evidence'][0]['sample_size'] = 1
        self.refresh(self.p)
        self.p['evidence'][0]['sample_size'] = True
        self.assertEqual(len(run(self.p)['planning']['work_with_stale_planning_assertion']), 2)

    def test_adapter_to_planning_progress_and_bundle_journey(self):
        protocol = json.loads(Path('examples/adapter-protocol.json').read_text())
        fixture = json.loads(Path('examples/adapter-fixture.json').read_text())
        reviews = json.loads(Path('examples/adapter-reviews.json').read_text())
        enriched = assemble(protocol, fixture, reviews)['protocol']
        for field in ('gaps', 'contexts', 'appraisals', 'planning_decisions'):
            enriched[field] = copy.deepcopy(self.p[field])
        self.refresh(enriched)
        self.assertEqual(run(enriched)['planning']['work_with_stale_planning_assertion'], [])
        enriched['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic://done',acceptance_verified=True)
        packet = review_packets(enriched, 'WP-TRANSLATION')['packets'][0]
        self.assertEqual(packet['planning_assertion']['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(packet['work_package']['blocked_by'], [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.zip'
            path.write_bytes(build_bundle(json.dumps(enriched).encode()))
            self.assertTrue(verify(path)['valid'])

    def test_bundle_csv_keeps_stale_rank_historical_and_escapes_rationale(self):
        self.p['planning_decisions'][0]['rationale'] = '=synthetic_formula'
        self.p['evidence'][0]['result'] = 'Changed supplied result'
        data = build_bundle(json.dumps(self.p).encode())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            rows = list(csv.DictReader(io.StringIO(archive.read('work-packages.csv').decode())))
            summary = archive.read('summary.md').decode()
        row = next(r for r in rows if r['work_package_id'] == 'WP-TRANSLATION')
        self.assertEqual(row['supplied_priority_rank'], '1')
        self.assertEqual(row['current_priority_rank'], '')
        self.assertEqual(row['planning_source_status'], 'STALE_SOURCE')
        self.assertEqual(row['planning_rationale'], "'=synthetic_formula")
        self.assertIn('Work with stale planning source bindings: 2', summary)

    def test_no_autofill_or_input_mutation_and_comparison_tracks_decisions(self):
        before = copy.deepcopy(self.p)
        result = run(self.p)
        self.assertEqual(self.p, before)
        self.assertEqual(result, run(self.p))
        self.p['planning_decisions'][0]['rationale'] += ' Synthetic revised planning note.'
        change = compare_protocols(before, self.p)['entity_changes']['planning_decisions']
        self.assertEqual(change['changed'][0]['fields'], ['rationale'])
        self.p['planning_decisions'][0]['rationale'] = 'Synthetic\nDecision: APPROVED\u202e'
        text = render_text(review_packets(self.p))
        self.assertNotIn('\nDecision: APPROVED', text)
        self.assertNotIn('\u202e', text)


if __name__ == '__main__':
    unittest.main()
