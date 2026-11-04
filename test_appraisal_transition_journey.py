"""Run documented synthetic appraisal archive commands, without scientific review."""
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

import appraisal_intake
import appraisal_source_review
import appraisal_transition_bundle

ROOT = Path(__file__).resolve().parent


class AppraisalTransitionJourneyTests(unittest.TestCase):
    def test_documented_archive_replays_import_and_retains_comparison_inputs(self):
        original = json.loads((ROOT / 'examples/synthesis-review.json').read_bytes())
        candidates = json.loads((ROOT / 'examples/manual-appraisal-candidates.json').read_bytes())
        review = appraisal_intake.prepare(original, candidates)['review_document']
        review.update(receipt_id='fictional-archive-journey', reviewer='Fictional reviewer',
            decision='import_appraisals', reviewed_at='2026-11-04', rationale='Synthetic assertions only.')
        application = appraisal_intake.assemble(original, candidates, review)
        endpoint = application['protocol_candidate']
        snapshot = copy.deepcopy((original, application, endpoint))
        doc = (ROOT / 'docs/APPRAISAL_TRANSITION_BUNDLES.md').read_text(encoding='utf-8')
        commands = [line for block in re.findall(r'```sh\n(.*?)```', doc, re.S)
                    for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands), 2)
        with tempfile.TemporaryDirectory(prefix='appraisal archive journey ') as directory:
            output = Path(directory)
            (output / 'appraisal-application.json').write_text(json.dumps(application), encoding='utf-8')
            (output / 'with-appraisals.json').write_text(json.dumps(endpoint), encoding='utf-8')
            for command in commands:
                args = [str(ROOT / token) if token.endswith('.py') or token.startswith('examples/')
                        else str(output / token[7:]) if token.startswith('OUTPUT/') else token
                        for token in shlex.split(command)[1:]]
                result = subprocess.run([sys.executable, *args], cwd=directory, capture_output=True, timeout=90)
                self.assertEqual(result.returncode, 0, (command, result.stderr))
                self.assertIn(b'Conclusion: NOT_READY', result.stdout)
            result = appraisal_transition_bundle.verify(output / 'appraisal-segment.zip')
            self.assertEqual(result['supported_steps'], 1)
            self.assertEqual(result['explicit_appraisal_ids_by_step'],
                             [[row['appraisal_id'] for row in candidates['appraisals']]])
            comparison = appraisal_source_review.review(original, application, endpoint)
            self.assertEqual(comparison['counts']['appraisal']['UNCHANGED'], 2)
        self.assertEqual((original, application, endpoint), snapshot)


if __name__ == '__main__':
    unittest.main()
