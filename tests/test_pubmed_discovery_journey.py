"""Offline documented discovery-to-reviewed-collection rehearsal, synthetic IDs only."""
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

import bibliographic_review
from evidence_workflow import run

ROOT = Path(__file__).resolve().parents[1]


class DiscoveryJourneyTests(unittest.TestCase):
    def test_documented_offline_commands_require_separate_collection_review(self):
        doc = (ROOT / 'docs/PUBMED_DISCOVERY.md').read_text(encoding='utf-8')
        commands = [line for block in re.findall(r'```sh\n(.*?)```', doc, re.S)
                    for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands), 6)
        self.assertFalse(any(' fetch ' in command for command in commands))
        original = json.loads((ROOT / 'examples/pubmed-discovery-base.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='discovery journey ') as directory:
            output = Path(directory)
            for command in commands:
                args = [str(ROOT / value) if value.endswith('.py') or value.startswith('examples/')
                        else str(output / value[7:]) if value.startswith('OUTPUT/') else value
                        for value in shlex.split(command)[1:]]
                if 'target' in args:
                    choices = json.loads((output / 'pubmed-choices.json').read_bytes())
                    self.assertIsNone(choices['review'])
                    for index, row in enumerate(choices['resolutions']):
                        self.assertIsNone(row['disposition'])
                        row.update(disposition='new_record', record_id=f'fictional-record-{index + 1}',
                                   rationale='Explicit fictional identity choice for software rehearsal only.')
                    (output / 'pubmed-choices.json').write_text(json.dumps(choices), encoding='utf-8')
                result = subprocess.run([sys.executable, *args], cwd=directory, capture_output=True, timeout=90)
                self.assertEqual(result.returncode, 0, (command, result.stderr))
            discovery = json.loads((output / 'pubmed-discovery.json').read_bytes())
            intake = json.loads((output / 'pubmed-intake.json').read_bytes())
            review = json.loads((output / 'pubmed-collection-review.json').read_bytes())
            self.assertIsNone(review['review']['decision'])
            with self.assertRaises(ValueError):
                bibliographic_review.assemble(original, intake, review)
            review['review'].update(reviewer='Fictional rehearsal reviewer', reviewed_at='2026-11-04',
                                    rationale='Synthetic collection import only.', decision='import_for_screening')
            snapshot = copy.deepcopy(original)
            candidate = bibliographic_review.assemble(original, intake, review)['protocol_candidate']
            self.assertEqual(original, snapshot)
            self.assertEqual(candidate['search_plan'], original['search_plan'])
            self.assertEqual(candidate['screening'], [])
            self.assertEqual(candidate['evidence'], [])
            self.assertEqual(candidate['searches'][0]['record_ids'],
                             ['fictional-record-1', 'fictional-record-2', 'fictional-record-3'])
            self.assertFalse(candidate['searches'][0]['complete'])
            self.assertEqual(discovery['search_completeness'], 'NOT_ESTABLISHED')
            result = run(candidate)
            self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
            rows = result['bibliographic_collection']['row_ledger']
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(row['original_values']['discovery_request_id'] for row in rows))


if __name__ == '__main__':
    unittest.main()
