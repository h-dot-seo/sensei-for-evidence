from tests._native_archive_compat import prior_handoff_display
"""Explicit map context is separate from default protocol views and gate decisions."""
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import research_map
import research_map_views as maps
import research_status
import review_handoff
import compare_runs
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads((ROOT/path).read_bytes())

class MapViewTests(unittest.TestCase):
    def setUp(self):
        self.p=load('examples/bibliographic-base.json');self.d=load('examples/research-map-sidecar.json')

    def test_twelve_default_views_exact_baselines_with_named_engine_revision_paths(self):
        data=load('tests/map_view_default_baselines.json');self.assertEqual(len(data['cases']),12)
        expected={'status':{'research_status.py'},'handoff':{'research_status.py','review_handoff.py'},'compare':{'compare_runs.py'}}
        for case in data['cases']:
            p=load(case['fixture']);kind=case['view']
            module={'status':research_status,'handoff':review_handoff,'compare':compare_runs}[kind]
            result={'status':lambda:research_status.status(p),'handoff':lambda:review_handoff.handoff(p),'compare':lambda:compare_runs.compare_protocols(p,p)}[kind]()
            if 'cli_errors.py' in result['engine_sha256']:
                self.assertEqual(result['engine_sha256'].pop('cli_errors.py'),hashlib.sha256((ROOT/'cli_errors.py').read_bytes()).hexdigest())
            self.assertEqual(result['engine_sha256'].pop('amendment_links.py'),hashlib.sha256((ROOT/'amendment_links.py').read_bytes()).hexdigest())
            self.assertNotIn('research_map_context',result)
            self.assertEqual(set(case['omitted_fingerprints']),expected[kind])
            # Round55: restore only the new shared-loader ENGINE digest; four CLI-only
            # source hashes are already the exact named per-view omissions below.
            from tests._json_depth_compat import prior_bytes as pre_depth_bytes
            self.assertEqual(result['engine_sha256']['json_io.py'],hashlib.sha256((ROOT/'json_io.py').read_bytes()).hexdigest())
            result['engine_sha256']['json_io.py']=hashlib.sha256(pre_depth_bytes('json_io.py')).hexdigest()
            # Round51: only CLI-source hashes newly changed outside prior revision exceptions.
            cli_prior=load('tests/cli_input_prior_sources.json')['changed']
            already_named={'evidence_workflow.py','synthesis_review.py','readiness_review.py'}
            for name,old in cli_prior.items():
                if name in result['engine_sha256'] and name not in already_named:
                    self.assertEqual(result['engine_sha256'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
                    result['engine_sha256'][name]=old
            # Round50 optional disclosure ENGINE leaf; no absent-context fields change.
            self.assertEqual(result['engine_sha256'].pop('output_disclosure_links.py'),hashlib.sha256((ROOT/'output_disclosure_links.py').read_bytes()).hexdigest())
            # Round49 adds only this optional question ENGINE leaf; existing hashes follow named revisions below.
            self.assertEqual(result['engine_sha256'].pop('question_links.py'),hashlib.sha256((ROOT/'question_links.py').read_bytes()).hexdigest())
            if kind == 'handoff':
                name='readiness_review.py'
                prior49=load('tests/question_legacy_baselines.json')['prior_source_sha256']
                self.assertEqual(result['engine_sha256'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
                result['engine_sha256'][name]=prior49[name]
            # Round48 adds only this named ENGINE fingerprint; preserve historical view data.
            self.assertEqual(result['engine_sha256'].pop('archive_safety.py'),hashlib.sha256((ROOT/'archive_safety.py').read_bytes()).hexdigest())
            # Round46: exact named implementation changes plus one declared catalog route.
            delta=load('tests/evidence_basis_view_changes.json')
            self.assertEqual(set(delta['prior_45_sha256']),{'evidence_workflow.py','synthesis_links.py','planning_links.py','adapter_integrity.py','bibliographic_integrity.py','research_bundle.py','synthesis_review.py'})
            for name,recorded in delta['prior_45_sha256'].items():
                if name not in result['engine_sha256']:
                    self.assertEqual(name,'synthesis_review.py');self.assertNotEqual(kind,'handoff');continue
                self.assertEqual(result['engine_sha256'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
                result['engine_sha256'][name]=recorded
            self.assertEqual(delta['added_engine_files'],['evidence_basis_links.py'])
            self.assertEqual(result['engine_sha256'].pop('evidence_basis_links.py'),hashlib.sha256((ROOT/'evidence_basis_links.py').read_bytes()).hexdigest())
            if kind=='handoff':
                routes=result['supplied_input_workflows']
                added=[row for row in routes if row['workflow_id']=='evidence_basis_intake']
                self.assertEqual(added,[delta['added_workflow']])
                result['supplied_input_workflows']=[row for row in routes if row['workflow_id']!='evidence_basis_intake']
            # Round45 changes exactly two engine files. Preserve the round43
            # baseline and substitute only these named top-level digest values.
            prior=load('tests/challenge_origin_legacy_baselines.json')['prior_engine_sha256']
            self.assertEqual(set(prior),{'challenge_links.py','research_bundle.py'})
            for name,recorded in prior.items():
                self.assertEqual(result['engine_sha256'][name],delta['prior_45_sha256'].get(name,hashlib.sha256((ROOT/name).read_bytes()).hexdigest()))
                self.assertNotEqual(result['engine_sha256'][name],recorded)
                result['engine_sha256'][name]=recorded
            text_result=copy.deepcopy(result)
            # Compare text prints the same named digest entry; substitute only that
            # recorded value, never remove a line or normalize any other text.
            for name,value in case['omitted_fingerprints'].items():text_result['engine_sha256'][name]=value
            self.assertEqual(hashlib.sha256(prior_handoff_display(module.render_text(text_result).encode())).hexdigest(),case['text_sha256'])
            for name in expected[kind]:
                self.assertEqual(result['engine_sha256'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
                self.assertNotEqual(result['engine_sha256'].pop(name),case['omitted_fingerprints'][name])
            raw=(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
            self.assertEqual(hashlib.sha256(prior_handoff_display(raw)).hexdigest(),case['json_without_named_fingerprints_sha256'],(kind,case['fixture']))

    def test_context_does_not_change_any_base_field_or_gate_queue(self):
        before=copy.deepcopy((self.p,self.d))
        for func in (research_status.status,review_handoff.handoff):
            default=func(self.p);opt=func(self.p,research_map=self.d)
            context=opt.pop('research_map_context');self.assertEqual(opt,default)
            self.assertEqual(context['current_record_ids'],['map-record-A'])
            stale=copy.deepcopy(self.d);stale['records'][0]['basis_sha256']='0'*64
            opt=func(self.p,research_map=stale);context=opt.pop('research_map_context')
            self.assertEqual(opt,default);self.assertEqual(context['stale_record_ids'],['map-record-A'])
            self.assertEqual(context['stop_events'][0]['source_match_status'],'STALE_SOURCE')
            self.assertEqual(context['conclusion_readiness'],'NOT_READY')
        self.assertEqual((self.p,self.d),before)

    def test_paired_comparison_map_only_core_only_and_supplied_record_event_fields(self):
        base=compare_runs.compare_protocols(self.p,self.p)
        for section,key,value in [('research_map','decision_scope','changed scope'),('records','recorder','changed recorder'),
                                  ('records','recorded_at','2099-01-01'),('records','statement','changed statement'),
                                  ('stop_events','note','changed note'),('stop_events','recorded_by','changed recorder')]:
            d=copy.deepcopy(self.d)
            (d[section] if section=='research_map' else d[section][0])[key]=value
            joined=compare_runs.compare_protocols(self.p,self.p,before_map=self.d,after_map=d)
            context=joined.pop('research_map_context');self.assertEqual(joined,base)
            self.assertTrue(context['map_document_changed']);self.assertEqual(context['basis_changed'],section=='research_map')
            self.assertFalse(joined['has_changes'])
            if section!='research_map':self.assertIn(key,context['supplied_changes'][section]['modified'][0]['changed_fields'])
        p=copy.deepcopy(self.p);p['question']+=' changed'
        joined=compare_runs.compare_protocols(self.p,p,before_map=self.d,after_map=self.d)
        self.assertFalse(joined['research_map_context']['map_document_changed']);self.assertTrue(joined['research_map_context']['basis_changed'])
        self.assertEqual(joined['research_map_context']['after']['stale_record_ids'],['map-record-A'])
        p=copy.deepcopy(self.p);p['version']='another'
        self.assertFalse(maps.comparison(self.p,p,self.d,self.d)['basis_changed'])
        with self.assertRaises(ValueError):compare_runs.compare_protocols(self.p,self.p,before_map=self.d)
        with self.assertRaises(ValueError):research_status.status(self.p,research_map=None)

    def test_added_removed_reordered_records_events_and_empty_stage(self):
        other=copy.deepcopy(self.d);record=copy.deepcopy(other['records'][0]);record['record_id']='record-B';other['records'].append(record)
        event=copy.deepcopy(other['stop_events'][0]);event.update(event_id='event-B',record_id='record-B');other['stop_events'].append(event)
        c=maps.comparison(self.p,self.p,self.d,other);self.assertEqual(c['supplied_changes']['records']['added_ids'],['record-B'])
        self.assertEqual(c['supplied_changes']['stop_events']['added_ids'],['event-B'])
        reordered=copy.deepcopy(other);reordered['records'].reverse();reordered['stop_events'].reverse()
        c=maps.comparison(self.p,self.p,other,reordered)
        self.assertTrue(c['supplied_changes']['records']['order_changed']);self.assertEqual(c['supplied_changes']['records']['modified'],[])
        empty=copy.deepcopy(self.d);empty.update(records=[],stop_events=[])
        c=maps.comparison(self.p,self.p,self.d,empty);self.assertEqual(c['after']['record_stage'],'NOT_SUPPLIED')
        self.assertEqual(c['supplied_changes']['records']['removed_ids'],['map-record-A'])

    def test_opt_in_limits_and_quoted_hostile_identifiers(self):
        d=copy.deepcopy(self.d);d['records'][0]['record_id']='x\nforged';d['stop_events'][0]['record_id']='x\nforged'
        result=research_status.status(self.p,research_map=d);text=research_status.render_text(result)
        self.assertNotIn('\nforged',text);self.assertIn('x\\nforged',text)
        with patch.object(research_map,'MAX_REPORT_BYTES',10):
            with self.assertRaises(ValueError):research_status.status(self.p,research_map=self.d)
        stream=io.BytesIO(json.dumps(self.d).encode())
        with patch.object(Path,'open',return_value=stream),patch.object(research_map,'MAX_DOCUMENT_BYTES',10):
            with self.assertRaises(ValueError):maps.read_document(Path('private-input'))
        default=research_status.status(self.p)
        with patch.object(maps,'context',side_effect=AssertionError('no optional validation')):
            self.assertEqual(research_status.status(self.p),default)

    def test_real_three_cli_journey_and_default_json_bytes(self):
        blocks=re.findall(r'```sh\n(.*?)```',(ROOT/'docs/RESEARCH_MAP_VIEWS.md').read_text(),re.S)
        self.assertEqual(len(blocks),1);self.assertEqual(len(blocks[0].strip().splitlines()),3)
        for line in blocks[0].strip().splitlines():
            args=shlex.split(line);self.assertEqual(args.pop(0),'python')
            for text in (True,False):
                selected=args if text else [a for a in args if a!='--text']
                result=subprocess.run([sys.executable,*selected],cwd=ROOT,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,b'')
                if text:self.assertIn(b'Standalone map',result.stdout)
                else:self.assertIn('research_map_context',json.loads(result.stdout))

    def test_invalid_maps_fail_closed_and_pair_is_usage_not_findings(self):
        with tempfile.TemporaryDirectory(prefix='private-map ') as td:
            path=Path(td)/'private-map.json';p=ROOT/'examples/bibliographic-base.json'
            for raw in (b'\xff',b'{"x":1,"x":2}',b'null',b'{}'):
                path.write_bytes(raw)
                for script,args in [('research_status.py',[p,'--research-map',path]),('review_handoff.py',[p,'--research-map',path]),
                                    ('compare_runs.py',[p,p,'--before-map',path,'--after-map',path])]:
                    result=run_cli(script,*args,cwd=ROOT)
                    self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')
                    self.assertIn(b'protocol or research map',result.stderr);self.assertNotIn(b'private-map',result.stderr)
                    self.assertNotIn(b'Traceback',result.stderr)
            result=run_cli('compare_runs.py',p,p,'--before-map',path,cwd=ROOT)
            self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'')

    def test_existing_amendment_negative_exit_unchanged_with_map_context(self):
        with tempfile.TemporaryDirectory() as td:
            p=ROOT/'examples/bibliographic-base.json';d=ROOT/'examples/research-map-sidecar.json';note=Path(td)/'note.json'
            note.write_bytes(json.dumps(dict(schema_version=1,before_sha256='0'*64,after_sha256='0'*64,from_version=self.p['version'],to_version=self.p['version'],reason='Supplied synthetic note',authored_by='Fictional author',authored_at='2026-11-14',scope_fields=[])).encode())
            for args in [[],['--before-map',d,'--after-map',d]]:
                result=run_cli('compare_runs.py',p,p,'--amendment',note,*args,cwd=ROOT)
                self.assertEqual(result.returncode,1);self.assertEqual(result.stderr,b'')
                self.assertEqual(json.loads(result.stdout)['amendment_review']['binding_status'],'MISMATCH')
