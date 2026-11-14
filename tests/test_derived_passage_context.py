"""Declared original/derived context never authenticates a conversion or reads the original."""
import copy
import json
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch

import artifact_review as ar
import result_passage_check as pc
from tests import test_result_passage_check as fixtures


class DerivedPassageTests(unittest.TestCase):
    rebind = fixtures.PassageTests.rebind
    reject = fixtures.PassageTests.reject
    catalog = fixtures.PassageTests.catalog

    def setUp(self):
        fixtures.PassageTests.setUp(self)
        origin=copy.deepcopy(self.p['report_sources'][0])
        origin.update(source_id='original-document',document_version='Supplied original representation',
                      document_sha256='a'*64,source_locator='synthetic://never-open-original')
        self.p['report_sources'].append(origin)
        self.m['schema_version']=2
        self.m['sources'][0]['derived_from']=dict(source_id=origin['source_id'],source_descriptor_sha256=pc.digest(origin))
        self.rebind()

    def test_same_report_context_without_original_access(self):
        if not ar.secure_open_supported():self.skipTest('POSIX secure traversal unavailable')
        before=copy.deepcopy((self.p,self.c,self.m))
        with patch.object(pc,'_read_source',wraps=pc._read_source) as read:
            result=pc.check_passages(self.p,self.c,self.m,self.root)
        self.assertEqual(read.call_count,1)
        self.assertEqual(result['schema_version'],2)
        context=result['sources'][0]['conversion_context']
        self.assertEqual(context['declared_origin'],self.p['report_sources'][-1])
        self.assertEqual(context['conversion_verification'],'NOT_PERFORMED')
        self.assertEqual(context['original_bytes_check'],'NOT_PERFORMED')
        self.assertTrue(result['all_requested_passages_match'])
        self.assertEqual((self.p,self.c,self.m),before)
        self.assertIn('NOT_PERFORMED',pc.render_text(result))

    def test_reference_failures_before_any_source_access(self):
        mutations=[lambda m:m['sources'][0]['derived_from'].update(source_id='absent'),
                   lambda m:m['sources'][0]['derived_from'].update(source_id='source-main'),
                   lambda m:m['sources'][0]['derived_from'].update(source_descriptor_sha256='0'*64),
                   lambda m:m['sources'][0]['derived_from'].update(document_sha256='a'*64),
                   lambda m:m['sources'][0].update(derived_from=[]),
                   lambda m:m['sources'][0].pop('derived_from')]
        for mutate in mutations:
            m=copy.deepcopy(self.m);mutate(m)
            self.reject(m=m)
        for change in ({'document_sha256':None},{'report_id':'report-other'}):
            p=copy.deepcopy(self.p);p['report_sources'][-1].update(change)
            m=copy.deepcopy(self.m);m['protocol_sha256']=pc.digest(p)
            m['sources'][0]['derived_from']['source_descriptor_sha256']=pc.digest(p['report_sources'][-1])
            self.reject(p=p,m=m)

    def test_legacy_shape_remains_strict_and_v2_null_is_explicit(self):
        legacy=copy.deepcopy(self.m);legacy['schema_version']=1
        self.reject(m=legacy)
        self.m['sources'][0]['derived_from']=None
        if not ar.secure_open_supported():self.skipTest('POSIX secure traversal unavailable')
        result=self.catalog()
        self.assertIsNone(result['sources'][0]['conversion_context'])
        legacy['sources'][0].pop('derived_from')
        old=pc.catalog(self.p,self.c,legacy,self.root)
        self.assertEqual(old['schema_version'],1)
        self.assertNotIn('conversion_context',old['sources'][0])

    def test_unsupported_platform_still_fails_closed(self):
        with patch.object(pc,'secure_open_supported',return_value=False),patch.object(pc,'open_root',side_effect=AssertionError('must not open')):
            with self.assertRaises((ValueError,pc.PassageCheckError)):
                pc.catalog(self.p,self.c,self.m,self.root)



    def test_guide_commands_and_platform_contract(self):
        root=Path(pc.__file__).resolve().parent
        commands=[line for line in (root/'docs/DERIVED_TEXT_CONTEXT.md').read_text(encoding='utf-8').splitlines() if line.startswith('python ')]
        self.assertEqual(len(commands),2)
        for command in commands:
            args=[sys.executable if x=='python' else str(self.root/x[len('OUTPUT/'):]) if x.startswith('OUTPUT/') else x for x in shlex.split(command)]
            process=subprocess.run(args,cwd=root,capture_output=True)
            if ar.secure_open_supported():
                self.assertEqual(process.returncode,0,process.stderr)
                output=Path(args[args.index('--output')+1])
                result=json.loads(output.read_bytes())
                self.assertEqual(result['schema_version'],2)
                self.assertEqual(result['sources'][0]['conversion_context']['conversion_verification'],'NOT_PERFORMED')
            else:
                self.assertEqual(process.returncode,1)
                self.assertFalse(Path(args[args.index('--output')+1]).exists())
