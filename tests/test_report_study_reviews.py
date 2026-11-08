"""Fictional report-study positions remain distinct from document eligibility."""
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
from report_study_review_links import prepare_targets, link_report_study_reviews
from report_study_review import review, template, render_text

ROOT = Path(__file__).resolve().parents[1]
KEY = 'report_study_reviews'
VIEW = 'report_study_review'


def protocol():
    p = json.loads((ROOT/'examples/multi-study-report.json').read_text(encoding='utf-8'))
    p['report_sources'] = [
        dict(source_id='main', report_id='report-one', source_locator='fictional://main', document_version='v1', document_sha256='a'*64),
        dict(source_id='supplement', report_id='report-one', source_locator='fictional://supplement', document_version='v1', document_sha256='b'*64),
        dict(source_id='other', report_id='report-two', source_locator='fictional://other', document_version='v1', document_sha256=None)]
    return p


def targets(p):
    return {(r['report_id'],r['study_id']):r for r in prepare_targets(p)['membership_targets']}


def assertion(p, report='report-one', study='study-A', reviewer='Fictional reviewer', rid='review-1', decision='include', sources=None):
    return dict(review_id=rid, report_id=report, study_id=study, reviewer=reviewer, reviewed_at='2026-11-04',
                decision=decision, rationale='Fictional study-scoped human position.', reviewed_locator='Fictional section 2.',
                reviewed_source_ids=sources if sources is not None else ['main'],
                source_basis_sha256=targets(p)[(report,study)]['source_basis_sha256'])


class ReportStudyReviewTests(unittest.TestCase):
    def setUp(self): self.p = protocol()

    def ledger(self,p=None): return link_report_study_reviews(self.p if p is None else p)

    def cli(self,path,*args):
        return subprocess.run([sys.executable,str(ROOT/'report_study_review.py'),str(path),*args],
                              capture_output=True,env=dict(os.environ,PYTHONIOENCODING='utf-8'),cwd=ROOT)

    def test_absent_empty_null_and_missing_report_stage(self):
        self.assertNotIn(VIEW,run(self.p)); self.assertEqual(self.ledger()['stage'],'NOT_SUPPLIED')
        p=copy.deepcopy(self.p);p[KEY]=[]
        self.assertEqual(run(p)[VIEW]['stage'],'SUPPLIED')
        for value in (None,{},False,'',0,[None]):
            with self.subTest(value=value),self.assertRaises((ValueError,TypeError)): run(dict(p,**{KEY:value}))
        p.pop('reports');p.pop('report_sources');p['evidence']=[];p['gaps']=[]
        self.assertEqual(review(p)['report_stage'],'NOT_SUPPLIED')
        self.assertEqual(review(p)['membership_targets'],[])
        p[KEY]=[assertion(self.p)]
        with self.assertRaises(ValueError): run(p)

    def test_strict_exact_schema_and_scalar_strings(self):
        good=assertion(self.p)
        cases=[dict(good,unexpected='x')]
        for key in good:
            missing=copy.deepcopy(good);missing.pop(key);cases.append(missing)
            if key!='reviewed_source_ids':
                cases.extend(dict(good,**{key:value}) for value in ('',' \t\n',None,True,1,[],{}))
        for bad in cases:
            with self.subTest(bad=bad),self.assertRaises((ValueError,TypeError)):
                run(dict(self.p,**{KEY:[bad]}))

    def test_strict_dates_hashes_positions_and_unknown_reports(self):
        good=assertion(self.p)
        invalid={'reviewed_at':['2026-2-04','20261104','2026-02-30','0000-01-01','2026-11-04\n'],
                 'source_basis_sha256':['A'*64,'z'*64,'0'*63,'0'*65,'0'*64+'\n'],
                 'decision':['pending','Include',' include'], 'report_id':['unknown','report-one ']}
        for field,values in invalid.items():
            for value in values:
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    self.ledger(dict(self.p,**{KEY:[dict(good,**{field:value})]}))
        self.ledger(dict(self.p,**{KEY:[dict(good,reviewed_at='2024-02-29')]}))

    def test_reviewed_source_selection_is_nonempty_unique_literal_list(self):
        good=assertion(self.p)
        for value in (None,[],{},'main',True,[''],[' '],['main','main'],['main',None],['main',{}]):
            with self.subTest(value=value),self.assertRaises((ValueError,TypeError)):
                self.ledger(dict(self.p,**{KEY:[dict(good,reviewed_source_ids=value)]}))
        for sources in (['main','other'],['other']):
            for digest in (good['source_basis_sha256'],'0'*64):
                with self.subTest(sources=sources,digest=digest),self.assertRaises(ValueError):
                    self.ledger(dict(self.p,**{KEY:[dict(good,reviewed_source_ids=sources,source_basis_sha256=digest)]}))

    def test_duplicate_ids_and_exact_triples(self):
        a=assertion(self.p)
        for b in (dict(a,reviewer='Other'),dict(a,review_id='another'),dict(a,study_id='study-B')):
            with self.subTest(b=b),self.assertRaises(ValueError): self.ledger(dict(self.p,**{KEY:[a,b]}))
        b=assertion(self.p,study='study-B',rid='review-2')
        self.assertEqual(self.ledger(dict(self.p,**{KEY:[a,b]}))['counts']['review_assertions'],2)

    def test_same_study_in_different_reports_has_distinct_targets_and_reviews(self):
        t=targets(self.p)
        self.assertNotEqual(t['report-one','study-A']['source_basis_sha256'],t['report-two','study-A']['source_basis_sha256'])
        self.p[KEY]=[assertion(self.p),assertion(self.p,report='report-two',rid='review-2',sources=['other'],decision='exclude')]
        result=self.ledger(); self.assertEqual(result['counts']['current_source_reviews'],2)
        rows={(x['report_id'],x['study_id']):x for x in result['membership_review_ledger']}
        self.assertEqual(rows['report-one','study-A']['current_decisions'],['include'])
        self.assertEqual(rows['report-two','study-A']['current_decisions'],['exclude'])

    def test_report_inclusion_and_results_never_generate_study_position(self):
        result=self.ledger();self.assertEqual(result['review_ledger'],[])
        self.assertTrue(all(not x['current_decisions'] for x in result['membership_review_ledger']))
        self.assertEqual(result['canonical_study_selection'],'NOT_MODELED')
        self.assertEqual(len(result['current_memberships_with_review_cues']),4)

    def test_opposing_siblings_do_not_filter_evidence_or_compare_report_decision(self):
        from prisma_reports import report_flow
        before=run(self.p); flow=report_flow(self.p)
        self.p[KEY]=[assertion(self.p),assertion(self.p,study='study-B',rid='review-B',decision='exclude')]
        result=run(self.p)
        self.assertEqual(result['flow'],before['flow']);self.assertEqual(result['evidence'],before['evidence'])
        after=report_flow(self.p)
        for key in ('record_flow','report_flow','report_csv','report_study_coverage'): self.assertEqual(after[key],flow[key])
        self.assertEqual(after['report_study_coverage']['study_eligibility_assessment'],'NOT_PERFORMED')
        self.assertFalse(any('matches_recorded' in key for row in result[VIEW]['review_ledger'] for key in row))

    def test_multiple_positions_no_date_or_majority_winner(self):
        rows=[assertion(self.p,reviewer='A',rid='a',decision='include'),
              assertion(self.p,reviewer='B',rid='b',decision='exclude',sources=['supplement']),
              assertion(self.p,reviewer='C',rid='c',decision='unclear')]
        rows[1]['reviewed_at']='2020-01-01';self.p[KEY]=rows
        item=self.ledger()['membership_review_ledger'][0]
        self.assertEqual(item['current_decisions'],['exclude','include','unclear'])
        self.assertIn('DIFFERING_CURRENT_POSITIONS',item['comparison_cues'])
        self.assertIn('DIFFERING_CURRENT_REVIEWED_SOURCE_ID_SETS',item['comparison_cues'])
        self.assertEqual(item['review_ids'],['a','b','c'])

    def test_selected_source_order_not_inferred_different_coverage(self):
        self.p[KEY]=[assertion(self.p,rid='a',reviewer='A',sources=['main','supplement']),
                     assertion(self.p,rid='b',reviewer='B',sources=['supplement','main'])]
        item=self.ledger()['membership_review_ledger'][0]
        self.assertEqual(item['current_reviewed_source_id_sets'],[['main','supplement']])
        self.assertNotIn('DIFFERING_CURRENT_REVIEWED_SOURCE_ID_SETS',item['comparison_cues'])
        self.assertEqual(self.ledger()['document_bytes_verification'],'NOT_PERFORMED')

    def test_pair_hash_is_canonical_and_report_hash_unchanged(self):
        from report_review_links import prepare_targets as report_targets
        baseline=report_targets(self.p)
        self.p[KEY]=[assertion(self.p)]
        self.assertEqual(report_targets(self.p),baseline)
        for row in targets(self.p).values():
            self.assertEqual(row['source_basis_sha256'],hashlib.sha256(canonical_json_bytes(row['source_basis'])).hexdigest())
        p=dict(reversed(list(self.p.items())))
        self.assertEqual(targets(p),targets(self.p))

    def test_scalar_to_singleton_and_reorder_preserve_pair_binding(self):
        before=targets(self.p);p=copy.deepcopy(self.p)
        p['reports'][1]['study_ids']=[p['reports'][1].pop('study_id')]
        p['reports'][0]['study_ids'].reverse();p['reports'].reverse()
        after=targets(p)
        self.assertEqual(set(before),set(after))
        for key in before: self.assertEqual(before[key]['source_basis_sha256'],after[key]['source_basis_sha256'])
        self.assertNotEqual(before['report-two','study-A']['input_pointer'],after['report-two','study-A']['input_pointer'])

    def test_sibling_membership_results_work_and_version_not_source_basis(self):
        self.p[KEY]=[assertion(self.p)]
        p=copy.deepcopy(self.p);p['reports'][0]['study_ids'].append('study-D')
        p['evidence'][0]['result']='Changed fictional result';p['gaps'][0]['question']='Changed fictional work'
        p['version']='another-version';p['reports'][0]['reason']='Changed canonical report reason'
        self.assertEqual(self.ledger(p)['review_ledger'][0]['source_match_status'],'CURRENT_SOURCE')

    def test_criteria_catalog_and_provenance_changes_stale(self):
        self.p[KEY]=[assertion(self.p)]
        edits=[lambda p:p.update(question='Changed question'),lambda p:p['inclusion_criteria'].append('Changed scope'),
               lambda p:p['exclusion_criteria'].append('Changed scope'),lambda p:p['report_sources'][0].update(document_version='v2'),
               lambda p:p['report_sources'][1].update(document_sha256='c'*64),
               lambda p:p['report_sources'].reverse(),lambda p:p['reports'][0].update(locator='fictional://changed'),
               lambda p:p['searches'][0].update(query='Changed source context')]
        for change in edits:
            p=copy.deepcopy(self.p);change(p)
            with self.subTest(change=change): self.assertEqual(self.ledger(p)['review_ledger'][0]['source_match_status'],'STALE_SOURCE')

    def test_removed_membership_retains_orphan_without_queue_or_scaffold(self):
        self.p[KEY]=[assertion(self.p,study='study-C')]
        original=copy.deepcopy(self.p[KEY]);self.p['reports'][0]['study_ids'].remove('study-C')
        result=self.ledger();row=result['orphan_review_assertions'][0]
        self.assertEqual(row['review'],original[0]);self.assertFalse(row['membership_currently_declared'])
        self.assertEqual(row['source_match_status'],'STALE_SOURCE')
        self.assertNotIn(dict(report_id='report-one',study_id='study-C'),result['current_memberships_with_review_cues'])
        self.assertEqual(template(self.p,'report-one','study-C')[KEY],[])
        self.assertEqual(result['counts']['current_memberships'],3)
        self.assertEqual(result['counts']['orphan_pair_views'],1)

    def test_hash_matching_orphan_is_rejected(self):
        self.p[KEY]=[assertion(self.p,study='study-C')]
        self.p['reports'][0]['study_ids'].remove('study-C')
        current=targets(self.p)['report-one','study-C']['source_basis_sha256']
        self.p[KEY][0]['source_basis_sha256']=current
        with self.assertRaises(ValueError): review(self.p)

    def test_report_exclusion_removes_membership_without_changing_report_review_hash(self):
        from report_review_links import prepare_targets as rt
        self.p[KEY]=[assertion(self.p,report='report-two',rid='other-review',sources=['other'])]
        previous={r['report_id']:r['source_basis_sha256'] for r in rt(self.p)['report_targets']}
        self.p['reports'][1].update(decision='exclude',reason='Fictional canonical report exclusion')
        after={r['report_id']:r['source_basis_sha256'] for r in rt(self.p)['report_targets']}
        self.assertEqual(previous,after)
        self.assertEqual(self.ledger()['review_ledger'][0]['source_match_status'],'STALE_SOURCE')
        self.assertEqual(template(self.p,'report-two')[KEY],[])

    def test_removed_source_only_allowed_for_stale_assertion(self):
        self.p[KEY]=[assertion(self.p)]
        self.p['report_sources']=[s for s in self.p['report_sources'] if s['source_id']!='main']
        row=self.ledger()['review_ledger'][0]
        self.assertEqual(row['unresolved_reviewed_source_ids'],['main'])
        self.assertEqual(row['source_match_status'],'STALE_SOURCE')
        current=row['current_source_basis_sha256'];self.p[KEY][0]['source_basis_sha256']=current
        with self.assertRaises(ValueError): self.ledger()

    def test_unknown_source_with_arbitrary_stale_hash_not_claimed_valid_history(self):
        a=assertion(self.p);a.update(reviewed_source_ids=['never-declared'],source_basis_sha256='0'*64)
        self.p[KEY]=[a];r=self.ledger()
        self.assertEqual(r['review_ledger'][0]['unresolved_reviewed_source_ids'],['never-declared'])
        self.assertEqual(r['review_ledger'][0]['source_match_status'],'STALE_SOURCE')
        self.assertIn('not proof of valid history',r['boundary'])

    def test_unknown_pair_retained_only_as_unverified_orphan(self):
        a=assertion(self.p);a.update(study_id='never-declared',source_basis_sha256='0'*64)
        self.p[KEY]=[a];r=self.ledger()
        self.assertEqual(r['counts']['current_memberships'],4)
        self.assertEqual(r['counts']['orphan_pair_views'],1)
        self.assertEqual(template(self.p,'report-one','never-declared')[KEY],[])

    def test_explicit_source_subset_template_and_no_renewal(self):
        self.p[KEY]=[assertion(self.p)];self.p['report_sources'][0]['document_version']='v2'
        previous=copy.deepcopy(self.p[KEY]);result=template(self.p,'report-one','study-A')
        draft=result[KEY][0]
        self.assertIsNone(draft['reviewed_source_ids'])
        self.assertTrue(all(v is None for k,v in draft.items() if k not in ('report_id','study_id','source_basis_sha256')))
        self.assertEqual(result['review_ledger'][0]['review'],previous[0]);self.assertEqual(self.p[KEY],previous)
        with self.assertRaises(ValueError): run(dict(self.p,**{KEY:result[KEY]}))

    def test_source_first_and_null_digest_scaffolds(self):
        self.p['report_sources']=[];result=template(self.p)
        self.assertEqual(result[KEY],[]);self.assertEqual(len(result['source_first_memberships']),4)
        p=protocol();result=template(p,'report-two','study-A')
        self.assertEqual(len(result[KEY]),1)
        self.assertEqual(result['membership_targets'][0]['source_binding_state'],'DOCUMENT_BYTES_UNBOUND')
        self.assertEqual(result['document_bytes_verification'],'NOT_PERFORMED')

    def test_exact_selection_requires_report_and_whole_input_validation(self):
        for args in ((None,'study-A'),('report-one','missing'),('missing',None)):
            with self.subTest(args=args),self.assertRaises(ValueError): review(self.p,*args)
        p=copy.deepcopy(self.p);p['reports'][1]['record_ids']=['unknown']
        with self.assertRaises(ValueError): review(p,'report-one','study-A')
        p=copy.deepcopy(self.p);p['reports'][0]['study_ids'].remove('study-B')
        with self.assertRaises(ValueError): review(p,'report-two','study-A')

    def test_selected_view_preserves_exact_pointers_and_detaches(self):
        self.p[KEY]=[assertion(self.p),assertion(self.p,report='report-two',rid='other-review',sources=['other'])]
        before=copy.deepcopy(self.p);r=review(self.p,'report-two','study-A')
        self.assertEqual(r['review_ledger'][0]['input_pointer'],'/report_study_reviews/1')
        self.assertEqual(r['membership_targets'][0]['input_pointer'],'/reports/1/study_id')
        self.assertEqual([s['source']['source_id'] for s in r['source_ledger']],['other'])
        r['report_targets'][0]['recorded_report']['locator']='Changed output'
        r['review_ledger'][0]['review']['reviewed_source_ids'].append('Changed output')
        r['source_contexts'][0]['search']['query']='Changed output'
        self.assertEqual(self.p,before)

    def test_cli_controls_utf8_create_only_and_input_preservation(self):
        self.p['report_sources'][0]['source_locator']='fictional://한글\n\x1b\x00'
        self.p[KEY]=[assertion(self.p)]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'p.json';path.write_bytes((json.dumps(self.p,ensure_ascii=False)+'\r\n').encode('utf-8'))
            before=path.read_bytes();out=Path(tmp)/'view.json'
            result=self.cli(path,'--report-id=report-one','--study-id=study-A','--text','--output',str(out))
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('한글'.encode(),result.stdout)
            self.assertNotIn(b'\x1b',result.stdout);self.assertNotIn(b'\x00',result.stdout)
            self.assertEqual(json.loads(out.read_bytes())['counts']['current_memberships'],1)
            saved=out.read_bytes();failed=self.cli(path,'--output',str(out))
            self.assertNotEqual(failed.returncode,0);self.assertEqual(failed.stdout,b'');self.assertEqual(out.read_bytes(),saved)
            failed=self.cli(path,'--output',str(path));self.assertNotEqual(failed.returncode,0)
            self.assertEqual(path.read_bytes(),before)

    def test_cli_invalid_json_and_surrogate_create_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'p.json';out=Path(tmp)/'output.json'
            for raw in (b'{"question":1,"question":2}',b'{"bad":NaN}'):
                path.write_bytes(raw);result=self.cli(path,'--output',str(out))
                self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())
            p=copy.deepcopy(self.p);p['report_sources'][0]['source_locator']='\ud800'
            path.write_text(json.dumps(p),encoding='utf-8');result=self.cli(path,'--output',str(out))
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())

    def test_optional_projection_status_handoff_and_orphan_scope(self):
        from prisma_audit import export_audit
        from prisma_reports import report_flow
        from research_status import status
        from review_handoff import handoff
        from synthesis_review import snapshot
        self.p[KEY]=[assertion(self.p,study='study-C')];self.p['reports'][0]['study_ids'].remove('study-C')
        expected=run(self.p)[VIEW]
        for project in (export_audit,report_flow,snapshot): self.assertEqual(project(self.p)[VIEW],expected)
        state=status(self.p);packet=handoff(self.p)
        self.assertEqual(state['queues']['study_memberships_with_review_cues'],expected['current_memberships_with_review_cues'])
        self.assertEqual(len(state[VIEW]['orphan_review_assertions']),1)
        self.assertEqual(packet[VIEW],state[VIEW])
        self.assertTrue(any(x['script']=='report_study_review.py' for x in packet['detailed_views']))

    def test_comparison_keeps_source_stale_and_orphan_changes(self):
        from compare_runs import compare_protocols,render_text as compare_text
        self.p[KEY]=[assertion(self.p,study='study-C')];after=copy.deepcopy(self.p)
        after['reports'][0]['study_ids'].remove('study-C')
        delta=compare_protocols(self.p,after)['report_study_review_changes']
        self.assertEqual(delta['assertion_changes']['unchanged_count'],1)
        self.assertTrue(delta['review_comparisons'][0]['before']['membership_currently_declared'])
        self.assertFalse(delta['review_comparisons'][0]['after']['membership_currently_declared'])
        self.assertIn('not canonical eligibility',compare_text(compare_protocols(self.p,after)))

    def test_legacy_views_omit_new_projection_and_metadata_preserves_bindings(self):
        from compare_runs import compare_protocols
        from prisma_reports import report_flow
        old=run(self.p);old_report=report_flow(self.p)
        self.assertNotIn('report_study_review_changes',compare_protocols(self.p,self.p))
        self.p[KEY]=[assertion(self.p)];new=run(self.p)
        for field in ('flow','evidence','planning','synthesis','context','work_packages','report_study_coverage','report_review'):
            self.assertEqual(old[field],new[field],field)
        self.assertEqual(old_report['report_csv'],report_flow(self.p)['report_csv'])

    def test_bundle_preserves_assertions_without_document_bytes(self):
        from research_bundle import create,verify
        self.p[KEY]=[assertion(self.p)]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bundle.zip';source=Path(tmp)/'protocol.json'
            source.write_text(json.dumps(self.p),encoding='utf-8');create(source,path)
            result=verify(path);self.assertTrue(result['valid'])
            self.assertEqual(len(__import__('zipfile').ZipFile(path).namelist()),7)


    def test_tuple_identities_cannot_collide_via_delimiters(self):
        self.p['evidence']=[];self.p['gaps']=[]
        self.p['reports'][0].update(report_id='a:b',study_ids=['c'])
        self.p['reports'][1].update(report_id='a',study_id='b:c')
        for source in self.p['report_sources']:
            source['report_id']='a:b' if source['report_id']=='report-one' else 'a'
        self.p[KEY]=[assertion(self.p,report='a:b',study='c',rid='first',reviewer='d'),
                     assertion(self.p,report='a',study='b:c',rid='second',reviewer='d',sources=['other'])]
        result=self.ledger()
        self.assertEqual(result['counts']['current_memberships'],2)
        self.assertEqual(result['counts']['current_source_reviews'],2)
        from compare_runs import compare_protocols
        comparisons=compare_protocols(self.p,self.p)['report_study_review_changes']['pair_comparisons']
        self.assertEqual({(r['report_id'],r['study_id']) for r in comparisons},{('a:b','c'),('a','b:c')})

    def test_linear_pair_targets_share_full_source_context(self):
        sizes=[]
        for size in (80,160):
            p=protocol();p['evidence']=[];p['gaps']=[]
            p['reports'][0]['study_ids']=['s-'+str(i) for i in range(size)]
            result=prepare_targets(p)
            self.assertEqual(len(result['source_contexts']),1)
            for target in result['membership_targets']:
                self.assertEqual(set(target['source_basis']),{'schema_version','scope','report_id','study_id',
                                                           'report_source_basis_sha256','membership_currently_declared'})
            sizes.append(len(json.dumps(result)))
        self.assertLess(sizes[1],sizes[0]*2.1)

    def test_current_pair_without_cues_still_has_no_verified_eligibility(self):
        self.p[KEY]=[assertion(self.p)]
        result=self.ledger();row=result['membership_review_ledger'][0]
        self.assertEqual(row['comparison_cues'],[])
        self.assertEqual(result['eligibility_correctness'],'NOT_ASSESSED')
        self.assertEqual(result['canonical_study_selection'],'NOT_MODELED')
        self.assertEqual(result['document_bytes_verification'],'NOT_PERFORMED')

    def test_handoff_points_to_exact_pairs_sources_assertions_and_results(self):
        from review_handoff import handoff
        self.p[KEY]=[assertion(self.p,study='study-B',decision='unclear')]
        packet=handoff(self.p)
        step=next(x for x in packet['manual_review_steps'] if x['queue']=='study_memberships_with_review_cues')
        self.assertIn('/report_study_reviews/0',step['matching_input_rows'])
        self.assertIn('/evidence/1',step['matching_input_rows'])
        self.assertIn('/report_sources/1',step['matching_input_rows'])
        self.assertFalse(any('orphan' in row['queue'] for row in packet['manual_review_steps']))

    def test_bibliographic_import_enrichment_and_mapped_source_binding(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        from bibliographic_integrity import ENRICHMENT_FIELDS
        helper=BibliographicReviewTests();helper.setUp();p=helper.imported()
        rid=p['searches'][0]['record_ids'][0]
        p['screening']=[dict(record_id=rid,decision='include',reason='Fictional scope')]
        p['reports']=[dict(report_id='report-one',record_ids=[rid],retrieval='retrieved',locator='fictional',decision='include',study_id='study-A')]
        p['report_sources']=[copy.deepcopy(self.p['report_sources'][0])]
        collection=run(p)['bibliographic_collection']
        target=prepare_targets(p,collection)['membership_targets'][0]
        row=assertion(self.p);row['source_basis_sha256']=target['source_basis_sha256'];p[KEY]=[row]
        self.assertIn(KEY,ENRICHMENT_FIELDS)
        self.assertEqual(run(p)[VIEW]['review_ledger'][0]['source_match_status'],'CURRENT_SOURCE')
        self.assertNotEqual(target['source_basis_sha256'],prepare_targets(p)['membership_targets'][0]['source_basis_sha256'])

    def test_read_only_projections_never_follow_locators(self):
        self.p['report_sources'][0]['source_locator']='https://invalid.example/never-open'
        self.p[KEY]=[assertion(self.p)]
        before=copy.deepcopy(self.p)
        with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')), \
             patch('subprocess.run',side_effect=AssertionError('execution forbidden')):
            result=review(self.p);render_text(result);template(self.p)
        self.assertEqual(self.p,before)
        self.assertEqual(result['external_calls'],0)

    def test_clean_import_orders_have_no_cycles(self):
        for modules in ('report_study_review,evidence_workflow,prisma_reports',
                        'research_bundle,report_study_review_links,report_study_review'):
            result=subprocess.run([sys.executable,'-c','import '+modules],cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)


    def test_exclude_position_with_results_is_literal_cue_not_filter(self):
        self.p[KEY]=[assertion(self.p,study='study-B',decision='exclude')]
        before=copy.deepcopy(self.p['evidence']);result=run(self.p)
        row=next(x for x in result[VIEW]['membership_review_ledger'] if x['study_id']=='study-B')
        self.assertIn('CURRENT_EXCLUDE_POSITION_WITH_RESULT_ROWS',row['comparison_cues'])
        self.assertTrue(row['has_result_rows']);self.assertEqual(self.p['evidence'],before)
        p=copy.deepcopy(self.p);p['evidence']=[x for x in p['evidence'] if x['study_id']!='study-B'];p['gaps']=[]
        row=next(x for x in run(p)[VIEW]['membership_review_ledger'] if x['study_id']=='study-B')
        self.assertNotIn('CURRENT_EXCLUDE_POSITION_WITH_RESULT_ROWS',row['comparison_cues'])
        self.assertEqual(row['current_decisions'],['exclude'])

    def test_documented_fictional_example_counts_and_preserved_canonical_data(self):
        from prisma_reports import report_flow
        p=json.loads((ROOT/'examples/report-study-reviews.json').read_text(encoding='utf-8'))
        bare=copy.deepcopy(p);bare.pop(KEY)
        result=review(p)
        self.assertEqual({k:result['counts'][k] for k in ('current_memberships','orphan_pair_views','review_assertions',
                         'current_source_reviews','stale_source_reviews','current_memberships_with_review_cues')},
                         dict(current_memberships=3,orphan_pair_views=1,review_assertions=5,current_source_reviews=4,
                              stale_source_reviews=1,current_memberships_with_review_cues=2))
        before,after=report_flow(bare),report_flow(p)
        for key in ('record_flow','report_flow','report_csv','report_study_coverage'): self.assertEqual(before[key],after[key])
        drafts=template(p)[KEY];self.assertEqual(len(drafts),3)
        self.assertTrue(all(row['reviewed_source_ids'] is None for row in drafts))
        self.assertEqual(template(p,'report-one','study-C')[KEY],[])

    def test_documented_cli_audit_handoff_comparison_bundle_journey(self):
        fixture=ROOT/'examples/report-study-reviews.json';before=fixture.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            destination=Path(tmp)/'view.json'
            report=self.cli(fixture,'--report-id=report-one','--study-id=study-B','--template','--text','--output',str(destination))
            self.assertEqual(report.returncode,0,report.stderr)
            self.assertEqual(json.loads(destination.read_bytes())[KEY][0]['reviewed_source_ids'],None)
            for script,args in [('prisma_audit.py',[str(fixture),'--text']),('review_handoff.py',[str(fixture),'--text']),
                                ('compare_runs.py',[str(fixture),str(fixture),'--text']),
                                ('research_bundle.py',['create',str(fixture),str(Path(tmp)/'bundle.zip')]),
                                ('research_bundle.py',['verify',str(Path(tmp)/'bundle.zip')])]:
                run=subprocess.run([sys.executable,str(ROOT/script),*args],cwd=ROOT,capture_output=True)
                self.assertEqual(run.returncode,0,(script,run.stderr))
        self.assertEqual(fixture.read_bytes(),before)


    def test_renamed_study_is_new_pair_and_old_assertion_stays_orphan(self):
        from compare_runs import compare_protocols
        self.p[KEY]=[assertion(self.p,study='study-C')]
        after=copy.deepcopy(self.p);after['reports'][0]['study_ids'][-1]='study-D'
        result=review(after)
        old=next(row for row in result['membership_review_ledger'] if row['study_id']=='study-C')
        new=next(row for row in result['membership_review_ledger'] if row['study_id']=='study-D')
        self.assertFalse(old['membership_currently_declared']);self.assertEqual(old['stale_review_ids'],['review-1'])
        self.assertTrue(new['membership_currently_declared']);self.assertEqual(new['review_ids'],[])
        changes=compare_protocols(self.p,after)['report_study_review_changes']['pair_projection_changes']
        self.assertEqual(changes['added_pairs'],[dict(report_id='report-one',study_id='study-D')])
        self.assertEqual(changes['removed_pairs'],[])


if __name__=='__main__': unittest.main()
