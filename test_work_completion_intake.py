"""Independent synthetic reviewed completion and exact replay regression tests."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import work_completion_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from work_review import review_packets

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def candidate(wid='WP-RESULT-LINKS'):
    return dict(schema_version=1, work_package_id=wid,
                artifact_locator='synthetic://fictional-completion/검토', acceptance_verified=True,
                completed_by='Fictional operator', completed_at='2026-11-04',
                completion_note='Supplied fictional bookkeeping assertion, not scientific acceptance.')


class WorkCompletionIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('result-source-current.json')
        self.c = candidate()

    def review(self, p, c):
        review = intake.prepare(p, c)['review_document']
        review.update(receipt_id='fictional-completion-receipt', decision='record_supplied_completion',
                      reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                      rationale='Review this fictional completion assertion only.')
        return review

    def assembled(self, p=None, c=None):
        p = self.p if p is None else p
        c = self.c if c is None else c
        return intake.assemble(p, c, self.review(p, c))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'work_completion_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0', PYTHONDONTWRITEBYTECODE='1'))

    def test_template_selects_only_id_and_leaves_every_assertion_null(self):
        old = copy.deepcopy(self.p)
        result = intake.template(self.p, self.c['work_package_id'])
        self.assertEqual(result, intake.template(self.p, self.c['work_package_id']))
        self.assertEqual(self.p, old)
        draft = result['candidate_document']
        self.assertEqual(set(draft), set(self.c))
        self.assertEqual(draft['work_package_id'], self.c['work_package_id'])
        self.assertEqual(draft['schema_version'], 1)
        self.assertTrue(all(v is None for k, v in draft.items() if k not in ('schema_version', 'work_package_id')))
        self.assertFalse(result['protocol_changed'])
        with self.assertRaises(ValueError):
            intake.prepare(self.p, draft)

    def test_unknown_and_nonliteral_selection_reject(self):
        for wid in (None, True, 1, [], {}, '', ' ', 'WP-RESULT-LINKS ', 'wp-result-links', 'missing'):
            with self.subTest(wid=wid), self.assertRaises((ValueError, TypeError)):
                intake.template(self.p, wid)

    def test_prepare_is_nonmutating_and_requires_blank_separate_review(self):
        original = copy.deepcopy((self.p, self.c))
        prepared = intake.prepare(self.p, self.c)
        self.assertEqual(prepared, intake.prepare(self.p, self.c))
        self.assertEqual((self.p, self.c), original)
        review = prepared['review_document']
        self.assertEqual(review['target_sha256'], prepared['target']['target_sha256'])
        self.assertTrue(all(v is None for k, v in review.items() if k not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError):
            intake.assemble(self.p, self.c, review)
        prepared['target']['before_raw_work']['question'] = 'detached mutation'
        self.assertEqual((self.p, self.c), original)

    def test_changes_only_four_selected_fields_and_retains_raw_defaults(self):
        self.p['opaque_metadata'] = {'literal': ['β', None, {'verbatim': '  preserve\n  '}]}
        old = copy.deepcopy(self.p)
        record = self.assembled()
        after = record['protocol_candidate']
        changed = {'status', 'artifact_locator', 'acceptance_verified', 'completion_basis_sha256'}
        self.assertEqual({k: v for k, v in after['gaps'][0].items() if k not in changed}, old['gaps'][0])
        restored = copy.deepcopy(after)
        restored['gaps'][0] = old['gaps'][0]
        self.assertEqual(restored, old)
        self.assertEqual(self.p, old)
        self.assertNotIn('depends_on', after['gaps'][0])
        self.assertNotIn('completed_by', after['gaps'][0])
        self.assertEqual(after['gaps'][0]['status'], 'COMPLETE')
        self.assertIs(after['gaps'][0]['acceptance_verified'], True)
        before_run, after_run = run(old), run(after)
        for key in ('review_targets', 'planning_ledger'):
            self.assertEqual(before_run['planning'][key], after_run['planning'][key])
        target = record['receipt']['target']
        self.assertEqual(target['before_raw_work'], old['gaps'][0])
        self.assertEqual(target['proposed_raw_work'], after['gaps'][0])
        self.assertEqual(target['input_pointer'], '/gaps/0')
        self.assertEqual(target['output_pointer'], '/gaps/0')
        completion = target['proposed_completion_review']
        self.assertEqual(completion['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(completion['supplied_basis_sha256'], completion['current_basis_sha256'])
        self.assertEqual(completion['acceptance_assessment'], 'NOT_PERFORMED')
        self.assertTrue(intake.verify(old, record)['valid'])

    def test_existing_unfinished_locator_and_acceptance_are_visible_before_overwrite(self):
        self.p['gaps'][0].update(status='IN_PROGRESS', artifact_locator='synthetic://old', acceptance_verified=False)
        target = self.assembled()['receipt']['target']
        self.assertEqual(target['before_raw_work']['artifact_locator'], 'synthetic://old')
        self.assertIs(target['before_raw_work']['acceptance_verified'], False)
        self.assertEqual(target['proposed_raw_work']['artifact_locator'], self.c['artifact_locator'])

    def test_implicit_legacy_id_is_not_materialized(self):
        p = fixture('context-protocol.json')
        record = self.assembled(p, candidate('WP-001'))
        target = record['receipt']['target']
        self.assertEqual(target['identity_origin'], 'LEGACY_POSITIONAL_ID')
        self.assertEqual(target['before_normalized_work']['work_package_id'], 'WP-001')
        self.assertNotIn('work_package_id', record['protocol_candidate']['gaps'][0])
        self.assertEqual(record['protocol_candidate']['contexts'], p['contexts'])
        self.assertTrue(intake.verify(p, record)['valid'])

    def test_source_work_preserves_refs_and_no_evidence_is_invented(self):
        c = candidate('WP-MEMBERSHIP-SOURCES')
        after = self.assembled(self.p, c)['protocol_candidate']
        self.assertEqual(after['gaps'][1]['source_refs'], self.p['gaps'][1]['source_refs'])
        self.assertEqual(after['gaps'][1]['evidence_ids'], [])
        self.assertEqual(after['evidence'], self.p['evidence'])
        self.assertEqual(after['gaps'][1]['work_type'], 'source_review')

    def test_blocked_completion_rejects_then_separate_prerequisite_unblocks(self):
        p = fixture('source-work-protocol.json')
        first, second = [w['work_package_id'] for w in p['gaps']]
        with self.assertRaisesRegex(ValueError, 'unfinished dependency'):
            intake.prepare(p, candidate(second))
        record = self.assembled(p, candidate(first))
        self.assertEqual(record['receipt']['derived_blocking_changes'], [dict(
            work_package_id=second, before_blocked_by=[first], after_blocked_by=[])])
        after = record['protocol_candidate']
        self.assertEqual(after['gaps'][1], p['gaps'][1])
        self.assertEqual(run(after)['planning']['review_targets'], run(p)['planning']['review_targets'])
        final = self.assembled(after, candidate(second))
        self.assertEqual([w['status'] for w in run(final['protocol_candidate'])['work_packages']], ['COMPLETE', 'COMPLETE'])
        self.assertTrue(intake.verify(after, final)['valid'])

    def test_stale_and_unbound_prerequisites_are_not_renewed_or_hidden(self):
        for mode in ('STALE_SOURCE', 'UNBOUND_COMPLETION'):
            p = fixture('completion-binding.json')
            if mode == 'STALE_SOURCE':
                p['gaps'][0]['completion_basis_sha256'] = '0' * 64
            else:
                p['gaps'][0].pop('completion_basis_sha256')
            record = self.assembled(p, candidate('WP-TRANSLATION'))
            self.assertEqual(record['protocol_candidate']['gaps'][0], p['gaps'][0])
            cues = record['receipt']['target']['direct_prerequisite_completion_reviews']
            self.assertEqual(cues[0]['completion_review']['source_match_status'], mode)
            self.assertEqual(cues[0]['supplied_status'], 'COMPLETE')
            self.assertEqual(record['receipt']['target']['proposed_completion_review']['source_match_status'], 'CURRENT_SOURCE')

    def test_complete_work_cannot_be_rebound_even_if_stale(self):
        p = fixture('completion-binding.json')
        for value in ('0' * 64, None):
            if value is None:
                p['gaps'][0].pop('completion_basis_sha256')
            else:
                p['gaps'][0]['completion_basis_sha256'] = value
            with self.assertRaisesRegex(ValueError, 'existing COMPLETE'):
                intake.prepare(p, candidate('WP-MECHANISM'))
            with self.assertRaisesRegex(ValueError, 'existing COMPLETE'):
                intake.template(p, 'WP-MECHANISM')

    def test_document_source_context_and_dependent_bindings_do_not_change(self):
        from test_work_document_sources import fixture as document_fixture
        p = document_fixture()
        record = self.assembled(p, candidate('WP-OWN'))
        before, after = run(p), run(record['protocol_candidate'])
        self.assertEqual(before['planning']['review_targets'], after['planning']['review_targets'])
        self.assertEqual(record['protocol_candidate']['report_sources'], p['report_sources'])
        self.assertEqual(record['protocol_candidate']['gaps'][0]['document_source_ids'], ['source-main'])
        packet = review_packets(record['protocol_candidate'], 'WP-DIRECT')['packets'][0]
        self.assertTrue(packet['direct_dependency_document_sources'])
        self.assertEqual(packet['direct_prerequisite_completion_reviews'][0]['source_match_status'], 'CURRENT_SOURCE')

    def test_strict_candidate_schema_types_dates_and_acceptance(self):
        bads = [None, [], True, {}, dict(self.c, schema_version=True), dict(self.c, schema_version=2), dict(self.c, extra=1)]
        for field in self.c:
            missing = copy.deepcopy(self.c); missing.pop(field); bads.append(missing)
        for value in (False, 1, 'true', None, [], {}):
            bads.append(dict(self.c, acceptance_verified=value))
        for field in ('work_package_id', 'artifact_locator', 'completed_by', 'completion_note'):
            for value in ('', ' ', None, True, 2, [], {}):
                bads.append(dict(self.c, **{field: value}))
        for value in ('2026-02-30', '2026-1-04', '2026-11-04T00:00:00Z', '0000-01-01'):
            bads.append(dict(self.c, completed_at=value))
        for bad in bads:
            with self.subTest(bad=bad), self.assertRaises((ValueError, TypeError)):
                intake.prepare(self.p, bad)

    def test_strict_review_no_implicit_decision(self):
        review = self.review(self.p, self.c)
        for field, value in [('schema_version', True), ('decision', 'approve'), ('reviewer', ''),
                             ('reviewed_at', '2026-02-30'), ('target_sha256', 'A' * 64), ('rationale', None)]:
            bad = dict(review, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                intake.assemble(self.p, self.c, bad)

    def test_exact_target_rejects_unrelated_input_candidate_and_implementation_changes(self):
        review = self.review(self.p, self.c)
        p = copy.deepcopy(self.p); p['unrelated'] = 'new metadata'
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(p, self.c, review)
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(self.p, dict(self.c, completion_note='Changed'), review)
        hashes = intake._implementation_hashes()
        hashes['work_completion_intake.py'] = '0' * 64
        with patch.object(intake, '_implementation_hashes', return_value=hashes):
            with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
                intake.assemble(self.p, self.c, review)

    def test_verify_detects_receipt_candidate_output_and_claim_tampering(self):
        record = self.assembled()
        for kind in ('candidate', 'output', 'target', 'claim', 'receipt'):
            changed = copy.deepcopy(record)
            if kind == 'candidate': changed['receipt']['candidate_document']['artifact_locator'] = 'synthetic://changed'
            if kind == 'output': changed['protocol_candidate']['gaps'][0]['completion_basis_sha256'] = '0' * 64
            if kind == 'target': changed['receipt']['target']['before_raw_work']['question'] = 'changed'
            if kind == 'claim': changed['receipt']['acceptance_assessment'] = 'VERIFIED'
            if kind == 'receipt': changed['receipt']['receipt_sha256'] = '0' * 64
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                intake.verify(self.p, changed)

    def test_detached_output_does_not_alias_inputs(self):
        record = self.assembled()
        original = canonical_json_bytes(self.p)
        record['protocol_candidate']['evidence'][0]['limitations'] = 'mutated output'
        record['receipt']['candidate_document']['completed_by'] = 'mutated receipt'
        self.assertEqual(canonical_json_bytes(self.p), original)
        self.assertEqual(self.c['completed_by'], 'Fictional operator')

    def test_current_and_stale_planning_assertions_are_preserved(self):
        for state in ('CURRENT_SOURCE', 'STALE_SOURCE'):
            p = fixture('planning-review.json')
            if state == 'STALE_SOURCE':
                for row in p['planning_decisions']:
                    row['basis_sha256'] = '0' * 64
            before = run(p)
            self.assertEqual({r['source_match_status'] for r in before['planning']['planning_ledger']}, {state})
            record = self.assembled(p, candidate('WP-MECHANISM'))
            after = run(record['protocol_candidate'])
            self.assertEqual(record['protocol_candidate']['planning_decisions'], p['planning_decisions'])
            for key in ('review_targets', 'planning_ledger', 'current_rank_groups'):
                self.assertEqual(after['planning'][key], before['planning'][key])
            self.assertTrue(intake.verify(p, record)['valid'])

    def test_mock_adapter_provenance_survives_completion(self):
        import offline_adapter
        p = offline_adapter.assemble(fixture('adapter-protocol.json'), fixture('adapter-fixture.json'),
                                     fixture('adapter-reviews.json'))['protocol']
        p['gaps'] = [dict(work_package_id='WP-MOCK', question='Fictional metadata review?',
            evidence_ids=['e1', 'e2'], deliverable='Fictional trace note',
            acceptance_criterion='Human checks the fictional trace note.')]
        record = self.assembled(p, candidate('WP-MOCK'))
        new = record['protocol_candidate']
        self.assertEqual({k: v for k, v in new.items() if k != 'gaps'},
                         {k: v for k, v in p.items() if k != 'gaps'})
        self.assertEqual(run(new)['evidence'], run(p)['evidence'])
        self.assertTrue(intake.verify(p, record)['valid'])

    def test_csv_collection_provenance_survives_completion(self):
        import bibliographic_intake
        import bibliographic_review
        p = fixture('bibliographic-base.json')
        artifact = bibliographic_intake.prepare(p, b'record_id,source_locator\nfictional-input,synthetic:export\n',
                                                'local-primary', '2026-11-04T00:00:00Z')
        choices = bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record', record_id='record-one', rationale='Synthetic identity assertion')
        review = bibliographic_review.prepare_review(p, artifact, choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                               rationale='Fictional collection', decision='import_for_screening')
        p = bibliographic_review.assemble(p, artifact, review)['protocol_candidate']
        p['screening'] = [dict(record_id='record-one', decision='include', reason='Fictional scope')]
        evidence = copy.deepcopy(self.p['evidence'][0])
        evidence.update(evidence_id='csv-result', record_id='record-one')
        p['evidence'] = [evidence]
        p['gaps'] = [dict(work_package_id='WP-CSV', question='Fictional provenance review?',
            evidence_ids=['csv-result'], deliverable='Fictional provenance note',
            acceptance_criterion='Human checks the fictional provenance note.')]
        record = self.assembled(p, candidate('WP-CSV'))
        new = record['protocol_candidate']
        self.assertEqual({k: v for k, v in new.items() if k != 'gaps'},
                         {k: v for k, v in p.items() if k != 'gaps'})
        self.assertEqual(run(new)['bibliographic_collection'], run(p)['bibliographic_collection'])
        self.assertTrue(intake.verify(p, record)['valid'])

    def test_size_limits_and_nonfinite_json_fail(self):
        with patch.object(intake, 'MAX_CANDIDATE_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                intake.prepare(self.p, self.c)
        with patch.object(intake, 'MAX_PROTOCOL_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                intake.prepare(self.p, self.c)
        with patch.object(intake, 'MAX_APPLICATION_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                intake.prepare(self.p, self.c)
        p = copy.deepcopy(self.p); p['opaque'] = float('nan')
        with self.assertRaises(ValueError): intake.prepare(p, self.c)

    def test_locator_is_literal_and_not_opened(self):
        for locator in ('https://invalid.example/never-fetch', '/does/not/exist', '=HYPERLINK("fictional")', 'synthetic://line\nnext'):
            c = dict(self.c, artifact_locator=locator)
            with patch('urllib.request.urlopen', side_effect=AssertionError('must not fetch')):
                record = self.assembled(self.p, c)
            self.assertEqual(record['protocol_candidate']['gaps'][0]['artifact_locator'], locator)
            self.assertEqual(record['receipt']['external_calls'], 0)
            self.assertEqual(record['receipt']['artifact_content_verification'], 'NOT_PERFORMED')

    def test_cli_roundtrip_utf8_and_exclusive_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            p, c, r, target, app, output, draft = [d / name for name in ('p.json', 'c.json', 'r.json', 'target.json', 'app.json', 'output.json', 'draft.json')]
            p.write_text(json.dumps(self.p), encoding='utf-8')
            c.write_text(json.dumps(self.c, ensure_ascii=False), encoding='utf-8')
            result = self.cli('template', p, '--work-package', self.c['work_package_id'], '--candidate-output', draft)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsNone(json.loads(draft.read_bytes())['acceptance_verified'])
            result = self.cli('target', p, c, '--output', target, '--text')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('검토', result.stdout.decode('utf-8'))
            review = json.loads(target.read_bytes())['review_document']
            review.update(self.review(self.p, self.c))
            r.write_text(json.dumps(review), encoding='utf-8')
            result = self.cli('assemble', p, c, r, '--output', app)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.cli('verify', p, app, '--protocol-output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_bytes()), self.assembled()['protocol_candidate'])
            original = output.read_bytes()
            result = self.cli('verify', p, app, '--protocol-output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            corrupted = json.loads(app.read_bytes()); corrupted['receipt']['receipt_sha256'] = '0' * 64
            app.write_text(json.dumps(corrupted), encoding='utf-8')
            blocked = d / 'must-not-exist.json'
            result = self.cli('verify', p, app, '--protocol-output', blocked)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(blocked.exists())

    def test_cli_rejects_duplicate_json_and_existing_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp); p = d / 'p.json'; c = d / 'c.json'; output = d / 'new.json'
            p.write_text(json.dumps(self.p), encoding='utf-8')
            c.write_text('{"schema_version":1,"schema_version":1}', encoding='utf-8')
            result = self.cli('target', p, c, '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            c.write_text(json.dumps(self.c), encoding='utf-8')
            try:
                output.symlink_to(d / 'missing.json')
            except (OSError, NotImplementedError):
                return
            result = self.cli('target', p, c, '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(output.is_symlink())
            self.assertFalse((d / 'missing.json').exists())


if __name__ == '__main__':
    unittest.main()
