"""Seven existing preflights share mechanics, not new acceptance or security claims."""
import ast
import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import re
import stat
import types
import unittest
from unittest.mock import patch
import zipfile

import archive_safety
import research_bundle
from tests._archive_preflight_compat import prior_bytes

ROOT=Path(__file__).resolve().parents[1]
NAMES=('collection_bundle','batch_collection_bundle','native_collection_bundle','report_transition_bundle',
       'extraction_transition_bundle','appraisal_transition_bundle','work_transition_bundle')
CHANGED={name+'.py' for name in NAMES}|{'archive_safety.py'}
CLASSES=('CollectionBundleTests','BatchCollectionBundleTests','NativeCollectionBundleTests','ReportTransitionBundleTests',
         'ExtractionTransitionBundleTests','AppraisalTransitionBundleTests','WorkTransitionBundleTests')


def old_module(name):
    module=types.ModuleType('prior_'+name);module.__file__=str(ROOT/(name+'.py'))
    exec(compile(prior_bytes(name+'.py'),module.__file__,'exec'),module.__dict__)
    return module


def entry(name,**overrides):
    value=dict(filename=name,file_size=3,compress_size=3,flag_bits=0,compress_type=zipfile.ZIP_STORED,
               create_system=3,external_attr=0o100600<<16,directory=False)
    value.update(overrides);return value


class ArchivePreflightSharedTests(unittest.TestCase):
    def observe(self,module,rows,limit=None,size_error=False):
        events=[]
        class Member:
            def __init__(self,row):self.__dict__.update(row)
            def is_dir(self):events.append(('is_dir',self.filename));return self.directory
        class Archive:
            def infolist(self):events.append(('infolist',));return [Member(row) for row in rows]
            def read(self,*args):raise AssertionError('preflight must not read payload')
            def open(self,*args):raise AssertionError('preflight must not open payload')
        original_size=module._size
        def size(value):
            events.append(('size',value))
            if size_error:raise ValueError('synthetic size rejection')
            return original_size(value)
        original_re=module.re
        def matching(pattern,name):events.append(('pattern',name));return original_re.fullmatch(pattern,name)
        def allowed(name):events.append(('allowed',name));return name.startswith('ok-')
        with patch.object(module,'_size',size),patch.object(module,'re',types.SimpleNamespace(fullmatch=matching)):
            try:
                if 'transition' in module.__name__:value=module._check_entries(Archive())
                else:value=module._check_entries(Archive(),allowed,10 if limit is None else limit)
                result=('success',value)
            except Exception as error:result=(type(error).__name__,str(error))
        return result,events

    def test_old_new_metadata_outcomes_order_and_callbacks_all_seven(self):
        for name in NAMES:
            current=importlib.import_module(name);old=old_module(name)
            fixed=sorted(current.FIXED_MEMBERS) if 'transition' in name else ['ok-one','ok-two']
            valid=[entry(n) for n in fixed]
            cases=[valid,list(reversed(valid)),valid+[copy.deepcopy(valid[0])],[],valid[1:],
                   valid+[entry('outside')],valid+[entry('applications/step-000000.json' if 'transition' in name else 'ok-three')]]
            for field,value in [('directory',True),('flag_bits',1),('compress_type',zipfile.ZIP_DEFLATED),
                                ('compress_size',4),('create_system',0),('external_attr',0o120777<<16),
                                ('file_size',50_000_001)]:
                bad=copy.deepcopy(valid);bad[0][field]=value;cases.append(bad)
            cases.append(valid+[entry('ok-overflow')]*(current.MAX_STEPS+len(current.FIXED_MEMBERS)+1 if 'transition' in name else 11))
            for index,rows in enumerate(cases):
                for size_error in (False,True):
                    with self.subTest(name=name,index=index,size_error=size_error):
                        self.assertEqual(self.observe(old,rows,size_error=size_error),self.observe(current,rows,size_error=size_error))
            self.assertEqual(self.observe(current,list(reversed(valid)))[0],('success',list(reversed(fixed))))

    def test_seven_actual_builds_identical_and_replay_with_controlled_prior_hashes(self):
        # Only eight exact implementation file reads are substituted. No inputs,
        # findings, ZIP members, output bytes or other reads are normalized.
        sources={(ROOT/name).resolve():prior_bytes(name) for name in CHANGED}
        prior_modules={name:old_module(name) for name in NAMES}
        original_read=Path.read_bytes
        def controlled(path):
            key=path.resolve()
            return sources[key] if key in sources else original_read(path)
        with patch.object(Path,'read_bytes',controlled):
            for name,classname in zip(NAMES,CLASSES):
                with self.subTest(name=name):
                    suite=importlib.import_module('tests.test_'+name);cls=getattr(suite,classname)
                    cls.setUpClass();fixture=cls();fixture.setUp()
                    try:
                        new=suite.bundle;old=prior_modules[name]
                        self.assertEqual(new.implementation_hashes(),old.implementation_hashes())
                        current=fixture.build()
                        with patch.object(suite,'bundle',old):prior=fixture.build()
                        self.assertEqual(current,prior)
                        self.assertTrue(new.verify_bundle(prior)['valid'])
                        self.assertTrue(old.verify_bundle(current)['valid'])
                    finally:
                        fixture.tearDown();cls.tearDownClass()

    def test_source_inventory_build_verify_and_existing_research_checks_unchanged(self):
        proof=json.loads((ROOT/'tests/archive_preflight_prior_sources.json').read_bytes())
        changes=json.loads((ROOT/'tests/archive_preflight_source_changes.json').read_bytes())
        self.assertEqual(set(changes),CHANGED)
        self.assertEqual(set(proof),{p.name for p in ROOT.glob('*.py') if p.name != 'cli_errors.py'})
        for name,digest in proof.items():self.assertEqual(hashlib.sha256(prior_bytes(name)).hexdigest(),digest,name)
        old=old_module('archive_safety')
        for name in ('_read_stream','read_bounded','check_stored_entries'):
            tree=ast.parse(prior_bytes('archive_safety.py'));node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            source=ast.get_source_segment(prior_bytes('archive_safety.py').decode(),node)
            self.assertEqual(inspect.getsource(getattr(archive_safety,name)).strip(),source)
        total=0
        for name in NAMES:
            module=importlib.import_module(name);prior=prior_bytes(name+'.py').decode();tree=ast.parse(prior)
            previous=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_check_entries');total+=previous.end_lineno-previous.lineno+1
            for function in ('build_bundle','verify_bundle'):
                node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function)
                self.assertEqual(inspect.getsource(getattr(module,function)).strip(),ast.get_source_segment(prior,node))
            if hasattr(module,'ENGINE_FILES'):
                self.assertEqual(module.ENGINE_FILES,old_module(name).ENGINE_FILES)
            self.assertEqual(set(module.implementation_hashes()),set(old_module(name).implementation_hashes()))
        self.assertEqual(total,102)
        self.assertIn('archive_safety.py',research_bundle.ENGINE_FILES)


if __name__=='__main__':unittest.main()
