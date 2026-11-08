"""Independent fictional drift tests: comparison never renews scientific approval."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import result_intake as intake
import result_source_review as review_module
from tests.test_result_intake import base, candidates

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    p = base()
    p['gaps'] = []
    for key in ('report_reviews', 'report_study_inventory', 'report_study_inventory_reviews'):
        p.pop(key, None)
    return p


def assemble(p, c=None):
    c = candidates() if c is None else c
    review = intake.prepare(p, c)['review_document']
    review.update(receipt_id='fictional-drift-receipt', reviewer='Fictional reviewer',
                  reviewed_at='2026-11-04', rationale='Fictional software test only.',
                  decision='import_results')
    return intake.assemble(p, c, review)


class ResultSourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()
        self.record = assemble(self.p)
        self.current = copy.deepcopy(self.record['protocol_candidate'])

    def review(self, current=None):
        return review_module.review(self.p, self.record, self.current if current is None else current)

    def test_original_and_receipt_must_replay_before_current_validation(self):
        bad_original = copy.deepcopy(self.p); bad_original['question'] += ' changed'
        bad_record = copy.deepcopy(self.record); bad_record['receipt']['reviewer'] = 'forged'
        for p, record in ((bad_original, self.record), (self.p, bad_record)):
            with self.subTest(original=p is bad_original), self.assertRaises((ValueError, TypeError)):
                review_module.review(p, record, self.current)
        with patch.object(intake, 'verify', side_effect=ValueError('prior replay rejected')) as verify:
            with self.assertRaisesRegex(ValueError, 'prior replay rejected'):
                review_module.review(self.p, self.record, None)
            verify.assert_called_once()

    def test_engine_drift_rejects_prior_receipt(self):
        original = intake._implementation_hashes()
        changed = dict(original, **{'result_intake.py': '0' * 64})
        with patch.object(intake, '_implementation_hashes', return_value=changed):
            with self.assertRaises(ValueError): self.review()

    def test_invalid_current_unselected_data_is_not_ignored(self):
        changes = [('report_sources', 2, 'document_sha256', 'not-a-digest'),
                   ('reports', 4, 'retrieval', 'invented'),
                   ('evidence', 0, 'study_id', 'undeclared')]
        for collection, index, field, value in changes:
            current = copy.deepcopy(self.current); current[collection][index][field] = value
            with self.subTest(field=field), self.assertRaises((ValueError, TypeError, KeyError)):
                self.review(current)

    def test_current_must_be_json_safe(self):
        for value in (float('nan'), float('inf'), {'not-json'}, '\ud800'):
            current = copy.deepcopy(self.current); current['unrelated'] = value
            with self.subTest(value=repr(value)), self.assertRaises((ValueError, TypeError, UnicodeError)):
                self.review(current)

    def test_comparison_does_not_fetch_or_open_declared_locators(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
            out = self.review()
        self.assertEqual(out['external_calls'], 0)
        self.assertIs(out['protocol_changed'], False)
        self.assertNotIn('valid', out)

    def cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(ROOT / 'result_source_review.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, env=env)

    def test_cli_json_utf8_text_no_overwrite_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.current['unrelated'] = '가상 문서'
            paths = [root / name for name in ('original.json', 'record.json', 'current.json')]
            for path, value in zip(paths, (self.p, self.record, self.current)):
                path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            before = [p.read_bytes() for p in paths]
            env = dict(os.environ, PYTHONIOENCODING='ascii')
            result = self.cli(*paths, env=env)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(json.loads(result.stdout), self.review())
            text = self.cli(*paths, '--text', env=env)
            self.assertEqual(text.returncode, 0, text.stderr.decode())
            self.assertTrue(text.stdout.decode('utf-8').strip())
            output = root / 'review.json'
            result = self.cli(*paths, '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            written = output.read_bytes()
            self.assertEqual(json.loads(written), self.review())
            self.assertNotEqual(self.cli(*paths, '--output', output).returncode, 0)
            self.assertEqual(output.read_bytes(), written)
            for path in paths:
                self.assertNotEqual(self.cli(*paths, '--output', path).returncode, 0)
            self.assertEqual([p.read_bytes() for p in paths], before)
            paths[2].write_text('{"question":1,"question":2}', encoding='utf-8')
            rejected = root / 'must-not-exist.json'
            self.assertNotEqual(self.cli(*paths, '--output', rejected).returncode, 0)
            self.assertFalse(rejected.exists())

    def test_unchanged_result_mapping_catalog_and_selected_descriptor(self):
        out = self.review(); row = out['rows'][0]
        self.assertEqual([r['evidence_id'] for r in out['rows']], ['result-C'])
        self.assertEqual(row['result']['status'], 'UNCHANGED')
        self.assertEqual(row['result']['changed_fields'], [])
        self.assertEqual(row['report_mapping']['status'], 'UNCHANGED')
        self.assertEqual(row['source_context_status'], 'UNCHANGED')
        self.assertEqual(row['selected_sources'][0]['status'], 'UNCHANGED')
        self.assertTrue(out['original_replay_result']['valid'])
        self.assertEqual(out['lineage'], 'NOT_ESTABLISHED')
        self.assertEqual(out['renewed_human_review'], 'NOT_PERFORMED')
        self.assertIn('UNCHANGED does not establish', out['boundary'])
        self.assertEqual(self.review(), out)

    def test_raw_result_edits_and_missing_rows(self):
        for field, value in [('result', 'Fictional revised statement'),
                             ('unexpected_raw_detail', {'nested': [None, 1, 'fictional']})]:
            current = copy.deepcopy(self.current); current['evidence'][-1][field] = value
            row = self.review(current)['rows'][0]
            self.assertEqual(row['result']['status'], 'CHANGED')
            self.assertEqual(row['result']['changed_fields'], [field])
            self.assertEqual(row['result']['after'][field], value)
            self.assertEqual(row['source_context_status'], 'UNCHANGED')
        self.current['evidence'].pop()
        row = self.review()['rows'][0]
        self.assertEqual(row['result']['status'], 'MISSING')
        self.assertIsNone(row['result']['after'])
        self.assertEqual(row['report_mapping']['status'], 'UNCHANGED')

    def test_implicit_legacy_id_is_not_explicit_evidence_match(self):
        c = candidates(); c['candidates'][0]['evidence']['evidence_id'] = 'record-one'
        self.record = assemble(self.p, c)
        self.current = copy.deepcopy(self.record['protocol_candidate'])
        self.current['evidence'][-1].pop('evidence_id')
        row = self.review()['rows'][0]
        self.assertEqual(row['result']['status'], 'MISSING')
        self.assertIsNone(row['result']['current_input_pointer'])

    def test_matched_row_moved_study_or_record_is_explicit(self):
        current = copy.deepcopy(self.current); current['evidence'][-1]['study_id'] = 'study-B'
        row = self.review(current)['rows'][0]
        self.assertEqual(row['result']['status'], 'CHANGED')
        self.assertEqual(row['report_mapping']['current_matched_row_link']['study_id'], 'study-B')
        self.assertEqual(row['report_mapping']['current_matched_row_link_status'], 'CHANGED')
        current = copy.deepcopy(self.current)
        current['reports'][1].update(decision='include', study_id='study-C')
        current['evidence'][-1]['record_id'] = 'record-two'
        row = self.review(current)['rows'][0]
        self.assertEqual(row['result']['status'], 'CHANGED')
        self.assertEqual(row['report_mapping']['current_matched_row_link']['report_id'], 'report-two')
        self.assertEqual(row['report_mapping']['current_matched_row_link']['record_id'], 'record-two')

    def test_original_record_reassigned_to_other_report(self):
        self.current['reports'][0]['record_ids'] = ['record-two']
        self.current['reports'][1].update(record_ids=['record-one'], decision='include')
        self.current['reports'][1].pop('study_id')
        self.current['reports'][1]['study_ids'] = ['study-A', 'study-B', 'study-C']
        row = self.review()['rows'][0]
        self.assertEqual(row['result']['status'], 'UNCHANGED')
        self.assertEqual(row['report_mapping']['status'], 'CHANGED')
        self.assertEqual(row['report_mapping']['current_mapping_of_original_record']['report_id'], 'report-two')

    def test_membership_order_and_scalar_plural_do_not_change_source_hash(self):
        self.current['reports'][0]['study_ids'].reverse()
        out = self.review()
        self.assertEqual(out['rows'][0]['report_mapping']['status'], 'UNCHANGED')
        self.assertEqual(out['report_comparisons'][0]['recorded_report']['status'], 'CHANGED')
        self.assertEqual(out['rows'][0]['source_context_status'], 'UNCHANGED')
        self.p['evidence'] = []
        self.p['reports'][0].pop('study_ids')
        self.p['reports'][0]['study_id'] = 'study-C'
        self.record = assemble(self.p); self.current = copy.deepcopy(self.record['protocol_candidate'])
        self.current['reports'][0].pop('study_id'); self.current['reports'][0]['study_ids'] = ['study-C']
        out = self.review()
        self.assertEqual(out['report_comparisons'][0]['recorded_report']['status'], 'CHANGED')
        self.assertEqual(out['rows'][0]['source_context_status'], 'UNCHANGED')

    def test_valid_eligibility_and_retrieval_changes_are_separate_dimensions(self):
        current = copy.deepcopy(self.current); current['evidence'] = []
        current['reports'][0].pop('study_ids')
        current['reports'][0].update(decision='exclude', reason='Fictional changed eligibility')
        out = self.review(current)
        self.assertEqual(out['rows'][0]['result']['status'], 'MISSING')
        self.assertEqual(out['rows'][0]['report_mapping']['status'], 'CHANGED')
        self.assertEqual(out['rows'][0]['source_context_status'], 'UNCHANGED')
        current['reports'][0].update(decision='pending', retrieval='not_retrieved')
        out = self.review(current)
        self.assertEqual(out['rows'][0]['report_mapping']['status'], 'CHANGED')
        self.assertEqual(out['rows'][0]['source_context_status'], 'CHANGED')
        self.assertEqual(out['rows'][0]['selected_sources'][0]['status'], 'UNCHANGED')

    def test_selected_descriptor_changed_missing_moved_and_not_supplied(self):
        for expected, mutate in [
            ('CHANGED', lambda p: p['report_sources'][0].update(document_version='Fictional v2')),
            ('MISSING', lambda p: p['report_sources'].pop(0)),
            ('MOVED', lambda p: p['report_sources'][0].update(report_id='report-two')),
            ('NOT_SUPPLIED', lambda p: p.pop('report_sources'))]:
            current = copy.deepcopy(self.current); mutate(current)
            with self.subTest(expected=expected):
                row = self.review(current)['rows'][0]
                self.assertEqual(row['selected_sources'][0]['status'], expected)
                self.assertEqual(row['result']['status'], 'UNCHANGED')
                self.assertEqual(row['source_context_status'], 'CHANGED')

    def test_unselected_same_report_source_catalog_and_criteria_search_drift(self):
        for mutate in [lambda p: p['report_sources'][1].update(document_version='Fictional changed supplement'),
                       lambda p: p['inclusion_criteria'].append('Fictional extra criterion'),
                       lambda p: p['searches'][0].update(searched_at='Fictional revised supplied timestamp')]:
            current = copy.deepcopy(self.current); mutate(current)
            row = self.review(current)['rows'][0]
            self.assertEqual(row['result']['status'], 'UNCHANGED')
            self.assertEqual(row['source_context_status'], 'CHANGED')
            self.assertEqual(row['selected_sources'][0]['status'], 'UNCHANGED')

    def test_pointer_relocation_is_not_descriptor_movement(self):
        self.current['evidence'].reverse(); self.current['reports'].reverse()
        self.current['report_sources'] = self.current['report_sources'][2:] + self.current['report_sources'][:2]
        out = self.review(); row = out['rows'][0]
        self.assertEqual(row['result']['status'], 'UNCHANGED')
        self.assertEqual(row['result']['current_input_pointer'], '/evidence/0')
        self.assertEqual(row['selected_sources'][0]['status'], 'UNCHANGED')
        self.assertEqual(row['selected_sources'][0]['current_input_pointer'], '/report_sources/2')
        self.assertEqual(row['source_context_status'], 'UNCHANGED')
        self.current['report_sources'].reverse()
        row = self.review()['rows'][0]
        self.assertEqual(row['selected_sources'][0]['status'], 'UNCHANGED')
        self.assertEqual(row['source_context_status'], 'CHANGED')

    def test_unrelated_metadata_and_results_outside_batch_not_compared(self):
        self.current['version'] = 'fictional changed version'
        self.current['evidence'][0]['result'] = 'Fictional unrelated changed result'
        self.current['report_sources'][2]['document_version'] = 'Fictional unrelated descriptor'
        row = self.review()['rows'][0]
        self.assertEqual(row['result']['status'], 'UNCHANGED')
        self.assertEqual(row['source_context_status'], 'UNCHANGED')

    def test_absent_report_stage_and_empty_ledger_are_distinct(self):
        current = copy.deepcopy(self.current)
        current['evidence'] = []; current.pop('report_sources'); current.pop('reports')
        out = self.review(current)
        self.assertEqual(out['current_report_stage'], 'NOT_SUPPLIED')
        self.assertEqual(out['rows'][0]['report_mapping']['status'], 'NOT_SUPPLIED')
        self.assertEqual(out['rows'][0]['source_context_status'], 'NOT_SUPPLIED')
        current['reports'] = []; current['report_sources'] = []
        out = self.review(current)
        self.assertEqual(out['current_report_stage'], 'SUPPLIED')
        self.assertEqual(out['rows'][0]['report_mapping']['status'], 'MISSING')
        self.assertEqual(out['rows'][0]['source_context_status'], 'MISSING')
        self.assertEqual(out['rows'][0]['selected_sources'][0]['status'], 'MISSING')

    def test_multiple_imports_original_order_and_shared_report_comparison(self):
        c = candidates(); second = copy.deepcopy(c['candidates'][0])
        second['evidence']['evidence_id'] = 'result-D'; c['candidates'].append(second)
        self.record = assemble(self.p, c); self.current = copy.deepcopy(self.record['protocol_candidate'])
        self.current['evidence'].reverse()
        out = self.review()
        self.assertEqual([r['evidence_id'] for r in out['rows']], ['result-C', 'result-D'])
        self.assertEqual(len(out['report_comparisons']), 1)
        self.assertEqual(out['counts']['source_context']['UNCHANGED'], 1)
        self.assertEqual(out['counts']['result']['UNCHANGED'], 2)
        self.assertEqual(out['counts']['selected_sources']['UNCHANGED'], 2)

    def test_input_immutability_and_every_nested_output_is_detached(self):
        before = copy.deepcopy((self.p, self.record, self.current))
        result = self.review()
        def poison(value):
            if isinstance(value, dict):
                for child in list(value.values()): poison(child)
                value['__test_mutation__'] = True
            elif isinstance(value, list):
                for child in value: poison(child)
                value.append('__test_mutation__')
        poison(result)
        self.assertEqual((self.p, self.record, self.current), before)
        self.assertNotIn('__test_mutation__', json.dumps(self.review()))

    def test_api_input_and_output_size_limits_fail_closed(self):
        with patch.object(review_module, 'MAX_INPUT_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'byte limit'): self.review()
        with patch.object(review_module, 'MAX_OUTPUT_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'byte limit'): self.review()

    def test_raw_report_json_types_are_not_python_equality(self):
        self.p['reports'][0]['opaque_note'] = {'fictional': True}
        self.record = assemble(self.p)
        self.current = copy.deepcopy(self.record['protocol_candidate'])
        self.current['reports'][0]['opaque_note'] = {'fictional': 1}
        out = self.review()
        report = out['report_comparisons'][0]['recorded_report']
        self.assertEqual(report['status'], 'CHANGED')
        self.assertEqual(report['changed_fields'], ['opaque_note'])
        self.assertEqual(out['rows'][0]['source_context_status'], 'UNCHANGED')

    def test_real_csv_provenance_used_and_invalid_import_rejected(self):
        import bibliographic_intake
        import bibliographic_review
        p = json.loads((ROOT / 'examples/bibliographic-base.json').read_text(encoding='utf-8'))
        raw = b'record_id,source_locator\nfictional-input,synthetic:local-export\n'
        artifact = bibliographic_intake.prepare(p, raw, 'local-primary', '2026-11-04T00:00:00Z')
        choices = bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record', record_id='record-one',
                                         rationale='Fictional identity assertion')
        doc = bibliographic_review.prepare_review(p, artifact, choices)['review_document']
        doc['review'].update(reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                             rationale='Fictional collection', decision='import_for_screening')
        p = bibliographic_review.assemble(p, artifact, doc)['protocol_candidate']
        p['screening'] = [dict(record_id='record-one', decision='include', reason='Fictional screening')]
        p['reports'] = [dict(report_id='report-one', record_ids=['record-one'], retrieval='retrieved',
                             decision='include', study_id='study-C', locator='synthetic:report')]
        p['report_sources'] = [dict(source_id='source-main', report_id='report-one',
                                    source_locator='synthetic:source', document_version='Fictional v1',
                                    document_sha256=None)]
        self.p = p; self.record = assemble(p)
        self.current = copy.deepcopy(self.record['protocol_candidate'])
        from evidence_workflow import run
        from report_review_links import prepare_targets
        research = run(self.current)
        expected = prepare_targets(self.current, research['bibliographic_collection'])['report_targets'][0]
        out = self.review()
        source = out['report_comparisons'][0]['source_context']
        self.assertEqual(source['after_sha256'], expected['source_basis_sha256'])
        self.assertEqual(source['status'], 'UNCHANGED')
        self.current['bibliographic_imports']['imports'][0]['unexpected_tamper'] = True
        with self.assertRaises((ValueError, TypeError, KeyError)): self.review()

    def test_cli_rejects_oversized_or_invalid_utf8_before_output_creation(self):
        self.assertEqual(review_module.MAX_INPUT_BYTES, 50_000_000)
        self.assertEqual(review_module.MAX_OUTPUT_BYTES, 50_000_000)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = [root / name for name in ('original.json', 'record.json', 'current.json')]
            for path, value in zip(paths, (self.p, self.record, self.current)):
                path.write_text(json.dumps(value), encoding='utf-8')
            output = root / 'rejected.json'
            with paths[2].open('wb') as stream:
                stream.seek(review_module.MAX_INPUT_BYTES)
                stream.write(b' ')
            result = self.cli(*paths, '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'byte limit', result.stderr)
            self.assertFalse(output.exists())
            paths[2].write_bytes(b'\xff')
            self.assertNotEqual(self.cli(*paths, '--output', output).returncode, 0)
            self.assertFalse(output.exists())

    def test_text_rendering_escapes_supplied_control_characters(self):
        self.current['evidence'][-1]['result'] = 'Fictional\nVALID: true\u202e'
        text = review_module.render_text(self.review())
        self.assertNotIn('Fictional\nVALID: true', text)
        self.assertNotIn('\u202e', text)
        self.assertIn('VALID: true', text)


if __name__ == '__main__':
    unittest.main()
