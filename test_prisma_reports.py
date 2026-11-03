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
