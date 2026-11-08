"""Fictional local document checks do not become human or scientific verification."""
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
import report_source_check as sc
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
from report_review_links import prepare_targets

ROOT = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


class ReportSourceCheckTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads((ROOT/'examples/report-source-check-protocol.json').read_text(encoding='utf-8'))
        self.m = json.loads((ROOT/'examples/report-source-check-manifest.json').read_text(encoding='utf-8'))
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.file = self.root/'fictional-report.txt'
        self.body = (ROOT/'examples/local-sources/fictional-report.txt').read_bytes()
        self.file.write_bytes(self.body)

    def check(self, p=None, m=None):
        if not ar.secure_open_supported():
            self.skipTest('secure POSIX no-follow traversal unavailable; fail-closed tested separately')
        return sc.check_sources(self.p if p is None else p, self.m if m is None else m, self.root)

    def reject_without_access(self, p, m):
        with patch.object(sc, 'open_root', side_effect=AssertionError('must validate before access')):
            with self.assertRaises((ValueError, TypeError, KeyError)):
                sc.check_sources(p, m, self.root)

    def cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(ROOT/'report_source_check.py'), *map(str,args)],
                              cwd=ROOT, capture_output=True, env=env)

    def paths(self):
        p = self.root/'protocol.json'; m = self.root/'manifest.json'
        p.write_text(json.dumps(self.p, ensure_ascii=False), encoding='utf-8')
        m.write_text(json.dumps(self.m, ensure_ascii=False), encoding='utf-8')
        return p, m

    def test_template_only_copies_explicit_context_and_leaves_file_mapping_blank(self):
        before = copy.deepcopy(self.p)
        result = sc.template(self.p)
        rows = result['manifest']['sources']
        self.assertEqual({r['source_id'] for r in rows}, {'source-main','source-uninspected'})
        for row in rows:
            self.assertIsNone(row['path']); self.assertIsNone(row['bytes'])
            source = next(s for s in self.p['report_sources'] if s['source_id'] == row['source_id'])
            self.assertEqual(row['source_descriptor_sha256'], digest(source))
            self.assertEqual(row['report_id'], source['report_id'])
        self.assertIn('source-unbound', json.dumps(result['source_first_guidance']))
        self.assertEqual(self.p,before)
        self.assertEqual(sc.template(self.p, 'source-main')['manifest']['sources'], rows[:1])
        self.assertEqual(sc.template(self.p, 'source-unbound')['manifest']['sources'], [])

    def test_selection_is_literal_and_unknown_or_nonstring_rejects(self):
        for source in ('missing', 'source-main ', 'SOURCE-MAIN', [], {}, True, 1):
            with self.subTest(source=source), self.assertRaises((ValueError, TypeError)):
                sc.template(self.p, source)
        p = copy.deepcopy(self.p); p.pop('report_sources')
        self.assertEqual(sc.template(p)['manifest']['sources'], [])

    def test_whole_protocol_validates_even_with_narrow_or_empty_selection(self):
        p=copy.deepcopy(self.p); p['evidence'][0]['study_id']='unknown-study'
        for action in (lambda: sc.template(p,'source-main'), lambda: sc.check_sources(p,dict(schema_version=1,sources=[]),self.root)):
            with patch.object(sc,'open_root',side_effect=AssertionError('must not open')):
                with self.assertRaises(ValueError): action()

    def test_manifest_top_level_schema_strict(self):
        cases=[None, [], {}, dict(self.m,extra=True), {'schema_version':1,'sources':None}]
        for version in (True,False,1.0,'1',None,0,2): cases.append(dict(self.m,schema_version=version))
        for value in (None,{},False,'',0): cases.append(dict(self.m,sources=value))
        for manifest in cases:
            with self.subTest(manifest=manifest): self.reject_without_access(self.p,manifest)

    def test_manifest_entry_fields_and_types_strict(self):
        good=self.m['sources'][0]; cases=[None,[],dict(good,extra=True)]
        for field in good:
            row=dict(good);row.pop(field);cases.append(row)
        for field in ('source_id','report_id','source_descriptor_sha256','path'):
            for value in (None,False,1,[],{},'', ' '): cases.append(dict(good,**{field:value}))
        for value in (True,False,1.0,'225',None,-1,ar.MAX_FILE_BYTES+1): cases.append(dict(good,bytes=value))
        for row in cases:
            with self.subTest(row=row): self.reject_without_access(self.p,dict(schema_version=1,sources=[row]))

    def test_unknown_cross_report_and_source_fingerprint_drift_reject(self):
        good=self.m['sources'][0]
        for fields in (dict(source_id='missing'),dict(report_id='report-two'),dict(report_id='missing'),
                       dict(source_descriptor_sha256='0'*64),dict(source_descriptor_sha256='A'*64),
                       dict(source_descriptor_sha256='0'*64+'\n')):
            self.reject_without_access(self.p,dict(schema_version=1,sources=[dict(good,**fields)]))
        for field,value in [('source_locator','fictional://changed'),('document_version','changed'),('document_sha256','b'*64)]:
            p=copy.deepcopy(self.p);p['report_sources'][0][field]=value
            self.reject_without_access(p,self.m)

    def test_null_digest_cannot_be_promoted_by_manifest(self):
        p=copy.deepcopy(self.p);p['report_sources'][0]['document_sha256']=None
        m=copy.deepcopy(self.m);m['sources'][0]['source_descriptor_sha256']=digest(p['report_sources'][0])
        self.reject_without_access(p,m)
        self.assertEqual(sc.template(p,'source-main')['manifest']['sources'],[])

    def test_entire_manifest_validates_before_first_file_open(self):
        m=copy.deepcopy(self.m);m['sources'].append(dict(m['sources'][0],source_id='unknown'))
        self.reject_without_access(self.p,m)
        m=copy.deepcopy(self.m);m['sources']*=2;self.reject_without_access(self.p,m)
        other=self.p['report_sources'][2]
        m=copy.deepcopy(self.m);m['sources'].append(dict(m['sources'][0],source_id=other['source_id'],report_id=other['report_id'],source_descriptor_sha256=digest(other),path='FICTIONAL-REPORT.TXT'))
        self.reject_without_access(self.p,m)

    def test_unsafe_paths_and_protected_metadata_reject(self):
        for path in ('../x','/tmp/x','x/../y','./x','x//y','x/','C:/x','x\\y','https://x','.git/config','.aws/config','.codex/x','x\x00','x\n','x.','x '):
            m=copy.deepcopy(self.m);m['sources'][0]['path']=path
            with self.subTest(path=path):self.reject_without_access(self.p,m)

    def test_template_scaffold_is_not_a_completed_manifest(self):
        self.reject_without_access(self.p,sc.template(self.p)['manifest'])

    def test_descriptor_hash_ignores_object_key_order_not_literal_values(self):
        p=copy.deepcopy(self.p);p['report_sources'][0]=dict(reversed(list(p['report_sources'][0].items())))
        self.assertEqual(sc.template(p,'source-main')['manifest'],sc.template(self.p,'source-main')['manifest'])
        p['report_sources'][0]['document_version']+=' '
        self.assertNotEqual(sc.template(p,'source-main')['manifest'],sc.template(self.p,'source-main')['manifest'])

    def test_success_is_local_subset_only_and_no_content_or_absolute_root(self):
        result=self.check()
        self.assertTrue(result['all_requested_bytes_match'])
        self.assertEqual(result['sources'][0]['status'],'BYTES_MATCH')
        self.assertEqual(result['sources'][0]['observed_sha256'],hashlib.sha256(self.body).hexdigest())
        self.assertEqual(result['sources'][0]['observed_bytes'],len(self.body))
        self.assertEqual(result['uninspected_source_ids'],['source-unbound','source-uninspected'])
        encoded=json.dumps(result,ensure_ascii=False)
        self.assertNotIn(self.body.decode(),encoded);self.assertNotIn(str(self.root),encoded)
        self.assertEqual(result['external_calls'],0);self.assertIs(result['protocol_changed'],False)
        self.assertEqual(result['protocol_sha256'],digest(self.p));self.assertEqual(result['manifest_sha256'],digest(self.m))
        self.assertEqual(result,self.check())

    def test_hash_size_missing_and_empty_manifest_are_distinct(self):
        self.file.write_bytes(b'x'*len(self.body));self.assertEqual(self.check()['sources'][0]['status'],'HASH_MISMATCH')
        self.file.write_bytes(b'short');self.assertEqual(self.check()['sources'][0]['status'],'SIZE_MISMATCH')
        self.file.unlink();self.assertEqual(self.check()['sources'][0]['status'],'MISSING')
        result=self.check(m=dict(schema_version=1,sources=[]))
        self.assertFalse(result['all_requested_bytes_match']);self.assertEqual(result['sources'],[])
        self.assertEqual(result['uninspected_source_ids'],[s['source_id'] for s in self.p['report_sources']])

    def test_no_mutation_of_input_or_canonical_views_or_review_hashes(self):
        from research_bundle import build_bundle
        before=copy.deepcopy((self.p,self.m));core=run(self.p);reports=report_flow(self.p);targets=prepare_targets(self.p)
        bundle=build_bundle(canonical_json_bytes(self.p))
        result=self.check();result['sources'][0]['supplied_source']['document_version']='edited detached output'
        self.assertEqual((self.p,self.m),before);self.assertEqual(run(self.p),core)
        self.assertEqual(report_flow(self.p),reports);self.assertEqual(prepare_targets(self.p),targets)
        self.assertEqual(run(self.p)['report_review']['document_bytes_verification'],'NOT_PERFORMED')
        self.assertEqual(build_bundle(canonical_json_bytes(self.p)),bundle)

    def test_engine_fingerprints_include_actual_checker_and_reused_primitive(self):
        result=sc.template(self.p)
        for name in ('report_source_check.py','artifact_review.py','report_review_links.py'):
            self.assertEqual(result['engine_sha256'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())

    def test_invalid_protocol_does_not_open_even_when_platform_is_unsupported(self):
        p=copy.deepcopy(self.p);p['report_sources'][0]['document_sha256']='bad'
        with patch.object(sc,'secure_open_supported',return_value=False):self.reject_without_access(p,self.m)

    def test_unsupported_platform_fails_closed_without_open(self):
        with patch.object(sc,'secure_open_supported',return_value=False),patch.object(sc,'open_root',side_effect=AssertionError('must not open')):
            with self.assertRaisesRegex(ValueError,'unavailable|unsupported|no .* inspected'):
                sc.check_sources(self.p,self.m,self.root)

    @unittest.skipUnless(ar.secure_open_supported(),'secure POSIX traversal')
    def test_symlink_file_parent_and_root_reject(self):
        target=self.root/'target';self.file.rename(target);self.file.symlink_to(target)
        self.assertEqual(self.check()['sources'][0]['status'],'REJECTED_FILE_TYPE')
        self.file.unlink();self.file.write_bytes(target.read_bytes())
        link=self.root/'link';link.symlink_to(self.root,target_is_directory=True)
        m=copy.deepcopy(self.m);m['sources'][0]['path']='link/fictional-report.txt'
        self.assertEqual(self.check(m=m)['sources'][0]['status'],'UNREADABLE_OR_UNSAFE_PATH')
        with self.assertRaises(ValueError):sc.check_sources(self.p,self.m,link)

    @unittest.skipUnless(ar.secure_open_supported(),'secure POSIX traversal')
    def test_fifo_hardlink_directory_and_parent_traversal_reject(self):
        self.file.unlink();os.mkfifo(self.file)
        with patch.object(ar.os,'read',side_effect=AssertionError('must not read')):
            self.assertEqual(self.check()['sources'][0]['status'],'REJECTED_FILE_TYPE')
        self.file.unlink();self.file.mkdir();self.assertEqual(self.check()['sources'][0]['status'],'REJECTED_FILE_TYPE')
        self.file.rmdir();target=self.root/'target';target.write_bytes(self.body);os.link(target,self.file)
        self.assertEqual(self.check()['sources'][0]['status'],'REJECTED_FILE_TYPE')
        with self.assertRaises(ValueError):sc.check_sources(self.p,self.m,self.root/'child'/'..')

    def test_nested_and_zero_byte_files(self):
        nested=self.root/'nested';nested.mkdir();self.file.rename(nested/'empty')
        (nested/'empty').write_bytes(b'');p=copy.deepcopy(self.p);p['report_sources'][0]['document_sha256']=hashlib.sha256(b'').hexdigest()
        m=copy.deepcopy(self.m);m['sources'][0].update(path='nested/empty',bytes=0,source_descriptor_sha256=digest(p['report_sources'][0]))
        self.assertTrue(self.check(p=p,m=m)['all_requested_bytes_match'])

    @unittest.skipUnless(ar.secure_open_supported(),'secure POSIX traversal')
    def test_file_growth_during_read_does_not_match(self):
        original=ar.os.read;done=False
        def read(fd,n):
            nonlocal done
            if not done:
                done=True
                with self.file.open('ab') as output:output.write(b'growth')
            return original(fd,n)
        with patch.object(ar.os,'read',side_effect=read):
            self.assertEqual(self.check()['sources'][0]['status'],'CHANGED_DURING_READ')

    def test_report_source_hash_retains_csv_mapping_provenance(self):
        from test_report_study_inventory import ReportStudyInventoryTests
        helper=ReportStudyInventoryTests();helper.setUp();p=helper.imported()
        result=sc.template(p)
        research=run(p)
        expected=prepare_targets(p,research['bibliographic_collection'])['report_targets'][0]['source_basis_sha256']
        self.assertEqual(result['sources'][0]['current_source_basis_sha256'],expected)
        naive=prepare_targets(p)['report_targets'][0]['source_basis_sha256']
        self.assertNotEqual(expected,naive)

    def test_resource_caps_reject_before_root_access(self):
        for name,value in [('MAX_ARTIFACTS',0),('MAX_TOTAL_BYTES',len(self.body)-1),('MAX_FILE_BYTES',len(self.body)-1)]:
            with self.subTest(name=name),patch.object(sc,name,value):
                self.reject_without_access(self.p,self.m)

    @unittest.skipUnless(ar.secure_open_supported(),'secure POSIX traversal')
    def test_same_size_rewrite_during_read_is_not_success(self):
        original=ar.os.read;done=False
        def read(fd,n):
            nonlocal done
            if not done:
                done=True
                self.file.write_bytes(b'x'*len(self.body))
                current=self.file.stat()
                os.utime(self.file,ns=(current.st_atime_ns,current.st_mtime_ns+1_000_000_000))
            return original(fd,n)
        with patch.object(ar.os,'read',side_effect=read):
            self.assertEqual(self.check()['sources'][0]['status'],'CHANGED_DURING_READ')

    @unittest.skipUnless(ar.secure_open_supported(),'secure POSIX traversal')
    def test_file_replacement_between_stat_and_open_is_rejected(self):
        original=ar.os.open;done=False
        def opening(path,flags,*args,**kwargs):
            nonlocal done
            if path=='fictional-report.txt' and kwargs.get('dir_fd') is not None and not done:
                done=True
                self.file.rename(self.root/'old-file')
                self.file.write_bytes(self.body)
            return original(path,flags,*args,**kwargs)
        with patch.object(ar.os,'open',side_effect=opening),patch.object(sc,'secure_open_supported',return_value=True):
            self.assertEqual(sc.check_sources(self.p,self.m,self.root)['sources'][0]['status'],'REJECTED_FILE_TYPE')

    def test_local_match_does_not_upgrade_unavailable_retrieval(self):
        p=copy.deepcopy(self.p);p['evidence']=[];p['gaps']=[]
        p['reports'][0].pop('study_ids');p['reports'][0].update(retrieval='not_retrieved',decision='pending',reason='Fictional unavailable source')
        result=self.check(p=p)
        self.assertEqual(result['sources'][0]['status'],'BYTES_MATCH')
        self.assertEqual(result['sources'][0]['retrieval'],'not_retrieved')
        self.assertEqual(result['retrieval_assessment'],'NOT_PERFORMED')
        self.assertEqual(result['reading'],'NOT_ESTABLISHED')
        self.assertEqual(result['source_authenticity'],'NOT_VERIFIED')
        self.assertEqual(p['reports'][0]['retrieval'],'not_retrieved')

    def test_engine_fingerprint_inventory_has_all_shared_dependencies(self):
        from research_bundle import engine_hashes
        self.assertEqual(set(sc.template(self.p)['engine_sha256']),set(engine_hashes())|{'artifact_review.py','report_source_check.py'})

    def test_criteria_context_change_does_not_silently_rebind_file_descriptor(self):
        original=self.check();p=copy.deepcopy(self.p);p['question']+=' (fictional changed question)'
        changed=self.check(p=p)
        self.assertTrue(changed['all_requested_bytes_match'])
        self.assertEqual(original['sources'][0]['source_descriptor_sha256'],changed['sources'][0]['source_descriptor_sha256'])
        self.assertNotEqual(original['sources'][0]['current_source_basis_sha256'],changed['sources'][0]['current_source_basis_sha256'])
        self.assertNotEqual(original['protocol_sha256'],changed['protocol_sha256'])

    def test_cli_explicit_root_required_and_native_platform_boundary(self):
        p,m=self.paths()
        missing=self.cli('check',p,m);self.assertNotEqual(missing.returncode,0)
        result=self.cli('check',p,m,'--root',self.root)
        if ar.secure_open_supported():
            self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['all_requested_bytes_match'])
        else:
            self.assertNotEqual(result.returncode,0);self.assertIn(b'unavailable',result.stderr)

    def test_cli_template_strict_json_utf8_control_safe_and_no_overwrite(self):
        self.p['report_sources'][0]['source_locator']='fictional://한글\n\x1b[31m'
        p,m=self.paths();output=self.root/'new.json'
        env=dict(os.environ,PYTHONIOENCODING='ascii')
        result=self.cli('template',p,'--source-id','source-main','--output',output,'--text',env=env)
        self.assertEqual(result.returncode,0,result.stderr);self.assertNotIn(b'\x1b',result.stdout)
        parsed=json.loads(output.read_text(encoding='utf-8'));self.assertEqual(parsed['manifest']['sources'][0]['source_id'],'source-main')
        saved=output.read_bytes();again=self.cli('template',p,'--output',output)
        self.assertNotEqual(again.returncode,0);self.assertEqual(output.read_bytes(),saved)
        before=p.read_bytes();same=self.cli('template',p,'--output',p)
        self.assertNotEqual(same.returncode,0);self.assertEqual(p.read_bytes(),before)
        p.write_text('{"version":"a","version":"b"}',encoding='utf-8')
        bad=self.cli('template',p);self.assertNotEqual(bad.returncode,0);self.assertNotIn(b'Traceback',bad.stderr)

    def test_cli_errors_do_not_leak_absolute_paths_or_write_partial_outputs(self):
        p,m=self.paths();out=self.root/'must-not-exist.json'
        missing=self.cli('template',self.root/'missing-private-path','--output',out)
        self.assertNotEqual(missing.returncode,0);self.assertNotIn(str(self.root).encode(),missing.stderr);self.assertFalse(out.exists())
        bad=self.cli('check',p,m,'--root',self.root/'missing-private-root','--output',out)
        self.assertNotEqual(bad.returncode,0);self.assertNotIn(str(self.root).encode(),bad.stderr);self.assertFalse(out.exists())

    @unittest.skipUnless(ar.secure_open_supported(),'secure POSIX traversal')
    def test_cli_mismatch_output_is_still_saved_and_nonzero(self):
        p,m=self.paths();out=self.root/'mismatch.json';self.file.write_bytes(b'x'*len(self.body))
        result=self.cli('check',p,m,'--root',self.root,'--output',out)
        self.assertNotEqual(result.returncode,0);self.assertEqual(json.loads(out.read_text())['sources'][0]['status'],'HASH_MISMATCH')
        self.assertFalse(json.loads(result.stdout)['all_requested_bytes_match'])


if __name__=='__main__':unittest.main()
