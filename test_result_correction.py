"""Fictional text corrections preserve result identities and never approve science."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import result_correction as correction
import result_intake
import result_source_review
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
import research_bundle

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def proposal(evidence_id='result-C-manual'):
    return dict(schema_version=1, corrections=[dict(
        evidence_id=evidence_id, report_id='report-one',
        changes={'result': 'Corrected fictional null-finding text, not a real observation.'},
        source_references=[dict(source_id='source-supplement', extraction_locator='Fictional section C')],
        corrected_by='Fictional extractor', corrected_at='2026-11-04',
        correction_note='Fictional transcription correction; no source reading claimed.')])


class ResultCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('result-source-current.json')
        self.c = proposal()

    def human_review(self, p=None, c=None):
        doc = correction.prepare(self.p if p is None else p, self.c if c is None else c)['review_document']
        doc.update(receipt_id='fictional-correction', decision='correct_result_text',
                   reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                   rationale='Explicit fictional transcription change, not scientific acceptance.')
        return doc

    def assemble(self, p=None, c=None):
        p = self.p if p is None else p
        c = self.c if c is None else c
        return correction.assemble(p, c, self.human_review(p, c))

    def test_deterministic_blank_review_is_not_approval(self):
        before = copy.deepcopy((self.p, self.c))
        prepared = correction.prepare(self.p, self.c)
        self.assertEqual(prepared, correction.prepare(self.p, self.c))
        doc = prepared['review_document']
        self.assertEqual(set(doc), {'schema_version', 'receipt_id', 'target_sha256', 'decision', 'reviewer', 'reviewed_at', 'rationale'})
        self.assertEqual(doc['schema_version'], 1)
        self.assertEqual(len(doc['target_sha256']), 64)
        self.assertTrue(all(v is None for k, v in doc.items() if k not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError): correction.assemble(self.p, self.c, doc)
        self.assertEqual((self.p, self.c), before)

    def test_exact_in_place_delta_preserves_counts_order_opaque_fields(self):
        self.p['evidence'][2]['opaque_metadata'] = {'literal': [True, 1, 1.0, None]}
        self.p['opaque_metadata'] = {'also': 'retained'}
        before = canonical_json_bytes(self.p)
        record = self.assemble()
        expected = copy.deepcopy(self.p)
        expected['evidence'][2]['result'] = self.c['corrections'][0]['changes']['result']
        self.assertEqual(canonical_json_bytes(record['protocol_candidate']), canonical_json_bytes(expected))
        self.assertEqual(canonical_json_bytes(self.p), before)
        self.assertEqual(len(record['protocol_candidate']['evidence']), 4)
        self.assertEqual(record['receipt']['before_flow'], record['receipt']['after_flow'])
        self.assertEqual(record['receipt']['before_report_flow'], record['receipt']['after_report_flow'])
        self.assertTrue(correction.verify(self.p, record)['valid'])
        row = record['receipt']['target']['result_changes'][0]
        self.assertEqual(row['input_pointer'], '/evidence/2')
        self.assertEqual(row['before'], self.p['evidence'][2])
        self.assertEqual(row['after'], expected['evidence'][2])
        self.assertEqual(row['changed_fields'], ['result'])
        self.assertEqual(record['receipt']['source_association_scope'], 'DETACHED_RECORD_ONLY')

    def test_batch_order_does_not_reorder_evidence_and_both_fields_allowed(self):
        second = copy.deepcopy(self.c['corrections'][0])
        second.update(evidence_id='result-A')
        second['changes'] = dict(result='Another fictional corrected text.', limitations='Corrected fictional uncertainty.')
        self.c['corrections'].append(second)
        record = self.assemble()
        self.assertEqual([r['evidence_id'] for r in record['protocol_candidate']['evidence']],
                         [r['evidence_id'] for r in self.p['evidence']])
        changes = record['receipt']['target']['result_changes']
        self.assertEqual([r['input_pointer'] for r in changes], ['/evidence/2', '/evidence/0'])
        self.assertEqual(changes[1]['changed_fields'], ['limitations', 'result'])
        self.assertEqual(len(record['receipt']['target']['selected_report_targets']), 1)
        self.assertEqual([r['correction_index'] for r in record['receipt']['target']['selected_sources']], [0, 1])

    def test_strict_document_row_and_reference_shapes(self):
        for bad in (None, [], True, dict(self.c, schema_version=True), dict(self.c, schema_version=1.0),
                    dict(self.c, schema_version=2), dict(self.c, extra=True),
                    dict(self.c, corrections=[]), dict(self.c, corrections={}),
                    dict(self.c, corrections=self.c['corrections'] * 101)):
            with self.subTest(bad=repr(bad)[:80]), self.assertRaises((ValueError, TypeError)):
                correction.prepare(self.p, bad)
        for field in self.c['corrections'][0]:
            doc = copy.deepcopy(self.c); del doc['corrections'][0][field]
            with self.subTest(missing=field), self.assertRaises(ValueError): correction.prepare(self.p, doc)
        for location in ('row', 'reference'):
            doc = copy.deepcopy(self.c)
            row = doc['corrections'][0]
            (row if location == 'row' else row['source_references'][0])['extra'] = True
            with self.assertRaises(ValueError): correction.prepare(self.p, doc)

    def test_changes_reject_identity_other_fields_noops_and_blank_values(self):
        for field in ('evidence_id', 'record_id', 'study_id', 'report_id', 'locator', 'model', 'endpoint',
                      'intervention', 'comparator', 'mechanism_basis', 'source_references', 'unknown'):
            doc = copy.deepcopy(self.c); doc['corrections'][0]['changes'][field] = 'forbidden'
            with self.subTest(field=field), self.assertRaises(ValueError): correction.prepare(self.p, doc)
        for changes in ({}, None, [], {'result': self.p['evidence'][2]['result']},
                        {'result': 'Changed', 'limitations': self.p['evidence'][2]['limitations']}):
            doc = copy.deepcopy(self.c); doc['corrections'][0]['changes'] = changes
            with self.subTest(changes=changes), self.assertRaises((ValueError, TypeError)): correction.prepare(self.p, doc)
        for field in ('result', 'limitations'):
            for bad in (None, True, 3, [], {}, '', ' \n\t'):
                doc = copy.deepcopy(self.c); doc['corrections'][0]['changes'] = {field: bad}
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError): correction.prepare(self.p, doc)

    def test_literal_strings_and_actual_dates(self):
        for field in ('evidence_id', 'report_id', 'corrected_by', 'corrected_at', 'correction_note'):
            for bad in (None, True, 3, [], {}, '', '  '):
                doc = copy.deepcopy(self.c); doc['corrections'][0][field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(ValueError): correction.prepare(self.p, doc)
        for bad in ('2026-02-29', '2026-2-04', '2026-11-04\n', '0000-01-01'):
            doc = copy.deepcopy(self.c); doc['corrections'][0]['corrected_at'] = bad
            with self.assertRaises(ValueError): correction.prepare(self.p, doc)
        row = self.c['corrections'][0]
        row.update(corrected_at='2024-02-29', correction_note='  Literal fictional note.  ')
        row['changes']['result'] = '  합성 observation\nwith literal whitespace.  '
        record = self.assemble()
        self.assertEqual(record['protocol_candidate']['evidence'][2]['result'], row['changes']['result'])
        self.assertEqual(record['receipt']['correction_document'], self.c)

    def test_exact_explicit_ids_only_no_implicit_fallback_or_duplicates(self):
        for eid in ('result-C-manual ', 'RESULT-C-MANUAL', 'missing'):
            with self.subTest(eid=eid), self.assertRaises(ValueError): correction.prepare(self.p, proposal(eid))
        doc = copy.deepcopy(self.c); doc['corrections'].append(copy.deepcopy(doc['corrections'][0]))
        with self.assertRaises(ValueError): correction.prepare(self.p, doc)
        self.p['evidence'][2].pop('evidence_id')
        run(self.p); report_flow(self.p, include_csv=False)
        with self.assertRaises(ValueError): correction.prepare(self.p, proposal('record-one'))

    def test_current_exact_report_membership_and_selected_sources_required(self):
        for report in ('missing', 'report-two', 'report-one '):
            doc = copy.deepcopy(self.c); doc['corrections'][0]['report_id'] = report
            with self.assertRaises(ValueError): correction.prepare(self.p, doc)
        for refs in ([], None, [{'source_id': 'missing', 'extraction_locator': 'fictional'}],
                     [{'source_id': 'source-unbound', 'extraction_locator': 'fictional'}],
                     self.c['corrections'][0]['source_references'] * 2):
            doc = copy.deepcopy(self.c); doc['corrections'][0]['source_references'] = refs
            with self.assertRaises(ValueError): correction.prepare(self.p, doc)
        for field in ('source_id', 'extraction_locator'):
            for bad in (None, True, [], '', ' '):
                doc = copy.deepcopy(self.c); doc['corrections'][0]['source_references'][0][field] = bad
                with self.assertRaises(ValueError): correction.prepare(self.p, doc)
        self.p['report_sources'][1]['document_sha256'] = None
        record = self.assemble()
        self.assertIsNone(record['receipt']['target']['selected_sources'][0]['source']['document_sha256'])
        self.assertEqual(record['receipt']['document_bytes_verification'], 'NOT_PERFORMED')

    def test_whole_original_validation_not_only_selected_row(self):
        for change in (lambda p: p['evidence'][0].update(result=''),
                       lambda p: p['evidence'][0].update(evidence_id='result-C-manual'),
                       lambda p: p['reports'][0]['study_ids'].remove('study-C')):
            p = copy.deepcopy(self.p); change(p)
            with self.assertRaises(ValueError): correction.prepare(p, self.c)
        for value in (None, {}, []):
            p = copy.deepcopy(self.p); p['adapter_receipts'] = value
            with self.assertRaisesRegex(ValueError, 'adapter'): correction.prepare(p, self.c)
        p = copy.deepcopy(self.p); p.pop('reports')
        with self.assertRaises(ValueError): correction.prepare(p, self.c)

    def test_legacy_scalar_report_guard_and_before_after_validation(self):
        p = fixture('multi-result-protocol.json')
        p['report_sources'] = [dict(source_id='source-supplement', report_id=p['reports'][0]['report_id'],
            source_locator='synthetic:source', document_version='Fictional version', document_sha256=None)]
        doc = proposal(p['evidence'][0]['evidence_id']); doc['corrections'][0]['report_id'] = p['reports'][0]['report_id']
        correction.prepare(p, doc)
        p['reports'][0].update(decision='exclude', reason='Fictional exclusion')
        p.pop('report_sources')
        run(p)  # The historical scalar-only core path does not provide this guard.
        with self.assertRaises(ValueError): correction.prepare(p, doc)
        with patch.object(correction, 'run', wraps=run) as runs, patch.object(correction, 'report_flow', wraps=report_flow) as reports:
            correction.prepare(self.p, self.c)
        self.assertEqual(runs.call_count, 2)
        self.assertEqual(reports.call_count, 2)
        self.assertTrue(all(call.kwargs.get('include_csv') is False for call in reports.call_args_list))

    def test_exact_review_schema_identity_date_and_decision(self):
        doc = self.human_review()
        for field in doc:
            for bad in (None, True, 2, [], {}, '', ' '):
                changed = copy.deepcopy(doc); changed[field] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises((ValueError, TypeError)):
                    correction.assemble(self.p, self.c, changed)
            changed = copy.deepcopy(doc); del changed[field]
            with self.assertRaises(ValueError): correction.assemble(self.p, self.c, changed)
        for field, value in [('decision', 'import_results'), ('decision', 'correct_result_text '),
                             ('schema_version', 1.0), ('reviewed_at', '2026-02-29'),
                             ('target_sha256', 'A' * 64), ('target_sha256', '0' * 63)]:
            changed = copy.deepcopy(doc); changed[field] = value
            with self.assertRaises(ValueError): correction.assemble(self.p, self.c, changed)
        with self.assertRaises(ValueError): correction.assemble(self.p, self.c, dict(doc, extra=True))

    def test_input_proposal_source_and_implementation_drift_reject_old_review(self):
        review = self.human_review()
        for mutate in (lambda p: p.update(version='fictional-new-version'),
                       lambda p: p['evidence'].reverse(),
                       lambda p: p['report_sources'][0].update(document_version='unselected changed version'),
                       lambda p: p.update(opaque={'literal': True})):
            p = copy.deepcopy(self.p); mutate(p)
            with self.assertRaises(ValueError): correction.assemble(p, self.c, review)
        for mutate in (lambda c: c['corrections'][0].update(correction_note='different supplied reason'),
                       lambda c: c['corrections'][0]['changes'].update(result='another supplied text'),
                       lambda c: c['corrections'][0]['source_references'][0].update(extraction_locator='other section')):
            doc = copy.deepcopy(self.c); mutate(doc)
            with self.assertRaises(ValueError): correction.assemble(self.p, doc, review)
        with patch.object(correction, '_implementation_hashes', return_value={'result_correction.py': '0' * 64}):
            with self.assertRaises(ValueError): correction.assemble(self.p, self.c, review)

    def test_entire_replay_rejects_tampering_even_resealed(self):
        record = self.assemble()
        self.assertEqual(set(record), {'schema_version', 'kind', 'receipt', 'protocol_candidate'})
        self.assertEqual(record['kind'], 'detached_result_correction')
        self.assertIn('result_correction.py', record['receipt']['engine_sha256'])
        mutations = [lambda r: r.update(extra=True), lambda r: r.update(schema_version=True),
                     lambda r: r.update(kind='detached_result_intake'),
                     lambda r: r['protocol_candidate']['evidence'][2].update(result='tampered'),
                     lambda r: r['receipt']['target']['result_changes'][0]['before'].update(result='tampered'),
                     lambda r: r['receipt']['target']['result_changes'][0]['after'].update(result='tampered'),
                     lambda r: r['receipt']['target']['selected_sources'][0].update(extraction_locator='tampered'),
                     lambda r: r['receipt'].update(before_flow={}, source_authenticity='VERIFIED'),
                     lambda r: r['receipt'].update(external_calls=True)]
        for mutate in mutations:
            bad = copy.deepcopy(record); mutate(bad)
            bad['receipt']['receipt_sha256'] = correction.digest({k: v for k, v in bad['receipt'].items() if k != 'receipt_sha256'})
            with self.assertRaises(ValueError): correction.verify(self.p, bad)
        p = copy.deepcopy(self.p); p['question'] += ' changed'
        with self.assertRaises(ValueError): correction.verify(p, record)
        with patch.object(correction, '_implementation_hashes', return_value={'result_correction.py': '0' * 64}):
            with self.assertRaises(ValueError): correction.verify(self.p, record)

    def test_consistently_reauthored_assertion_is_not_authenticated_history(self):
        review = self.human_review(); review.update(reviewer='Other fictional reviewer', receipt_id='other-fictional-id')
        alternate = correction.assemble(self.p, self.c, review)
        self.assertTrue(correction.verify(self.p, alternate)['valid'])
        self.assertIn('unsigned', alternate['receipt']['boundary'])
        self.assertEqual(alternate['receipt']['reading'], 'NOT_ESTABLISHED')
        self.assertEqual(alternate['receipt']['source_result_correctness'], 'NOT_ASSESSED')

    def test_old_intake_replay_and_separate_source_comparison_remain_honest(self):
        original = fixture('report-study-inventory-reviews.json')
        candidates = fixture('manual-result-candidates.json')
        review = result_intake.prepare(original, candidates)['review_document']
        review.update(receipt_id='fictional-intake', decision='import_results', reviewer='Fictional reviewer',
                      reviewed_at='2026-11-04', rationale='Fictional supplied intake.')
        imported = result_intake.assemble(original, candidates, review)
        before = canonical_json_bytes(imported)
        corrected = self.assemble(imported['protocol_candidate'])
        self.assertTrue(result_intake.verify(original, imported)['valid'])
        compared = result_source_review.review(original, imported, corrected['protocol_candidate'])
        self.assertEqual([r['result']['status'] for r in compared['rows']], ['CHANGED', 'UNCHANGED'])
        self.assertEqual(compared['rows'][0]['source_context_status'], 'UNCHANGED')
        self.assertEqual(canonical_json_bytes(imported), before)

    def test_existing_assertions_not_renewed_and_existing_completion_logic_stales(self):
        p = fixture('completion-binding.json')
        report = p['reports'][0]
        p['report_sources'] = [dict(source_id='source-supplement', report_id=report['report_id'],
            source_locator='synthetic:source', document_version='Fictional version', document_sha256=None)]
        doc = proposal(p['evidence'][0]['evidence_id']); doc['corrections'][0]['report_id'] = report['report_id']
        before = run(p)
        candidate = self.assemble(p, doc)['protocol_candidate']
        after = run(candidate)
        for field in ('gaps', 'appraisals', 'experimental_units', 'planning_assertions', 'synthesis'):
            if field in p: self.assertEqual(canonical_json_bytes(p[field]), canonical_json_bytes(candidate[field]))
        old = next(r for r in before['planning']['completion_ledger'] if r['work_package_id'] == 'WP-MECHANISM')
        new = next(r for r in after['planning']['completion_ledger'] if r['work_package_id'] == 'WP-MECHANISM')
        self.assertEqual(old['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(new['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(candidate['gaps'][0]['status'], 'COMPLETE')
        self.assertEqual(before['appraisal'], after['appraisal'])

    def test_csv_history_preserved_and_corrected_candidate_bundles(self):
        import bibliographic_intake
        import bibliographic_review
        p = fixture('bibliographic-base.json')
        artifact = bibliographic_intake.prepare(p, b'record_id,source_locator\nfictional-input,synthetic:csv\n', 'local-primary', '2026-11-04T00:00:00Z')
        choices = bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record', record_id='record-one', rationale='Fictional identity assertion')
        review = bibliographic_review.prepare_review(p, artifact, choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer', reviewed_at='2026-11-04', rationale='Fictional collection', decision='import_for_screening')
        p = bibliographic_review.assemble(p, artifact, review)['protocol_candidate']
        p['screening'] = [dict(record_id='record-one', decision='include', reason='Fictional screening')]
        p['reports'] = [dict(report_id='report-one', record_ids=['record-one'], retrieval='retrieved', decision='include', study_id='study-C', locator='synthetic:report')]
        p['report_sources'] = [dict(source_id='source-supplement', report_id='report-one', source_locator='synthetic:source', document_version='Fictional v1', document_sha256=None)]
        p['evidence'] = [copy.deepcopy(self.p['evidence'][2])]
        before = canonical_json_bytes(p['bibliographic_imports'])
        record = self.assemble(p)
        self.assertEqual(canonical_json_bytes(record['protocol_candidate']['bibliographic_imports']), before)
        self.assertTrue(correction.verify(p, record)['valid'])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bundle.zip'
            path.write_bytes(research_bundle.build_bundle(canonical_json_bytes(record['protocol_candidate'])))
            self.assertTrue(research_bundle.verify(path)['valid'])
        p['question'] += ' unauthorized base drift'
        with self.assertRaises(ValueError): correction.prepare(p, self.c)

    def test_detached_outputs_and_no_network_or_source_opening(self):
        self.p['report_sources'][1]['source_locator'] = 'https://invalid.example/do-not-fetch'
        originals = copy.deepcopy((self.p, self.c))
        with patch('urllib.request.urlopen', side_effect=AssertionError('no network')), patch('socket.socket', side_effect=AssertionError('no network')), patch('subprocess.run', side_effect=AssertionError('no subprocess')):
            record = self.assemble()
            self.assertTrue(correction.verify(self.p, record)['valid'])
        record['protocol_candidate']['evidence'][2]['result'] = 'output-only edit'
        record['receipt']['correction_document']['corrections'][0]['correction_note'] = 'output-only note'
        self.assertEqual((self.p, self.c), originals)

    def test_size_limits_and_nonfinite_json(self):
        self.assertEqual(correction.MAX_CORRECTION_BYTES, 10_000_000)
        self.assertEqual(correction.MAX_PROTOCOL_BYTES, 50_000_000)
        self.assertEqual(correction.MAX_APPLICATION_BYTES, 50_000_000)
        record = self.assemble()
        for constant, action in [('MAX_CORRECTION_BYTES', lambda: correction.prepare(self.p, self.c)),
                                 ('MAX_PROTOCOL_BYTES', lambda: correction.prepare(self.p, self.c)),
                                 ('MAX_APPLICATION_BYTES', lambda: correction.verify(self.p, record))]:
            with patch.object(correction, constant, 10), self.assertRaises(ValueError): action()
        for bad in (float('nan'), float('inf'), '\ud800'):
            p = copy.deepcopy(self.p); p['opaque'] = bad
            with self.assertRaises((ValueError, UnicodeError)): correction.prepare(p, self.c)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'result_correction.py'), *map(str, args)],
            cwd=ROOT, capture_output=True, env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_cli_roundtrip_utf8_quoted_controls_and_exclusive_output(self):
        self.c['corrections'][0]['changes']['result'] = '합성 fictional text\n\x1b[31mnot a control'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); p = root/'original.json'; c = root/'corrections.json'; r = root/'review.json'
            target = root/'target.json'; app = root/'application.json'; output = root/'candidate.json'
            p.write_bytes(canonical_json_bytes(self.p)); c.write_bytes(canonical_json_bytes(self.c))
            result = self.cli('target', p, c, '--output', target)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            self.assertEqual(json.loads(target.read_text(encoding='utf-8')), correction.prepare(self.p, self.c))
            r.write_bytes(canonical_json_bytes(self.human_review()))
            result = self.cli('assemble', p, c, r, '--output', app, '--text')
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            self.assertNotIn(b'\x1b', result.stdout)
            saved = app.read_bytes()
            self.assertNotEqual(self.cli('assemble', p, c, r, '--output', app).returncode, 0)
            self.assertEqual(app.read_bytes(), saved)
            result = self.cli('verify', p, app, '--protocol-output', output)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')), json.loads(saved)['protocol_candidate'])
            self.assertNotEqual(self.cli('verify', p, app, '--protocol-output', p).returncode, 0)
            self.assertEqual(p.read_bytes(), canonical_json_bytes(self.p))
            self.assertEqual(c.read_bytes(), canonical_json_bytes(self.c))

    def test_cli_invalid_inputs_never_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); p = root/'p.json'; c = root/'c.json'; out = root/'out.json'
            p.write_bytes(canonical_json_bytes(self.p))
            for raw in (b'{"schema_version":1,"schema_version":1,"corrections":[]}', b'\xff',
                        b'{"schema_version":1,"corrections":NaN}', br'{"bad":"\ud800"}'):
                c.write_bytes(raw)
                self.assertNotEqual(self.cli('target', p, c, '--output', out).returncode, 0)
                self.assertFalse(out.exists())
            c.write_bytes(b' ' * (correction.MAX_CORRECTION_BYTES + 1))
            self.assertNotEqual(self.cli('target', p, c, '--output', out).returncode, 0)
            self.assertFalse(out.exists())

    def test_public_fixture_is_a_real_candidate_without_count_inflation(self):
        doc = fixture('manual-result-corrections.json')
        record = self.assemble(c=doc)
        self.assertEqual(len(record['protocol_candidate']['evidence']), len(self.p['evidence']))
        self.assertTrue(correction.verify(self.p, record)['valid'])
        self.assertEqual(record['receipt']['before_report_flow'], record['receipt']['after_report_flow'])

    def test_hundred_distinct_corrections_allowed_without_recounting_findings(self):
        self.p['evidence'] = []
        self.p['gaps'] = []
        self.c['corrections'] = []
        template = fixture('result-source-current.json')['evidence'][2]
        for index in range(100):
            row = copy.deepcopy(template); row['evidence_id'] = 'fictional-result-' + str(index)
            self.p['evidence'].append(row)
            self.c['corrections'].extend(proposal(row['evidence_id'])['corrections'])
        record = self.assemble()
        self.assertEqual(len(record['protocol_candidate']['evidence']), 100)
        self.assertEqual(record['receipt']['before_flow'], record['receipt']['after_flow'])
        self.assertTrue(correction.verify(self.p, record)['valid'])

    def test_canonical_key_order_ignored_but_literal_opaque_types_bound(self):
        self.p['opaque'] = {'literal': True}
        review = self.human_review()
        reordered = dict(reversed(list(self.p.items())))
        record = correction.assemble(reordered, self.c, review)
        self.assertTrue(correction.verify(self.p, record)['valid'])
        changed = copy.deepcopy(self.p); changed['opaque']['literal'] = 1
        with self.assertRaises(ValueError): correction.assemble(changed, self.c, review)

    def test_text_expansion_and_cli_encoding_bounds_precede_output_creation(self):
        # Canonical input can fit while safe quoted display expands controls.
        payload = {'fictional': '\u202e' * 100}
        with patch.object(correction, 'MAX_APPLICATION_BYTES', 450):
            with self.assertRaisesRegex(ValueError, 'byte limit'): correction.render_text(payload)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); p = root/'p.json'; c = root/'c.json'; out = root/'out.json'
            p.write_bytes(canonical_json_bytes(self.p)); c.write_bytes(canonical_json_bytes(self.c))
            argv = ['result_correction.py', 'target', str(p), str(c), '--output', str(out)]
            with patch.object(sys, 'argv', argv), patch.object(correction, '_encode', return_value='x' * 101), \
                    patch.object(correction, 'MAX_APPLICATION_BYTES', 100), \
                    patch.object(correction, 'prepare', return_value={'fictional': True}), \
                    patch.object(correction, 'configure_utf8_stdio'), patch('sys.stderr', new_callable=io.StringIO):
                with self.assertRaises(SystemExit): correction.main()
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
