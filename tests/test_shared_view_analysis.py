"""Same-call projection reuse; no cache, validation shortcut or general scale claim."""
import ast
from tests._amendment_compat import prior_bytes as pre_amendment
import copy
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import evidence_workflow
import research_status
import synthesis_review
import work_review
import review_handoff
from tests.test_view_scale import generated

ROOT=Path(__file__).resolve().parents[1]
CHANGES=json.loads((ROOT/'tests/shared_analysis_source_changes.json').read_bytes())
FUNCTIONS=[research_status.status,synthesis_review.snapshot,work_review.review_packets,review_handoff.handoff]


def count_runs(fn,*args,**kwargs):
    profiler=cProfile.Profile();profiler.enable()
    try:result=fn(*args,**kwargs)
    finally:profiler.disable()
    count=sum(row[1] for key,row in pstats.Stats(profiler).stats.items()
              if key[0].endswith('evidence_workflow.py') and key[2]=='run')
    return result,count


class SharedViewAnalysisTests(unittest.TestCase):
    def test_run_counts_repeat_changed_inputs_and_ownership(self):
        for value,expected in [(generated(30),1),(json.loads((ROOT/'examples/synthesis-review.json').read_bytes()),2)]:
            before=copy.deepcopy(value)
            for fn in FUNCTIONS:
                with self.subTest(fn=fn.__name__,reports='reports' in value):
                    first,n=count_runs(fn,value);self.assertEqual(n,expected)
                    clean=copy.deepcopy(first)
                    # Mutating the returned result cannot contaminate another call or input.
                    def poison(v):
                        if isinstance(v,dict):
                            for x in list(v.values()):poison(x)
                            v['synthetic-poison']='not research'
                        elif isinstance(v,list):
                            for x in v:poison(x)
                            v.append('synthetic-poison')
                    poison(first)
                    second,n=count_runs(fn,value);self.assertEqual((second,n),(clean,expected))
                    changed=copy.deepcopy(value);changed['version']+='-supplied-edit'
                    third,n=count_runs(fn,changed);self.assertEqual(n,expected)
                    self.assertEqual(third['protocol_version'],changed['version'])
                    self.assertNotEqual(third['protocol_sha256'],clean['protocol_sha256'])
                    self.assertEqual(value,before)

    def test_public_entries_still_validate_and_do_not_accept_analysis(self):
        for fn in FUNCTIONS:
            for bad in (None,{},[],{'question':'incomplete'}):
                with self.subTest(fn=fn.__name__,bad=bad),self.assertRaises((ValueError,KeyError,TypeError)):fn(bad)
            with self.assertRaises(TypeError):fn(generated(2),research={'fake':'approved'})
            with self.assertRaises(TypeError):fn(generated(2),reports={})
        with self.assertRaises(ValueError):work_review.review_packets(generated(2),include_prerequisites=1)
        with self.assertRaises(ValueError):work_review.review_packets(generated(2),include_prerequisites=True)
        for fn in (work_review.review_packets,review_handoff.handoff):
            with self.assertRaises(ValueError):fn(generated(2),'unknown')

    def test_actual_old_new_run_counts(self):
        script="""import cProfile,json,pstats,sys
from pathlib import Path
from research_status import status
from synthesis_review import snapshot
from work_review import review_packets
from review_handoff import handoff
p=json.loads(Path(sys.argv[1]).read_bytes());rows=[]
for fn in (status,snapshot,review_packets,handoff):
 c=cProfile.Profile();c.enable();fn(p);c.disable()
 rows.append(sum(v[1] for k,v in pstats.Stats(c).stats.items() if k[0].endswith('evidence_workflow.py') and k[2]=='run'))
print(json.dumps(rows))
"""
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);old=td/'old';old.mkdir()
            for p in ROOT.glob('*.py'):(old/p.name).write_bytes(CHANGES[p.name]['old'].encode() if p.name in CHANGES else pre_amendment(p.name))
            for value,multiplier in ((generated(3),1),(json.loads((ROOT/'examples/synthesis-review.json').read_bytes()),2)):
                source=td/'input.json';source.write_text(json.dumps(value))
                rows=[]
                for root in (old,ROOT):
                    result=subprocess.run([sys.executable,'-c',script,str(source)],cwd=root,capture_output=True)
                    self.assertEqual((result.returncode,result.stderr),(0,b''))
                    rows.append(json.loads(result.stdout))
                self.assertEqual(rows[0],[multiplier,2*multiplier,multiplier,4*multiplier])
                self.assertEqual(rows[1],[multiplier]*4)

    def test_private_projection_inputs_are_not_mutated(self):
        from prisma_reports import report_flow
        for p in (generated(4),json.loads((ROOT/'examples/synthesis-review.json').read_bytes())):
            research=evidence_workflow.run(p)
            reports=report_flow(p,include_csv=False) if 'reports' in p else None
            saved=copy.deepcopy((p,research,reports))
            state=research_status._status_from_analysis(p,research,reports)
            work_review._packets_from_analysis(p,research,reports)
            synthesis_review._snapshot_from_analysis(p,research,reports,state)
            self.assertEqual((p,research,reports),saved)

    def test_exact_four_sources_and_engine_other_sources_unchanged(self):
        expected=json.loads((ROOT/'tests/shared_analysis_prior_sources.json').read_bytes())
        self.assertEqual(set(expected),{p.name for p in ROOT.glob('*.py') if p.name not in ('retained_bundle_describe.py','amendment_links.py','amendment_intake.py')})
        self.assertEqual(set(CHANGES),{'research_status.py','synthesis_review.py','work_review.py','review_handoff.py'})
        import research_bundle
        self.assertFalse(set(CHANGES)&set(research_bundle.ENGINE_FILES))
        for name,digest in expected.items():
            raw=CHANGES[name]['old'].encode() if name in CHANGES else pre_amendment(name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest,name)
        for name,change in CHANGES.items():
            self.assertEqual(pre_amendment(name).decode(),change['new'])
            old=ast.parse(change['old']);new=ast.parse(change['new'])
            a={n.name:ast.get_source_segment(change['old'],n) for n in old.body if isinstance(n,ast.FunctionDef)}
            b={n.name:ast.get_source_segment(change['new'],n) for n in new.body if isinstance(n,ast.FunctionDef)}
            for fn in a:
                if fn not in ('status','snapshot','review_packets','handoff'):
                    self.assertEqual(a[fn],b[fn],(name,fn))

    def test_actual_prior_current_cli_bytes_with_four_controlled_hash_reads(self):
        # Code runs from the actual old/current roots. Only the four exact fingerprint
        # file reads are controlled, never protocol reads or general output text.
        runner='''import json,runpy,sys
from pathlib import Path
from unittest.mock import patch
root=Path(sys.argv[1]).resolve();old=Path(sys.argv[2]).resolve();script=sys.argv[3];args=sys.argv[4:]
names=['research_status.py','synthesis_review.py','work_review.py','review_handoff.py']
# Exact additional round60 source fingerprints; current functions still execute.
names=list(dict.fromkeys(names+list(json.loads((root/'tests/amendment_source_changes.json').read_bytes()))))
source={root/name:(old/name).read_bytes() for name in names}
real=Path.read_bytes
def controlled(path):
 return source[path.resolve()] if path.resolve() in source else real(path)
sys.path.insert(0,str(root));sys.argv=[str(root/script),*args]
import research_bundle
assert research_bundle.ENGINE_FILES[-1]=='amendment_links.py'
research_bundle.ENGINE_FILES=research_bundle.ENGINE_FILES[:-1]
with patch.object(Path,'read_bytes',controlled):runpy.run_path(str(root/script),run_name='__main__')
'''
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);old=td/'old';old.mkdir()
            for p in ROOT.glob('*.py'):(old/p.name).write_bytes(CHANGES[p.name]['old'].encode() if p.name in CHANGES else pre_amendment(p.name))
            runfile=td/'controlled.py';runfile.write_text(runner)
            cases=[]
            for fixture in ('examples/bibliographic-base.json','examples/review-demo.json','examples/synthesis-review.json'):
                for name in CHANGES:
                    for mode in ([],['--text']):cases.append((name,[str(ROOT/fixture),*mode]))
            for name in ('work_review.py','review_handoff.py'):
                for work in ('WP-MECHANISM','WP-TRANSLATION','unknown'):
                    cases.append((name,[str(ROOT/'examples/review-demo.json'),'--work-package',work]))
            cases.append(('work_review.py',[str(ROOT/'examples/review-demo.json'),'--brief']))
            cases.append(('work_review.py',[str(ROOT/'examples/review-demo.json'),'--work-package','WP-TRANSLATION','--include-prerequisites','--text']))
            for name in ('research_status.py','review_handoff.py'):
                for fixture in ('examples/bibliographic-base.json','examples/review-demo.json'):
                    cases.append((name,[str(ROOT/fixture),'--research-map',str(ROOT/'examples/research-map-sidecar.json')]))
            bad=td/'bad.json';bad.write_bytes(b'null')
            for name in CHANGES:cases.append((name,[str(bad)]))
            self.assertEqual(len(cases),40)
            for name,args in cases:
                with self.subTest(name=name,args=args):
                    before=subprocess.run([sys.executable,str(old/name),*args],cwd=old,capture_output=True)
                    after=subprocess.run([sys.executable,str(runfile),str(ROOT),str(old),name,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual((before.returncode,before.stdout,before.stderr),(after.returncode,after.stdout,after.stderr))
                    self.assertNotIn(b'Traceback',after.stderr)
            # Actual, uncontrolled fingerprints must still point to current source bytes.
            for fn in FUNCTIONS:
                result=fn(generated(2))
                for name in set(result['engine_sha256'])&set(CHANGES):
                    self.assertEqual(result['engine_sha256'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
