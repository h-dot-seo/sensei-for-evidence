import copy
import json
import unittest
from pathlib import Path
from evidence_workflow import run

class EvidenceTests(unittest.TestCase):
    def setUp(self): self.p=json.loads(Path('examples/protocol.json').read_text())
    def test_flow_and_work(self):
        self.p['searches'].append(copy.deepcopy(self.p['searches'][0]))
        result=run(self.p)
        self.assertEqual(result['flow']['identified'],4)
        self.assertEqual(result['flow']['duplicates'],2)
        self.assertEqual(result['flow']['included'],1)
        self.assertEqual(result['work_packages'][0]['evidence_ids'],['r1'])
        self.assertEqual(result['conclusion_readiness'],'NOT_READY')
    def test_paging_and_pending(self):
        self.p['searches'][0]['has_more']=True
        self.p['screening'].pop()
        result=run(self.p)
        self.assertFalse(result['coverage'][0]['complete'])
        self.assertEqual(result['flow']['pending'],1)
    def test_bad_links(self):
        self.p['gaps'][0]['evidence_ids']=['unknown']
        with self.assertRaises(ValueError): run(self.p)
    def test_excluded_evidence(self):
        self.p['screening'][0]['decision']='exclude'
        with self.assertRaises(ValueError): run(self.p)

    def test_dependencies_completion_and_reproducibility(self):
        second=copy.deepcopy(self.p['gaps'][0]); second['depends_on']=['WP-001']
        self.p['gaps'].append(second)
        result=run(self.p)
        self.assertEqual(result['execution_order'],['WP-001','WP-002'])
        self.assertEqual(result['work_packages'][1]['blocked_by'],['WP-001'])
        self.assertEqual(result,run(self.p))
        self.p['gaps'][1].update(status='COMPLETE',artifact_locator='synthetic artifact',acceptance_verified=True)
        with self.assertRaises(ValueError): run(self.p)
        self.p['gaps'][0].update(status='COMPLETE',artifact_locator='synthetic artifact',acceptance_verified=True)
        self.assertEqual(run(self.p)['work_packages'][1]['blocked_by'],[])

    def test_cycle_and_missing_artifact(self):
        self.p['gaps'][0]['depends_on']=['WP-001']
        with self.assertRaises(ValueError): run(self.p)
        self.p['gaps'][0]['depends_on']=[]
        self.p['gaps'][0]['status']='COMPLETE'
        with self.assertRaises(ValueError): run(self.p)


class WorkProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads(Path('examples/report-protocol.json').read_text())

    def test_evidence_links_nonempty_unique_and_typed(self):
        for value in ([], '', 'r1', {}, None, ['r1', 'r1'], [' '], [1], ['unknown']):
            self.protocol['gaps'][0]['evidence_ids'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                run(self.protocol)

    def test_completed_work_cannot_lose_evidence_after_exclusion(self):
        from research_bundle import build_bundle
        self.protocol['reports'][0].update(decision='exclude', reason='wrong model')
        self.protocol['evidence'] = []
        self.protocol['gaps'][0].update(evidence_ids=[], status='COMPLETE',
                                       artifact_locator='synthetic://artifact', acceptance_verified=True)
        with self.assertRaisesRegex(ValueError, 'at least one linked evidence'):
            build_bundle(json.dumps(self.protocol).encode())

    def test_work_text_and_completed_artifact_require_nonblank_strings(self):
        for field in ('question', 'deliverable', 'acceptance_criterion', 'work_package_id', 'artifact_locator'):
            for value in ('   ', None, True, []):
                protocol = copy.deepcopy(self.protocol)
                protocol['gaps'][0].update(status='COMPLETE', artifact_locator='synthetic://artifact', acceptance_verified=True)
                protocol['gaps'][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    run(protocol)
