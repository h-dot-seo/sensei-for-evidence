"""Synthetic accounting-only Mermaid serialization; no external renderer."""
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
from unittest.mock import patch

import accounting_flow as flow
from json_io import parse_json
from prisma_audit import export_audit
import views_export

ROOT = Path(__file__).resolve().parents[1]


class AccountingFlowTests(unittest.TestCase):
    def setUp(self):
        self.protocol = parse_json((ROOT / 'examples/prisma-audit.json').read_bytes())

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'views_export.py'), 'flow',
                               *map(str, args)], capture_output=True, cwd=ROOT, timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_counts_partitions_bridges_and_detached_nodes(self):
        audit = export_audit(self.protocol)
        receipt, raw = flow.export_flow(self.protocol)
        text = raw.decode()
        for node in audit['nodes']:
            self.assertIn(node['node_id'] + ' | ' + node['unit'] + ' | ' + flow._count(node['count']), text)
        for i, part in enumerate(audit['partition_checks']):
            group = text.split('subgraph p' + str(i) + '[', 1)[1].split('\nend\n', 1)[0]
            self.assertIn(part['unit'] + ' | ' + part['status'], group)
            for j, child in enumerate(part['child_nodes'], 1):
                self.assertIn('p%dn0 --> p%dn%d' % (i, i, j), group)
                self.assertIn(child + ' | ', group)
        self.assertEqual(text.count(' -. "' + flow.BRIDGE_LABEL + '" .-> '), 2)
        for name in ('included_studies', 'extracted_result_rows', 'studies_with_extraction'):
            self.assertRegex(text, r'\nd\d+\["' + name + r' \| ')
        self.assertEqual(receipt['node_count'], len(audit['nodes']))
        self.assertEqual(receipt['document']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertIn('boundary["' + flow.BOUNDARY + '"]', text)
        self.assertNotIn('PRISMA', text.split('\n')[0])

    def test_missing_stages_are_not_zero(self):
        self.protocol.pop('reports')
        self.protocol.pop('search_plan')
        text = flow.export_flow(self.protocol)[1].decode()
        self.assertIn('reports_sought | report | not supplied', text)
        self.assertIn('search plan | NOT_SUPPLIED | missing: not supplied | incomplete: not supplied', text)
        self.assertIn('NOT_SUPPLIED | separate bookkeeping', text)

    def test_optional_membership_partition_appears(self):
        p = parse_json((ROOT / 'examples/multi-study-report.json').read_bytes())
        text = flow.export_flow(p)[1].decode()
        self.assertIn('included_report_study_memberships | report_study_membership | ', text)
        self.assertIn('report_study_memberships_without_results | report_study_membership | ', text)
        self.assertIn('report_study_membership | RECORDED_MEMBERS_PARTITION', text)

    def test_determinism_key_order_and_input_unchanged(self):
        original = copy.deepcopy(self.protocol)
        reverse = json.loads(json.dumps(self.protocol), object_pairs_hook=lambda pairs: dict(reversed(pairs)))
        self.assertEqual(flow.export_flow(self.protocol), flow.export_flow(reverse))
        self.assertEqual(self.protocol, original)
        with patch('socket.socket', side_effect=AssertionError('network')), patch('time.time', side_effect=AssertionError('clock')):
            self.assertEqual(flow.export_flow(self.protocol), flow.export_flow(original))

    def test_hostile_supplied_strings_never_enter_graph(self):
        hostile = 'Fictional" ]\nclick x "javascript:bad"\n%%{init:bad}%% <img> ``` 한글'
        self.protocol['question'] = hostile
        self.protocol['protocol_version'] = hostile
        self.protocol['screening'][0]['reason'] = hostile
        receipt, raw = flow.export_flow(self.protocol)
        self.assertNotIn(b'Fictional', raw)
        self.assertNotIn(b'click ', raw)
        self.assertNotIn(b'%%{', raw)
        self.assertNotIn(b'<img>', raw)
        self.assertNotIn(hostile, json.dumps(receipt))
        audit = export_audit(self.protocol)
        audit['nodes'][0]['node_id'] = hostile
        with self.assertRaises(ValueError):
            flow.render_flow(audit, {})

    def test_invalid_node_count_unit_stage_and_plan_fail_closed(self):
        for field, value in (('count', True), ('count', -1), ('unit', 'click x'), ('stage', 'unexpected')):
            audit = export_audit(self.protocol)
            audit['nodes'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                flow.render_flow(audit, {})
        audit = export_audit(self.protocol)
        audit['search_plan_audit']['plan_status'] = '"bad'
        with self.assertRaises(ValueError):
            flow.render_flow(audit, {})

    def test_invalid_partition_and_hash_fail_closed(self):
        for field, value in (('unit', 'report'), ('status', 'bad'), ('child_nodes', ['unique_records'])):
            audit = export_audit(self.protocol)
            audit['partition_checks'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                flow.render_flow(audit, {})
        for hashes in ({'bad\nclick': '0' * 64}, {'safe.py': 'bad\nclick'}):
            with self.assertRaises(ValueError):
                flow.render_flow(export_audit(self.protocol), hashes)

    def test_size_bound_before_output(self):
        with patch.object(flow, 'MAX_BYTES', 20), self.assertRaisesRegex(ValueError, 'size limit'):
            flow.export_flow(self.protocol)

    def test_cli_receipts_and_exclusive_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'flow.mmd'
            before = (ROOT / 'examples/prisma-audit.json').read_bytes()
            result = self.cli('examples/prisma-audit.json', '--output', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = parse_json(result.stdout)
            self.assertEqual(receipt['document']['bytes'], output.stat().st_size)
            self.assertNotIn(b'flowchart TD', result.stdout)
            expected = output.read_bytes()
            again = self.cli('examples/prisma-audit.json', '--output', output)
            self.assertEqual(again.returncode, 1)
            self.assertEqual(again.stdout, b'')
            self.assertEqual(output.read_bytes(), expected)
            other = Path(folder) / 'other.mmd'
            result = self.cli('examples/prisma-audit.json', '--format', 'mermaid', '--output', other, '--text')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(other.read_bytes(), expected)
            self.assertIn(b'accounting flow receipt', result.stdout)
            self.assertEqual((ROOT / 'examples/prisma-audit.json').read_bytes(), before)
            self.assertNotIn(b'\r', expected)
            self.assertFalse(expected.startswith(b'\xef\xbb\xbf'))

    def test_invalid_input_and_format_create_no_file(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / 'bad.json', Path(folder) / 'bad.mmd'
            for raw in (b'not json', b'{"question":1,"question":2}', b'{}', b'\xff'):
                source.write_bytes(raw)
                result = self.cli(source, '--output', output)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertFalse(output.exists())
            result = self.cli('examples/prisma-audit.json', '--format', 'dot', '--output', output)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_documented_commands_execute_verbatim(self):
        with tempfile.TemporaryDirectory() as folder:
            guide = (ROOT / 'docs/ACCOUNTING_FLOW.md').read_text(encoding='utf-8')
            blocks = re.findall(r'```sh\n(.*?)```', guide, re.S)
            self.assertEqual(len(blocks), 1)
            for line in blocks[0].splitlines():
                tokens = shlex.split(line)
                self.assertEqual(tokens.pop(0), 'python')
                result = subprocess.run([sys.executable] + [t.replace('OUTPUT', folder) for t in tokens],
                                        cwd=ROOT, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((Path(folder) / 'flow.mmd').read_bytes(), (Path(folder) / 'flow-text.mmd').read_bytes())

    def test_fixed_mermaid_grammar_without_renderer(self):
        # Syntax-shape check only, not a third-party renderer acceptance claim.
        text = flow.export_flow(self.protocol)[1].decode()
        patterns = [r'flowchart TD', r'%% [A-Za-z0-9_.]+: [0-9a-f]{64}',
                    r'(?:subgraph )?[A-Za-z0-9]+\["[^"\n<>]+"\]', r'end',
                    r'p\d+n0 --> p\d+n\d+', r'b\d+a -\. "[^"\n<>]+" \.-> b\d+b']
        for line in text.splitlines():
            self.assertTrue(any(re.fullmatch(pattern, line) for pattern in patterns), line)
        self.assertEqual(text.count('\nsubgraph '), text.count('\nend\n'))

    def test_all_valid_synthetic_protocols_render_every_audit_node(self):
        seen = 0
        for path in sorted((ROOT / 'examples').glob('*.json')):
            protocol = parse_json(path.read_bytes())
            try:
                audit = export_audit(protocol)
            except (ValueError, KeyError, TypeError):
                continue  # Other example files are intake candidates, not protocols.
            with self.subTest(example=path.name):
                text = flow.export_flow(protocol)[1].decode()
                for node in audit['nodes']:
                    self.assertIn(node['node_id'] + ' | ' + node['unit'] + ' | ' +
                                  flow._count(node['count']), text)
            seen += 1
        self.assertGreater(seen, 10)


if __name__ == '__main__':
    unittest.main()
