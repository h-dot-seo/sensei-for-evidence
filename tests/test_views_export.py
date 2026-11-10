"""Entirely synthetic Markdown status rendering and exclusive-output tests."""
import copy
from contextlib import redirect_stderr, redirect_stdout
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
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from json_io import parse_json, quoted_display
import research_status
import views_export as views

ROOT = Path(__file__).resolve().parents[1]


class StatusMarkdownTests(unittest.TestCase):
    def setUp(self):
        self.protocol = parse_json((ROOT / 'examples/prisma-audit.json').read_bytes())

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'views_export.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def assert_complete(self, protocol):
        result = research_status.status(protocol)
        text = views.export_status(protocol)[1].decode('utf-8')
        for key, value in result.items():
            if key in ('counts', 'queues'):
                continue
            self.assertIn('### ' + key + '\n', text)
            self.assertIn('\n' + quoted_display(value) + '\n', text)
        for key, rows in result['queues'].items():
            count = result['counts'][key]
            self.assertIn('| ' + key + ' | ' + ('not supplied' if count is None else str(count)) + ' |', text)
            for item in rows if rows else [rows]:
                self.assertIn('\n' + quoted_display(item) + '\n', text)
        return result, text

    def test_all_status_fields_counts_and_queues_are_retained(self):
        result, text = self.assert_complete(self.protocol)
        self.assertEqual(result['counts']['records_pending_screening'], 2)
        self.assertIn('search-citation-followup', text)
        self.assertTrue(text.endswith('Census: NOT_ESTABLISHED\nConclusion: NOT_READY\n'))

    def test_all_valid_synthetic_protocol_examples_keep_optional_sections(self):
        seen = set()
        for path in sorted((ROOT / 'examples').glob('*.json')):
            protocol = parse_json(path.read_bytes())
            try:
                result = research_status.status(protocol)
            except (ValueError, KeyError, TypeError):
                continue  # This directory also contains non-protocol candidate documents.
            with self.subTest(example=path.name):
                self.assert_complete(protocol)
                seen.update(result)
        self.assertTrue({'report_study_inventory', 'report_study_inventory_review',
                         'report_study_review', 'screening_decision_history'} <= seen)

    def test_unknown_stage_differs_from_empty_queue_and_zero(self):
        self.protocol.pop('reports')
        self.protocol.pop('search_plan')
        result, text = self.assert_complete(self.protocol)
        self.assertIsNone(result['queues']['reports_pending_retrieval'])
        self.assertIn('| reports_pending_retrieval | not supplied |', text)
        self.assertIn('### report_stage\n\n```\n"NOT_SUPPLIED"', text)
        self.assertIn('### reports_pending_retrieval\n\n```\nnull', text)
        self.assertIn('| incomplete_searches | 0 |', text)
        self.assertIn('### incomplete_searches\n\n```\n[]', text)

    def test_supplied_empty_report_stage_remains_zero(self):
        self.protocol.update(reports=[], evidence=[], gaps=[])
        for key in ('experimental_units', 'synthesis_statements', 'planning_decisions', 'appraisals', 'contexts'):
            self.protocol.pop(key, None)
        _, text = self.assert_complete(self.protocol)
        self.assertIn('| reports_pending_retrieval | 0 |', text)
        self.assertIn('### report_stage\n\n```\n"SUPPLIED"', text)

    def test_incomplete_search_and_dependency_items_keep_all_nested_fields(self):
        protocol = parse_json((ROOT / 'examples/review-demo.json').read_bytes())
        protocol['searches'][0]['pages'][1]['has_more'] = True
        result, text = self.assert_complete(protocol)
        self.assertIn('page_pagination_unresolved', text)
        self.assertIn('search_index', text)
        self.assertIn('blocked_by', text)
        self.assertTrue(result['queues']['blocked_work'])

    def test_nested_input_pointers_are_kept_literally_without_joining(self):
        result = research_status.status(self.protocol)
        item = {'input_pointer': '/fictional~1rows/0/~0field', 'record_id': 'Fictional pointer record',
                'nested': {'other_pointer': '/fictional/1', 'unknown': None}}
        result['queues']['incomplete_searches'] = [item]
        result['counts']['incomplete_searches'] = 1
        original = copy.deepcopy(result)
        text = views.render_status(result).decode('utf-8')
        self.assertIn('\n' + quoted_display(item) + '\n', text)
        self.assertEqual(result, original)

    def test_every_supplied_string_is_fenced_and_tables_have_fixed_labels(self):
        hostile = '# Fictional\n```\n``````\n| fake | 999 |\n<img src=x> [x](javascript:fake)\r\x1b\u202e\u2028\u2029\u200b'
        self.protocol['question'] = hostile
        self.protocol['protocol_version'] = hostile
        self.protocol['searches'][0]['record_ids'].append(hostile)
        _, raw = views.export_status(self.protocol)
        text = raw.decode('utf-8')
        active = False
        fence = ''
        outside = []
        for line in text.splitlines():
            if re.fullmatch(r'`{3,}', line):
                if active:
                    self.assertEqual(line, fence)
                else:
                    fence = line
                active = not active
            elif not active:
                outside.append(line)
        self.assertFalse(active)
        self.assertNotIn('Fictional', '\n'.join(outside))
        self.assertNotIn('<img', '\n'.join(outside))
        self.assertIn(quoted_display(hostile), text)
        for control in ('\r', '\x1b', '\u202e', '\u2028', '\u2029', '\u200b'):
            self.assertNotIn(control, text)
        self.assertIn('\n```````\n', text)
        for row in outside:
            if row.startswith('| ') and not row.startswith(('| Queue ', '| Bookkeeping ', '| --- ')):
                self.assertRegex(row, r'^\| [a-z_]+ \| (?:[0-9]+|not supplied) \|$')

    def test_longest_backtick_fence_is_strictly_longer(self):
        document = views._Markdown()
        document.block(['Fictional ```', 'Fictional ' + '`' * 100], items=True)
        lines = bytes(document.raw).decode().splitlines()
        self.assertEqual(lines[0], '`' * 101)
        self.assertEqual(lines[-2], '`' * 101)
        self.assertEqual(len(lines), 5)

    def test_byte_determinism_key_permutation_and_no_mutation(self):
        original = copy.deepcopy(self.protocol)
        first = views.export_status(self.protocol)
        def permute(value):
            if isinstance(value, dict):
                return {key: permute(value[key]) for key in reversed(list(value))}
            if isinstance(value, list):
                return [permute(item) for item in value]
            return value
        self.assertEqual(first, views.export_status(self.protocol))
        self.assertEqual(first, views.export_status(permute(self.protocol)))
        self.assertEqual(self.protocol, original)

    def test_receipt_hashes_boundary_counts_and_no_payload_copy(self):
        receipt, raw = views.export_status(self.protocol)
        self.assertEqual(receipt['markdown']['bytes'], len(raw))
        self.assertEqual(receipt['markdown']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt['counts'], research_status.status(self.protocol)['counts'])
        for name in ('views_export.py', 'research_status.py', 'prisma_audit.py'):
            self.assertEqual(receipt['engine_sha256'][name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
        self.assertNotIn('question', receipt)
        self.assertNotIn('queues', receipt)
        self.assertEqual(receipt['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(receipt['conclusion_readiness'], 'NOT_READY')
        self.assertFalse(receipt['protocol_changed'])
        self.assertEqual(receipt['external_calls'], 0)
        self.assertIn(research_status.BOUNDARY, raw.decode())
        self.assertIn(views.BOUNDARY, raw.decode())

    def test_no_network_or_clock_and_only_existing_status_source(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('no network')), \
                patch.object(socket, 'create_connection', side_effect=AssertionError('no network')), \
                patch.object(time, 'time', side_effect=AssertionError('no clock')), \
                patch.object(views, 'status', wraps=research_status.status) as called:
            views.export_status(self.protocol)
        called.assert_called_once_with(self.protocol)

    def test_unknown_status_or_queue_fields_fail_closed(self):
        result = research_status.status(self.protocol)
        result['Fictional new field'] = 'not silently lost'
        with self.assertRaisesRegex(ValueError, 'unsupported status fields'):
            views.render_status(result)
        result.pop('Fictional new field')
        result['queues']['Fictional | malicious label'] = []
        result['counts']['Fictional | malicious label'] = 0
        with self.assertRaisesRegex(ValueError, 'unsupported status queues'):
            views.render_status(result)

    def test_invalid_count_types_mismatches_and_readiness_fields_fail(self):
        for value in (True, 1.0, -1, '0', '<img>'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                views._count(value)
        result = research_status.status(self.protocol)
        result['counts']['incomplete_searches'] += 1
        with self.assertRaisesRegex(ValueError, 'differs'):
            views.render_status(result)
        result = research_status.status(self.protocol)
        result['readiness']['counts']['Fictional extra'] = 0
        with self.assertRaisesRegex(ValueError, 'unsupported readiness'):
            views.render_status(result)

    def test_cli_json_and_text_receipts_are_utf8_without_document_duplication(self):
        with tempfile.TemporaryDirectory() as folder:
            outputs = []
            for option in ([], ['--text']):
                path = Path(folder) / ('status-text.md' if option else 'status.md')
                result = self.cli('status', ROOT / 'examples/prisma-audit.json', '--output', path, *option)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, b'')
                outputs.append(path.read_bytes())
                self.assertNotIn(b'# Supplied-data research status', result.stdout)
                self.assertNotIn(self.protocol['question'].encode(), result.stdout)
                self.assertIn(b'NOT_READY', result.stdout)
                if not option:
                    receipt = parse_json(result.stdout)
                    self.assertEqual(receipt['markdown']['bytes'], len(outputs[-1]))
            self.assertEqual(outputs[0], outputs[1])
            self.assertFalse(outputs[0].startswith(b'\xef\xbb\xbf'))
            self.assertNotIn(b'\r', outputs[0])

    def test_existing_file_directory_and_missing_parent_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            output = base / 'status.md'
            output.write_bytes(b'Fictional original')
            for path in (output, base, base / 'absent' / 'status.md'):
                result = self.cli('status', ROOT / 'examples/prisma-audit.json', '--output', path)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertNotIn(b'Traceback', result.stderr)
            self.assertEqual(output.read_bytes(), b'Fictional original')
            self.assertFalse((base / 'absent').exists())

    def test_second_export_refuses_and_preserves_saved_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'status.md'
            args = ('status', ROOT / 'examples/prisma-audit.json', '--output', path)
            self.assertEqual(self.cli(*args).returncode, 0)
            before = path.read_bytes()
            result = self.cli(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(path.read_bytes(), before)

    def test_existing_and_dangling_symlinks_are_never_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            target = base / 'target.md'
            target.write_bytes(b'Fictional retained target')
            for name, destination in (('existing.md', target), ('dangling.md', base / 'missing.md')):
                output = base / name
                try:
                    output.symlink_to(destination)
                except (OSError, NotImplementedError):
                    self.skipTest('symlink privilege unavailable')
                result = self.cli('status', ROOT / 'examples/prisma-audit.json', '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(output.is_symlink())
                self.assertEqual(result.stdout, b'')
            self.assertFalse((base / 'missing.md').exists())
            self.assertEqual(target.read_bytes(), b'Fictional retained target')

    def test_lstat_guard_prevents_open_on_every_platform(self):
        path = Mock(spec=Path)
        with self.assertRaises(FileExistsError):
            views._write_new(path, b'fictional')
        path.open.assert_not_called()
        path.lstat.side_effect = PermissionError('Fictional inspection failure')
        with self.assertRaises(PermissionError):
            views._write_new(path, b'fictional')
        path.open.assert_not_called()
        path.lstat.side_effect = FileNotFoundError()
        path.open.return_value = MagicMock()
        views._write_new(path, b'fictional')
        path.open.assert_called_once_with('xb')

    def test_invalid_input_never_creates_output_or_prints_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            protocol, output = base / 'fictional.json', base / 'status.md'
            for raw in (b'{"question":1,"question":2}', b'{"x":NaN}', b'{"x":1e999}',
                        b'{"x":"\\ud800"}', b'\xff', b'{', b'[]', b'null', b'{}', b'[' * 2000):
                protocol.write_bytes(raw)
                result = self.cli('status', protocol, '--output', output)
                self.assertNotEqual(result.returncode, 0, raw[:80])
                self.assertEqual(result.stdout, b'')
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertFalse(output.exists())

    def test_input_size_limit_creates_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            protocol, output = base / 'fictional.json', base / 'status.md'
            protocol.write_bytes(b' ' * (views.MAX_BYTES + 1))
            result = self.cli('status', protocol, '--output', output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'protocol exceeds size limit', result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertFalse(output.exists())

    def test_markdown_size_limit_before_write(self):
        with patch.object(views, 'MAX_BYTES', 100), self.assertRaisesRegex(ValueError, 'Markdown exceeds'):
            views.export_status(self.protocol)
        document = views._Markdown()
        with patch.object(views, 'MAX_BYTES', 4):
            document.line('abc')
            with self.assertRaises(ValueError):
                document.line()

    def test_json_and_text_receipt_preflight_before_any_output(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            source, output = base / 'fictional.json', base / 'status.md'
            source.write_bytes(b'{}')
            for option in ([], ['--text']):
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.object(sys, 'argv', ['views_export.py', 'status', str(source), '--output', str(output)] + option), \
                        patch.object(views, 'MAX_BYTES', 100), \
                        patch.object(views, 'export_status', return_value=({'boundary': 'Fictional ' * 200}, b'md')), \
                        redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as exit_info:
                    views.main()
                self.assertEqual(exit_info.exception.code, 1)
                self.assertIn('receipt exceeds size limit', stderr.getvalue())
                self.assertEqual(stdout.getvalue(), '')
                self.assertFalse(output.exists())

    def test_only_status_subcommand_and_required_output(self):
        for args in (['status', ROOT / 'examples/prisma-audit.json'], ['flow'], ['records'], ['handoff']):
            result = self.cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
        listed = subprocess.run([sys.executable, 'sensei.py', 'list'], cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn(b'views_export.py', listed.stdout)

    def test_documented_commands_replay_exactly_without_redirection(self):
        document = (ROOT / 'docs/SHAREABLE_VIEWS.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', document, re.S)
        self.assertEqual(len(blocks), 1)
        with tempfile.TemporaryDirectory(prefix='fictional status guide ') as folder:
            for line in blocks[0].splitlines():
                if not line.strip():
                    continue
                tokens = shlex.split(line)
                self.assertEqual(tokens[:3], ['python', 'views_export.py', 'status'])
                self.assertNotIn('>', tokens)
                result = self.cli(*[token.replace('OUTPUT', folder) for token in tokens[2:]])
                self.assertEqual(result.returncode, 0, result.stderr)
            first = (Path(folder) / 'status.md').read_bytes()
            self.assertEqual(first, (Path(folder) / 'status-text-receipt.md').read_bytes())


if __name__ == '__main__':
    unittest.main()
