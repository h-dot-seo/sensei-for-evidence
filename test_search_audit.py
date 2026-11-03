import copy
import io
import json
from pathlib import Path
import unittest
import zipfile
from evidence_workflow import run
from research_bundle import build_bundle


class SearchAuditTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/planned-protocol.json').read_text())

    def test_missing_search_remains_visible(self):
        result = run(self.protocol)
        audit = result['search_plan_audit']
        self.assertEqual(audit['planned'], 2)
        self.assertEqual(audit['completed'], 1)
        self.assertEqual(audit['missing_search_ids'], ['search-secondary'])
        self.assertFalse(audit['all_planned_searches_accounted_for'])
        self.assertEqual(audit['plan_status'], 'INCOMPLETE')
        self.assertIsNone(audit['search_plan_ledger'][1]['enumerated_records'])
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')

    def test_accounted_plan_does_not_establish_census(self):
        self.protocol['search_plan'].pop()
        result = run(self.protocol)
        self.assertEqual(result['search_plan_audit']['plan_status'], 'ASSERTED_ACCOUNTED')
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_paging_count_and_error_issues(self):
        search = self.protocol['searches'][0]
        search.update(has_more=True, total_count=10, error='synthetic timeout')
        audit = run(self.protocol)['search_plan_audit']
        self.assertEqual(audit['incomplete_search_ids'], ['search-primary'])
        self.assertEqual(audit['search_plan_ledger'][0]['issues'],
                         ['total_count_mismatch', 'pagination_unresolved', 'search_error_recorded'])

    def test_bool_float_and_negative_counts_cannot_mark_complete(self):
        for value in (True, 2.0, -1, None):
            self.protocol['searches'][0]['total_count'] = value
            with self.subTest(value=value):
                coverage = run(self.protocol)['coverage'][0]
                self.assertFalse(coverage['complete'])
                self.assertIn('total_count_not_nonnegative_integer', coverage['issues'])

    def test_exact_scope_mismatch_rejected(self):
        for field in ('source', 'query', 'window'):
            protocol = copy.deepcopy(self.protocol)
            protocol['searches'][0][field] += ' changed'
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'differs from planned'):
                run(protocol)

    def test_duplicate_unknown_and_missing_search_ids(self):
        self.protocol['searches'][0]['search_id'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'declared search ID'):
            run(self.protocol)
        self.protocol['searches'][0]['search_id'] = 'search-primary'
        self.protocol['searches'].append(copy.deepcopy(self.protocol['searches'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate executed'):
            run(self.protocol)
        self.protocol['searches'].pop()
        self.protocol['search_plan'].append(copy.deepcopy(self.protocol['search_plan'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate planned'):
            run(self.protocol)

    def test_invalid_shapes(self):
        for value in ({}, [], 'invalid'):
            self.protocol['search_plan'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'nonempty list'):
                run(self.protocol)
        self.protocol.pop('search_plan')
        self.protocol['searches'][0]['record_ids'] = 'r1'
        with self.assertRaisesRegex(ValueError, 'invalid or duplicate IDs'):
            run(self.protocol)

    def test_legacy_unplanned_not_complete_plan(self):
        self.protocol.pop('search_plan')
        result = run(self.protocol)
        self.assertEqual(result['search_plan_audit']['plan_status'], 'NOT_SUPPLIED')
        self.assertFalse(result['search_plan_audit']['all_planned_searches_accounted_for'])

    def test_bundle_preserves_missing_plan(self):
        self.protocol['searches'][0]['has_more'] = True
        raw = build_bundle(json.dumps(self.protocol).encode())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            result = json.loads(archive.read('research.json'))
            report = json.loads(archive.read('reports.json'))
            self.assertEqual(report['search_plan_audit'], result['search_plan_audit'])
            self.assertIn(b'Missing planned searches: 1', archive.read('summary.md'))
            self.assertIn(b'Incomplete planned searches: 1', archive.read('summary.md'))
            self.assertIn('search_audit.py', json.loads(archive.read('manifest.json'))['engine_sha256'])
