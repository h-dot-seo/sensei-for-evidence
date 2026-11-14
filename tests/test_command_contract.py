"""Partial effect declarations, exact inventory, source drift and safe inspection."""
import copy
import io
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import command_contract
from tests.test_command_reference import command_rows

ROOT = Path(__file__).resolve().parents[1]


def invoke(*args, cwd=ROOT):
    return subprocess.run([sys.executable, '-B', str(ROOT/'sensei.py'), *args], cwd=cwd,
                          capture_output=True, timeout=30)


class CommandContractTests(unittest.TestCase):
    def test_exact_inventory_usage_guides_and_source_bindings(self):
        result = command_contract.contract()
        expected = command_rows((ROOT/'docs/COMMANDS.md').read_text(encoding='utf-8'))
        actual = {(row['script'], (row['subcommand'],) if row['subcommand'] else ()): row for row in result['commands']}
        self.assertEqual(set(actual), set(expected))
        self.assertEqual(result['coverage']['reviewed_effects'], 26)
        for key, row in actual.items():
            self.assertEqual(row['usage'], expected[key] if row['has_parser'] else None)
            for guide in row['guides']:
                self.assertTrue((ROOT/guide).is_file(), guide)
            self.assertEqual(row['effect_status'], 'REVIEWED' if row['effects'] else 'NOT_REVIEWED')
            for arg in (row['effects'] or {}).get('inputs', []):
                self.assertIn(arg, expected[key])
            for output in (row['effects'] or {}).get('outputs', []):
                self.assertIn(output['argument'], expected[key])
        for name, digest in result['implementation_sha256'].items():
            self.assertEqual(digest, hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        self.assertEqual(result['registry_sha256'], hashlib.sha256((ROOT/command_contract.REGISTRY).read_bytes()).hexdigest())
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_routes_preserve_actual_required_human_inputs(self):
        from review_handoff import SUPPLIED_INPUT_WORKFLOWS
        result = command_contract.contract()
        routes = {row['workflow_id']: row for row in result['routes']}
        for route in SUPPLIED_INPUT_WORKFLOWS:
            self.assertEqual(routes[route['workflow_id']]['required_human_inputs'], route['required_human_inputs'])
            self.assertEqual(routes[route['workflow_id']]['boundary'], route['boundary'])
            for entry in route['entrypoints']:
                args = entry['arguments'][:-1]
                row = next(row for row in result['commands'] if row['script'] == entry['script'] and
                           ([row['subcommand']] if row['subcommand'] else []) == args)
                self.assertIn(route['workflow_id'], row['route_ids'])

    def test_documented_commands_deterministic_relocated_and_no_writes(self):
        doc = (ROOT/'docs/AGENT_CONTRACT.md').read_text(encoding='utf-8')
        commands = re.findall(r'^python sensei.py (.+)$', doc, re.M)
        self.assertEqual(commands, ['contract', 'contract --text'])
        with tempfile.TemporaryDirectory(prefix='sensei contract ') as td:
            first = invoke('contract', cwd=td)
            second = invoke('contract', cwd=td)
            text = invoke('contract', '--text', cwd=td)
            self.assertEqual((first.returncode, first.stderr), (0, b''))
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual((text.returncode, text.stderr), (0, b''))
            self.assertIn(b'NOT_REVIEWED', text.stdout)
            self.assertEqual(list(Path(td).iterdir()), [])
            # Copy only implementation+registry, no existing bytecode; normal Python CLI
            # must not populate caches during this particular inspection subcommand.
            clone = Path(td)/'clone';clone.mkdir();(clone/'docs').mkdir()
            for p in ROOT.glob('*.py'):
                shutil.copyfile(p, clone/p.name)
            shutil.copyfile(ROOT/command_contract.REGISTRY, clone/command_contract.REGISTRY)
            run = subprocess.run([sys.executable, str(clone/'sensei.py'), 'contract'], cwd=td,
                                 capture_output=True, timeout=30)
            self.assertEqual((run.returncode, run.stderr), (0, b''))
            self.assertEqual(first.stdout, run.stdout)
            self.assertEqual(list(clone.rglob('__pycache__')), [])

    def test_changed_missing_extra_source_and_bad_registry_refuse_before_catalog_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);(root/'docs').mkdir()
            for p in ROOT.glob('*.py'):
                shutil.copyfile(p, root/p.name)
            registry = root/command_contract.REGISTRY
            original_registry = (ROOT/command_contract.REGISTRY).read_bytes();registry.write_bytes(original_registry)
            source = root/'work_review.py';original = source.read_bytes()
            with patch.object(command_contract, 'ROOT', root):
                source.write_bytes(original+b'\n')
                with self.assertRaises(ValueError):command_contract.contract()
                source.unlink()
                with self.assertRaises(ValueError):command_contract.contract()
                source.write_bytes(original)
                (root/'extra.py').write_bytes(b'')
                with self.assertRaises(ValueError):command_contract.contract()
                (root/'extra.py').unlink()
                registry.write_bytes(b'{')
                with self.assertRaises(ValueError):command_contract.contract()
            run = subprocess.run([sys.executable, '-B', str(root/'sensei.py'), 'contract'], capture_output=True, timeout=30)
            self.assertEqual(run.returncode, 1);self.assertEqual(run.stdout, b'')
            self.assertNotIn(str(root).encode(), run.stderr)

    def test_registry_shapes_refuse_instead_of_claiming_reviewed(self):
        original=json.loads((ROOT/command_contract.REGISTRY).read_bytes())
        mutations=[lambda d:d.update(schema_version=True),
                   lambda d:d['commands'][0].update(effects={}),
                   lambda d:d['commands'][0].update(effects='read_only'),
                   lambda d:d['commands'][0].update(has_parser=1),
                   lambda d:d['commands'][0].update(guides=['../private.md']),
                   lambda d:d['commands'][0].update(subcommand=[]),
                   lambda d:d['commands'].append(copy.deepcopy(d['commands'][0]))]
        reviewed=next(i for i,row in enumerate(original['commands']) if row['effects'])
        mutations += [lambda d:d['commands'][reviewed]['effects']['success'].update(exit_code=False),
                      lambda d:d['commands'][reviewed]['effects'].update(network='authorized'),
                      lambda d:d['commands'][reviewed]['effects'].update(inputs=[{}]),
                      lambda d:d['commands'][reviewed]['effects'].update(usage_error={'exit_code':2}),
                      lambda d:d['commands'][reviewed]['effects'].update(outputs=[{'argument':'x','condition':'always','mode':'overwrite'}])]
        for mutate in mutations:
            data=copy.deepcopy(original);mutate(data)
            with patch.object(command_contract,'parse_json',return_value=data), self.assertRaises(ValueError):
                command_contract.contract()

    def test_effect_hazards_are_explicit_not_name_inference(self):
        rows = {(r['script'], r['subcommand']):r for r in command_contract.contract()['commands']}
        for key in [('sensei.py','run'),('build_manifest.py',None),('schema_check.py','check')]:
            self.assertIsNone(rows[key]['effects'])
        self.assertFalse(rows['verify_manifest.py',None]['has_parser'])
        self.assertFalse(rows['audit_publication.py',None]['has_parser'])
        self.assertTrue(rows['nbib_intake.py','verify']['effects']['outputs'])
        verify = rows['collection_export.py','verify']['effects']
        self.assertIn('--output', verify['inputs']);self.assertEqual(verify['outputs'], [])
        self.assertIn('nonempty', rows['collection_export.py','create']['effects']['outputs'][0]['condition'])
        self.assertEqual(rows['protocol_scaffold.py','check']['effects']['negative_report']['exit_code'], 2)
        network = [key for key,row in rows.items() if row['effects'] and row['effects']['network'] != 'none']
        self.assertEqual(sorted(network), [('pubmed_discovery.py','fetch'),('pubmed_metadata.py','fetch')])

    def test_every_reviewed_caught_error_channel_and_no_output(self):
        rows = [r for r in command_contract.contract()['commands'] if r['effects']]
        with tempfile.TemporaryDirectory() as td:
            missing = str(Path(td)/'absent.json')
            for row in rows:
                script, sub = row['script'], row['subcommand']
                args = [sub] if sub else []
                effects = row['effects']
                args += [missing for name in effects['inputs'] if not name.startswith('--')]
                if script == 'nbib_intake.py' and sub == 'preview':args += ['--search-id','synthetic','--searched-at','2026-01-01']
                if script == 'screening_decision.py' and sub == 'target':args += ['--record-id','synthetic']
                if script == 'research_bundle.py' and sub == 'create':args += [str(Path(td)/'new.zip')]
                if script == 'protocol_scaffold.py' and sub == 'template':args += ['--draft-output',str(Path(td)/'missing-parent'/'new.json')]
                if script.startswith('pubmed_') and sub != 'verify':args += ['--output',str(Path(td)/'new.json')]
                if script.startswith('pubmed_') and sub == 'fetch':args += ['--preview-sha256','0'*64]
                if script.startswith('pubmed_') and sub == 'to-intake':args += ['--search-id','synthetic']
                if script == 'collection_export.py':args += ['--output',missing,'--decision','include']
                with self.subTest(script=script, subcommand=sub):
                    result = subprocess.run([sys.executable,'-B',str(ROOT/script),*args],cwd=td,capture_output=True,timeout=30)
                    self.assertEqual(result.returncode,effects['caught_error']['exit_code'],result.stderr)
                    self.assertEqual(result.stdout,b'');self.assertTrue(result.stderr)
                    self.assertEqual(list(Path(td).iterdir()),[])

    def test_fetch_dispatch_is_mocked_no_live_requests(self):
        import pubmed_discovery
        import pubmed_metadata
        for module in (pubmed_discovery, pubmed_metadata):
            args = [module.__name__+'.py', 'fetch', 'input.json']
            if module is pubmed_metadata:args.append('selection.json')
            with tempfile.TemporaryDirectory() as td:
                dest=Path(td)/'new.json';args += ['--preview-sha256','0'*64,'--output',str(dest)]
                stdout=io.StringIO();stderr=io.StringIO()
                with patch.object(sys,'argv',args), patch.object(module,'_read',return_value={}), patch.object(module,'fetch',return_value={'synthetic':True}) as fetch, redirect_stdout(stdout), redirect_stderr(stderr):
                    module.main()
                fetch.assert_called_once()
                self.assertEqual(json.loads(stdout.getvalue()), {'synthetic':True})
                self.assertEqual(json.loads(dest.read_bytes()), {'synthetic':True})
                self.assertEqual(stderr.getvalue(),'')

    def test_scaffold_invalid_report_and_optional_output_contract(self):
        import protocol_scaffold
        with tempfile.TemporaryDirectory() as td:
            draft=Path(td)/'draft.json';dest=Path(td)/'protocol.json'
            draft.write_bytes(json.dumps(protocol_scaffold.template()['draft']).encode())
            result=subprocess.run([sys.executable,'-B',str(ROOT/'protocol_scaffold.py'),'check',str(draft),'--protocol-output',str(dest)],capture_output=True,timeout=30)
            self.assertEqual(result.returncode,2);self.assertEqual(result.stderr,b'')
            self.assertFalse(json.loads(result.stdout)['valid']);self.assertFalse(dest.exists())

    def test_local_nbib_walkthrough_operations_all_have_profiles(self):
        import shlex
        rows = {(r['script'],r['subcommand']):r for r in command_contract.contract()['commands']}
        count = 0
        for line in (ROOT/'docs/PUBMED_NBIB_INTAKE.md').read_text(encoding='utf-8').splitlines():
            if line.startswith('python '):
                args=shlex.split(line);key=(args[1],args[2])
                if key not in rows:key=(args[1],None)
                self.assertIsNotNone(rows[key]['effects']);count+=1
        self.assertEqual(count,14)  # Existing walkthrough test executes this full flow.

    def test_text_escapes_untrusted_catalog_strings(self):
        result=command_contract.contract()
        result['commands'][0]['usage']='fake\nREADY\x1b\u202e'
        text=command_contract.render_text(result)
        self.assertNotIn('\nREADY',text);self.assertNotIn('\x1b',text);self.assertNotIn('\u202e',text)
        self.assertIn('\\nREADY',text)
