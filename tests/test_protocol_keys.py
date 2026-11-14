"""Names-only inventory, deliberate limits and actual declared-field drift tests."""
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

import protocol_keys as keys
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]


def protocol_accesses(tree, section_tables=False):
    """Audit named protocol accesses, including finite literal loop/comprehension keys.

    Not general data-flow analysis: aliases/dynamic extensions need manual inventory
    review and the fixture coverage check. Unresolved named accesses fail closed.
    """
    parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    found=set()
    constants={}
    for assignment in tree.body:
        if isinstance(assignment,ast.Assign) and len(assignment.targets)==1 and isinstance(assignment.targets[0],ast.Name):
            try:constants[assignment.targets[0].id]=ast.literal_eval(assignment.value)
            except (ValueError,TypeError):pass
    sections=set()
    if section_tables:
        for name in ('SPECS','OPTIONAL_SPECS'):
            table=constants[name]
            for entry in table.values():
                if not isinstance(entry,tuple) or len(entry)!=2 or not isinstance(entry[0],str):
                    raise AssertionError('invalid handoff section table')
                sections.update(entry[0].split())
    def resolve(expr,node):
        if isinstance(expr,ast.Constant) and isinstance(expr.value,str):return {expr.value}
        if isinstance(expr,ast.Name):
            ancestor=node
            shadowed=False
            while ancestor in parents:
                ancestor=parents[ancestor]
                if isinstance(ancestor,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
                    if any(arg.arg==expr.id for arg in ast.walk(ancestor.args) if isinstance(arg,ast.arg)):
                        shadowed=True
                    if any(isinstance(n,ast.Name) and n.id==expr.id and isinstance(n.ctx,ast.Store)
                           for n in ast.walk(ancestor)):
                        shadowed=True
                loops=[ancestor] if isinstance(ancestor,ast.For) else getattr(ancestor,'generators',[])
                for loop in loops:
                    target=loop.target;index=None
                    if isinstance(target,ast.Name) and target.id==expr.id:index=-1
                    elif isinstance(target,(ast.Tuple,ast.List)):
                        for i,item in enumerate(target.elts):
                            if isinstance(item,ast.Name) and item.id==expr.id:index=i
                    if index is None:continue
                    if not isinstance(loop.iter,(ast.Tuple,ast.List)):
                        if section_tables and isinstance(loop.iter,ast.Name) and loop.iter.id=='sections' and index==-1:
                            return sections
                        raise AssertionError('unresolved protocol-key loop')
                    values=loop.iter.elts
                    if index!=-1:
                        if any(not isinstance(v,(ast.Tuple,ast.List)) or len(v.elts)<=index for v in values):
                            raise AssertionError('unresolved protocol-key tuple')
                        values=[v.elts[index] for v in values]
                    if any(not isinstance(v,ast.Constant) or not isinstance(v.value,str) for v in values):
                        raise AssertionError('nonliteral protocol-key loop')
                    return {v.value for v in values}
            if not shadowed and isinstance(constants.get(expr.id),str):return {constants[expr.id]}
        raise AssertionError('unresolved named protocol-key access')
    for node in ast.walk(tree):
        expressions=[]
        if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=='protocol':
            expressions.append(node.slice)
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                and isinstance(node.func.value,ast.Name) and node.func.value.id=='protocol'
                and node.func.attr in ('get','pop','setdefault') and node.args):
            expressions.append(node.args[0])
        if isinstance(node,ast.Compare):
            for left,op,right in zip([node.left]+node.comparators,node.ops,node.comparators):
                if isinstance(op,(ast.In,ast.NotIn)) and isinstance(right,ast.Name) and right.id=='protocol':
                    expressions.append(left)
        for expr in expressions:found.update(resolve(expr,node))
    return found


class ProtocolKeysTests(unittest.TestCase):
    def test_inventory_matches_literal_and_finite_dynamic_protocol_accesses(self):
        actual=set()
        for path in ROOT.glob('*.py'):
            with self.subTest(path=path.name):actual.update(protocol_accesses(ast.parse(path.read_bytes()),section_tables=path.name=='review_handoff.py'))
        self.assertEqual(set(keys.KNOWN_TOP_LEVEL_KEYS),actual)
        self.assertEqual(list(keys.KNOWN_TOP_LEVEL_KEYS),sorted(set(keys.KNOWN_TOP_LEVEL_KEYS)))
        self.assertEqual(len(actual),26)

    def test_inventory_scanner_fails_unknown_dynamic_access_and_covers_loop_keys(self):
        source="""for key, prefix in [('one','a'),('two','b')]:
    protocol.get(key)
x={key:protocol[key] for key in ('three','four')}
if 'five' in protocol: protocol.get('six')
"""
        self.assertEqual(protocol_accesses(ast.parse(source)),{'one','two','three','four','five','six'})
        self.assertEqual(protocol_accesses(ast.parse("key='wrong'\nfor key in ('question',):\n protocol.get(key)")),{'question'})
        for source in ["key='wrong'\ndef f(protocol,key):\n return protocol.get(key)",
                       "key='wrong'\ndef f(protocol):\n key=unknown\n return protocol.get(key)"]:
            with self.assertRaises(AssertionError):protocol_accesses(ast.parse(source))
        with self.assertRaises(AssertionError):protocol_accesses(ast.parse('protocol.get(dynamic_key)'))
        with self.assertRaises(AssertionError):protocol_accesses(ast.parse('for key in dynamic_list:\n protocol[key]'))

    def test_all_shipped_root_protocol_examples_have_recognized_names(self):
        count=0
        for path in (ROOT/'examples').rglob('*.json'):
            value=json.loads(path.read_bytes())
            if isinstance(value,dict) and {'question','version','searches','screening','evidence','gaps'}<=set(value):
                count+=1
                self.assertEqual(keys.inspect_keys(value)['unrecognized_top_level_keys'],[],path)
        self.assertGreaterEqual(count,43)

    def test_misspelling_reported_without_correction_rejection_or_values(self):
        value=json.loads((ROOT/'examples/review-demo.json').read_bytes())
        value['apraisals']=value.pop('appraisals')
        original=copy.deepcopy(value)
        with patch('socket.socket',side_effect=AssertionError('no network')):
            report=keys.inspect_keys(value)
        self.assertEqual(report['unrecognized_top_level_keys'],['apraisals'])
        self.assertNotIn('appraisals',report['recognized_top_level_keys'])
        self.assertEqual(report['schema_validation'],'NOT_PERFORMED')
        self.assertEqual(value,original)
        self.assertNotIn('protocol_sha256',report)
        self.assertNotIn('did_you_mean',report)

    def test_values_are_not_read_or_hashed_and_nested_keys_not_reported(self):
        class Uninspectable:
            def __repr__(self):raise AssertionError('value inspected')
        report=keys.inspect_keys({'question':Uninspectable(),'custom':Uninspectable()})
        self.assertEqual(report['unrecognized_top_level_keys'],['custom'])
        value={'question':{'secret_nested_key':'private-value'},'extra':'private-value'}
        encoded=json.dumps(keys.inspect_keys(value))
        self.assertNotIn('private-value',encoded);self.assertNotIn('secret_nested_key',encoded)
        self.assertEqual(keys.inspect_keys({})['unrecognized_top_level_keys'],[])
        self.assertEqual(keys.inspect_keys({'question':None})['recognized_top_level_keys'],['question'])
        for value in [None,[],True,{1:'value'}]:
            with self.assertRaises(ValueError):keys.inspect_keys(value)

    def test_control_format_names_are_visibly_escaped_and_deterministic(self):
        names=['\nspoof','\x1b[2J','\u202eabc','\u2028name','한국어','a/~b']
        report=keys.inspect_keys(dict.fromkeys(names,'NOT_ECHOED'))
        text=keys.render_text(report)
        for literal in ['\x1b','\u202e','\u2028']:self.assertNotIn(literal,text)
        self.assertIn('\\u202e',text);self.assertIn('\\nspoof',text)
        self.assertNotIn('NOT_ECHOED',text)
        self.assertEqual(report,keys.inspect_keys(dict.fromkeys(reversed(names),'different values')))

    def test_cli_read_only_unknown_exit_zero_and_generic_errors(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);source=td/'protocol.json'
            raw=b'{"apraisals":"PRIVATE_CONTENT_31", "question":null}'
            source.write_bytes(raw)
            for args in [('inspect',source),('inspect',source,'--text'),('list',),('list','--text')]:
                result=run_cli('protocol_keys.py',*args,cwd=td)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertNotIn(b'PRIVATE_CONTENT_31',result.stdout+result.stderr)
                self.assertEqual(source.read_bytes(),raw);self.assertEqual(list(td.iterdir()),[source])
            for bad in [b'{"secret":"PRIVATE_CONTENT_31",broken}',b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff',b'[]']:
                source.write_bytes(bad)
                result=run_cli('protocol_keys.py','inspect',source,cwd=td)
                self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'')
                self.assertNotIn(b'PRIVATE_CONTENT_31',result.stderr);self.assertNotIn(b'Traceback',result.stderr)

    def test_real_cli_limits_and_no_domain_module_imports(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);source=td/'p.json';source.write_bytes(b'{"question":"secret"}')
            code="import sys;sys.path.insert(0,sys.argv.pop(1));import protocol_keys as k;k.MAX_BYTES=4;k.main()"
            result=subprocess.run([sys.executable,'-c',code,str(ROOT),'inspect',str(source)],cwd=td,capture_output=True)
            self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'')
            result=subprocess.run([sys.executable,'-c',code,str(ROOT),'list'],cwd=td,capture_output=True)
            self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'')
            code="import sys;sys.path.insert(0,sys.argv[1]);import protocol_keys;assert 'evidence_workflow' not in sys.modules;assert 'research_status' not in sys.modules;assert 'review_handoff' not in sys.modules"
            result=subprocess.run([sys.executable,'-c',code,str(ROOT)],cwd=td,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_documented_commands(self):
        blocks=re.findall(r'```sh\n(.*?)```',(ROOT/'docs/PROTOCOL_KEYS.md').read_text(),re.S)
        self.assertEqual(len(blocks),1)
        for line in blocks[0].strip().splitlines():
            args=shlex.split(line);self.assertEqual(args.pop(0),'python')
            result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            if '--text' not in args:
                report=json.loads(result.stdout);self.assertEqual(report['status'],'KEY_INVENTORY_ONLY')
