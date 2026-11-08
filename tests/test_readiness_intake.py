"""Implementation-author synthetic readiness intake, preservation and documented-rehearsal regressions."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import readiness_intake as intake
from evidence_workflow import run
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


class ReadinessIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('synthesis-review.json')
        self.c = fixture('manual-readiness-candidates.json')

    def review(self, p=None, c=None):
        review = intake.prepare(self.p if p is None else p, self.c if c is None else c)['review_document']
        review.update(receipt_id='fictional-readiness-import', decision='import_readiness_assertions',
                      reviewer='Fictional import reviewer', reviewed_at='2026-11-08',
                      rationale='Record the supplied fictional readiness assertion only.')
        return review

    def assembled(self, p=None, c=None):
        p, c = self.p if p is None else p, self.c if c is None else c
        return intake.assemble(p, c, self.review(p, c))

    def reject(self, c, p=None, pattern=None):
        if pattern is None:
            with self.assertRaises((ValueError, TypeError)):
                intake.prepare(self.p if p is None else p, c)
        else:
            with self.assertRaisesRegex(ValueError, pattern):
                intake.prepare(self.p if p is None else p, c)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'readiness_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_template_binds_current_gates_lists_open_gates_and_leaves_judgements_blank(self):
        old = copy.deepcopy(self.p)
        result = intake.template(self.p)
        current = run(self.p)['readiness']
        row = result['candidate_document']['readiness_assertions'][0]
        self.assertEqual(row['gates_sha256'], current['gates_sha256'])
        self.assertIsNone(row['reopening'])
        self.assertTrue(all(row[key] is None for key in intake.TEXT_FIELDS | {'evidence_sufficiency', 'conclusion_readiness'}))
        self.assertEqual(set(row), intake.ASSERTION_FIELDS)
        self.assertEqual(result['gate_ledger'], current['gate_ledger'])
        self.assertEqual(result['open_gate_ids'], current['open_gate_ids'])
        self.assertEqual(result['closed_gate_ids'], ['searches_complete'])
        self.assertEqual(result['status'], 'AWAITING_SUPPLIED_READINESS_ASSERTIONS')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['mechanical_conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['readiness_assessment'], 'NOT_PERFORMED')
        self.assertFalse(result['protocol_changed'])
        self.assertEqual(self.p, old)
        self.reject(result['candidate_document'])
        demo = fixture('review-demo.json')
        self.assertEqual(intake.template(demo)['gates_sha256'], run(demo)['readiness']['gates_sha256'])

    def test_separate_blank_import_review_and_deterministic_preparation(self):
        old = copy.deepcopy((self.p, self.c))
        target = intake.prepare(self.p, self.c)
        self.assertEqual(target, intake.prepare(self.p, self.c))
        self.assertEqual((self.p, self.c), old)
        self.assertTrue(all(v is None for k, v in target['review_document'].items() if k not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError):
            intake.assemble(self.p, self.c, target['review_document'])
        inner = target['target']
        self.assertEqual(inner['target_type'], 'manual_readiness_intake')
        self.assertEqual(inner['gates_sha256'], run(self.p)['readiness']['gates_sha256'])
        self.assertEqual(inner['open_gate_ids'], run(self.p)['readiness']['open_gate_ids'])
        self.assertIsNone(inner['before_current_assertion_ids'])
        self.assertEqual(inner['after_current_assertion_ids'], ['readiness-supplied-1'])
        self.assertEqual(inner['after_stale_assertion_ids'], [])
        self.assertEqual([row['input_pointer'] for row in inner['reopening_work']], ['/gaps/0'])
        self.assertEqual(inner['reopening_work'][0]['work_package_id'], 'WP-MECHANISM')
        self.assertEqual(inner['appended_assertions'][0]['output_pointer'], '/readiness_assertions/0')
        self.assertEqual(inner['normalized_appended_assertions'][0]['source_match_status'], 'CURRENT_GATES')
        self.assertEqual(inner['normalized_appended_assertions'][0]['reopening_status'], 'OPEN_WORK')

    def test_only_assertions_append_and_every_other_assertion_is_preserved(self):
        self.p['opaque'] = {'β': [1, True, None], 'literal': '\n  preserve '}
        old = copy.deepcopy(self.p)
        app = self.assembled()
        after = app['protocol_candidate']
        self.assertEqual(after['readiness_assertions'], self.c['readiness_assertions'])
        self.assertEqual({k: v for k, v in after.items() if k != 'readiness_assertions'}, old)
        self.assertEqual(self.p, old)
        self.assertEqual(app['receipt']['before_assertion_count'], 0)
        self.assertEqual(app['receipt']['after_assertion_count'], 1)
        self.assertEqual(app['receipt']['before_flow'], app['receipt']['after_flow'])
        for key in ('synthesis', 'challenge', 'planning', 'work_packages'):
            self.assertEqual(run(after)[key], run(old)[key])
        self.assertEqual(run(after)['readiness']['gate_ledger'], run(old)['readiness']['gate_ledger'])
        self.assertEqual(run(after)['conclusion_readiness'], 'NOT_READY')
        self.assertTrue(intake.verify(old, app)['valid'])
        second = copy.deepcopy(self.c)
        second['readiness_assertions'][0].update(assertion_id='readiness-supplied-2', conclusion_readiness='READY',
                                                 evidence_sufficiency='UNASSESSED', reopening=None)
        again = intake.assemble(after, second, self.review(after, second))
        self.assertEqual(again['receipt']['before_assertion_count'], 1)
        self.assertEqual(again['receipt']['after_assertion_count'], 2)
        self.assertEqual(again['protocol_candidate']['readiness_assertions'][:1], self.c['readiness_assertions'])
        readiness = run(again['protocol_candidate'])['readiness']
        self.assertEqual(readiness['current_assertion_ids'], ['readiness-supplied-1', 'readiness-supplied-2'])
        self.assertTrue(readiness['assertion_ledger'][1]['ready_with_open_gates'])
        self.assertEqual(run(again['protocol_candidate'])['conclusion_readiness'], 'NOT_READY')

    def test_changed_gates_invalidate_the_template_hash(self):
        p = copy.deepcopy(self.p)
        p['synthesis_statements'][0]['text'] = 'Changed fictional statement text.'
        self.reject(self.c, p, 'regenerate the template')
        p = copy.deepcopy(self.p)
        p['screening'].append(dict(record_id='r8', decision='exclude', reason='Synthetic exclusion'))
        self.reject(self.c, p, 'regenerate the template')
        fresh = intake.template(p)['candidate_document']['readiness_assertions'][0]
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0]['gates_sha256'] = fresh['gates_sha256']
        self.assertTrue(intake.verify(p, self.assembled(p, c))['valid'])
        p = copy.deepcopy(self.p)
        p['version'] = 'different supplied version'
        self.assertTrue(intake.verify(p, self.assembled(p, self.c))['valid'])

    def test_reopening_rules_apply_at_intake(self):
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0]['reopening'] = None
        self.reject(c, pattern='must name existing reopening work')
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0]['reopening'] = dict(work_package_id='WP-MISSING')
        self.reject(c, pattern='existing work package')
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0]['reopening'] = dict(amendment_note='Fictional amendment note.')
        self.assertEqual(run(self.assembled(c=c)['protocol_candidate'])['readiness']['assertion_ledger'][0]['reopening_status'],
                         'OPEN_AMENDMENT')
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0].update(conclusion_readiness='READY', evidence_sufficiency='SUFFICIENT', reopening=None)
        row = run(self.assembled(c=c)['protocol_candidate'])['readiness']['assertion_ledger'][0]
        self.assertTrue(row['ready_with_open_gates'])
        self.assertEqual(row['open_gates_at_assertion'], run(self.p)['readiness']['open_gate_ids'])

    def test_strict_candidate_schema_types_dates_and_lists(self):
        for bad in (None, [], {}, True, dict(self.c, schema_version=True), dict(self.c, schema_version=2),
                    dict(self.c, extra=1), dict(self.c, readiness_assertions=[])):
            self.reject(bad)
        for field in intake.ASSERTION_FIELDS:
            c = copy.deepcopy(self.c)
            c['readiness_assertions'][0].pop(field)
            self.reject(c)
        for key, value in [('extra', True), ('assessed_at', '2026-02-30'), ('assessed_at', '2026-1-08'),
                           ('evidence_sufficiency', 'ENOUGH'), ('evidence_sufficiency', None),
                           ('conclusion_readiness', 'MAYBE'), ('conclusion_readiness', None),
                           ('reopening', dict(work_package_id='WP-MECHANISM', amendment_note='x')),
                           ('reopening', dict(other='x')), ('reopening', []), ('reopening', dict(amendment_note=' ')),
                           ('gates_sha256', 'A' * 64), ('gates_sha256', None), ('gates_sha256', 'abc')]:
            c = copy.deepcopy(self.c)
            c['readiness_assertions'][0][key] = value
            with self.subTest(key=key, value=value):
                self.reject(c)
        for field in intake.TEXT_FIELDS:
            for value in (None, True, 1, ' ', {}, []):
                c = copy.deepcopy(self.c)
                c['readiness_assertions'][0][field] = value
                self.reject(c)
        c = copy.deepcopy(self.c)
        row = c['readiness_assertions'][0]
        c['readiness_assertions'] = [dict(copy.deepcopy(row), assertion_id='new-%03d' % i) for i in range(100)]
        self.assertEqual(len(intake.prepare(self.p, c)['target']['appended_assertions']), 100)
        c['readiness_assertions'].append(dict(row, assertion_id='over-limit'))
        self.reject(c)

    def test_existing_and_candidate_id_collisions_never_replace(self):
        app = self.assembled()
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0].update(conclusion_readiness='READY', evidence_sufficiency='SUFFICIENT', reopening=None)
        self.reject(c, app['protocol_candidate'], 'collides with an existing readiness assertion')
        c = copy.deepcopy(self.c)
        c['readiness_assertions'].append(copy.deepcopy(c['readiness_assertions'][0]))
        self.reject(c, pattern='duplicate candidate assertion_id')

    def test_whole_input_candidate_and_implementation_changes_invalidate_review(self):
        review = self.review()
        p = copy.deepcopy(self.p)
        p['opaque'] = 'new'
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(p, self.c, review)
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0]['limitations'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(self.p, c, review)
        hashes = intake._implementation_hashes()
        hashes['readiness_intake.py'] = '0' * 64
        with patch.object(intake, '_implementation_hashes', return_value=hashes):
            with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
                intake.assemble(self.p, self.c, review)

    def test_strict_review_and_wrong_kind_rejected(self):
        review = self.review()
        for key, value in [('schema_version', True), ('decision', 'import_challenges'), ('reviewer', ''),
                           ('reviewed_at', '2026-02-30'), ('target_sha256', 'A' * 64), ('extra', 1)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.assemble(self.p, self.c, dict(review, **{key: value}))
        app = self.assembled()
        app['kind'] = 'detached_challenge_intake'
        with self.assertRaises(ValueError):
            intake.verify(self.p, app)

    def test_resealed_tampering_cannot_hide_changed_labels_or_claims(self):
        original = self.assembled()
        for part in ('output', 'snapshot', 'queue', 'claim'):
            app = copy.deepcopy(original)
            if part == 'output':
                app['protocol_candidate']['readiness_assertions'][-1]['conclusion_readiness'] = 'READY'
            if part == 'snapshot':
                app['receipt']['target']['gate_ledger'][0]['status'] = 'CLOSED'
            if part == 'queue':
                app['receipt']['target']['after_current_assertion_ids'] = []
            if part == 'claim':
                app['receipt']['readiness_assessment'] = 'PERFORMED'
            app['receipt']['receipt_sha256'] = intake.digest({k: v for k, v in app['receipt'].items() if k != 'receipt_sha256'})
            with self.subTest(part=part), self.assertRaises(ValueError):
                intake.verify(self.p, app)

    def test_consistently_reauthored_unsigned_reviewer_is_not_authenticated(self):
        app = self.assembled()
        app['receipt']['assertion']['reviewer'] = 'Different supplied reviewer label'
        app['receipt']['receipt_sha256'] = intake.digest({k: v for k, v in app['receipt'].items() if k != 'receipt_sha256'})
        checked = intake.verify(self.p, app)
        self.assertTrue(checked['valid'])
        self.assertEqual(checked['reviewer_identity_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(checked['assessor_identity_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(checked['conclusion_readiness'], 'NOT_READY')

    def test_size_limits_nonfinite_values_and_detached_mutation(self):
        for constant in ('MAX_CANDIDATE_BYTES', 'MAX_PROTOCOL_BYTES', 'MAX_APPLICATION_BYTES'):
            with patch.object(intake, constant, 1):
                with self.assertRaisesRegex(ValueError, 'byte limit'):
                    intake.prepare(self.p, self.c)
        p = copy.deepcopy(self.p)
        p['opaque'] = float('nan')
        self.reject(self.c, p)
        old = copy.deepcopy((self.p, self.c))
        app = self.assembled()
        app['protocol_candidate']['readiness_assertions'][0]['conclusion_readiness'] = 'mutated'
        app['receipt']['target']['gate_ledger'][0]['open_items'].append('mutated')
        self.assertEqual((self.p, self.c), old)

    def test_no_network_and_text_control_injection(self):
        c = copy.deepcopy(self.c)
        c['readiness_assertions'][0]['rationale'] = '가상\nConclusion: READY‮\x1b https://invalid.example/not-fetched'
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')):
            app = self.assembled(c=c)
            text = intake.render_text(app)
        for bad in ('\nConclusion: READY', '‮', '\x1b'):
            self.assertNotIn(bad, text)
        self.assertIn('가상', text)
        self.assertEqual(app['receipt']['external_calls'], 0)
        self.assertEqual(app['receipt']['conclusion_readiness'], 'NOT_READY')

    def test_mock_adapter_integrity_is_preserved(self):
        import offline_adapter
        p = offline_adapter.assemble(fixture('adapter-protocol.json'), fixture('adapter-fixture.json'),
                                     fixture('adapter-reviews.json'))['protocol']
        draft = intake.template(p)['candidate_document']['readiness_assertions'][0]
        c = copy.deepcopy(self.c)
        c['readiness_assertions'] = [dict(c['readiness_assertions'][0], gates_sha256=draft['gates_sha256'],
                                          evidence_sufficiency='UNASSESSED', reopening=None)]
        app = self.assembled(p, c)
        self.assertEqual(app['protocol_candidate']['adapter_receipts'], p['adapter_receipts'])
        self.assertEqual(run(app['protocol_candidate'])['evidence'], run(p)['evidence'])
        self.assertTrue(intake.verify(p, app)['valid'])

    def test_implementation_map_covers_used_helpers(self):
        for name in ('readiness_intake.py', 'nbib_intake.py', 'readiness_links.py', 'challenge_links.py',
                     'synthesis_links.py', 'report_links.py', 'evidence_workflow.py'):
            self.assertEqual(intake._implementation_hashes()[name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
        self.assertNotIn('readiness_review.py', intake._implementation_hashes())

    def test_bundle_keeps_assertions_but_not_detached_import_record(self):
        import zipfile
        app = self.assembled()
        raw = research_bundle.build_bundle(json.dumps(app['protocol_candidate']).encode())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(json.loads(archive.read('protocol.json'))['readiness_assertions'],
                             app['protocol_candidate']['readiness_assertions'])
            self.assertNotIn('readiness-application.json', archive.namelist())
            self.assertIn(b'Supplied readiness assertions: current 1, stale 0', archive.read('summary.md'))
            self.assertIn(b'Conclusion: NOT_READY', archive.read('summary.md'))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'bundle.zip'
            path.write_bytes(raw)
            self.assertTrue(research_bundle.verify(path)['valid'])

    def test_documented_rehearsal_commands_run_in_order(self):
        allowed = {'readiness_intake.py', 'readiness_review.py', 'research_status.py', 'research_bundle.py'}
        document = (ROOT / 'docs' / 'CONCLUSION_READINESS.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        self.assertEqual(len(blocks), 2)
        with tempfile.TemporaryDirectory(prefix='sensei readiness rehearsal ') as td:
            output = Path(td)
            executed = 0
            for index, block in enumerate(blocks):
                if index == 1:
                    target = json.loads((output / 'readiness-target.json').read_bytes())
                    review = target['review_document']
                    review.update(receipt_id='fictional-readiness-import', decision='import_readiness_assertions',
                                  reviewer='Fictional import reviewer', reviewed_at='2026-11-08',
                                  rationale='Record the supplied fictional readiness assertion only.')
                    (output / 'readiness-review.json').write_text(json.dumps(review), encoding='utf-8')
                for line in block.splitlines():
                    if not line.strip():
                        continue
                    tokens = shlex.split(line)
                    self.assertEqual(tokens[0], 'python')
                    self.assertIn(tokens[1], allowed, line)
                    command = [sys.executable] + [token.replace('OUTPUT', str(output)) for token in tokens[1:]]
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120,
                                            env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))
                    self.assertEqual(result.returncode, 0, (line, result.stderr.decode('utf-8', 'replace')))
                    executed += 1
                    text = result.stdout.decode('utf-8')
                    if tokens[1] == 'research_status.py':
                        self.assertIn('Open readiness gates: 10', text)
                        self.assertIn('Supplied readiness assertions: current 1, stale 0', text)
                        self.assertIn('Conclusion: NOT_READY', text)
                    elif tokens[1] == 'readiness_review.py':
                        self.assertIn('Assertions bound to the current gates: ["readiness-supplied-1"]', text)
                        self.assertIn('Mechanical conclusion readiness: NOT_READY', text)
                    elif '--text' not in tokens:
                        json.loads(result.stdout)
            self.assertEqual(executed, 8)
            final = json.loads((output / 'with-readiness.json').read_bytes())
            self.assertEqual([row['assertion_id'] for row in final['readiness_assertions']], ['readiness-supplied-1'])
            readiness = run(final)['readiness']
            self.assertEqual(readiness['current_assertion_ids'], ['readiness-supplied-1'])
            self.assertEqual(readiness['assertion_ledger'][0]['reopening_status'], 'OPEN_WORK')
            self.assertEqual(run(final)['conclusion_readiness'], 'NOT_READY')
            self.assertTrue((output / 'research.zip').is_file())
            self.assertTrue((output / 'readiness-draft.json').is_file())

    def test_cli_roundtrip_exclusive_outputs_and_replay_before_export(self):
        with tempfile.TemporaryDirectory(prefix='readiness cli ') as td:
            d = Path(td)
            p, c = d / 'p.json', d / 'c.json'
            p.write_bytes(json.dumps(self.p).encode())
            c.write_bytes(json.dumps(self.c).encode())
            draft, target, review, app, out = (d / name for name in ('draft.json', 'target.json', 'review.json', 'app.json', 'out.json'))
            for args in [('template', p, '--candidate-output', draft), ('target', p, c, '--output', target, '--text')]:
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(self.cli('template', p, '--candidate-output', draft).returncode, 0)
            review.write_bytes(json.dumps(self.review()).encode())
            for args in [('assemble', p, c, review, '--output', app), ('verify', p, app, '--protocol-output', out)]:
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
            before = out.read_bytes()
            self.assertNotEqual(self.cli('verify', p, app, '--protocol-output', out).returncode, 0)
            self.assertEqual(out.read_bytes(), before)
            value = json.loads(app.read_bytes())
            value['receipt']['receipt_sha256'] = '0' * 64
            app.write_bytes(json.dumps(value).encode())
            blocked = d / 'blocked.json'
            self.assertNotEqual(self.cli('verify', p, app, '--protocol-output', blocked).returncode, 0)
            self.assertFalse(blocked.exists())
            c.write_bytes(b'{"schema_version":1,"schema_version":1}')
            dup = d / 'dup.json'
            self.assertNotEqual(self.cli('target', p, c, '--output', dup).returncode, 0)
            self.assertFalse(dup.exists())


if __name__ == '__main__':
    unittest.main()
