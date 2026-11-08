"""Synthetic local passage observations, including deliberately false associations."""
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

import artifact_review as ar
from json_io import canonical_json_bytes
import result_intake
import result_passage_check as pc

ROOT = Path(__file__).resolve().parents[1]
UNSET = object()


def fixture(name):
    return json.loads((ROOT / 'examples' / ('result-passage-' + name + '.json')).read_text(encoding='utf-8'))


class PassageTests(unittest.TestCase):
    def setUp(self):
        self.p, self.c, self.m = (fixture(n) for n in ('protocol', 'candidates', 'manifest'))
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.body = (ROOT / 'examples/result-passage-source.txt').read_bytes()
        self.file = self.root / 'result-passage-source.txt'; self.file.write_bytes(self.body)

    def check(self, p=None, c=None, m=None):
        if not ar.secure_open_supported():
            self.skipTest('POSIX secure traversal unavailable; fail-closed mocked separately')
        return pc.check_passages(self.p if p is None else p, self.c if c is None else c,
                                 self.m if m is None else m, self.root)

    def catalog(self, m=None):
        if not ar.secure_open_supported(): self.skipTest('POSIX secure traversal unavailable')
        return pc.catalog(self.p, self.c, self.m if m is None else m, self.root)

    def rebind(self):
        self.m['protocol_sha256'] = pc.digest(self.p)
        self.m['candidate_document_sha256'] = pc.digest(self.c)
        for entry in self.m['sources']:
            source = next(s for s in self.p['report_sources'] if s['source_id'] == entry['source_id'])
            entry['source_descriptor_sha256'] = pc.digest(source)

    def source_body(self, body, start=0, end=None, quote=None):
        self.body = body; self.file.write_bytes(body)
        self.p['report_sources'][0]['document_sha256'] = hashlib.sha256(body).hexdigest()
        self.m['sources'][0]['bytes'] = len(body)
        end = len(body) if end is None else end
        self.m['passages'] = [dict(self.m['passages'][0], byte_start=start, byte_end=end,
                                  quote=body[start:end].decode('utf-8') if quote is None else quote)]
        self.rebind()

    def reject(self, p=UNSET, c=UNSET, m=UNSET, mode='check'):
        with patch.object(pc, 'open_root', side_effect=AssertionError('metadata before read')), \
             patch.object(pc, '_read_source', side_effect=AssertionError('metadata before source')):
            with self.assertRaises((ValueError, TypeError, KeyError)):
                (pc.check_passages if mode == 'check' else pc.catalog)(
                    self.p if p is UNSET else p, self.c if c is UNSET else c,
                    self.m if m is UNSET else m, self.root)

    def cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(ROOT / 'result_passage_check.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, env=env)

    def inputs(self):
        paths = []
        for name, value in [('protocol', self.p), ('candidates', self.c), ('manifest', self.m)]:
            path = self.root / (name + '.json')
            path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
            paths.append(path)
        return paths

    def test_template_empty_selection_separate_shapes_literal_values_no_reads(self):
        before = copy.deepcopy((self.p, self.c))
        with patch.object(pc, 'open_root', side_effect=AssertionError('no root')):
            result = pc.template(self.p, self.c)
        self.assertEqual(result['manifest']['sources'], [])
        self.assertEqual(result['manifest']['passages'], [])
        self.assertEqual(set(result['blank_source']), pc.SOURCE_FIELDS)
        self.assertEqual(set(result['blank_passage']), pc.PASSAGE_FIELDS)
        self.assertTrue(all(v is None for v in result['blank_passage'].values()))
        self.assertTrue(all(v is None for v in result['blank_source'].values()))
        self.assertEqual(result['available_candidates'][0]['evidence_fields'],
                         {k: self.c['candidates'][0]['evidence'][k] for k in pc.EVIDENCE_FIELDS})
        self.assertTrue(result['available_sources'][0]['selectable'])
        self.assertNotIn('review_document', result)
        self.assertEqual((self.p, self.c), before)
        self.assertEqual(result, pc.template(self.p, self.c))

    def test_fixture_and_independent_manual_intake_target(self):
        result = self.check(); target = result_intake.prepare(self.p, self.c)
        self.assertEqual(result['manual_intake_target_sha256'], target['target']['target_sha256'])
        self.assertTrue(result['all_requested_passages_match'])
        self.assertEqual([r['status'] for r in result['passages']], ['TEXT_MATCH', 'TEXT_MATCH'])
        self.assertTrue(all(v is None for k, v in target['review_document'].items()
                            if k not in ('schema_version', 'target_sha256')))
        self.assertEqual(result, self.check())
        self.assertEqual(result['protocol_sha256'], pc.digest(self.p))
        self.assertEqual(result['candidate_document_sha256'], pc.digest(self.c))
        self.assertEqual(result['manifest_sha256'], pc.digest(self.m))

    def test_no_semantic_assessment_even_false_field_and_mechanism_associations(self):
        self.c['candidates'][0]['evidence']['result'] = 'An intentionally unrelated manual claim.'
        self.m['passages'][1]['evidence_field'] = 'mechanism_basis'
        self.rebind(); result = self.check()
        self.assertTrue(result['all_requested_passages_match'])
        self.assertEqual(result['passages'][0]['field_value'], 'An intentionally unrelated manual claim.')
        self.assertEqual(result['passages'][1]['field_value'], 'unknown')
        self.assertEqual(result['field_meaning_assessment'], 'NOT_PERFORMED')
        self.assertEqual(result['scientific_acceptance'], 'NOT_ASSESSED')
        self.assertEqual(result['extraction_completeness'], 'NOT_ESTABLISHED')
        self.assertFalse(result['protocol_changed']); self.assertFalse(result['candidate_document_changed'])
        self.assertEqual(result['external_calls'], 0)
        self.assertNotIn('physical_lines', result['sources'][0])
        self.assertNotIn(self.body.decode(), json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_no_mutation_or_implicit_review_import_or_network(self):
        before = copy.deepcopy((self.p, self.c, self.m))
        with patch.object(result_intake, 'assemble', side_effect=AssertionError('no import')), \
             patch('socket.create_connection', side_effect=AssertionError('no network')):
            result = self.check()
        result['passages'][0]['field_value'] = 'detached edit'
        result['sources'][0]['supplied_source']['document_version'] = 'detached edit'
        self.assertEqual((self.p, self.c, self.m), before)

    def test_entire_protocol_and_all_candidates_validate_before_root(self):
        p = copy.deepcopy(self.p); p['reports'][0]['retrieval'] = 'pending'
        self.reject(p=p)
        c = copy.deepcopy(self.c); row = copy.deepcopy(c['candidates'][0]); row['evidence']['evidence_id'] = 'second'
        row['extracted_at'] = '2026-02-29'; c['candidates'].append(row)
        self.reject(c=c)
        for date in ('2026-2-04', '2026-11-04\n', '0000-01-01'):
            c = copy.deepcopy(self.c); c['candidates'][0]['extracted_at'] = date
            self.reject(c=c)
        p = copy.deepcopy(self.p); p['question'] = float('nan'); self.reject(p=p)

    def test_entire_manifest_including_later_passage_validates_before_read(self):
        for fields in (dict(evidence_field='unsupported'), dict(source_id='missing'), dict(byte_start=-1),
                       dict(byte_end=len(self.body) + 1), dict(candidate_index=True), dict(quote='')):
            m = copy.deepcopy(self.m); m['passages'][-1].update(fields)
            with self.subTest(fields=fields): self.reject(m=m)
        m = copy.deepcopy(self.m); m['sources'].append(dict(m['sources'][0], source_id='missing'))
        self.reject(m=m)

    def test_manifest_exact_top_schema_and_input_hashes(self):
        for m in (None, [], {}, dict(self.m, extra=1), dict(self.m, schema_version=True),
                  dict(self.m, schema_version=1.0), dict(self.m, sources=[]), dict(self.m, passages=[]),
                  dict(self.m, protocol_sha256='A' * 64), dict(self.m, candidate_document_sha256='0' * 64),
                  dict(self.m, protocol_sha256=True), dict(self.m, candidate_document_sha256='x' * 64)):
            with self.subTest(m=m): self.reject(m=m)
        self.reject(m=pc.template(self.p, self.c)['manifest'])
        for field in self.m:
            m = copy.deepcopy(self.m); del m[field]; self.reject(m=m)

    def test_source_entry_exact_fields_and_types(self):
        row = self.m['sources'][0]
        invalid = [None, [], dict(row, extra=True)]
        for field in row:
            bad = copy.deepcopy(row); del bad[field]; invalid.append(bad)
        for field in ('source_id', 'report_id', 'source_descriptor_sha256', 'path'):
            for value in (None, True, 1, [], {}, '', ' '): invalid.append(dict(row, **{field: value}))
        for value in (True, -1, 1.0, '417', None, pc.MAX_SOURCE_BYTES + 1):
            invalid.append(dict(row, bytes=value))
        for bad in invalid:
            m = copy.deepcopy(self.m); m['sources'] = [bad]
            with self.subTest(bad=bad): self.reject(m=m)

    def test_passage_entry_exact_fields_and_types(self):
        row = self.m['passages'][0]
        invalid = [None, [], dict(row, extra=True)]
        for field in row:
            bad = dict(row); del bad[field]; invalid.append(bad)
        for field in ('passage_id', 'evidence_field', 'source_id', 'quote'):
            for value in (None, True, 1, [], {}, ''): invalid.append(dict(row, **{field: value}))
        for field in ('candidate_index', 'byte_start', 'byte_end'):
            for value in (None, True, 1.0, '1', -1): invalid.append(dict(row, **{field: value}))
        invalid.extend([dict(row, candidate_index=1), dict(row, evidence_field='locator'),
                        dict(row, byte_end=row['byte_start']), dict(row, byte_start=row['byte_end']),
                        dict(row, quote='x' * (pc.MAX_QUOTE_BYTES + 1))])
        for bad in invalid:
            m = copy.deepcopy(self.m); m['passages'] = [bad]
            with self.subTest(bad=repr(bad)[:100]): self.reject(m=m)

    def test_null_digest_and_entire_descriptor_drift_reject_before_read(self):
        for field, value in (('document_sha256', None), ('document_version', 'Changed'),
                             ('source_locator', 'fictional://changed')):
            p = copy.deepcopy(self.p); p['report_sources'][0][field] = value
            m = copy.deepcopy(self.m); m['protocol_sha256'] = pc.digest(p)
            self.reject(p=p, m=m)
        p = copy.deepcopy(self.p); p['report_sources'][0]['document_sha256'] = None
        m = copy.deepcopy(self.m); m['protocol_sha256'] = pc.digest(p)
        m['sources'][0]['source_descriptor_sha256'] = pc.digest(p['report_sources'][0])
        self.reject(p=p, m=m)
        self.assertFalse(pc.template(p, self.c)['available_sources'][0]['selectable'])

    def test_candidate_selected_membership_and_same_report(self):
        self.p['report_sources'].append(dict(self.p['report_sources'][0], source_id='unselected'))
        self.rebind(); m = copy.deepcopy(self.m)
        m['sources'].append(dict(m['sources'][0], source_id='unselected', path='other.txt',
                               source_descriptor_sha256=pc.digest(self.p['report_sources'][1])))
        self.reject(m=m, mode='catalog')
        # Two candidates may select different sources for the same report; a
        # passage cannot borrow the other candidate's reference.
        second = copy.deepcopy(self.c['candidates'][0]); second['evidence']['evidence_id'] = 'second'
        second['source_references'][0]['source_id'] = 'unselected'; self.c['candidates'].append(second)
        self.rebind(); self.m['passages'][0]['candidate_index'] = 1; self.reject()
        m = copy.deepcopy(self.m); m['sources'][0]['report_id'] = 'other'; self.reject(m=m)

    def test_duplicates_ids_paths_anchors_and_unused_source(self):
        for collection in ('sources', 'passages'):
            m = copy.deepcopy(self.m); m[collection].append(copy.deepcopy(m[collection][0])); self.reject(m=m)
        m = copy.deepcopy(self.m); m['passages'].append(dict(m['passages'][0], passage_id='different', quote='different'))
        self.reject(m=m)
        self.p['report_sources'].append(dict(self.p['report_sources'][0], source_id='second-source'))
        self.c['candidates'][0]['source_references'].append(dict(source_id='second-source', extraction_locator='Fictional'))
        self.m['sources'].append(dict(self.m['sources'][0], source_id='second-source', path='RESULT-PASSAGE-SOURCE.TXT',
                                     source_descriptor_sha256=pc.digest(self.p['report_sources'][1])))
        self.rebind(); self.reject()
        self.m['sources'][1]['path'] = 'other.txt'; self.reject()
        self.m['passages'] = []; self.catalog()  # Catalog may intentionally map unused sources.

    def test_uninspected_references_and_unanchored_fields_are_not_completeness(self):
        self.p['report_sources'].append(dict(self.p['report_sources'][0], source_id='uninspected', document_sha256=None))
        self.c['candidates'][0]['source_references'].append(dict(source_id='uninspected', extraction_locator='Fictional unknown'))
        self.rebind(); result = self.check()
        self.assertEqual(result['uninspected_source_references'], [dict(candidate_index=0, report_id='report-one', source_id='uninspected')])
        self.assertEqual([r['evidence_field'] for r in result['unanchored_fields']],
                         ['model', 'intervention', 'comparator', 'endpoint', 'mechanism_basis'])
        self.assertEqual(result['extraction_completeness'], 'NOT_ESTABLISHED')

    def test_unsafe_relative_paths_casefold_protected_metadata(self):
        for value in ('../x', '/tmp/x', './x', 'x//y', 'x/', 'x/../y', 'C:/x', 'x\\y',
                      'https://x', '.git/config', 'a/.AWS/x', '.CoDeX/x', '.agents/x', 'x\x00', 'x\n', 'x.', 'x '):
            m = copy.deepcopy(self.m); m['sources'][0]['path'] = value
            with self.subTest(path=value): self.reject(m=m)

    def test_unsafe_roots_and_platform_fail_closed(self):
        for root in ('/', '.', '//', 'a/../b', 'a/.git/b', 'a/.AWS', '/tmp/.CoDeX/x', './foo', '/tmp/a/./b', 'C:\\synthetic-root'):
            with patch.object(pc, 'open_root', side_effect=AssertionError('unsafe root not opened')):
                with self.assertRaises(ValueError): pc.check_passages(self.p, self.c, self.m, root)
        with patch.object(pc, 'secure_open_supported', return_value=False), \
             patch.object(pc, 'open_root', side_effect=AssertionError('no unsupported read')):
            with self.assertRaisesRegex(ValueError, 'unavailable.*Windows'):
                # Use a portable spelling so unsafe Windows backslashes do not
                # short-circuit the platform gate this assertion exercises.
                pc.check_passages(self.p, self.c, self.m, 'synthetic-source-root')

    def test_metadata_failure_takes_precedence_over_unsupported_platform(self):
        m = copy.deepcopy(self.m); m['passages'][-1]['quote'] = False
        with patch.object(pc, 'secure_open_supported', side_effect=AssertionError('metadata first')):
            self.reject(m=m)

    def test_bytes_failed_never_decode_or_expose_observed_quotes(self):
        for status, action in [('HASH_MISMATCH', lambda: self.file.write_bytes(b'x' * len(self.body))),
                               ('SIZE_MISMATCH', lambda: self.file.write_bytes(b'x')),
                               ('MISSING', lambda: self.file.unlink(missing_ok=True))]:
            self.file.write_bytes(self.body); action()
            with patch.object(pc, '_decode', side_effect=AssertionError('no decode')):
                result = self.check()
            self.assertEqual(result['sources'][0]['status'], status)
            self.assertTrue(all(p['observed_quote'] is None for p in result['passages']))
            self.assertTrue(all(p['status'] == 'SOURCE_BYTES_NOT_MATCHED' for p in result['passages']))
            self.assertNotIn('physical_lines', self.catalog()['sources'][0])
            self.assertFalse(result['all_requested_passages_match'])

    def test_whole_source_utf8_validation_even_if_anchor_is_valid_ascii(self):
        for body, text_status in [(b'valid\ninvalid\xff', 'INVALID_UTF8'),
                                  (b'valid\n\0binary', 'UNSUPPORTED_BINARY_OR_CONTROL_TEXT'),
                                  (b'valid\n\x01binary', 'UNSUPPORTED_BINARY_OR_CONTROL_TEXT')]:
            self.source_body(body, 0, 5, 'valid')
            result = self.check()
            self.assertEqual(result['sources'][0]['status'], 'BYTES_MATCH')
            self.assertEqual(result['sources'][0]['text_status'], text_status)
            self.assertEqual(result['passages'][0]['status'], 'SOURCE_' + text_status)
            self.assertIsNone(result['passages'][0]['observed_quote'])
            self.assertNotIn('physical_lines', self.catalog()['sources'][0])

    def test_multibyte_bom_crlf_catalog_exact_physical_ranges(self):
        body = '\ufeff한글\r\nécho\nlast\rfinal'.encode('utf-8')
        self.source_body(body, 3, 9, '한글')
        result = self.check(); self.assertEqual(result['passages'][0]['status'], 'TEXT_MATCH')
        lines = self.catalog()['sources'][0]['physical_lines']
        self.assertEqual([r['text'] for r in lines], ['\ufeff한글\r\n', 'écho\n', 'last\r', 'final'])
        self.assertEqual([r['line_number'] for r in lines], [1, 2, 3, 4])
        self.assertEqual([(r['byte_start'], r['byte_end']) for r in lines], [(0, 11), (11, 17), (17, 22), (22, 27)])
        self.assertEqual(b''.join(r['text'].encode('utf-8') for r in lines), body)
        self.assertEqual(pc._physical_lines(b'\n\r\n\r'), [dict(line_number=1,byte_start=0,byte_end=1,text='\n'),
            dict(line_number=2,byte_start=1,byte_end=3,text='\r\n'), dict(line_number=3,byte_start=3,byte_end=4,text='\r')])
        self.assertEqual(pc._physical_lines(b''), [])

    def test_codepoint_boundary_and_literal_mismatch_no_normalization(self):
        self.source_body('é\r\n'.encode('utf-8'), 0, 2, 'é')
        for start, end in ((1, 2), (0, 1), (1, 3)):
            self.m['passages'][0].update(byte_start=start, byte_end=end)
            self.assertEqual(self.check()['passages'][0]['status'], 'INVALID_UTF8_BOUNDARY')
        self.m['passages'][0].update(byte_start=0, byte_end=4, quote='é\n')
        result = self.check(); self.assertEqual(result['passages'][0]['status'], 'QUOTE_MISMATCH')
        self.assertEqual(result['passages'][0]['observed_quote'], 'é\r\n')
        self.m['passages'][0].update(byte_start=0, byte_end=2, quote='e\u0301')
        self.assertEqual(self.check()['passages'][0]['status'], 'QUOTE_MISMATCH')

    def test_repeated_same_quote_at_distinct_offsets_is_retained(self):
        self.source_body(b'repeat repeat', 0, 6, 'repeat')
        self.m['passages'].append(dict(self.m['passages'][0], passage_id='repeat-two', byte_start=7, byte_end=13))
        result = self.check(); self.assertTrue(result['all_requested_passages_match'])
        self.assertEqual([p['byte_start'] for p in result['passages']], [0, 7])
        self.m['passages'][1]['evidence_field'] = 'endpoint'
        self.assertTrue(self.check()['all_requested_passages_match'])

    def test_catalog_empty_passages_verified_text_no_automatic_anchors(self):
        self.m['passages'] = []
        result = self.catalog()
        self.assertEqual(result['passages'], [])
        self.assertFalse(result['all_requested_passages_match'])
        self.assertTrue(result['all_requested_bytes_match'])
        self.assertEqual(len(result['unanchored_fields']), 7)
        lines = result['sources'][0]['physical_lines']
        self.assertEqual(''.join(r['text'] for r in lines).encode(), self.body)
        self.assertEqual(len(lines), 7)
        self.reject()

    def test_caps_before_source_access_and_output_cap(self):
        for name, limit in [('MAX_SOURCES', 0), ('MAX_PASSAGES', 1), ('MAX_SOURCE_BYTES', len(self.body) - 1),
                            ('MAX_TOTAL_BYTES', len(self.body) - 1), ('MAX_QUOTE_BYTES', 1), ('MAX_MANIFEST_BYTES', 1)]:
            with self.subTest(name=name), patch.object(pc, name, limit): self.reject()
        with patch.object(pc, 'MAX_OUTPUT_BYTES', 1):
            with self.assertRaises(ValueError): pc.template(self.p, self.c)

    def test_per_span_cap_before_read_even_if_short_expected_quote(self):
        self.source_body(b'x' * (pc.MAX_QUOTE_BYTES + 1), 0, 1, 'x')
        self.m['passages'][0]['byte_end'] = pc.MAX_QUOTE_BYTES + 1
        self.reject()
        self.m['passages'][0]['byte_end'] = pc.MAX_QUOTE_BYTES
        self.assertEqual(self.check()['passages'][0]['status'], 'QUOTE_MISMATCH')

    def test_catalog_line_caps_count_before_any_line_dicts_and_check_still_allowed(self):
        self.source_body(b'x\n' * 10, 0, 1, 'x')
        for name, limit in [('MAX_CATALOG_LINES_PER_SOURCE', 9), ('MAX_CATALOG_LINES_TOTAL', 9)]:
            with self.subTest(name=name), patch.object(pc, name, limit), \
                 patch.object(pc, '_physical_lines', side_effect=AssertionError('count before allocation')):
                with self.assertRaisesRegex(ValueError, 'catalog physical line count'):
                    self.catalog()
                self.assertTrue(self.check()['all_requested_passages_match'])
        with patch.object(pc, 'MAX_CATALOG_LINES_PER_SOURCE', 10), patch.object(pc, 'MAX_CATALOG_LINES_TOTAL', 10):
            self.assertEqual(len(self.catalog()['sources'][0]['physical_lines']), 10)

    def test_duplicate_large_field_output_budget_rejected_before_root(self):
        # Each input is small and valid; output repeats this field by association.
        self.c['candidates'][0]['evidence']['result'] = 'x' * 20_000
        self.m['passages'] = [dict(self.m['passages'][0], passage_id='p' + str(i), byte_start=i, byte_end=i+1, quote='x')
                              for i in range(10)]
        self.rebind()
        with patch.object(pc, 'MAX_OUTPUT_BYTES', 150_000):
            self.reject()

    def test_uninspected_large_reference_output_budget_rejected_before_root(self):
        sid = 'uninspected-' + 'x' * 25_000
        self.p['report_sources'].append(dict(self.p['report_sources'][0], source_id=sid))
        self.c['candidates'][0]['source_references'].append(dict(source_id=sid, extraction_locator='Fictional'))
        self.rebind()
        with patch.object(pc, 'MAX_OUTPUT_BYTES', 20_000): self.reject()

    def test_non_json_python_values_not_silently_normalized(self):
        m = copy.deepcopy(self.m); m['passages'] = tuple(m['passages']); self.reject(m=m)
        c = copy.deepcopy(self.c); c['candidates'][0]['source_references'] = tuple(c['candidates'][0]['source_references'])
        self.reject(c=c)
        p = copy.deepcopy(self.p); p[3] = 'not a JSON key'; self.reject(p=p)

    def test_python_api_circular_containers_rejected_without_looping(self):
        p = copy.deepcopy(self.p); p['cycle'] = p
        self.reject(p=p)
        c = copy.deepcopy(self.c); c['candidates'].append(c['candidates'])
        self.reject(c=c)
        m = copy.deepcopy(self.m); m['passages'].append(m)
        self.reject(m=m)
        # Shared-but-acyclic JSON containers retain ordinary JSON semantics.
        shared = ['same']; value = dict(first=shared, second=shared)
        self.assertEqual(pc._normalize(value, 100, 'test'), dict(first=['same'], second=['same']))

    def test_render_budget_checked_incrementally_before_join(self):
        result = self.check()
        with patch.object(pc, 'MAX_OUTPUT_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'text observation exceeds'):
                pc.render_text(result)

    def test_cross_report_passage_source_cannot_borrow_other_candidates_selection(self):
        self.p['searches'][0]['record_ids'].append('record-two')
        self.p['screening'].append(dict(record_id='record-two', decision='include', reason='Fictional'))
        self.p['reports'].append(dict(self.p['reports'][0], report_id='report-two', record_ids=['record-two'], study_ids=['study-two']))
        source = dict(self.p['report_sources'][0], source_id='other-source', report_id='report-two')
        self.p['report_sources'].append(source)
        candidate = copy.deepcopy(self.c['candidates'][0]); candidate['report_id'] = 'report-two'
        candidate['evidence'].update(record_id='record-two', study_id='study-two', evidence_id='other-result')
        candidate['source_references'][0]['source_id'] = 'other-source'
        self.c['candidates'].append(candidate)
        self.m['sources'].append(dict(self.m['sources'][0], source_id='other-source', report_id='report-two',
                                      source_descriptor_sha256=pc.digest(source), path='other.txt'))
        self.m['passages'][0]['source_id'] = 'other-source'
        self.rebind(); self.reject()

    def test_empty_utf8_catalog_and_no_empty_range_check(self):
        self.source_body(b'', 0, 1, 'x'); self.m['passages'] = []
        result = self.catalog()
        self.assertTrue(result['all_requested_bytes_match']); self.assertTrue(result['all_requested_text_decodable'])
        self.assertEqual(result['sources'][0]['physical_lines'], [])
        self.m['passages'] = [dict(fixture('manifest')['passages'][0], byte_start=0, byte_end=0)]
        self.reject()

    def test_cli_raw_root_alias_spelling_is_not_normalized(self):
        p, c, m = self.inputs()
        for root in ('./' + str(self.root).lstrip('/'), str(self.root) + '/.', str(self.root) + '//',
                     str(self.root) + '/.GIT/private'):
            result = self.cli('check', p, c, m, '--root', root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'root is unsafe', result.stderr)
            self.assertNotIn(str(self.root).encode(), result.stderr)

    def test_actual_implementation_fingerprints(self):
        result = self.check()
        for name in ('result_passage_check.py', 'artifact_review.py', 'result_intake.py', 'report_review_links.py', 'json_io.py'):
            self.assertEqual(result['engine_sha256'][name], hashlib.sha256((ROOT / name).read_bytes()).hexdigest())

    @unittest.skipUnless(ar.secure_open_supported(), 'secure POSIX filesystem')
    def test_symlink_root_parent_file_and_hardlink_nonregular_rejected(self):
        target = self.root / 'target'; self.file.rename(target); self.file.symlink_to(target)
        self.assertEqual(self.check()['sources'][0]['status'], 'REJECTED_FILE_TYPE')
        self.file.unlink(); os.link(target, self.file)
        self.assertEqual(self.check()['sources'][0]['status'], 'REJECTED_FILE_TYPE')
        self.file.unlink(); os.mkfifo(self.file)
        with patch.object(pc.os, 'read', side_effect=AssertionError('do not read FIFO')):
            self.assertEqual(self.check()['sources'][0]['status'], 'REJECTED_FILE_TYPE')
        self.file.unlink(); self.file.mkdir()
        self.assertEqual(self.check()['sources'][0]['status'], 'REJECTED_FILE_TYPE'); self.file.rmdir()
        self.file.write_bytes(self.body)
        alias = self.root / 'alias'; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): pc.check_passages(self.p, self.c, self.m, alias)
        m = copy.deepcopy(self.m); m['sources'][0]['path'] = 'alias/result-passage-source.txt'
        self.assertEqual(self.check(m=m)['sources'][0]['status'], 'UNREADABLE_OR_UNSAFE_PATH')

    @unittest.skipUnless(ar.secure_open_supported(), 'secure POSIX filesystem')
    def test_growth_and_same_size_change_during_one_descriptor_read(self):
        for grow in (True, False):
            self.file.write_bytes(self.body); original = pc.os.read; done = False
            def reading(fd, count):
                nonlocal done
                if not done:
                    done = True
                    self.file.write_bytes(self.body + b'growth' if grow else b'x' * len(self.body))
                    metadata = self.file.stat()
                    os.utime(self.file, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 10_000_000))
                return original(fd, count)
            with patch.object(pc.os, 'read', side_effect=reading):
                result = self.check()
            self.assertEqual(result['sources'][0]['status'], 'CHANGED_DURING_READ')
            self.assertTrue(all(p['observed_quote'] is None for p in result['passages']))

    @unittest.skipUnless(ar.secure_open_supported(), 'secure POSIX filesystem')
    def test_replacement_between_stat_open_rejected_and_source_opens_only_once(self):
        original = pc.os.open; source_opens = 0
        def opening(path, flags, *args, **kwargs):
            nonlocal source_opens
            if path == self.file.name and kwargs.get('dir_fd') is not None:
                source_opens += 1
                self.file.rename(self.root / 'old')
                self.file.write_bytes(self.body)
            return original(path, flags, *args, **kwargs)
        with patch.object(pc.os, 'open', side_effect=opening), patch.object(pc, 'secure_open_supported', return_value=True):
            self.assertEqual(pc.check_passages(self.p, self.c, self.m, self.root)['sources'][0]['status'], 'REJECTED_FILE_TYPE')
        self.assertEqual(source_opens, 1)
        self.assertTrue(self.check()['all_requested_passages_match'])

    def test_render_controls_quote_side_by_side_and_physical_line_numbers(self):
        self.c['candidates'][0]['evidence']['result'] = '한글\n\x1b[31m\u202e'
        self.rebind(); result = self.check(); rendered = pc.render_text(result)
        self.assertIn('Manual field value:', rendered); self.assertIn('Expected quote:', rendered)
        self.assertIn('Observed quote:', rendered); self.assertIn('한글', rendered)
        self.assertNotIn('\x1b', rendered); self.assertNotIn('\u202e', rendered)
        self.assertIn('Physical line 4 bytes [199, 257)', pc.render_text(self.catalog()))

    def test_cli_utf8_template_catalog_check_and_nonzero_mismatch_output(self):
        p, c, m = self.inputs(); out = self.root / 'observation.json'
        env = dict(os.environ, PYTHONIOENCODING='ascii')
        result = self.cli('template', p, c, '--text', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        if not ar.secure_open_supported():
            unsupported = self.cli('check', p, c, m, '--root', self.root)
            self.assertNotEqual(unsupported.returncode, 0); return
        result = self.cli('catalog', p, c, m, '--root', self.root, '--text')
        self.assertEqual(result.returncode, 0, result.stderr); self.assertIn(b'Physical line 4 bytes', result.stdout)
        self.m['passages'][0]['quote'] = 'not the quote'; m.write_text(json.dumps(self.m), encoding='utf-8')
        result = self.cli('check', p, c, m, '--root', self.root, '--output', out)
        self.assertEqual(result.returncode, 1, result.stderr)
        saved = json.loads(out.read_text(encoding='utf-8'))
        self.assertEqual(saved['passages'][0]['status'], 'QUOTE_MISMATCH')
        self.assertIsNotNone(saved['passages'][0]['observed_quote'])
        self.assertEqual(saved, json.loads(result.stdout))

    def test_cli_preflight_existing_and_dangling_output_before_any_source_or_input_read(self):
        p, c, m = self.inputs()
        for output in (p, c, m, self.file, self.root / 'existing'):
            if not output.exists(): output.write_text('retain', encoding='utf-8')
            before = output.read_bytes()
            with patch.object(pc, 'read_input', side_effect=AssertionError('preflight before input')), \
                 patch('sys.stderr'), patch.object(sys, 'argv', ['result_passage_check.py', 'check', str(p), str(c), str(m), '--root', str(self.root), '--output', str(output)]):
                with self.assertRaises(SystemExit) as error: pc.main()
                self.assertEqual(error.exception.code, 1)
            self.assertEqual(output.read_bytes(), before)
        if ar.secure_open_supported():
            link = self.root / 'dangling'; link.symlink_to(self.root / 'missing')
            result = self.cli('check', p, c, m, '--root', self.root, '--output', link)
            self.assertNotEqual(result.returncode, 0); self.assertTrue(link.is_symlink())
            self.assertFalse((self.root / 'missing').exists())

    def test_cli_invalid_later_metadata_no_partial_output_no_path_exception_leak(self):
        p, c, m = self.inputs(); out = self.root / 'new.json'
        self.m['passages'][-1]['byte_end'] = True; m.write_text(json.dumps(self.m), encoding='utf-8')
        result = self.cli('check', p, c, m, '--root', self.root / 'private-missing', '--output', out)
        self.assertNotEqual(result.returncode, 0); self.assertFalse(out.exists())
        self.assertNotIn(str(self.root).encode(), result.stderr); self.assertNotIn(b'Traceback', result.stderr)
        p.write_text('{"question":"a","question":"b"}', encoding='utf-8')
        self.assertNotEqual(self.cli('template', p, c).returncode, 0)
        self.assertNotEqual(self.cli('check', p, c, m).returncode, 0)


if __name__ == '__main__':
    unittest.main()
