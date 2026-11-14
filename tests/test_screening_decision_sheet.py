"""Synthetic, offline blank decision sheets; no automated adjudication."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from json_io import canonical_json_bytes
import screening_decision_sheet as sheet
import screening_sheet_intake
import screening_review
from tests.test_screening_reviews import protocol, assertion

ROOT = Path(__file__).resolve().parents[1]


def rows(raw):
    return list(csv.DictReader(io.StringIO(raw.decode('utf-8'), newline='')))


class ScreeningDecisionSheetTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()

    def test_blank_choices_exact_source_targets_and_no_mutation(self):
        self.p['screening_reviews'] = [assertion(self.p)]
        prior = copy.deepcopy(self.p)
        with patch('socket.socket', side_effect=AssertionError('no network')):
            raw, receipt = sheet.export_sheet(self.p)
        self.assertEqual(self.p, prior)
        self.assertEqual(raw, sheet.export_sheet(self.p)[0])
        self.assertTrue(raw.endswith(b'\n'))
        self.assertNotIn(b'\r', raw)
        self.assertEqual(receipt['sheet_bytes'], len(raw))
        self.assertEqual(receipt['sheet_sha256'], hashlib.sha256(raw).hexdigest())
        expected = {t['record_id']: t for t in screening_review.template(self.p)['record_targets']}
        for row in rows(raw):
            rid = json.loads(row['readonly_record_id_json'])
            self.assertEqual(row['source_basis_sha256'], expected[rid]['source_basis_sha256'])
            self.assertEqual(row['readonly_export_protocol_sha256'], hashlib.sha256(canonical_json_bytes(self.p)).hexdigest())
            self.assertTrue(all(row[key] == '' for key in sheet.HUMAN_COLUMNS))
            context = json.loads(row['readonly_review_context_json'])
            self.assertEqual(row['readonly_export_review_context_sha256'], hashlib.sha256(canonical_json_bytes(context)).hexdigest())
        self.assertFalse(receipt['protocol_changed'])
        self.assertFalse(receipt['decision_history_changed'])
        self.assertFalse(receipt['sequential_decision_targets_created'])
        self.assertEqual(receipt['edited_sheet_intake'], 'NOT_IMPLEMENTED')

    def test_context_keeps_conflict_stale_and_prior_without_choosing(self):
        self.p['screening_reviews'] = [assertion(self.p), assertion(self.p, reviewer='Fictional B', decision='exclude', review_id='b'),
                                       dict(assertion(self.p, reviewer='Fictional C', review_id='c'), source_basis_sha256='0'*64)]
        raw, _ = sheet.export_sheet(self.p, ['r1'])
        row = rows(raw)[0]
        self.assertEqual(json.loads(row['readonly_prior_screening_json']), self.p['screening'][0])
        context = json.loads(row['readonly_review_context_json'])
        self.assertEqual(len(context['supplied_review_ledger']), 3)
        self.assertEqual(context['supplied_review_ledger'][-1]['source_match_status'], 'STALE_SOURCE')
        self.assertIn('DIFFERING_CURRENT_POSITIONS', context['record_review_cues']['comparison_cues'])
        self.assertEqual(row['decision'], '')
        self.assertEqual(row['reason'], '')

    def test_explicit_selection_is_literal_and_keeps_order(self):
        raw, receipt = sheet.export_sheet(self.p, ['r2', 'pending'])
        self.assertEqual([json.loads(r['readonly_record_id_json']) for r in rows(raw)], ['r2', 'pending'])
        self.assertEqual(receipt['selection_scope'], 'EXPLICIT_ORDERED_RECORD_IDS')
        self.assertEqual(receipt['validation_scope'], 'ENTIRE_PROTOCOL')
        self.assertIsNone(json.loads(rows(raw)[1]['readonly_prior_screening_json']))

    def test_selection_validation_and_boundaries(self):
        for ids in [[], ['unknown'], ['r1','r1'], [' r1'], '', [None], [True]]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                sheet.export_sheet(self.p, ids)
        ids = ['r'+str(i) for i in range(101)]
        self.p['searches'][0]['record_ids'] = ids
        self.p['searches'][0]['total_count'] = len(ids)
        self.p['screening'] = []
        with self.assertRaises(ValueError):
            sheet.export_sheet(self.p)
        raw, receipt = sheet.export_sheet(self.p, ids[:100])
        self.assertEqual(len(rows(raw)), 100)
        self.assertEqual(receipt['record_rows'], 100)
        with self.assertRaises(ValueError):
            sheet.export_sheet(self.p, ids)

    def test_selected_subset_still_validates_unselected_assertions(self):
        self.p['screening_reviews'] = [dict(assertion(self.p, 'r2'), decision='invalid')]
        with self.assertRaises(ValueError):
            sheet.export_sheet(self.p, ['r1'])

    def test_formula_like_ids_literal_json_and_safe_display(self):
        ids = ['=id', "'=id", '-id', '+id', '@id', ' id', '\tid', '\nid', '한국어', 'quote"id']
        self.p['searches'][0]['record_ids'] = ids
        self.p['searches'][0]['total_count'] = len(ids)
        self.p['screening'] = []
        raw, _ = sheet.export_sheet(self.p, ids)
        self.assertEqual([json.loads(r['readonly_record_id_json']) for r in rows(raw)], ids)
        self.assertEqual(len({r['source_basis_sha256'] for r in rows(raw)}), len(ids))
        self.assertEqual(rows(raw)[0]['record_id'], rows(raw)[1]['record_id'])
        self.assertNotEqual(rows(raw)[0]['readonly_record_id_json'], rows(raw)[1]['readonly_record_id_json'])

    def test_context_change_changes_hashes_without_reusing_choices(self):
        self.p['screening_reviews'] = [assertion(self.p)]
        old, _ = sheet.export_sheet(self.p, ['r1'])
        self.p['screening_reviews'][0]['rationale'] += ' changed'
        new, _ = sheet.export_sheet(self.p, ['r1'])
        before, after = rows(old)[0], rows(new)[0]
        self.assertEqual(before['source_basis_sha256'], after['source_basis_sha256'])
        self.assertNotEqual(before['readonly_export_protocol_sha256'], after['readonly_export_protocol_sha256'])
        self.assertNotEqual(before['readonly_export_review_context_sha256'], after['readonly_export_review_context_sha256'])
        self.assertTrue(all(after[name] == '' for name in sheet.HUMAN_COLUMNS))

    def test_manual_display_is_blank_and_position_intake_rejects_decision_sheet(self):
        raw, receipt = sheet.export_sheet(self.p, display_columns=['title'])
        self.assertTrue(all(row['readonly_display:title'] == '' for row in rows(raw)))
        self.assertEqual(receipt['display_columns'][0]['original_column'], 'title')
        with self.assertRaises(ValueError):
            screening_sheet_intake.prepare(self.p, raw)
        for columns in [['title', 'title'], ['\x00'], 'title']:
            with self.assertRaises(ValueError):
                sheet.export_sheet(self.p, display_columns=columns)

    def test_empty_protocol_exports_header_only(self):
        self.p['searches'][0]['record_ids'] = []
        self.p['searches'][0]['total_count'] = 0
        self.p['screening'] = []
        raw, receipt = sheet.export_sheet(self.p)
        self.assertEqual(rows(raw), [])
        self.assertEqual(receipt['record_rows'], 0)

    def test_strict_bytes_and_function_limits(self):
        with patch.object(sheet, 'MAX_INPUT_BYTES', 10), self.assertRaises(ValueError):
            sheet.export_sheet(self.p)
        with patch.object(sheet, 'MAX_OUTPUT_BYTES', 10), self.assertRaises(ValueError):
            sheet.export_sheet(self.p)
        for p in [None, [], {'bad': float('nan')}]:
            with self.assertRaises((ValueError, TypeError)):
                sheet.export_sheet(p)
        self.p['screening_reviews'] = [assertion(self.p)]
        self.p['screening_reviews'][0]['rationale'] = 'text\x00value'
        # JSON strings preserve an inert escaped NUL, never a raw CSV NUL.
        raw, _ = sheet.export_sheet(self.p)
        self.assertNotIn(b'\x00', raw)

    def test_cli_exclusive_outputs_and_json_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            source = d/'protocol.json'; source.write_text(json.dumps(self.p), encoding='utf-8')
            out = d/'sheet.csv'
            args = [sys.executable, str(ROOT/'screening_decision_sheet.py'), 'export', str(source), '--record-id', 'r1', '--output', str(out)]
            result = subprocess.run(args, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['record_rows'], 1)
            original = out.read_bytes()
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertEqual(out.read_bytes(), original)
            missing = d/'missing'/'out.csv'
            self.assertNotEqual(subprocess.run(args[:-1]+[str(missing)], capture_output=True).returncode, 0)
            self.assertFalse(missing.exists())
            self.assertNotEqual(subprocess.run(args[:-1]+[str(d)], capture_output=True).returncode, 0)

    def test_documented_command_verbatim_and_windows_tokenization(self):
        guide = (ROOT/'docs/SCREENING_DECISION_SHEETS.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', guide, re.S)
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory() as tmp:
            for line in blocks[0].splitlines():
                args = shlex.split(line)
                self.assertEqual(args[:2], ['python', 'screening_decision_sheet.py'])
                args = [str(Path(tmp)/x[7:]) if x.startswith('OUTPUT/') else x for x in args]
                result = subprocess.run([sys.executable,*args[1:]], cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(b'Blank screening-decision sheet exported', result.stdout)
            actual = rows((Path(tmp)/'decisions.csv').read_bytes())
            self.assertEqual(len(actual), 4)
            self.assertTrue(all(row[name] == '' for row in actual for name in sheet.HUMAN_COLUMNS))
        args = shlex.split('python tool.py OUTPUT/decisions.csv')
        replaced = [str(Path(r'C:\synthetic space')/x[7:]) if x.startswith('OUTPUT/') else x for x in args]
        self.assertIn(r'C:\synthetic space', replaced[-1])


if __name__ == '__main__':
    unittest.main()
