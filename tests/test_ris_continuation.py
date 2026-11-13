"""Synthetic declared continuation grammar, provenance and exact guide replay."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import bibliographic_review
import ris_continuation_parser as parser
import ris_continuation_intake as intake
import ris_intake

ROOT = Path(__file__).resolve().parents[1]

class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT/'examples/dialects/continuation.ris').read_bytes()
        self.protocol = json.loads((ROOT/'examples/source-work-protocol.json').read_bytes())

    def parse(self, raw):
        return parser.parse_export(raw, dialect=parser.DIALECT)

    def prepare(self, raw=None):
        return intake.prepare(self.protocol, self.raw if raw is None else raw,
                              'search-primary', '2026-11-04T00:00:00Z', dialect=parser.DIALECT)

    def test_explicit_dialect_and_paragraphs(self):
        parsed = self.parse(self.raw)
        self.assertEqual(len(parsed['records']), 2)
        abstract = parsed['records'][0]['fields'][2]
        self.assertEqual(abstract['value_lines'], ['Fictional first paragraph',
            'An unindented continuation', '', 'Another fictional paragraph', 'Six-space continuation'])
        for dialect in (None, '', 'ris-indented', [], parser.DIALECT.upper()):
            with self.assertRaises(ValueError):
                parser.parse_export(self.raw, dialect=dialect)
        with self.assertRaises(TypeError):
            parser.parse_export(self.raw)
        with self.assertRaises(ValueError):
            ris_intake.parse_export(self.raw)

    def test_exact_full_file_and_field_spans(self):
        for raw in (self.raw, b'\xef\xbb\xbf\r\n' + self.raw.replace(b'\n', b'\r\n'),
                    self.raw.replace(b'\n', b'\r').rstrip(b'\r')):
            parsed = self.parse(raw)
            spans = parsed['ignored_blank_spans'] + [r['source_span'] for r in parsed['records']]
            cursor = 0
            for span in sorted(spans, key=lambda s:s['byte_start']):
                self.assertEqual(span['byte_start'], cursor)
                value = raw[span['byte_start']:span['byte_end']]
                self.assertEqual(hashlib.sha256(value).hexdigest(), span['sha256'])
                cursor = span['byte_end']
            self.assertEqual(cursor, len(raw))
            for record in parsed['records']:
                self.assertEqual(''.join(f['raw_text'] for f in record['fields']), record['raw_text'])
                for field in record['fields']:
                    span = field['source_span']; value = raw[span['byte_start']:span['byte_end']]
                    self.assertEqual(value, field['raw_text'].encode())
                    self.assertEqual(hashlib.sha256(value).hexdigest(), span['sha256'])
            artifact = self.prepare(raw)
            self.assertEqual(artifact['source_export']['text'].encode(), raw)
            self.assertTrue(intake.verify(artifact)['valid'])

    def test_tag_like_lines_rejected_not_repaired(self):
        for line in (b'AB - one', b'ab  - lower', b'ABC  - three', b'ABCD  - four',
                     b'\tAB  - tab', b'      AB - indented', b'plain\ttext', b' AB  - spaced'):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, 'line 3:'):
                self.parse(b'TY  - JOUR\nAB  - text\n' + line + b'\nER  -\n')

    def test_framing_and_orphans_fail_closed(self):
        for raw, line in [(b'orphan\n',1), (b'TY  - JOUR\ntext\nER  -\n',2),
            (b'TY  - JOUR\n\nER  -\n',2), (b'TY  - JOUR\nTI  - text\nTY  - JOUR\n',3),
            (b'TY  - JOUR\nTI  - text\nER  - bad\n',3),
            (b'TY  - JOUR\nTI  - text\nER  -\ntrailing\n',4),
            (b'TY  - JOUR\nTI  - text\n',1)]:
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, f'line {line}:'):
                self.parse(raw)

    def test_tag_shaped_abstract_text_is_separate_field_or_framing(self):
        parsed = self.parse(b'TY  - JOUR\nAB  - first\nAB  - second\nER  -\n')
        self.assertEqual([f['tag'] for f in parsed['records'][0]['fields']], ['TY','AB','AB','ER'])
        with self.assertRaisesRegex(ValueError, 'line 4:'):
            self.parse(b'TY  - JOUR\nAB  - first\nER  -\nlater narrative\n')

    def test_invalid_bytes_and_resource_limits(self):
        for raw in (b'', b'\xff', b'\x00'):
            with self.assertRaises(ValueError): self.parse(raw)
        for name, limit in [('MAX_EXPORT_BYTES', 5), ('MAX_RECORDS', 1), ('MAX_PHYSICAL_LINES', 2)]:
            with patch.object(parser, name, limit), self.assertRaises(ValueError): self.parse(self.raw)

    def test_bound_dialect_and_tampering_rejected(self):
        artifact = self.prepare()
        self.assertEqual(artifact['source_export']['format'], parser.DIALECT)
        self.assertIn(parser.DIALECT, artifact['mode'])
        self.assertTrue(intake.verify(artifact)['valid'])
        for path, value in [(('source_export','format'), 'ris-indented'), (('mode',), 'local_ris_preparation'),
            (('source_export','text'), artifact['source_export']['text']+'\n'),
            (('engine_sha256','ris_continuation_parser.py'), '0'*64),
            (('parsed_export','physical_lines'), 1), (('extra',), True)]:
            changed = copy.deepcopy(artifact); target = changed
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value
            with self.assertRaises(ValueError): intake.verify(changed)

    def test_native_formats_not_guessed_or_interchanged(self):
        strict_raw = b'TY  - JOUR\nTI  - fictional\nER  -\n'
        strict = ris_intake.prepare(self.protocol, strict_raw, 'search-primary', '2026-11-04T00:00:00Z')
        declared = self.prepare(strict_raw)
        with self.assertRaises(ValueError): intake.verify(strict)
        with self.assertRaises(ValueError): ris_intake.verify(declared)
        for key in ('review_status','record_identity_verification','conclusion_readiness'):
            self.assertEqual(declared[key], strict[key])
        self.assertEqual(declared['protocol_snapshot'], self.protocol)
        self.assertFalse(declared['effects']['protocol_changed'])

    def test_new_wrapper_cli_exclusive_output_and_explicit_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            retained = root/'wrapper.json'
            retained.write_bytes(intake.artifact_bytes(self.prepare()))
            output = root/'output.json'
            output.write_bytes(b'keep-existing-bytes')
            preview = ['preview', 'examples/source-work-protocol.json',
                'examples/dialects/continuation.ris', '--search-id', 'search-primary',
                '--searched-at', '2026-11-04T00:00:00Z', '--output', str(output)]
            commands = [preview, preview+['--dialect', 'ris-indented'],
                preview+['--dialect', parser.DIALECT],
                ['verify', str(retained), '--intake-output', str(output)],
                ['verify', str(retained), '--csv-output', str(output)]]
            for args in commands:
                checked = subprocess.run([sys.executable, 'ris_continuation_intake.py', *args],
                                         cwd=ROOT, capture_output=True)
                self.assertNotEqual(checked.returncode, 0, args)
                self.assertEqual(output.read_bytes(), b'keep-existing-bytes')
                self.assertEqual(retained.read_bytes(), intake.artifact_bytes(self.prepare()))

    def test_documented_commands_exactly_and_exclusive_outputs(self):
        blocks = re.findall(r'```sh\n(.*?)```', (ROOT/'docs/RIS_CONTINUATION_INTAKE.md').read_text(), re.S)
        self.assertEqual(len(blocks), 1)
        commands = [line for line in blocks[0].splitlines() if line.strip()]
        self.assertEqual(len(commands), 4)
        with tempfile.TemporaryDirectory() as td:
            import shlex
            for command in commands:
                args = shlex.split(command.replace('OUTPUT/', td+'/'))
                args[0] = sys.executable
                result = subprocess.run(args, cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'NOT_READY', subprocess.run([sys.executable, 'ris_continuation_intake.py',
                'verify', td+'/continuation.json', '--text'], cwd=ROOT, capture_output=True).stdout)
            self.assertNotEqual(subprocess.run(args, cwd=ROOT, capture_output=True).returncode, 0)
            artifact = json.loads((Path(td)/'continuation.json').read_bytes())
            self.assertTrue(intake.verify(artifact)['valid'])
            draft = json.loads((Path(td)/'continuation-review.json').read_bytes())
            self.assertEqual(draft, bibliographic_review.template(artifact['csv_intake']))
            self.assertIsNone(draft['review'])
            self.assertEqual(len(draft['resolutions']), 2)
            for row in draft['resolutions']:
                for key in ('disposition', 'record_id', 'rationale'):
                    self.assertIsNone(row[key])
            self.assertEqual((ROOT/'examples/dialects/continuation.ris').read_bytes(), self.raw)
