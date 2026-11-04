"""Synthetic batch exports: exact bytes, independent review and bounded replay."""
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
import zipfile

import bibliographic_intake
import bibliographic_review as review
import nbib_batch_intake as batch
import nbib_export_parser as parser
import nbib_intake as single
import research_bundle
from evidence_workflow import run
from prisma_audit import export_audit
from screening_links import prepare_targets

ROOT = Path(__file__).resolve().parent
PMID = '999999999999999999999999999991'
OTHER = '999999999999999999999999999992'


def record(pmid=PMID, newline='\n'):
    return newline.join(['PMID- ' + pmid, 'TI  - Fictional "title", 합성',
                         '      folded title', 'AB  - Synthetic paragraph',
                         'AU  - Invented Alpha', 'AU  - Invented Beta',
                         'ZZ  - unknown retained', '']).encode('utf-8')


class BatchIntakeTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / 'examples/bibliographic-base.json').read_text(encoding='utf-8'))
        self.sources = [dict(source_id='first synthetic', raw=b'\xef\xbb\xbf' + record(newline='\r\n')),
                        dict(source_id='second synthetic', raw=record() + b'\n' + record(OTHER))]

    def prepare(self, sources=None, protocol=None, **kwargs):
        return batch.prepare(self.base if protocol is None else protocol,
                             self.sources if sources is None else sources,
                             kwargs.get('search_id', 'local-primary'),
                             kwargs.get('searched_at', 'supplied synthetic timestamp'))

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'nbib_batch_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=30,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_ordered_bom_newlines_fields_spans_and_deterministic_derivative(self):
        before = copy.deepcopy((self.base, self.sources))
        for newline in ['\n', '\r\n', '\r']:
            raw = b'\xef\xbb\xbf' + record(newline=newline) + (newline * 2).encode() + record(OTHER, newline).rstrip(b'\r\n')
            sources = [dict(source_id='α synthetic', raw=raw), dict(source_id='β synthetic', raw=record())]
            artifact = self.prepare(sources)
            self.assertEqual(artifact, self.prepare(sources))
            self.assertEqual(artifact['schema_version'], 1)
            self.assertEqual(artifact['mode'], 'local_nbib_batch_preparation')
            self.assertEqual(len(artifact['source_exports']), 2)
            self.assertEqual(set(batch.HEADERS), set(single.HEADERS) |
                             {'nbib_source_id', 'nbib_source_index', 'nbib_batch_occurrence_id'})
            nested = artifact['csv_intake']
            self.assertTrue(bibliographic_intake.verify(nested)['valid'])
            checked = batch.verify(artifact)
            self.assertTrue(checked['valid'])
            self.assertEqual(len(checked['source_exports']), 2)
            self.assertEqual(checked['source_exports'], [dict(source_index=i, source_id=source['source_id'],
                sha256=hashlib.sha256(source['raw']).hexdigest(), bytes=len(source['raw']),
                record_rows=len(parser.parse_export(source['raw'])['records'])) for i, source in enumerate(sources)])
            rows = iter(nested['parsed_export']['record_rows'])
            for index, (supplied, source) in enumerate(zip(sources, artifact['source_exports'])):
                self.assertEqual(set(source), {'source_index', 'source_id', 'source_export', 'parsed_export'})
                self.assertEqual(source['source_index'], index)
                self.assertEqual(source['source_id'], supplied['source_id'])
                native = source['source_export']
                self.assertEqual(native, single.prepare(self.base, supplied['raw'], 'local-primary', 'supplied synthetic timestamp')['source_export'])
                self.assertEqual(source['parsed_export'], parser.parse_export(supplied['raw']))
                for original in source['parsed_export']['records']:
                    values = next(rows)['original_values']
                    self.assertEqual(set(values), set(batch.HEADERS))
                    self.assertEqual(values['record_id'], 'pubmed:' + original['pmid'])
                    self.assertEqual(values['source_locator'], 'https://pubmed.ncbi.nlm.nih.gov/' + original['pmid'] + '/')
                    self.assertEqual(values['nbib_source_id'], supplied['source_id'])
                    self.assertEqual(values['nbib_source_index'], str(index))
                    self.assertEqual(values['nbib_occurrence_id'], original['candidate_id'])
                    self.assertEqual(values['nbib_batch_occurrence_id'], f"source-{index + 1:06d}/" + original['candidate_id'])
                    self.assertEqual(values['nbib_original_export_sha256'], hashlib.sha256(supplied['raw']).hexdigest())
                    self.assertEqual(json.loads(values['nbib_record_span_json']), original['source_span'])
                    self.assertEqual(json.loads(values['nbib_fields_json']), original['fields'])
                    self.assertEqual(values['nbib_record_text'], original['raw_text'])
                    span = original['source_span']
                    self.assertEqual(supplied['raw'][span['byte_start']:span['byte_end']], original['raw_text'].encode())
            self.assertEqual(list(rows), [])
        self.assertEqual((self.base, self.sources), before)

    def test_identical_bytes_and_pmids_retained_as_distinct_ordered_occurrences(self):
        raw = record() + b'\n' + record()
        sources = [dict(source_id='copy one', raw=raw), dict(source_id='copy two', raw=raw)]
        artifact = self.prepare(sources)
        rows = artifact['csv_intake']['parsed_export']['record_rows']
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({r['candidate_id'] for r in rows}), 4)
        self.assertEqual(len({r['original_values']['nbib_batch_occurrence_id'] for r in rows}), 4)
        self.assertEqual(len({r['original_values']['nbib_original_export_sha256'] for r in rows}), 1)
        self.assertEqual(len({r['record_id'] for r in rows}), 1)
        self.assertEqual(artifact['source_grouping']['duplicate_pmids'], [dict(pmid=PMID, occurrences=[
            dict(source_index=i, source_id=sources[i]['source_id'],
                 native_candidate_id=f'nbib-record-{j + 1:06d}',
                 batch_candidate_id=f'source-{i + 1:06d}/nbib-record-{j + 1:06d}')
            for i in range(2) for j in range(2)])])
        self.assertNotEqual(artifact, self.prepare(list(reversed(sources))))
        for field, expected in [('review_status', 'NOT_PERFORMED'), ('search_completion', 'NOT_ESTABLISHED'),
                                ('record_identity_verification', 'NOT_ESTABLISHED'), ('external_calls', 0)]:
            self.assertEqual(artifact[field], expected)
        self.assertFalse(artifact['effects']['protocol_changed'])
        self.assertNotIn('protocol_candidate', artifact)

    def test_independent_explicit_review_one_incomplete_search_and_ordinary_bundle(self):
        raw = record()
        artifact = self.prepare([dict(source_id='one', raw=raw), dict(source_id='two', raw=raw),
                                 dict(source_id='three', raw=raw)])
        nested = artifact['csv_intake']
        choices = review.template(nested)
        self.assertEqual(len(choices['resolutions']), 3)
        self.assertTrue(all(r['disposition'] is None for r in choices['resolutions']))
        with self.assertRaises(ValueError): review.assemble(self.base, nested, choices)
        decisions = [('new_record', 'fictional-canonical'), ('same_record', 'fictional-canonical'), ('do_not_promote', None)]
        for row, (disposition, record_id) in zip(choices['resolutions'], decisions):
            row.update(disposition=disposition, record_id=record_id, rationale='Explicit fictional operator choice')
        document = review.prepare_review(self.base, nested, choices)['review_document']
        document['review'].update(reviewer='Fictional human', reviewed_at='2026-11-04',
                                 rationale='Independent synthetic row review', decision='import_for_screening')
        protocol = review.assemble(self.base, nested, document)['protocol_candidate']
        self.assertEqual(len(protocol['searches']), 1)
        search = protocol['searches'][0]
        self.assertEqual(search['record_ids'], ['fictional-canonical'])
        self.assertIs(search['complete'], False)
        self.assertIsNone(search['total_count'])
        self.assertEqual(protocol['screening'], [])
        self.assertEqual(protocol['evidence'], [])
        collection = run(protocol)['bibliographic_collection']
        self.assertEqual(collection['counts'], dict(raw_rows=3, promoted_row_occurrences=2,
                                                   withheld_rows=1, canonical_search_memberships=1))
        self.assertEqual(export_audit(protocol)['bibliographic_collection'], collection)
        original = [r['original_values'] for r in nested['parsed_export']['record_rows']]
        self.assertEqual([r['original_values'] for r in collection['row_ledger']], original)
        target = prepare_targets(protocol, collection)['record_targets'][0]
        self.assertEqual([r['original_values'] for r in target['source_basis']['bibliographic_rows']], original[:2])
        data = research_bundle.build_bundle(json.dumps(protocol).encode())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ordinary.zip'; path.write_bytes(data)
            self.assertTrue(research_bundle.verify(path)['valid'])
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertFalse(any('nbib' in name for name in archive.namelist()))
            retained = json.loads(archive.read('protocol.json'))
            self.assertEqual(run(retained)['bibliographic_collection'], collection)
        self.assertTrue(batch.verify(artifact)['valid'])
        self.assertEqual(self.base['searches'], [])

    def test_sources_are_strict_nonempty_bounded_unique_ids_but_not_unique_bytes(self):
        class StringSubclass(str): pass
        class ListSubclass(list): pass
        class DictSubclass(dict): pass
        valid = dict(source_id='synthetic', raw=record())
        invalid = [None, {}, (), [], [valid] * 101, ListSubclass([valid]), [None],
                   [dict(valid, extra=True)], [{'raw': record()}], [{'source_id': 'missing'}],
                   [DictSubclass(valid)], [valid, dict(valid)]]
        for source_id in [None, True, 1, '', ' ', 'x' * 129, '\ud800', '\x00', StringSubclass('synthetic')]:
            invalid.append([dict(source_id=source_id, raw=record())])
        for raw in [None, '', bytearray(record()), memoryview(record()), b'', b'\xff', b'PMID- 1\nSECRET malformed\n']:
            invalid.append([dict(source_id='synthetic', raw=raw)])
        for sources in invalid:
            with self.subTest(sources=repr(sources)[:160]), self.assertRaises(ValueError):
                batch.prepare(self.base, sources, 'local-primary', 'supplied')
        self.assertTrue(batch.verify(self.prepare([dict(source_id='x' * 128, raw=record())]))['valid'])
        self.assertEqual(len(self.prepare([dict(source_id=str(i), raw=b'PMID- 1\n') for i in range(100)])['source_exports']), 100)

    def test_tampering_extra_keys_type_substitution_and_resealing_fail(self):
        artifact = self.prepare()
        mutations = {
            'top extra': lambda a: a.update(approved=True),
            'schema bool': lambda a: a.update(schema_version=True),
            'schema float': lambda a: a.update(schema_version=1.0),
            'source index bool': lambda a: a['source_exports'][0].update(source_index=False),
            'source index float': lambda a: a['source_exports'][0].update(source_index=0.0),
            'source index': lambda a: a['source_exports'][0].update(source_index=2),
            'source extra': lambda a: a['source_exports'][0].update(approved=True),
            'source id': lambda a: a['source_exports'][0].update(source_id='changed'),
            'source order': lambda a: a['source_exports'].reverse(),
            'source missing': lambda a: a['source_exports'].pop(),
            'group completeness': lambda a: a['source_grouping'].update(completeness='ESTABLISHED'),
            'group count bool': lambda a: a['source_grouping'].update(source_count=True),
            'duplicate hints': lambda a: a['source_grouping'].update(duplicate_pmids=[]),
            'source bytes bool': lambda a: a['source_exports'][0]['source_export'].update(bytes=True),
            'source hash': lambda a: a['source_exports'][0]['source_export'].update(sha256='0' * 64),
            'source text': lambda a: a['source_exports'][0]['source_export'].update(text='PMID- 1\n'),
            'native extra': lambda a: a['source_exports'][0]['source_export'].update(approved=True),
            'parsed extra': lambda a: a['source_exports'][0]['parsed_export'].update(approved=True),
            'span bool': lambda a: a['source_exports'][0]['parsed_export']['records'][0]['source_span'].update(byte_start=False),
            'field text': lambda a: a['source_exports'][0]['parsed_export']['records'][0]['fields'][1].update(value_lines=['forged']),
            'csv provenance': lambda a: a['csv_intake']['parsed_export']['record_rows'][0]['original_values'].update(nbib_source_id='forged'),
            'protocol': lambda a: a['protocol_snapshot'].update(question='forged'),
            'engine': lambda a: a['engine_sha256'].update({'nbib_batch_intake.py': '0' * 64}),
        }
        for name, mutate in mutations.items():
            for reseal in [False, True]:
                changed = copy.deepcopy(artifact); mutate(changed)
                if reseal:
                    changed['review_target']['target_sha256'] = single.digest({k: v for k, v in changed.items() if k != 'review_target'})
                with self.subTest(name=name, reseal=reseal), self.assertRaises(ValueError): batch.verify(changed)
        hashes = batch.implementation_hashes()
        for name, sha in single.implementation_hashes().items(): self.assertEqual(hashes[name], sha)
        self.assertEqual(hashes['nbib_batch_intake.py'], hashlib.sha256((ROOT / 'nbib_batch_intake.py').read_bytes()).hexdigest())
        with patch.object(batch, 'implementation_hashes', return_value={'stale': 'code'}), self.assertRaises(ValueError): batch.verify(artifact)

    def test_strict_json_and_protocol_inputs(self):
        cycle = []; cycle.append(cycle)
        for value in [float('nan'), float('inf'), ('tuple',), {'set'}, {1: 'key'}, '\ud800', cycle]:
            base = copy.deepcopy(self.base); base['opaque_metadata'] = value
            with self.subTest(kind=type(value)), self.assertRaises(ValueError): self.prepare(protocol=base)
            with self.assertRaises(ValueError): batch.artifact_bytes(base)
        for field in ['search_id', 'searched_at']:
            for value in [None, '', ' ', True, []]:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError): self.prepare(**{field: value})
        with self.assertRaises(ValueError): self.prepare(search_id='undeclared')
        for bad in [[], 42, 'bad']:
            with self.assertRaises(ValueError): self.prepare(protocol=bad)
        for bad in [None, [], {}, {'schema_version': True}, {'schema_version': 1.0}]:
            with self.assertRaises(ValueError): batch.verify(bad)
        for reports in [42, [42], {'unexpected': True}]:
            base = copy.deepcopy(self.base); base['reports'] = reports
            with self.assertRaises(ValueError): self.prepare(protocol=base)

    def test_aggregate_and_per_source_quotas_inclusive_and_artifact_bounds(self):
        sources = [dict(source_id='one', raw=b'PMID- 1\n'), dict(source_id='two', raw=b'PMID- 2\n')]
        size = sum(len(s['raw']) for s in sources)
        self.assertEqual(batch.MAX_TOTAL_EXPORT_BYTES, 10_000_000)
        with patch.object(batch, 'MAX_TOTAL_EXPORT_BYTES', size): self.prepare(sources)
        with patch.object(batch, 'MAX_TOTAL_EXPORT_BYTES', size - 1), self.assertRaises(ValueError): self.prepare(sources)
        for name in ['MAX_TOTAL_RECORDS', 'MAX_TOTAL_PHYSICAL_LINES']:
            with patch.object(batch, name, 2): self.prepare(sources)
            with patch.object(batch, name, 1), self.assertRaises(ValueError): self.prepare(sources)
        for name in ['MAX_RECORDS', 'MAX_PHYSICAL_LINES']:
            with patch.object(parser, name, 0), self.assertRaises(ValueError): self.prepare(sources)
        with patch.object(parser, 'MAX_EXPORT_BYTES', len(sources[0]['raw']) - 1), self.assertRaises(ValueError): self.prepare(sources)
        artifact = self.prepare()
        size = len(batch.artifact_bytes(artifact))
        with patch.object(batch, 'MAX_ARTIFACT_BYTES', size): self.assertEqual(len(batch.artifact_bytes(artifact)), size)
        with patch.object(batch, 'MAX_ARTIFACT_BYTES', size - 1):
            for action in [lambda: batch.artifact_bytes(artifact), lambda: batch.verify(artifact), self.prepare]:
                with self.assertRaises(ValueError): action()

    def test_cli_roundtrip_mutual_exclusion_nooverwrite_and_dangling_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol = root / 'base.json'; protocol.write_text(json.dumps(self.base))
            first = root / 'first=synthetic.nbib'; first.write_bytes(self.sources[0]['raw'])
            second = root / 'second.nbib'; second.write_bytes(self.sources[1]['raw'])
            output = root / 'artifact.json'
            args = ['preview', protocol, '--export', 'first=' + str(first), '--export', 'second=' + str(second),
                    '--search-id', 'local-primary', '--searched-at', 'supplied', '--output', output]
            result = self.invoke(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            artifact = json.loads(output.read_bytes())
            self.assertEqual(json.loads(result.stdout), artifact)
            self.assertEqual([s['source_id'] for s in artifact['source_exports']], ['first', 'second'])
            saved = output.read_bytes()
            failed = self.invoke(*args)
            self.assertNotEqual(failed.returncode, 0); self.assertEqual(failed.stdout, b'')
            self.assertEqual(output.read_bytes(), saved)
            for flag, filename in [('--csv-output', 'derived.csv'), ('--intake-output', 'intake.json')]:
                destination = root / filename
                checked = self.invoke('verify', output, flag, destination)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertTrue(json.loads(checked.stdout)['valid'])
                if flag == '--csv-output': self.assertEqual(destination.read_bytes(), artifact['csv_intake']['source_export']['text'].encode())
                else: self.assertEqual(json.loads(destination.read_bytes()), artifact['csv_intake'])
                previous = destination.read_bytes()
                self.assertNotEqual(self.invoke('verify', output, flag, destination).returncode, 0)
                self.assertEqual(destination.read_bytes(), previous)
            self.assertNotEqual(self.invoke('verify', output, '--csv-output', root / 'a', '--intake-output', root / 'b').returncode, 0)
            self.assertFalse((root / 'a').exists()); self.assertFalse((root / 'b').exists())
            text = self.invoke('verify', output, '--text')
            self.assertEqual(text.returncode, 0, text.stderr); self.assertIn(b'NOT_READY', text.stdout)
            dangling = root / 'dangling'; missing = root / 'missing'
            try: dangling.symlink_to(missing)
            except (OSError, NotImplementedError): pass
            else:
                for command in [args[:-1] + [dangling], ['verify', output, '--csv-output', dangling], ['verify', output, '--intake-output', dangling]]:
                    result = self.invoke(*command)
                    self.assertNotEqual(result.returncode, 0); self.assertEqual(result.stdout, b'')
                    self.assertTrue(dangling.is_symlink()); self.assertFalse(missing.exists())

    def test_cli_invalid_inputs_and_serialization_fail_before_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            protocol = root / 'base'; protocol.write_text(json.dumps(self.base))
            export = root / 'native'; export.write_bytes(record())
            output = root / 'out'
            base = ['preview', protocol, '--search-id', 'local-primary', '--searched-at', 'supplied', '--output', output]
            for extra in [[], ['--export', 'missing-equals'], ['--export', '=' + str(export)],
                          ['--export', 'same=' + str(export), '--export', 'same=' + str(export)],
                          ['--export', 'valid=' + str(export), '--export', 'missing=' + str(root / 'missing')]]:
                result = self.invoke(*(base + extra))
                self.assertNotEqual(result.returncode, 0); self.assertEqual(result.stdout, b'')
                self.assertFalse(output.exists()); self.assertNotIn(b'Traceback', result.stderr)
            argv = ['nbib_batch_intake.py', *map(str, base), '--export', 'synthetic=' + str(export), '--text']
            artifact = self.prepare()
            for render in [lambda _: (_ for _ in ()).throw(ValueError('synthetic render failure')), lambda _: 'x' * 257]:
                with patch.object(sys, 'argv', argv), patch.object(batch, 'configure_utf8_stdio'), \
                     patch.object(sys, 'stderr', io.StringIO()), patch.object(sys, 'stdout', io.StringIO()), \
                     patch.object(batch, 'render_text', side_effect=render) as renderer, patch.object(batch, 'prepare', return_value=artifact), \
                     patch.object(batch, 'artifact_bytes', return_value=b'{}\n'), patch.object(batch, 'MAX_ARTIFACT_BYTES', 256), \
                     patch.object(batch.bibliographic_intake, 'read_bounded', side_effect=[json.dumps(self.base).encode(), record()]):
                    with self.assertRaises(SystemExit): batch.main()
                    renderer.assert_called_once()
                self.assertFalse(output.exists())
            export.write_bytes(b'PMID- 1\nSECRET malformed\n')
            result = self.invoke(*(base + ['--export', 'synthetic=' + str(export)]))
            self.assertNotEqual(result.returncode, 0); self.assertEqual(result.stdout, b'')
            self.assertFalse(output.exists()); self.assertNotIn(b'SECRET', result.stderr)
            malformed = root / 'malformed'; malformed.write_bytes(b'{"schema_version":1,"schema_version":1}')
            for flag in ['--csv-output', '--intake-output']:
                result = self.invoke('verify', malformed, flag, output)
                self.assertNotEqual(result.returncode, 0); self.assertFalse(output.exists())

    def test_text_output_quotes_controls_without_losing_native_values(self):
        hostile = 'synthetic\t"quote"\x1b\u202e\u2028\u0085\nConclusion: READY'
        artifact = self.prepare([dict(source_id=hostile, raw=record())], searched_at=hostile)
        self.assertEqual(artifact['source_exports'][0]['source_id'], hostile)
        for result in [artifact, batch.verify(artifact)]:
            rendered = batch.render_text(result)
            for character in ['\x1b', '\u202e', '\u2028', '\u0085', '\t']: self.assertNotIn(character, rendered)
            self.assertNotIn('\nConclusion: READY', rendered)
            self.assertIn('Conclusion: NOT_READY', rendered)
        self.assertTrue(batch.verify(json.loads(batch.artifact_bytes(artifact)))['valid'])

    def test_raw_csv_retains_formula_like_labels_not_spreadsheet_safety(self):
        labels = ['=1+1', '+1+1', '-1+1', '@synthetic', '\t=1+1', '\r=1+1', ' =1+1']
        sources = [dict(source_id=label, raw=record()) for label in labels]
        before = copy.deepcopy(sources)
        artifact = self.prepare(sources)
        self.assertEqual([row['original_values']['nbib_source_id']
            for row in artifact['csv_intake']['parsed_export']['record_rows']], labels)
        self.assertTrue(batch.verify(artifact)['valid'])
        self.assertEqual(sources, before)

    def test_prior_review_rejected_after_group_source_or_timestamp_changes(self):
        artifact = self.prepare()
        nested = artifact['csv_intake']
        choices = review.template(nested)
        for index, row in enumerate(choices['resolutions']):
            row.update(disposition='new_record', record_id=f'fictional-{index}',
                       rationale='Explicit synthetic identity choice')
        document = review.prepare_review(self.base, nested, choices)['review_document']
        document['review'].update(reviewer='Fictional human', reviewed_at='2026-11-04',
            rationale='Synthetic review of exact original batch', decision='import_for_screening')
        before = copy.deepcopy(document)
        changed_sources = []
        changed = copy.deepcopy(self.sources); changed.append(dict(source_id='additional', raw=record(OTHER))); changed_sources.append(changed)
        changed = copy.deepcopy(self.sources); changed.reverse(); changed_sources.append(changed)
        changed = copy.deepcopy(self.sources); changed[0]['source_id'] = 'changed label'; changed_sources.append(changed)
        changed = copy.deepcopy(self.sources); changed[0]['raw'] += b'\r\n'; changed_sources.append(changed)
        derivatives = [self.prepare(sources)['csv_intake'] for sources in changed_sources]
        derivatives.append(self.prepare(searched_at='another supplied timestamp')['csv_intake'])
        for derivative in derivatives:
            with self.assertRaises(ValueError):
                review.assemble(self.base, derivative, document)
        self.assertEqual(document, before)
        self.assertEqual(self.base['searches'], [])

    def test_output_entry_inspection_refuses_existing_and_propagates_errors(self):
        path = Path('synthetic-output-entry')
        with patch.object(Path, 'lstat', return_value=object()), patch.object(Path, 'open') as opened:
            with self.assertRaises(FileExistsError): batch._write_new(path, b'data')
            opened.assert_not_called()
        for error in [PermissionError('synthetic denial'), OSError('synthetic inspection failure')]:
            with patch.object(Path, 'lstat', side_effect=error), patch.object(Path, 'open') as opened:
                with self.assertRaises(type(error)): batch._write_new(path, b'data')
                opened.assert_not_called()


if __name__ == '__main__':
    unittest.main()
