"""Execute documented fictional context intake without clinical assertions."""
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

ROOT=Path(__file__).resolve().parent


class ContextJourneyTests(unittest.TestCase):
    def test_eight_documented_commands_preserve_source_work_and_review_status(self):
        doc=(ROOT/'docs/MANUAL_CONTEXT_INTAKE.md').read_text(encoding='utf-8')
        commands=[line for block in re.findall(r'```sh\n(.*?)```',doc,re.S)
                  for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),8)
        original=json.loads((ROOT/'examples/source-context-protocol.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='context intake journey ') as directory:
            output=Path(directory)
            for command in commands:
                args=[str(ROOT/value) if value.endswith('.py') or value.startswith('examples/')
                      else str(output/value[7:]) if value.startswith('OUTPUT/') else value
                      for value in shlex.split(command)[1:]]
                if 'assemble' in args:
                    review=copy.deepcopy(json.loads((output/'context-target.json').read_bytes())['review_document'])
                    self.assertIsNone(review['decision'])
                    review.update(receipt_id='fictional-context-journey',decision='import_contexts',
                        reviewer='Fictional import reviewer',reviewed_at='2026-11-04',rationale='Synthetic bookkeeping only.')
                    (output/'context-review.json').write_text(json.dumps(review),encoding='utf-8')
                result=subprocess.run([sys.executable,*args],cwd=directory,capture_output=True,timeout=90)
                self.assertEqual(result.returncode,0,(command,result.stderr))
            candidate=json.loads((output/'with-contexts.json').read_bytes())
            self.assertEqual(candidate['contexts'][:2],original['contexts'])
            self.assertEqual(len(candidate['contexts']),4)
            self.assertEqual(candidate['evidence'],[])
            before,after=run(original),run(candidate)
            for key in ('flow','evidence','work_packages','planning','synthesis'):
                self.assertEqual(before[key],after[key])
            self.assertEqual(len(after['context']['unassigned_context_ids']),2)
            self.assertEqual(candidate['contexts'][2]['review_status'],'pending')
            self.assertNotIn('reviewer',candidate['contexts'][2])
            self.assertEqual(after['conclusion_readiness'],'NOT_READY')


if __name__=='__main__':unittest.main()
