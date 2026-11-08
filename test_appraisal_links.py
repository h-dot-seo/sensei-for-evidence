import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from evidence_workflow import run
from prisma_reports import report_flow
from research_bundle import build_bundle, verify


class AppraisalTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/appraised-protocol.json').read_text())

    def test_missing_appraisal_links_visible_without_quality_inference(self):
        result = run(self.protocol)
        appraisal = result['appraisal']
        self.assertEqual(appraisal['evidence_without_recorded_appraisal'], ['e2'])
        self.assertEqual(appraisal['work_package_appraisals'][0]['appraisal_ids'], ['appraisal-1'])
        self.assertEqual(appraisal['work_package_appraisals'][0]['evidence_without_recorded_appraisal'], ['e2'])
        self.assertEqual(appraisal['appraisal_ledger'][0]['linked_study_id'], 's1')
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_legacy_inputs_mark_appraisal_unrecorded(self):
        self.protocol.pop('appraisals')
        result = run(self.protocol)
        self.assertEqual(result['appraisal']['evidence_without_recorded_appraisal'], ['e1', 'e2'])

    def test_provenance_and_domain_fields_required(self):
        for field in ('method', 'method_version', 'method_locator', 'reviewer', 'assessed_at', 'limitations'):
            protocol = copy.deepcopy(self.protocol)
            protocol['appraisals'][0][field] = '  '
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                run(protocol)
        for field in ('name', 'judgement', 'rationale', 'source_locator'):
            protocol = copy.deepcopy(self.protocol)
            protocol['appraisals'][0]['domains'][0].pop(field)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                run(protocol)

    def test_unknown_empty_duplicate_evidence_links_rejected(self):
        for value in ([], ['missing'], ['e1', 'e1'], 'e1'):
            self.protocol['appraisals'][0]['evidence_ids'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                run(self.protocol)

    def test_duplicate_appraisal_or_domain_ids_rejected(self):
        self.protocol['appraisals'].append(copy.deepcopy(self.protocol['appraisals'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate appraisal ID'):
            run(self.protocol)
        self.protocol['appraisals'].pop()
        self.protocol['appraisals'][0]['domains'] *= 2
        with self.assertRaisesRegex(ValueError, 'duplicate appraisal domain'):
            run(self.protocol)

    def test_conflicting_reviewers_preserved_without_consensus(self):
        second = copy.deepcopy(self.protocol['appraisals'][0])
        second.update(appraisal_id='appraisal-2', reviewer='other-synthetic-reviewer')
        second['domains'][0]['judgement'] = 'different supplied judgement'
        self.protocol['appraisals'].append(second)
        result = run(self.protocol)
        ledger = result['appraisal']['appraisal_ledger']
        self.assertEqual(len(ledger), 2)
        self.assertNotEqual(ledger[0]['domains'][0]['judgement'], ledger[1]['domains'][0]['judgement'])
        self.assertEqual(result['conclusion_readiness'], 'NOT_READY')

    def test_cross_study_appraisal_rejected(self):
        self.protocol['screening'][1]['decision'] = 'include'
        self.protocol['evidence'].append(dict(self.protocol['evidence'][0], evidence_id='e3', record_id='r2', study_id='s2'))
        self.protocol['appraisals'][0]['evidence_ids'] = ['e1', 'e3']
        with self.assertRaisesRegex(ValueError, 'one supplied study ID'):
            run(self.protocol)

    def test_invalid_shapes_and_dates(self):
        for value in (None, {}, ['invalid']):
            self.protocol['appraisals'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                run(self.protocol)
        self.setUp()
        self.protocol['appraisals'][0]['assessed_at'] = '2026-02-30'
        with self.assertRaisesRegex(ValueError, 'ISO date'):
            run(self.protocol)

    def test_report_and_bundle_preserve_appraisal_and_pending(self):
        result = run(self.protocol)
        self.assertEqual(report_flow(self.protocol)['appraisal'], result['appraisal'])
        bundle = build_bundle(json.dumps(self.protocol).encode())
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            self.assertEqual(json.loads(archive.read('research.json'))['appraisal'], result['appraisal'])
            self.assertIn(b'Result rows without recorded appraisal: 1', archive.read('summary.md'))
            self.assertIn('appraisal_links.py', json.loads(archive.read('manifest.json'))['engine_sha256'])
            work = list(csv.DictReader(io.StringIO(archive.read('work-packages.csv').decode())))[0]
            self.assertEqual(json.loads(work['appraisal_ids']), ['appraisal-1'])
            self.assertEqual(json.loads(work['evidence_without_recorded_appraisal']), ['e2'])
            self.assertEqual(json.loads(work['context_review_pending']), ['ctx-guideline'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'bundle.zip'
            path.write_bytes(bundle)
            self.assertTrue(verify(path)['valid'])
