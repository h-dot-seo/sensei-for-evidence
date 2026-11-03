import copy
import io
import json
from pathlib import Path
import unittest
import zipfile
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import build_bundle
from validate_run import validate


class PageLedgerTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/paged-protocol.json').read_text())

    def test_pages_reconcile_without_census_claim(self):
        result = run(self.protocol)
        audit = result['coverage'][0]['page_audit']
        self.assertEqual(audit['status'], 'RECONCILED')
        self.assertEqual(audit['page_count'], 2)
        self.assertEqual(audit['record_occurrences'], 2)
        self.assertEqual(audit['unique_records'], 2)
        self.assertTrue(result['coverage'][0]['complete'])
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')

    def test_omitted_page_ledger_is_not_zero_results(self):
        self.protocol['searches'][0].pop('pages')
        audit = run(self.protocol)['coverage'][0]['page_audit']
        self.assertEqual(audit['status'], 'NOT_SUPPLIED')
        self.assertIsNone(audit['unique_records'])
        self.protocol['searches'][0].update(record_ids=[], total_count=0, pages=[dict(page_number=1, record_ids=[], has_more=False)])
        for key in ('screening', 'evidence', 'gaps', 'contexts', 'reports'):
            self.protocol[key] = []
        result = run(self.protocol)
        self.assertEqual(result['coverage'][0]['page_audit']['unique_records'], 0)
        self.assertEqual(result['coverage'][0]['page_audit']['status'], 'RECONCILED')
        self.assertTrue(result['coverage'][0]['complete'])

    def test_missing_or_reordered_pages_block_completion(self):
        for numbers in ((1,3), (2,1)):
            protocol = copy.deepcopy(self.protocol)
            for page, number in zip(protocol['searches'][0]['pages'], numbers):
                page['page_number'] = number
            with self.subTest(numbers=numbers):
                result = run(protocol)
                self.assertIn('page_sequence_unresolved', result['coverage'][0]['issues'])
                self.assertFalse(result['coverage'][0]['complete'])

    def test_final_or_intermediate_paging_flags_must_match(self):
        for index, value in ((0,False), (1,True), (1,None), (1,0)):
            protocol = copy.deepcopy(self.protocol)
            protocol['searches'][0]['pages'][index]['has_more'] = value
            with self.subTest(index=index, value=value):
                self.assertIn('page_pagination_unresolved', run(protocol)['coverage'][0]['issues'])
        for flag in ('truncated', 'pagination_limited', 'field_pages_pending'):
            protocol = copy.deepcopy(self.protocol)
            protocol['searches'][0]['pages'][1][flag] = True
            result = run(protocol)
            self.assertFalse(result['coverage'][0]['complete'])
            self.assertIn('page_' + flag + '_unresolved', result['coverage'][0]['issues'])

    def test_overlap_requires_reconciliation_even_if_unique_count_matches(self):
        self.protocol['searches'][0]['pages'][1]['record_ids'].insert(0,'r1')
        result = run(self.protocol)
        self.assertIn('page_record_overlap', result['coverage'][0]['issues'])
        self.assertEqual(result['coverage'][0]['page_audit']['record_occurrences'],3)
        self.assertEqual(result['coverage'][0]['page_audit']['unique_records'],2)
        self.assertFalse(result['coverage'][0]['complete'])

    def test_page_record_sets_and_errors_exposed(self):
        self.protocol['searches'][0]['pages'][1].update(record_ids=['r3'],error='synthetic timeout')
        issues = run(self.protocol)['coverage'][0]['issues']
        self.assertIn('page_record_set_mismatch', issues)
        self.assertIn('page_error_recorded', issues)

    def test_invalid_shapes_ids_and_numbers_rejected(self):
        for value in ([],None,{},[None],[dict(page_number=True,record_ids=['r1'])],
                      [dict(page_number=1,record_ids=['r1','r1'])]):
            self.protocol['searches'][0]['pages'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                run(self.protocol)

    def test_report_and_bundle_preserve_page_audit(self):
        self.protocol['searches'][0]['pages'][1]['has_more'] = True
        result = run(self.protocol)
        reports = report_flow(self.protocol)
        self.assertEqual(reports['search_plan_audit'], result['search_plan_audit'])
        self.assertEqual(reports['search_plan_audit']['search_plan_ledger'][0]['page_audit']['status'], 'UNRESOLVED')
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(self.protocol).encode()))) as archive:
            self.assertIn(b'Incomplete planned searches: 1', archive.read('summary.md'))
            self.assertEqual(json.loads(archive.read('research.json'))['coverage'][0]['page_audit']['status'],'UNRESOLVED')
        self.protocol.pop('search_plan')
        reports = report_flow(self.protocol)
        self.assertEqual(reports['search_coverage'][0]['page_audit']['status'], 'UNRESOLVED')
        self.assertIn('page_pagination_unresolved', reports['search_coverage'][0]['issues'])

    def test_state_validator_parity_and_invalid_pages_are_errors(self):
        state = dict(project_id='synthetic',research_question='Synthetic?',run_id='demo',phase='discovery',gate='intent',evidence_sufficiency='UNASSESSED',conclusion_readiness='NOT_READY',next_action='Review')
        search = dict(self.protocol['searches'][0],enumerated_ids=['r1','r2'])
        state['searches'] = [search]
        self.assertEqual(validate(state), [])
        search['pages'][1]['has_more'] = True
        self.assertTrue(any('page_pagination_unresolved' in error for error in validate(state)))
        search['pages'] = None
        self.assertTrue(any('nonempty list' in error for error in validate(state)))
        search['complete'] = False
        self.assertTrue(any('nonempty list' in error for error in validate(state)))
        search['pages'] = [dict(page_number=1, record_ids=['r1'], has_more=True)]
        self.assertEqual(validate(state), [])
