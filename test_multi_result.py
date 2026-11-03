import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import build_bundle, verify


class MultiResultTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/multi-result-protocol.json').read_text())

    def test_multiple_results_do_not_inflate_record_or_study_counts(self):
        result = run(self.protocol)
        self.assertEqual(result['flow']['extracted'], 2)
        self.assertEqual(result['flow']['extracted_records'], 1)
        self.assertEqual(result['flow']['extracted_studies'], 1)
        self.assertEqual(result['extraction_pending'], [])
        self.assertEqual(result['extraction_completeness'], 'NOT_ESTABLISHED')
        reports = report_flow(self.protocol)
        self.assertEqual(reports['report_flow']['included_studies'], 1)
        self.assertEqual({r['evidence_id']: r['record_id'] for r in reports['evidence']}, {'e1': 'r1', 'e2': 'r1'})
        self.assertEqual(reports['extraction_completeness'], 'NOT_ESTABLISHED')
        self.assertEqual([r['evidence_id'] for r in result['evidence']], ['e1', 'e2'])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_legacy_ids_default_to_record_ids_without_input_mutation(self):
        protocol = json.loads(Path('examples/context-protocol.json').read_text())
        original = copy.deepcopy(protocol)
        result = run(protocol)
        self.assertEqual(result['evidence'][0]['evidence_id'], 'r1')
        self.assertEqual(protocol, original)
        self.assertEqual(result['work_packages'][0]['evidence_ids'], ['r1'])

    def test_duplicate_and_invalid_extraction_ids_rejected(self):
        for value in ('e1', '', '   ', None, [], 1):
            self.protocol['evidence'][1]['evidence_id'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'evidence IDs'):
                run(self.protocol)

    def test_duplicate_implicit_record_id_remains_rejected(self):
        for row in self.protocol['evidence']:
            row.pop('evidence_id')
        with self.assertRaisesRegex(ValueError, 'evidence IDs'):
            run(self.protocol)

    def test_context_and_work_links_address_results_not_record_aliases(self):
        result = run(self.protocol)
        self.assertEqual(result['work_packages'][0]['evidence_ids'], ['e1', 'e2'])
        for context in result['context']['context_ledger']:
            self.assertEqual(context['linked_study_ids'], ['s1'])
        self.protocol['gaps'][0]['evidence_ids'] = ['r1']
        with self.assertRaisesRegex(ValueError, 'unknown evidence'):
            run(self.protocol)

    def test_pending_records_are_distinct_from_result_ids(self):
        self.protocol['screening'][1]['decision'] = 'include'
        result = run(self.protocol)
        self.assertEqual(result['extraction_pending'], ['r2'])
        self.assertEqual(result['flow']['extracted_records'], 1)

    def test_full_text_exclusion_invalidates_all_results(self):
        self.protocol['reports'][0].update(decision='exclude', reason='outside scope')
        with self.assertRaisesRegex(ValueError, 'reconcile screening first'):
            report_flow(self.protocol)
        self.protocol['reports'][0]['decision'] = 'include'
        self.protocol['evidence'][1]['study_id'] = 'different-study'
        with self.assertRaisesRegex(ValueError, 'study ID conflicts'):
            report_flow(self.protocol)

    def test_record_only_cannot_assign_two_study_ids_to_one_source(self):
        self.protocol.pop('reports')
        self.protocol['evidence'][1]['study_id'] = 'different-study'
        with self.assertRaisesRegex(ValueError, 'study ID conflicts'):
            build_bundle(json.dumps(self.protocol).encode())

    def test_bundle_preserves_positive_and_null_results(self):
        bundle = build_bundle(json.dumps(self.protocol).encode())
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            result = json.loads(archive.read('research.json'))
            self.assertEqual(result['evidence'][1]['result'], 'no change observed')
            self.assertEqual(result['flow']['extracted'], 2)
            self.assertEqual(result['flow']['extracted_studies'], 1)
            self.assertIn(b'Extracted result rows: 2', archive.read('summary.md'))
            self.assertIn(b'Source records with extraction: 1', archive.read('summary.md'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bundle.zip'
            path.write_bytes(bundle)
            self.assertTrue(verify(path)['valid'])
