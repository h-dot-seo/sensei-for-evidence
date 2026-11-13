"""Synthetic blank screening-sheet export; no eligibility judgements or live data."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import screening_review
import screening_sheet as sheet
from csv_safety import safe_csv_cell
from csv_export_parser import parse_export
from tests.test_screening_reviews import protocol

ROOT = Path(__file__).resolve().parents[1]


def rows(raw):
    return list(csv.DictReader(io.StringIO(raw.decode('utf-8'), newline='')))


class ScreeningSheetTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()

    def test_exact_template_targets_blank_human_cells_and_no_mutation(self):
        p = json.loads((ROOT/'examples/screening-reviews.json').read_bytes())
        before = copy.deepcopy(p)
        raw, receipt = sheet.export_sheet(p)
        draft = screening_review.template(p)
        self.assertEqual(p, before)
        self.assertEqual(raw, sheet.export_sheet(p)[0])
        self.assertEqual(len(rows(raw)), len(draft['screening_reviews']))
        for row, target in zip(rows(raw), draft['screening_reviews']):
            self.assertEqual(row['record_id'], safe_csv_cell(target['record_id']))
            self.assertEqual(json.loads(row['readonly_record_id_json']), target['record_id'])
            self.assertEqual(row['source_basis_sha256'], target['source_basis_sha256'])
            self.assertEqual(row['readonly_export_protocol_sha256'], draft['protocol_sha256'])
            self.assertTrue(all(row[name] == '' for name in sheet.HUMAN_COLUMNS))
            self.assertEqual(row['readonly_retained_locators_json'], '')
        self.assertEqual(receipt['sheet_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt['sheet_bytes'], len(raw))
        self.assertFalse(receipt['screening_performed'])
        self.assertFalse(receipt['protocol_changed'])
        self.assertFalse(receipt['existing_review_assertions_copied'])
        self.assertEqual(receipt['edited_sheet_intake'], 'NOT_IMPLEMENTED')

    def test_formula_like_ids_escape_and_literal_ids_remain_distinct(self):
        ids = ['=formula', "'=formula", '-id', '+id', '@id', ' id', '\tid', '\nid', '한국어']
        self.p['searches'][0]['record_ids'] = ids
        self.p['screening'] = []
        self.p['searches'][0]['total_count'] = len(ids)
        raw, _ = sheet.export_sheet(self.p)
        actual = rows(raw)
        self.assertEqual({json.loads(r['readonly_record_id_json']) for r in actual}, set(ids))
        self.assertEqual(len({r['source_basis_sha256'] for r in actual}), len(ids))
        for row in actual:
            self.assertEqual(row['record_id'], safe_csv_cell(json.loads(row['readonly_record_id_json'])))
        parsed = parse_export(raw, id_column='record_id', locator_column='source_basis_sha256')
        self.assertEqual(len(parsed['record_rows']), len(ids))

    def test_source_drift_changes_export_target_without_refreshing_prior_assertion(self):
        from tests.test_screening_reviews import assertion
        self.p['screening_reviews'] = [assertion(self.p)]
        before = copy.deepcopy(self.p['screening_reviews'])
        old, _ = sheet.export_sheet(self.p)
        self.p['inclusion_criteria'].append('New fictional criterion')
        new, _ = sheet.export_sheet(self.p)
        old_basis = {r['record_id']:r['source_basis_sha256'] for r in rows(old)}
        self.assertTrue(all(old_basis[r['record_id']] != r['source_basis_sha256'] for r in rows(new)))
        self.assertEqual(self.p['screening_reviews'], before)
        self.assertEqual(screening_review.review(self.p)['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
        self.assertIn('Never refill', sheet.BOUNDARY)

    def test_selected_retained_values_are_literal_ordered_and_not_in_human_fields(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        helper = BibliographicReviewTests(); helper.setUp()
        p = helper.imported()
        raw, receipt = sheet.export_sheet(p, ['title','missing'])
        targets = {t['source_basis_sha256']:t for t in screening_review.template(p)['record_targets']}
        for row in rows(raw):
            native = targets[row['source_basis_sha256']]['source_basis']['bibliographic_rows']
            expected = [dict(source_pointer=r['source_pointer'],value=r['original_values']['title'])
                        for r in native if 'title' in r['original_values']]
            self.assertEqual(json.loads(row['readonly_display:title']), expected)
            self.assertEqual(row['readonly_display:missing'], '')
            self.assertEqual(json.loads(row['readonly_retained_locators_json']),
                [dict(source_pointer=r['source_pointer'], value=r['source_locator']) for r in native])
            self.assertEqual(row['source_locator'], '')
        self.assertEqual(receipt['display_columns'][0]['original_column'], 'title')

    def test_formula_display_text_remains_literal_json_and_never_opens_locators(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        helper = BibliographicReviewTests(); helper.setUp()
        helper.raw = b'record_id,source_locator,title\n1,https://example.invalid/a,=1+1\n'
        helper.artifact = helper.prepare(raw=helper.raw)
        import bibliographic_review
        choices = bibliographic_review.template(helper.artifact)
        choices['resolutions'][0].update(disposition='new_record', record_id='formula-record', rationale='Fictional')
        helper.choices = choices
        p = helper.imported()
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network')):
            raw, receipt = sheet.export_sheet(p, ['title'])
        value = rows(raw)[0]['readonly_display:title']
        self.assertFalse(value.startswith(('=', '+', '-', '@')))
        self.assertEqual(json.loads(value)[0]['value'], '=1+1')
        self.assertEqual(receipt['external_calls'], 0)

    def test_blank_manual_display_and_empty_protocol_export(self):
        raw, receipt = sheet.export_sheet(self.p, ['title'])
        self.assertTrue(all(r['readonly_display:title'] == '' for r in rows(raw)))
        self.assertEqual(receipt['rows_without_retained_values'], 3)
        self.p['searches'] = []; self.p['screening'] = []
        raw, receipt = sheet.export_sheet(self.p)
        self.assertEqual(rows(raw), [])
        self.assertEqual(receipt['record_rows'], 0)

    def test_invalid_selection_protocol_and_output_bounds(self):
        for names in (['title','title'],[''], ['x\n'],['x'*129], ['x']*17, 'title', [None]):
            with self.subTest(names=names), self.assertRaises(ValueError): sheet.export_sheet(self.p, names)
        invalid = copy.deepcopy(self.p); invalid['screening'][0]['decision'] = 'guess'
        with self.assertRaises(ValueError): sheet.export_sheet(invalid)
        with patch.object(sheet,'MAX_ROWS',1), self.assertRaises(ValueError): sheet.export_sheet(self.p)
        with patch.object(sheet,'MAX_OUTPUT_BYTES',1), self.assertRaises(ValueError): sheet.export_sheet(self.p)

    def test_cli_exact_guide_commands_and_receipt(self):
        document = (ROOT/'docs/SCREENING_SHEETS.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory(prefix='screening sheet ') as folder:
            for command in blocks[0].splitlines():
                args = [s.replace('OUTPUT/', folder+'/') for s in shlex.split(command)]
                args[0] = sys.executable
                result = subprocess.run(args, cwd=ROOT, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            raw = (Path(folder)/'screening.csv').read_bytes()
            self.assertEqual(raw, sheet.export_sheet(json.loads((ROOT/'examples/screening-reviews.json').read_bytes()), ['title'])[0])
            self.assertIn(b'not screening performed', result.stdout)
            rerun = subprocess.run(args, cwd=ROOT, capture_output=True)
            self.assertNotEqual(rerun.returncode, 0)
            self.assertEqual((Path(folder)/'screening.csv').read_bytes(), raw)

    def test_cli_failures_do_not_create_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source=root/'bad.json'; out=root/'out.csv'
            for raw in (b'{"x":1,"x":2}', b'\xff', b'{}'):
                source.write_bytes(raw)
                result=subprocess.run([sys.executable,str(ROOT/'screening_sheet.py'),'export',str(source),'--output',str(out)],capture_output=True)
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn(b'Traceback',result.stderr)
                self.assertFalse(out.exists())
            for path in (root/'existing',root/'directory'):
                if path.name=='directory':path.mkdir()
                else:path.write_bytes(b'unchanged')
                with self.assertRaises(FileExistsError):sheet._write_new(path,b'new')
            with self.assertRaises(FileNotFoundError):sheet._write_new(root/'absent'/'out',b'new')

    def test_dangling_output_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);link=root/'link';target=root/'missing'
            try:link.symlink_to(target)
            except (OSError,NotImplementedError):self.skipTest('symlink privilege unavailable')
            with self.assertRaises(FileExistsError):sheet._write_new(link,b'new')
            self.assertFalse(target.exists())
