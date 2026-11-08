"""Detached local CSV intake is byte-traceable, never review or retrieval approval."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import bibliographic_intake as intake
import csv_export_parser
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow

ROOT = Path(__file__).resolve().parents[1]


class BibliographicIntakeTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / 'examples/paged-protocol.json').read_text(encoding='utf-8'))
        self.raw = b'record_id,source_locator,title\r\nr1,local:one,synthetic\r\nnew,local:two,other\r\n'

    def prepare(self, raw=None, protocol=None, **kwargs):
        return intake.prepare(self.protocol if protocol is None else protocol,
                              self.raw if raw is None else raw,
                              kwargs.pop('search_id', 'search-primary'),
                              kwargs.pop('searched_at', '2026-11-04T00:00:00Z'), **kwargs)

    def reseal(self, artifact):
        payload = {key: value for key, value in artifact.items() if key != 'review_target'}
        artifact['review_target']['target_sha256'] = intake.digest(payload)
        return artifact

    def invoke(self, *args):
        env = dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0')
        return subprocess.run([sys.executable, str(ROOT / 'bibliographic_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, env=env)

    def test_deterministic_exact_bytes_bom_crlf_and_spans(self):
        header = b'\xef\xbb\xbfrecord_id,source_locator,title\r\n'
        row = '합성,local:one,"first\r\nsecond"\r\n'.encode('utf-8')
        raw = header + b'\r\n' + row
        result = self.prepare(raw)
        self.assertEqual(result, self.prepare(raw))
        self.assertEqual(intake.artifact_bytes(result), intake.artifact_bytes(self.prepare(raw)))
        source = result['source_export']
        self.assertEqual(source['text'].encode('utf-8'), raw)
        self.assertEqual(source['bytes'], len(raw))
        self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest())
        parsed = result['parsed_export']
        self.assertEqual(parsed['header_source_span']['byte_start'], 0)
        self.assertEqual(parsed['header_source_span']['byte_end'], len(header))
        span = parsed['record_rows'][0]['source_span']
        self.assertEqual((span['line_start'], span['line_end']), (3, 4))
        self.assertEqual(raw[span['byte_start']:span['byte_end']], row)
        self.assertEqual(span['sha256'], hashlib.sha256(row).hexdigest())
        self.assertTrue(intake.verify(json.loads(intake.artifact_bytes(result)))['valid'])

    def test_protocol_digest_covers_full_canonical_snapshot_and_list_order(self):
        self.protocol['opaque_metadata'] = {'z': [1, 2], 'a': '합성'}
        result = self.prepare()
        expected = hashlib.sha256(canonical_json_bytes(self.protocol)).hexdigest()
        self.assertEqual(result['protocol_sha256'], expected)
        reordered = dict(reversed(list(self.protocol.items())))
        self.assertEqual(result, self.prepare(protocol=reordered))
        reordered['opaque_metadata'] = {'a': '합성', 'z': [2, 1]}
        changed = self.prepare(protocol=reordered)
        self.assertNotEqual(result['protocol_sha256'], changed['protocol_sha256'])
        self.assertNotEqual(result['review_target']['target_sha256'], changed['review_target']['target_sha256'])
        self.assertEqual(result['review_target']['target_sha256'], intake.digest(
            {k: v for k, v in result.items() if k != 'review_target'}))

    def test_explicit_mapping_search_selection_and_uninterpreted_fields(self):
        self.protocol['search_plan'][1]['operator_note'] = 'supplied metadata'
        result = self.prepare(b' ID ,Locator,unused\nx,local:one,keep me\n',
                              search_id='search-secondary', id_column=' ID ', locator_column='Locator')
        self.assertEqual(result['selected_plan_pointer'], '/search_plan/1')
        self.assertEqual(result['selected_plan_entry'], self.protocol['search_plan'][1])
        self.assertEqual(result['uninterpreted_plan_fields'], ['operator_note'])
        self.assertEqual(result['column_mapping'], {'id_column': ' ID ', 'locator_column': 'Locator'})
        self.assertEqual(result['parsed_export']['record_rows'][0]['original_values']['unused'], 'keep me')
        self.assertTrue(intake.verify(result)['valid'])
        with self.assertRaises(ValueError):
            self.prepare(b'ID,Locator\nx,y\n')
        for field in ('id_column', 'locator_column'):
            for invalid in (None, '', ' ', 4, []):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    self.prepare(**{field: invalid})

    def test_declared_search_and_supplied_timestamp_are_required(self):
        for field in ('search_id', 'searched_at'):
            for invalid in (None, '', ' ', 4, []):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    self.prepare(**{field: invalid})
        with self.assertRaises(ValueError):
            self.prepare(search_id='undeclared')
        for plan in (None, [], 'not a plan'):
            protocol = copy.deepcopy(self.protocol)
            protocol['search_plan'] = plan
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                self.prepare(protocol=protocol)
        protocol = copy.deepcopy(self.protocol)
        del protocol['search_plan']
        with self.assertRaises(ValueError):
            self.prepare(protocol=protocol)
        protocol = copy.deepcopy(self.protocol)
        protocol['search_plan'].append(copy.deepcopy(protocol['search_plan'][0]))
        with self.assertRaises(ValueError):
            self.prepare(protocol=protocol)
        result = self.prepare(searched_at='operator-supplied, not authenticated')
        self.assertEqual(result['query_export_association'], 'SUPPLIED_NOT_VERIFIED')

    def test_duplicates_conflicting_locators_remain_literal_and_unresolved(self):
        result = self.prepare(b'record_id,source_locator\nr1,z\nr1, z\nr1,z\n r1,z\n')
        parsed = result['parsed_export']
        self.assertEqual(len(parsed['record_rows']), 4)
        candidates = ['csv-row-000001', 'csv-row-000002', 'csv-row-000003']
        self.assertEqual(parsed['duplicate_record_ids'], [dict(record_id='r1', candidate_ids=candidates)])
        self.assertEqual(parsed['locator_conflicts'], [dict(record_id='r1', source_locators=[' z', 'z'],
                                                          candidate_ids=candidates)])
        self.assertEqual(result['record_identity_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(result['existing_protocol']['exact_record_overlap_ids'], ['r1'])
        self.assertTrue(intake.verify(result)['valid'])

    def test_existing_receipts_protocol_and_prisma_counts_never_mutate(self):
        before = copy.deepcopy(self.protocol)
        flow_before = run(self.protocol)['flow']
        reports_before = report_flow(self.protocol)
        result = self.prepare()
        self.assertEqual(self.protocol, before)
        self.assertEqual(result['protocol_snapshot'], before)
        self.assertEqual(result['existing_protocol']['observed_search_indices'], [0])
        self.assertEqual(result['existing_protocol']['exact_record_overlap_ids'], ['r1'])
        self.assertEqual(result['existing_protocol']['record_flow'], flow_before)
        self.assertEqual(run(result['protocol_snapshot'])['flow'], flow_before)
        self.assertEqual(report_flow(result['protocol_snapshot']), reports_before)
        self.assertEqual(result['effects'], dict(protocol_changed=False, new_searches=0,
                         new_screening_decisions=0, new_reports=0, new_evidence_rows=0))
        self.assertNotIn('protocol_candidate', result)
        result['protocol_snapshot']['searches'][0]['pages'].clear()
        result['selected_plan_entry']['query'] = 'changed only in returned copy'
        self.assertEqual(self.protocol, before)

    def test_header_only_and_verified_artifact_never_become_authentic_or_complete(self):
        artifact = self.prepare(b'\xef\xbb\xbfrecord_id,source_locator\r\n')
        verified = intake.verify(artifact)
        self.assertEqual(verified['record_rows'], 0)
        for result in (artifact, verified):
            self.assertEqual(result['review_status'], 'NOT_PERFORMED')
            self.assertEqual(result['search_completion'], 'NOT_ESTABLISHED')
            self.assertEqual(result['source_authenticity'], 'NOT_VERIFIED')
            self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
            self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
            self.assertEqual(result['external_calls'], 0)
            self.assertIn('not a search total', intake.render_text(result))
        self.assertEqual(artifact['collection_status'], 'UNREVIEWED_LOCAL_EXPORT')

    def test_tampering_rejected_even_with_recomputed_review_target_digest(self):
        artifact = self.prepare()
        mutations = {
            'source_hash': lambda a: a['source_export'].update(sha256='0' * 64),
            'source_length': lambda a: a['source_export'].update(bytes=True),
            'source_text': lambda a: a['source_export'].update(text=a['source_export']['text'] + '\n'),
            'source_encoding': lambda a: a['source_export'].update(encoding='ascii'),
            'span': lambda a: a['parsed_export']['record_rows'][0]['source_span'].update(byte_end=1),
            'span_hash': lambda a: a['parsed_export']['record_rows'][0]['source_span'].update(sha256='0' * 64),
            'derived_locator': lambda a: a['parsed_export']['record_rows'][0].update(source_locator='fake'),
            'original_field': lambda a: a['parsed_export']['record_rows'][0]['original_values'].update(title='fake'),
            'unknown_top': lambda a: a.update(approved=True),
            'unknown_nested': lambda a: a['parsed_export'].update(approved=True),
            'extra_mapping': lambda a: a['column_mapping'].update(title_column='title'),
            'protocol_hash': lambda a: a.update(protocol_sha256='0' * 64),
            'protocol_snapshot': lambda a: a['protocol_snapshot'].update(question='changed'),
            'selected_plan': lambda a: a['selected_plan_entry'].update(query='different'),
            'plan_pointer': lambda a: a.update(selected_plan_pointer='/search_plan/1'),
            'request_query': lambda a: a['search_request'].update(query='different'),
            'overlap': lambda a: a['existing_protocol'].update(exact_record_overlap_ids=[]),
            'counts': lambda a: a['effects'].update(new_evidence_rows=1),
            'approval': lambda a: a.update(review_status='APPROVED'),
            'engine': lambda a: a['engine_sha256'].update({'bibliographic_intake.py': '0' * 64}),
            'review_scope': lambda a: a['review_target'].update(scope='approved'),
        }
        for name, mutate in mutations.items():
            for reseal in (False, True):
                with self.subTest(name=name, reseal=reseal):
                    changed = copy.deepcopy(artifact)
                    mutate(changed)
                    if reseal:
                        self.reseal(changed)
                    with self.assertRaises(ValueError):
                        intake.verify(changed)
        with patch.object(intake, 'implementation_hashes', return_value={'different_engine': 'changed'}):
            with self.assertRaisesRegex(ValueError, 'implementation bytes differ'):
                intake.verify(artifact)

    def test_malformed_protocol_objects_are_rejected(self):
        for invalid in (None, [], 42, 'protocol'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                intake.prepare(invalid, self.raw, 'search-primary', 'supplied')

    def test_invalid_verification_shapes_and_schema(self):
        for invalid in (None, [], {}, {'schema_version': True}, {'schema_version': 1.0}, {'schema_version': 2}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                intake.verify(invalid)
        for key, value in [('source_export', []), ('column_mapping', None), ('search_request', [])]:
            artifact = self.prepare()
            artifact[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.verify(artifact)

    def test_safe_hostile_display_does_not_execute_or_spoof_labels(self):
        hostile = '가상\nConclusion: READY\u202e\x1b\u2028\u0085'
        self.protocol['search_plan'][0]['query'] = hostile
        self.protocol['searches'][0]['query'] = hostile
        raw = ('record_id,source_locator\n"' + hostile + '",file:///definitely-not-opened\n').encode()
        result = self.prepare(raw, searched_at=hostile)
        display = intake.render_text(result)
        self.assertIn('가상', display)
        self.assertIn('\\nConclusion: READY', display)
        for character in ('\u202e', '\x1b', '\u2028', '\u0085'):
            self.assertNotIn(character, display)
        self.assertNotIn('\nConclusion: READY', display)
        self.assertIn('Conclusion: NOT_READY', display)
        self.assertEqual(result['parsed_export']['record_rows'][0]['record_id'], hostile)

    def test_bounds_for_artifact_export_records_and_bounded_reads(self):
        artifact = self.prepare()
        size = len(intake.artifact_bytes(artifact))
        with patch.object(intake, 'MAX_ARTIFACT_BYTES', size):
            self.assertEqual(len(intake.artifact_bytes(artifact)), size)
        with patch.object(intake, 'MAX_ARTIFACT_BYTES', size - 1):
            for action in (lambda: intake.artifact_bytes(artifact), lambda: intake.verify(artifact), self.prepare):
                with self.assertRaisesRegex(ValueError, 'size limit'):
                    action()
        with patch.object(csv_export_parser, 'MAX_EXPORT_BYTES', len(self.raw) - 1):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                self.prepare()
        with patch.object(csv_export_parser, 'MAX_RECORDS', 1):
            with self.assertRaisesRegex(ValueError, 'record limit'):
                self.prepare()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bounded'
            path.write_bytes(b'abcd')
            self.assertEqual(intake.read_bounded(path, 4), b'abcd')
            with self.assertRaisesRegex(ValueError, 'size limit'):
                intake.read_bounded(path, 3)

    def test_cli_exclusive_output_utf8_newlines_and_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            protocol, export, output = (base / name for name in ('protocol.json', 'export.csv', 'artifact.json'))
            protocol.write_text(json.dumps(self.protocol), encoding='utf-8')
            for newline in (b'\n', b'\r\n', b'\r'):
                raw = b'\xef\xbb\xbfrecord_id,source_locator' + newline + '합성,local:one'.encode() + newline
                export.write_bytes(raw)
                result = self.invoke('preview', protocol, export, '--search-id', 'search-primary',
                                     '--searched-at', 'supplied timestamp', '--output', output)
                self.assertEqual(result.returncode, 0, result.stderr)
                artifact = json.loads(result.stdout.decode('utf-8'))
                self.assertEqual(artifact['source_export']['text'].encode(), raw)
                self.assertIn('합성'.encode(), output.read_bytes())
                self.assertTrue(output.read_bytes().endswith(b'\n'))
                saved = output.read_bytes()
                duplicate = self.invoke('preview', protocol, export, '--search-id', 'search-primary',
                                        '--searched-at', 'supplied timestamp', '--output', output)
                self.assertNotEqual(duplicate.returncode, 0)
                self.assertEqual(duplicate.stdout, b'')
                self.assertEqual(output.read_bytes(), saved)
                verified = self.invoke('verify', output)
                self.assertEqual(verified.returncode, 0, verified.stderr)
                self.assertTrue(json.loads(verified.stdout)['valid'])
                text = self.invoke('verify', output, '--text')
                self.assertEqual(text.returncode, 0, text.stderr)
                self.assertIn(b'Conclusion: NOT_READY', text.stdout)
                output.unlink()

    def test_cli_invalid_inputs_leave_no_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            protocol, export, output = (base / name for name in ('protocol.json', 'export.csv', 'artifact.json'))
            valid_protocol = json.dumps(self.protocol).encode()
            cases = [(valid_protocol, b'record_id,source_locator\nSECRET,too,many\n', 'search-primary'),
                     (valid_protocol, b'record_id,source_locator\nx,\xff\n', 'search-primary'),
                     (valid_protocol, self.raw, 'undeclared'),
                     (b'{"question":"a","question":"b"}', self.raw, 'search-primary'),
                     (b'{invalid', self.raw, 'search-primary'),
                     (b'null', self.raw, 'search-primary'),
                     (b'[]', self.raw, 'search-primary'),
                     (b'42', self.raw, 'search-primary')]
            for protocol_bytes, export_bytes, search_id in cases:
                protocol.write_bytes(protocol_bytes)
                export.write_bytes(export_bytes)
                result = self.invoke('preview', protocol, export, '--search-id', search_id,
                                     '--searched-at', 'supplied', '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertFalse(output.exists())
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertNotIn(b'SECRET', result.stderr)
            protocol.write_bytes(valid_protocol)
            export.write_bytes(self.raw)
            missing = self.invoke('preview', protocol, export, '--search-id', 'search-primary', '--output', output)
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
