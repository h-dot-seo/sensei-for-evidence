"""Descriptive completed decisions, not target approval or a new research authority."""
import ast
import copy
import inspect
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

import schema_check
import screening_decision
import screening_decision_links
import report_decision

ROOT=Path(__file__).resolve().parents[1]


def load(path):return json.loads((ROOT/path).read_bytes())


class DecisionSchemaTests(unittest.TestCase):
    def parts(self, kind):
        return (load('schemas/'+kind+'-decision.schema.json'),
                load('examples/'+kind+'-decision-document.json'),
                screening_decision_links if kind=='screening' else report_decision)

    def assert_rejected_by_both(self, schema, document, validator):
        self.assertTrue(schema_check.check(schema,document))
        with self.assertRaises(ValueError):validator(document)

    def test_exact_fields_and_decisions_track_authoritative_source(self):
        for kind in ('screening','report'):
            schema,document,module=self.parts(kind)
            self.assertEqual(set(schema['properties']),module.DOCUMENT_FIELDS)
            self.assertEqual(set(schema['required']),module.DOCUMENT_FIELDS)
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(schema_check.check(schema,document),[])
            module.validate_document(document)
            tree=ast.parse(inspect.getsource(module.validate_document))
            decisions=[node for node in ast.walk(tree) if isinstance(node,ast.Compare)
                       and isinstance(node.left,ast.Subscript) and isinstance(node.left.slice,ast.Constant)
                       and node.left.slice.value=='decision' and any(isinstance(op,ast.NotIn) for op in node.ops)]
            self.assertEqual(len(decisions),1)
            self.assertEqual(schema['properties']['decision']['enum'],list(ast.literal_eval(decisions[0].comparators[0])))

    def test_required_extra_wrong_types_and_literal_mutations_agree(self):
        for kind in ('screening','report'):
            schema,document,module=self.parts(kind)
            before=copy.deepcopy(document)
            for key in document:
                bad=copy.deepcopy(document);del bad[key]
                self.assert_rejected_by_both(schema,bad,module.validate_document)
                bad=copy.deepcopy(document);bad[key]=False
                self.assert_rejected_by_both(schema,bad,module.validate_document)
            for key,value in [('extra','unrecognized'),('decision','INCLUDE'),('decision','pending'),
                              ('schema_version',2),('decided_at','2026/11/14'),('target_sha256','A'*64),
                              ('target_sha256','0'*63),('reason','')]:
                bad=copy.deepcopy(document);bad[key]=value
                self.assert_rejected_by_both(schema,bad,module.validate_document)
            self.assertEqual(document,before)

    def test_report_inclusion_scalar_plural_and_exclusion_null(self):
        schema,document,module=self.parts('report')
        for decision,declaration in [('include',{'study_id':'one'}),('include',{'study_ids':['two','one']}),('exclude',None)]:
            good=copy.deepcopy(document);good.update(decision=decision,study_declaration=declaration)
            self.assertEqual(schema_check.check(schema,good),[]);module.validate_document(good)
        for decision,declaration in [('include',None),('include',{}),('include',{'study_ids':[]}),
                                     ('include',{'study_ids':['a','a']}),('include',{'study_ids':['a',None]}),
                                     ('include',{'study_id':'a','study_ids':['a']}),('include',{'study_id':'a','extra':'b'}),
                                     ('exclude',{'study_id':'a'}),('exclude',{'study_ids':['a']})]:
            bad=copy.deepcopy(document);bad.update(decision=decision,study_declaration=declaration)
            self.assert_rejected_by_both(schema,bad,module.validate_document)

    def test_documented_shape_differences_are_not_hidden(self):
        for kind in ('screening','report'):
            schema,document,module=self.parts(kind)
            for key,value in [('schema_version',1.0),('reason',' '),('decided_at','2026-02-30'),
                              ('target_sha256','0'*64+'\n'),('decided_at','2026-11-14\n')]:
                bad=copy.deepcopy(document);bad[key]=value
                self.assertEqual(schema_check.check(schema,bad),[],(kind,key))
                with self.assertRaises(ValueError):module.validate_document(bad)
        schema,document,module=self.parts('report')
        document['study_declaration']={'study_ids':[' ']}
        self.assertEqual(schema_check.check(schema,document),[])
        with self.assertRaises(ValueError):module.validate_document(document)

    def test_shape_match_cannot_refresh_stale_or_wrong_context_targets(self):
        for kind,protocol_path,assemble,id_field in [
            ('screening','examples/screening-reviews.json',screening_decision.assemble,'record_id'),
            ('report','examples/report-study-inventory.json',report_decision.assemble,'report_id')]:
            schema,document,module=self.parts(kind);protocol=load(protocol_path)
            before=copy.deepcopy(protocol);assemble(protocol,document)
            for key,value in [('target_sha256','0'*64),(id_field,'unknown-synthetic-id')]:
                bad=copy.deepcopy(document);bad[key]=value
                self.assertEqual(schema_check.check(schema,bad),[]);module.validate_document(bad)
                with self.assertRaises(ValueError):assemble(protocol,bad)
            self.assertEqual(protocol,before)

    def test_existing_decision_journeys_with_preflight_commands(self):
        for kind,expected in [('SCREENING',11),('REPORT',8)]:
            source=ROOT/'docs'/(kind+'_DECISIONS.md')
            commands=[line for block in re.findall(r'```sh\n(.*?)```',source.read_text(encoding='utf-8'),re.S)
                      for line in block.strip().splitlines()]
            self.assertEqual(len(commands),expected)
            self.assertEqual(sum(line.startswith('python schema_check.py check') for line in commands),1)
            with tempfile.TemporaryDirectory(prefix='decision schema journey ') as td:
                for line in commands:
                    args=shlex.split(line);self.assertEqual(args.pop(0),'python')
                    args=[str(Path(td)/arg[len('/outside/'):]) if arg.startswith('/outside/') else arg for arg in args]
                    result=subprocess.run([sys.executable,'-B',*args],cwd=ROOT,capture_output=True,timeout=30)
                    self.assertEqual(result.returncode,0,(line,result.stderr))
                    if args[0]=='schema_check.py':
                        self.assertEqual(json.loads(result.stdout)['scientific_assessment'],'NOT_PERFORMED')

    def test_templates_are_not_completed_decision_documents(self):
        for kind,path,module,identity in [('screening','examples/screening-reviews.json',screening_decision,'record-alpha'),
                                         ('report','examples/report-study-inventory.json',report_decision,'report-three')]:
            schema,_,validator=self.parts(kind)
            prepared=module.prepare(load(path),identity)
            document=prepared['decision_document']
            self.assertTrue(schema_check.check(schema,document))
            with self.assertRaises(ValueError):validator.validate_document(document)
