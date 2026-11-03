import copy
import unittest
from validate_run import validate


class StateTest(unittest.TestCase):
    def setUp(self):
        self.s = dict(project_id='synthetic', research_question='Synthetic demonstration?',
                      run_id='demo', phase='discovery', gate='intent',
                      evidence_sufficiency='UNASSESSED', conclusion_readiness='NOT_READY',
                      next_action='Define scope')

    def test_pending_is_valid_not_ready(self):
        self.assertEqual(validate(self.s), [])

    def test_incomplete_census(self):
        self.s['searches']=[dict(query='synthetic',enumerated_ids=['one'],total_count=2,complete=True,has_more=True)]
        errors=validate(self.s)
        self.assertTrue(any('paging' in x for x in errors))
        self.assertTrue(any('count mismatch' in x for x in errors))

    def test_count_reconciliation(self):
        self.s['screening']=dict(identified=10, duplicates=2, screened=9)
        self.assertTrue(validate(self.s))

    def test_complete_count_and_flags_are_strict(self):
        baseline = dict(query='synthetic', enumerated_ids=['one'], total_count=1, complete=True, has_more=False)
        self.s['searches'] = [baseline]
        self.assertEqual(validate(self.s), [])
        for field, value in (('total_count', True), ('total_count', 1.0), ('has_more', None),
                             ('complete', 'true'), ('error', 'synthetic timeout'),
                             ('truncated', None), ('pagination_limited', 'false'), ('field_pages_pending', 0)):
            self.s['searches'] = [dict(baseline, **{field: value})]
            with self.subTest(field=field, value=value):
                self.assertTrue(validate(self.s))

    def test_invalid_search_shapes_return_errors(self):
        for searches in ({}, ['invalid'], [dict(query='synthetic', enumerated_ids='one')],
                         [dict(query='synthetic', enumerated_ids=[{}])]):
            self.s['searches'] = searches
            with self.subTest(searches=searches):
                self.assertTrue(validate(self.s))

    def test_boolean_screening_counts_rejected(self):
        self.s['screening'] = dict(identified=True, duplicates=0, screened=1)
        self.assertTrue(any('nonnegative integers' in error for error in validate(self.s)))

    def test_false_release_rejected(self):
        self.s['blockers']=['synthetic missing evidence']
        self.s['release']=dict(status='COMPLETE',qa_passed=False,storage_verified=False,
                               required_artifacts=['evidence_table'],artifacts=[],cited_reference_numbers=[1])
        errors=validate(self.s)
        for term in ('sufficiency','blockers','conclusion','QA','storage','citation','evidence_table'):
            self.assertTrue(any(term in x for x in errors), term)


if __name__ == '__main__':
    unittest.main()
