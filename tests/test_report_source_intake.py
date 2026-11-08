"""Synthetic reviewed source declaration append tests, not source authentication."""
import copy
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import report_source_intake as intake
from json_io import canonical_json_bytes
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


class ReportSourceIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('report-study-inventory-reviews.json')
        self.c = fixture('manual-source-declarations.json')

    def review(self, p=None, c=None):
        doc = intake.prepare(self.p if p is None else p, self.c if c is None else c)['review_document']
        doc.update(receipt_id='fictional-source-import', decision='append_source_declarations',
                   reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                   rationale='Synthetic separate catalog review, not document verification.')
        return doc

    def application(self, p=None, c=None):
        p = self.p if p is None else p
        c = self.c if c is None else c
        return intake.assemble(p, c, self.review(p, c))

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'report_source_intake.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=60,
                              env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def files(self, root):
        p, c, r = root / 'input = protocol.json', root / 'candidate = declarations.json', root / 'review.json'
        for path, value in [(p, self.p), (c, self.c), (r, self.review())]:
            path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return p, c, r

    def test_blank_template_fills_only_explicit_report_id(self):
        before = copy.deepcopy(self.p)
        result = intake.template(self.p, 'report-three')
        row = result['candidate_document']['candidates'][0]
        self.assertEqual(row['source']['report_id'], 'report-three')
        self.assertTrue(all(value is None for key, value in row['source'].items() if key != 'report_id'))
        self.assertTrue(all(value is None for key, value in row.items() if key != 'source'))
        with self.assertRaises(ValueError): intake.prepare(self.p, result['candidate_document'])
        self.assertEqual(self.p, before)
        self.assertEqual(result, intake.template(self.p, 'report-three'))
        self.assertEqual(result['document_bytes_verification'], 'NOT_PERFORMED')

    def test_exact_append_and_all_other_fields_unchanged(self):
        self.p['opaque_metadata'] = {'raw': ['β', True, 1, 1.0, None], 'text': '  literal\ntext  '}
        before = canonical_json_bytes(self.p)
        app = self.application(); candidate = app['protocol_candidate']
        self.assertEqual(candidate['report_sources'], self.p['report_sources'] + [row['source'] for row in self.c['candidates']])
        self.assertEqual({k: v for k, v in candidate.items() if k != 'report_sources'},
                         {k: v for k, v in self.p.items() if k != 'report_sources'})
        self.assertEqual(canonical_json_bytes(self.p), before)
        receipt = app['receipt']
        self.assertEqual(receipt['before_flow'], receipt['after_flow'])
        self.assertEqual(receipt['before_report_flow'], receipt['after_report_flow'])
        self.assertEqual(receipt['after_source_summary']['source_declarations'], len(candidate['report_sources']))
        self.assertTrue(intake.verify(self.p, app)['valid'])
        for source in candidate['report_sources']:
            self.assertNotIn('declared_by', source)
        self.assertEqual(receipt['candidate_document'], self.c)

    def test_missing_and_empty_source_stage_supported(self):
        p = fixture('report-intake-base.json')
        # This separate supplied base is already retrieved but has no downstream source assertions.
        p['reports'] = [dict(report_id='rpt', record_ids=['r1'], retrieval='retrieved', decision='pending', locator='synthetic:report')]
        c = copy.deepcopy(self.c); c['candidates'] = c['candidates'][:1]; c['candidates'][0]['source']['report_id'] = 'rpt'
        for present in [False, True]:
            if present: p['report_sources'] = []
            app = self.application(p, c)
            self.assertEqual(app['receipt']['before_source_summary']['stage'], 'SUPPLIED' if present else 'NOT_SUPPLIED')
            self.assertEqual(app['receipt']['after_source_summary']['source_declarations'], 1)
            self.assertTrue(intake.verify(p, app)['valid'])

    def test_retrieved_pending_included_excluded_all_supported_without_decision_change(self):
        for report_id in ['report-one', 'report-two', 'report-three']:
            c = copy.deepcopy(self.c); c['candidates'] = c['candidates'][:1]
            c['candidates'][0]['source']['report_id'] = report_id
            app = self.application(c=c)
            self.assertEqual(app['protocol_candidate']['reports'], self.p['reports'])
            self.assertEqual(app['protocol_candidate']['evidence'], self.p['evidence'])

    def test_unknown_unretrieved_and_nonliteral_selections_fail(self):
        for rid in ['missing', 'report-four', 'report-five', 'report-one ', 'REPORT-ONE', None, True, 3, [], {}]:
            with self.subTest(report_id=rid), self.assertRaises(ValueError): intake.template(self.p, rid)
            c = copy.deepcopy(self.c); c['candidates'][0]['source']['report_id'] = rid
            with self.assertRaises(ValueError): intake.prepare(self.p, c)

    def test_same_locator_digest_new_ids_are_not_merged_or_preferred(self):
        c = copy.deepcopy(self.c); c['candidates'] = c['candidates'][:1]
        c['candidates'][0]['source'] = dict(self.p['report_sources'][0], source_id='literal-new-id')
        app = self.application(c=c)
        self.assertEqual(app['protocol_candidate']['report_sources'][-1], c['candidates'][0]['source'])
        self.assertEqual(len(app['protocol_candidate']['report_sources']), len(self.p['report_sources']) + 1)
        self.assertEqual(app['receipt']['preferred_source_selection'], 'NOT_PERFORMED')
        self.assertEqual(app['receipt']['source_identity'], 'NOT_ESTABLISHED')

    def test_existing_or_batch_duplicate_ids_are_refused_without_upsert(self):
        for report_id in ['report-one', 'report-two']:
            c = copy.deepcopy(self.c)
            c['candidates'][0]['source']['source_id'] = self.p['report_sources'][0]['source_id']
            c['candidates'][0]['source']['report_id'] = report_id
            with self.assertRaises(ValueError): intake.prepare(self.p, c)
        c = copy.deepcopy(self.c); c['candidates'][1]['source']['source_id'] = c['candidates'][0]['source']['source_id']
        with self.assertRaises(ValueError): intake.prepare(self.p, c)
        c = copy.deepcopy(self.c); c['candidates'].append(copy.deepcopy(c['candidates'][0]))
        with self.assertRaises(ValueError): intake.prepare(self.p, c)

    def test_strict_document_candidate_source_and_review_shapes(self):
        for bad in [None, [], True, dict(self.c, schema_version=True), dict(self.c, schema_version=1.0),
                    dict(self.c, schema_version=2), dict(self.c, extra=1), dict(self.c, candidates=[]), dict(self.c, candidates={})]:
            with self.assertRaises(ValueError): intake.prepare(self.p, bad)
        for location in ('candidate', 'source'):
            target = self.c['candidates'][0] if location == 'candidate' else self.c['candidates'][0]['source']
            for field in list(target) + ['unexpected']:
                c = copy.deepcopy(self.c); row = c['candidates'][0] if location == 'candidate' else c['candidates'][0]['source']
                if field == 'unexpected': row[field] = True
                else: del row[field]
                with self.assertRaises(ValueError): intake.prepare(self.p, c)
        for field in list(self.review()) + ['unexpected']:
            review = self.review()
            if field == 'unexpected': review[field] = True
            else: del review[field]
            with self.assertRaises(ValueError): intake.assemble(self.p, self.c, review)

    def test_literal_text_dates_and_declared_digest_strictness(self):
        for key in ['declared_by', 'declared_at', 'declaration_note']:
            for value in [None, True, 1, [], {}, '', ' \n']:
                c = copy.deepcopy(self.c); c['candidates'][0][key] = value
                with self.assertRaises(ValueError): intake.prepare(self.p, c)
        for key in intake.SOURCE_FIELDS - {'document_sha256'}:
            for value in [None, True, 1, [], {}, '', ' \n']:
                c = copy.deepcopy(self.c); c['candidates'][0]['source'][key] = value
                with self.assertRaises(ValueError): intake.prepare(self.p, c)
        for value in [True, 1, '', 'A'*64, 'a'*63, 'a'*65, 'g'*64, [], {}]:
            c = copy.deepcopy(self.c); c['candidates'][0]['source']['document_sha256'] = value
            with self.assertRaises(ValueError): intake.prepare(self.p, c)
        for value in ['2026-02-29', '2026-2-04', '2026-11-04\n', '0000-01-01']:
            c = copy.deepcopy(self.c); c['candidates'][0]['declared_at'] = value
            with self.assertRaises(ValueError): intake.prepare(self.p, c)
        c = copy.deepcopy(self.c); c['candidates'][0]['declared_at'] = '2024-02-29'
        c['candidates'][0]['source']['source_locator'] = '  file:///never-read β\n  '
        app = self.application(c=c)
        self.assertEqual(app['protocol_candidate']['report_sources'][-2], c['candidates'][0]['source'])

    def test_blank_review_is_not_approval_and_invalid_assertions_fail(self):
        prepared = intake.prepare(self.p, self.c); blank = prepared['review_document']
        self.assertTrue(all(v is None for k,v in blank.items() if k not in ('schema_version','target_sha256')))
        with self.assertRaises(ValueError): intake.assemble(self.p, self.c, blank)
        for field in intake.REVIEW_FIELDS - {'schema_version'}:
            for value in [None, True, 3, [], {}, '', ' \n']:
                review = self.review(); review[field] = value
                with self.assertRaises(ValueError): intake.assemble(self.p, self.c, review)
        for field, value in [('schema_version',True),('schema_version',1.0),('decision','approve'),
                             ('reviewed_at','2026-02-29'),('target_sha256','a'*63)]:
            review = self.review(); review[field] = value
            with self.assertRaises(ValueError): intake.assemble(self.p, self.c, review)

    def test_whole_input_candidate_order_and_implementation_bind_review(self):
        review = self.review()
        for mode in ['opaque', 'version', 'order', 'declaration', 'source']:
            p,c = copy.deepcopy(self.p),copy.deepcopy(self.c)
            if mode == 'opaque': p['unrelated'] = True
            if mode == 'version': p['version'] += '-changed'
            if mode == 'order': c['candidates'].reverse()
            if mode == 'declaration': c['candidates'][0]['declaration_note'] += ' changed'
            if mode == 'source': p['report_sources'][0]['document_version'] += ' changed'
            with self.assertRaises(ValueError): intake.assemble(p,c,review)
        with patch.object(intake, 'implementation_hashes', return_value={'changed': 'bytes'}):
            with self.assertRaises(ValueError): intake.assemble(self.p,self.c,review)

    def test_target_retains_before_after_catalogs_pointers_and_raw_source_context(self):
        target = intake.prepare(self.p,self.c)['target']; app = self.application()
        self.assertEqual([r['report_id'] for r in target['selected_report_targets']], ['report-one','report-three'])
        self.assertEqual([r['output_pointer'] for r in target['appended_sources']], ['/report_sources/4','/report_sources/5'])
        for old,new in zip(target['selected_report_targets'],target['candidate_report_targets']):
            self.assertNotEqual(old['source_basis_sha256'],new['source_basis_sha256'])
            self.assertEqual(old['recorded_report'],new['recorded_report'])
        self.assertTrue(target['selected_record_targets'])
        self.assertEqual(target['candidate_document'],self.c)
        self.assertEqual(app['receipt']['target'],target)

    def test_full_replay_rejects_resealed_fields_and_endpoint_changes(self):
        baseline = self.application()
        for field in ['protocol_candidate','receipt','schema_version','kind','extra']:
            app=copy.deepcopy(baseline)
            if field=='protocol_candidate':app[field]['report_sources'][0]['document_version']='changed existing row'
            elif field=='receipt':app[field]['after_source_summary']['document_bytes_verification']='VERIFIED'
            elif field=='schema_version':app[field]=True
            elif field=='kind':app[field]='detached_inventory_intake'
            else:app[field]=True
            app['receipt']['receipt_sha256']=intake.digest({k:v for k,v in app['receipt'].items() if k!='receipt_sha256'})
            with self.assertRaises(ValueError):intake.verify(self.p,app)
        p=copy.deepcopy(self.p);p['opaque']=True
        with self.assertRaises(ValueError):intake.verify(p,baseline)

    def test_entire_protocol_is_validated_mock_and_missing_report_context_rejected(self):
        for field,value in [('reports',None),('reports',[]),('adapter_receipts',[]),('evidence',[{'bad':True}])]:
            p=copy.deepcopy(self.p);p[field]=value
            with self.assertRaises((ValueError,TypeError,KeyError)):intake.prepare(p,self.c)
        p=copy.deepcopy(self.p);del p['reports']
        with self.assertRaises(ValueError):intake.template(p,'report-one')

    def test_strict_python_json_values_cycles_surrogates_and_coercions(self):
        class ListLike(list):pass
        class TextLike(str):pass
        cycle=[];cycle.append(cycle)
        for value in [float('nan'),float('inf'),(1,2),{1:'bad'},ListLike([1]),TextLike('str'),'\ud800',cycle]:
            p=copy.deepcopy(self.p);p['opaque']=value
            with self.assertRaises((ValueError,RecursionError)):intake.prepare(p,self.c)
        shared=['valid'];p=copy.deepcopy(self.p);p['opaque']=[shared,shared]
        self.assertTrue(intake.verify(p,self.application(p=p))['valid'])

    def test_count_and_byte_boundaries(self):
        c=copy.deepcopy(self.c);c['candidates']=[]
        for i in range(100):
            row=copy.deepcopy(self.c['candidates'][0]);row['source']['source_id']='source-%d'%i;c['candidates'].append(row)
        self.assertEqual(len(self.application(c=c)['protocol_candidate']['report_sources']),104)
        c['candidates'].append(copy.deepcopy(c['candidates'][0]))
        with self.assertRaises(ValueError):intake.prepare(self.p,c)
        size=len(canonical_json_bytes(self.c))
        with patch.object(intake,'MAX_CANDIDATE_BYTES',size):intake.prepare(self.p,self.c)
        with patch.object(intake,'MAX_CANDIDATE_BYTES',size-1):
            with self.assertRaises(ValueError):intake.prepare(self.p,self.c)
        with patch.object(intake,'MAX_PROTOCOL_BYTES',1):
            with self.assertRaises(ValueError):intake.template(self.p,'report-one')
        with patch.object(intake,'MAX_APPLICATION_BYTES',1):
            with self.assertRaises(ValueError):self.application()

    def test_no_source_reads_network_or_claim_escalation(self):
        c=copy.deepcopy(self.c);c['candidates'][0]['source']['source_locator']='file:///never/open/this'
        with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            app=self.application(c=c);checked=intake.verify(self.p,app)
        for value in [app['receipt'],checked,intake.template(self.p,'report-one')]:
            for key in ['document_bytes_verification','existing_review_renewal','preferred_source_selection','downstream_reassessment']:
                self.assertEqual(value[key],'NOT_PERFORMED')
            self.assertEqual(value['external_calls'],0);self.assertEqual(value['conclusion_readiness'],'NOT_READY')
            self.assertEqual(value['census_claim'],'NOT_ESTABLISHED')
        self.assertIn('report_source_intake.py',intake.implementation_hashes())
        self.assertNotIn('report_source_intake.py',research_bundle.ENGINE_FILES)

    def test_cli_all_commands_unicode_spaces_and_research_snapshot(self):
        with tempfile.TemporaryDirectory(prefix='sensei source cli ') as temp:
            root=Path(temp);p,c,r=self.files(root);draft=root/'draft.json';target=root/'target.json';app=root/'application.json';final=root/'final.json'
            for args in [('template',p,'--report-id','report-three','--candidate-output',draft),
                         ('target',p,c,'--output',target),('assemble',p,c,r,'--output',app),
                         ('verify',p,app,'--protocol-output',final,'--text')]:
                result=self.invoke(*args);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(final.read_bytes()),self.application()['protocol_candidate'])
            self.assertIn(b'NOT_READY',result.stdout)
            archive=root/'research.zip';archive.write_bytes(research_bundle.build_bundle(final.read_bytes()))
            self.assertTrue(research_bundle.verify(archive)['valid'])

    def test_cli_invalid_input_refuses_partial_output_or_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,c,r=self.files(root);out=root/'out.json'
            for raw in [b'\xff',b'null',b'{"x":1,"x":1}',b'{"x":NaN}',b'{"x":"\\ud800"}']:
                c.write_bytes(raw);result=self.invoke('target',p,c,'--output',out)
                self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists());self.assertNotIn(b'Traceback',result.stderr)

    def test_existing_outputs_directories_dangling_links_and_inspection_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,c,r=self.files(root);out=root/'existing';out.write_bytes(b'keep')
            for destination in [out,root]:
                result=self.invoke('assemble',p,c,r,'--output',destination);self.assertNotEqual(result.returncode,0)
            self.assertEqual(out.read_bytes(),b'keep')
            link=root/'dangling';target=root/'missing'
            try:link.symlink_to(target)
            except (OSError,NotImplementedError):pass
            else:
                self.assertNotEqual(self.invoke('assemble',p,c,r,'--output',link).returncode,0)
                self.assertTrue(link.is_symlink());self.assertFalse(target.exists())
            with patch.object(Path,'lstat',side_effect=PermissionError('inspection denied')),patch.object(Path,'open') as opened:
                with self.assertRaises(OSError):intake._write_new(out,b'bad')
                opened.assert_not_called()

    def test_render_encoding_and_output_size_fail_before_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p,c,r=self.files(root);out=root/'out.json'
            argv=['report_source_intake.py','assemble',str(p),str(c),str(r),'--output',str(out),'--text']
            for render in [lambda _: '\ud800',lambda _: (_ for _ in ()).throw(ValueError('render failure'))]:
                with patch.object(sys,'argv',argv),patch.object(intake,'configure_utf8_stdio'),patch.object(sys,'stdout',io.StringIO()),patch.object(sys,'stderr',io.StringIO()),patch.object(intake,'render_text',side_effect=render):
                    with self.assertRaises(SystemExit):intake.main()
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
