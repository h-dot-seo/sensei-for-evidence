"""Explicit retained continuation RIS; no identity/review/gate inference."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import native_collection_bundle as bundle
import ris_continuation_intake as continuation
import ris_continuation_parser as parser
import research_bundle
import retained_bundle_describe
from tests._dispatcher_search_compat import before_list_search
from json_io import canonical_json_bytes
import tests.test_native_collection_bundle as native_cases
encoded=native_cases.encoded

ROOT=Path(__file__).resolve().parents[1]


class NativeContinuationArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture=native_cases.NativeCollectionBundleTests();self.fixture.setUp()
        self.base=self.fixture.base
        self.raw=b'\xef\xbb\xbf'+(ROOT/'examples/dialects/continuation.ris').read_bytes().replace(b'\n',b'\r\n')
        self.wrapper=continuation.prepare(self.base,self.raw,'local-primary','supplied synthetic time',dialect=parser.DIALECT)
        self.protocol=self.fixture.imported(self.base,self.wrapper['csv_intake'],'fictional-continuation')
        self.bindings=[dict(import_index=0,format='ris_continuation',artifact=self.wrapper)]

    def test_exact_original_wrapper_protocol_and_ordinary_research_zip(self):
        before=canonical_json_bytes([self.base,self.wrapper,self.protocol,self.bindings])
        with patch('socket.socket',side_effect=AssertionError('no network')):
            raw=bundle.build_bundle(encoded(self.protocol),self.bindings)
            result=bundle.verify_bundle(raw)
        self.assertTrue(result['valid']);self.assertEqual(result['bound_wrapper_formats'],{'ris':0,'nbib':0,'nbib_batch':0,'ris_continuation':1})
        self.assertEqual(result['conclusion_readiness'],'NOT_READY');self.assertEqual(result['review_status'],'NOT_PERFORMED')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(archive.read('native/import-000000/source-000000.ris'),self.raw)
            self.assertEqual(json.loads(archive.read('native/import-000000.json')),self.wrapper)
            self.assertEqual(archive.read('research.zip'),research_bundle.build_bundle(encoded(self.protocol)))
        self.assertEqual(canonical_json_bytes([self.base,self.wrapper,self.protocol,self.bindings]),before)

    def test_closed_format_separate_verifier_and_exact_import_association(self):
        for kind in ['ris','nbib','nbib_batch',parser.DIALECT,'auto','RIS_CONTINUATION']:
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                bundle.build_bundle(encoded(self.protocol),[dict(self.bindings[0],format=kind)])
        for change in ['wrong_index','duplicate','tampered_wrapper','wrong_source']:
            bindings=copy.deepcopy(self.bindings)
            if change=='wrong_index':bindings[0]['import_index']=1
            elif change=='duplicate':bindings.append(copy.deepcopy(bindings[0]))
            elif change=='tampered_wrapper':bindings[0]['artifact']['review_status']='APPROVED'
            else:bindings[0]['artifact']['source_export']['text']+='changed'
            with self.subTest(change=change),self.assertRaises(ValueError):bundle.build_bundle(encoded(self.protocol),bindings)
        with self.assertRaises(ValueError):bundle.build_bundle(encoded(self.protocol),[])

    def test_native_hash_expansion_not_global_engine_or_parser_change(self):
        expected=set(research_bundle.ENGINE_FILES)
        import nbib_batch_intake,ris_intake
        expected|=set(nbib_batch_intake.implementation_hashes())|set(ris_intake.implementation_hashes())|set(continuation.implementation_hashes())|{'native_collection_bundle.py'}
        self.assertEqual(set(bundle.implementation_hashes()),expected)
        self.assertNotIn('ris_continuation_intake.py',research_bundle.ENGINE_FILES)
        prior=json.loads((ROOT/'tests/native_continuation_prior_sources.json').read_bytes())
        changes=json.loads((ROOT/'tests/native_continuation_source_changes.json').read_bytes())
        self.assertEqual(set(changes),{'native_collection_bundle.py','ris_continuation_intake.py','review_handoff.py'})
        for name,digest in prior.items():
            actual=before_list_search(name, (ROOT/name).read_bytes())
            if name in changes:
                self.assertEqual(actual,changes[name]['new'].encode());actual=changes[name]['old'].encode()
            self.assertEqual(hashlib.sha256(actual).hexdigest(),digest,name)

    def test_actual_prior_implementation_replays_old_records_current_refuses(self):
        changes=json.loads((ROOT/'tests/native_continuation_source_changes.json').read_bytes())
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for source in ROOT.glob('*.py'):shutil.copyfile(source,root/source.name)
            for name,row in changes.items():(root/name).write_bytes(row['old'].encode())
            def load(name):
                spec=importlib.util.spec_from_file_location('prior_'+name,root/(name+'.py'))
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
            old_bundle=load('native_collection_bundle');old_cont=load('ris_continuation_intake')
            old_handoff=load('review_handoff')
            import review_handoff
            before=old_handoff.handoff(self.fixture.protocol);after=review_handoff.handoff(self.fixture.protocol)
            self.assertEqual(after['engine_sha256']['review_handoff.py'],hashlib.sha256((ROOT/'review_handoff.py').read_bytes()).hexdigest())
            after['engine_sha256']['review_handoff.py']=before['engine_sha256']['review_handoff.py']
            old_row=next(row for row in before['supplied_input_workflows'] if row['workflow_id']=='native_collection')
            new_row=next(row for row in after['supplied_input_workflows'] if row['workflow_id']=='native_collection')
            self.assertNotEqual(new_row['boundary'],old_row['boundary'])
            new_boundary=new_row['boundary'];new_row['boundary']=old_row['boundary']
            self.assertEqual(after,before)
            actual=review_handoff.handoff(self.fixture.protocol)
            from json_io import quoted_display
            old_text=old_handoff.render_text(before);new_text=review_handoff.render_text(actual)
            self.assertEqual(new_text.count(quoted_display(new_boundary)),1)
            self.assertEqual(new_text.replace(quoted_display(new_boundary),quoted_display(old_row['boundary']),1),old_text)
            old_wrapper=old_cont.prepare(self.base,self.raw,'local-primary','supplied synthetic time',dialect=parser.DIALECT)
            self.assertTrue(old_cont.verify(old_wrapper)['valid'])
            self.assertEqual(old_wrapper['csv_intake'],self.wrapper['csv_intake'])
            with self.assertRaisesRegex(ValueError,'implementation bytes differ'):continuation.verify(old_wrapper)
            old_raw=old_bundle.build_bundle(encoded(self.fixture.protocol),self.fixture.bindings)
            self.assertTrue(old_bundle.verify_bundle(old_raw)['valid'])
            described=retained_bundle_describe.describe(old_raw)
            self.assertEqual(described['implementation_match'],'DIFFERS')
            self.assertEqual(described['verification'],'NOT_PERFORMED')
            self.assertEqual(described['bundle_sha256'],hashlib.sha256(old_raw).hexdigest())
            self.assertEqual(described['differing_engine_files'],['native_collection_bundle.py','ris_continuation_intake.py','ris_continuation_parser.py'])
            with self.assertRaisesRegex(ValueError,'implementation bytes differ'):bundle.verify_bundle(old_raw)
            new_raw=bundle.build_bundle(encoded(self.fixture.protocol),self.fixture.bindings)
            old_summary=old_bundle.verify_bundle(old_raw);new_summary=bundle.verify_bundle(new_raw)
            for key in ['total_imports','bound_native_wrappers','bound_wrapper_formats','bound_native_sources','covered_import_indices','uncovered_import_indices','review_status','conclusion_readiness']:
                self.assertEqual(old_summary[key],new_summary[key],key)
            with zipfile.ZipFile(io.BytesIO(old_raw)) as oldzip,zipfile.ZipFile(io.BytesIO(new_raw)) as newzip:
                self.assertEqual(oldzip.read('research.zip'),newzip.read('research.zip'))
                self.assertEqual(oldzip.read('native/import-000000/source-000000.nbib'),newzip.read('native/import-000000/source-000000.nbib'))
            # Old code must never be loaded from an archive. These sources are explicit test evidence only.
            self.assertEqual(hashlib.sha256((root/'native_collection_bundle.py').read_bytes()).hexdigest(),hashlib.sha256(changes['native_collection_bundle.py']['old'].encode()).hexdigest())

    def test_eight_documented_commands_with_separate_fictional_human_inputs(self):
        import bibliographic_review
        commands=re.findall(r'^python (.+)$',(ROOT/'docs/NATIVE_CONTINUATION_ARCHIVE.md').read_text(encoding='utf-8'),re.M)
        self.assertEqual(len(commands),8)
        original={p:p.read_bytes() for p in [ROOT/'examples/bibliographic-base.json',ROOT/'examples/dialects/continuation.ris']}
        with tempfile.TemporaryDirectory(prefix='native continuation guide ') as td:
            out=Path(td)
            for i,command in enumerate(commands):
                if i==3:
                    choices=json.loads((out/'blank-choices.json').read_bytes())
                    for n,row in enumerate(choices['resolutions']):row.update(disposition='new_record',record_id='fictional-'+str(n),rationale='Synthetic test supplies identity choice')
                    (out/'manual-choices.json').write_bytes(encoded(choices))
                if i==4:
                    review=json.loads((out/'target-review.json').read_bytes())
                    review['review'].update(reviewer='Fictional test reviewer',reviewed_at='2026-11-04',rationale='Explicit fictional software check',decision='import_for_screening')
                    (out/'manual-review.json').write_bytes(encoded(review))
                args=[a.replace('OUTPUT/',str(out)+'/') for a in shlex.split(command)]
                result=subprocess.run([sys.executable,*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
                self.assertEqual((result.returncode,result.stderr),(0,b''),(i,result.stderr))
            protocol=json.loads((out/'collected.json').read_bytes())
            self.assertEqual(protocol['bibliographic_imports']['imports'][0]['intake']['source_export']['text'],json.loads((out/'intake.json').read_bytes())['source_export']['text'])
            archive=(out/'continuation-collection.zip').read_bytes()
            self.assertTrue(bundle.verify_bundle(archive)['valid'])
            with zipfile.ZipFile(io.BytesIO(archive)) as z:self.assertEqual(z.read('native/import-000000/source-000000.ris'),original[ROOT/'examples/dialects/continuation.ris'])
            # Wrong flag is never an alias for the declared continuation verifier.
            result=subprocess.run([sys.executable,'native_collection_bundle.py','create',str(out/'collected.json'),str(out/'wrong.zip'),'--ris','0='+str(out/'continuation.json')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
            self.assertEqual(result.returncode,1);self.assertFalse((out/'wrong.zip').exists())
        for path,raw in original.items():self.assertEqual(path.read_bytes(),raw)
