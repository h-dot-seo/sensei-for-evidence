"""Canonical archive envelopes, bounded input and unchanged payload derivation."""
import copy
import hashlib
import inspect
import io
import json
import re
import shlex
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

import archive_safety
import research_bundle as bundle
from tests._canonical_zip import pack
from tests._question_compat import prior_builder_source

ROOT=Path(__file__).resolve().parents[1]

class ResearchZipSafetyTests(unittest.TestCase):
    def setUp(self):
        self.protocol=(ROOT/'examples/report-protocol.json').read_bytes()
        self.raw=bundle.build_bundle(self.protocol)
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            self.entries={n:archive.read(n) for n in archive.namelist()}
            self.total=sum(e.file_size for e in archive.infolist())

    def repack(self, *, overrides=None, compression=zipfile.ZIP_STORED, comment=b'', duplicate=False, reverse=False):
        out=io.BytesIO();overrides=overrides or {}
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(out,'w',compression=compression) as archive:
                rows=sorted(self.entries.items(),reverse=reverse)
                if duplicate:rows.append(rows[0])
                for name,data in rows:
                    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100600<<16;info.compress_type=compression
                    for key,value in overrides.items():setattr(info,key,value)
                    archive.writestr(info,data)
                archive.comment=comment
        return out.getvalue()

    def test_actual_previous_build_bytes_identical_with_same_recorded_engine(self):
        data=json.loads((ROOT/'tests/research_zip_previous_baselines.json').read_bytes())
        self.assertEqual(hashlib.sha256(prior_builder_source(bundle).encode()).hexdigest(),data['build_function_sha256'])
        current=bundle.engine_hashes()
        self.assertEqual(set(current),set(data['engine_sha256'])|{'archive_safety.py','question_links.py','output_disclosure_links.py','amendment_links.py'})
        for name,expected in data['engine_sha256'].items():
            if name in ('prisma_reports.py','screening_decision.py','json_io.py'):
                from tests._cli_input_compat import prior_bytes as pre_cli_bytes
                self.assertEqual(hashlib.sha256(pre_cli_bytes(name)).hexdigest(),expected,name)
            elif name not in ('research_bundle.py','evidence_workflow.py','adapter_integrity.py','bibliographic_integrity.py'):self.assertEqual(current[name],expected,name)
            elif name!='research_bundle.py':
                prior=json.loads((ROOT/'tests/question_legacy_baselines.json').read_bytes())['prior_source_sha256']
                self.assertEqual(prior[name],expected,name)
        with patch.object(bundle,'engine_hashes',return_value=copy.deepcopy(data['engine_sha256'])):
            for case in data['cases']:
                raw=(ROOT/case['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),case['input_sha256'])
                actual=bundle.build_bundle(raw)
                self.assertEqual(len(actual),case['archive_bytes']);self.assertEqual(hashlib.sha256(actual).hexdigest(),case['archive_sha256'])
                self.assertTrue(bundle.verify_bytes(actual)['valid'])

    def test_canonical_repack_is_byte_identical_and_allowed(self):
        self.assertEqual(self.repack(),self.raw);self.assertEqual(pack(self.entries),self.raw)
        self.assertTrue(bundle.verify_bytes(self.repack())['valid'])
        with patch.object(zipfile.ZipFile,'extract',side_effect=AssertionError('no extraction')),patch.object(zipfile.ZipFile,'extractall',side_effect=AssertionError('no extraction')):
            self.assertTrue(bundle.verify(io.BytesIO(self.raw))['valid'])

    def test_path_bytesio_partial_read_bounds_and_position(self):
        class Partial(io.BytesIO):
            def read(self,n=-1):
                self.requests.append(n)
                return super().read(min(n,7))
        stream=Partial(self.raw);stream.requests=[];stream.seek(9)
        self.assertTrue(bundle.verify(stream)['valid']);self.assertEqual(stream.tell(),9);self.assertFalse(stream.closed)
        self.assertTrue(all(0<n<=65_536 for n in stream.requests))
        self.assertEqual(bundle.ZIP_HEADER_OVERHEAD,732)
        self.assertEqual(len(self.raw),self.total+bundle.ZIP_HEADER_OVERHEAD)
        with patch.object(bundle,'MAX_BUNDLE_BYTES',self.total):
            self.assertTrue(bundle.verify(stream)['valid']);self.assertEqual(bundle.build_bundle(self.protocol),self.raw)
        with patch.object(bundle,'MAX_BUNDLE_BYTES',self.total-1):
            with self.assertRaisesRegex(ValueError,'size limit'):bundle.verify(stream)
            with self.assertRaisesRegex(ValueError,'size limit'):bundle.build_bundle(self.protocol)
        self.assertEqual(stream.tell(),9)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'input.zip';path.write_bytes(self.raw)
            self.assertTrue(bundle.verify(path)['valid'])
            with patch.object(bundle,'MAX_BUNDLE_BYTES',1),self.assertRaisesRegex(ValueError,'size limit'):bundle.verify(path)
        for bad in (io.StringIO('text'),b'not a path',None):
            with self.assertRaises((ValueError,AttributeError)):bundle.verify(bad)

    def test_bounded_create_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'protocol.json';p.write_bytes(b'x'*9);out=Path(td)/'never.zip'
            with patch.object(bundle,'MAX_BUNDLE_BYTES',8),self.assertRaisesRegex(ValueError,'size limit'):bundle.create(p,out)
            self.assertFalse(out.exists());self.assertEqual(p.read_bytes(),b'x'*9)

    def test_noncanonical_metadata_order_and_trailing_rejected(self):
        cases=[self.repack(comment=b'archive comment'),self.repack(reverse=True),
            self.repack(overrides=dict(date_time=(2020,1,1,0,0,0))),
            self.repack(overrides=dict(comment=b'entry comment')),
            self.repack(overrides=dict(extra=b'\x99\x99\x00\x00')),
            b'prefix'+self.raw,self.raw+b'trailing',self.raw[:-1],b'not ZIP',b'']
        for raw in cases:
            with self.subTest(size=len(raw)),self.assertRaises((ValueError,zipfile.BadZipFile)):bundle.verify_bytes(raw)
        for raw in (None,bytearray(self.raw),'text'):
            with self.assertRaises(ValueError):bundle.verify_bytes(raw)

    def test_preflight_compression_type_paths_duplicates_size_and_encryption_before_payload(self):
        encrypted=bytearray(self.raw);local=encrypted.index(b'PK\x03\x04');central=encrypted.index(b'PK\x01\x02')
        for offset in (local+6,central+8):struct.pack_into('<H',encrypted,offset,struct.unpack_from('<H',encrypted,offset)[0]|1)
        huge=bytearray(self.raw)
        for offset in (local+18,local+22,central+20,central+24):struct.pack_into('<I',huge,offset,0xffffffff)
        attacks=[self.repack(compression=zipfile.ZIP_DEFLATED),self.repack(duplicate=True),
            self.repack(overrides=dict(create_system=0)),
            self.repack(overrides=dict(external_attr=(stat.S_IFLNK|0o777)<<16)),bytes(encrypted),bytes(huge)]
        for name in ('../outside','/absolute','directory/','unexpected'):
            entries=dict(self.entries);entries[name]=entries.pop('summary.md');attacks.append(pack(entries))
        with patch.object(zipfile.ZipFile,'read',side_effect=AssertionError('payload must not be read')):
            for raw in attacks:
                with self.subTest(size=len(raw)),self.assertRaises(ValueError):bundle.verify_bytes(raw)

    def test_crc_size_mismatch_eocd_and_manifest_extras_fail(self):
        crc=bytearray(self.raw);local=crc.index(b'PK\x03\x04');central=crc.index(b'PK\x01\x02')
        for offset in (local+14,central+16):struct.pack_into('<I',crc,offset,0)
        with self.assertRaises(zipfile.BadZipFile):bundle.verify_bytes(bytes(crc))
        mismatch=bytearray(self.raw);struct.pack_into('<I',mismatch,central+20,1)
        with self.assertRaises(ValueError):bundle.verify_bytes(bytes(mismatch))
        eocd=bytearray(self.raw);struct.pack_into('<H',eocd,len(eocd)-2,100)
        with self.assertRaises((ValueError,zipfile.BadZipFile)):bundle.verify_bytes(bytes(eocd))
        entries=dict(self.entries);manifest=json.loads(entries['manifest.json']);manifest['unverified_extra']='not canonical';entries['manifest.json']=json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError,'canonical'):bundle.verify_bytes(pack(entries))

    def test_documented_create_verify_commands(self):
        doc=(ROOT/'docs/RESEARCH_ZIP_SAFETY.md').read_text(encoding='utf-8')
        commands=[line for block in re.findall(r'```sh\n(.*?)```',doc,re.S) for line in block.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),2)
        with tempfile.TemporaryDirectory() as td:
            work=Path(td);(work/'examples').mkdir();source=work/'examples/report-protocol.json';source.write_bytes(self.protocol)
            for line in commands:
                args=shlex.split(line)[1:];args[0]=str(ROOT/args[0])
                r=subprocess.run([sys.executable,'-B',*args],cwd=work,capture_output=True,timeout=30)
                self.assertEqual((r.returncode,r.stderr),(0,b''),line)
            self.assertEqual(source.read_bytes(),self.protocol)
            self.assertEqual((work/'canonical-research.zip').read_bytes(),self.raw)

    def test_actual_cli_invalid_zip_has_no_traceback_or_stdout(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'bad.zip'
            for raw in (self.raw+b'trailing',self.repack(compression=zipfile.ZIP_DEFLATED),self.raw[:-1],b''):
                path.write_bytes(raw)
                r=subprocess.run([sys.executable,str(ROOT/'research_bundle.py'),'verify',str(path)],capture_output=True,timeout=30)
                self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b'');self.assertNotIn(b'Traceback',r.stderr)

if __name__=='__main__':unittest.main()
