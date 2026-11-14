"""Supplied patent information is not legal analysis, current status or readiness."""
import copy
import json
import os
import re
import shlex
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from evidence_workflow import run
import patent_intake as intake
import patent_links as links

ROOT = Path(__file__).resolve().parents[1]


class PatentLedgerTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((ROOT/'examples/patent-protocol.json').read_bytes())
        self.c = json.loads((ROOT/'examples/patent-candidates.json').read_bytes())

    def assertion(self, p=None, c=None):
        target = intake.target(self.p if p is None else p, self.c if c is None else c)
        return dict(schema_version=1, target_sha256=target['target_sha256'], decision='accept',
                    reviewer='Fictional reviewer', reviewed_at='2026-01-03', rationale='Synthetic recording test only')

    def application(self):
        return intake.assemble(self.p, self.c, self.assertion())

    def test_complete_flow_preserves_inputs_and_existing_engine_results(self):
        before = copy.deepcopy((self.p, self.c))
        result = self.application(); candidate = result['protocol_candidate']
        self.assertEqual((self.p, self.c), before)
        self.assertEqual({k:v for k,v in candidate.items() if k not in links.FIELDS}, self.p)
        self.assertEqual(run(candidate), run(self.p))
        self.assertTrue(intake.verify(self.p, result)['valid'])
        view = links.review(candidate)
        self.assertTrue(all(r['source_status']=='CURRENT_SOURCE' for rows in view['rows'].values() for r in rows))
        self.assertEqual(view['literature_readiness'], run(self.p)['readiness'])
        self.assertEqual(view['external_calls'], 0); self.assertEqual(view['legal_opinion'], 'NOT_PROVIDED')
        self.assertEqual(view['legal_status_currency'], 'NOT_VERIFIED')
        self.assertEqual(view['conclusion_readiness'], 'NOT_READY')

    def test_queues_are_missing_supplied_rows_not_legal_findings(self):
        view = links.review(self.application()['protocol_candidate']); q=view['queues']
        self.assertEqual(q['publications_not_in_any_search'], ['ZZ-SYN-0003-A'])
        self.assertEqual(q['search_record_ids_without_publication_row'], ['ZZ-SYN-UNKNOWN-A'])
        self.assertEqual(q['publications_not_listed_in_any_supplied_family'], ['ZZ-SYN-0003-A'])
        self.assertEqual(q['family_member_ids_without_ledger_row'], ['ZZ-SYN-OUTSIDE-A'])
        self.assertEqual(q['applications_without_supplied_legal_status_observation'], ['ZZ-SYN-APP-0002'])
        self.assertEqual(q['legal_status_observations_after_as_of_date'], ['ZZ-SYN-OBS-0001'])
        self.assertEqual(view['search_accounting']['cross_search_overlap'][0]['record_id'], 'ZZ-SYN-0002-A')
        family=view['supplied_family_cooccurrence'][0]
        self.assertTrue(family['occurs_in_multiple_supplied_searches'])
        self.assertEqual(family['search_occurrences'], [dict(search_index=0,publication_ids=['ZZ-SYN-0001-A','ZZ-SYN-0002-A']),dict(search_index=1,publication_ids=['ZZ-SYN-0002-A'])])

    def test_question_and_search_basis_stale_but_version_does_not(self):
        base = self.application()['protocol_candidate']
        variants=[]
        for field, value in [('as_of_date','2026-01-04'),('technical_question','Different supplied scope'),('intended_output','LANDSCAPE'),('claim_feature_scope','Other explicit scope'),('jurisdictions',['ZZ','ZZ-SYN'])]:
            p=copy.deepcopy(base);p['patent_question'][field]=value;variants.append(p)
        p=copy.deepcopy(base);p['searches'][0]['searched_at']='2026-01-04';variants.append(p)
        p=copy.deepcopy(base);p['search_plan'][0]['query']='Changed supplied query';p['searches'][0]['query']='Changed supplied query';variants.append(p)
        for p in variants:
            view=links.review(p)
            self.assertTrue(all(r['source_status']=='STALE_SOURCE' for rows in view['rows'].values() for r in rows))
            self.assertEqual(view['literature_readiness'],run(p)['readiness'])
        p=copy.deepcopy(base);p['version']='changed label'
        self.assertEqual(links.review(p)['basis_sha256'],links.review(base)['basis_sha256'])
        self.assertNotEqual(links.review(p)['protocol_sha256'],links.review(base)['protocol_sha256'])

    def test_exact_review_missing_rejected_stale_and_tampered_are_not_acceptance(self):
        for bad in (None,{},dict(self.assertion(),decision='reject'),dict(self.assertion(),reviewer=' '),dict(self.assertion(),reviewed_at='2026-02-30'),dict(self.assertion(),target_sha256='0'*64),dict(self.assertion(),schema_version=True)):
            with self.subTest(bad=bad),self.assertRaises((ValueError,TypeError)):
                intake.assemble(self.p,self.c,bad)
        p=copy.deepcopy(self.p);p['version']='changed'
        with self.assertRaises(ValueError):intake.assemble(p,self.c,self.assertion())
        c=copy.deepcopy(self.c);c['patent_publications'][0]['locator']='synthetic:changed'
        with self.assertRaises(ValueError):intake.assemble(self.p,c,self.assertion())
        app=self.application();app['protocol_candidate']['patent_publications'][0]['locator']='synthetic:changed'
        self.assertFalse(intake.verify(self.p,app)['valid'])
        app=self.application();app['extra']=None
        self.assertFalse(intake.verify(self.p,app)['valid'])

    def test_implementation_change_stales_target(self):
        app=self.application()
        with patch.object(links,'implementation_hashes',return_value={'changed':'0'*64}):
            with self.assertRaises(ValueError):intake.verify(self.p,app)

    def test_template_never_supplies_a_review_or_decision(self):
        with self.assertRaises(ValueError):intake.template(self.p,None)
        blank=intake.template(self.p)
        self.assertIsNone(blank['draft']['patent_question']);self.assertIsNone(blank['current_basis_sha256'])
        self.assertTrue(all(v is None for v in blank['question_template'].values()))
        self.assertTrue(all(v is None for row in blank['row_templates'].values() for v in row.values()))
        self.assertTrue(all(v is None for k,v in blank['review_template'].items() if k!='schema_version'))
        ready=intake.template(self.p,self.c['patent_question'])
        self.assertEqual(ready['current_basis_sha256'],self.c['patent_publications'][0]['basis_sha256'])
        with self.assertRaises(ValueError):intake.target(self.p,ready['draft'])

    def test_reference_shapes_exact_ids_and_family_assertions(self):
        mutations=[('patent_applications','publication_ids',['unknown']),('patent_legal_status_observations','application_id','unknown'),('patent_publications','publication_date','2026-02-30'),('patent_publications','basis_sha256','0'*64),('patent_families','member_ids',[]),('patent_families','member_ids',['x','x']),('patent_families','grouping_basis','INFERRED'),('patent_families','asserted_by','invented')]
        for name,key,value in mutations:
            c=copy.deepcopy(self.c);c[name][0][key]=value
            with self.subTest(name=name,key=key),self.assertRaises(ValueError):intake.target(self.p,c)
        for name in links.LEDGERS:
            c=copy.deepcopy(self.c);c[name].append(copy.deepcopy(c[name][0]))
            with self.assertRaises(ValueError):intake.target(self.p,c)
            c=copy.deepcopy(self.c);c[name][0]['unknown']=None
            with self.assertRaises(ValueError):intake.target(self.p,c)
        c=copy.deepcopy(self.c);c['patent_families'][0].update(grouping_basis='MANUAL_ASSERTION',asserted_by='Fictional supplier',asserted_at='2026-01-02')
        self.assertEqual(intake.assemble(self.p,c,self.assertion(c=c))['protocol_candidate']['patent_families'],c['patent_families'])
        c['patent_publications'][0]['publication_id']='zz-syn-0001-a'
        with self.assertRaises(ValueError):intake.target(self.p,c)  # no case normalization of references

    def test_family_definition_labels_are_not_merged_and_overlap_not_rejected(self):
        c=copy.deepcopy(self.c);a=copy.deepcopy(c['patent_families'][0]);a['family_id']='ZZ-SYN-FAMILY-0002';c['patent_families'].append(a)
        b=copy.deepcopy(a);b['family_id']='ZZ-SYN-FAMILY-0003';b['family_definition_label']='different definition';c['patent_families'].append(b)
        view=links.review(intake.assemble(self.p,c,self.assertion(c=c))['protocol_candidate'])
        self.assertEqual(len(view['supplied_family_cooccurrence']),3)
        self.assertEqual(len(view['multiple_supplied_families_with_same_definition']),3)
        self.assertTrue(all(r['family_ids']==['ZZ-SYN-FAMILY-0001','ZZ-SYN-FAMILY-0002'] for r in view['multiple_supplied_families_with_same_definition']))

    def test_candidate_limit_does_not_limit_whole_ledger_and_existing_rows_preserved(self):
        c=copy.deepcopy(self.c)
        for name in links.LEDGERS:c[name]=[]
        row=self.c['patent_publications'][0]
        c['patent_publications']=[dict(row,publication_id=f'ZZ-SYN-BATCH-{i}') for i in range(100)]
        app=intake.assemble(self.p,c,self.assertion(c=c));p=app['protocol_candidate']
        c['patent_publications']=[dict(row,publication_id='ZZ-SYN-BATCH-100')]
        second=intake.assemble(p,c,self.assertion(p,c))['protocol_candidate']
        self.assertEqual(len(second['patent_publications']),101)
        self.assertEqual(second['patent_publications'][:100],p['patent_publications'])
        with self.assertRaises(ValueError):intake.target(second,c)
        c['patent_publications']=[dict(row,publication_id=f'ZZ-SYN-BATCH-{i}') for i in range(101)]
        with self.assertRaises(ValueError):intake.target(self.p,c)

    def test_unsupported_histories_partial_sections_and_legal_output_rejected(self):
        for name in ('adapter_receipts','bibliographic_imports'):
            for value in (None,{},[]):
                p=copy.deepcopy(self.p);p[name]=value
                with self.assertRaises(ValueError):intake.template(p)
        p=copy.deepcopy(self.p);p['patent_question']={'invalid':'ignored by run'}
        self.assertEqual(run(p),run(self.p))
        with self.assertRaises(ValueError):links.protocol(p)
        for value in ('FTO_OPINION','LEGAL_ADVICE',None):
            c=copy.deepcopy(self.c);c['patent_question']['intended_output']=value
            with self.assertRaises(ValueError):intake.target(self.p,c)
        p=self.application()['protocol_candidate'];c=copy.deepcopy(self.c);c['patent_question']['as_of_date']='2026-02-01'
        with self.assertRaises(ValueError):intake.target(p,c)

    def test_bounds_strict_json_and_quoted_display(self):
        with patch.object(links,'MAX_CANDIDATE_BYTES',10):
            with self.assertRaises(ValueError):intake.target(self.p,self.c)
        with patch.object(links,'MAX_PROTOCOL_BYTES',10):
            with self.assertRaises(ValueError):intake.template(self.p)
        nested=[]
        for _ in range(130):nested=[nested]
        with self.assertRaises(ValueError):links.normalize(nested,1_000_000)
        for value in (float('nan'),float('inf'),'\ud800'):
            with self.assertRaises(ValueError):links.normalize(value,100)
        p=self.application()['protocol_candidate'];p['patent_publications'][0]['locator']='fake\nREADY\x1b\u202e'
        rendered=links.render_text(links.review(p))
        self.assertNotIn('\nREADY',rendered);self.assertNotIn('\x1b',rendered);self.assertNotIn('\u202e',rendered)
        self.assertIn('\\nREADY',rendered)

    def test_actual_cli_roundtrip_negative_verify_fixed_errors_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/'protocol.json';c=root/'candidates.json';q=root/'question.json';r=root/'review.json';a=root/'application.json';out=root/'candidate.json'
            for path,value in [(p,self.p),(c,self.c),(q,self.c['patent_question'])]:path.write_bytes(intake.encode(value))
            originals={path:path.read_bytes() for path in (p,c,q)}
            def call(script,*args):
                return subprocess.run([sys.executable,'-B',str(ROOT/script),*map(str,args)],capture_output=True,cwd=td,timeout=30)
            template=call('patent_intake.py','template',p,'--question',q)
            self.assertEqual(template.returncode,0,template.stderr)
            null=root/'null.json';null.write_bytes(b'null')
            bad_question=call('patent_intake.py','template',p,'--question',null)
            self.assertEqual(bad_question.returncode,1);self.assertEqual(bad_question.stdout,b'')
            target=call('patent_intake.py','target',p,c);self.assertEqual(target.returncode,0,target.stderr)
            review=json.loads(target.stdout)['review_template'];review.update(decision='accept',reviewer='Fictional reviewer',reviewed_at='2026-01-03',rationale='Synthetic rehearsal only');r.write_bytes(intake.encode(review))
            assembled=call('patent_intake.py','assemble',p,c,r,'--output',a)
            self.assertEqual(assembled.returncode,0,assembled.stderr);self.assertEqual(json.loads(assembled.stdout),json.loads(a.read_bytes()))
            verified=call('patent_intake.py','verify',p,a);self.assertEqual(verified.returncode,0,verified.stderr)
            out.write_bytes(intake.encode(json.loads(a.read_bytes())['protocol_candidate']))
            for extra in ([],['--text']):
                result=call('patent_review.py',out,*extra);self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(result.stdout);self.assertEqual(result.stderr,b'')
            original=a.read_bytes();again=call('patent_intake.py','assemble',p,c,r,'--output',a)
            self.assertEqual(again.returncode,1);self.assertEqual(again.stdout,b'');self.assertEqual(a.read_bytes(),original)
            bad=json.loads(original);bad['protocol_candidate']['version']='changed';a.write_bytes(intake.encode(bad))
            negative=call('patent_intake.py','verify',p,a);self.assertEqual(negative.returncode,1);self.assertFalse(json.loads(negative.stdout)['valid']);self.assertEqual(negative.stderr,b'')
            malformed=root/'PRIVATE-PATH.json';malformed.write_bytes(b'{"secret":1,"secret":2}')
            result=call('patent_review.py',malformed)
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertNotIn(b'PRIVATE',result.stderr);self.assertNotIn(b'secret',result.stderr)
            self.assertEqual({path:path.read_bytes() for path in originals},originals)
            missing=call('patent_intake.py','assemble',p,c);self.assertEqual(missing.returncode,2)

    def test_dangling_output_entry_and_size_failure_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'existing';path.write_bytes(b'kept')
            with self.assertRaises(FileExistsError):intake.write_new(path,b'new')
            self.assertEqual(path.read_bytes(),b'kept')
            link=Path(td)/'dangling'
            try:link.symlink_to(Path(td)/'missing')
            except (OSError,NotImplementedError):pass
            else:
                with self.assertRaises(FileExistsError):intake.write_new(link,b'new')
                self.assertTrue(link.is_symlink());self.assertFalse((Path(td)/'missing').exists())
        with patch.object(links,'MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):intake.encode(self.c)

    def test_documented_real_cli_rehearsal_and_json_output_with_text(self):
        guide=(ROOT/'docs/PATENT_INFORMATION.md').read_text(encoding='utf-8')
        commands=[line for block in re.findall(r"```sh\n(.*?)```",guide,re.S) for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),7)
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);(work/'examples').mkdir()
            for name in ('patent-protocol.json','patent-candidates.json'):
                shutil.copyfile(ROOT/'examples'/name,work/'examples'/name)
            original={p:p.read_bytes() for p in (work/'examples').iterdir()}
            for line in commands:
                args=shlex.split(line)[1:]
                if args[0]!='-c':args[0]=str(ROOT/args[0])
                result=subprocess.run([sys.executable,'-B',*args],cwd=work,capture_output=True,timeout=30)
                self.assertEqual((result.returncode,result.stderr),(0,b''),line)
                if ' target ' in line:
                    review=json.loads((work/'patent-target.json').read_bytes())['review_template']
                    review.update(decision='accept',reviewer='Fictional reviewer',reviewed_at='2026-01-03',rationale='Synthetic recording rehearsal only')
                    (work/'patent-review.json').write_bytes(intake.encode(review))
            report=json.loads((work/'patent-observations.json').read_bytes())
            self.assertEqual(report['legal_opinion'],'NOT_PROVIDED')
            self.assertEqual(report['queues']['applications_without_supplied_legal_status_observation'],['ZZ-SYN-APP-0002'])
            result=subprocess.run([sys.executable,'-B',str(ROOT/'patent_review.py'),'patent-candidate.json','--text','--output','text-output.json'],cwd=work,capture_output=True,timeout=30)
            self.assertEqual((result.returncode,result.stderr),(0,b''))
            self.assertEqual(json.loads((work/'text-output.json').read_bytes()),report)
            self.assertIn(b'Supplied patent ledger',result.stdout)
            self.assertEqual({p:p.read_bytes() for p in original},original)

    def test_api_json_shape_and_partial_stale_append_preservation(self):
        for value in ({1:'key'},('tuple',),{1,2},object()):
            with self.assertRaises(ValueError):links.normalize(value,10000)
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'{"x":"\\ud800"}'):
            with tempfile.TemporaryDirectory() as td:
                path=Path(td)/'input';path.write_bytes(raw)
                with self.assertRaises(ValueError):links.read(path,10000)
        p=self.application()['protocol_candidate'];p['patent_question']['as_of_date']='2026-01-04'
        c=copy.deepcopy(self.c)
        for name in links.LEDGERS:c[name]=[]
        c['patent_question']=copy.deepcopy(p['patent_question'])
        c['patent_publications']=[dict(self.c['patent_publications'][0],publication_id='ZZ-SYN-NEW',basis_sha256=links.basis(p,c['patent_question']))]
        candidate=intake.assemble(p,c,self.assertion(p,c))['protocol_candidate']
        self.assertEqual(candidate['patent_publications'][:-1],p['patent_publications'])
        states=[r['source_status'] for r in links.review(candidate)['rows']['patent_publications']]
        self.assertEqual(states,['STALE_SOURCE']*3+['CURRENT_SOURCE'])
