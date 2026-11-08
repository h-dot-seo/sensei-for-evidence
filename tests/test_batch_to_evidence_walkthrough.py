"""Execute the fixed synthetic NBIB-to-evidence documentation, not perform review."""
import copy
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
import zipfile

from evidence_workflow import run
from prisma_audit import export_audit
from prisma_reports import report_flow
import report_intake
import report_retrieval
import bibliographic_review
import nbib_batch_intake
import batch_collection_bundle
import result_intake
import screening_decision
from research_status import status
from json_io import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'examples' / 'batch-to-evidence'


def load(path):
    return json.loads(Path(path).read_bytes())


class BatchToEvidenceWalkthroughTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sensei batch evidence ')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name)
        allowed = {'nbib_batch_intake.py', 'bibliographic_review.py', 'screening_decision.py',
                   'report_intake.py', 'report_retrieval.py', 'report_decision.py', 'result_intake.py',
                   'condition_intake.py', 'prisma_audit.py', 'research_status.py', 'batch_collection_bundle.py',
                   'search_manifest.py', 'result_source_review.py', 'compare_runs.py'}
        def execute(guide):
            doc = (ROOT/'docs'/guide).read_text(encoding='utf-8')
            commands = [line for block in re.findall(r'```sh\n(.*?)```', doc, re.S)
                        for line in block.splitlines() if line.strip()]
            stdout = []
            for line in commands:
                tokens = shlex.split(line)
                if len(tokens) < 2 or tokens[0] != 'python' or tokens[1] not in allowed:
                    raise AssertionError('Unexpected walkthrough command: '+line)
                cmd = [sys.executable] + [token.replace('OUTPUT', str(cls.output)) for token in tokens[1:]]
                result = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=60,
                    env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONUTF8='0'))
                if result.returncode:
                    raise AssertionError((line, result.stderr.decode('utf-8')))
                stdout.append(json.loads(result.stdout))
            return commands, stdout
        cls.commands, cls.stdout = execute('BATCH_TO_EVIDENCE.md')
        cls.final = load(cls.output/'final.json')
        cls.original_output_bytes = {p.name:p.read_bytes() for p in cls.output.iterdir()}
        cls.continuation_commands, cls.continuation_stdout = execute('SECOND_SEARCH_CONTINUATION.md')
        cls.continued = load(cls.output/'continued.json')


    def test_all_documented_commands_run_with_outside_space_named_directory(self):
        self.assertEqual(len(self.commands), 30)
        self.assertTrue(all(isinstance(value, dict) for value in self.stdout))
        self.assertTrue(self.stdout[-1]['valid'])
        self.assertNotIn('adapter_receipts', self.final)
        self.assertTrue((self.output/'batch-to-evidence.zip').is_file())

    def test_five_raw_rows_remain_distinct_from_three_declared_memberships(self):
        batch = load(self.output/'batch.json')
        intake = load(self.output/'intake.json')
        self.assertEqual(batch['source_grouping']['recorded_occurrences'], 5)
        self.assertEqual(batch['source_grouping']['source_count'], 2)
        self.assertEqual(len(intake['parsed_export']['record_rows']), 5)
        choices = load(FIXTURES/'collection-choices.json')['resolutions']
        self.assertEqual([r['disposition'] for r in choices],
                         ['new_record','same_record','new_record','do_not_promote','new_record'])
        self.assertEqual(choices[0]['record_id'], choices[1]['record_id'])
        self.assertIsNone(choices[3]['record_id'])
        collected = load(self.output/'collected.json')
        self.assertEqual(collected['searches'][0]['record_ids'], ['record-A','record-B','record-C'])
        self.assertEqual(collected['screening'], [])
        self.assertEqual(collected['evidence'], [])
        self.assertEqual(collected['bibliographic_imports'], self.final['bibliographic_imports'])
        entry = self.final['bibliographic_imports']['imports'][0]
        self.assertEqual(entry['resolutions'], choices)
        self.assertEqual(entry['intake']['source_export'], intake['source_export'])
        audit = export_audit(self.final); counts = {n['node_id']:n['count'] for n in audit['nodes']}
        self.assertEqual(counts['identified_occurrences'], 3)
        self.assertEqual(counts['unique_records'], 3)
        self.assertEqual(counts['repeated_exact_id_occurrences'], 0)

    def test_blank_targets_are_not_auto_reviews_and_fixed_assertions_match(self):
        blank = load(self.output/'blank-choices.json')
        self.assertIsNone(blank['review'])
        self.assertTrue(all(row[key] is None for row in blank['resolutions']
                            for key in ('disposition','record_id','rationale')))
        target = load(self.output/'collection-target.json')['review']
        supplied = load(FIXTURES/'collection-review.json')['review']
        self.assertEqual(target['target_sha256'], supplied['target_sha256'])
        self.assertTrue(all(target[key] is None for key in ('reviewer','reviewed_at','rationale','decision')))
        for label in ['A','B','C']:
            blank = load(self.output/f'screen-{label}-target.json')['decision_document']
            supplied = load(FIXTURES/f'screen-record-{label}.json')
            self.assertEqual(blank['target_sha256'], supplied['target_sha256'])
            self.assertIsNone(blank['decision']); self.assertIsNone(blank['adjudicator'])
        for target_name, fixture_name in [('report','reports'),('retrieval','retrieval'),('result','results'),('condition','conditions')]:
            blank = load(self.output/f'{target_name}-target.json')['review_document']
            supplied = load(FIXTURES/f'{fixture_name}-review.json')
            self.assertEqual(blank['target_sha256'], supplied['target_sha256'])
            self.assertTrue(all(value is None for key,value in blank.items() if key not in ('schema_version','target_sha256')))
        blank = load(self.output/'full-text-target.json')['decision_document']
        self.assertEqual(blank['target_sha256'], load(FIXTURES/'full-text.json')['target_sha256'])
        self.assertIsNone(blank['decision']); self.assertIsNone(blank['study_declaration'])

    def test_each_stage_keeps_registration_retrieval_and_eligibility_separate(self):
        screened = load(self.output/'screened.json'); registered = load(self.output/'registered.json')
        retrieved = load(self.output/'retrieved.json'); included = load(self.output/'included.json')
        self.assertEqual(len(screened['screening']), 3); self.assertNotIn('reports', screened)
        self.assertEqual(len(registered['reports']), 2)
        self.assertEqual(registered['reports'][0]['record_ids'], ['record-A','record-B'])
        self.assertEqual([r['retrieval'] for r in registered['reports']], ['retrieved','pending'])
        self.assertTrue(all(r['decision']=='pending' for r in registered['reports']))
        self.assertEqual([r['retrieval'] for r in retrieved['reports']], ['retrieved','retrieved'])
        self.assertTrue(all(r['decision']=='pending' for r in retrieved['reports']))
        self.assertEqual(included['reports'][0]['decision'], 'include')
        self.assertEqual(included['reports'][0]['study_id'], 'study-A')
        self.assertEqual(included['reports'][1]['decision'], 'pending')
        for p in [registered,retrieved,included,self.final]:
            self.assertEqual(p['screening'], screened['screening'])
            self.assertEqual(p['screening_decision_history'], screened['screening_decision_history'])
        self.assertEqual(report_flow(self.final,include_csv=False)['report_flow'],
            dict(sought=2,retrieved=2,not_retrieved=0,retrieval_pending=0,assessed=1,assessment_pending=1,
                 excluded=0,included=1,included_studies=1,reports_with_extraction=1))

    def test_result_and_nonclinical_absences_never_become_inferred_values(self):
        results = load(self.output/'results.json')
        self.assertEqual(len(results['evidence']),2)
        self.assertEqual({r['study_id'] for r in results['evidence']},{'study-A'})
        self.assertEqual({r['record_id'] for r in results['evidence']},{'record-A'})
        self.assertIn('No difference',results['evidence'][0]['result'])
        self.assertEqual(self.final['evidence'],results['evidence'])
        self.assertEqual(self.final['reports'],results['reports'])
        self.assertEqual(len(self.final['experimental_units']),1)
        unit = self.final['experimental_units'][0]
        self.assertEqual(unit['evidence_ids'],['result-1','result-2'])
        missing = [unit['treatment']['concentration'],unit['treatment']['exposure_time'],unit['comparator']]
        missing += [row[key] for row in unit['observation_times'] for key in ('time','reference_event')]
        self.assertTrue(all(row['status']=='unknown' and 'value' not in row for row in missing))
        self.assertEqual(unit['causal_basis'],'unknown')
        audit = export_audit(self.final); counts = {n['node_id']:n['count'] for n in audit['nodes']}
        self.assertEqual(counts['records_with_extraction'],1)
        self.assertEqual(counts['included_records_without_extraction'],2)
        self.assertEqual(counts['included_reports_without_extraction'],0)
        self.assertEqual(counts['extracted_result_rows'],2)
        research = run(self.final)
        self.assertEqual(research['search_plan_audit']['missing_search_ids'],['local-secondary'])
        self.assertEqual(audit['census_claim'],'NOT_ESTABLISHED')
        self.assertEqual(audit['conclusion_readiness'],'NOT_READY')
        self.assertTrue(all(s['complete'] is False and s['total_count'] is None for s in self.final['searches']))

    def test_portable_native_archive_retains_original_bytes_and_not_detached_history(self):
        archive = self.output/'batch-to-evidence.zip'
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            for index,name in enumerate(['pubmed-export.nbib','pubmed-export-additional.nbib']):
                self.assertEqual(z.read(f'native/import-000000/source-{index:06d}.nbib'),(ROOT/'examples'/name).read_bytes())
            self.assertNotIn('report-application.json',names)
            self.assertNotIn('retrieval-application.json',names)
            self.assertNotIn('condition-application.json',names)
        with tempfile.TemporaryDirectory(prefix='sensei relocated batch ') as td:
            relocated = Path(td)/'bundle.zip'; relocated.write_bytes(archive.read_bytes())
            result = subprocess.run([sys.executable,str(ROOT/'batch_collection_bundle.py'),'verify',str(relocated)],
                cwd=td,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])
        original = archive.read_bytes()
        result = subprocess.run([sys.executable,'batch_collection_bundle.py','create',str(self.output/'final.json'),
            str(archive),'--batch','0='+str(self.output/'batch.json')],cwd=ROOT,capture_output=True,timeout=60)
        self.assertNotEqual(result.returncode,0);self.assertEqual(archive.read_bytes(),original)

    def test_exact_fixture_reviews_cannot_be_reused_on_changed_originals(self):
        for module, original, candidates, review, application in [
            (report_intake,'screened.json','reports.json','reports-review.json','report-application.json'),
            (report_retrieval,'registered.json','retrieval.json','retrieval-review.json','retrieval-application.json')]:
            p=load(self.output/original);c=load(FIXTURES/candidates);r=load(FIXTURES/review)
            self.assertTrue(module.verify(p,load(self.output/application))['valid'])
            changed=copy.deepcopy(p);changed['version']='different supplied input'
            with self.assertRaises(ValueError):module.assemble(changed,c,r)
        prior=(self.output/'registered.json').read_bytes()
        result=subprocess.run([sys.executable,'report_intake.py','verify',str(self.output/'screened.json'),
            str(self.output/'report-application.json'),'--protocol-output',str(self.output/'registered.json')],
            cwd=ROOT,capture_output=True,timeout=60)
        self.assertNotEqual(result.returncode,0);self.assertEqual((self.output/'registered.json').read_bytes(),prior)

    def test_secondary_documented_commands_preserve_all_earlier_output_bytes(self):
        self.assertEqual(len(self.continuation_commands),13)
        self.assertTrue(all(isinstance(row,dict) for row in self.continuation_stdout))
        self.assertTrue(self.continuation_stdout[-1]['valid'])
        for name,raw in self.original_output_bytes.items():
            self.assertEqual((self.output/name).read_bytes(),raw,name)
        self.assertEqual(load(self.output/'final.json'),self.final)

    def test_secondary_import_keeps_raw_membership_and_record_units_distinct(self):
        research=run(self.continued)
        self.assertEqual(research['bibliographic_collection']['counts'],dict(
            raw_rows=7,promoted_row_occurrences=6,withheld_rows=1,canonical_search_memberships=5))
        nodes={row['node_id']:row for row in export_audit(self.continued)['nodes']}
        expected={'identified_occurrences':5,'repeated_exact_id_occurrences':1,'unique_records':4,
                  'screened_records':3,'screening_pending_records':1,'reports_retrieved':2,
                  'reports_included':1,'reports_assessment_pending':1,'included_studies':1,'extracted_result_rows':2}
        for name,count in expected.items():self.assertEqual(nodes[name]['count'],count,name)
        self.assertEqual(nodes['repeated_exact_id_occurrences']['member_ids'],['/searches/1/record_ids/0'])
        self.assertEqual(nodes['screening_pending_records']['member_ids'],['record-D'])
        self.assertEqual(self.continued['searches'][1]['record_ids'],['record-A','record-D'])

    def test_secondary_import_only_appends_search_and_flat_receipt(self):
        self.assertEqual(set(self.continued),set(self.final))
        for key,value in self.final.items():
            if key not in ('searches','bibliographic_imports'):
                self.assertEqual(canonical_json_bytes(self.continued[key]),canonical_json_bytes(value),key)
        self.assertEqual(self.continued['searches'][:-1],self.final['searches'])
        old=self.final['bibliographic_imports']; new=self.continued['bibliographic_imports']
        self.assertEqual(new['base_protocol'],old['base_protocol'])
        self.assertEqual(new['imports'][:-1],old['imports'])
        self.assertEqual(new['imports'][1]['prior_prefix_count'],1)
        self.assertEqual(new['imports'][1]['prior_protocol_body'],
                         {k:v for k,v in self.final.items() if k!='bibliographic_imports'})
        self.assertEqual(load(self.output/'secondary-batch.json')['protocol_snapshot'],old['base_protocol'])
        self.assertEqual(self.continued['screening_decision_history'],self.final['screening_decision_history'])

    def test_secondary_target_keeps_choices_separate_and_binds_current_protocol(self):
        blank=load(self.output/'secondary-blank-choices.json')
        self.assertIsNone(blank['review'])
        self.assertTrue(all(row[k] is None for row in blank['resolutions'] for k in ('disposition','record_id','rationale')))
        target=load(self.output/'secondary-target.json')['review']
        supplied=load(ROOT/'examples/second-search/review.json')
        self.assertEqual(target['target_sha256'],supplied['review']['target_sha256'])
        self.assertTrue(all(v is None for k,v in target.items() if k!='target_sha256'))
        self.assertEqual([(r['disposition'],r['record_id']) for r in supplied['resolutions']],
                         [('same_record','record-A'),('new_record','record-D')])
        altered=copy.deepcopy(self.final);altered['version']='different current snapshot'
        with self.assertRaises(ValueError):
            bibliographic_review.assemble(altered,load(self.output/'secondary-intake.json'),supplied)
        with self.assertRaises(ValueError):
            bibliographic_review.assemble(self.continued,load(self.output/'secondary-intake.json'),supplied)

    def test_secondary_does_not_make_an_intermediate_protocol_a_new_common_base(self):
        sources=[dict(source_id='secondary',raw=(ROOT/'examples/second-search/export.nbib').read_bytes())]
        intermediate=nbib_batch_intake.prepare(self.final,sources,'local-secondary','2026-11-04T01:00:00Z')
        choices=load(ROOT/'examples/second-search/choices.json')
        with self.assertRaisesRegex(ValueError,'common base'):
            bibliographic_review.prepare_review(self.final,intermediate['csv_intake'],choices)
        changed=copy.deepcopy(self.final);changed['search_plan'][1]['query']='changed query'
        with self.assertRaises(ValueError):
            bibliographic_review.prepare_review(changed,load(self.output/'secondary-intake.json'),choices)

    def test_secondary_source_comparison_preserves_results_and_exposes_context_drift(self):
        compared=load(self.output/'continued-result-source.json')
        self.assertTrue(compared['original_replay_result']['valid'])
        counts=compared['counts']
        for label,n in [('result',2),('matched_row_link',2),('report_mapping',2),('selected_sources',2),('recorded_report',1)]:
            self.assertEqual(counts[label]['UNCHANGED'],n,label)
            self.assertEqual(counts[label]['CHANGED'],0,label)
        self.assertEqual(counts['source_context']['CHANGED'],1)
        self.assertEqual([r['source_context_status'] for r in compared['rows']],['CHANGED','CHANGED'])
        self.assertEqual(compared['lineage'],'NOT_ESTABLISHED')
        self.assertEqual(compared['renewed_human_review'],'NOT_PERFORMED')
        self.assertFalse(compared['protocol_changed']);self.assertEqual(compared['external_calls'],0)
        self.assertNotIn('valid',compared)
        self.assertTrue(result_intake.verify(load(self.output/'included.json'),load(self.output/'result-application.json'))['valid'])
        with self.assertRaises(ValueError):
            result_intake.verify(self.continued,load(self.output/'result-application.json'))
        history=screening_decision.inspect(self.continued,'record-A')
        self.assertEqual(history['record_history'][0]['current_screening']['decision'],'include')
        self.assertFalse(history['protocol_changed'])
        self.assertEqual(history['receipt_ledger'][0]['current_source_match_status'],'STALE_SOURCE')
        self.assertTrue(history['receipt_ledger'][0]['matches_current_screening'])
        self.assertEqual(history['records_with_history_cues'],['record-A'])

    def test_no_missing_search_is_not_complete_or_ready_after_secondary_import(self):
        current=status(self.continued);audit=export_audit(self.continued)
        self.assertEqual(current['queues']['missing_planned_searches'],[])
        self.assertEqual(len(current['queues']['incomplete_searches']),2)
        self.assertEqual(current['queues']['records_pending_screening'],['record-D'])
        self.assertEqual(current['queues']['reports_pending_assessment'],['report-B'])
        self.assertTrue(all(s['complete'] is False and s['total_count'] is None and s['has_more'] is None
                            for s in self.continued['searches']))
        self.assertEqual(self.continued['experimental_units'],self.final['experimental_units'])
        self.assertEqual(audit['census_claim'],'NOT_ESTABLISHED');self.assertEqual(audit['conclusion_readiness'],'NOT_READY')

    def test_secondary_native_archive_preserves_two_imports_and_relocates(self):
        archive=self.output/'continued-native.zip'
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read('native/import-000001/source-000000.nbib'),
                             (ROOT/'examples/second-search/export.nbib').read_bytes())
            for index,name in enumerate(['pubmed-export.nbib','pubmed-export-additional.nbib']):
                self.assertEqual(z.read(f'native/import-000000/source-{index:06d}.nbib'),(ROOT/'examples'/name).read_bytes())
            self.assertNotIn('result-application.json',z.namelist())
            self.assertNotIn('condition-application.json',z.namelist())
        verified=batch_collection_bundle.verify_bundle(archive.read_bytes())
        self.assertTrue(verified['valid'])
        self.assertEqual(verified['bound_batch_wrappers'],2)
        self.assertEqual(verified['bound_native_sources'],3)
        self.assertEqual(verified['covered_import_indices'],[0,1])
        self.assertEqual(verified['uncovered_import_indices'],[])
        with tempfile.TemporaryDirectory(prefix='sensei second relocated ') as td:
            copied=Path(td)/'continued.zip';copied.write_bytes(archive.read_bytes())
            checked=subprocess.run([sys.executable,str(ROOT/'batch_collection_bundle.py'),'verify',str(copied)],
                                   cwd=td,capture_output=True,timeout=60)
            self.assertEqual(checked.returncode,0,checked.stderr)
            self.assertTrue(json.loads(checked.stdout)['valid'])
        bindings=[dict(import_index=0,nbib_batch_artifact=load(self.output/'secondary-batch.json'))]
        with self.assertRaises(ValueError):
            batch_collection_bundle.build_bundle((self.output/'continued.json').read_bytes(),bindings)

    def test_secondary_guide_links_and_fixture_inventory_are_explicit(self):
        doc=ROOT/'docs/SECOND_SEARCH_CONTINUATION.md'
        for link in re.findall(r'\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            self.assertTrue((doc.parent/link.split('#')[0]).is_file(),link)
        self.assertEqual({p.name for p in (ROOT/'examples/second-search').iterdir()},
                         {'export.nbib','choices.json','review.json'})
        self.assertIn('unused entry in the original plan',doc.read_text(encoding='utf-8'))

    def test_document_links_and_fixture_inventory_are_explicit(self):
        doc=ROOT/'docs/BATCH_TO_EVIDENCE.md'
        for link in re.findall(r'\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            self.assertTrue((doc.parent/link.split('#')[0]).is_file(),link)
        expected={'collection-choices.json','collection-review.json','screen-record-A.json','screen-record-B.json',
                  'screen-record-C.json','reports.json','reports-review.json','retrieval.json','retrieval-review.json',
                  'full-text.json','results.json','results-review.json','conditions.json','conditions-review.json'}
        self.assertEqual({p.name for p in FIXTURES.iterdir()},expected)
        self.assertTrue(all(p.suffix=='.json' for p in FIXTURES.iterdir()))


if __name__=='__main__':
    unittest.main()
