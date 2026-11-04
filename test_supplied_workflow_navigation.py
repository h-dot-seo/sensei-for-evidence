"""Synthetic static handoff discovery tests; not application or scientific review."""
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import research_bundle
from research_status import status
import review_handoff
from work_review import review_packets

ROOT = Path(__file__).resolve().parent
WORKFLOW_IDS = ['native_collection','screening_decision','report_registration','report_retrieval',
                'report_source_declarations','descriptive_inventory','full_text_decision','result_intake','result_review_continuation','condition_intake','appraisal_intake','source_review_work','evidence_review_work','work_completion',
                'collection_archives','report_transition_archive','extraction_transition_archive','work_transition_archive']


def fixture(name):
    return json.loads((ROOT/'examples'/name).read_bytes())


class SuppliedWorkflowNavigationTests(unittest.TestCase):
    def setUp(self):
        self.protocol = fixture('claim-comparison.json')

    def test_static_catalog_is_present_for_every_context_and_work_selection(self):
        first = review_handoff.handoff(self.protocol)['supplied_input_workflows']
        self.assertEqual([item['workflow_id'] for item in first], WORKFLOW_IDS)
        for p, selection in [(self.protocol,'WP-TRANSLATION'),(fixture('bibliographic-base.json'),None),
                             (fixture('report-intake-base.json'),None),(fixture('source-work-protocol.json'),None),
                             (fixture('result-source-current.json'),None)]:
            result = review_handoff.handoff(p,selection)
            self.assertEqual(result['supplied_input_workflows'], first)
            self.assertIn('protocol-independent', result['supplied_input_workflow_scope'])
            self.assertIn('not queue-based eligibility', result['supplied_input_workflow_scope'])
            self.assertEqual(result['census_claim'],'NOT_ESTABLISHED')
            self.assertEqual(result['conclusion_readiness'],'NOT_READY')

    def test_catalog_schema_files_and_parser_help_entrypoints_are_real(self):
        result = review_handoff.handoff(self.protocol)
        entries = []
        for item in result['supplied_input_workflows']:
            self.assertEqual(set(item),{'workflow_id','title','guide_paths','entrypoints','required_human_inputs','boundary'})
            self.assertTrue(item['title'] and item['required_human_inputs'] and item['boundary'])
            for guide in item['guide_paths']:
                self.assertTrue(guide.startswith('docs/'))
                self.assertTrue((ROOT/guide).is_file(),guide)
            for entry in item['entrypoints']:
                self.assertEqual(set(entry),{'script','arguments'})
                self.assertTrue((ROOT/entry['script']).is_file())
                self.assertNotIn('/',entry['script'])
                self.assertEqual(entry['arguments'][-1],'--help')
                self.assertTrue(all(type(x) is str for x in entry['arguments']))
                entries.append(entry)
        self.assertEqual(len(entries),76)
        with tempfile.TemporaryDirectory(prefix='sensei help discovery ') as td:
            for entry in entries:
                checked=subprocess.run([sys.executable,str(ROOT/entry['script']),*entry['arguments']],
                    cwd=td,capture_output=True,timeout=30)
                self.assertEqual(checked.returncode,0,(entry,checked.stderr))
                self.assertIn(b'usage:',checked.stdout)
                self.assertEqual(list(Path(td).iterdir()),[])

    def test_legacy_mock_workflow_is_unchanged_and_not_the_only_route(self):
        result=review_handoff.handoff(self.protocol)
        self.assertEqual(result['manual_input_workflow'],dict(
            precondition='Use a separate declared-plan base with empty searches/evidence and no adapter receipts; do not erase current research',
            template_arguments=['receipt_intake.py','template','BASE_PROTOCOL.json'],
            check_arguments=['receipt_intake.py','check','BASE_PROTOCOL.json','FILLED_MOCK_RECEIPTS.json','--text'],
            scope='Synthetic entry rehearsal only; null template fields need supplied facts, checks never approve receipts'))
        self.assertIn('separate mock receipt rehearsal',result['supplied_input_workflow_scope'])
        self.assertIn('Separate mock receipt rehearsal',review_handoff.render_text(result))

    def test_existing_queues_selected_work_and_protocol_hash_remain_unchanged(self):
        result=review_handoff.handoff(self.protocol,'WP-TRANSLATION')
        state=status(self.protocol)
        self.assertEqual(result['protocol_sha256'],state['protocol_sha256'])
        self.assertEqual({item['queue']:item['items'] for item in result['manual_review_steps']},state['queues'])
        self.assertEqual(result['manual_review_steps'],review_handoff.handoff(self.protocol)['manual_review_steps'])
        self.assertTrue(all(item['scope']=='protocol_wide_not_selected_work_only' for item in result['manual_review_steps']))
        packet=review_packets(self.protocol,'WP-TRANSLATION')['packets'][0]
        self.assertEqual(result['selected_work'][0]['work_package'],packet['work_package'])
        self.assertEqual(result['selected_work'][0]['claim_positions'],packet['claim_positions'])
        self.assertEqual(result['work_selection'],review_packets(self.protocol,'WP-TRANSLATION')['selection'])

    def test_deep_copy_isolation_determinism_and_no_protocol_mutation(self):
        original=copy.deepcopy(self.protocol)
        first=review_handoff.handoff(self.protocol); second=review_handoff.handoff(self.protocol)
        self.assertEqual(first,second);self.assertEqual(self.protocol,original)
        first['supplied_input_workflows'][0]['entrypoints'][0]['arguments'].append('INJECTED')
        first['supplied_input_workflows'][0]['guide_paths'][0]='bad'
        first['supplied_input_workflows'][0]['required_human_inputs'][0]='Changed'
        self.assertEqual(review_handoff.handoff(self.protocol),second)
        self.assertNotIn('INJECTED',repr(review_handoff.SUPPLIED_INPUT_WORKFLOWS))

    def test_source_strings_are_not_interpolated_and_rendering_quotes_controls(self):
        base=review_handoff.handoff(self.protocol)['supplied_input_workflows']
        p=copy.deepcopy(self.protocol);p['question']='가상\nConclusion: READY\u202e\x1b'
        result=review_handoff.handoff(p)
        self.assertEqual(result['supplied_input_workflows'],base)
        text=review_handoff.render_text(result)
        self.assertNotIn('\nConclusion: READY',text);self.assertNotIn('\u202e',text);self.assertNotIn('\x1b',text)
        for item in result['supplied_input_workflows']:
            self.assertIn(item['workflow_id'],text)
            for path in item['guide_paths']:self.assertIn(path,text)
        # Even a caller-edited output catalog is displayed as quoted data.
        result['supplied_input_workflows'][0]['title']='forged\nConclusion: READY\x1b'
        self.assertNotIn('\nConclusion: READY',review_handoff.render_text(result))

    def test_workflow_limits_keep_human_choices_and_archive_scopes_separate(self):
        catalog={r['workflow_id']:r for r in review_handoff.handoff(self.protocol)['supplied_input_workflows']}
        self.assertIn('docs/RIS_INTAKE.md',catalog['native_collection']['guide_paths'])
        self.assertIn('file-occurrence labels are not publication identity',catalog['native_collection']['boundary'])
        self.assertIn('docs/MANUAL_INVENTORY_INTAKE.md',catalog['descriptive_inventory']['guide_paths'])
        self.assertIn('not inclusion',catalog['descriptive_inventory']['boundary'])
        self.assertIn('without renewal',catalog['descriptive_inventory']['boundary'])
        self.assertIn('No report grouping',catalog['report_registration']['boundary'])
        self.assertIn('Mock-adapter',catalog['report_registration']['boundary'])
        self.assertIn('already retrieved',catalog['report_retrieval']['boundary'])
        self.assertIn('No result',catalog['result_intake']['boundary'])
        self.assertIn('Optional missing stages',catalog['condition_intake']['boundary'])
        self.assertIn('No task, priority, dependency',catalog['source_review_work']['boundary'])
        self.assertIn('do not retain detached application history',catalog['collection_archives']['boundary'])
        archive=catalog['collection_archives']
        self.assertIn('docs/NATIVE_COLLECTION_BUNDLES.md',archive['guide_paths'])
        self.assertEqual([entry for entry in archive['entrypoints'] if entry['script']=='native_collection_bundle.py'],
                         [dict(script='native_collection_bundle.py',arguments=[command,'--help'])
                          for command in ('create','verify')])
        self.assertIn('explicit ris, nbib or nbib_batch format',' '.join(archive['required_human_inputs']))
        scope=catalog['report_transition_archive']['boundary']
        self.assertIn('Only registration, retrieval-update and full-text',scope)
        self.assertIn('result and condition operations are outside',scope)
        self.assertIn('earlier/later history is unassessed',scope)

    def test_appraisal_route_keeps_judgements_and_downstream_review_separate(self):
        catalog = {r['workflow_id']: r for r in review_handoff.handoff(self.protocol)['supplied_input_workflows']}
        route = catalog['appraisal_intake']
        self.assertIn('docs/MANUAL_APPRAISAL_INTAKE.md', route['guide_paths'])
        self.assertEqual(route['entrypoints'], [dict(script='appraisal_intake.py', arguments=[c,'--help'])
                                               for c in ('template','target','assemble','verify')]
                         + [dict(script='appraisal_source_review.py', arguments=['--help'])])
        self.assertIn('docs/APPRAISAL_SOURCE_REVIEW.md', route['guide_paths'])
        for phrase in ['Conflicting positions remain separate', 'no score, consensus', 'not proof of reading',
                       'hashes are not renewed', 'source-status cues may change']:
            self.assertIn(phrase, route['boundary'])

    def test_work_segment_route_keeps_historical_completion_bounds(self):
        catalog = {r['workflow_id']: r for r in review_handoff.handoff(self.protocol)['supplied_input_workflows']}
        route = catalog['work_transition_archive']
        self.assertEqual(route['guide_paths'], ['docs/WORK_TRANSITION_BUNDLES.md'])
        self.assertEqual(route['entrypoints'], [dict(script='work_transition_bundle.py', arguments=[c,'--help'])
                                               for c in ('create','verify')])
        for phrase in ['Only source-work intake, evidence-work intake and single-work completion',
                       'No review/completion is renewed', 'Explicit step IDs', 'complete project history']:
            self.assertIn(phrase, route['boundary'])

    def test_completion_route_keeps_acceptance_and_existing_completion_boundaries(self):
        catalog = {r['workflow_id']: r for r in review_handoff.handoff(self.protocol)['supplied_input_workflows']}
        route = catalog['work_completion']
        self.assertEqual(route['entrypoints'], [dict(script='work_completion_intake.py', arguments=[c,'--help'])
                                               for c in ('template','target','assemble','verify')])
        self.assertIn('docs/WORK_COMPLETION_INTAKE.md', route['guide_paths'])
        for phrase in ['one unfinished work completion', 'no artifact access, acceptance assessment',
                       'cannot be renewed or reopened', 'Stale/unbound prerequisite', 'blocking may change']:
            self.assertIn(phrase, route['boundary'])

    def test_evidence_work_route_retains_explicit_review_and_scope(self):
        catalog = {r['workflow_id']: r for r in review_handoff.handoff(self.protocol)['supplied_input_workflows']}
        route = catalog['evidence_review_work']
        self.assertEqual(route['entrypoints'], [dict(script='evidence_work_intake.py', arguments=[c,'--help'])
                                               for c in ('template','target','assemble','verify')])
        self.assertIn('docs/EVIDENCE_WORK_INTAKE.md', route['guide_paths'])
        for text in ['Only new PLANNED', 'No result, scientific task', 'Source-review work is not converted',
                     'source_refs/document_source_ids are rejected', 'not recursive source approval']:
            self.assertIn(text, route['boundary'])

    def test_source_declaration_route_separates_append_from_byte_inspection(self):
        catalog = {r['workflow_id']: r for r in review_handoff.handoff(self.protocol)['supplied_input_workflows']}
        route = catalog['report_source_declarations']
        self.assertEqual(route['entrypoints'],
            [dict(script='report_source_intake.py', arguments=[c, '--help']) for c in ('template','target','assemble','verify')] +
            [dict(script='report_source_check.py', arguments=[c, '--help']) for c in ('template','check')])
        self.assertIn('docs/MANUAL_SOURCE_DECLARATIONS.md', route['guide_paths'])
        for phrase in ['Old null digests remain unbound', 'native Windows fails closed',
                       'without renewal', 'source locator is followed automatically']:
            self.assertIn(phrase, route['boundary'])

    def test_extraction_segment_discovery_preserves_historical_context_boundary(self):
        catalog = {r['workflow_id']: r for r in review_handoff.handoff(self.protocol)['supplied_input_workflows']}
        route = catalog['extraction_transition_archive']
        self.assertEqual(route['guide_paths'], ['docs/EXTRACTION_TRANSITION_BUNDLES.md'])
        self.assertEqual(route['entrypoints'], [dict(script='extraction_transition_bundle.py', arguments=[c, '--help'])
                                               for c in ('create', 'verify')])
        self.assertIn('recorded step context', ' '.join(route['required_human_inputs']))
        for text in ['result intake, result-text correction and descriptive condition intake',
                     'No earlier review is renewed', 'downstream work reassessed', 'earlier/later history',
                     'complete history and extraction completeness remain unestablished']:
            self.assertIn(text, route['boundary'])

    def test_result_continuation_distinguishes_comparison_from_reviewed_correction(self):
        result=review_handoff.handoff(fixture('result-source-current.json'))
        route=next(r for r in result['supplied_input_workflows'] if r['workflow_id']=='result_review_continuation')
        self.assertEqual(route['guide_paths'],['docs/RESULT_SOURCE_REVIEW.md','docs/RESULT_CORRECTIONS.md'])
        self.assertEqual(route['entrypoints'],[
            dict(script='result_source_review.py',arguments=['--help']),
            *[dict(script='result_correction.py',arguments=[command,'--help'])
              for command in ('target','assemble','verify')]])
        inputs=' '.join(route['required_human_inputs'])
        for required in ['original protocol','retained manual-result intake application','current protocol',
                         'selected source references','separate exact-target review','recorded implementation',
                         'do not re-import a corrected copy under a new ID']:
            self.assertIn(required,inputs)
        for boundary in ['not historical lineage or approval','only result/limitations text',
                         'preserving IDs, row order and counts','does not renew earlier reviews',
                         'reassess all downstream assertions','never selects a correction automatically']:
            self.assertIn(boundary,route['boundary'])
        self.assertEqual({row['queue']:row['items'] for row in result['manual_review_steps']},
                         status(fixture('result-source-current.json'))['queues'])

    def test_discovery_never_executes_commands_or_opens_source_locators(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('No execution')), \
             patch.object(socket,'create_connection',side_effect=AssertionError('No network')):
            result=review_handoff.handoff(self.protocol)
            self.assertTrue(result['supplied_input_workflows'])
        self.assertEqual(result['manual_work_remaining'],review_handoff.handoff(self.protocol)['manual_work_remaining'])

    def test_handoff_hash_changes_only_its_own_scope_not_replay_engine_files(self):
        result=review_handoff.handoff(self.protocol)
        self.assertEqual(result['engine_sha256']['review_handoff.py'],hashlib.sha256((ROOT/'review_handoff.py').read_bytes()).hexdigest())
        self.assertNotIn('review_handoff.py',research_bundle.ENGINE_FILES)
        import report_intake,report_retrieval,report_transition_bundle,result_intake,result_correction,result_source_review
        for hashes in [report_intake._implementation_hashes(),report_retrieval._implementation_hashes(),report_transition_bundle.implementation_hashes(),
                       result_intake._implementation_hashes(),result_correction._implementation_hashes(),result_source_review._implementation_hashes()]:
            self.assertNotIn('review_handoff.py',hashes)

    def test_cli_json_text_spaces_and_leading_dash_work_id_write_no_files(self):
        p=fixture('report-intake-base.json')
        p['gaps']=[dict(work_package_id='--literal-id',work_type='source_review',question='Synthetic question',
            deliverable='Synthetic note',acceptance_criterion='Synthetic criterion',evidence_ids=[],
            source_refs=[dict(kind='record',record_id='r1')],depends_on=[],status='PLANNED')]
        with tempfile.TemporaryDirectory(prefix='sensei catalog cli ') as td:
            root=Path(td);source=root/'protocol with spaces.json';source.write_text(json.dumps(p),encoding='utf-8')
            before=source.read_bytes()
            for text in [False,True]:
                args=[sys.executable,str(ROOT/'review_handoff.py'),str(source),'--work-package=--literal-id']
                if text:args.append('--text')
                result=subprocess.run(args,cwd=td,capture_output=True,timeout=30,
                    env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))
                self.assertEqual(result.returncode,0,result.stderr)
                if text:self.assertIn(b'Supplied-input workflow discovery',result.stdout)
                else:self.assertEqual([r['workflow_id'] for r in json.loads(result.stdout)['supplied_input_workflows']],WORKFLOW_IDS)
                self.assertEqual(source.read_bytes(),before);self.assertEqual(list(root.iterdir()),[source])

    def test_invalid_input_still_fails_before_any_handoff_output(self):
        p=copy.deepcopy(self.protocol);p['screening'][0]['record_id']='unknown-record'
        with self.assertRaises(ValueError):review_handoff.handoff(p)
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'bad.json';source.write_text('{"question":1,"question":2}')
            result=subprocess.run([sys.executable,str(ROOT/'review_handoff.py'),str(source)],cwd=td,capture_output=True,timeout=30)
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
            self.assertEqual(list(Path(td).iterdir()),[source])


if __name__=='__main__':
    unittest.main()
