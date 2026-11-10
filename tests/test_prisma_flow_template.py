"""Entirely synthetic native crosswalk tests; no external template or source."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import prisma_flow_template as flow
from json_io import parse_json

ROOT = Path(__file__).resolve().parents[1]


class CrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.protocol = parse_json((ROOT / 'examples/prisma-audit.json').read_bytes())

    def export(self, **kwargs):
        return flow.export_crosswalk(self.protocol, **kwargs)

    def rows(self, **kwargs):
        return list(csv.DictReader(io.StringIO(self.export(**kwargs)[1].decode('utf-8'))))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'prisma_flow_template.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_default_cells_are_conservative_and_searches_are_unassigned(self):
        result, _ = self.export()
        rows = {row['template_key']: row for row in self.rows()}
        self.assertEqual(result['unassigned_search_indices'], [0, 1])
        for key in ('database_results', 'register_results', 'duplicates', 'records_screened'):
            self.assertEqual(rows[key]['count'], '')
        self.assertTrue(all(row['count'] is None for row in result['mapping_ledger']
                            if row['template_key'] == 'unassigned_search'))
        self.assertEqual(result['search_ledger'][0]['accounting']['enumerated'], 10)

    def test_opt_in_expected_counts_preserve_per_search_rows(self):
        rows = self.rows(search_arms={0: 'databases', 1: 'databases'}, include_exact_id_accounting=True)
        identified = [row for row in rows if row['template_key'] == 'database_results']
        self.assertEqual([(r['search_index'], r['count']) for r in identified], [('0', '10'), ('1', '3')])
        indexed = {row['template_key']: row for row in rows}
        expected = dict(duplicates=2, records_screened=9, records_excluded=1, dbr_sought_reports=6,
                        dbr_notretrieved_reports=1, dbr_assessed=3, dbr_excluded=1, new_studies=1, new_reports=2)
        for key, value in expected.items():
            self.assertEqual(indexed[key]['count'], str(value))
        self.assertIn('not deduplication', indexed['duplicates']['scope'])
        self.assertEqual(indexed['dbr_excluded_reason']['label'], 'Fictional exclusion reason')
        self.assertEqual(indexed['dbr_excluded_reason']['count'], '1')

    def test_register_assignment_does_not_partition_downstream_counts(self):
        rows = self.rows(search_arms={0: 'databases', 1: 'registers'})
        self.assertEqual([(r['template_key'], r['count']) for r in rows[:2]],
                         [('database_results', '10'), ('register_results', '3')])
        sought = next(r for r in rows if r['template_key'] == 'dbr_sought_reports')
        self.assertEqual(sought['count'], '6')
        self.assertIn('all supplied searches', sought['scope'])

    def test_duplicate_source_labels_are_never_aggregated(self):
        self.protocol.pop('search_plan')
        for search in self.protocol['searches']:
            search['source'] = 'Fictional same label'
            search['search_id'] = 'same'
        result, _ = self.export(search_arms={0: 'databases', 1: 'databases'})
        rows = result['mapping_ledger'][:2]
        self.assertEqual([r['search_index'] for r in rows], [0, 1])
        self.assertEqual([r['count'] for r in rows], [10, 3])

    def test_missing_or_duplicate_optional_ids_do_not_affect_assignment(self):
        self.protocol.pop('search_plan')
        for label in (None, 'fictional-duplicate'):
            for search in self.protocol['searches']:
                search['search_id'] = label
            result, _ = self.export(search_arms={1: 'registers'})
            self.assertEqual(result['unassigned_search_indices'], [0])
            self.assertEqual(result['search_ledger'][1]['supplied_arm'], 'registers')

    def test_missing_report_stage_is_blank_not_zero(self):
        self.protocol.pop('reports')
        result, _ = self.export()
        for row in result['mapping_ledger']:
            if row['template_key'].startswith('dbr_') or row['template_key'] in ('new_studies', 'new_reports'):
                self.assertIsNone(row['count'])
        self.assertEqual(result['transition_differences'][2]['status'], 'NOT_SUPPLIED')

    def test_supplied_empty_report_stage_is_zero(self):
        self.protocol.update(reports=[], evidence=[], gaps=[])
        for key in ('experimental_units', 'synthesis_statements', 'planning_decisions', 'appraisals', 'contexts'):
            self.protocol.pop(key, None)
        rows = {r['template_key']: r for r in self.rows()}
        self.assertEqual(rows['dbr_sought_reports']['count'], '0')
        self.assertEqual(rows['new_studies']['count'], '0')
        self.assertEqual(rows['new_reports']['count'], '0')
        self.assertEqual(rows['other_sought_reports']['count'], '')

    def test_unsupported_methods_never_become_zero(self):
        rows = {row['template_key']: row for row in self.rows()}
        for key in flow.UNSUPPORTED_KEYS:
            self.assertEqual(rows[key]['count'], '')

    def test_pending_nodes_missing_plans_and_transition_residuals_remain_visible(self):
        result, _ = self.export()
        self.assertEqual({n['node_id']: n['count'] for n in result['outside_flow_nodes']},
                         dict(screening_pending_records=2, unmapped_included_records=1,
                              reports_retrieval_pending=1, reports_assessment_pending=1))
        self.assertEqual(result['search_plan_audit']['missing_search_ids'], ['search-citation-followup'])
        self.assertEqual([r['difference'] for r in result['transition_differences']], [2, 1, 2])
        self.assertTrue(all(r['difference'] == r['residual_count'] for r in result['transition_differences']))

    def test_incomplete_total_and_page_issues_are_retained(self):
        search = self.protocol['searches'][0]
        search.update(total_count=100, complete=False, has_more=True)
        search['pages'][0]['has_more'] = True
        result, _ = self.export(search_arms={0: 'databases'})
        ledger = result['search_ledger'][0]
        self.assertEqual(ledger['supplied_total_count'], 100)
        self.assertFalse(ledger['supplied_complete'])
        self.assertTrue(ledger['supplied_has_more'])
        self.assertTrue(ledger['accounting']['issues'])
        self.assertTrue(ledger['accounting']['page_audit']['issues'])
        self.assertEqual(result['mapping_ledger'][0]['count'], 10)

    def test_formula_escaping_preserves_raw_receipt_labels_and_reasons(self):
        self.protocol.pop('search_plan')
        source = '=Fictional("source"),\n가상'
        reason = '\t+Fictional, reason\nsecond line'
        self.protocol['searches'][0]['source'] = source
        for report in self.protocol['reports']:
            if report.get('decision') == 'exclude':
                report['reason'] = reason
        result, raw = self.export(search_arms={0: 'databases'})
        rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
        self.assertEqual(rows[0]['label'], "'" + source)
        reason_row = next(r for r in rows if r['template_key'] == 'dbr_excluded_reason')
        self.assertEqual(reason_row['label'], "'" + reason)
        self.assertEqual(result['search_ledger'][0]['source'], source)
        self.assertEqual(next(r for r in result['mapping_ledger'] if r['template_key'] == 'dbr_excluded_reason')['label'], reason)

    def test_text_cannot_forge_lines_or_direction(self):
        self.protocol.pop('search_plan')
        self.protocol['searches'][0]['source'] = 'Fictional\nConclusion: READY\u202e\x1b\x85'
        text = flow.render_text(self.export()[0])
        for hostile in ('\nConclusion: READY', '\u202e', '\x1b', '\x85'):
            self.assertNotIn(hostile, text)
        for field in ('mapping_ledger:', 'outside_flow_nodes:', 'search_plan_audit:', 'transition_differences:'):
            self.assertIn(field, text)

    def test_deterministic_nonmutating_offline_export_and_hashes(self):
        original = copy.deepcopy(self.protocol)
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            first, raw = self.export(search_arms={0: 'databases'})
            self.assertEqual((first, raw), self.export(search_arms={0: 'databases'}))
        self.assertEqual(self.protocol, original)
        self.assertEqual(first['csv']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(first['csv']['bytes'], len(raw))
        for name in ('prisma_audit.py', 'prisma_flow_template.py', 'csv_safety.py'):
            self.assertEqual(first['engine_sha256'][name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())

    def test_every_csv_row_keeps_boundaries(self):
        for row in self.rows():
            self.assertEqual(row['boundary'], flow.BOUNDARY)
            self.assertEqual(row['census_claim'], 'NOT_ESTABLISHED')
            self.assertEqual(row['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(tuple(self.rows()[0]), flow.HEADERS)

    def test_invalid_search_assignments_fail(self):
        for values in (['0=other'], ['0=databases', '0=registers'], ['-1=databases'],
                       ['01=databases'], ['a=databases'], ['０=databases'], ['1']):
            with self.subTest(values=values), self.assertRaises(ValueError):
                flow.parse_search_arms(values)
        for arms in ({2: 'databases'}, {-1: 'registers'}, {True: 'databases'}, {'0': 'databases'}, [], {0: 'other'}):
            with self.subTest(arms=arms), self.assertRaises(ValueError):
                self.export(search_arms=arms)
        with self.assertRaises(ValueError):
            self.export(include_exact_id_accounting='yes')

    def test_csv_size_limit_is_checked_before_output(self):
        with patch.object(flow, 'MAX_BYTES', 100), self.assertRaisesRegex(ValueError, 'size limit'):
            self.export()

    def test_stdout_size_preflight_leaves_no_csv(self):
        result, raw = self.export()
        limit = len(raw) + 1
        self.assertGreater(len(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2)), limit)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'flow.csv'
            protocol = Path(directory) / 'fictional.json'
            protocol.write_text(json.dumps(self.protocol, separators=(',', ':')), encoding='utf-8')
            self.assertLess(protocol.stat().st_size, limit)
            argv = ['prisma_flow_template.py', str(protocol), '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch.object(flow, 'MAX_BYTES', limit), \
                    redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr, \
                    self.assertRaises(SystemExit) as exited:
                flow.main()
            self.assertEqual(exited.exception.code, 1)
            self.assertIn('receipt exceeds size limit', stderr.getvalue())
            self.assertEqual(stdout.getvalue(), '')
            self.assertFalse(output.exists())

    def test_input_size_preflight_leaves_no_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'flow.csv'
            argv = ['prisma_flow_template.py', str(ROOT / 'examples/prisma-audit.json'), '--output', str(output)]
            with patch.object(sys, 'argv', argv), patch.object(flow, 'MAX_BYTES', 10), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as stderr, \
                    self.assertRaises(SystemExit):
                flow.main()
            self.assertIn('protocol exceeds size limit', stderr.getvalue())
            self.assertFalse(output.exists())

    def test_cli_exclusive_files_and_input_preservation(self):
        with tempfile.TemporaryDirectory(prefix='synthetic crosswalk ') as directory:
            base = Path(directory)
            protocol = base / 'fictional.json'
            original = json.dumps(self.protocol).encode('utf-8')
            protocol.write_bytes(original)
            output = base / 'flow.csv'
            result = self.cli(protocol, '--output', output, '--search-arm', '0=databases')
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt['csv']['sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
            saved = output.read_bytes()
            self.assertNotEqual(self.cli(protocol, '--output', output).returncode, 0)
            self.assertEqual(output.read_bytes(), saved)
            self.assertNotEqual(self.cli(protocol, '--output', protocol).returncode, 0)
            self.assertEqual(protocol.read_bytes(), original)
            result = self.cli(protocol, '--output', base / 'text.csv', '--text')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'transition_differences:', result.stdout)

    def test_dangling_symlink_output_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'link.csv'
            missing = Path(directory) / 'absent.csv'
            try:
                output.symlink_to(missing)
            except OSError:
                self.skipTest('symlink privilege unavailable')
            result = self.cli(ROOT / 'examples/prisma-audit.json', '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(output.is_symlink())
            self.assertFalse(missing.exists())

    def test_invalid_json_and_arm_failure_create_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            protocol, output = base / 'fictional.json', base / 'flow.csv'
            for raw in (b'{"x": 1, "x": 2}', b'{"x": NaN}', b'{"x": "\\ud800"}', b'{'):
                protocol.write_bytes(raw)
                result = self.cli(protocol, '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertFalse(output.exists())
            result = self.cli(ROOT / 'examples/prisma-audit.json', '--output', output, '--search-arm', '9=databases')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_documented_commands_execute_without_redirection(self):
        document = (ROOT / 'docs/PRISMA_FLOW_TEMPLATE.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory(prefix='synthetic flow guide ') as directory:
            for line in blocks[0].splitlines():
                if not line.strip():
                    continue
                tokens = shlex.split(line)
                self.assertEqual(tokens[:2], ['python', 'prisma_flow_template.py'])
                self.assertNotIn('>', tokens)
                args = [token.replace('OUTPUT', directory) for token in tokens[2:]]
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
            rows = list(csv.DictReader(io.StringIO((Path(directory) / 'flow-opt-in.csv').read_text(encoding='utf-8'))))
            self.assertEqual(next(row for row in rows if row['template_key'] == 'duplicates')['count'], '2')


if __name__ == '__main__':
    unittest.main()
