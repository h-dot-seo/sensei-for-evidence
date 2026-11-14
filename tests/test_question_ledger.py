"""Supplied question lifecycles never assess answers or alter existing gates."""
import copy
import io
import hashlib
import os
import re
import shlex
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from evidence_workflow import run
import question_intake as intake
from question_links import TRANSITIONS, question_basis
from question_review import review
from research_status import status
from synthesis_review import snapshot
from readiness_review import review as readiness_view
from review_handoff import handoff
from compare_runs import compare_protocols
from research_bundle import build_bundle, verify_bytes
from tests.test_bibliographic_assertion_continuation import imported, research

ROOT = Path(__file__).resolve().parents[1]

def base(): return json.loads((ROOT/'examples/bibliographic-base.json').read_bytes())

def row(p, qid='question-one', status='OPEN', parent=None, sids=None):
    sids = [] if sids is None else sids
    return dict(question_id=qid, text='Fictional supplied question?', status=status, parent_question_id=parent,
        origin=dict(kind='PROTOCOL', ref_id=None, protocol_question_sha256=intake.digest(p['question']), external_record_sha256=None, label='Fictional protocol declaration'),
        statement_ids=sids, basis_sha256=question_basis(run(p)['synthesis'],sids), recorded_by='Fictional recorder',
        recorded_at='2026-11-14', rationale='Fictional supplied rationale', limitations='Synthetic only', reopening=None)

def document(*rows): return dict(schema_version=1, operation='append', question_records=list(rows))

def application(p,d):
    r=intake.prepare(p,d)['review_document'];r.update(receipt_id='synthetic-review',decision='record_supplied_questions',
        reviewer='Fictional reviewer',reviewed_at='2026-11-14',rationale='Record supplied labels only')
    return intake.assemble(p,d,r)

def transition(p,qid,status,sids=None):
    t=intake.transition_template(p,qid)['candidate_document'];r=row(p,qid,status,sids=sids)
    t['changes']={key:r[key] for key in intake.CHANGED_FIELDS}
    return t

class QuestionLedgerTests(unittest.TestCase):
    def test_exact_engine_additions_preserve_prior_implementation_bytes(self):
        prior=json.loads((ROOT/'tests/question_legacy_baselines.json').read_bytes())['prior_source_sha256']
        additions=json.loads((ROOT/'tests/question_source_additions.json').read_bytes())
        for name in ('adapter_integrity.py','bibliographic_integrity.py'):
            source=(ROOT/name).read_bytes();token=b"'evidence_bases', 'question_records'"
            self.assertEqual(source.count(token),1)
            self.assertEqual(hashlib.sha256(source.replace(token,b"'evidence_bases'",1)).hexdigest(),prior[name])
        source=(ROOT/'evidence_workflow.py').read_bytes();token=additions['engine_hook'].encode()
        self.assertEqual(source.count(token),1)
        self.assertEqual(hashlib.sha256(source.replace(token,b'',1)).hexdigest(),prior['evidence_workflow.py'])
        source=(ROOT/'research_bundle.py').read_bytes();token=additions['bundle_summary'].encode()
        self.assertEqual(source.count(token),1);source=source.replace(token,b'',1)
        token=b"'archive_safety.py', 'question_links.py')";self.assertEqual(source.count(token),1)
        source=source.replace(token,b"'archive_safety.py')",1)
        self.assertEqual(hashlib.sha256(source).hexdigest(),prior['research_bundle.py'])

    def test_actual_previous_cli_raw_bytes_without_questions(self):
        baseline=json.loads((ROOT/'tests/question_legacy_baselines.json').read_bytes())
        self.assertEqual(len(baseline['cases']),12)
        for case in baseline['cases']:
            with self.subTest(args=case['args']):
                self.assertEqual(hashlib.sha256((ROOT/case['args'][1]).read_bytes()).hexdigest(),case['input_sha256'])
                process=subprocess.run([sys.executable,*case['args']],cwd=ROOT,capture_output=True)
                self.assertEqual(process.returncode,case['returncode'])
                key='stdout_crlf_sha256' if os.linesep=='\r\n' else 'stdout_lf_sha256'
                self.assertEqual(hashlib.sha256(process.stdout).hexdigest(),case[key])
                self.assertEqual(hashlib.sha256(process.stderr).hexdigest(),case['stderr_sha256'])

    def test_blank_template_early_unresolved_and_separate_review(self):
        p=base();t=intake.template(p);r=t['candidate_document']['question_records'][0]
        self.assertEqual(r['text'],p['question']);self.assertIsNone(r['status']);self.assertIsNone(r['recorded_by'])
        with self.assertRaises(ValueError):intake.prepare(p,t['candidate_document'])
        d=document(row(p,status='UNRESOLVED'));target=intake.prepare(p,d)
        self.assertIsNone(target['review_document']['decision'])
        with self.assertRaises(ValueError):intake.assemble(p,d,target['review_document'])
        a=application(p,d);self.assertTrue(intake.verify(p,a)['valid']);q=a['protocol_candidate']
        actual=run(q);self.assertEqual(actual['question_ledger']['unresolved_question_ids'],['question-one'])
        self.assertEqual(actual['question_ledger']['question_ledger'][0]['source_match_status'],'NOT_LINKED')
        actual.pop('question_ledger');self.assertEqual(actual,run(p));self.assertNotIn('question_records',p)

    def test_exact_transition_table_and_preserved_identity_fields(self):
        self.assertEqual(TRANSITIONS,{'OPEN':('NARROWED','ANSWERED_WITHIN_BOUNDS','UNRESOLVED'),
            'NARROWED':('ANSWERED_WITHIN_BOUNDS','UNRESOLVED'),'ANSWERED_WITHIN_BOUNDS':(),'UNRESOLVED':()})
        p=research('CSV')[3]
        for old in TRANSITIONS:
            q=copy.deepcopy(p);q['question_records']=[row(q,status=old,sids=['statement-one']),row(q,qid='child',parent='question-one')]
            run(q)
            for new in TRANSITIONS:
                d=dict(schema_version=1,operation='transition',question_id='question-one',changes={k:row(q,status=new,sids=['statement-one'])[k] for k in intake.CHANGED_FIELDS})
                if new in TRANSITIONS[old]:
                    a=application(q,d);self.assertTrue(intake.verify(q,a)['valid'])
                    current=a['protocol_candidate']['question_records'][0]
                    for key in set(current)-intake.CHANGED_FIELDS:self.assertEqual(current[key],q['question_records'][0][key])
                    self.assertEqual(a['protocol_candidate']['question_records'][1],q['question_records'][1])
                else:
                    with self.assertRaises(ValueError):intake.prepare(q,d)
            if not TRANSITIONS[old]:
                with self.assertRaises(ValueError):intake.transition_template(q,'question-one')
        q=application(p,document(row(p)))['protocol_candidate']
        d=transition(q,'question-one','UNRESOLVED');d['changes']['text']='changed'
        with self.assertRaises(ValueError):intake.prepare(q,d)

    def test_children_cycle_duplicate_missing_and_unknown_fields(self):
        p=base();parent=row(p,status='NARROWED');child=row(p,qid='child',parent='question-one')
        self.assertTrue(intake.verify(p,application(p,document(parent,child)))['valid'])
        bads=[document(parent),document(child),document(row(p),row(p)),document(dict(row(p),extra=True))]
        a=copy.deepcopy(parent);a['parent_question_id']='child';bads.append(document(a,child))
        a=row(p);a['parent_question_id']='question-one';bads.append(document(a))
        for d in bads:
            with self.subTest(d=d):
                with self.assertRaises(ValueError):intake.prepare(p,d)
        with self.assertRaises(ValueError):intake.prepare(p,document(row(p,status='ANSWERED_WITHIN_BOUNDS')))

    def test_stale_links_origin_and_gate_policy_remain_visible(self):
        p=research('CSV')[3];d=document(row(p,status='ANSWERED_WITHIN_BOUNDS',sids=['statement-one']))
        q=application(p,d)['protocol_candidate'];original=copy.deepcopy(q['question_records'])
        before=run(p);after=run(q);self.assertEqual(before,{k:v for k,v in after.items() if k!='question_ledger'})
        q['synthesis_statements'][0]['text']+=' changed';actual=run(q)
        self.assertEqual(actual['question_ledger']['stale_question_bindings'],['question-one'])
        self.assertEqual(q['question_records'],original)
        plain=base();plain['question_records']=[row(plain)];plain['question']+=' changed'
        self.assertEqual(run(plain)['question_ledger']['changed_protocol_question_origins'],['question-one'])
        q['question']+=' changed'
        with self.assertRaises(ValueError):run(q)  # Bibliographic root remains immutable.
        self.assertEqual(q['question_records'],original)
        with self.assertRaises(ValueError):intake.prepare(p,document(dict(d['question_records'][0],basis_sha256='0'*64)))

    def test_origin_existence_controlled_consultation_and_no_external_reads(self):
        p=base();r=row(p);r['origin']=dict(kind='CONSULTATION',ref_id=None,protocol_question_sha256=None,external_record_sha256='1'*64,label='Opaque fictional consultation')
        with self.assertRaises(ValueError):intake.prepare(p,document(r))
        r['reopening']={'amendment_note':'Supplied follow-up, not completed'}
        q=application(p,document(r))['protocol_candidate'];self.assertEqual(run(q)['question_ledger']['questions_with_consultation_origin'],['question-one'])
        for kind in ('CHALLENGE','READINESS_ASSERTION'):
            r['origin'].update(kind=kind,ref_id='missing',external_record_sha256=None)
            with self.assertRaises(ValueError):intake.prepare(p,document(r))
        r['origin'].update(kind='AMENDMENT',ref_id='Fictional note not an authenticated amendment')
        self.assertTrue(intake.verify(p,application(p,document(r)))['valid'])

    def test_replay_rejects_tampering_and_original_changes(self):
        p=base();d=document(row(p));a=application(p,d)
        for key in ('reviewer','decision','target_sha256'):
            changed=copy.deepcopy(a);changed['receipt']['assertion'][key]='tampered'
            with self.assertRaises(ValueError):intake.verify(p,changed)
        changed=copy.deepcopy(a);changed['protocol_candidate']['question_records'][0]['text']='changed'
        with self.assertRaises(ValueError):intake.verify(p,changed)
        p['question']+=' changed'
        with self.assertRaises(ValueError):intake.verify(p,a)

    def test_optional_views_and_bundle_roundtrip(self):
        p=base();q=application(p,document(row(p)))['protocol_candidate']
        for func in (status,snapshot,handoff):
            self.assertNotIn('question_ledger',func(p));self.assertIn('question_ledger',func(q))
        rv=readiness_view(q);self.assertEqual(rv['gates_sha256'],readiness_view(p)['gates_sha256']);self.assertEqual(rv['question_context']['open_count'],1)
        terminal=application(q,transition(q,'question-one','UNRESOLVED'))['protocol_candidate']
        diff=compare_protocols(q,terminal);self.assertTrue(diff['has_changes']);self.assertTrue(diff['question_transitions'])
        raw=build_bundle((json.dumps(terminal)+'\n').encode());self.assertTrue(verify_bytes(raw)['valid'])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:self.assertIn(b'not assessed answers',z.read('summary.md'))
        self.assertEqual(review(terminal)['answer_assessment'],'NOT_PERFORMED')

    def test_actual_three_format_import_continuations(self):
        for fmt in ('CSV','NBIB','RIS'):
            with self.subTest(format=fmt):
                p=imported(fmt)[3];before=copy.deepcopy(p)
                a=application(p,document(row(p)));q=a['protocol_candidate']
                b=application(q,transition(q,'question-one','UNRESOLVED'))
                self.assertTrue(intake.verify(q,b)['valid']);self.assertEqual(p,before)
                self.assertEqual(run(p),{k:v for k,v in run(b['protocol_candidate']).items() if k!='question_ledger'})
                bad=copy.deepcopy(q);bad['question']+=' changed'
                with self.assertRaises(ValueError):run(bad)

    def test_documented_twelve_command_journey_for_three_actual_import_formats(self):
        commands=re.findall(r'^python (.+)$',(ROOT/'docs/QUESTION_LEDGER.md').read_text(),re.M)
        self.assertEqual(len(commands),12)
        for fmt in ('CSV','NBIB','RIS'):
            with self.subTest(format=fmt), tempfile.TemporaryDirectory() as td:
                work=Path(td);source=work/'input.json';p=imported(fmt)[3]
                source.write_bytes((json.dumps(p)+'\n').encode())
                before=source.read_bytes()
                for command in commands:
                    args=shlex.split(command)
                    args=[str(source) if a=='QUESTION_INPUT.json' else str(work/a[5:]) if a.startswith('WORK/') else str(ROOT/a) if a.endswith('.py') or a.startswith('examples/') else a for a in args]
                    if args[0].endswith('question_intake.py') and args[1]=='assemble':
                        target=work/('transition-target.json' if 'transition-review' in args[4] else 'target.json')
                        review_doc=json.loads(target.read_bytes())['review_document']
                        review_doc.update(receipt_id='fictional-guide-review',decision='record_supplied_questions',reviewer='Fictional independent recorder',reviewed_at='2026-11-14',rationale='Synthetic walkthrough only')
                        Path(args[4]).write_bytes((json.dumps(review_doc)+'\n').encode())
                    process=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(process.returncode,0,(fmt,command,process.stderr))
                    self.assertEqual(process.stderr,b'')
                self.assertEqual(source.read_bytes(),before)
                final=json.loads((work/'transitioned.json').read_bytes())
                self.assertEqual(final['question_records'][0]['status'],'UNRESOLVED')
                self.assertEqual(run(p),{k:v for k,v in run(final).items() if k!='question_ledger'})

    def test_bounds_and_fixed_error_channel_exclusive_outputs(self):
        p=base();q=copy.deepcopy(p);q['question_records']=[row(p,qid=str(i)) for i in range(100)]
        self.assertEqual(len(run(q)['question_ledger']['question_ledger']),100)
        q['question_records'].append(row(p,qid='too-many'))
        with self.assertRaises(ValueError):run(q)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'input.json';source.write_text(json.dumps(p));out=root/'out.json'
            args=[sys.executable,str(ROOT/'question_intake.py'),'template',str(source),'--output',str(out)]
            first=subprocess.run(args,capture_output=True);self.assertEqual(first.returncode,0,first.stderr)
            saved=out.read_bytes();second=subprocess.run(args,capture_output=True)
            self.assertEqual(second.returncode,1);self.assertEqual(second.stdout,b'');self.assertNotIn(str(source).encode(),second.stderr);self.assertEqual(out.read_bytes(),saved)
            source.write_text('null');bad=subprocess.run(args,capture_output=True);self.assertEqual(bad.returncode,1);self.assertEqual(bad.stdout,b'')

if __name__=='__main__':unittest.main()
