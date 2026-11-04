"""Explicit fictional document context binds work, never reading or acceptance."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from evidence_workflow import run
from report_review_links import prepare_targets
from work_document_links import link_work_documents
from work_review import review_packets, navigation_summary, render_brief, render_text
from review_handoff import handoff
from research_status import status
from research_bundle import build_bundle, verify
from compare_runs import compare_protocols

ROOT = Path(__file__).resolve().parent


def fixture():
    p = json.loads((ROOT/'examples/report-source-check-protocol.json').read_text(encoding='utf-8'))
    own = copy.deepcopy(p['gaps'][1])
    own.update(work_package_id='WP-OWN', source_refs=[dict(kind='record', record_id='record-one')],
               document_source_ids=['source-main'], depends_on=[])
    direct = copy.deepcopy(own)
    direct.update(work_package_id='WP-DIRECT', depends_on=['WP-OWN'])
    direct.pop('document_source_ids')
    indirect = copy.deepcopy(direct)
    indirect.update(work_package_id='WP-INDIRECT', depends_on=['WP-DIRECT'])
    p['gaps'] = [own, direct, indirect]
    return p


def targets(p):
    return {r['work_package_id']: r for r in run(p)['planning']['review_targets']}


def complete(p):
    for w in p['gaps']:
        w.update(status='COMPLETE', acceptance_verified=True,
                 artifact_locator='fictional://completion/'+w['work_package_id'])
    ledger = run(p)['planning']['completion_ledger']
    hashes = {r['work_package_id']: r['current_basis_sha256'] for r in ledger}
    for w in p['gaps']:
        w['completion_basis_sha256'] = hashes[w['work_package_id']]
    return p


class WorkDocumentSourcesTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()

    def states(self, p=None):
        return {r['work_package_id']: r['source_match_status'] for r in
                run(self.p if p is None else p)['planning']['completion_ledger']}

    def test_planning_derives_binding_internally_and_rejects_external_map(self):
        from planning_links import link_planning
        r=run(self.p)
        args=(self.p,r['evidence'],r['work_packages'],r['context'],r['appraisal'],r['experiments'],r['synthesis'])
        forged=link_work_documents(self.p,r['work_packages'])
        forged['WP-OWN']['sources'][0].update(matched_record_ids=['not-a-protocol-record'],report_source_basis_sha256='0'*64)
        forged['WP-OWN']['sources'][0]['source']['document_version']='forged supplied context'
        with self.assertRaises(TypeError):
            link_planning(*args,document_sources=forged)
        self.assertEqual(link_planning(*args),r['planning'])
        self.assertEqual(r['planning']['review_targets'][0]['basis'].get('direct_dependency_document_sources'),
                         link_planning(*args)['review_targets'][0]['basis'].get('direct_dependency_document_sources'))

    def test_report_targets_prepare_once_only_when_work_opts_in(self):
        with patch('work_document_links.prepare_targets',wraps=prepare_targets) as prepare:
            run(self.p)
            self.assertEqual(prepare.call_count,1)
        p=copy.deepcopy(self.p);p['gaps'][0].pop('document_source_ids')
        with patch('work_document_links.prepare_targets',side_effect=AssertionError('no legacy document binding')):
            run(p)

    def test_exact_detached_context_and_whole_report_hash(self):
        before = copy.deepcopy(self.p)
        links = link_work_documents(self.p, self.p['gaps'])
        report = next(r for r in prepare_targets(self.p)['report_targets'] if r['report_id']=='report-one')
        self.assertEqual(links, {'WP-OWN': dict(schema_version=1, scope='explicit_work_document_sources',
            sources=[dict(source=self.p['report_sources'][0], matched_record_ids=['record-one'],
                          report_id='report-one', report_source_basis_sha256=report['source_basis_sha256'])])})
        self.assertNotIn('pointer', json.dumps(links))
        links['WP-OWN']['sources'][0]['source']['document_version']='changed output'
        self.assertEqual(self.p, before)

    def test_nonempty_unique_literal_ids_and_source_only_scope(self):
        for value in (None, [], {}, True, 'source-main', [None], [True], [''], ['source-main','source-main'],
                      ['source-main '], ['SOURCE-MAIN'], ['missing']):
            p=copy.deepcopy(self.p); p['gaps'][0]['document_source_ids']=value
            with self.subTest(value=value), self.assertRaises(ValueError): run(p)
        for work_type in ('evidence_review', None):
            p=copy.deepcopy(self.p); w=p['gaps'][0]; w.pop('source_refs'); w['evidence_ids']=['result-A']
            if work_type is None: w.pop('work_type')
            else: w['work_type']=work_type
            with self.subTest(work_type=work_type), self.assertRaises(ValueError): run(p)

    def test_wrong_report_and_planned_search_do_not_inherit_documents(self):
        p=copy.deepcopy(self.p); p['gaps'][0]['document_source_ids']=['source-uninspected']
        with self.assertRaises(ValueError): run(p)
        p=copy.deepcopy(self.p)
        p['search_plan']=[dict(search_id='planned', source='fictional', query='fictional', window='fictional')]
        p['gaps'][0]['source_refs']=[dict(kind='planned_search',search_id='planned')]
        with self.assertRaises(ValueError): run(p)

    def test_partial_record_intersection_uses_report_order(self):
        p=copy.deepcopy(self.p); p['reports'][0]['record_ids'].extend(['record-three','record-four'])
        p['searches'][0]['record_ids'].extend(['record-three','record-four'])
        p['searches'][0]['total_count']=len(p['searches'][0]['record_ids'])
        p['screening'].extend(dict(record_id=r,decision='include',reason='Fictional scope') for r in ['record-three','record-four'])
        p['gaps'][0]['source_refs']=[dict(kind='record',record_id=r) for r in ['record-four','record-one','record-two']]
        context=targets(p)['WP-OWN']['basis']['document_source_context']
        self.assertEqual(context['sources'][0]['matched_record_ids'],['record-one','record-four'])

    def test_pending_and_not_retrieved_null_digest_remain_supplied_context(self):
        for state in ('pending','not_retrieved'):
            p=copy.deepcopy(self.p); p['evidence']=[]
            p['reports'][0]=dict(report_id='report-one',record_ids=['record-one'],retrieval=state,
                                 decision='pending',reason='Fictional unresolved source')
            p['report_sources'][0]['document_sha256']=None
            with self.subTest(state=state):
                result=run(p)
                context=targets(p)['WP-OWN']['basis']['document_source_context']
                self.assertIsNone(context['sources'][0]['source']['document_sha256'])
                self.assertEqual(result['evidence'],[])
                self.assertEqual(result['conclusion_readiness'],'NOT_READY')

    def test_own_and_only_direct_dependency_context_is_added(self):
        rows=targets(self.p)
        own=rows['WP-OWN']['basis']; direct=rows['WP-DIRECT']['basis']; indirect=rows['WP-INDIRECT']['basis']
        self.assertNotIn('direct_dependency_document_sources',own)
        self.assertNotIn('document_source_context',direct)
        self.assertEqual(direct['direct_dependency_document_sources'],[
            dict(work_package_id='WP-OWN',document_source_context=own['document_source_context'])])
        self.assertNotIn('document_source_context',indirect)
        self.assertNotIn('direct_dependency_document_sources',indirect)
        self.p['gaps'][0]['document_source_context']={'freeform':'retained, not authoritative'}
        self.assertEqual(targets(self.p)['WP-OWN']['basis']['work_scope']['document_source_context'],
                         self.p['gaps'][0]['document_source_context'])

    def test_selected_descriptor_edit_stales_own_and_direct_not_indirect(self):
        complete(self.p); old=copy.deepcopy(self.p['gaps'])
        self.p['report_sources'][0]['document_version']='Fictional revision'
        self.assertEqual(self.states(),{'WP-OWN':'STALE_SOURCE','WP-DIRECT':'STALE_SOURCE','WP-INDIRECT':'CURRENT_SOURCE'})
        result=run(self.p)
        self.assertTrue(all(w['status']=='COMPLETE' and w['blocked_by']==[] for w in result['work_packages']))
        self.assertEqual(self.p['gaps'],old)
        self.assertTrue(all(r['acceptance_assessment']=='NOT_PERFORMED' and r['artifact_content_verification']=='NOT_PERFORMED'
                            for r in result['planning']['completion_ledger']))

    def test_whole_same_report_catalog_add_remove_reorder_and_unselected_edit_stale(self):
        complete(self.p)
        for change in ('add','remove','reorder','edit'):
            p=copy.deepcopy(self.p)
            if change=='add': p['report_sources'].append(dict(p['report_sources'][1],source_id='extra'))
            if change=='remove': p['report_sources'].pop(1)
            if change=='reorder': p['report_sources'][:2]=reversed(p['report_sources'][:2])
            if change=='edit': p['report_sources'][1]['document_version']='Changed unselected catalog entry'
            with self.subTest(change=change):
                self.assertEqual(self.states(p)['WP-OWN'],'STALE_SOURCE')
                self.assertEqual(self.states(p)['WP-DIRECT'],'STALE_SOURCE')
                self.assertEqual(self.states(p)['WP-INDIRECT'],'CURRENT_SOURCE')

    def test_unrelated_report_source_and_pointer_reorder_do_not_stale(self):
        complete(self.p)
        self.p['report_sources'][2]['document_version']='Unrelated fictional edition'
        self.p['report_sources'].insert(0,self.p['report_sources'].pop(2))
        self.assertEqual(set(self.states().values()),{'CURRENT_SOURCE'})

    def test_selected_source_deletion_and_invalid_unselected_scalar_reject(self):
        for mutation in ('delete','scalar'):
            p=copy.deepcopy(self.p)
            if mutation=='delete': p['report_sources'].pop(0)
            else: p['report_sources'][2]=False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): run(p)

    def test_result_content_and_review_metadata_do_not_change_document_context(self):
        before=targets(self.p)['WP-OWN']['basis']['document_source_context']
        self.p['evidence'][0]['result']='Changed fictional result content'
        from test_report_reviews import assertion
        self.p['report_reviews']=[assertion(self.p,report_id='report-one')]
        self.assertEqual(targets(self.p)['WP-OWN']['basis']['document_source_context'],before)

    def test_legacy_source_catalog_does_not_change_existing_hashes_or_shapes(self):
        p=json.loads((ROOT/'examples/completion-binding.json').read_text(encoding='utf-8'))
        before=run(p)
        from test_report_reviews import source
        p['report_sources']=[source(report_id=p['reports'][0]['report_id'])]
        after=run(p)
        self.assertEqual(after['planning'],before['planning'])
        self.assertEqual(after['work_packages'],before['work_packages'])
        self.assertEqual(link_work_documents(p,after['work_packages']),{})
        self.assertEqual(next(r for r in after['planning']['completion_ledger'] if r['work_package_id']=='WP-MECHANISM')['source_match_status'],'CURRENT_SOURCE')

    def test_csv_import_validated_provenance_reaches_report_hash(self):
        from test_bibliographic_review import BibliographicReviewTests
        from test_report_reviews import source
        helper=BibliographicReviewTests(); helper.setUp(); p=helper.imported()
        rid=p['searches'][0]['record_ids'][0]
        p['screening']=[dict(record_id=rid,decision='include',reason='Fictional scope')]
        p['reports']=[dict(report_id='report-1',record_ids=[rid],retrieval='retrieved',locator='fictional',decision='pending')]
        p['report_sources']=[source()]
        w=copy.deepcopy(self.p['gaps'][0]); w.update(source_refs=[dict(kind='record',record_id=rid)],document_source_ids=['source-1'])
        p['gaps']=[w]
        result=run(p); collection=result['bibliographic_collection']
        expected=prepare_targets(p,collection)['report_targets'][0]['source_basis_sha256']
        actual=result['planning']['review_targets'][0]['basis']['document_source_context']['sources'][0]
        self.assertEqual(actual['report_source_basis_sha256'],expected)
        self.assertEqual(link_work_documents(p,p['gaps'],collection)['WP-OWN']['sources'][0],actual)

    def test_packets_navigation_brief_and_handoff_preserve_context(self):
        result=review_packets(self.p)
        own=next(r for r in result['packets'] if r['work_package']['work_package_id']=='WP-OWN')
        self.assertEqual(own['document_source_context'],targets(self.p)['WP-OWN']['basis']['document_source_context'])
        self.assertIn('not document bytes or authenticity',own['document_source_boundary'])
        for rendered in (render_brief(result),render_text(result),json.dumps(navigation_summary(result)),json.dumps(handoff(self.p))):
            self.assertIn('document_source_context',rendered)
            self.assertIn('source-main',rendered)
        base=copy.deepcopy(self.p); base['gaps'][0].pop('document_source_ids')
        self.assertEqual(status(self.p)['queues'],status(base)['queues'])

    def test_comparison_has_exact_optional_changes_and_detached_snapshots(self):
        complete(self.p); after=copy.deepcopy(self.p); after['report_sources'][0]['document_version']='Changed edition'
        rows={r['work_package_id']:r for r in compare_protocols(self.p,after)['completion_work_impact']['work_packages']}
        for wid,field in [('WP-OWN','document_source_context'),('WP-DIRECT','direct_dependency_document_sources')]:
            change=rows[wid]['work_source_changes'][field]
            self.assertEqual(set(change),{'before','after','changed'})
            self.assertTrue(change['changed'])
            self.assertEqual(change['after'],rows[wid]['after'][field])
            self.assertIn(field,rows[wid]['work_source_changes']['changed_sections'])
        self.assertNotIn('document_source_context',rows['WP-INDIRECT']['work_source_changes'])
        rows['WP-OWN']['after']['document_source_context']['sources'][0]['source']['source_id']='mutated output'
        self.assertEqual(after['report_sources'][0]['source_id'],'source-main')

    def test_document_selection_does_not_bypass_existing_completion_guards(self):
        for missing in ('artifact_locator','acceptance_verified'):
            p=complete(copy.deepcopy(self.p)); p['gaps'][0].pop(missing)
            with self.subTest(missing=missing), self.assertRaises(ValueError): run(p)
        p=copy.deepcopy(self.p)
        p['gaps'][1].update(status='COMPLETE',artifact_locator='fictional://note',acceptance_verified=True)
        with self.assertRaisesRegex(ValueError,'unfinished dependency'): run(p)

    def test_inventory_and_review_edits_leave_completed_document_basis_current(self):
        from test_report_reviews import assertion as review_assertion
        from test_report_study_inventory import assertion as inventory_assertion
        complete(self.p)
        original=targets(self.p)
        self.p['report_reviews']=[review_assertion(self.p,report_id='report-one')]
        self.p['report_study_inventory']=[inventory_assertion(self.p,sources=['source-main'])]
        self.assertEqual(targets(self.p),original)
        self.assertEqual(set(self.states().values()),{'CURRENT_SOURCE'})
        self.p['report_reviews'][0]['rationale']='Changed fictional review narrative'
        self.p['report_study_inventory'][0]['description']='Changed fictional inventory narrative'
        self.assertEqual(targets(self.p),original)
        self.assertEqual(set(self.states().values()),{'CURRENT_SOURCE'})

    def test_selected_source_order_is_preserved_and_bound(self):
        self.p['gaps'][0]['document_source_ids']=['source-unbound','source-main']
        complete(self.p)
        context=targets(self.p)['WP-OWN']['basis']['document_source_context']
        self.assertEqual([r['source']['source_id'] for r in context['sources']],['source-unbound','source-main'])
        self.assertIsNone(context['sources'][0]['source']['document_sha256'])
        self.p['gaps'][0]['document_source_ids'].reverse()
        self.assertEqual(self.states()['WP-OWN'],'STALE_SOURCE')

    def test_bundle_conditional_columns_quoting_engine_copy_and_no_mutation(self):
        self.p['report_sources'][0]['document_version']='Fictional, "quoted"\nrevision'
        before=copy.deepcopy(self.p)
        data=build_bundle(json.dumps(self.p).encode())
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            reader=csv.DictReader(io.StringIO(z.read('work-packages.csv').decode()))
            self.assertEqual(reader.fieldnames[-3:],['document_source_ids','document_source_context','direct_dependency_document_sources'])
            rows={r['work_package_id']:r for r in reader}
            self.assertEqual(json.loads(rows['WP-OWN']['document_source_ids']),['source-main'])
            self.assertEqual(json.loads(rows['WP-OWN']['document_source_context']),targets(self.p)['WP-OWN']['basis']['document_source_context'])
            self.assertEqual(rows['WP-DIRECT']['document_source_context'],'')
            self.assertEqual(json.loads(rows['WP-INDIRECT']['direct_dependency_document_sources']),[])
            manifest=json.loads(z.read('manifest.json'))
            self.assertEqual(manifest['engine_sha256']['work_document_links.py'],
                             hashlib.sha256((ROOT/'work_document_links.py').read_bytes()).hexdigest())
            self.assertEqual(json.loads(z.read('protocol.json')),self.p)
        self.assertEqual(self.p,before)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bundle.zip'; path.write_bytes(data)
            self.assertTrue(verify(path)['valid'])
        self.p['gaps'][0].pop('document_source_ids')
        with zipfile.ZipFile(io.BytesIO(build_bundle(json.dumps(self.p).encode()))) as z:
            self.assertNotIn('document_source_ids',next(csv.reader(io.StringIO(z.read('work-packages.csv').decode()))))


if __name__=='__main__':
    unittest.main()
