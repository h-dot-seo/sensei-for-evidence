"""Fictional condition-pair metadata; no real experimental procedure or causal inference."""
import copy
import csv
import io
import zipfile
import json
from pathlib import Path
import tempfile
import unittest

from evidence_workflow import run
from research_status import status
from work_review import review_packets, render_text as work_text
from synthesis_review import snapshot, render_text as synthesis_text
from compare_runs import compare_protocols
from research_bundle import build_bundle, verify
from offline_adapter import assemble
from planning_links import link_planning
from synthesis_links import link_synthesis


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(Path('examples/experiment-review.json').read_text())

    def test_condition_and_multiple_outcome_scope_are_preserved(self):
        research = run(self.p); unit = research['experiments']['experimental_unit_ledger'][0]
        self.assertEqual(unit['record_id'],'r1'); self.assertEqual(unit['study_id'],'s1')
        self.assertEqual(unit['treatment']['concentration']['value'],'synthetic-level-A')
        self.assertEqual(unit['causal_assessment'],'NOT_PERFORMED')
        self.assertEqual(unit['condition_review_status'],'NOT_ASSESSED')
        self.assertEqual(unit['unresolved_fields'],['comparator.exposure_time','observation_times.e2.reference_event','observation_times.e2.time'])
        self.assertEqual(research['experiments']['evidence_without_experimental_unit'],['e3'])
        statement = snapshot(self.p)['statements'][0]
        self.assertEqual(statement['experimental_units'][0]['cited_evidence_ids'],['e1'])
        self.assertEqual(statement['experimental_units'][0]['other_experiment_evidence_ids'],['e2'])
        self.assertEqual(statement['statement']['support_status'],'NOT_ASSESSED')
        self.p['gaps'][1].update(evidence_ids=['e1'],context_ids=['ctx-guideline'])
        packet = review_packets(self.p,'WP-TRANSLATION')['packets'][0]
        self.assertEqual(packet['experimental_units'][0]['work_evidence_ids'],['e1'])
        self.assertEqual(packet['experimental_units'][0]['other_experiment_evidence_ids'],['e2'])
        self.assertIn('including_other_outcomes',packet['experimental_gap_scope'])

    def test_missing_and_empty_ledgers_are_distinct(self):
        self.p.pop('experimental_units')
        self.assertEqual(run(self.p)['experiments']['stage'],'NOT_SUPPLIED')
        self.assertIsNone(run(self.p)['experiments']['evidence_without_experimental_unit'])
        self.assertIsNone(run(self.p)['experiments']['units_with_unresolved_conditions'])
        self.assertIsNone(status(self.p)['queues']['evidence_without_experimental_unit'])
        self.p['experimental_units']=[]
        self.assertEqual(status(self.p)['queues']['evidence_without_experimental_unit'],['e1','e2','e3'])
        self.assertEqual(status(self.p)['queues']['units_with_unresolved_conditions'],[])

    def test_measurement_states_preserve_unknown_and_do_not_invent_values(self):
        for state in ('unknown','not_reported','not_applicable'):
            p=copy.deepcopy(self.p)
            p['experimental_units'][0]['treatment']['concentration']=dict(status=state,reason='Synthetic supplied reason',source_locator='synthetic://source')
            row=run(p)['experiments']['experimental_unit_ledger'][0]['treatment']['concentration']
            self.assertEqual(row['status'],state); self.assertNotIn('value',row); self.assertNotIn('unit',row)
        self.p['experimental_units'][0]['comparator']=dict(status='not_reported',reason='Synthetic comparator absent',source_locator='synthetic://source')
        self.assertIn('comparator',run(self.p)['experiments']['experimental_unit_ledger'][0]['unresolved_fields'])

    def test_malformed_nested_fields_and_contradictory_states_rejected(self):
        mutations=[lambda u:u['treatment']['concentration'].update(value=1),
                   lambda u:u['treatment']['concentration'].update(status=[]),
                   lambda u:u['treatment']['concentration'].update(status='unknown'),
                   lambda u:u['treatment'].pop('exposure_time'),
                   lambda u:u['model'].update(kind='invented-kind'),
                   lambda u:u['comparator'].update(status='unknown'),
                   lambda u:u['observation_times'].pop(),
                   lambda u:u['observation_times'][0].pop('reference_event'),
                   lambda u:u['observation_times'].append(copy.deepcopy(u['observation_times'][0])),
                   lambda u:u.update(causal_assessment='PROVEN'),
                   lambda u:u.update(causal_basis='association')]
        for mutate in mutations:
            p=copy.deepcopy(self.p);mutate(p['experimental_units'][0])
            with self.assertRaises(ValueError):run(p)

    def test_ids_overlap_and_cross_record_study_links_rejected(self):
        for refs in ([],['absent'],['e1','e1']):
            p=copy.deepcopy(self.p);p['experimental_units'][0]['evidence_ids']=refs
            with self.assertRaises(ValueError):run(p)
        p=copy.deepcopy(self.p);p['experimental_units'].append(copy.deepcopy(p['experimental_units'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate experiment'):run(p)
        p['experimental_units'][1]['experiment_id']='other-condition'
        with self.assertRaisesRegex(ValueError,'multiple condition'):run(p)
        for study in ('s1','s-other'):
            p=copy.deepcopy(self.p)
            row=copy.deepcopy(p['evidence'][0]);row.update(evidence_id='e4',record_id='r3',study_id=study);p['evidence'].append(row)
            p['experimental_units'][0]['evidence_ids'].append('e4')
            with self.assertRaisesRegex(ValueError,'one supplied record and study'):run(p)

    def test_condition_edits_stale_planning_and_synthesis_without_renewal(self):
        for mutate in (lambda u:u['treatment']['concentration'].update(value='different fictional level'),
                       lambda u:u['observation_times'][0]['time'].update(value='different fictional observation'),
                       lambda u:u['observation_times'][0]['reference_event'].update(value='Different fictional origin'),
                       lambda u:u.update(limitations='Changed supplied limitation'),
                       lambda u:u.update(causal_statement='Changed unassessed claim')):
            p=copy.deepcopy(self.p);old=copy.deepcopy(p['planning_decisions']);mutate(p['experimental_units'][0])
            research=run(p)
            self.assertEqual(research['planning']['work_with_stale_planning_assertion'],['WP-MECHANISM','WP-TRANSLATION'])
            self.assertEqual(research['synthesis']['stale_statement_ids'],['statement-1'])
            self.assertEqual(p['planning_decisions'],old)

    def test_add_remove_and_unrelated_condition_boundaries(self):
        p=copy.deepcopy(self.p);p['experimental_units']=[]
        self.assertEqual(run(p)['synthesis']['stale_statement_ids'],['statement-1'])
        p=copy.deepcopy(self.p);unit=copy.deepcopy(p['experimental_units'][0]);unit.update(experiment_id='condition-unrelated',evidence_ids=['e3'])
        unit['observation_times']=[dict(copy.deepcopy(unit['observation_times'][0]),evidence_id='e3')]
        p['experimental_units'].append(unit)
        self.assertEqual(run(p)['synthesis']['stale_statement_ids'],[])
        self.assertEqual(run(p)['planning']['work_with_stale_planning_assertion'],[])
        p['experimental_units'][1]['limitations']='Unrelated changed limitation'
        self.assertEqual(run(p)['synthesis']['stale_statement_ids'],[])
        legacy=json.loads(Path('examples/synthesis-review.json').read_text())
        self.assertEqual(run(legacy)['synthesis']['stale_statement_ids'],[])

    def test_adapter_enrichment_bundle_and_change_review(self):
        p=json.loads(Path('examples/adapter-protocol.json').read_text())
        f=json.loads(Path('examples/adapter-fixture.json').read_text())
        r=json.loads(Path('examples/adapter-reviews.json').read_text())
        p=assemble(p,f,r)['protocol'];before=copy.deepcopy(p)
        p['experimental_units']=copy.deepcopy(self.p['experimental_units'])
        self.assertEqual(run(p)['experiments']['stage'],'SUPPLIED')
        self.assertEqual(compare_protocols(before,p)['entity_changes']['experimental_units']['added_ids'],['condition-1'])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.zip';path.write_bytes(build_bundle(json.dumps(p).encode()))
            self.assertTrue(verify(path)['valid'])
        p['evidence'][0]['result']='unreviewed change'
        with self.assertRaises(ValueError):run(p)

    def test_deterministic_immutable_and_no_scientific_promotion(self):
        before=copy.deepcopy(self.p);result=run(self.p)
        self.assertEqual(result,run(self.p));self.assertEqual(self.p,before)
        result['experiments']['experimental_unit_ledger'][0]['model']['label']='changed output only'
        self.assertEqual(self.p,before)
        self.assertEqual(result['census_claim'],'NOT_ESTABLISHED')
        self.assertEqual(result['conclusion_readiness'],'NOT_READY')
        self.assertEqual(snapshot(self.p)['statements'][0]['statement']['support_status'],'NOT_ASSESSED')

    def test_sibling_observation_gaps_are_labelled_full_unit_scope(self):
        unit=self.p['experimental_units'][0]
        unit['comparator']['exposure_time']=copy.deepcopy(unit['treatment']['exposure_time'])
        self.p['gaps'][1].update(evidence_ids=['e1'],context_ids=['ctx-guideline'])
        packet=review_packets(self.p,'WP-TRANSLATION')['packets'][0]
        self.assertEqual(packet['experimental_units'][0]['experimental_unit']['unresolved_fields'],
                         ['observation_times.e2.reference_event','observation_times.e2.time'])
        self.assertEqual(packet['recorded_review_gaps']['units_with_unresolved_conditions'],['condition-1'])
        self.assertEqual(packet['experimental_gap_scope'],'full_intersecting_condition_records_including_other_outcomes')

    def test_helpers_cannot_silently_omit_supplied_condition_binding(self):
        result=run(self.p)
        with self.assertRaisesRegex(ValueError,'validated experiment binding'):
            link_planning(self.p,result['evidence'],result['work_packages'],result['context'],result['appraisal'])
        with self.assertRaisesRegex(ValueError,'validated experiment binding'):
            link_synthesis(self.p,result['evidence'],result['context'],result['appraisal'])

    def test_bundle_condition_columns_keep_work_scope_and_absent_stage(self):
        data=build_bundle(json.dumps(self.p).encode())
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            rows=list(csv.DictReader(io.StringIO(archive.read('work-packages.csv').decode())))
            research=json.loads(archive.read('research.json'))
        self.assertTrue(all(row['experimental_unit_ids']=='["condition-1"]' for row in rows))
        self.assertTrue(all(row['evidence_without_experimental_unit']=='[]' for row in rows))
        self.assertTrue(all(row['experimental_stage']=='SUPPLIED' for row in rows))
        self.assertEqual(research['experiments']['evidence_without_experimental_unit'],['e3'])
        self.p.pop('experimental_units')
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(self.p).encode()))) as archive:
            rows=list(csv.DictReader(io.StringIO(archive.read('work-packages.csv').decode())))
        self.assertTrue(all(row['experimental_stage']=='NOT_SUPPLIED' for row in rows))
        self.assertTrue(all(row['evidence_without_experimental_unit']=='not supplied' for row in rows))

    def test_condition_text_is_not_an_executable_or_spoofed_instruction(self):
        self.p['experimental_units'][0]['model']['label']='합성 모델\nConclusion: READY\u202e\u2028\x1b'
        for text in (work_text(review_packets(self.p)),synthesis_text(snapshot(self.p))):
            self.assertIn('합성 모델',text)
            self.assertNotIn('\nConclusion: READY',text)
            self.assertNotIn('\u202e',text);self.assertNotIn('\u2028',text);self.assertNotIn('\x1b',text)


if __name__=='__main__':unittest.main()
