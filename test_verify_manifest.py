import hashlib
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import stat
from verify_manifest import verify, link_like


class PublicationManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()/'publication'
        self.root.mkdir()
        (self.root/'README.md').write_text('synthetic publication\n', encoding='utf-8')
        raw = (self.root/'README.md').read_bytes()
        self.manifest = dict(file_count=1,files=[dict(path='README.md',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())])
        self.write_manifest()

    def write_manifest(self):
        (self.root/'PUBLICATION_MANIFEST.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_exact_inventory_passes_and_generated_cache_is_ignored(self):
        self.assertEqual(verify(self.root), [])
        (self.root/'__pycache__').mkdir()
        (self.root/'__pycache__'/'synthetic.pyc').write_bytes(b'cache')
        self.assertEqual(verify(self.root), [])

    def test_unlisted_file_is_not_silently_outside_manifest(self):
        (self.root/'extra.txt').write_text('synthetic omitted file')
        self.assertIn('extra.txt: unlisted file', verify(self.root))

    def test_changed_or_missing_file_rejected(self):
        (self.root/'README.md').write_text('changed')
        self.assertIn('README.md: size/hash mismatch', verify(self.root))
        (self.root/'README.md').unlink()
        self.assertIn('README.md: missing', verify(self.root))

    def test_unsafe_paths_are_rejected(self):
        for value in ('../outside.txt','/outside.txt','C:/outside.txt','docs\\outside.txt','./README.md','.git/config','PUBLICATION_MANIFEST.json','bad\nname','bad\x00name'):
            self.manifest['files'][0]['path'] = value
            self.write_manifest()
            with self.subTest(value=value):
                self.assertIn('unsafe manifest path', verify(self.root))

    def test_duplicate_and_case_colliding_paths_rejected(self):
        self.manifest['files'].append(dict(self.manifest['files'][0]))
        self.manifest['file_count'] = 2
        self.write_manifest()
        self.assertTrue(any('duplicate manifest path' in error for error in verify(self.root)))
        self.manifest['files'][1]['path'] = 'readme.md'
        self.write_manifest()
        self.assertTrue(any('case-insensitive' in error for error in verify(self.root)))

    def test_malformed_metadata_is_validation_error(self):
        for key, value in (('bytes',True),('bytes',-1),('sha256','not-a-hash')):
            original = dict(self.manifest['files'][0])
            self.manifest['files'][0][key] = value
            self.write_manifest()
            self.assertTrue(any('invalid size/hash metadata' in error for error in verify(self.root)))
            self.manifest['files'][0] = original
        self.manifest['file_count'] = True
        self.write_manifest()
        self.assertIn('file count mismatch', verify(self.root))
        (self.root/'PUBLICATION_MANIFEST.json').write_text('[]')
        self.assertTrue(verify(self.root))

    def test_unreadable_inventory_directory_fails_closed(self):
        hidden = self.root/'hidden'
        hidden.mkdir()
        (hidden/'unlisted.txt').write_text('synthetic')
        original = Path.iterdir
        def guarded(path):
            if path == hidden:
                raise PermissionError('synthetic unreadable directory')
            return original(path)
        with patch.object(Path, 'iterdir', guarded):
            self.assertTrue(any('inventory unreadable' in error for error in verify(self.root)))

    def test_nonregular_inventory_entry_rejected(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('FIFO creation unavailable on this platform')
        os.mkfifo(self.root/'synthetic.fifo')
        self.assertIn('synthetic.fifo: nonregular filesystem entry not allowed', verify(self.root))
        manifest_path = self.root/'PUBLICATION_MANIFEST.json'
        manifest_path.unlink()
        os.mkfifo(manifest_path)
        self.assertEqual(verify(self.root), ['manifest must be a regular file'])

    @unittest.skipUnless(os.name == 'nt', 'native Windows junction test')
    def test_native_windows_junction_rejected(self):
        outside = Path(self.tmp.name)/'junction-target'
        outside.mkdir()
        (outside/'data.txt').write_text('synthetic only')
        junction = self.root/'junction'
        result = subprocess.run(['cmd','/c','mklink','/J',str(junction),str(outside)],
                                capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout + result.stderr)
        self.assertTrue(link_like(junction))
        raw = (outside/'data.txt').read_bytes()
        self.manifest['files'] = [dict(path='junction/data.txt',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())]
        self.manifest['file_count'] = 1
        self.write_manifest()
        self.assertIn('junction/data.txt: symlink not allowed',verify(self.root))

    def test_symlink_file_and_parent_are_rejected(self):
        with patch.object(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024, create=True):
            with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=1024)):
                self.assertTrue(link_like(self.root))
        outside = Path(self.tmp.name)/'outside'
        outside.mkdir()
        (outside/'data.txt').write_text('synthetic only')
        try:
            (self.root/'linked').symlink_to(outside, target_is_directory=True)
            (self.root/'link.txt').symlink_to(outside/'data.txt')
        except (OSError, NotImplementedError) as error:
            self.skipTest('symlink creation unavailable: ' + str(error))
        raw = (outside/'data.txt').read_bytes()
        self.manifest['files'] = [dict(path='linked/data.txt',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),dict(path='link.txt',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())]
        self.manifest['file_count'] = 2
        self.write_manifest()
        errors = verify(self.root)
        self.assertIn('linked/data.txt: symlink not allowed',errors)
        self.assertIn('link.txt: symlink not allowed',errors)
        alias = Path(self.tmp.name)/'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        (self.root/'nested').mkdir()
        self.assertEqual(verify(alias/'nested'), ['publication root and manifest must not be symlinks'])
        manifest_path = self.root/'PUBLICATION_MANIFEST.json'
        outside_manifest = outside/'manifest.json'
        outside_manifest.write_text(json.dumps(self.manifest))
        manifest_path.unlink()
        manifest_path.symlink_to(outside_manifest)
        self.assertEqual(verify(self.root), ['publication root and manifest must not be symlinks'])
