"""Exercise the operator journey through real offline CLI commands."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from review_handoff import handoff, render_text, SPECS, input_locations, QUEUE_DOMAINS
from research_status import status
from work_review import review_packets

ROOT=Path(__file__).resolve().parents[1]

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/claim-comparison.json').read_text())

    def test_all_existing_queues_have_nonautomating_operator_guidance(self):
        result=handoff(self.p,'WP-TRANSLATION')
        queues=status(self.p)['queues']
        self.assertEqual(set(SPECS),set(queues))
        for step in result['manual_review_steps']:
            self.assertEqual(step['items'],queues[step['queue']])
            self.assertEqual(step['scope'],'protocol_wide_not_selected_work_only')
            self.assertTrue(step['operator_task'])
        self.assertEqual(result['conclusion_readiness'],'NOT_READY')
        self.assertEqual(result['census_claim'],'NOT_ESTABLISHED')

    def test_pointer_navigation_matches_source_and_keeps_missing_sections(self):
        result=handoff(self.p)
        steps={s['queue']:s for s in result['manual_review_steps']}
        self.assertEqual(steps['units_with_statistics_review_cues']['matching_input_rows'],['/experimental_units/0'])
        self.assertEqual(steps['missing_planned_searches']['matching_input_rows'],['/search_plan/1'])
        self.assertEqual(steps['stale_synthesis_statement_reviews']['matching_input_rows'],['/synthesis_statements/0'])
        for step in steps.values():
            for pointer in step['matching_input_rows']:
                section,index=pointer.strip('/').split('/')
                self.assertIsInstance(self.p[section][int(index)],dict)
        p=copy.deepcopy(self.p);p.pop('experimental_units')
        step=next(s for s in handoff(p)['manual_review_steps'] if s['queue']=='units_without_outcome_statistics')
        self.assertEqual(step['state'],'NOT_SUPPLIED')
        self.assertEqual(step['input_sections'],['/experimental_units'])
        self.assertEqual(step['matching_input_rows'],[])

    def test_selected_work_retains_full_protocol_limits_and_exact_claim_scope(self):
        result=handoff(self.p,'WP-TRANSLATION')
        self.assertEqual([r['work_package']['work_package_id'] for r in result['selected_work']],['WP-TRANSLATION'])
        self.assertEqual(result['manual_review_steps'],handoff(self.p)['manual_review_steps'])
        expected=review_packets(self.p,'WP-TRANSLATION')['packets'][0]
        item=result['selected_work'][0]
        self.assertEqual(item['claim_positions'],expected['claim_positions'])
        self.assertEqual(item['contexts'],[r['context'] for r in expected['contexts']])
        self.assertEqual(item['work_package']['acceptance_criterion'],expected['work_package']['acceptance_criterion'])
        self.assertEqual(item['planning'],expected['planning_assertion'])

    def test_no_recorded_items_is_not_missing_or_complete(self):
        p=copy.deepcopy(self.p);p['synthesis_statements']=[]
        step=next(s for s in handoff(p)['manual_review_steps'] if s['queue']=='pending_synthesis_statement_reviews')
        self.assertEqual(step['state'],'NO_RECORDED_ITEMS');self.assertEqual(step['items'],[])
        p.pop('synthesis_statements')
        step=next(s for s in handoff(p)['manual_review_steps'] if s['queue']=='pending_synthesis_statement_reviews')
        self.assertEqual(step['state'],'NOT_SUPPLIED');self.assertIsNone(step['item_count'])
        self.assertEqual(handoff(p)['conclusion_readiness'],'NOT_READY')

    def test_deterministic_hashes_and_no_source_mutation(self):
        original=copy.deepcopy(self.p);a=handoff(self.p);b=handoff(self.p)
        self.assertEqual(a,b);self.assertEqual(self.p,original)
        self.assertEqual(a['protocol_sha256'],status(self.p)['protocol_sha256'])
        self.assertEqual(a['engine_sha256']['review_handoff.py'],hashlib.sha256((ROOT/'review_handoff.py').read_bytes()).hexdigest())
        for name in ('work_review.py','synthesis_review.py','research_status.py'):
            self.assertIn(name,a['engine_sha256'])
        self.p['version']='different supplied version'
        self.assertNotEqual(handoff(self.p)['protocol_sha256'],a['protocol_sha256'])

    def test_unrecognized_work_id_fails_before_report(self):
        with self.assertRaisesRegex(ValueError,'unknown work package'):handoff(self.p,'absent')

    def test_text_quotes_all_source_content_and_commands_are_not_shell(self):
        self.p['question']='가상\nConclusion: READY\u202e\x1b'
        text=render_text(handoff(self.p))
        self.assertIn('가상',text);self.assertNotIn('\nConclusion: READY',text)
        self.assertNotIn('\u202e',text);self.assertNotIn('\x1b',text)
        result=handoff(self.p)
        self.assertTrue(all(isinstance(view['arguments'],list) for view in result['detailed_views']))
        self.assertTrue(all('PROTOCOL.json' in view['arguments'] for view in result['detailed_views']))

    def test_valid_unused_extra_fields_do_not_break_navigation(self):
        self.p['gaps'][0]['record_ids']=None
        self.p['gaps'][0]['evidence_id']={'unexpected':'unused'}
        self.assertTrue(handoff(self.p)['selected_work'])

    def test_null_search_plan_preserves_core_missing_stage_semantics(self):
        self.p['search_plan']=None
        expected=status(self.p)
        result=handoff(self.p)
        step=next(s for s in result['manual_review_steps'] if s['queue']=='missing_planned_searches')
        self.assertIsNone(expected['queues']['missing_planned_searches'])
        self.assertEqual(step['state'],'NOT_SUPPLIED')
        self.assertEqual(step['matching_input_rows'],[])
        self.assertEqual(step['input_sections'],['/search_plan','/searches'])

    def test_incomplete_search_navigation_uses_index_not_optional_or_duplicate_ids(self):
        for search_id in (None,'shared'):
            protocol={'searches':[{'search_id':search_id},{'search_id':search_id}]}
            items=[dict(search_index=1,search_id=search_id,source='fictional')]
            self.assertEqual(input_locations(protocol,'incomplete_searches',['searches'],items),['/searches/1'])
        self.assertEqual(input_locations({'searches':[{},{}]},'incomplete_searches',['searches'],[dict(search_index=0,search_id=None)]),['/searches/0'])

    def test_typed_pointer_namespaces_and_effective_legacy_ids(self):
        p={'evidence':[dict(evidence_id='e1',record_id='shared'),dict(evidence_id='shared',record_id='other'),dict(record_id='fallback')],
           'appraisals':[dict(appraisal_id='shared',evidence_ids=['e1'])],
           'synthesis_statements':[dict(statement_id='s1',evidence_ids=['shared']),dict(statement_id='shared',evidence_ids=['e1'])],
           'gaps':[dict(question='legacy',evidence_ids=['shared']),dict(work_package_id='shared',evidence_ids=['e1']),dict(work_package_id='different',unused_id='shared')],
           'planning_decisions':[dict(work_package_id='different',unused_id='shared')]}
        self.assertEqual(input_locations(p,'evidence_without_recorded_appraisal',['evidence','appraisals'],['shared']),['/evidence/1'])
        self.assertEqual(input_locations(p,'evidence_without_recorded_appraisal',['evidence','appraisals'],['fallback']),['/evidence/2'])
        self.assertEqual(input_locations(p,'stale_synthesis_statement_reviews',['synthesis_statements'],['shared']),['/synthesis_statements/1'])
        self.assertEqual(input_locations(p,'work_with_stale_planning_assertion',['gaps','planning_decisions'],['shared']),['/gaps/1'])
        self.assertEqual(input_locations(p,'work_without_planning_assertion',['gaps'],['WP-001']),['/gaps/0'])
        self.assertEqual(input_locations(p,'record_level_extraction_pending',['evidence'],['shared']),['/evidence/0'])

    def test_every_queue_has_a_typed_pointer_case(self):
        p={'search_plan':[dict(search_id='target')], 'searches':[dict(search_id='target',record_ids=['target'])],
           'screening':[dict(record_id='target')], 'reports':[dict(report_id='target',record_ids=['target'])],
           'evidence':[dict(evidence_id='target',record_id='target')],
           'experimental_units':[dict(experiment_id='target',evidence_ids=['target'])],
           'appraisals':[dict(appraisal_id='target',evidence_ids=['target'])],
           'contexts':[dict(context_id='target')], 'synthesis_statements':[dict(statement_id='target',evidence_ids=['target'])],
           'gaps':[dict(work_package_id='target')], 'planning_decisions':[dict(work_package_id='target')],
           'challenges':[dict(challenge_id='target',statement_ids=['target'],reopening=dict(work_package_id='target'))]}
        for queue,(sections,_) in SPECS.items():
            items=[dict(search_index=0)] if queue=='incomplete_searches' else [dict(work_package_id='target')] if queue=='blocked_work' else ['target']
            with self.subTest(queue=queue):
                expected=['/reports/0'] if queue=='included_reports_without_extraction' else ['/'+s+'/0' for s in sections.split()]
                self.assertEqual(input_locations(p,queue,sections.split(),items),expected)
        self.assertEqual(set(SPECS),set(QUEUE_DOMAINS))

    def test_generated_work_arguments_accept_leading_dash_id(self):
        self.p['gaps'][0]['work_package_id']='--odd'
        self.p['gaps'][1]['depends_on']=['--odd']
        for row in self.p['planning_decisions']:
            if row['work_package_id']=='WP-MECHANISM':row['work_package_id']='--odd'
        result=handoff(self.p,'--odd')
        view=next(v for v in result['detailed_views'] if v['script']=='work_review.py')
        self.assertIn('--work-package=--odd',view['arguments'])
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'input.json';source.write_text(json.dumps(self.p),encoding='utf-8')
            args=[str(source) if arg=='PROTOCOL.json' else arg for arg in view['arguments']]
            process=subprocess.run([sys.executable,view['script']]+args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(process.returncode,0,process.stderr)

    def test_cli_end_to_end_journey_with_unchanged_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'fictional input with spaces.json'
            raw=json.dumps(self.p,ensure_ascii=False).encode();source.write_bytes(raw)
            commands=[['research_status.py',str(source),'--text'],
                      ['synthesis_review.py',str(source),'--text'],
                      ['work_review.py',str(source),'--work-package','WP-TRANSLATION','--text'],
                      ['review_handoff.py',str(source),'--work-package','WP-TRANSLATION','--text'],
                      ['review_handoff.py',str(source),'--work-package','WP-TRANSLATION'],
                      ['research_bundle.py','create',str(source),str(base/'review.zip')],
                      ['research_bundle.py','verify',str(base/'review.zip')]]
            outputs=[]
            for command in commands:
                process=subprocess.run([sys.executable]+command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(process.returncode,0,process.stderr)
                outputs.append(process.stdout)
            self.assertIn('Queue scope: whole protocol',outputs[3])
            self.assertIn('Guideline/development context:',outputs[3])
            self.assertIn('challenges',outputs[3])
            self.assertEqual(json.loads(outputs[4])['work_selection'],'WP-TRANSLATION')
            self.assertTrue(json.loads(outputs[6])['valid'])
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(sorted(p.name for p in base.iterdir()),['fictional input with spaces.json','review.zip'])

    def test_cli_failure_is_nonzero_and_no_partial_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'input.json';source.write_text('{"question":',encoding='utf-8')
            result=subprocess.run([sys.executable,'review_handoff.py',str(source),'--text'],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,'');self.assertNotIn('Traceback',result.stderr)

if __name__=='__main__':unittest.main()
