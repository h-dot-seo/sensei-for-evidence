"""Supplied labels bind reviews but never determine scientific findings."""
import copy
import hashlib
import json
import re
import shlex
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from json_io import canonical_json_bytes
from evidence_workflow import run
from evidence_basis_links import FIELDS
import evidence_basis_intake as intake
from evidence_basis_review import review
from research_status import status
from synthesis_review import snapshot
from compare_runs import compare_protocols
from review_handoff import handoff

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT/'examples'/name).read_bytes())

def label(eid='e1'):
    return dict(evidence_id=eid,text_access='ABSTRACT_ONLY',value_origin='REPORTED_TEXT',
        finding_kind='UNCLEAR',uncertainty=dict(status='unknown',reason='Synthetic unknown',source_locator='Synthetic page'),
        document_source_ids=[],declared_by='Synthetic declarer',declared_at='2026-11-14',limitations='Synthetic only')

class EvidenceBasisTests(unittest.TestCase):
    def setUp(self):
        self.p=load('synthesis-review.json')
        self.d=dict(schema_version=1,evidence_bases=[label()])

    def application(self):
        target=intake.prepare(self.p,self.d)
        review=target['review_document'];review.update(receipt_id='synthetic-import',decision='import_evidence_bases',
            reviewer='Synthetic importer',reviewed_at='2026-11-14',rationale='Record supplied labels, not endorse truth')
        return intake.assemble(self.p,self.d,review)

    def test_actual_previous_44_protocol_outputs_exactly_preserved_without_labels(self):
        baseline=json.loads((ROOT/'tests/evidence_basis_legacy_baselines.json').read_bytes())
        self.assertEqual(len(baseline['cases']),44)
        for case in baseline['cases']:
            with self.subTest(path=case['path']):
                p=json.loads((ROOT/case['path']).read_bytes())
                self.assertEqual(hashlib.sha256(canonical_json_bytes(p)).hexdigest(),case['input_sha256'])
                self.assertEqual(hashlib.sha256(canonical_json_bytes(run(p))).hexdigest(),case['run_sha256'])

    def test_template_null_and_separate_review_required(self):
        t=intake.template(self.p,dict(schema_version=1,evidence_ids=['e1']))
        row=t['candidate_document']['evidence_bases'][0]
        self.assertEqual(set(row),FIELDS)
        self.assertEqual(row['evidence_id'],'e1')
        self.assertTrue(all(v is None for k,v in row.items() if k!='evidence_id'))
        with self.assertRaises(ValueError):intake.prepare(self.p,t['candidate_document'])
        t=intake.prepare(self.p,self.d)
        with self.assertRaises(ValueError):intake.assemble(self.p,self.d,t['review_document'])
        self.assertIsNone(t['review_document']['decision'])

    def test_append_exact_replay_preserves_original(self):
        p=copy.deepcopy(self.p);d=copy.deepcopy(self.d)
        a=self.application();self.assertTrue(intake.verify(self.p,a)['valid'])
        restored=copy.deepcopy(a['protocol_candidate']);restored.pop('evidence_bases')
        self.assertEqual(restored,p);self.assertEqual(self.p,p);self.assertEqual(self.d,d)
        with self.assertRaises(ValueError):intake.prepare(a['protocol_candidate'],d)
        for field in ('reviewer','decision','target_sha256'):
            b=copy.deepcopy(a);b['receipt']['assertion'][field]='tampered'
            with self.assertRaises(ValueError):intake.verify(self.p,b)
        p['question']+=' changed'
        with self.assertRaises(ValueError):intake.verify(p,a)

    def test_conditional_current_stale_and_no_automatic_renewal(self):
        old=run(self.p);p=copy.deepcopy(self.p);p['evidence_bases']=[label()];new=run(p)
        self.assertEqual(old['synthesis']['stale_statement_ids'],[])
        self.assertIn('statement-1',new['synthesis']['stale_statement_ids'])
        self.assertEqual(p['synthesis_statements'],self.p['synthesis_statements'])
        self.assertEqual(old['evidence'],new['evidence']);self.assertEqual(old['flow'],new['flow'])
        self.assertEqual(old['work_packages'],new['work_packages'])
        self.assertNotIn('evidence_bases',old)
        self.assertNotIn('evidence_bases',old['synthesis']['review_targets'][0]['basis'])
        self.assertIn('evidence_bases',new['synthesis']['review_targets'][0]['basis'])
        # Presence, including an empty ledger, is a deliberate stage transition.
        empty=run(dict(self.p,evidence_bases=[]))
        self.assertIn('statement-1',empty['synthesis']['stale_statement_ids'])

    def test_invalid_shapes_and_explicit_null(self):
        for rows in (None,{},False,[None],[dict(label(),extra='x')],[label(),label()],
                     [dict(label(),evidence_id='missing')],[dict(label(),text_access='SUPPLEMENT')],
                     [dict(label(),finding_kind='NO_EFFECT_REPORTED')],[dict(label(),declared_at='2026-02-30')],
                     [dict(label(),document_source_ids=None)],[dict(label(),uncertainty='unknown')]):
            with self.subTest(rows=rows),self.assertRaises(ValueError):run(dict(self.p,evidence_bases=rows))
        with patch('evidence_basis_links.MAX_LEDGER_BYTES',1),self.assertRaises(ValueError):run(dict(self.p,evidence_bases=[label()]))
        for ids in (None,[],['e1','e1'],['unknown']):
            with self.assertRaises(ValueError):intake.template(self.p,dict(schema_version=1,evidence_ids=ids))
        for count in (0,101):
            with self.assertRaises(ValueError):intake.prepare(self.p,dict(schema_version=1,evidence_bases=[label()]*count))

    def test_uncertainty_is_status_text_not_numeric_inference(self):
        for state in ('reported','not_reported','unknown','not_applicable'):
            row=label();row['uncertainty']=dict(status=state,source_locator='Synthetic locator')
            row['uncertainty']['value' if state=='reported' else 'reason']='not a number, deliberately'
            result=run(dict(self.p,evidence_bases=[row]))
            self.assertEqual(result['evidence_bases']['basis_ledger'][0]['uncertainty'],row['uncertainty'])

    def test_views_and_literal_transition_not_gate_policy(self):
        p=dict(self.p,evidence_bases=[label()]);s=status(p)
        self.assertEqual(s['queues']['evidence_without_basis'],['e2','e3'])
        self.assertIn('statement-1',s['queues']['statements_with_abstract_only_citations'])
        self.assertEqual(review(p)['stage'],'SUPPLIED')
        snap=snapshot(p);self.assertEqual(snap['evidence_citation_index'][0]['supplied_evidence_basis']['text_access'],'ABSTRACT_ONLY')
        handoff(p)
        q=copy.deepcopy(p);q['evidence_bases'][0]['text_access']='FULL_TEXT'
        compared=compare_protocols(p,q)
        self.assertEqual(compared['entity_changes']['evidence']['changed'],[])
        self.assertEqual(compared['evidence_basis_label_transitions'][0]['before']['text_access'],'ABSTRACT_ONLY')
        self.assertEqual(run(q)['readiness'],run(p)['readiness'])

    def test_document_membership_multiple_sources_and_unbound_bytes(self):
        p=load('extraction-worksheet-protocol.json');row=label('result-A-second')
        row['document_source_ids']=['source-main','source-supplement'];p['evidence_bases']=[row]
        linked=run(p)['evidence_bases']['basis_ledger'][0]['document_sources']
        self.assertEqual(len(linked),2)
        self.assertEqual(linked[0]['document_binding'],'DECLARED_HASH_UNVERIFIED')
        p['report_sources'][0]['document_sha256']=None
        self.assertEqual(run(p)['evidence_bases']['basis_ledger'][0]['document_sources'][0]['document_binding'],'DOCUMENT_BYTES_UNBOUND')
        for ids in (['missing'],['source-main','source-main']):
            q=copy.deepcopy(p);q['evidence_bases'][0]['document_source_ids']=ids
            with self.assertRaises(ValueError):run(q)
        q=copy.deepcopy(self.p);q['evidence_bases']=[dict(label(),document_source_ids=['source-main'])]
        with self.assertRaises(ValueError):run(q)

    def test_figure_statistics_coexistence_is_only_cue(self):
        p=load('statistics-review.json');unit=p['experimental_units'][0]
        eid=unit['outcome_statistics'][0]['evidence_id'];row=label(eid)
        row['value_origin']='FIGURE_VISUAL_ESTIMATE';p['evidence_bases']=[row]
        result=run(p)
        self.assertIn(eid,result['evidence_bases']['figure_estimate_results_with_reported_statistics'])
        self.assertEqual(result['evidence'],run(dict(p,evidence_bases=[]))['evidence'])
        for key in ('value','dispersion'):
            for arm in ('treatment','comparator'):
                unit['outcome_statistics'][0][arm][key]=dict(status='not_reported',reason='Synthetic figure estimate; no exact value',source_locator='Synthetic figure')
        for key in ('estimate','uncertainty'):
            unit['outcome_statistics'][0]['contrast'][key]=dict(status='not_reported',reason='Synthetic unknown',source_locator='Synthetic figure')
        self.assertNotIn(eid,run(p)['evidence_bases']['figure_estimate_results_with_reported_statistics'])

    def test_documented_eleven_command_journey(self):
        doc=(ROOT/'docs/EVIDENCE_BASIS.md').read_text(encoding='utf-8')
        commands=[line for block in re.findall(r'```sh\n(.*?)```',doc,re.S) for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),11)
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);(work/'examples').mkdir()
            for name in ('synthesis-review.json','evidence-basis-references.json','manual-evidence-basis-candidates.json'):
                shutil.copyfile(ROOT/'examples'/name,work/'examples'/name)
            original={p:p.read_bytes() for p in (work/'examples').iterdir()}
            for line in commands:
                args=shlex.split(line)[1:];args[0]=str(ROOT/args[0])
                result=subprocess.run([sys.executable,'-B',*args],cwd=work,capture_output=True,timeout=30)
                self.assertEqual((result.returncode,result.stderr),(0,b''),line)
                if ' target ' in line:
                    r=json.loads((work/'basis-target.json').read_bytes())['review_document']
                    r.update(receipt_id='fictional-basis-import',decision='import_evidence_bases',reviewer='Fictional importer',reviewed_at='2026-11-14',rationale='Record fictional labels only')
                    (work/'basis-review.json').write_bytes((json.dumps(r)+'\n').encode())
            self.assertEqual({p:p.read_bytes() for p in original},original)
            q=json.loads((work/'basis-protocol.json').read_bytes())
            self.assertEqual(q['evidence_bases'],self.d['evidence_bases'])
            self.assertIn('statement-1',run(q)['synthesis']['stale_statement_ids'])

    def test_real_cli_fixed_error_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);pp=t/'protocol.json';dd=t/'candidates.json';rr=t/'review.json';out=t/'target.json'
            pp.write_text(json.dumps(self.p),encoding='utf-8');dd.write_text(json.dumps(self.d),encoding='utf-8')
            def call(*args):return subprocess.run([sys.executable,str(ROOT/'evidence_basis_intake.py'),*map(str,args)],capture_output=True)
            r=call('target',pp,dd,'--output',out);self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(r.stderr,b'');saved=out.read_bytes()
            r=call('target',pp,dd,'--output',out);self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b'')
            self.assertNotIn(str(t).encode(),r.stderr);self.assertEqual(out.read_bytes(),saved)
            target=json.loads(saved);rv=target['review_document'];rv.update(receipt_id='synthetic',decision='import_evidence_bases',reviewer='Synthetic',reviewed_at='2026-11-14',rationale='Synthetic only')
            rr.write_text(json.dumps(rv),encoding='utf-8');app=t/'application.json'
            r=call('assemble',pp,dd,rr,'--output',app);self.assertEqual(r.returncode,0,r.stderr)
            r=call('verify',pp,app,'--protocol-output',t/'candidate.json');self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue(json.loads(r.stdout)['valid'])

if __name__=='__main__':unittest.main()
