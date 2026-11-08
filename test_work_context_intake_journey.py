"""Execute the documented fictional context-to-existing-work continuation."""
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

import context_intake
from evidence_workflow import run

ROOT=Path(__file__).resolve().parent


class WorkContextJourneyTests(unittest.TestCase):
    def test_eight_documented_commands_link_only_selected_work_without_renewal(self):
        original=json.loads((ROOT/'examples/source-context-protocol.json').read_bytes())
        candidates=json.loads((ROOT/'examples/manual-context-candidates.json').read_bytes())
        review=context_intake.prepare(original,candidates)['review_document']
        review.update(receipt_id='fictional-prerequisite',decision='import_contexts',reviewer='Fictional reviewer',
            reviewed_at='2026-11-04',rationale='Synthetic prerequisite only.')
        base=context_intake.assemble(original,candidates,review)['protocol_candidate']
        doc=(ROOT/'docs/WORK_CONTEXT_INTAKE.md').read_text(encoding='utf-8')
        commands=[line for block in re.findall(r'```sh\n(.*?)```',doc,re.S)
                  for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),8)
        with tempfile.TemporaryDirectory(prefix='work context journey ') as directory:
            output=Path(directory)
            (output/'with-contexts.json').write_text(json.dumps(base),encoding='utf-8')
            for command in commands:
                args=[str(ROOT/value) if value.endswith('.py') or value.startswith('examples/')
                      else str(output/value[7:]) if value.startswith('OUTPUT/') else value
                      for value in shlex.split(command)[1:]]
                if 'assemble' in args:
                    target=json.loads((output/'work-context-target.json').read_bytes())
                    review=copy.deepcopy(target['review_document']);self.assertIsNone(review['decision'])
                    self.assertEqual(len(target['target']['changed_work_source_targets']),2)
                    review.update(receipt_id='fictional-link-review',decision='append_work_contexts',
                        reviewer='Fictional link reviewer',reviewed_at='2026-11-04',rationale='Synthetic link only.')
                    (output/'work-context-review.json').write_text(json.dumps(review),encoding='utf-8')
                result=subprocess.run([sys.executable,*args],cwd=directory,capture_output=True,timeout=90)
                self.assertEqual(result.returncode,0,(command,result.stderr))
            after=json.loads((output/'with-work-context.json').read_bytes())
            self.assertEqual(after['gaps'][0]['context_ids'],['ctx-source-guideline','ctx-source-guideline-supplied'])
            self.assertEqual(after['gaps'][1],base['gaps'][1])
            self.assertEqual(after['contexts'],base['contexts'])
            before_r,after_r=run(base),run(after)
            self.assertEqual(before_r['flow'],after_r['flow'])
            self.assertEqual(before_r['execution_order'],after_r['execution_order'])
            self.assertEqual(after_r['context']['unassigned_context_ids'],['ctx-source-development-supplied'])
            self.assertEqual(after_r['conclusion_readiness'],'NOT_READY')


if __name__=='__main__':unittest.main()
