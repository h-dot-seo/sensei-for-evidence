from tests._native_archive_compat import prior_bytes as pre_native_archive, prior_handoff_display
"""Two-snapshot supplied amendment records never close existing gates."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import amendment_intake as intake
import amendment_links as links
from evidence_workflow import run
from compare_runs import compare_protocols,render_text as compare_text
from research_status import status,render_text as status_text
from review_handoff import handoff,render_text as handoff_text
from research_bundle import build_bundle,verify_bytes
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]
def base():return json.loads((ROOT/'examples/bibliographic-base.json').read_bytes())
def changed(p):
    q=copy.deepcopy(p);q['version']+='-changed';return q

def candidate(before,after,aid='A1',refs=None):
    d=intake.template(before,after)['candidate_document'];d['amendment'].update(amendment_id=aid,
        reason='Fictional supplied reason',authored_by='Fictional author',authored_at='2026-01-02',
        scope_fields=sorted(k for k in set(before)|set(after) if k!='amendments' and (k not in before or k not in after or intake.digest(before[k])!=intake.digest(after[k]))),
        triggered_by=[] if refs is None else refs)
    return d

def review(before,after,document):
    r=intake.prepare(before,after,document)['review_document'];r.update(receipt_id='fictional-receipt',
        decision='record_supplied_amendment',reviewer='Fictional supplied reviewer',reviewed_at='2026-01-03',rationale='Record bookkeeping only')
    return r

def apply(before,after,aid='A1',refs=None):
    d=candidate(before,after,aid,refs);return intake.assemble(before,after,d,review(before,after,d))

class AmendmentLedgerTests(unittest.TestCase):
    def test_template_null_review_and_exact_preservation(self):
        b=base();a=changed(b);saved=copy.deepcopy((b,a));t=intake.template(b,a)
        for k in ('reason','scope_fields','amendment_id','authored_by','authored_at','triggered_by'):self.assertIsNone(t['candidate_document']['amendment'][k])
        with self.assertRaises(ValueError):intake.prepare(b,a,t['candidate_document'])
        d=candidate(b,a);target=intake.prepare(b,a,d)
        self.assertIsNone(target['review_document']['decision']);self.assertIsNone(target['review_document']['reviewer'])
        with self.assertRaises(ValueError):intake.assemble(b,a,d,target['review_document'])
        app=apply(b,a);final=app['protocol_candidate'];self.assertTrue(intake.verify(b,a,app)['valid'])
        self.assertEqual({k:v for k,v in final.items() if k!='amendments'},a)
        self.assertEqual((b,a),saved)
        old=run(a);new=run(final);new.pop('amendments');self.assertEqual(new,old)
        self.assertNotIn('after_protocol_sha256',final['amendments'][0])
        self.assertEqual(app['receipt']['after_input_protocol_sha256'],intake.digest(a))

    def test_two_sequential_rows_preserve_history_and_limited_currentness(self):
        b=base();a=changed(b);first=apply(b,a)['protocol_candidate'];next_input=changed(first)
        app=apply(first,next_input,'A2');final=app['protocol_candidate'];self.assertEqual(final['amendments'][:-1],first['amendments'])
        ledger=run(final)['amendments']['amendment_ledger']
        self.assertEqual([r['version_match'] for r in ledger],['NOT_CURRENT_VERSION','CURRENT_VERSION'])
        self.assertTrue(all(r['before_hash_verification']=='NOT_VERIFIED_IN_PLACE' for r in ledger))
        self.assertTrue(intake.verify(first,next_input,app)['valid'])
        self.assertEqual(compare_protocols(first,final,amendment_id='A2')['embedded_amendment_review']['binding_status'],'RECORDED_BEFORE_AND_SCOPE_MATCH')
        self.assertEqual(compare_protocols(b,final,amendment_id='A1')['embedded_amendment_review']['binding_status'],'MISMATCH')
        bad=copy.deepcopy(next_input);bad['amendments'][0]['reason']='overwrite'
        with self.assertRaises(ValueError):intake.template(first,bad)
        with self.assertRaises(ValueError):apply(first,next_input,'A1')

    def test_before_references_and_open_amendment_gates_never_closed(self):
        b=json.loads((ROOT/'examples/synthesis-review.json').read_bytes())
        b['challenges']=json.loads((ROOT/'examples/manual-challenge-candidates.json').read_bytes())['challenges']
        b['readiness_assertions']=json.loads((ROOT/'examples/manual-readiness-candidates.json').read_bytes())['readiness_assertions']
        a=changed(b);ref={'kind':'CHALLENGE','ref_id':b['challenges'][0]['challenge_id']}
        app=apply(b,a,refs=[ref,{'kind':'READINESS_ASSERTION','ref_id':b['readiness_assertions'][0]['assertion_id']}]);final=app['protocol_candidate']
        before=run(a);after=run(final)
        self.assertEqual(before['challenge'],after['challenge']);self.assertEqual(before['readiness'],after['readiness'])
        self.assertEqual(before['synthesis'],after['synthesis'])
        unknown=candidate(b,a,refs=[{'kind':'CHALLENGE','ref_id':'missing'}])
        with self.assertRaises(ValueError):intake.prepare(b,a,unknown)
        for kind in ('QUESTION','STOP_RULE','OTHER'):
            d=candidate(b,a,refs=[dict(kind=kind,ref_id='anything')])
            with self.assertRaises(ValueError):intake.prepare(b,a,d)
        # A later snapshot may remove historical references; the standalone record
        # observes no current-reference authority and keeps its old row.
        later=copy.deepcopy(final);later['challenges']=[]
        self.assertEqual(run(later)['amendments']['recorded_count'],1)

    def test_hash_scope_version_mismatch_and_supplied_before_is_required(self):
        b=base();a=changed(b);d=candidate(b,a)
        for key,value in [('before_protocol_sha256','0'*64),('from_version','wrong'),('to_version','wrong'),('scope_fields',[]),('scope_fields',['question','version'])]:
            bad=copy.deepcopy(d);bad['amendment'][key]=value
            with self.assertRaises(ValueError):intake.prepare(b,a,bad)
        final=apply(b,a)['protocol_candidate'];wrong=copy.deepcopy(b);wrong['question']='different supplied question'
        report=compare_protocols(wrong,final,amendment_id='A1')['embedded_amendment_review'];self.assertEqual(report['binding_status'],'MISMATCH')
        self.assertFalse(report['before_input_hash_match']);self.assertEqual(report['after_hash_verification'],'NOT_APPLICABLE_EMBEDDED')
        self.assertIn('amendments',report['implicit_scope_fields']);self.assertNotIn('amendments',report['actual_changed_fields'])
        self.assertNotIn('RECORDED_INPUTS_AND_SCOPE_MATCH',json.dumps(report))
        for aid in (None,'',[],'unknown'):
            with self.assertRaises((ValueError,TypeError)):compare_protocols(b,final,amendment_id=aid)
        with self.assertRaises(ValueError):compare_protocols(b,final,{},amendment_id='A1')

    def test_shape_rows_bounds_and_old_version_types(self):
        b=base();a=changed(b);good=candidate(b,a)['amendment']
        for key in links.FIELDS:
            row=copy.deepcopy(good);row.pop(key)
            with self.assertRaises(ValueError):links.validate_row(row)
        for field,value in [('reason',' '),('authored_at','2026-02-30'),('before_protocol_sha256','A'*64),('scope_fields',['amendments']),('scope_fields',['version','version']),('triggered_by',[{'kind':'CHALLENGE','ref_id':'x'}]*2)]:
            row=copy.deepcopy(good);row[field]=value
            with self.assertRaises((ValueError,TypeError)):links.validate_row(row)
        for rows in (None,{},[good,good]):
            p=copy.deepcopy(a);p['amendments']=rows
            with self.assertRaises(ValueError):run(p)
        p=copy.deepcopy(a);p['amendments']=[dict(copy.deepcopy(good),amendment_id=str(i)) for i in range(100)]
        self.assertEqual(run(p)['amendments']['recorded_count'],100)
        p['amendments'].append(dict(good,amendment_id='overflow'))
        with self.assertRaises(ValueError):run(p)
        legacy=base();legacy['version']=True;run(legacy)
        with self.assertRaises(ValueError):intake.template(legacy,a)
        empty=base();empty['amendments']=[];actual=run(empty);actual.pop('amendments');self.assertEqual(actual,run(base()))

    def test_exact_review_replay_and_tamper_rejection(self):
        b=base();a=changed(b);d=candidate(b,a);r=review(b,a,d)
        for key,value in [('target_sha256','0'*64),('decision','approve_change'),('reviewer',''),('reviewed_at','2026-02-30')]:
            bad=dict(r);bad[key]=value
            with self.assertRaises(ValueError):intake.assemble(b,a,d,bad)
        app=intake.assemble(b,a,d,r)
        for edit in (lambda x:x['protocol_candidate'].update(question='altered'),lambda x:x['receipt'].update(receipt_sha256='0'*64),lambda x:x['receipt']['target'].update(assessment='PERFORMED')):
            bad=copy.deepcopy(app);edit(bad)
            with self.assertRaises(ValueError):intake.verify(b,a,bad)
        bad=copy.deepcopy(a);bad['question']='different'
        with self.assertRaises(ValueError):intake.verify(b,bad,app)
        self.assertEqual(intake.digest(b),app['receipt']['before_protocol_sha256'])

    def test_views_and_bundle_observe_without_approval_or_gate_change(self):
        b=base();a=changed(b);final=apply(b,a)['protocol_candidate']
        for fn,render in ((status,status_text),(handoff,handoff_text)):
            value=fn(final);self.assertEqual(value['amendments']['assessment'],'NOT_PERFORMED')
            self.assertIn('before hashes not verified in place',render(value))
        result=compare_protocols(b,final,amendment_id='A1');self.assertIn('not approval',compare_text(result))
        raw=build_bundle(json.dumps(final).encode());self.assertTrue(verify_bytes(raw)['valid'])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(json.loads(z.read('protocol.json')),final)
            self.assertIn(b'before hashes not verified in place',z.read('summary.md'))
        self.assertEqual(run(a)['readiness'],run(final)['readiness'])

    def test_actual_native_imports_allow_only_amendment_enrichment(self):
        from tests.test_bibliographic_assertion_continuation import imported
        for fmt in ('CSV','NBIB','RIS'):
            _,_,_,b,_=imported(fmt);a=changed(b);app=apply(b,a)
            self.assertTrue(intake.verify(b,a,app)['valid'])
            self.assertEqual(run(a)['readiness'],run(app['protocol_candidate'])['readiness'])
            bad=copy.deepcopy(a);bad['question']='immutable edit'
            with self.assertRaises(ValueError):intake.template(b,bad)
            bad=copy.deepcopy(app['protocol_candidate']);bad['arbitrary_new_enrichment']=[]
            with self.assertRaises(ValueError):run(bad)

    def test_human_input_change_can_make_prior_bindings_stale_but_append_does_not(self):
        b=json.loads((ROOT/'examples/synthesis-review.json').read_bytes())
        b['challenges']=json.loads((ROOT/'examples/manual-challenge-candidates.json').read_bytes())['challenges']
        a=changed(b);a['question']+=' human-supplied revision'
        prior=run(b);edited=run(a);final=apply(b,a)['protocol_candidate'];observed=run(final)
        self.assertNotEqual(prior['challenge']['challenge_ledger'],edited['challenge']['challenge_ledger'])
        self.assertEqual(edited['challenge'],observed['challenge']);self.assertEqual(edited['readiness'],observed['readiness'])
        self.assertTrue(any(row['source_match_status']!='CURRENT_BASIS' for row in observed['challenge']['challenge_ledger']))

    def test_input_byte_limits_before_parse_and_output_limits(self):
        b=base();a=changed(b);d=candidate(b,a)
        with patch.object(intake,'MAX_PROTOCOL_BYTES',len(intake.canonical_json_bytes(b))-1):
            with self.assertRaises(ValueError):intake.template(b,a)
        with patch.object(intake,'MAX_DOCUMENT_BYTES',1):
            with self.assertRaises(ValueError):intake.prepare(b,a,d)
        with patch.object(intake,'MAX_APPLICATION_BYTES',1):
            with self.assertRaises(ValueError):intake.prepare(b,a,d)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'never.json'
            with patch.object(intake,'MAX_APPLICATION_BYTES',1):
                with self.assertRaises(ValueError):intake._write(out,d)
            self.assertFalse(out.exists())

    def test_exact_prior_root_and_absent_actual_cli_bytes(self):
        changes=json.loads((ROOT/'tests/amendment_source_changes.json').read_bytes())
        proof=json.loads((ROOT/'tests/amendment_prior_sources.json').read_bytes())
        self.assertEqual(set(changes),{'evidence_workflow.py','research_bundle.py','adapter_integrity.py','bibliographic_integrity.py','compare_runs.py','research_status.py','review_handoff.py','protocol_keys.py'})
        self.assertEqual({p.name for p in ROOT.glob('*.py')},set(proof)|{'amendment_links.py','amendment_intake.py','pubmed_partition.py','pubmed_partition_compare.py'})
        for name,digest in proof.items():
            data=changes[name]['old'].encode() if name in changes else pre_native_archive(name)
            self.assertEqual(hashlib.sha256(data).hexdigest(),digest,name)
        for name,change in changes.items():self.assertEqual(pre_native_archive(name),change['new'].encode())
        # Run prior byte-exact sources and current sources, changing only explicit
        # implementation-map values when comparing otherwise exact JSON bytes.
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);old=td/'prior';old.mkdir()
            for name in proof:(old/name).write_bytes(changes[name]['old'].encode() if name in changes else pre_native_archive(name))
            for fixture in ('bibliographic-base.json','synthesis-review.json','first-run-enriched.json'):
                source=ROOT/'examples'/fixture
                for script in ('research_status.py','review_handoff.py','compare_runs.py'):
                    args=[str(source)]*(2 if script=='compare_runs.py' else 1)
                    if fixture=='first-run-enriched.json' and script=='compare_runs.py':
                        args=[str(source),str(ROOT/'examples/first-run-note-complete.json'),'--amendment',str(ROOT/'examples/work-note-amendment.json')]
                    for flags in ([],['--text']):
                        before=subprocess.run([sys.executable,str(old/script),*args,*flags],cwd=old,capture_output=True)
                        after=subprocess.run([sys.executable,str(ROOT/script),*args,*flags],cwd=ROOT,capture_output=True)
                        self.assertEqual((before.returncode,before.stderr),(after.returncode,after.stderr))
                        self.assertEqual(before.returncode,0)
                        if flags:
                            observed=prior_handoff_display(after.stdout)
                            if script=='compare_runs.py':
                                prefix=b'Implementation SHA-256 fingerprints (not authentication): '
                                left=[line for line in before.stdout.splitlines() if line.startswith(prefix)]
                                right=[line for line in after.stdout.splitlines() if line.startswith(prefix)]
                                self.assertEqual((len(left),len(right)),(1,1))
                                x=json.loads(left[0][len(prefix):]);y=json.loads(right[0][len(prefix):])
                                self.assertEqual(y.pop('amendment_links.py'),hashlib.sha256((ROOT/'amendment_links.py').read_bytes()).hexdigest())
                                for name in set(changes)&set(y):
                                    self.assertEqual(y[name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
                                    self.assertEqual(x[name],hashlib.sha256(changes[name]['old'].encode()).hexdigest());y[name]=x[name]
                                self.assertEqual(x,y)
                                observed=observed.replace(right[0],left[0],1)
                            self.assertEqual(before.stdout,observed);continue
                        a=json.loads(before.stdout);b=json.loads(prior_handoff_display(after.stdout))
                        def restore(x,y,path=()):
                            if isinstance(x,dict) and isinstance(y,dict):
                                if path and path[-1]=='engine_sha256':
                                    if 'amendment_links.py' in y:
                                        self.assertEqual(y.pop('amendment_links.py'),hashlib.sha256((ROOT/'amendment_links.py').read_bytes()).hexdigest())
                                    for name in set(changes)&set(y):
                                        self.assertEqual(y[name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
                                        self.assertEqual(x[name],hashlib.sha256(changes[name]['old'].encode()).hexdigest());y[name]=x[name]
                                self.assertEqual(set(x),set(y),path)
                                for key in x:restore(x[key],y[key],path+(key,))
                            elif isinstance(x,list) and isinstance(y,list):
                                self.assertEqual(len(x),len(y))
                                for i,(xx,yy) in enumerate(zip(x,y)):restore(xx,yy,path+(i,))
                        restore(a,b)
                        # Native newline is retained; no stripping or normalizing.
                        encoded=json.dumps(b,ensure_ascii=False,indent=2,allow_nan=False).replace('\n',os.linesep)+os.linesep
                        self.assertEqual(before.stdout,encoded.encode('utf-8'))

    def test_documented_nine_commands_with_separate_supplied_review(self):
        import re,shlex
        commands=re.findall(r'^python (.+)$',(ROOT/'docs/AMENDMENT_LEDGER.md').read_text(encoding='utf-8'),re.M)
        self.assertEqual(len(commands),9)
        sources={p:p.read_bytes() for p in (ROOT/'examples').glob('*amendment*.json')}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            for command in commands:
                args=[str(out/a[5:]) if a.startswith('WORK/') else a for a in shlex.split(command)]
                if args[:2]==['amendment_intake.py','assemble']:
                    supplied=json.loads((out/'target.json').read_bytes())['review_document']
                    supplied.update(receipt_id='fictional-guide-review',decision='record_supplied_amendment',reviewer='Fictional reviewer',reviewed_at='2026-11-15',rationale='Fictional recording only')
                    (out/'review.json').write_bytes(json.dumps(supplied).encode())
                result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                self.assertEqual((result.returncode,result.stderr),(0,b''),command)
            final=json.loads((out/'recorded.json').read_bytes());after=json.loads((ROOT/'examples/amendment-after.json').read_bytes())
            actual=run(final);actual.pop('amendments');self.assertEqual(actual,run(after))
        for path,raw in sources.items():self.assertEqual(path.read_bytes(),raw)

    def test_cli_exact_journey_errors_negative_and_exclusive_outputs(self):
        b=base();a=changed(b);d=candidate(b,a);r=review(b,a,d)
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            for n,v in [('before',b),('after',a),('candidate',d),('review',r)]: (td/(n+'.json')).write_bytes(json.dumps(v).encode())
            invoke=lambda *args:subprocess.run([sys.executable,'amendment_intake.py',*map(str,args)],cwd=ROOT,capture_output=True)
            for cmd in ('template','target','assemble'):
                args=[cmd,td/'before.json',td/'after.json']
                if cmd!='template':args.append(td/'candidate.json')
                if cmd=='assemble':args.append(td/'review.json')
                output=td/(cmd+'.json');result=invoke(*args,'--output',output)
                self.assertEqual((result.returncode,result.stderr),(0,b''));self.assertEqual(json.loads(result.stdout),json.loads(output.read_bytes()))
            result=invoke('verify',td/'before.json',td/'after.json',td/'assemble.json','--protocol-output',td/'final.json')
            self.assertEqual(result.returncode,0);self.assertTrue(json.loads(result.stdout)['valid'])
            original=(td/'final.json').read_bytes();result=invoke('verify',td/'before.json',td/'after.json',td/'assemble.json','--protocol-output',td/'final.json')
            self.assertEqual((result.returncode,result.stdout),(1,b''));self.assertNotIn(str(td).encode(),result.stderr);self.assertEqual((td/'final.json').read_bytes(),original)
            compare=subprocess.run([sys.executable,'compare_runs.py',str(td/'before.json'),str(td/'final.json'),'--amendment-id','A1'],cwd=ROOT,capture_output=True)
            self.assertEqual(compare.returncode,0)
            bad=copy.deepcopy(b);bad['version']='wrong';(td/'wrong.json').write_bytes(json.dumps(bad).encode())
            compare=subprocess.run([sys.executable,'compare_runs.py',str(td/'wrong.json'),str(td/'final.json'),'--amendment-id','A1'],cwd=ROOT,capture_output=True)
            self.assertEqual((compare.returncode,compare.stderr),(1,b''));self.assertEqual(json.loads(compare.stdout)['embedded_amendment_review']['binding_status'],'MISMATCH')
            usage=invoke();self.assertEqual(usage.returncode,2)
            missing=invoke('template',td/'PRIVATE-missing',td/'after.json');self.assertEqual((missing.returncode,missing.stdout),(1,b''));self.assertNotIn(b'PRIVATE',missing.stderr)
            real=invoke('template',td/'before.json',td/'after.json')
            direct=run_cli('amendment_intake.py','template',str(td/'before.json'),str(td/'after.json'),cwd=ROOT)
            self.assertEqual((real.returncode,real.stdout,real.stderr),(direct.returncode,direct.stdout,direct.stderr))


if __name__=='__main__':unittest.main()
