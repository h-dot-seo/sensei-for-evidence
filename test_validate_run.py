import copy
import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
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

    def complete_state(self):
        state = copy.deepcopy(self.s)
        state.update(evidence_sufficiency='SUFFICIENT', conclusion_readiness='READY',
                     references=[dict(reference_no=1, included_in_report=True, verified=True)])
        state['release'] = dict(status='COMPLETE', qa_passed=True, storage_verified=True,
                                cited_reference_numbers=[1], required_artifacts=['evidence_table'],
                                artifacts=[dict(type='evidence_table', exists=True)])
        return state

    def test_complete_assertions_require_true_boolean(self):
        baseline = self.complete_state()
        self.assertEqual(validate(baseline), [])
        for value in ('false', 'true', 1, [], None, False):
            for field in ('qa_passed', 'storage_verified', 'verified', 'exists'):
                state = copy.deepcopy(baseline)
                target = (state['references'][0] if field == 'verified' else
                          state['release']['artifacts'][0] if field == 'exists' else state['release'])
                target[field] = value
                with self.subTest(field=field, value=value):
                    self.assertTrue(validate(state))

    def test_actual_citations_require_verification_without_inclusion_flag(self):
        for included in (False, None, True):
            state = self.complete_state()
            state['references'][0].update(included_in_report=included, verified=False)
            self.assertIn('release: unverified cited reference', validate(state))

    def test_included_reference_requires_verification_without_explicit_citation(self):
        state = self.complete_state()
        state['release']['cited_reference_numbers'] = []
        state['references'][0]['verified'] = False
        self.assertIn('release: unverified cited reference', validate(state))

    def test_uncited_unincluded_reference_need_not_be_verified(self):
        state = self.complete_state()
        state['references'].append(dict(reference_no=2, included_in_report=False, verified=False))
        self.assertEqual(validate(state), [])

    def test_malformed_nested_shapes_return_errors(self):
        for key, value in (('screening', []), ('screening', 0), ('references', {}),
                           ('references', [None]), ('references', [1]), ('release', [])):
            state = self.complete_state()
            state[key] = value
            with self.subTest(key=key, value=value):
                self.assertTrue(validate(state))
        for key, value in (('artifacts', [None]), ('artifacts', {}),
                           ('required_artifacts', {}), ('required_artifacts', [None]),
                           ('artifacts', [dict(exists=True)]), ('cited_reference_numbers', {})):
            state = self.complete_state()
            state['release'][key] = value
            with self.subTest(key=key, value=value):
                self.assertTrue(validate(state))

    def test_partial_screening_counts_are_validated_individually(self):
        for field in ('identified', 'duplicates', 'screened', 'excluded', 'advanced'):
            for value in (-1, True, 1.0, '1', None):
                state = copy.deepcopy(self.s)
                state['screening'] = {field: value}
                with self.subTest(field=field, value=value):
                    self.assertTrue(validate(state))
            state['screening'] = {field: 0}
            self.assertEqual(validate(state), [])

    def test_reference_numbers_do_not_alias_boolean_float_or_null(self):
        for number in (True, 1.0, None, '1', [], {}, 0, -1):
            for where in ('reference', 'citation'):
                state = self.complete_state()
                if where == 'reference':
                    state['references'][0]['reference_no'] = number
                else:
                    state['release']['cited_reference_numbers'] = [number]
                with self.subTest(number=number, where=where):
                    self.assertTrue(validate(state))
        state = self.complete_state()
        state['release']['cited_reference_numbers'] = [1, 1]
        self.assertTrue(validate(state))

    def test_reference_flags_are_boolean_even_before_release(self):
        for flag in ('included_in_report', 'verified', 'text_complete', 'text_truncated'):
            state = self.complete_state()
            state['release']['status'] = 'DRAFT'
            state['references'][0][flag] = 'false'
            self.assertTrue(validate(state))

    def test_malformed_state_cli_returns_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic-state.json'
            for field, value in (('references', [None]), ('release', []), ('screening', 0)):
                state = self.complete_state()
                state[field] = value
                path.write_text(json.dumps(state), encoding='utf-8')
                result = subprocess.run([sys.executable, 'validate_run.py', str(path)],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(json.loads(result.stdout)['valid'])
                self.assertNotIn('Traceback', result.stderr)

    def test_false_release_rejected(self):
        self.s['blockers']=['synthetic missing evidence']
        self.s['release']=dict(status='COMPLETE',qa_passed=False,storage_verified=False,
                               required_artifacts=['evidence_table'],artifacts=[],cited_reference_numbers=[1])
        errors=validate(self.s)
        for term in ('sufficiency','blockers','conclusion','QA','storage','citation','evidence_table'):
            self.assertTrue(any(term in x for x in errors), term)


if __name__ == '__main__':
    unittest.main()
