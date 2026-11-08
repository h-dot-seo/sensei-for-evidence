"""Fictional descriptive inventory cannot promote study identity or eligibility."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from evidence_workflow import run
from json_io import canonical_json_bytes
from report_study_inventory_links import (INVENTORY_FIELDS, prepare_targets,
    prepare_candidate_target, link_report_study_inventory)
from report_study_inventory import review, template, render_text
from tests.test_report_study_reviews import protocol

ROOT = Path(__file__).resolve().parents[1]
KEY = 'report_study_inventory'


def assertion(p, report='report-one', study='study-A', recorder='Fictional recorder',
              iid='inventory-1', sources=None, collection=None):
    target = prepare_candidate_target(p, report, study, collection)
    return dict(inventory_id=iid, report_id=report, study_id=study, recorded_by=recorder,
                recorded_at='2026-11-04', description='Fictional supplied candidate description.',
                source_locator='fictional://section-2', source_ids=['main'] if sources is None else sources,
                source_basis_sha256=target['source_basis_sha256'])


class ReportStudyInventoryTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()

    def ledger(self, p=None):
        return link_report_study_inventory(self.p if p is None else p)

    def pending(self, decision='pending'):
        p = copy.deepcopy(self.p)
        p['evidence'] = []; p['gaps'] = []
        p['reports'][0].pop('study_ids')
        p['reports'][0].update(decision=decision, reason='Fictional supplied disposition')
        return p

    def cli(self, path, *args):
        return subprocess.run([sys.executable, str(ROOT/'report_study_inventory.py'), str(path), *args],
                              capture_output=True, cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING='utf-8'))

    def imported(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        helper = BibliographicReviewTests(); helper.setUp(); p = helper.imported()
        rid = p['searches'][0]['record_ids'][0]
        p['screening'] = [dict(record_id=rid, decision='include', reason='Fictional scope')]
        p['reports'] = [dict(report_id='report-one', record_ids=[rid], retrieval='retrieved',
                             locator='fictional://imported', decision='pending')]
        p['report_sources'] = [copy.deepcopy(self.p['report_sources'][0])]
        return p

    def test_absent_empty_and_null_are_distinct(self):
        self.assertNotIn(KEY, run(self.p))
        self.assertEqual(self.ledger()['stage'], 'NOT_SUPPLIED')
        self.p[KEY] = []
        self.assertEqual(run(self.p)[KEY]['stage'], 'SUPPLIED')
        self.assertEqual(self.ledger()['candidate_targets'], [])
        for value in (None, {}, False, '', 0, [None]):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                run(dict(self.p, **{KEY:value}))

    def test_empty_inventory_without_reports_is_valid(self):
        p = self.pending(); p.pop('reports'); p.pop('report_sources'); p[KEY] = []
        result = review(p)
        self.assertEqual(result['report_stage'], 'NOT_SUPPLIED')
        self.assertEqual(result['counts']['reports'], 0)
        self.assertEqual(result['candidate_targets'], [])
        p[KEY] = [assertion(self.p)]
        with self.assertRaises(ValueError): review(p)

    def test_exact_schema_and_nonblank_literal_scalars(self):
        good = assertion(self.p)
        self.assertEqual(set(good), INVENTORY_FIELDS)
        cases = [dict(good, unexpected='x')]
        for field in good:
            row = dict(good); row.pop(field); cases.append(row)
            if field != 'source_ids':
                cases.extend(dict(good, **{field:value}) for value in ('', ' \t\n', None, True, 1, [], {}))
        for row in cases:
            with self.subTest(row=row), self.assertRaises((ValueError, TypeError)):
                self.ledger(dict(self.p, **{KEY:[row]}))

    def test_dates_hashes_and_unknown_reports(self):
        good = assertion(self.p)
        cases = {'recorded_at':['2026-2-04', '20261104', '2026-02-30', '0000-01-01', '2026-11-04\n'],
                 'source_basis_sha256':['A'*64, 'z'*64, '0'*63, '0'*65, '0'*64+'\n'],
                 'report_id':['missing', 'report-one ']}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.ledger(dict(self.p, **{KEY:[dict(good, **{field:value})]}))
        self.ledger(dict(self.p, **{KEY:[dict(good, recorded_at='2024-02-29')]}))

    def test_source_list_nonempty_unique_and_literal(self):
        good = assertion(self.p)
        for value in (None, [], {}, 'main', True, [''], [' '], ['main','main'], ['main',None], ['main',{}]):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                self.ledger(dict(self.p, **{KEY:[dict(good, source_ids=value)]}))

    def test_duplicate_identifier_and_exact_recorder_triple_reject(self):
        a = assertion(self.p)
        for b in (dict(a, recorded_by='Other'), dict(a, inventory_id='other'), dict(a, study_id='study-B')):
            with self.subTest(b=b), self.assertRaises(ValueError):
                self.ledger(dict(self.p, **{KEY:[a,b]}))
        b = assertion(self.p, study='study-B', iid='other')
        self.assertEqual(self.ledger(dict(self.p, **{KEY:[a,b]}))['counts']['inventory_assertions'], 2)

    def test_delimiters_do_not_collide_in_exact_tuple_keys(self):
        p = self.pending(); p['reports'][0]['report_id']='a:b'; p['reports'][1]['report_id']='a'
        for source in p['report_sources']:
            source['report_id']='a:b' if source['report_id']=='report-one' else 'a'
        p[KEY]=[assertion(p, report='a:b', study='c', recorder='d', iid='one'),
                assertion(p, report='a', study='b:c', recorder='d', iid='two', sources=['other'])]
        self.assertEqual(self.ledger(p)['counts']['described_report_study_pairs'], 2)
        from compare_runs import compare_protocols
        pairs=compare_protocols(p,p)[KEY+'_changes']['pair_comparisons']
        self.assertEqual({(r['report_id'],r['study_id']) for r in pairs}, {('a:b','c'),('a','b:c')})

    def test_multiple_people_descriptions_retained_without_date_winner(self):
        a=assertion(self.p, recorder='A', iid='a')
        b=assertion(self.p, recorder='B', iid='b', sources=['supplement'])
        b.update(description='Different fictional description.', recorded_at='2020-01-01')
        self.p[KEY]=[a,b]; result=self.ledger(); pair=result['pair_inventory_ledger'][0]
        self.assertEqual(pair['inventory_ids'], ['a','b'])
        self.assertEqual(pair['current_recorder_labels'], ['A','B'])
        self.assertEqual(len(pair['current_descriptions']), 2)
        self.assertIn('DIFFERING_CURRENT_DESCRIPTIONS', pair['comparison_cues'])
        self.assertIn('DIFFERING_CURRENT_SOURCE_ID_SETS', pair['comparison_cues'])
        self.assertEqual([r['inventory'] for r in result['inventory_ledger']], [a,b])
        self.assertEqual(result['adjudication'], 'NOT_PERFORMED')

    def test_source_order_is_not_different_coverage(self):
        self.p[KEY]=[assertion(self.p, iid='a', recorder='A', sources=['main','supplement']),
                     assertion(self.p, iid='b', recorder='B', sources=['supplement','main'])]
        pair=self.ledger()['pair_inventory_ledger'][0]
        self.assertEqual(pair['current_source_id_sets'], [['main','supplement']])
        self.assertNotIn('DIFFERING_CURRENT_SOURCE_ID_SETS', pair['comparison_cues'])

    def test_pending_and_excluded_reports_can_describe_new_candidates(self):
        for decision in ('pending', 'exclude'):
            p=self.pending(decision); p[KEY]=[assertion(p, study='human-new-label')]
            with self.subTest(decision=decision):
                result=review(p); pair=result['pair_inventory_ledger'][0]
                self.assertFalse(pair['membership_currently_declared'])
                self.assertFalse(pair['has_result_rows'])
                self.assertEqual(result['counts']['current_source_assertions'],1)
                self.assertEqual(len(template(p,'report-one','human-new-label')[KEY]),1)

    def test_reports_still_require_title_abstract_inclusion(self):
        self.p[KEY]=[assertion(self.p)]; self.p['screening'][0]['decision']='exclude'
        with self.assertRaises(ValueError): review(self.p)

    def test_inventory_never_makes_invalid_evidence_valid(self):
        p=self.pending(); p[KEY]=[assertion(p,study='study-A')]
        p['evidence']=[copy.deepcopy(self.p['evidence'][0])]
        with self.assertRaises(ValueError): review(p)
        p=copy.deepcopy(self.p); p['reports'][0]['study_ids'].remove('study-A')
        p[KEY]=[dict(assertion(self.p), source_basis_sha256='0'*64)]
        with self.assertRaises(ValueError): review(p)

    def test_no_implicit_candidates_from_memberships_or_evidence(self):
        result=self.ledger()
        self.assertEqual(result['candidate_targets'],[])
        self.assertEqual(result['pair_inventory_ledger'],[])
        self.p[KEY]=[assertion(self.p,study='only-explicit')]
        self.assertEqual([r['study_id'] for r in self.ledger()['candidate_targets']],['only-explicit'])

    def test_pair_hash_is_canonical_distinct_and_membership_free(self):
        a=prepare_candidate_target(self.p,'report-one','study-A')
        b=prepare_candidate_target(self.p,'report-two','study-A')
        self.assertNotEqual(a['source_basis_sha256'],b['source_basis_sha256'])
        self.assertEqual(set(a['source_basis']), {'schema_version','scope','report_id','study_id','report_source_basis_sha256'})
        self.assertEqual(a['source_basis_sha256'],hashlib.sha256(canonical_json_bytes(a['source_basis'])).hexdigest())
        p=dict(reversed(list(self.p.items())))
        self.assertEqual(a,prepare_candidate_target(p,'report-one','study-A'))

    def test_binding_stable_pending_included_excluded_and_membership_changes(self):
        p=self.pending(); p[KEY]=[assertion(p,study='new-label')]
        initial=review(p)['candidate_targets'][0]['source_basis_sha256']
        for decision in ('include','exclude','pending'):
            changed=copy.deepcopy(p); changed['reports'][0]['decision']=decision
            if decision=='include': changed['reports'][0]['study_ids']=['new-label','sibling']
            result=review(changed)
            self.assertEqual(result['candidate_targets'][0]['source_basis_sha256'],initial)
            self.assertEqual(result['inventory_ledger'][0]['source_match_status'],'CURRENT_SOURCE')
            self.assertEqual(result['pair_inventory_ledger'][0]['membership_currently_declared'],decision=='include')

    def test_membership_removal_preserves_current_description(self):
        self.p[KEY]=[assertion(self.p,study='study-C')]
        self.p['reports'][0]['study_ids'].remove('study-C')
        result=review(self.p)
        self.assertEqual(result['inventory_ledger'][0]['source_match_status'],'CURRENT_SOURCE')
        self.assertFalse(result['pair_inventory_ledger'][0]['membership_currently_declared'])
        self.assertEqual(len(template(self.p,'report-one','study-C')[KEY]),1)

    def test_scalar_plural_reorder_results_work_version_description_do_not_stale(self):
        self.p[KEY]=[assertion(self.p,report='report-two',sources=['other'])]
        p=copy.deepcopy(self.p); p['reports'][1]['study_ids']=[p['reports'][1].pop('study_id')]
        p['reports'].reverse(); p['reports'][1]['study_ids'].reverse()
        p['evidence'][0]['result']='Changed fictional result'; p['gaps'][0]['question']='Changed fictional task'
        p['version']='fictional-v2'; p[KEY][0]['description']='Changed literal description'
        self.assertEqual(self.ledger(p)['inventory_ledger'][0]['source_match_status'],'CURRENT_SOURCE')

    def test_criteria_source_retrieval_and_catalog_changes_stale(self):
        p=self.pending(); p[KEY]=[assertion(p)]
        edits=[lambda p:p.update(question='Changed fictional scope'),
               lambda p:p['inclusion_criteria'].append('Changed scope'),
               lambda p:p['exclusion_criteria'].append('Changed scope'),
               lambda p:p['report_sources'][0].update(document_version='v2'),
               lambda p:p['report_sources'][1].update(document_sha256='c'*64),
               lambda p:p['report_sources'].reverse(),
               lambda p:p['reports'][0].update(locator='fictional://changed'),
               lambda p:p['reports'][0].update(retrieval='pending'),
               lambda p:p['searches'][0].update(query='Changed fictional query')]
        for edit in edits:
            changed=copy.deepcopy(p); edit(changed)
            with self.subTest(edit=edit):
                self.assertEqual(self.ledger(changed)['inventory_ledger'][0]['source_match_status'],'STALE_SOURCE')

    def test_prior_review_source_hashes_are_independent(self):
        from report_review_links import prepare_targets as reports
        from report_study_review_links import prepare_targets as studies
        old_reports=reports(self.p); old_studies=studies(self.p)
        self.p[KEY]=[assertion(self.p,study='new-label')]
        self.assertEqual(reports(self.p),old_reports)
        self.assertEqual(studies(self.p),old_studies)

    def test_cross_report_sources_reject_even_stale(self):
        good=assertion(self.p)
        for sources in (['other'],['main','other']):
            for digest in (good['source_basis_sha256'],'0'*64):
                with self.subTest(sources=sources,digest=digest),self.assertRaises(ValueError):
                    self.ledger(dict(self.p,**{KEY:[dict(good,source_ids=sources,source_basis_sha256=digest)]}))

    def test_missing_source_only_stale_and_explicitly_unresolved(self):
        self.p[KEY]=[assertion(self.p)]
        self.p['report_sources']=[s for s in self.p['report_sources'] if s['source_id']!='main']
        result=self.ledger(); row=result['inventory_ledger'][0]
        self.assertEqual(row['source_match_status'],'STALE_SOURCE')
        self.assertEqual(row['unresolved_source_ids'],['main'])
        self.assertIn('UNRESOLVED_SOURCE_IDS',result['pair_inventory_ledger'][0]['comparison_cues'])
        self.p[KEY][0]['source_basis_sha256']=row['current_source_basis_sha256']
        with self.assertRaises(ValueError): self.ledger()

    def test_null_document_digest_still_unverified_and_unbound(self):
        self.p[KEY]=[assertion(self.p,report='report-two',sources=['other'])]
        result=review(self.p)
        self.assertEqual(result['candidate_targets'][0]['source_binding_state'],'DOCUMENT_BYTES_UNBOUND')
        self.assertEqual(result['document_bytes_verification'],'NOT_PERFORMED')
        self.assertEqual(result['source_authenticity'],'NOT_VERIFIED')
        self.assertEqual(result['eligibility_assessment'],'NOT_PERFORMED')
        self.assertEqual(result['study_identity'],'NOT_ESTABLISHED')
        self.assertEqual(result['inventory_completeness'],'NOT_ESTABLISHED')

    def test_explicit_new_label_template_separate_from_stored_counts(self):
        self.p[KEY]=[assertion(self.p)]
        result=template(self.p,'report-one','new-human-label')
        self.assertEqual(result['proposed_target']['study_id'],'new-human-label')
        self.assertEqual(result['counts']['inventory_assertions'],0)
        self.assertEqual(result['counts']['described_report_study_pairs'],0)
        self.assertEqual(result['protocol_counts']['inventory_assertions'],1)
        self.assertEqual(result['candidate_targets'],[])
        draft=result[KEY][0]
        self.assertTrue(all(v is None for k,v in draft.items() if k not in ('report_id','study_id','source_basis_sha256')))
        with self.assertRaises(ValueError): run(dict(self.p,**{KEY:result[KEY]}))

    def test_template_does_not_renew_stale_rows(self):
        self.p[KEY]=[assertion(self.p)]; self.p['report_sources'][0]['document_version']='v2'
        before=copy.deepcopy(self.p); result=template(self.p,'report-one','study-A')
        self.assertEqual(result['inventory_ledger'][0]['inventory'],before[KEY][0])
        self.assertEqual(result['inventory_ledger'][0]['source_match_status'],'STALE_SOURCE')
        self.assertNotEqual(result[KEY][0]['source_basis_sha256'],before[KEY][0]['source_basis_sha256'])
        self.assertEqual(self.p,before)

    def test_missing_sources_or_retrieval_give_guidance_without_scaffold(self):
        p=self.pending(); p['report_sources']=[]
        result=template(p,'report-one','new')
        self.assertEqual(result[KEY],[])
        self.assertEqual(result['source_first_candidates'],[dict(report_id='report-one',study_id='new')])
        for state in ('pending','not_retrieved'):
            p=self.pending(); p['reports'][0]['retrieval']=state
            result=template(p,'report-one','new')
            self.assertEqual(result[KEY],[])
            self.assertEqual(result['retrieval_required_candidates'],[dict(report_id='report-one',study_id='new')])

    def test_selection_requires_exact_stored_pair_but_template_explicit_label(self):
        self.p[KEY]=[assertion(self.p)]
        for args in ((None,'study-A'),('missing',None),('report-one','new-label')):
            with self.subTest(args=args),self.assertRaises(ValueError): review(self.p,*args)
        for args in ((None,None),('report-one',None),(None,'new'),('report-one',' ')):
            with self.subTest(args=args),self.assertRaises(ValueError): template(self.p,*args)
        self.assertEqual(review(self.p,'report-one','study-A')['selection']['scope'],'EXACT_REPORT_STUDY_PAIR')
        self.assertEqual(len(template(self.p,'report-one','new-label')[KEY]),1)

    def test_whole_protocol_validated_before_selection(self):
        self.p[KEY]=[assertion(self.p)]
        for operation in (review,template):
            p=copy.deepcopy(self.p); p['reports'][1]['record_ids']=['unknown']
            with self.assertRaises(ValueError): operation(p,'report-one','study-A')
            p=copy.deepcopy(self.p); p['evidence'][0]['study_id']='unknown'
            with self.assertRaises(ValueError): operation(p,'report-one','study-A')

    def test_selected_view_preserves_context_pointers_and_detaches(self):
        self.p[KEY]=[assertion(self.p),assertion(self.p,report='report-two',iid='second',sources=['other'])]
        before=copy.deepcopy(self.p); result=review(self.p,'report-two','study-A')
        self.assertEqual(result['inventory_ledger'][0]['input_pointer'],'/report_study_inventory/1')
        self.assertEqual([s['source']['source_id'] for s in result['source_ledger']],['other'])
        self.assertEqual(len(result['record_targets']),1)
        self.assertEqual(len(result['source_contexts']),1)
        result['inventory_ledger'][0]['inventory']['source_ids'].append('changed')
        result['source_contexts'][0]['search']['query']='changed'
        result['report_targets'][0]['recorded_report']['locator']='changed'
        self.assertEqual(self.p,before)

    def test_catalog_shared_once_and_growth_linear(self):
        sizes=[]
        for size in (80,160):
            p=self.pending(); basis=prepare_candidate_target(p,'report-one','new')
            rows=[]
            for i in range(size):
                row=assertion(p,study='s-'+str(i),iid='i-'+str(i)); rows.append(row)
            p[KEY]=rows; result=prepare_targets(p)
            self.assertEqual(len(result['source_contexts']),1)
            self.assertEqual(len(result['source_ledger']),3)
            for target in result['candidate_targets']:
                self.assertEqual(set(target['source_basis']),set(basis['source_basis']))
            sizes.append(len(json.dumps(result)))
        self.assertLess(sizes[1],sizes[0]*2.1)

    def test_canonical_counts_csv_evidence_and_queues_unchanged(self):
        from prisma_reports import report_flow
        from research_status import status
        before=run(self.p); flow=report_flow(self.p); state=status(self.p)
        self.p[KEY]=[assertion(self.p,study='new-label')]
        after=run(self.p); current=report_flow(self.p)
        for field in ('flow','evidence','planning','synthesis','context','work_packages','report_study_coverage','report_review'):
            self.assertEqual(before[field],after[field],field)
        for field in ('record_flow','report_flow','report_csv','report_study_coverage'):
            self.assertEqual(flow[field],current[field],field)
        self.assertEqual(state['queues'],status(self.p)['queues'])

    def test_optional_projection_status_handoff_and_no_inventory_queue(self):
        from prisma_audit import export_audit
        from prisma_reports import report_flow
        from research_status import status
        from review_handoff import handoff
        from synthesis_review import snapshot
        self.p[KEY]=[assertion(self.p,study='new-label')]
        expected=run(self.p)[KEY]
        for project in (export_audit,report_flow,snapshot): self.assertEqual(project(self.p)[KEY],expected)
        state=status(self.p); packet=handoff(self.p)
        self.assertEqual(state[KEY]['counts'],expected['counts'])
        self.assertEqual(packet[KEY],state[KEY])
        self.assertTrue(any(x['script']=='report_study_inventory.py' for x in packet['detailed_views']))
        self.assertFalse(any('inventory' in name for name in state['queues']))
        self.assertFalse(any('inventory' in row['queue'] for row in packet['manual_review_steps']))

    def test_comparison_unchanged_assertion_becomes_stale(self):
        from compare_runs import compare_protocols
        self.p[KEY]=[assertion(self.p)]; after=copy.deepcopy(self.p)
        after['report_sources'][0]['document_version']='v2'
        changes=compare_protocols(self.p,after)[KEY+'_changes']
        self.assertEqual(changes['assertion_changes']['unchanged_count'],1)
        item=changes['inventory_comparisons'][0]
        self.assertEqual(item['before']['source_match_status'],'CURRENT_SOURCE')
        self.assertEqual(item['after']['source_match_status'],'STALE_SOURCE')
        self.assertEqual(len(changes['pair_comparisons']),1)

    def test_legacy_comparison_omits_inventory_and_empty_optin_is_visible(self):
        from compare_runs import compare_protocols
        self.assertNotIn(KEY+'_changes',compare_protocols(self.p,self.p))
        p=copy.deepcopy(self.p); p[KEY]=[]
        changes=compare_protocols(self.p,p)[KEY+'_changes']
        self.assertEqual(changes['before_stage'],'NOT_SUPPLIED')
        self.assertEqual(changes['after_stage'],'SUPPLIED')

    def test_bundle_roundtrip_and_helper_fingerprint(self):
        from research_bundle import create,verify,engine_hashes
        self.p[KEY]=[assertion(self.p)]
        hashes=engine_hashes()
        self.assertEqual(hashes['report_study_inventory_links.py'],hashlib.sha256((ROOT/'report_study_inventory_links.py').read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'protocol.json'; destination=Path(tmp)/'bundle.zip'
            source.write_text(json.dumps(self.p),encoding='utf-8'); create(source,destination)
            self.assertTrue(verify(destination)['valid'])

    def test_bibliographic_import_is_enrichment_with_mapped_provenance(self):
        from bibliographic_integrity import ENRICHMENT_FIELDS
        p=self.imported(); collection=run(p)['bibliographic_collection']
        p[KEY]=[assertion(p,collection=collection)]
        self.assertIn(KEY,ENRICHMENT_FIELDS)
        self.assertEqual(run(p)[KEY]['inventory_ledger'][0]['source_match_status'],'CURRENT_SOURCE')
        self.assertNotEqual(prepare_candidate_target(p,'report-one','study-A')['source_basis_sha256'],p[KEY][0]['source_basis_sha256'])

    def test_imported_csv_template_hash_is_current_when_completed(self):
        p=self.imported(); result=template(p,'report-one','new-label')
        collection=run(p)['bibliographic_collection']
        expected=prepare_candidate_target(p,'report-one','new-label',collection)
        self.assertEqual(result['proposed_target']['source_basis_sha256'],expected['source_basis_sha256'])
        row=result[KEY][0]
        row.update(inventory_id='imported-inventory',recorded_by='Fictional recorder',recorded_at='2026-11-04',
                   description='Fictional imported description',source_locator='fictional://section',source_ids=['main'])
        p[KEY]=[row]
        self.assertEqual(review(p)['inventory_ledger'][0]['source_match_status'],'CURRENT_SOURCE')

    def test_imported_csv_source_first_target_retains_mapped_provenance(self):
        p=self.imported(); p['report_sources']=[]
        result=template(p,'report-one','new-label')
        expected=prepare_candidate_target(p,'report-one','new-label',run(p)['bibliographic_collection'])
        self.assertEqual(result['proposed_target']['source_basis_sha256'],expected['source_basis_sha256'])
        self.assertEqual(result[KEY],[])
        self.assertEqual(len(result['source_first_candidates']),1)

    def test_locators_inert_and_readonly(self):
        self.p['report_sources'][0]['source_locator']='https://invalid.example/never-open'
        self.p[KEY]=[assertion(self.p)]; self.p[KEY][0]['source_locator']='$(do-not-execute)'
        before=copy.deepcopy(self.p)
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')), \
             patch('subprocess.run',side_effect=AssertionError('execution forbidden')):
            result=review(self.p); render_text(result); template(self.p,'report-one','new')
        self.assertEqual(self.p,before)
        self.assertEqual(result['external_calls'],0)

    def test_cli_utf8_controls_createonly_and_input_preservation(self):
        self.p['report_sources'][0]['source_locator']='fictional://한글\n\x1b\x00'
        self.p[KEY]=[assertion(self.p)]
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'p.json'; output=Path(tmp)/'out.json'
            source.write_bytes((json.dumps(self.p,ensure_ascii=False)+'\r\n').encode('utf-8')); before=source.read_bytes()
            result=self.cli(source,'--report-id=report-one','--study-id=study-A','--text','--output',str(output))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('한글'.encode(),result.stdout); self.assertNotIn(b'\x1b',result.stdout); self.assertNotIn(b'\x00',result.stdout)
            self.assertEqual(json.loads(output.read_bytes())['counts']['inventory_assertions'],1)
            saved=output.read_bytes(); failed=self.cli(source,'--output',str(output))
            self.assertNotEqual(failed.returncode,0); self.assertEqual(failed.stdout,b''); self.assertEqual(output.read_bytes(),saved)
            failed=self.cli(source,'--output',str(source)); self.assertNotEqual(failed.returncode,0)
            self.assertEqual(source.read_bytes(),before)

    def test_cli_strict_json_utf8_and_encoding_before_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'p.json'; output=Path(tmp)/'out.json'
            for raw in (b'{"question":1,"question":2}', b'{"bad":NaN}', b'\xff'):
                source.write_bytes(raw); result=self.cli(source,'--output',str(output))
                self.assertNotEqual(result.returncode,0); self.assertEqual(result.stdout,b''); self.assertFalse(output.exists())
            p=copy.deepcopy(self.p); p['report_sources'][0]['source_locator']='\ud800'
            source.write_text(json.dumps(p),encoding='utf-8'); result=self.cli(source,'--output',str(output))
            self.assertNotEqual(result.returncode,0); self.assertEqual(result.stdout,b''); self.assertFalse(output.exists())

    def test_clean_import_orders(self):
        for modules in ('report_study_inventory,evidence_workflow,prisma_reports',
                        'research_bundle,report_study_inventory_links,report_study_inventory'):
            result=subprocess.run([sys.executable,'-c','import '+modules],cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_documented_fictional_example_counts_and_canonical_preservation(self):
        from prisma_reports import report_flow
        p=json.loads((ROOT/'examples/report-study-inventory.json').read_text(encoding='utf-8'))
        before=copy.deepcopy(p); bare=copy.deepcopy(p); bare.pop(KEY)
        result=review(p)
        self.assertEqual({k:result['counts'][k] for k in
                          ('inventory_assertions','described_report_study_pairs','current_source_assertions','stale_source_assertions')},
                         dict(inventory_assertions=5,described_report_study_pairs=4,
                              current_source_assertions=4,stale_source_assertions=1))
        self.assertEqual(len(result['source_ledger']),4)
        pairs={(r['report_id'],r['study_id']):r for r in result['pair_inventory_ledger']}
        self.assertEqual(len(pairs['report-three','candidate-X']['current_recorder_labels']),2)
        self.assertFalse(pairs['report-three','candidate-X']['membership_currently_declared'])
        self.assertFalse(pairs['report-two','candidate-Y']['membership_currently_declared'])
        self.assertTrue(pairs['report-one','study-A']['membership_currently_declared'])
        self.assertTrue(pairs['report-five','candidate-Z']['unresolved_source_ids'])
        old,new=report_flow(bare),report_flow(p)
        for key in ('record_flow','report_flow','report_csv','report_study_coverage'):
            self.assertEqual(old[key],new[key],key)
        result=template(p,'report-three','candidate-new')
        self.assertEqual(result['counts']['inventory_assertions'],0)
        self.assertEqual(result['counts']['described_report_study_pairs'],0)
        self.assertEqual(result['proposed_target']['study_id'],'candidate-new')
        self.assertEqual(len(result[KEY]),1)
        self.assertIsNone(result[KEY][0]['source_ids'])
        self.assertEqual(p,before)

    def test_documented_cli_audit_handoff_compare_and_bundle_journey(self):
        fixture=ROOT/'examples/report-study-inventory.json'; before=fixture.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'view.json'; bundle=Path(tmp)/'bundle.zip'
            result=self.cli(fixture,'--report-id=report-three','--study-id=candidate-new',
                            '--template','--text','--output',str(output))
            self.assertEqual(result.returncode,0,result.stderr)
            saved=json.loads(output.read_bytes())
            self.assertEqual(saved['counts']['inventory_assertions'],0)
            self.assertEqual(saved['protocol_counts']['inventory_assertions'],5)
            self.assertIsNone(saved[KEY][0]['source_ids'])
            for script,args in [('prisma_audit.py',[str(fixture),'--text']),
                                ('review_handoff.py',[str(fixture),'--text']),
                                ('research_status.py',[str(fixture),'--text']),
                                ('compare_runs.py',[str(fixture),str(fixture),'--text']),
                                ('research_bundle.py',['create',str(fixture),str(bundle)]),
                                ('research_bundle.py',['verify',str(bundle)])]:
                result=subprocess.run([sys.executable,str(ROOT/script),*args],cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,(script,result.stderr))
        self.assertEqual(fixture.read_bytes(),before)


if __name__ == '__main__': unittest.main()
