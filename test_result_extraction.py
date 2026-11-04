"""Independent fictional-data tests for read-only manual extraction preparation."""
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

import result_extraction as extraction
import result_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
from research_bundle import engine_hashes

ROOT = Path(__file__).resolve().parent


def base():
    return json.loads((ROOT / 'examples/result-source-current.json').read_text(encoding='utf-8'))


def minimal():
    p = base()
    keep = {'question', 'version', 'inclusion_criteria', 'exclusion_criteria', 'search_plan',
            'searches', 'screening', 'reports', 'evidence', 'report_sources', 'gaps'}
    p = {k: v for k, v in p.items() if k in keep}
    p['gaps'] = []
    return p


def context(cid, ids):
    row = json.loads((ROOT / 'examples/context-protocol.json').read_text(encoding='utf-8'))['contexts'][0]
    row.update(context_id=cid, evidence_ids=ids)
    return row


class ResultExtractionTests(unittest.TestCase):
    def setUp(self):
        self.p = base()

    def sheet(self, p=None, report='report-one', study='study-A', record='record-one'):
        return extraction.worksheet(self.p if p is None else p, report, study, record)

    def test_exact_blank_intake_schema_and_determinism(self):
        before = canonical_json_bytes(self.p)
        s = self.sheet()
        self.assertEqual(s, self.sheet())
        self.assertEqual(canonical_json_bytes(self.p), before)
        expected = {key: None for key in intake.EVIDENCE_FIELDS}
        expected.update(record_id='record-one', study_id='study-A')
        self.assertEqual(s['candidate_document'], {'schema_version': 1, 'candidates': [{
            'report_id': 'report-one', 'evidence': expected, 'source_references': [],
            'extracted_by': None, 'extracted_at': None, 'extraction_note': None}]})
        with self.assertRaises(ValueError):
            intake.prepare(self.p, s['candidate_document'])
        self.assertFalse(s['candidate_is_complete'])
        self.assertFalse(s['protocol_changed'])
        self.assertEqual(s['external_calls'], 0)
        self.assertEqual(s['source_reference_template'], {'source_id': None, 'extraction_locator': None})
        self.assertNotIn('review_document', s)

    def test_documented_fixture_has_only_explicit_context_intersections(self):
        p = json.loads((ROOT/'examples/extraction-worksheet-protocol.json').read_text(encoding='utf-8'))
        s = self.sheet(p, study='study-C')
        self.assertEqual(s['counts'], dict(existing_pair_results=1,
                         existing_selected_record_results=1, available_source_descriptors=2))
        self.assertEqual([r['context']['context_id'] for r in s['source_record_contexts']], ['ctx-selected-record'])
        self.assertEqual([r['context']['context_id'] for r in s['existing_result_contexts']], ['ctx-existing-result'])
        for group in ('source_record_contexts', 'existing_result_contexts'):
            for linked in s[group]:
                index = int(linked['input_pointer'].split('/')[-1])
                self.assertEqual(linked['context'], p['contexts'][index])
        self.assertEqual(s['source_record_contexts'][0]['matched_source_refs'],
                         [dict(kind='record', record_id='record-one')])
        self.assertEqual(s['existing_result_contexts'][0]['matched_evidence_ids'], ['result-C-manual'])

    def test_all_three_selections_mandatory_literal_and_exact(self):
        for args in ((), ('report-one',), ('report-one', 'study-A')):
            with self.subTest(args=args), self.assertRaises(TypeError):
                extraction.worksheet(self.p, *args)
        for index in range(3):
            for value in (None, True, 3, [], {}, '', ' ', 'unknown',
                          ('report-one', 'study-A', 'record-one')[index] + ' '):
                args = ['report-one', 'study-A', 'record-one']; args[index] = value
                with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                    extraction.worksheet(self.p, *args)
        with self.assertRaises(ValueError): self.sheet(record='record-two')
        with self.assertRaises(ValueError): self.sheet(study='candidate-X')

    def test_scalar_and_plural_memberships(self):
        self.assertEqual(self.sheet(study='study-B')['selection']['study_id'], 'study-B')
        p = minimal(); p['reports'][0].pop('study_ids'); p['reports'][0]['study_id'] = 'study-A'
        p['evidence'] = [r for r in p['evidence'] if r['study_id'] == 'study-A']
        self.assertEqual(self.sheet(p)['counts']['existing_pair_results'], 2)
        with self.assertRaises(ValueError): self.sheet(p, study='study-B')

    def test_retrieved_explicitly_included_report_required(self):
        for rid, record in [('report-two','record-two'), ('report-three','record-three'),
                            ('report-four','record-four'), ('report-five','record-five')]:
            with self.subTest(report=rid), self.assertRaises(ValueError):
                self.sheet(report=rid, record=record)
        p = minimal(); del p['reports']
        with self.assertRaisesRegex(ValueError, 'explicit reports'): self.sheet(p)
        p = minimal(); p['adapter_receipts'] = {}
        with self.assertRaisesRegex(ValueError, 'adapter_receipts'): self.sheet(p)

    def test_pair_scope_spans_mapped_records_but_not_other_reports_or_studies(self):
        p = minimal()
        p['searches'][0]['record_ids'].append('record-six')
        p['screening'].append(dict(record_id='record-six', decision='include', reason='Fictional inclusion'))
        p['reports'][0]['record_ids'].append('record-six')
        same = dict(p['evidence'][0], evidence_id='result-six', record_id='record-six')
        other = dict(p['evidence'][0], evidence_id='other-report-same-study', record_id='record-two')
        p['reports'][1]['decision'] = 'include'; p['reports'][1].pop('reason')
        p['evidence'].extend([same, other])
        s = self.sheet(p)
        self.assertEqual([r['normalized_evidence_id'] for r in s['existing_results']],
                         ['result-A', 'result-A-second', 'result-six'])
        self.assertEqual([r['input_pointer'] for r in s['existing_results']], ['/evidence/0','/evidence/3','/evidence/4'])
        self.assertEqual([r['selected_record'] for r in s['existing_results']], [True, True, False])
        self.assertEqual(s['counts']['existing_pair_results'], 3)
        self.assertEqual(s['counts']['existing_selected_record_results'], 2)
        selected_six = self.sheet(p, record='record-six')
        self.assertEqual([r['evidence'] for r in selected_six['existing_results']],
                         [r['evidence'] for r in s['existing_results']])
        self.assertEqual(selected_six['counts']['existing_selected_record_results'], 1)

    def test_raw_implicit_id_and_literal_values_preserved_without_mutation(self):
        p = minimal(); p['evidence'][0].pop('evidence_id')
        p['evidence'][0]['result'] = '  Fictional literal\n결과  '
        s = self.sheet(p); row = s['existing_results'][0]
        self.assertEqual(row['evidence'], p['evidence'][0])
        self.assertNotIn('evidence_id', row['evidence'])
        self.assertEqual(row['normalized_evidence_id'], 'record-one')
        self.assertEqual(row['evidence_id_origin'], 'IMPLICIT_RECORD_ID')
        self.assertEqual(s['existing_results'][1]['evidence_id_origin'], 'EXPLICIT')
        row['evidence']['result'] = 'changed detached worksheet'
        self.assertEqual(p['evidence'][0]['result'], '  Fictional literal\n결과  ')

    def test_no_existing_pair_does_not_invent_results(self):
        p = minimal(); p['reports'][0]['study_ids'].append('study-empty')
        s = self.sheet(p, study='study-empty')
        self.assertEqual(s['existing_results'], [])
        self.assertEqual(s['existing_result_contexts'], [])
        self.assertEqual(s['counts']['existing_pair_results'], 0)
        self.assertIsNone(s['candidate_document']['candidates'][0]['evidence']['result'])

    def test_sources_available_unverified_unselected_and_source_less_scaffolds(self):
        s = self.sheet()
        self.assertEqual(s['available_sources'], [dict(source=source, input_pointer=f'/report_sources/{i}')
                         for i, source in enumerate(self.p['report_sources']) if source['report_id']=='report-one'])
        self.assertEqual(s['preparation_status'], 'DRAFT_REQUIRES_HUMAN_INPUT')
        for key, expected in [('source_authenticity','NOT_VERIFIED'), ('document_bytes_verification','NOT_PERFORMED'),
                              ('reading','NOT_ESTABLISHED'), ('extraction_completeness','NOT_ESTABLISHED'),
                              ('scientific_correctness','NOT_ASSESSED'), ('conclusion_readiness','NOT_READY')]:
            self.assertEqual(s[key], expected)
        for supplied in (False, True):
            p = minimal()
            if supplied: p['report_sources'] = []
            else: p.pop('report_sources')
            s = self.sheet(p)
            self.assertEqual(s['source_stage'], 'SUPPLIED' if supplied else 'NOT_SUPPLIED')
            self.assertEqual(s['preparation_status'], 'SOURCE_DESCRIPTORS_REQUIRED')
            self.assertEqual(s['available_sources'], [])
            self.assertFalse(s['candidate_is_complete'])
            self.assertEqual(s['candidate_document']['candidates'][0]['source_references'], [])
        p = minimal(); p['report_sources'] = p['report_sources'][2:]
        self.assertEqual(self.sheet(p)['preparation_status'], 'SOURCE_DESCRIPTORS_REQUIRED')

    def test_available_sources_preserve_null_and_nonnull_digests(self):
        p = minimal()
        p['report_sources'][0]['document_sha256'] = None
        p['report_sources'][1]['document_sha256'] = 'b' * 64
        s = self.sheet(p)
        self.assertEqual([r['source']['document_sha256'] for r in s['available_sources']], [None, 'b' * 64])
        self.assertEqual(s['report_target']['source_binding_state'], 'DOCUMENT_BYTES_UNBOUND')
        self.assertEqual(s['source_authenticity'], 'NOT_VERIFIED')
        self.assertEqual(s['document_bytes_verification'], 'NOT_PERFORMED')
        self.assertEqual(s['candidate_document']['candidates'][0]['source_references'], [])
        self.assertEqual(s['available_sources'][0]['source'], p['report_sources'][0])
        self.assertEqual(s['available_sources'][1]['source'], p['report_sources'][1])

    def test_deep_output_detachment_from_input_and_between_views(self):
        p = json.loads((ROOT/'examples/extraction-worksheet-protocol.json').read_text(encoding='utf-8'))
        before = copy.deepcopy(p)
        s = self.sheet(p, study='study-C')
        fresh = copy.deepcopy(s)
        s['inclusion_criteria'].append('Fictional detached edit')
        s['report_target']['recorded_report']['record_ids'].append('detached-record')
        s['selected_record_target']['source_basis']['occurrences'][0]['search_index'] = -1
        s['source_contexts'][0]['search_index'] = -2
        s['available_sources'][0]['source']['document_version'] = 'detached version'
        s['existing_results'][0]['evidence']['result'] = 'detached finding'
        s['source_record_contexts'][0]['context']['source_refs'][0]['record_id'] = 'detached-context-record'
        s['existing_result_contexts'][0]['context']['evidence_ids'].append('detached-result')
        s['candidate_document']['candidates'][0]['evidence']['record_id'] = 'detached-candidate-record'
        self.assertEqual(p, before)
        self.assertEqual(self.sheet(p, study='study-C'), fresh)
        self.assertEqual(s['selection'], fresh['selection'])
        self.assertEqual(s['report_target']['source_basis']['report_sources'],
                         fresh['report_target']['source_basis']['report_sources'])
        self.assertEqual(s['source_record_contexts'][0]['matched_source_refs'],
                         fresh['source_record_contexts'][0]['matched_source_refs'])
        self.assertEqual(s['existing_result_contexts'][0]['matched_evidence_ids'],
                         fresh['existing_result_contexts'][0]['matched_evidence_ids'])

    def test_opaque_numeric_metadata_retained_in_fingerprint_without_coercion(self):
        p = minimal()
        p['opaque_metadata'] = dict(whole=10**30+7, fractional=1.25, enabled=True,
                                   absent=None, nested=[0, -9, 0.125])
        before = copy.deepcopy(p)
        s = self.sheet(p)
        self.assertEqual(p, before)
        self.assertEqual(s['protocol_sha256'], hashlib.sha256(canonical_json_bytes(p)).hexdigest())
        self.assertIsNone(s['candidate_document']['candidates'][0]['evidence']['result'])
        p['opaque_metadata']['whole'] += 1
        self.assertNotEqual(self.sheet(p)['protocol_sha256'], s['protocol_sha256'])

    def test_context_links_exact_typed_noninherited_and_full_raw_context_preserved(self):
        p = minimal()
        selected = context('selected-record', [])
        selected.update(context_scope='source_review', source_refs=[
            dict(kind='record',record_id='record-one'), dict(kind='record',record_id='record-two'),
            dict(kind='planned_search', search_id='synthetic-search')])
        planned = copy.deepcopy(selected); planned.update(context_id='search-only', source_refs=[selected['source_refs'][2]])
        other = copy.deepcopy(selected); other.update(context_id='other-record', source_refs=[selected['source_refs'][1]])
        # Same text in a different typed namespace must not match record-one.
        p['search_plan'].append(dict(search_id='record-one', source='synthetic-index', query='Fictional query', window='2020-2026'))
        cross = copy.deepcopy(selected); cross.update(context_id='cross-kind', source_refs=[dict(kind='planned_search',search_id='record-one')])
        pair = context('pair-results', ['result-B', 'result-A-second', 'result-A'])
        other_pair = context('other-pair', ['result-B'])
        p['contexts'] = [selected, planned, other, cross, pair, other_pair]
        s = self.sheet(p)
        self.assertEqual(s['source_record_contexts'], [dict(context=selected, input_pointer='/contexts/0',
                          matched_source_refs=[dict(kind='record', record_id='record-one')])])
        self.assertEqual(s['existing_result_contexts'], [dict(context=pair, input_pointer='/contexts/4',
                          matched_evidence_ids=['result-A-second','result-A'])])
        self.assertEqual(s['existing_result_contexts'][0]['context']['evidence_ids'][0], 'result-B')
        self.assertIn('NOT_NEW_CANDIDATE_APPLICABILITY', s['context_scope'])
        self.assertNotIn('contexts', s['candidate_document']['candidates'][0])
        self.assertNotIn('context_ids', s['candidate_document']['candidates'][0]['evidence'])
        p['evidence'][0].pop('evidence_id'); pair['evidence_ids'][-1] = 'record-one'
        self.assertEqual(self.sheet(p)['existing_result_contexts'][0]['matched_evidence_ids'], ['result-A-second','record-one'])

    def test_whole_protocol_guards_before_filtering(self):
        with patch.object(extraction, 'run', wraps=run) as runs, patch.object(extraction, 'report_flow', wraps=report_flow) as reports:
            self.sheet()
        runs.assert_called_once_with(self.p)
        reports.assert_called_once_with(self.p, include_csv=False)
        for mutate in (lambda p: p['evidence'][1].update(mechanism_basis='invalid'),
                       lambda p: p['reports'][1].update(record_ids=['missing']),
                       lambda p: p['report_sources'][2].update(document_sha256='bad'),
                       lambda p: p.update(contexts=[context('unrelated-invalid', ['missing'])])):
            p = minimal(); mutate(p)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): self.sheet(p)

    def test_human_reviews_unchanged_and_no_renewal(self):
        before = copy.deepcopy(self.p)
        flow = report_flow(self.p, include_csv=False)
        self.sheet()
        self.assertEqual(self.p, before)
        self.assertEqual(report_flow(self.p, include_csv=False), flow)
        for key in ('report_reviews', 'report_study_inventory_reviews'):
            self.assertEqual(self.p[key], before[key])

    def test_full_protocol_and_implementation_fingerprints(self):
        s = self.sheet()
        self.assertEqual(s['protocol_sha256'], hashlib.sha256(canonical_json_bytes(self.p)).hexdigest())
        hashes = dict(engine_hashes())
        for name in ('result_extraction.py', 'result_intake.py'):
            hashes[name] = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        self.assertEqual(s['engine_sha256'], hashes)
        p = copy.deepcopy(self.p); p['question'] += ' Fictional changed question.'
        self.assertNotEqual(self.sheet(p)['protocol_sha256'], s['protocol_sha256'])

    def test_complete_fictional_candidate_prepare_assemble_and_replay(self):
        c = self.sheet()['candidate_document']; row = c['candidates'][0]
        row['evidence'].update(evidence_id='fictional-new-result', locator='synthetic:manual-location',
            model='Fictional model', intervention='Fictional intervention', comparator='Fictional comparison',
            endpoint='Fictional endpoint', result='Fictional null result, no real measurement.',
            limitations='Fictional software test, not verified reading.', mechanism_basis='unknown')
        row.update(extracted_by='Fictional extractor', extracted_at='2026-11-04',
                   extraction_note='Fictional manual assertion',
                   source_references=[dict(source_id='source-supplement',extraction_locator='Fictional table S1')])
        target = intake.prepare(self.p, c)
        review = target['review_document']
        review.update(receipt_id='fictional-worksheet-import', decision='import_results', reviewer='Fictional reviewer',
                      reviewed_at='2026-11-04', rationale='Fictional explicit import')
        record = intake.assemble(self.p, c, review)
        self.assertTrue(intake.verify(self.p, record)['valid'])
        self.assertEqual(record['protocol_candidate']['evidence'], self.p['evidence']+[row['evidence']])
        after = self.sheet(record['protocol_candidate'])
        self.assertEqual(after['counts']['existing_pair_results'], 3)
        self.assertIsNone(after['candidate_document']['candidates'][0]['evidence']['evidence_id'])

    def test_validated_csv_provenance_is_included_and_tampering_rejected(self):
        import bibliographic_intake
        import bibliographic_review
        p = json.loads((ROOT/'examples/bibliographic-base.json').read_text(encoding='utf-8'))
        raw = b'record_id,source_locator\nfictional-input,synthetic:local-export\n'
        artifact = bibliographic_intake.prepare(p, raw, 'local-primary', '2026-11-04T00:00:00Z')
        choices = bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record',record_id='record-one',rationale='Fictional identity')
        review = bibliographic_review.prepare_review(p,artifact,choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional import',decision='import_for_screening')
        p = bibliographic_review.assemble(p,artifact,review)['protocol_candidate']
        p['screening'] = [dict(record_id='record-one',decision='include',reason='Fictional inclusion')]
        p['reports'] = [dict(report_id='report-one',record_ids=['record-one'],retrieval='retrieved',decision='include',study_id='study-A',locator='synthetic:report')]
        s = self.sheet(p)
        rows = s['selected_record_target']['source_basis']['bibliographic_rows']
        self.assertEqual(len(rows), 1)
        self.assertIn('/bibliographic_imports/', rows[0]['source_pointer'])
        self.assertIn('original_values', rows[0])
        self.assertTrue(s['source_contexts'])
        p['bibliographic_imports']['imports'][0]['intake']['parsed_export']['record_rows'][0]['source_locator'] = 'tampered'
        with self.assertRaises(ValueError): self.sheet(p)

    def test_no_external_actions_or_source_document_reading(self):
        p = minimal(); p['report_sources'][0]['source_locator'] = 'https://invalid.example/no-fetch'
        original = Path.read_bytes
        def guarded_read(path):
            self.assertEqual(path.parent, ROOT)
            self.assertEqual(path.suffix, '.py')
            return original(path)
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')), \
             patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch('subprocess.run', side_effect=AssertionError('subprocess forbidden')), \
             patch.object(Path, 'read_bytes', guarded_read):
            s = self.sheet(p)
        self.assertEqual(s['external_calls'], 0)

    def test_api_bounds_strict_json_and_quoted_controls(self):
        self.assertEqual(extraction.MAX_INPUT_BYTES, 50_000_000)
        self.assertEqual(extraction.MAX_OUTPUT_BYTES, 50_000_000)
        for constant in ('MAX_INPUT_BYTES','MAX_OUTPUT_BYTES'):
            with patch.object(extraction, constant, 10), self.assertRaises(ValueError): self.sheet()
        for value in (float('nan'), float('inf'), '\ud800'):
            p = minimal(); p['metadata'] = value
            with self.assertRaises((ValueError, UnicodeError)): self.sheet(p)
        p = minimal(); p['question'] += '\n\x1b[31m\x00 Fictional 결과'
        rendered = extraction.render_text(self.sheet(p))
        self.assertIn('결과', rendered)
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('\x00', rendered)
        with patch.object(extraction,'MAX_OUTPUT_BYTES',10), self.assertRaises(ValueError): extraction.render_text(self.sheet())

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'result_extraction.py'), *map(str,args)],
                              cwd=ROOT, capture_output=True, env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))

    def test_cli_utf8_full_and_candidate_outputs_exclusive_and_immutable(self):
        p = minimal(); p['question'] += ' Fictional 결과\n\x1b[31m'
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); source=d/'protocol.json'; full=d/'sheet.json'; candidate=d/'candidate.json'
            source.write_bytes(canonical_json_bytes(p)); before=source.read_bytes()
            args=[source,'--report-id','report-one','--study-id','study-A','--record-id','record-one']
            result=self.cli(*args)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
            expected=json.loads(result.stdout)
            result=self.cli(*args,'--output',full,'--text')
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
            self.assertNotIn(b'\x1b',result.stdout)
            self.assertIn('결과'.encode(),result.stdout)
            self.assertEqual(json.loads(full.read_bytes()),expected)
            saved=full.read_bytes()
            self.assertNotEqual(self.cli(*args,'--output',full).returncode,0)
            self.assertEqual(full.read_bytes(),saved)
            result=self.cli(*args,'--candidate-output',candidate)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
            self.assertEqual(json.loads(candidate.read_bytes()),expected['candidate_document'])
            saved=candidate.read_bytes()
            self.assertNotEqual(self.cli(*args,'--candidate-output',candidate).returncode,0)
            self.assertEqual(candidate.read_bytes(),saved)
            a,b=d/'a.json',d/'b.json'
            self.assertNotEqual(self.cli(*args,'--output',a,'--candidate-output',b).returncode,0)
            self.assertFalse(a.exists()); self.assertFalse(b.exists())
            self.assertNotEqual(self.cli(*args,'--output',source).returncode,0)
            self.assertEqual(source.read_bytes(),before)
            for option in ('--report-id','--study-id','--record-id'):
                missing=list(args); i=missing.index(option); del missing[i:i+2]
                self.assertNotEqual(self.cli(*missing).returncode,0)

    def test_cli_strict_json_and_encoding_fail_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); source=d/'bad.json'; output=d/'out.json'
            for raw in (b'{"question":1,"question":2}', b'{"question":NaN}', b'\xff', b'{"question":"\\ud800"}', b'{} trailing'):
                source.write_bytes(raw)
                result=self.cli(source,'--report-id','report-one','--study-id','study-A','--record-id','record-one','--output',output)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(output.exists())

    def test_cli_size_bounds_checked_before_creating_file(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); source=d/'protocol.json'; output=d/'out.json'
            source.write_bytes(canonical_json_bytes(self.p))
            args=['result_extraction.py',str(source),'--report-id','report-one','--study-id','study-A','--record-id','record-one','--output',str(output)]
            for constant in ('MAX_INPUT_BYTES','MAX_OUTPUT_BYTES'):
                with patch.object(extraction,constant,10), patch.object(sys,'argv',args), \
                     patch.object(extraction,'configure_utf8_stdio'), patch('sys.stderr',new_callable=io.StringIO), self.assertRaises(SystemExit):
                    extraction.main()
                self.assertFalse(output.exists())

    def test_cli_pretty_encoding_and_text_expansion_bounded_before_file(self):
        # A valid compact worksheet can grow during pretty JSON or quoted text
        # rendering. These final encodings must also be checked before open('x').
        sheet = self.sheet()
        compact_size = len(canonical_json_bytes(sheet))
        pretty_size = len(extraction._encode(sheet).encode('utf-8'))
        self.assertGreater(pretty_size, compact_size)
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); source=d/'protocol.json'; output=d/'out.json'
            source.write_bytes(canonical_json_bytes(self.p))
            for flags in ([], ['--text'], ['--candidate-output', str(output)]):
                args=['result_extraction.py',str(source),'--report-id','report-one',
                      '--study-id','study-A','--record-id','record-one']
                args += flags if '--candidate-output' in flags else flags+['--output', str(output)]
                with patch.object(extraction,'MAX_OUTPUT_BYTES',compact_size), \
                     patch.object(extraction,'worksheet',return_value=sheet), \
                     patch.object(extraction,'configure_utf8_stdio'), patch.object(sys,'argv',args), \
                     patch('sys.stderr',new_callable=io.StringIO), self.assertRaises(SystemExit):
                    extraction.main()
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
