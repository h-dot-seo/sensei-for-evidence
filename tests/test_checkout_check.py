"""Synthetic checkout smoke checks and exact quick-start command replay."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import sensei

ROOT = Path(__file__).resolve().parents[1]


class CheckoutCheckTests(unittest.TestCase):
    def copy_checkout(self, destination):
        shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns('.git', '__pycache__'))

    def run_check(self, checkout, cwd):
        return subprocess.run([sys.executable, str(checkout / 'sensei.py'), 'check'],
                              cwd=cwd, capture_output=True, timeout=60)

    def test_clean_checkout_no_bytecode_or_caller_writes(self):
        with tempfile.TemporaryDirectory(prefix='sensei smoke ') as folder:
            root = Path(folder) / 'checkout'
            cwd = Path(folder) / 'caller'
            cwd.mkdir()
            self.copy_checkout(root)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result = self.run_check(root, cwd)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            for phrase in (b'PASS inventory', b'PASS syntax', b'PASS synthetic status',
                           b'not the test suite, CI matrix or research validation', b'NOT_READY'):
                self.assertIn(phrase, result.stdout)
            self.assertNotIn(b'Listing only', result.stdout)
            self.assertEqual(list(cwd.iterdir()), [])
            self.assertEqual(list(root.rglob('__pycache__')), [])
            after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_changed_missing_and_invalid_manifest_fail(self):
        for change in ('changed', 'missing', 'manifest', 'project', 'verifier_missing', 'verifier_syntax'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / 'checkout'
                self.copy_checkout(root)
                target = root / 'examples/review-demo.json'
                if change == 'changed':
                    target.write_bytes(target.read_bytes() + b'\n')
                elif change == 'missing':
                    target.unlink()
                elif change == 'manifest':
                    (root / 'PUBLICATION_MANIFEST.json').write_text('{')
                elif change == 'verifier_missing':
                    (root / 'verify_manifest.py').unlink()
                elif change == 'verifier_syntax':
                    (root / 'verify_manifest.py').write_text('fictional invalid !!!')
                else:
                    manifest = root / 'PUBLICATION_MANIFEST.json'
                    data = json.loads(manifest.read_bytes())
                    data['project'] = 'other'
                    manifest.write_text(json.dumps(data))
                result = self.run_check(root, folder)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(b'FAIL ', result.stdout)
                self.assertNotIn(b'PASS synthetic status', result.stdout)
                self.assertNotIn(b'Traceback', result.stderr)

    def test_unlisted_invalid_python_warns_but_strict_verifier_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'checkout'
            self.copy_checkout(root)
            (root / 'extra').mkdir()
            (root / 'extra/fictional.py').write_text('not valid python !!!')
            result = self.run_check(root, folder)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(b'WARN inventory', result.stdout)
            self.assertIn(b'extra/fictional.py', result.stdout)
            verified = subprocess.run([sys.executable, '-B', str(root / 'verify_manifest.py')],
                                      capture_output=True, timeout=60)
            self.assertEqual(verified.returncode, 1)

    def test_listed_syntax_error_fails_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'checkout'
            self.copy_checkout(root)
            name = 'tests/test_dispatcher.py'
            raw = b'fictional invalid python !!!\n'
            (root / name).write_bytes(raw)
            manifest = root / 'PUBLICATION_MANIFEST.json'
            data = json.loads(manifest.read_bytes())
            for row in data['files']:
                if row['path'] == name:
                    row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            manifest.write_text(json.dumps(data))
            result = self.run_check(root, folder)
            self.assertEqual(result.returncode, 1)
            self.assertIn(b'FAIL syntax', result.stdout)
            self.assertNotIn(b'PASS synthetic status', result.stdout)

    def test_unlisted_symlink_is_failure_not_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'checkout'
            self.copy_checkout(root)
            try:
                (root / 'fictional-link').symlink_to(root / 'README.md')
            except OSError:
                self.skipTest('symlink creation unavailable')
            result = self.run_check(root, folder)
            self.assertEqual(result.returncode, 1)
            self.assertIn(b'symlink not allowed', result.stdout)

    def test_status_errors_and_wrong_boundaries_fail_without_bytecode_setting_leak(self):
        cases = [subprocess.CompletedProcess([], 1, b'', b''),
                 subprocess.CompletedProcess([], 0, b'{', b''),
                 subprocess.CompletedProcess([], 0, b'[]', b''),
                 subprocess.CompletedProcess([], 0, b'{"conclusion_readiness":"READY"}', b''),
                 subprocess.TimeoutExpired('synthetic', 30)]
        for case in cases:
            with self.subTest(case=case), io.StringIO() as output:
                kwargs = {'side_effect': case} if isinstance(case, Exception) else {'return_value': case}
                before = sys.dont_write_bytecode
                with mock.patch.object(sensei.subprocess, 'run', **kwargs) as runner, contextlib.redirect_stdout(output):
                    self.assertEqual(sensei.check_checkout(), 1)
                self.assertEqual(sys.dont_write_bytecode, before)
                self.assertIn('FAIL synthetic status', output.getvalue())
                self.assertIn('-B', runner.call_args.args[0])
                self.assertEqual(runner.call_args.kwargs['timeout'], 30)

    def test_readme_quickstart_and_korean_mirror(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        block = re.search(r'## Quick start\n.*?```sh\n(.*?)```', readme, re.S).group(1)
        korean = (ROOT / 'docs/README.ko.md').read_text(encoding='utf-8')
        self.assertEqual(block, re.search(r'```sh\n(.*?)```', korean, re.S).group(1))
        self.assertEqual(block.splitlines()[0], 'python sensei.py check')
        with tempfile.TemporaryDirectory(prefix='sensei quick start ') as folder:
            for line in block.splitlines():
                args = shlex.split(line)
                self.assertEqual(args.pop(0), 'python')
                self.assertNotEqual(args[:2], ['-m', 'unittest'])
                args = [str(Path(folder) / 'synthetic-review.zip') if arg == '../synthetic-review.zip'
                        else arg for arg in args]
                result = subprocess.run([sys.executable, '-B', *args], cwd=ROOT,
                                        capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, (line, result.stdout, result.stderr))

    def test_documented_smoke_rehearsal(self):
        guide = (ROOT / 'docs/CHECKOUT_CHECK.md').read_text(encoding='utf-8')
        block = re.search(r'```sh\n(.*?)```', guide, re.S).group(1)
        self.assertEqual(block, 'python sensei.py check\n')
        result = subprocess.run([sys.executable, *shlex.split(block)[1:]], cwd=ROOT,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
