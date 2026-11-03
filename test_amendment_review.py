"""Supplied amendment notes match inputs and scope, never approve changes."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from compare_runs import compare_protocols,changed_fields
from json_io import canonical_json_bytes
from evidence_workflow import run
ROOT=Path(__file__).resolve().parent

def load(name):return json.loads((ROOT/'examples'/name).read_text())
def note(before,after):
    return dict(schema_version=1,before_sha256=hashlib.sha256(canonical_json_bytes(before)).hexdigest(),after_sha256=hashlib.sha256(canonical_json_bytes(after)).hexdigest(),from_version=before['version'],to_version=after['version'],reason='Fictional supplied reason',authored_by='fictional',authored_at='2026-11-03',scope_fields=changed_fields(before,after))

class AmendmentReviewTests(unittest.TestCase):
    def setUp(self):self.a=load('first-run-enriched.json');self.b=load('first-run-note-complete.json');self.n=load('work-note-amendment.json')
    def review(self):return compare_protocols(self.a,self.b,self.n)['amendment_review']
    def test_exact_binding_preserves_reason_and_recorded_dependency_transition(self):
        r=self.review();self.assertEqual(r['binding_status'],'RECORDED_INPUTS_AND_SCOPE_MATCH')
        self.assertEqual(r['assertion'],self.n);self.assertEqual(r['actual_changed_fields'],['gaps','version'])
        work={w['id']:w for w in r['observed_state_transitions']['work']}
        self.assertEqual(work['WP-RECEIPT-REVIEW']['after']['status'],'COMPLETE')
        self.assertEqual(work['WP-EXTRACTION-REVIEW']['before']['blocked_by'],['WP-RECEIPT-REVIEW'])
        self.assertEqual(work['WP-EXTRACTION-REVIEW']['after']['blocked_by'],[])
        self.assertEqual(r['observed_state_transitions']['search_plan']['after']['missing_search_ids'],['search-secondary'])
    def test_missing_and_explicit_null_are_different(self):
        self.assertEqual(compare_protocols(self.a,self.b)['amendment_review']['stage'],'NOT_SUPPLIED')
        with self.assertRaises(ValueError):compare_protocols(self.a,self.b,None)
    def test_hash_or_version_mismatch_does_not_hide_actual_transitions(self):
        for key,value in (('before_sha256','0'*64),('after_sha256','0'*64),('from_version','other'),('to_version','other')):
            n=copy.deepcopy(self.n);n[key]=value;r=compare_protocols(self.a,self.b,n)['amendment_review']
            self.assertEqual(r['binding_status'],'MISMATCH');self.assertTrue(r['observed_state_transitions']['work'])
    def test_missing_and_overdeclared_scope_fields_are_explicit(self):
        self.n['scope_fields']=['version','searches'];r=self.review()
        self.assertEqual(r['undeclared_changed_fields'],['gaps']);self.assertEqual(r['declared_but_unchanged_fields'],['searches'])
        self.assertEqual(r['binding_status'],'MISMATCH')
    def test_strict_schema_date_hash_and_scope_types(self):
        mutations=[dict(schema_version=True),dict(schema_version=1.0),dict(before_sha256='A'*64),dict(after_sha256=None),dict(authored_at='2026-02-30'),dict(reason=' '),dict(authored_by=[]),dict(from_version=1),dict(scope_fields='gaps'),dict(scope_fields=['gaps','gaps']),dict(scope_fields=[1]),dict(extra='field')]
        for fields in mutations:
            n=copy.deepcopy(self.n);n.update(fields)
            with self.subTest(fields=fields),self.assertRaises(ValueError):compare_protocols(self.a,self.b,n)
    def test_empty_scope_on_identical_inputs_is_not_scientific_approval(self):
        r=compare_protocols(self.a,self.a,note(self.a,self.a))
        self.assertFalse(r['has_changes']);self.assertEqual(r['amendment_review']['binding_status'],'RECORDED_INPUTS_AND_SCOPE_MATCH')
        self.assertEqual(r['conclusion_readiness'],'NOT_READY')
    def test_planning_and_synthesis_stale_transitions_not_inferred_decisions(self):
        a=load('rationale-links.json')
        # Explicit synthetic baseline review setup, not runtime assertion renewal.
        targets={r['statement_id']:r for r in run(a)['synthesis']['review_targets']}
        a['synthesis_statements'][0]['basis_sha256']=targets['statement-1']['basis_sha256']
        planning={r['work_package_id']:r for r in run(a)['planning']['review_targets']}
        for d in a['planning_decisions']:d['basis_sha256']=planning[d['work_package_id']]['basis_sha256']
        b=copy.deepcopy(a);b['synthesis_statements'][0]['text']+=' Fictional amendment.'
        r=compare_protocols(a,b,note(a,b))['amendment_review']
        self.assertEqual(len(r['observed_state_transitions']['planning']),2)
        self.assertTrue(all(row['after']['source_match_status']=='STALE_SOURCE' for row in r['observed_state_transitions']['planning']))
        self.assertEqual(r['observed_state_transitions']['work'],[])
        synthesis=r['observed_state_transitions']['synthesis']
        self.assertEqual(len(synthesis),1);self.assertEqual(synthesis[0]['id'],'statement-1')
        self.assertEqual(synthesis[0]['before']['source_match_status'],'CURRENT_SOURCE')
        self.assertEqual(synthesis[0]['after']['source_match_status'],'STALE_SOURCE')
    def test_metadata_is_not_provenance_and_output_is_isolated(self):
        original=copy.deepcopy(self.n);r=self.review();r['assertion']['reason']='edited';self.assertEqual(self.n,original)
        self.n['reason']='Different supplied reason';self.assertEqual(self.review()['binding_status'],'RECORDED_INPUTS_AND_SCOPE_MATCH')
        self.assertIn('not approval or verified authorship',r['boundary'])
    def test_object_key_order_ignored_but_typed_value_change_bound(self):
        self.a=dict(reversed(list(self.a.items())));self.assertEqual(self.review()['binding_status'],'RECORDED_INPUTS_AND_SCOPE_MATCH')
        self.a['gaps'][0]['uninterpreted_flag']=True;self.n=note(self.a,self.b);self.a['gaps'][0]['uninterpreted_flag']=1
        self.assertFalse(self.review()['input_hash_matches']['before'])
    def test_no_amendment_comparison_outputs_unchanged(self):
        old=compare_protocols(self.a,self.b);with_note=compare_protocols(self.a,self.b,self.n)
        old.pop('amendment_review');with_note.pop('amendment_review');self.assertEqual(old,with_note)
    def test_actual_documented_cli_and_mismatch_exit(self):
        cmd=[sys.executable,str(ROOT/'compare_runs.py'),str(ROOT/'examples/first-run-enriched.json'),str(ROOT/'examples/first-run-note-complete.json'),'--amendment',str(ROOT/'examples/work-note-amendment.json')]
        r=subprocess.run(cmd,capture_output=True,check=True);self.assertEqual(json.loads(r.stdout)['amendment_review'],self.review())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'mismatch.json';self.n['before_sha256']='0'*64;path.write_text(json.dumps(self.n))
            r=subprocess.run(cmd[:-1]+[str(path)],capture_output=True);self.assertEqual(r.returncode,1)
            self.assertEqual(json.loads(r.stdout)['amendment_review']['binding_status'],'MISMATCH')
            path.write_text('null');r=subprocess.run(cmd[:-1]+[str(path)],capture_output=True);self.assertEqual(r.returncode,1);self.assertFalse(r.stdout)

if __name__=='__main__':unittest.main()
