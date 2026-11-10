"""Synthetic detached CSV checks; no external requests or renderer."""
import copy
import csv
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import socket
import time
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from json_io import parse_json
from prisma_audit import export_audit
import records_csv as records
import views_export as views

ROOT = Path(__file__).resolve().parents[1]


class RecordsCSVTests(unittest.TestCase):
    def setUp(self):
        self.protocol = parse_json((ROOT / 'examples/prisma-audit.json').read_bytes())

    def rows(self, protocol=None):
        receipt, raw = records.export_records(self.protocol if protocol is None else protocol)
        return receipt, list(csv.DictReader(io.StringIO(raw.decode(), newline='')))

    def cli(self, *args):
        return subprocess.run([sys.executable, 'views_export.py', 'records', *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60)

    def test_exact_existing_ledgers_and_separate_study_columns(self):
        audit = export_audit(self.protocol)
        receipt, rows = self.rows()
        self.assertEqual(receipt['row_count'], len(audit['record_ledger']))
        for source, row in zip(audit['record_ledger'], rows):
            self.assertEqual(row['record_id'], source['record_id'])
            self.assertEqual(json.loads(row['occurrence_ids']), source['occurrence_ids'])
            self.assertEqual(json.loads(row['result_ids']), source['evidence_ids'])
        first = rows[0]
        self.assertEqual(json.loads(first['search_indices']), [0, 1])
        self.assertEqual(json.loads(first['report_study_ids']), ['s1'])
        self.assertEqual(json.loads(first['result_study_ids']), ['s1', 's1', 's1'])
        self.assertEqual(rows[1]['result_study_ids'], '[]')
        self.assertEqual(rows[1]['report_study_ids'], '["s1"]')
        self.assertEqual(first['screening_input_pointer'], '/screening/0')
        self.assertEqual(rows[2]['screening_decision'], 'pending')

    def test_missing_and_duplicate_search_labels_preserve_authoritative_indices(self):
        self.protocol.pop('search_plan')
        for search in self.protocol['searches']:
            search.pop('search_id', None)
        _, rows = self.rows()
        self.assertEqual(json.loads(rows[0]['search_ids']), [None, None])
        for search in self.protocol['searches']:
            search['search_id'] = 'Fictional repeated display label'
        _, rows = self.rows()
        self.assertEqual(json.loads(rows[0]['search_ids']), ['Fictional repeated display label'] * 2)
        self.assertEqual(json.loads(rows[0]['search_indices']), [0, 1])

    def test_missing_report_and_review_stages_not_empty(self):
        self.protocol.pop('reports')
        receipt, rows = self.rows()
        self.assertEqual(receipt['report_stage'], 'NOT_SUPPLIED')
        self.assertTrue(all(row['report_stage'] == 'NOT_SUPPLIED' for row in rows))
        self.assertTrue(all(row['screening_review_stage'] == 'NOT_SUPPLIED' for row in rows))
        self.assertNotIn('screening_review_cues', receipt['columns'])
        self.protocol.update(reports=[], evidence=[], gaps=[], screening_reviews=[])
        for key in ('experimental_units', 'synthesis_statements', 'planning_decisions', 'appraisals', 'contexts'):
            self.protocol.pop(key, None)
        receipt, rows = self.rows()
        self.assertEqual(receipt['report_stage'], 'SUPPLIED')
        self.assertEqual(receipt['screening_review_stage'], 'SUPPLIED')
        self.assertIn('screening_review_cues', receipt['columns'])
        self.assertTrue(all(row['report_study_ids'] == '[]' for row in rows))
        self.assertEqual(json.loads(rows[0]['screening_review_cues']), ['NO_CURRENT_SOURCE_REVIEW'])

    def test_all_valid_examples_and_optional_columns(self):
        seen = set()
        for path in sorted((ROOT / 'examples').glob('*.json')):
            protocol = parse_json(path.read_bytes())
            try:
                audit = export_audit(protocol)
            except (ValueError, KeyError, TypeError):
                continue
            with self.subTest(example=path.name):
                receipt, rows = self.rows(protocol)
                seen.update(receipt['columns'])
                self.assertEqual(len(rows), len(audit['record_ledger']))
                for original, row in zip(audit['record_ledger'], rows):
                    if 'bibliographic_row_pointers' in row:
                        self.assertEqual(json.loads(row['bibliographic_row_pointers']), original['bibliographic_row_pointers'])
                    if 'screening_review_cues' in row:
                        match = next(r for r in audit['screening_review']['record_review_ledger'] if r['record_id'] == original['record_id'])
                        self.assertEqual(json.loads(row['screening_review_cues']), match['comparison_cues'])
        self.assertIn('screening_review_cues', seen)

    def test_optional_bibliographic_pointers_are_copied(self):
        audit = export_audit(self.protocol)
        audit['bibliographic_collection'] = {}
        for row in audit['record_ledger']:
            row['bibliographic_row_pointers'] = ['/bibliographic_imports/0/rows/0'] if row['record_id'] == 'r1' else []
        raw, columns = records.render_records(audit)
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        self.assertIn('bibliographic_row_pointers', columns)
        self.assertEqual(json.loads(rows[0]['bibliographic_row_pointers']), ['/bibliographic_imports/0/rows/0'])
        self.assertEqual(rows[1]['bibliographic_row_pointers'], '[]')

    def test_byte_determinism_permuted_keys_and_no_mutation(self):
        original = copy.deepcopy(self.protocol)
        def permute(value):
            if isinstance(value, dict):
                return {key: permute(value[key]) for key in reversed(list(value))}
            if isinstance(value, list):
                return [permute(item) for item in value]
            return value
        self.assertEqual(records.export_records(self.protocol), records.export_records(permute(self.protocol)))
        self.assertEqual(self.protocol, original)

    def test_hostile_scalar_strings_are_escaped_and_round_trip(self):
        for value in ('=1+1', '+1', '-2', '@SUM(1)', ' \t=1', '\t=1', '\r=1', '\n=1',
                      'Fictional,"quote"\rnew\nline', '# ``` | <img> [x](javascript:fake)', '\u202eFictional'):
            with self.subTest(value=value):
                self.protocol['screening'][0]['reason'] = value
                _, rows = self.rows()
                self.assertEqual(rows[0]['screening_reason'], records.safe_csv_cell(value))
        audit = export_audit(self.protocol)
        audit['record_ledger'][0]['record_id'] = '=Fictional'
        raw, _ = records.render_records(audit)
        self.assertEqual(list(csv.DictReader(io.StringIO(raw.decode(), newline='')))[0]['record_id'], "'=Fictional")

    def test_json_lists_escape_nul_and_formula_is_not_promoted(self):
        self.assertEqual(json.loads(records._safe(['=Fictional', '\0', '\r\n'])), ['=Fictional', '\0', '\r\n'])
        self.protocol['screening'][0]['reason'] = 'Fictional\0reason'
        with self.assertRaisesRegex(ValueError, 'NUL'):
            records.export_records(self.protocol)

    def test_receipt_exact_hashes_boundary_and_no_csv_comments(self):
        receipt, raw = records.export_records(self.protocol)
        self.assertEqual(receipt['document']['bytes'], len(raw))
        self.assertEqual(receipt['document']['sha256'], hashlib.sha256(raw).hexdigest())
        for name in ('records_csv.py', 'views_export.py', 'prisma_audit.py', 'research_status.py'):
            self.assertEqual(receipt['engine_sha256'][name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
        self.assertEqual(receipt['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(receipt['conclusion_readiness'], 'NOT_READY')
        self.assertIn('not a PRISMA-standard', receipt['boundary'])
        self.assertTrue(raw.startswith(b'"record_id",'))
        self.assertNotIn(b'\xef\xbb\xbf', raw)

    def test_empty_records_still_header_and_stage_receipt(self):
        audit = export_audit(self.protocol)
        audit['record_ledger'] = []
        raw, columns = records.render_records(audit)
        self.assertEqual(list(csv.reader(io.StringIO(raw.decode()))), [columns])

    def test_output_size_bound_before_write(self):
        with patch.object(records, 'MAX_BYTES', 100), self.assertRaisesRegex(ValueError, 'size limit'):
            records.export_records(self.protocol)

    def test_cli_json_text_exclusive_directory_missing_parent_and_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source = ROOT / 'examples/prisma-audit.json'
            output = base / 'records.csv'
            result = self.cli(source, '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            raw = output.read_bytes()
            text = self.cli(source, '--output', base / 'text.csv', '--text')
            self.assertEqual(text.returncode, 0, text.stderr)
            self.assertIn(b'Supplied-data records CSV receipt', text.stdout)
            self.assertEqual(raw, (base / 'text.csv').read_bytes())
            for path in (output, base, base / 'absent' / 'new.csv'):
                result = self.cli(source, '--output', path)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')
            self.assertEqual(output.read_bytes(), raw)
            link = base / 'dangling.csv'
            try:
                link.symlink_to(base / 'missing.csv')
            except (OSError, NotImplementedError):
                return
            self.assertEqual(self.cli(source, '--output', link).returncode, 1)
            self.assertFalse((base / 'missing.csv').exists())

    def test_csv_error_and_nul_cli_fail_without_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'records.csv'
            args = ['views_export.py', 'records', str(ROOT / 'examples/prisma-audit.json'), '--output', str(output)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(sys, 'argv', args), patch.object(records.csv, 'writer', side_effect=csv.Error('Fictional CSV error')), redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit):
                views.main()
            self.assertEqual(stdout.getvalue(), '')
            self.assertIn('Records CSV error:', stderr.getvalue())
            self.assertFalse(output.exists())
            source = Path(folder) / 'synthetic.json'
            self.protocol['screening'][0]['reason'] = 'Fictional\0reason'
            source.write_text(json.dumps(self.protocol), encoding='utf-8')
            result = self.cli(source, '--output', output)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, b'')
            self.assertFalse(output.exists())

    def test_write_failure_removes_only_new_file(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'records.csv'
            real_open = Path.open
            class Broken:
                def __enter__(self):
                    return self
                def write(self, raw):
                    raise OSError('Fictional disk full')
                def __exit__(self, *args):
                    self.target.close()
            def broken_open(path, *args, **kwargs):
                broken = Broken()
                broken.target = real_open(path, *args, **kwargs)
                broken.target.write(b'partial')
                return broken
            with patch.object(Path, 'open', broken_open), self.assertRaises(OSError):
                records.write_records(output, b'Fictional')
            self.assertFalse(output.exists())
            output.write_bytes(b'original')
            with self.assertRaises(FileExistsError):
                records.write_records(output, b'replacement')
            self.assertEqual(output.read_bytes(), b'original')

    def test_no_network_clock_and_single_authoritative_audit(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('no network')), patch.object(time, 'time', side_effect=AssertionError('no clock')), patch.object(records, 'export_audit', wraps=export_audit) as called:
            records.export_records(self.protocol)
        called.assert_called_once_with(self.protocol)

    def test_receipt_preflight_and_invalid_json_create_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'synthetic.json', Path(folder) / 'records.csv'
            source.write_bytes(b'{}')
            for flag in ([], ['--text']):
                stdout, stderr = io.StringIO(), io.StringIO()
                args = ['views_export.py', 'records', str(source), '--output', str(output)] + flag
                with patch.object(sys, 'argv', args), patch.object(views, 'MAX_BYTES', 100), patch.object(views, 'export_records', return_value=({'boundary': 'Fictional ' * 200}, b'csv')), redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit):
                    views.main()
                self.assertIn('receipt exceeds size limit', stderr.getvalue())
                self.assertEqual(stdout.getvalue(), '')
                self.assertFalse(output.exists())
            for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":"\\ud800"}', b'[]', b'null', b'{}'):
                source.write_bytes(raw)
                result = self.cli(source, '--output', output)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')
                self.assertFalse(output.exists())

    def test_documented_rehearsal(self):
        document = (ROOT / 'docs/RECORDS_CSV.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory(prefix='fictional CSV guide ') as folder:
            for line in blocks[0].splitlines():
                tokens = shlex.split(line)
                self.assertEqual(tokens[:3], ['python', 'views_export.py', 'records'])
                result = self.cli(*[token.replace('OUTPUT', folder) for token in tokens[3:]])
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((Path(folder) / 'records.csv').read_bytes(), (Path(folder) / 'records-text.csv').read_bytes())


if __name__ == '__main__':
    unittest.main()
