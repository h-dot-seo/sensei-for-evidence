from tests._native_archive_compat import prior_bytes as pre_native_archive
"""Explicit local Markdown coverage, never inferred execution or authority."""
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests._doc_conformance import (anchors,check_links,command_argv,dialect_issues,documents,execute_block,
    links,local_target,parse_only,parts,shell_blocks)
ROOT=Path(__file__).resolve().parents[1]


class DocumentationConformanceTests(unittest.TestCase):
    def test_all_supported_inline_links_and_anchors(self):
        count,failures=check_links(ROOT)
        self.assertGreater(count,1000)
        self.assertEqual(failures,[])

    def test_markdown_fences_code_percent_and_duplicate_heading(self):
        text='# Alpha `beta`!\n## 한글 제목\n## Same\n## Same\n## Same-1\n~~~sh\n[ignored](missing)\n~~~\n```text\n[also ignored](missing)\n```\n    [indented](missing)\n`[inline](missing)`\n[real](file%20name.md#same-1)\n'
        self.assertEqual(anchors(text),['alpha-beta','한글-제목','same','same-1','same-1-1'])
        self.assertEqual(links(text),['file%20name.md#same-1'])
        self.assertEqual(parts(text)[1][0],('sh','[ignored](missing)\n'))
        with self.assertRaises(ValueError):parts('```sh\nunterminated')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'docs').mkdir();source=root/'docs/x.md';source.write_text('')
            target=root/'file name.md';target.write_text('# Same\n# Same\n')
            self.assertEqual(local_target(root,source,'../file%20name.md#same-1'),(target.resolve(),'same-1'))
            for bad in ['../../outside','%2e%2e/%2e%2e/outside','/outside','bad%XX','bad%FF','a\\b','a%00b','a?query=1']:
                with self.subTest(bad=bad),self.assertRaises(ValueError):local_target(root,source,bad)
            for remote in ['https://example.invalid/x','mailto:nobody','//example.invalid/x']:
                self.assertIsNone(local_target(root,source,remote))
            source.write_text('[one](../file%20name.md#missing)\n[two](missing.md)\n')
            self.assertEqual(len(check_links(root)[1]),2)

    def test_unsupported_link_dialects_fail_instead_of_silent_coverage(self):
        for text in ['[ref]: file.md\n', '[label][ref]\n', '<!-- [hidden](file.md) -->\n',
                     '<a href="file.md">link</a>\n','[label](file(name).md)\n','Heading\n===\n']:
            with self.subTest(text=text):
                self.assertTrue(dialect_issues(text))
                with tempfile.TemporaryDirectory() as td:
                    root=Path(td);(root/'docs').mkdir();(root/'README.md').write_text(text)
                    self.assertEqual(check_links(root)[1][0][1],'unsupported Markdown dialect')
        self.assertEqual(dialect_issues('---\nname: value\n---\n# Heading\n'),[])
        self.assertEqual(dialect_issues('```text\n[label][ref]\n```\n`<a href="x">`\n'),[])

    def test_every_shell_block_has_an_exact_explicit_classification(self):
        blocks=shell_blocks(ROOT);registry=json.loads((ROOT/'tests/doc_block_registry.json').read_bytes())
        self.assertEqual(set(blocks),set(registry))
        self.assertEqual(len(blocks),200)
        for key,entry in registry.items():
            with self.subTest(block=key):
                self.assertEqual(entry['sha256'],blocks[key]['sha256'])
                self.assertIn(entry['classification'],{'run','parse-only','covered-by','exempt'})
                self.assertTrue(entry['reason'].strip())
                if entry['classification'] in ('run','parse-only'):
                    self.assertEqual(command_argv(blocks[key]['body']),entry['argv'])
                if entry['classification']=='covered-by':
                    module,cls,method=entry['test'].rsplit('.',2)
                    obj=importlib.import_module(module)
                    source=Path(obj.__file__).read_bytes()
                    self.assertEqual(hashlib.sha256(source).hexdigest(),entry['test_source_sha256'])
                    self.assertTrue(callable(getattr(getattr(obj,cls),method)))
                    # Exact test source and real guide reference are pinned, not just a filename search claim.
                    self.assertIn(key.split('::')[0].split('/')[-1],source.decode())
                    self.assertIn('read_text',source.decode())
                if key.startswith(('VALIDATION.md::','docs/SCALE_ENVELOPE.md::')):
                    self.assertEqual(entry['classification'],'exempt')

    def test_reviewed_synthetic_blocks_execute_without_shell(self):
        registry=json.loads((ROOT/'tests/doc_block_registry.json').read_bytes());blocks=shell_blocks(ROOT)
        count=0
        for key,entry in registry.items():
            if entry['classification']!='run':continue
            with self.subTest(block=key),tempfile.TemporaryDirectory(prefix='sensei documented argv ') as td:
                results=execute_block(ROOT,blocks[key]['body'],entry,Path(td));count+=len(results)
        self.assertEqual(count,77)

    def test_parse_only_stops_before_reading_or_creating_bundle(self):
        registry=json.loads((ROOT/'tests/doc_block_registry.json').read_bytes());blocks=shell_blocks(ROOT)
        import research_bundle
        key='docs/RESEARCH_ZIP_SAFETY.md::0'
        with patch.object(research_bundle,'create',side_effect=AssertionError('must not execute')),patch.object(research_bundle,'verify',side_effect=AssertionError('must not execute')):
            self.assertEqual(parse_only(blocks[key]['body'],registry[key]),2)
        bad=copy.deepcopy(registry[key]);bad['argv'][0].append('--nonexistent-option')
        body='\n'.join('python '+' '.join(a) for a in bad['argv'])+'\n'
        with patch('sys.stderr'),self.assertRaises(SystemExit) as cm:parse_only(body,bad)
        self.assertEqual(cm.exception.code,2)

    def test_no_shell_unapproved_scripts_or_unmapped_paths(self):
        for body in ['python x.py; touch y','python x.py > file','python x.py | other','python x.py $(whoami)','python -m tests.scale_probe --run','sh x.sh']:
            with self.subTest(body=body),self.assertRaises(ValueError):command_argv(body)
        entry=dict(argv=[['research_status.py','/outside/private.json']],scratch={},returncodes=[0])
        with tempfile.TemporaryDirectory() as td,patch('subprocess.run',side_effect=AssertionError('must not run')):
            with self.assertRaises(ValueError):execute_block(ROOT,'python research_status.py /outside/private.json\n',entry,Path(td))
            entry['argv']=[['pubmed_fetch.py','examples/review-demo.json']]
            with self.assertRaises(ValueError):execute_block(ROOT,'python pubmed_fetch.py examples/review-demo.json\n',entry,Path(td))

    def test_original_sources_examples_workflows_and_block_bytes_preserved(self):
        proof=json.loads((ROOT/'tests/doc_conformance_prior_bytes.json').read_bytes())
        for name,digest in proof['files'].items():
            self.assertEqual(hashlib.sha256(pre_native_archive(name) if '/' not in name else (ROOT/name).read_bytes()).hexdigest(),digest,name)
        current=shell_blocks(ROOT)
        self.assertEqual({key:current[key]['sha256'] for key in proof['blocks']},proof['blocks'])
        self.assertEqual(set(current)-set(proof['blocks']),{'docs/NATIVE_CONTINUATION_ARCHIVE.md::'+str(i) for i in range(3)})
        history=(ROOT/'docs/VALIDATION_HISTORY.md').read_bytes()
        proof=proof['history_prefix'];prefix=history[:proof['new_bytes']]
        self.assertEqual(hashlib.sha256(prefix).hexdigest(),proof['new_sha256'])
        restored=prefix;shift=0
        for edit in proof['edits']:
            offset=edit['offset']
            self.assertEqual(restored[offset:offset+len(edit['new'])],edit['new'].encode())
            restored=restored[:offset]+edit['old'].encode()+restored[offset+len(edit['new']):]
        self.assertEqual(len(restored),proof['old_bytes'])
        self.assertEqual(hashlib.sha256(restored).hexdigest(),proof['old_sha256'])
