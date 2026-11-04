"""Execute the documented synthetic appraisal path; no actual quality assessment."""
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from evidence_workflow import run
from prisma_reports import report_flow

ROOT=Path(__file__).resolve().parent


class AppraisalJourneyTests(unittest.TestCase):
    def test_ten_documented_commands_preserve_disagreement_and_show_stale_statement(self):
        doc=(ROOT/'docs/MANUAL_APPRAISAL_INTAKE.md').read_text(encoding='utf-8')
        commands=[line for block in re.findall(r'```sh\n(.*?)```',doc,re.S) for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),10)
        original=json.loads((ROOT/'examples/synthesis-review.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='sensei appraisal journey ') as td:
            output=Path(td)
            for command in commands:
                args=[str(ROOT/value) if value.endswith('.py') or value.startswith('examples/') else str(output/value[7:]) if value.startswith('OUTPUT/') else value for value in shlex.split(command)[1:]]
                if 'assemble' in args:
                    review=copy.deepcopy(json.loads((output/'appraisal-target.json').read_bytes())['review_document'])
                    self.assertIsNone(review['decision'])
                    review.update(receipt_id='fictional-appraisal-rehearsal',decision='import_appraisals',reviewer='Fictional import reviewer',reviewed_at='2026-11-04',rationale='Explicit synthetic bookkeeping review only.')
                    (output/'appraisal-review.json').write_text(json.dumps(review),encoding='utf-8')
                result=subprocess.run([sys.executable,*args],cwd=td,capture_output=True,timeout=90)
                self.assertEqual(result.returncode,0,(command,result.stderr))
            candidate=json.loads((output/'with-appraisals.json').read_bytes())
            self.assertEqual(len(candidate['appraisals']),3)
            self.assertEqual(len(candidate['evidence']),3)
            self.assertEqual({k:v for k,v in candidate.items() if k!='appraisals'},{k:v for k,v in original.items() if k!='appraisals'})
            self.assertEqual(candidate['appraisals'][0],original['appraisals'][0])
            before,after=run(original),run(candidate)
            self.assertEqual(before['flow'],after['flow'])
            self.assertEqual(report_flow(original)['report_flow'],report_flow(candidate)['report_flow'])
            self.assertEqual(before['synthesis']['statement_ledger'][0]['source_match_status'],'CURRENT_SOURCE')
            self.assertEqual(after['synthesis']['statement_ledger'][0]['source_match_status'],'STALE_SOURCE')
            self.assertEqual(after['synthesis']['statement_ledger'][0]['support_status'],'NOT_ASSESSED')
            self.assertEqual(after['appraisal']['evidence_without_recorded_appraisal'],['e3'])
            self.assertEqual(after['conclusion_readiness'],'NOT_READY')
            draft=json.loads((output/'appraisal-draft.json').read_bytes())
            self.assertIsNone(draft['appraisals'][0]['method'])
            self.assertTrue(all(v is None for v in draft['appraisals'][0]['domains'][0].values()))
            app=json.loads((output/'appraisal-application.json').read_bytes())
            self.assertEqual(app['receipt']['current_appraisal_validity'],'NOT_ASSESSED')


if __name__=='__main__':unittest.main()
