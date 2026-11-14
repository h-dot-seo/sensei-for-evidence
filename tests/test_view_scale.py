"""Bounded-shape search reference growth, not a general linearity claim."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from evidence_workflow import run
from json_io import canonical_json_bytes
from synthesis_review import snapshot
from work_review import review_packets
import research_view

ROOT=Path(__file__).resolve().parents[1]
def generated(n):
    seed=json.loads((ROOT/'examples/review-demo.json').read_text())
    p={k:copy.deepcopy(seed[k]) for k in ('question','version','inclusion_criteria','exclusion_criteria')}
    ids=['r'+str(i) for i in range(n)]
    p['searches']=[dict(source='synthetic',query='synthetic',searched_at='2026-01-01',window='2026',record_ids=ids,total_count=n,complete=True,has_more=False)]
    p['screening']=[dict(record_id=i,decision='include',reason='synthetic') for i in ids]
    p['evidence']=[];p['gaps']=[]
    for i,rid in enumerate(ids):
        e=copy.deepcopy(seed['evidence'][0]);e.update(record_id=rid,evidence_id='e'+str(i),study_id='s'+str(i));p['evidence'].append(e)
        p['gaps'].append(dict(work_package_id='w'+str(i),question='synthetic',evidence_ids=[e['evidence_id']],deliverable='synthetic',acceptance_criterion='human review',context='synthetic'))
    return p

class ScaleTests(unittest.TestCase):
    def test_exact_refs_reconstruct_sources_and_do_not_mutate(self):
        p=generated(5);old=copy.deepcopy(p);expected=run(p)['search_ledger']
        for result in (snapshot(p),review_packets(p)):
            self.assertEqual(result['schema_version'],2);self.assertEqual(result['search_ledger'],expected)
        s=snapshot(p);w=review_packets(p)
        sources=[x for row in s['evidence_citation_index'] for x in row['search_sources']]
        sources += [x for packet in w['packets'] for x in packet['sources']]
        for source in sources:
            self.assertNotIn('search',source);ref=source['search_ref'];self.assertEqual(ref['search_sha256'],hashlib.sha256(canonical_json_bytes(expected[ref['search_index']])).hexdigest())
        self.assertEqual(p,old)
    def test_declared_shape_doubling_output_under_threefold(self):
        for build in (snapshot,review_packets):
            small=len(canonical_json_bytes(build(generated(200))))
            large=len(canonical_json_bytes(build(generated(400))))
            self.assertLess(large,3*small)
    def test_list_order_changes_binding_and_key_order_does_not(self):
        p=generated(3);a=snapshot(p);p['searches'][0]=dict(reversed(list(p['searches'][0].items())));b=snapshot(p)
        self.assertEqual(a['search_ledger'],b['search_ledger'])
        p['searches'][0]['record_ids'].reverse();c=snapshot(p)
        self.assertNotEqual(a['search_ledger'],c['search_ledger'])
    def test_html_snapshot_retains_reference_ledger(self):
        p=generated(2);s=research_view.snapshot(p)
        self.assertEqual(s['synthesis']['search_ledger'],snapshot(p)['search_ledger'])
        self.assertIn('search_coverage',s['synthesis']);research_view.render(p)

    def test_nested_statement_refs_resolve(self):
        p=json.loads((ROOT/'examples/claim-comparison.json').read_text())
        result=snapshot(p);count=0
        for statement in result['statements']:
            for citation in statement['citations']:
                for source in citation['search_sources']:
                    ref=source['search_ref'];count+=1
                    self.assertEqual(ref['search_sha256'],hashlib.sha256(canonical_json_bytes(result['search_ledger'][ref['search_index']])).hexdigest())
        self.assertGreater(count,0)
        html=research_view.snapshot(p)
        self.assertEqual(html['schema_version'],2);self.assertEqual(html['synthesis']['schema_version'],2)
