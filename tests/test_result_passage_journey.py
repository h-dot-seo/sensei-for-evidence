"""Run documented synthetic source passage checks before independent result intake."""
import copy
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

from artifact_review import secure_open_supported
from evidence_workflow import run

ROOT = Path(__file__).resolve().parents[1]


class PassageJourneyTests(unittest.TestCase):
    @unittest.skipUnless(secure_open_supported(), 'secure local source reading requires supported POSIX descriptors')
    def test_six_documented_commands_keep_quote_matching_separate_from_import(self):
        doc = (ROOT / 'docs/RESULT_PASSAGE_CHECK.md').read_text(encoding='utf-8')
        commands = [line for block in re.findall(r'```sh\n(.*?)```', doc, re.S)
                    for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands), 6)
        original = json.loads((ROOT / 'examples/result-passage-protocol.json').read_bytes())
        candidates = json.loads((ROOT / 'examples/result-passage-candidates.json').read_bytes())
        original_copy, candidate_copy = copy.deepcopy(original), copy.deepcopy(candidates)
        source = (ROOT / 'examples/result-passage-source.txt').read_bytes()
        with tempfile.TemporaryDirectory(prefix='result passage journey ') as directory:
            output = Path(directory)
            for command in commands:
                args = [str(ROOT / value) if value.endswith('.py') or value == 'examples' or value.startswith('examples/')
                        else str(output / value[7:]) if value.startswith('OUTPUT/') else value
                        for value in shlex.split(command)[1:]]
                if 'assemble' in args:
                    target = json.loads((output / 'result-target.json').read_bytes())
                    review = target['review_document']
                    self.assertIsNone(review['decision'])
                    review.update(receipt_id='fictional-passage-review', reviewer='Fictional reviewer',
                                  reviewed_at='2026-11-04', rationale='Explicit fictional result import after separate inspection.',
                                  decision='import_results')
                    (output / 'completed-result-review.json').write_text(json.dumps(review), encoding='utf-8')
                completed = subprocess.run([sys.executable, *args], cwd=directory, capture_output=True, timeout=90)
                self.assertEqual(completed.returncode, 0, (command, completed.stderr))
            checked = json.loads((output / 'passage-check.json').read_bytes())
            self.assertTrue(checked['all_requested_bytes_match'])
            self.assertTrue(checked['all_requested_passages_match'])
            self.assertEqual([row['status'] for row in checked['passages']], ['TEXT_MATCH', 'TEXT_MATCH'])
            for row in checked['passages']:
                self.assertEqual(row['expected_quote'], row['observed_quote'])
                self.assertEqual(row['field_value'], candidates['candidates'][row['candidate_index']]['evidence'][row['evidence_field']])
            catalog = json.loads((output / 'source-catalog.json').read_bytes())
            lines = catalog['sources'][0]['physical_lines']
            self.assertEqual(''.join(line['text'] for line in lines).encode('utf-8'), source)
            self.assertEqual(lines[0]['byte_start'], 0)
            self.assertEqual(lines[-1]['byte_end'], len(source))
            self.assertEqual(hashlib.sha256(source).hexdigest(), original['report_sources'][0]['document_sha256'])
            application = json.loads((output / 'result-application.json').read_bytes())
            self.assertEqual(application['receipt']['document_bytes_verification'], 'NOT_PERFORMED')
            result = json.loads((output / 'results-protocol.json').read_bytes())
            self.assertEqual(result['evidence'], original['evidence'] + [row['evidence'] for row in candidates['candidates']])
            self.assertEqual({key: value for key, value in result.items() if key != 'evidence'},
                             {key: value for key, value in original.items() if key != 'evidence'})
            self.assertEqual((original, candidates), (original_copy, candidate_copy))
            before_flow, after = run(original)['flow'], run(result)
            for key in ('identified','duplicates','unique_records','screened','pending','excluded','included'):
                self.assertEqual(before_flow[key],after['flow'][key])
            self.assertEqual(after['flow']['extracted'],len(candidates['candidates']))
            self.assertEqual(after['conclusion_readiness'], 'NOT_READY')


if __name__ == '__main__':
    unittest.main()
