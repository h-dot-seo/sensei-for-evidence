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

    def test_false_release_rejected(self):
        self.s['blockers']=['synthetic missing evidence']
        self.s['release']=dict(status='COMPLETE',qa_passed=False,storage_verified=False,
                               required_artifacts=['evidence_table'],artifacts=[],cited_reference_numbers=[1])
        errors=validate(self.s)
        for term in ('sufficiency','blockers','conclusion','QA','storage','citation','evidence_table'):
            self.assertTrue(any(term in x for x in errors), term)


if __name__ == '__main__':
    unittest.main()
