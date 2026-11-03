import copy
import csv
import tempfile
import io
import json
from pathlib import Path
import unittest
import zipfile
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import build_bundle, verify


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/context-protocol.json').read_text())

    def test_context_links_and_pending_review(self):
        result = run(self.protocol)
        self.assertEqual(result['context']['review_pending'], ['ctx-guideline'])
        self.assertEqual(result['context']['context_ledger'][0]['linked_study_ids'], ['s1'])
        self.assertEqual(result['context']['work_package_context'][0]['context_review_pending'], ['ctx-guideline'])
        self.assertEqual(result['census_claim'], 'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(result, run(self.protocol))
        self.assertEqual(report_flow(self.protocol)['context'], result['context'])

    def test_no_context_backward_compatibility(self):
        self.protocol.pop('contexts')
        self.protocol['gaps'][0].pop('context_ids')
        self.assertEqual(run(self.protocol)['context']['context_ledger'], [])

    def test_missing_provenance_and_applicability_rejected(self):
        for field in ('locator', 'issuer', 'version', 'applicability', 'limitations', 'recommendation_strength', 'evidence_certainty'):
            protocol = copy.deepcopy(self.protocol)
            protocol['contexts'][0].pop(field)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                run(protocol)

    def test_unknown_and_duplicate_context_ids(self):
        self.protocol['gaps'][0]['context_ids'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'unknown context'):
            run(self.protocol)
        self.protocol['gaps'][0]['context_ids'] = ['ctx-guideline', 'ctx-guideline']
        with self.assertRaisesRegex(ValueError, 'unique nonempty IDs'):
            run(self.protocol)
        self.protocol['gaps'][0]['context_ids'] = []
        self.protocol['contexts'].append(self.protocol['contexts'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate context ID'):
            run(self.protocol)

    def test_evidence_links_required(self):
        for value in ([], ['missing'], ['r1', 'r1'], 'r1'):
            self.protocol['contexts'][0]['evidence_ids'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                run(self.protocol)

    def test_review_requires_provenance(self):
        context = self.protocol['contexts'][0]
        context['review_status'] = 'reviewed'
        with self.assertRaisesRegex(ValueError, 'reviewer'):
            run(self.protocol)
        context['reviewer'] = 'synthetic-reviewer'
        with self.assertRaisesRegex(ValueError, 'reviewed_at'):
            run(self.protocol)
        context['reviewed_at'] = '2026-01-03'
        self.assertEqual(run(self.protocol)['context']['review_pending'], [])
        self.assertEqual(run(self.protocol)['conclusion_readiness'], 'NOT_READY')

    def test_invalid_date_domain_and_shape(self):
        for value in ('2026-02-30', '20260102', 'unknown'):
            self.protocol['contexts'][0]['accessed_at'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'ISO date'):
                run(self.protocol)
        self.protocol['contexts'][0]['accessed_at'] = '2026-01-02'
        self.protocol['contexts'][0]['domain'] = 'unsupported'
        with self.assertRaisesRegex(ValueError, 'context domain'):
            run(self.protocol)
        self.protocol['contexts'] = {}
        with self.assertRaisesRegex(ValueError, 'contexts must be a list'):
            run(self.protocol)
        self.protocol['contexts'] = ['invalid']
        with self.assertRaisesRegex(ValueError, 'context must be an object'):
            run(self.protocol)

    def test_unassigned_and_unrelated_context_visible_or_rejected(self):
        self.protocol['gaps'][0]['context_ids'] = []
        self.assertEqual(run(self.protocol)['context']['unassigned_context_ids'], ['ctx-development', 'ctx-guideline'])
        self.protocol['gaps'][0]['context_ids'] = ['ctx-guideline']
        self.protocol['gaps'][0]['evidence_ids'] = []
        with self.assertRaisesRegex(ValueError, 'share a linked evidence ID'):
            run(self.protocol)

    def test_bundle_preserves_context_and_engine_fingerprint(self):
        raw = json.dumps(self.protocol).encode()
        bundle = build_bundle(raw)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'context.zip'
            path.write_bytes(bundle)
            self.assertTrue(verify(path)['valid'])
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            result = json.loads(archive.read('research.json'))
            self.assertEqual(result['context']['review_pending'], ['ctx-guideline'])
            self.assertEqual(json.loads(archive.read('reports.json'))['context'], result['context'])
            rows = list(csv.DictReader(io.StringIO(archive.read('work-packages.csv').decode())))
            self.assertEqual(json.loads(rows[0]['context_ids']), ['ctx-guideline', 'ctx-development'])
            self.assertIn(b'Context review pending: 1', archive.read('summary.md'))
            manifest = json.loads(archive.read('manifest.json'))
            self.assertIn('context_links.py', manifest['engine_sha256'])
