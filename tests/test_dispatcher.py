"""Synthetic dispatcher tests: listing, transparent run, strict rejection and no side effects."""
import ast
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import sensei

ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / 'sensei.py'
ENTRY_POINT = re.compile(r"__name__\s*==\s*['\"]__main__['\"]|^def main\(", re.M)


def dispatch(*arguments, cwd):
    return subprocess.run([sys.executable, str(DISPATCHER), *arguments], cwd=cwd, capture_output=True, timeout=120)


def direct(script, *arguments):
    return subprocess.run([sys.executable, str(ROOT / script), *arguments], cwd=ROOT, capture_output=True, timeout=120)


class DispatcherListingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix='sensei dispatcher ') as folder:
            cls.result = dispatch('list', cwd=folder)
            cls.created = list(Path(folder).iterdir())
        cls.text = cls.result.stdout.decode('utf-8')

    def test_list_runs_from_any_directory_without_writing_files(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        self.assertEqual(self.result.stderr, b'')
        self.assertEqual(self.created, [])

    def test_list_names_exactly_the_root_scripts_with_an_entry_point(self):
        expected = {path.name for path in ROOT.glob('*.py')
                    if path.name != 'sensei.py' and ENTRY_POINT.search(path.read_text(encoding='utf-8'))}
        listed = [line.split()[0] for line in self.text.splitlines()
                  if line.startswith('  ') and line.split()[0].endswith('.py')]
        self.assertEqual(listed, sorted(expected))
        self.assertIn('verify_manifest.py', listed)
        self.assertIn('audit_publication.py', listed)
        self.assertIn('research_status.py', listed)
        self.assertNotIn('json_io.py', listed)
        self.assertNotIn('sensei.py', listed)
        self.assertFalse(any(name.startswith('test_') for name in listed))
        self.assertEqual([name for name, _ in sensei.entry_point_scripts()], sorted(expected))

    def test_list_shows_first_docstring_sentences_only(self):
        self.assertIn('research_status.py', self.text)
        self.assertIn('Summarize mechanical review queues from a validated supplied protocol.', self.text)
        self.assertIn('Preserve an explicitly supplied contiguous appraisal-transition replay segment.', self.text)
        self.assertNotIn('The wrapper never changes protocols', self.text)
        self.assertEqual(sensei.first_sentence('First sentence.  Second one.\n\nThird.'), 'First sentence.')
        self.assertEqual(sensei.first_sentence('No terminal punctuation'), 'No terminal punctuation')
        self.assertEqual(sensei.first_sentence(None), '(no module docstring)')

    def test_list_shows_every_catalog_route_with_scripts_and_guides(self):
        import review_handoff
        routes = review_handoff.SUPPLIED_INPUT_WORKFLOWS
        self.assertTrue(routes)
        for route in routes:
            with self.subTest(workflow=route['workflow_id']):
                self.assertIn('  ' + route['workflow_id'].ljust(34) + ' ' + route['title'], self.text)
                for guide in route['guide_paths']:
                    self.assertIn(guide, self.text)
                for entry in route['entrypoints']:
                    self.assertIn(entry['script'], self.text)
        rendered = sensei.catalog_routes()
        self.assertEqual([row[0] for row in rendered], [route['workflow_id'] for route in routes])
        self.assertEqual(rendered[0][3], routes[0]['guide_paths'])
        self.assertEqual(rendered[3][2], ['nbib_intake.py', 'nbib_batch_intake.py', 'ris_intake.py', 'bibliographic_review.py'])

    def test_list_carries_boundary_text(self):
        for phrase in ('no script was executed', 'no network request', 'NOT_ESTABLISHED', 'NOT_READY'):
            self.assertIn(phrase, self.text)
        self.assertTrue(self.text.endswith('\n'))

    def test_listing_escapes_control_and_format_characters(self):
        text = sensei.render_listing([('x.py', 'Fictional\nConclusion: READY\x1b‮')], [])
        self.assertNotIn('\nConclusion: READY', text)
        self.assertNotIn('\x1b', text)
        self.assertNotIn('‮', text)
        self.assertIn('Fictional\\nConclusion: READY', text)

    def test_entry_point_detection_is_structural(self):
        self.assertTrue(sensei.has_entry_point(ast.parse('def main():\n    pass\n')))
        self.assertTrue(sensei.has_entry_point(ast.parse("if __name__ == '__main__':\n    pass\n")))
        self.assertFalse(sensei.has_entry_point(ast.parse('def helper():\n    pass\nMAIN = "__main__"\n')))
        self.assertFalse(sensei.has_entry_point(ast.parse('"""Only a docstring: if __name__ == \'__main__\'."""\n')))


class DispatcherRunTests(unittest.TestCase):
    def test_run_matches_direct_invocation_from_a_temporary_directory(self):
        protocol = str(ROOT / 'examples' / 'review-demo.json')
        for arguments in ([protocol], [protocol, '--text']):
            with self.subTest(arguments=arguments[1:]):
                expected = direct('research_status.py', *arguments)
                with tempfile.TemporaryDirectory(prefix='sensei dispatcher ') as folder:
                    result = dispatch('run', 'research_status.py', *arguments, cwd=folder)
                    self.assertEqual(list(Path(folder).iterdir()), [])
                self.assertEqual(expected.returncode, 0, expected.stderr)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected.stdout, b''))
                self.assertIn(b'NOT_READY', result.stdout)

    def test_run_passes_help_arguments_and_exit_status_through_unchanged(self):
        with tempfile.TemporaryDirectory(prefix='sensei dispatcher ') as folder:
            helped = dispatch('run', 'evidence_workflow.py', '--help', cwd=folder)
            self.assertEqual(helped.returncode, 0, helped.stderr)
            self.assertTrue(helped.stdout.startswith(b'usage: evidence_workflow.py'), helped.stdout[:80])
            self.assertEqual(helped.stdout, direct('evidence_workflow.py', '--help').stdout)
            verified = dispatch('run', 'verify_manifest.py', cwd=folder)
            report = json.loads(verified.stdout.decode('utf-8'))
            self.assertIn('valid', report)
            self.assertEqual(verified.returncode, int(not report['valid']))
            self.assertEqual(verified.stdout, direct('verify_manifest.py').stdout)
            failed = dispatch('run', 'research_status.py', str(Path(folder) / 'absent.json'), cwd=folder)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(failed.stdout, b'')
            self.assertNotIn(b'Traceback', failed.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_run_rejects_anything_but_a_listed_root_script_name(self):
        rejected = ['missing.py', 'json_io.py', 'sensei.py', 'README.md', 'research_status', 'RESEARCH_STATUS.PY',
                    '../sensei.py', 'tests/test_dispatcher.py', 'examples/review-demo.json',
                    str(ROOT / 'research_status.py'), '..', '.', '']
        with tempfile.TemporaryDirectory(prefix='sensei dispatcher ') as folder:
            for name in rejected:
                with self.subTest(name=name):
                    result = dispatch('run', name, '--help', cwd=folder)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, b'')
                    self.assertIn(b'sensei.py run: error: not a', result.stderr)
                    self.assertNotIn(b'Traceback', result.stderr)
            self.assertEqual(dispatch('run', cwd=folder).returncode, 2)
            self.assertEqual(dispatch(cwd=folder).returncode, 2)
            self.assertEqual(list(Path(folder).iterdir()), [])
        for name in rejected:
            with self.assertRaises(ValueError):
                sensei.resolve_script(name)
        self.assertEqual(sensei.resolve_script('verify_manifest.py'), ROOT / 'verify_manifest.py')

    def test_help_is_available_from_any_directory_and_names_the_boundary(self):
        with tempfile.TemporaryDirectory(prefix='sensei dispatcher ') as folder:
            result = dispatch('--help', cwd=folder)
            self.assertEqual(list(Path(folder).iterdir()), [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(b'usage: sensei.py'))
        for phrase in (b'list', b'run', b'NOT_READY', b'no network request'):
            self.assertIn(phrase, result.stdout)

    def test_startup_and_run_import_no_catalog_module(self):
        modules = sorted({path.stem for path in ROOT.glob('*.py')} - {'sensei'})
        code = ('import json, sys, sensei\n'
                'print(json.dumps(sorted(set(sys.modules) & set(' + repr(modules) + '))))\n')
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.decode('utf-8').splitlines()[-1]), [])
        code = ('import sys, sensei\n'
                "sys.argv = ['sensei.py', 'run', 'validate_run.py', '--help']\n"
                'try:\n    sensei.main()\nexcept SystemExit:\n    pass\n'
                "print('IMPORTED' if 'review_handoff' in sys.modules else 'NOT_IMPORTED')\n")
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'usage: validate_run.py', result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith(b'NOT_IMPORTED'), result.stdout[-200:])


if __name__ == '__main__':
    unittest.main()
