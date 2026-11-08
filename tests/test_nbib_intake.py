"""Synthetic NBIB only: byte provenance, strict parsing and explicit CSV review.

The deliberately enormous PMID strings are fabricated identifiers, not claims
about real publications. No remote metadata or actual papers are used.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import nbib_export_parser as parser
import nbib_intake as intake
import bibliographic_intake as csv_intake
import bibliographic_review as review
from evidence_workflow import run
from prisma_audit import export_audit
from screening_links import prepare_targets

ROOT = Path(__file__).resolve().parents[1]
PMID = '999999999999999999999999999991'
OTHER = '999999999999999999999999999992'


def record(pmid=PMID, newline='\n'):
    return newline.join(['PMID- ' + pmid, 'TI  - Fictional "title", 합성',
                         '      folded title', 'AB  - Synthetic first paragraph',
                         '      second paragraph', 'AU  - Invented Alpha',
                         'AU  - Invented Beta', 'ZZ  - unknown retained',
                         'AID - 10.0000/fictional [doi]', '']).encode('utf-8')


class NbibIntakeTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / 'examples/bibliographic-base.json').read_text(encoding='utf-8'))
        self.raw = record() + b'\n' + record() + b'\n' + record(OTHER)

    def prepare(self, raw=None, protocol=None, **kwargs):
        return intake.prepare(self.base if protocol is None else protocol,
                              self.raw if raw is None else raw,
                              kwargs.get('search_id', 'local-primary'),
                              kwargs.get('searched_at', 'supplied synthetic timestamp'))

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'nbib_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=30,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_exact_bom_newlines_fields_spans_and_blank_separators(self):
        for newline in ['\n', '\r\n', '\r']:
            first = b'\xef\xbb\xbf' + record(newline=newline)
            raw = first + (newline * 2).encode() + record(OTHER, newline)
            parsed = parser.parse_export(raw)
            self.assertTrue(parsed['initial_utf8_bom'])
            self.assertEqual(len(parsed['records']), 2)
            self.assertEqual(len(parsed['ignored_blank_spans']), 2)
            self.assertEqual(parsed['records'][0]['raw_text'].encode(), first)
            for item in parsed['records'] + parsed['ignored_blank_spans']:
                span = item.get('source_span', item)
                chunk = raw[span['byte_start']:span['byte_end']]
                self.assertEqual(span['sha256'], hashlib.sha256(chunk).hexdigest())
                if 'raw_text' in item:
                    self.assertEqual(item['raw_text'].encode(), chunk)
            fields = parsed['records'][0]['fields']
            self.assertEqual([f['tag'] for f in fields], ['PMID', 'TI', 'AB', 'AU', 'AU', 'ZZ', 'AID'])
            self.assertEqual(fields[1]['value_lines'], ['Fictional "title", 합성', 'folded title'])
            self.assertEqual(fields[2]['value_lines'], ['Synthetic first paragraph', 'second paragraph'])
            self.assertEqual([f['value_lines'] for f in fields if f['tag'] == 'AU'],
                             [['Invented Alpha'], ['Invented Beta']])
            for field in fields:
                span = field['source_span']
                self.assertEqual(raw[span['byte_start']:span['byte_end']], field['raw_text'].encode())

    def test_bare_cr_without_csv_specials_roundtrips_entire_bridge(self):
        raw = ('PMID- ' + PMID + '\rTI  - fictional\r').encode()
        artifact = self.prepare(raw)
        self.assertTrue(intake.verify(artifact)['valid'])
        rows = artifact['csv_intake']['parsed_export']['record_rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['original_values']['nbib_record_text'].encode(), raw)
        self.assertEqual(artifact['source_export']['text'].encode(), raw)

    def test_no_final_newline_and_leading_separators_preserved(self):
        raw = b'\n\r\n' + record().rstrip(b'\n')
        parsed = parser.parse_export(raw)
        self.assertEqual(parsed['records'][0]['source_span']['line_start'], 3)
        self.assertEqual(parsed['records'][0]['source_span']['byte_end'], len(raw))
        artifact = self.prepare(raw)
        self.assertEqual(artifact['source_export']['text'].encode(), raw)

    def test_repeated_pmids_are_distinct_occurrences_not_deduplicated(self):
        parsed = parser.parse_export(self.raw)
        self.assertEqual(len(parsed['records']), 3)
        self.assertEqual(parsed['duplicate_pmids'], [dict(pmid=PMID,
            candidate_ids=['nbib-record-000001', 'nbib-record-000002'])])
        self.assertEqual([r['candidate_id'] for r in parsed['records']],
                         ['nbib-record-000001', 'nbib-record-000002', 'nbib-record-000003'])

    def test_strict_grammar_rejects_bad_bytes_records_and_fields(self):
        invalid = [b'', b'\n\n', b'\xef\xbb\xbf', b'\xff', b'PMID- 1\nTI  - a\x00\n',
                   b'      orphan\n', b'TI  - no PMID\n', b'PMID- 0\n', b'PMID- -1\n',
                   b'PMID- 1.0\n', b'PMID- +1\n', b'PMID-  1\n', b'PMID- 1 \n',
                   'PMID- １２\n'.encode(), b'PMID- 1\n      2\n',
                   b'PMID- 1\nPMID- 2\n', b'PMID- 1\nPMID- 1\n',
                   b'PMID- 1\nTI - bad\n', b'PMID- 1\nTI  -bad\n',
                   b'PMID- 1\nti  - bad\n', b'PMID- 1\nA   - bad\n',
                   b'PMID- 1\nABCDE- bad\n', b'PMID- 1\n     bad\n',
                   b'PMID- 1\n \n', b'PMID- 1\n\xef\xbb\xbfTI  - bad\n']
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parser.parse_export(raw)
        for value in [None, '', 1, bytearray(record()), memoryview(record())]:
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                parser.parse_export(value)

    def test_wrapper_determinism_lossless_csv_and_unverified_boundaries(self):
        before = copy.deepcopy(self.base)
        artifact = self.prepare()
        self.assertEqual(artifact, self.prepare())
        self.assertEqual(artifact['source_export']['text'].encode(), self.raw)
        self.assertEqual(artifact['source_export']['bytes'], len(self.raw))
        self.assertEqual(artifact['source_export']['sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.base, before)
        nested = artifact['csv_intake']
        self.assertTrue(csv_intake.verify(nested)['valid'])
        self.assertTrue(intake.verify(artifact)['valid'])
        self.assertEqual(nested['query_export_association'], 'SUPPLIED_NOT_VERIFIED')
        self.assertEqual(nested['record_identity_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(nested['effects']['new_reports'], 0)
        self.assertEqual(nested['effects']['new_evidence_rows'], 0)
        self.assertEqual(nested['effects']['protocol_changed'], False)
        self.assertEqual(nested['external_calls'], 0)
        self.assertNotIn('protocol_candidate', artifact)
        rows = nested['parsed_export']['record_rows']
        self.assertEqual(len(rows), 3)
        for native, row in zip(artifact['parsed_export']['records'], rows):
            values = row['original_values']
            self.assertEqual(set(values), {'record_id', 'source_locator', 'nbib_occurrence_id',
                'nbib_original_export_sha256', 'nbib_record_span_json', 'nbib_fields_json', 'nbib_record_text'})
            self.assertEqual(values['record_id'], 'pubmed:' + native['pmid'])
            self.assertEqual(values['source_locator'], 'https://pubmed.ncbi.nlm.nih.gov/' + native['pmid'] + '/')
            self.assertEqual(values['nbib_occurrence_id'], native['candidate_id'])
            self.assertEqual(values['nbib_record_text'], native['raw_text'])
            self.assertEqual(json.loads(values['nbib_fields_json']), native['fields'])
            self.assertEqual(json.loads(values['nbib_record_span_json']), native['source_span'])
            self.assertEqual(values['nbib_original_export_sha256'], hashlib.sha256(self.raw).hexdigest())

    def test_explicit_human_reconciliation_run_audit_and_screening_provenance(self):
        artifact = self.prepare()
        nested = artifact['csv_intake']
        choices = review.template(nested)
        self.assertTrue(all(r['disposition'] is None for r in choices['resolutions']))
        with self.assertRaises(ValueError):
            review.assemble(self.base, nested, choices)
        for choice, disposition, rid in zip(choices['resolutions'],
                ['new_record', 'same_record', 'do_not_promote'], ['fictional-canonical', 'fictional-canonical', None]):
            choice.update(disposition=disposition, record_id=rid, rationale='Explicit synthetic operator choice')
        prepared = review.prepare_review(self.base, nested, choices)
        document = prepared['review_document']
        document['review'].update(reviewer='Fictional human', reviewed_at='2026-11-04',
            rationale='Synthetic collection reconciliation', decision='import_for_screening')
        protocol = review.assemble(self.base, nested, document)['protocol_candidate']
        research = run(protocol)
        audit = export_audit(protocol)
        collection = research['bibliographic_collection']
        self.assertEqual(collection['counts'], dict(raw_rows=3, promoted_row_occurrences=2,
            withheld_rows=1, canonical_search_memberships=1))
        self.assertEqual(protocol['searches'][0]['record_ids'], ['fictional-canonical'])
        self.assertIs(protocol['searches'][0]['complete'], False)
        self.assertIsNone(protocol['searches'][0]['total_count'])
        self.assertEqual(protocol['screening'], [])
        self.assertEqual(protocol['evidence'], [])
        self.assertEqual(audit['bibliographic_collection'], collection)
        for actual, original in zip(collection['row_ledger'], nested['parsed_export']['record_rows']):
            self.assertEqual(actual['original_values'], original['original_values'])
        targets = prepare_targets(protocol, collection)['record_targets']
        self.assertEqual(len(targets), 1)
        retained = targets[0]['source_basis']['bibliographic_rows']
        self.assertEqual(len(retained), 2)
        for row, original in zip(retained, nested['parsed_export']['record_rows']):
            self.assertEqual(row['original_values'], original['original_values'])
        self.assertEqual(self.base['searches'], [])
        self.assertEqual(self.raw, artifact['source_export']['text'].encode())

    def test_same_title_and_doi_do_not_create_identity_or_report_links(self):
        artifact = self.prepare()
        rows = artifact['csv_intake']['parsed_export']['record_rows']
        self.assertNotEqual(rows[0]['record_id'], rows[2]['record_id'])
        self.assertEqual(len(rows), 3)
        self.assertEqual(artifact['csv_intake']['review_status'], 'NOT_PERFORMED')
        self.assertEqual(self.base['evidence'], [])
        self.assertNotIn('reports', self.base)

    def test_tampering_unknown_keys_and_boolean_integer_rejected_even_resealed(self):
        artifact = self.prepare()
        mutations = {
            'unknown top': lambda a: a.update(approved=True),
            'schema bool': lambda a: a.update(schema_version=True),
            'source bool': lambda a: a['source_export'].update(bytes=True),
            'source hash': lambda a: a['source_export'].update(sha256='0'*64),
            'source text': lambda a: a['source_export'].update(text=a['source_export']['text']+'\n'),
            'unknown source': lambda a: a['source_export'].update(approved=True),
            'unknown parsed': lambda a: a['parsed_export'].update(approved=True),
            'span bool': lambda a: a['parsed_export']['records'][0]['source_span'].update(byte_start=False),
            'raw record': lambda a: a['parsed_export']['records'][0].update(raw_text='forged'),
            'field': lambda a: a['parsed_export']['records'][0]['fields'][1].update(value_lines=['forged']),
            'nested CSV': lambda a: a['csv_intake']['parsed_export']['record_rows'][0]['original_values'].update(nbib_record_text='forged'),
            'protocol': lambda a: a['protocol_snapshot'].update(question='forged'),
            'engine': lambda a: a['engine_sha256'].update({'nbib_export_parser.py': '0'*64}),
        }
        for name, mutate in mutations.items():
            for reseal in [False, True]:
                changed = copy.deepcopy(artifact)
                mutate(changed)
                if reseal:
                    changed['review_target']['target_sha256'] = intake.digest({k:v for k,v in changed.items() if k != 'review_target'})
                with self.subTest(name=name, reseal=reseal), self.assertRaises(ValueError):
                    intake.verify(changed)
        with patch.object(intake, 'implementation_hashes', return_value={'wrong': 'engine'}), self.assertRaises(ValueError):
            intake.verify(artifact)

    def test_whole_protocol_validation_and_required_search_inputs(self):
        for bad in [None, [], 42, 'bad']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.prepare(protocol=bad if bad is not None else [])
        for field in ['search_id', 'searched_at']:
            for value in [None, '', ' ', True, []]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.prepare(**{field: value})
        with self.assertRaises(ValueError): self.prepare(search_id='undeclared')
        for reports in [42, [42], {'unexpected': True}]:
            base = copy.deepcopy(self.base)
            base['reports'] = reports
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                self.prepare(protocol=base)
        for bad in [None, [], {}, {'schema_version': True}, {'schema_version': 1.0}]:
            with self.subTest(artifact=bad), self.assertRaises(ValueError): intake.verify(bad)

    def test_legacy_scalar_report_invalid_decision_is_validated_beyond_run(self):
        protocol = copy.deepcopy(self.base)
        protocol['searches'] = [dict(search_id='local-secondary', source='synthetic-second-export',
            query='fictional development context', window='2020-2026', searched_at='supplied',
            record_ids=['fictional-existing'], complete=False, total_count=None, has_more=None)]
        protocol['screening'] = [dict(record_id='fictional-existing', decision='include', reason='Synthetic scope')]
        protocol['reports'] = [dict(report_id='fictional-report', record_ids=['fictional-existing'],
            retrieval='retrieved', decision='invalid-decision', study_id='fictional-study', locator='synthetic:inert')]
        run(protocol)  # Legacy scalar-report validation is not performed by run alone.
        with self.assertRaises(ValueError): self.prepare(protocol=protocol)
        protocol['reports'][0]['decision'] = 'include'
        self.assertTrue(intake.verify(self.prepare(protocol=protocol))['valid'])

    def test_small_patched_bounds(self):
        for constant, limit in [('MAX_EXPORT_BYTES', len(self.raw)-1), ('MAX_RECORDS', 2), ('MAX_PHYSICAL_LINES', 2)]:
            with self.subTest(constant=constant), patch.object(parser, constant, limit), self.assertRaises(ValueError):
                self.prepare()
        artifact = self.prepare()
        size = len(intake.artifact_bytes(artifact))
        with patch.object(intake, 'MAX_ARTIFACT_BYTES', size):
            self.assertEqual(len(intake.artifact_bytes(artifact)), size)
        with patch.object(intake, 'MAX_ARTIFACT_BYTES', size-1):
            for action in [lambda: intake.artifact_bytes(artifact), lambda: intake.verify(artifact), self.prepare]:
                with self.assertRaises(ValueError): action()

    def test_cli_preview_verify_csv_and_intake_roundtrip_exclusive_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol, export, output = [root / name for name in ['base.json', 'raw.nbib', 'artifact.json']]
            protocol.write_text(json.dumps(self.base), encoding='utf-8')
            raw = b'\xef\xbb\xbf' + record(newline='\r\n') + b'\r\n\r\n'
            export.write_bytes(raw)
            args = ['preview', protocol, export, '--search-id', 'local-primary', '--searched-at', 'supplied', '--output', output]
            result = self.invoke(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            artifact = json.loads(output.read_bytes())
            self.assertEqual(artifact['source_export']['text'].encode(), raw)
            self.assertEqual(json.loads(result.stdout), artifact)
            saved = output.read_bytes()
            duplicate = self.invoke(*args)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertEqual(duplicate.stdout, b'')
            self.assertEqual(output.read_bytes(), saved)
            for flag, filename in [('--intake-output', 'csv-intake.json'), ('--csv-output', 'derived.csv')]:
                destination = root / filename
                checked = self.invoke('verify', output, flag, destination)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertTrue(json.loads(checked.stdout)['valid'])
                if flag == '--intake-output':
                    self.assertEqual(json.loads(destination.read_bytes()), artifact['csv_intake'])
                else:
                    self.assertEqual(destination.read_bytes(), artifact['csv_intake']['source_export']['text'].encode())
                previous = destination.read_bytes()
                self.assertNotEqual(self.invoke('verify', output, flag, destination).returncode, 0)
                self.assertEqual(destination.read_bytes(), previous)
            rendered = self.invoke('verify', output, '--text')
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assertIn(b'NOT_READY', rendered.stdout)
            target = root / 'target'; target.write_bytes(b'unchanged')
            symlink = root / 'symlink'
            try:
                symlink.symlink_to(target)
            except (OSError, NotImplementedError):
                pass  # Some Windows hosts do not grant symlink creation privileges.
            else:
                self.assertNotEqual(self.invoke('verify', output, '--csv-output', symlink).returncode, 0)
                self.assertEqual(target.read_bytes(), b'unchanged')

    def test_leading_zero_pmids_remain_distinct_literal_conventions(self):
        raw = record('0' + PMID) + b'\n' + record(PMID)
        artifact = self.prepare(raw)
        self.assertEqual(artifact['parsed_export']['duplicate_pmids'], [])
        rows = artifact['csv_intake']['parsed_export']['record_rows']
        self.assertEqual([r['record_id'] for r in rows], ['pubmed:0' + PMID, 'pubmed:' + PMID])
        with self.assertRaises(ValueError): parser.parse_export(b'PMID- 0000\n')

    def test_controls_remain_in_fields_but_cannot_spoof_text_status(self):
        hostile = 'synthetic\t"quote"\x1b\u202e\u2028\u0085'
        raw = ('PMID- ' + PMID + '\nTI  - ' + hostile + '\n').encode('utf-8')
        artifact = self.prepare(raw, searched_at=hostile + '\nConclusion: READY')
        native = artifact['parsed_export']['records'][0]['fields'][1]
        self.assertEqual(native['value_lines'], [hostile])
        values = artifact['csv_intake']['parsed_export']['record_rows'][0]['original_values']
        self.assertEqual(json.loads(values['nbib_fields_json'])[1], native)
        self.assertEqual(values['nbib_record_text'].encode(), raw)
        display = intake.render_text(artifact)
        for character in ['\x1b', '\u202e', '\u2028', '\u0085', '\t']:
            self.assertNotIn(character, display)
        self.assertNotIn('\nConclusion: READY', display)
        self.assertIn('\\nConclusion: READY', display)
        self.assertIn('Conclusion: NOT_READY', display)
        self.assertTrue(intake.verify(json.loads(intake.artifact_bytes(artifact)))['valid'])

    def test_non_json_protocol_metadata_and_cyclic_containers_rejected(self):
        cycle = []; cycle.append(cycle)
        for bad in [float('nan'), float('inf'), ('tuple',), {'set'}, {1: 'key'}, '\ud800', cycle]:
            protocol = copy.deepcopy(self.base)
            protocol['opaque_metadata'] = bad
            with self.subTest(kind=type(bad)), self.assertRaises(ValueError):
                self.prepare(protocol=protocol)
            with self.assertRaises(ValueError): intake.artifact_bytes(protocol)

    def test_cli_serialization_and_output_bound_fail_before_file_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol, export, output = [root / name for name in ['base', 'raw', 'out']]
            protocol.write_text(json.dumps(self.base), encoding='utf-8')
            export.write_bytes(self.raw)
            argv = ['nbib_intake.py', 'preview', str(protocol), str(export),
                    '--search-id', 'local-primary', '--searched-at', 'supplied', '--output', str(output), '--text']
            for render in [lambda value: (_ for _ in ()).throw(ValueError('synthetic serialization failure')),
                           lambda value: 'x' * 257]:
                with patch.object(sys, 'argv', argv), patch.object(intake, 'configure_utf8_stdio'), \
                     patch.object(sys, 'stderr', io.StringIO()), patch.object(sys, 'stdout', io.StringIO()), \
                     patch.object(intake, 'render_text', side_effect=render):
                    # Patch only the final bound; preparation and JSON sizes use
                    # their normal bounded serializer rather than large fixtures.
                    artifact = self.prepare()
                    with patch.object(intake, 'prepare', return_value=artifact), \
                         patch.object(intake, 'artifact_bytes', return_value=b'{}\n'), \
                         patch.object(intake, 'MAX_ARTIFACT_BYTES', 256), \
                         patch.object(intake.bibliographic_intake, 'read_bounded',
                                      side_effect=[json.dumps(self.base).encode(), self.raw]):
                        with self.assertRaises(SystemExit): intake.main()
                self.assertFalse(output.exists())

    def test_cli_invalid_inputs_leave_no_output_and_no_sensitive_echo(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol, export, output = [root / name for name in ['base', 'raw', 'out']]
            valid = json.dumps(self.base).encode()
            cases = [(valid, b'PMID- 1\nSECRET malformed\n'), (valid, b'\xff'),
                     (b'{"question":1,"question":2}', self.raw), (b'null', self.raw),
                     (b'[]', self.raw), (b'42', self.raw), (b'{bad', self.raw), (b'\xff', self.raw)]
            for p, raw in cases:
                protocol.write_bytes(p); export.write_bytes(raw)
                result = self.invoke('preview', protocol, export, '--search-id', 'local-primary',
                                     '--searched-at', 'supplied', '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertFalse(output.exists())
                self.assertNotIn(b'Traceback', result.stderr)
                self.assertNotIn(b'SECRET', result.stderr)
            protocol.write_bytes(valid); export.write_bytes(self.raw)
            self.assertNotEqual(self.invoke('preview', protocol, export, '--search-id', 'local-primary', '--output', output).returncode, 0)
            self.assertFalse(output.exists())
            artifact = root / 'invalid-artifact'; artifact.write_bytes(b'{"schema_version":1,"schema_version":1}')
            for flag in ['--csv-output', '--intake-output']:
                self.assertNotEqual(self.invoke('verify', artifact, flag, output).returncode, 0)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
