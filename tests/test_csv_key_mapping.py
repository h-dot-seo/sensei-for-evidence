"""Explicit same-column CSV mapping retains native values without guessing links."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

import bibliographic_intake as intake
import bibliographic_review as review

ROOT = Path(__file__).resolve().parents[1]


class CSVKeyMappingTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / 'examples/source-work-protocol.json').read_bytes())
        self.raw = (ROOT / 'examples/dialects/keyed-csv.csv').read_bytes()

    def prepare(self, raw=None, **mapping):
        return intake.prepare(self.protocol, self.raw if raw is None else raw,
                              'search-primary', '2026-11-04T00:00:00Z',
                              **dict(dict(id_column='Key', locator_column='Key'), **mapping))

    def test_same_key_mapping_preserves_all_original_values_and_occurrences(self):
        artifact = self.prepare()
        self.assertEqual(artifact['column_mapping'], {'id_column': 'Key', 'locator_column': 'Key'})
        rows = artifact['parsed_export']['record_rows']
        self.assertEqual(len(rows), 3)
        self.assertEqual([r['record_id'] for r in rows], ['fictional-a', 'fictional-b', 'fictional-a'])
        self.assertEqual([r['source_locator'] for r in rows], [r['record_id'] for r in rows])
        self.assertEqual([r['original_values']['URL'] for r in rows],
                         ['', 'https://example.invalid/fictional-b',
                          'https://example.invalid/fictional-a-alternate'])
        self.assertEqual([r['original_values']['DOI'] for r in rows], ['', '', ''])
        self.assertEqual(rows[0]['original_values']['Abstract'],
                         'Synthetic first line\nSynthetic second line')
        self.assertEqual(len({r['candidate_id'] for r in rows}), 3)
        self.assertTrue(artifact['parsed_export']['duplicate_record_ids'])
        self.assertEqual(artifact['parsed_export']['locator_conflicts'], [])
        self.assertEqual(artifact['source_export']['text'].encode('utf-8'), self.raw)
        self.assertTrue(intake.verify(artifact)['valid'])

    def test_bom_crlf_and_multiline_spans_are_retained(self):
        raw = b'\xef\xbb\xbf' + self.raw.replace(b'\n', b'\r\n')
        artifact = self.prepare(raw)
        self.assertEqual(artifact['source_export']['text'].encode('utf-8'), raw)
        self.assertEqual(artifact['source_export']['sha256'], hashlib.sha256(raw).hexdigest())
        rows = artifact['parsed_export']['record_rows']
        self.assertEqual(rows[0]['original_values']['Abstract'],
                         'Synthetic first line\r\nSynthetic second line')
        self.assertEqual((rows[0]['source_span']['line_start'], rows[0]['source_span']['line_end']), (2, 3))
        for row in rows:
            span = row['source_span']
            self.assertEqual(span['sha256'], hashlib.sha256(raw[span['byte_start']:span['byte_end']]).hexdigest())
        self.assertTrue(intake.verify(artifact)['valid'])

    def test_no_mapping_or_blank_selected_url_is_not_repaired(self):
        for mapping in ({'id_column': 'record_id', 'locator_column': 'source_locator'},
                        {'id_column': 'Key', 'locator_column': 'URL'},
                        {'id_column': 'key', 'locator_column': 'Key'}):
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                self.prepare(**mapping)

    def test_invalid_or_blank_selected_key_is_rejected(self):
        for raw in (b'Key,URL\n,\n', b'Key,URL\n   ,\n',
                    b'URL,Title\n,fictional\n', b'Key,URL\nfictional,,extra\n',
                    b'Key,URL\n\xff,\n'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                self.prepare(raw)

    def test_mapping_and_original_blank_values_are_bound_to_verification(self):
        artifact = self.prepare()
        for mutate in (lambda a: a['column_mapping'].update(locator_column='URL'),
                       lambda a: a['parsed_export']['record_rows'][0]['original_values'].update(URL='invented'),
                       lambda a: a['parsed_export']['record_rows'][0].update(source_locator='invented')):
            changed = copy.deepcopy(artifact)
            mutate(changed)
            changed['review_target']['target_sha256'] = intake.digest(
                {k: v for k, v in changed.items() if k != 'review_target'})
            with self.assertRaises(ValueError):
                intake.verify(changed)

    def test_template_remains_unfilled_and_protocol_unchanged(self):
        before = copy.deepcopy(self.protocol)
        artifact = self.prepare()
        draft = review.template(artifact)
        self.assertEqual(self.protocol, before)
        self.assertEqual(artifact['protocol_snapshot'], before)
        self.assertFalse(artifact['effects']['protocol_changed'])
        self.assertEqual(artifact['external_calls'], 0)
        self.assertEqual(artifact['review_status'], 'NOT_PERFORMED')
        self.assertEqual(artifact['record_identity_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(artifact['conclusion_readiness'], 'NOT_READY')
        self.assertIsNone(draft['review'])
        self.assertEqual(len(draft['resolutions']), 3)
        for row in draft['resolutions']:
            self.assertEqual(set(row), {'candidate_id', 'disposition', 'record_id', 'rationale'})
            for field in ('disposition', 'record_id', 'rationale'):
                self.assertIsNone(row[field])

    def test_documented_commands_execute_exactly_and_refuse_overwrite(self):
        document = (ROOT / 'docs/CSV_KEY_MAPPING.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        self.assertEqual(len(blocks), 1)
        lines = blocks[0].splitlines()
        self.assertEqual(len(lines), 3)
        before = (ROOT / 'examples/source-work-protocol.json').read_bytes()
        env = dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0')
        with tempfile.TemporaryDirectory(prefix='fictional keyed CSV ') as folder:
            commands = []
            for line in lines:
                tokens = shlex.split(line)
                self.assertEqual(tokens[0], 'python')
                command = [sys.executable] + [token.replace('OUTPUT', folder) for token in tokens[1:]]
                commands.append(command)
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                if tokens[1] == 'bibliographic_review.py':
                    self.assertIn(b'No identity choice or export-level review has been supplied.', result.stdout)
                else:
                    self.assertIn(b'NOT_READY', result.stdout)
            saved = Path(folder) / 'keyed-intake.json'
            artifact = json.loads(saved.read_bytes())
            self.assertEqual(artifact, self.prepare())
            draft_path = Path(folder) / 'keyed-review.json'
            self.assertEqual(json.loads(draft_path.read_bytes()), review.template(artifact))
            for command, output in ((commands[0], saved), (commands[2], draft_path)):
                original = output.read_bytes()
                repeated = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
                self.assertNotEqual(repeated.returncode, 0)
                self.assertEqual(output.read_bytes(), original)
        self.assertEqual((ROOT / 'examples/source-work-protocol.json').read_bytes(), before)
        self.assertEqual((ROOT / 'examples/dialects/keyed-csv.csv').read_bytes(), self.raw)


if __name__ == '__main__':
    unittest.main()
