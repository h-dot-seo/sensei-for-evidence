"""Portable completion-source labels remain distinct from acceptance checks."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from research_bundle import build_bundle, verify

ROOT = Path(__file__).resolve().parents[1]


class CompletionExportTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / 'examples/completion-binding.json').read_text())

    def entries(self):
        raw = json.dumps(self.protocol, ensure_ascii=False).encode('utf-8')
        with zipfile.ZipFile(io.BytesIO(build_bundle(raw))) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def rows(self, entries=None):
        entries = self.entries() if entries is None else entries
        return {row['work_package_id']: row for row in
                csv.DictReader(io.StringIO(entries['work-packages.csv'].decode('utf-8')))}

    def test_current_completion_retains_supplied_fields_and_nonverification(self):
        row = self.rows()['WP-MECHANISM']
        self.assertEqual(row['status'], 'COMPLETE')
        self.assertEqual(row['supplied_artifact_locator'], self.protocol['gaps'][0]['artifact_locator'])
        self.assertEqual(row['supplied_acceptance_verified'], 'True')
        self.assertEqual(row['completion_source_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['supplied_completion_basis_sha256'], row['current_completion_basis_sha256'])
        self.assertEqual(row['completion_acceptance_assessment'], 'NOT_PERFORMED')
        self.assertEqual(row['completion_artifact_content_verification'], 'NOT_PERFORMED')

    def test_stale_completion_does_not_renew_supplied_hash_or_reopen_work(self):
        old_hash = self.protocol['gaps'][0]['completion_basis_sha256']
        self.protocol['gaps'][0]['deliverable'] = 'Changed fictional requirement'
        entries = self.entries()
        row = self.rows(entries)['WP-MECHANISM']
        self.assertEqual(row['completion_source_status'], 'STALE_SOURCE')
        self.assertEqual(row['supplied_completion_basis_sha256'], old_hash)
        self.assertNotEqual(row['current_completion_basis_sha256'], old_hash)
        self.assertEqual(row['status'], 'COMPLETE')
        self.assertIn(b'Completed work with stale source binding: 1', entries['summary.md'])
        self.assertIn(b'not artifact-byte verification or acceptance', entries['summary.md'])

    def test_unbound_and_unfinished_rows_preserve_missing_assertions(self):
        self.protocol['gaps'][0].pop('completion_basis_sha256')
        entries = self.entries()
        rows = self.rows(entries)
        completed, unfinished = rows['WP-MECHANISM'], rows['WP-TRANSLATION']
        self.assertEqual(completed['completion_source_status'], 'UNBOUND_COMPLETION')
        self.assertEqual(completed['supplied_completion_basis_sha256'], '')
        self.assertEqual(unfinished['completion_source_status'], 'NOT_COMPLETE')
        self.assertEqual(unfinished['supplied_completion_basis_sha256'], '')
        self.assertEqual(unfinished['supplied_artifact_locator'], '')
        self.assertEqual(unfinished['supplied_acceptance_verified'], '')
        self.assertEqual(len(unfinished['current_completion_basis_sha256']), 64)
        self.assertIn(b'Completed work without source binding: 1', entries['summary.md'])

    def test_direct_prerequisite_rows_preserve_source_status_and_order(self):
        extra = copy.deepcopy(self.protocol['gaps'][0])
        extra.update(work_package_id='WP-SECOND', artifact_locator='synthetic://second')
        extra.pop('completion_basis_sha256')
        unrelated = copy.deepcopy(extra)
        unrelated['work_package_id'] = 'WP-UNRELATED'
        self.protocol['gaps'].extend([extra, unrelated])
        self.protocol['gaps'][1]['depends_on'] = ['WP-SECOND', 'WP-MECHANISM']
        rows = self.rows()
        direct = json.loads(rows['WP-TRANSLATION']['direct_prerequisite_completion_sources'])
        self.assertEqual(direct, [
            dict(work_package_id='WP-SECOND', supplied_work_status='COMPLETE', source_match_status='UNBOUND_COMPLETION'),
            dict(work_package_id='WP-MECHANISM', supplied_work_status='COMPLETE', source_match_status='CURRENT_SOURCE')])
        self.assertEqual(rows['WP-MECHANISM']['direct_prerequisite_completion_sources'], '[]')
        self.assertEqual(rows['WP-TRANSLATION']['blocked_by'], '[]')

    def test_formula_like_artifact_locator_is_escaped_only_in_csv(self):
        for locator in ('=1+1', '\n=1+1', ' \t=1+1', '@synthetic'):
            with self.subTest(locator=locator):
                self.protocol['gaps'][0]['artifact_locator'] = locator
                entries = self.entries()
                self.assertEqual(self.rows(entries)['WP-MECHANISM']['supplied_artifact_locator'], "'" + locator)
                self.assertEqual(json.loads(entries['protocol.json'])['gaps'][0]['artifact_locator'], locator)
                self.assertEqual(json.loads(entries['research.json'])['work_packages'][0]['artifact_locator'], locator)

    def test_bundle_reproduction_verification_and_no_input_mutation(self):
        before = copy.deepcopy(self.protocol)
        first = self.entries()
        self.assertEqual(first, self.entries())
        self.assertEqual(self.protocol, before)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bundle.zip'
            path.write_bytes(build_bundle(json.dumps(self.protocol).encode('utf-8')))
            result = verify(path)
            self.assertTrue(result['valid'])
            self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_rehashed_fabricated_csv_completion_is_rejected(self):
        entries = self.entries()
        entries['work-packages.csv'] = entries['work-packages.csv'].replace(b'CURRENT_SOURCE', b'FABRICATED_ACCEPTANCE')
        manifest = json.loads(entries['manifest.json'])
        for row in manifest['files']:
            if row['path'] == 'work-packages.csv':
                raw = entries[row['path']]
                row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        entries['manifest.json'] = json.dumps(manifest).encode('utf-8')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tampered.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                for name, raw in entries.items():
                    archive.writestr(name, raw)
            with self.assertRaisesRegex(ValueError, 'derived artifacts'):
                verify(path)

    def test_source_review_completion_and_empty_work_are_not_readiness(self):
        self.protocol = json.loads((ROOT / 'examples/source-work-protocol.json').read_text())
        self.protocol['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://receipt', acceptance_verified=True)
        row = self.rows()['WP-RECEIPT-REVIEW']
        self.assertEqual(row['work_type'], 'source_review')
        self.assertEqual(row['completion_source_status'], 'UNBOUND_COMPLETION')
        self.protocol['gaps'] = []
        entries = self.entries()
        self.assertEqual(self.rows(entries), {})
        self.assertIn(b'Completed work without source binding: 0', entries['summary.md'])
        self.assertIn(b'Conclusion: NOT_READY', entries['summary.md'])

    def test_existing_csv_column_prefix_is_preserved(self):
        expected = ['work_package_id', 'status', 'question', 'deliverable', 'acceptance_criterion',
                    'evidence_ids', 'depends_on', 'blocked_by', 'context_ids', 'context_review_pending',
                    'appraisal_ids', 'evidence_without_recorded_appraisal', 'supplied_priority_rank',
                    'current_priority_rank', 'planning_source_status', 'planning_rationale',
                    'planning_uncertainty', 'planner', 'planned_at', 'planning_basis_sha256',
                    'current_planning_basis_sha256', 'experimental_unit_ids', 'evidence_without_experimental_unit',
                    'experimental_stage', 'units_without_outcome_sampling', 'units_with_unresolved_sampling',
                    'units_without_outcome_statistics', 'units_with_statistics_review_cues',
                    'linked_synthesis_statement_ids', 'work_type', 'source_refs']
        reader = csv.DictReader(io.StringIO(self.entries()['work-packages.csv'].decode('utf-8')))
        self.assertEqual(reader.fieldnames[:len(expected)], expected)
        self.assertEqual(len(reader.fieldnames), len(set(reader.fieldnames)))

    def test_stale_and_unfinished_prerequisites_keep_distinct_labels(self):
        self.protocol['gaps'][0]['artifact_locator'] = 'synthetic://changed-note'
        row = self.rows()['WP-TRANSLATION']
        self.assertEqual(json.loads(row['direct_prerequisite_completion_sources'])[0]['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(row['blocked_by'], '[]')
        self.protocol['gaps'][0].pop('completion_basis_sha256')
        self.protocol['gaps'][0]['status'] = 'IN_PROGRESS'
        row = self.rows()['WP-TRANSLATION']
        direct = json.loads(row['direct_prerequisite_completion_sources'])[0]
        self.assertEqual(direct['source_match_status'], 'NOT_COMPLETE')
        self.assertEqual(direct['supplied_work_status'], 'IN_PROGRESS')
        self.assertEqual(json.loads(row['blocked_by']), ['WP-MECHANISM'])

    def test_three_level_chain_exports_only_each_works_direct_links(self):
        root = copy.deepcopy(self.protocol['gaps'][0])
        root.update(work_package_id='WP-EARLIER', artifact_locator='synthetic://earlier')
        root.pop('completion_basis_sha256')
        self.protocol['gaps'].append(root)
        self.protocol['gaps'][0]['depends_on'] = ['WP-EARLIER']
        rows = self.rows()
        selected = json.loads(rows['WP-TRANSLATION']['direct_prerequisite_completion_sources'])
        middle = json.loads(rows['WP-MECHANISM']['direct_prerequisite_completion_sources'])
        self.assertEqual([row['work_package_id'] for row in selected], ['WP-MECHANISM'])
        self.assertEqual([row['work_package_id'] for row in middle], ['WP-EARLIER'])
        self.assertEqual(rows['WP-EARLIER']['direct_prerequisite_completion_sources'], '[]')

    def test_explicit_false_supplied_acceptance_is_not_missing(self):
        self.protocol['gaps'][0].pop('completion_basis_sha256')
        self.protocol['gaps'][0].update(status='IN_PROGRESS', acceptance_verified=False)
        rows = self.rows()
        self.assertEqual(rows['WP-MECHANISM']['supplied_acceptance_verified'], 'False')
        self.assertEqual(rows['WP-TRANSLATION']['supplied_acceptance_verified'], '')
        self.assertEqual(rows['WP-MECHANISM']['completion_acceptance_assessment'], 'NOT_PERFORMED')


if __name__ == '__main__':
    unittest.main()
