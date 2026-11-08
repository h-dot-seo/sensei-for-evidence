"""Synthetic descriptive inventory append, exact replay and output boundaries."""
import copy
import hashlib
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

import inventory_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
import research_bundle
import report_decision
import result_extraction
import result_intake

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT/'examples'/name).read_bytes())


def encoded(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


class InventoryIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p=fixture('report-study-inventory.json')
        self.c=fixture('manual-inventory-candidates.json')

    def row(self,p=None,report='report-three',study='candidate-new',identifier='fictional-new',person='Fictional new recorder',sources=None):
        p=self.p if p is None else p
        row=intake.template(p,report,study)['candidate_document']['candidates'][0]
        row.update(inventory_id=identifier,recorded_by=person,recorded_at='2026-11-04',
                   description='Fictional descriptive assertion only.',source_locator='synthetic:section',
                   source_ids=['source-candidate'] if sources is None else sources)
        return row

    def review(self,p=None,c=None):
        p=self.p if p is None else p;c=self.c if c is None else c
        r=intake.prepare(p,c)['review_document']
        r.update(receipt_id='fictional-inventory-intake',decision='import_descriptive_inventory',
                 reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional descriptive import only.')
        return r

    def assembled(self,p=None,c=None):
        p=self.p if p is None else p;c=self.c if c is None else c
        return intake.assemble(p,c,self.review(p,c))

    def reject(self,c=None,p=None):
        with self.assertRaises((ValueError,TypeError,UnicodeError)):
            intake.prepare(self.p if p is None else p,self.c if c is None else c)

    def invoke(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'inventory_intake.py'),*map(str,args)],cwd=ROOT,
            capture_output=True,timeout=60,env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))

    def test_template_has_only_explicit_ids_and_source_hash_filled(self):
        original=copy.deepcopy(self.p)
        result=intake.template(self.p,'report-three','candidate-new')
        row=result['candidate_document']['candidates'][0]
        self.assertEqual(row['report_id'],'report-three');self.assertEqual(row['study_id'],'candidate-new')
        self.assertEqual(row['source_basis_sha256'],result['proposed_target']['source_basis_sha256'])
        self.assertTrue(all(value is None for key,value in row.items() if key not in ('report_id','study_id','source_basis_sha256')))
        self.assertFalse(result['proposed_target']['membership_currently_declared'])
        self.assertFalse(result['protocol_changed']);self.assertEqual(self.p,original)
        self.reject(result['candidate_document'])
        self.assertEqual(result,intake.template(self.p,'report-three','candidate-new'))
        for report,study in [('unknown','new'),('report-three',''),('report-three',None),(None,'new'),([], 'new')]:
            with self.subTest(report=report,study=study),self.assertRaises((ValueError,TypeError)):
                intake.template(self.p,report,study)

    def test_template_requires_actual_retrieval_and_existing_descriptors(self):
        for report in ['report-four','report-five']:
            with self.assertRaises(ValueError):intake.template(self.p,report,'candidate-new')
        for sources in [[],[s for s in self.p['report_sources'] if s['report_id']!='report-three']]:
            p=copy.deepcopy(self.p);p['report_sources']=sources
            # Keep other existing assertions valid by removing only fixture inventory for this separate setup.
            p.pop('report_study_inventory');p.pop('report_reviews',None);p.pop('report_study_reviews',None)
            with self.assertRaises(ValueError):intake.template(p,'report-three','new')

    def test_prepare_immutable_deterministic_and_blank_review_cannot_assemble(self):
        old=copy.deepcopy((self.p,self.c));result=intake.prepare(self.p,self.c)
        self.assertEqual(result,intake.prepare(self.p,self.c));self.assertEqual((self.p,self.c),old)
        r=result['review_document'];self.assertEqual(set(r),intake.REVIEW_FIELDS)
        self.assertTrue(all(v is None for k,v in r.items() if k not in ('schema_version','target_sha256')))
        self.assertEqual(r['target_sha256'],result['target']['target_sha256'])
        with self.assertRaises(ValueError):intake.assemble(self.p,self.c,r)
        result['target']['candidate_document']['candidates'][0]['description']='changed copy'
        self.assertEqual((self.p,self.c),old)

    def test_exact_append_prefix_all_other_fields_and_flows_preserved(self):
        self.p['opaque_metadata']={'literal':'  합성\r\n\x1b  ','order':[None,0,0.0,True]}
        old=canonical_json_bytes(self.p);a=self.assembled();p=a['protocol_candidate'];r=a['receipt']
        self.assertEqual(p['report_study_inventory'],self.p['report_study_inventory']+self.c['candidates'])
        self.assertEqual({k:v for k,v in p.items() if k!='report_study_inventory'},
                         {k:v for k,v in self.p.items() if k!='report_study_inventory'})
        self.assertEqual(canonical_json_bytes(self.p),old)
        self.assertEqual(r['before_flow'],r['after_flow']);self.assertEqual(r['before_report_flow'],r['after_report_flow'])
        self.assertEqual(r['before_inventory_summary']['inventory_assertions'],5)
        self.assertEqual(r['after_inventory_summary']['inventory_assertions'],6)
        self.assertEqual(r['after_inventory_summary']['stale_source_assertions'],1)
        self.assertEqual(r['after_inventory_summary']['described_report_study_pairs'],5)
        self.assertEqual(set(a),intake.APPLICATION_FIELDS);self.assertTrue(intake.verify(self.p,a)['valid'])
        self.assertEqual(a['kind'],'detached_inventory_intake')

    def test_absent_and_empty_inventory_stages_preserved_in_receipt(self):
        for present in [False,True]:
            p=copy.deepcopy(self.p);p.pop('report_study_inventory')
            if present:p['report_study_inventory']=[]
            a=self.assembled(p=p)
            self.assertEqual(a['receipt']['before_inventory_summary']['stage'],'SUPPLIED' if present else 'NOT_SUPPLIED')
            self.assertEqual(a['receipt']['before_inventory_summary']['inventory_assertions'],0)
            self.assertEqual(a['receipt']['after_inventory_summary']['inventory_assertions'],1)
            self.assertEqual(a['protocol_candidate']['report_study_inventory'],self.c['candidates'])
        p=copy.deepcopy(self.p);p['report_study_inventory']=None;self.reject(p=p)

    def test_pending_excluded_included_reports_do_not_change_membership_or_results(self):
        for rid,study,sources in [('report-three','new-pending',['source-candidate']),
                                  ('report-two','new-excluded',['source-unbound']),
                                  ('report-one','new-included',['source-main','source-supplement'])]:
            c=dict(schema_version=1,candidates=[self.row(report=rid,study=study,sources=sources)])
            a=self.assembled(c=c);p=a['protocol_candidate']
            self.assertEqual(p['reports'],self.p['reports']);self.assertEqual(p['evidence'],self.p['evidence'])
            self.assertEqual(run(p)['flow'],run(self.p)['flow'])
            self.assertEqual(report_flow(p,include_csv=False)['report_flow'],report_flow(self.p,include_csv=False)['report_flow'])
            self.assertFalse(a['receipt']['target']['selected_candidate_targets'][0]['target']['membership_currently_declared'])

    def test_same_pair_different_recorders_remain_separate_ordered_assertions(self):
        first=self.row(study='candidate-X',identifier='new-description-A',person='Fictional new A')
        second=self.row(study='candidate-X',identifier='new-description-B',person='Fictional new B')
        second['description']='Different fictional wording, not contradiction adjudication.'
        c=dict(schema_version=1,candidates=[second,first]);a=self.assembled(c=c)
        self.assertEqual(a['protocol_candidate']['report_study_inventory'][-2:],[second,first])
        self.assertEqual(a['receipt']['after_inventory_summary']['inventory_assertions'],7)
        self.assertEqual(a['receipt']['after_inventory_summary']['described_report_study_pairs'],4)
        self.assertEqual([r['candidate_index'] for r in a['receipt']['target']['selected_candidate_targets']],[0,1])
        self.assertEqual(a['receipt']['canonical_study_selection'],'NOT_PERFORMED')

    def test_duplicate_ids_or_exact_recorder_tuples_rejected_not_replaced(self):
        row=self.row()
        for rows in [[row,row],[row,dict(row,inventory_id='another')],
                     [dict(row,inventory_id=self.p['report_study_inventory'][0]['inventory_id'])],
                     [dict(row,study_id='candidate-X',recorded_by='Fictional recorder A',
                           source_basis_sha256=intake.template(self.p,'report-three','candidate-X')['proposed_target']['source_basis_sha256'])]]:
            self.reject(dict(schema_version=1,candidates=rows))

    def test_source_selection_is_explicit_exact_same_report_and_never_guessed(self):
        for sources in [None,[],{},'source-candidate',['source-candidate','source-candidate'],['unknown'],['source-main'],[' source-candidate'],[True],['']]:
            c=copy.deepcopy(self.c);c['candidates'][0]['source_ids']=sources;self.reject(c)
        c=dict(schema_version=1,candidates=[self.row(report='report-one',study='new',sources=['source-supplement','source-main'])])
        target=intake.prepare(self.p,c)['target']
        self.assertEqual([s['source']['source_id'] for s in target['selected_sources']],['source-supplement','source-main'])
        for s in target['selected_sources']:
            self.assertEqual(s['source'],self.p['report_sources'][int(s['input_pointer'].split('/')[-1])])

    def test_new_stale_basis_refused_existing_stale_assertion_preserved(self):
        self.assertTrue(any(r['source_basis_sha256']!='' for r in self.p['report_study_inventory']))
        c=copy.deepcopy(self.c);c['candidates'][0]['source_basis_sha256']='0'*64;self.reject(c)
        p=copy.deepcopy(self.p);p['report_sources'][3]['document_version']='changed supplied source version'
        self.reject(p=p)
        fresh=self.row(p=p);a=self.assembled(p,dict(schema_version=1,candidates=[fresh]))
        self.assertEqual(a['protocol_candidate']['report_study_inventory'][:-1],p['report_study_inventory'])
        self.assertEqual(a['receipt']['existing_review_renewal'],'NOT_PERFORMED')

    def test_every_unrelated_original_field_binds_review_even_when_source_basis_stays(self):
        review=self.review()
        for change in [lambda p:p.update(version='changed'),lambda p:p.update(extra='unrelated'),
                       lambda p:p['gaps'].clear()]:
            p=copy.deepcopy(self.p);change(p)
            if p==self.p:continue
            self.assertNotEqual(intake.prepare(p,self.c)['target']['target_sha256'],review['target_sha256'])
            with self.assertRaises(ValueError):intake.assemble(p,self.c,review)

    def test_completed_candidate_changes_and_order_require_fresh_review(self):
        c=copy.deepcopy(self.c);c['candidates'].append(self.row(study='other',identifier='other'))
        review=self.review(c=c)
        for change in [lambda d:d['candidates'].reverse(),lambda d:d['candidates'][0].update(description='Changed'),
                       lambda d:d['candidates'][0].update(source_locator=' different literal locator '),
                       lambda d:d['candidates'][0].update(recorded_by='Different person')]:
            changed=copy.deepcopy(c);change(changed)
            with self.assertRaises(ValueError):intake.assemble(self.p,changed,review)

    def test_candidate_schema_text_dates_and_limits_fail_closed(self):
        for bad in [None,[],True,{},dict(self.c,schema_version=True),dict(self.c,schema_version=1.0),dict(self.c,extra=1),
                    dict(self.c,candidates=[]),dict(self.c,candidates={}),dict(self.c,candidates=self.c['candidates']*101)]:
            with self.assertRaises((ValueError,TypeError)):intake.prepare(self.p,bad)
        for key in self.c['candidates'][0]:
            c=copy.deepcopy(self.c);del c['candidates'][0][key];self.reject(c)
        for key in intake.INVENTORY_FIELDS-{'source_ids'}:
            for bad in [None,True,0,[],{},'', ' \t\n']:
                c=copy.deepcopy(self.c);c['candidates'][0][key]=bad;self.reject(c)
        for date in ['2026-02-29','2026-2-04','2026-11-04\n','0000-01-01']:
            c=copy.deepcopy(self.c);c['candidates'][0]['recorded_at']=date;self.reject(c)
        c=copy.deepcopy(self.c);c['candidates'][0]['recorded_at']='2024-02-29';intake.prepare(self.p,c)
        for key in ['decision','study_ids','result','reviewer','extra']:
            c=copy.deepcopy(self.c);c['candidates'][0][key]='invented';self.reject(c)
        with patch.object(intake,'MAX_CANDIDATES',0):self.reject()

    def test_review_schema_human_fields_and_real_date_required(self):
        review=self.review()
        for key in review:
            bad=dict(review);del bad[key]
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,bad)
        for key in intake.REVIEW_FIELDS-{'schema_version'}:
            for value in [None,True,0,[],{},'', ' \t']:
                bad=dict(review);bad[key]=value
                with self.assertRaises(ValueError):intake.assemble(self.p,self.c,bad)
        for changes in [dict(schema_version=True),dict(schema_version=1.0),dict(decision='include'),
                        dict(target_sha256='0'*64),dict(extra='x'),dict(reviewed_at='2026-02-29')]:
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,dict(review,**changes))

    def test_exact_replay_rejects_tampering_extra_keys_and_resealed_checksums(self):
        a=self.assembled()
        changes=[lambda a:a.update(schema_version=True),lambda a:a.update(kind='detached_result_intake'),
                 lambda a:a.update(extra='x'),lambda a:a['receipt'].update(extra=True),
                 lambda a:a['receipt']['target']['selected_sources'][0]['source'].update(locator='forged'),
                 lambda a:a['receipt']['after_inventory_summary'].update(inventory_assertions=99),
                 lambda a:a['receipt']['candidate_document']['candidates'][0].update(description='forged'),
                 lambda a:a['protocol_candidate']['report_study_inventory'][-1].update(description='forged'),
                 lambda a:a['receipt'].update(census_claim='ESTABLISHED'),
                 lambda a:a['receipt']['engine_sha256'].update({'inventory_intake.py':'0'*64})]
        for mutate in changes:
            changed=copy.deepcopy(a);mutate(changed)
            changed['receipt']['receipt_sha256']=intake.digest({k:v for k,v in changed['receipt'].items() if k!='receipt_sha256'})
            with self.assertRaises(ValueError):intake.verify(self.p,changed)
        changed=copy.deepcopy(self.p);changed['version']='different'
        with self.assertRaises(ValueError):intake.verify(changed,a)

    def test_consistently_reauthored_review_is_not_authenticated(self):
        r=self.review();r.update(reviewer='Different supplied reviewer',receipt_id='another supplied label')
        a=intake.assemble(self.p,self.c,r);checked=intake.verify(self.p,a)
        self.assertTrue(checked['valid']);self.assertEqual(checked['reviewer_identity_verification'],'NOT_ESTABLISHED')
        self.assertEqual(a['receipt']['assertion'],r)

    def test_strict_json_rejects_coercions_cycles_surrogates_and_nonfinite_numbers(self):
        class D(dict):pass
        class L(list):pass
        class S(str):pass
        for value in [(1,),{1:'x'}, {'x':float('nan')},{'x':float('inf')},{'x':'\ud800'},D(self.c),L([1]),S('x'),object()]:
            with self.assertRaises((ValueError,TypeError,UnicodeError)):
                intake._normalized(value,50_000_000,'synthetic')
        cyclic=[];cyclic.append(cyclic)
        with self.assertRaises(ValueError):intake._normalized(cyclic,50_000_000,'synthetic')
        shared=[];self.assertEqual(intake._normalized([shared,shared],100,'shared'),[[],[]])

    def test_whole_protocol_validation_and_adapter_rejection(self):
        for mutate in [lambda p:p.update(adapter_receipts=[]),lambda p:p.pop('reports'),
                       lambda p:p['evidence'][0].update(study_id='unknown'),
                       lambda p:p['report_study_inventory'][0].update(source_ids=['source-main'])]:
            p=copy.deepcopy(self.p);mutate(p);self.reject(p=p)
        for p in [None,[],True,{}]:
            with self.assertRaises((ValueError,TypeError)):intake.prepare(p,self.c)

    def test_object_key_order_ignored_but_literal_values_and_json_types_preserved(self):
        p=dict(reversed(list(self.p.items())));c=dict(reversed(list(self.c.items())))
        self.assertEqual(intake.prepare(p,c),intake.prepare(self.p,self.c))
        p=copy.deepcopy(self.p);p['opaque']=0;review=self.review(p=p)
        p['opaque']=0.0
        with self.assertRaises(ValueError):intake.assemble(p,self.c,review)
        c=copy.deepcopy(self.c);c['candidates'][0]['description']='  합성\r\n\u2028  '
        self.assertEqual(self.assembled(c=c)['protocol_candidate']['report_study_inventory'][-1]['description'],c['candidates'][0]['description'])

    def test_implementation_hashes_and_ordinary_bundle_preserve_the_correct_scope(self):
        hashes=intake.implementation_hashes()
        self.assertEqual(hashes['inventory_intake.py'],hashlib.sha256((ROOT/'inventory_intake.py').read_bytes()).hexdigest())
        self.assertIn('report_study_inventory_links.py',hashes)
        a=self.assembled();raw=research_bundle.build_bundle(encoded(a['protocol_candidate']))
        self.assertTrue(research_bundle.verify(io.BytesIO(raw))['valid'])
        with patch.object(intake,'implementation_hashes',return_value=dict(hashes,**{'inventory_intake.py':'0'*64})):
            with self.assertRaises(ValueError):intake.verify(self.p,a)

    def test_bounds_are_inclusive_and_apply_before_outputs(self):
        raw=canonical_json_bytes(self.c)
        with patch.object(intake,'MAX_CANDIDATE_BYTES',len(raw)):intake.prepare(self.p,self.c)
        with patch.object(intake,'MAX_CANDIDATE_BYTES',len(raw)-1):self.reject()
        with patch.object(intake,'MAX_PROTOCOL_BYTES',1):self.reject()
        with patch.object(intake,'MAX_APPLICATION_BYTES',1):self.reject()
        with self.assertRaises(ValueError):intake._normalized(self.c,len(raw)-1,'candidate')
        self.assertEqual(intake._normalized(self.c,len(raw),'candidate'),self.c)

    def test_no_source_access_network_or_scientific_generation(self):
        with patch.object(socket,'create_connection',side_effect=AssertionError('no network')):
            a=self.assembled();result=intake.verify(self.p,a)
        for key,value in intake.NEGATIVE_CLAIMS.items():self.assertEqual(result[key],value)
        self.assertEqual(a['protocol_candidate']['searches'],self.p['searches'])
        self.assertEqual(a['protocol_candidate']['evidence'],self.p['evidence'])
        self.assertEqual(a['protocol_candidate']['reports'],self.p['reports'])

    def test_cli_full_journey_saves_draft_application_and_verified_candidate(self):
        with tempfile.TemporaryDirectory(prefix='sensei inventory CLI ') as folder:
            root=Path(folder);p=root/'protocol.json';c=root/'candidates=합성.json';r=root/'review.json'
            draft=root/'draft.json';target=root/'target.json';app=root/'application.json';out=root/'candidate.json'
            p.write_bytes(encoded(self.p));c.write_bytes(encoded(self.c));before=(p.read_bytes(),c.read_bytes())
            result=self.invoke('template',p,'--report-id=report-three','--study-id=candidate-new','--candidate-output',draft,'--text')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(draft.read_bytes()),intake.template(self.p,'report-three','candidate-new')['candidate_document'])
            result=self.invoke('target',p,c,'--output',target,'--text');self.assertEqual(result.returncode,0,result.stderr)
            review=json.loads(target.read_bytes())['review_document'];review.update(self.review());r.write_bytes(encoded(review))
            result=self.invoke('assemble',p,c,r,'--output',app);self.assertEqual(result.returncode,0,result.stderr)
            record=json.loads(app.read_bytes());self.assertEqual(record,self.assembled())
            result=self.invoke('verify',p,app,'--protocol-output',out,'--text');self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(out.read_bytes()),record['protocol_candidate'])
            self.assertEqual((p.read_bytes(),c.read_bytes()),before)
            self.assertIn(b'NOT_ESTABLISHED',result.stdout)
            result=self.invoke('verify',p,app);self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])

    def test_cli_existing_outputs_inputs_symlinks_and_inspection_errors_not_bypassed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'p';c=root/'c';out=root/'out';p.write_bytes(encoded(self.p));c.write_bytes(encoded(self.c))
            for path in [p,c,out]:
                if path==out:path.write_bytes(b'unchanged')
                old=path.read_bytes();result=self.invoke('target',p,c,'--output',path)
                self.assertNotEqual(result.returncode,0);self.assertEqual(path.read_bytes(),old)
            link=root/'link';target=root/'missing'
            try:link.symlink_to(target)
            except (OSError,NotImplementedError):pass
            else:
                result=self.invoke('target',p,c,'--output',link)
                self.assertNotEqual(result.returncode,0);self.assertFalse(target.exists());self.assertTrue(link.is_symlink())
            with patch.object(Path,'lstat',side_effect=PermissionError('synthetic inspection failure')):
                with self.assertRaises(PermissionError):intake._write_new(root/'new',b'no')
            self.assertFalse((root/'new').exists())

    def test_cli_invalid_json_or_inputs_never_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'p';c=root/'c';out=root/'out';p.write_bytes(encoded(self.p))
            for raw in [b'\xff',b'null',b'{}',b'{"schema_version":1,"schema_version":1}',b'{"x":NaN}',b'{"x":1e999}']:
                c.write_bytes(raw);result=self.invoke('target',p,c,'--output',out)
                self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists());self.assertNotIn(b'Traceback',result.stderr)
            c.write_bytes(encoded(self.c));result=self.invoke('template',p,'--report-id=report-four','--study-id=new','--candidate-output',out)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())
            app=root/'app';app.write_bytes(encoded(dict(self.assembled(),unknown=True)))
            result=self.invoke('verify',p,app,'--protocol-output',out)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())

    def test_cli_serialization_and_rendering_preflight_prevents_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'p';c=root/'c';out=root/'out';p.write_bytes(encoded(self.p));c.write_bytes(encoded(self.c))
            args=['inventory_intake.py','target',str(p),str(c),'--output',str(out),'--text']
            for renderer in [lambda _: '\ud800',lambda _: (_ for _ in ()).throw(ValueError('synthetic rendering failure'))]:
                with patch.object(sys,'argv',args),patch.object(intake,'configure_utf8_stdio'), \
                     patch.object(sys,'stdout',io.StringIO()),patch.object(sys,'stderr',io.StringIO()), \
                     patch.object(intake,'render_text',side_effect=renderer):
                    with self.assertRaises(SystemExit):intake.main()
                self.assertFalse(out.exists())
            with patch.object(sys,'argv',args),patch.object(intake,'configure_utf8_stdio'), \
                 patch.object(sys,'stdout',io.StringIO()),patch.object(sys,'stderr',io.StringIO()), \
                 patch.object(intake,'_encode',side_effect=ValueError('synthetic encoding failure')):
                with self.assertRaises(SystemExit):intake.main()
            self.assertFalse(out.exists())

    def test_described_candidate_needs_separate_full_text_choice_before_extraction(self):
        described=self.assembled()['protocol_candidate']
        record_id=next(r for r in described['reports'] if r['report_id']=='report-three')['record_ids'][0]
        with self.assertRaises(ValueError):
            result_extraction.worksheet(described,'report-three','candidate-new',record_id)
        decision=report_decision.prepare(described,'report-three')['decision_document']
        self.assertIsNone(decision['study_declaration']);self.assertIsNone(decision['decision'])
        decision.update(receipt_id='fictional-separate-full-text',decision='include',
            reason='Separate fictional eligibility choice.',adjudicator='Fictional adjudicator',
            decided_at='2026-11-04',rationale='Explicit new choice, not inventory-derived approval.',
            source_locator='synthetic:full-text-choice',study_declaration={'study_ids':['candidate-new']})
        application=report_decision.assemble(described,decision)
        self.assertTrue(report_decision.verify(described,application)['valid'])
        included=application['protocol_candidate']
        self.assertEqual(included['report_study_inventory'],described['report_study_inventory'])
        self.assertEqual(included['evidence'],described['evidence'])
        worksheet=result_extraction.worksheet(included,'report-three','candidate-new',record_id)
        candidate=worksheet['candidate_document']['candidates'][0]
        self.assertEqual(candidate['evidence']['study_id'],'candidate-new')
        self.assertIsNone(candidate['evidence']['result']);self.assertEqual(candidate['source_references'],[])
        with self.assertRaises(ValueError):result_intake.prepare(included,worksheet['candidate_document'])

    def test_text_quotes_untrusted_controls(self):
        c=copy.deepcopy(self.c);c['candidates'][0]['description']='fake\nConclusion: READY\x1b\u202e'
        text=intake.render_text(intake.prepare(self.p,c))
        self.assertNotIn('\nConclusion: READY',text);self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        self.assertIn('NOT_ESTABLISHED',text);self.assertIn('NOT_READY',text)


if __name__=='__main__':
    unittest.main()
