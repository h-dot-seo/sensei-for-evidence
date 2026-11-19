"""Seven-family manifest navigation is never payload verification or replay."""
import copy
from tests._amendment_compat import prior_bytes as pre_amendment, prior_fixture_bytes as pre_amendment_fixture
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import retained_bundle_describe as reader
from json_io import canonical_json_bytes
from tests._cli import run_cli

ROOT=Path(__file__).resolve().parents[1]
NAMES=['collection_bundle','batch_collection_bundle','native_collection_bundle','report_transition_bundle','extraction_transition_bundle','appraisal_transition_bundle','work_transition_bundle']
CLASSES=['CollectionBundleTests','BatchCollectionBundleTests','NativeCollectionBundleTests','ReportTransitionBundleTests','ExtractionTransitionBundleTests','AppraisalTransitionBundleTests','WorkTransitionBundleTests']


def repack(raw,change=None,entries=None):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        payloads={n:archive.read(n) for n in archive.namelist()}
    if change:change(payloads)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,value in sorted(payloads.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100600<<16
            if entries:entries(info)
            archive.writestr(info,value)
    return out.getvalue()


def manifest_change(raw,fn):
    def update(payloads):
        value=json.loads(payloads['manifest.json']);fn(value);payloads['manifest.json']=canonical_json_bytes(value)+b'\n'
    return repack(raw,update)


class RetainedBundleDescribeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archives={}
        for name,classname in zip(NAMES,CLASSES):
            module=importlib.import_module('tests.test_'+name);case=getattr(module,classname)
            case.setUpClass();fixture=case();fixture.setUp()
            try:cls.archives[name]=fixture.build()
            finally:fixture.tearDown();case.tearDownClass()

    def test_seven_actual_archives_old_implementation_navigation_not_replay(self):
        for name,raw in self.archives.items():
            with self.subTest(name=name):
                module=importlib.import_module(name)
                self.assertTrue(module.verify_bundle(raw)['valid'])
                report=reader.describe(raw)
                self.assertEqual(report['implementation_match'],'MATCH')
                self.assertEqual(report['bundle_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual(report['verifier_command'],['python',name+'.py','verify','BUNDLE.zip'])
                def change(m):
                    first=sorted(m['engine_sha256'])[0];m['engine_sha256'][first]='0'*64
                    m['engine_sha256']['synthetic_retired_module.py']='1'*64
                    del m['engine_sha256'][sorted(m['engine_sha256'])[1]]
                altered=manifest_change(raw,change)
                old=reader.describe(altered)
                self.assertEqual(old['implementation_match'],'DIFFERS')
                self.assertEqual(len(old['differing_engine_files']),3)
                with self.assertRaisesRegex(ValueError,'implementation bytes differ'):module.verify_bundle(altered)
                self.assertEqual(reader.describe(raw),report)
                for key in ('verification','payload_hash_verification','derivation_replay','canonical_zip_verification'):
                    self.assertEqual(old[key],'NOT_PERFORMED')
                self.assertEqual(old['conclusion_readiness'],'NOT_READY')

    def test_only_manifest_is_opened_no_replay_network_or_nested_zip(self):
        original=zipfile.ZipFile.read
        for name,raw in self.archives.items():
            calls=[]
            def read(archive,member,*args,**kwargs):
                calls.append(member)
                if member!='manifest.json':raise AssertionError('payload read forbidden')
                return original(archive,member,*args,**kwargs)
            module=importlib.import_module(name)
            with patch.object(zipfile.ZipFile,'read',read),patch.object(module,'verify_bundle',side_effect=AssertionError('replay forbidden')),patch.object(socket,'socket',side_effect=AssertionError('network forbidden')):
                result=reader.describe(raw)
            self.assertEqual(calls,['manifest.json'])
            self.assertEqual(result['verification'],'NOT_PERFORMED')

    def test_unverified_values_are_not_promoted_and_payload_hashes_not_checked(self):
        for raw in self.archives.values():
            forged=manifest_change(raw,lambda m:(m.update(conclusion_readiness='READY',review_status='APPROVED'),m['files'][0].update(sha256='f'*64)))
            result=reader.describe(forged)
            self.assertEqual(result['recorded_unverified']['conclusion_readiness'],'READY')
            self.assertEqual(result['conclusion_readiness'],'NOT_READY')
            self.assertEqual(result['verification'],'NOT_PERFORMED')
            self.assertEqual(result['implementation_match'],'MATCH')
        raw=self.archives['collection_bundle']
        def corrupt_payload(p):
            name=next(n for n in p if n!='manifest.json');p[name]=b'X'*len(p[name])
        damaged=repack(raw,corrupt_payload)
        self.assertEqual(reader.describe(damaged)['payload_hash_verification'],'NOT_PERFORMED')
        # Trailing/repacked metadata is not canonical verification; exact bytes are hashed.
        result=reader.describe(raw+b'trailing synthetic bytes')
        self.assertEqual(result['bundle_sha256'],hashlib.sha256(raw+b'trailing synthetic bytes').hexdigest())

    def test_strict_manifest_shape_and_recorded_inventory(self):
        raw=self.archives['collection_bundle']
        mutations=[lambda m:m.update(schema_version=True),lambda m:m.update(schema_version=2),lambda m:m.update(mode='unknown'),lambda m:m.update(extra=1),lambda m:m.pop('boundary'),lambda m:m.update(boundary='x'*4097),lambda m:m.update(engine_sha256={}),lambda m:m.update(engine_sha256={'../bad.py':'0'*64}),lambda m:m.update(input_sha256='A'*64),lambda m:m['files'][0].update(bytes=True),lambda m:m['files'][0].update(bytes=m['files'][0]['bytes']+1),lambda m:m['files'][0].update(sha256='bad'),lambda m:m['files'].append(copy.deepcopy(m['files'][0])),lambda m:m['files'][0].update(path='manifest.json'),lambda m:m.update(protocol_changed=1)]
        for i,fn in enumerate(mutations):
            with self.subTest(i=i),self.assertRaises(ValueError):reader.describe(manifest_change(raw,fn))
        for payload in (b'null',b'{"schema_version":1,"schema_version":1}',b'\xff',b'NaN',b'['*129+b']'*129):
            with self.assertRaises(ValueError):reader.describe(repack(raw,lambda p:p.update({'manifest.json':payload})))

    def test_entry_preflight_before_member_read_and_family_inventory(self):
        raw=self.archives['collection_bundle']
        cases=[repack(raw,lambda p:p.update({'../outside':b'x'})),repack(raw,lambda p:p.update({'directory/':b''})),repack(raw,entries=lambda i:setattr(i,'compress_type',zipfile.ZIP_DEFLATED)),repack(raw,entries=lambda i:setattr(i,'external_attr',0o120777<<16)),repack(raw,entries=lambda i:setattr(i,'create_system',0))]
        for data in cases:
            with patch.object(zipfile.ZipFile,'read',side_effect=AssertionError('must reject first')):
                with self.assertRaises(ValueError):reader.describe(data)
        missing=repack(raw,lambda p:p.pop('summary.txt'))
        with self.assertRaises(ValueError):reader.describe(missing)
        wrong=manifest_change(raw,lambda m:m.update(mode='explicit_work_transition_bundle'))
        with self.assertRaises(ValueError):reader.describe(wrong)
        # Entry-count refusal and total declared bytes precede reading manifest.
        with patch.object(reader,'MAX_ENTRIES',1),patch.object(zipfile.ZipFile,'read',side_effect=AssertionError('read forbidden')):
            with self.assertRaises(ValueError):reader.describe(raw)

    def test_duplicate_encryption_size_crc_and_truncation_boundaries(self):
        import struct
        import warnings
        raw=self.archives['collection_bundle']
        duplicate=io.BytesIO(raw)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(duplicate,'a') as archive:archive.writestr('manifest.json',b'{}')
        encrypted=bytearray(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:central=archive.start_dir
        flags=struct.unpack_from('<H',encrypted,central+8)[0]
        struct.pack_into('<H',encrypted,central+8,flags|1)
        huge=bytearray(raw)
        struct.pack_into('<I',huge,central+24,reader.MAX_BYTES+1)
        for data in (duplicate.getvalue(),bytes(encrypted),bytes(huge)):
            with patch.object(zipfile.ZipFile,'read',side_effect=AssertionError('preflight required')):
                with self.assertRaises(ValueError):reader.describe(data)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:entry=archive.getinfo('manifest.json')
        crc_bad=bytearray(raw);offset=entry.header_offset
        name_len,extra_len=struct.unpack_from('<HH',crc_bad,offset+26)
        start=offset+30+name_len+extra_len;crc_bad[start]^=1
        with self.assertRaises(zipfile.BadZipFile):reader.describe(bytes(crc_bad))
        # A truncated outer EOCD can expose an inner ZIP directory; either
        # ZIP parsing or the outer-family preflight must refuse it.
        for data in (raw[:10],raw[:-22]):
            with self.assertRaises((zipfile.BadZipFile, ValueError)):reader.describe(data)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input.zip';p.write_bytes(raw)
            with patch.object(reader,'MAX_BYTES',len(raw)-1),patch.object(reader,'describe',side_effect=AssertionError('parse forbidden')):
                # Invoke main directly so the patched bound is used before describe.
                import contextlib
                with patch.object(sys,'argv',['reader',str(p)]),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as e:
                    reader.main()
                self.assertEqual(e.exception.code,1)

    def test_bounded_input_output_and_unsupported_research_zip(self):
        raw=self.archives['collection_bundle']
        with patch.object(reader,'MAX_BYTES',len(raw)):reader.describe(raw)
        with patch.object(reader,'MAX_BYTES',len(raw)-1):
            with self.assertRaises(ValueError):reader.describe(raw)
        with patch.object(reader,'MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):reader.describe(raw)
        import research_bundle
        research=research_bundle.build_bundle((ROOT/'examples/review-demo.json').read_bytes())
        with self.assertRaises(ValueError):reader.describe(research)
        for value in (bytearray(raw),None,'zip'):
            with self.assertRaises(ValueError):reader.describe(value)

    def test_cli_json_text_exclusive_output_and_fixed_private_errors(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'PRIVATE_PATH.zip';source.write_bytes(self.archives['collection_bundle']);target=root/'output.json'
            r=run_cli('retained_bundle_describe.py',source,'--output',target)
            self.assertEqual((r.returncode,r.stderr),(0,b''))
            self.assertEqual(json.loads(target.read_bytes()),json.loads(r.stdout))
            before={p:p.read_bytes() for p in root.iterdir()}
            r=run_cli('retained_bundle_describe.py',source,'--output',target)
            self.assertEqual((r.returncode,r.stdout),(1,b''));self.assertNotIn(b'PRIVATE',r.stderr)
            self.assertEqual({p:p.read_bytes() for p in root.iterdir()},before)
            r=run_cli('retained_bundle_describe.py',source,'--text');self.assertEqual(r.returncode,0);self.assertIn(b'NOT_PERFORMED',r.stdout)
            real=subprocess.run([sys.executable,str(ROOT/'retained_bundle_describe.py'),str(source),'--text'],capture_output=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(real.returncode,real.stdout,real.stderr))
            source.write_bytes(b'PRIVATE_PAYLOAD')
            r=run_cli('retained_bundle_describe.py',source);self.assertEqual((r.returncode,r.stdout),(1,b''));self.assertNotIn(b'PRIVATE',r.stderr)
            self.assertEqual(run_cli('retained_bundle_describe.py').returncode,2)

    def test_documented_three_commands_for_all_seven_families(self):
        guide=(ROOT/'docs/RETAINED_BUNDLE_DESCRIBE.md').read_text(encoding='utf-8')
        commands=[line for line in guide.splitlines() if line.startswith('python retained_bundle_describe.py ')]
        self.assertEqual(len(commands),3)
        for name,raw in self.archives.items():
            with tempfile.TemporaryDirectory() as td:
                out=Path(td);source=out/'retained.zip';source.write_bytes(raw)
                before=source.read_bytes()
                for command in commands:
                    args=[part.replace('OUTPUT/',str(out)+os.sep) for part in command.split()[1:]]
                    result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(result.returncode,0,(name,result.stderr))
                    self.assertEqual(result.stderr,b'')
                    if '--text' in args:self.assertIn(b'UNVERIFIED',result.stdout)
                    else:self.assertEqual(json.loads(result.stdout)['verification'],'NOT_PERFORMED')
                saved=json.loads((out/'descriptor.json').read_bytes())
                self.assertEqual(saved['bundle_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual(source.read_bytes(),before)

    def test_all_existing_root_and_examples_unchanged(self):
        proof=json.loads((ROOT/'tests/retained_descriptor_prior_bytes.json').read_bytes())
        current={p.relative_to(ROOT).as_posix() for p in list(ROOT.glob('*.py'))+list((ROOT/'examples').rglob('*')) if p.is_file() and p.name not in ('amendment-before.json','amendment-after.json','manual-amendment.json')}
        self.assertEqual(current,set(proof)|{'retained_bundle_describe.py','amendment_links.py','amendment_intake.py','pubmed_partition.py','pubmed_partition_compare.py'})
        for name,digest in proof.items():self.assertEqual(hashlib.sha256(pre_amendment(name) if '/' not in name else pre_amendment_fixture(name)).hexdigest(),digest,name)

    def test_text_quotes_supplied_controls_and_descriptor_is_independent(self):
        raw=manifest_change(self.archives['collection_bundle'],lambda m:m.update(boundary='PRIVATE supplied\n\r\x1b\u202e text'))
        result=reader.describe(raw);text=reader.render_text(result)
        self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text);self.assertIn('PRIVATE',text)
        result['recorded_unverified']['files'].clear()
        self.assertTrue(reader.describe(raw)['recorded_unverified']['files'])


if __name__=='__main__':unittest.main()
