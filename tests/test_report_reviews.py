"""Fictional full-text assertions: exact identity, source binding and offline IO."""
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
from unittest.mock import patch
import zipfile

from evidence_workflow import run
from report_review_links import prepare_targets, link_report_reviews

ROOT = Path(__file__).resolve().parents[1]


def protocol():
    return dict(question='Fictional document review question?', version='fictional-v1',
                inclusion_criteria=['Fictional scope'], exclusion_criteria=['Outside fictional scope'],
                searches=[dict(source='fictional-export', query='fictional', searched_at='2026-11-04',
                               window='fictional', record_ids=['r1', 'r2'], total_count=2,
                               complete=True, has_more=False)],
                screening=[dict(record_id='r1', decision='include', reason='Fictional scope'),
                           dict(record_id='r2', decision='include', reason='Fictional scope')],
                reports=[dict(report_id='report-1', record_ids=['r1'], retrieval='retrieved',
                              decision='include', study_id='study-1', locator='fictional://report-one'),
                         dict(report_id='report-2', record_ids=['r2'], retrieval='pending')],
                evidence=[], gaps=[])


def source(report_id='report-1', source_id='source-1', digest='a' * 64):
    return dict(source_id=source_id, report_id=report_id, source_locator='fictional://document',
                document_version='fictional-v1', document_sha256=digest)


def assertion(p, report_id='report-1', reviewer='Fictional A', decision='include', review_id='review-1', collection=None):
    targets = {row['report_id']: row for row in prepare_targets(p, collection)['report_targets']}
    return dict(review_id=review_id, report_id=report_id, reviewer=reviewer, reviewed_at='2026-11-04',
                decision=decision, rationale='Fictional supplied position only', reviewed_locator='fictional://reviewed',
                source_basis_sha256=targets[report_id]['source_basis_sha256'])


class ReportReviewTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()
        self.p['report_sources'] = [source()]

    def projected(self, p=None):
        return link_report_reviews(self.p if p is None else p)

    def report(self, report_id='report-1', p=None):
        return next(row for row in self.projected(p)['report_review_ledger'] if row['report_id'] == report_id)

    def test_missing_reports_has_no_targets_and_nonempty_references_reject(self):
        p = protocol(); p.pop('reports')
        self.assertEqual(prepare_targets(p)['report_targets'], [])
        self.assertEqual(link_report_reviews(p)['stage'], 'NOT_SUPPLIED')
        for key, rows in (('report_sources', [source()]), ('report_reviews', [assertion(self.p)])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                link_report_reviews(dict(p, **{key: rows}))

    def test_optional_null_and_container_shapes_reject(self):
        for key in ('report_sources', 'report_reviews'):
            for value in (None, {}, '', 0, False, [None], [[]], ['row']):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.projected(dict(self.p, **{key: value}))

    def test_sources_exact_schema_and_nonblank_literal_fields(self):
        row = source()
        cases = [dict(row, extra='forbidden')]
        for key in row:
            missing = dict(row); missing.pop(key); cases.append(missing)
            if key != 'document_sha256':
                cases.extend(dict(row, **{key: value}) for value in ('', ' \t\r\n', None, True, 1, [], {}))
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.projected(dict(self.p, report_sources=[bad]))

    def test_source_hash_and_reference_are_strict(self):
        for digest in ('A'*64, 'z'*64, '0'*63, '0'*65, '0'*64+'\n', '', True, 0, [], {}):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                self.projected(dict(self.p, report_sources=[source(digest=digest)]))
        for report_id in ('missing', 'REPORT-1', 'report-1 '):
            with self.subTest(report_id=report_id), self.assertRaises(ValueError):
                self.projected(dict(self.p, report_sources=[source(report_id=report_id)]))
        self.projected(dict(self.p, report_sources=[source(digest=None)]))

    def test_source_ids_unique_but_duplicate_locator_hash_not_identity(self):
        self.p['report_sources'].append(source(source_id='source-2'))
        self.assertEqual(len(self.projected()['report_targets']), 2)
        self.p['report_sources'].append(source(report_id='report-2'))
        with self.assertRaises(ValueError): self.projected()

    def test_reviews_exact_schema_and_all_nonblank_literal_fields(self):
        row = assertion(self.p)
        cases = [dict(row, extra='forbidden')]
        for key in row:
            missing = dict(row); missing.pop(key); cases.append(missing)
            cases.extend(dict(row, **{key: value}) for value in ('', ' \t\r\n', None, True, 1, [], {}))
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.projected(dict(self.p, report_reviews=[bad]))

    def test_review_dates_hashes_decisions_and_report_ids_strict(self):
        invalid = {'reviewed_at': ['2026-2-04', '20261104', '2026-02-30', '0000-01-01', '2026-11-04T00:00:00Z', '2026-11-04\n'],
                   'source_basis_sha256': ['A'*64, 'g'*64, '0'*63, '0'*65, '0'*64+'\n'],
                   'decision': ['Include', 'pending', ' include'], 'report_id': ['report-1 ', 'missing']}
        row = assertion(self.p)
        for key, values in invalid.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.projected(dict(self.p, report_reviews=[dict(row, **{key: value})]))
        self.projected(dict(self.p, report_reviews=[dict(row, reviewed_at='2024-02-29')]))

    def test_duplicate_review_ids_and_exact_report_reviewer_pairs(self):
        first = assertion(self.p)
        for second in (dict(first, reviewer='B'), dict(first, review_id='second'),
                       dict(first, report_id='report-2', reviewer='B')):
            with self.subTest(second=second), self.assertRaises(ValueError):
                self.projected(dict(self.p, report_reviews=[first, second]))
        self.p['report_reviews'] = [first, assertion(self.p, reviewer=' Fictional A', review_id=' review-1')]
        self.assertEqual(len(self.projected()['review_ledger']), 2)

    def test_hash_is_canonical_basis_and_key_order_independent(self):
        from json_io import canonical_json_bytes
        prepared = prepare_targets(self.p)
        for row in prepared['report_targets']:
            self.assertEqual(row['source_basis_sha256'], hashlib.sha256(canonical_json_bytes(row['source_basis'])).hexdigest())
        shuffled = dict(reversed(list(self.p.items())))
        shuffled['reports'] = [dict(reversed(list(row.items()))) for row in self.p['reports']]
        self.assertEqual(prepare_targets(shuffled), prepared)

    def test_criteria_report_locator_retrieval_and_source_metadata_stale(self):
        self.p['report_reviews'] = [assertion(self.p)]
        edits = [lambda p: p.update(question='Different fictional question'),
                 lambda p: p['inclusion_criteria'].append('Another criterion'),
                 lambda p: p['exclusion_criteria'].append('Another exclusion'),
                 lambda p: p['reports'][0].update(locator='fictional://changed'),
                 lambda p: p['reports'][0].update(retrieval='pending', decision='pending'),
                 lambda p: p['report_sources'][0].update(document_version='v2'),
                 lambda p: p['report_sources'][0].update(document_sha256='b'*64),
                 lambda p: p['report_sources'][0].update(source_locator='fictional://changed'),
                 lambda p: p['report_sources'][0].update(source_id='different-source'),
                 lambda p: p['searches'][0].update(query='changed fictional receipt')]
        for edit in edits:
            p = copy.deepcopy(self.p); edit(p)
            with self.subTest(edit=edit):
                self.assertEqual(self.projected(p)['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')

    def test_canonical_decisions_studies_version_and_review_metadata_not_binding(self):
        self.p['report_reviews'] = [assertion(self.p)]
        original_hash = self.p['report_reviews'][0]['source_basis_sha256']
        self.p.update(version='v2', work_metadata={'fictional': True})
        self.p['reports'][0].update(decision='exclude', reason='Reassessed canonical position', study_id='different-study')
        self.p['report_reviews'][0].update(reviewer='Other fictional label', reviewed_at='2026-11-05', rationale='Other rationale', reviewed_locator='fictional://new')
        row = self.projected()['review_ledger'][0]
        self.assertEqual(row['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['current_source_basis_sha256'], original_hash)
        self.assertFalse(row['matches_recorded_decision'])

    def test_ordered_sources_bind_without_collapsing_equal_locator_or_hash(self):
        self.p['report_sources'].append(source(source_id='source-2'))
        self.p['report_reviews'] = [assertion(self.p)]
        self.p['report_sources'].reverse()
        self.assertEqual(self.projected()['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')

    def test_source_removal_and_unretrieved_state_keep_existing_assertions(self):
        self.p['report_reviews'] = [assertion(self.p)]
        expected = copy.deepcopy(self.p['report_reviews'][0])
        self.p['report_sources'] = []
        for state in ('retrieved', 'pending', 'not_retrieved'):
            p = copy.deepcopy(self.p)
            p['reports'][0].update(retrieval=state, decision='pending', reason='Fictional missing document')
            row = self.projected(p)['review_ledger'][0]
            self.assertEqual(row['review'], expected)
            self.assertEqual(row['source_match_status'], 'STALE_SOURCE')

    def test_conflicting_unclear_and_stale_positions_never_adjudicate(self):
        self.p['report_reviews'] = [assertion(self.p), assertion(self.p, reviewer='B', decision='exclude', review_id='b'),
                                    assertion(self.p, reviewer='C', decision='unclear', review_id='c')]
        result = self.projected()
        self.assertEqual(result['adjudication'], 'NOT_PERFORMED')
        self.assertEqual(self.report()['current_decisions'], ['exclude', 'include', 'unclear'])
        self.assertIn('DIFFERING_CURRENT_POSITIONS', self.report()['comparison_cues'])
        self.assertIn('UNCLEAR_CURRENT_POSITION', self.report()['comparison_cues'])
        self.p['report_reviews'][1]['source_basis_sha256'] = '0'*64
        self.assertEqual(self.report()['current_decisions'], ['include', 'unclear'])
        self.assertEqual(self.report()['stale_review_ids'], ['b'])
        self.assertEqual(self.p['reports'][0]['decision'], 'include')

    def test_bibliographic_promoted_provenance_changes_binding(self):
        collection = {'row_ledger': [dict(resolution=dict(disposition='new_record', record_id='r1'), original_values={'title':'Fictional title'}),
                                     dict(resolution=dict(disposition='do_not_promote', record_id=None), original_values={'title':'Unused'})]}
        self.p['report_reviews'] = [assertion(self.p, collection=collection)]
        collection['row_ledger'][1]['original_values']['title'] = 'Still unused'
        self.assertEqual(link_report_reviews(self.p, collection)['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        collection['row_ledger'][0]['original_values']['title'] = 'Changed fictional title'
        self.assertEqual(link_report_reviews(self.p, collection)['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')

    def test_output_is_deterministic_detached_and_locators_inert(self):
        self.p['report_sources'][0]['source_locator'] = 'https://example.invalid/never-fetch'
        self.p['report_reviews'] = [assertion(self.p)]
        before = copy.deepcopy(self.p)
        with patch('urllib.request.urlopen', side_effect=AssertionError('must not retrieve')), patch('socket.create_connection', side_effect=AssertionError('must not connect')):
            result = self.projected()
            self.assertEqual(result, self.projected())
        def mutate(value):
            if isinstance(value, dict):
                for nested in list(value.values()): mutate(nested)
                value['mutated-output-only'] = True
            elif isinstance(value, list):
                for nested in value: mutate(nested)
                value.append('mutated-output-only')
        mutate(result)
        self.assertEqual(self.p, before)

    def test_api_selection_validates_entire_protocol_and_exact_report_id(self):
        from report_review import review
        self.p['report_reviews'] = [assertion(self.p), assertion(self.p, 'report-2', review_id='second')]
        result = review(self.p, 'report-1')
        self.assertEqual([r['report_id'] for r in result['report_targets']], ['report-1'])
        self.assertEqual(result['protocol_counts']['reports'], 2)
        self.assertEqual(result['counts']['reports'], 1)
        self.assertEqual(result['selection']['validation_scope'], 'ENTIRE_PROTOCOL')
        for bad in ('REPORT-1', 'report-1 ', '', 1, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError): review(self.p, bad)
        self.p['report_reviews'][1]['reviewed_at'] = 'invalid'
        with self.assertRaises(ValueError): review(self.p, 'report-1')

    def test_invalid_unselected_scalar_plural_and_evidence_membership_rejected(self):
        from report_review import review
        mutations = [lambda p: p['reports'][1].update(retrieval='invalid'),
                     lambda p: p['reports'][1].update(record_ids=['unknown-record']),
                     lambda p: p['reports'][1].update(retrieval='retrieved', locator='fictional', decision='include', study_id=''),
                     lambda p: p['reports'][1].update(study_ids=['forbidden-on-pending']),
                     lambda p: p['reports'][0].update(study_ids=['s1'])]
        for mutate in mutations:
            p = copy.deepcopy(self.p); mutate(p)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): review(p, 'report-1')
        p = copy.deepcopy(self.p)
        p['reports'][1].update(retrieval='retrieved', locator='fictional', decision='include', study_id='study-2')
        p['evidence'] = [dict(record_id='r2', study_id='wrong-study', locator='fictional', model='fictional',
                              intervention='fictional', comparator='fictional', endpoint='fictional', result='fictional',
                              limitations='fictional', mechanism_basis='unknown')]
        with self.assertRaises(ValueError): review(p, 'report-1')

    def cli(self, source_path, *args):
        return subprocess.run([sys.executable, str(ROOT/'report_review.py'), str(source_path), *args],
                              capture_output=True, cwd=ROOT, timeout=30,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_cli_utf8_controls_exclusive_output_and_input_preservation(self):
        from report_review import review, render_text
        self.p['question'] = '가상\nConclusion: READY\x1b\u202e'
        self.p['report_reviews'] = [assertion(self.p)]
        self.p['report_reviews'][0]['reviewer'] = '가상\nConclusion: READY\x1b\u202e'
        rendered = render_text(review(self.p))
        for unsafe in ('\nConclusion: READY', '\x1b', '\u202e'):
            self.assertNotIn(unsafe, rendered)
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp)/'protocol.json'; output = Path(tmp)/'view.json'
            raw = (json.dumps(self.p, ensure_ascii=False, indent=2)+'\n').replace('\n', '\r\n').encode('utf-8')
            input_path.write_bytes(raw)
            result = self.cli(input_path, '--report-id', 'report-1', '--output', str(output), '--text')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('가상', result.stdout.decode('utf-8'))
            self.assertEqual(json.loads(output.read_bytes())['counts']['reports'], 1)
            original = output.read_bytes()
            result = self.cli(input_path, '--output', str(output))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(input_path.read_bytes(), raw)

    def test_cli_invalid_unselected_row_duplicate_json_and_surrogate_write_nothing(self):
        self.p['report_reviews'] = [assertion(self.p), dict(assertion(self.p, 'report-2', review_id='bad'), reviewed_at='bad')]
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp)/'protocol.json'; output = Path(tmp)/'view.json'
            for raw in (json.dumps(self.p).encode(), b'{"question":"a","question":"b"}', b'{"question":"\\ud800"}'):
                input_path.write_bytes(raw)
                result = self.cli(input_path, '--report-id', 'report-1', '--output', str(output))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertFalse(output.exists())


    def test_missing_source_and_null_digest_loud_even_when_assertion_hash_matches(self):
        for sources, state in (([], 'SOURCE_NOT_SUPPLIED'), ([source(digest=None)], 'DOCUMENT_BYTES_UNBOUND'),
                               ([source()], 'SUPPLIED_DIGESTS')):
            p = dict(self.p, report_sources=sources)
            p['report_reviews'] = [assertion(p)]
            result = self.projected(p)
            self.assertEqual(result['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
            row = next(row for row in result['report_review_ledger'] if row['report_id']=='report-1')
            self.assertEqual(row['source_binding_state'], state)
            if state != 'SUPPLIED_DIGESTS':
                self.assertIn(state, row['comparison_cues'])
            else:
                self.assertEqual(row['comparison_cues'], [])
            self.assertEqual(result['document_bytes_verification'], 'NOT_PERFORMED')
            self.assertEqual(result['source_authenticity'], 'NOT_VERIFIED')
            self.assertEqual(result['reviewer_identity_verification'], 'NOT_ESTABLISHED')
            self.assertEqual(result['eligibility_correctness'], 'NOT_ASSESSED')

    def test_template_drafts_blank_new_assertion_and_never_refreshes_existing(self):
        from report_review import template
        self.p['report_reviews'] = [assertion(self.p)]
        self.p['report_sources'][0]['document_version'] = 'changed-v2'
        before = copy.deepcopy(self.p)
        result = template(self.p, 'report-1')
        self.assertEqual(result['report_sources'], [])
        draft = result['report_reviews'][0]
        self.assertEqual(set(draft), set(assertion(self.p)))
        self.assertEqual(draft['report_id'], 'report-1')
        self.assertEqual(draft['source_basis_sha256'], assertion(self.p)['source_basis_sha256'])
        self.assertNotEqual(draft['source_basis_sha256'], self.p['report_reviews'][0]['source_basis_sha256'])
        self.assertTrue(all(value is None for key, value in draft.items() if key not in ('report_id','source_basis_sha256')))
        self.assertEqual(result['review_ledger'][0]['review'], before['report_reviews'][0])
        self.assertEqual(result['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(self.p, before)
        self.assertFalse(result['protocol_changed'])
        self.assertEqual(result['external_calls'], 0)
        with self.assertRaises(ValueError): run(dict(self.p, report_reviews=result['report_reviews']))

    def test_template_source_scaffold_requires_regeneration_and_no_unretrieved_reviews(self):
        from report_review import template
        self.p['report_sources'] = []
        result = template(self.p)
        self.assertEqual(result['report_reviews'], [])
        self.assertEqual(len(result['report_sources']), 1)
        draft = result['report_sources'][0]
        self.assertEqual(draft['report_id'], 'report-1')
        self.assertTrue(all(value is None for key, value in draft.items() if key != 'report_id'))
        for state in ('pending', 'not_retrieved'):
            p = copy.deepcopy(self.p)
            p['reports'][0].update(retrieval=state, decision='pending', reason='Fictional unavailable')
            p['report_sources'] = [source()]
            result = template(p)
            self.assertEqual(result['report_reviews'], [])
            self.assertEqual(result['report_sources'], [])
        self.p['report_sources'] = [source(digest=None)]
        result = template(self.p, 'report-1')
        self.assertEqual(len(result['report_reviews']), 1)
        self.assertIn('DOCUMENT_BYTES_UNBOUND', result['template_warning'])
        self.assertEqual(result['report_targets'][0]['source_binding_state'], 'DOCUMENT_BYTES_UNBOUND')

    def test_template_cli_json_and_selection_keep_original_pointers(self):
        from report_review import review
        self.p['report_sources'].append(source(report_id='report-2', source_id='source-2'))
        self.p['report_reviews'] = [assertion(self.p), assertion(self.p, 'report-2', review_id='review-2')]
        result = review(self.p, 'report-2')
        self.assertEqual(result['report_targets'][0]['input_pointer'], '/reports/1')
        self.assertEqual(result['report_targets'][0]['source_input_pointers'], ['/report_sources/1'])
        self.assertEqual(result['source_ledger'][0]['input_pointer'], '/report_sources/1')
        self.assertEqual(result['review_ledger'][0]['input_pointer'], '/report_reviews/1')
        self.assertEqual([row['record_id'] for row in result['record_targets']], ['r2'])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'p.json'; path.write_text(json.dumps(self.p), encoding='utf-8')
            result = self.cli(path, '--template', '--report-id', 'report-1')
            self.assertEqual(result.returncode, 0, result.stderr)
            draft = json.loads(result.stdout)['report_reviews'][0]
            self.assertIsNone(draft['reviewer'])
            self.assertIsNone(draft['review_id'])

    def test_exact_report_reviewer_pairs_cannot_collide_by_concatenation(self):
        self.p['reports'][0]['report_id'] = 'A:B'
        self.p['reports'][1]['report_id'] = 'A'
        self.p['report_sources'] = [source(report_id='A:B')]
        self.p['report_reviews'] = [assertion(self.p, 'A:B', reviewer='C'),
                                    assertion(self.p, 'A', reviewer='B:C', review_id='second')]
        result = self.projected()
        self.assertEqual(len(result['review_ledger']), 2)
        self.assertEqual({row['report_id'] for row in result['report_review_ledger']}, {'A:B','A'})

    def test_linear_shared_source_catalog_without_full_receipts_in_each_report(self):
        sizes = []
        for size in (80, 160):
            p = protocol(); ids = ['r-%04d'%i for i in range(size)]
            p['searches'][0].update(record_ids=ids, total_count=size)
            p['screening'] = [dict(record_id=rid, decision='include', reason='Fictional scope') for rid in ids]
            p['reports'] = [dict(report_id='report-'+rid, record_ids=[rid], retrieval='pending') for rid in ids]
            result = prepare_targets(p)
            self.assertEqual(len(result['source_contexts']), 1)
            self.assertEqual(len(result['record_targets']), size)
            self.assertEqual(len(result['report_targets']), size)
            for target in result['report_targets']:
                self.assertEqual(set(target['source_basis']['mapped_records'][0]), {'record_id','source_basis_sha256'})
                self.assertNotIn('searches', target['source_basis'])
            sizes.append(len(json.dumps(result)))
        self.assertLess(sizes[1], sizes[0]*2.2)

    def test_unrelated_record_receipt_change_does_not_stale_other_report(self):
        self.p['searches'][0]['record_ids'] = ['r1']
        self.p['searches'].append(dict(self.p['searches'][0], record_ids=['r2']))
        self.p['report_reviews'] = [assertion(self.p)]
        self.p['searches'][1]['query'] = 'Changed unrelated query'
        self.assertEqual(self.projected()['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.p['reports'][1]['locator'] = 'Unrelated locator'
        self.assertEqual(self.projected()['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')

    def test_legacy_omission_explicit_empty_and_exact_counts_csv_preservation(self):
        from prisma_reports import report_flow
        p = protocol()
        baseline = run(p); old_reports = report_flow(p)
        self.assertNotIn('report_review', baseline)
        self.assertNotIn('report_review', old_reports)
        for key in ('report_sources', 'report_reviews'):
            enriched = dict(p, **{key: []})
            result = run(enriched)
            self.assertEqual(result.pop('report_review')['stage'], 'SUPPLIED')
            self.assertEqual(result, baseline)
            reports = report_flow(enriched)
            reports.pop('report_review')
            self.assertEqual(reports, old_reports)
        self.p['report_reviews'] = [assertion(self.p, decision='exclude')]
        reports = report_flow(self.p)
        self.assertEqual(reports['report_csv'], old_reports['report_csv'])
        self.assertEqual(reports['report_flow'], old_reports['report_flow'])
        self.assertEqual(reports['record_flow'], old_reports['record_flow'])
        self.assertEqual(reports['work_packages'], old_reports['work_packages'])

    def test_all_optional_projection_paths_agree_and_navigation_is_exact(self):
        from prisma_audit import export_audit
        from prisma_reports import report_flow
        from synthesis_review import snapshot
        from research_status import status
        from review_handoff import handoff
        for project in (export_audit, report_flow, snapshot):
            self.assertNotIn('report_review', project(protocol()))
        self.p['report_reviews'] = [assertion(self.p, decision='exclude')]
        expected = run(self.p)['report_review']
        for project in (export_audit, report_flow, snapshot):
            self.assertEqual(project(self.p)['report_review'], expected)
        self.assertNotIn('reports_with_review_cues', status(protocol())['queues'])
        self.assertEqual(status(self.p)['queues']['reports_with_review_cues'], expected['reports_with_review_cues'])
        packet = handoff(self.p)
        step = next(row for row in packet['manual_review_steps'] if row['queue']=='reports_with_review_cues')
        for pointer in ('/reports/0', '/report_sources/0', '/report_reviews/0'):
            self.assertIn(pointer, step['matching_input_rows'])
        self.assertTrue(any(row['script']=='report_review.py' for row in packet['detailed_views']))

    def test_comparison_retains_unchanged_assertions_that_become_stale(self):
        from compare_runs import compare_protocols, render_text
        self.assertNotIn('report_review_changes', compare_protocols(protocol(), protocol()))
        self.p['report_reviews'] = [assertion(self.p)]
        after = copy.deepcopy(self.p); after['report_sources'][0]['document_version'] = 'v2'
        delta = compare_protocols(self.p, after)['report_review_changes']
        self.assertEqual(delta['assertion_changes']['changed'], [])
        self.assertEqual(delta['assertion_changes']['unchanged_count'], 1)
        self.assertEqual(delta['source_changes']['changed'], [{'id':'source-1','fields':['document_version']}])
        row = delta['review_comparisons'][0]
        self.assertEqual(row['before']['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['after']['source_match_status'], 'STALE_SOURCE')
        identical = compare_protocols(after, after)
        self.assertFalse(identical['has_changes'])
        self.assertIn('STALE_SOURCE', render_text(identical))
        delta = compare_protocols(protocol(), dict(protocol(), report_reviews=[]))['report_review_changes']
        self.assertEqual(delta['before_review_stage'], 'NOT_SUPPLIED')
        self.assertEqual(delta['after_review_stage'], 'SUPPLIED')

    def test_bundle_roundtrip_preserves_source_assertions_and_helper_fingerprint(self):
        from research_bundle import build_bundle, verify
        self.p['report_reviews'] = [assertion(self.p)]
        raw = json.dumps(self.p).encode('utf-8')
        packed = build_bundle(raw)
        self.assertEqual(packed, build_bundle(raw))
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            self.assertEqual(len(archive.namelist()), 7)
            research = json.loads(archive.read('research.json'))
            reports = json.loads(archive.read('reports.json'))
            self.assertEqual(research['report_review'], reports['report_review'])
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['engine_sha256']['report_review_links.py'], hashlib.sha256((ROOT/'report_review_links.py').read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'reviews.zip'; path.write_bytes(packed)
            self.assertTrue(verify(path)['valid'])

    def test_real_fictional_csv_import_accepts_source_and_review_enrichment(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        from bibliographic_integrity import ENRICHMENT_FIELDS
        self.assertTrue({'report_sources', 'report_reviews'}.issubset(ENRICHMENT_FIELDS))
        helper = BibliographicReviewTests(); helper.setUp(); p = helper.imported()
        rid = p['searches'][0]['record_ids'][0]
        p['screening'] = [dict(record_id=rid, decision='include', reason='Fictional scope')]
        p['reports'] = [dict(report_id='report-1', record_ids=[rid], retrieval='retrieved', locator='fictional', decision='pending')]
        p['report_sources'] = [source()]
        collection = run(p)['bibliographic_collection']
        p['report_reviews'] = [assertion(p, collection=collection)]
        self.assertEqual(run(p)['report_review']['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')

    def test_informational_reviews_do_not_invalidate_synthesis_and_work_bindings(self):
        p = json.loads((ROOT/'examples/synthesis-review.json').read_text(encoding='utf-8'))
        baseline = run(p)
        self.assertIn('reports', p)
        report_id = p['reports'][0]['report_id']
        p['report_sources'] = [source(report_id=report_id)]
        p['report_reviews'] = [assertion(p, report_id=report_id)]
        result = run(p)
        for key in ('planning', 'synthesis', 'context', 'appraisal', 'work_packages', 'flow'):
            self.assertEqual(result[key], baseline[key], key)


    def test_empty_optional_keys_without_reports_remain_explicit_opt_in(self):
        from report_review import review, template
        p = protocol(); p.pop('reports')
        for key in ('report_sources', 'report_reviews'):
            candidate = dict(p, **{key: []})
            result = review(candidate)
            self.assertEqual(result['stage'], 'SUPPLIED')
            self.assertEqual(result['report_stage'], 'NOT_SUPPLIED')
            self.assertEqual(result['report_targets'], [])
            self.assertEqual(result['counts']['reports'], 0)
            self.assertEqual(template(candidate)['report_reviews'], [])
            self.assertEqual(template(candidate)['report_sources'], [])

    def test_unclear_and_pending_canonical_comparison_remain_unresolved(self):
        self.p['report_reviews'] = [assertion(self.p, decision='unclear'), assertion(self.p, 'report-2', review_id='second')]
        result = self.projected()
        self.assertTrue(all(row['matches_recorded_decision'] is None for row in result['review_ledger']))
        for report in result['report_review_ledger']:
            self.assertNotIn('CURRENT_POSITION_DIFFERS_FROM_RECORDED', report['comparison_cues'])
        self.assertIn('UNCLEAR_CURRENT_POSITION', self.report()['comparison_cues'])
        self.assertIn('RETRIEVAL_PENDING', self.report('report-2')['comparison_cues'])

    def test_source_basis_excludes_evidence_work_and_study_memberships(self):
        self.p['report_reviews'] = [assertion(self.p)]
        original = prepare_targets(self.p)['report_targets'][0]['source_basis']
        p = copy.deepcopy(self.p)
        p['reports'][0].pop('study_id'); p['reports'][0]['study_ids'] = ['study-1', 'study-2']
        p['evidence'] = [dict(record_id='r1', study_id='study-2', locator='fictional', model='fictional',
                              intervention='fictional', comparator='fictional', endpoint='fictional', result='fictional',
                              limitations='fictional', mechanism_basis='unknown')]
        p['gaps'] = [dict(question='Fictional follow-up?', evidence_ids=['r1'], deliverable='Fictional deliverable',
                          acceptance_criterion='Fictional acceptance')]
        result = self.projected(p)
        self.assertEqual(result['report_targets'][0]['source_basis'], original)
        self.assertEqual(result['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        for field in ('decision','reason','study_id','study_ids','report_reviews','evidence','gaps','version'):
            self.assertNotIn(field, original)

    def test_report_reordering_changes_pointers_not_bound_source_context(self):
        self.p['report_reviews'] = [assertion(self.p)]
        self.p['reports'].reverse()
        result = self.projected()
        target = next(row for row in result['report_targets'] if row['report_id']=='report-1')
        self.assertEqual(target['input_pointer'], '/reports/1')
        self.assertEqual(result['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')

    def test_same_locator_hash_across_reports_never_merge_source_identities(self):
        self.p['report_sources'] = [source(), source(report_id='report-2', source_id=' source-1')]
        result = self.projected()
        self.assertEqual(len(result['source_ledger']), 2)
        self.assertEqual([row['source']['source_id'] for row in result['source_ledger']], ['source-1',' source-1'])
        self.assertEqual(result['report_targets'][0]['source_input_pointers'], ['/report_sources/0'])
        self.assertEqual(result['report_targets'][1]['source_input_pointers'], ['/report_sources/1'])

    def test_full_target_catalog_detachment_from_bibliographic_collection(self):
        collection = {'row_ledger': [dict(resolution=dict(disposition='new_record', record_id='r1'), original_values={'title':['Fictional nested title']})]}
        before = copy.deepcopy(collection)
        result = prepare_targets(self.p, collection)
        result['record_targets'][0]['source_basis']['bibliographic_rows'][0]['original_values']['title'].append('Changed output')
        result['source_ledger'][0]['source']['document_version'] = 'Changed output'
        self.assertEqual(collection, before)
        self.assertEqual(self.p['report_sources'][0]['document_version'], 'fictional-v1')
        self.assertEqual(result['report_targets'][0]['source_basis']['report_sources'][0]['document_version'], 'fictional-v1')

    def test_clean_imports_do_not_have_workflow_report_cycles(self):
        for imports in ('import report_review_links; import evidence_workflow; import prisma_reports; import report_review',
                        'import prisma_reports; import report_review; import evidence_workflow; import report_review_links'):
            result = subprocess.run([sys.executable, '-c', imports], cwd=ROOT, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


    def test_documented_example_exact_counts_and_canonical_ledger_unchanged(self):
        from prisma_reports import report_flow
        path = ROOT/'examples/report-reviews.json'; raw = path.read_bytes(); p = json.loads(raw)
        original = copy.deepcopy(p); result = run(p)
        projection = result['report_review']
        self.assertEqual(projection['counts'], dict(reports=5, source_descriptors=3, review_assertions=4,
                                                   current_source_reviews=3, stale_source_reviews=1, reports_with_review_cues=5))
        rows = {row['report_id']:row for row in projection['report_review_ledger']}
        self.assertEqual(rows['report-one']['current_decisions'], ['exclude','include'])
        self.assertEqual(rows['report-two']['comparison_cues'], ['DOCUMENT_BYTES_UNBOUND','UNCLEAR_CURRENT_POSITION'])
        self.assertEqual(rows['report-three']['comparison_cues'], ['SOURCE_NOT_SUPPLIED','NO_CURRENT_SOURCE_REVIEW'])
        self.assertIn('RETRIEVAL_PENDING', rows['report-four']['comparison_cues'])
        self.assertEqual(rows['report-five']['stale_review_ids'], ['review-five-old'])
        self.assertIn('REPORT_NOT_RETRIEVED', rows['report-five']['comparison_cues'])
        self.assertEqual(rows['report-one']['supplied_study_ids'], ['study-A','study-B','study-C'])
        self.assertEqual(rows['report-two']['supplied_study_ids'], ['study-A'])
        self.assertEqual(sum(len(row['supplied_study_ids']) for row in rows.values()), 4)
        self.assertEqual(len(p['evidence']), 2)
        legacy = copy.deepcopy(p); legacy.pop('report_sources'); legacy.pop('report_reviews')
        baseline = run(legacy)
        for key in ('flow','work_packages','report_study_coverage','planning','synthesis'):
            self.assertEqual(result[key], baseline[key])
        reports = report_flow(p); old_reports = report_flow(legacy)
        for key in ('report_flow','record_flow','report_csv','report_study_coverage'):
            self.assertEqual(reports[key], old_reports[key])
        self.assertEqual(reports['report_flow'], dict(sought=5, retrieved=3, not_retrieved=1, retrieval_pending=1,
                                                    assessed=2, assessment_pending=1, excluded=0, included=2,
                                                    included_studies=3, reports_with_extraction=1))
        self.assertEqual(p, original)
        self.assertEqual(path.read_bytes(), raw)

    def test_documented_example_cli_audit_handoff_compare_and_bundle_journey(self):
        path = ROOT/'examples/report-reviews.json'; raw = path.read_bytes()
        def command(script, *args):
            result = subprocess.run([sys.executable, str(ROOT/script), *map(str,args)],
                                    capture_output=True, cwd=ROOT, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            return json.loads(result.stdout)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'new-full-text-template.json'; archive = Path(tmp)/'reviews.zip'
            result = self.cli(path, '--template', '--output', str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            template = json.loads(output.read_bytes())
            self.assertEqual(template, json.loads(result.stdout))
            self.assertEqual([row['report_id'] for row in template['report_sources']], ['report-three'])
            self.assertEqual([row['report_id'] for row in template['report_reviews']], ['report-one','report-two'])
            for row in template['report_reviews']:
                self.assertTrue(all(value is None for key,value in row.items() if key not in ('report_id','source_basis_sha256')))
            self.assertEqual(template['review_ledger'][-1]['review'], json.loads(raw)['report_reviews'][-1])
            self.assertEqual(template['review_ledger'][-1]['source_match_status'], 'STALE_SOURCE')
            audit = command('prisma_audit.py', path)
            self.assertEqual(audit['report_review']['counts']['review_assertions'], 4)
            handoff = command('review_handoff.py', path)
            step = next(row for row in handoff['manual_review_steps'] if row['queue']=='reports_with_review_cues')
            self.assertEqual(set(step['items']), {'report-one','report-two','report-three','report-four','report-five'})
            for pointer in ('/reports/4','/report_sources/2','/report_reviews/3'):
                self.assertIn(pointer, step['matching_input_rows'])
            comparison = command('compare_runs.py', path, path)
            self.assertFalse(comparison['has_changes'])
            self.assertEqual(comparison['report_review_changes']['assertion_changes']['unchanged_count'], 4)
            command('research_bundle.py', 'create', path, archive)
            self.assertTrue(command('research_bundle.py', 'verify', archive)['valid'])
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(json.loads(output.read_bytes()), template)

    def test_documented_source_first_scaffold_regenerated_before_review_binding(self):
        from report_review import template
        path = ROOT/'examples/report-reviews.json'; raw = path.read_bytes(); p = json.loads(raw)
        initial = template(p, 'report-three')
        self.assertEqual(initial['report_reviews'], [])
        self.assertEqual(len(initial['report_sources']), 1)
        scaffold = initial['report_sources'][0]
        self.assertEqual(set(scaffold), set(source()))
        self.assertNotIn('source_basis_sha256', scaffold)
        completed = dict(scaffold, source_id='source-three-new', source_locator='synthetic://report-three/main',
                         document_version='Fictional manually supplied version', document_sha256='c'*64)
        candidate = copy.deepcopy(p); candidate['report_sources'].append(completed)
        regenerated = template(candidate, 'report-three')
        self.assertEqual(regenerated['report_sources'], [])
        self.assertEqual(len(regenerated['report_reviews']), 1)
        draft = regenerated['report_reviews'][0]
        self.assertEqual(draft['source_basis_sha256'], regenerated['report_targets'][0]['source_basis_sha256'])
        self.assertNotEqual(draft['source_basis_sha256'], initial['report_targets'][0]['source_basis_sha256'])
        self.assertIsNone(draft['decision'])
        self.assertEqual(candidate['report_reviews'], p['report_reviews'])
        self.assertEqual(candidate['reports'], p['reports'])
        self.assertEqual(run(candidate)['flow'], run(p)['flow'])
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
