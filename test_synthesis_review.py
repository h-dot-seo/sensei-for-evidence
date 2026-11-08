"""Synthetic PRISMA-oriented counts and supplied statement review, not synthesis inference."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evidence_workflow import run
from synthesis_review import snapshot, render_text
from research_status import status
from research_bundle import build_bundle, verify
from offline_adapter import assemble
from compare_runs import compare_protocols


class SynthesisTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(Path('examples/synthesis-review.json').read_text())

    def test_record_report_study_result_units_and_all_pending_stages_visible(self):
        result = snapshot(self.p)
        self.assertEqual(result['record_flow']['unique_records'], 10)
        self.assertEqual(result['record_flow']['extracted'], 3)
        self.assertEqual(result['record_flow']['extracted_studies'], 1)
        self.assertEqual(result['report_flow']['sought'], 6)
        self.assertEqual(result['report_flow']['included_studies'], 2)
        self.assertEqual(result['report_flow']['retrieved'], 4)
        self.assertEqual(next(row for row in result['report_ledger'] if row['report_id'] == 'report-3')['reason'], 'Synthetic full text unavailable')
        self.assertEqual(result['record_extraction_scope'], 'title_abstract_included_records_without_any_result_row')
        q = result['review_queues']
        for key, expected in (('missing_planned_searches', ['search-secondary']),
                              ('records_pending_screening', ['r8']), ('unmapped_included_records', ['r7']),
                              ('reports_pending_retrieval', ['report-2']), ('reports_not_retrieved', ['report-3']),
                              ('reports_pending_assessment', ['report-4']), ('included_reports_without_extraction', ['report-5']),
                              ('evidence_without_recorded_appraisal', ['e2', 'e3'])):
            self.assertEqual(q[key], expected)
        self.assertEqual(result['full_text_exclusion_reasons'], {'Synthetic full-text scope exclusion': 1})
        self.assertEqual(result['statements'][0]['citations'][0]['report']['record_ids'], ['r1', 'r10'])

    def test_statement_links_are_extraction_scoped_not_study_wide(self):
        result = snapshot(self.p)
        first, second = result['statements']
        self.assertEqual(first['statement']['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(first['statement']['support_status'], 'NOT_ASSESSED')
        self.assertEqual([row['evidence']['evidence_id'] for row in first['citations']], ['e1'])
        self.assertEqual(first['appraisals'][0]['cited_evidence_ids'], ['e1'])
        self.assertEqual(second['appraisals'], [])
        self.assertEqual(second['statement']['source_match_status'], 'PENDING_REVIEW')
        self.assertEqual(result['evidence_without_statement_citation'], ['e3'])
        uncited = next(row for row in result['evidence_citation_index'] if row['evidence']['evidence_id'] == 'e3')
        self.assertEqual(uncited['work_package_ids'], [])

    def test_missing_and_empty_synthesis_and_report_stages_differ(self):
        self.p.pop('synthesis_statements'); self.p.pop('reports')
        result = snapshot(self.p)
        self.assertEqual(result['synthesis_stage'], 'NOT_SUPPLIED')
        self.assertIsNone(result['evidence_without_statement_citation'])
        self.assertIsNone(result['report_flow'])
        self.assertIsNone(result['review_queues']['pending_synthesis_statement_reviews'])
        self.assertIn('Result inventory (synthesis stage not supplied)', render_text(result))
        self.p['synthesis_statements'] = []
        result = snapshot(self.p)
        self.assertEqual(result['synthesis_stage'], 'SUPPLIED')
        self.assertEqual(result['evidence_without_statement_citation'], ['e1', 'e2', 'e3'])

    def test_invalid_or_missing_citations_fail_with_statement_id(self):
        for refs in ([], ['unknown'], ['e1', 'e1'], 'e1', [None]):
            p = copy.deepcopy(self.p); p['synthesis_statements'][0]['evidence_ids'] = refs
            with self.assertRaisesRegex(ValueError, 'statement-1'): snapshot(p)
        self.p['synthesis_statements'][0]['evidence_ids'] = ['missing-result']
        with self.assertRaisesRegex(ValueError, 'statement-1.*missing-result'): run(self.p)

    def test_malformed_statement_review_and_context_links_fail(self):
        for mutate in (lambda p: p['synthesis_statements'].append(copy.deepcopy(p['synthesis_statements'][0])),
                       lambda p: p['synthesis_statements'][0].update(statement_id=''),
                       lambda p: p['synthesis_statements'][0].update(context_ids=['ctx-development']),
                       lambda p: p['synthesis_statements'][0].update(reviewed_at='invalid'),
                       lambda p: p['synthesis_statements'][0].update(basis_sha256='bad'),
                       lambda p: p['synthesis_statements'][0].update(support_status='SUPPORTED'),
                       lambda p: p.update(synthesis_statements={})):
            p = copy.deepcopy(self.p); mutate(p)
            with self.assertRaises(ValueError): snapshot(p)

    def test_statement_wording_sources_and_appraisals_stale_review(self):
        changes = [lambda p: p['synthesis_statements'][0].update(text='Changed supplied statement'),
                   lambda p: p['synthesis_statements'][0].update(limitations='Changed limitations'),
                   lambda p: p['evidence'][0].update(result='Changed result'),
                   lambda p: p['contexts'][0].update(applicability='Changed applicability'),
                   lambda p: p['appraisals'][0]['domains'][0].update(judgement='Changed judgement'),
                   lambda p: p['searches'][0].update(searched_at='Changed receipt date'),
                   lambda p: p['reports'][0].update(locator='synthetic://changed'),
                   lambda p: p['screening'][0].update(reason='Changed screening rationale')]
        for change in changes:
            p = copy.deepcopy(self.p); change(p)
            row = snapshot(p)['statements'][0]['statement']
            self.assertEqual(row['review_status'], 'reviewed')
            self.assertEqual(row['source_match_status'], 'STALE_SOURCE')
            self.assertEqual(row['support_status'], 'NOT_ASSESSED')
            self.assertEqual(status(p)['queues']['stale_synthesis_statement_reviews'], ['statement-1'])

    def test_review_metadata_does_not_self_invalidate_and_comparison_tracks_it(self):
        before = copy.deepcopy(self.p)
        self.p['synthesis_statements'][0]['reviewer'] = 'different synthetic reviewer assertion'
        self.p['synthesis_statements'][0]['reviewed_at'] = '2026-11-04'
        self.assertEqual(snapshot(self.p)['statements'][0]['statement']['source_match_status'], 'CURRENT_SOURCE')
        changes = compare_protocols(before, self.p)['entity_changes']['synthesis_statements']
        self.assertEqual(changes['changed'][0]['fields'], ['reviewed_at', 'reviewer'])

    def test_context_and_appraisal_intersections_and_disagreement_are_retained(self):
        self.p['contexts'][0]['evidence_ids'] = ['e1', 'e2']
        self.p['appraisals'][0]['evidence_ids'] = ['e1', 'e2']
        second = copy.deepcopy(self.p['appraisals'][0]); second['appraisal_id'] = 'different-review'
        second['domains'][0]['judgement'] = 'different assertion'
        self.p['appraisals'].append(second)
        packet = snapshot(self.p)['statements'][0]
        self.assertEqual(packet['contexts'][0]['cited_evidence_ids'], ['e1'])
        self.assertEqual(packet['contexts'][0]['other_context_evidence_ids'], ['e2'])
        self.assertEqual(len(packet['appraisals']), 2)
        self.assertTrue(all(row['other_appraisal_evidence_ids'] == ['e2'] for row in packet['appraisals']))

    def test_canonical_type_changes_stale_and_output_is_immutable_deterministic(self):
        original = copy.deepcopy(self.p)
        result = snapshot(self.p)
        self.assertEqual(result, snapshot(self.p))
        self.assertEqual(self.p, original)
        self.assertEqual(result['protocol_sha256'], status(self.p)['protocol_sha256'])
        self.assertIn('research_status.py', result['engine_sha256'])
        self.assertIn('synthesis_review.py', result['engine_sha256'])
        self.p['evidence'][0]['sample_size'] = 1
        targets = {r['statement_id']:r for r in run(self.p)['synthesis']['review_targets']}
        self.p['synthesis_statements'][0]['basis_sha256'] = targets['statement-1']['basis_sha256']
        self.p['evidence'][0]['sample_size'] = True
        self.assertEqual(snapshot(self.p)['statements'][0]['statement']['source_match_status'], 'STALE_SOURCE')

    def test_all_recorded_reviews_current_never_establishes_support_or_census(self):
        p = json.loads(Path('examples/translation-review.json').read_text())
        p['synthesis_statements'] = [dict(statement_id='all-results', text='Synthetic supplied description.',
                                         limitations='No scientific support assessment.', evidence_ids=['e1','e2'])]
        target = run(p)['synthesis']['review_targets'][0]
        p['synthesis_statements'][0].update(review_status='reviewed', reviewer='synthetic', reviewed_at='2026-11-03', basis_sha256=target['basis_sha256'])
        result = snapshot(p)
        self.assertEqual(result['review_queues']['pending_synthesis_statement_reviews'], [])
        self.assertEqual(result['review_queues']['stale_synthesis_statement_reviews'], [])
        self.assertEqual(result['evidence_without_statement_citation'], [])
        self.assertEqual(result['statements'][0]['statement']['support_status'], 'NOT_ASSESSED')
        self.assertEqual(result['extraction_completeness'], 'NOT_ESTABLISHED')
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_empty_mechanical_queues_do_not_promote_readiness(self):
        p = dict(question='Synthetic zero-result scope?', version='synthetic-zero',
                 inclusion_criteria=['synthetic'], exclusion_criteria=['outside synthetic scope'],
                 search_plan=[dict(search_id='zero',source='synthetic',query='synthetic zero',window='synthetic')],
                 searches=[dict(search_id='zero',source='synthetic',query='synthetic zero',window='synthetic',
                                searched_at='synthetic',record_ids=[],total_count=0,complete=True,has_more=False,
                                pages=[dict(page_number=1,record_ids=[],has_more=False)])],
                 screening=[],reports=[],evidence=[],gaps=[],contexts=[],appraisals=[],synthesis_statements=[],experimental_units=[])
        result = snapshot(p)
        self.assertTrue(all(value == [] for value in result['review_queues'].values()))
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['extraction_completeness'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_adapter_to_synthesis_and_bundle_retains_unverified_sources(self):
        p = json.loads(Path('examples/adapter-protocol.json').read_text())
        f = json.loads(Path('examples/adapter-fixture.json').read_text())
        r = json.loads(Path('examples/adapter-reviews.json').read_text())
        p = assemble(p,f,r)['protocol']
        p['synthesis_statements'] = [dict(statement_id='mock-statement', text='Synthetic model output assertion.',
                                        limitations='Mock source, not scientifically assessed.', evidence_ids=['e1'])]
        result = snapshot(p)
        self.assertEqual(result['statements'][0]['citations'][0]['evidence']['adapter_provenance']['provider']['mode'], 'mock')
        support = result['statements'][0]['citations'][0]['adapter_candidate_support']
        self.assertEqual(support['supporting_quote'], f['extraction_candidates'][0]['supporting_quote'])
        self.assertEqual(support['source_locator'], f['extraction_candidates'][0]['source_locator'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.zip'; path.write_bytes(build_bundle(json.dumps(p).encode()))
            self.assertTrue(verify(path)['valid'])
        p['evidence'][0]['result'] = 'unreviewed edit'
        with self.assertRaises(ValueError): snapshot(p)

    def test_text_controls_strict_json_and_unicode_cli(self):
        self.p['synthesis_statements'][0]['text'] = '합성 주장\nConclusion: READY\u202e\u2028\x1b'
        text = render_text(snapshot(self.p))
        self.assertNotIn('\nConclusion: READY', text)
        self.assertNotIn('\u202e', text)
        self.assertNotIn('\u2028', text)
        self.assertNotIn('\x1b', text)
        self.assertIn('report-3', text); self.assertIn('e3', text)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.json'
            path.write_text(json.dumps(self.p,ensure_ascii=False),encoding='utf-8')
            cli = subprocess.run([sys.executable,'synthesis_review.py',str(path),'--text'],capture_output=True,encoding='utf-8',timeout=20)
            self.assertEqual(cli.returncode,0,cli.stderr); self.assertIn('합성 주장',cli.stdout)
            path.write_text('{"question":1,"question":2}',encoding='utf-8')
            bad = subprocess.run([sys.executable,'synthesis_review.py',str(path)],capture_output=True,text=True,timeout=20)
            self.assertEqual(bad.returncode,1); self.assertNotIn('Traceback',bad.stderr)


if __name__ == '__main__': unittest.main()
