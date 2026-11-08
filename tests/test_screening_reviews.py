"""Fictional supplied screening assertions: binding, non-adjudication and offline IO."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from evidence_workflow import run
from screening_links import prepare_targets, link_screening_reviews

ROOT = Path(__file__).resolve().parents[1]


def protocol():
    return dict(question='Fictional screening question?', version='fictional-v1',
                inclusion_criteria=['Fictional scope'], exclusion_criteria=['Outside fictional scope'],
                searches=[dict(source='fictional-export', query='fictional', searched_at='2026-11-04',
                               window='fictional', record_ids=['r1', 'r2', 'pending'], total_count=3,
                               complete=True, has_more=False)],
                screening=[dict(record_id='r1', decision='include', reason='Fictional scope'),
                           dict(record_id='r2', decision='exclude', reason='Fictional outside scope')],
                evidence=[], gaps=[])


def assertion(p, rid='r1', reviewer='Fictional A', decision='include', review_id='review-1', collection=None):
    targets = {row['record_id']: row for row in prepare_targets(p, collection)['record_targets']}
    return dict(review_id=review_id, record_id=rid, reviewer=reviewer, reviewed_at='2026-11-04',
                decision=decision, rationale='Fictional supplied position only', source_locator='fictional://receipt',
                source_basis_sha256=targets[rid]['source_basis_sha256'])


class ScreeningReviewTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()

    def projected(self, p=None):
        return link_screening_reviews(self.p if p is None else p)

    def record(self, rid='r1', p=None):
        return next(row for row in self.projected(p)['record_review_ledger'] if row['record_id'] == rid)

    def test_missing_is_legacy_and_explicit_empty_opts_in(self):
        baseline = run(self.p)
        self.assertNotIn('screening_review', baseline)
        self.assertEqual(self.projected()['stage'], 'NOT_SUPPLIED')
        self.assertEqual(self.projected()['records_with_review_cues'], [])
        self.p['screening_reviews'] = []
        result = run(self.p)
        self.assertEqual(result['screening_review']['stage'], 'SUPPLIED')
        self.assertEqual(result['screening_review']['records_with_review_cues'], ['pending', 'r1', 'r2'])
        result.pop('screening_review')
        self.assertEqual(result, baseline)

    def test_unscreened_and_excluded_records_accept_assertions_without_deciding(self):
        baseline = run(self.p)
        self.p['screening_reviews'] = [assertion(self.p, 'pending'),
                                     assertion(self.p, 'r2', review_id='review-2')]
        result = run(self.p)
        self.assertEqual(result['flow'], baseline['flow'])
        self.assertEqual(result['work_packages'], baseline['work_packages'])
        self.assertIsNone(self.projected()['review_ledger'][0]['matches_recorded_decision'])
        self.assertFalse(self.projected()['review_ledger'][1]['matches_recorded_decision'])
        self.assertIn('CURRENT_POSITION_DIFFERS_FROM_RECORDED', self.record('r2')['comparison_cues'])
        self.assertEqual(len(self.p['screening']), 2)

    def test_conflicting_current_views_and_unclear_are_retained_without_consensus(self):
        self.p['screening_reviews'] = [assertion(self.p), assertion(self.p, reviewer='Fictional B', decision='exclude', review_id='b'),
                                     assertion(self.p, reviewer='Fictional C', decision='unclear', review_id='c')]
        row = self.record()
        self.assertEqual(row['current_decisions'], ['exclude', 'include', 'unclear'])
        self.assertEqual(row['current_review_ids'], ['review-1', 'b', 'c'])
        self.assertEqual(set(row['comparison_cues']), {'DIFFERING_CURRENT_POSITIONS', 'UNCLEAR_CURRENT_POSITION', 'CURRENT_POSITION_DIFFERS_FROM_RECORDED'})
        self.assertEqual(self.projected()['adjudication'], 'NOT_PERFORMED')
        self.assertIsNone(self.projected()['review_ledger'][2]['matches_recorded_decision'])

    def test_stale_exclusion_does_not_create_current_conflict(self):
        self.p['screening_reviews'] = [assertion(self.p), assertion(self.p, reviewer='Fictional B', decision='exclude', review_id='b')]
        self.p['screening_reviews'][1]['source_basis_sha256'] = '0' * 64
        row = self.record()
        self.assertEqual(row['current_decisions'], ['include'])
        self.assertEqual(row['stale_review_ids'], ['b'])
        self.assertEqual(row['comparison_cues'], ['STALE_REVIEW_ASSERTIONS'])

    def test_all_stale_and_unclear_have_explicit_separate_cues(self):
        self.p['screening_reviews'] = [assertion(self.p, decision='unclear')]
        self.p['question'] += ' changed'
        self.assertEqual(self.record()['comparison_cues'], ['NO_CURRENT_SOURCE_REVIEW', 'STALE_REVIEW_ASSERTIONS'])
        self.assertEqual(self.projected()['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(self.p['screening_reviews'][0]['decision'], 'unclear')

    def test_duplicate_review_ids_and_record_reviewer_pairs_are_rejected(self):
        first = assertion(self.p)
        for second in (dict(first, reviewer='B'), dict(first, review_id='second'),
                       dict(first, record_id='r2', reviewer='B')):
            with self.subTest(second=second):
                self.p['screening_reviews'] = [first, second]
                with self.assertRaises(ValueError): self.projected()
                with self.assertRaises(ValueError): run(self.p)
        self.p['screening_reviews'] = [first, assertion(self.p, 'r2', review_id='second')]
        self.assertEqual(len(self.projected()['review_ledger']), 2)

    def test_exact_schema_and_list_shape_are_validated(self):
        row = assertion(self.p)
        cases = [None, {}, 'reviews', [None], [dict(row, extra='forbidden')]]
        for field in row:
            missing = dict(row); missing.pop(field); cases.append([missing])
        for value in cases:
            with self.subTest(value=value):
                self.p['screening_reviews'] = value
                with self.assertRaises(ValueError): self.projected()

    def test_all_fields_are_nonblank_literal_strings(self):
        for key in assertion(self.p):
            for value in ('', ' \t\r\n', None, 1, True, [], {}):
                with self.subTest(key=key, value=value):
                    self.p['screening_reviews'] = [dict(assertion(self.p), **{key:value})]
                    with self.assertRaises(ValueError): self.projected()

    def test_dates_hashes_decisions_and_unknown_record_are_strict(self):
        invalid = {'reviewed_at':['2026-2-04', '20261104', '2026-02-30', '0000-01-01', '2026-11-04T00:00:00Z', '2026-11-04\n'],
                   'source_basis_sha256':['A'*64, 'g'*64, '0'*63, '0'*65, '0'*64+'\n'],
                   'decision':['Include', 'pending', ' include'], 'record_id':['r1 ', 'missing']}
        for key, values in invalid.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    self.p['screening_reviews'] = [dict(assertion(self.p), **{key:value})]
                    with self.assertRaises(ValueError): self.projected()
        self.p['screening_reviews'] = [dict(assertion(self.p), reviewed_at='2024-02-29')]
        self.assertEqual(self.projected()['counts']['review_assertions'], 1)

    def test_literal_reviewer_labels_and_ids_are_not_normalized(self):
        self.p['searches'][0]['record_ids'].extend([' r1', 'R1', '가상\r\n\x1b\u202e'])
        self.p['searches'][0]['total_count'] = 6
        self.p['screening_reviews'] = [assertion(self.p, reviewer='A'), assertion(self.p, reviewer=' A', review_id=' review-1'),
                                     assertion(self.p, ' r1', reviewer='A', review_id='R')]
        self.assertEqual(self.record()['current_reviewer_labels'], [' A', 'A'])
        self.assertEqual(self.record(' r1')['current_review_ids'], ['R'])
        self.assertEqual(len(prepare_targets(self.p)['record_targets']), 6)

    def test_question_criteria_and_full_search_receipt_changes_stale(self):
        self.p['screening_reviews'] = [assertion(self.p)]
        edits = [lambda p:p.update(question='Different fictional question'),
                 lambda p:p['inclusion_criteria'].append('New criterion'),
                 lambda p:p['exclusion_criteria'].append('New exclusion'),
                 lambda p:p['searches'][0].update(query='Changed query'),
                 lambda p:p['searches'][0].update(searched_at='2026-11-05'),
                 lambda p:p['searches'][0]['record_ids'].append('another'),
                 lambda p:p['searches'][0].update(supplied_annotation='Different receipt')]
        for edit in edits:
            p = copy.deepcopy(self.p); edit(p)
            with self.subTest(edit=edit):
                self.assertEqual(self.projected(p)['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')

    def test_canonical_screening_version_work_and_review_metadata_do_not_stale(self):
        self.p['screening_reviews'] = [assertion(self.p)]
        digest = self.p['screening_reviews'][0]['source_basis_sha256']
        self.p.update(version='v2', gaps=[dict(fictional='irrelevant helper metadata')])
        self.p['screening'][0].update(decision='exclude', reason='Changed canonical decision')
        self.p['screening_reviews'][0].update(reviewer='Different supplied label', reviewed_at='2026-11-05', rationale='Other rationale', source_locator='fictional://new')
        row = self.projected()['review_ledger'][0]
        self.assertEqual(row['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['current_source_basis_sha256'], digest)
        self.assertFalse(row['matches_recorded_decision'])

    def test_duplicate_occurrences_across_searches_and_exact_pointers_survive(self):
        self.p['searches'].append(copy.deepcopy(self.p['searches'][0]))
        target = next(r for r in prepare_targets(self.p)['record_targets'] if r['record_id']=='r1')
        self.assertEqual([r['input_pointer'] for r in target['source_basis']['occurrences']], ['/searches/0/record_ids/0','/searches/1/record_ids/0'])
        self.assertEqual(len(prepare_targets(self.p)['source_contexts']), 2)

    def test_source_contexts_are_linear_and_full_search_not_repeated_in_targets(self):
        sizes = []
        for size in (100, 200):
            p = protocol(); p['searches'][0]['record_ids'] = ['record-%04d'%i for i in range(size)]
            prepared = prepare_targets(p)
            self.assertEqual(len(prepared['source_contexts']), 1)
            self.assertEqual(len(prepared['record_targets']), size)
            for target in prepared['record_targets']:
                self.assertNotIn('search', target['source_basis'])
                self.assertNotIn('record_ids', target['source_basis']['occurrences'][0])
            sizes.append(len(json.dumps(prepared)))
        self.assertLess(sizes[1], sizes[0] * 2.2)

    def test_detached_deterministic_projection_and_template_inputs(self):
        self.p['screening_reviews'] = [assertion(self.p)]
        original = copy.deepcopy(self.p); result = self.projected()
        self.assertEqual(result, self.projected())
        result['review_ledger'][0]['review']['rationale'] = 'Mutated output'
        result['record_review_ledger'][1]['recorded_screening']['reason'] = 'Mutated output'
        result['source_contexts'][0]['search']['query'] = 'Mutated output'
        result['record_targets'][0]['source_basis']['inclusion_criteria'].append('Mutated output')
        self.assertEqual(self.p, original)

    def test_bibliographic_mapping_binds_promoted_rows_but_not_nonpromoted(self):
        collection = {'row_ledger':[{'resolution':{'disposition':'new_record','record_id':'r1'}, 'original_values':{'title':'Fictional title'}},
                                    {'resolution':{'disposition':'same_record','record_id':'r1'}, 'original_values':{'title':'Alternate fictional title'}},
                                    {'resolution':{'disposition':'do_not_promote','record_id':None}, 'original_values':{'title':'Unused'}}]}
        first = prepare_targets(self.p, collection)
        target = next(r for r in first['record_targets'] if r['record_id']=='r1')
        self.assertEqual(len(target['source_basis']['bibliographic_rows']), 2)
        collection['row_ledger'][2]['original_values']['title'] = 'Still unused'
        self.assertEqual(first, prepare_targets(self.p, collection))
        collection['row_ledger'][0]['original_values']['title'] = 'Changed promoted title'
        self.assertNotEqual(first, prepare_targets(self.p, collection))
        self.assertEqual(target['source_basis']['bibliographic_rows'][0]['original_values']['title'], 'Fictional title')

    def test_real_fictional_csv_import_allows_screening_review_enrichment(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        from bibliographic_integrity import ENRICHMENT_FIELDS
        self.assertIn('screening_reviews', ENRICHMENT_FIELDS)
        helper = BibliographicReviewTests(); helper.setUp(); p = helper.imported()
        collection = run(p)['bibliographic_collection']
        rid = p['searches'][0]['record_ids'][0]
        p['screening_reviews'] = [assertion(p, rid, collection=collection)]
        result = run(p)['screening_review']
        self.assertEqual(result['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        target = next(r for r in result['record_targets'] if r['record_id']==rid)
        expected = [r for r in collection['row_ledger'] if r['resolution']['record_id']==rid and r['resolution']['disposition']!='do_not_promote']
        self.assertEqual(target['source_basis']['bibliographic_rows'], expected)

    def test_all_projection_paths_keep_reviews_and_legacy_omission(self):
        from prisma_audit import export_audit
        from prisma_reports import report_flow
        from synthesis_review import snapshot
        p = json.loads((ROOT/'examples/report-protocol.json').read_text())
        for project in (export_audit, report_flow, snapshot):
            self.assertNotIn('screening_review', project(p))
        p['screening_reviews'] = [assertion(p)]
        expected = run(p)['screening_review']
        for project in (export_audit, report_flow, snapshot):
            with self.subTest(project=project.__name__):
                self.assertEqual(project(p)['screening_review'], expected)

    def test_status_handoff_use_exact_ids_and_navigate_all_source_sections(self):
        from research_status import status
        from review_handoff import handoff
        self.assertNotIn('records_with_screening_review_cues', status(self.p)['queues'])
        self.p['screening_reviews'] = [assertion(self.p, decision='exclude')]
        expected = self.projected()['records_with_review_cues']
        self.assertEqual(status(self.p)['queues']['records_with_screening_review_cues'], expected)
        packet = handoff(self.p)
        step = next(s for s in packet['manual_review_steps'] if s['queue']=='records_with_screening_review_cues')
        self.assertEqual(step['items'], expected)
        for pointer in ('/screening_reviews/0', '/screening/0', '/searches/0'):
            self.assertIn(pointer, step['matching_input_rows'])
        self.assertTrue(any(v['script']=='screening_review.py' for v in packet['detailed_views']))
        self.assertEqual(packet['conclusion_readiness'], 'NOT_READY')

    def test_compare_opt_in_and_review_identity_without_canonical_change(self):
        from compare_runs import compare_protocols
        self.assertNotIn('screening_review_changes', compare_protocols(self.p, self.p))
        after = copy.deepcopy(self.p); after['screening_reviews'] = [assertion(after)]
        delta = compare_protocols(self.p, after)
        self.assertIn('screening_review_changes', delta)
        self.assertEqual(delta['screening_review_changes']['assertion_changes']['added_ids'], ['review-1'])
        revised = copy.deepcopy(after); revised['screening_reviews'][0]['decision'] = 'exclude'
        delta = compare_protocols(after, revised)
        self.assertEqual(delta['screening_review_changes']['assertion_changes']['changed'], [{'id':'review-1', 'fields':['decision']}])
        self.assertEqual(delta['entity_changes']['screening']['changed'], [])
        removed = compare_protocols(after, self.p)
        self.assertEqual(removed['screening_review_changes']['assertion_changes']['removed_ids'], ['review-1'])

    def test_bundle_seven_payloads_fingerprints_and_round_trip(self):
        from research_bundle import build_bundle, verify
        p = json.loads((ROOT/'examples/report-protocol.json').read_text())
        p['screening_reviews'] = [assertion(p)]
        raw = json.dumps(p).encode()
        packed = build_bundle(raw)
        self.assertEqual(packed, build_bundle(raw))
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            self.assertEqual(len(archive.namelist()), 7)
            research = json.loads(archive.read('research.json'))
            reports = json.loads(archive.read('reports.json'))
            self.assertEqual(research['screening_review'], reports['screening_review'])
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['engine_sha256']['screening_links.py'], hashlib.sha256((ROOT/'screening_links.py').read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'review.zip'; path.write_bytes(packed)
            self.assertTrue(verify(path)['valid'])

    def test_informational_reviews_do_not_invalidate_planning_or_synthesis_bindings(self):
        p = json.loads((ROOT/'examples/synthesis-review.json').read_text())
        baseline = run(p)
        p['screening_reviews'] = [assertion(p)]
        result = run(p)
        for key in ('planning', 'synthesis', 'context', 'appraisal', 'work_packages', 'flow'):
            self.assertEqual(result[key], baseline[key], key)

    def test_api_selection_retains_contexts_and_full_validation(self):
        from screening_review import review
        self.p['searches'].append(dict(self.p['searches'][0], record_ids=['different'], total_count=1))
        self.p['screening_reviews'] = [assertion(self.p), assertion(self.p, 'different', review_id='second')]
        selected = review(self.p, 'r1')
        self.assertEqual([r['record_id'] for r in selected['record_targets']], ['r1'])
        self.assertEqual([r['search_index'] for r in selected['source_contexts']], [0])
        self.assertEqual(selected['protocol_counts']['records'], 4)
        self.assertEqual(selected['counts']['records'], 1)
        self.assertEqual(selected['selection']['validation_scope'], 'ENTIRE_PROTOCOL')
        self.assertEqual(selected['selection']['scope'], 'EXACT_RECORD_ID')
        for wrong in ('R1', 'r1 ', '', 1, True):
            with self.assertRaises(ValueError): review(self.p, wrong)
        self.p['screening_reviews'][1]['reviewed_at'] = 'invalid'
        with self.assertRaises(ValueError): review(self.p, 'r1')

    def test_selection_validates_invalid_unselected_report_rows(self):
        from screening_review import review
        p = json.loads((ROOT/'examples/report-protocol.json').read_text())
        p['reports'][0]['retrieval'] = 'not-a-valid-status'
        with self.assertRaises(ValueError): review(p, 'r2')

    def test_template_is_separate_unfilled_and_preserves_existing_assertions(self):
        from screening_review import template
        self.p['screening_reviews'] = [assertion(self.p)]
        original = copy.deepcopy(self.p)
        result = template(self.p, 'r1')
        draft = result['screening_reviews'][0]
        self.assertEqual(set(draft), set(assertion(self.p)))
        self.assertEqual(draft['record_id'], 'r1')
        self.assertEqual(draft['source_basis_sha256'], self.p['screening_reviews'][0]['source_basis_sha256'])
        self.assertTrue(all(value is None for key,value in draft.items() if key not in ('record_id','source_basis_sha256')))
        self.assertEqual(self.p, original)
        self.assertFalse(result['protocol_changed'])
        self.assertEqual(result['external_calls'], 0)
        with self.assertRaises(ValueError): run(dict(self.p, screening_reviews=result['screening_reviews']))

    def cli(self, source, *arguments):
        return subprocess.run([sys.executable, str(ROOT/'screening_review.py'), str(source), *arguments],
                              capture_output=True, cwd=ROOT, timeout=30,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_cli_unicode_crlf_selection_and_exclusive_json_output(self):
        self.p['question'] = '가상 질문\r\n두 번째 줄'
        self.p['screening_reviews'] = [assertion(self.p)]
        self.p['screening_reviews'][0]['rationale'] = '가상\r\n설명'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'protocol.json'; output = Path(tmp)/'view.json'
            source.write_bytes((json.dumps(self.p, ensure_ascii=False, indent=2)+'\n').replace('\n','\r\n').encode('utf-8'))
            result = self.cli(source, '--record-id', 'r1', '--output', str(output), '--text')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('가상', result.stdout.decode('utf-8'))
            saved = json.loads(output.read_bytes())
            self.assertEqual(saved['counts']['records'], 1)
            self.assertEqual(saved['review_ledger'][0]['review']['rationale'], '가상\r\n설명')
            original = output.read_bytes()
            result = self.cli(source, '--output', str(output))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(output.read_bytes(), original)

    def test_cli_bad_unselected_review_and_duplicate_json_produce_no_partial_output(self):
        self.p['screening_reviews'] = [assertion(self.p), dict(assertion(self.p,'r2',review_id='bad'),reviewed_at='bad')]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'protocol.json'; output = Path(tmp)/'result.json'
            for raw in (json.dumps(self.p).encode(), b'{"question":"a","question":"b"}'):
                source.write_bytes(raw)
                result = self.cli(source, '--record-id', 'r1', '--output', str(output))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertFalse(output.exists())

    def test_text_controls_escaped_and_template_cli_is_json(self):
        from screening_review import review, render_text
        self.p['question'] = 'Fictional\nConclusion: READY\x1b\u202e'
        self.p['screening_reviews'] = [assertion(self.p)]
        self.p['screening_reviews'][0]['reviewer'] = '가상\nConclusion: READY\x1b\u202e'
        rendered = render_text(review(self.p))
        self.assertNotIn('\nConclusion: READY', rendered)
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('\u202e', rendered)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'p.json'; source.write_text(json.dumps(self.p), encoding='utf-8')
            result = self.cli(source, '--template', '--record-id', 'r1')
            self.assertEqual(result.returncode, 0, result.stderr)
            doc = json.loads(result.stdout)
            self.assertIsNone(doc['screening_reviews'][0]['reviewer'])
            self.assertIsNone(doc['screening_reviews'][0]['review_id'])



    def test_core_rejects_malformed_assertions_without_exposing_partial_projection(self):
        rows = [None, {}, 'bad', [None], [dict(assertion(self.p), decision='pending')],
                [dict(assertion(self.p), source_basis_sha256='INVALID')]]
        for value in rows:
            with self.subTest(value=value):
                p = dict(self.p, screening_reviews=value)
                with self.assertRaises(ValueError): run(p)

    def test_unrelated_search_context_change_does_not_stale_selected_record(self):
        self.p['searches'].append(dict(self.p['searches'][0], record_ids=['other'], total_count=1))
        self.p['screening_reviews'] = [assertion(self.p)]
        self.p['searches'][1]['query'] = 'A different unrelated fictional query'
        self.assertEqual(self.projected()['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.p['searches'][0]['record_ids'][1] = 'changed-other-record-in-same-search'
        self.assertEqual(self.projected()['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')

    def test_hash_is_canonical_source_basis_and_object_key_order_independent(self):
        from json_io import canonical_json_bytes
        prepared = prepare_targets(self.p)
        for row in prepared['record_targets']:
            self.assertEqual(row['source_basis_sha256'], hashlib.sha256(canonical_json_bytes(row['source_basis'])).hexdigest())
        reversed_keys = dict(reversed(list(self.p.items())))
        reversed_keys['searches'] = [dict(reversed(list(row.items()))) for row in self.p['searches']]
        self.assertEqual(prepare_targets(reversed_keys), prepared)

    def test_empty_enumeration_is_supplied_but_never_implies_readiness(self):
        from screening_review import review, template
        self.p.update(searches=[], screening=[], screening_reviews=[])
        result = run(self.p)
        self.assertEqual(result['screening_review']['records_with_review_cues'], [])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(review(self.p)['counts']['records'], 0)
        self.assertEqual(template(self.p)['screening_reviews'], [])



    def test_comparison_exposes_unchanged_assertions_becoming_and_remaining_stale(self):
        from compare_runs import compare_protocols, render_text
        self.p['screening_reviews'] = [assertion(self.p)]
        after = copy.deepcopy(self.p); after['question'] += ' changed'
        comparison = compare_protocols(self.p, after)
        delta = comparison['screening_review_changes']
        self.assertEqual(delta['assertion_changes']['changed'], [])
        self.assertEqual(delta['assertion_changes']['unchanged_count'], 1)
        row = delta['review_comparisons'][0]
        self.assertEqual(row['before']['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['after']['source_match_status'], 'STALE_SOURCE')
        self.assertIn('STALE_SOURCE', render_text(comparison))
        identical = compare_protocols(after, after)
        self.assertFalse(identical['has_changes'])
        self.assertEqual(identical['screening_review_changes']['review_comparisons'][0]['after']['source_match_status'], 'STALE_SOURCE')
        self.assertIn('STALE_SOURCE', render_text(identical))

    def test_comparison_distinguishes_absent_empty_and_canonical_reassessment(self):
        from compare_runs import compare_protocols
        empty = dict(self.p, screening_reviews=[])
        delta = compare_protocols(self.p, empty)['screening_review_changes']
        self.assertEqual(delta['before_stage'], 'NOT_SUPPLIED')
        self.assertEqual(delta['after_stage'], 'SUPPLIED')
        self.assertIsNone(delta['before_records_with_review_cues'])
        self.assertEqual(delta['after_records_with_review_cues'], ['pending','r1','r2'])
        before = dict(self.p, screening_reviews=[assertion(self.p)])
        after = copy.deepcopy(before); after['screening'][0]['decision'] = 'exclude'
        delta = compare_protocols(before, after)['screening_review_changes']
        row = delta['review_comparisons'][0]
        self.assertEqual(row['before']['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['after']['source_match_status'], 'CURRENT_SOURCE')
        self.assertTrue(row['before']['matches_recorded_decision'])
        self.assertFalse(row['after']['matches_recorded_decision'])
        self.assertEqual(delta['assertion_changes']['changed'], [])



    def test_documented_fictional_example_has_exact_review_cues_and_unchanged_flow(self):
        source = ROOT/'examples/screening-reviews.json'
        raw = source.read_bytes(); p = json.loads(raw)
        original = copy.deepcopy(p); result = run(p)
        projection = result['screening_review']
        self.assertEqual(projection['counts'], dict(records=4, review_assertions=5, current_source_reviews=4,
                                                   stale_source_reviews=1, records_with_review_cues=4))
        rows = {r['record_id']:r for r in projection['record_review_ledger']}
        self.assertEqual(rows['record-alpha']['comparison_cues'], ['DIFFERING_CURRENT_POSITIONS'])
        self.assertIsNone(rows['record-alpha']['recorded_screening'])
        self.assertEqual(rows['record-beta']['comparison_cues'], ['CURRENT_POSITION_DIFFERS_FROM_RECORDED'])
        self.assertEqual(rows['record-beta']['recorded_screening']['decision'], 'exclude')
        self.assertEqual(rows['record-gamma']['comparison_cues'], ['UNCLEAR_CURRENT_POSITION','STALE_REVIEW_ASSERTIONS'])
        self.assertEqual(rows['record-delta']['comparison_cues'], ['NO_CURRENT_SOURCE_REVIEW'])
        self.assertEqual(result['flow']['screened'], 1)
        self.assertEqual(result['flow']['excluded'], 1)
        self.assertEqual(result['flow']['pending'], 3)
        self.assertEqual(result['flow']['included'], 0)
        legacy = copy.deepcopy(p); legacy.pop('screening_reviews')
        self.assertEqual(result['flow'], run(legacy)['flow'])
        self.assertEqual(result['work_packages'], run(legacy)['work_packages'])
        self.assertEqual(p, original)
        self.assertEqual(source.read_bytes(), raw)

    def test_documented_example_cli_journey_keeps_template_separate_and_sources_unchanged(self):
        source = ROOT/'examples/screening-reviews.json'; raw = source.read_bytes()
        def command(script, *args):
            result = subprocess.run([sys.executable, str(ROOT/script), *map(str,args)],
                                    capture_output=True, cwd=ROOT, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            return json.loads(result.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'new-review-template.json'; archive = Path(tmp)/'review.zip'
            result = self.cli(source, '--template', '--record-id', 'record-alpha', '--output', str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            template = json.loads(output.read_bytes())
            self.assertEqual(template, json.loads(result.stdout))
            self.assertEqual(len(template['screening_reviews']), 1)
            draft = template['screening_reviews'][0]
            self.assertEqual(draft['record_id'], 'record-alpha')
            self.assertEqual(draft['source_basis_sha256'], json.loads(raw)['screening_reviews'][0]['source_basis_sha256'])
            self.assertTrue(all(value is None for key,value in draft.items() if key not in ('record_id','source_basis_sha256')))
            with self.assertRaises(ValueError): run(template)
            self.assertEqual(command('prisma_audit.py',source)['screening_review']['counts']['review_assertions'], 5)
            handoff = command('review_handoff.py',source)
            queue = next(r for r in handoff['manual_review_steps'] if r['queue']=='records_with_screening_review_cues')
            self.assertEqual(queue['items'], ['record-alpha','record-beta','record-delta','record-gamma'])
            compared = command('compare_runs.py',source,source)
            self.assertFalse(compared['has_changes'])
            self.assertEqual(compared['screening_review_changes']['assertion_changes']['unchanged_count'], 5)
            command('research_bundle.py','create',source,archive)
            self.assertTrue(command('research_bundle.py','verify',archive)['valid'])
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(json.loads(output.read_bytes()), template)


if __name__ == '__main__':
    unittest.main()
