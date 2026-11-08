import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliScenario(unittest.TestCase):
    def invoke(self,path):
        return subprocess.run([sys.executable,'prisma_reports.py',str(path)],capture_output=True,text=True,timeout=20)
    def test_search_screen_extract_work_and_reconcile_failure(self):
        source=Path('examples/report-protocol.json')
        first=self.invoke(source); self.assertEqual(first.returncode,0,first.stderr)
        self.assertEqual(first.stdout,self.invoke(source).stdout)
        output=json.loads(first.stdout)
        self.assertEqual(output['report_flow']['included_studies'],1)
        self.assertEqual(output['work_packages'][0]['evidence_ids'],['r1'])
        with tempfile.TemporaryDirectory() as folder:
            value=json.loads(source.read_text()); value['reports'][0].update(decision='exclude',reason='wrong model')
            path=Path(folder)/'protocol.json'; path.write_text(json.dumps(value))
            failed=self.invoke(path); self.assertNotEqual(failed.returncode,0)
            self.assertIn('reconcile screening first',failed.stderr); self.assertEqual(failed.stdout,'')
            value['evidence']=[]; value['gaps']=[]; path.write_text(json.dumps(value))
            resumed=self.invoke(path); self.assertEqual(resumed.returncode,0,resumed.stderr)
            self.assertEqual(json.loads(resumed.stdout)['report_flow']['excluded'],1)


class CompletePipelineScenario(unittest.TestCase):
    def test_plan_multi_result_context_report_and_bundle(self):
        protocol = json.loads(Path('examples/multi-result-protocol.json').read_text())
        planned = json.loads(Path('examples/planned-protocol.json').read_text())
        protocol['search_plan'] = planned['search_plan']
        protocol['searches'][0]['search_id'] = 'search-primary'
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'protocol.json'
            output = Path(folder)/'bundle.zip'
            source.write_text(json.dumps(protocol))
            created = subprocess.run([sys.executable, 'research_bundle.py', 'create', str(source), str(output)], capture_output=True, text=True, timeout=20)
            self.assertEqual(created.returncode, 0, created.stderr)
            checked = subprocess.run([sys.executable, 'research_bundle.py', 'verify', str(output)], capture_output=True, text=True, timeout=20)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            import zipfile
            with zipfile.ZipFile(output) as archive:
                record = json.loads(archive.read('research.json'))
                reports = json.loads(archive.read('reports.json'))
                self.assertEqual(record['search_plan_audit']['missing_search_ids'], ['search-secondary'])
                self.assertEqual(record['flow']['extracted'], 2)
                self.assertEqual(record['context']['review_pending'], ['ctx-guideline'])
                self.assertEqual(reports['report_flow']['reports_with_extraction'], 1)
                self.assertEqual(reports['extraction_pending_reports'], [])
                self.assertIn(b'Included reports without extraction: 0', archive.read('summary.md'))
            self.assertEqual(json.loads(checked.stdout)['conclusion_readiness'], 'NOT_READY')
