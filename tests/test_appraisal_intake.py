"""Implementation-author synthetic appraisal intake and preservation regressions."""
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

import appraisal_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
import research_bundle

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


class AppraisalIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture('synthesis-review.json')
        self.c = fixture('manual-appraisal-candidates.json')

    def review(self, p=None, c=None):
        review = intake.prepare(self.p if p is None else p, self.c if c is None else c)['review_document']
        review.update(receipt_id='fictional-appraisal-import', decision='import_appraisals',
            reviewer='Fictional import reviewer', reviewed_at='2026-11-04', rationale='Record supplied fictional assertions only.')
        return review

    def assembled(self, p=None, c=None):
        p, c = self.p if p is None else p, self.c if c is None else c
        return intake.assemble(p, c, self.review(p, c))

    def reject(self, c, p=None):
        with self.assertRaises((ValueError, TypeError)):
            intake.prepare(self.p if p is None else p, c)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'appraisal_intake.py'), *map(str, args)],
            cwd=ROOT, capture_output=True, timeout=60,
            env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))

    def test_template_copies_only_selected_results_and_no_method_or_domain_meaning(self):
        refs = dict(schema_version=1, evidence_ids=['e2','e1'])
        old = copy.deepcopy((self.p, refs))
        result = intake.template(self.p, refs)
        row = result['candidate_document']['appraisals'][0]
        self.assertEqual(row['evidence_ids'], ['e2','e1'])
        self.assertEqual(row['domains'], [dict(name=None, judgement=None, rationale=None, source_locator=None)])
        self.assertTrue(all(v is None for k,v in row.items() if k not in ('evidence_ids','domains')))
        self.assertEqual((self.p, refs), old)
        self.assertEqual(result['selected_supplied_study_id'], 's1')
        self.assertFalse(result['protocol_changed'])
        self.reject(result['candidate_document'])

    def test_reference_schema_unknown_repeated_and_empty_ids_rejected(self):
        for refs in (None, [], {}, {'schema_version':True,'evidence_ids':['e1']},
                     {'schema_version':1,'evidence_ids':[]}, {'schema_version':1,'evidence_ids':['e1','e1']},
                     {'schema_version':1,'evidence_ids':['r1']}, {'schema_version':1,'evidence_ids':['missing']},
                     {'schema_version':1,'evidence_ids':['e1'],'extra':True}):
            with self.subTest(refs=refs), self.assertRaises((ValueError,TypeError)):
                intake.template(self.p, refs)

    def test_separate_blank_import_review_and_deterministic_preparation(self):
        old = copy.deepcopy((self.p,self.c))
        target = intake.prepare(self.p,self.c)
        self.assertEqual(target,intake.prepare(self.p,self.c))
        self.assertEqual((self.p,self.c),old)
        self.assertTrue(all(v is None for k,v in target['review_document'].items() if k not in ('schema_version','target_sha256')))
        with self.assertRaises(ValueError): intake.assemble(self.p,self.c,target['review_document'])
        self.assertEqual(target['target']['source_context_scope'],'MAPPED_CATALOG_CONTEXT_NOT_SELECTED_OR_READ_DOCUMENTS')

    def test_only_appraisals_append_and_raw_existing_assertions_are_preserved(self):
        self.p['opaque'] = {'β':[1,True,None],'literal':'\n  preserve '}
        old=copy.deepcopy(self.p);app=self.assembled();after=app['protocol_candidate']
        self.assertEqual(after['appraisals'][:len(old['appraisals'])],old['appraisals'])
        self.assertEqual(after['appraisals'][len(old['appraisals']):],self.c['appraisals'])
        self.assertEqual({k:v for k,v in after.items() if k!='appraisals'},{k:v for k,v in old.items() if k!='appraisals'})
        self.assertEqual(self.p,old)
        self.assertEqual(app['receipt']['before_flow'],app['receipt']['after_flow'])
        self.assertEqual(app['receipt']['before_report_flow'],app['receipt']['after_report_flow'])
        self.assertEqual(app['receipt']['before_appraisal_count'],1);self.assertEqual(app['receipt']['after_appraisal_count'],3)
        self.assertTrue(intake.verify(old,app)['valid'])

    def test_conflicting_appraisals_remain_separate_and_uncited_sibling_unappraised(self):
        app=self.assembled();research=run(app['protocol_candidate'])
        e1=[r for r in research['appraisal']['appraisal_ledger'] if 'e1' in r['evidence_ids']]
        self.assertEqual(len(e1),2)
        self.assertNotEqual(e1[0]['domains'][0]['judgement'],e1[1]['domains'][0]['judgement'])
        self.assertEqual(research['appraisal']['evidence_without_recorded_appraisal'],['e3'])
        self.assertEqual(app['receipt']['target']['before_unappraised_evidence_ids'],['e2','e3'])
        self.assertEqual(app['receipt']['target']['after_unappraised_evidence_ids'],['e3'])
        self.assertEqual(research['conclusion_readiness'],'NOT_READY')
        self.assertEqual(app['receipt']['quality_scoring'],'NOT_PERFORMED')
        self.assertEqual(app['receipt']['consensus'],'NOT_INFERRED')

    def test_missing_and_empty_appraisal_ledgers_supported_without_rewriting_other_input(self):
        for present in (False,True):
            p=copy.deepcopy(self.p)
            if present:p['appraisals']=[]
            else:p.pop('appraisals')
            app=self.assembled(p)
            self.assertEqual(app['receipt']['before_appraisal_count'],0)
            self.assertEqual(len(app['protocol_candidate']['appraisals']),2)
            self.assertEqual('appraisals' in p,present)
            self.assertTrue(intake.verify(p,app)['valid'])

    def test_existing_and_candidate_id_collisions_never_replace(self):
        c=copy.deepcopy(self.c);c['appraisals'][0]['appraisal_id']=self.p['appraisals'][0]['appraisal_id'];self.reject(c)
        c=copy.deepcopy(self.c);c['appraisals'][1]['appraisal_id']=c['appraisals'][0]['appraisal_id'];self.reject(c)

    def test_same_reviewer_method_or_domain_text_does_not_merge_distinct_records(self):
        c=copy.deepcopy(self.c);c['appraisals'][1]=copy.deepcopy(c['appraisals'][0]);c['appraisals'][1]['appraisal_id']='separate-id'
        app=self.assembled(c=c);self.assertEqual(len(app['protocol_candidate']['appraisals']),3)
        self.assertEqual(app['protocol_candidate']['appraisals'][-2]['domains'],app['protocol_candidate']['appraisals'][-1]['domains'])

    def test_cross_study_template_and_single_appraisal_rejected_but_separate_rows_allowed(self):
        p=fixture('result-source-current.json');c=copy.deepcopy(self.c)
        c['appraisals'][0]['evidence_ids']=['result-A','result-B'];c['appraisals'][1]['evidence_ids']=['result-A']
        self.reject(c,p)
        with self.assertRaisesRegex(ValueError,'one supplied study ID'):
            intake.template(p,dict(schema_version=1,evidence_ids=['result-A','result-B']))
        c['appraisals'][0]['evidence_ids']=['result-A'];c['appraisals'][1]['evidence_ids']=['result-B']
        self.assertTrue(intake.verify(p,self.assembled(p,c))['valid'])

    def test_legacy_result_identity_is_exposed_not_materialized(self):
        p=fixture('context-protocol.json');c=copy.deepcopy(self.c);c['appraisals']=c['appraisals'][:1];c['appraisals'][0]['evidence_ids']=['r1']
        app=self.assembled(p,c);selected=app['receipt']['target']['selected_evidence'][0]
        self.assertEqual(selected['identity_origin'],'LEGACY_RECORD_ID')
        self.assertEqual(selected['input_pointer'],'/evidence/0')
        self.assertNotIn('evidence_id',app['protocol_candidate']['evidence'][0])

    def test_explicit_result_ids_do_not_accept_record_report_or_study_substitutes(self):
        for ids in (['r1'],['report-1'],['s1'],['e1','e1'],[],['missing']):
            c=copy.deepcopy(self.c);c['appraisals'][0]['evidence_ids']=ids;self.reject(c)

    def test_selected_raw_rows_pointers_and_full_mapped_catalog_are_preserved(self):
        p=fixture('result-source-current.json');c=copy.deepcopy(self.c)
        for r in c['appraisals']:r['evidence_ids']=['result-A']
        target=self.assembled(p,c)['receipt']['target']
        self.assertEqual([r['output_pointer'] for r in target['appended_appraisals']],['/appraisals/0','/appraisals/1'])
        self.assertEqual(len(target['selected_evidence']),2)
        for r in target['selected_evidence']:
            self.assertEqual(r['raw_evidence'],p['evidence'][0]);self.assertEqual(r['identity_origin'],'EXPLICIT_EVIDENCE_ID')
        report=target['mapped_report_source_targets'][0]
        self.assertEqual(report['report_id'],'report-one')
        self.assertEqual(report['source_basis']['report_sources'],p['report_sources'][:2])
        self.assertEqual(target['selected_record_targets'][0]['record_id'],'record-one')

    def test_synthesis_current_review_stales_without_new_support_or_reviewer(self):
        self.assertEqual(run(self.p)['synthesis']['statement_ledger'][0]['source_match_status'],'CURRENT_SOURCE')
        app=self.assembled();after=run(app['protocol_candidate'])
        self.assertEqual(app['protocol_candidate']['synthesis_statements'],self.p['synthesis_statements'])
        self.assertEqual(after['synthesis']['statement_ledger'][0]['source_match_status'],'STALE_SOURCE')
        self.assertEqual(after['synthesis']['statement_ledger'][0]['support_status'],'NOT_ASSESSED')
        self.assertEqual(after['synthesis']['statement_ledger'][1]['source_match_status'],'PENDING_REVIEW')
        changes=app['receipt']['derived_source_status_changes']['synthesis']
        self.assertEqual([r['statement_id'] for r in changes],['statement-1','statement-2'])

    def test_current_planning_ranks_stale_without_reprioritization(self):
        p=fixture('planning-review.json');self.assertEqual({r['source_match_status'] for r in run(p)['planning']['planning_ledger']},{'CURRENT_SOURCE'})
        app=self.assembled(p);after=run(app['protocol_candidate'])
        self.assertEqual(app['protocol_candidate']['planning_decisions'],p['planning_decisions'])
        self.assertEqual({r['source_match_status'] for r in after['planning']['planning_ledger']},{'STALE_SOURCE'})
        self.assertEqual(after['planning']['current_rank_groups'],[])
        self.assertEqual(after['work_packages'],run(p)['work_packages'])

    def test_completed_work_stales_but_remains_complete_and_unblocks_as_before(self):
        p=fixture('completion-binding.json');app=self.assembled(p);after=run(app['protocol_candidate'])
        self.assertEqual(app['protocol_candidate']['gaps'],p['gaps'])
        row=next(r for r in after['planning']['completion_ledger'] if r['work_package_id']=='WP-MECHANISM')
        self.assertEqual(row['source_match_status'],'STALE_SOURCE')
        self.assertEqual(after['work_packages'][0]['status'],'COMPLETE')
        self.assertEqual(after['work_packages'][1]['blocked_by'],[])
        self.assertEqual(row['acceptance_assessment'],'NOT_PERFORMED')

    def test_unlinked_source_work_basis_and_old_appraisal_literal_extras_are_unchanged(self):
        p=copy.deepcopy(self.p);p['appraisals'][0]['opaque_assertion']={'literal':True}
        p['gaps'].append(dict(work_package_id='WP-SOURCE-ONLY',work_type='source_review',question='Fictional source scope?',deliverable='Fictional note',acceptance_criterion='Human checks provenance.',evidence_ids=[],source_refs=[dict(kind='record',record_id='r1')]))
        app=self.assembled(p);self.assertEqual(app['protocol_candidate']['appraisals'][0],p['appraisals'][0])
        changes=app['receipt']['derived_source_status_changes']
        self.assertNotIn('WP-SOURCE-ONLY',[r['work_package_id'] for r in changes['planning']])

    def test_strict_candidate_appraisal_and_domain_schema_types_and_dates(self):
        for bad in (None,[],{},True,dict(self.c,schema_version=True),dict(self.c,schema_version=2),dict(self.c,extra=1),dict(self.c,appraisals=[])):
            self.reject(bad)
        for field in intake.APPRAISAL_FIELDS:
            c=copy.deepcopy(self.c);c['appraisals'][0].pop(field);self.reject(c)
        for key,value in [('extra',True),('assessed_at','2026-02-30'),('assessed_at','2026-1-04'),('domains',[]),('domains',[{}])]:
            c=copy.deepcopy(self.c);c['appraisals'][0][key]=value;self.reject(c)
        for field in intake.APPRAISAL_FIELDS-{'evidence_ids','domains'}:
            for value in (None,True,1,' ',{},[]):
                c=copy.deepcopy(self.c);c['appraisals'][0][field]=value;self.reject(c)
        for field in intake.DOMAIN_FIELDS:
            c=copy.deepcopy(self.c);c['appraisals'][0]['domains'][0][field]=' ';self.reject(c)
        c=copy.deepcopy(self.c);c['appraisals'][0]['domains'][0]['score']=1;self.reject(c)
        c=copy.deepcopy(self.c);c['appraisals'][0]['domains']*=2;self.reject(c)

    def test_inclusive_appraisal_and_domain_counts(self):
        c=copy.deepcopy(self.c);row=c['appraisals'][0]
        c['appraisals']=[dict(copy.deepcopy(row),appraisal_id='new-%03d'%i) for i in range(100)]
        self.assertEqual(len(intake.prepare(self.p,c)['target']['appended_appraisals']),100)
        c['appraisals'].append(dict(row,appraisal_id='over-limit'));self.reject(c)
        c=copy.deepcopy(self.c);domain=c['appraisals'][0]['domains'][0]
        c['appraisals'][0]['domains']=[dict(domain,name='domain-%03d'%i) for i in range(100)]
        self.assertTrue(intake.prepare(self.p,c))
        c['appraisals'][0]['domains'].append(dict(domain,name='over-limit'));self.reject(c)

    def test_whole_input_candidate_and_implementation_changes_invalidate_review(self):
        review=self.review();p=copy.deepcopy(self.p);p['opaque']='new'
        with self.assertRaisesRegex(ValueError,'no automatic rebase'):intake.assemble(p,self.c,review)
        c=copy.deepcopy(self.c);c['appraisals'][0]['limitations']='changed'
        with self.assertRaisesRegex(ValueError,'no automatic rebase'):intake.assemble(self.p,c,review)
        hashes=intake._implementation_hashes();hashes['appraisal_intake.py']='0'*64
        with patch.object(intake,'_implementation_hashes',return_value=hashes):
            with self.assertRaisesRegex(ValueError,'no automatic rebase'):intake.assemble(self.p,self.c,review)

    def test_strict_review_and_wrong_kind_rejected(self):
        review=self.review()
        for key,value in [('schema_version',True),('decision','approve'),('reviewer',''),('reviewed_at','2026-02-30'),('target_sha256','A'*64),('extra',1)]:
            with self.assertRaises(ValueError):intake.assemble(self.p,self.c,dict(review,**{key:value}))
        app=self.assembled();app['kind']='detached_result_intake'
        with self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_resealed_tampering_cannot_hide_changed_judgement_or_review_cues(self):
        original=self.assembled()
        for part in ('output','snapshot','cue','claim'):
            app=copy.deepcopy(original)
            if part=='output':app['protocol_candidate']['appraisals'][-1]['domains'][0]['judgement']='changed'
            if part=='snapshot':app['receipt']['target']['selected_evidence'][0]['raw_evidence']['result']='changed'
            if part=='cue':app['receipt']['derived_source_status_changes']['synthesis']=[]
            if part=='claim':app['receipt']['quality_scoring']='VERIFIED'
            app['receipt']['receipt_sha256']=intake.digest({k:v for k,v in app['receipt'].items() if k!='receipt_sha256'})
            with self.subTest(part=part),self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_consistently_reauthored_unsigned_reviewer_is_not_authenticated(self):
        app=self.assembled();app['receipt']['assertion']['reviewer']='Different supplied reviewer label'
        app['receipt']['receipt_sha256']=intake.digest({k:v for k,v in app['receipt'].items() if k!='receipt_sha256'})
        checked=intake.verify(self.p,app)
        self.assertTrue(checked['valid'])
        self.assertEqual(checked['reviewer_identity_verification'],'NOT_ESTABLISHED')

    def test_size_limits_nonfinite_values_and_detached_mutation(self):
        for constant in ('MAX_CANDIDATE_BYTES','MAX_PROTOCOL_BYTES','MAX_APPLICATION_BYTES'):
            with patch.object(intake,constant,1):
                with self.assertRaisesRegex(ValueError,'byte limit'):intake.prepare(self.p,self.c)
        p=copy.deepcopy(self.p);p['opaque']=float('nan');self.reject(self.c,p)
        old=copy.deepcopy((self.p,self.c));app=self.assembled();app['protocol_candidate']['appraisals'][0]['method']='mutated';app['receipt']['target']['selected_evidence'][0]['raw_evidence']['result']='mutated'
        self.assertEqual((self.p,self.c),old)

    def test_no_source_lookup_and_text_control_injection(self):
        c=copy.deepcopy(self.c);c['appraisals'][0]['method_locator']='https://invalid.example/not-fetched';c['appraisals'][0]['domains'][0]['source_locator']='/does/not/exist'
        c['appraisals'][0]['domains'][0]['rationale']='가상\nConclusion: READY\u202e\x1b'
        with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')):
            app=self.assembled(c=c);text=intake.render_text(app)
        for bad in ('\nConclusion: READY','\u202e','\x1b'):self.assertNotIn(bad,text)
        self.assertIn('가상',text);self.assertEqual(app['receipt']['external_calls'],0)

    def test_mock_adapter_integrity_is_preserved(self):
        import offline_adapter
        p=offline_adapter.assemble(fixture('adapter-protocol.json'),fixture('adapter-fixture.json'),fixture('adapter-reviews.json'))['protocol']
        app=self.assembled(p);self.assertEqual(app['protocol_candidate']['adapter_receipts'],p['adapter_receipts'])
        self.assertEqual(run(app['protocol_candidate'])['evidence'],run(p)['evidence'])
        self.assertTrue(intake.verify(p,app)['valid'])

    def test_csv_collection_and_absent_reports_are_preserved(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        helper=BibliographicReviewTests();helper.setUp();p=helper.imported()
        p['screening']=[dict(record_id='synthetic-record-1',decision='include',reason='Fictional scope')]
        row=copy.deepcopy(self.p['evidence'][0]);row.update(record_id='synthetic-record-1',evidence_id='csv-result');p['evidence']=[row]
        c=copy.deepcopy(self.c);c['appraisals']=c['appraisals'][:1];c['appraisals'][0]['evidence_ids']=['csv-result']
        app=self.assembled(p,c);self.assertNotIn('reports',app['protocol_candidate'])
        self.assertEqual(app['receipt']['target']['mapped_report_source_targets'],[])
        self.assertEqual(run(app['protocol_candidate'])['bibliographic_collection'],run(p)['bibliographic_collection'])
        self.assertTrue(intake.verify(p,app)['valid'])

    def test_invalid_whole_protocol_rejected_and_empty_results_cannot_be_filled(self):
        p=copy.deepcopy(self.p);p['screening'][0]['decision']='invalid';self.reject(self.c,p)
        p=fixture('bibliographic-base.json');self.reject(self.c,p)
        with self.assertRaises(ValueError):intake.template(p,dict(schema_version=1,evidence_ids=['invented']))

    def test_implementation_map_covers_used_helpers(self):
        for name in ('appraisal_intake.py','nbib_intake.py','report_review_links.py','screening_links.py','appraisal_links.py'):
            self.assertEqual(intake._implementation_hashes()[name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())

    def test_bundle_keeps_appraisals_but_not_detached_import_record(self):
        import zipfile
        app=self.assembled();raw=research_bundle.build_bundle(json.dumps(app['protocol_candidate']).encode())
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(json.loads(z.read('protocol.json'))['appraisals'],app['protocol_candidate']['appraisals'])
            self.assertNotIn('appraisal-application.json',z.namelist())
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bundle.zip';p.write_bytes(raw);self.assertTrue(research_bundle.verify(p)['valid'])

    def test_cli_roundtrip_utf8_exclusive_outputs_and_replay_before_export(self):
        with tempfile.TemporaryDirectory(prefix='appraisal cli ') as td:
            d=Path(td);p=d/'p.json';c=d/'c.json';refs=d/'refs.json';p.write_bytes(json.dumps(self.p).encode());c.write_bytes(json.dumps(self.c).encode());refs.write_bytes(json.dumps(dict(schema_version=1,evidence_ids=['e1'])).encode())
            draft=d/'draft.json';target=d/'target.json';review=d/'review.json';app=d/'app.json';out=d/'out.json'
            for args in [('template',p,refs,'--candidate-output',draft),('target',p,c,'--output',target,'--text')]:
                result=self.cli(*args);self.assertEqual(result.returncode,0,result.stderr)
            review.write_bytes(json.dumps(self.review()).encode())
            for args in [('assemble',p,c,review,'--output',app),('verify',p,app,'--protocol-output',out)]:
                result=self.cli(*args);self.assertEqual(result.returncode,0,result.stderr)
            before=out.read_bytes();self.assertNotEqual(self.cli('verify',p,app,'--protocol-output',out).returncode,0);self.assertEqual(out.read_bytes(),before)
            value=json.loads(app.read_bytes());value['receipt']['receipt_sha256']='0'*64;app.write_bytes(json.dumps(value).encode())
            bad=d/'blocked.json';self.assertNotEqual(self.cli('verify',p,app,'--protocol-output',bad).returncode,0);self.assertFalse(bad.exists())

    def test_cli_duplicate_json_symlink_and_preflight_refusals(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);p=d/'p.json';c=d/'c.json';out=d/'out.json';p.write_bytes(json.dumps(self.p).encode());c.write_bytes(b'{"schema_version":1,"schema_version":1}')
            self.assertNotEqual(self.cli('target',p,c,'--output',out).returncode,0);self.assertFalse(out.exists())
            c.write_bytes(json.dumps(self.c).encode())
            try:out.symlink_to(d/'absent')
            except (OSError,NotImplementedError):pass
            else:
                self.assertNotEqual(self.cli('target',p,c,'--output',out).returncode,0);self.assertTrue(out.is_symlink());out.unlink()
            argv=['appraisal_intake.py','target',str(p),str(c),'--output',str(out),'--text']
            with patch.object(sys,'argv',argv),patch.object(intake,'configure_utf8_stdio'),patch.object(intake,'render_text',side_effect=ValueError('synthetic preflight failure')),patch.object(sys,'stderr',io.StringIO()):
                with self.assertRaises(SystemExit):intake.main()
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
