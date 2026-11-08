"""Independent fictional descriptive-condition append and exact replay boundaries."""
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

import condition_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow

ROOT = Path(__file__).resolve().parent
UNSET = object()


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def missing():
    return dict(status='unknown', reason='Fictional metadata not supplied.', source_locator='synthetic:caption')


def unit(eids=('result-A',), xid='fictional-condition'):
    return dict(experiment_id=xid, evidence_ids=list(eids), source_locator='synthetic:caption',
        model=dict(kind='unknown', label='Fictional model label', source_locator='synthetic:caption', limitations='Unverified supplied label.'),
        treatment=dict(label='Fictional comparison label', source_locator='synthetic:caption', concentration=missing(), exposure_time=missing()),
        comparator=missing(), observation_times=[dict(evidence_id=e, time=missing(), reference_event=missing()) for e in eids],
        causal_basis='unknown', causal_statement='No causal assessment supplied.',
        causal_limitations='Fictional descriptive assertion only.', causal_source_locator='synthetic:caption',
        limitations='Not a procedure, independent unit, or replicate count.')


def candidates(eids=('result-A',), xid='fictional-condition'):
    return dict(schema_version=1, candidates=[dict(report_id='report-one', experimental_unit=unit(eids,xid),
        source_references=[dict(source_id='source-main', extraction_locator='Fictional caption')],
        extracted_by='Fictional extractor', extracted_at='2026-11-04', extraction_note='Supplied descriptive metadata, not source verification.')])


class ConditionIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('report-study-inventory-reviews.json')
        self.c = candidates()

    def review(self,p=None,c=None):
        doc = intake.prepare(self.p if p is None else p,self.c if c is None else c)['review_document']
        doc.update(receipt_id='fictional-condition-receipt',decision='import_conditions',reviewer='Fictional reviewer',
                   reviewed_at='2026-11-04',rationale='Explicit fictional metadata import.')
        return doc

    def assembled(self,p=None,c=None):
        p=self.p if p is None else p;c=self.c if c is None else c
        return intake.assemble(p,c,self.review(p,c))

    def reject(self,c=UNSET,p=None):
        with self.assertRaises((ValueError,TypeError)):
            intake.prepare(self.p if p is None else p,self.c if c is UNSET else c)

    def test_prepare_deterministic_immutable_blank_review(self):
        old=copy.deepcopy((self.p,self.c)); prepared=intake.prepare(self.p,self.c)
        self.assertEqual(prepared,intake.prepare(self.p,self.c))
        self.assertEqual((self.p,self.c),old)
        review=prepared['review_document']
        self.assertEqual(set(review),{'schema_version','receipt_id','target_sha256','decision','reviewer','reviewed_at','rationale'})
        self.assertTrue(all(v is None for k,v in review.items() if k not in ('schema_version','target_sha256')))
        self.assertEqual(len(review['target_sha256']),64)
        with self.assertRaises(ValueError):intake.assemble(self.p,self.c,review)

    def test_absent_empty_stage_and_unchanged_flows(self):
        for present in (False,True):
            p=copy.deepcopy(self.p)
            if present:p['experimental_units']=[]
            record=self.assembled(p=p); receipt=record['receipt']
            self.assertEqual(receipt['before_condition_summary'],dict(stage='SUPPLIED' if present else 'NOT_SUPPLIED',condition_pair_count=0,
                unlinked_evidence_ids=['result-A','result-B'] if present else None))
            self.assertEqual(receipt['after_condition_summary'],dict(stage='SUPPLIED',condition_pair_count=1,unlinked_evidence_ids=['result-B']))
            self.assertEqual(receipt['before_flow'],receipt['after_flow'])
            self.assertEqual(receipt['before_report_flow'],receipt['after_report_flow'])
            self.assertEqual(record['kind'],'detached_condition_intake')
            self.assertEqual(set(record),{'schema_version','kind','receipt','protocol_candidate'})
            self.assertTrue(intake.verify(p,record)['valid'])

    def test_exact_append_prefix_order_and_opaque_preservation(self):
        self.p['experimental_units']=[unit(('result-B',),'existing-condition')]
        self.p['opaque_metadata']={'ordered':['β',None,{'verbatim':'  keep\nthis  '}], 'number':0}
        original=canonical_json_bytes(self.p)
        record=self.assembled(); new=record['protocol_candidate']
        self.assertEqual(new['experimental_units'],self.p['experimental_units']+[self.c['candidates'][0]['experimental_unit']])
        self.assertEqual({k:v for k,v in new.items() if k!='experimental_units'},{k:v for k,v in self.p.items() if k!='experimental_units'})
        self.assertEqual(canonical_json_bytes(self.p),original)
        self.assertNotIn('source_references',new['experimental_units'][-1])
        self.assertEqual(record['receipt']['source_association_scope'],'DETACHED_RECORD_ONLY')
        self.assertEqual(record['receipt']['external_calls'],0)
        self.assertEqual(record['receipt']['scientific_acceptance'],'NOT_ASSESSED')
        self.assertEqual(record['receipt']['reading'],'NOT_ESTABLISHED')

    def test_multiple_outcomes_raw_selection_order_and_snapshots(self):
        row=copy.deepcopy(self.p['evidence'][0]);row['evidence_id']='result-A-second';self.p['evidence'].append(row)
        self.c=candidates(('result-A-second','result-A'))
        second=candidates(('result-B',),'condition-B')['candidates'][0];self.c['candidates'].append(second)
        record=self.assembled(); target=record['receipt']['target']
        selected=target['selected_evidence']
        self.assertEqual([s['evidence_id'] for s in selected],['result-A-second','result-A','result-B'])
        self.assertEqual([s['input_pointer'] for s in selected],['/evidence/2','/evidence/0','/evidence/1'])
        for s in selected:
            raw=self.p['evidence'][int(s['input_pointer'].split('/')[-1])]
            self.assertEqual(s['evidence'],raw)
        self.assertEqual(record['protocol_candidate']['experimental_units'],[r['experimental_unit'] for r in self.c['candidates']])
        self.assertEqual(record['receipt']['after_condition_summary']['condition_pair_count'],2)

    def test_exact_candidate_schema_and_human_provenance(self):
        for bad in (None,[],True,dict(self.c,schema_version=True),dict(self.c,schema_version=2),dict(self.c,extra=1),dict(self.c,candidates=[]),dict(self.c,candidates={}),dict(self.c,candidates=self.c['candidates']*101)):
            with self.subTest(bad=repr(bad)[:60]):self.reject(bad)
        for field in self.c['candidates'][0]:
            c=copy.deepcopy(self.c);del c['candidates'][0][field];self.reject(c)
        for field in ('report_id','extracted_by','extracted_at','extraction_note'):
            for bad in (None,True,0,[],{},'', ' \t\n'):
                c=copy.deepcopy(self.c);c['candidates'][0][field]=bad;self.reject(c)
        for date in ('2026-02-29','2026-2-04','2026-11-04\n','0000-01-01'):
            c=copy.deepcopy(self.c);c['candidates'][0]['extracted_at']=date;self.reject(c)
        c=copy.deepcopy(self.c);c['candidates'][0]['extracted_at']='2024-02-29';intake.prepare(self.p,c)
        for target in ('candidate','unit','source'):
            c=copy.deepcopy(self.c);r=c['candidates'][0]
            (r if target=='candidate' else r['experimental_unit'] if target=='unit' else r['source_references'][0])['extra']=1
            self.reject(c)

    def test_source_references_unique_exact_known_same_report(self):
        ref=self.c['candidates'][0]['source_references'][0]
        for refs in (None,[],{},'source-main',[ref,ref],[dict(ref,source_id='missing')],[dict(ref,source_id='source-unbound')],[dict(ref,extraction_locator=' ')],[{'source_id':'source-main'}]):
            c=copy.deepcopy(self.c);c['candidates'][0]['source_references']=refs;self.reject(c)
        for field in ('source_id','extraction_locator'):
            for bad in (None,True,0,[],{}):
                c=copy.deepcopy(self.c);c['candidates'][0]['source_references'][0][field]=bad;self.reject(c)

    def test_report_mapping_membership_and_scalar_plural_guards(self):
        for rid in ('missing','report-two','report-three','report-four','report-five'):
            c=copy.deepcopy(self.c);c['candidates'][0]['report_id']=rid;self.reject(c)
        for field,value in [('retrieval','pending'),('decision','exclude'),('study_ids',['study-B']),('record_ids',['record-two'])]:
            p=copy.deepcopy(self.p);p['reports'][0][field]=value;self.reject(p=p)
        p=copy.deepcopy(self.p);p['reports'][0].pop('study_ids');p['reports'][0]['study_id']='study-A'
        p['evidence']=p['evidence'][:1];p['gaps']=[]
        # Drop dependent assertions only in this independent fixture setup.
        for key in ('report_reviews','report_completions'):p.pop(key,None)
        self.assertTrue(intake.verify(p,self.assembled(p=p))['valid'])
        p['reports'][0]['study_id']='wrong-existing-membership';self.reject(p=p)

    def test_raw_explicit_ids_required_not_normalized_fallback(self):
        p=copy.deepcopy(self.p);p['evidence'][0].pop('evidence_id');p['gaps']=[]
        for key in ('report_reviews','report_completions'):p.pop(key,None)
        run(p);report_flow(p)
        self.reject(candidates(('record-one',)),p)
        for refs in ([],['missing'],['result-A','result-A'],'result-A'):
            c=copy.deepcopy(self.c);c['candidates'][0]['experimental_unit']['evidence_ids']=refs;self.reject(c)

    def test_collisions_reassignment_cross_record_and_study(self):
        c=copy.deepcopy(self.c);c['candidates'].append(copy.deepcopy(c['candidates'][0]));self.reject(c)
        c['candidates'][1]['experimental_unit']['experiment_id']='another-condition';self.reject(c)
        self.p['experimental_units']=[unit()];self.reject()
        self.c['candidates'][0]['experimental_unit']['experiment_id']='different-id';self.reject()
        self.p.pop('experimental_units');self.reject(candidates(('result-A','result-B')))
        p=copy.deepcopy(self.p);row=copy.deepcopy(p['evidence'][0]);row.update(evidence_id='other-record-result',record_id='record-two');p['evidence'].append(row)
        self.reject(candidates(('result-A','other-record-result')),p)
        p=copy.deepcopy(self.p);p['experimental_units']=[unit(('result-B',),'different-id')];self.reject(p=p)

    def test_existing_engine_missingness_schema_and_optional_coverage(self):
        changes=[lambda u:u['treatment']['concentration'].update(value=0),lambda u:u['treatment'].pop('exposure_time'),
            lambda u:u['model'].update(kind='invented'),lambda u:u['observation_times'].clear(),
            lambda u:u['observation_times'].append(copy.deepcopy(u['observation_times'][0])),
            lambda u:u.update(causal_basis='association'),lambda u:u.update(outcome_sampling=[]),lambda u:u.update(outcome_statistics=[])]
        for mutate in changes:
            c=copy.deepcopy(self.c);mutate(c['candidates'][0]['experimental_unit']);self.reject(c)
        for state in ('unknown','not_reported','not_applicable'):
            c=copy.deepcopy(self.c);c['candidates'][0]['experimental_unit']['treatment']['concentration']['status']=state
            self.assertEqual(self.assembled(c=c)['protocol_candidate']['experimental_units'][0],c['candidates'][0]['experimental_unit'])
        p=copy.deepcopy(self.p);p['experimental_units']=[unit(('result-B',),'old')]
        p['experimental_units'][0]['observation_times']=[];self.reject(p=p)

    def test_optional_sampling_statistics_preserved_without_calculation(self):
        p=fixture('statistics-review.json');u=p.pop('experimental_units')[0]
        p['report_sources']=[dict(source_id='source-main',report_id='report-1',source_locator='synthetic:inert',document_version='Fictional v1',document_sha256=None)]
        c=candidates();c['candidates'][0].update(report_id='report-1',experimental_unit=u)
        u['treatment']['concentration']=dict(status='reported',value='0',unit='fictional arbitrary label',source_locator='synthetic:caption')
        u['outcome_statistics'][0]['treatment']['value']['value']='0'
        r=self.assembled(p,c);new=r['protocol_candidate']
        self.assertEqual(new['experimental_units'][0],u)
        result=run(new)['experiments']['experimental_unit_ledger'][0]
        self.assertEqual(result['statistics_review']['numeric_consistency'],'NOT_ASSESSED')
        self.assertEqual(result['statistics_review']['effect_assessment'],'NOT_PERFORMED')
        self.assertEqual(result['sampling_review']['independence_assessment'],'NOT_PERFORMED')
        for field in ('outcome_sampling','outcome_statistics'):
            for op in ('missing','duplicate','alien'):
                bad=copy.deepcopy(c);rows=bad['candidates'][0]['experimental_unit'][field]
                if op=='missing':rows.pop()
                elif op=='duplicate':rows.append(copy.deepcopy(rows[0]))
                else:rows[0]['evidence_id']='alien'
                self.reject(bad,p)
        self.assertEqual(new['planning_decisions'],p['planning_decisions'])
        self.assertEqual(new['synthesis_statements'],p['synthesis_statements'])

    def test_whole_inputs_and_current_engine_bind_review(self):
        review=self.review()
        for mutate in (lambda p:p.update(question=p['question']+' changed'),lambda p:p.update(opaque={'changed':True}),lambda p:p['report_sources'][1].update(document_version='changed')):
            p=copy.deepcopy(self.p);mutate(p)
            with self.assertRaises(ValueError):intake.assemble(p,self.c,review)
        c=copy.deepcopy(self.c);c['candidates'][0]['extraction_note']+=' changed'
        with self.assertRaises(ValueError):intake.assemble(self.p,c,review)
        self.assertIn('condition_intake.py',self.assembled()['receipt']['engine_sha256'])
        with patch.object(intake,'_implementation_hashes',return_value={'condition_intake.py':'0'*64}):
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,review)

    def test_review_exact_schema_humans_real_dates(self):
        review=self.review()
        for field in review:
            for bad in (None,True,2,[],{},'', ' '):
                doc=copy.deepcopy(review);doc[field]=bad
                with self.subTest(field=field,bad=bad),self.assertRaises((ValueError,TypeError)):intake.assemble(self.p,self.c,doc)
            doc=copy.deepcopy(review);del doc[field]
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,doc)
        for field,value in [('decision','approve'),('decision','import_conditions '),('reviewed_at','2026-02-29'),('reviewed_at','2026-11-04\n'),('extra',True)]:
            doc=copy.deepcopy(review);doc[field]=value
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,doc)

    def test_full_replay_resealed_tampering_and_unsigned_reauthorship(self):
        record=self.assembled()
        for field,value in [('before_flow',{}),('after_flow',{}),('before_condition_summary',{}),('after_condition_summary',{}),('external_calls',True),('source_authenticity','VERIFIED'),('receipt_id','changed')]:
            bad=copy.deepcopy(record);bad['receipt'][field]=value
            bad['receipt']['receipt_sha256']=intake.digest({k:v for k,v in bad['receipt'].items() if k!='receipt_sha256'})
            with self.assertRaises(ValueError):intake.verify(self.p,bad)
        for mutate in (lambda r:r.update(extra=True),lambda r:r.update(schema_version=True),lambda r:r.update(kind='authenticated'),lambda r:r['protocol_candidate']['experimental_units'][0].update(limitations='changed')):
            bad=copy.deepcopy(record);mutate(bad)
            with self.assertRaises(ValueError):intake.verify(self.p,bad)
        bad=copy.deepcopy(record);bad['receipt']['target']['selected_evidence'][0]['input_pointer']='/evidence/1'
        target=bad['receipt']['target'];target['target_sha256']=intake.digest({k:v for k,v in target.items() if k!='target_sha256'})
        bad['receipt']['assertion']['target_sha256']=target['target_sha256']
        bad['receipt']['receipt_sha256']=intake.digest({k:v for k,v in bad['receipt'].items() if k!='receipt_sha256'})
        with self.assertRaises(ValueError):intake.verify(self.p,bad)
        review=self.review();review.update(reviewer='Another fictional reviewer',receipt_id='replacement')
        rewritten=intake.assemble(self.p,self.c,review)
        self.assertTrue(intake.verify(self.p,rewritten)['valid']);self.assertIn('unsigned',rewritten['receipt']['boundary'])

    def test_both_entire_protocols_use_engine_and_csv_aware_report_guard(self):
        with patch.object(intake,'run',wraps=run) as runs,patch.object(intake,'report_flow',wraps=report_flow) as flows:
            intake.prepare(self.p,self.c)
        self.assertEqual(runs.call_count,2);self.assertEqual(flows.call_count,2)
        self.assertEqual(runs.call_args_list[0].args[0],self.p)
        self.assertEqual(runs.call_args_list[1].args[0]['experimental_units'],[self.c['candidates'][0]['experimental_unit']])
        for call in flows.call_args_list:self.assertIs(call.kwargs['include_csv'],False)

    def test_no_network_source_opening_or_external_process(self):
        self.p['report_sources'][0]['source_locator']='https://invalid.example/do-not-open'
        with patch('urllib.request.urlopen',side_effect=AssertionError('no network')),patch('socket.socket',side_effect=AssertionError('no network')),patch('subprocess.run',side_effect=AssertionError('no subprocess')):
            record=self.assembled();self.assertTrue(intake.verify(self.p,record)['valid'])
        self.assertIsInstance(intake.render_text(record),str)

    def test_api_bounds_nonfinite_and_upper_candidate_boundary(self):
        for name,value in [('MAX_CANDIDATE_BYTES',10_000_000),('MAX_PROTOCOL_BYTES',50_000_000),('MAX_APPLICATION_BYTES',50_000_000),('MAX_CANDIDATES',100)]:self.assertEqual(getattr(intake,name),value)
        record=self.assembled()
        for name,action in [('MAX_CANDIDATE_BYTES',lambda:intake.prepare(self.p,self.c)),('MAX_PROTOCOL_BYTES',lambda:intake.prepare(self.p,self.c)),('MAX_APPLICATION_BYTES',lambda:intake.verify(self.p,record))]:
            with patch.object(intake,name,10),self.assertRaises(ValueError):action()
        for bad in (float('nan'),float('inf')):
            p=copy.deepcopy(self.p);p['opaque']=bad;self.reject(p=p)
        p=copy.deepcopy(self.p);p['evidence']=[];p['gaps']=[]
        for key in ('report_reviews','report_completions'):p.pop(key,None)
        c={'schema_version':1,'candidates':[]}
        for i in range(100):
            eid='fictional-result-%03d'%i;row=copy.deepcopy(self.p['evidence'][0]);row['evidence_id']=eid;p['evidence'].append(row)
            c['candidates'].append(candidates((eid,),'condition-%03d'%i)['candidates'][0])
        self.assertEqual(len(self.assembled(p,c)['protocol_candidate']['experimental_units']),100)

    def test_invalid_originals_and_missing_reports_are_not_bypassed(self):
        for field,value in [('adapter_receipts',{}),('evidence',[None]),('experimental_units',{}),('screening',[])]:
            p=copy.deepcopy(self.p);p[field]=value;self.reject(p=p)
        p=copy.deepcopy(self.p);p.pop('reports');self.reject(p=p)
        p=copy.deepcopy(self.p);p['report_sources'][0]['document_sha256']='not-a-hash';self.reject(p=p)

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'condition_intake.py'),*map(str,args)],cwd=ROOT,capture_output=True,env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))

    def test_cli_utf8_roundtrip_exclusive_and_strict_json(self):
        self.c['candidates'][0]['experimental_unit']['limitations']='Fictional 합성\n\x1b[31mnot a procedure'
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'p.json';c=d/'c.json';r=d/'r.json';out=d/'out.json';target=d/'target.json';derived=d/'derived.json'
            p.write_bytes(canonical_json_bytes(self.p));c.write_bytes(canonical_json_bytes(self.c));r.write_bytes(canonical_json_bytes(self.review()))
            for args in [('target',p,c,'--output',target,'--text'),('assemble',p,c,r,'--output',out,'--text'),('verify',p,out,'--protocol-output',derived,'--text')]:
                result=self.cli(*args);self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'));self.assertNotIn(b'\x1b',result.stdout)
            self.assertEqual(json.loads(derived.read_bytes()),json.loads(out.read_bytes())['protocol_candidate'])
            for args,path in [(('target',p,c,'--output',target),target),(('assemble',p,c,r,'--output',out),out),(('verify',p,out,'--protocol-output',derived),derived)]:
                old=path.read_bytes();self.assertNotEqual(self.cli(*args).returncode,0);self.assertEqual(path.read_bytes(),old)
            for raw in (b'{"schema_version":1,"schema_version":1,"candidates":[]}',b'\xff',b'{"x":NaN}',b'{} trailing',br'{"bad":"\ud800"}'):
                c.write_bytes(raw);bad=d/'bad.json';self.assertNotEqual(self.cli('target',p,c,'--output',bad).returncode,0);self.assertFalse(bad.exists())

    def test_valid_mock_base_preserved_and_later_descriptor_edits_rejected(self):
        import offline_adapter
        from adapter_integrity import prepare_exchange
        base=fixture('adapter-protocol.json');mock=fixture('adapter-fixture.json')
        base['report_sources']=[dict(source_id='source-main',report_id='report-1',source_locator='synthetic:mock-source',document_version='Fictional base v1',document_sha256=None)]
        targets=prepare_exchange(base,mock)[1]
        reviews=fixture('adapter-reviews.json')
        for row in reviews:row['target_sha256']=targets[(row['target_type'],row['target_id'])]['sha256']
        p=offline_adapter.assemble(base,mock,reviews)['protocol']
        c=candidates(('e1','e2'));c['candidates'][0]['report_id']='report-1'
        c['candidates'][0]['experimental_unit']['causal_basis']='intervention'
        record=self.assembled(p,c);new=record['protocol_candidate']
        for field in ('adapter_receipts','evidence','searches','reports','report_sources'):
            self.assertEqual(canonical_json_bytes(new[field]),canonical_json_bytes(p[field]))
        self.assertTrue(intake.verify(p,record)['valid'])
        for mutate in (lambda p:p['report_sources'][0].update(document_version='post-history edit'),
                       lambda p:p['reports'][0].update(locator='post-history edit'),
                       lambda p:p['evidence'][0].update(result='post-history edit'),
                       lambda p:p['adapter_receipts'].update(base_protocol_sha256='0'*64)):
            bad=copy.deepcopy(p);mutate(bad);self.reject(c,bad)
        bad=copy.deepcopy(self.p);bad['evidence'][0]['adapter_provenance']={};self.reject(p=bad)

    def test_csv_history_preserved_and_original_result_receipts_still_replay(self):
        import bibliographic_intake
        import bibliographic_review
        import result_intake
        import result_correction
        p=fixture('bibliographic-base.json')
        raw=b'record_id,source_locator\nfictional-input,synthetic:local-export\n'
        artifact=bibliographic_intake.prepare(p,raw,'local-primary','2026-11-04T00:00:00Z')
        choices=bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record',record_id='record-one',rationale='Fictional identity assertion')
        review=bibliographic_review.prepare_review(p,artifact,choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional collection',decision='import_for_screening')
        p=bibliographic_review.assemble(p,artifact,review)['protocol_candidate']
        p['screening']=[dict(record_id='record-one',decision='include',reason='Fictional screening')]
        p['reports']=[dict(report_id='report-one',record_ids=['record-one'],retrieval='retrieved',decision='include',study_ids=['study-A','study-C'],locator='synthetic:report')]
        p['report_sources']=copy.deepcopy(self.p['report_sources'][:2])
        original=copy.deepcopy(p);rc=fixture('manual-result-candidates.json')
        review=result_intake.prepare(p,rc)['review_document']
        review.update(receipt_id='fictional-result-import',decision='import_results',reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional input')
        result_record=result_intake.assemble(p,rc,review);p=result_record['protocol_candidate']
        correction_original=copy.deepcopy(p);corrections=fixture('manual-result-corrections.json')
        review=result_correction.prepare(p,corrections)['review_document']
        review.update(receipt_id='fictional-result-correction',decision='correct_result_text',reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional correction')
        corrected=result_correction.assemble(p,corrections,review);p=corrected['protocol_candidate']
        c=candidates(('result-C-manual',));record=self.assembled(p,c)
        self.assertEqual(record['protocol_candidate']['bibliographic_imports'],p['bibliographic_imports'])
        self.assertEqual(record['protocol_candidate']['evidence'],p['evidence'])
        self.assertTrue(intake.verify(p,record)['valid'])
        self.assertTrue(result_intake.verify(original,result_record)['valid'])
        self.assertTrue(result_correction.verify(correction_original,corrected)['valid'])
        self.assertTrue(record['receipt']['target']['selected_record_targets'])

    def test_downstream_staleness_without_renewed_status_or_assertions(self):
        p=fixture('experiment-review.json');u=p.pop('experimental_units')[0]
        p['report_sources']=[dict(source_id='source-main',report_id='report-1',source_locator='synthetic:inert',document_version='Fictional v1',document_sha256=None)]
        # Establish supplied assertions for this independent pre-enrichment fixture.
        before=run(p)
        for row in p['synthesis_statements']:
            row['basis_sha256']=next(t['basis_sha256'] for t in before['synthesis']['review_targets'] if t['statement_id']==row['statement_id'])
        before=run(p)
        for row in p['planning_decisions']:
            row['basis_sha256']=next(t['basis_sha256'] for t in before['planning']['review_targets'] if t['work_package_id']==row['work_package_id'])
        p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic:fictional-note',acceptance_verified=True)
        binding=next(t for t in run(p)['planning']['completion_ledger'] if t['work_package_id']==p['gaps'][0]['work_package_id'])
        p['gaps'][0]['completion_basis_sha256']=binding['current_basis_sha256']
        before=run(p)
        self.assertEqual(before['synthesis']['stale_statement_ids'],[])
        self.assertEqual(before['planning']['work_with_stale_planning_assertion'],[])
        c=candidates();c['candidates'][0].update(report_id='report-1',experimental_unit=u)
        new=self.assembled(p,c)['protocol_candidate'];after=run(new)
        self.assertTrue(after['synthesis']['stale_statement_ids'])
        self.assertTrue(after['planning']['work_with_stale_planning_assertion'])
        binding=next(t for t in after['planning']['completion_ledger'] if t['work_package_id']==p['gaps'][0]['work_package_id'])
        self.assertEqual(binding['source_match_status'],'STALE_SOURCE')
        self.assertEqual(new['gaps'][0]['status'],'COMPLETE')
        for field in ('synthesis_statements','planning_decisions','gaps'):
            self.assertEqual(new[field],p[field])
        self.assertEqual(after['conclusion_readiness'],'NOT_READY')

    def test_cli_encoding_and_size_failure_precede_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'p.json';c=d/'c.json';out=d/'out.json'
            p.write_bytes(canonical_json_bytes(self.p));c.write_bytes(canonical_json_bytes(self.c))
            argv=['condition_intake.py','target',str(p),str(c),'--output',str(out),'--text']
            for rendered in ('x'*(intake.MAX_APPLICATION_BYTES+1),'\ud800'):
                with patch.object(sys,'argv',argv),patch.object(intake,'configure_utf8_stdio'),patch.object(intake,'render_text',return_value=rendered),patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):
                    intake.main()
                self.assertFalse(out.exists())
            c.write_bytes(b' '*(intake.MAX_CANDIDATE_BYTES+1))
            self.assertNotEqual(self.cli('target',p,c,'--output',out).returncode,0);self.assertFalse(out.exists())

    def test_public_fixture_keeps_result_counts_and_reviews(self):
        p=fixture('extraction-worksheet-protocol.json');c=fixture('manual-condition-candidates.json')
        record=self.assembled(p,c);new=record['protocol_candidate']
        self.assertEqual(len(new['evidence']),4)
        self.assertEqual(record['receipt']['after_condition_summary']['unlinked_evidence_ids'],['result-B'])
        for field in ('report_reviews','report_completions'):
            if field in p:self.assertEqual(new[field],p[field])
        self.assertTrue(intake.verify(p,record)['valid'])


if __name__=='__main__':unittest.main()
