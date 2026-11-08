"""Independent, fictional manual-result append/replay boundary tests."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import result_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


def base():
    return json.loads((ROOT / 'examples/report-study-inventory-reviews.json').read_text(encoding='utf-8'))


def candidates():
    return {'schema_version': 1, 'candidates': [{
        'report_id': 'report-one',
        'evidence': dict(evidence_id='result-C', record_id='record-one', study_id='study-C',
                         locator='fictional:result-C', model='Fictional system C',
                         intervention='Fictional intervention', comparator='Fictional reference',
                         endpoint='Fictional endpoint', result='Fictional positive finding, not a real measurement.',
                         limitations='Fictional example only; no source reading established.', mechanism_basis='unknown'),
        'source_references': [dict(source_id='source-main', extraction_locator='Fictional section 3')],
        'extracted_by': 'Fictional extractor', 'extracted_at': '2026-11-04',
        'extraction_note': 'Supplied manual assertion, not verified source content.'}]}


class ResultIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p, self.c = base(), candidates()

    def review(self, p=None, c=None):
        doc = copy.deepcopy(intake.prepare(self.p if p is None else p, self.c if c is None else c)['review_document'])
        doc.update(receipt_id='fictional-receipt', reviewer='Fictional reviewer',
                             reviewed_at='2026-11-04', rationale='Fictional explicit result import.',
                             decision='import_results')
        return doc

    def assembled(self, p=None, c=None):
        p = self.p if p is None else p
        c = self.c if c is None else c
        return intake.assemble(p, c, self.review(p, c))

    def reject_candidate(self, document):
        with self.assertRaises((ValueError, TypeError)):
            intake.prepare(self.p, document)

    def test_prepare_is_deterministic_and_never_invents_review(self):
        old_p, old_c = copy.deepcopy(self.p), copy.deepcopy(self.c)
        prepared = intake.prepare(self.p, self.c)
        self.assertEqual(prepared, intake.prepare(self.p, self.c))
        doc = prepared['review_document']
        self.assertEqual(doc['schema_version'], 1)
        self.assertEqual(set(doc), {'schema_version', 'target_sha256', 'receipt_id', 'decision', 'reviewer', 'reviewed_at', 'rationale'})
        self.assertEqual(len(doc['target_sha256']), 64)
        self.assertTrue(all(v is None for k, v in doc.items() if k not in ('schema_version', 'target_sha256')))
        with self.assertRaises(ValueError): intake.assemble(self.p, self.c, doc)
        self.assertEqual((self.p, self.c), (old_p, old_c))

    def test_append_only_exact_order_detached_record_and_replay(self):
        before = canonical_json_bytes(self.p)
        second = copy.deepcopy(self.c['candidates'][0])
        second['evidence'].update(evidence_id='result-C-null', result='Fictional null finding; no real measurement.')
        self.c['candidates'].append(second)
        record = self.assembled()
        self.assertEqual(set(record), {'schema_version', 'kind', 'receipt', 'protocol_candidate'})
        self.assertEqual(record['kind'], 'detached_result_intake')
        new = record['protocol_candidate']
        self.assertEqual(new['evidence'], self.p['evidence'] + [c['evidence'] for c in self.c['candidates']])
        self.assertEqual({k: v for k, v in new.items() if k != 'evidence'}, {k: v for k, v in self.p.items() if k != 'evidence'})
        self.assertEqual(canonical_json_bytes(new['evidence'][:2]), canonical_json_bytes(self.p['evidence']))
        self.assertEqual(canonical_json_bytes(self.p), before)
        self.assertTrue(intake.verify(self.p, record)['valid'])
        run(new); report_flow(new)
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / 'fictional.zip'
            archive.write_bytes(research_bundle.build_bundle(canonical_json_bytes(new)))
            self.assertTrue(research_bundle.verify(archive)['valid'])
        # Detached evidence-source associations must not leak into the protocol.
        self.assertNotIn('source_references', new['evidence'][-1])
        self.assertNotIn('result_imports', new)

    def test_strict_document_and_candidate_shapes(self):
        for bad in (None, [], True, {'schema_version': True, 'candidates': self.c['candidates']},
                    dict(self.c, extra=1), dict(self.c, schema_version=2), dict(self.c, candidates=[]),
                    dict(self.c, candidates=self.c['candidates'] * 101), dict(self.c, candidates={})):
            with self.subTest(bad=repr(bad)[:100]): self.reject_candidate(bad)
        row = self.c['candidates'][0]
        for field in row:
            c = copy.deepcopy(self.c); del c['candidates'][0][field]
            with self.subTest(missing=field): self.reject_candidate(c)
        for location in ('candidate', 'evidence', 'source'):
            c = copy.deepcopy(self.c); r = c['candidates'][0]
            target = r if location == 'candidate' else r['evidence'] if location == 'evidence' else r['source_references'][0]
            target['unexpected'] = 'not allowed'
            with self.subTest(location=location): self.reject_candidate(c)

    def test_nonblank_literal_fields_real_dates_and_mechanism_enum(self):
        for field in self.c['candidates'][0]['evidence']:
            for bad in (None, True, 1, [], {}, '', ' \t\n'):
                c = copy.deepcopy(self.c); c['candidates'][0]['evidence'][field] = bad
                with self.subTest(field=field, bad=bad): self.reject_candidate(c)
        for field in ('report_id', 'extracted_by', 'extracted_at', 'extraction_note'):
            for bad in (None, True, 2, [], {}, '', ' '):
                c = copy.deepcopy(self.c); c['candidates'][0][field] = bad
                with self.subTest(field=field, bad=bad): self.reject_candidate(c)
        for date in ('2026-02-29', '2026-2-04', '2026-11-04\n', '0000-01-01'):
            c = copy.deepcopy(self.c); c['candidates'][0]['extracted_at'] = date
            self.reject_candidate(c)
        for mechanism in ('Unknown', ' intervention', 'causal'):
            c = copy.deepcopy(self.c); c['candidates'][0]['evidence']['mechanism_basis'] = mechanism
            self.reject_candidate(c)
        for mechanism in ('association', 'intervention', 'unknown'):
            c = copy.deepcopy(self.c); c['candidates'][0]['evidence']['mechanism_basis'] = mechanism
            c['candidates'][0]['extracted_at'] = '2024-02-29'
            intake.prepare(self.p, c)

    def test_literal_values_preserved_and_upper_candidate_boundary(self):
        c = copy.deepcopy(self.c)
        c['candidates'][0]['evidence']['result'] = '  Fictional literal result\nwith supplied whitespace.  '
        c['candidates'][0]['extraction_note'] = '  Fictional literal note  '
        c['candidates'][0]['source_references'][0]['extraction_locator'] = '  section 3  '
        record = self.assembled(c=c)
        self.assertEqual(record['protocol_candidate']['evidence'][-1]['result'], c['candidates'][0]['evidence']['result'])
        self.assertEqual(record['receipt']['candidate_document'], c)
        for field in ('report_id', 'record_id', 'study_id'):
            bad = copy.deepcopy(c)
            row = bad['candidates'][0] if field == 'report_id' else bad['candidates'][0]['evidence']
            row[field] += ' '
            with self.subTest(field=field): self.reject_candidate(bad)
        c['candidates'] = [copy.deepcopy(c['candidates'][0]) for _ in range(100)]
        for i, row in enumerate(c['candidates']): row['evidence']['evidence_id'] = 'fictional-result-%03d' % i
        self.assertEqual(len(self.assembled(c=c)['protocol_candidate']['evidence']), 102)

    def test_sources_nonempty_unique_known_same_report(self):
        ref = self.c['candidates'][0]['source_references'][0]
        for refs in (None, [], {}, 'source-main', [ref, ref], [dict(ref, source_id='missing')],
                     [dict(ref, source_id='source-unbound')], [dict(ref, extraction_locator=' ')],
                     [dict(source_id='source-main')]):
            c = copy.deepcopy(self.c); c['candidates'][0]['source_references'] = refs
            with self.subTest(refs=refs): self.reject_candidate(c)

    def test_report_record_study_and_eligibility_bindings(self):
        for field, value in [('report_id', 'missing'), ('report_id', 'report-two'), ('report_id', 'report-three'),
                             ('report_id', 'report-four'), ('report_id', 'report-five'),
                             ('record_id', 'record-two'), ('record_id', 'missing'), ('study_id', 'undeclared')]:
            c = copy.deepcopy(self.c)
            target = c['candidates'][0] if field == 'report_id' else c['candidates'][0]['evidence']
            target[field] = value
            with self.subTest(field=field, value=value): self.reject_candidate(c)
        for field, value in [('retrieval', 'pending'), ('decision', 'exclude')]:
            p = copy.deepcopy(self.p); p['reports'][0][field] = value
            with self.assertRaises(ValueError): intake.prepare(p, self.c)

    def test_duplicate_and_implicit_id_collisions(self):
        for eid in ('result-A', 'result-B'):
            c = copy.deepcopy(self.c); c['candidates'][0]['evidence']['evidence_id'] = eid
            self.reject_candidate(c)
        c = copy.deepcopy(self.c); c['candidates'].append(copy.deepcopy(c['candidates'][0]))
        self.reject_candidate(c)
        # Retain valid implicit-ID old row while removing references to its former explicit ID.
        p = copy.deepcopy(self.p); p['gaps'] = []; p['evidence'][0].pop('evidence_id')
        for key in list(p):
            if key not in ('question','version','inclusion_criteria','exclusion_criteria','search_plan','searches','screening','reports','evidence','gaps','report_sources'):
                del p[key]
        run(p); report_flow(p)
        c = copy.deepcopy(self.c); c['candidates'][0]['evidence']['evidence_id'] = 'record-one'
        with self.assertRaises(ValueError): intake.prepare(p, c)

    def test_scalar_report_membership_and_original_validation(self):
        p = copy.deepcopy(self.p)
        p['reports'][0].pop('study_ids'); p['reports'][0]['study_id'] = 'study-A'
        p['evidence'] = [p['evidence'][0]]; p['gaps'] = []
        for key in list(p):
            if key not in ('question','version','inclusion_criteria','exclusion_criteria','search_plan','searches','screening','reports','evidence','gaps','report_sources'): del p[key]
        c = copy.deepcopy(self.c); c['candidates'][0]['evidence']['study_id'] = 'study-A'
        record = self.assembled(p, c)
        self.assertTrue(intake.verify(p, record)['valid'])
        c['candidates'][0]['evidence']['study_id'] = 'study-C'
        with self.assertRaises(ValueError): intake.prepare(p, c)
        p['reports'][1]['study_id'] = 'undeclared-but-old-evidence'
        p['reports'][0]['study_id'] = 'wrong-existing-membership'
        with self.assertRaises(ValueError): intake.prepare(p, c)
        for key, value in [('adapter_receipts', {}), ('screening', []), ('evidence', [None])]:
            bad = copy.deepcopy(self.p); bad[key] = value
            with self.assertRaises((ValueError, TypeError)): intake.prepare(bad, self.c)

    def test_stale_full_input_and_candidates_require_new_review(self):
        review = self.review()
        for mutate in (lambda p: p.update(question=p['question']+' unrelated edit'),
                       lambda p: p.update(extra_metadata={'operator': 'fictional'}),
                       lambda p: p['report_sources'][1].update(document_version='new supplement'),
                       lambda p: p['searches'][0].update(searched_at='new supplied date')):
            p = copy.deepcopy(self.p); mutate(p)
            with self.assertRaises(ValueError): intake.assemble(p, self.c, review)
        for field in ('extraction_note', 'extracted_by'):
            c = copy.deepcopy(self.c); c['candidates'][0][field] += ' changed'
            with self.assertRaises(ValueError): intake.assemble(self.p, c, review)

    def test_exact_review_schema_dates_and_decisions(self):
        review = self.review()
        for field in review:
            for bad in (None, True, 2, [], {}, '', ' '):
                doc = copy.deepcopy(review); doc[field] = bad
                with self.subTest(field=field,bad=bad), self.assertRaises((ValueError,TypeError)):
                    intake.assemble(self.p,self.c,doc)
            doc = copy.deepcopy(review); del doc[field]
            with self.assertRaises(ValueError): intake.assemble(self.p,self.c,doc)
        for field,value in [('decision','approve'),('decision','import_results '),('reviewed_at','2026-02-29'),('reviewed_at','2026-11-04\n')]:
            doc=copy.deepcopy(review);doc[field]=value
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,doc)
        for doc in (dict(review,extra=True),dict(review,schema_version=True)):
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,doc)

    def test_tampering_and_changed_original_reject_but_new_valid_assertions_are_not_authentication(self):
        record=self.assembled()
        changes=[lambda r:r.update(extra=True),lambda r:r.update(schema_version=True),
                 lambda r:r.update(kind='authenticated'),lambda r:r['protocol_candidate'].update(version='changed'),
                 lambda r:r['protocol_candidate']['evidence'][-1].update(result='altered after review'),
                 lambda r:r['receipt'].update(extra='forged')]
        for mutate in changes:
            changed=copy.deepcopy(record);mutate(changed)
            with self.assertRaises(ValueError):intake.verify(self.p,changed)
        changed=copy.deepcopy(self.p);changed['question']+=' edit'
        with self.assertRaises(ValueError):intake.verify(changed,record)
        c=copy.deepcopy(self.c);c['candidates'][0]['evidence']['result']='Alternative fictional null assertion.'
        alternative=self.assembled(c=c)
        self.assertTrue(intake.verify(self.p,alternative)['valid'])
        self.assertNotEqual(alternative,record)

    def test_no_source_opening_or_external_actions(self):
        self.p['report_sources'][0]['source_locator']='https://invalid.example/do-not-fetch'
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')), patch('socket.socket',side_effect=AssertionError('network forbidden')), patch('subprocess.run',side_effect=AssertionError('external process forbidden')):
            prepared=intake.prepare(self.p,self.c)
            record=self.assembled()
            self.assertTrue(intake.verify(self.p,record)['valid'])
        for result in (prepared,record,intake.verify(self.p,record)):
            text=intake.render_text(result)
            self.assertIsInstance(text,str)
            self.assertNotIn('SOURCE_AUTHENTICATED',text)

    def test_engine_binding_receipt_fields_and_resealed_tampering(self):
        record = self.assembled()
        self.assertIn('result_intake.py', record['receipt']['engine_sha256'])
        with patch.object(intake, '_implementation_hashes', return_value={'result_intake.py': '0'*64}):
            with self.assertRaises(ValueError): intake.verify(self.p, record)
            with self.assertRaises(ValueError): intake.assemble(self.p, self.c, record['receipt']['assertion'])
        # A digest is not a signature: changing derived fields and merely resealing
        # their hashes does not establish deterministic replay.
        for field, value in [('before_flow', {}), ('after_flow', {}),
                             ('source_authenticity', 'VERIFIED'), ('reading', 'ESTABLISHED'),
                             ('external_calls', True), ('receipt_id', 'changed'),
                             ('protocol_candidate_sha256', '0'*64)]:
            changed = copy.deepcopy(record)
            changed['receipt'][field] = value
            changed['receipt']['receipt_sha256'] = intake.digest({k:v for k,v in changed['receipt'].items() if k != 'receipt_sha256'})
            with self.subTest(field=field), self.assertRaises(ValueError): intake.verify(self.p, changed)
        changed = copy.deepcopy(record)
        changed['receipt']['target']['selected_sources'][0]['extraction_locator'] = 'altered assertion'
        changed['receipt']['target']['target_sha256'] = intake.digest({k:v for k,v in changed['receipt']['target'].items() if k != 'target_sha256'})
        changed['receipt']['assertion']['target_sha256'] = changed['receipt']['target']['target_sha256']
        changed['receipt']['receipt_sha256'] = intake.digest({k:v for k,v in changed['receipt'].items() if k != 'receipt_sha256'})
        with self.assertRaises(ValueError): intake.verify(self.p, changed)
        # Conversely, fully consistent re-authored assertions still replay. They
        # are not authenticated history or proof anyone executed this earlier.
        doc = self.review(); doc.update(reviewer='Different fictional reviewer', receipt_id='different-receipt')
        alternate = intake.assemble(self.p, self.c, doc)
        self.assertTrue(intake.verify(self.p, alternate)['valid'])
        self.assertIn('unsigned', alternate['receipt']['boundary'])

    def test_entire_original_and_appended_candidate_run_both_guards(self):
        with patch.object(intake, 'run', wraps=run) as runs, patch.object(intake, 'report_flow', wraps=report_flow) as reports:
            intake.prepare(self.p, self.c)
        self.assertEqual(runs.call_count, 2)
        self.assertEqual(reports.call_count, 2)
        self.assertEqual(runs.call_args_list[0].args[0], self.p)
        self.assertEqual(runs.call_args_list[1].args[0]['evidence'], self.p['evidence']+[self.c['candidates'][0]['evidence']])

    def test_size_caps_and_strict_json_values(self):
        self.assertEqual(intake.MAX_CANDIDATE_BYTES, 10_000_000)
        self.assertEqual(intake.MAX_PROTOCOL_BYTES, 50_000_000)
        self.assertEqual(intake.MAX_APPLICATION_BYTES, 50_000_000)
        record = self.assembled()
        for constant, action in [('MAX_CANDIDATE_BYTES', lambda: intake.prepare(self.p,self.c)),
                                 ('MAX_PROTOCOL_BYTES', lambda: intake.prepare(self.p,self.c)),
                                 ('MAX_APPLICATION_BYTES', lambda: intake.verify(self.p,record))]:
            with self.subTest(constant=constant), patch.object(intake, constant, 10), self.assertRaises(ValueError): action()
        for bad in (float('nan'),float('inf')):
            p=copy.deepcopy(self.p);p['uninterpreted_metadata']=bad
            with self.assertRaises(ValueError):intake.prepare(p,self.c)

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'result_intake.py'),*map(str,args)],cwd=ROOT,capture_output=True,
            env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))

    def test_cli_roundtrip_utf8_exclusive_files_and_no_partial_failure(self):
        self.c['candidates'][0]['evidence']['result']='Fictional 합성 result\n\x1b[31mnot terminal control'
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'protocol.json';c=d/'candidates.json';r=d/'review.json';out=d/'record.json';target=d/'target.json';derived=d/'derived.json'
            p.write_bytes(canonical_json_bytes(self.p));c.write_bytes(canonical_json_bytes(self.c))
            result=self.cli('target',p,c,'--output',target)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
            prepared=json.loads(target.read_text(encoding='utf-8'))
            self.assertIn('review_document',prepared)
            r.write_bytes(canonical_json_bytes(self.review()))
            result=self.cli('assemble',p,c,r,'--output',out,'--text')
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
            self.assertNotIn(b'\x1b',result.stdout)
            before=out.read_bytes()
            self.assertNotEqual(self.cli('assemble',p,c,r,'--output',out).returncode,0)
            self.assertEqual(out.read_bytes(),before)
            verified=self.cli('verify',p,out,'--protocol-output',derived)
            self.assertEqual(verified.returncode,0,verified.stderr.decode('utf-8'))
            self.assertEqual(json.loads(derived.read_text(encoding='utf-8')),json.loads(before)['protocol_candidate'])
            before_derived=derived.read_bytes()
            self.assertNotEqual(self.cli('verify',p,out,'--protocol-output',derived).returncode,0)
            self.assertEqual(derived.read_bytes(),before_derived)
            c.write_text('{"schema_version":1,"schema_version":1,"candidates":[]}',encoding='utf-8')
            badout=d/'bad.json'
            self.assertNotEqual(self.cli('target',p,c,'--output',badout).returncode,0)
            self.assertFalse(badout.exists())

    def test_csv_import_screening_report_source_result_replay_bundle(self):
        import bibliographic_intake
        import bibliographic_review
        p=json.loads((ROOT/'examples/bibliographic-base.json').read_text(encoding='utf-8'))
        raw=b'record_id,source_locator\nfictional-input,synthetic:local-export\n'
        artifact=bibliographic_intake.prepare(p,raw,'local-primary','2026-11-04T00:00:00Z')
        choices=bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record',record_id='record-one',rationale='Fictional identity assertion')
        review=bibliographic_review.prepare_review(p,artifact,choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional collection',decision='import_for_screening')
        p=bibliographic_review.assemble(p,artifact,review)['protocol_candidate']
        p['screening']=[dict(record_id='record-one',decision='include',reason='Fictional screening')]
        p['reports']=[dict(report_id='report-one',record_ids=['record-one'],retrieval='retrieved',decision='include',study_id='study-C',locator='synthetic:report')]
        p['report_sources']=[dict(source_id='source-main',report_id='report-one',source_locator='synthetic:source',document_version='Fictional v1',document_sha256=None)]
        before=canonical_json_bytes(p['bibliographic_imports'])
        record=self.assembled(p=p)
        self.assertEqual(canonical_json_bytes(record['protocol_candidate']['bibliographic_imports']),before)
        self.assertTrue(intake.verify(p,record)['valid'])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bundle.zip';path.write_bytes(research_bundle.build_bundle(canonical_json_bytes(record['protocol_candidate'])))
            self.assertTrue(research_bundle.verify(path)['valid'])


if __name__ == '__main__':
    unittest.main()
