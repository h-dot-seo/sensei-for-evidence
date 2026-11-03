import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from csv_safety import safe_csv_cell
from prisma_reports import report_flow
from research_bundle import build_bundle, verify


class CsvSafetyTests(unittest.TestCase):
    def test_formula_and_whitespace_prefixes_escaped(self):
        for prefix in ('=', '+', '-', '@', '\t', '\r', '\n', ' ', '\v', '\f', '\u00a0'):
            value = prefix + '=1+1'
            with self.subTest(prefix=repr(prefix)):
                self.assertEqual(safe_csv_cell(value), "'" + value)

    def test_plain_text_and_unicode_preserved(self):
        for value in ('', 'ordinary', 'r1', 'x=y', "'already text", '합성 근거'):
            self.assertEqual(safe_csv_cell(value), value)

    def test_report_csv_preserves_escaped_multiline_cells(self):
        protocol = json.loads(Path('examples/report-protocol.json').read_text())
        protocol['reports'][0]['report_id'] = '\n=1+1'
        protocol['reports'][0]['locator'] = ' \t=1+1'
        rows = list(csv.DictReader(io.StringIO(report_flow(protocol)['report_csv'])))
        self.assertEqual(rows[0]['report_id'], "'\n=1+1")
        self.assertEqual(rows[0]['locator'], "' \t=1+1")

    def test_bundle_work_csv_uses_same_escaping_and_verifies(self):
        protocol = json.loads(Path('examples/report-protocol.json').read_text())
        protocol['gaps'][0]['question'] = '\n=1+1'
        protocol['gaps'][0]['deliverable'] = ' =1+1'
        bundle = build_bundle(json.dumps(protocol).encode())
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            rows = list(csv.DictReader(io.StringIO(archive.read('work-packages.csv').decode())))
            self.assertEqual(rows[0]['question'], "'\n=1+1")
            self.assertEqual(rows[0]['deliverable'], "' =1+1")
            self.assertIn('csv_safety.py', json.loads(archive.read('manifest.json'))['engine_sha256'])
            self.assertEqual(json.loads(archive.read('protocol.json')), protocol)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bundle.zip'
            path.write_bytes(bundle)
            self.assertTrue(verify(path)['valid'])
