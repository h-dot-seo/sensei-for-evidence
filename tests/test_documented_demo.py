import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile
from compare_runs import compare_protocols
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import create, verify


class DocumentedDemoTests(unittest.TestCase):
    def test_combined_demo_matches_documented_bounds(self):
        path = Path('examples/review-demo.json')
        protocol = json.loads(path.read_text())
        result = run(protocol)
        reports = report_flow(protocol)
        self.assertEqual(result['flow']['identified'], 2)
        self.assertEqual(result['flow']['extracted'], 2)
        self.assertEqual(reports['report_flow']['included'], 1)
        self.assertEqual(reports['report_flow']['included_studies'], 1)
        self.assertEqual(result['coverage'][0]['page_audit']['status'], 'RECONCILED')
        self.assertEqual(result['search_plan_audit']['missing_search_ids'], ['search-secondary'])
        self.assertEqual(result['context']['review_pending'], ['ctx-guideline'])
        self.assertEqual(result['appraisal']['evidence_without_recorded_appraisal'], ['e2'])
        self.assertEqual(result['work_packages'][1]['blocked_by'], ['WP-MECHANISM'])
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        comparison = compare_protocols(protocol, protocol)
        self.assertFalse(comparison['has_changes'])
        self.assertEqual(comparison['identity_warnings'], [])
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'synthetic-review.zip'
            create(path, target)
            self.assertTrue(verify(target)['valid'])
            with zipfile.ZipFile(target) as archive:
                self.assertIn(b'Incomplete planned searches: 0', archive.read('summary.md'))
                self.assertIn(b'Missing planned searches: 1', archive.read('summary.md'))

    def test_readme_and_usage_local_links_resolve(self):
        for source in (Path('README.md'), Path('docs/USAGE.md'), Path('docs/COMMANDS.md')):
            for target in re.findall(r'\]\(([^)]+)\)', source.read_text(encoding='utf-8')):
                if '://' in target or target.startswith('#'):
                    continue
                with self.subTest(source=source, target=target):
                    self.assertTrue((source.parent / target.split('#')[0]).is_file())
