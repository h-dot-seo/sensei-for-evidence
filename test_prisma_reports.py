import copy
import json
import unittest
from pathlib import Path
from prisma_reports import report_flow


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(Path('examples/protocol.json').read_text())
        self.p['reports']=[dict(report_id='report-1',record_ids=['r1'],retrieval='retrieved',decision='include',study_id='s1',locator='synthetic section')]
    def test_report_study_and_output_reproducibility(self):
        r=report_flow(self.p)
        self.assertEqual(r['report_flow']['included_studies'],1)
        self.assertEqual(r['unmapped_records'],[])
        self.assertEqual(r,report_flow(self.p))
        self.assertIn('report-1',r['report_csv'])
    def test_exclusions_and_csv_formula(self):
        self.p['reports'][0].update(decision='exclude',reason='=synthetic formula')
        self.p['evidence']=[]; self.p['gaps']=[]
        r=report_flow(self.p)
        self.assertEqual(r['report_flow']['excluded'],1)
        self.assertIn("'=synthetic formula",r['report_csv'])
    def test_unretrieved_and_duplicate_report(self):
        self.p['reports'][0]['retrieval']='not_retrieved'
        with self.assertRaises(ValueError): report_flow(self.p)

    def test_full_text_exclusion_invalidates_extraction(self):
        self.p['reports'][0].update(decision='exclude',reason='outside scope')
        with self.assertRaisesRegex(ValueError,'included retrieved report'): report_flow(self.p)
        self.setUp(); self.p['reports'][0]['study_id']='other-study'
        with self.assertRaisesRegex(ValueError,'study ID conflicts'): report_flow(self.p)
        self.setUp(); self.p['reports'].append(copy.deepcopy(self.p['reports'][0]))
        with self.assertRaises(ValueError): report_flow(self.p)

class ReportProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/report-protocol.json').read_text())
        self.protocol['evidence'] = []
        self.protocol['gaps'] = []

    def test_blank_or_nontext_included_provenance_rejected(self):
        for field in ('report_id', 'locator', 'study_id'):
            for value in ('', '   ', '\n\t', None, 1, True, [], {}):
                protocol = copy.deepcopy(self.protocol)
                protocol['reports'][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    report_flow(protocol)

    def test_exclusion_and_retrieval_reasons_must_be_text(self):
        for state in (dict(retrieval='retrieved', decision='exclude'),
                      dict(retrieval='not_retrieved', decision='pending')):
            for value in ('   ', None, 1, [], {}):
                protocol = copy.deepcopy(self.protocol)
                protocol['reports'][0].update(state, reason=value)
                with self.subTest(state=state, value=value), self.assertRaisesRegex(ValueError, 'requires reason'):
                    report_flow(protocol)

    def test_report_container_shapes_rejected(self):
        for value in ('', {}, None, ['invalid'], [None]):
            self.protocol['reports'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                report_flow(self.protocol)

    def test_pending_report_does_not_require_unavailable_provenance(self):
        self.protocol['reports'][0] = dict(report_id='pending-report', record_ids=['r1'], retrieval='pending')
        result = report_flow(self.protocol)
        self.assertEqual(result['report_flow']['retrieval_pending'], 1)
        self.assertEqual(result['report_flow']['included_studies'], 0)
