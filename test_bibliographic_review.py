"""Synthetic, explicit reconciliation, flat history, accounting and CLI regression tests."""
import copy
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

import bibliographic_intake as intake
import bibliographic_integrity as integrity
import bibliographic_review as review
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_audit import export_audit
import research_bundle as bundle

ROOT = Path(__file__).resolve().parent


class BibliographicReviewTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / 'examples/bibliographic-base.json').read_text(encoding='utf-8'))
        self.raw = (ROOT / 'examples/bibliographic-export.csv').read_bytes()
        self.choices = json.loads((ROOT / 'examples/bibliographic-resolutions.json').read_text(encoding='utf-8'))
        self.artifact = self.prepare()

    def prepare(self, base=None, raw=None, search='local-primary'):
        return intake.prepare(self.base if base is None else base, self.raw if raw is None else raw,
                              search, '2026-11-04T00:00:00Z')

    def signed(self, protocol=None, artifact=None, choices=None):
        doc = review.prepare_review(self.base if protocol is None else protocol,
                                    self.artifact if artifact is None else artifact,
                                    self.choices if choices is None else choices)['review_document']
        doc['review'].update(reviewer='Synthetic test operator', reviewed_at='2026-11-04',
                             rationale='Synthetic explicit collection review only', decision='import_for_screening')
        return doc

    def imported(self):
        return review.assemble(self.base, self.artifact, self.signed())['protocol_candidate']

    def second(self):
        current = self.imported()
        current['version'] = 'synthetic-enriched-v2'
        current['screening'] = [dict(record_id='synthetic-record-1', decision='include', reason='synthetic scope')]
        current['gaps'] = [dict(question='Synthetic work question?', evidence_ids=[],
                               deliverable='Synthetic plan', acceptance_criterion='Explicit controls', context='synthetic',
                               work_type='source_review', source_refs=[dict(kind='record', record_id='synthetic-record-1')])]
        artifact = self.prepare(raw=b'record_id,source_locator\nx,synthetic:second\ny,synthetic:third\n', search='local-secondary')
        choices = review.template(artifact)
        for row, disposition, rid in zip(choices['resolutions'], ['same_record', 'new_record'],
                                          ['synthetic-record-1', 'synthetic-second-new']):
            row.update(disposition=disposition, record_id=rid, rationale='Synthetic supplied identity choice')
        return current, artifact, choices

    def reseal_entry(self, protocol, index=0):
        entry = protocol['bibliographic_imports']['imports'][index]
        entry['sha256'] = integrity.digest({k: v for k, v in entry.items() if k != 'sha256'})

    def test_template_target_and_explicit_import(self):
        template = review.template(self.artifact)
        self.assertIsNone(template['review'])
        self.assertTrue(all(r['disposition'] is None for r in template['resolutions']))
        prepared = review.prepare_review(self.base, self.artifact, self.choices)
        self.assertFalse(prepared['protocol_changed'])
        self.assertTrue(all(v is None for k, v in prepared['review_document']['review'].items() if k != 'target_sha256'))
        with self.assertRaises(ValueError):
            review.assemble(self.base, self.artifact, prepared['review_document'])
        protocol = self.imported()
        self.assertEqual(protocol['searches'][0]['record_ids'], ['synthetic-record-1', 'synthetic-guideline-record'])
        self.assertEqual(protocol['screening'], [])
        rows = run(protocol)['bibliographic_collection']['row_ledger']
        self.assertNotEqual(rows[0]['original_values']['source_locator'], rows[2]['original_values']['source_locator'])

    def test_forward_reference_and_reordered_choices_are_canonical(self):
        choices = copy.deepcopy(self.choices)
        choices['resolutions'][0]['disposition'] = 'same_record'
        choices['resolutions'][2]['disposition'] = 'new_record'
        expected = review.prepare_review(self.base, self.artifact, choices)
        choices['resolutions'].reverse()
        actual = review.prepare_review(self.base, self.artifact, choices)
        self.assertEqual(expected, actual)
        self.assertEqual([r['candidate_id'] for r in actual['review_document']['resolutions']],
                         [r['candidate_id'] for r in self.artifact['parsed_export']['record_rows']])
        review.assemble(self.base, self.artifact, self.signed(choices=choices))

    def test_invalid_resolution_sets(self):
        cases = []
        def case(label, edit):
            doc = copy.deepcopy(self.choices); edit(doc['resolutions']); cases.append((label, doc))
        case('missing', lambda r: r.pop())
        case('duplicate', lambda r: r.append(copy.deepcopy(r[0])))
        case('unknown', lambda r: r[0].update(candidate_id='unknown'))
        case('new collision', lambda r: r[3].update(record_id=r[0]['record_id']))
        case('unknown same', lambda r: r[1].update(record_id='missing'))
        case('extra field', lambda r: r[0].update(extra=True))
        case('blank rationale', lambda r: r[0].update(rationale=' '))
        case('unknown disposition', lambda r: r[0].update(disposition='include'))
        case('withheld ID', lambda r: r[-1].update(record_id='bad'))
        case('null new ID', lambda r: r[0].update(record_id=None))
        for label, doc in cases:
            with self.subTest(label=label), self.assertRaises(ValueError):
                review.prepare_review(self.base, self.artifact, doc)

    def test_strict_document_schema_and_no_review_renewal(self):
        for key, value in [('extra', True), ('schema_version', True), ('review', {})]:
            doc = copy.deepcopy(self.choices); doc[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                review.prepare_review(self.base, self.artifact, doc)
        with self.assertRaises(ValueError):
            review.prepare_review(self.base, self.artifact, self.signed())

    def test_invalid_review_metadata(self):
        for field, values in {'reviewed_at': ['2026-02-30', '2026-1-01', '2026-11-04T00:00:00Z', '0000-01-01'],
                              'decision': ['approve', 'include', None], 'reviewer': ['', ' ', None],
                              'rationale': ['', None], 'target_sha256': ['0' * 64]}.items():
            for value in values:
                doc = self.signed(); doc['review'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    review.assemble(self.base, self.artifact, doc)
        doc = self.signed(); doc['review']['extra'] = True
        with self.assertRaises(ValueError): review.assemble(self.base, self.artifact, doc)

    def test_stale_protocol_artifact_and_resolution_targets(self):
        signed = self.signed()
        changed = copy.deepcopy(self.base); changed['version'] = 'changed'
        with self.assertRaises(ValueError): review.assemble(changed, self.artifact, signed)
        altered = self.prepare(raw=self.raw + b'new,synthetic:extra,Extra,synthetic,note\n')
        with self.assertRaises(ValueError): review.assemble(self.base, altered, signed)
        signed['resolutions'][0]['rationale'] += ' changed'
        with self.assertRaises(ValueError): review.assemble(self.base, self.artifact, signed)

    def test_empty_and_all_withheld_still_need_review_and_remain_incomplete(self):
        for raw in [b'record_id,source_locator\r\n', self.raw]:
            artifact = self.prepare(raw=raw)
            doc = review.template(artifact)
            for row in doc['resolutions']:
                row.update(disposition='do_not_promote', rationale='Synthetic withheld')
            with self.assertRaises(ValueError): review.assemble(self.base, artifact, doc)
            protocol = review.assemble(self.base, artifact, self.signed(artifact=artifact, choices=doc))['protocol_candidate']
            search = protocol['searches'][0]
            self.assertEqual(search['record_ids'], [])
            self.assertIs(search['complete'], False)
            self.assertIsNone(search['total_count']); self.assertIsNone(search['has_more'])
            self.assertEqual(run(protocol)['bibliographic_collection']['counts']['withheld_rows'], len(doc['resolutions']))

    def test_sequential_common_base_preserves_current_enrichment(self):
        current, artifact, choices = self.second()
        before = copy.deepcopy(current)
        result = review.assemble(current, artifact, self.signed(current, artifact, choices))
        protocol = result['protocol_candidate']
        self.assertEqual(current, before)
        for field in ['version', 'screening', 'gaps']:
            self.assertEqual(protocol[field], current[field])
        self.assertEqual(len(run(protocol)['work_packages']), len(run(current)['work_packages']))
        self.assertEqual(protocol['searches'][1]['record_ids'], ['synthetic-record-1', 'synthetic-second-new'])
        self.assertEqual(result['artifact_base_version'], self.base['version'])
        self.assertEqual(result['reviewed_protocol_version'], current['version'])
        self.assertEqual(run(protocol)['bibliographic_collection']['counts']['raw_rows'], 7)
        choices['resolutions'][0]['disposition'] = 'new_record'
        with self.assertRaises(ValueError): review.prepare_review(current, artifact, choices)

    def test_repeated_search_intermediate_base_and_implicit_rebase_rejected(self):
        current, artifact, choices = self.second()
        with self.assertRaises(ValueError): review.prepare_review(current, self.artifact, self.choices)
        intermediate = self.prepare(base=current, raw=b'record_id,source_locator\nx,y\n', search='local-secondary')
        with self.assertRaises(ValueError): review.prepare_review(current, intermediate, review.template(intermediate))
        changed = copy.deepcopy(self.base); changed['version'] = 'other-base'
        other = self.prepare(base=changed)
        with self.assertRaises(ValueError): review.prepare_review(self.base, other, self.choices)

    def test_no_mixing_mock_ledgers_or_provenance(self):
        for location in ['ledger', 'search', 'evidence']:
            protocol = self.imported()
            if location == 'ledger': protocol['adapter_receipts'] = []
            elif location == 'search': protocol['searches'][0]['adapter_provenance'] = {}
            else: protocol['evidence'] = [dict(adapter_provenance={})]
            with self.subTest(location=location), self.assertRaises(ValueError): run(protocol)

    def test_compact_reconstruction_only_calls_ledger_free_base(self):
        current, artifact, choices = self.second()
        protocol = review.assemble(current, artifact, self.signed(current, artifact, choices))['protocol_candidate']
        calls = []
        def verify(full):
            self.assertNotIn('bibliographic_imports', full['protocol_snapshot'])
            self.assertNotIn('adapter_receipts', full['protocol_snapshot'])
            self.assertEqual(full['protocol_snapshot'], self.base)
            calls.append(copy.deepcopy(full)); return intake.verify(full)
        summary = integrity.validate_protocol(protocol, verify)
        self.assertEqual(calls, [self.artifact, artifact])
        self.assertEqual(len(summary['imports']), 2)
        for entry in protocol['bibliographic_imports']['imports']:
            self.assertNotIn('protocol_snapshot', entry['intake'])
            self.assertNotIn('bibliographic_imports', entry['prior_protocol_body'])
        with self.assertRaises(ValueError): integrity.validate_protocol(protocol, None)

    def test_tampered_raw_spans_rows_choices_review_and_history_rejected_even_resealed(self):
        mutations = {
            'raw': lambda e: e['intake']['source_export'].update(text='changed'),
            'span': lambda e: e['intake']['parsed_export']['record_rows'][0]['source_span'].update(byte_start=999),
            'row': lambda e: e['intake']['parsed_export']['record_rows'][0]['original_values'].update(title='changed'),
            'choice': lambda e: e['resolutions'][0].update(rationale='changed'),
            'review': lambda e: e['review'].update(target_sha256='0' * 64),
            'history': lambda e: e['prior_protocol_body'].update(version='changed'),
            'prefix': lambda e: e.update(prior_prefix_count=1),
            'compact': lambda e: e['intake'].update(protocol_snapshot=self.base),
        }
        for name, mutate in mutations.items():
            for reseal in [False, True]:
                protocol = self.imported(); mutate(protocol['bibliographic_imports']['imports'][0])
                if reseal: self.reseal_entry(protocol)
                with self.subTest(name=name, reseal=reseal), self.assertRaises(ValueError): run(protocol)

    def test_tampered_base_context_search_completeness_orphan_and_order(self):
        current, artifact, choices = self.second()
        original = review.assemble(current, artifact, self.signed(current, artifact, choices))['protocol_candidate']
        mutations = {
            'base': lambda p: p['bibliographic_imports']['base_protocol'].update(version='changed'),
            'question': lambda p: p.update(question='changed'),
            'plan': lambda p: p['search_plan'][0].update(query='changed'),
            'complete': lambda p: p['searches'][0].update(complete=True),
            'total': lambda p: p['searches'][0].update(total_count=2, has_more=False),
            'orphan': lambda p: p.pop('bibliographic_imports'),
            'order': lambda p: p['bibliographic_imports']['imports'].reverse(),
            'search order': lambda p: p['searches'].reverse(),
            'empty ledger': lambda p: p['bibliographic_imports'].update(imports=[]),
        }
        for name, mutate in mutations.items():
            protocol = copy.deepcopy(original); mutate(protocol)
            with self.subTest(name=name), self.assertRaises(ValueError): run(protocol)

    def test_second_history_prefix_tampering_resealed(self):
        current, artifact, choices = self.second()
        original = review.assemble(current, artifact, self.signed(current, artifact, choices))['protocol_candidate']
        for field, value in [('prior_prefix_count', 0), ('prior_protocol_body', self.base)]:
            protocol = copy.deepcopy(original)
            protocol['bibliographic_imports']['imports'][1][field] = copy.deepcopy(value)
            self.reseal_entry(protocol, 1)
            with self.subTest(field=field), self.assertRaises(ValueError): run(protocol)

    def test_current_screening_can_evolve_without_invalidating_history(self):
        protocol = self.imported()
        protocol['screening'] = [dict(record_id='synthetic-record-1', decision='exclude', reason='Synthetic out of scope')]
        self.assertEqual(run(protocol)['flow']['excluded'], 1)
        protocol['screening'][0].update(decision='include', reason='Synthetic corrected scope')
        self.assertEqual(run(protocol)['flow']['included'], 1)

    def test_protocol_size_import_and_output_bounds(self):
        protocol = self.imported()
        size = len(canonical_json_bytes(protocol))
        with patch.object(integrity, 'MAX_PROTOCOL_BYTES', size): run(protocol)
        with patch.object(integrity, 'MAX_PROTOCOL_BYTES', size - 1), self.assertRaises(ValueError): run(protocol)
        with patch.object(integrity, 'MAX_IMPORTS', 0), self.assertRaises(ValueError): run(protocol)
        with patch.object(intake, 'MAX_ARTIFACT_BYTES', 1), self.assertRaises(ValueError):
            review.assemble(self.base, self.artifact, self.signed())

    def test_inputs_and_all_nested_outputs_are_isolated(self):
        document = self.signed()
        snapshots = copy.deepcopy((self.base, self.artifact, document))
        result = review.assemble(self.base, self.artifact, document)
        self.assertEqual((self.base, self.artifact, document), snapshots)
        result['protocol_candidate']['bibliographic_imports']['base_protocol']['search_plan'][0]['query'] = 'mutated'
        result['protocol_candidate']['bibliographic_imports']['imports'][0]['intake']['parsed_export']['record_rows'][0]['original_values']['title'] = 'mutated'
        result['bibliographic_collection']['row_ledger'][0]['resolution']['rationale'] = 'mutated'
        self.assertEqual((self.base, self.artifact, document), snapshots)
        normalized = integrity.normalize_resolutions(self.artifact, self.choices['resolutions'], set())
        normalized[0]['rationale'] = 'mutated'
        self.assertNotEqual(normalized, self.choices['resolutions'])

    def test_raw_collection_and_prisma_membership_counts_and_pointers(self):
        protocol = self.imported(); research = run(protocol); audit = export_audit(protocol)
        self.assertEqual(research['bibliographic_collection']['counts'], dict(raw_rows=5,
                         promoted_row_occurrences=4, withheld_rows=1, canonical_search_memberships=2))
        self.assertEqual(research['flow']['identified'], 2)
        self.assertEqual(research['flow']['duplicates'], 0)
        self.assertEqual(len(audit['occurrence_ledger']), 2)
        self.assertEqual(audit['bibliographic_collection'], research['bibliographic_collection'])
        for record in audit['record_ledger']:
            pointers = record['bibliographic_row_pointers']
            self.assertEqual(len(pointers), 3 if record['record_id'] == 'synthetic-record-1' else 1)
            for pointer in pointers:
                value = protocol
                for key in pointer.lstrip('/').split('/'):
                    value = value[int(key)] if isinstance(value, list) else value[key]
                self.assertIn(value, self.artifact['parsed_export']['record_rows'])

    def test_safe_text_quotes_supplied_control_characters(self):
        choices = copy.deepcopy(self.choices)
        choices['resolutions'][0]['rationale'] = 'Synthetic\nFORGED STATUS\x1b[31m'
        rendered = review.render_text(review.prepare_review(self.base, self.artifact, choices))
        self.assertNotIn('\nFORGED STATUS', rendered)
        self.assertNotIn('\x1b', rendered)
        self.assertIn('\\nFORGED STATUS', rendered)

    def test_bundle_deterministic_roundtrip_and_dependency_hashes(self):
        protocol = self.imported(); raw = intake.artifact_bytes(protocol)
        archive = bundle.build_bundle(raw)
        self.assertEqual(archive, bundle.build_bundle(raw))
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            manifest = json.loads(z.read('manifest.json'))
            for filename in ['bibliographic_review.py', 'bibliographic_integrity.py', 'bibliographic_intake.py', 'csv_export_parser.py']:
                self.assertIn(filename, manifest['engine_sha256'])
            self.assertEqual(json.loads(z.read('research.json'))['bibliographic_collection'], run(protocol)['bibliographic_collection'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.zip'; path.write_bytes(archive)
            self.assertTrue(bundle.verify(path)['valid'])

    def invoke(self, *args):
        env = dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0')
        return subprocess.run([sys.executable, str(ROOT / 'bibliographic_review.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, env=env, timeout=30)

    def test_cli_template_target_assemble_exclusive_outputs_utf8_crlf(self):
        raw = 'record_id,source_locator,title\r\n합성,synthetic:one,"첫째\r\n둘째"\r\n'.encode('utf-8')
        artifact = self.prepare(raw=raw)
        choices = review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record', record_id='합성', rationale='합성 검토')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, value in [('base', self.base), ('artifact', artifact), ('choices', choices)]:
                (root / name).write_bytes(intake.artifact_bytes(value))
            commands = [('template', [root/'artifact'], '--review-output', root/'template'),
                        ('target', [root/'base', root/'artifact', root/'choices'], '--review-output', root/'review')]
            for command, args, flag, output in commands:
                result = self.invoke(command, *args, flag, output, '--text')
                self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
                saved = output.read_bytes()
                self.assertNotEqual(self.invoke(command, *args, flag, output).returncode, 0)
                self.assertEqual(saved, output.read_bytes())
            signed = json.loads((root/'review').read_bytes())
            signed['review'].update(reviewer='합성 검토자', reviewed_at='2026-11-04', rationale='합성', decision='import_for_screening')
            (root/'signed').write_bytes(intake.artifact_bytes(signed))
            args = ['assemble', root/'base', root/'artifact', root/'signed', '--protocol-output', root/'protocol']
            result = self.invoke(*args)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            decoded = json.loads(result.stdout.decode('utf-8'))
            self.assertEqual(decoded['protocol_candidate']['searches'][0]['record_ids'], ['합성'])
            retained = decoded['protocol_candidate']['bibliographic_imports']['imports'][0]['intake']['source_export']['text']
            self.assertEqual(retained.encode('utf-8'), raw)
            saved = (root/'protocol').read_bytes()
            self.assertNotEqual(self.invoke(*args).returncode, 0)
            self.assertEqual(saved, (root/'protocol').read_bytes())

    def test_same_record_can_link_to_ledger_free_existing_record(self):
        base = copy.deepcopy(self.base)
        base['searches'] = [dict(search_id='local-secondary', source='synthetic-second-export',
                                query='fictional development context', window='2020-2026',
                                searched_at='2026-11-03', record_ids=['synthetic-record-1'],
                                complete=False, total_count=None, has_more=None)]
        artifact = self.prepare(base=base)
        choices = copy.deepcopy(self.choices)
        choices['resolutions'][0]['disposition'] = 'same_record'
        protocol = review.assemble(base, artifact, self.signed(base, artifact, choices))['protocol_candidate']
        self.assertEqual(run(protocol)['flow']['identified'], 3)
        self.assertEqual(run(protocol)['flow']['duplicates'], 1)
        self.assertEqual(run(protocol)['bibliographic_collection']['counts']['raw_rows'], 5)
        choices['resolutions'][0]['disposition'] = 'new_record'
        with self.assertRaises(ValueError): review.prepare_review(base, artifact, choices)

    def test_second_target_binds_exact_current_enrichment_and_prior_prefix(self):
        current, artifact, choices = self.second()
        signed = self.signed(current, artifact, choices)
        altered = copy.deepcopy(current)
        altered['screening'][0]['reason'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'target hash mismatch'):
            review.assemble(altered, artifact, signed)
        protocol = review.assemble(current, artifact, signed)['protocol_candidate']
        first = protocol['bibliographic_imports']['imports'][0]
        first['review']['reviewer'] = 'Another supplied synthetic reviewer'
        self.reseal_entry(protocol)
        protocol['searches'][0] = integrity.normalized_search(self.artifact, first, 0)
        second = protocol['bibliographic_imports']['imports'][1]
        second['prior_protocol_body']['searches'][0] = copy.deepcopy(protocol['searches'][0])
        self.reseal_entry(protocol, 1)
        protocol['searches'][1] = integrity.normalized_search(artifact, second, 1)
        with self.assertRaisesRegex(ValueError, 'reconciliation target mismatch'):
            run(protocol)

    def test_historical_enrichment_bound_even_after_receipt_and_search_reseal(self):
        current, artifact, choices = self.second()
        protocol = review.assemble(current, artifact, self.signed(current, artifact, choices))['protocol_candidate']
        second = protocol['bibliographic_imports']['imports'][1]
        second['prior_protocol_body']['screening'][0]['reason'] += ' changed history'
        self.reseal_entry(protocol, 1)
        protocol['searches'][1] = integrity.normalized_search(artifact, second, 1)
        with self.assertRaisesRegex(ValueError, 'reconciliation target mismatch'):
            run(protocol)

    def test_opaque_base_fields_immutable_and_summary_independent_of_protocol(self):
        base = copy.deepcopy(self.base); base['opaque'] = {'nested': ['synthetic']}
        artifact = self.prepare(base=base)
        protocol = review.assemble(base, artifact, self.signed(base, artifact))['protocol_candidate']
        summary = integrity.validate_protocol(protocol, intake.verify)
        before = copy.deepcopy(protocol)
        summary['row_ledger'][0]['original_values']['title'] = 'changed summary'
        summary['imports'][0]['review']['reviewer'] = 'changed summary'
        self.assertEqual(protocol, before)
        protocol['opaque']['nested'].append('changed context')
        with self.assertRaisesRegex(ValueError, 'immutable protocol context'):
            run(protocol)

    def test_cli_invalid_inputs_never_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, value in [('base', self.base), ('artifact', self.artifact), ('choices', self.choices), ('invalid', {})]:
                (root/name).write_bytes(intake.artifact_bytes(value))
            cases = [('template', [root/'invalid'], '--review-output'),
                     ('target', [root/'base', root/'artifact', root/'invalid'], '--review-output'),
                     ('assemble', [root/'base', root/'artifact', root/'choices'], '--protocol-output')]
            for index, (command, args, flag) in enumerate(cases):
                output = root / str(index)
                with self.subTest(command=command):
                    self.assertNotEqual(self.invoke(command, *args, flag, output).returncode, 0)
                    self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
