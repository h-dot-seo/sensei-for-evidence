"""Synthetic independent-challenge engine regressions; no scientific adjudication is tested or implied."""
import copy
import io
import json
from pathlib import Path
import unittest
import zipfile

import challenge_links
from challenge_links import challenge_basis, link_challenges
from compare_runs import compare_protocols
from evidence_workflow import run
from research_status import render_text, status
import research_bundle
from review_handoff import handoff
from synthesis_review import snapshot

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


class ChallengeLinkTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('synthesis-review.json')
        self.rows = fixture('manual-challenge-candidates.json')['challenges']
        self.q = copy.deepcopy(self.p)
        self.q['challenges'] = copy.deepcopy(self.rows)

    def reject(self, protocol, pattern=None):
        if pattern is None:
            with self.assertRaises((ValueError, TypeError)):
                run(protocol)
        else:
            with self.assertRaisesRegex(ValueError, pattern):
                run(protocol)

    def test_not_supplied_stage_keeps_statement_queue_and_null_challenge_queues(self):
        result = run(self.p)['challenge']
        self.assertEqual(result['stage'], 'NOT_SUPPLIED')
        self.assertEqual(result['challenge_ledger'], [])
        self.assertEqual(result['statements_without_challenge'], ['statement-1', 'statement-2'])
        for key in ('challenges_with_open_material_gaps', 'unresolved_challenge_ids', 'stale_challenge_ids', 'unbound_challenge_ids'):
            self.assertIsNone(result[key])
        counts = status(self.p)['counts']
        self.assertEqual(counts['statements_without_independent_challenge'], 2)
        self.assertIsNone(counts['unresolved_challenges'])
        self.assertIn('Statements without a recorded independent challenge: 2', render_text(status(self.p)))
        self.assertIn('Unresolved challenges: not supplied', render_text(status(self.p)))

    def test_statement_queue_is_null_without_synthesis_statements(self):
        p = fixture('review-demo.json')
        self.assertEqual(run(p)['synthesis']['stage'], 'NOT_SUPPLIED')
        self.assertIsNone(run(p)['challenge']['statements_without_challenge'])
        p['challenges'] = []
        result = run(p)['challenge']
        self.assertEqual(result['stage'], 'SUPPLIED')
        self.assertIsNone(result['statements_without_challenge'])
        self.assertEqual(result['challenges_with_open_material_gaps'], [])
        p['challenges'] = copy.deepcopy(self.rows[:1])
        self.reject(p, 'known synthesis statements')

    def test_fixture_bases_match_current_statement_bases(self):
        synthesis = run(self.p)['synthesis']
        for row in self.rows:
            self.assertEqual(row['basis_sha256'], challenge_basis(synthesis, row['statement_ids']))
        self.assertEqual(challenge_basis(synthesis, ['statement-2', 'statement-1']),
                         challenge_basis(synthesis, ['statement-1', 'statement-2']))
        with self.assertRaisesRegex(ValueError, 'unknown synthesis statements'):
            challenge_basis(synthesis, ['missing'])

    def test_supplied_rows_derive_bindings_queues_and_labels(self):
        result = run(self.q)['challenge']
        self.assertEqual(result['stage'], 'SUPPLIED')
        rows = {row['challenge_id']: row for row in result['challenge_ledger']}
        self.assertEqual(sorted(rows), ['challenge-supplied-1', 'challenge-supplied-2'])
        self.assertEqual({row['source_match_status'] for row in rows.values()}, {'CURRENT_SOURCE'})
        self.assertEqual(rows['challenge-supplied-1']['reopening_status'], 'OPEN_WORK')
        self.assertEqual(rows['challenge-supplied-2']['reopening_status'], 'OPEN_AMENDMENT')
        self.assertEqual(rows['challenge-supplied-1']['cited_evidence_ids'], ['e1'])
        self.assertEqual(rows['challenge-supplied-2']['cited_evidence_ids'], ['e2'])
        for row in rows.values():
            self.assertEqual(row['independence_verification'], 'LABEL_DISTINCT_ONLY')
            self.assertEqual(row['assessment'], 'NOT_PERFORMED')
        self.assertEqual(result['statements_without_challenge'], [])
        self.assertEqual(result['challenges_with_open_material_gaps'], ['challenge-supplied-1'])
        self.assertEqual(result['unresolved_challenge_ids'], ['challenge-supplied-2'])
        self.assertEqual(result['stale_challenge_ids'], [])
        self.assertEqual(result['unbound_challenge_ids'], [])
        self.assertEqual(result['statement_challenge_links'],
                         [dict(statement_id='statement-1', challenge_ids=['challenge-supplied-1']),
                          dict(statement_id='statement-2', challenge_ids=['challenge-supplied-2'])])
        self.assertEqual(run(self.q)['synthesis'], run(self.p)['synthesis'])
        self.assertEqual(run(self.q)['planning'], run(self.p)['planning'])
        self.assertEqual(run(self.q)['conclusion_readiness'], 'NOT_READY')

    def test_challenger_label_matching_any_recorded_label_is_rejected(self):
        for label in ('synthetic-reviewer',):
            q = copy.deepcopy(self.q)
            q['challenges'][0]['challenger'] = label
            self.reject(q, 'distinct supplied label')
        q = copy.deepcopy(self.q)
        q['synthesis_statements'][0]['evidence_positions'] = [dict(
            evidence_id='e1', claim_component='first recorded endpoint changed', aspect='observation',
            relation='supports', rationale='Fictional position.', source_locator='synthetic section 1',
            source_excerpt='synthetic excerpt', limitations='fictional', recorded_by='Fictional position recorder',
            recorded_at='2026-11-05')]
        q['synthesis_statements'][0]['review_status'] = 'pending'
        for key in ('reviewer', 'reviewed_at', 'basis_sha256'):
            q['synthesis_statements'][0].pop(key)
        synthesis = run(dict(q, challenges=[]))['synthesis']
        self.assertIn('Fictional position recorder', challenge_links.reviewer_labels(synthesis, ['statement-1']))
        q['challenges'][0]['basis_sha256'] = challenge_basis(synthesis, ['statement-1'])
        self.assertEqual(run(q)['challenge']['challenge_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        q['challenges'][0]['challenger'] = 'Fictional position recorder'
        self.reject(q, 'distinct supplied label')
        q['challenges'][0]['challenger'] = 'Fictional independent challenger'
        q['challenges'][1]['challenger'] = 'Fictional alternative assessor'
        q['appraisals'].append(dict(fixture('manual-appraisal-candidates.json')['appraisals'][1]))
        self.reject(q, 'distinct supplied label')

    def test_statement_evidence_or_appraisal_changes_make_bindings_stale(self):
        q = copy.deepcopy(self.q)
        q['synthesis_statements'][0]['text'] = 'Changed fictional statement text.'
        result = run(q)['challenge']
        self.assertEqual(result['stale_challenge_ids'], ['challenge-supplied-1'])
        self.assertEqual(result['challenge_ledger'][1]['source_match_status'], 'CURRENT_SOURCE')
        q = copy.deepcopy(self.q)
        q['appraisals'].append(fixture('manual-appraisal-candidates.json')['appraisals'][1])
        self.assertEqual(run(q)['challenge']['stale_challenge_ids'], ['challenge-supplied-2'])
        q = copy.deepcopy(self.q)
        q['challenges'][0].pop('basis_sha256')
        result = run(q)['challenge']
        self.assertEqual(result['unbound_challenge_ids'], ['challenge-supplied-1'])
        self.assertEqual(result['challenge_ledger'][0]['source_match_status'], 'UNBOUND_CHALLENGE')
        self.assertEqual(result['stale_challenge_ids'], [])

    def test_outcome_and_reopening_rules(self):
        q = copy.deepcopy(self.q)
        q['challenges'][0]['reopening'] = None
        self.reject(q, 'MATERIAL_GAP outcome must name')
        q = copy.deepcopy(self.q)
        q['challenges'][0].update(outcome='SURVIVES')
        self.reject(q, 'SURVIVES outcome must not record reopening')
        q['challenges'][0]['reopening'] = None
        self.assertEqual(run(q)['challenge']['challenges_with_open_material_gaps'], [])
        self.assertIsNone(run(q)['challenge']['challenge_ledger'][0]['reopening_status'])
        for bad in (dict(work_package_id='WP-MISSING'), dict(work_package_id='WP-MECHANISM', amendment_note='x'),
                    dict(amendment_note=' '), dict(other='x'), [], 'WP-MECHANISM'):
            q = copy.deepcopy(self.q)
            q['challenges'][0]['reopening'] = bad
            with self.subTest(bad=bad):
                self.reject(q)
        q = copy.deepcopy(self.q)
        q['challenges'][1]['reopening'] = None
        self.assertEqual(run(q)['challenge']['unresolved_challenge_ids'], ['challenge-supplied-2'])
        q = copy.deepcopy(self.q)
        q['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://artifact', acceptance_verified=True)
        result = run(q)['challenge']
        self.assertEqual(result['challenge_ledger'][0]['reopening_status'], 'RECORDED_COMPLETE')
        self.assertEqual(result['challenges_with_open_material_gaps'], [])

    def test_strict_fields_enums_dates_ids_and_findings(self):
        cases = [
            ('extra', True, None), ('conclusion_width', 'WIDE', 'conclusion_width'), ('outcome', 'REFUTED', 'outcome'),
            ('challenged_at', '2026-02-30', None), ('challenged_at', '2026-1-08', None),
            ('statement_ids', [], 'known synthesis statements'), ('statement_ids', ['statement-1', 'statement-1'], None),
            ('statement_ids', ['missing'], 'known synthesis statements'), ('statement_ids', 'statement-1', None),
            ('missing_discriminating_evidence', [' '], 'nonempty strings'), ('missing_discriminating_evidence', None, None),
            ('citation_integrity_findings', [dict(evidence_id='e3', finding='uncited')], 'cited by the challenged'),
            ('citation_integrity_findings', [dict(evidence_id='e1', finding='x', extra=1)], None),
            ('citation_integrity_findings', [dict(evidence_id='e1')], None), ('citation_integrity_findings', None, None),
            ('basis_sha256', 'A' * 64, 'lowercase SHA-256'), ('basis_sha256', 'abc', 'lowercase SHA-256'),
            ('challenger', ' ', 'requires challenger'), ('alternative_explanation', None, 'requires alternative_explanation'),
            ('independence_declaration', '', 'requires independence_declaration'), ('limitations', 1, 'requires limitations'),
        ]
        for key, value, pattern in cases:
            q = copy.deepcopy(self.q)
            q['challenges'][0][key] = value
            with self.subTest(key=key, value=value):
                self.reject(q, pattern)
        q = copy.deepcopy(self.q)
        q['challenges'][1]['challenge_id'] = q['challenges'][0]['challenge_id']
        self.reject(q, 'duplicate challenge ID')
        q = copy.deepcopy(self.q)
        q['challenges'] = {}
        self.reject(q, 'challenges must be a list')
        q = copy.deepcopy(self.q)
        q['challenges'] = [None]
        self.reject(q, 'challenge must be an object')
        q = copy.deepcopy(self.q)
        q['challenges'][0]['missing_discriminating_evidence'] = ['item'] * 101
        self.reject(q, 'at most 100')
        q = copy.deepcopy(self.q)
        q['challenges'][0]['citation_integrity_findings'] = [dict(evidence_id='e1', finding='x')] * 101
        self.reject(q, 'at most 100')

    def test_multi_statement_challenge_binds_the_set_and_cites_all_results(self):
        q = copy.deepcopy(self.q)
        row = q['challenges'][0]
        row.update(statement_ids=['statement-2', 'statement-1'], citation_integrity_findings=[
            dict(evidence_id='e1', finding='fictional'), dict(evidence_id='e2', finding='fictional')])
        row['basis_sha256'] = challenge_basis(run(self.p)['synthesis'], row['statement_ids'])
        result = run(q)['challenge']
        self.assertEqual(result['challenge_ledger'][0]['cited_evidence_ids'], ['e1', 'e2'])
        self.assertEqual(result['challenge_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(result['statement_challenge_links'][1]['challenge_ids'], ['challenge-supplied-1', 'challenge-supplied-2'])

    def test_status_handoff_snapshot_bundle_and_comparison_surface_challenges(self):
        state = status(self.q)
        self.assertEqual(state['queues']['challenges_with_open_material_gaps'], ['challenge-supplied-1'])
        self.assertEqual(state['queues']['unresolved_challenges'], ['challenge-supplied-2'])
        self.assertEqual(state['queues']['statements_without_independent_challenge'], [])
        text = render_text(state)
        self.assertIn('Challenges with open material gaps: 1', text)
        self.assertIn('Unresolved challenges: 1', text)
        steps = {step['queue']: step for step in handoff(self.q)['manual_review_steps']}
        self.assertEqual(steps['challenges_with_open_material_gaps']['matching_input_rows'], ['/challenges/0', '/gaps/0'])
        self.assertEqual(steps['unresolved_challenges']['matching_input_rows'], ['/challenges/1'])
        stale = copy.deepcopy(self.q)
        stale['synthesis_statements'][0]['text'] = 'Changed fictional statement text.'
        step = next(s for s in handoff(stale)['manual_review_steps'] if s['queue'] == 'stale_challenge_bindings')
        self.assertEqual(step['items'], ['challenge-supplied-1'])
        self.assertEqual(step['matching_input_rows'], ['/challenges/0', '/synthesis_statements/0'])
        self.assertEqual(steps['statements_without_independent_challenge']['state'], 'NO_RECORDED_ITEMS')
        partial = copy.deepcopy(self.q)
        partial['challenges'] = partial['challenges'][:1]
        step = next(s for s in handoff(partial)['manual_review_steps'] if s['queue'] == 'statements_without_independent_challenge')
        self.assertEqual(step['items'], ['statement-2'])
        self.assertEqual(step['matching_input_rows'], ['/synthesis_statements/1'])
        view = snapshot(self.q)
        self.assertEqual(view['challenge_stage'], 'SUPPLIED')
        self.assertEqual(len(view['challenge_ledger']), 2)
        self.assertEqual([row['challenge_id'] for row in view['statements'][0]['challenges']], ['challenge-supplied-1'])
        self.assertEqual(snapshot(self.p)['challenge_stage'], 'NOT_SUPPLIED')
        raw = research_bundle.build_bundle(json.dumps(self.q).encode())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            summary = archive.read('summary.md')
            self.assertIn(b'Independent challenge stage: SUPPLIED', summary)
            self.assertIn(b'Challenges with open material gaps: 1', summary)
            self.assertEqual(json.loads(archive.read('protocol.json'))['challenges'], self.q['challenges'])
        with zipfile.ZipFile(io.BytesIO(research_bundle.build_bundle(json.dumps(self.p).encode()))) as archive:
            self.assertIn(b'Challenges with open material gaps: not supplied', archive.read('summary.md'))
        comparison = compare_protocols(self.p, self.q)
        self.assertEqual(comparison['entity_changes']['challenges']['added_ids'], ['challenge-supplied-1', 'challenge-supplied-2'])
        self.assertIn('challenges', comparison['changed_protocol_fields'])
        self.assertIn('challenge_links.py', research_bundle.engine_hashes())


if __name__ == '__main__':
    unittest.main()
