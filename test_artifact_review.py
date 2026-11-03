"""Synthetic local artifact checks, permissions and byte-only boundaries."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import artifact_review as ar
ROOT=Path(__file__).resolve().parent

class ArtifactReviewTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/artifact-review-protocol.json').read_text())
        self.m=json.loads((ROOT/'examples/artifact-review-manifest.json').read_text())
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.file=self.root/'receipt-review.txt'
        self.file.write_bytes((ROOT/'examples/local-artifacts/receipt-review.txt').read_bytes())
    def review(self):
        if not ar.secure_open_supported():self.skipTest('secure descriptor traversal unavailable; explicit fail-closed tested separately')
        return ar.review_artifacts(self.p,self.m,self.root)
    def test_bytes_match_does_not_complete_work_or_accept_receipts(self):
        before=copy.deepcopy(self.p);r=self.review()
        self.assertTrue(r['all_requested_bytes_match']);self.assertEqual(r['artifacts'][0]['status'],'BYTES_MATCH')
        self.assertEqual(r['artifacts'][0]['supplied_work_status'],'IN_PROGRESS')
        self.assertEqual(r['artifacts'][0]['acceptance_assessment'],'NOT_PERFORMED')
        self.assertEqual(r['uninspected_work_ids'],['WP-EXTRACTION-REVIEW'])
        self.assertEqual(r['conclusion_readiness'],'NOT_READY');self.assertEqual(self.p,before)
        self.assertNotIn('FICTIONAL LOCAL WORK ARTIFACT',json.dumps(r));self.assertNotIn(str(self.root),json.dumps(r))
    def test_hash_size_missing_and_empty_manifest_are_distinct(self):
        self.m['artifacts'][0]['sha256']='0'*64
        self.assertEqual(self.review()['artifacts'][0]['status'],'HASH_MISMATCH')
        self.file.write_bytes(b'short');self.assertEqual(self.review()['artifacts'][0]['status'],'SIZE_MISMATCH')
        self.file.unlink();self.assertEqual(self.review()['artifacts'][0]['status'],'MISSING')
        self.m['artifacts']=[];self.assertFalse(self.review()['all_requested_bytes_match'])
    def test_validate_entire_manifest_before_file_access(self):
        self.m['artifacts'].append(dict(self.m['artifacts'][0],work_package_id='unknown'))
        with patch.object(ar,'open_root',side_effect=AssertionError('must not open')),self.assertRaises(ValueError):
            ar.review_artifacts(self.p,self.m,self.root)
    def test_paths_reject_escape_uri_noncanonical_and_protected_metadata(self):
        for name in ('../x','/tmp/x','x/../y','./x','x//y','x/','C:/x','x\\y','https://x','.git/config','.aws/config','x\x00','x.','x '):
            with self.subTest(name=name),self.assertRaises(ValueError):ar.safe_relative(name)
    def test_manifest_types_duplicates_hash_and_limits(self):
        work={w['work_package_id']:w for w in self.p['gaps']}
        mutations=[dict(bytes=True),dict(bytes=-1),dict(bytes=ar.MAX_FILE_BYTES+1),dict(sha256='X'*64),dict(artifact_locator='other'),dict(work_package_id=[]),dict(extra='unknown')]
        for fields in mutations:
            m=copy.deepcopy(self.m);m['artifacts'][0].update(fields)
            with self.subTest(fields=fields),self.assertRaises(ValueError):ar.validate_manifest(m,work)
        for schema in (True,1.0,'1',None):
            m=copy.deepcopy(self.m);m['schema_version']=schema
            with self.assertRaises(ValueError):ar.validate_manifest(m,work)
        self.m['artifacts']*=2
        with self.assertRaises(ValueError):ar.validate_manifest(self.m,work)
    def test_unsupported_environment_fails_closed(self):
        with patch.object(ar,'secure_open_supported',return_value=False),patch.object(ar,'open_root',side_effect=AssertionError('must not open')):
            with self.assertRaisesRegex(ValueError,'no artifacts inspected'):ar.review_artifacts(self.p,self.m,self.root)
    @unittest.skipUnless(ar.secure_open_supported(),'POSIX descriptor traversal')
    def test_symlink_file_and_parent_and_root_rejected(self):
        target=self.root/'target';self.file.rename(target);self.file.symlink_to(target)
        self.assertEqual(self.review()['artifacts'][0]['status'],'REJECTED_FILE_TYPE')
        self.file.unlink();self.file.write_bytes(target.read_bytes())
        link=self.root/'link';link.symlink_to(self.root,target_is_directory=True)
        self.m['artifacts'][0]['path']='link/receipt-review.txt'
        self.assertEqual(self.review()['artifacts'][0]['status'],'UNREADABLE_OR_UNSAFE_PATH')
        with self.assertRaisesRegex(ValueError,'root unreadable or unsafe'):ar.review_artifacts(self.p,self.m,link)
    @unittest.skipUnless(ar.secure_open_supported(),'POSIX descriptor traversal')
    def test_fifo_directory_and_hardlink_not_read(self):
        self.file.unlink();os.mkfifo(self.file)
        with patch.object(ar.os,'read',side_effect=AssertionError('must not read')):
            self.assertEqual(self.review()['artifacts'][0]['status'],'REJECTED_FILE_TYPE')
        self.file.unlink();self.file.mkdir();self.assertEqual(self.review()['artifacts'][0]['status'],'REJECTED_FILE_TYPE')
        self.file.rmdir();target=self.root/'target';target.write_bytes(b'fictional');os.link(target,self.file)
        self.assertEqual(self.review()['artifacts'][0]['status'],'REJECTED_FILE_TYPE')
    @unittest.skipUnless(ar.secure_open_supported(),'POSIX descriptor traversal')
    def test_nested_regular_file_and_zero_bytes(self):
        sub=self.root/'notes';sub.mkdir();self.file.rename(sub/'receipt-review.txt')
        self.m['artifacts'][0]['path']='notes/receipt-review.txt';self.assertTrue(self.review()['all_requested_bytes_match'])
        (sub/'receipt-review.txt').write_bytes(b'');self.m['artifacts'][0].update(bytes=0,sha256=hashlib.sha256(b'').hexdigest())
        self.assertTrue(self.review()['all_requested_bytes_match'])
    @unittest.skipUnless(ar.secure_open_supported(),'POSIX descriptor traversal')
    def test_growth_during_read_is_not_success(self):
        original=ar.os.read;done=False
        def read(fd,n):
            nonlocal done
            if not done:
                done=True
                with self.file.open('ab') as f:f.write(b'growth')
            return original(fd,n)
        with patch.object(ar.os,'read',side_effect=read):
            self.assertEqual(self.review()['artifacts'][0]['status'],'CHANGED_DURING_READ')
    def test_limits_and_input_read_errors(self):
        work={w['work_package_id']:w for w in self.p['gaps']}
        with patch.object(ar,'MAX_ARTIFACTS',0),self.assertRaises(ValueError):ar.validate_manifest(self.m,work)
        with patch.object(ar,'MAX_INPUT_BYTES',1),self.assertRaisesRegex(ValueError,'byte limit'):ar.read_input(self.file)
        with self.assertRaisesRegex(ValueError,'regular'):ar.read_input(self.root)
        result=subprocess.run([sys.executable,str(ROOT/'artifact_review.py'),str(self.root/'missing'),str(ROOT/'examples/artifact-review-manifest.json'),'--root',str(self.root)],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertNotIn(str(self.root).encode(),result.stderr)
    @unittest.skipUnless(ar.secure_open_supported(),'POSIX descriptor traversal')
    def test_root_parent_traversal_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'parent traversal'):ar.review_artifacts(self.p,self.m,self.root/'child'/'..')

    def test_cli_platform_boundary_and_opt_in_root(self):
        cmd=[sys.executable,str(ROOT/'artifact_review.py'),str(ROOT/'examples/artifact-review-protocol.json'),str(ROOT/'examples/artifact-review-manifest.json')]
        missing=subprocess.run(cmd,capture_output=True);self.assertNotEqual(missing.returncode,0)
        result=subprocess.run(cmd+['--root',str(self.root)],capture_output=True)
        if ar.secure_open_supported():
            self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['all_requested_bytes_match'])
        else:
            self.assertNotEqual(result.returncode,0);self.assertIn(b'no artifacts inspected',result.stderr)

if __name__=='__main__':unittest.main()
