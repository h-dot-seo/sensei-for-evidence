"""Independent fictional source-work intake and exact replay boundaries."""
import copy
import io
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import source_work_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow

ROOT = Path(__file__).resolve().parents[1]
UNSET = object()


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def candidates(wid='WP-FICTIONAL-NEW', refs=None, dependencies=None):
    return dict(schema_version=1, candidates=[dict(work_package=dict(
        work_package_id=wid, work_type='source_review', question='Supplied fictional review question?',
        deliverable='Supplied fictional review note.', acceptance_criterion='Human checks the supplied fictional note.',
        evidence_ids=[], source_refs=copy.deepcopy(refs if refs is not None else [dict(kind='planned_search',search_id='search-secondary')]),
        depends_on=list(dependencies or []),status='PLANNED'), proposed_by='Fictional proposer',
        proposed_at='2026-11-04',proposal_note='Explicit fictional human-authored work.')])


class SourceWorkIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('source-work-protocol.json')
        self.c = candidates()

    def review(self,p=None,c=None):
        doc=intake.prepare(self.p if p is None else p,self.c if c is None else c)['review_document']
        doc.update(receipt_id='fictional-work-receipt',decision='import_source_work',reviewer='Fictional reviewer',
                   reviewed_at='2026-11-04',rationale='Explicit fictional work import.')
        return doc

    def assembled(self,p=None,c=None):
        p=self.p if p is None else p;c=self.c if c is None else c
        return intake.assemble(p,c,self.review(p,c))

    def reject(self,c=UNSET,p=None):
        with self.assertRaises((ValueError,TypeError)):
            intake.prepare(self.p if p is None else p,self.c if c is UNSET else c)

    def test_template_only_structure_and_selected_references_no_authored_meaning(self):
        refs=dict(schema_version=1,source_refs=[dict(kind='planned_search',search_id='search-secondary'),dict(kind='record',record_id='r2')])
        original=copy.deepcopy((self.p,refs));result=intake.template(self.p,refs)
        self.assertEqual(result,intake.template(self.p,refs));self.assertEqual((self.p,refs),original)
        doc=result['candidate_document'];self.assertEqual(doc['schema_version'],1);self.assertEqual(len(doc['candidates']),1)
        row=doc['candidates'][0];work=row['work_package']
        self.assertEqual(work['source_refs'],refs['source_refs'])
        self.assertEqual(work['work_type'],'source_review');self.assertEqual(work['evidence_ids'],[]);self.assertEqual(work['status'],'PLANNED')
        for field in ('work_package_id','question','deliverable','acceptance_criterion','depends_on'):self.assertIsNone(work[field])
        for field in ('proposed_by','proposed_at','proposal_note'):self.assertIsNone(row[field])
        self.reject(doc)
        for bad in (dict(refs,extra=1),dict(refs,schema_version=True),dict(refs,source_refs=[]),dict(refs,source_refs=refs['source_refs']*2)):
            with self.assertRaises(ValueError):intake.template(self.p,bad)

    def test_absent_reports_and_present_empty_reports_are_distinct(self):
        p=fixture('bibliographic-base.json');c=candidates(refs=[dict(kind='planned_search',search_id='local-secondary')])
        record=self.assembled(p,c)
        self.assertNotIn('reports',record['protocol_candidate'])
        self.assertIsNone(record['receipt']['before_report_flow']);self.assertIsNone(record['receipt']['after_report_flow'])
        self.assertTrue(intake.verify(p,record)['valid'])
        p['reports']=[];record=self.assembled(p,c)
        self.assertEqual(record['protocol_candidate']['reports'],[])
        self.assertIsNotNone(record['receipt']['before_report_flow'])
        self.assertEqual(record['receipt']['before_report_flow'],record['receipt']['after_report_flow'])
        for bad in (None,{},[None]):
            p['reports']=bad;self.reject(c,p)

    def test_exact_selected_source_snapshots_and_after_planning_targets(self):
        self.c=candidates(refs=[dict(kind='record',record_id='r2'),dict(kind='planned_search',search_id='search-secondary')])
        result=self.assembled();target=result['receipt']['target'];new=result['protocol_candidate']
        self.assertEqual(target['candidate_work_packages'],[dict(candidate_index=0,input_pointer='/gaps/2',work_package=self.c['candidates'][0]['work_package'])])
        self.assertEqual([r['source_ref'] for r in target['selected_sources']],self.c['candidates'][0]['work_package']['source_refs'])
        self.assertEqual(target['selected_sources'][1]['planned_search'],self.p['search_plan'][1])
        self.assertEqual(target['selected_sources'][1]['input_pointer'],'/search_plan/1')
        self.assertEqual(target['selected_sources'][0]['record_target']['record_id'],'r2')
        expected=[t for t in run(new)['planning']['review_targets'] if t['work_package_id']=='WP-FICTIONAL-NEW']
        self.assertEqual(target['selected_planning_targets'],expected)

    def test_explicit_source_context_and_document_ids_use_core_bindings(self):
        p=fixture('report-source-check-protocol.json')
        contexts=fixture('context-protocol.json')['contexts']
        for row in contexts:row.update(context_scope='source_review',evidence_ids=[],source_refs=[dict(kind='record',record_id='record-one')])
        p['contexts']=contexts
        c=candidates(refs=[dict(kind='record',record_id='record-one')]);w=c['candidates'][0]['work_package']
        w.update(context='Human-authored fictional context.',context_ids=['ctx-guideline'],document_source_ids=['source-main'])
        result=self.assembled(p,c);target=result['receipt']['target'];new=result['protocol_candidate']
        self.assertEqual(new['gaps'][-1],w)
        expected=[t for t in run(new)['planning']['review_targets'] if t['work_package_id']==w['work_package_id']]
        self.assertEqual(target['selected_planning_targets'],expected)
        for field in ('context_ids','document_source_ids'):
            for bad in (None,[],['missing'],['source-main','source-main'],True):
                altered=copy.deepcopy(c);altered['candidates'][0]['work_package'][field]=bad;self.reject(altered,p)
        bad=copy.deepcopy(c);bad['candidates'][0]['work_package']['source_refs']=[dict(kind='record',record_id='record-two')];self.reject(bad,p)

    def test_mock_and_csv_provenance_survive_without_new_eligibility(self):
        record=self.assembled();new=record['protocol_candidate']
        for key in ('adapter_receipts','searches','screening','evidence','reports'):
            self.assertEqual(canonical_json_bytes(new[key]),canonical_json_bytes(self.p[key]))
        import bibliographic_intake
        import bibliographic_review
        p=fixture('bibliographic-base.json')
        artifact=bibliographic_intake.prepare(p,b'record_id,source_locator\nfictional-input,synthetic:local-export\n','local-primary','2026-11-04T00:00:00Z')
        choices=bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record',record_id='record-one',rationale='Fictional identity assertion')
        review=bibliographic_review.prepare_review(p,artifact,choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional collection',decision='import_for_screening')
        p=bibliographic_review.assemble(p,artifact,review)['protocol_candidate']
        c=candidates(refs=[dict(kind='record',record_id='record-one')])
        record=self.assembled(p,c);new=record['protocol_candidate']
        self.assertEqual({k:v for k,v in new.items() if k!='gaps'},{k:v for k,v in p.items() if k!='gaps'})
        self.assertTrue(intake.verify(p,record)['valid']);self.assertEqual(new['screening'],[])

    def test_nbib_pre_screening_work_preserves_native_metadata(self):
        import nbib_intake
        import bibliographic_review
        p=fixture('bibliographic-base.json')
        raw=b'PMID- 999999999999999999999999999991\nTI  - Fictional software-test record\n'
        artifact=nbib_intake.prepare(p,raw,'local-primary','2026-11-04T00:00:00Z')
        nested=artifact['csv_intake'];choices=bibliographic_review.template(nested)
        choices['resolutions'][0].update(disposition='new_record',record_id='fictional-canonical',rationale='Synthetic human identity choice')
        review=bibliographic_review.prepare_review(p,nested,choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer',reviewed_at='2026-11-04',rationale='Fictional collection',decision='import_for_screening')
        p=bibliographic_review.assemble(p,nested,review)['protocol_candidate']
        c=candidates(refs=[dict(kind='record',record_id='fictional-canonical')]);record=self.assembled(p,c)
        new=record['protocol_candidate'];self.assertNotIn('reports',new)
        self.assertEqual({k:v for k,v in new.items() if k!='gaps'},{k:v for k,v in p.items() if k!='gaps'})
        self.assertEqual(new['screening'],[]);self.assertEqual(new['evidence'],[])
        self.assertTrue(intake.verify(p,record)['valid'])

    def test_negative_claims_distinguish_detached_receipt_and_retained_source_links(self):
        result=self.assembled();receipt=result['receipt']
        for key,value in dict(source_authenticity='NOT_VERIFIED',reading='NOT_ESTABLISHED',
            scientific_acceptance='NOT_ASSESSED',scientific_task_generation='NOT_PERFORMED',
            priority_generation='NOT_PERFORMED',completion_generation='NOT_PERFORMED',
            existing_review_renewal='NOT_PERFORMED',reviewer_identity_verification='NOT_ESTABLISHED',
            proposer_identity_verification='NOT_ESTABLISHED',external_calls=0).items():self.assertEqual(receipt[key],value)
        self.assertNotIn('source_association_scope',receipt)
        self.assertEqual(receipt['retained_source_snapshot_scope'],'DETACHED_RECORD_ONLY')
        self.assertEqual(receipt['proposal_review_scope'],'DETACHED_RECORD_ONLY')
        self.assertEqual(result['protocol_candidate']['gaps'][-1]['source_refs'],self.c['candidates'][0]['work_package']['source_refs'])

    def test_cli_template_exports_only_candidate_and_supports_stdout(self):
        refs=dict(schema_version=1,source_refs=[dict(kind='planned_search',search_id='search-secondary')])
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'p.json';r=d/'refs.json';out=d/'candidate.json'
            p.write_bytes(canonical_json_bytes(self.p));r.write_bytes(canonical_json_bytes(refs))
            result=self.cli('template',p,r)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
            self.assertEqual(json.loads(result.stdout),intake.template(self.p,refs))
            result=self.cli('template',p,r,'--candidate-output',out,'--text')
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8'))
            self.assertEqual(json.loads(out.read_bytes()),intake.template(self.p,refs)['candidate_document'])
            old=out.read_bytes();self.assertNotEqual(self.cli('template',p,r,'--candidate-output',out).returncode,0)
            self.assertEqual(out.read_bytes(),old)

    def test_prepare_deterministic_immutable_blank_review(self):
        old=copy.deepcopy((self.p,self.c));prepared=intake.prepare(self.p,self.c)
        self.assertEqual(prepared,intake.prepare(self.p,self.c));self.assertEqual((self.p,self.c),old)
        r=prepared['review_document']
        self.assertEqual(set(r),{'schema_version','receipt_id','target_sha256','decision','reviewer','reviewed_at','rationale'})
        self.assertTrue(all(v is None for k,v in r.items() if k not in ('schema_version','target_sha256')))
        self.assertEqual(len(r['target_sha256']),64)
        with self.assertRaises(ValueError):intake.assemble(self.p,self.c,r)

    def test_exact_append_preserves_all_raw_fields_and_existing_implicit_defaults(self):
        self.p.pop('adapter_receipts')
        for search in self.p['searches']:search.pop('adapter_provenance',None)
        self.p['opaque_metadata']={'ordered':['β',None,{'verbatim':'  keep\nthis  '}],'number':0}
        original=canonical_json_bytes(self.p);record=self.assembled();new=record['protocol_candidate']
        self.assertEqual(new['gaps'],self.p['gaps']+[self.c['candidates'][0]['work_package']])
        self.assertEqual({k:v for k,v in new.items() if k!='gaps'},{k:v for k,v in self.p.items() if k!='gaps'})
        self.assertNotIn('status',new['gaps'][0]);self.assertNotIn('depends_on',new['gaps'][0])
        self.assertEqual(canonical_json_bytes(self.p),original)
        self.assertEqual(set(record),{'schema_version','kind','receipt','protocol_candidate'})
        self.assertTrue(intake.verify(self.p,record)['valid'])
        self.assertEqual(record,self.assembled())
        self.reject(p=new)

    def test_source_work_never_changes_eligibility_or_accounting(self):
        self.p.pop('adapter_receipts')
        for s in self.p['searches']:s.pop('adapter_provenance',None)
        self.p['screening']=self.p['screening'][1:];self.p.pop('reports')
        self.c=candidates(refs=[dict(kind='planned_search',search_id='search-secondary'),dict(kind='record',record_id='r1'),dict(kind='record',record_id='r2')])
        record=self.assembled();new=record['protocol_candidate'];receipt=record['receipt']
        self.assertEqual(receipt['before_flow'],receipt['after_flow'])
        self.assertEqual(receipt['before_report_flow'],receipt['after_report_flow'])
        before,after=run(self.p),run(new)
        for key in ('evidence','flow','conclusion_readiness','census_claim','search_plan_audit'):
            self.assertEqual(before[key],after[key],key)
        self.assertEqual(new['screening'],self.p['screening']);self.assertEqual(new['evidence'],[])

    def test_exact_document_candidate_work_schemas(self):
        for bad in (None,[],True,dict(self.c,schema_version=True),dict(self.c,schema_version=2),dict(self.c,extra=1),dict(self.c,candidates=[]),dict(self.c,candidates={}),dict(self.c,candidates=self.c['candidates']*101)):
            with self.subTest(bad=repr(bad)[:60]):self.reject(bad)
        for scope in ('candidate','work'):
            exemplar=self.c['candidates'][0] if scope=='candidate' else self.c['candidates'][0]['work_package']
            for field in exemplar:
                c=copy.deepcopy(self.c);row=c['candidates'][0];target=row if scope=='candidate' else row['work_package'];del target[field]
                with self.subTest(scope=scope,missing=field):self.reject(c)
            c=copy.deepcopy(self.c);row=c['candidates'][0];(row if scope=='candidate' else row['work_package'])['extra']=1;self.reject(c)

    def test_human_text_and_calendar_dates_required(self):
        for scope,fields in [('candidate',('proposed_by','proposed_at','proposal_note')),('work',('work_package_id','question','deliverable','acceptance_criterion'))]:
            for field in fields:
                for bad in (None,True,0,[],{},'', ' \t\n'):
                    c=copy.deepcopy(self.c);row=c['candidates'][0];(row if scope=='candidate' else row['work_package'])[field]=bad
                    with self.subTest(field=field,bad=bad):self.reject(c)
        for date in ('2026-02-29','2026-2-04','2026-11-04\n','0000-01-01'):
            c=copy.deepcopy(self.c);c['candidates'][0]['proposed_at']=date;self.reject(c)
        c=copy.deepcopy(self.c);c['candidates'][0]['proposed_at']='2024-02-29';intake.prepare(self.p,c)

    def test_source_refs_strict_known_and_unique(self):
        ref=self.c['candidates'][0]['work_package']['source_refs'][0]
        for refs in (None,[],{},True,'search-secondary',[ref,ref],[dict(ref,search_id='missing')],[dict(ref,extra=True)],
                     [dict(kind='record',record_id='missing')],[dict(kind='evidence',record_id='r1')],[dict(kind='planned_search')]):
            c=copy.deepcopy(self.c);c['candidates'][0]['work_package']['source_refs']=refs;self.reject(c)
        for field in ('kind','search_id'):
            for value in (None,True,3,[],{}):
                c=copy.deepcopy(self.c);c['candidates'][0]['work_package']['source_refs'][0][field]=value;self.reject(c)

    def test_no_evidence_completion_artifacts_or_priorities_can_enter(self):
        for field,value in [('work_type','evidence_review'),('work_type',None),('evidence_ids',['r1']),('evidence_ids',None),
                            ('status','COMPLETE'),('status','ACTIVE'),('status',None),('priority_rank',1),('artifact_locator','synthetic:note'),
                            ('acceptance_verified',True),('completion_basis_sha256','0'*64),('completion_review',{})]:
            c=copy.deepcopy(self.c);c['candidates'][0]['work_package'][field]=value
            with self.subTest(field=field,value=value):self.reject(c)

    def test_explicit_existing_same_batch_dependency_order_and_cycles(self):
        self.c=candidates(dependencies=['WP-EXTRACTION-REVIEW'])
        second=candidates('WP-FICTIONAL-SECOND',dependencies=['WP-FICTIONAL-NEW'])['candidates'][0]
        self.c['candidates'].insert(0,second)
        record=self.assembled();self.assertEqual(record['protocol_candidate']['gaps'][-2:],[r['work_package'] for r in self.c['candidates']])
        for deps in (None,'WP-RECEIPT-REVIEW',['missing'],['WP-FICTIONAL-NEW'],['WP-RECEIPT-REVIEW']*2,[True]):
            c=candidates();c['candidates'][0]['work_package']['depends_on']=deps;self.reject(c)
        c=copy.deepcopy(self.c);c['candidates'][1]['work_package']['depends_on']=['WP-FICTIONAL-SECOND'];self.reject(c)
        c=candidates();c['candidates'].append(copy.deepcopy(c['candidates'][0]));self.reject(c)
        self.reject(candidates('WP-RECEIPT-REVIEW'))

    def test_normalized_legacy_id_collision_without_rewriting_raw_prefix(self):
        self.p['gaps'][0].pop('work_package_id');self.p['gaps'][1]['depends_on']=['WP-001']
        self.reject(candidates('WP-001'))
        record=self.assembled(c=candidates(dependencies=['WP-001']))
        self.assertNotIn('work_package_id',record['protocol_candidate']['gaps'][0])
        self.assertEqual(record['protocol_candidate']['gaps'][:2],self.p['gaps'])

    def test_existing_planning_and_completion_bindings_remain_unchanged(self):
        self.p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic:note',acceptance_verified=True)
        before=run(self.p)
        binding=before['planning']['completion_ledger'][0]
        self.p['gaps'][0]['completion_basis_sha256']=binding['current_basis_sha256']
        target=before['planning']['review_targets'][0]
        self.p['planning_decisions']=[dict(work_package_id=target['work_package_id'],priority_rank=1,
            rationale='Fictional priority',uncertainty='No scientific priority established',planner='Fictional planner',
            planned_at='2026-11-04',basis_sha256=target['basis_sha256'])]
        before=run(self.p);new=self.assembled()['protocol_candidate'];after=run(new)
        self.assertEqual(new['planning_decisions'],self.p['planning_decisions']);self.assertEqual(new['gaps'][:2],self.p['gaps'])
        old_ids={w['work_package_id'] for w in before['work_packages']}
        for key in ('review_targets','completion_ledger'):
            self.assertEqual(before['planning'][key],[w for w in after['planning'][key] if w['work_package_id'] in old_ids])

    def test_whole_protocol_run_and_report_flow_before_after(self):
        with patch.object(intake,'run',wraps=run) as runs,patch.object(intake,'report_flow',wraps=report_flow) as flows:
            intake.prepare(self.p,self.c)
        self.assertEqual(runs.call_count,2);self.assertEqual(flows.call_count,2)
        for call in flows.call_args_list:self.assertIs(call.kwargs['include_csv'],False)
        p=copy.deepcopy(self.p);p.pop('adapter_receipts');p['searches'][0].pop('adapter_provenance')
        p['reports'][0]['retrieval']='invalid'
        run(p)  # Legacy scalar reports are not fully checked by run alone.
        self.reject(p=p)
        p=copy.deepcopy(self.p);p['evidence']=[None];self.reject(p=p)

    def test_blank_invalid_stale_review_no_automatic_rebase(self):
        review=self.review()
        for field in review:
            r=copy.deepcopy(review);r.pop(field)
            with self.subTest(missing=field),self.assertRaises(ValueError):intake.assemble(self.p,self.c,r)
        for field in ('receipt_id','reviewer','reviewed_at','rationale'):
            for value in (None,' ',True,[],{}):
                r=copy.deepcopy(review);r[field]=value
                with self.assertRaises(ValueError):intake.assemble(self.p,self.c,r)
        for changes in ({'schema_version':True},{'extra':1},{'decision':'approve'},{'target_sha256':'0'*64},{'reviewed_at':'2026-02-29'}):
            r=dict(review,**changes)
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,r)
        p=copy.deepcopy(self.p);p['opaque']='changed'
        with self.assertRaises(ValueError):intake.assemble(p,self.c,review)
        c=copy.deepcopy(self.c);c['candidates'][0]['proposal_note']='changed'
        with self.assertRaises(ValueError):intake.assemble(self.p,c,review)

    def test_entire_replay_rejects_unknown_resealed_and_typed_tampering(self):
        record=self.assembled()
        for mutate in (lambda a:a.update(extra=True),lambda a:a.update(schema_version=True),
                       lambda a:a['receipt'].update(extra=True),lambda a:a['receipt'].update(external_calls=False),
                       lambda a:a['protocol_candidate'].update(version='forged'),
                       lambda a:a['receipt']['target'].update(extra='forged'),
                       lambda a:a['receipt']['candidate_document']['candidates'][0].update(proposal_note='forged')):
            bad=copy.deepcopy(record);mutate(bad)
            bad['receipt']['receipt_sha256']=intake.digest({k:v for k,v in bad['receipt'].items() if k!='receipt_sha256'})
            with self.assertRaises(ValueError):intake.verify(self.p,bad)
        r=self.review();r.update(reviewer='Another fictional reviewer',receipt_id='rewritten')
        rewritten=intake.assemble(self.p,self.c,r)
        self.assertTrue(intake.verify(self.p,rewritten)['valid'])
        self.assertIn('unsigned',rewritten['receipt']['boundary'])

    def test_api_strict_json_and_byte_limits(self):
        for name,value in [('MAX_CANDIDATE_BYTES',10_000_000),('MAX_PROTOCOL_BYTES',50_000_000),('MAX_APPLICATION_BYTES',50_000_000),('MAX_CANDIDATES',100)]:self.assertEqual(getattr(intake,name),value)
        record=self.assembled()
        for name,action in [('MAX_CANDIDATE_BYTES',lambda:intake.prepare(self.p,self.c)),('MAX_PROTOCOL_BYTES',lambda:intake.prepare(self.p,self.c)),('MAX_APPLICATION_BYTES',lambda:intake.verify(self.p,record))]:
            with patch.object(intake,name,10),self.assertRaises(ValueError):action()
        for value in (float('nan'),float('inf'),{1:'non-string key'},('tuple',),{1,2},'\ud800'):
            p=copy.deepcopy(self.p);p['opaque']=value
            with self.assertRaises((ValueError,TypeError,UnicodeError)):intake.prepare(p,self.c)
        p=copy.deepcopy(self.p);p['cycle']=p
        with self.assertRaises((ValueError,TypeError,RecursionError)):intake.prepare(p,self.c)
        with patch.object(intake,'MAX_CANDIDATES',2):
            c=candidates();c['candidates'].append(candidates('WP-SECOND')['candidates'][0]);intake.prepare(self.p,c)
            c['candidates'].append(candidates('WP-THIRD')['candidates'][0]);self.reject(c)

    def test_no_source_opening_network_or_external_process(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('no network')),patch('socket.socket',side_effect=AssertionError('no network')),patch('subprocess.run',side_effect=AssertionError('no subprocess')):
            record=self.assembled();self.assertTrue(intake.verify(self.p,record)['valid'])
        self.assertIsInstance(intake.render_text(record),str)

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'source_work_intake.py'),*map(str,args)],cwd=ROOT,capture_output=True,env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))

    def test_cli_roundtrip_utf8_strict_json_and_no_overwrite(self):
        self.c['candidates'][0]['work_package']['question']='Fictional 합성\n\x1b[31m question'
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

    def test_output_preflight_rejects_dangling_directory_entry_before_open(self):
        # Model lstat succeeding on a dangling link even when exists() is false.
        # This runs on Windows without depending on symlink creation privileges.
        destination=Mock(spec=Path)
        destination.lstat.return_value=os.stat_result((stat.S_IFLNK | 0o777,0,0,1,0,0,0,0,0,0))
        destination.exists.return_value=False
        with self.assertRaises(FileExistsError):intake._write_new(destination,b'fictional output')
        destination.lstat.assert_called_once_with()
        destination.exists.assert_not_called()
        destination.open.assert_not_called()

    def test_output_preflight_propagates_inspection_failure_without_open(self):
        for error in (PermissionError('fictional inspection denied'),NotADirectoryError('fictional parent is not a directory'),OSError('fictional inspection failed')):
            with self.subTest(error=type(error).__name__):
                destination=Mock(spec=Path);destination.lstat.side_effect=error
                with self.assertRaises(type(error)) as caught:intake._write_new(destination,b'fictional output')
                self.assertIs(caught.exception,error)
                destination.lstat.assert_called_once_with()
                destination.open.assert_not_called()

    def test_cli_existing_and_dangling_symlink_outputs_not_followed(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'p.json';c=d/'c.json';target=d/'link.json';victim=d/'victim.json'
            p.write_bytes(canonical_json_bytes(self.p));c.write_bytes(canonical_json_bytes(self.c))
            try:target.symlink_to(victim)
            except (OSError,NotImplementedError):self.skipTest('symlinks unavailable on this platform')
            self.assertNotEqual(self.cli('target',p,c,'--output',target).returncode,0);self.assertFalse(victim.exists())
            victim.write_text('unchanged',encoding='utf-8')
            self.assertNotEqual(self.cli('target',p,c,'--output',target).returncode,0);self.assertEqual(victim.read_text(),'unchanged')

    def test_cli_small_input_limit_precedes_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'p.json';c=d/'c.json';out=d/'out.json'
            p.write_bytes(canonical_json_bytes(self.p));c.write_bytes(canonical_json_bytes(self.c))
            argv=['source_work_intake.py','target',str(p),str(c),'--output',str(out)]
            with patch.object(sys,'argv',argv),patch.object(intake,'configure_utf8_stdio'),patch.object(intake,'MAX_CANDIDATE_BYTES',10),patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):intake.main()
            self.assertFalse(out.exists())

    def test_cli_preflights_text_encoding_and_bounds_before_file_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);p=d/'p.json';c=d/'c.json';out=d/'out.json'
            p.write_bytes(canonical_json_bytes(self.p));c.write_bytes(canonical_json_bytes(self.c))
            argv=['source_work_intake.py','target',str(p),str(c),'--output',str(out),'--text']
            for rendered in ('x'*(intake.MAX_APPLICATION_BYTES+1),'\ud800'):
                with patch.object(sys,'argv',argv),patch.object(intake,'configure_utf8_stdio'),patch.object(intake,'render_text',return_value=rendered),patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):intake.main()
                self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
