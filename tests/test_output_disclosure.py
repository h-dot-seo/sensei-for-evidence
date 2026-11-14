"""Supplied disclosure/attachment consistency never becomes publication or scientific approval."""
import copy
import hashlib
import io
import os
import re
import shlex
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from evidence_workflow import run
from tests._disclosure_compat import prior_bytes
import output_disclosure_intake as intake
from output_disclosure_review import review, render_text
from output_disclosure_links import CANDIDATE_FIELDS, FIELDS, NEGATIVE_CLAIMS
import readiness_intake
from tests.test_bibliographic_assertion_continuation import base, assertion, append, imported
from research_bundle import build_bundle, verify_bytes
from research_status import status
from review_handoff import handoff
from compare_runs import compare_protocols
import artifact_review

ROOT=Path(__file__).resolve().parents[1]


def ready(p=None):
    p=base() if p is None else p
    return append(readiness_intake,p,assertion(p),'import_readiness_assertions')['protocol_candidate']


def row(p,rid='disclosure-one'):
    r=intake.template(p,'fictional-assertion')['candidate_document']['output_disclosures'][0]
    r.update(release_id=rid,released_by='Fictional recorder',released_at='2026-11-14',scope_statement='Synthetic scope',
        coverage_disclosure='Synthetic incomplete coverage',limitations_disclosure='Synthetic only',
        supplied_relevance_statement='Supplied relevance, not assessed',supplied_confidence_label='Uncertain supplied label',
        supplied_recommendation_strength=None,release_readiness='RELEASED_WITHIN_SCOPE')
    return r


def document(*rows):return dict(schema_version=1,output_disclosures=list(rows))


def application(p,d,**kwargs):
    r=intake.prepare(p,d,**kwargs)['review_document'];r.update(receipt_id='fictional-import-review',decision='record_supplied_disclosures',
        reviewer='Fictional reviewer',reviewed_at='2026-11-14',rationale='Record supplied labels; not publish anything')
    return intake.assemble(p,d,r,**kwargs)


class OutputDisclosureTests(unittest.TestCase):
    def test_exact_engine_additions_preserve_previous_source(self):
        prior=json.loads((ROOT/'tests/output_disclosure_legacy_baselines.json').read_bytes())['prior_source_sha256']
        for name in ('evidence_workflow.py','adapter_integrity.py','bibliographic_integrity.py','research_bundle.py'):
            self.assertEqual(hashlib.sha256(prior_bytes(name)).hexdigest(),prior[name])

    def test_actual_previous_cli_raw_bytes_without_disclosures(self):
        data=json.loads((ROOT/'tests/output_disclosure_legacy_baselines.json').read_bytes())
        self.assertEqual(len(data['cases']),12)
        for case in data['cases']:
            self.assertEqual(hashlib.sha256((ROOT/case['args'][1]).read_bytes()).hexdigest(),case['input_sha256'])
            result=subprocess.run([sys.executable,*case['args']],cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,case['returncode'])
            key='stdout_crlf_sha256' if os.linesep=='\r\n' else 'stdout_lf_sha256'
            self.assertEqual(hashlib.sha256(result.stdout).hexdigest(),case[key])
            self.assertEqual(hashlib.sha256(result.stderr).hexdigest(),case['stderr_sha256'])

    def test_blank_separate_review_and_release_not_ready_coexist(self):
        p=ready();t=intake.template(p,'fictional-assertion');self.assertIsNone(t['candidate_document']['output_disclosures'][0]['release_readiness'])
        with self.assertRaises(ValueError):intake.prepare(p,t['candidate_document'])
        d=document(row(p));target=intake.prepare(p,d)
        with self.assertRaises(ValueError):intake.assemble(p,d,target['review_document'])
        a=application(p,d);self.assertTrue(intake.verify(p,a)['valid']);q=a['protocol_candidate'];current=run(q)
        context=current.pop('output_disclosures');self.assertEqual(current,run(p))
        self.assertEqual(context['released_with_not_ready_assertion'],['disclosure-one'])
        self.assertEqual(context['mechanical_release_readiness'],'NOT_RELEASED');self.assertFalse(context['actual_publication_performed'])
        self.assertEqual(context['disclosure_assessment'],'NOT_PERFORMED')
        self.assertEqual(p,ready());self.assertNotIn('output_disclosures',p)

    def test_prefix_original_preservation_duplicates_and_exact_replay(self):
        p=ready();d=document(row(p));a=application(p,d);q=a['protocol_candidate']
        b=application(q,document(row(q,'second')));self.assertEqual(b['protocol_candidate']['output_disclosures'][0],q['output_disclosures'][0])
        restored=copy.deepcopy(b['protocol_candidate']);restored.pop('output_disclosures');self.assertEqual(restored,p)
        for doc in (d,document(row(q,'third'),row(q,'third'))):
            with self.assertRaises(ValueError):intake.prepare(q,doc)
        changed=copy.deepcopy(a);changed['receipt']['assertion']['reviewer']='tampered'
        with self.assertRaises(ValueError):intake.verify(p,changed)
        changed=copy.deepcopy(a);changed['protocol_candidate']['output_disclosures'][0]['release_readiness']='WITHHELD'
        with self.assertRaises(ValueError):intake.verify(p,changed)
        p['question']+=' changed'
        with self.assertRaises(ValueError):intake.verify(p,a)

    def test_exact_gate_item_pairs_not_substrings_and_stale(self):
        p=base();p['searches']=[dict(p['search_plan'][0],searched_at='2026-11-14',record_ids=['r1','r10'],total_count=2,complete=True,has_more=False)]
        p=ready(p);r=row(p);r['unresolved_issues']=[dict(gate_id='screening_complete',item_id='r10',statement='Only r10 named')]
        a=application(p,document(r));q=a['protocol_candidate'];ctx=run(q)['output_disclosures']['disclosure_ledger'][0]
        self.assertIn(dict(gate_id='screening_complete',item_id='r1'),ctx['open_items_not_named_in_disclosure'])
        self.assertNotIn(dict(gate_id='screening_complete',item_id='r10'),ctx['open_items_not_named_in_disclosure'])
        q['screening']=[dict(record_id='r1',decision='exclude',reason='Fictional supplied exclusion')]
        self.assertEqual(run(q)['output_disclosures']['stale_disclosure_ids'],['disclosure-one'])
        with self.assertRaises(ValueError):intake.prepare(q,document(row(q,'new')))
        self.assertEqual(q['output_disclosures'],a['protocol_candidate']['output_disclosures'])

    def test_bundle_requires_actual_original_and_same_bytes_on_replay(self):
        p=ready();d=document(row(p));raw=build_bundle((json.dumps(p)+'\n').encode())
        a=application(p,d,bundle=raw);self.assertTrue(intake.verify(p,a,bundle=raw)['valid'])
        self.assertTrue(a['receipt']['target']['bundle_context']['bundle_manifest_sha256'])
        with self.assertRaises(ValueError):intake.verify(p,a)
        for bad in (raw+b'x',b'',None):
            with self.assertRaises((ValueError,zipfile.BadZipFile)):intake.prepare(p,d,bundle=bad)
        other=copy.deepcopy(p);other['question']+=' changed';bad=build_bundle(json.dumps(other).encode())
        with self.assertRaises(ValueError):intake.prepare(p,d,bundle=bad)
        resulting=build_bundle(json.dumps(a['protocol_candidate']).encode())
        with self.assertRaises(ValueError):intake.verify(p,a,bundle=resulting)
        reformatted=build_bundle(json.dumps(p,sort_keys=True,indent=2).encode())
        self.assertTrue(application(p,d,bundle=reformatted))
        with self.assertRaises(ValueError):intake.verify(p,a,bundle=reformatted)

    def synthetic_observation(self,p):
        research=run(p);work=research['work_packages'][0];content=b'fictional artifact\n';sha=hashlib.sha256(content).hexdigest()
        entry=dict(work_package_id=work['work_package_id'],artifact_locator=work['artifact_locator'],path='synthetic.txt',bytes=len(content),sha256=sha)
        observed=dict(entry,status='BYTES_MATCH',observed_bytes=len(content),observed_sha256=sha,
            supplied_work_status=work['status'],completion_source_status=research['planning']['completion_ledger'][0]['source_match_status'],
            question=work['question'],deliverable=work['deliverable'],acceptance_criterion=work['acceptance_criterion'],
            supplied_acceptance_verified=work.get('acceptance_verified'),depends_on=work['depends_on'],blocked_by=work['blocked_by'],acceptance_assessment='NOT_PERFORMED')
        manifest=dict(schema_version=1,artifacts=[entry])
        doc=dict(schema_version=1,protocol_sha256=intake.digest(p),manifest_sha256=intake.digest(manifest),engine_sha256={'unverified-recorded-engine.py':'0'*64},
            artifacts=[observed],uninspected_work_ids=sorted(w['work_package_id'] for w in research['work_packages'][1:]),all_requested_bytes_match=True,
            inspection_scope='Synthetic supplied observation only',census_claim='NOT_ESTABLISHED',conclusion_readiness='NOT_READY',boundary='Synthetic untrusted observation, not live checking')
        return doc,entry,content

    def artifact_protocol(self):
        p=json.loads((ROOT/'examples/protocol.json').read_bytes())
        p['gaps'][0]['artifact_locator']='synthetic:artifact'
        return ready(p)

    def test_optional_observations_bound_untrusted_and_no_source_open(self):
        p=self.artifact_protocol();obs,entry,_=self.synthetic_observation(p);r=row(p)
        r['required_artifacts']=[{k:entry[k] for k in ('work_package_id','artifact_locator','sha256')}]
        with patch.object(artifact_review,'open_root',side_effect=AssertionError('no artifact access')),patch.object(artifact_review,'check_file',side_effect=AssertionError('no artifact access')):
            a=application(p,document(r),observations=obs);self.assertTrue(intake.verify(p,a,observations=obs)['valid'])
        target=a['receipt']['target'];self.assertFalse(target['artifact_observation_context']['recorded_engine_verified'])
        self.assertEqual(target['artifact_checks'][0]['recorded_observation_status'],'RECORDED_BYTES_MATCH')
        self.assertFalse(target['artifact_checks'][0]['live_bytes_checked'])
        for bad in (None,dict(obs,protocol_sha256='1'*64),dict(obs,extra='x')):
            with self.assertRaises(ValueError):intake.prepare(p,document(r),observations=bad)
        with self.assertRaises(ValueError):intake.verify(p,a)
        bad=copy.deepcopy(obs);bad['engine_sha256']['unverified-recorded-engine.py']='1'*64
        with self.assertRaises(ValueError):intake.verify(p,a,observations=bad)
        negative=copy.deepcopy(obs);negative['artifacts'][0].update(status='MISSING',observed_bytes=None,observed_sha256=None);negative['all_requested_bytes_match']=False
        b=application(p,document(r),observations=negative)
        self.assertEqual(b['receipt']['target']['artifact_checks'][0]['recorded_observation_status'],'RECORDED_MISMATCH_OR_UNVERIFIED')
        self.assertTrue(intake.verify(p,b,observations=negative)['valid'])

    @unittest.skipUnless(artifact_review.secure_open_supported(), 'secure native source access unavailable')
    def test_actual_saved_artifact_observation_is_accepted_without_reopening_file(self):
        p=self.artifact_protocol();_,entry,content=self.synthetic_observation(p)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/entry['path'];path.write_bytes(content)
            observed=artifact_review.review_artifacts(p,dict(schema_version=1,artifacts=[entry]),td)
            path.unlink()  # Later intake does not claim these bytes still exist.
            r=row(p);r['required_artifacts']=[{k:entry[k] for k in ('work_package_id','artifact_locator','sha256')}]
            a=application(p,document(r),observations=observed)
            self.assertTrue(intake.verify(p,a,observations=observed)['valid'])
            self.assertFalse(a['receipt']['target']['artifact_checks'][0]['live_bytes_checked'])

    def test_views_and_three_native_imports_preserve_existing_results(self):
        for fmt in ('CSV','NBIB','RIS'):
            p=ready(imported(fmt)[3]);q=application(p,document(row(p)))['protocol_candidate']
            self.assertEqual(run(p),{k:v for k,v in run(q).items() if k!='output_disclosures'})
            for func in (status,handoff):self.assertIn('output_disclosures',func(q));self.assertNotIn('output_disclosures',func(p))
            diff=compare_protocols(p,q);self.assertFalse(diff['output_disclosure_context']['actual_publication_performed'])
            self.assertIn('NOT_RELEASED',render_text(review(q)))
            raw=build_bundle(json.dumps(q).encode());self.assertTrue(verify_bytes(raw)['valid'])
            with zipfile.ZipFile(io.BytesIO(raw)) as z:self.assertIn(b'NOT_RELEASED',z.read('summary.md'))

    def test_eleven_documented_commands_with_explicit_saved_attachments(self):
        commands=re.findall(r'^python (.+)$',(ROOT/'docs/OUTPUT_DISCLOSURE.md').read_text(),re.M)
        self.assertEqual(len(commands),11)
        source=ROOT/'examples/output-disclosure-input.json';before=source.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            work=Path(td)
            for command in commands:
                args=[str(work/a[5:]) if a.startswith('WORK/') else str(ROOT/a) if a.endswith('.py') or a.startswith('examples/') else a for a in shlex.split(command)]
                if args[0].endswith('output_disclosure_intake.py') and args[1]=='assemble':
                    r=json.loads((work/'target.json').read_bytes())['review_document']
                    r.update(receipt_id='fictional-guide-review',decision='record_supplied_disclosures',reviewer='Fictional reviewer',reviewed_at='2026-11-14',rationale='Record fictional labels, not actual publication')
                    (work/'import-review.json').write_bytes((json.dumps(r)+'\n').encode())
                result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,(command,result.stderr));self.assertEqual(result.stderr,b'')
            q=json.loads((work/'disclosed.json').read_bytes());p=json.loads(before)
            self.assertEqual(run(p),{k:v for k,v in run(q).items() if k!='output_disclosures'})
            self.assertFalse(run(q)['output_disclosures']['actual_publication_performed'])
        self.assertEqual(source.read_bytes(),before)

    def test_shape_limits_and_cli_fixed_error(self):
        p=ready();r=row(p)
        for bad in (dict(r,extra=True),dict(r,released_at='2026-02-30'),dict(r,gates_sha256='0'*64),dict(r,release_readiness='APPROVED')):
            with self.assertRaises(ValueError):intake.prepare(p,document(bad))
        with self.assertRaises(ValueError):intake.prepare(p,document(*(row(p,str(i)) for i in range(101))))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'private-marker.json';source.write_bytes(b'null')
            result=subprocess.run([sys.executable,str(ROOT/'output_disclosure_intake.py'),'template',str(source),'fictional-assertion'],capture_output=True)
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertNotIn(b'private-marker',result.stderr)

if __name__=='__main__':unittest.main()
