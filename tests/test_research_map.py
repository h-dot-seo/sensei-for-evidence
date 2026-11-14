"""Standalone map records never promote supplied stopping statements to research findings."""
import copy
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import research_map as m
from evidence_workflow import run
from research_bundle import ENGINE_FILES,build_bundle
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]

class ResearchMapTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/bibliographic-base.json').read_bytes())
        self.d=json.loads((ROOT/'examples/research-map-sidecar.json').read_bytes())

    def test_template_nulls_and_empty_record_stage(self):
        t=m.template(self.p)
        self.assertTrue(all(v is None for v in t['draft']['research_map'].values()))
        self.assertTrue(all(v is None for v in t['record_template'].values()))
        self.assertTrue(all(v is None for v in t['event_template'].values()))
        self.assertEqual(t['source_context'],{k:self.p[k] for k in m.CORE_FIELDS})
        with self.assertRaises(ValueError):m.review(self.p,t['draft'])
        self.d.update(records=[],stop_events=[])
        r=m.review(self.p,self.d)
        self.assertEqual(r['record_stage'],'NOT_SUPPLIED');self.assertEqual(r['current_record_ids'],[])

    def test_current_stale_and_all_records_retained_without_selection(self):
        before=copy.deepcopy((self.p,self.d));r=m.review(self.p,self.d)
        self.assertEqual(r['current_record_ids'],['map-record-A'])
        stale=copy.deepcopy(self.d['records'][0]);stale.update(record_id='old',basis_sha256='0'*64)
        self.d['records'].insert(0,stale);r=m.review(self.p,self.d)
        self.assertEqual(r['stale_record_ids'],['old']);self.assertEqual([x['record']['record_id'] for x in r['records']],['old','map-record-A'])
        self.assertEqual(r['stop_events'][0]['source_match_status'],'CURRENT_SOURCE')
        r['research_map']['decision_scope']='mutated output'
        self.assertNotEqual(self.d['research_map']['decision_scope'],'mutated output')
        self.assertEqual(self.p,before[0]);self.assertEqual(self.d['records'][1],before[1]['records'][0])

    def test_core_and_map_changes_stale_records_and_events(self):
        for field in ('question','inclusion_criteria','exclusion_criteria','search_plan'):
            p=copy.deepcopy(self.p)
            if field=='question':p[field]+=' changed'
            elif field=='search_plan':p[field][0]['query']+=' changed'
            else:p[field].append('Supplied changed criterion')
            r=m.review(p,self.d)
            self.assertEqual(r['stale_record_ids'],['map-record-A']);self.assertEqual(r['stop_events'][0]['source_match_status'],'STALE_SOURCE')
        for field in ('decision_scope','challenge_plan'):
            d=copy.deepcopy(self.d);d['research_map'][field]+=' changed';self.assertEqual(m.review(self.p,d)['stale_record_ids'],['map-record-A'])
        d=copy.deepcopy(self.d);d['research_map']['stop_rules'][0]['rule']='different supplied rule'
        self.assertEqual(m.review(self.p,d)['stop_events'][0]['source_match_status'],'STALE_SOURCE')

    def test_version_records_events_excluded_from_scope_but_full_replay_binds_them(self):
        r=m.review(self.p,self.d)
        p=copy.deepcopy(self.p);p['version']='changed-version'
        changed=m.review(p,self.d)
        self.assertEqual(changed['current_basis_sha256'],r['current_basis_sha256'])
        self.assertNotEqual(changed['protocol_sha256'],r['protocol_sha256'])
        self.assertFalse(m.verify(p,self.d,r)['valid'])
        d=copy.deepcopy(self.d);d['stop_events'][0]['note']='other supplied event note'
        changed=m.review(self.p,d);self.assertEqual(changed['current_basis_sha256'],r['current_basis_sha256'])
        self.assertFalse(m.verify(self.p,d,r)['valid'])
        self.assertTrue(m.verify(self.p,self.d,r)['valid'])
        for key,value in [('conclusion_readiness','READY'),('current_record_ids',[]),('implementation_sha256',{})]:
            bad=copy.deepcopy(r);bad[key]=value;self.assertFalse(m.verify(self.p,self.d,bad)['valid'])
        with patch.object(m,'_hashes',return_value={'synthetic':'changed'}):self.assertFalse(m.verify(self.p,self.d,r)['valid'])

    def test_exact_shapes_blank_dates_duplicate_and_unknown_ids_reject(self):
        paths=[(),('research_map',),('records',0),('stop_events',0),('research_map','stop_rules',0),('research_map','evidence_classes',0),('research_map','appraisal_plan',0)]
        for path in paths:
            def at(d):
                for key in path:d=d[key]
                return d
            for key in at(self.d):
                d=copy.deepcopy(self.d);del at(d)[key]
                with self.assertRaises(ValueError):m.review(self.p,d)
            d=copy.deepcopy(self.d);at(d)['unexpected']=True
            with self.assertRaises(ValueError):m.review(self.p,d)
        for path,value in [(('schema_version',),True),(('schema_version',),1.0),(('records',0,'recorder'),' '),
                           (('records',0,'recorded_at'),'2026-02-30'),(('records',0,'basis_sha256'),'0'*64+'\n'),
                           (('stop_events',0,'record_id'),'missing'),(('stop_events',0,'search_id'),'missing'),
                           (('stop_events',0,'stop_rule_id'),'missing'),(('research_map','stop_rules',0,'applies_to'),'missing'),
                           (('research_map','appraisal_plan',0,'evidence_class'),'missing')]:
            d=copy.deepcopy(self.d);node=d
            for key in path[:-1]:node=node[key]
            node[path[-1]]=value
            with self.assertRaises(ValueError):m.review(self.p,d)
        for path in [('records',),('stop_events',),('research_map','stop_rules'),('research_map','evidence_classes')]:
            d=copy.deepcopy(self.d);node=d
            for key in path:node=node[key]
            node.append(copy.deepcopy(node[0]))
            with self.assertRaises(ValueError):m.review(self.p,d)

    def test_unknown_or_ambiguous_plan_and_rule_scope_rejected(self):
        p=copy.deepcopy(self.p);p['search_plan'].append(copy.deepcopy(p['search_plan'][0]))
        with self.assertRaises(ValueError):m.review(p,self.d)
        p=copy.deepcopy(self.p);p['search_plan'].append(dict(p['search_plan'][0],search_id='other'))
        d=copy.deepcopy(self.d);d['stop_events'][0]['search_id']='other'
        with self.assertRaises(ValueError):m.review(p,d)
        d['research_map']['stop_rules'][0]['applies_to']='ALL'
        r=m.review(p,d);self.assertEqual(r['planned_searches_without_stop_rule'],[])
        self.assertEqual(r['stop_events'][0]['source_match_status'],'STALE_SOURCE')

    def test_engine_bundle_and_protocol_unchanged_and_stops_not_complete(self):
        raw=json.dumps(self.p).encode();original=copy.deepcopy(self.p)
        before=run(self.p);bundle_before=build_bundle(raw)
        r=m.review(self.p,self.d);after=run(self.p)
        self.assertEqual(before,after);self.assertEqual(build_bundle(raw),bundle_before);self.assertEqual(self.p,original)
        self.assertNotIn('research_map.py',ENGINE_FILES)
        self.assertEqual(r['conclusion_readiness'],'NOT_READY');self.assertEqual(r['census_claim'],'NOT_ESTABLISHED')
        self.assertEqual(r['search_execution'],'NOT_PERFORMED');self.assertEqual(r['engine_integration'],'NOT_IMPLEMENTED')
        self.assertEqual(r['input_observation']['identified_occurrences'],0)
        self.assertEqual(r['stop_events'][0]['observation'],'SUPPLIED_STOP_STATEMENT_NOT_EXECUTION')
        self.assertEqual(before['flow']['identified'],0)

    def test_bounds_and_replay_type_difference(self):
        with patch.object(m,'MAX_DOCUMENT_BYTES',10):
            with self.assertRaises(ValueError):m.review(self.p,self.d)
        with patch.object(m,'MAX_ROWS',0):
            with self.assertRaises(ValueError):m.review(self.p,self.d)
        deep={};node=deep
        for _ in range(130):node['extra']={};node=node['extra']
        with self.assertRaises(ValueError):m._normalize(deep,10000)
        r=m.review(self.p,self.d);r['schema_version']=True
        self.assertFalse(m.verify(self.p,self.d,r)['valid'])

    def test_documented_real_cli_journey_and_exclusive_output(self):
        blocks=re.findall(r'```sh\n(.*?)```',(ROOT/'docs/RESEARCH_MAP.md').read_text(),re.S)
        self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory(prefix='map rehearsal ') as td:
            for line in blocks[0].strip().splitlines():
                args=shlex.split(line);self.assertEqual(args.pop(0),'python')
                args=[str(Path(td)/a[len('/outside/'):]) if a.startswith('/outside/') else a for a in args]
                result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout)['conclusion_readiness'],'NOT_READY')
            path=Path(td)/'map-review.json';old=path.read_bytes()
            result=run_cli('research_map.py','review',ROOT/'examples/bibliographic-base.json',ROOT/'examples/research-map-sidecar.json','--output',path,cwd=td)
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertEqual(path.read_bytes(),old)
            report=json.loads(old);report['assessment']='ASSESSSED';path.write_bytes(json.dumps(report).encode())
            result=run_cli('research_map.py','verify',ROOT/'examples/bibliographic-base.json',ROOT/'examples/research-map-sidecar.json',path,cwd=td)
            self.assertEqual(result.returncode,1);self.assertEqual(result.stderr,b'');self.assertFalse(json.loads(result.stdout)['valid'])

    def test_cli_strict_json_errors_no_output_or_sensitive_echo(self):
        with tempfile.TemporaryDirectory(prefix='private-map ') as td:
            bad=Path(td)/'private-map.json';output=Path(td)/'out.json'
            for raw in [b'\xff',b'{"private-map":1,"private-map":2}',b'null',b'{"private-map":NaN}']:
                bad.write_bytes(raw)
                result=run_cli('research_map.py','review',ROOT/'examples/bibliographic-base.json',bad,'--output',output,cwd=ROOT)
                self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertFalse(output.exists())
                self.assertNotIn(b'private-map',result.stderr);self.assertNotIn(b'Traceback',result.stderr)
