"""Origin labels are supplied provenance, never authenticated authorship or gate policy."""
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

import challenge_intake as intake
from challenge_links import validate_origin
from evidence_workflow import run
from json_io import canonical_json_bytes
from research_status import status
from review_handoff import handoff
from synthesis_review import snapshot
from compare_runs import compare_protocols
import research_bundle

ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/name).read_bytes())
def digest(value):return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
def origin(kind='INTERPRETIVE_SIMULATION'):
    return dict(kind=kind,package_sha256=None,consultation_record_sha256=None,declared_provenance=None)


class ChallengeOriginTests(unittest.TestCase):
    def setUp(self):
        self.p=load('examples/synthesis-review.json')
        self.c=load('examples/manual-challenge-candidates.json')
        self.q=copy.deepcopy(self.p);self.q['challenges']=copy.deepcopy(self.c['challenges'])

    def labelled(self):
        q=copy.deepcopy(self.q)
        for row in q['challenges']:row['origin']=origin()
        return q

    def test_actual_previous_run_baselines_only_derived_undeclared_label_changes(self):
        baseline=load('tests/challenge_origin_legacy_baselines.json')
        self.assertEqual(hashlib.sha256((ROOT/'tests/map_view_default_baselines.json').read_bytes()).hexdigest(),baseline['map_view_baseline_file_sha256'])
        for case in baseline['cases']:
            p=load('examples/'+case['fixture'])
            if case['attach_challenges']:p['challenges']=copy.deepcopy(self.c['challenges'])
            self.assertEqual(digest(p),case['input_sha256'])
            result=run(p)
            self.assertEqual(result['readiness']['gates_sha256'],case['gates_sha256'])
            self.assertNotIn('statements_with_only_interpretive_challenges',result['challenge'])
            self.assertNotIn('origin_verification',result['challenge'])
            for row in result['challenge']['challenge_ledger']:
                self.assertNotIn('origin',row)
                self.assertEqual(row.pop('origin_kind'),'UNDECLARED')
            self.assertEqual(digest(result),case['run_sha256'])
        self.assertTrue(all('origin' not in r for r in self.c['challenges']))

    def test_origin_alone_preserves_exact_readiness_all_other_engine_fields_and_raw_inputs(self):
        q=self.labelled();before=copy.deepcopy(q);old=run(self.q);new=run(q)
        self.assertEqual({k:v for k,v in old.items() if k!='challenge'},{k:v for k,v in new.items() if k!='challenge'})
        for key in ('statements_without_challenge','challenges_with_open_material_gaps','unresolved_challenge_ids','stale_challenge_ids','unbound_challenge_ids'):
            self.assertEqual(new['challenge'][key],old['challenge'][key])
        self.assertEqual(new['readiness'],old['readiness'])
        self.assertEqual(q,before)
        self.assertEqual(new['challenge']['origin_verification'],'DECLARED_NOT_VERIFIED')
        self.assertIn('neither the simulated scholar',new['challenge']['boundary'])
        self.assertNotIn('outcomes are human assertions',new['challenge']['boundary'])
        self.assertEqual(new['challenge']['statements_with_only_interpretive_challenges'],['statement-1','statement-2'])

    def test_mixed_human_and_undeclared_do_not_disappear_into_interpretive_only(self):
        q=self.labelled();r=copy.deepcopy(q['challenges'][0]);r['challenge_id']='fictional-second-kind'
        for kind in ('HUMAN_AUTHORED','UNDECLARED'):
            other=copy.deepcopy(r)
            if kind=='UNDECLARED':other.pop('origin')
            else:other['origin']=origin(kind)
            p=copy.deepcopy(q);p['challenges'].append(other);result=run(p)['challenge']
            for sid in other['statement_ids']:
                self.assertNotIn(sid,result['statements_with_only_interpretive_challenges'])
                row=next(x for x in result['statement_challenge_links'] if x['statement_id']==sid)
                field='human_challenge_ids' if kind=='HUMAN_AUTHORED' else 'undeclared_challenge_ids'
                self.assertIn(other['challenge_id'],row[field])
            self.assertEqual(run(p)['readiness']['gate_ledger'],run(dict(p,challenges=[{k:v for k,v in x.items() if k!='origin'} for x in p['challenges']]))['readiness']['gate_ledger'])

    def test_origin_presence_exact_shapes_hashes_and_human_metadata_rules(self):
        bad=[None,{},True,dict(origin(),kind='human'),dict(origin(),extra=None),dict(origin(),package_sha256='A'*64),dict(origin(),consultation_record_sha256='1'*64+'\n'),dict(origin('HUMAN_AUTHORED'),package_sha256='1'*64),dict(origin('HUMAN_AUTHORED'),consultation_record_sha256='2'*64)]
        for value in bad:
            with self.subTest(value=value),self.assertRaises(ValueError):validate_origin(value)
            p=copy.deepcopy(self.q);p['challenges'][0]['origin']=value
            with self.assertRaises(ValueError):run(p)
            c=copy.deepcopy(self.c);c['challenges'][0]['origin']=value
            with self.assertRaises(ValueError):intake.prepare(self.p,c)
        self.assertEqual(validate_origin(origin('HUMAN_AUTHORED')),'HUMAN_AUTHORED')
        self.assertEqual(validate_origin(dict(origin(),package_sha256='1'*64,consultation_record_sha256='2'*64)),'INTERPRETIVE_SIMULATION')

    def test_persona_provenance_exact_five_field_contract_without_authentication(self):
        provenance=dict(provider_id='fictional-provider',model_id='fictional-model',run_id='fictional-run',operator_id='fictional-operator',execution_location='unknown')
        self.assertEqual(validate_origin(dict(origin(),declared_provenance=provenance)),'INTERPRETIVE_SIMULATION')
        for key in provenance:
            for value in (None,'',' ','x'*129,'x\n','x\x7f'):
                p=dict(provenance,**{key:value})
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate_origin(dict(origin(),declared_provenance=p))
        for value in ({},dict(provenance,extra='x'),dict(provenance,execution_location='cloud')):
            with self.assertRaises(ValueError):validate_origin(dict(origin(),declared_provenance=value))
        for location in ('local','remote','unknown'):
            self.assertEqual(validate_origin(dict(origin(),declared_provenance=dict(provenance,execution_location=location,provider_id='x'*128))),'INTERPRETIVE_SIMULATION')
        with self.assertRaises(ValueError):validate_origin(dict(origin('HUMAN_AUTHORED'),declared_provenance=provenance))

    def test_target_binds_supplied_origin_review_never_generated_and_template_unchanged(self):
        c=load('examples/interpretive-challenge-candidates.json');old=copy.deepcopy((self.p,c))
        target=intake.prepare(self.p,c);review=copy.deepcopy(target['review_document'])
        self.assertIsNone(review['decision'])
        with self.assertRaises(ValueError):intake.assemble(self.p,c,review)
        review.update(receipt_id='fictional-origin-import',decision='import_challenges',reviewer='Fictional import reviewer',reviewed_at='2026-11-14',rationale='Synthetic declaration recording only')
        app=intake.assemble(self.p,c,review)
        self.assertTrue(intake.verify(self.p,app)['valid'])
        self.assertEqual(app['protocol_candidate']['challenges'],c['challenges'])
        self.assertEqual((self.p,c),old)
        changed=copy.deepcopy(c);changed['challenges'][0]['origin']['package_sha256']='3'*64
        with self.assertRaises(ValueError):intake.assemble(self.p,changed,review)
        app['protocol_candidate']['challenges'][0]['origin']['package_sha256']='3'*64
        with self.assertRaises(ValueError):intake.verify(self.p,app)
        draft=intake.template(self.p,load('examples/challenge-references.json'))['candidate_document']
        self.assertEqual(draft['schema_version'],1)
        self.assertTrue(all('origin' not in row for row in draft['challenges']))

    def test_existing_readiness_assertion_remains_current_when_origin_is_added(self):
        p=copy.deepcopy(self.p);p['readiness_assertions']=copy.deepcopy(load('examples/manual-readiness-candidates.json')['readiness_assertions'])
        baseline=run(p)['readiness'];self.assertTrue(baseline['current_assertion_ids'])
        # Existing assertions bind gates, not engine version or origin declarations.
        # Adding challenges can change gates; only compare same challenges +/- origin.
        q=self.labelled()
        self.assertEqual(run(q)['readiness']['gates_sha256'],run(self.q)['readiness']['gates_sha256'])
        assertion=copy.deepcopy(p['readiness_assertions'][0]);assertion['gates_sha256']=run(self.q)['readiness']['gates_sha256']
        original=copy.deepcopy(self.q);original['readiness_assertions']=[assertion]
        labelled=copy.deepcopy(q);labelled['readiness_assertions']=[copy.deepcopy(assertion)]
        self.assertEqual(run(original)['readiness'],run(labelled)['readiness'])
        self.assertTrue(run(labelled)['readiness']['current_assertion_ids'])
        self.assertEqual(run(p)['readiness'],baseline)

    def test_views_expose_only_optional_queue_bundle_and_inert_hashes(self):
        q=self.labelled();a=status(self.q);b=status(q)
        key='statements_with_only_interpretive_challenges'
        self.assertNotIn(key,a['queues']);self.assertIn(key,b['queues'])
        self.assertEqual({k:v for k,v in b['queues'].items() if k!=key},a['queues'])
        self.assertEqual({k:v for k,v in b['counts'].items() if k!=key},a['counts'])
        self.assertEqual(a['readiness'],b['readiness'])
        packet=handoff(q);self.assertIn(key,[row['queue'] for row in packet['manual_review_steps']])
        snap=snapshot(q)
        self.assertIn('INTERPRETIVE_SIMULATION',json.dumps(snap))
        comparison=compare_protocols(self.q,q)
        self.assertTrue(comparison['has_changes'])  # supplied origin is a real raw field change
        raw=canonical_json_bytes(q);bundle=research_bundle.build_bundle(raw)
        with zipfile.ZipFile(io.BytesIO(bundle)) as z:
            summary=z.read('summary.md').decode()
            self.assertIn('only declared interpretive challenges',summary)
            self.assertEqual(json.loads(z.read('protocol.json')),q)
        self.assertTrue(research_bundle.verify(io.BytesIO(bundle))['valid'])
        with zipfile.ZipFile(io.BytesIO(research_bundle.build_bundle(canonical_json_bytes(self.q)))) as z:
            self.assertNotIn(b'only declared interpretive challenges',z.read('summary.md'))

    def test_stale_unresolved_and_no_challenge_are_not_reclassified_as_human_review(self):
        q=self.labelled();q['challenges'][0]['basis_sha256']='0'*64
        result=run(q)
        self.assertIn(q['challenges'][0]['challenge_id'],result['challenge']['stale_challenge_ids'])
        self.assertTrue(result['challenge']['statements_with_only_interpretive_challenges'])
        self.assertEqual(result['readiness'],run(dict(q,challenges=[{k:v for k,v in row.items() if k!='origin'} for row in q['challenges']]))['readiness'])
        p=copy.deepcopy(self.p);p['challenges']=[]
        self.assertNotIn('statements_with_only_interpretive_challenges',run(p)['challenge'])

    def test_documented_ten_command_origin_journey_and_old_guide_unchanged(self):
        doc=(ROOT/'docs/INTERPRETIVE_CHALLENGE_ORIGIN.md').read_text(encoding='utf-8')
        commands=[line for block in re.findall(r'```sh\n(.*?)```',doc,re.S) for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),10)
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);(work/'examples').mkdir()
            for name in ('synthesis-review.json','challenge-references.json','interpretive-challenge-candidates.json'):
                shutil.copyfile(ROOT/'examples'/name,work/'examples'/name)
            sources={p:p.read_bytes() for p in (work/'examples').iterdir()}
            for line in commands:
                args=shlex.split(line)[1:];args[0]=str(ROOT/args[0])
                result=subprocess.run([sys.executable,'-B',*args],cwd=work,capture_output=True,timeout=30)
                self.assertEqual((result.returncode,result.stderr),(0,b''),line)
                if ' target ' in line:
                    review=json.loads((work/'origin-target.json').read_bytes())['review_document']
                    review.update(receipt_id='fictional-origin-import',decision='import_challenges',reviewer='Fictional import reviewer',reviewed_at='2026-11-14',rationale='Record fictional origin declarations only')
                    (work/'origin-review.json').write_bytes((json.dumps(review)+'\n').encode())
            p=json.loads((work/'origin-protocol.json').read_bytes())
            self.assertTrue(all(r['origin']['kind']=='INTERPRETIVE_SIMULATION' for r in p['challenges']))
            self.assertEqual({p:p.read_bytes() for p in sources},sources)
            raw=(work/'origin-application.json').read_bytes()
            result=subprocess.run([sys.executable,'-B',str(ROOT/'challenge_intake.py'),'assemble','examples/synthesis-review.json','examples/interpretive-challenge-candidates.json','origin-review.json','--output','origin-application.json'],cwd=work,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')
            self.assertEqual((work/'origin-application.json').read_bytes(),raw)

    def test_only_fifteen_synthetic_hash_fields_changed_no_review_assertion_rewritten(self):
        proofs=load('tests/challenge_origin_synthetic_targets.json')
        self.assertEqual(len(proofs),15);self.assertEqual(len({r['path'] for r in proofs}),15)
        for item in proofs:
            value=load(item['path']);at=value;pointer=item['pointer'].strip('/').split('/')
            for key in pointer[:-1]:at=at[key]
            self.assertRegex(at[pointer[-1]],r'^[0-9a-f]{64}$')
            at[pointer[-1]]=None
            self.assertEqual(digest(value),item['remaining_value_sha256'],item['path'])
        for path,expected in load('tests/challenge_origin_legacy_baselines.json')['unchanged_existing_guides_and_tests'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected,path)
