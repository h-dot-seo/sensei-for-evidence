"""Fictional supplied human decisions: exact binding, flat receipts and atomic IO."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from evidence_workflow import run
from json_io import canonical_json_bytes
from tests.test_screening_reviews import protocol, assertion
import screening_decision as decision
import screening_decision_links as links

ROOT = Path(__file__).resolve().parents[1]
HISTORY = 'screening_decision_history'


class ScreeningDecisionTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()

    def document(self, p=None, rid='r1', receipt_id='decision-1', **fields):
        p = self.p if p is None else p
        document = decision.prepare(p, rid)['decision_document']
        document.update(receipt_id=receipt_id, decision='include', reason='Fictional explicit reason',
                        adjudicator='Fictional human', decided_at='2026-11-04',
                        rationale='Fictional supplied choice, not computed consensus',
                        source_locator='fictional://human-decision')
        document.update(fields)
        return document

    def applied(self, p=None, rid='r1', receipt_id='decision-1', **fields):
        p = self.p if p is None else p
        return decision.assemble(p, self.document(p, rid, receipt_id, **fields))['protocol_candidate']

    def reseal(self, p, index=0, source=False):
        receipt = p[HISTORY]['receipts'][index]
        target = receipt['target']
        if source:
            basis = target['source_target']['source_basis']
            target['source_target']['source_basis_sha256'] = links.digest(basis)
        target['target_sha256'] = links.digest({k:v for k,v in target.items() if k!='target_sha256'})
        receipt['assertion']['target_sha256'] = target['target_sha256']
        receipt['receipt_sha256'] = links.digest({k:v for k,v in receipt.items() if k!='receipt_sha256'})

    def test_target_blank_human_fields_exact_whole_input_and_detached(self):
        before = copy.deepcopy(self.p)
        prepared = decision.prepare(self.p, 'r1')
        doc = prepared['decision_document']
        self.assertEqual(set(doc), links.DOCUMENT_FIELDS)
        for key, value in doc.items():
            if key not in ('schema_version', 'record_id', 'target_sha256'):
                self.assertIsNone(value, key)
        self.assertEqual(doc['record_id'], 'r1')
        self.assertEqual(prepared['target']['input_protocol_sha256'], hashlib.sha256(canonical_json_bytes(self.p)).hexdigest())
        self.assertEqual(prepared['target']['prior_screening'], self.p['screening'][0])
        self.assertIsNone(prepared['target']['previous_receipt_sha256'])
        with self.assertRaises(ValueError): decision.assemble(self.p, doc)
        prepared['target']['prior_screening']['reason'] = 'mutated detached output'
        self.assertEqual(self.p, before)

    def test_conflict_unclear_stale_retained_and_choice_has_no_quorum(self):
        self.p['screening_reviews'] = [assertion(self.p, decision='exclude'),
            assertion(self.p, reviewer='Fictional B', decision='unclear', review_id='b'),
            dict(assertion(self.p, reviewer='Fictional C', decision='exclude', review_id='c'), source_basis_sha256='0'*64)]
        before = copy.deepcopy(self.p)
        p = self.applied()
        self.assertEqual(p['screening_reviews'], before['screening_reviews'])
        target = p[HISTORY]['receipts'][0]['target']
        self.assertEqual(target['review_snapshots'], before['screening_reviews'])
        self.assertEqual(p['screening'][0]['decision'], 'include')
        self.assertEqual(run(p)['screening_review']['review_ledger'], run(before)['screening_review']['review_ledger'])
        self.assertEqual(run(p)['screening_review']['records_with_review_cues'], run(before)['screening_review']['records_with_review_cues'])
        self.assertEqual(self.p, before)

    def test_existing_metadata_position_and_cross_record_isolation(self):
        self.p['screening'][0]['supplied_metadata'] = {'note':['Fictional retained note']}
        before = copy.deepcopy(self.p)
        p = self.applied(decision='exclude')
        expected = copy.deepcopy(before['screening'])
        expected[0].update(decision='exclude', reason='Fictional explicit reason')
        self.assertEqual(p['screening'], expected)
        self.assertEqual({k:v for k,v in p.items() if k not in ('screening',HISTORY)},
                         {k:v for k,v in before.items() if k!='screening'})

    def test_new_canonical_row_appended_without_version_or_date_inference(self):
        p = self.applied(rid='pending', decided_at='1999-12-31')
        self.assertEqual(p['screening'][:-1], self.p['screening'])
        self.assertEqual(p['screening'][-1], {'record_id':'pending','decision':'include','reason':'Fictional explicit reason'})
        self.assertEqual(p['version'], self.p['version'])
        self.assertEqual(p[HISTORY]['receipts'][0]['assertion']['decided_at'], '1999-12-31')
        self.assertIsNone(p[HISTORY]['receipts'][0]['target']['prior_screening'])

    def test_reason_only_edit_and_exact_reason_comparison(self):
        p = self.applied()
        self.assertEqual(p['screening'][0]['decision'], self.p['screening'][0]['decision'])
        self.assertTrue(decision.inspect(p)['receipt_ledger'][0]['matches_current_screening'])
        p['screening'][0]['reason'] += ' '
        self.assertFalse(decision.inspect(p)['receipt_ledger'][0]['matches_current_screening'])

    def test_whole_input_changes_stale_document_without_mutation(self):
        doc = self.document()
        mutations = [lambda p:p.update(version='fictional-v2'),
            lambda p:p['screening'][1].update(reason='Unrelated reason edit'),
            lambda p:p['searches'][0].update(query='Other supplied query'),
            lambda p:p.update(screening_reviews=[assertion(p)]),
            lambda p:p['inclusion_criteria'].append('Other supplied criterion')]
        for mutate in mutations:
            p = copy.deepcopy(self.p); mutate(p); original = copy.deepcopy(p)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): decision.assemble(p, doc)
            self.assertEqual(p, original)

    def test_assembly_exposes_before_after_flows_and_preserved_reviews(self):
        self.p['screening_reviews']=[assertion(self.p,decision='exclude')]
        result=decision.assemble(self.p,self.document(decision='exclude'))
        self.assertEqual(result['before_flow'],run(self.p)['flow'])
        self.assertEqual(result['after_flow'],run(result['protocol_candidate'])['flow'])
        self.assertEqual(result['before_flow']['included'],1)
        self.assertEqual(result['after_flow']['included'],0)
        self.assertFalse(result['review_assertions_changed'])
        self.assertEqual(result['external_calls'],0)
        self.assertEqual(result['screening_review_before']['review_ledger'][0]['review'],
                         result['screening_review_after']['review_ledger'][0]['review'])

    def test_inspect_selection_counts_and_full_unselected_validation(self):
        p=self.applied(); p=self.applied(p,'r2','decision-2')
        view=decision.inspect(p,'r1')
        self.assertEqual(view['counts']['receipts'],1)
        self.assertEqual(view['protocol_counts']['receipts'],2)
        self.assertEqual(view['selection']['validation_scope'],'ENTIRE_PROTOCOL')
        self.assertEqual(view['record_history'][0]['record_id'],'r1')
        for rid in ('R1','r1 ','',1,True):
            with self.subTest(rid=rid),self.assertRaises(ValueError): decision.inspect(p,rid)
        p[HISTORY]['receipts'][1]['assertion']['decided_at']='invalid'
        with self.assertRaises(ValueError): decision.inspect(p,'r1')
        with self.assertRaises(ValueError): decision.prepare(p,'r1')

    def test_strict_document_fields_types_dates_and_hashes(self):
        valid = self.document()
        wrong = [('schema_version',True),('schema_version',1.0),('schema_version',2),
                 ('decision','unclear'),('decision',' include'),('record_id','r1 '),
                 ('decided_at','2026-02-30'),('decided_at','20261104'),('decided_at','2026-11-04T00:00:00Z'),
                 ('target_sha256','A'*64),('target_sha256','0'*63),('target_sha256','0'*64)]
        for key in links.DOCUMENT_FIELDS-{'schema_version'}:
            wrong.extend([(key,None),(key,''),(key,'  '),(key,1),(key,[])])
        for key,value in wrong:
            doc = copy.deepcopy(valid); doc[key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError): decision.assemble(self.p,doc)
        for mode in ('missing','extra'):
            doc=copy.deepcopy(valid)
            if mode=='missing': del doc['rationale']
            else: doc['approved']=True
            with self.assertRaises(ValueError): decision.assemble(self.p,doc)

    def test_sequential_receipts_flat_deduplicated_and_dates_not_winners(self):
        first = self.applied(decision='exclude')
        second = self.applied(first, receipt_id='decision-2', decided_at='2000-01-01')
        history=second[HISTORY]
        self.assertEqual(len(history['source_contexts']),1)
        self.assertEqual(len(history['receipts']),2)
        self.assertEqual(history['receipts'][1]['previous_receipt_sha256'],history['receipts'][0]['receipt_sha256'])
        self.assertEqual(history['receipts'][1]['receipt_index'],1)
        self.assertEqual(second['screening'][0]['decision'],'include')
        self.assertNotIn(HISTORY,json.dumps(history['receipts']))
        ledger=decision.inspect(second)['receipt_ledger']
        self.assertFalse(ledger[0]['matches_current_screening'])
        self.assertTrue(ledger[1]['matches_current_screening'])
        self.assertTrue(ledger[1]['prior_row_matches_preceding_record_result'])

    def test_duplicate_receipt_id_rejected_and_manual_intervening_edit_is_cue(self):
        p=self.applied()
        with self.assertRaises(ValueError): self.applied(p)
        p['screening'][0]['reason']='Manually supplied intervening reason'
        p=self.applied(p,receipt_id='decision-2')
        row=decision.inspect(p)['receipt_ledger'][1]
        self.assertFalse(row['prior_row_matches_preceding_record_result'])
        self.assertIn('PRIOR_ROW_DIFFERS_FROM_PRECEDING_RECORD_RESULT',row['comparison_cues'])

    def test_receipt_tampering_and_resealed_generated_result_rejected(self):
        base=self.applied()
        for field,value in [('receipt_index',True),('receipt_index',1),('previous_receipt_sha256','0'*64),('receipt_id','other')]:
            p=copy.deepcopy(base); p[HISTORY]['receipts'][0][field]=value
            self.reseal(p)
            with self.subTest(field=field),self.assertRaises(ValueError): decision.inspect(p)
        p=copy.deepcopy(base); p[HISTORY]['receipts'][0]['result_screening']['reason']='Tampered result'
        self.reseal(p)
        with self.assertRaises(ValueError): decision.inspect(p)
        p=copy.deepcopy(base); p[HISTORY]['receipts'][0]['assertion']['rationale']='Tampered assertion'
        with self.assertRaises(ValueError): decision.inspect(p)

    def test_broken_chain_and_duplicate_receipt_forks_rejected(self):
        first=self.applied(); base=self.applied(first,receipt_id='decision-2')
        for mutate in (lambda h:h['receipts'].reverse(),
                       lambda h:h['receipts'].append(copy.deepcopy(h['receipts'][0])),
                       lambda h:h['receipts'][1].update(previous_receipt_sha256='0'*64)):
            p=copy.deepcopy(base); mutate(p[HISTORY])
            with self.assertRaises(ValueError): decision.inspect(p)

    def test_catalog_digest_duplicate_and_orphan_rejected(self):
        base=self.applied()
        for mode in ('digest','duplicate','orphan','missing'):
            p=copy.deepcopy(base); contexts=p[HISTORY]['source_contexts']
            if mode=='digest': contexts[0]['search']['query']='tampered'
            elif mode=='duplicate': contexts.append(copy.deepcopy(contexts[0]))
            elif mode=='orphan':
                row=copy.deepcopy(contexts[0]); row['search']['query']='orphan'
                row['search_context_sha256']=links.digest(row['search']); contexts.append(row)
            else: contexts.clear()
            with self.subTest(mode=mode),self.assertRaises(ValueError): decision.inspect(p)

    def test_resealed_source_record_membership_and_occurrence_integrity(self):
        base=self.applied()
        for mode in ('record_index','input_pointer','source_identity','ref_pointer','ref_index'):
            p=copy.deepcopy(base); target=p[HISTORY]['receipts'][0]['target']; source=target['source_target']
            if mode=='record_index': source['source_basis']['occurrences'][0]['record_index']=1
            elif mode=='input_pointer': source['source_basis']['occurrences'][0]['input_pointer']='/searches/0/record_ids/1'
            elif mode=='source_identity': source['source_basis']['record_id']='r2'
            elif mode=='ref_pointer': target['source_context_refs'][0]['input_pointer']='/searches/9'
            else: target['source_context_refs'][0]['search_index']=True
            self.reseal(p,source=True)
            with self.subTest(mode=mode),self.assertRaises(ValueError): decision.inspect(p)

    def test_resealed_review_snapshots_must_be_valid_same_historical_record(self):
        self.p['screening_reviews']=[assertion(self.p)]
        base=self.applied()
        for key,value in [('record_id','r2'),('reviewed_at','bad'),('source_basis_sha256','UPPER'),('decision','invalid')]:
            p=copy.deepcopy(base); p[HISTORY]['receipts'][0]['target']['review_snapshots'][0][key]=value
            self.reseal(p)
            with self.subTest(key=key),self.assertRaises(ValueError): decision.inspect(p)

    def test_stale_criteria_and_changed_reviews_are_cues_not_invalidity(self):
        self.p['screening_reviews']=[assertion(self.p)]
        p=self.applied(); retained=copy.deepcopy(p[HISTORY])
        p['inclusion_criteria'].append('New supplied criterion')
        p['screening_reviews'][0]['rationale']='Edited supplied rationale'
        row=decision.inspect(p)['receipt_ledger'][0]
        self.assertEqual(row['current_source_match_status'],'STALE_SOURCE')
        self.assertEqual(row['review_snapshot_match_status'],'CHANGED_ASSERTIONS')
        self.assertEqual(p[HISTORY],retained)
        self.assertEqual(row['receipt']['target']['review_snapshots'],self.p['screening_reviews'])

    def test_removed_record_history_is_retained_and_inspectable(self):
        p=self.applied(); retained=copy.deepcopy(p[HISTORY])
        p['screening']=[r for r in p['screening'] if r['record_id']!='r1']
        p['searches'][0]['record_ids'].remove('r1'); p['searches'][0]['total_count']=2
        view=decision.inspect(p,'r1')
        self.assertEqual(view['receipt_ledger'][0]['current_source_match_status'],'RECORD_NOT_ENUMERATED')
        self.assertIsNone(view['receipt_ledger'][0]['current_source_basis_sha256'])
        self.assertEqual(p[HISTORY],retained)
        with self.assertRaises(ValueError): decision.prepare(p,'r1')

    def test_linked_evidence_and_reports_reject_exclusion_atomically(self):
        p=json.loads((ROOT/'examples/report-protocol.json').read_text())
        before=copy.deepcopy(p)
        with self.assertRaises(ValueError): self.applied(p,decision='exclude')
        self.assertEqual(p,before)
        p['evidence']=[]; p['gaps']=[]
        with self.assertRaises(ValueError): self.applied(p,decision='exclude')

    def test_entire_invalid_reports_validate_even_unselected_or_scalar(self):
        for reports in ('invalid',42,{},[dict(report_id='bad',record_ids=['r2'],retrieval='bad')]):
            p=copy.deepcopy(self.p); p['reports']=reports
            with self.subTest(reports=reports),self.assertRaises(ValueError): decision.prepare(p,'r1')
            with self.assertRaises(ValueError): decision.inspect(p,'r1')
            with self.assertRaises(ValueError): decision.assemble(p,self.document())

    def test_history_caps_bounded_mock_and_input_unchanged(self):
        p=self.applied(); original=copy.deepcopy(p)
        with patch.object(links,'MAX_RECEIPTS',1):
            with self.assertRaises(ValueError): self.applied(p,receipt_id='decision-2')
        with patch.object(links,'MAX_HISTORY_BYTES',1):
            with self.assertRaises(ValueError): decision.inspect(p)
        self.assertEqual(p,original)

    def test_output_copy_isolation_across_candidate_receipt_and_view(self):
        doc=self.document(); before=copy.deepcopy(doc)
        result=decision.assemble(self.p,doc)
        result['appended_receipt']['assertion']['reason']='Detached receipt changed'
        self.assertEqual(result['protocol_candidate'][HISTORY]['receipts'][0]['assertion'],before)
        result['protocol_candidate']['screening'][0]['reason']='Candidate changed'
        self.assertEqual(self.p,protocol()); self.assertEqual(doc,before)
        view=decision.inspect(result['protocol_candidate'])
        view['receipt_ledger'][0]['receipt']['assertion']['reason']='View changed'
        self.assertEqual(result['protocol_candidate'][HISTORY]['receipts'][0]['assertion'],before)

    def test_legacy_omission_and_exact_empty_opt_in(self):
        from prisma_audit import export_audit
        from prisma_reports import report_flow
        from synthesis_review import snapshot
        self.p['reports']=[]
        for project in (run,export_audit,report_flow,snapshot):
            self.assertNotIn(HISTORY,project(self.p))
        self.p[HISTORY]={'schema_version':1,'source_contexts':[],'receipts':[]}
        self.assertEqual(run(self.p)[HISTORY]['stage'],'SUPPLIED')
        for value in (None,[],{'schema_version':True,'source_contexts':[],'receipts':[]}):
            p=copy.deepcopy(self.p); p[HISTORY]=value
            with self.assertRaises(ValueError): run(p)

    def test_core_audit_report_snapshot_projection_agrees(self):
        from prisma_audit import export_audit
        from prisma_reports import report_flow
        from synthesis_review import snapshot
        self.p['reports']=[]
        p=self.applied(); expected=run(p)[HISTORY]
        for project in (export_audit,report_flow,snapshot):
            with self.subTest(project=project.__name__): self.assertEqual(project(p)[HISTORY],expected)

    def test_history_metadata_does_not_change_source_review_targets(self):
        from screening_links import prepare_targets
        p=self.applied(reason=self.p['screening'][0]['reason'])
        self.assertEqual(prepare_targets(p),prepare_targets(self.p))
        baseline=run(self.p); after=run(p); after.pop(HISTORY)
        self.assertEqual(after,baseline)

    def test_status_handoff_no_retrospective_pending_queue_and_compare_opt_in(self):
        from research_status import status
        from review_handoff import handoff
        from compare_runs import compare_protocols
        self.assertNotIn('screening_decision_changes',compare_protocols(self.p,self.p))
        p=self.applied(); p['screening'][0]['reason']='Later manual reason'
        expected=decision.inspect(p)['records_with_history_cues']
        self.assertEqual(expected,['r1'])
        self.assertFalse(any('decision_history' in key for key in status(p)['queues']))
        self.assertFalse(any('decision_history' in step.get('queue','') for step in handoff(p)['manual_review_steps']))
        delta=compare_protocols(self.p,p)['screening_decision_changes']
        self.assertEqual(delta['receipt_changes']['added_ids'],['decision-1'])
        self.assertIsNone(delta['receipt_comparisons'][0]['before'])
        self.assertFalse(delta['receipt_comparisons'][0]['after']['matches_current_screening'])
        self.assertEqual(status(p)[HISTORY]['scope'],'retrospective_comparisons_not_pending_tasks')
        self.assertEqual(handoff(p)[HISTORY],status(p)[HISTORY])
        self.assertTrue(any(v['script']=='screening_decision.py' for v in handoff(p)['detailed_views']))

    def test_compare_retained_receipt_source_changes_without_rewriting_history(self):
        from compare_runs import compare_protocols,render_text
        before=self.applied(); after=copy.deepcopy(before)
        after['searches'][0]['query']='New literal supplied query'
        delta=compare_protocols(before,after)
        change=delta['screening_decision_changes']
        self.assertEqual(change['receipt_changes']['changed'],[])
        self.assertEqual(change['receipt_changes']['unchanged_count'],1)
        pair=change['receipt_comparisons'][0]
        self.assertEqual(pair['before']['current_source_match_status'],'CURRENT_SOURCE')
        self.assertRegex(pair['before']['current_source_basis_sha256'],r'^[0-9a-f]{64}$')
        self.assertEqual(pair['after']['current_source_match_status'],'STALE_SOURCE')
        self.assertNotEqual(pair['before']['current_source_basis_sha256'],pair['after']['current_source_basis_sha256'])
        self.assertEqual(pair['before']['receipt'],pair['after']['receipt'])
        self.assertIn('STALE_SOURCE',render_text(delta))
        removal=compare_protocols(after,self.p)['screening_decision_changes']
        self.assertEqual(removal['receipt_changes']['removed_ids'],['decision-1'])

    def test_real_fictional_csv_import_allows_decision_history_enrichment(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        from bibliographic_integrity import ENRICHMENT_FIELDS
        self.assertIn(HISTORY,ENRICHMENT_FIELDS)
        helper=BibliographicReviewTests(); helper.setUp(); p=helper.imported()
        rid=p['searches'][0]['record_ids'][0]
        p=self.applied(p,rid)
        self.assertEqual(run(p)[HISTORY]['receipt_ledger'][0]['current_source_match_status'],'CURRENT_SOURCE')
        self.assertTrue(p[HISTORY]['receipts'][0]['target']['source_target']['source_basis']['bibliographic_rows'])

    def test_resealed_bibliographic_fragment_pointers_require_canonical_indices(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        helper=BibliographicReviewTests(); helper.setUp(); imported=helper.imported()
        rid=imported['searches'][0]['record_ids'][0]
        base=self.applied(imported,rid)
        for mode in ('leading_zero_import','leading_zero_row','mismatched_import_index','duplicate_pointer'):
            p=copy.deepcopy(base)
            rows=p[HISTORY]['receipts'][0]['target']['source_target']['source_basis']['bibliographic_rows']
            if mode=='leading_zero_import':
                rows[0]['source_pointer']=rows[0]['source_pointer'].replace('/imports/0/','/imports/00/')
            elif mode=='leading_zero_row':
                rows[0]['source_pointer']=rows[0]['source_pointer'].replace('/record_rows/0','/record_rows/00')
            elif mode=='mismatched_import_index': rows[0]['import_index']=1
            else: rows[1]['source_pointer']=rows[0]['source_pointer']
            self.reseal(p,source=True)
            with self.subTest(mode=mode),self.assertRaises(ValueError): decision.inspect(p)

    def test_csv_decision_second_import_retains_flat_history_and_same_record_mapping(self):
        from tests.test_bibliographic_review import BibliographicReviewTests
        import bibliographic_review as review
        helper=BibliographicReviewTests(); helper.setUp()
        p,artifact,choices=helper.second()
        rid=p['searches'][0]['record_ids'][0]
        first=self.applied(p,rid)
        retained=copy.deepcopy(first[HISTORY])
        doc=helper.signed(protocol=first,artifact=artifact,choices=choices)
        second=review.assemble(first,artifact,doc)['protocol_candidate']
        self.assertEqual(second[HISTORY],retained)
        self.assertEqual(decision.inspect(second)['receipt_ledger'][0]['current_source_match_status'],'STALE_SOURCE')
        third=self.applied(second,rid,receipt_id='decision-2')
        rows=third[HISTORY]['receipts'][1]['target']['source_target']['source_basis']['bibliographic_rows']
        self.assertIn('same_record',[row['resolution']['disposition'] for row in rows])
        self.assertEqual(third[HISTORY]['receipts'][0],retained['receipts'][0])
        pending=[third[HISTORY]]
        while pending:
            item=pending.pop()
            if isinstance(item,dict):
                self.assertNotIn('bibliographic_imports',item)
                self.assertNotIn(HISTORY,item)
                pending.extend(item.values())
            elif isinstance(item,list): pending.extend(item)
        run(third)

    def test_bundle_deterministic_roundtrip_and_new_engine_fingerprints(self):
        from research_bundle import build_bundle,verify
        self.p['reports']=[]
        p=self.applied(); raw=json.dumps(p).encode(); packed=build_bundle(raw)
        self.assertEqual(packed,build_bundle(raw))
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            research=json.loads(archive.read('research.json')); reports=json.loads(archive.read('reports.json'))
            self.assertEqual(research[HISTORY],reports[HISTORY])
            manifest=json.loads(archive.read('manifest.json'))
            for name in ('screening_decision.py','screening_decision_links.py'):
                self.assertEqual(manifest['engine_sha256'][name],hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fictional.zip'; path.write_bytes(packed)
            self.assertTrue(verify(path)['valid'])

    def test_documented_fixtures_explicit_choice_reverse_dates_and_conflict(self):
        base=json.loads((ROOT/'examples/screening-reviews.json').read_bytes())
        document=json.loads((ROOT/'examples/screening-decision-document.json').read_bytes())
        final=json.loads((ROOT/'examples/screening-decisions.json').read_bytes())
        first=decision.assemble(base,document)['protocol_candidate']
        receipts=final[HISTORY]['receipts']
        self.assertEqual(first[HISTORY]['receipts'][0],receipts[0])
        self.assertEqual(decision.assemble(first,receipts[1]['assertion'])['protocol_candidate'],final)
        self.assertEqual(len(receipts),2)
        self.assertEqual([r['target']['record_id'] for r in receipts],['record-alpha']*2)
        self.assertGreater(receipts[0]['assertion']['decided_at'],receipts[1]['assertion']['decided_at'])
        view=decision.inspect(final)
        self.assertEqual(view['counts']['source_contexts'],1)
        self.assertFalse(view['receipt_ledger'][0]['matches_current_screening'])
        self.assertTrue(view['receipt_ledger'][1]['matches_current_screening'])
        self.assertEqual(base['screening_reviews'],final['screening_reviews'])
        before=next(row for row in run(base)['screening_review']['record_review_ledger'] if row['record_id']=='record-alpha')
        after=next(row for row in run(final)['screening_review']['record_review_ledger'] if row['record_id']=='record-alpha')
        self.assertEqual(before['current_decisions'],after['current_decisions'])
        self.assertIn('DIFFERING_CURRENT_POSITIONS',after['comparison_cues'])

    def test_documented_cli_target_assemble_inspect_compare_audit_bundle(self):
        source_fixture=ROOT/'examples/screening-reviews.json'
        document_fixture=ROOT/'examples/screening-decision-document.json'
        original=(source_fixture.read_bytes(),document_fixture.read_bytes())
        def script(name,*args):
            result=subprocess.run([sys.executable,str(ROOT/name),*map(str,args)],capture_output=True,cwd=ROOT,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            return json.loads(result.stdout)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.json'; document=Path(temp)/'document.json'
            target=Path(temp)/'target.json'; candidate=Path(temp)/'candidate.json'; bundle=Path(temp)/'bundle.zip'
            source.write_bytes(original[0]); document.write_bytes(original[1])
            prepared=self.cli('target',source,'--record-id','record-alpha','--output',target)
            self.assertEqual(prepared.returncode,0,prepared.stderr)
            self.assertEqual(json.loads(target.read_bytes())['decision_document']['target_sha256'],
                             json.loads(original[1])['target_sha256'])
            assembled=self.cli('assemble',source,document,'--protocol-output',candidate)
            self.assertEqual(assembled.returncode,0,assembled.stderr)
            inspection=self.cli('inspect',candidate,'--record-id','record-alpha')
            self.assertEqual(inspection.returncode,0,inspection.stderr)
            self.assertTrue(json.loads(inspection.stdout)['receipt_ledger'][0]['matches_current_screening'])
            comparison=script('compare_runs.py',source,candidate)
            self.assertEqual(comparison['screening_decision_changes']['receipt_changes']['added_ids'],['decision-alpha-first'])
            audit=script('prisma_audit.py',candidate)
            self.assertEqual(audit[HISTORY]['counts']['receipts'],1)
            script('research_bundle.py','create',candidate,bundle)
            self.assertTrue(script('research_bundle.py','verify',bundle)['valid'])
            self.assertEqual((source.read_bytes(),document.read_bytes()),original)
        self.assertEqual((source_fixture.read_bytes(),document_fixture.read_bytes()),original)

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'screening_decision.py'),*map(str,args)],capture_output=True,
            cwd=ROOT,timeout=30,env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONUTF8='0'))

    def test_cli_utf8_crlf_target_and_exclusive_output(self):
        self.p['question']='가상 질문\r\n두 번째 줄'
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'protocol.json'; output=Path(temp)/'target.json'
            source.write_bytes((json.dumps(self.p,ensure_ascii=False,indent=2)+'\n').replace('\n','\r\n').encode())
            result=self.cli('target',source,'--record-id','r1','--output',output,'--text')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('가상',result.stdout.decode())
            self.assertEqual(json.loads(output.read_bytes())['decision_document']['record_id'],'r1')
            original=output.read_bytes(); result=self.cli('target',source,'--record-id','r1','--output',output)
            self.assertNotEqual(result.returncode,0); self.assertEqual(result.stdout,b''); self.assertEqual(output.read_bytes(),original)

    def test_cli_assemble_writes_new_candidate_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'protocol.json'; document=Path(temp)/'decision.json'; out=Path(temp)/'candidate.json'
            source.write_text(json.dumps(self.p)); document.write_text(json.dumps(self.document()))
            original=(source.read_bytes(),document.read_bytes())
            result=self.cli('assemble',source,document,'--protocol-output',out)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(out.read_bytes()),json.loads(result.stdout)['protocol_candidate'])
            self.assertEqual((source.read_bytes(),document.read_bytes()),original)
            saved=out.read_bytes(); result=self.cli('assemble',source,document,'--protocol-output',out)
            self.assertNotEqual(result.returncode,0); self.assertEqual(result.stdout,b''); self.assertEqual(out.read_bytes(),saved)

    def test_cli_invalid_input_empty_stdout_no_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'protocol.json'; out=Path(temp)/'target.json'
            for raw in (b'{"question":"a","question":"b"}',b'not-json',json.dumps(dict(self.p,reports=42)).encode()):
                source.write_bytes(raw)
                result=self.cli('target',source,'--record-id','r1','--output',out)
                self.assertNotEqual(result.returncode,0); self.assertEqual(result.stdout,b''); self.assertFalse(out.exists())

    def test_cli_hostile_controls_and_locator_remain_inert(self):
        with tempfile.TemporaryDirectory() as temp:
            marker=Path(temp)/'must-not-exist'; source=Path(temp)/'protocol.json'; document=Path(temp)/'decision.json'
            doc=self.document(reason='Fictional\x1b[31m\nreason',source_locator=f'file://{marker}; touch {marker}')
            source.write_text(json.dumps(self.p)); document.write_text(json.dumps(doc))
            result=self.cli('assemble',source,document,'--text')
            self.assertEqual(result.returncode,0,result.stderr); self.assertNotIn(b'\x1b',result.stdout); self.assertFalse(marker.exists())


if __name__=='__main__':
    unittest.main()
