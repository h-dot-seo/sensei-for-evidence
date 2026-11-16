from tests._native_archive_compat import prior_bytes as pre_native_archive
"""Small deterministic probe mechanics; no large run in ordinary CI."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tests import scale_probe as probe
from evidence_workflow import run
from json_io import canonical_json_bytes

ROOT=Path(__file__).resolve().parents[1]

class ScaleProbeTests(unittest.TestCase):
    def test_explicit_shape_and_invalid_generation_bounds(self):
        shape=copy.deepcopy(probe.PROFILES['smoke']);value=probe.generate(shape);result=run(value)
        self.assertEqual((result['flow']['identified'],len(result['evidence']),len(result['work_packages'])),(200,50,20))
        self.assertEqual(len(value['searches']),2);self.assertEqual(len(value['synthesis_statements']),13)
        self.assertTrue(all(len(x['evidence_ids'])<=4 for x in value['synthesis_statements']))
        self.assertTrue(all(len(x['evidence_ids'])==1 for x in value['gaps']))
        self.assertEqual(probe.generate(shape),value)
        for name,bad in [('records',40001),('records',0),('results',10001),('work',3001),('searches',5),('statement_width',5),('records',True)]:
            changed=dict(shape);changed[name]=bad
            with self.assertRaises(ValueError):probe.generate(changed)
        for bad in ({},None,dict(shape,unknown=1)):
            with self.assertRaises(ValueError):probe.generate(bad)
        self.assertEqual(shape,probe.PROFILES['smoke'])

    def test_complete_output_hash_exact_bytes_and_inclusive_budget(self):
        for value in ({'한':'line\ntext','n':[1,True,None]},b'ZIP\x00fictional'):
            raw=value if isinstance(value,bytes) else (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
            result=probe.output_observation(value,len(raw));self.assertEqual(result['status'],'COMPLETE')
            self.assertEqual(result['bytes'],len(raw));self.assertEqual(result['sha256'],hashlib.sha256(raw).hexdigest())
            over=probe.output_observation(value,len(raw)-1);self.assertEqual(over['status'],'OUTPUT_BUDGET_EXCEEDED')
            self.assertIsNone(over['sha256']);self.assertIsNone(over['bytes']);self.assertGreater(over['observed_at_least_bytes'],len(raw)-1)
        for limit in (-1,True,probe.MAX_OUTPUT_BYTES+1):
            with self.assertRaises(ValueError):probe.output_observation({},limit)

    def test_actual_smoke_calls_input_identity_and_complete_receipt(self):
        result=probe.measure('smoke');self.assertEqual(result['status'],'COMPLETE');self.assertTrue(result['input_unchanged'])
        raw=canonical_json_bytes(probe.generate(probe.PROFILES['smoke']))
        self.assertEqual(result['input']['bytes'],len(raw));self.assertEqual(result['input']['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual([r['operation'] for r in result['measurements']],['engine','status','synthesis','work','handoff','self_comparison','bundle_create','bundle_verify'])
        self.assertEqual(set(result['implementation_sha256']),{p.name for p in ROOT.glob('*.py')})
        self.assertEqual(result['probe_sha256'],hashlib.sha256((ROOT/'tests/scale_probe.py').read_bytes()).hexdigest())
        self.assertEqual(set(result['environment']),{'python','implementation','system','release','machine'})
        self.assertNotIn(str(ROOT),json.dumps(result));self.assertEqual(result['external_calls'],0)
        self.assertGreaterEqual(result['generation_seconds'],0);self.assertGreaterEqual(result['input_serialization_seconds'],0)
        for row in result['measurements']:
            self.assertEqual(row['status'],'COMPLETE');self.assertGreaterEqual(row['computation_seconds'],0);self.assertGreaterEqual(row['serialization_seconds'],0)
            self.assertEqual(row['output']['bytes'],row['output']['observed_at_least_bytes'])
        # Output hash is the current complete product result, not a fabricated size.
        direct=probe.output_observation(run(probe.generate(probe.PROFILES['smoke'])))
        self.assertEqual(result['measurements'][0]['output'],direct)

    def test_failures_budget_excess_and_unrun_dependency_are_not_success(self):
        result=probe.measure('smoke',output_limit=1)
        self.assertEqual(result['status'],'INCOMPLETE_OBSERVATION')
        self.assertTrue(all(row['status']=='OUTPUT_BUDGET_EXCEEDED' for row in result['measurements']))
        def refused():raise ValueError('synthetic failure')
        def not_run():raise AssertionError('prerequisite failure must skip verification')
        with patch.object(probe,'_operations',return_value=[('bundle_create',refused),('bundle_verify',not_run)]):
            result=probe.measure('smoke')
        self.assertEqual(result['status'],'INCOMPLETE_OBSERVATION')
        self.assertEqual([x['status'] for x in result['measurements']],['PRODUCT_REFUSED','NOT_RUN_PREREQUISITE_FAILED'])
        self.assertIsNone(result['measurements'][1]['computation_seconds'])
        self.assertNotIn('synthetic failure',json.dumps(result))
        with patch.object(probe,'_operations',return_value=[('bad_output',lambda:{'not_json':object()})]):
            result=probe.measure('smoke')
        self.assertEqual(result['measurements'][0]['status'],'SERIALIZATION_REFUSED')
        with patch.object(probe,'MAX_INPUT_BYTES',1),patch.object(probe,'_operations',side_effect=AssertionError('must not compute')):
            result=probe.measure('smoke')
        self.assertEqual(result['status'],'INPUT_BUDGET_EXCEEDED');self.assertEqual(result['measurements'],[])

    def test_input_mutation_is_visible(self):
        def ops(p,raw):
            def mutate():p['version']='synthetic changed input';return {}
            return [('synthetic_mutation',mutate)]
        with patch.object(probe,'_operations',side_effect=ops):result=probe.measure('smoke')
        self.assertFalse(result['input_unchanged']);self.assertEqual(result['status'],'INCOMPLETE_OBSERVATION')

    def test_cli_requires_opt_in_and_outputs_only_exclusive_receipt(self):
        invoke=lambda *args:subprocess.run([sys.executable,'-m','tests.scale_probe',*map(str,args)],cwd=ROOT,capture_output=True)
        for args in ([],['--profile','large'],['--run'],['--run','--profile','unknown']):
            value=invoke(*args);self.assertEqual(value.returncode,2);self.assertEqual(value.stdout,b'')
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/'receipt.json';value=invoke('--run','--profile','smoke','--output',dest)
            self.assertEqual((value.returncode,value.stderr),(0,b''));report=json.loads(dest.read_bytes())
            self.assertEqual(report,json.loads(value.stdout));self.assertEqual(report['status'],'COMPLETE')
            prior=dest.read_bytes();failed=invoke('--run','--profile','smoke','--output',dest)
            self.assertEqual((failed.returncode,failed.stdout),(1,b''));self.assertEqual(dest.read_bytes(),prior)
            self.assertNotIn(str(td).encode(),failed.stderr);self.assertEqual(list(Path(td).iterdir()),[dest])

    def test_all_prior_products_workflows_schemas_and_examples_unchanged(self):
        proof=json.loads((ROOT/'tests/scale_probe_prior_bytes.json').read_bytes())
        paths=list(ROOT.glob('*.py'))+list((ROOT/'examples').rglob('*'))+list((ROOT/'schemas').rglob('*'))+list((ROOT/'.github').rglob('*'))
        current={p.relative_to(ROOT).as_posix():p for p in paths if p.is_file()}
        self.assertEqual(set(current),set(proof)|{'pubmed_partition.py'})
        for name,digest in proof.items():self.assertEqual(hashlib.sha256(pre_native_archive(name) if '/' not in name else current[name].read_bytes()).hexdigest(),digest,name)


if __name__=='__main__':unittest.main()
