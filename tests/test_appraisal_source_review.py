"""Synthetic literal-drift regressions; no real appraisal or source reading."""
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import appraisal_intake as intake
import appraisal_source_review as comparison
from evidence_workflow import run
from prisma_reports import report_flow

ROOT = Path(__file__).resolve().parents[1]


class AppraisalSourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.original = json.loads((ROOT / 'examples/synthesis-review.json').read_bytes())
        candidates = json.loads((ROOT / 'examples/manual-appraisal-candidates.json').read_bytes())
        review = intake.prepare(self.original, candidates)['review_document']
        review.update(receipt_id='fictional-review', reviewer='Fictional reviewer',
            reviewed_at='2026-11-04', rationale='Synthetic supplied assertions only.', decision='import_appraisals')
        self.application = intake.assemble(self.original, candidates, review)
        self.current = copy.deepcopy(self.application['protocol_candidate'])

    def result(self):
        return comparison.review(self.original, self.application, self.current)

    def link(self):
        return self.result()['rows'][0]['linked_results'][0]

    def test_unchanged_deterministic_without_mutation_or_network(self):
        snapshot = copy.deepcopy((self.original, self.application, self.current))
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            a = self.result(); b = self.result()
        self.assertEqual(a, b)
        self.assertEqual(snapshot, (self.original, self.application, self.current))
        self.assertEqual(a['counts']['appraisal']['UNCHANGED'], 2)
        self.assertEqual(a['counts']['normalized_result']['UNCHANGED'], 2)
        self.assertEqual(a['appraisal_validity'], 'NOT_ASSESSED')
        self.assertEqual(a['renewed_human_review'], 'NOT_PERFORMED')
        self.assertFalse(a['protocol_changed'])
        self.assertEqual(a['external_calls'], 0)

    def test_appraisal_wording_is_separate_from_result_context(self):
        self.current['appraisals'][1]['limitations'] += ' Revised synthetic limitation.'
        result = self.result()
        self.assertEqual(result['rows'][0]['appraisal']['changed_fields'], ['limitations'])
        self.assertEqual(result['counts']['normalized_result']['UNCHANGED'], 2)

    def test_missing_appraisal_does_not_discard_original_links(self):
        self.current['appraisals'].pop(1)
        row = self.result()['rows'][0]
        self.assertEqual(row['appraisal']['status'], 'MISSING')
        self.assertIsNone(row['current_input_pointer'])
        self.assertEqual(row['linked_results'][0]['normalized_result']['status'], 'UNCHANGED')

    def test_result_wording_drift_without_appraisal_rewrite(self):
        self.current['evidence'][0]['result'] = 'Different supplied fictional wording'
        result = self.result()
        self.assertEqual(result['rows'][0]['appraisal']['status'], 'UNCHANGED')
        self.assertEqual(self.link()['raw_result']['changed_fields'], ['result'])
        self.assertEqual(self.link()['normalized_result']['status'], 'CHANGED')

    def test_unrelated_result_not_expanded(self):
        self.current['evidence'][2]['result'] = 'Unrelated fictional change'
        self.assertEqual(self.result()['counts']['raw_result']['UNCHANGED'], 2)

    def test_raw_opaque_metadata_visible_separately(self):
        self.current['evidence'][0]['opaque'] = None
        self.assertEqual(self.link()['raw_result']['changed_fields'], ['opaque'])
        self.assertEqual(self.link()['normalized_result']['changed_fields'], ['opaque'])

    def test_reorder_tracks_identity_not_position(self):
        self.current['appraisals'].reverse()
        self.current['evidence'].reverse()
        result = self.result()
        self.assertEqual(result['counts']['appraisal']['UNCHANGED'], 2)
        self.assertEqual(result['counts']['raw_result']['UNCHANGED'], 2)
        self.assertEqual(result['rows'][0]['linked_results'][0]['current_input_pointer'], '/evidence/2')

    def test_search_context_change_is_visible(self):
        self.current['searches'][0]['query'] += ' changed'
        self.current['search_plan'][0]['query'] += ' changed'
        link = self.link()
        self.assertEqual(link['original_record_context']['status'], 'CHANGED')
        self.assertEqual(link['original_record_report_context']['status'], 'CHANGED')
        self.assertEqual(link['raw_result']['status'], 'UNCHANGED')

    def test_report_locator_change_is_visible(self):
        self.current['reports'][0]['locator'] = 'Different synthetic section'
        self.assertEqual(self.link()['original_record_report_context']['status'], 'CHANGED')
        self.assertEqual(self.link()['original_record_context']['status'], 'UNCHANGED')

    def test_report_omission_not_silently_unchanged(self):
        self.current.pop('reports')
        result = self.result()
        self.assertEqual(result['current_report_stage'], 'NOT_SUPPLIED')
        self.assertEqual(self.link()['original_record_report_context']['status'], 'MISSING')

    def test_no_report_context_on_either_side(self):
        self.original.pop('reports')
        candidates = self.application['receipt']['candidate_document']
        review = intake.prepare(self.original, candidates)['review_document']
        review.update(receipt_id='fictional-review', reviewer='Fictional reviewer',
            reviewed_at='2026-11-04', rationale='Synthetic only', decision='import_appraisals')
        self.application = intake.assemble(self.original, candidates, review)
        self.current = copy.deepcopy(self.application['protocol_candidate'])
        self.assertEqual(self.link()['original_record_report_context']['status'], 'NOT_PRESENT_EITHER')

    def test_missing_results_in_valid_later_snapshot_are_visible(self):
        for key in ('evidence', 'gaps', 'contexts', 'appraisals', 'synthesis_statements'):
            self.current[key] = []
        result = self.result()
        self.assertEqual(result['counts']['raw_result']['MISSING'], 2)
        self.assertEqual(result['counts']['appraisal']['MISSING'], 2)
        self.assertEqual(self.link()['original_record_context']['status'], 'UNCHANGED')
        self.assertEqual(self.link()['matched_result_record_context']['status'], 'MISSING')

    def test_added_appraisal_links_are_visible_but_not_expanded(self):
        self.current['appraisals'][1]['evidence_ids'].append('e2')
        row = self.result()['rows'][0]
        self.assertEqual(row['appraisal']['changed_fields'], ['evidence_ids'])
        self.assertEqual(len(row['linked_results']), 1)

    def test_report_reorder_does_not_change_context(self):
        self.current['reports'].reverse()
        self.assertEqual(self.link()['original_record_report_context']['status'], 'UNCHANGED')

    def test_input_and_output_bounds_fail_closed(self):
        with patch.object(comparison, 'MAX_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                self.result()
        real_normalize = intake._normalized
        def output_limit(value, limit, label):
            return real_normalize(value, 10 if label == 'comparison output' else limit, label)
        with patch.object(intake, '_normalized', side_effect=output_limit):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                self.result()

    def test_moved_result_does_not_hide_behind_original_record_context(self):
        self.current['evidence'][0]['record_id'] = 'r10'
        link = self.link()
        self.assertEqual(link['original_record_context']['status'], 'UNCHANGED')
        self.assertEqual(link['matched_result_record_context']['status'], 'CHANGED')
        self.assertEqual(link['normalized_result']['changed_fields'], ['record_id'])

    def test_legacy_identity_origin_change_visible_with_equal_normalized_result(self):
        self.original['evidence'] = [self.original['evidence'][0]]
        self.original['evidence'][0].pop('evidence_id')
        for key in ('gaps', 'contexts', 'appraisals', 'synthesis_statements'):
            self.original[key] = []
        candidates = copy.deepcopy(self.application['receipt']['candidate_document'])
        candidates['appraisals'] = [candidates['appraisals'][0]]
        candidates['appraisals'][0]['evidence_ids'] = ['r1']
        review = intake.prepare(self.original, candidates)['review_document']
        review.update(receipt_id='fictional-legacy', reviewer='Fictional reviewer',
            reviewed_at='2026-11-04', rationale='Synthetic only', decision='import_appraisals')
        self.application = intake.assemble(self.original, candidates, review)
        self.current = copy.deepcopy(self.application['protocol_candidate'])
        self.current['evidence'][0]['evidence_id'] = 'r1'
        link = self.link()
        self.assertEqual(link['historical_identity_origin'], 'LEGACY_RECORD_ID')
        self.assertEqual(link['current_identity_origin'], 'EXPLICIT_EVIDENCE_ID')
        self.assertEqual(link['raw_result']['changed_fields'], ['evidence_id'])
        self.assertEqual(link['normalized_result']['status'], 'UNCHANGED')

    def test_new_mapped_source_catalog_visible_without_reading(self):
        self.current['report_sources'] = [dict(source_id='fictional-source', report_id='report-1',
            source_locator='synthetic:inert-source', document_version='Fictional v1', document_sha256=None)]
        result = self.result()
        self.assertEqual(result['current_source_stage'], 'SUPPLIED')
        link = result['rows'][0]['linked_results'][0]
        self.assertEqual(link['original_record_report_context']['status'], 'CHANGED')
        self.assertEqual(link['raw_result']['status'], 'UNCHANGED')
        self.assertEqual(result['source_context_scope'], 'MAPPED_CATALOG_CONTEXT_NOT_SELECTED_OR_READ_DOCUMENTS')

    def test_replay_rejects_changed_original(self):
        self.original['question'] += ' changed'
        with self.assertRaises(ValueError): self.result()

    def test_replay_rejects_tampered_application(self):
        self.application['receipt']['target']['selected_evidence'][0]['raw_evidence']['result'] = 'tampered'
        with self.assertRaises(ValueError): self.result()

    def test_invalid_current_rejected(self):
        self.current['evidence'][0]['study_id'] = ''
        with self.assertRaises(ValueError): self.result()

    def test_duplicate_appraisal_ids_rejected(self):
        self.current['appraisals'].append(copy.deepcopy(self.current['appraisals'][1]))
        with self.assertRaises(ValueError): self.result()

    def test_counts_and_work_state_preserved(self):
        before = (run(self.current), report_flow(self.current))
        self.result()
        self.assertEqual(before, (run(self.current), report_flow(self.current)))

    def test_absent_null_and_boolean_not_equal_to_number(self):
        self.assertEqual(comparison.compare({}, {'x': None})['changed_fields'], ['x'])
        self.assertEqual(comparison.compare({'x': True}, {'x': 1})['status'], 'CHANGED')

    def test_cli_output_no_overwrite_and_strict_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in ('original.json', 'application.json', 'current.json')]
            for path, value in zip(paths, (self.original, self.application, self.current)):
                path.write_text(json.dumps(value), encoding='utf-8')
            output = root / 'comparison.json'
            def cli(*extra):
                return subprocess.run([sys.executable, str(ROOT / 'appraisal_source_review.py'),
                    *map(str, paths), *map(str, extra)], cwd=ROOT, capture_output=True, timeout=60,
                    env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))
            first = cli('--output', output, '--text')
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn(b'Detached appraisal source comparison', first.stdout)
            raw = output.read_bytes()
            self.assertEqual(json.loads(raw)['counts']['appraisal']['UNCHANGED'], 2)
            self.assertNotEqual(cli('--output', output).returncode, 0)
            self.assertEqual(output.read_bytes(), raw)
            paths[2].write_text('{"x": 1, "x": 2}', encoding='utf-8')
            self.assertNotEqual(cli().returncode, 0)


if __name__ == '__main__':
    unittest.main()
