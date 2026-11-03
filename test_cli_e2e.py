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
