"""Recorded-context reader is distinct from hash verification and research replay."""
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import research_bundle as engine
import research_bundle_describe as reader

ROOT=Path(__file__).resolve().parents[1]


def repack(raw,transform=None,compression=zipfile.ZIP_STORED,extra=False):
    target=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source,zipfile.ZipFile(target,'w') as out:
        for item in source.infolist():
            data=source.read(item.filename)
            if transform: item,data=transform(item,data)
            item.compress_type=compression
            out.writestr(item,data)
        if extra:out.writestr('extra',b'x')
    return target.getvalue()


class BundleDescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=(ROOT/'examples/review-demo.json').read_bytes()
        cls.raw=engine.build_bundle(cls.protocol)

    def mutate_json(self,name,change):
        def transform(item,data):
            if item.filename==name:
                obj=json.loads(data);change(obj);data=json.dumps(obj).encode()
            return item,data
        return repack(self.raw,transform)

    def test_actual_bundle_values_and_hash_scopes(self):
        result=reader.describe(self.raw)
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:
            research=json.loads(archive.read('research.json'))
            manifest=json.loads(archive.read('manifest.json'))
        self.assertEqual(result['recorded_unverified']['flow'],research['flow'])
        self.assertEqual(result['recorded_unverified']['gates_sha256'],research['readiness']['gates_sha256'])
        self.assertEqual(result['recorded_unverified']['open_gate_ids'],research['readiness']['open_gate_ids'])
        self.assertEqual(result['manifest']['input_sha256'],manifest['input_sha256'])
        self.assertEqual(result['bundle_sha256'],hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(result['implementation_match'],'MATCH')
        for key in ('verification','payload_hash_verification','derivation_replay'):
            self.assertEqual(result[key],'NOT_PERFORMED')

    def test_changed_recorded_flow_is_not_verified_or_replayed(self):
        altered=self.mutate_json('research.json',lambda d:d.update(flow={'recorded_untrusted':999}))
        with patch.object(engine,'run',side_effect=AssertionError('must not run')):
            report=reader.describe(altered)
        self.assertEqual(report['recorded_unverified']['flow'],{'recorded_untrusted':999})
        self.assertEqual(report['verification'],'NOT_PERFORMED')
        self.assertEqual(report['conclusion_readiness'],'NOT_READY')

    def test_missing_readiness_and_flow_remain_null(self):
        raw=self.mutate_json('research.json',lambda d:(d.pop('readiness',None),d.pop('flow',None)))
        self.assertEqual(reader.describe(raw)['recorded_unverified'],dict(flow=None,gates_sha256=None,open_gate_ids=None))

    def test_differing_extra_and_missing_engine_files(self):
        def mutate(d):
            d['engine_sha256'].pop('research_bundle.py')
            d['engine_sha256']['offline_adapter.py']='0'*64
            d['engine_sha256']['old_extra.py']='1'*64
        result=reader.describe(self.mutate_json('manifest.json',mutate))
        self.assertEqual(result['implementation_match'],'DIFFERS')
        self.assertEqual(result['differing_engine_files'],['offline_adapter.py','old_extra.py','research_bundle.py'])

    def test_entry_schema_json_and_type_rejection(self):
        bad=[b'not zip',repack(self.raw,compression=zipfile.ZIP_DEFLATED),repack(self.raw,extra=True),
             self.mutate_json('manifest.json',lambda d:d.update(schema_version=1)),
             self.mutate_json('manifest.json',lambda d:d.update(schema_version=True)),
             self.mutate_json('manifest.json',lambda d:d.update(mode='other_bundle')),
             self.mutate_json('manifest.json',lambda d:d['engine_sha256'].update({'../unsafe.py':'0'*64})),
             self.mutate_json('research.json',lambda d:d.update(flow=[])),
             self.mutate_json('research.json',lambda d:d.update(readiness={'open_gate_ids':0}))]
        def untrusted_creator(item,data):item.create_system=0;return item,data
        bad.append(repack(self.raw,untrusted_creator))
        def duplicate_json(item,data):return item,(b'{"x":1,"x":2}' if item.filename=='research.json' else data)
        bad.append(repack(self.raw,duplicate_json))
        for raw in bad:
            with self.subTest(size=len(raw)):
                with self.assertRaises((ValueError,zipfile.BadZipFile)):reader.describe(raw)

    def test_byte_bounds_and_text_escaping(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as archive:total=sum(i.file_size for i in archive.infolist())
        with patch.object(reader,'MAX_BUNDLE_BYTES',total):reader.describe(self.raw)
        with patch.object(reader,'MAX_BUNDLE_BYTES',total-1):
            with self.assertRaises(ValueError):reader.describe(self.raw)
        with patch.object(reader,'MAX_ARCHIVE_BYTES',len(self.raw)-1):
            with self.assertRaises(ValueError):reader.describe(self.raw)
        raw=self.mutate_json('protocol.json',lambda d:d.update(question='secret\n\x1b[31m\u202e'))
        text=reader.render_text(reader.describe(raw))
        self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        self.assertIn('\\n',text);self.assertIn('Verification: NOT_PERFORMED',text)

    def test_guide_commands_verbatim_and_cli_failure_no_echo(self):
        guide=(ROOT/'docs/RESEARCH_BUNDLE_DESCRIBE.md').read_text(encoding='utf-8')
        commands=[line for line in guide.splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),3)
        with tempfile.TemporaryDirectory(prefix='private sentinel ') as tmp:
            for command in commands:
                args=[sys.executable if token=='python' else str(Path(tmp)/token[len('OUTPUT/'):]) if token.startswith('OUTPUT/') else token for token in shlex.split(command)]
                result=subprocess.run(args,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
                if 'research_bundle_describe.py' in args:self.assertIn(b'NOT_PERFORMED',result.stdout)
            bad=Path(tmp)/'private-sentinel.zip';bad.write_bytes(b'private-secret')
            result=subprocess.run([sys.executable,str(ROOT/'research_bundle_describe.py'),str(bad)],capture_output=True)
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')
            for marker in (b'Traceback',b'private-secret',str(bad).encode()):self.assertNotIn(marker,result.stderr)
