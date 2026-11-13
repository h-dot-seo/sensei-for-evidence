"""Synthetic, offline edited screening sheet intake and exact replay."""
import base64
import copy
import csv
import hashlib
import io
import json
import re
import shlex
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import screening_sheet
import screening_sheet_intake as intake
from tests.test_screening_reviews import protocol

ROOT = Path(__file__).resolve().parents[1]


def rewrite(raw, edit):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    rows = list(reader)
    edit(rows)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, reader.fieldnames, lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def fill(rows):
    rows[0].update(review_id='synthetic-review', reviewer='synthetic-reader', reviewed_at='2026-11-14',
                   decision='unclear', rationale='Synthetic supplied position only.', source_locator='synthetic:row-1')


def review(target):
    return dict(target['review_document'], receipt_id='synthetic-import', reviewer='synthetic-importer',
                reviewed_at='2026-11-14', rationale='Record these synthetic supplied positions only.')


class ScreeningSheetIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()
        self.blank = screening_sheet.export_sheet(self.p)[0]
        self.raw = rewrite(self.blank, fill)

    def test_append_preserves_every_other_field_and_input(self):
        original = copy.deepcopy(self.p)
        target = intake.prepare(self.p, self.raw)
        self.assertEqual(target['review_document']['decision'], 'import_screening_reviews')
        self.assertIsNone(target['review_document']['reviewer'])
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            app = intake.assemble(self.p, self.raw, review(target))
            self.assertTrue(intake.verify(self.p, app)['valid'])
        self.assertEqual(self.p, original)
        candidate = copy.deepcopy(app['protocol_candidate'])
        candidate.pop('screening_reviews')
        self.assertEqual(candidate, original)
        self.assertEqual(base64.b64decode(app['receipt']['sheet_base64']), self.raw)
        t = app['receipt']['target']
        self.assertEqual(t['sheet_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(t['sheet_bytes'], len(self.raw))
        for row in t['parsed_human_rows']:
            span = row['source_span']
            self.assertEqual(hashlib.sha256(self.raw[span['byte_start']:span['byte_end']]).hexdigest(), span['sha256'])
        self.assertEqual(len(t['appended_positions']), 1)
        self.assertEqual(len(t['skipped_blank_human_rows']), len(t['parsed_human_rows'])-1)
        self.assertEqual(t['negative_claims']['adjudication'], 'NOT_PERFORMED')

    def test_blank_partial_and_invalid_human_fields(self):
        with self.assertRaises(ValueError):
            intake.prepare(self.p, self.blank)
        changes = {'reviewer':'', 'rationale':' ', 'reviewed_at':'11/14/2026',
                   'decision':'accept', 'review_id':'=formula', 'source_locator':"'=formula"}
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.prepare(self.p, rewrite(self.raw, lambda rows: rows[0].update({key:value})))
        for value in ['@formula', '+formula', '-formula', '\ttext', '\ntext', ' text', "'literal"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                intake.prepare(self.p, rewrite(self.raw, lambda rows: rows[0].update(rationale=value)))

    def test_every_readonly_cell_is_exact_and_stale_protocol_fails(self):
        for key in screening_sheet.BASE_COLUMNS:
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.prepare(self.p, rewrite(self.raw, lambda rows: rows[0].update({key:rows[0][key]+'x'})))
        changed = copy.deepcopy(self.p)
        changed['version'] += '-changed'
        with self.assertRaises(ValueError):
            intake.prepare(changed, self.raw)
        changed = copy.deepcopy(self.p)
        changed['inclusion_criteria'].append('new synthetic criterion')
        with self.assertRaises(ValueError):
            intake.prepare(changed, self.raw)

    def test_duplicates_and_existing_pairs_are_not_superseded(self):
        with self.assertRaises(ValueError):
            intake.prepare(self.p, rewrite(self.raw, lambda rows: rows.append(copy.deepcopy(rows[0]))))
        app = intake.assemble(self.p, self.raw, review(intake.prepare(self.p, self.raw)))
        existing = app['protocol_candidate']
        fresh = rewrite(screening_sheet.export_sheet(existing)[0], fill)
        with self.assertRaises(ValueError):
            intake.prepare(existing, fresh)
        fresh = rewrite(fresh, lambda rows: rows[0].update(review_id='another-id'))
        with self.assertRaises(ValueError):
            intake.prepare(existing, fresh)
        fresh = rewrite(fresh, lambda rows: rows[0].update(reviewer='different-reader'))
        second = intake.assemble(existing, fresh, review(intake.prepare(existing, fresh)))
        self.assertEqual(second['protocol_candidate']['screening_reviews'][:1], existing['screening_reviews'])

    def test_formula_like_ids_round_trip_without_guessing(self):
        ids = ['=id', "'=id", '-id', '+id', '@id', ' id', '\tid', '한국어']
        self.p['searches'][0]['record_ids'] = ids
        self.p['searches'][0]['total_count'] = len(ids)
        self.p['screening'] = []
        def filled(rows):
            for index, row in enumerate(rows):
                fill([row])
                row['review_id'] = 'synthetic-'+str(index)
        raw = rewrite(screening_sheet.export_sheet(self.p)[0], filled)
        app = intake.assemble(self.p, raw, review(intake.prepare(self.p, raw)))
        self.assertEqual({row['record_id'] for row in app['protocol_candidate']['screening_reviews']}, set(ids))

    def test_display_cells_and_header_changes_rejected(self):
        raw = rewrite(screening_sheet.export_sheet(self.p, ['title'])[0], fill)
        self.assertTrue(intake.prepare(self.p, raw))
        with self.assertRaises(ValueError):
            intake.prepare(self.p, rewrite(raw, lambda rows: rows[0].update({'readonly_display:title':'altered'})))
        with self.assertRaises(ValueError):
            intake.prepare(self.p, raw.replace(b'"reviewer"', b'"person"', 1))

    def test_malformed_bytes_and_limits(self):
        for raw in [b'', b'\xff', self.raw+b'\x00', self.raw.replace(b'"record_id"',b'"record_id", "extra"',1)]:
            with self.subTest(raw=raw[:10]), self.assertRaises(ValueError):
                intake.prepare(self.p, raw)
        with patch.object(intake, 'MAX_POSITIONS', 0), self.assertRaises(ValueError):
            intake.prepare(self.p, self.raw)

    def test_exact_bytes_bom_crlf_multiline_and_tamper_detection(self):
        raw = rewrite(self.raw, lambda rows: rows[0].update(rationale='Synthetic line one\nline two'))
        raw = b'\xef\xbb\xbf'+raw.replace(b'\n', b'\r\n')
        target = intake.prepare(self.p, raw)
        app = intake.assemble(self.p, raw, review(target))
        self.assertTrue(intake.verify(self.p, app)['valid'])
        for key in ('protocol_candidate', 'receipt'):
            changed = copy.deepcopy(app)
            changed[key]['extra'] = 'tampered'
            with self.assertRaises(ValueError):
                intake.verify(self.p, changed)
        changed = copy.deepcopy(app)
        changed['receipt']['sheet_base64'] += '?'
        with self.assertRaises(ValueError):
            intake.verify(self.p, changed)
        with self.assertRaises(ValueError):
            intake.assemble(self.p, self.raw, review(target))
        with patch.object(intake, '_hashes', return_value={'changed':'implementation'}), self.assertRaises(ValueError):
            intake.verify(self.p, app)

    def test_documented_synthetic_commands_verbatim(self):
        guide = (ROOT/'docs/SCREENING_SHEET_INTAKE.md').read_text(encoding='utf-8')
        commands = re.findall(r'```sh\n(.*?)```', guide, re.S)
        self.assertEqual(len(commands), 1)
        with tempfile.TemporaryDirectory() as tmp:
            for line in commands[0].splitlines():
                args = shlex.split(line)
                self.assertEqual(args[:2], ['python', 'screening_sheet_intake.py'])
                args = [str(Path(tmp)/arg[len('OUTPUT/'):]) if arg.startswith('OUTPUT/') else arg for arg in args]
                result = subprocess.run([sys.executable, *args[1:]], cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            self.assertTrue(json.loads((Path(tmp)/'verification.json').read_bytes())['valid'])
            app = json.loads((Path(tmp)/'application.json').read_bytes())
            self.assertEqual(app['protocol_candidate'], json.loads((Path(tmp)/'protocol.json').read_bytes()))
        tokens = shlex.split('python tool.py OUTPUT/a.json')
        replaced = [str(Path(r'C:\synthetic space')/t[7:]) if t.startswith('OUTPUT/') else t for t in tokens]
        self.assertIn(r'C:\synthetic space', replaced[-1])

    def test_cli_exclusive_output_and_unverified_no_protocol_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory/'p.json').write_text(json.dumps(self.p), encoding='utf-8')
            (directory/'s.csv').write_bytes(self.raw)
            def command(*args):
                return subprocess.run([sys.executable, str(ROOT/'screening_sheet_intake.py'), *map(str,args)],
                    capture_output=True, text=True, encoding='utf-8')
            target = directory/'target.json'
            self.assertEqual(command('target', directory/'p.json', directory/'s.csv', '--output', target).returncode, 0)
            prior = target.read_bytes()
            self.assertNotEqual(command('target', directory/'p.json', directory/'s.csv', '--output', target).returncode, 0)
            self.assertEqual(target.read_bytes(), prior)
            (directory/'review.json').write_text(json.dumps(review(json.loads(prior))), encoding='utf-8')
            application = directory/'app.json'
            self.assertEqual(command('assemble', directory/'p.json', directory/'s.csv', directory/'review.json', '--output', application).returncode, 0)
            existing_result = directory/'existing.json'
            existing_result.write_bytes(b'preserve existing')
            premature = directory/'premature.json'
            self.assertNotEqual(command('verify', directory/'p.json', application, '--protocol-output', premature, '--output', existing_result).returncode, 0)
            self.assertFalse(premature.exists())
            self.assertEqual(existing_result.read_bytes(), b'preserve existing')
            same = directory/'same.json'
            self.assertNotEqual(command('verify', directory/'p.json', application, '--protocol-output', same, '--output', same).returncode, 0)
            self.assertFalse(same.exists())
            missing_parent = directory/'missing'/'result.json'
            self.assertNotEqual(command('verify', directory/'p.json', application, '--protocol-output', premature, '--output', missing_parent).returncode, 0)
            self.assertFalse(premature.exists())
            destination = directory/'candidate.json'
            self.assertEqual(command('verify', directory/'p.json', application, '--protocol-output', destination).returncode, 0)
            app = json.loads(application.read_bytes())
            app['protocol_candidate']['version'] = 'tampered'
            application.write_text(json.dumps(app), encoding='utf-8')
            blocked = directory/'blocked.json'
            self.assertNotEqual(command('verify', directory/'p.json', application, '--protocol-output', blocked).returncode, 0)
            self.assertFalse(blocked.exists())


if __name__ == '__main__':
    unittest.main()
