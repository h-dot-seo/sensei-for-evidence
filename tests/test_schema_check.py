"""Descriptive authored shapes and explicit differences from authoritative validators."""
import ast
import copy
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import schema_check as checker
import protocol_scaffold
import bibliographic_review
import bibliographic_integrity as integrity
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]


def schema(name):return json.loads((ROOT/'schemas'/name).read_bytes())
def fixture(name):return json.loads((ROOT/name).read_bytes())


class SchemaTests(unittest.TestCase):
    def test_all_examples_explicitly_classified_and_mapped_documents_match(self):
        inventory=fixture('tests/schema_fixture_inventory.json')
        self.assertEqual(set(inventory),{p.relative_to(ROOT).as_posix() for p in (ROOT/'examples').rglob('*.json')})
        count=0
        for path,item in inventory.items():
            self.assertTrue(item['scope'])
            if item['schema']:
                count+=1;self.assertEqual(checker.check(schema(item['schema']),fixture(path)),[],path)
        self.assertEqual(count,5)

    def test_base_keys_and_plan_fields_track_recommended_scaffold(self):
        s=schema('base-protocol.schema.json')
        self.assertEqual(set(s['properties']),protocol_scaffold.FIELDS)
        self.assertEqual(set(s['required']),protocol_scaffold.FIELDS)
        self.assertEqual(set(s['properties']['search_plan']['items']['properties']),set(protocol_scaffold.PLAN_FIELDS))
        base=fixture('examples/bibliographic-base.json')
        self.assertTrue(protocol_scaffold.check(base)['valid'])
        for key in protocol_scaffold.FIELDS:
            bad=copy.deepcopy(base);del bad[key]
            self.assertTrue(checker.check(s,bad));self.assertFalse(protocol_scaffold.check(bad)['valid'])
        bad=copy.deepcopy(base);bad['unknown']=1
        self.assertTrue(checker.check(s,bad));self.assertFalse(protocol_scaffold.check(bad)['valid'])
        bad=copy.deepcopy(base);bad['question']=' '
        self.assertEqual(checker.check(s,bad),[]);self.assertFalse(protocol_scaffold.check(bad)['valid'])

    def test_resolution_field_sets_and_dispositions_track_source_literals(self):
        tree=ast.parse((ROOT/'bibliographic_integrity.py').read_bytes())
        literals=[]
        for node in ast.walk(tree):
            if isinstance(node,(ast.Set,ast.Tuple)):
                try:literals.append(set(ast.literal_eval(node)))
                except (ValueError,TypeError):pass
        s=schema('bibliographic-choices.schema.json');row=s['properties']['resolutions']['items']
        self.assertIn(set(row['properties']),literals)
        self.assertIn(set(row['properties']['disposition']['enum']),literals)
        review=schema('bibliographic-reviewed.schema.json')['properties']['review']
        self.assertIn(set(review['properties']),literals)
        self.assertEqual(review['properties']['decision']['const'],'import_for_screening')
        self.assertEqual(set(s['properties']),{'schema_version','resolutions','review'})

    def test_structural_mutations_match_authoritative_collection_checks(self):
        s=schema('bibliographic-choices.schema.json')
        doc=dict(schema_version=1,resolutions=[dict(candidate_id='row1',disposition='new_record',record_id='r1',rationale='Supplied')],review=None)
        artifact=dict(parsed_export=dict(record_rows=[dict(candidate_id='row1')]))
        self.assertEqual(checker.check(s,doc),[])
        integrity.normalize_resolutions(artifact,doc['resolutions'],set())
        for key in doc['resolutions'][0]:
            bad=copy.deepcopy(doc);del bad['resolutions'][0][key]
            self.assertTrue(checker.check(s,bad))
            with self.assertRaises(ValueError):integrity.normalize_resolutions(artifact,bad['resolutions'],set())
        for values in [dict(disposition='other'),dict(disposition='do_not_promote',record_id='r1'),dict(record_id=None),dict(unknown=True)]:
            bad=copy.deepcopy(doc);bad['resolutions'][0].update(values)
            self.assertTrue(checker.check(s,bad))
            with self.assertRaises(ValueError):integrity.normalize_resolutions(artifact,bad['resolutions'],set())
        for field in ['schema_version','resolutions','review']:
            bad=copy.deepcopy(doc);del bad[field]
            self.assertTrue(checker.check(s,bad))
            with self.assertRaises(ValueError):bibliographic_review.check_document(bad,False)

    def test_shape_match_does_not_establish_context_calendar_or_exact_int(self):
        s=schema('bibliographic-reviewed.schema.json')
        doc=fixture('examples/batch-to-evidence/collection-review.json')
        doc['review']['reviewed_at']='2026-02-30'
        self.assertEqual(checker.check(s,doc),[])
        with self.assertRaises(ValueError):integrity.validate_review(doc['review'],dict(target_sha256=doc['review']['target_sha256']))
        doc=fixture('examples/batch-to-evidence/collection-review.json')
        self.assertEqual(checker.check(s,doc),[])
        with self.assertRaises(ValueError):integrity.validate_review(doc['review'],dict(target_sha256='0'*64))
        trailing=copy.deepcopy(doc);trailing['review']['target_sha256']+='\n'
        self.assertEqual(checker.check(s,trailing),[])  # JSON Schema pattern search, not fullmatch.
        with self.assertRaises(ValueError):integrity.validate_review(trailing['review'],dict(target_sha256=doc['review']['target_sha256']))
        doc['schema_version']=1.0;self.assertEqual(checker.check(s,doc),[])
        with self.assertRaises(ValueError):bibliographic_review.check_document(doc,True)

    def test_typed_equality_integer_bool_and_unique_items(self):
        self.assertTrue(checker.check({'type':'integer'},True));self.assertEqual(checker.check({'type':'integer'},1.0),[])
        self.assertTrue(checker.check({'const':1},True));self.assertEqual(checker.check({'const':1},1.0),[])
        self.assertTrue(checker.check({'enum':[False]},0))
        self.assertEqual(checker.check({'uniqueItems':True},[False,0]),[])
        self.assertTrue(checker.check({'uniqueItems':True},[{'a':1},{'a':1.0}]))
        self.assertEqual(checker.check({'type':['null','string']},None),[])

    def test_unsupported_keywords_in_unused_branches_fail_closed(self):
        for s in [{'type':'object','$ref':'https://invalid.example/schema'},
                  {'properties':{'unused':{'format':'date'}}},
                  {'oneOf':[{'const':1},{'unknown':True}]},
                  {'pattern':'(a+)+$'},{'additionalProperties':{}},{'type':'unknown'},
                  {'minLength':True},{'required':['x','x']},{'oneOf':[]},True]:
            with self.assertRaises((ValueError,TypeError)):checker.check(s,{})

    def test_oneof_arrays_objects_patterns_and_diagnostic_privacy(self):
        s={'type':'object','required':['x'],'additionalProperties':False,'properties':{'x':{'type':'string','minLength':2}}}
        errors=checker.check(s,{'x':'s','a/~b':'PRIVATE_VALUE'})
        self.assertIn(dict(input_pointer='/a~1~0b',rule='additionalProperties'),errors)
        self.assertNotIn('PRIVATE_VALUE',json.dumps(errors))
        self.assertTrue(checker.check({'oneOf':[{},{}]},'value'))
        self.assertEqual(checker.check({'type':'array','minItems':1,'maxItems':2,'items':{'type':'string'}},['x']),[])
        self.assertTrue(checker.check({'pattern':'^[0-9a-f]{64}$'},'z'*64))
        with patch.object(checker,'MAX_DEPTH',1):
            with self.assertRaises(ValueError):checker.check({'items':{'items':{}}},[])
        with patch.object(checker,'MAX_NODES',1):
            with self.assertRaises(ValueError):checker.check({'items':{}},[1])
        with patch.object(checker,'MAX_NODES',3):
            with self.assertRaises(ValueError):checker.check({'uniqueItems':True},[[1,2],[1,3]])
        with patch.object(checker,'MAX_DEPTH',1):
            with self.assertRaises(ValueError):checker.check({},[[[1]]])
            with self.assertRaises(ValueError):checker.check({'const':[[1]]},[[1]])
        with patch.object(checker,'MAX_COMPARE_CHARS',3):
            with self.assertRaises(ValueError):checker.check({'const':'long'},'long')
        with patch.object(checker,'MAX_ERRORS',1):
            with self.assertRaises(ValueError):checker.check({'required':['a','b']},{})

    def test_cli_exit_contract_strict_json_and_immutable_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);sp=td/'s.json';dp=td/'d.json'
            sp.write_text('{"type":"string"}');dp.write_text('"literal"');before={p.name:p.read_bytes() for p in td.iterdir()}
            for command in [('explain',sp),('check',sp,dp)]:
                result=run_cli('schema_check.py',*command,cwd=td);self.assertEqual(result.returncode,0,result.stderr)
                report=json.loads(result.stdout);self.assertEqual(report['engine_validation'],'NOT_PERFORMED')
                self.assertEqual({p.name:p.read_bytes() for p in td.iterdir()},before)
            dp.write_text('{}');result=run_cli('schema_check.py','check',sp,dp,cwd=td)
            self.assertEqual(result.returncode,1);self.assertFalse(json.loads(result.stdout)['valid'])
            for raw in ['{"x":1,"x":2}','NaN','{private-fragment']:
                dp.write_text(raw);result=run_cli('schema_check.py','check',sp,dp,cwd=td)
                self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'');self.assertNotIn(b'private-fragment',result.stderr)
            sp.write_text('{"$ref":"https://invalid.example/no"}');dp.write_text('{}')
            with patch('socket.socket',side_effect=AssertionError('network forbidden')):
                result=run_cli('schema_check.py','check',sp,dp,cwd=td)
            self.assertEqual(result.returncode,2);self.assertNotIn(b'Traceback',result.stderr)

    def test_documented_commands(self):
        blocks=re.findall(r'```sh\n(.*?)```',(ROOT/'docs/SCHEMAS.md').read_text(),re.S)
        self.assertEqual(len(blocks),1)
        for line in blocks[0].strip().splitlines():
            args=shlex.split(line);self.assertEqual(args.pop(0),'python')
            result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['scientific_assessment'],'NOT_PERFORMED')
