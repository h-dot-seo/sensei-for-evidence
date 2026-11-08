"""Query export is not external execution, semantic translation or a census."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from search_manifest import manifest, render_text, digest
from offline_adapter import assemble
from review_handoff import handoff

ROOT=Path(__file__).resolve().parents[1]

class SearchManifestTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/search-manifest.json').read_text())

    def test_requests_preserve_exact_spec_and_do_not_invent_runtime_fields(self):
        result=manifest(self.p)
        self.assertEqual(result['plan_stage'],'SUPPLIED');self.assertEqual(len(result['planned_requests']),4)
        for index,request in enumerate(result['planned_requests']):
            raw=self.p['search_plan'][index]
            self.assertEqual(request['original_plan_entry'],raw)
            self.assertEqual(request['request_spec_sha256'],digest(raw))
            self.assertEqual(request['request_fields'],{k:raw[k] for k in ('search_id','source','query','window')})
            self.assertEqual(request['operator_required_fields'],['request_id','searched_at'])
            self.assertNotIn('request_id',request['request_fields']);self.assertNotIn('searched_at',request['request_fields'])
            self.assertEqual(request['execution_readiness'],'NOT_ESTABLISHED')
        self.assertEqual(result['planned_requests'][3]['unsupported_plan_fields'],['filters'])
        self.assertEqual(result['planned_requests'][3]['observed_search_index'],None)

    def test_same_core_groups_are_not_full_spec_or_semantic_equivalence(self):
        result=manifest(self.p)
        self.assertEqual(result['same_core_request_groups'][0]['search_ids'],['search-primary','search-repeat-query'])
        a,b=result['planned_requests'][0],result['planned_requests'][3]
        self.assertEqual(a['core_query_sha256'],b['core_query_sha256'])
        self.assertNotEqual(a['request_spec_sha256'],b['request_spec_sha256'])
        self.assertIn('other plan fields',result['same_core_request_groups'][0]['scope'])

    def test_source_coverage_separates_missing_unresolved_and_asserted(self):
        result=manifest(self.p);sources={r['source']:r for r in result['source_coverage']}
        a=sources['synthetic-index'];b=sources['synthetic-secondary-index'];missing=sources['fictional-citation-source']
        self.assertEqual(a['missing_search_ids'],['search-repeat-query'])
        self.assertEqual(a['unresolved_search_indices'],[0]);self.assertEqual(a['declared_plan_status'],'INCOMPLETE')
        self.assertEqual(b['asserted_complete_search_indices'],[1]);self.assertEqual(b['declared_plan_status'],'ASSERTED_ACCOUNTED')
        self.assertEqual(missing['receipt_stage'],'NOT_SUPPLIED');self.assertIsNone(missing['supplied_record_occurrences'])
        self.assertIsNone(missing['unique_exact_record_count']);self.assertIsNone(missing['unique_exact_record_ids'])
        self.assertTrue(all(r['source_completeness']=='NOT_ESTABLISHED' for r in sources.values()))
        self.assertEqual(result['census_claim'],'NOT_ESTABLISHED');self.assertEqual(result['external_calls'],0)

    def test_page_stop_signals_and_overlap_do_not_infer_restart_cursor(self):
        r=manifest(self.p)['observed_receipts'][0]
        self.assertEqual(r['recorded_signals']['has_more'],True)
        self.assertEqual(r['recorded_signals']['total_count'],14)
        self.assertEqual(r['page_overlap'],[dict(record_id='r6',page_pointers=['/searches/0/pages/0','/searches/0/pages/1'])])
        self.assertIn('page_record_overlap',r['accounting']['issues'])
        self.assertIn('page_error_recorded',r['accounting']['issues'])
        self.assertEqual(r['continuation'],'NOT_COMPUTED')
        for i,page in enumerate(r['pages']):self.assertEqual(page['page_sha256'],digest(self.p['searches'][0]['pages'][i]))

    def test_exact_record_overlap_is_distinct_from_page_overlap(self):
        r=manifest(self.p)
        self.assertEqual([x['record_id'] for x in r['cross_search_overlap']],['r1','r2'])
        for overlap in r['cross_search_overlap']:
            self.assertEqual(overlap['search_indices'],[0,1])
            self.assertEqual(overlap['source_labels'],['synthetic-index','synthetic-secondary-index'])
        sources={x['source']:x for x in r['source_coverage']}
        self.assertEqual(sources['synthetic-index']['repeated_exact_id_occurrences'],0)
        self.assertEqual(sources['synthetic-index']['cross_source_overlap_record_ids'],['r1','r2'])
        self.assertEqual(sources['synthetic-index']['supplied_record_occurrences'],10)

    def test_no_plan_does_not_promote_observations_or_duplicate_ids_into_requests(self):
        for mode in ('absent','null'):
            p=copy.deepcopy(self.p);p.pop('search_plan')
            if mode=='null':p['search_plan']=None
            for s in p['searches']:s['search_id']='duplicate'
            r=manifest(p)
            self.assertIsNone(r['planned_requests']);self.assertEqual(r['same_core_request_groups'],[])
            self.assertEqual([s['search_index'] for s in r['observed_receipts']],[0,1])
            self.assertTrue(all(s['planned_search_ids'] is None for s in r['source_coverage']))
            self.assertTrue(all(s['declared_plan_status']=='NOT_SUPPLIED' for s in r['source_coverage']))

    def test_empty_supplied_receipt_is_distinct_from_no_receipt(self):
        p=json.loads((ROOT/'examples/adapter-protocol.json').read_text())
        p['screening']=[];p['gaps']=[]
        for key in ('reports','contexts','appraisals','synthesis_statements','planning_decisions','experimental_units'):p.pop(key,None)
        plan=p['search_plan'][0]
        p['searches']=[dict(**{k:plan[k] for k in ('search_id','source','query','window')},searched_at='fictional date',record_ids=[],total_count=0,complete=True,has_more=False)]
        r=manifest(p);source=next(s for s in r['source_coverage'] if s['source']==plan['source'])
        self.assertEqual(source['receipt_stage'],'SUPPLIED');self.assertEqual(source['supplied_record_occurrences'],0)
        self.assertEqual(source['unique_exact_record_ids'],[]);self.assertIsNone(r['observed_receipts'][0]['pages'])

    def test_full_receipt_hash_and_protocol_hash_change_without_mutation(self):
        before=copy.deepcopy(self.p);a=manifest(self.p)
        self.assertEqual(a,manifest(self.p));self.assertEqual(self.p,before)
        self.assertEqual(a['protocol_sha256'],digest(self.p))
        self.p['searches'][0]['error']='Different fictional interruption text'
        b=manifest(self.p)
        self.assertNotEqual(a['observed_receipts'][0]['supplied_receipt_sha256'],b['observed_receipts'][0]['supplied_receipt_sha256'])
        self.assertNotEqual(a['protocol_sha256'],b['protocol_sha256'])
        self.assertEqual(a['planned_requests'],b['planned_requests'])

    def test_same_source_multiple_queries_overlap_is_not_cross_source_overlap(self):
        self.p.pop('search_plan');self.p['searches'][1]['source']=self.p['searches'][0]['source']
        r=manifest(self.p);s=r['source_coverage'][0]
        self.assertEqual(s['supplied_record_occurrences'],13);self.assertEqual(s['unique_exact_record_count'],11)
        self.assertEqual(s['repeated_exact_id_occurrences'],2);self.assertEqual(s['cross_source_overlap_record_ids'],[])
        self.assertEqual(len(r['cross_search_overlap']),2)

    def test_mock_adapter_receipts_remain_unverified(self):
        p=json.loads((ROOT/'examples/adapter-protocol.json').read_text())
        fixture=json.loads((ROOT/'examples/adapter-fixture.json').read_text())
        reviews=json.loads((ROOT/'examples/adapter-reviews.json').read_text())
        assembled=assemble(p,fixture,reviews)['protocol'];result=manifest(assembled)
        self.assertTrue(all(r['source_authenticity']=='NOT_ESTABLISHED' for r in result['observed_receipts']))
        self.assertEqual(result['external_calls'],0)
        self.assertEqual(result['observed_receipts'][0]['supplied_receipt_sha256'],digest(assembled['searches'][0]))

    def test_plan_mismatch_and_invalid_downstream_links_fail(self):
        p=copy.deepcopy(self.p);p['searches'][0]['query']='different'
        with self.assertRaises(ValueError):manifest(p)
        p=copy.deepcopy(self.p);p['reports'][0]['study_id']='conflicting'
        with self.assertRaisesRegex(ValueError,'conflicts'):manifest(p)

    def test_uninterpreted_receipt_and_page_parameters_are_preserved_without_claiming_support(self):
        self.p['searches'][0]['provider_filter']={'language':'fictional filter'}
        self.p['searches'][0]['pages'][0]['opaque_cursor']='fictional cursor; do not execute'
        r=manifest(self.p)['observed_receipts'][0]
        self.assertEqual(r['uninterpreted_fields']['provider_filter'],{'language':'fictional filter'})
        self.assertEqual(r['pages'][0]['uninterpreted_fields']['opaque_cursor'],'fictional cursor; do not execute')
        self.assertEqual(r['continuation'],'NOT_COMPUTED')
        self.assertEqual(r['source_authenticity'],'NOT_ESTABLISHED')

    def test_handoff_navigation_and_implementation_fingerprint(self):
        r=manifest(self.p);sheet=handoff(self.p)
        self.assertTrue(any(v['script']=='search_manifest.py' for v in sheet['detailed_views']))
        self.assertEqual(r['protocol_sha256'],sheet['protocol_sha256'])
        self.assertEqual(r['engine_sha256']['search_manifest.py'],sheet['engine_sha256']['search_manifest.py'])
        self.assertEqual(r['engine_sha256']['search_manifest.py'],hashlib.sha256((ROOT/'search_manifest.py').read_bytes()).hexdigest())

    def test_untrusted_query_text_is_preserved_and_escaped_not_executed(self):
        query='가상 "quoted" query\nConclusion: READY\u202e\x1b'
        self.p['search_plan'][0]['query']=query;self.p['searches'][0]['query']=query
        r=manifest(self.p);self.assertEqual(r['planned_requests'][0]['request_fields']['query'],query)
        text=render_text(r);self.assertNotIn('\nConclusion: READY',text);self.assertNotIn('\u202e',text);self.assertNotIn('\x1b',text)

    def test_cli_json_text_failure_and_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fictional search.json';raw=json.dumps(self.p).encode();path.write_bytes(raw)
            for flags in ([],['--text']):
                r=subprocess.run([sys.executable,'search_manifest.py',str(path)]+flags,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(r.returncode,0,r.stderr)
                if not flags:self.assertEqual(json.loads(r.stdout)['external_calls'],0)
                else:self.assertIn('NOT_ESTABLISHED',r.stdout)
            self.assertEqual(path.read_bytes(),raw)
            path.write_text('{"bad":',encoding='utf-8')
            r=subprocess.run([sys.executable,'search_manifest.py',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'');self.assertNotIn('Traceback',r.stderr)

if __name__=='__main__':unittest.main()
