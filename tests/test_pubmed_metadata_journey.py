"""Execute documented synthetic discovery-to-metadata-to-review preparation."""
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


class MetadataJourneyTests(unittest.TestCase):
    def test_six_offline_commands_preserve_nonpositional_linkage_and_review_gate(self):
        doc = (ROOT / 'docs/PUBMED_METADATA.md').read_text(encoding='utf-8')
        commands = [line for block in re.findall(r'```sh\n(.*?)```', doc, re.S)
                    for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands), 6)
        self.assertFalse(any(' fetch ' in command for command in commands))
        original = json.loads((ROOT / 'examples/pubmed-discovery-base.json').read_bytes())
        with tempfile.TemporaryDirectory(prefix='metadata journey ') as directory:
            output = Path(directory)
            for command in commands:
                args = [str(ROOT / value) if value.endswith('.py') or value.startswith('examples/')
                        else str(output / value[7:]) if value.startswith('OUTPUT/') else value
                        for value in shlex.split(command)[1:]]
                completed = subprocess.run([sys.executable, *args], cwd=directory,
                                           capture_output=True, timeout=90)
                self.assertEqual(completed.returncode, 0, (command, completed.stderr))
            metadata = json.loads((output / 'metadata.json').read_bytes())
            derived = metadata['derived']
            self.assertEqual(derived['acquisition_status'], 'SELECTED_IDS_RECEIVED')
            self.assertEqual([row['pmid'] for row in derived['candidates']], ['13', '11'])
            by_pmid = {row['pmid']: row for row in derived['candidates']}
            self.assertEqual(by_pmid['13']['selected_discovery_occurrence_indices'], [2])
            self.assertEqual(by_pmid['11']['selected_discovery_occurrence_indices'], [0])
            self.assertEqual(by_pmid['11']['abstract_status'], 'NOT_PRESENT')
            self.assertEqual(by_pmid['11']['abstract_fields'], [])
            self.assertTrue(by_pmid['13']['abstract_fields'])
            for candidate in derived['candidates']:
                native = derived['responses'][candidate['response_index']]['parsed_export']['records'][candidate['response_record_index']]
                for field in candidate['title_fields'] + candidate['abstract_fields']:
                    original_field = native['fields'][field['field_index']]
                    self.assertIn(original_field['tag'], ['TI', 'AB'])
                    self.assertEqual(field['unfolded_text'], ' '.join(original_field['value_lines']))
            intake = json.loads((output / 'metadata-intake.json').read_bytes())
            choices = json.loads((output / 'metadata-choices.json').read_bytes())
            self.assertIsNone(choices['review'])
            for index, row in enumerate(choices['resolutions']):
                self.assertIsNone(row['disposition'])
                row.update(disposition='new_record', record_id=f'fictional-metadata-{index + 1}',
                           rationale='Explicit fictional identity choice, not scientific screening.')
            review = bibliographic_review.prepare_review(original, intake, choices)['review_document']
            with self.assertRaises(ValueError):
                bibliographic_review.assemble(original, intake, review)
            review['review'].update(reviewer='Fictional metadata reviewer', reviewed_at='2026-11-04',
                                    rationale='Synthetic collection import only.', decision='import_for_screening')
            snapshot = copy.deepcopy(original)
            candidate = bibliographic_review.assemble(original, intake, review)['protocol_candidate']
            self.assertEqual(original, snapshot)
            self.assertEqual(candidate['search_plan'], original['search_plan'])
            self.assertEqual(candidate['screening'], [])
            self.assertEqual(candidate['evidence'], [])
            self.assertFalse(candidate['searches'][0]['complete'])
            result = run(candidate)
            self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
            rows = result['bibliographic_collection']['row_ledger']
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row['original_values']['metadata_acquisition_sha256'] for row in rows))


if __name__ == '__main__':
    unittest.main()
