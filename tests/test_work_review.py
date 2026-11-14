"""Synthetic research-management review packets, never scientific decisions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from work_review import review_packets, render_text
from research_status import status
from offline_adapter import assemble


class WorkReviewTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(Path('examples/translation-review.json').read_text())

    def test_combined_scope_sources_and_uncertainty_are_preserved(self):
        result = review_packets(self.p, 'WP-TRANSLATION')
        packet = result['packets'][0]
        self.assertEqual(packet['scope_counts'], dict(result_rows=2, source_records=1, supplied_study_ids=1, linked_reports=1))
        self.assertEqual(packet['linked_context_domains'], ['clinical_guideline', 'drug_development'])
        self.assertEqual(packet['recorded_review_gaps']['pending_context_ids'], ['ctx-guideline'])
        self.assertEqual(packet['recorded_review_gaps']['evidence_without_recorded_appraisal'], ['e2'])
        self.assertEqual(packet['work_package']['blocked_by'], ['WP-MECHANISM'])
        self.assertEqual(result['global_search_plan_audit']['missing_search_ids'], ['search-secondary'])
        self.assertEqual(packet['recorded_review_gaps']['source_indices_with_unresolved_accounting'], [])
        by_context = {row['context']['context_id']: row for row in packet['contexts']}
        self.assertEqual(by_context['ctx-guideline']['work_evidence_ids'], ['e1'])
        self.assertEqual(by_context['ctx-development']['work_evidence_ids'], ['e2'])
        self.assertEqual(by_context['ctx-development']['context']['regulatory_status'], 'unknown')
        self.assertEqual(packet['appraisals'][0]['work_evidence_ids'], ['e1'])
        self.assertEqual(packet['results'][0]['screening']['record_id'], 'r1')
        self.assertEqual(packet['results'][0]['report']['report_id'], 'report-1')
        self.assertEqual(result['search_ledger'][packet['sources'][0]['search_ref']['search_index']]['query'], self.p['searches'][0]['query'])
        text = render_text(result)
        for term in ('population/model limitations', 'NO_AUTOMATED_DECISION', 'NOT_READY',
                     'NOT_ESTABLISHED', 'regulatory_status', 'evidence_certainty', 'source_locator', 'limitations'):
            self.assertIn(term, text)

    def test_narrowed_work_does_not_inherit_other_results_reviews(self):
        self.p['gaps'][1].update(evidence_ids=['e2'], context_ids=['ctx-development'])
        packet = review_packets(self.p, 'WP-TRANSLATION')['packets'][0]
        self.assertEqual(packet['appraisals'], [])
        self.assertEqual(packet['recorded_review_gaps']['pending_context_ids'], [])
        self.assertEqual(packet['recorded_review_gaps']['evidence_without_recorded_appraisal'], ['e2'])
        self.assertEqual([r['context']['context_id'] for r in packet['contexts']], ['ctx-development'])
        self.assertEqual([r['evidence']['evidence_id'] for r in packet['results']], ['e2'])

    def test_partly_overlapping_context_and_appraisal_scope_is_explicit(self):
        self.p['contexts'][0]['evidence_ids'] = ['e1', 'e2']
        self.p['appraisals'][0]['evidence_ids'] = ['e1', 'e2']
        self.p['gaps'][1].update(evidence_ids=['e1'], context_ids=['ctx-guideline'])
        packet = review_packets(self.p, 'WP-TRANSLATION')['packets'][0]
        self.assertEqual(packet['contexts'][0]['other_context_evidence_ids'], ['e2'])
        self.assertEqual(packet['appraisals'][0]['other_appraisal_evidence_ids'], ['e2'])
        self.assertEqual(packet['appraisals'][0]['work_evidence_ids'], ['e1'])

    def test_multiple_reports_do_not_inflate_study_identity_or_appraisal_scope(self):
        self.p.pop('search_plan')
        search = self.p['searches'][0]
        search.pop('pages')
        search['record_ids'].append('r3'); search['total_count'] += 1
        self.p['screening'].append(dict(record_id='r3', decision='include', reason='Synthetic scope'))
        evidence = copy.deepcopy(self.p['evidence'][0]); evidence.update(record_id='r3', evidence_id='e3')
        self.p['evidence'].append(evidence)
        report = copy.deepcopy(self.p['reports'][0]); report.update(report_id='report-2', record_ids=['r3'])
        self.p['reports'].append(report)
        self.p['gaps'][1]['evidence_ids'].append('e3')
        packet = review_packets(self.p, 'WP-TRANSLATION')['packets'][0]
        self.assertEqual(packet['scope_counts'], dict(result_rows=3, source_records=2, supplied_study_ids=1, linked_reports=2))
        self.assertEqual(packet['recorded_review_gaps']['evidence_without_recorded_appraisal'], ['e2', 'e3'])
        self.assertEqual(packet['appraisals'][0]['work_evidence_ids'], ['e1'])

    def test_multiple_appraisals_are_not_collapsed_into_consensus(self):
        second = copy.deepcopy(self.p['appraisals'][0])
        second.update(appraisal_id='appraisal-disagreement', reviewer='synthetic-second-reviewer')
        second['domains'][0]['judgement'] = 'different supplied judgement'
        self.p['appraisals'].append(second)
        packet = review_packets(self.p, 'WP-TRANSLATION')['packets'][0]
        self.assertEqual(len(packet['appraisals']), 2)
        self.assertEqual(packet['decision_status'], 'NO_AUTOMATED_DECISION')
        self.assertEqual(packet['recorded_review_gaps']['evidence_without_recorded_appraisal'], ['e2'])

    def test_optional_stages_remain_unknown_not_zero(self):
        self.p.pop('reports'); self.p.pop('search_plan')
        self.p['contexts'] = []
        for work in self.p['gaps']: work['context_ids'] = []
        result = review_packets(self.p)
        self.assertEqual(result['packets'][0]['report_stage'], 'NOT_SUPPLIED')
        self.assertIsNone(result['packets'][0]['scope_counts']['linked_reports'])
        self.assertEqual(result['packets'][0]['context_link_status'], 'NO_CONTEXT_LINKS_SUPPLIED')
        self.assertIn('Missing planned searches: not supplied', render_text(result))

    def test_search_occurrences_join_by_position_not_optional_id(self):
        self.p.pop('search_plan')
        self.p['searches'].append(copy.deepcopy(self.p['searches'][0]))
        result = review_packets(self.p, 'WP-TRANSLATION')
        packet = result['packets'][0]
        self.assertEqual([row['search_index'] for row in packet['sources']], [0, 1])
        self.assertEqual([row['search_index'] for row in packet['results'][0]['search_occurrences']], [0, 1])
        self.assertEqual(result['search_ledger'][packet['sources'][0]['search_ref']['search_index']]['search_id'], result['search_ledger'][packet['sources'][1]['search_ref']['search_index']]['search_id'])

    def test_full_protocol_validation_precedes_selection(self):
        with self.assertRaisesRegex(ValueError, 'unknown work package'):
            review_packets(self.p, 'absent')
        self.p['gaps'][0]['context_ids'] = ['missing-context']
        with self.assertRaises(ValueError): review_packets(self.p, 'WP-TRANSLATION')

    def test_completion_assertions_never_produce_a_development_decision(self):
        for work in self.p['gaps']:
            work.update(status='COMPLETE', artifact_locator='synthetic://deliverable', acceptance_verified=True)
        result = review_packets(self.p)
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result['extraction_completeness'], 'NOT_ESTABLISHED')
        self.assertIn('Extraction completeness: NOT_ESTABLISHED', render_text(result))
        self.assertTrue(all(p['decision_status'] == 'NO_AUTOMATED_DECISION' for p in result['packets']))
        self.assertIn('Supplied acceptance_verified: true', render_text(result))

    def test_deterministic_immutable_and_hash_consistent(self):
        original = copy.deepcopy(self.p)
        result = review_packets(self.p)
        self.assertEqual(result, review_packets(self.p))
        self.assertEqual(original, self.p)
        self.assertEqual(result['protocol_sha256'], status(self.p)['protocol_sha256'])
        self.assertIn('work_review.py', result['engine_sha256'])
        self.p['gaps'] = []
        self.assertEqual(review_packets(self.p)['packets'], [])

    def test_mock_adapter_to_guideline_development_work_packet(self):
        protocol = json.loads(Path('examples/adapter-protocol.json').read_text())
        fixture = json.loads(Path('examples/adapter-fixture.json').read_text())
        reviews = json.loads(Path('examples/adapter-reviews.json').read_text())
        assembled = assemble(protocol, fixture, reviews)['protocol']
        for field in ('gaps', 'contexts', 'appraisals'):
            assembled[field] = copy.deepcopy(self.p[field])
        assembled['version'] = 'synthetic-enriched-v2'
        result = review_packets(assembled, 'WP-TRANSLATION')
        row = result['packets'][0]['results'][0]
        self.assertEqual(row['evidence']['adapter_provenance']['provider']['mode'], 'mock')
        self.assertIsNotNone(row['adapter_candidate_support'])
        self.assertEqual(row['adapter_candidate_support']['supporting_quote'], fixture['extraction_candidates'][0]['supporting_quote'])
        assembled['evidence'][0]['result'] = 'unreviewed change'
        with self.assertRaises(ValueError): review_packets(assembled)

    def test_text_escapes_supplied_controls_and_cli_accepts_unicode(self):
        self.p['gaps'][1]['deliverable'] = '합성 검토\nDecision: APPROVED\x1b[31m\u202e\u2028'
        text = render_text(review_packets(self.p, 'WP-TRANSLATION'))
        self.assertNotIn('\x1b', text)
        self.assertNotIn('\u202e', text)
        self.assertNotIn('\u2028', text)
        self.assertNotIn('\nDecision: APPROVED', text)
        self.assertIn('\\nDecision: APPROVED', text)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.json'
            path.write_text(json.dumps(self.p, ensure_ascii=False), encoding='utf-8')
            result = subprocess.run([sys.executable, 'work_review.py', str(path), '--work-package', 'WP-TRANSLATION', '--text'],
                                    capture_output=True, encoding='utf-8', timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('합성 검토', result.stdout)
            path.write_text('{"question":1,"question":2}', encoding='utf-8')
            invalid = subprocess.run([sys.executable, 'work_review.py', str(path)], capture_output=True, text=True, timeout=20)
            self.assertEqual(invalid.returncode, 1)
            self.assertNotIn('Traceback', invalid.stderr)


if __name__ == '__main__':
    unittest.main()
