"""Synthetic manual data entry never constitutes receipt or extraction approval."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from receipt_intake import template, check, render_text
from offline_adapter import assemble
from research_bundle import build_bundle
from review_handoff import handoff
ROOT=Path(__file__).resolve().parent

class ReceiptIntakeTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/adapter-protocol.json').read_text())
        self.f=json.loads((ROOT/'examples/manual-receipt-fixture.json').read_text())

    def test_template_preserves_queries_and_does_not_fabricate_receipt_facts(self):
        before=copy.deepcopy(self.p);f=template(self.p)
        self.assertEqual(f['mode'],'mock');self.assertIsNone(f['provider_id']);self.assertIsNone(f['adapter_version'])
        self.assertEqual(f['extraction_candidates'],[])
        for plan,response in zip(self.p['search_plan'],f['search_responses']):
            for k in ('search_id','source','query','window'):self.assertEqual(response['request'][k],plan[k])
            self.assertIsNone(response['request']['request_id']);self.assertIsNone(response['request']['searched_at'])
            self.assertTrue(all(v is None for v in response['pages'][0].values()))
        self.assertEqual(self.p,before)
        result=check(self.p,f);self.assertFalse(result['valid_input'])
        pointers={h['input_pointer'] for h in result['missing_field_hints']}
        self.assertIn('/search_responses/0/pages/0/records',pointers)
        self.assertIn('/provider_id',pointers)
        self.assertNotIn('protocol_candidate',result)

    def test_filled_interrupted_duplicate_receipts_stay_unreviewed(self):
        r=check(self.p,self.f)
        self.assertTrue(r['valid_input']);self.assertEqual(r['status'],'UNREVIEWED_SUPPLIED_CANDIDATES')
        self.assertTrue(r['review_pending']);self.assertEqual(r['protocol_candidate']['evidence'],[])
        self.assertEqual(r['protocol_candidate']['adapter_receipts']['reviews'],[])
        receipt=r['search_manifest']['observed_receipts'][0]
        self.assertFalse(receipt['recorded_signals']['complete'])
        self.assertIn('page_record_overlap',receipt['accounting']['issues'])
        self.assertIn('page_error_recorded',receipt['accounting']['issues'])
        self.assertIn('pagination_unresolved',receipt['accounting']['issues'])
        self.assertEqual(r['search_manifest']['search_plan_audit']['missing_search_ids'],['search-secondary'])
        self.assertEqual(r['external_calls'],0);self.assertEqual(r['conclusion_readiness'],'NOT_READY')

    def test_core_assembly_is_reused_without_automatic_approvals(self):
        r=check(self.p,self.f);expected=assemble(self.p,self.f)
        self.assertEqual(r['protocol_candidate'],expected['protocol'])
        self.assertEqual(r['review_pending'],expected['review_pending'])
        self.assertEqual(len(build_bundle(json.dumps(r['protocol_candidate']).encode()))>0,True)
        self.assertEqual(r['prisma_audit']['census_claim'],'NOT_ESTABLISHED')

    def test_existing_research_is_never_reset_or_imported_over(self):
        p=json.loads((ROOT/'examples/prisma-audit.json').read_text());before=copy.deepcopy(p)
        with self.assertRaisesRegex(ValueError,'separate base'):template(p)
        r=check(p,self.f);self.assertFalse(r['valid_input']);self.assertEqual(p,before)
        self.assertNotIn('protocol_candidate',r)

    def test_extraction_candidates_and_live_mode_are_rejected(self):
        f=json.loads((ROOT/'examples/adapter-fixture.json').read_text())
        r=check(self.p,f);self.assertFalse(r['valid_input']);self.assertIn('extraction_candidates=[]',r['validation_error'])
        f=copy.deepcopy(self.f);f['mode']='live'
        r=check(self.p,f);self.assertFalse(r['valid_input']);self.assertIn('only mock',r['validation_error'])

    def test_review_payloads_cannot_be_silently_mistaken_for_approval(self):
        for key in ('reviews','review_decisions'):
            f=copy.deepcopy(self.f);f[key]=[dict(decision='accept')]
            r=check(self.p,f)
            self.assertFalse(r['valid_input']);self.assertIn('does not accept review payloads',r['validation_error'])
            self.assertNotIn('protocol_candidate',r)
        f=copy.deepcopy(self.f);f['search_responses'][0]['pages'][0]['review_status']='opaque supplied metadata only'
        r=check(self.p,f);self.assertTrue(r['valid_input'])
        self.assertEqual(r['protocol_candidate']['adapter_receipts']['reviews'],[])
        self.assertFalse(r['protocol_candidate']['searches'][0]['complete'])

    def test_missing_record_provenance_and_template_hints_are_specific(self):
        f=copy.deepcopy(self.f);f['search_responses'][0]['pages'][0]['records'][0]['source_locator']=None
        r=check(self.p,f);self.assertFalse(r['valid_input'])
        self.assertIn('/search_responses/0/pages/0/records/0/source_locator',[h['input_pointer'] for h in r['missing_field_hints']])
        self.assertIn('source_locator',r['validation_error'])

    def test_wrong_shapes_conflicting_pages_and_queries_use_canonical_validation(self):
        for mutation in ('bad_request','bad_pages','bad_records','query','page_number','conflicting_locator'):
            f=copy.deepcopy(self.f);e=f['search_responses'][0]
            if mutation=='bad_request':e['request']=[]
            if mutation=='bad_pages':e['pages']=None
            if mutation=='bad_records':e['pages'][0]['records']=None
            if mutation=='query':e['request']['query']='different query'
            if mutation=='page_number':e['pages'][0]['page_number']=True
            if mutation=='conflicting_locator':e['pages'][1]['records'][0]['source_locator']='different fictional locator'
            with self.subTest(mutation=mutation):
                r=check(self.p,f);self.assertFalse(r['valid_input']);self.assertNotIn('protocol_candidate',r)

    def test_unknown_totals_are_retained_as_unresolved_not_invented(self):
        f=copy.deepcopy(self.f);f['search_responses'][0]['total_count']=None
        for page in f['search_responses'][0]['pages']:page.pop('total_count')
        r=check(self.p,f);self.assertTrue(r['valid_input'])
        receipt=r['search_manifest']['observed_receipts'][0]
        self.assertIsNone(receipt['recorded_signals']['total_count'])
        self.assertIn('total_count_not_nonnegative_integer',receipt['accounting']['issues'])

    def test_intentionally_empty_result_is_explicit_and_not_template_null(self):
        p=copy.deepcopy(self.p);p['screening']=[];p['reports']=[]
        f=copy.deepcopy(self.f);e=f['search_responses'][0];e['total_count']=0;e['pages']=e['pages'][:1]
        e['pages'][0].update(records=[],has_more=False,total_count=0)
        r=check(p,f);self.assertTrue(r['valid_input'])
        self.assertEqual(r['search_manifest']['observed_receipts'][0]['record_ids'],[])
        self.assertFalse(r['protocol_candidate']['searches'][0]['complete'])
        e['pages'][0]['records']=None
        self.assertFalse(check(p,f)['valid_input'])

    def test_determinism_hashes_and_source_nonmutation(self):
        p=copy.deepcopy(self.p);f=copy.deepcopy(self.f);a=check(self.p,self.f)
        self.assertEqual(a,check(self.p,self.f));self.assertEqual(self.p,p);self.assertEqual(self.f,f)
        self.assertEqual(a['engine_sha256']['receipt_intake.py'],hashlib.sha256((ROOT/'receipt_intake.py').read_bytes()).hexdigest())
        self.f['search_responses'][0]['pages'][0]['retrieved_at']='different supplied date'
        b=check(self.p,self.f);self.assertNotEqual(a['fixture_sha256'],b['fixture_sha256'])
        self.assertNotEqual(a['review_pending'],b['review_pending'])

    def test_text_escapes_supplied_values_and_error_messages(self):
        f=copy.deepcopy(self.f);f['search_responses'][0]['request']['query']='가상\nConclusion: READY\u202e\x1b'
        self.p['search_plan'][0]['query']=f['search_responses'][0]['request']['query']
        result=check(self.p,f);self.assertTrue(result['valid_input']);text=render_text(result)
        self.assertIn('가상',text)
        self.assertNotIn('\nConclusion: READY',text);self.assertNotIn('\u202e',text);self.assertNotIn('\x1b',text)

    def test_handoff_entry_is_separate_base_not_current_protocol_overwrite(self):
        p=json.loads((ROOT/'examples/claim-comparison.json').read_text());r=handoff(p)
        self.assertEqual(r['manual_input_workflow']['template_arguments'],['receipt_intake.py','template','BASE_PROTOCOL.json'])
        self.assertIn('do not erase',r['manual_input_workflow']['precondition'])
        self.assertIn('receipt_intake.py',r['engine_sha256'])

    def test_cli_template_check_export_audit_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);p=base/'base input.json';f=base/'filled receipts.json';out=base/'candidate.json'
            raw=json.dumps(self.p).encode();p.write_bytes(raw);f.write_text(json.dumps(self.f),encoding='utf-8')
            def invoke(args):return subprocess.run([sys.executable,'receipt_intake.py']+args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            t=invoke(['template',str(p)]);self.assertEqual(t.returncode,0,t.stderr)
            unfinished=base/'template.json';unfinished.write_text(t.stdout,encoding='utf-8')
            invalid=invoke(['check',str(p),str(unfinished),'--protocol-output',str(out)])
            self.assertNotEqual(invalid.returncode,0);self.assertFalse(json.loads(invalid.stdout)['valid_input']);self.assertFalse(out.exists())
            valid=invoke(['check',str(p),str(f),'--protocol-output',str(out)])
            self.assertEqual(valid.returncode,0,valid.stderr);self.assertEqual(json.loads(out.read_text())['evidence'],[])
            saved=out.read_bytes();duplicate=invoke(['check',str(p),str(f),'--protocol-output',str(out)])
            self.assertNotEqual(duplicate.returncode,0);self.assertEqual(out.read_bytes(),saved)
            audit=subprocess.run([sys.executable,'prisma_audit.py',str(out)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(audit.returncode,0,audit.stderr);self.assertEqual(json.loads(audit.stdout)['conclusion_readiness'],'NOT_READY')
            self.assertEqual(p.read_bytes(),raw)

if __name__=='__main__':unittest.main()
