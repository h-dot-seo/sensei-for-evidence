"""Implementation-author synthetic challenge intake, preservation and documented-rehearsal regressions."""
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

import challenge_intake as intake
from challenge_links import challenge_basis
from evidence_workflow import run
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


class ChallengeIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('synthesis-review.json')
        self.c = fixture('manual-challenge-candidates.json')
        self.refs = fixture('challenge-references.json')

    def review(self, p=None, c=None):
        review = intake.prepare(self.p if p is None else p, self.c if c is None else c)['review_document']
        review.update(receipt_id='fictional-challenge-import', decision='import_challenges',
                      reviewer='Fictional import reviewer', reviewed_at='2026-11-08',
                      rationale='Record supplied fictional challenges only.')
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
        return subprocess.run([sys.executable, str(ROOT / 'challenge_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_template_binds_selection_lists_labels_and_leaves_judgements_blank(self):
        old = copy.deepcopy((self.p, self.refs))
        result = intake.template(self.p, self.refs)
        row = result['candidate_document']['challenges'][0]
        self.assertEqual(row['statement_ids'], ['statement-1', 'statement-2'])
        self.assertEqual(row['basis_sha256'], challenge_basis(run(self.p)['synthesis'], ['statement-1', 'statement-2']))
        self.assertEqual(row['missing_discriminating_evidence'], [])
        self.assertEqual(row['citation_integrity_findings'], [])
        self.assertIsNone(row['reopening'])
        self.assertTrue(all(row[key] is None for key in intake.TEXT_FIELDS | {'conclusion_width', 'outcome'}))
        self.assertEqual(set(row), intake.CHALLENGE_FIELDS)
        self.assertEqual(result['recorded_labels_on_selected_statements'], ['synthetic-reviewer'])
        self.assertEqual(result['independence_verification'], 'LABEL_DISTINCT_ONLY')
        self.assertFalse(result['protocol_changed'])
        self.assertEqual((self.p, self.refs), old)
        self.reject(result['candidate_document'])

    def test_reference_schema_unknown_repeated_and_empty_ids_rejected(self):
        for refs in (None, [], {}, {'schema_version': True, 'statement_ids': ['statement-1']},
                     {'schema_version': 1, 'statement_ids': []}, {'schema_version': 1, 'statement_ids': ['statement-1', 'statement-1']},
                     {'schema_version': 1, 'statement_ids': ['e1']}, {'schema_version': 1, 'statement_ids': ['missing']},
                     {'schema_version': 1, 'statement_ids': ['statement-1'], 'extra': True}):
            with self.subTest(refs=refs), self.assertRaises((ValueError, TypeError)):
                intake.template(self.p, refs)
        with self.assertRaisesRegex(ValueError, 'require supplied synthesis statements'):
            intake.template(fixture('review-demo.json'), dict(schema_version=1, statement_ids=['statement-1']))

    def test_separate_blank_import_review_and_deterministic_preparation(self):
        old = copy.deepcopy((self.p, self.c))
        target = intake.prepare(self.p, self.c)
        self.assertEqual(target, intake.prepare(self.p, self.c))
        self.assertEqual((self.p, self.c), old)
        self.assertTrue(all(v is None for k, v in target['review_document'].items() if k not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError):
            intake.assemble(self.p, self.c, target['review_document'])
        self.assertEqual(target['target']['before_statements_without_challenge'], ['statement-1', 'statement-2'])
        self.assertEqual(target['target']['after_statements_without_challenge'], [])
        self.assertEqual(target['target']['after_challenges_with_open_material_gaps'], ['challenge-supplied-1'])
        self.assertEqual(target['target']['recorded_labels_on_selected_statements'], ['synthetic-reviewer'])
        self.assertEqual([row['input_pointer'] for row in target['target']['selected_statements']],
                         ['/synthesis_statements/0', '/synthesis_statements/1'])
        self.assertEqual([row['evidence_id'] for row in target['target']['selected_evidence']], ['e1', 'e2'])

    def test_only_challenges_append_and_every_other_assertion_is_preserved(self):
        self.p['opaque'] = {'β': [1, True, None], 'literal': '\n  preserve '}
        old = copy.deepcopy(self.p)
        app = self.assembled()
        after = app['protocol_candidate']
        self.assertEqual(after['challenges'], self.c['challenges'])
        self.assertEqual({k: v for k, v in after.items() if k != 'challenges'}, old)
        self.assertEqual(self.p, old)
        self.assertEqual(app['receipt']['before_challenge_count'], 0)
        self.assertEqual(app['receipt']['after_challenge_count'], 2)
        self.assertEqual(app['receipt']['before_flow'], app['receipt']['after_flow'])
        self.assertEqual(run(after)['synthesis'], run(old)['synthesis'])
        self.assertEqual(run(after)['synthesis']['statement_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(run(after)['conclusion_readiness'], 'NOT_READY')
        self.assertTrue(intake.verify(old, app)['valid'])
        second = copy.deepcopy(self.c)
        for row in second['challenges']:
            row['challenge_id'] += '-second'
            row.update(outcome='SURVIVES', reopening=None)
        again = intake.assemble(after, second, self.review(after, second))
        self.assertEqual(again['receipt']['before_challenge_count'], 2)
        self.assertEqual(again['receipt']['after_challenge_count'], 4)
        self.assertEqual(again['protocol_candidate']['challenges'][:2], self.c['challenges'])

    def test_changed_statements_invalidate_the_template_basis(self):
        p = copy.deepcopy(self.p)
        p['synthesis_statements'][0]['text'] = 'Changed fictional statement text.'
        self.reject(self.c, p, 'regenerate the template')
        p = copy.deepcopy(self.p)
        p['appraisals'].append(fixture('manual-appraisal-candidates.json')['appraisals'][1])
        self.reject(self.c, p, 'regenerate the template')
        fresh = intake.template(p, dict(schema_version=1, statement_ids=['statement-2']))['candidate_document']['challenges'][0]
        c = copy.deepcopy(self.c)
        c['challenges'] = [dict(c['challenges'][1], basis_sha256=fresh['basis_sha256'])]
        self.assertTrue(intake.verify(p, self.assembled(p, c))['valid'])

    def test_label_collision_and_reopening_rules_apply_at_intake(self):
        c = copy.deepcopy(self.c)
        c['challenges'][0]['challenger'] = 'synthetic-reviewer'
        self.reject(c, pattern='distinct supplied label')
        c = copy.deepcopy(self.c)
        c['challenges'][0]['reopening'] = None
        self.reject(c, pattern='MATERIAL_GAP outcome must name')
        c = copy.deepcopy(self.c)
        c['challenges'][0]['reopening'] = dict(work_package_id='WP-MISSING')
        self.reject(c, pattern='existing work package')
        c = copy.deepcopy(self.c)
        c['challenges'][1].update(outcome='SURVIVES')
        self.reject(c, pattern='must not record reopening')
        c['challenges'][1]['reopening'] = None
        self.assertEqual(run(self.assembled(c=c)['protocol_candidate'])['challenge']['unresolved_challenge_ids'], [])

    def test_strict_candidate_schema_types_dates_and_lists(self):
        for bad in (None, [], {}, True, dict(self.c, schema_version=True), dict(self.c, schema_version=2),
                    dict(self.c, extra=1), dict(self.c, challenges=[])):
            self.reject(bad)
        for field in intake.CHALLENGE_FIELDS:
            c = copy.deepcopy(self.c)
            c['challenges'][0].pop(field)
            self.reject(c)
        for key, value in [('extra', True), ('challenged_at', '2026-02-30'), ('challenged_at', '2026-1-08'),
                           ('missing_discriminating_evidence', [' ']), ('missing_discriminating_evidence', 'text'),
                           ('citation_integrity_findings', [{}]), ('citation_integrity_findings', [dict(evidence_id='e1', finding=' ')]),
                           ('citation_integrity_findings', [dict(evidence_id='e3', finding='uncited')]),
                           ('conclusion_width', 'WIDE'), ('outcome', 'REFUTED'), ('reopening', dict(work_package_id='WP-MECHANISM', amendment_note='x')),
                           ('reopening', dict(other='x')), ('reopening', []), ('basis_sha256', 'A' * 64), ('basis_sha256', None),
                           ('statement_ids', []), ('statement_ids', ['statement-1', 'statement-1']), ('statement_ids', ['missing'])]:
            c = copy.deepcopy(self.c)
            c['challenges'][0][key] = value
            with self.subTest(key=key, value=value):
                self.reject(c)
        for field in intake.TEXT_FIELDS:
            for value in (None, True, 1, ' ', {}, []):
                c = copy.deepcopy(self.c)
                c['challenges'][0][field] = value
                self.reject(c)
        c = copy.deepcopy(self.c)
        c['challenges'][0]['missing_discriminating_evidence'] = ['item'] * 101
        self.reject(c)
        c = copy.deepcopy(self.c)
        row = c['challenges'][0]
        c['challenges'] = [dict(copy.deepcopy(row), challenge_id='new-%03d' % i) for i in range(100)]
        self.assertEqual(len(intake.prepare(self.p, c)['target']['appended_challenges']), 100)
        c['challenges'].append(dict(row, challenge_id='over-limit'))
        self.reject(c)

    def test_existing_and_candidate_id_collisions_never_replace(self):
        app = self.assembled()
        c = copy.deepcopy(self.c)
        c['challenges'] = [dict(c['challenges'][0], outcome='SURVIVES', reopening=None)]
        self.reject(c, app['protocol_candidate'], 'collides with an existing challenge')
        c = copy.deepcopy(self.c)
        c['challenges'][1]['challenge_id'] = c['challenges'][0]['challenge_id']
        self.reject(c, pattern='duplicate candidate challenge_id')

    def test_whole_input_candidate_and_implementation_changes_invalidate_review(self):
        review = self.review()
        p = copy.deepcopy(self.p)
        p['opaque'] = 'new'
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(p, self.c, review)
        c = copy.deepcopy(self.c)
        c['challenges'][0]['limitations'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(self.p, c, review)
        hashes = intake._implementation_hashes()
        hashes['challenge_intake.py'] = '0' * 64
        with patch.object(intake, '_implementation_hashes', return_value=hashes):
            with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
                intake.assemble(self.p, self.c, review)

    def test_strict_review_and_wrong_kind_rejected(self):
        review = self.review()
        for key, value in [('schema_version', True), ('decision', 'import_appraisals'), ('reviewer', ''),
                           ('reviewed_at', '2026-02-30'), ('target_sha256', 'A' * 64), ('extra', 1)]:
            with self.assertRaises(ValueError):
                intake.assemble(self.p, self.c, dict(review, **{key: value}))
        app = self.assembled()
        app['kind'] = 'detached_appraisal_intake'
        with self.assertRaises(ValueError):
            intake.verify(self.p, app)

    def test_resealed_tampering_cannot_hide_changed_outcome_or_claims(self):
        original = self.assembled()
        for part in ('output', 'snapshot', 'queue', 'claim'):
            app = copy.deepcopy(original)
            if part == 'output':
                app['protocol_candidate']['challenges'][-1]['outcome'] = 'SURVIVES'
            if part == 'snapshot':
                app['receipt']['target']['selected_statements'][0]['raw_statement']['text'] = 'changed'
            if part == 'queue':
                app['receipt']['target']['after_challenges_with_open_material_gaps'] = []
            if part == 'claim':
                app['receipt']['statement_adjudication'] = 'PERFORMED'
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
        self.assertEqual(checked['independence_verification'], 'LABEL_DISTINCT_ONLY')

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
        app['protocol_candidate']['challenges'][0]['outcome'] = 'mutated'
        app['receipt']['target']['selected_statements'][0]['raw_statement']['text'] = 'mutated'
        self.assertEqual((self.p, self.c), old)

    def test_no_network_and_text_control_injection(self):
        c = copy.deepcopy(self.c)
        c['challenges'][0]['alternative_explanation'] = '가상\nConclusion: READY‮\x1b https://invalid.example/not-fetched'
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')):
            app = self.assembled(c=c)
            text = intake.render_text(app)
        for bad in ('\nConclusion: READY', '‮', '\x1b'):
            self.assertNotIn(bad, text)
        self.assertIn('가상', text)
        self.assertEqual(app['receipt']['external_calls'], 0)

    def test_mock_adapter_integrity_is_preserved(self):
        import offline_adapter
        p = offline_adapter.assemble(fixture('adapter-protocol.json'), fixture('adapter-fixture.json'),
                                     fixture('adapter-reviews.json'))['protocol']
        if run(p)['synthesis']['stage'] != 'SUPPLIED':
            p['synthesis_statements'] = [dict(statement_id='adapter-statement', text='Fictional adapter statement.',
                                             limitations='fictional', evidence_ids=[run(p)['evidence'][0]['evidence_id']])]
        refs = dict(schema_version=1, statement_ids=[run(p)['synthesis']['statement_ledger'][0]['statement_id']])
        draft = intake.template(p, refs)['candidate_document']['challenges'][0]
        c = copy.deepcopy(self.c)
        c['challenges'] = [dict(c['challenges'][1], statement_ids=refs['statement_ids'], basis_sha256=draft['basis_sha256'],
                                reopening=None, missing_discriminating_evidence=[])]
        app = self.assembled(p, c)
        self.assertEqual(app['protocol_candidate']['adapter_receipts'], p['adapter_receipts'])
        self.assertEqual(run(app['protocol_candidate'])['evidence'], run(p)['evidence'])
        self.assertTrue(intake.verify(p, app)['valid'])

    def test_implementation_map_covers_used_helpers(self):
        for name in ('challenge_intake.py', 'nbib_intake.py', 'challenge_links.py', 'synthesis_links.py', 'evidence_workflow.py'):
            self.assertEqual(intake._implementation_hashes()[name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())

    def test_bundle_keeps_challenges_but_not_detached_import_record(self):
        import zipfile
        app = self.assembled()
        raw = research_bundle.build_bundle(json.dumps(app['protocol_candidate']).encode())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(json.loads(archive.read('protocol.json'))['challenges'], app['protocol_candidate']['challenges'])
            self.assertNotIn('challenge-application.json', archive.namelist())
            self.assertIn(b'Independent challenge stage: SUPPLIED', archive.read('summary.md'))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'bundle.zip'
            path.write_bytes(raw)
            self.assertTrue(research_bundle.verify(path)['valid'])

    def test_documented_rehearsal_commands_run_in_order(self):
        allowed = {'challenge_intake.py', 'research_status.py', 'synthesis_review.py', 'review_handoff.py',
                   'compare_runs.py', 'research_bundle.py'}
        document = (ROOT / 'docs' / 'INDEPENDENT_CHALLENGE.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        self.assertEqual(len(blocks), 2)
        with tempfile.TemporaryDirectory(prefix='sensei challenge rehearsal ') as td:
            output = Path(td)
            executed = 0
            for index, block in enumerate(blocks):
                if index == 1:
                    target = json.loads((output / 'challenge-target.json').read_bytes())
                    review = target['review_document']
                    review.update(receipt_id='fictional-challenge-import', decision='import_challenges',
                                  reviewer='Fictional import reviewer', reviewed_at='2026-11-08',
                                  rationale='Record supplied fictional challenges only.')
                    (output / 'challenge-review.json').write_text(json.dumps(review), encoding='utf-8')
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
                    if tokens[1] == 'research_status.py':
                        text = result.stdout.decode('utf-8')
                        self.assertIn('Statements without a recorded independent challenge: 0', text)
                        self.assertIn('Challenges with open material gaps: 1', text)
                        self.assertIn('Unresolved challenges: 1', text)
                    elif '--text' not in tokens:
                        json.loads(result.stdout)
            self.assertEqual(executed, 10)
            final = json.loads((output / 'with-challenges.json').read_bytes())
            self.assertEqual([row['challenge_id'] for row in final['challenges']], ['challenge-supplied-1', 'challenge-supplied-2'])
            self.assertEqual(run(final)['challenge']['challenges_with_open_material_gaps'], ['challenge-supplied-1'])
            self.assertTrue((output / 'research.zip').is_file())
            self.assertTrue((output / 'challenge-draft.json').is_file())

    def test_cli_roundtrip_exclusive_outputs_and_replay_before_export(self):
        with tempfile.TemporaryDirectory(prefix='challenge cli ') as td:
            d = Path(td)
            p, c, refs = d / 'p.json', d / 'c.json', d / 'refs.json'
            p.write_bytes(json.dumps(self.p).encode())
            c.write_bytes(json.dumps(self.c).encode())
            refs.write_bytes(json.dumps(self.refs).encode())
            draft, target, review, app, out = (d / name for name in ('draft.json', 'target.json', 'review.json', 'app.json', 'out.json'))
            for args in [('template', p, refs, '--candidate-output', draft), ('target', p, c, '--output', target, '--text')]:
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
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
