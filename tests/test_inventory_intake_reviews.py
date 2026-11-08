"""Synthetic inventory-intake regressions for retained review and source context."""
import copy
import json
from pathlib import Path
import unittest

import bibliographic_intake
import bibliographic_review
import inventory_intake as intake
from evidence_workflow import run
from json_io import canonical_json_bytes
from prisma_reports import report_flow
from report_study_inventory_links import prepare_candidate_target
from report_study_inventory_review_links import prepare_targets as prepare_review_targets

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = 'report_study_inventory'
REVIEWS = 'report_study_inventory_reviews'
REVIEW_VIEW = 'report_study_inventory_review'


def protocol():
    """Use only the explicitly fictional repository fixture."""
    return json.loads((ROOT / 'examples/report-study-inventory.json').read_text(encoding='utf-8'))


def candidate_document(p, report='report-three', study='candidate-X',
                       inventory_id='inventory-explicit-second',
                       recorder='Fictional second intake recorder', sources=None):
    document = intake.template(p, report, study)['candidate_document']
    document['candidates'][0].update(
        inventory_id=inventory_id, recorded_by=recorder, recorded_at='2020-01-01',
        description='Explicit second fictional description; no identity or inclusion claim.',
        source_locator='synthetic://explicit-description/section-2',
        source_ids=['source-candidate'] if sources is None else sources)
    return document


def import_review(p, document):
    review = intake.prepare(p, document)['review_document']
    review.update(receipt_id='synthetic-inventory-import', decision='import_descriptive_inventory',
                  reviewer='Fictional descriptive intake reviewer', reviewed_at='2026-11-04',
                  rationale='Explicitly import only these supplied fictional descriptions.')
    return review


def eligibility_review(p, report, study, inventory_id, source_id, decision='include'):
    collection = run(p).get('bibliographic_collection')
    target = next(row for row in prepare_review_targets(p, collection)['candidate_targets']
                  if (row['report_id'], row['study_id']) == (report, study))
    return dict(review_id='synthetic-existing-candidate-review', report_id=report,
                study_id=study, reviewer='Fictional prior eligibility reviewer',
                reviewed_at='2026-11-04', decision=decision,
                rationale='Explicit fictional eligibility position, not canonical membership.',
                reviewed_locator='synthetic://prior-eligibility/section-1',
                reviewed_inventory_ids=[inventory_id], reviewed_source_ids=[source_id],
                source_basis_sha256=target['source_basis_sha256'])


def imported_protocol():
    """Build a real CSV-ledger import with explicitly supplied synthetic choices."""
    base = json.loads((ROOT / 'examples/bibliographic-base.json').read_text(encoding='utf-8'))
    raw = (b'record_id,source_locator,title\r\n'
           b'fictional-export-A,synthetic:source-A,Fictional first title\r\n'
           b'fictional-export-A,synthetic:alternate-A,Fictional alternate title\r\n'
           b'fictional-withheld,synthetic:withheld,Fictional withheld title\r\n')
    artifact = bibliographic_intake.prepare(base, raw, 'local-primary', '2026-11-04T00:00:00Z')
    choices = bibliographic_review.template(artifact)
    for row, disposition, record_id in zip(
            choices['resolutions'], ['new_record', 'same_record', 'do_not_promote'],
            ['fictional-canonical-record', 'fictional-canonical-record', None]):
        row.update(disposition=disposition, record_id=record_id,
                   rationale='Explicit fictional collection mapping for this regression.')
    review = bibliographic_review.prepare_review(base, artifact, choices)['review_document']
    review['review'].update(reviewer='Fictional collection reviewer', reviewed_at='2026-11-04',
                            decision='import_for_screening',
                            rationale='Explicit synthetic collection approval only.')
    p = bibliographic_review.assemble(base, artifact, review)['protocol_candidate']
    p['screening'] = [dict(record_id='fictional-canonical-record', decision='include',
                           reason='Explicit fictional screening position.')]
    p['reports'] = [dict(report_id='report-imported', record_ids=['fictional-canonical-record'],
                         retrieval='retrieved', decision='pending', locator='synthetic://imported-report')]
    p['report_sources'] = [dict(source_id='source-imported', report_id='report-imported',
                                source_locator='synthetic://imported-main',
                                document_version='Fictional supplied main version 1',
                                document_sha256='a' * 64)]
    return p


class InventoryIntakeReviewTests(unittest.TestCase):
    def assert_only_appended(self, before, after, rows):
        self.assertEqual(after[INVENTORY], before.get(INVENTORY, []) + rows)
        restored = copy.deepcopy(after)
        if INVENTORY in before:
            restored[INVENTORY] = restored[INVENTORY][:-len(rows)]
        else:
            del restored[INVENTORY]
        self.assertEqual(canonical_json_bytes(restored), canonical_json_bytes(before))

    def test_second_recorder_stales_prior_candidate_review_without_selecting_or_renewing(self):
        cases = [('report-three', 'candidate-X', 'inventory-pending-A', 'source-candidate'),
                 ('report-one', 'study-A', 'inventory-included', 'source-main')]
        for report, study, inventory_id, source_id in cases:
            for decision in ('include', 'exclude', 'unclear'):
                with self.subTest(report=report, decision=decision):
                    p = protocol()
                    p[INVENTORY] = [row for row in p[INVENTORY]
                                    if row['inventory_id'] != 'inventory-pending-B']
                    p[REVIEWS] = [eligibility_review(p, report, study, inventory_id, source_id, decision)]
                    original = copy.deepcopy(p)
                    before = run(p)
                    before_reports = report_flow(p)
                    self.assertEqual(before[REVIEW_VIEW]['review_ledger'][0]['source_match_status'],
                                     'CURRENT_SOURCE')
                    document = candidate_document(p, report, study, sources=[source_id])
                    application = intake.assemble(p, document, import_review(p, document))
                    candidate = application['protocol_candidate']
                    after = run(candidate)
                    prior_review = after[REVIEW_VIEW]['review_ledger'][0]
                    self.assertEqual(prior_review['source_match_status'], 'STALE_SOURCE')
                    self.assertEqual(prior_review['review'], original[REVIEWS][0])
                    self.assertNotEqual(prior_review['current_source_basis_sha256'],
                                        prior_review['review']['source_basis_sha256'])
                    pair = next(row for row in after[REVIEW_VIEW]['candidate_review_ledger']
                                if (row['report_id'], row['study_id']) == (report, study))
                    self.assertEqual(pair['current_review_ids'], [])
                    self.assertEqual(pair['stale_review_ids'], ['synthetic-existing-candidate-review'])
                    self.assertEqual(pair['current_decisions'], [])
                    self.assertEqual(pair['stale_decisions'], [decision])
                    self.assertIn('NO_CURRENT_SOURCE_REVIEW', pair['comparison_cues'])
                    self.assertIn('STALE_REVIEW_ASSERTIONS', pair['comparison_cues'])
                    self.assert_only_appended(original, candidate, document['candidates'])
                    self.assertEqual(p, original)
                    for field in ('flow', 'evidence', 'work_packages', 'report_study_coverage'):
                        self.assertEqual(after[field], before[field], field)
                    after_reports = report_flow(candidate)
                    for field in ('record_flow', 'report_flow', 'report_csv', 'report_study_coverage'):
                        self.assertEqual(after_reports[field], before_reports[field], field)
                    inventory_pair = next(row for row in after[INVENTORY]['pair_inventory_ledger']
                                          if (row['report_id'], row['study_id']) == (report, study))
                    self.assertEqual(inventory_pair['current_inventory_ids'],
                                     [inventory_id, 'inventory-explicit-second'])
                    self.assertIn('DIFFERING_CURRENT_DESCRIPTIONS', inventory_pair['comparison_cues'])
                    self.assertEqual(inventory_pair['membership_currently_declared'], report == 'report-one')
                    self.assertEqual(inventory_pair['has_result_rows'], report == 'report-one')
                    self.assertEqual(application['receipt']['existing_review_renewal'], 'NOT_PERFORMED')
                    self.assertTrue(intake.verify(original, application)['valid'])

    def test_other_candidate_description_does_not_stale_same_report_existing_pair_review(self):
        p = protocol()
        p[REVIEWS] = [eligibility_review(p, 'report-three', 'candidate-X',
                                         'inventory-pending-A', 'source-candidate')]
        document = candidate_document(p, study='explicit-other-candidate')
        application = intake.assemble(p, document, import_review(p, document))
        after = run(application['protocol_candidate'])
        self.assertEqual(after[REVIEW_VIEW]['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(after[REVIEW_VIEW]['review_ledger'][0]['review'], p[REVIEWS][0])
        self.assertEqual(after[REVIEW_VIEW]['counts']['current_source_reviews'], 1)
        self.assert_only_appended(p, application['protocol_candidate'], document['candidates'])
        self.assertTrue(intake.verify(p, application)['valid'])

    def test_existing_stale_inventory_and_orphan_review_history_are_preserved(self):
        p = protocol()
        p[REVIEWS] = [dict(
            review_id='synthetic-retained-orphan', report_id='report-five', study_id='retired-candidate',
            reviewer='Fictional historical reviewer', reviewed_at='2020-01-01', decision='exclude',
            rationale='Fictional retained history with unresolved old references.',
            reviewed_locator='synthetic://retired-context',
            reviewed_inventory_ids=['historical-inventory-removed'],
            reviewed_source_ids=['historical-source-removed'], source_basis_sha256='0' * 64)]
        before = copy.deepcopy(p)
        view_before = run(p)
        self.assertGreater(view_before[INVENTORY]['counts']['stale_source_assertions'], 0)
        document = candidate_document(p, study='fresh-candidate')
        application = intake.assemble(p, document, import_review(p, document))
        candidate = application['protocol_candidate']
        after = run(candidate)
        self.assert_only_appended(before, candidate, document['candidates'])
        self.assertEqual(after[INVENTORY]['inventory_ledger'][:-1], view_before[INVENTORY]['inventory_ledger'])
        self.assertEqual(after[INVENTORY]['inventory_ledger'][-1]['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(after[REVIEW_VIEW]['orphan_review_assertions'],
                         view_before[REVIEW_VIEW]['orphan_review_assertions'])
        orphan = after[REVIEW_VIEW]['orphan_review_assertions'][0]
        self.assertEqual(orphan['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(orphan['unresolved_reviewed_inventory_ids'], ['historical-inventory-removed'])
        self.assertEqual(orphan['unresolved_reviewed_source_ids'], ['historical-source-removed'])
        self.assertTrue(intake.verify(before, application)['valid'])
        self.assertEqual(p, before)

    def test_new_stale_or_unresolved_assertion_rejected_even_with_old_stale_history(self):
        p = protocol()
        document = candidate_document(p)
        review = import_review(p, document)
        original = copy.deepcopy(p)
        self.assertGreater(run(p)[INVENTORY]['counts']['stale_source_assertions'], 0)
        bads = [dict(document['candidates'][0], source_basis_sha256='0' * 64),
                dict(document['candidates'][0], source_ids=['historical-source-removed'])]
        for row in bads:
            bad = dict(schema_version=1, candidates=[row])
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    intake.prepare(p, bad)
                with self.assertRaises(ValueError):
                    intake.assemble(p, bad, review)
                self.assertEqual(p, original)

    def test_unselected_same_report_source_changes_stale_new_assertions(self):
        p = protocol()
        document = candidate_document(p, 'report-one', 'study-A', sources=['source-main'])
        prepared = intake.prepare(p, document)
        target = prepared['target']
        self.assertEqual([row['source']['source_id'] for row in target['selected_sources']], ['source-main'])
        self.assertEqual([row['source_id'] for row in
                          target['selected_report_targets'][0]['source_basis']['report_sources']],
                         ['source-main', 'source-supplement'])
        edits = [('digest', lambda q: q['report_sources'][1].update(document_sha256='e' * 64)),
                 ('version', lambda q: q['report_sources'][1].update(document_version='Fictional supplement v2')),
                 ('locator', lambda q: q['report_sources'][1].update(source_locator='synthetic://changed-supplement')),
                 ('order', lambda q: q['report_sources'].__setitem__(slice(0, 2), q['report_sources'][1::-1]))]
        for label, edit in edits:
            with self.subTest(edit=label):
                changed = copy.deepcopy(p)
                edit(changed)
                original = copy.deepcopy(changed)
                with self.assertRaisesRegex(ValueError, 'current context'):
                    intake.prepare(changed, document)
                fresh = candidate_document(changed, 'report-one', 'study-A', sources=['source-main'])
                self.assertNotEqual(fresh['candidates'][0]['source_basis_sha256'],
                                    document['candidates'][0]['source_basis_sha256'])
                application = intake.assemble(changed, fresh, import_review(changed, fresh))
                after = run(application['protocol_candidate'])[INVENTORY]
                old = next(row for row in after['inventory_ledger']
                           if row['inventory']['inventory_id'] == 'inventory-included')
                self.assertEqual(old['source_match_status'], 'STALE_SOURCE')
                self.assertEqual(after['inventory_ledger'][-1]['source_match_status'], 'CURRENT_SOURCE')
                self.assert_only_appended(changed, application['protocol_candidate'], fresh['candidates'])
                self.assertEqual(changed, original)
                self.assertTrue(intake.verify(changed, application)['valid'])

    def test_csv_import_enrichment_and_mapped_provenance_survive_review_staleness(self):
        p = imported_protocol()
        first = candidate_document(p, 'report-imported', 'fictional-imported-study',
                                   inventory_id='inventory-first-imported', recorder='Fictional first recorder',
                                   sources=['source-imported'])['candidates'][0]
        p[INVENTORY] = [first]
        p[REVIEWS] = [eligibility_review(p, 'report-imported', 'fictional-imported-study',
                                         'inventory-first-imported', 'source-imported')]
        before = copy.deepcopy(p)
        before_view = run(p)
        collection = before_view['bibliographic_collection']
        document = candidate_document(p, 'report-imported', 'fictional-imported-study',
                                      sources=['source-imported'])
        prepared = intake.prepare(p, document)
        target = prepared['target']
        mapped = target['selected_record_targets'][0]['source_basis']['bibliographic_rows']
        expected_rows = [row for row in collection['row_ledger']
                         if row['resolution']['record_id'] == 'fictional-canonical-record']
        self.assertEqual(mapped, expected_rows)
        self.assertEqual(len(mapped), 2)
        self.assertEqual([row['original_values']['source_locator'] for row in mapped],
                         ['synthetic:source-A', 'synthetic:alternate-A'])
        self.assertTrue(all(row['source_pointer'].startswith('/bibliographic_imports/imports/0/')
                            for row in mapped))
        supplied = prepare_candidate_target(p, 'report-imported', 'fictional-imported-study', collection)
        unenriched = prepare_candidate_target(p, 'report-imported', 'fictional-imported-study')
        self.assertEqual(document['candidates'][0]['source_basis_sha256'], supplied['source_basis_sha256'])
        self.assertNotEqual(supplied['source_basis_sha256'], unenriched['source_basis_sha256'])
        application = intake.assemble(p, document, import_review(p, document))
        candidate = application['protocol_candidate']
        after = run(candidate)
        self.assertEqual(after['bibliographic_collection'], collection)
        self.assertEqual(candidate['bibliographic_imports'], before['bibliographic_imports'])
        self.assertEqual(after[REVIEW_VIEW]['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(after[REVIEW_VIEW]['review_ledger'][0]['review'], before[REVIEWS][0])
        self.assertTrue(all(row['source_match_status'] == 'CURRENT_SOURCE'
                            for row in after[INVENTORY]['inventory_ledger']))
        self.assert_only_appended(before, candidate, document['candidates'])
        self.assertEqual(p, before)
        self.assertTrue(intake.verify(before, application)['valid'])

    def test_recomputed_receipt_cannot_hide_renewed_existing_candidate_review(self):
        p = protocol()
        p[REVIEWS] = [eligibility_review(p, 'report-three', 'candidate-X',
                                         'inventory-pending-A', 'source-candidate')]
        document = candidate_document(p)
        application = intake.assemble(p, document, import_review(p, document))
        tampered = copy.deepcopy(application)
        candidate = tampered['protocol_candidate']
        current = run(candidate)[REVIEW_VIEW]['review_ledger'][0]['current_source_basis_sha256']
        candidate[REVIEWS][0]['source_basis_sha256'] = current
        self.assertEqual(run(candidate)[REVIEW_VIEW]['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        tampered['receipt']['protocol_candidate_sha256'] = intake.digest(candidate)
        tampered['receipt']['receipt_sha256'] = intake.digest(
            {key: value for key, value in tampered['receipt'].items() if key != 'receipt_sha256'})
        with self.assertRaisesRegex(ValueError, 'exact replay'):
            intake.verify(p, tampered)
        self.assertTrue(intake.verify(p, application)['valid'])

    def test_existing_eligibility_edit_invalidates_detached_import_review_without_rebase(self):
        p = protocol()
        p[REVIEWS] = [eligibility_review(p, 'report-three', 'candidate-X',
                                         'inventory-pending-A', 'source-candidate')]
        document = candidate_document(p)
        review = import_review(p, document)
        changed = copy.deepcopy(p)
        changed[REVIEWS][0]['rationale'] += ' Explicitly revised fictional rationale.'
        self.assertEqual(intake.template(changed, 'report-three', 'candidate-X')['proposed_target']['source_basis_sha256'],
                         document['candidates'][0]['source_basis_sha256'])
        with self.assertRaisesRegex(ValueError, 'no automatic rebase'):
            intake.assemble(changed, document, review)
        self.assertNotEqual(intake.prepare(changed, document)['target']['target_sha256'], review['target_sha256'])


if __name__ == '__main__':
    unittest.main()
