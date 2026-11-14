"""Exact parser usage and complete command-reference inventory, without research actions."""
import ast
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import sensei

ROOT = Path(__file__).resolve().parents[1]
NO_HELP = {'audit_publication.py', 'verify_manifest.py'}


def normalize(value):
    return ' '.join(value.replace('\\|', '|').split())


def command_rows(text):
    rows = {}
    for line in text.splitlines():
        if not line.startswith('| `python ') or line.startswith('| `python -m '):
            continue
        match = re.match(r'^\| `(python [^`]+)` \|', line)
        if not match:
            raise ValueError('one complete usage string per command-table row required')
        usage = normalize(match.group(1))
        tokens = usage.split()
        if not re.fullmatch(r'[a-z][a-z0-9_]*\.py', tokens[1]):
            raise ValueError('expected a bare root Python script')
        prefix = tokens[2:tokens.index('[-h]')] if '[-h]' in tokens else tokens[2:]
        if len(prefix) > 1 or any(not re.fullmatch(r'[a-z][a-z0-9_-]*', p) for p in prefix):
            raise ValueError('usage must include parser help and at most one subcommand')
        key = (tokens[1], tuple(prefix))
        if key in rows:
            raise ValueError('duplicate command row: ' + repr(key))
        rows[key] = usage
    return rows


def usage_paragraph(output):
    match = re.search(r'^usage: (.+?)(?:\n\s*\n|\Z)', output, re.S | re.M)
    if not match:
        raise ValueError('missing usage paragraph')
    return 'python ' + normalize(match.group(1))


def subcommands(usage):
    match = re.search(r' \{([a-z0-9_,-]+)\} \.\.\.$', usage)
    return set(match.group(1).split(',')) if match else set()


def help_usage(script, args, cwd):
    env = dict(os.environ, COLUMNS='4000', NO_COLOR='1', PYTHON_COLORS='0', PYTHONDONTWRITEBYTECODE='1')
    env.pop('FORCE_COLOR', None)
    result = subprocess.run([sys.executable, str(ROOT/script), *args, '--help'], cwd=cwd,
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode or result.stderr:
        raise AssertionError((script, args, result.returncode, result.stderr))
    return usage_paragraph(result.stdout.decode('utf-8'))


class CommandReferenceTests(unittest.TestCase):
    def test_every_documented_usage_and_subcommand_matches_real_help(self):
        rows = command_rows((ROOT/'docs/COMMANDS.md').read_text(encoding='utf-8'))
        expected = {name for name, _ in sensei.entry_point_scripts()} | {'sensei.py'}
        self.assertEqual({key[0] for key in rows}, expected)
        with tempfile.TemporaryDirectory(prefix='sensei command help ') as td:
            for script in sorted(expected):
                documented = {args for name, args in rows if name == script}
                if script in NO_HELP:
                    self.assertEqual(documented, {()})
                    self.assertEqual(rows[script, ()], 'python ' + script)
                    tree = ast.parse((ROOT/script).read_text(encoding='utf-8'))
                    self.assertFalse(any(isinstance(n, ast.Import) and any(a.name == 'argparse' for a in n.names)
                        or isinstance(n, ast.ImportFrom) and n.module == 'argparse' for n in ast.walk(tree)))
                    continue
                top = help_usage(script, (), td)
                children = subcommands(top)
                self.assertEqual({a[0] for a in documented if a}, children, script)
                if not children:
                    self.assertEqual(documented, {()}, script)
                for args in sorted(documented):
                    with self.subTest(script=script, args=args):
                        self.assertEqual(rows[script, args], help_usage(script, args, td) if args else top)
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_non_cli_module_table_is_complete(self):
        text = (ROOT/'docs/COMMANDS.md').read_text(encoding='utf-8')
        modules = re.findall(r'^\| `([a-z][a-z0-9_]*\.py)` \|', text, re.M)
        self.assertEqual(len(modules), len(set(modules)))
        self.assertEqual(set(modules), {path.name for path, tree in sensei.root_scripts() if not sensei.has_entry_point(tree)})

    def test_parser_rejects_duplicate_compressed_and_non_usage_rows(self):
        row = '| `python example.py [-h] input` | Purpose | Guide |'
        self.assertEqual(command_rows(row), {('example.py', ()): 'python example.py [-h] input'})
        for bad in (row+'\n'+row, '| `python example.py target INPUT` / `verify INPUT` | Purpose | Guide |',
                    '| `python example.py target INPUT` | Purpose | Guide |',
                    '| `python ../example.py [-h]` | Purpose | Guide |'):
            with self.assertRaises(ValueError):
                command_rows(bad)
        self.assertEqual(command_rows('| `python -m unittest discover -v` | tests | guide |'), {})

    def test_usage_normalization_and_subcommand_extraction(self):
        self.assertEqual(usage_paragraph('usage: thing.py [-h]\n  [--output X | --text]\n\ndescription\n'),
                         normalize('python thing.py [-h] [--output X \\| --text]'))
        self.assertEqual(subcommands('python tool.py [-h] {create,verify} ...'), {'create', 'verify'})
        self.assertEqual(subcommands('python tool.py [-h] [--verbose] {create,verify} ...'), {'create', 'verify'})
        self.assertEqual(subcommands('python tool.py [-h] --decision {include,exclude} input'), set())
        with self.assertRaises(ValueError):
            usage_paragraph('not help')
