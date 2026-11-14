"""Explicit stored-shape navigation agrees with literal source constructors."""
import ast
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MARKERS = ('kind', 'target_type', 'mode')


def constructors(source):
    """Parse only; do not import modules or infer dynamic values."""
    result = []
    class Visitor(ast.NodeVisitor):
        function = '<module>'
        def visit_FunctionDef(self, node):
            previous = self.function
            self.function = node.name
            self.generic_visit(node)
            self.function = previous
        visit_AsyncFunctionDef = visit_FunctionDef
        def collect(self, fields, expansions=()):
            for key in MARKERS:
                value = fields.get(key)
                if isinstance(value, ast.Constant) and type(value.value) is str:
                    version = fields.get('schema_version')
                    if version is not None and not (isinstance(version, ast.Constant) and type(version.value) is int):
                        raise ValueError('dynamic or non-integer version needs explicit review')
                    result.append(dict(function=self.function, discriminator=key, value=value.value,
                        schema_version=None if version is None else version.value, constructor_expansions=list(expansions),
                        constructor_bindings=sorted(k for k in fields if k and (k.endswith('_sha256') or k == 'review_target'))))
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == 'dict':
                self.collect({k.arg: k.value for k in node.keywords if k.arg}, [ast.unparse(k.value) for k in node.keywords if k.arg is None])
            self.generic_visit(node)
        def visit_Dict(self, node):
            self.collect({k.value:v for k,v in zip(node.keys,node.values) if isinstance(k,ast.Constant) and type(k.value) is str}, [ast.unparse(v) for k,v in zip(node.keys,node.values) if k is None])
            self.generic_visit(node)
    Visitor().visit(ast.parse(source))
    return result


def identity(row):
    return tuple(row[k] for k in ('module','function','discriminator','value'))


class RecordRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / 'docs/record_registry.json').read_bytes())

    def test_bidirectional_source_inventory_and_versions(self):
        found = {}
        for path in sorted(ROOT.glob('*.py')):
            for row in constructors(path.read_bytes()):
                row['module'] = path.name
                key = identity(row)
                self.assertNotIn(key, found, 'duplicate construction requires explicit review')
                found[key] = row
        declared = self.registry['tagged_shapes'] + self.registry['excluded_literals']
        self.assertEqual(len(declared), len({identity(r) for r in declared}))
        self.assertEqual(set(found), {identity(r) for r in declared})
        for row in self.registry['tagged_shapes']:
            actual = found[identity(row)]
            for key in ('schema_version','constructor_bindings','constructor_expansions'):
                self.assertEqual(row[key], actual[key], identity(row))
        self.assertEqual(len(self.registry['excluded_literals']), 6)
        self.assertTrue(all(row['reason'] for row in self.registry['excluded_literals']))

    def test_untagged_research_manifest_is_explicit(self):
        row = self.registry['untagged_research_manifest']
        tree = ast.parse((ROOT / row['module']).read_bytes())
        function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==row['function'])
        matches=[]
        for node in ast.walk(function):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id=='dict':
                fields={k.arg:k.value for k in node.keywords}
                if {'schema_version','engine_sha256','input_sha256','files'}==set(fields):
                    matches.append(fields)
        self.assertEqual(len(matches),1)
        self.assertEqual(ast.literal_eval(matches[0]['schema_version']),row['schema_version'])
        self.assertEqual(row['constructor_bindings'],['engine_sha256','input_sha256'])

    def test_human_table_and_guides_match_registry(self):
        document=(ROOT/'docs/RECORD_SCHEMAS.md').read_text(encoding='utf-8')
        table=[]
        commands=(ROOT/'docs/COMMANDS.md').read_text(encoding='utf-8')
        for row in self.registry['tagged_shapes']:
            version=row['schema_version'] if row['schema_version'] is not None else 'none on this object'
            line=f"| `{row['discriminator']}={row['value']}` | {version} | {row['role']} | `{row['module']}:{row['function']}` | [Guide]({row['guide']}) |"
            table.append(line)
            self.assertTrue((ROOT/'docs'/row['guide'].split('#')[0]).is_file())
            self.assertIn(row['module'],commands)
            self.assertIn('python ',(ROOT/'docs'/row['guide'].split('#')[0]).read_text(encoding='utf-8'))
        actual=[line for line in document.splitlines() if line.startswith('| `')]
        self.assertEqual(actual,table)
        self.assertIn('No network access',document)

    def test_scanner_covers_literal_forms_and_preserves_missing_version(self):
        source="def build():\n return dict(target_type='nested'), {'kind':'kept', 'schema_version':2, 'input_sha256':'x'}\n"
        rows=constructors(source)
        self.assertEqual([(r['value'],r['schema_version']) for r in rows],[('nested',None),('kept',2)])
        self.assertEqual(rows[1]['constructor_bindings'],['input_sha256'])
        self.assertEqual(constructors('def dynamic(value):\n return dict(mode=value)\n'),[])
        with self.assertRaises(ValueError): constructors("dict(kind='x',schema_version=VERSION)")
        with self.assertRaises(ValueError): constructors("dict(kind='x',schema_version=True)")

    def test_tagged_expansions_require_explicit_review(self):
        for source in ("dict(kind='x', **fields)", "{'kind':'x', **fields}"):
            self.assertEqual(constructors(source)[0]['constructor_expansions'], ['fields'])
