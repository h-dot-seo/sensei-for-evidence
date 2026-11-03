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
