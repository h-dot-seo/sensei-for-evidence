"""Fictional numerical reporting, not observations or statistical inference."""
import copy
import csv
import io
import json
from pathlib import Path
import unittest
import zipfile
from evidence_workflow import run
from research_status import status
from work_review import review_packets, render_text as work_text
from synthesis_review import snapshot, render_text as synthesis_text
from research_bundle import build_bundle
from prisma_reports import report_flow


class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(Path('examples/statistics-review.json').read_text())

    def unit(self,p=None):
        return run(self.p if p is None else p)['experiments']['experimental_unit_ledger'][0]

    def test_preserves_number_direction_and_source_without_calculation(self):
        unit=self.unit();row=unit['outcome_statistics'][0]
        self.assertEqual(row['treatment']['value']['value'],'7.5')
        self.assertEqual(row['comparator']['value']['value'],'6.0')
        self.assertEqual(row['contrast']['estimate']['value'],'1.0')
        self.assertEqual(row['contrast']['direction']['value'],'lower')
        self.assertEqual(row['contrast']['direction']['source_locator'],'fictional result caption C')
        self.assertEqual(unit['statistics_review']['numeric_consistency'],'NOT_ASSESSED')
        self.assertEqual(unit['statistics_review']['effect_assessment'],'NOT_PERFORMED')

    def test_literal_labels_are_review_cues_not_incompatibility_findings(self):
        review=self.unit()['statistics_review']
        self.assertEqual(review['literal_label_differences'],[
            dict(evidence_id=e,field=f,treatment=a,comparator=b)
            for e in ('e1','e2') for f,a,b in [('value.unit','fictional units A','fictional units B'),('summary_statistic.value','mean','median')]])
        self.assertIn('outcome_statistics.e1.contrast.uncertainty_level',review['missing_fields'])
        self.assertIn('outcome_statistics.e1.comparator.dispersion',review['missing_fields'])
        # Whitespace/case are not normalized as scientific equivalence.
        row=self.p['experimental_units'][0]['outcome_statistics'][0]
        row['comparator']['value']['unit']='Fictional units A'
        self.assertEqual(self.unit()['statistics_review']['literal_label_differences'][0]['comparator'],'Fictional units A')

    def test_direction_requires_explicit_orientation_and_source_wording(self):
        for mutation in ('reverse','unknown_label','missing_quote','number_label','extra'):
            p=copy.deepcopy(self.p);d=p['experimental_units'][0]['outcome_statistics'][0]['contrast']['direction']
            if mutation=='reverse':d['orientation']='comparator_relative_to_treatment'
            if mutation=='unknown_label':d['value']='significant'
            if mutation=='missing_quote':del d['source_text']
            if mutation=='number_label':d['value']=True
            if mutation=='extra':d['p_value']='0.01'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):run(p)

    def test_strict_numeric_metadata_and_state_shapes(self):
        for value in (7.5,7,True,None,[],{},''):
            p=copy.deepcopy(self.p);p['experimental_units'][0]['outcome_statistics'][0]['treatment']['value']['value']=value
            with self.subTest(value=value),self.assertRaises(ValueError):run(p)
        for field in ('unit','source_locator'):
            p=copy.deepcopy(self.p);del p['experimental_units'][0]['outcome_statistics'][0]['treatment']['value'][field]
            with self.assertRaises(ValueError):run(p)
        p=copy.deepcopy(self.p);p['experimental_units'][0]['outcome_statistics'][0]['contrast']['statistical_test']['value']='invented'
        with self.assertRaises(ValueError):run(p)

    def test_exact_outcome_and_arm_coverage(self):
        for mutation in ('empty','duplicate','unknown','extra_arm','missing_contrast','list_arm'):
            p=copy.deepcopy(self.p);u=p['experimental_units'][0];rows=u['outcome_statistics']
            if mutation=='empty':u['outcome_statistics']=[]
            if mutation=='duplicate':rows.append(copy.deepcopy(rows[0]))
            if mutation=='unknown':rows[0]['evidence_id']='absent'
            if mutation=='extra_arm':rows[0]['third_arm']={}
            if mutation=='missing_contrast':del rows[0]['contrast']
            if mutation=='list_arm':rows[0]['treatment']=[]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):run(p)

    def test_missing_stage_and_empty_ledger(self):
        p=copy.deepcopy(self.p);p['experimental_units'][0].pop('outcome_statistics')
        self.assertEqual(status(p)['queues']['units_without_outcome_statistics'],['condition-1'])
        self.assertNotIn('statistics_review',self.unit(p))
        p['experimental_units']=[]
        self.assertEqual(status(p)['queues']['units_without_outcome_statistics'],[])
        p.pop('experimental_units')
        self.assertIsNone(status(p)['queues']['units_without_outcome_statistics'])
        self.assertIsNone(status(p)['queues']['units_with_statistics_review_cues'])

    def test_nonreported_direction_and_not_applicable_do_not_invent_effect(self):
        for state in ('not_reported','unknown','not_applicable'):
            p=copy.deepcopy(self.p);p['experimental_units'][0]['outcome_statistics'][0]['contrast']['direction']=dict(status=state,reason='Supplied missingness assertion',source_locator='fictional caption')
            review=self.unit(p)['statistics_review']
            self.assertEqual('outcome_statistics.e1.contrast.direction' in review['missing_fields'],state!='not_applicable')
            self.assertEqual(review['effect_assessment'],'NOT_PERFORMED')

    def test_full_reported_equal_labels_do_not_promote_readiness(self):
        for row in self.p['experimental_units'][0]['outcome_statistics']:
            row['comparator']=copy.deepcopy(row['treatment'])
            for key,field in row['contrast'].items():
                if field['status']=='not_reported':row['contrast'][key]=dict(status='reported',value='Supplied arbitrary text',source_locator='fictional caption')
        review=self.unit()['statistics_review']
        self.assertEqual(review['missing_fields'],[]);self.assertEqual(review['literal_label_differences'],[])
        self.assertEqual(run(self.p)['conclusion_readiness'],'NOT_READY')
        self.assertEqual(review['effect_assessment'],'NOT_PERFORMED')

    def test_dispersion_unit_difference_alone_is_queued(self):
        for row in self.p['experimental_units'][0]['outcome_statistics']:
            row['comparator']=copy.deepcopy(row['treatment'])
            for key,field in row['contrast'].items():
                if field['status']=='not_reported':row['contrast'][key]=dict(status='reported',value='Supplied arbitrary text',source_locator='fictional caption')
        self.p['experimental_units'][0]['outcome_statistics'][0]['comparator']['dispersion']['unit']='other supplied label'
        review=self.unit()['statistics_review']
        self.assertEqual(review['missing_fields'],[])
        self.assertEqual(review['literal_label_differences'],[dict(evidence_id='e1',field='dispersion.unit',treatment='fictional units A',comparator='other supplied label')])
        self.assertEqual(status(self.p)['queues']['units_with_statistics_review_cues'],['condition-1'])
        self.assertEqual(review['numeric_consistency'],'NOT_ASSESSED')

    def test_e2e_packets_csv_bundle_and_prisma_scope(self):
        before=copy.deepcopy(self.p);before['experimental_units'][0].pop('outcome_statistics')
        self.assertEqual(report_flow(before)['report_flow'],report_flow(self.p)['report_flow'])
        self.assertEqual(report_flow(before)['record_flow'],report_flow(self.p)['record_flow'])
        result=run(self.p)
        self.assertEqual(result['planning']['work_with_stale_planning_assertion'],['WP-MECHANISM','WP-TRANSLATION'])
        self.assertEqual(result['synthesis']['stale_statement_ids'],['statement-1'])
        for packet in review_packets(self.p)['packets']:
            self.assertEqual(packet['recorded_review_gaps']['units_with_statistics_review_cues'],['condition-1'])
            self.assertEqual(packet['experimental_gap_scope'],'full_intersecting_condition_records_including_other_outcomes')
        snap=snapshot(self.p)
        self.assertEqual(snap['review_queues']['units_with_statistics_review_cues'],['condition-1'])
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(self.p).encode()))) as z:
            self.assertEqual(json.loads(z.read('research.json'))['experiments'],result['experiments'])
            rows=list(csv.DictReader(io.StringIO(z.read('work-packages.csv').decode())))
        self.assertTrue(all(r['units_with_statistics_review_cues']=='["condition-1"]' for r in rows))

    def test_statistics_edits_and_removal_stale_previously_current_reviews(self):
        research=run(self.p)
        targets={r['work_package_id']:r['basis_sha256'] for r in research['planning']['review_targets']}
        for assertion in self.p['planning_decisions']:
            assertion['basis_sha256']=targets[assertion['work_package_id']]
        targets={r['statement_id']:r['current_basis_sha256'] for r in research['synthesis']['statement_ledger']}
        for assertion in self.p['synthesis_statements']:
            if assertion.get('review_status')=='reviewed':assertion['basis_sha256']=targets[assertion['statement_id']]
        self.assertEqual(run(self.p)['planning']['work_with_stale_planning_assertion'],[])
        self.assertEqual(run(self.p)['synthesis']['stale_statement_ids'],[])
        for mutation in ('number','locator','remove','sibling'):
            p=copy.deepcopy(self.p);u=p['experimental_units'][0]
            if mutation=='number':u['outcome_statistics'][0]['treatment']['value']['value']='7.6'
            if mutation=='locator':u['outcome_statistics'][0]['contrast']['p_value']['source_locator']='different fictional source'
            if mutation=='remove':u.pop('outcome_statistics')
            if mutation=='sibling':u['outcome_statistics'][1]['contrast']['direction']['value']='mixed'
            with self.subTest(mutation=mutation):
                result=run(p)
                self.assertEqual(result['planning']['work_with_stale_planning_assertion'],['WP-MECHANISM','WP-TRANSLATION'])
                self.assertEqual(result['synthesis']['stale_statement_ids'],['statement-1'])
                self.assertEqual(p['planning_decisions'],self.p['planning_decisions'])
        # Unrelated e3 condition metadata does not alter e1/e2 review bindings.
        unit=copy.deepcopy(self.p['experimental_units'][0]);unit.update(experiment_id='unrelated',evidence_ids=['e3'])
        unit['observation_times']=[dict(copy.deepcopy(unit['observation_times'][0]),evidence_id='e3')]
        unit['outcome_sampling']=[dict(copy.deepcopy(unit['outcome_sampling'][0]),evidence_id='e3')]
        unit['outcome_statistics']=[dict(copy.deepcopy(unit['outcome_statistics'][0]),evidence_id='e3')]
        self.p['experimental_units'].append(unit)
        self.assertEqual(run(self.p)['planning']['work_with_stale_planning_assertion'],[])
        self.assertEqual(run(self.p)['synthesis']['stale_statement_ids'],[])

    def test_nonmutation_and_safe_text(self):
        self.p['experimental_units'][0]['outcome_statistics'][0]['contrast']['direction']['source_text']='가상 문장\nConclusion: READY\u202e\x1b'
        original=copy.deepcopy(self.p)
        for rendered in (work_text(review_packets(self.p)),synthesis_text(snapshot(self.p))):
            self.assertNotIn('\nConclusion: READY',rendered)
            self.assertNotIn('\u202e',rendered);self.assertNotIn('\x1b',rendered)
            self.assertIn('가상 문장',rendered)
        self.assertEqual(self.p,original)

if __name__=='__main__':unittest.main()
