"""Independent fictional source-append context tests, not scientific validation."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bibliographic_intake
import bibliographic_review
from evidence_workflow import run
from json_io import canonical_json_bytes
from report_review_links import prepare_targets as report_targets
import report_source_check
import report_source_intake as intake
from report_study_review_links import prepare_targets as study_targets
from report_study_inventory_review_links import prepare_targets as inventory_review_targets
import result_intake
import result_source_review

ROOT = Path(__file__).resolve().parent


def fixture(name='report-source-check-protocol.json'):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def declarations(report='report-one', source_id='independent-new-source', digest='c' * 64):
    return dict(schema_version=1, candidates=[dict(source=dict(source_id=source_id,
        report_id=report, source_locator='fictional://inert-new-source',
        document_version='Fictional supplementary declaration', document_sha256=digest),
        declared_by='Fictional declarer', declared_at='2026-11-04',
        declaration_note='Fictional software test; no source reading or authentication.')])


def append(protocol, document=None):
    document = declarations() if document is None else document
    review = intake.prepare(protocol, document)['review_document']
    review.update(receipt_id='independent-fictional-source-receipt',
        decision='append_source_declarations', reviewer='Fictional import reviewer',
        reviewed_at='2026-11-04', rationale='Fictional declaration append only.')
    return intake.assemble(protocol, document, review)


def fulltext_positions(protocol):
    targets = report_targets(protocol)['report_targets']
    protocol['report_reviews'] = [dict(review_id='independent-' + row['report_id'],
        report_id=row['report_id'], reviewer='Fictional source reviewer', reviewed_at='2026-11-04',
        decision='unclear', rationale='Fictional supplied position only.',
        reviewed_locator='Fictional source section', source_basis_sha256=row['source_basis_sha256'])
        for row in targets if row['retrieval'] == 'retrieved']


def completed_document_work(protocol):
    own = copy.deepcopy(protocol['gaps'][1])
    own.update(work_package_id='CONTEXT-OWN',
        source_refs=[dict(kind='record', record_id='record-one')],
        document_source_ids=['source-main'], depends_on=[])
    direct = copy.deepcopy(own)
    direct.update(work_package_id='CONTEXT-DIRECT', depends_on=['CONTEXT-OWN'])
    direct.pop('document_source_ids')
    indirect = copy.deepcopy(direct)
    indirect.update(work_package_id='CONTEXT-INDIRECT', depends_on=['CONTEXT-DIRECT'])
    protocol['gaps'] = [own, direct, indirect]
    for work in protocol['gaps']:
        work.update(status='COMPLETE', acceptance_verified=True,
            artifact_locator='fictional://completed/' + work['work_package_id'])
    hashes = {row['work_package_id']: row['current_basis_sha256']
              for row in run(protocol)['planning']['completion_ledger']}
    for work in protocol['gaps']:
        work['completion_basis_sha256'] = hashes[work['work_package_id']]


class ReportSourceIntakeContextTests(unittest.TestCase):
    def test_unselected_new_descriptor_stales_fulltext_only_for_its_report(self):
        protocol = fixture()
        fulltext_positions(protocol)
        original = copy.deepcopy(protocol)
        application = append(protocol)
        candidate = application['protocol_candidate']
        states = {row['review']['report_id']: row['source_match_status']
                  for row in run(candidate)['report_review']['review_ledger']}
        self.assertEqual(states, {'report-one': 'STALE_SOURCE', 'report-two': 'CURRENT_SOURCE'})
        self.assertEqual(candidate['report_reviews'], protocol['report_reviews'])
        self.assertEqual(candidate['reports'], protocol['reports'])
        self.assertEqual(candidate['evidence'], protocol['evidence'])
        self.assertEqual(candidate['report_sources'][:-1], protocol['report_sources'])
        self.assertEqual(application['receipt']['before_flow'], application['receipt']['after_flow'])
        self.assertEqual(application['receipt']['before_report_flow'], application['receipt']['after_report_flow'])
        self.assertEqual(protocol, original)

    def test_report_study_positions_bind_whole_catalog_not_only_reviewed_ids(self):
        protocol = fixture()
        targets = {(row['report_id'], row['study_id']): row
                   for row in study_targets(protocol)['membership_targets']}
        protocol['report_study_reviews'] = [dict(review_id='study-' + rid,
            report_id=rid, study_id='study-A', reviewer='Fictional reviewer',
            reviewed_at='2026-11-04', decision='include', rationale='Fictional position.',
            reviewed_locator='Fictional section', reviewed_source_ids=[source_id],
            source_basis_sha256=targets[rid, 'study-A']['source_basis_sha256'])
            for rid, source_id in [('report-one', 'source-main'), ('report-two', 'source-uninspected')]]
        candidate = append(protocol)['protocol_candidate']
        states = {row['review']['report_id']: row['source_match_status']
                  for row in run(candidate)['report_study_review']['review_ledger']}
        self.assertEqual(states, {'report-one': 'STALE_SOURCE', 'report-two': 'CURRENT_SOURCE'})
        self.assertEqual(candidate['report_study_reviews'], protocol['report_study_reviews'])
        self.assertEqual(candidate['reports'], protocol['reports'])

    def test_inventory_and_candidate_positions_stale_without_promotion(self):
        protocol = fixture('report-study-inventory.json')
        target = next(row for row in inventory_review_targets(protocol)['candidate_targets']
                      if (row['report_id'], row['study_id']) == ('report-three', 'candidate-X'))
        protocol['report_study_inventory_reviews'] = [dict(review_id='fictional-candidate-position',
            report_id='report-three', study_id='candidate-X', reviewer='Fictional reviewer',
            reviewed_at='2026-11-04', decision='include', rationale='Fictional position only.',
            reviewed_locator='Fictional section', reviewed_inventory_ids=['inventory-pending-A'],
            reviewed_source_ids=['source-candidate'], source_basis_sha256=target['source_basis_sha256'])]
        before = run(protocol)
        candidate = append(protocol, declarations('report-three'))['protocol_candidate']
        after = run(candidate)
        self.assertEqual(before['report_study_inventory_review']['review_ledger'][0]['source_match_status'],
                         'CURRENT_SOURCE')
        self.assertEqual(after['report_study_inventory_review']['review_ledger'][0]['source_match_status'],
                         'STALE_SOURCE')
        old = {row['inventory']['inventory_id']: row['source_match_status']
               for row in before['report_study_inventory']['inventory_ledger']}
        new = {row['inventory']['inventory_id']: row['source_match_status']
               for row in after['report_study_inventory']['inventory_ledger']}
        self.assertEqual(old['inventory-pending-A'], 'CURRENT_SOURCE')
        self.assertEqual(new['inventory-pending-A'], 'STALE_SOURCE')
        self.assertEqual(new['inventory-pending-B'], 'STALE_SOURCE')
        self.assertEqual(new['inventory-excluded'], old['inventory-excluded'])
        for key in ('report_study_inventory', 'report_study_inventory_reviews', 'reports', 'evidence'):
            self.assertEqual(candidate[key], protocol[key])

    def test_document_work_and_direct_dependents_stale_but_indirect_does_not(self):
        protocol = fixture()
        completed_document_work(protocol)
        old_work = copy.deepcopy(protocol['gaps'])
        candidate = append(protocol)['protocol_candidate']
        after = run(candidate)
        states = {row['work_package_id']: row['source_match_status']
                  for row in after['planning']['completion_ledger']}
        self.assertEqual(states, {'CONTEXT-OWN': 'STALE_SOURCE', 'CONTEXT-DIRECT': 'STALE_SOURCE',
                                  'CONTEXT-INDIRECT': 'CURRENT_SOURCE'})
        self.assertEqual(candidate['gaps'], old_work)
        self.assertTrue(all(row['status'] == 'COMPLETE' for row in after['work_packages']))

    def test_other_report_append_does_not_change_document_work_hashes(self):
        protocol = fixture()
        completed_document_work(protocol)
        before = run(protocol)
        candidate = append(protocol, declarations('report-two'))['protocol_candidate']
        after = run(candidate)
        self.assertEqual(before['planning'], after['planning'])
        self.assertEqual(before['work_packages'], after['work_packages'])

    def test_work_without_document_opt_in_is_not_automatically_rebound(self):
        protocol = fixture()
        before = run(protocol)
        candidate = append(protocol)['protocol_candidate']
        after = run(candidate)
        self.assertEqual(before['planning'], after['planning'])
        self.assertEqual(before['work_packages'], after['work_packages'])

    def test_new_digest_does_not_fill_or_replace_retained_null_descriptor(self):
        protocol = fixture()
        candidate = append(protocol)['protocol_candidate']
        target = next(row for row in report_targets(candidate)['report_targets']
                      if row['report_id'] == 'report-one')
        self.assertEqual(target['source_binding_state'], 'DOCUMENT_BYTES_UNBOUND')
        self.assertIsNone(candidate['report_sources'][1]['document_sha256'])
        self.assertEqual(report_source_check.template(candidate, 'source-unbound')['manifest']['sources'], [])
        draft = report_source_check.template(candidate, 'independent-new-source')
        self.assertEqual(len(draft['manifest']['sources']), 1)
        self.assertIsNone(draft['manifest']['sources'][0]['path'])
        self.assertIsNone(draft['manifest']['sources'][0]['bytes'])
        self.assertEqual(draft['document_bytes_verification'], 'NOT_PERFORMED')

    def test_explicit_local_byte_observation_is_separate_and_never_renews_reviews(self):
        if not report_source_check.secure_open_supported():
            self.skipTest('secure descriptor-relative byte checks unsupported')
        protocol = fixture()
        fulltext_positions(protocol)
        body = b'Fictional bytes for a separate, explicit local observation.\n'
        document = declarations(digest=hashlib.sha256(body).hexdigest())
        with patch('urllib.request.urlopen', side_effect=AssertionError('no network')):
            application = append(protocol, document)
        candidate = application['protocol_candidate']
        original = canonical_json_bytes(candidate)
        manifest = report_source_check.template(candidate, 'independent-new-source')['manifest']
        manifest['sources'][0].update(path='fictional.txt', bytes=len(body))
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'fictional.txt').write_bytes(body)
            observation = report_source_check.check_sources(candidate, manifest, Path(directory))
        self.assertTrue(observation['all_requested_bytes_match'])
        self.assertEqual(observation['sources'][0]['status'], 'BYTES_MATCH')
        self.assertEqual(application['receipt']['document_bytes_verification'], 'NOT_PERFORMED')
        self.assertEqual(application['receipt']['source_authenticity'], 'NOT_VERIFIED')
        self.assertEqual(canonical_json_bytes(candidate), original)
        self.assertEqual(run(candidate)['report_review']['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
        self.assertTrue(intake.verify(protocol, application)['valid'])

    def test_identical_bytes_and_locator_keep_distinct_descriptors_and_order(self):
        protocol = fixture()
        document = declarations()
        second = copy.deepcopy(document['candidates'][0])
        second['source']['source_id'] = 'independent-second-source'
        document['candidates'].append(second)
        first = append(protocol, document)
        reversed_document = copy.deepcopy(document)
        reversed_document['candidates'].reverse()
        second_application = append(protocol, reversed_document)
        self.assertEqual(first['protocol_candidate']['report_sources'][-2:],
                         [row['source'] for row in document['candidates']])
        self.assertNotEqual(first['receipt']['target']['candidate_report_targets'][0]['source_basis_sha256'],
                            second_application['receipt']['target']['candidate_report_targets'][0]['source_basis_sha256'])
        with self.assertRaises(ValueError):
            intake.assemble(protocol, reversed_document, first['receipt']['assertion'])

    def test_all_retrieved_eligibility_states_preserve_counts_and_memberships(self):
        protocol = fixture('report-study-inventory.json')
        document = dict(schema_version=1, candidates=[])
        for rid in ('report-one', 'report-two', 'report-three'):
            document['candidates'].extend(declarations(rid, 'independent-' + rid)['candidates'])
        application = append(protocol, document)
        candidate = application['protocol_candidate']
        self.assertEqual(candidate['reports'], protocol['reports'])
        self.assertEqual(candidate['evidence'], protocol['evidence'])
        self.assertEqual(application['receipt']['before_report_flow'], application['receipt']['after_report_flow'])
        for rid in ('report-four', 'report-five'):
            with self.subTest(report=rid), self.assertRaises(ValueError):
                intake.prepare(protocol, declarations(rid))

    def test_new_id_cannot_cross_an_existing_stale_other_report_reference(self):
        protocol = fixture('report-study-inventory.json')
        original = copy.deepcopy(protocol)
        # The old unavailable inventory names a currently missing source-archived.
        # Adding that ID on another report must not silently reinterpret its reference.
        with self.assertRaisesRegex(ValueError, 'another report'):
            intake.prepare(protocol, declarations('report-one', 'source-archived'))
        self.assertEqual(protocol, original)

    def test_csv_import_ledger_and_derived_record_provenance_remain_exact(self):
        base = fixture('bibliographic-base.json')
        artifact = bibliographic_intake.prepare(base,
            (ROOT / 'examples' / 'bibliographic-export.csv').read_bytes(),
            'local-primary', '2026-11-04T00:00:00Z')
        review = bibliographic_review.prepare_review(base, artifact,
            fixture('bibliographic-resolutions.json'))['review_document']
        review['review'].update(reviewer='Fictional reviewer', reviewed_at='2026-11-04',
            rationale='Fictional import only.', decision='import_for_screening')
        protocol = bibliographic_review.assemble(base, artifact, review)['protocol_candidate']
        rid = protocol['searches'][0]['record_ids'][0]
        protocol['screening'] = [dict(record_id=rid, decision='include', reason='Fictional inclusion.')]
        protocol['reports'] = [dict(report_id='report-one', record_ids=[rid], retrieval='retrieved',
            decision='pending', locator='fictional://imported-report')]
        before = run(protocol)
        application = append(protocol)
        candidate = application['protocol_candidate']
        after = run(candidate)
        self.assertEqual(candidate['bibliographic_imports'], protocol['bibliographic_imports'])
        self.assertEqual(after['bibliographic_collection'], before['bibliographic_collection'])
        self.assertEqual(after['search_ledger'], before['search_ledger'])
        selected = application['receipt']['target']['selected_record_targets']
        self.assertEqual(selected, [row for row in
            report_targets(protocol, before['bibliographic_collection'])['record_targets']
            if row['record_id'] == rid])
        self.assertTrue(intake.verify(protocol, application)['valid'])

    def test_result_drift_distinguishes_whole_catalog_from_selected_descriptor(self):
        protocol = fixture()
        result = copy.deepcopy(protocol['evidence'][0])
        result.update(evidence_id='independent-added-result', study_id='study-C',
                      result='Fictional software assertion, not a measurement.')
        document = dict(schema_version=1, candidates=[dict(report_id='report-one', evidence=result,
            source_references=[dict(source_id='source-main', extraction_locator='Fictional section')],
            extracted_by='Fictional extractor', extracted_at='2026-11-04',
            extraction_note='Fictional detached extraction assertion.')])
        review = result_intake.prepare(protocol, document)['review_document']
        review.update(receipt_id='independent-result-receipt', decision='import_results',
            reviewer='Fictional reviewer', reviewed_at='2026-11-04', rationale='Fictional review.')
        result_application = result_intake.assemble(protocol, document, review)
        candidate = append(result_application['protocol_candidate'])['protocol_candidate']
        compared = result_source_review.review(protocol, result_application, candidate)
        row = compared['rows'][0]
        self.assertEqual(row['result']['status'], 'UNCHANGED')
        self.assertEqual(row['source_context_status'], 'CHANGED')
        self.assertEqual(row['selected_sources'][0]['status'], 'UNCHANGED')
        self.assertEqual(compared['report_comparisons'][0]['recorded_report']['status'], 'UNCHANGED')
        self.assertEqual(compared['renewed_human_review'], 'NOT_PERFORMED')


if __name__ == '__main__':
    unittest.main()
