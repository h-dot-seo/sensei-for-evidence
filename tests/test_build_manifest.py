"""Public regeneration is deterministic, explicit and non-destructive."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_manifest as b
from verify_manifest import verify

ROOT = Path(__file__).resolve().parents[1]


class ManifestBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'tree'
        self.root.mkdir()
        self.original = json.loads((ROOT / b.MANIFEST).read_bytes())
        (self.root / b.MANIFEST).write_text(json.dumps(self.original), encoding='utf-8')
        (self.root / 'example.txt').write_bytes(b'fictional\n')

    def generate(self):
        return b.generate(self.root, '1.2.3-example', '2026-11-14')

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return b.main(['--root', str(self.root), '--release', '1.2.3-example', '--date', '2026-11-14', *args])

    def test_roundtrip_headers_and_exact_check(self):
        raw = self.generate()
        generated = json.loads(raw)
        for key in b.DECLARATIONS:
            if key not in ('release', 'date'):
                self.assertEqual(generated[key], self.original[key])
        self.assertEqual(generated['file_count'], 1)
        self.assertEqual([x['path'] for x in generated['files']], ['example.txt'])
        self.assertEqual(self.cli('--check'), 1)
        (self.root / b.MANIFEST).write_bytes(raw)
        self.assertEqual(verify(self.root), [])
        self.assertEqual(self.cli('--check'), 0)
        (self.root / 'example.txt').write_bytes(b'changed\n')
        self.assertEqual(self.cli('--check'), 1)

    def test_current_release_byte_reproduction(self):
        current = json.loads((ROOT / b.MANIFEST).read_bytes())
        self.assertEqual(b.generate(ROOT, current['release'], current['date']), (ROOT / b.MANIFEST).read_bytes())

    def test_ignored_files_sorted_and_no_self(self):
        for directory in ('.git', '__pycache__'):
            (self.root / directory).mkdir()
            (self.root / directory / 'private').write_bytes(b'\r')
        (self.root / 'A').write_bytes(b'a')
        self.assertEqual([r['path'] for r in json.loads(self.generate())['files']], ['A', 'example.txt'])

    def test_output_exclusive_outside_and_no_source_mutation(self):
        original = (self.root / b.MANIFEST).read_bytes()
        output = self.base / 'new.json'
        self.assertEqual(self.cli('--output', str(self.root / 'new.json')), 2)
        self.assertEqual(self.cli('--output', str(output)), 0)
        self.assertEqual(output.read_bytes(), self.generate())
        output.write_bytes(b'keep')
        self.assertEqual(self.cli('--output', str(output)), 2)
        self.assertEqual(output.read_bytes(), b'keep')
        self.assertEqual((self.root / b.MANIFEST).read_bytes(), original)

    def test_crlf_collision_and_limits_reject_before_output(self):
        output = self.base / 'new.json'
        (self.root / 'example.txt').write_bytes(b'line\r\n')
        self.assertEqual(self.cli('--output', str(output)), 2)
        self.assertFalse(output.exists())
        (self.root / 'example.txt').write_bytes(b'x')
        (self.root / 'EXAMPLE.txt').write_bytes(b'x')
        names = {path.name for path in self.root.iterdir()}
        if {'example.txt', 'EXAMPLE.txt'} <= names:
            with self.assertRaises(ValueError): self.generate()
            (self.root / 'EXAMPLE.txt').unlink()
        with patch.object(b, 'MAX_FILES', 0):
            with self.assertRaises(ValueError): self.generate()
        with patch.object(b, 'MAX_BYTES', 1):
            with self.assertRaises(ValueError): self.generate()

    def test_invalid_declaration_and_explicit_release_date(self):
        for release, day in [('1.2', '2026-11-14'), ('1.2.3', '2026-02-30'), ('1.2.3', '2026-1-1')]:
            with self.assertRaises(ValueError): b.generate(self.root, release, day)
        self.original['new_declaration'] = True
        (self.root / b.MANIFEST).write_text(json.dumps(self.original), encoding='utf-8')
        with self.assertRaises(ValueError): self.generate()

    def test_candidate_audit_and_dangling_output(self):
        output = self.base / 'new.json'
        self.original['project'] = 'fictional' + chr(64) + 'example.test'
        (self.root / b.MANIFEST).write_bytes(json.dumps(self.original).encode('utf-8'))
        self.assertEqual(self.cli('--output', str(output)), 2)
        self.assertFalse(output.exists())
        self.original['project'] = 'sensei-for-evidence'
        (self.root / b.MANIFEST).write_bytes(json.dumps(self.original).encode('utf-8'))
        try:
            output.symlink_to(self.base / 'absent')
        except OSError:
            self.skipTest('symlink creation unavailable')
        self.assertEqual(self.cli('--output', str(output)), 2)
        self.assertFalse((self.base / 'absent').exists())

    def test_symlink_rejected(self):
        try:
            (self.root / 'link').symlink_to(self.root / 'example.txt')
        except OSError:
            self.skipTest('symlink creation unavailable')
        with self.assertRaises(ValueError): self.generate()
