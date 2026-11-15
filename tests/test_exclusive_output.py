"""One explicit existing-entry guard for the scoped fifteen consumers; no race-proof claim."""
import ast
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import output_io
from tests._exclusive_output_compat import prior_bytes
ROOT=Path(__file__).resolve().parents[1]
def load(n):return json.loads((ROOT/n).read_bytes())
CHANGES=load('tests/exclusive_output_source_changes.json')

class ExclusiveOutputTests(unittest.TestCase):
    def test_exact_inventory_and_prior_product_bytes(self):
        baseline=load('tests/exclusive_output_prior_sources.json');self.assertEqual(set(CHANGES),set(baseline['consumers']))
        self.assertEqual(len(CHANGES),15);sites=0
        for name,sha in baseline['consumers'].items():
            self.assertEqual(hashlib.sha256(prior_bytes(name)).hexdigest(),sha,name)
            tree=ast.parse((ROOT/name).read_bytes());calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='write_new'];sites+=len(calls)
            for n in ast.walk(tree):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='open':self.assertFalse(any(isinstance(a,ast.Constant) and a.value in ('x','xb') for a in n.args),name)
        self.assertEqual(sites,16)
        for name,sha in baseline['excluded'].items():
            from tests._json_depth_compat import prior_bytes as pre_depth_bytes
            self.assertEqual(hashlib.sha256(pre_depth_bytes(name)).hexdigest(),sha,name)

    def test_success_exact_utf8_and_binary_bytes_and_parent_requirement(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            for i,raw in enumerate((b'',b'\x00\xff\r\n','한글\n'.encode())):
                p=d/str(i);self.assertIsNone(output_io.write_new(p,raw));self.assertEqual(p.read_bytes(),raw)
            with self.assertRaises(FileNotFoundError):output_io.write_new(d/'missing'/'out',b'x')
            with self.assertRaises(TypeError):output_io.write_new(d/'wrong','text')
            self.assertFalse((d/'wrong').exists())

    def test_existing_file_directory_and_links_never_opened(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);f=d/'file';f.write_bytes(b'original');directory=d/'dir';directory.mkdir()
            for p in (f,directory):
                with patch.object(Path,'open',side_effect=AssertionError('existing entry opened')):
                    with self.assertRaises(FileExistsError):output_io.write_new(p,b'replacement')
            self.assertEqual(f.read_bytes(),b'original')
            for name,target in [('dangling',d/'not-created'),('link',f)]:
                p=d/name
                try:p.symlink_to(target)
                except (OSError,NotImplementedError):continue
                with patch.object(Path,'open',side_effect=AssertionError('link opened')):
                    with self.assertRaises(FileExistsError):output_io.write_new(p,b'replacement')
                self.assertTrue(p.is_symlink());self.assertEqual(f.read_bytes(),b'original');self.assertFalse((d/'not-created').exists())

    def test_native_symlink_entry_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'link';target=Path(td)/'never-create'
            try:p.symlink_to(target)
            except (OSError,NotImplementedError) as error:self.skipTest('native symlink unavailable: '+type(error).__name__)
            with self.assertRaises(FileExistsError):output_io.write_new(p,b'no')
            self.assertFalse(target.exists());self.assertTrue(p.is_symlink())

    @unittest.skipUnless(os.name=='nt','native Windows junction only')
    def test_native_windows_junction_entry_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);target=d/'target';target.mkdir();p=d/'junction'
            result=subprocess.run(['cmd','/c','mklink','/J',str(p),str(target)],capture_output=True)
            if result.returncode:self.skipTest('junction unavailable: '+repr(result.stderr))
            try:
                with self.assertRaises(FileExistsError):output_io.write_new(p,b'no')
                self.assertEqual(list(target.iterdir()),[])
            finally:os.rmdir(p)

    def test_exclusive_create_still_refuses_entry_created_after_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'race';real_lstat=Path.lstat
            def race(path,*a,**k):
                if path==p:
                    path.write_bytes(b'concurrent');raise FileNotFoundError()
                return real_lstat(path,*a,**k)
            with patch.object(Path,'lstat',race):
                with self.assertRaises(FileExistsError):output_io.write_new(p,b'ours')
            self.assertEqual(p.read_bytes(),b'concurrent')

    def test_stat_failure_does_not_open_and_partial_write_is_not_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'out'
            with patch.object(Path,'lstat',side_effect=PermissionError('stat failed')),patch.object(Path,'open',side_effect=AssertionError('opened')):
                with self.assertRaises(PermissionError):output_io.write_new(p,b'data')
            real_open=Path.open
            class Failing:
                def __init__(self,path):self.file=real_open(path,'xb')
                def __enter__(self):return self
                def __exit__(self,*args):self.file.close()
                def write(self,raw):self.file.write(raw[:2]);self.file.flush();raise OSError('synthetic disk failure')
            with patch.object(Path,'open',lambda path,*a,**k:Failing(path)):
                with self.assertRaises(OSError):output_io.write_new(p,b'full-data')
            self.assertEqual(p.read_bytes(),b'fu')

    def test_helper_is_in_explicit_consumer_fingerprints_not_research_engine(self):
        import research_bundle
        self.assertNotIn('output_io.py',research_bundle.ENGINE_FILES)
        digest=hashlib.sha256((ROOT/'output_io.py').read_bytes()).hexdigest()
        for name in CHANGES:
            m=importlib.import_module(name[:-3]);fn=getattr(m,'_implementation_hashes',None) or getattr(m,'implementation_hashes',None)
            if fn:self.assertEqual(fn()['output_io.py'],digest,name)
        # View consumers expose the helper as part of their existing implementation map.
        p=load('examples/bibliographic-base.json')
        for name in ('report_review','report_study_inventory','report_study_inventory_review','report_study_review','screening_review'):
            m=importlib.import_module(name);self.assertEqual(m.review(p)['engine_sha256']['output_io.py'],digest,name)

    def test_documented_success_repeat_and_dangling_destinations(self):
        import re,shlex,sys
        commands=[shlex.split(line) for block in re.findall(r'```sh\n(.*?)```',(ROOT/'docs/OUTPUT_CONTRACT.md').read_text(),re.S) for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),7)
        with tempfile.TemporaryDirectory(prefix='exclusive journey ') as td:
            for index,original in enumerate(commands):
                args=[sys.executable,*[p.replace('OUTPUT',td) for p in original[1:]]]
                flags={'--output','--intake-output','--csv-output','--candidate-output'};position=next(i+1 for i,v in enumerate(args) if v in flags);destination=Path(args[position])
                r=subprocess.run(args,cwd=ROOT,capture_output=True);self.assertEqual(r.returncode,0,(args,r.stderr));self.assertEqual(r.stderr,b'');saved=destination.read_bytes()
                again=subprocess.run(args,cwd=ROOT,capture_output=True);self.assertEqual(again.returncode,1);self.assertEqual(again.stdout,b'');self.assertEqual(destination.read_bytes(),saved)
                link=Path(td)/('dangling-'+str(index));target=Path(td)/('absent-'+str(index))
                try:link.symlink_to(target)
                except (OSError,NotImplementedError):continue
                bad=list(args);bad[position]=str(link);blocked=subprocess.run(bad,cwd=ROOT,capture_output=True)
                self.assertEqual(blocked.returncode,1);self.assertEqual(blocked.stdout,b'');self.assertFalse(target.exists());self.assertTrue(link.is_symlink());self.assertEqual(destination.read_bytes(),saved)
