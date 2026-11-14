"""Protect the deliberately small, explicit CI workflow surface without a YAML dependency."""
import ast
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CIContractTests(unittest.TestCase):
    def test_exact_eight_version_os_pairs_and_version_specific_test_commands(self):
        text=(ROOT/'.github/workflows/tests.yml').read_text(encoding='utf-8')
        versions=ast.literal_eval(re.search(r'^        python: (.+)$',text,re.M).group(1))
        systems=re.search(r'^        os: \[(.+)\]$',text,re.M).group(1).split(', ')
        self.assertEqual(versions,['3.10','3.12','3.14','3.15'])
        self.assertEqual(systems,['ubuntu-latest','windows-latest'])
        self.assertEqual(len({(os,version) for os in systems for version in versions}),8)
        self.assertIn("      - if: matrix.python == '3.10'\n        run: python -m unittest discover -v\n",text)
        self.assertIn("      - if: matrix.python != '3.10'\n        run: python -m unittest discover -v --durations 25\n",text)
        self.assertIn('    timeout-minutes: 10\n',text)
        self.assertIn('      fail-fast: false\n',text)
        for command in ('python audit_publication.py','python verify_manifest.py'):
            self.assertIn('      - run: '+command+'\n',text)

    def test_trigger_and_cancellation_scope_preserve_main_and_distinct_prs(self):
        text=(ROOT/'.github/workflows/tests.yml').read_text(encoding='utf-8')
        self.assertIn('on:\n  push:\n    branches: ["main"]\n  pull_request:\n  workflow_dispatch:\n',text)
        self.assertIn("concurrency:\n  group: ${{ github.workflow }}-${{ github.event_name == 'pull_request' && github.ref || github.run_id }}\n  cancel-in-progress: ${{ github.event_name == 'pull_request' }}\n",text)
        self.assertNotIn('pull_request_target',text)
        self.assertNotIn('codex/core-workflows-20261103',text)
        # Evaluate the declared simple grouping rule on representative event contexts,
        # not a claim to emulate GitHub's scheduler or every expression language feature.
        def group(event,workflow,ref,run_id):
            return workflow+'-'+(ref if event=='pull_request' else str(run_id))
        self.assertEqual(group('pull_request','tests','refs/pull/1/merge',1),group('pull_request','tests','refs/pull/1/merge',2))
        self.assertNotEqual(group('pull_request','tests','refs/pull/1/merge',1),group('pull_request','tests','refs/pull/2/merge',2))
        self.assertNotEqual(group('pull_request','other','refs/pull/1/merge',1),group('pull_request','tests','refs/pull/1/merge',1))
        for old,new in [('push','push'),('workflow_dispatch','workflow_dispatch'),('push','workflow_dispatch')]:
            self.assertNotEqual(group(old,'tests','refs/heads/main',1),group(new,'tests','refs/heads/main',2))
        self.assertNotEqual(group('push','tests','refs/heads/main',1),group('pull_request','tests','refs/pull/1/merge',2))
        for event,cancel in [('push',False),('workflow_dispatch',False),('pull_request',True)]:
            self.assertEqual(event=='pull_request',cancel)

    def test_pinned_actions_and_readonly_permissions_have_not_expanded(self):
        text=(ROOT/'.github/workflows/tests.yml').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'uses: (\S+)',text),[
            'actions/checkout@11d5960a326750d5838078e36cf38b85af677262',
            'actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065'])
        self.assertIn('permissions:\n  contents: read\njobs:\n',text)
        self.assertIn('          persist-credentials: false\n',text)
        self.assertEqual(text.count('permissions:'),1)
        self.assertNotIn('secrets.',text)
        self.assertNotIn('continue-on-error',text)
