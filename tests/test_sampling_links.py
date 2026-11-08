"""Synthetic n reporting only: no statistical or independence assessment."""
import copy
import csv
import io
import json
from pathlib import Path
import unittest
import zipfile
from evidence_workflow import run
from research_status import status
from work_review import review_packets
from synthesis_review import snapshot
from research_bundle import build_bundle


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(Path('examples/sampling-review.json').read_text())

    def unit(self,p=None):
        return run(p or self.p)['experiments']['experimental_unit_ledger'][0]

    def test_preserves_arm_outcome_counts_without_independence_inference(self):
        unit=self.unit()
        self.assertEqual(unit['outcome_sampling'][0]['treatment']['technical_n']['value'],'12')
        self.assertEqual(unit['sampling_review']['independence_assessment'],'NOT_PERFORMED')
        self.assertEqual(unit['sampling_review']['numeric_consistency'],'NOT_ASSESSED')
        gaps=unit['sampling_review']['unresolved_fields']
        self.assertIn('outcome_sampling.e1.comparator.analyzed_n',gaps)
        self.assertIn('outcome_sampling.e2.independence_basis',gaps)
        self.assertNotIn('outcome_sampling.e1.treatment.animal_n',gaps)

    def test_absence_empty_and_unknown_are_not_silent_completeness(self):
        self.p['experimental_units'][0].pop('outcome_sampling')
        self.assertEqual(status(self.p)['queues']['units_without_outcome_sampling'],['condition-1'])
        self.p['experimental_units'][0]['outcome_sampling']=[]
        with self.assertRaisesRegex(ValueError,'each linked evidence'):run(self.p)
        self.p.pop('experimental_units')
        self.assertIsNone(status(self.p)['queues']['units_without_outcome_sampling'])

    def test_outcomes_exactly_once_and_no_extra_arm(self):
        for change in ('missing','duplicate','unknown','extra_arm'):
            p=copy.deepcopy(self.p);rows=p['experimental_units'][0]['outcome_sampling']
            if change=='missing':rows.pop()
            if change=='duplicate':rows.append(copy.deepcopy(rows[0]))
            if change=='unknown':rows[0]['evidence_id']='alien'
            if change=='extra_arm':rows[0]['third_arm']={}
            with self.subTest(change=change),self.assertRaises(ValueError):run(p)

    def test_strict_status_union_rejects_numeric_coercion_and_partial_values(self):
        for value in (12,True,None,{},[],12.0):
            p=copy.deepcopy(self.p)
            p['experimental_units'][0]['outcome_sampling'][0]['treatment']['analyzed_n']['value']=value
            with self.subTest(value=value),self.assertRaises(ValueError):run(p)
        p=copy.deepcopy(self.p)
        del p['experimental_units'][0]['outcome_sampling'][0]['treatment']['analyzed_n']['unit']
        with self.assertRaises(ValueError):run(p)
        p=copy.deepcopy(self.p)
        p['experimental_units'][0]['outcome_sampling'][0]['comparator']['analyzed_n']['value']='12'
        with self.assertRaises(ValueError):run(p)

    def test_text_counts_not_calculated_or_compared(self):
        row=self.p['experimental_units'][0]['outcome_sampling'][0]
        row['treatment']['analyzed_n']['value']='range 4 to 8; source wording uncertain'
        row['treatment']['technical_n']['value']='different reported population'
        self.assertEqual(self.unit()['outcome_sampling'][0],row)
        self.assertEqual(self.unit()['sampling_review']['numeric_consistency'],'NOT_ASSESSED')

    def test_end_to_end_scope_and_stale_review(self):
        research=run(self.p)
        self.assertEqual(research['experiments']['units_with_unresolved_sampling'],['condition-1'])
        packet=review_packets(self.p)['packets'][0]
        self.assertEqual(packet['recorded_review_gaps']['units_with_unresolved_sampling'],['condition-1'])
        self.assertEqual(packet['recorded_review_gaps']['units_without_outcome_sampling'],[])
        snap=snapshot(self.p)
        self.assertEqual(snap['experimental_unit_ledger'][0]['outcome_sampling'],self.unit()['outcome_sampling'])
        self.assertTrue(research['planning']['work_with_stale_planning_assertion'])
        self.assertTrue(research['synthesis']['stale_statement_ids'])
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(self.p).encode()))) as z:
            bundled=json.loads(z.read('research.json'))
            rows=list(csv.DictReader(io.StringIO(z.read('work-packages.csv').decode())))
            self.assertTrue(all(row['units_with_unresolved_sampling']=='["condition-1"]' for row in rows))
            self.assertTrue(all(row['units_without_outcome_sampling']=='[]' for row in rows))
        self.assertEqual(bundled['experiments'],research['experiments'])

    def test_all_reported_does_not_assert_independence_or_readiness(self):
        for row in self.p['experimental_units'][0]['outcome_sampling']:
            row['independence_basis']=dict(status='reported',value='Supplied assertion only',source_locator='fictional appendix')
            for arm in ('treatment','comparator'):
                for name,field in row[arm].items():
                    if field['status']=='not_reported':
                        row[arm][name]=dict(status='reported',value='arbitrary source text',unit='fictional units',source_locator='fictional appendix')
        self.assertEqual(self.unit()['sampling_review']['unresolved_fields'],[])
        self.assertEqual(self.unit()['sampling_review']['independence_assessment'],'NOT_PERFORMED')
        self.assertEqual(run(self.p)['conclusion_readiness'],'NOT_READY')

    def test_supplied_empty_condition_ledger_is_distinct_from_missing(self):
        self.p['experimental_units']=[]
        self.assertEqual(status(self.p)['queues']['units_without_outcome_sampling'],[])
        self.assertEqual(status(self.p)['queues']['units_with_unresolved_sampling'],[])
        self.assertEqual(status(self.p)['queues']['evidence_without_experimental_unit'],['e1','e2','e3'])

    def test_analysis_unit_shape_and_arm_count_fields_fail_closed(self):
        for mutation in ('missing_arm','extra_count','missing_locator','list_analysis','unit_on_analysis'):
            p=copy.deepcopy(self.p);row=p['experimental_units'][0]['outcome_sampling'][0]
            if mutation=='missing_arm':del row['comparator']
            if mutation=='extra_count':row['treatment']['total_n']={}
            if mutation=='missing_locator':del row['independence_basis']['source_locator']
            if mutation=='list_analysis':row['analysis_unit']=[]
            if mutation=='unit_on_analysis':row['analysis_unit']['unit']='invented'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):run(p)

    def test_sampling_does_not_change_prisma_counts_or_infer_n(self):
        from prisma_reports import report_flow
        before=copy.deepcopy(self.p);before['experimental_units'][0].pop('outcome_sampling')
        self.assertEqual(report_flow(before)['report_flow'],report_flow(self.p)['report_flow'])
        original=copy.deepcopy(self.p);self.unit();self.assertEqual(original,self.p)

if __name__=='__main__':unittest.main()
