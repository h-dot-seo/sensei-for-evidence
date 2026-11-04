"""Independent, entirely fictional candidate-position boundary regression tests."""
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
from report_study_inventory_review_links import prepare_targets, link_report_study_inventory_reviews
from report_study_inventory_review import review, template, render_text

ROOT = Path(__file__).resolve().parent
KEY = 'report_study_inventory_reviews'
VIEW = 'report_study_inventory_review'


def protocol():
    return json.loads((ROOT / 'examples/report-study-inventory.json').read_text(encoding='utf-8'))


def targets(p):
    return {(r['report_id'], r['study_id']): r for r in prepare_targets(p)['candidate_targets']}


def assertion(p, report='report-three', study='candidate-X', reviewer='Fictional reviewer A',
              rid='candidate-review-A', decision='include', inventories=None, sources=None):
    return dict(review_id=rid, report_id=report, study_id=study, reviewer=reviewer,
                reviewed_at='2026-11-04', decision=decision,
                rationale='Fictional candidate position; no scientific assertion.',
                reviewed_locator='Fictional candidate section.',
                reviewed_inventory_ids=['inventory-pending-A'] if inventories is None else inventories,
                reviewed_source_ids=['source-candidate'] if sources is None else sources,
                source_basis_sha256=targets(p)[report, study]['source_basis_sha256'])


class ReportStudyInventoryReviewTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol()

    def ledger(self, p=None):
        return link_report_study_inventory_reviews(self.p if p is None else p)

    def position(self, **kwargs):
        self.p[KEY] = [assertion(self.p, **kwargs)]
        return self.p[KEY][0]

    def cli(self, path, *args):
        return subprocess.run([sys.executable, str(ROOT / 'report_study_inventory_review.py'),
                               str(path), *args], cwd=ROOT, capture_output=True,
                              env=dict(os.environ, PYTHONIOENCODING='utf-8'))

    def test_optional_absent_empty_and_invalid_container(self):
        self.assertNotIn(VIEW, run(self.p))
        self.assertEqual(self.ledger()['stage'], 'NOT_SUPPLIED')
        self.p[KEY] = []
        self.assertEqual(run(self.p)[VIEW]['stage'], 'SUPPLIED')
        for bad in (None, False, {}, '', 0, [None]):
            with self.subTest(bad=bad), self.assertRaises((TypeError, ValueError)):
                run(dict(self.p, **{KEY: bad}))

    def test_exact_schema_and_nonblank_literal_scalars(self):
        a = assertion(self.p)
        cases = [dict(a, unexpected='fictional')]
        for field in a:
            bad = copy.deepcopy(a); bad.pop(field); cases.append(bad)
            if field not in ('reviewed_inventory_ids', 'reviewed_source_ids'):
                cases.extend(dict(a, **{field: v}) for v in ('', ' \t\n', None, True, 4, [], {}))
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises((TypeError, ValueError)):
                self.ledger(dict(self.p, **{KEY: [bad]}))

    def test_real_date_lowercase_hash_and_literal_decisions(self):
        a = assertion(self.p)
        bads = {'reviewed_at': ['2026-2-04', '2026-02-29', '2026-11-04\n', '0000-01-01'],
                'source_basis_sha256': ['A'*64, 'z'*64, '0'*63, '0'*65, '0'*64+'\n'],
                'decision': ['pending', 'Include', ' include'], 'report_id': ['missing', 'report-three ']}
        for field, values in bads.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.ledger(dict(self.p, **{KEY: [dict(a, **{field: value})]}))
        self.ledger(dict(self.p, **{KEY: [dict(a, reviewed_at='2024-02-29')]}))

    def test_both_selections_are_nonempty_unique_literal_lists(self):
        a = assertion(self.p)
        for field in ('reviewed_inventory_ids', 'reviewed_source_ids'):
            existing = a[field][0]
            for value in (None, [], {}, existing, True, [''], [' '], [existing, existing], [None], [{}]):
                with self.subTest(field=field, value=value), self.assertRaises((TypeError, ValueError)):
                    self.ledger(dict(self.p, **{KEY: [dict(a, **{field: value})]}))

    def test_global_ids_and_report_study_reviewer_uniqueness(self):
        a = assertion(self.p)
        for b in (dict(a, reviewer='Other fictional reviewer'), dict(a, review_id='other')):
            with self.subTest(b=b), self.assertRaises(ValueError):
                self.ledger(dict(self.p, **{KEY: [a, b]}))
        b = assertion(self.p, report='report-two', study='candidate-Y', rid='other',
                      inventories=['inventory-excluded'], sources=['source-unbound'])
        self.assertEqual(self.ledger(dict(self.p, **{KEY: [a, b]}))['counts']['review_assertions'], 2)
        b['review_id'] = a['review_id']
        with self.assertRaises(ValueError): self.ledger(dict(self.p, **{KEY: [a, b]}))

    def test_known_crossed_ids_rejected_even_when_stale(self):
        a = assertion(self.p)
        # Same-report wrong candidate is still a crossed inventory reference.
        other = copy.deepcopy(self.p['report_study_inventory'][0])
        other.update(inventory_id='other-candidate', study_id='candidate-other', source_basis_sha256='0'*64)
        self.p['report_study_inventory'].append(other)
        a = assertion(self.p)
        for field, value in [('reviewed_inventory_ids', ['inventory-excluded']),
                             ('reviewed_inventory_ids', ['other-candidate']),
                             ('reviewed_source_ids', ['source-main'])]:
            for digest in (a['source_basis_sha256'], '0'*64):
                with self.subTest(field=field, value=value, digest=digest), self.assertRaises(ValueError):
                    self.ledger(dict(self.p, **{KEY: [dict(a, **{field: value}, source_basis_sha256=digest)]}))

    def test_unknown_selected_ids_allowed_only_for_stale_rows(self):
        for field in ('reviewed_inventory_ids', 'reviewed_source_ids'):
            a = assertion(self.p); a[field] = ['never-supplied']
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.ledger(dict(self.p, **{KEY: [a]}))
            a['source_basis_sha256'] = '0'*64
            result = self.ledger(dict(self.p, **{KEY: [a]}))
            self.assertEqual(result['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
            self.assertEqual(result['review_ledger'][0]['review'][field], ['never-supplied'])

    def test_pending_and_excluded_reports_allow_current_candidate_positions(self):
        self.p[KEY] = [assertion(self.p), assertion(self.p, report='report-two', study='candidate-Y',
                       rid='excluded-report-position', decision='exclude', inventories=['inventory-excluded'],
                       sources=['source-unbound'])]
        result = self.ledger()
        self.assertEqual(result['counts']['current_source_reviews'], 2)
        self.assertEqual(len(template(self.p, 'report-three', 'candidate-X')[KEY]), 1)
        self.assertEqual(len(template(self.p, 'report-two', 'candidate-Y')[KEY]), 1)

    def test_multiple_positions_never_choose_latest_majority_or_canonical_winner(self):
        self.p[KEY] = [assertion(self.p, rid='a', reviewer='A'),
                       assertion(self.p, rid='b', reviewer='B', decision='exclude', inventories=['inventory-pending-B']),
                       assertion(self.p, rid='c', reviewer='C', decision='unclear')]
        self.p[KEY][1]['reviewed_at'] = '2020-01-01'
        item = next(x for x in self.ledger()['candidate_review_ledger'] if x['study_id'] == 'candidate-X')
        self.assertEqual(item['current_decisions'], ['exclude', 'include', 'unclear'])
        self.assertIn('DIFFERING_CURRENT_POSITIONS', item['comparison_cues'])
        self.assertEqual(self.ledger()['canonical_study_selection'], 'NOT_MODELED')

    def test_selected_id_order_not_different_set(self):
        self.p[KEY] = [assertion(self.p, rid='a', reviewer='A', inventories=['inventory-pending-A', 'inventory-pending-B']),
                       assertion(self.p, rid='b', reviewer='B', inventories=['inventory-pending-B', 'inventory-pending-A'])]
        row = next(x for x in self.ledger()['candidate_review_ledger'] if x['study_id'] == 'candidate-X')
        self.assertNotIn('DIFFERING_CURRENT_REVIEWED_INVENTORY_ID_SETS', row['comparison_cues'])
        self.assertEqual(self.p[KEY][1]['reviewed_inventory_ids'], ['inventory-pending-B', 'inventory-pending-A'])

    def test_basis_exact_scope_pair_all_ordered_raw_descriptions_and_hash(self):
        t = targets(self.p)['report-three', 'candidate-X']
        basis = t['source_basis']
        self.assertEqual(basis['scope'], 'report_study_inventory_supplied_eligibility_context')
        self.assertEqual((basis['report_id'], basis['study_id']), ('report-three', 'candidate-X'))
        self.assertTrue(basis['inventory_currently_described'])
        self.assertEqual(basis['report_study_inventory_assertions'], self.p['report_study_inventory'][:2])
        self.assertEqual(t['source_basis_sha256'], hashlib.sha256(canonical_json_bytes(basis)).hexdigest())
        reordered = dict(reversed(list(self.p.items())))
        self.assertEqual(targets(reordered), targets(self.p))

    def test_every_raw_description_field_and_order_binds_even_unselected_description(self):
        self.position()
        changes = [lambda p: p['report_study_inventory'][1].update(description='Different fictional wording'),
                   lambda p: p['report_study_inventory'][1].update(recorded_by='Other fictional recorder'),
                   lambda p: p['report_study_inventory'][1].update(recorded_at='2024-02-29'),
                   lambda p: p['report_study_inventory'][1].update(source_locator='Fictional other section'),
                   lambda p: p['report_study_inventory'][1].update(source_basis_sha256='0'*64),
                   lambda p: p['report_study_inventory'].reverse(),
                   lambda p: p['report_study_inventory'].pop(1)]
        for change in changes:
            p = copy.deepcopy(self.p); change(p)
            with self.subTest(change=change):
                self.assertEqual(self.ledger(p)['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')

    def test_membership_report_decision_result_and_version_changes_do_not_stale(self):
        self.position()
        changes = [lambda p: p['reports'][2].update(decision='include', study_ids=['candidate-X']),
                   lambda p: p['reports'][2].update(decision='exclude', reason='Fictional exclusion'),
                   lambda p: p['evidence'][0].update(result='Changed fictional result'),
                   lambda p: p.update(version='fictional-v2')]
        for change in changes:
            p = copy.deepcopy(self.p); change(p)
            with self.subTest(change=change):
                self.assertEqual(self.ledger(p)['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')

    def test_criteria_and_sources_stale_without_renewing_input(self):
        self.position()
        changes = [lambda p: p.update(question='Other fictional question'),
                   lambda p: p['inclusion_criteria'].append('Other fictional criterion'),
                   lambda p: p['exclusion_criteria'].append('Other fictional criterion'),
                   lambda p: p['report_sources'][3].update(document_version='Fictional v2'),
                   lambda p: p['report_sources'][3].update(document_sha256='e'*64)]
        for change in changes:
            p = copy.deepcopy(self.p); change(p); before = copy.deepcopy(p)
            with self.subTest(change=change):
                self.assertEqual(self.ledger(p)['review_ledger'][0]['source_match_status'], 'STALE_SOURCE')
                template(p)
                self.assertEqual(p, before)

    def test_description_removal_retains_stale_orphan_without_template_or_queue(self):
        original = copy.deepcopy(self.position())
        self.p['report_study_inventory'] = self.p['report_study_inventory'][2:]
        result = self.ledger()
        orphan = result['orphan_review_assertions'][0]
        self.assertEqual(orphan['review'], original)
        self.assertFalse(orphan['inventory_currently_described'])
        self.assertEqual(orphan['source_match_status'], 'STALE_SOURCE')
        self.assertEqual(template(self.p, 'report-three', 'candidate-X')[KEY], [])
        self.assertFalse(any(r['report_id'] == 'report-three' and r['study_id'] == 'candidate-X'
                             for r in result['current_candidates_with_review_cues']))
        self.p[KEY][0]['source_basis_sha256'] = targets(self.p)['report-three', 'candidate-X']['source_basis_sha256']
        with self.assertRaises(ValueError): self.ledger()

    def test_template_null_human_fields_and_retrieved_sources_only(self):
        result = template(self.p)
        self.assertTrue(result[KEY])
        for row in result[KEY]:
            for field, value in row.items():
                if field not in ('report_id', 'study_id', 'source_basis_sha256'):
                    self.assertIsNone(value, field)
        self.assertEqual(template(self.p, 'report-five', 'candidate-Z')[KEY], [])
        p = copy.deepcopy(self.p); p['report_sources'] = []
        self.assertEqual(template(p)[KEY], [])
        with self.assertRaises(ValueError): run(dict(self.p, **{KEY: result[KEY]}))

    def test_exact_selection_whole_protocol_validation_and_no_input_mutation(self):
        self.position()
        for args in ((None, 'candidate-X'), ('missing', None), ('report-three', 'missing')):
            with self.subTest(args=args), self.assertRaises(ValueError): review(self.p, *args)
        p = copy.deepcopy(self.p); p['reports'][0]['record_ids'] = ['missing-record']
        with self.assertRaises(ValueError): review(p, 'report-three', 'candidate-X')
        before = copy.deepcopy(self.p)
        result = review(self.p, 'report-three', 'candidate-X')
        result['review_ledger'][0]['review']['reviewed_inventory_ids'].append('changed-output')
        self.assertEqual(self.p, before)

    def test_no_network_or_execution_for_locators(self):
        self.p['report_sources'][3]['source_locator'] = 'https://invalid.example/never-fetch'
        self.position()
        before = copy.deepcopy(self.p)
        with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')), \
             patch('subprocess.run', side_effect=AssertionError('execution forbidden')):
            result = review(self.p); render_text(result); template(self.p)
        self.assertEqual(self.p, before)
        self.assertEqual(result['external_calls'], 0)

    def test_legacy_membership_hashes_counts_csv_and_results_unchanged(self):
        from report_study_review_links import prepare_targets as membership_targets
        from prisma_reports import report_flow
        before = run(self.p); flow = report_flow(self.p); hashes = membership_targets(self.p)
        self.position(decision='exclude')
        after = run(self.p); newflow = report_flow(self.p)
        self.assertEqual(membership_targets(self.p), hashes)
        for key in ('flow', 'evidence', 'report_study_coverage', 'report_review', 'report_study_inventory'):
            self.assertEqual(before[key], after[key], key)
        for key in ('record_flow', 'report_flow', 'report_csv', 'report_study_coverage'):
            self.assertEqual(flow[key], newflow[key], key)

    def test_projection_integration_and_bundle_round_trip(self):
        from prisma_audit import export_audit
        from prisma_reports import report_flow
        from research_status import status
        from review_handoff import handoff
        from synthesis_review import snapshot
        from research_bundle import create, verify
        self.position()
        expected = run(self.p)[VIEW]
        for fn in (export_audit, report_flow, snapshot):
            self.assertEqual(fn(self.p)[VIEW], expected)
        state = status(self.p); packet = handoff(self.p)
        self.assertIn(VIEW, state); self.assertEqual(packet[VIEW], state[VIEW])
        self.assertTrue(any(x['script'] == 'report_study_inventory_review.py' for x in packet['detailed_views']))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'protocol.json'; destination = Path(tmp)/'bundle.zip'
            source.write_text(json.dumps(self.p), encoding='utf-8')
            create(source, destination)
            self.assertTrue(verify(destination)['valid'])

    def test_comparison_retains_deleted_description_history(self):
        from compare_runs import compare_protocols
        self.position(); after = copy.deepcopy(self.p)
        after['report_study_inventory'] = after['report_study_inventory'][2:]
        delta = compare_protocols(self.p, after)['report_study_inventory_review_changes']
        self.assertEqual(delta['assertion_changes']['unchanged_count'], 1)
        comparison = delta['review_comparisons'][0]
        self.assertTrue(comparison['before']['inventory_currently_described'])
        self.assertFalse(comparison['after']['inventory_currently_described'])

    def test_cli_utf8_control_safe_create_only_and_input_preservation(self):
        self.p['report_sources'][3]['source_locator'] = 'fictional://한글\n\x1b\x00'
        self.position()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'protocol.json'; output = Path(tmp)/'view.json'
            source.write_bytes((json.dumps(self.p, ensure_ascii=False)+'\r\n').encode('utf-8'))
            before = source.read_bytes()
            result = self.cli(source, '--report-id=report-three', '--study-id=candidate-X', '--text', '--output', str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('한글'.encode(), result.stdout)
            self.assertNotIn(b'\x1b', result.stdout); self.assertNotIn(b'\x00', result.stdout)
            saved = output.read_bytes()
            for target in (output, source):
                failed = self.cli(source, '--output', str(target))
                self.assertNotEqual(failed.returncode, 0); self.assertEqual(failed.stdout, b'')
            self.assertEqual(output.read_bytes(), saved); self.assertEqual(source.read_bytes(), before)

    def test_cli_malformed_json_surrogate_and_invalid_unselected_context_write_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'protocol.json'; output = Path(tmp)/'view.json'
            surrogate = copy.deepcopy(self.p); surrogate['report_sources'][3]['source_locator'] = '\ud800'
            invalid = copy.deepcopy(self.p); invalid['reports'][0]['record_ids'] = ['missing-record']
            for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', json.dumps(surrogate).encode(), json.dumps(invalid).encode()):
                source.write_bytes(raw)
                result = self.cli(source, '--report-id=report-three', '--output', str(output))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b''); self.assertFalse(output.exists())


    def test_current_review_does_not_upgrade_stale_description_or_unbound_bytes(self):
        self.p['report_study_inventory'][0]['source_basis_sha256'] = '0'*64
        self.position()
        result = self.ledger()
        row = result['review_ledger'][0]
        self.assertEqual(row['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(row['reviewed_inventory_source_status'],
                         [dict(inventory_id='inventory-pending-A', source_match_status='STALE_SOURCE')])
        candidate = next(r for r in result['candidate_review_ledger'] if r['study_id'] == 'candidate-X')
        self.assertIn('STALE_INVENTORY_ASSERTIONS', candidate['comparison_cues'])
        self.assertEqual(result['document_bytes_verification'], 'NOT_PERFORMED')
        self.assertEqual(result['eligibility_correctness'], 'NOT_ASSESSED')
        self.assertEqual(result['reviewer_identity_verification'], 'NOT_ESTABLISHED')
        self.assertEqual(template(self.p, 'report-two', 'candidate-Y')['candidate_targets'][0]['source_binding_state'],
                         'DOCUMENT_BYTES_UNBOUND')

    def test_unrelated_pair_description_changes_do_not_stale(self):
        self.position()
        before = self.p[KEY][0]['source_basis_sha256']
        self.p['report_study_inventory'][2]['description'] = 'Another fictional description on another pair.'
        self.assertEqual(targets(self.p)['report-three', 'candidate-X']['source_basis_sha256'], before)
        self.assertEqual(self.ledger()['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')

    def test_no_report_stage_returns_no_targets_or_drafts(self):
        self.p.pop('reports'); self.p.pop('report_sources'); self.p.pop('report_study_inventory')
        self.p.pop('report_reviews', None)
        self.p['evidence'] = []; self.p['gaps'] = []
        self.p[KEY] = []
        self.assertEqual(review(self.p)['report_stage'], 'NOT_SUPPLIED')
        self.assertEqual(template(self.p)[KEY], [])
        self.assertEqual(review(self.p)['candidate_targets'], [])

    def test_selected_view_preserves_input_pointer_and_exact_candidate(self):
        self.p[KEY] = [assertion(self.p), assertion(self.p, report='report-two', study='candidate-Y',
                       rid='second-review', inventories=['inventory-excluded'], sources=['source-unbound'])]
        result = review(self.p, 'report-two', 'candidate-Y')
        self.assertEqual(result['review_ledger'][0]['input_pointer'], '/report_study_inventory_reviews/1')
        self.assertEqual([(r['report_id'], r['study_id']) for r in result['candidate_targets']],
                         [('report-two', 'candidate-Y')])
        self.assertEqual([r['source']['source_id'] for r in result['source_ledger']], ['source-unbound'])

    def test_cli_template_leaves_all_human_selections_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'protocol.json'; output = Path(tmp)/'template.json'
            source.write_text(json.dumps(self.p), encoding='utf-8')
            result = self.cli(source, '--report-id=report-three', '--study-id=candidate-X',
                              '--template', '--output', str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = json.loads(output.read_bytes())[KEY]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['study_id'], 'candidate-X')
            self.assertIsNone(rows[0]['reviewed_inventory_ids'])
            self.assertIsNone(rows[0]['reviewed_source_ids'])
            self.assertIsNone(rows[0]['decision'])


    def test_csv_import_enrichment_and_real_mapped_provenance_binding(self):
        from bibliographic_integrity import ENRICHMENT_FIELDS
        from test_report_study_inventory import ReportStudyInventoryTests, assertion as inventory_assertion
        helper = ReportStudyInventoryTests(); helper.setUp(); p = helper.imported()
        collection = run(p)['bibliographic_collection']
        p['report_study_inventory'] = [inventory_assertion(p, collection=collection)]
        self.assertIn(KEY, ENRICHMENT_FIELDS)
        scaffold = template(p, 'report-one', 'study-A')
        target = prepare_targets(p, collection)['candidate_targets'][0]
        self.assertEqual(scaffold[KEY][0]['source_basis_sha256'], target['source_basis_sha256'])
        self.assertNotEqual(target['source_basis_sha256'],
                            prepare_targets(p)['candidate_targets'][0]['source_basis_sha256'])
        row = scaffold[KEY][0]
        row.update(review_id='fictional-import-review', reviewer='Fictional imported reviewer',
                   reviewed_at='2026-11-04', decision='unclear', rationale='Fictional supplied position',
                   reviewed_locator='fictional://import-section', reviewed_inventory_ids=['inventory-1'],
                   reviewed_source_ids=['main'])
        p[KEY] = [row]
        result = run(p)[VIEW]
        self.assertEqual(result['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(review(p)['review_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(result['inventory_ledger'][0]['source_match_status'], 'CURRENT_SOURCE')
        self.assertEqual(result['candidate_targets'][0]['source_basis_sha256'], target['source_basis_sha256'])

    def test_report_decision_optional_snapshots_selected_exact_rows_and_replay(self):
        import report_decision as decision
        bare = decision.prepare(self.p, 'report-three')['target']
        self.assertNotIn('inventory_review_stage', bare)
        self.assertNotIn('inventory_review_snapshots', bare)
        empty = copy.deepcopy(self.p); empty[KEY] = []
        target = decision.prepare(empty, 'report-three')['target']
        self.assertEqual(target['inventory_review_stage'], 'SUPPLIED')
        self.assertEqual(target['inventory_review_snapshots'], [])
        self.p[KEY] = [assertion(self.p, decision='exclude'),
                       assertion(self.p, rid='second', reviewer='Other fictional reviewer', decision='unclear'),
                       assertion(self.p, report='report-two', study='candidate-Y', rid='other-report',
                                 inventories=['inventory-excluded'], sources=['source-unbound'])]
        original = copy.deepcopy(self.p)
        prepared = decision.prepare(self.p, 'report-three')
        self.assertEqual(prepared['target']['inventory_review_snapshots'], self.p[KEY][:2])
        self.assertEqual(prepared['target']['inventory_review_stage'], 'SUPPLIED')
        document = prepared['decision_document']
        document.update(receipt_id='fictional-candidate-include', decision='include',
                        reason='Fictional explicit human inclusion despite differing positions',
                        adjudicator='Fictional decision maker', decided_at='2026-11-04',
                        rationale='Fictional explicit choice, not a vote', source_locator='fictional://choice',
                        study_declaration={'study_ids': ['candidate-X']})
        record = decision.assemble(self.p, document)
        candidate = record['protocol_candidate']
        self.assertEqual(candidate[KEY], original[KEY])
        self.assertEqual(candidate['report_study_inventory'], original['report_study_inventory'])
        self.assertEqual(record['receipt']['target']['inventory_review_snapshots'], original[KEY][:2])
        self.assertEqual(candidate['reports'][2]['decision'], 'include')
        self.assertEqual(candidate['reports'][2]['study_ids'], ['candidate-X'])
        before = run(original)[VIEW]['review_ledger']; after = run(candidate)[VIEW]['review_ledger']
        self.assertEqual(before, after)
        self.assertTrue(all(row['source_match_status'] == 'CURRENT_SOURCE' for row in after))
        roundtrip = json.loads(json.dumps(record))
        self.assertTrue(decision.verify(original, roundtrip)['valid'])
        self.assertEqual(self.p, original)
        tampered = copy.deepcopy(roundtrip)
        tampered['receipt']['target']['inventory_review_snapshots'][0]['decision'] = 'include'
        with self.assertRaises(ValueError): decision.verify(original, tampered)


if __name__ == '__main__':
    unittest.main()
