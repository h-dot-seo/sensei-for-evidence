"""Synthetic extraction history tests, not scientific or source-content validation."""
import copy
import io
import json
from pathlib import Path
import unittest
import zipfile

import bibliographic_intake
import bibliographic_review
import condition_intake
import extraction_transition_bundle as bundle
import result_correction
import result_intake
import result_source_review
from evidence_workflow import run
from json_io import canonical_json_bytes
from test_condition_intake import candidates as condition_candidates

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT / 'examples' / name).read_bytes())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def assemble(module, protocol, document, receipt_id, decision):
    review = module.prepare(protocol, document)['review_document']
    review.update(receipt_id=receipt_id, decision=decision,
                  reviewer='Fictional context reviewer', reviewed_at='2026-11-04',
                  rationale='Synthetic bookkeeping assertion; no scientific acceptance.')
    return module.assemble(protocol, document, review)


def extraction_chain(initial=None):
    initial = fixture('report-study-inventory-reviews.json') if initial is None else initial
    candidates = fixture('manual-result-candidates.json')
    candidates['candidates'][0]['evidence']['result'] = '  Fictional prior text β\nkept literally.  '
    candidates['candidates'][0]['source_references'] = [
        dict(source_id='source-supplement', extraction_locator='  Fictional prior supplement\nlocation  '),
        dict(source_id='source-main', extraction_locator='Fictional prior main location')]
    imported = assemble(result_intake, initial, candidates, 'context-import', 'import_results')
    conditions = condition_candidates(('result-C-manual',), 'context-condition')
    conditions['candidates'][0]['source_references'] = [
        dict(source_id='source-main', extraction_locator='  Fictional condition location β  ')]
    conditioned = assemble(condition_intake, imported['protocol_candidate'], conditions,
                           'context-condition', 'import_conditions')
    corrections = dict(schema_version=1, corrections=[dict(
        evidence_id='result-C-manual', report_id='report-one',
        changes={'result': '  Fictional corrected text β\nkept literally.  '},
        source_references=[dict(source_id='source-supplement',
                                extraction_locator='Fictional correction location, not the old extraction')],
        corrected_by='Fictional corrector', corrected_at='2026-11-04',
        correction_note='Synthetic textual correction only; no reassessment.')])
    corrected = assemble(result_correction, conditioned['protocol_candidate'], corrections,
                         'context-correction', 'correct_result_text')
    return initial, [imported, conditioned, corrected], corrected['protocol_candidate']


def unpack(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def archived_chain(initial, applications, endpoint):
    raw = bundle.build_bundle(encoded(initial), [encoded(a) for a in applications], encoded(endpoint))
    entries = unpack(raw)
    restored = [json.loads(entries['applications/step-%06d.json' % i])
                for i in range(len(applications))]
    return raw, entries, json.loads(entries['protocols/initial.json']), restored, json.loads(entries['protocols/endpoint.json'])


def evidence(protocol, evidence_id):
    return next(row for row in protocol['evidence'] if row['evidence_id'] == evidence_id)


class ExtractionTransitionContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial, cls.applications, cls.endpoint = extraction_chain()
        (cls.raw, cls.entries, cls.archived_initial, cls.archived_applications,
         cls.archived_endpoint) = archived_chain(cls.initial, cls.applications, cls.endpoint)

    def test_historical_exact_source_selection_order_and_locations_survive(self):
        self.assertTrue(bundle.verify_bundle(self.raw)['valid'])
        selected_ids = []
        for index, (original, retained) in enumerate(zip(self.applications, self.archived_applications)):
            self.assertEqual(self.entries['applications/step-%06d.json' % index], encoded(original))
            selected = retained['receipt']['target']['selected_sources']
            self.assertEqual(selected, original['receipt']['target']['selected_sources'])
            selected_ids.append([row['source']['source_id'] for row in selected])
            for row in selected:
                pointer = int(row['input_pointer'].split('/')[-1])
                self.assertEqual(row['source'], self.archived_initial['report_sources'][pointer])
            self.assertEqual(retained['receipt']['assertion'], original['receipt']['assertion'])
            self.assertEqual(retained['receipt']['source_association_scope'], 'DETACHED_RECORD_ONLY')
        self.assertEqual(selected_ids, [
            ['source-supplement', 'source-main', 'source-main', 'source-supplement'],
            ['source-main'], ['source-supplement']])
        historical = self.archived_applications[0]['receipt']['target']['selected_sources'][0]
        current = self.archived_applications[2]['receipt']['target']['selected_sources'][0]
        self.assertEqual(historical['extraction_locator'], '  Fictional prior supplement\nlocation  ')
        self.assertNotEqual(historical['extraction_locator'], current['extraction_locator'])
        for row in self.archived_endpoint['evidence']:
            self.assertNotIn('source_references', row)
        for row in self.archived_endpoint['experimental_units']:
            self.assertNotIn('source_references', row)

    def test_prior_result_text_and_correction_delta_are_not_replaced_by_endpoint(self):
        imported, conditioned, corrected = self.archived_applications
        old = imported['receipt']['candidate_document']['candidates'][0]['evidence']
        change = corrected['receipt']['target']['result_changes'][0]
        final = evidence(self.archived_endpoint, 'result-C-manual')
        self.assertEqual(old['result'], '  Fictional prior text β\nkept literally.  ')
        self.assertEqual(evidence(imported['protocol_candidate'], 'result-C-manual'), old)
        self.assertEqual(evidence(conditioned['protocol_candidate'], 'result-C-manual'), old)
        self.assertEqual(change['before'], old)
        self.assertEqual(change['after'], final)
        self.assertEqual(change['changed_fields'], ['result'])
        self.assertNotEqual(change['before']['result'], final['result'])
        self.assertEqual(final['result'], '  Fictional corrected text β\nkept literally.  ')
        self.assertEqual({k: v for k, v in old.items() if k != 'result'},
                         {k: v for k, v in final.items() if k != 'result'})

    def test_condition_before_correction_retains_its_own_evidence_snapshot(self):
        imported, conditioned, corrected = self.archived_applications
        selected = conditioned['receipt']['target']['selected_evidence']
        self.assertEqual(len(selected), 1)
        snapshot = selected[0]
        self.assertEqual(snapshot['input_pointer'], '/evidence/2')
        self.assertEqual(snapshot['evidence'], evidence(imported['protocol_candidate'], 'result-C-manual'))
        self.assertNotEqual(snapshot['evidence'], evidence(self.archived_endpoint, 'result-C-manual'))
        self.assertEqual(conditioned['protocol_candidate']['experimental_units'],
                         self.archived_endpoint['experimental_units'])
        self.assertEqual(conditioned['receipt']['candidate_document']['candidates'][0]['experimental_unit'],
                         self.archived_endpoint['experimental_units'][-1])
        self.assertTrue(condition_intake.verify(imported['protocol_candidate'], conditioned)['valid'])
        self.assertTrue(result_correction.verify(conditioned['protocol_candidate'], corrected)['valid'])
        # Same condition object is not permission to transplant its original review to a later input.
        with self.assertRaises(ValueError):
            condition_intake.verify(self.archived_endpoint, conditioned)
        self.assertEqual(json.loads(self.entries['chain.json'])['source_association_scope'],
                         'RECORDED_STEP_CONTEXT_ONLY')

    def test_retained_intake_remains_replayable_and_reports_changed_endpoint_text(self):
        imported = self.archived_applications[0]
        before = canonical_json_bytes((self.archived_initial, imported, self.archived_endpoint))
        earlier = result_source_review.review(self.archived_initial, imported, imported['protocol_candidate'])
        later = result_source_review.review(self.archived_initial, imported, self.archived_endpoint)
        self.assertEqual([row['result']['status'] for row in earlier['rows']], ['UNCHANGED', 'UNCHANGED'])
        self.assertEqual([row['result']['status'] for row in later['rows']], ['CHANGED', 'UNCHANGED'])
        self.assertEqual(later['rows'][0]['result']['changed_fields'], ['result'])
        self.assertEqual(later['rows'][0]['source_context_status'], 'UNCHANGED')
        self.assertTrue(later['original_replay_result']['valid'])
        self.assertEqual(later['renewed_human_review'], 'NOT_PERFORMED')
        self.assertEqual(later['source_result_correctness'], 'NOT_ASSESSED')
        self.assertEqual(later['lineage'], 'NOT_ESTABLISHED')
        self.assertEqual(later['rows'][0]['historical_extraction'], earlier['rows'][0]['historical_extraction'])
        self.assertEqual(canonical_json_bytes((self.archived_initial, imported, self.archived_endpoint)), before)
        self.assertTrue(bundle.verify_bundle(self.raw)['valid'])

    def test_later_source_drift_does_not_rewrite_archived_source_currentness(self):
        imported = self.archived_applications[0]
        later = copy.deepcopy(self.archived_endpoint)
        later['report_sources'][1]['document_version'] = 'Fictional later declaration outside the archived segment'
        compared = result_source_review.review(self.archived_initial, imported, later)
        row = compared['rows'][0]
        self.assertEqual([s['status'] for s in row['selected_sources']], ['CHANGED', 'UNCHANGED'])
        self.assertEqual(row['selected_sources'][0]['changed_fields'], ['document_version'])
        self.assertEqual(row['selected_sources'][0]['before'], self.archived_initial['report_sources'][1])
        self.assertEqual(row['selected_sources'][0]['after'], later['report_sources'][1])
        self.assertEqual(row['source_context_status'], 'CHANGED')
        self.assertEqual(compared['renewed_human_review'], 'NOT_PERFORMED')
        self.assertEqual(self.archived_endpoint['report_sources'], self.archived_initial['report_sources'])
        self.assertTrue(bundle.verify_bundle(self.raw)['valid'])
        with self.assertRaises(ValueError):
            bundle.build_bundle(encoded(self.archived_initial), [encoded(a) for a in self.archived_applications], encoded(later))

    def test_retained_review_assertions_and_stale_positions_are_never_renewed(self):
        before, after = run(self.archived_initial), run(self.archived_endpoint)
        for field in ('report_reviews', 'report_study_inventory', 'report_study_inventory_reviews', 'gaps'):
            self.assertEqual(canonical_json_bytes(self.archived_endpoint[field]),
                             canonical_json_bytes(self.archived_initial[field]))
        for section in ('report_review', 'report_study_inventory_review'):
            self.assertEqual(after[section]['review_ledger'], before[section]['review_ledger'])
        statuses = [r['source_match_status'] for r in after['report_review']['review_ledger']]
        self.assertIn('CURRENT_SOURCE', statuses)
        self.assertIn('STALE_SOURCE', statuses)
        verified = bundle.verify_bundle(self.raw)
        for result in (verified, json.loads(self.entries['chain.json']), json.loads(self.entries['manifest.json'])):
            self.assertEqual(result['review_renewal'], 'NOT_PERFORMED')
            self.assertEqual(result['downstream_reassessment'], 'NOT_PERFORMED')
            self.assertEqual(result['scientific_acceptance'], 'NOT_ASSESSED')
            self.assertEqual(result['conclusion_readiness'], 'NOT_READY')
        self.assertEqual(self.archived_applications[-1]['receipt']['existing_review_renewal'], 'NOT_PERFORMED')

    def test_correction_preserves_assertions_while_completion_becomes_stale(self):
        initial = fixture('completion-binding.json')
        report = initial['reports'][0]
        initial['report_sources'] = [dict(source_id='source-supplement', report_id=report['report_id'],
            source_locator='synthetic:context-only', document_version='Fictional declared version', document_sha256=None)]
        corrections = dict(schema_version=1, corrections=[dict(
            evidence_id=initial['evidence'][0]['evidence_id'], report_id=report['report_id'],
            changes={'result': 'Fictional corrected bookkeeping text; not an observation.'},
            source_references=[dict(source_id='source-supplement', extraction_locator='Fictional text location')],
            corrected_by='Fictional corrector', corrected_at='2026-11-04',
            correction_note='Synthetic correction, not downstream review.')])
        application = assemble(result_correction, initial, corrections, 'context-completion-correction', 'correct_result_text')
        raw, _, restored_initial, _, endpoint = archived_chain(initial, [application], application['protocol_candidate'])
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        before, after = run(restored_initial), run(endpoint)
        old = next(r for r in before['planning']['completion_ledger'] if r['work_package_id'] == 'WP-MECHANISM')
        new = next(r for r in after['planning']['completion_ledger'] if r['work_package_id'] == 'WP-MECHANISM')
        self.assertEqual(old['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(new['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(endpoint['gaps'][0]['status'], 'COMPLETE')
        for field in ('gaps', 'appraisals', 'contexts'):
            self.assertEqual(endpoint[field], restored_initial[field])
        self.assertEqual(after['appraisal'], before['appraisal'])
        self.assertEqual(after['conclusion_readiness'], 'NOT_READY')

    def test_preexisting_bibliographic_ledger_survives_all_extraction_steps(self):
        initial = fixture('bibliographic-base.json')
        artifact = bibliographic_intake.prepare(initial,
            b'record_id,source_locator\nfictional-input,synthetic:retained-export\n',
            'local-primary', '2026-11-04T00:00:00Z')
        choices = bibliographic_review.template(artifact)
        choices['resolutions'][0].update(disposition='new_record', record_id='record-one',
                                         rationale='Fictional identity assertion')
        review = bibliographic_review.prepare_review(initial, artifact, choices)['review_document']
        review['review'].update(reviewer='Fictional reviewer', reviewed_at='2026-11-04',
                                rationale='Synthetic collection only', decision='import_for_screening')
        initial = bibliographic_review.assemble(initial, artifact, review)['protocol_candidate']
        initial['screening'] = [dict(record_id='record-one', decision='include', reason='Fictional screening')]
        initial['reports'] = [dict(report_id='report-one', record_ids=['record-one'], retrieval='retrieved',
                                   decision='include', study_ids=['study-A', 'study-C'], locator='synthetic:report')]
        initial['report_sources'] = copy.deepcopy(self.initial['report_sources'][:2])
        initial, applications, endpoint = extraction_chain(initial)
        raw, _, restored_initial, restored_applications, restored_endpoint = archived_chain(initial, applications, endpoint)
        self.assertTrue(bundle.verify_bundle(raw)['valid'])
        ledger = canonical_json_bytes(initial['bibliographic_imports'])
        for protocol in [restored_initial, restored_endpoint] + [a['protocol_candidate'] for a in restored_applications]:
            self.assertEqual(canonical_json_bytes(protocol['bibliographic_imports']), ledger)
            self.assertEqual(protocol['searches'], initial['searches'])
            self.assertIn('bibliographic_collection', run(protocol))
        for application in restored_applications:
            targets = application['receipt']['target']['selected_record_targets']
            self.assertTrue(targets)
            self.assertTrue(targets[0]['source_basis']['bibliographic_rows'])
        # Existing ledger integrity remains authoritative; the wrapper cannot bless changed history.
        changed = copy.deepcopy(initial)
        changed['question'] += ' Fictional unauthorized change to the recorded base.'
        with self.assertRaises(ValueError):
            bundle.build_bundle(encoded(changed), [encoded(a) for a in applications], encoded(endpoint))


if __name__ == '__main__':
    unittest.main()
