"""Synthetic conclusion-readiness gate regressions; no sufficiency or readiness judgement is tested or implied."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from compare_runs import changed_fields, compare_protocols
from evidence_workflow import run
from json_io import canonical_json_bytes
from readiness_review import render_text as render_review, review
from research_status import render_text, status
import research_bundle
from review_handoff import handoff
from synthesis_review import render_text as render_snapshot, snapshot

ROOT = Path(__file__).resolve().parents[1]
GATE_IDS = ['search_plan_complete', 'searches_complete', 'screening_complete', 'reports_resolved',
            'extraction_recorded', 'cited_results_appraised', 'statements_reviewed_current', 'results_cited',
            'challenges_recorded', 'challenges_resolved', 'contexts_reviewed', 'work_complete']


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


class ReadinessLinkTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('synthesis-review.json')
        self.rows = fixture('manual-readiness-candidates.json')['readiness_assertions']
        self.q = copy.deepcopy(self.p)
        self.q['readiness_assertions'] = copy.deepcopy(self.rows)

    def reject(self, protocol, pattern=None):
        if pattern is None:
            with self.assertRaises((ValueError, TypeError)):
                run(protocol)
        else:
            with self.assertRaisesRegex(ValueError, pattern):
                run(protocol)

    def gates(self, protocol):
        return {row['gate_id']: row for row in run(protocol)['readiness']['gate_ledger']}

    def test_gate_ledger_on_synthesis_review_without_challenges(self):
        result = run(self.p)['readiness']
        self.assertEqual([row['gate_id'] for row in result['gate_ledger']], GATE_IDS)
        gates = {row['gate_id']: row for row in result['gate_ledger']}
        expected = {
            'search_plan_complete': ('OPEN', ['search-secondary']),
            'searches_complete': ('CLOSED', []),
            'screening_complete': ('OPEN', ['r8']),
            'reports_resolved': ('OPEN', ['r7', 'report-2', 'report-3', 'report-4', 'report-5']),
            'extraction_recorded': ('NOT_APPLICABLE', []),
            'cited_results_appraised': ('OPEN', ['e2']),
            'statements_reviewed_current': ('OPEN', ['statement-2']),
            'results_cited': ('OPEN', ['e3']),
            'challenges_recorded': ('OPEN', ['statement-1', 'statement-2']),
            'challenges_resolved': ('OPEN', []),
            'contexts_reviewed': ('OPEN', ['ctx-guideline']),
            'work_complete': ('OPEN', ['WP-MECHANISM', 'WP-TRANSLATION']),
        }
        for gate_id, (state, items) in expected.items():
            with self.subTest(gate=gate_id):
                self.assertEqual((gates[gate_id]['status'], gates[gate_id]['open_items']), (state, items))
                self.assertEqual(set(gates[gate_id]), {'gate_id', 'status', 'open_items', 'basis'})
                self.assertTrue(gates[gate_id]['basis'].endswith('.'))
        self.assertEqual(result['open_gate_ids'], [gate for gate in GATE_IDS if expected[gate][0] == 'OPEN'])
        self.assertEqual(result['closed_gate_ids'], ['searches_complete'])
        self.assertEqual(result['not_applicable_gate_ids'], ['extraction_recorded'])
        self.assertEqual(result['gates_sha256'], hashlib.sha256(canonical_json_bytes(result['gate_ledger'])).hexdigest())
        self.assertEqual(result['mechanical_conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['stage'], 'NOT_SUPPLIED')
        self.assertEqual(result['assertion_ledger'], [])
        self.assertIsNone(result['current_assertion_ids'])
        self.assertIsNone(result['stale_assertion_ids'])
        self.assertEqual(run(self.p)['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(run(self.p)['census_claim'], 'NOT_ESTABLISHED')

    def test_recorded_challenges_close_recording_and_open_resolution(self):
        q = copy.deepcopy(self.p)
        q['challenges'] = fixture('manual-challenge-candidates.json')['challenges']
        gates = self.gates(q)
        self.assertEqual((gates['challenges_recorded']['status'], gates['challenges_recorded']['open_items']), ('CLOSED', []))
        self.assertEqual(gates['challenges_resolved']['open_items'], ['challenge-supplied-1', 'challenge-supplied-2'])
        self.assertNotEqual(run(q)['readiness']['gates_sha256'], run(self.p)['readiness']['gates_sha256'])
        for row in q['challenges']:
            row.update(outcome='SURVIVES', reopening=None)
        self.assertEqual(self.gates(q)['challenges_resolved']['status'], 'CLOSED')
        q['synthesis_statements'][0]['text'] = 'Changed fictional statement text.'
        gates = self.gates(q)
        self.assertEqual(gates['challenges_resolved']['open_items'], ['challenge-supplied-1'])
        self.assertEqual(gates['statements_reviewed_current']['open_items'], ['statement-1', 'statement-2'])
        self.assertEqual(run(q)['conclusion_readiness'], 'NOT_READY')

    def test_fixture_assertion_binds_the_current_gates(self):
        current = run(self.p)['readiness']
        self.assertEqual(self.rows[0]['gates_sha256'], current['gates_sha256'])
        result = run(self.q)['readiness']
        self.assertEqual(result['stage'], 'SUPPLIED')
        row = result['assertion_ledger'][0]
        self.assertEqual(row['source_match_status'], 'CURRENT_GATES')
        self.assertEqual(row['current_gates_sha256'], current['gates_sha256'])
        self.assertEqual(row['open_gates_at_assertion'], current['open_gate_ids'])
        self.assertEqual(row['open_gates_scope'], 'RECOMPUTED_FROM_CURRENT_LEDGER')
        self.assertEqual(row['reopening_status'], 'OPEN_WORK')
        self.assertFalse(row['ready_with_open_gates'])
        self.assertEqual(row['assessment'], 'NOT_PERFORMED')
        self.assertEqual(row['assertion_scope'], 'SUPPLIED_HUMAN_ASSERTION_BOUND_TO_GATE_SNAPSHOT')
        self.assertEqual(result['current_assertion_ids'], ['readiness-supplied-1'])
        self.assertEqual(result['stale_assertion_ids'], [])
        self.assertEqual(result['gate_ledger'], current['gate_ledger'])
        self.assertEqual(result['gates_sha256'], current['gates_sha256'])
        for key in ('synthesis', 'challenge', 'planning', 'work_packages', 'flow'):
            self.assertEqual(run(self.q)[key], run(self.p)[key])
        self.assertEqual(run(self.q)['conclusion_readiness'], 'NOT_READY')

    def test_gate_changes_make_assertions_stale_and_unrelated_changes_do_not(self):
        q = copy.deepcopy(self.q)
        q['synthesis_statements'][0]['text'] = 'Changed fictional statement text.'
        result = run(q)['readiness']
        self.assertEqual(result['stale_assertion_ids'], ['readiness-supplied-1'])
        self.assertEqual(result['current_assertion_ids'], [])
        row = result['assertion_ledger'][0]
        self.assertEqual(row['source_match_status'], 'STALE_GATES')
        self.assertIsNone(row['open_gates_at_assertion'])
        self.assertEqual(row['open_gates_scope'], 'UNKNOWN_STALE_GATES')
        self.assertIsNone(row['ready_with_open_gates'])
        q = copy.deepcopy(self.q)
        q['appraisals'].append(fixture('manual-appraisal-candidates.json')['appraisals'][1])
        self.assertEqual(self.gates(q)['cited_results_appraised']['status'], 'CLOSED')
        self.assertEqual(run(q)['readiness']['stale_assertion_ids'], ['readiness-supplied-1'])
        q = copy.deepcopy(self.q)
        q['screening'].append(dict(record_id='r8', decision='exclude', reason='Synthetic exclusion'))
        self.assertEqual(self.gates(q)['screening_complete']['status'], 'CLOSED')
        self.assertEqual(run(q)['readiness']['stale_assertion_ids'], ['readiness-supplied-1'])
        q = copy.deepcopy(self.q)
        q['version'] = 'different supplied version'
        q['synthesis_statements'][1]['limitations'] = 'Changed limitations of the pending statement.'
        self.assertEqual(run(q)['readiness']['current_assertion_ids'], ['readiness-supplied-1'])

    def test_missing_stages_stay_open_or_not_applicable_as_documented(self):
        demo = fixture('review-demo.json')
        gates = self.gates(demo)
        for gate_id in ('cited_results_appraised', 'statements_reviewed_current', 'results_cited',
                        'challenges_recorded', 'challenges_resolved'):
            with self.subTest(gate=gate_id):
                self.assertEqual((gates[gate_id]['status'], gates[gate_id]['open_items']), ('OPEN', []))
                self.assertIn('supplied', gates[gate_id]['basis'])
        self.assertEqual(gates['extraction_recorded']['status'], 'NOT_APPLICABLE')
        self.assertEqual(gates['reports_resolved']['status'], 'CLOSED')
        self.assertEqual(gates['search_plan_complete']['open_items'], ['search-secondary'])
        demo.pop('reports')
        demo.pop('search_plan')
        gates = self.gates(demo)
        self.assertEqual(gates['search_plan_complete']['status'], 'NOT_APPLICABLE')
        self.assertEqual(gates['reports_resolved']['status'], 'NOT_APPLICABLE')
        self.assertEqual((gates['extraction_recorded']['status'], gates['extraction_recorded']['open_items']), ('CLOSED', []))
        for key in ('evidence', 'gaps', 'contexts', 'appraisals'):
            demo[key] = []
        gates = self.gates(demo)
        self.assertEqual(gates['extraction_recorded']['open_items'], ['r1'])
        self.assertEqual(gates['work_complete']['status'], 'CLOSED')
        self.assertEqual(gates['contexts_reviewed']['status'], 'CLOSED')
        demo['synthesis_statements'] = []
        demo['challenges'] = []
        demo['evidence'] = []
        result = run(demo)['readiness']
        gates = {row['gate_id']: row for row in result['gate_ledger']}
        for gate_id in ('cited_results_appraised', 'statements_reviewed_current', 'results_cited',
                        'challenges_recorded', 'challenges_resolved'):
            self.assertEqual(gates[gate_id]['status'], 'CLOSED')
        self.assertEqual(result['open_gate_ids'], ['extraction_recorded'])
        self.assertEqual(result['mechanical_conclusion_readiness'], 'NOT_READY')
        self.assertEqual(run(demo)['conclusion_readiness'], 'NOT_READY')

    def test_search_gate_uses_authoritative_index_pointers(self):
        q = copy.deepcopy(self.p)
        q['searches'][0]['has_more'] = True
        gates = self.gates(q)
        self.assertEqual(gates['searches_complete']['open_items'], ['/searches/0'])
        self.assertEqual(gates['search_plan_complete']['open_items'], ['search-primary', 'search-secondary'])
        q.pop('search_plan')
        q['searches'][0].pop('search_id')
        self.assertEqual(self.gates(q)['searches_complete']['open_items'], ['/searches/0'])

    def test_ready_assertion_is_permitted_with_open_gates_and_recorded(self):
        q = copy.deepcopy(self.q)
        q['readiness_assertions'][0].update(evidence_sufficiency='UNASSESSED', conclusion_readiness='READY', reopening=None)
        result = run(q)
        row = result['readiness']['assertion_ledger'][0]
        self.assertTrue(row['ready_with_open_gates'])
        self.assertEqual(row['open_gates_at_assertion'], run(self.p)['readiness']['open_gate_ids'])
        self.assertIsNone(row['reopening_status'])
        self.assertEqual(row['conclusion_readiness'], 'READY')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['readiness']['mechanical_conclusion_readiness'], 'NOT_READY')
        for field in ('rationale', 'scope_statement'):
            bad = copy.deepcopy(q)
            bad['readiness_assertions'][0][field] = ' '
            self.reject(bad, 'requires ' + field)
        q['readiness_assertions'][0].update(evidence_sufficiency='INSUFFICIENT')
        self.assertEqual(run(q)['readiness']['current_assertion_ids'], ['readiness-supplied-1'])
        q['readiness_assertions'][0]['reopening'] = dict(work_package_id='WP-MECHANISM')
        self.assertEqual(run(q)['readiness']['assertion_ledger'][0]['reopening_status'], 'OPEN_WORK')

    def test_reopening_rules(self):
        q = copy.deepcopy(self.q)
        q['readiness_assertions'][0]['reopening'] = None
        self.reject(q, 'NOT_READY assertion with INSUFFICIENT evidence must name')
        q['readiness_assertions'][0]['evidence_sufficiency'] = 'UNASSESSED'
        self.assertIsNone(run(q)['readiness']['assertion_ledger'][0]['reopening_status'])
        q = copy.deepcopy(self.q)
        q['readiness_assertions'][0]['reopening'] = dict(amendment_note='Fictional amendment: reopen the mechanism review.')
        self.assertEqual(run(q)['readiness']['assertion_ledger'][0]['reopening_status'], 'OPEN_AMENDMENT')
        q = copy.deepcopy(self.q)
        q['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://artifact', acceptance_verified=True)
        row = run(q)['readiness']['assertion_ledger'][0]
        self.assertEqual(row['reopening_status'], 'RECORDED_COMPLETE')
        self.assertEqual(row['source_match_status'], 'STALE_GATES')
        for bad in (dict(work_package_id='WP-MISSING'), dict(work_package_id='WP-MECHANISM', amendment_note='x'),
                    dict(amendment_note=' '), dict(other='x'), [], 'WP-MECHANISM'):
            q = copy.deepcopy(self.q)
            q['readiness_assertions'][0]['reopening'] = bad
            with self.subTest(bad=bad):
                self.reject(q)

    def test_strict_fields_enums_dates_and_ids(self):
        cases = [
            ('extra', True, 'unknown fields'), ('evidence_sufficiency', 'ENOUGH', 'evidence_sufficiency'),
            ('evidence_sufficiency', None, 'evidence_sufficiency'), ('conclusion_readiness', 'MAYBE', 'conclusion_readiness'),
            ('conclusion_readiness', True, 'conclusion_readiness'), ('assessed_at', '2026-02-30', None),
            ('assessed_at', '2026-1-08', None), ('gates_sha256', 'A' * 64, 'lowercase SHA-256'),
            ('gates_sha256', 'abc', 'lowercase SHA-256'), ('gates_sha256', None, 'lowercase SHA-256'),
            ('assessor', ' ', 'requires assessor'), ('scope_statement', None, 'requires scope_statement'),
            ('rationale', '', 'requires rationale'), ('limitations', 1, 'requires limitations'),
            ('assertion_id', '', 'requires assertion_id'),
        ]
        for key, value, pattern in cases:
            q = copy.deepcopy(self.q)
            q['readiness_assertions'][0][key] = value
            with self.subTest(key=key, value=value):
                self.reject(q, pattern)
        q = copy.deepcopy(self.q)
        q['readiness_assertions'].append(copy.deepcopy(q['readiness_assertions'][0]))
        self.reject(q, 'duplicate readiness assertion ID')
        q = copy.deepcopy(self.q)
        q['readiness_assertions'] = {}
        self.reject(q, 'readiness_assertions must be a list')
        q = copy.deepcopy(self.q)
        q['readiness_assertions'] = [None]
        self.reject(q, 'readiness assertion must be an object')
        q = copy.deepcopy(self.q)
        row = q['readiness_assertions'][0]
        q['readiness_assertions'] = [dict(copy.deepcopy(row), assertion_id='assertion-%03d' % i) for i in range(100)]
        self.assertEqual(len(run(q)['readiness']['assertion_ledger']), 100)
        q['readiness_assertions'].append(dict(copy.deepcopy(row), assertion_id='over-limit'))
        self.reject(q, 'at most 100')

    def test_status_handoff_snapshot_bundle_and_comparison_surface_readiness(self):
        state = status(self.q)
        self.assertEqual(set(state['queues']), set(status(self.p)['queues']))
        self.assertEqual(state['readiness']['open_gate_ids'], run(self.p)['readiness']['open_gate_ids'])
        self.assertEqual(state['readiness']['counts'], dict(open_gates=10, closed_gates=1, not_applicable_gates=1,
                                                            supplied_assertions=1, current_assertions=1, stale_assertions=0))
        self.assertEqual(state['readiness']['current_assertion_ids'], ['readiness-supplied-1'])
        self.assertEqual(state['readiness']['mechanical_conclusion_readiness'], 'NOT_READY')
        self.assertEqual(state['conclusion_readiness'], 'NOT_READY')
        text = render_text(state)
        self.assertIn('Open readiness gates: 10', text)
        self.assertIn('Supplied readiness assertions: current 1, stale 0', text)
        self.assertIn('Conclusion: NOT_READY', text)
        baseline = status(self.p)
        self.assertIsNone(baseline['readiness']['counts']['supplied_assertions'])
        self.assertIn('Supplied readiness assertions: not supplied', render_text(baseline))
        result = handoff(self.q)
        views = {view['script']: view for view in result['detailed_views']}
        self.assertEqual(views['readiness_review.py']['arguments'], ['PROTOCOL.json', '--text'])
        self.assertEqual(result['engine_sha256']['readiness_review.py'],
                         hashlib.sha256((ROOT / 'readiness_review.py').read_bytes()).hexdigest())
        routes = [route['workflow_id'] for route in result['supplied_input_workflows']]
        self.assertEqual(routes.index('readiness_intake'), routes.index('challenge_intake') + 1)
        route = next(r for r in result['supplied_input_workflows'] if r['workflow_id'] == 'readiness_intake')
        self.assertEqual(route['guide_paths'], ['docs/CONCLUSION_READINESS.md'])
        self.assertEqual(route['entrypoints'], [dict(script='readiness_intake.py', arguments=[c, '--help'])
                                               for c in ('template', 'target', 'assemble', 'verify')])
        for phrase in ('Closed gates are bookkeeping, not sufficiency', 'READY assertion may be recorded while gates are open',
                       'mechanical conclusion readiness stays NOT_READY'):
            self.assertIn(phrase, route['boundary'])
        self.assertEqual({step['queue'] for step in result['manual_review_steps']}, set(state['queues']))
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        view = snapshot(self.q)
        self.assertEqual(view['readiness']['gates_sha256'], run(self.q)['readiness']['gates_sha256'])
        self.assertEqual([row['assertion_id'] for row in view['readiness']['assertion_ledger']], ['readiness-supplied-1'])
        self.assertEqual(view['conclusion_readiness'], 'NOT_READY')
        self.assertIn('Mechanical readiness gates and supplied readiness assertions', render_snapshot(view))
        raw = research_bundle.build_bundle(json.dumps(self.q).encode())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            summary = archive.read('summary.md')
            self.assertIn(b'Open readiness gates: 10', summary)
            self.assertIn(b'Supplied readiness assertions: current 1, stale 0', summary)
            self.assertIn(b'Conclusion: NOT_READY', summary)
            self.assertEqual(json.loads(archive.read('protocol.json'))['readiness_assertions'], self.q['readiness_assertions'])
            self.assertEqual(json.loads(archive.read('research.json'))['readiness']['current_assertion_ids'], ['readiness-supplied-1'])
        with zipfile.ZipFile(io.BytesIO(research_bundle.build_bundle(json.dumps(self.p).encode()))) as archive:
            self.assertIn(b'Supplied readiness assertions: not supplied', archive.read('summary.md'))
        comparison = compare_protocols(self.p, self.q)
        self.assertEqual(comparison['entity_changes']['readiness_assertions']['added_ids'], ['readiness-supplied-1'])
        self.assertIn('readiness_assertions', comparison['changed_protocol_fields'])
        self.assertEqual(comparison['conclusion_readiness'], 'NOT_READY')
        self.assertIn('readiness_links.py', research_bundle.engine_hashes())
        after = copy.deepcopy(self.q)
        after['screening'].append(dict(record_id='r8', decision='exclude', reason='Synthetic exclusion'))
        after['version'] = 'synthetic-synthesis-v2'
        note = dict(schema_version=1, before_sha256=hashlib.sha256(canonical_json_bytes(self.q)).hexdigest(),
                    after_sha256=hashlib.sha256(canonical_json_bytes(after)).hexdigest(),
                    from_version=self.q['version'], to_version=after['version'], reason='Fictional supplied reason',
                    authored_by='fictional', authored_at='2026-11-08', scope_fields=changed_fields(self.q, after))
        amended = compare_protocols(self.q, after, note)
        transitions = amended['amendment_review']['observed_state_transitions']['readiness']
        self.assertEqual(transitions, [dict(id='screening_complete', before=dict(status='OPEN'), after=dict(status='CLOSED'))])
        changed = amended['entity_changes']['readiness_assertions']['changed']
        self.assertEqual(changed[0]['id'], 'readiness-supplied-1')
        self.assertIn('source_match_status', changed[0]['fields'])
        self.assertEqual(amended['conclusion_readiness'], 'NOT_READY')

    def test_readiness_review_view_and_text_controls(self):
        q = copy.deepcopy(self.q)
        q['readiness_assertions'][0]['rationale'] = '가상\nConclusion: READY‮\x1b'
        q['readiness_assertions'][0].update(conclusion_readiness='READY', evidence_sufficiency='UNASSESSED', reopening=None)
        original = copy.deepcopy(q)
        result = review(q)
        self.assertEqual(q, original)
        self.assertEqual(result, review(q))
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['mechanical_conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['assertion_ledger'][0]['conclusion_readiness'], 'READY')
        self.assertTrue(result['assertion_ledger'][0]['ready_with_open_gates'])
        self.assertEqual(result['open_items']['screening_complete'], ['r8'])
        self.assertEqual(result['gates_sha256'], run(q)['readiness']['gates_sha256'])
        self.assertEqual(result['protocol_sha256'], status(q)['protocol_sha256'])
        self.assertIn('readiness_review.py', result['engine_sha256'])
        self.assertIn('readiness_links.py', result['engine_sha256'])
        for text in (render_review(result), render_text(status(q)), render_snapshot(snapshot(q))):
            self.assertNotIn('\nConclusion: READY', text)
            self.assertNotIn('‮', text)
            self.assertNotIn('\x1b', text)
            self.assertIn('Conclusion: NOT_READY', text)
        rendered = render_review(result)
        self.assertIn('가상', rendered)
        self.assertIn('Mechanical conclusion readiness: NOT_READY', rendered)
        self.assertIn('Gate "screening_complete": OPEN; open items: ["r8"]', rendered)

    def test_readiness_review_cli_json_text_and_strict_input(self):
        args = [sys.executable, str(ROOT / 'readiness_review.py'), str(ROOT / 'examples' / 'synthesis-review.json')]
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)['open_gate_ids']), 10)
        result = subprocess.run(args + ['--text'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Open gates: ', result.stdout)
        self.assertIn('Conclusion: NOT_READY', result.stdout)
        with tempfile.TemporaryDirectory(prefix='sensei readiness review ') as folder:
            path = Path(folder) / 'bad.json'
            path.write_text('{"question":1,"question":2}', encoding='utf-8')
            failed = subprocess.run([sys.executable, str(ROOT / 'readiness_review.py'), str(path)], cwd=folder,
                                    capture_output=True, text=True, timeout=60)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(failed.stdout, '')
            self.assertNotIn('Traceback', failed.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_mock_adapter_context_allows_readiness_assertions(self):
        import offline_adapter
        p = offline_adapter.assemble(fixture('adapter-protocol.json'), fixture('adapter-fixture.json'),
                                     fixture('adapter-reviews.json'))['protocol']
        before = run(p)
        p['readiness_assertions'] = [dict(self.rows[0], gates_sha256=before['readiness']['gates_sha256'],
                                          evidence_sufficiency='UNASSESSED', reopening=None)]
        after = run(p)
        self.assertEqual(after['evidence'], before['evidence'])
        self.assertEqual(after['readiness']['gate_ledger'], before['readiness']['gate_ledger'])
        self.assertEqual(after['readiness']['current_assertion_ids'], ['readiness-supplied-1'])
        self.assertEqual(after['conclusion_readiness'], 'NOT_READY')
        p['question'] = 'changed synthetic question'
        self.reject(p, 'context changed')


if __name__ == '__main__':
    unittest.main()
