"""Completed supplied assertions remain separate from authenticated or scientific judgment."""
import ast
import copy
import hashlib
import inspect
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
import challenge_intake as challenge
import readiness_intake as readiness
import challenge_links
import readiness_links
import schema_check
ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/name).read_bytes())
def shape(kind,review=False):return load('schemas/'+kind+('-review' if review else '-candidates')+'.schema.json')
def document(kind):return load('examples/manual-'+kind+'-candidates.json')
def valid_review(kind):return dict(schema_version=1,receipt_id='synthetic-review',target_sha256='0'*64,decision='import_challenges' if kind=='challenge' else 'import_readiness_assertions',reviewer='Fictional reviewer',reviewed_at='2026-11-14',rationale='Synthetic structure only')
def module(kind):return challenge if kind=='challenge' else readiness
def field(kind):return 'challenges' if kind=='challenge' else 'readiness_assertions'

class AssertionSchemaTests(unittest.TestCase):
    def bad(self,s,d,v):
        self.assertTrue(schema_check.check(s,d))
        with self.assertRaises((ValueError,TypeError)):v(d)

    def test_exact_fields_enums_review_decisions_and_bounds(self):
        for kind in ('challenge','readiness'):
            m=module(kind);s=shape(kind);row=s['properties'][field(kind)]['items'];fields=m.CHALLENGE_FIELDS if kind=='challenge' else m.ASSERTION_FIELDS
            self.assertEqual(set(row['required']),fields);self.assertEqual(set(row['properties']),fields|({'origin'} if kind=='challenge' else set()));self.assertFalse(row['additionalProperties'])
            self.assertEqual(s['properties'][field(kind)]['maxItems'],m.MAX_CHALLENGES if kind=='challenge' else m.MAX_ASSERTIONS)
            enums={'conclusion_width':challenge_links.CONCLUSION_WIDTHS,'outcome':challenge_links.OUTCOMES} if kind=='challenge' else {'evidence_sufficiency':readiness_links.SUFFICIENCY_LABELS,'conclusion_readiness':readiness_links.READINESS_LABELS}
            for name,values in enums.items():self.assertEqual(row['properties'][name]['enum'],list(values))
            r=shape(kind,True);self.assertEqual(set(r['properties']),m.REVIEW_FIELDS);self.assertEqual(set(r['required']),m.REVIEW_FIELDS)
            tree=ast.parse(inspect.getsource(m.validate_review_document));decisions=[ast.literal_eval(n.comparators[0]) for n in ast.walk(tree) if isinstance(n,ast.Compare) and isinstance(n.left,ast.Subscript) and isinstance(n.left.slice,ast.Constant) and n.left.slice.value=='decision']
            self.assertEqual(r['properties']['decision']['const'],decisions[0])
        origin=shape('challenge')['properties']['challenges']['items']['properties']['origin']['oneOf']
        for branch in origin:self.assertEqual(set(branch['properties']),challenge_links.ORIGIN_FIELDS)
        provenance=origin[1]['properties']['declared_provenance']['oneOf'][1]
        self.assertEqual(set(provenance['properties']),challenge_links.PROVENANCE_FIELDS)
        finding=shape('challenge')['properties']['challenges']['items']['properties']['citation_integrity_findings']['items']
        self.assertEqual(set(finding['properties']),challenge.FINDING_FIELDS)

    def test_nested_missing_extra_and_wrong_types_rejected(self):
        for kind in ('challenge','readiness'):
            for reviewing in (False,True):
                s=shape(kind,reviewing);d=valid_review(kind) if reviewing else document(kind);v=module(kind).validate_review_document if reviewing else module(kind).validate_candidate_document
                v(d);self.assertEqual(schema_check.check(s,d),[])
                paths=[()] if reviewing else [(),(field(kind),0)]
                if kind=='challenge' and not reviewing:paths.append(('challenges',0,'citation_integrity_findings',0))
                for path in paths:
                    def at(x):
                        for k in path:x=x[k]
                        return x
                    for key in at(d):
                        bad=copy.deepcopy(d);del at(bad)[key];self.bad(s,bad,v)
                        bad=copy.deepcopy(d);at(bad)[key]=False;self.bad(s,bad,v)
                    bad=copy.deepcopy(d);at(bad)['extra']=None;self.bad(s,bad,v)

    def test_enums_counts_reopening_and_optional_origin(self):
        for kind in ('challenge','readiness'):
            s=shape(kind);d=document(kind);v=module(kind).validate_candidate_document;key=field(kind)
            for reopening in (None,{'work_package_id':'supplied-id'},{'amendment_note':'Supplied note'}):
                good=copy.deepcopy(d);good[key][0]['reopening']=reopening;v(good);self.assertEqual(schema_check.check(s,good),[])
            for reopening in ({},{'work_package_id':'a','amendment_note':'b'},{'unknown':'a'}):
                bad=copy.deepcopy(d);bad[key][0]['reopening']=reopening;self.bad(s,bad,v)
            for count in (1,100):
                good=copy.deepcopy(d);good[key]=[copy.deepcopy(d[key][0]) for _ in range(count)]
                for i,row in enumerate(good[key]):row['challenge_id' if kind=='challenge' else 'assertion_id']=str(i)
                v(good);self.assertEqual(schema_check.check(s,good),[])
            for count in (0,101):
                bad=copy.deepcopy(d);bad[key]=[copy.deepcopy(d[key][0]) for _ in range(count)];self.bad(s,bad,v)
            row=s['properties'][key]['items']
            for name,prop in row['properties'].items():
                if 'enum' not in prop:continue
                for value in prop['enum']:
                    good=copy.deepcopy(d);good[key][0][name]=value;v(good);self.assertEqual(schema_check.check(s,good),[])
                bad=copy.deepcopy(d);bad[key][0][name]='invented';self.bad(s,bad,v)
        s=shape('challenge');d=document('challenge');v=challenge.validate_candidate_document
        human=dict(kind='HUMAN_AUTHORED',package_sha256=None,consultation_record_sha256=None,declared_provenance=None)
        simulation=dict(human,kind='INTERPRETIVE_SIMULATION',package_sha256='1'*64,declared_provenance=dict(provider_id='Supplied',model_id='Supplied',run_id='Supplied',operator_id='Supplied',execution_location='unknown'))
        for origin in (human,simulation,dict(simulation,declared_provenance=None)):
            good=copy.deepcopy(d);good['challenges'][0]['origin']=origin;v(good);self.assertEqual(schema_check.check(s,good),[])
        for origin in (None,{},dict(human,package_sha256='1'*64),dict(simulation,kind='AUTO')):
            bad=copy.deepcopy(d);bad['challenges'][0]['origin']=origin;self.bad(s,bad,v)

    def test_known_looseness_is_visible_not_python_equivalence(self):
        for kind in ('challenge','readiness'):
            for reviewing in (False,True):
                s=shape(kind,reviewing);d=valid_review(kind) if reviewing else document(kind);v=module(kind).validate_review_document if reviewing else module(kind).validate_candidate_document
                cases=[];bad=copy.deepcopy(d);bad['schema_version']=1.0;cases.append(bad)
                changes=[('reviewer',' '),('reviewed_at','2026-02-30'),('target_sha256','0'*64+'\n')] if reviewing else [('challenger' if kind=='challenge' else 'assessor',' '),('challenged_at' if kind=='challenge' else 'assessed_at','2026-02-30'),('basis_sha256' if kind=='challenge' else 'gates_sha256','0'*64+'\n')]
                for name,value in changes:
                    bad=copy.deepcopy(d);node=bad if reviewing else bad[field(kind)][0];node[name]=value;cases.append(bad)
                if not reviewing:
                    bad=copy.deepcopy(d);bad[field(kind)].append(copy.deepcopy(bad[field(kind)][0]));cases.append(bad)
                for bad in cases:
                    self.assertEqual(schema_check.check(s,bad),[])
                    with self.assertRaises((ValueError,TypeError)):v(bad)
        d=load('examples/interpretive-challenge-candidates.json')
        for val in ('x'*129,'supplied\nlabel',' '):
            bad=copy.deepcopy(d);bad['challenges'][0]['origin']['declared_provenance']['provider_id']=val
            self.assertEqual(schema_check.check(shape('challenge'),bad),[])
            with self.assertRaises(ValueError):challenge.validate_candidate_document(bad)

    def test_incomplete_templates_and_current_binding_remain_python_authority(self):
        p=load('examples/synthesis-review.json')
        for kind in ('challenge','readiness'):
            m=module(kind);draft=m.template(p,load('examples/challenge-references.json')) if kind=='challenge' else m.template(p)
            self.assertTrue(schema_check.check(shape(kind),draft['candidate_document']))
            d=document(kind);target=m.prepare(p,d);self.assertTrue(schema_check.check(shape(kind,True),target['review_document']))
            stale=copy.deepcopy(d);stale[field(kind)][0]['basis_sha256' if kind=='challenge' else 'gates_sha256']='0'*64
            self.assertEqual(schema_check.check(shape(kind),stale),[])
            with self.assertRaises(ValueError):m.prepare(p,stale)
            wrong=valid_review(kind);self.assertEqual(schema_check.check(shape(kind,True),wrong),[])
            with self.assertRaises(ValueError):m.assemble(p,d,wrong)
        bad=document('challenge');bad['challenges'][0]['statement_ids']=['unknown-supplied-id'];self.assertEqual(schema_check.check(shape('challenge'),bad),[])
        with self.assertRaises(ValueError):challenge.prepare(p,bad)

    def test_documented_two_journeys_with_separate_fictional_reviews(self):
        source=(ROOT/'docs/ASSERTION_SCHEMAS.md').read_text();commands=[shlex.split(line) for block in re.findall(r'```sh\n(.*?)```',source,re.S) for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),12)
        originals={p:p.read_bytes() for p in (ROOT/'examples').rglob('*') if p.is_file() and p.name not in ('amendment-before.json','amendment-after.json','manual-amendment.json')}
        with tempfile.TemporaryDirectory(prefix='schema journey ') as td:
            for cmd in commands:
                cmd=[sys.executable,*[v.replace('OUTPUT',td) for v in cmd[1:]]]
                # Only the synthetic test authors a fictional separate review; product never does.
                if cmd[1]=='schema_check.py' and cmd[3].endswith('-review.schema.json'):
                    kind=Path(cmd[3]).name.split('-')[0];target=json.loads((Path(td)/(kind+'-target.json')).read_bytes());review=target['review_document'];review.update(receipt_id='fictional-'+kind,reviewer='Fictional reviewer',reviewed_at='2026-11-14',rationale='Fictional structural exercise',decision='import_challenges' if kind=='challenge' else 'import_readiness_assertions');Path(cmd[4]).write_bytes((json.dumps(review)+'\n').encode())
                r=subprocess.run(cmd,cwd=ROOT,capture_output=True);self.assertEqual(r.returncode,0,(cmd,r.stderr));self.assertEqual(r.stderr,b'')
            for kind in ('challenge','readiness'):
                q=json.loads((Path(td)/(kind+'-protocol.json')).read_bytes());self.assertIn(field(kind),q)
        self.assertEqual({p:p.read_bytes() for p in originals},originals)

    def test_all_prior_root_examples_and_schemas_are_byte_preserved(self):
        baseline=load('tests/assertion_schema_prior_bytes.json')
        self.assertEqual({p.name for p in ROOT.glob('*.py')},set(baseline['root'])|{'output_io.py','cli_errors.py','retained_bundle_describe.py','amendment_links.py','amendment_intake.py'})
        self.assertEqual({p.relative_to(ROOT).as_posix() for p in (ROOT/'examples').rglob('*') if p.is_file() and p.name not in ('amendment-before.json','amendment-after.json','manual-amendment.json')},set(baseline['examples']))
        from tests._exclusive_output_compat import prior_bytes, prior_fixture_bytes
        for kind,group in baseline.items():
            for name,sha in group.items():
                source=prior_bytes(name) if kind=='root' else prior_fixture_bytes(name) if kind=='examples' else (ROOT/name).read_bytes()
                self.assertEqual(hashlib.sha256(source).hexdigest(),sha,name)
