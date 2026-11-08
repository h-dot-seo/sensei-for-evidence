import csv
import hashlib
import unittest
from unittest.mock import patch

import csv_export_parser as parser


class CsvExportParserTests(unittest.TestCase):
    def assert_span(self, raw, span, part, line_start, line_end, byte_start):
        self.assertEqual(span, dict(line_start=line_start, line_end=line_end,
            byte_start=byte_start, byte_end=byte_start + len(part),
            sha256=hashlib.sha256(part).hexdigest()))
        self.assertEqual(raw[span['byte_start']:span['byte_end']], part)

    def test_literal_values_all_columns_and_determinism(self):
        raw = 'record_id,source_locator,title\n  합성  , HTTPS://X/AbC ,"=1+1, title"\n'.encode()
        before = bytes(raw)
        result = parser.parse_export(raw)
        self.assertEqual(raw, before)
        self.assertEqual(result, parser.parse_export(raw))
        row = result['record_rows'][0]
        self.assertEqual(row['candidate_id'], 'csv-row-000001')
        self.assertEqual(row['record_id'], '  합성  ')
        self.assertEqual(row['source_locator'], ' HTTPS://X/AbC ')
        self.assertEqual(row['original_values'], dict(record_id='  합성  ',
            source_locator=' HTTPS://X/AbC ', title='=1+1, title'))
        result['headers'].append('mutation')
        self.assertNotEqual(result, parser.parse_export(raw))

    def test_all_newline_styles_bom_unicode_multiline_and_blanks(self):
        for newline in (b'\n', b'\r\n', b'\r'):
            with self.subTest(newline=newline):
                header = b'\xef\xbb\xbfrecord_id,source_locator,title' + newline
                first = '합성,local:one,"a'.encode() + newline + b'b"' + newline
                last = b'two,local:two,"quoted ""title"""'
                raw = header + newline + first + newline + last
                result = parser.parse_export(raw)
                self.assertEqual(result['headers'], ['record_id', 'source_locator', 'title'])
                self.assert_span(raw, result['header_source_span'], header, 1, 1, 0)
                rows = result['record_rows']
                self.assertEqual([r['candidate_id'] for r in rows], ['csv-row-000001', 'csv-row-000002'])
                self.assertEqual(rows[0]['original_values']['title'], 'a' + newline.decode() + 'b')
                self.assert_span(raw, rows[0]['source_span'], first, 3, 4, len(header + newline))
                self.assert_span(raw, rows[1]['source_span'], last, 6, 6, len(raw) - len(last))
                self.assert_span(raw, result['ignored_blank_spans'][0], newline, 2, 2, len(header))
                self.assert_span(raw, result['ignored_blank_spans'][1], newline, 5, 5, len(header + newline + first))

    def test_mixed_newlines_and_unicode_line_separators(self):
        raw = 'record_id,source_locator,note\r\none,loc,"a\rb\nc\r\nd\u2028e\u0085f"\rtwo,loc,last\n'.encode()
        result = parser.parse_export(raw)
        self.assertEqual(result['record_rows'][0]['source_span']['line_end'], 5)
        self.assertEqual(result['record_rows'][1]['source_span']['line_start'], 6)
        self.assertEqual(result['record_rows'][0]['original_values']['note'], 'a\rb\nc\r\nd\u2028e\u0085f')

    def test_repeated_ids_preserve_occurrences_and_literal_conflicts(self):
        raw = b'record_id,source_locator\nb,z\na,x\nb, z\na,x\nb,z\n b,z\n'
        result = parser.parse_export(raw)
        self.assertEqual(len(result['record_rows']), 6)
        self.assertEqual(result['duplicate_record_ids'], [
            dict(record_id='b', candidate_ids=['csv-row-000001', 'csv-row-000003', 'csv-row-000005']),
            dict(record_id='a', candidate_ids=['csv-row-000002', 'csv-row-000004'])])
        self.assertEqual(result['locator_conflicts'], [dict(record_id='b', source_locators=[' z', 'z'],
            candidate_ids=['csv-row-000001', 'csv-row-000003', 'csv-row-000005'])])

    def test_custom_columns_and_no_header_normalization(self):
        raw = b' ID ,Locator,Other\nitem,custom:source,\n'
        result = parser.parse_export(raw, id_column=' ID ', locator_column='Locator')
        self.assertEqual(result['record_rows'][0]['original_values']['Other'], '')
        with self.assertRaises(ValueError):
            parser.parse_export(raw, id_column='ID', locator_column='Locator')

    def test_header_only_and_leading_blank_lines(self):
        for raw in (b'record_id,source_locator', b'record_id,source_locator\n',
                    b'\xef\xbb\xbfrecord_id,source_locator\r\n'):
            result = parser.parse_export(raw)
            self.assertEqual(result['record_rows'], [])
            self.assertEqual(result['duplicate_record_ids'], [])
            self.assertEqual(result['locator_conflicts'], [])
        result = parser.parse_export(b'\n\r\nrecord_id,source_locator\ra,b\r')
        self.assertEqual(result['header_source_span']['line_start'], 3)
        self.assertEqual(len(result['ignored_blank_spans']), 2)

    def test_invalid_inputs(self):
        cases = [None, 'record_id,source_locator', bytearray(b'abc'), b'', b'\n\r\n',
                 b'\xef\xbb\xbf', b'record_id,source_locator\na,\xff',
                 b'record_id,source_locator\na,\x00', b',source_locator\n',
                 b' ,source_locator\n', b'record_id,record_id,source_locator\n',
                 b'record_id,title\n', b'record_id,source_locator\na\n',
                 b'record_id,source_locator\na,b,c\n',
                 b'record_id,source_locator\n,loc\n',
                 b'record_id,source_locator\n" \t",loc\n',
                 b'record_id,source_locator\na, \n',
                 b'record_id,source_locator\n"unterminated,loc',
                 b'record_id,source_locator\n"private"trailing,loc\n',
                 b'record_id,source_locator\n""\n',
                 b'record_id,source_locator\n \n']
        for raw in cases:
            with self.subTest(raw=repr(raw)):
                with self.assertRaisesRegex(ValueError, r'line \d+:'):
                    parser.parse_export(raw)

    def test_errors_do_not_echo_cells(self):
        for raw in (b'record_id,source_locator\nSECRET,loc,extra\n',
                    b'record_id,source_locator\n"SECRET"bad,loc\n'):
            with self.assertRaises(ValueError) as caught:
                parser.parse_export(raw)
            self.assertNotIn('SECRET', str(caught.exception))
            self.assertIn('line 2:', str(caught.exception))

    def test_resource_limits_and_global_csv_limit_unchanged(self):
        raw = b'record_id,source_locator\na,b\nc,d\n'
        with patch.object(parser, 'MAX_EXPORT_BYTES', len(raw)):
            self.assertEqual(len(parser.parse_export(raw)['record_rows']), 2)
        with patch.object(parser, 'MAX_EXPORT_BYTES', len(raw) - 1):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                parser.parse_export(raw)
        with patch.object(parser, 'MAX_RECORDS', 1):
            with self.assertRaisesRegex(ValueError, 'line 3:.*record limit'):
                parser.parse_export(raw)
            self.assertEqual(len(parser.parse_export(b'record_id,source_locator\na,b\n')['record_rows']), 1)
        limit = csv.field_size_limit()
        with patch.object(csv, 'field_size_limit', side_effect=AssertionError('must not call')):
            parser.parse_export(raw)
            if limit + 100 < parser.MAX_EXPORT_BYTES:
                with self.assertRaisesRegex(ValueError, 'line 2:'):
                    parser.parse_export(b'record_id,source_locator\na,' + b'x' * (limit + 1))
        self.assertEqual(csv.field_size_limit(), limit)

    def test_multiline_header_and_noninitial_bom_are_literal(self):
        header = b'record_id,source_locator,"note\r\nname"\r\n'
        row = 'x,local,"\ufeffone\n\ntwo"\n'.encode()
        raw = header + row
        result = parser.parse_export(raw)
        self.assert_span(raw, result['header_source_span'], header, 1, 2, 0)
        self.assert_span(raw, result['record_rows'][0]['source_span'], row, 3, 5, len(header))
        self.assertEqual(result['record_rows'][0]['original_values']['note\r\nname'],
                         '\ufeffone\n\ntwo')
        self.assertEqual(result['ignored_blank_spans'], [])

    def test_selected_column_arguments(self):
        for invalid in (None, '', ' ', 3, []):
            with self.assertRaises(ValueError):
                parser.parse_export(b'record_id,source_locator\n', id_column=invalid)

    def test_physical_line_limit_bounds_empty_and_multiline_rows(self):
        with patch.object(parser, 'MAX_PHYSICAL_LINES', 3):
            for ending in (b'', b'\n', b'\r', b'\r\n'):
                raw = b'record_id,source_locator\na,b\nc,d' + ending
                self.assertEqual(len(parser.parse_export(raw)['record_rows']), 2)
            self.assertEqual(len(parser.parse_export(b'\n\nrecord_id,source_locator')['ignored_blank_spans']), 2)
            for raw in (b'\n' * 4, b'\r\n' * 4,
                        b'record_id,source_locator\na,b\nc,d\ne,f',
                        b'record_id,source_locator\na,"b\nc\nd"'):
                with self.assertRaisesRegex(ValueError, 'line 4:.*physical line limit'):
                    parser.parse_export(raw)


if __name__ == '__main__':
    unittest.main()
