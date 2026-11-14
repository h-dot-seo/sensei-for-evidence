"""Exact one-file selection keeps discovery semantics and does not cache eligibility."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sensei


class DispatcherSelectionTests(unittest.TestCase):
    def test_clean_checkout_membership_matches_discovery(self):
        listed={name for name,_ in sensei.entry_point_scripts()}
        for path in sensei.ROOT.glob('*.py'):
            with self.subTest(name=path.name):
                if path.name in listed:self.assertEqual(sensei.resolve_script(path.name),path)
                else:
                    with self.assertRaisesRegex(ValueError,'not a listed root script'):sensei.resolve_script(path.name)

    def test_invalid_names_and_dispatcher_never_read_or_parse(self):
        invalid=[None,True,1,[], '', '.', '..', '../x.py', 'nested/x.py', 'nested\\x.py',
                 '/x.py','x.py\n','-x.py','.hidden.py','x.PY','x?.py','x*.py','x[1].py','é.py']
        with patch.object(Path,'read_bytes',side_effect=AssertionError('read forbidden')),patch.object(ast,'parse',side_effect=AssertionError('parse forbidden')):
            for name in invalid:
                with self.subTest(name=name),self.assertRaisesRegex(ValueError,'not a root script file name'):sensei.resolve_script(name)
            with self.assertRaisesRegex(ValueError,'not a listed root script'):sensei.resolve_script('sensei.py')

    def test_selected_file_only_one_read_and_parse_no_discovery(self):
        original_read=Path.read_bytes;original_parse=ast.parse;reads=[];parses=[]
        def read(path):reads.append(path);return original_read(path)
        def parse(*args,**kwargs):parses.append(kwargs.get('filename'));return original_parse(*args,**kwargs)
        with patch.object(Path,'read_bytes',read),patch.object(ast,'parse',parse),patch.object(sensei,'entry_point_scripts',side_effect=AssertionError('no full discovery')):
            self.assertEqual(sensei.resolve_script('research_status.py'),sensei.ROOT/'research_status.py')
        self.assertEqual(reads,[sensei.ROOT/'research_status.py']);self.assertEqual(parses,['research_status.py'])

    def test_unrelated_bad_syntax_does_not_block_selection_but_discovery_fails(self):
        with tempfile.TemporaryDirectory() as td,patch.object(sensei,'ROOT',Path(td)):
            root=Path(td);(root/'chosen.py').write_text('def main(): pass\n',encoding='utf-8')
            (root/'broken.py').write_text('def syntax error\n',encoding='utf-8')
            self.assertEqual(sensei.resolve_script('chosen.py'),root/'chosen.py')
            with self.assertRaises(SyntaxError):sensei.entry_point_scripts()
            with self.assertRaises(SyntaxError):sensei.resolve_script('broken.py')
            with self.assertRaisesRegex(ValueError,'not a root script file name'):sensei.resolve_script('../chosen.py')

    def test_exact_spelling_directory_helpers_and_no_cached_eligibility(self):
        with tempfile.TemporaryDirectory() as td,patch.object(sensei,'ROOT',Path(td)):
            root=Path(td);chosen=root/'Chosen.py';chosen.write_text('def main(): pass\n',encoding='utf-8')
            self.assertEqual(sensei.resolve_script('Chosen.py'),chosen)
            for name in ('chosen.py','CHOSEN.py','missing.py'):
                with self.assertRaisesRegex(ValueError,'not a listed root script'):sensei.resolve_script(name)
            (root/'folder.py').mkdir()
            with self.assertRaisesRegex(ValueError,'not a listed root script'):sensei.resolve_script('folder.py')
            chosen.write_text('def helper(): pass\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'not a listed root script'):sensei.resolve_script('Chosen.py')
            chosen.write_text('if __name__ == "__main__": pass\n',encoding='utf-8')
            self.assertEqual(sensei.resolve_script('Chosen.py'),chosen)
            chosen.unlink()
            with self.assertRaisesRegex(ValueError,'not a listed root script'):sensei.resolve_script('Chosen.py')

    def test_selected_read_error_propagates_and_nonselected_files_are_not_opened(self):
        with patch.object(Path,'read_bytes',side_effect=PermissionError('synthetic unreadable')):
            with self.assertRaises(PermissionError):sensei.resolve_script('research_status.py')
        with tempfile.TemporaryDirectory() as td,patch.object(sensei,'ROOT',Path(td)):
            root=Path(td);(root/'chosen.py').write_text('def main(): pass\n',encoding='utf-8')
            (root/'inert.py').write_text('raise RuntimeError("must never import")\n',encoding='utf-8')
            self.assertEqual(sensei.resolve_script('chosen.py'),root/'chosen.py')

    def test_measurement_reference_exact_errors_and_counts(self):
        from tests.benchmark_dispatcher_selection import measure
        with tempfile.TemporaryDirectory() as td,patch.object(sensei,'ROOT',Path(td)):
            root=Path(td);(root/'research_status.py').write_text('def main(): pass\n',encoding='utf-8')
            (root/'json_io.py').write_text('def helper(): pass\n',encoding='utf-8')
            result=measure(1);sample=result['samples'][0]
            self.assertTrue(result['equivalent'])
            self.assertEqual(sample['legacy']['source_reads'],8);self.assertEqual(sample['legacy']['ast_parses'],8)
            self.assertEqual(sample['selected']['source_reads'],2);self.assertEqual(sample['selected']['ast_parses'],2)
        for invalid in (0,11,True):
            with self.assertRaises(ValueError):measure(invalid)

    def test_existing_symlink_discovery_policy_is_not_broadened(self):
        # This trusted-checkout selector is not a symlink/TOCTOU security sandbox.
        with tempfile.TemporaryDirectory() as td,patch.object(sensei,'ROOT',Path(td)):
            root=Path(td);source=root/'source.py';source.write_text('def main(): pass\n',encoding='utf-8')
            link=root/'alias.py'
            try:link.symlink_to(source)
            except (OSError,NotImplementedError):self.skipTest('symlink creation unavailable')
            self.assertIn('alias.py',{name for name,_ in sensei.entry_point_scripts()})
            self.assertEqual(sensei.resolve_script('alias.py'),link)
            source.unlink()
            with self.assertRaisesRegex(ValueError,'not a listed root script'):sensei.resolve_script('alias.py')


if __name__=='__main__':unittest.main()
