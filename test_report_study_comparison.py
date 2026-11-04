"""Exact report/study pair diffs preserve source assertions, never identity inference."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from compare_runs import compare_protocols, render_text
from json_io import quoted_display
from prisma_reports import report_flow

ROOT = Path(__file__).resolve().parent


def fixture(plural=True, second_study=False):
    protocol = json.loads((ROOT / 'examples/report-protocol.json').read_text(encoding='utf-8'))
    protocol['gaps'] = []
    protocol['evidence'][0]['evidence_id'] = 'e1'
    if plural:
        protocol['reports'][0]['study_ids'] = [protocol['reports'][0].pop('study_id')]
    if second_study:
        protocol['reports'][0]['study_ids'].append('s2')
        protocol['evidence'].append(dict(protocol['evidence'][0], evidence_id='e2', study_id='s2'))
    return protocol


def second_report(protocol, report_id='report-2', study_id='s1', with_result=False):
    protocol['screening'][1]['decision'] = 'include'
    protocol['reports'].append(dict(report_id=report_id, record_ids=['r2'], retrieval='retrieved',
                                    decision='include', study_id=study_id, locator='synthetic section'))
    if with_result:
        protocol['evidence'].append(dict(protocol['evidence'][0], record_id='r2',
                                        evidence_id='e-other', study_id=study_id))
    return protocol


def block(before, after):
    return compare_protocols(before, after)['report_study_comparison']


def indexed(result):
    return {(row['report_id'], row['study_id']): row for row in result['memberships']}


class ReportStudyComparisonTests(unittest.TestCase):
    def test_opt_in_either_side_and_legacy_omission(self):
        scalar, plural = fixture(False), fixture()
        self.assertNotIn('report_study_comparison', compare_protocols(scalar, scalar))
        for before, after in ((scalar, plural), (plural, scalar)):
            with self.subTest(before_plural='study_ids' in before['reports'][0]):
                result = block(before, after)
                self.assertEqual(result['retained_count'], 1)
                self.assertEqual(result['unchanged_count'], 0)
                self.assertEqual(result['added_memberships'], [])
                self.assertEqual(result['removed_memberships'], [])
                row = result['memberships'][0]
                self.assertEqual(row['membership_status'], 'RETAINED')
                self.assertEqual(row['changed_report_fields'], ['study_id', 'study_ids'])
                self.assertTrue(row['input_pointer_changed'])
                self.assertEqual({row['before']['declaration_form'], row['after']['declaration_form']}, {'study_id', 'study_ids'})
                self.assertEqual(row['before']['declared_study_ids'], ['s1'])
                self.assertEqual(row['after']['declared_study_ids'], ['s1'])
                self.assertEqual(row['linked_evidence_changes']['unchanged_count'], 1)

    def test_identical_snapshots_and_nonpromotion_boundaries(self):
        p = fixture(second_study=True)
        result = block(p, p)
        self.assertEqual(result['retained_count'], 2)
        self.assertEqual(result['unchanged_count'], 2)
        self.assertEqual(result['before_report_ledger_stage'], 'SUPPLIED')
        self.assertEqual(result['after_report_ledger_stage'], 'SUPPLIED')
        self.assertEqual(result['before_counts'], dict(included_memberships=2, memberships_with_result_rows=2, memberships_without_result_rows=0))
        self.assertEqual(result['after_counts'], result['before_counts'])
        for key, value in dict(change_significance='NOT_ASSESSED', study_identity_verification='NOT_ESTABLISHED',
                               study_eligibility_assessment='NOT_PERFORMED', extraction_completeness='NOT_ESTABLISHED').items():
            self.assertEqual(result[key], value)
        for row in result['memberships']:
            self.assertEqual(row['before'], row['after'])
            self.assertEqual(row['comparison_cues'], [])
            self.assertFalse(row['input_pointer_changed'])
            self.assertEqual(row['changed_report_fields'], [])
            self.assertTrue(row['before']['has_result_rows'])
            self.assertEqual(row['before']['report'], p['reports'][0])

    def test_memberships_without_any_result_are_counted(self):
        before = fixture(second_study=True)
        before['evidence'] = []
        after = copy.deepcopy(before)
        after['reports'][0]['study_ids'].append('s3')
        result = block(before, after)
        self.assertEqual(result['before_counts']['memberships_without_result_rows'], 2)
        self.assertEqual(result['after_counts']['memberships_without_result_rows'], 3)
        self.assertEqual(result['added_memberships'], [dict(report_id='report-1', study_id='s3')])
        row = indexed(result)[('report-1', 's3')]
        self.assertIsNone(row['before'])
        self.assertIsNone(row['input_pointer_changed'])
        self.assertFalse(row['after']['has_result_rows'])
        self.assertEqual(row['after']['evidence_ids'], [])
        self.assertEqual(row['after']['linked_evidence'], [])

    def test_partial_extraction_diff_even_when_report_counter_unchanged(self):
        before = fixture(second_study=True)
        after = copy.deepcopy(before)
        after['evidence'].pop()
        comparison = compare_protocols(before, after)
        self.assertEqual(comparison['before_report_counts']['reports_with_extraction'], 1)
        self.assertEqual(comparison['after_report_counts']['reports_with_extraction'], 1)
        result = comparison['report_study_comparison']
        self.assertEqual(result['after_counts']['memberships_without_result_rows'], 1)
        self.assertEqual(result['unchanged_count'], 1)
        row = indexed(result)[('report-1', 's2')]
        self.assertEqual(row['linked_evidence_changes'], dict(added_ids=[], removed_ids=['e2'], changed=[], unchanged_count=0))
        self.assertEqual(row['changed_report_fields'], [])
        self.assertTrue(row['before']['has_result_rows'])
        self.assertFalse(row['after']['has_result_rows'])
        self.assertTrue(row['comparison_cues'])

    def test_reordered_study_ids_retain_pairs_and_show_positions(self):
        before = fixture(second_study=True)
        after = copy.deepcopy(before)
        after['reports'][0]['study_ids'].reverse()
        result = block(before, after)
        self.assertEqual(result['retained_count'], 2)
        self.assertEqual(result['unchanged_count'], 0)
        self.assertEqual(result['added_memberships'], [])
        self.assertEqual(result['removed_memberships'], [])
        for row in result['memberships']:
            self.assertTrue(row['input_pointer_changed'])
            self.assertEqual(row['changed_report_fields'], ['study_ids'])
            self.assertEqual(row['before']['report_input_pointer'], '/reports/0')
            self.assertEqual(row['after']['declared_study_ids'], ['s2', 's1'])
        s1 = indexed(result)[('report-1', 's1')]
        self.assertEqual(s1['before']['input_pointer'], '/reports/0/study_ids/0')
        self.assertEqual(s1['after']['input_pointer'], '/reports/0/study_ids/1')

    def test_reordered_reports_only_move_pointers(self):
        before = second_report(fixture(), with_result=True)
        after = copy.deepcopy(before)
        after['reports'].reverse()
        result = block(before, after)
        self.assertEqual(result['retained_count'], 2)
        self.assertEqual(result['unchanged_count'], 0)
        self.assertEqual([(r['report_id'], r['study_id']) for r in result['memberships']], [('report-1', 's1'), ('report-2', 's1')])
        for row in result['memberships']:
            self.assertTrue(row['input_pointer_changed'])
            self.assertNotEqual(row['before']['report_input_pointer'], row['after']['report_input_pointer'])
            self.assertEqual(row['changed_report_fields'], [])
            self.assertEqual(row['linked_evidence_changes']['unchanged_count'], 1)

    def test_renamed_study_is_remove_add_even_with_same_locator(self):
        before = fixture()
        after = copy.deepcopy(before)
        after['reports'][0]['study_ids'] = ['renamed']
        after['evidence'][0]['study_id'] = 'renamed'
        result = block(before, after)
        self.assertEqual(result['retained_count'], 0)
        self.assertEqual(result['removed_memberships'], [dict(report_id='report-1', study_id='s1')])
        self.assertEqual(result['added_memberships'], [dict(report_id='report-1', study_id='renamed')])
        rows = indexed(result)
        self.assertIsNone(rows[('report-1', 's1')]['after'])
        self.assertEqual(rows[('report-1', 's1')]['membership_status'], 'REMOVED')
        self.assertEqual(rows[('report-1', 'renamed')]['membership_status'], 'ADDED')

    def test_renamed_report_is_remove_add_not_locator_matching(self):
        before = fixture()
        after = copy.deepcopy(before)
        after['reports'][0]['report_id'] = 'renamed'
        result = block(before, after)
        self.assertEqual(result['retained_count'], 0)
        self.assertEqual(result['removed_memberships'], [dict(report_id='report-1', study_id='s1')])
        self.assertEqual(result['added_memberships'], [dict(report_id='renamed', study_id='s1')])

    def test_same_evidence_id_reassigned_between_studies(self):
        before = fixture(second_study=True)
        before['evidence'].pop()
        after = copy.deepcopy(before)
        after['evidence'][0]['study_id'] = 's2'
        rows = indexed(block(before, after))
        self.assertEqual(rows[('report-1', 's1')]['linked_evidence_changes']['removed_ids'], ['e1'])
        self.assertEqual(rows[('report-1', 's2')]['linked_evidence_changes']['added_ids'], ['e1'])
        self.assertEqual(rows[('report-1', 's1')]['linked_evidence_changes']['changed'], [])
        self.assertEqual(rows[('report-1', 's2')]['linked_evidence_changes']['changed'], [])

    def test_same_study_two_reports_and_result_reassignment(self):
        before = second_report(fixture())
        after = copy.deepcopy(before)
        after['evidence'][0]['record_id'] = 'r2'
        result = block(before, after)
        self.assertEqual(result['retained_count'], 2)
        self.assertEqual(result['unchanged_count'], 0)
        self.assertEqual(result['before_counts'], result['after_counts'])
        rows = indexed(result)
        self.assertEqual(rows[('report-1', 's1')]['linked_evidence_changes']['removed_ids'], ['e1'])
        self.assertEqual(rows[('report-2', 's1')]['linked_evidence_changes']['added_ids'], ['e1'])

    def test_record_alias_change_within_pair_is_source_difference(self):
        before = fixture()
        before['screening'][1]['decision'] = 'include'
        before['reports'][0]['record_ids'].append('r2')
        after = copy.deepcopy(before)
        after['evidence'][0]['record_id'] = 'r2'
        row = block(before, after)['memberships'][0]
        self.assertEqual(row['changed_report_fields'], [])
        self.assertEqual(row['linked_evidence_changes']['changed'], [dict(id='e1', fields=['record_id'])])
        self.assertEqual(row['membership_status'], 'RETAINED')
        self.assertTrue(row['comparison_cues'])

    def test_changed_results_and_both_locators_remain_visible(self):
        before = fixture()
        after = copy.deepcopy(before)
        after['reports'][0]['locator'] = 'new report locator'
        after['evidence'][0].update(result='new supplied result', locator='new result locator')
        row = block(before, after)['memberships'][0]
        self.assertEqual(row['changed_report_fields'], ['locator'])
        self.assertEqual(row['linked_evidence_changes']['changed'], [dict(id='e1', fields=['locator', 'result'])])
        self.assertEqual(row['after']['linked_evidence'][0]['result'], 'new supplied result')
        self.assertEqual(row['after']['report']['locator'], 'new report locator')

    def test_absent_and_empty_reports_have_distinct_stages_and_counts(self):
        plural = fixture()
        plural['evidence'] = []
        absent = copy.deepcopy(plural)
        absent.pop('reports')
        empty = copy.deepcopy(absent)
        empty['reports'] = []
        zero = dict(included_memberships=0, memberships_with_result_rows=0, memberships_without_result_rows=0)
        for other, stage, counts in ((absent, 'NOT_SUPPLIED', None), (empty, 'SUPPLIED', zero)):
            for before, after, side in ((other, plural, 'before'), (plural, other, 'after')):
                with self.subTest(stage=stage, side=side):
                    result = block(before, after)
                    self.assertEqual(result[side + '_report_ledger_stage'], stage)
                    self.assertEqual(result[side + '_counts'], counts)
                    self.assertEqual(result['retained_count'], 0)

    def test_mixed_scalar_and_excluded_metadata_not_membership(self):
        before = second_report(fixture())
        before['reports'][1].update(decision='exclude', reason='scope', study_id='ignored')
        after = copy.deepcopy(before)
        after['reports'][1]['study_id'] = 'different ignored scalar'
        after['reports'][1]['metadata'] = {'comment': 'retained assertion only'}
        result = block(before, after)
        self.assertEqual(result['retained_count'], 1)
        self.assertEqual(result['unchanged_count'], 1)
        self.assertEqual(result['before_counts']['included_memberships'], 1)
        self.assertEqual(len(result['memberships']), 1)
        before['reports'][1].update(decision='include', study_id='s2')
        rows = indexed(block(before, before))
        self.assertEqual(rows[('report-2', 's2')]['before']['declaration_form'], 'study_id')
        self.assertFalse(rows[('report-2', 's2')]['before']['has_result_rows'])

    def test_included_to_excluded_removes_membership_with_other_plural_opt_in(self):
        before = second_report(fixture(), with_result=True)
        after = copy.deepcopy(before)
        after['reports'][1].update(decision='exclude', reason='outside supplied scope')
        after['evidence'] = [row for row in after['evidence'] if row['record_id'] != 'r2']
        after['gaps'] = []
        result = block(before, after)
        self.assertEqual(result['removed_memberships'], [dict(report_id='report-2', study_id='s1')])
        self.assertEqual(result['added_memberships'], [])
        self.assertEqual(result['retained_count'], 1)
        self.assertEqual(result['unchanged_count'], 1)
        self.assertEqual(result['before_counts']['included_memberships'], 2)
        self.assertEqual(result['after_counts']['included_memberships'], 1)
        row = indexed(result)[('report-2', 's1')]
        self.assertEqual(row['membership_status'], 'REMOVED')
        self.assertIsNone(row['after'])
        self.assertIsNone(row['input_pointer_changed'])
        self.assertEqual(row['before']['evidence_ids'], ['e-other'])
        self.assertEqual(row['linked_evidence_changes']['removed_ids'], ['e-other'])
        self.assertEqual(row['comparison_cues'], ['MEMBERSHIP_REMOVED', 'LINKED_RESULT_ASSERTIONS_CHANGED'])

    def test_source_record_links_change_with_stable_pair_and_evidence(self):
        original = fixture()
        original['screening'][1]['decision'] = 'include'
        expanded = copy.deepcopy(original)
        expanded['reports'][0]['record_ids'].append('r2')
        for before, after in ((original, expanded), (expanded, original)):
            with self.subTest(before_records=before['reports'][0]['record_ids']):
                result = block(before, after)
                self.assertEqual(result['retained_count'], 1)
                self.assertEqual(result['unchanged_count'], 0)
                self.assertEqual(result['added_memberships'], [])
                self.assertEqual(result['removed_memberships'], [])
                row = result['memberships'][0]
                self.assertEqual(row['changed_report_fields'], ['record_ids'])
                self.assertEqual(row['comparison_cues'], ['REPORT_ASSERTIONS_CHANGED'])
                self.assertFalse(row['input_pointer_changed'])
                self.assertEqual(row['before']['evidence_ids'], ['e1'])
                self.assertEqual(row['after']['evidence_ids'], ['e1'])
                self.assertEqual(row['before']['linked_evidence'], row['after']['linked_evidence'])
                self.assertEqual(row['linked_evidence_changes'], dict(added_ids=[], removed_ids=[], changed=[], unchanged_count=1))

    def test_report_unknown_metadata_is_not_dropped(self):
        before = fixture()
        before['reports'][0]['metadata'] = {'supplied': [1, True, '1']}
        after = copy.deepcopy(before)
        after['reports'][0]['metadata']['supplied'][0] = True
        row = block(before, after)['memberships'][0]
        self.assertEqual(row['changed_report_fields'], ['metadata'])
        self.assertEqual(row['before']['report']['metadata']['supplied'][0], 1)
        self.assertIs(row['after']['report']['metadata']['supplied'][0], True)

    def test_exact_literals_and_tuple_keys_prevent_collisions(self):
        for delimiter in ('|', '::', '/', '\\', '\u0000'):
            p = second_report(fixture(), report_id='a', study_id='b' + delimiter + 'c')
            p['evidence'] = []
            p['reports'][0].update(report_id='a' + delimiter + 'b', study_ids=['c', 'c ', 'C'])
            result = block(p, p)
            expected = sorted([('a' + delimiter + 'b', 'c'), ('a' + delimiter + 'b', 'c '),
                               ('a' + delimiter + 'b', 'C'), ('a', 'b' + delimiter + 'c')])
            with self.subTest(delimiter=delimiter):
                self.assertEqual(list(indexed(result)), expected)
                self.assertEqual(result['retained_count'], 4)
                self.assertEqual(result['unchanged_count'], 4)

    def test_evidence_order_and_object_key_order_do_not_change_snapshots(self):
        before = fixture()
        before['evidence'].append(dict(before['evidence'][0], evidence_id='e0'))
        after = copy.deepcopy(before)
        after['evidence'].reverse()
        after['reports'][0] = dict(reversed(list(after['reports'][0].items())))
        result = block(before, after)
        self.assertEqual(result['unchanged_count'], 1)
        self.assertEqual(result['memberships'][0]['before']['evidence_ids'], ['e0', 'e1'])
        self.assertEqual([e['evidence_id'] for e in result['memberships'][0]['before']['linked_evidence']], ['e0', 'e1'])

    def test_deterministic_and_detached_outputs(self):
        before = fixture(second_study=True)
        after = copy.deepcopy(before)
        saved = copy.deepcopy((before, after))
        first = compare_protocols(before, after)
        self.assertEqual(first, compare_protocols(before, after))
        copied = copy.deepcopy(first)
        render_text(first)
        self.assertEqual(first, copied)
        row = first['report_study_comparison']['memberships'][0]
        row['before']['report']['study_ids'].append('mutated')
        row['before']['linked_evidence'][0]['result'] = 'mutated'
        row['before']['declared_study_ids'].append('mutated')
        row['before']['evidence_ids'].append('mutated')
        self.assertEqual((before, after), saved)
        self.assertEqual(compare_protocols(before, after), copied)
        self.assertNotIn('mutated', row['after']['report']['study_ids'])
        self.assertNotIn('mutated', first['report_study_comparison']['memberships'][1]['before']['report']['study_ids'])

    def test_invalid_declarations_and_conflicting_evidence_fail(self):
        good = fixture()
        for value in ([], None, 's1', ['s1', 's1'], [False], [' ']):
            bad = copy.deepcopy(good)
            bad['reports'][0]['study_ids'] = value
            for before, after in ((good, bad), (bad, good)):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    compare_protocols(before, after)
        bad = copy.deepcopy(good)
        bad['evidence'][0]['study_id'] = 'undeclared'
        with self.assertRaises(ValueError):
            compare_protocols(good, bad)
        bad = copy.deepcopy(good)
        bad['reports'][0]['study_id'] = None
        with self.assertRaises(ValueError):
            compare_protocols(bad, good)

    def test_exact_comparison_cues_distinguish_sources_order_and_presence(self):
        before = fixture()
        cases = []
        after = copy.deepcopy(before)
        after['reports'][0]['locator'] += ' revised'
        cases.append((after, ['REPORT_ASSERTIONS_CHANGED']))
        after = copy.deepcopy(before)
        after['reports'][0]['study_ids'].append('no results')
        cases.append((after, ['DECLARED_STUDY_ORDER_OR_SET_CHANGED']))
        after = copy.deepcopy(before)
        after['evidence'] = []
        cases.append((after, ['RESULT_PRESENCE_CHANGED', 'LINKED_RESULT_ASSERTIONS_CHANGED']))
        after = copy.deepcopy(before)
        after['evidence'][0]['result'] += ' revised'
        cases.append((after, ['LINKED_RESULT_ASSERTIONS_CHANGED']))
        after = copy.deepcopy(before)
        after['reports'][0]['study_id'] = after['reports'][0].pop('study_ids')[0]
        cases.append((after, ['DECLARATION_FORM_CHANGED', 'INPUT_LOCATION_CHANGED']))
        for after, cues in cases:
            with self.subTest(cues=cues):
                self.assertEqual(indexed(block(before, after))[('report-1', 's1')]['comparison_cues'], cues)
        after = copy.deepcopy(before)
        after['reports'][0]['report_id'] = 'other'
        rows = indexed(block(before, after))
        self.assertEqual(rows[('other', 's1')]['comparison_cues'], ['MEMBERSHIP_ADDED', 'LINKED_RESULT_ASSERTIONS_CHANGED'])
        self.assertEqual(rows[('report-1', 's1')]['comparison_cues'], ['MEMBERSHIP_REMOVED', 'LINKED_RESULT_ASSERTIONS_CHANGED'])

    def test_text_exposes_every_pair_even_unchanged_and_missing(self):
        before = fixture(second_study=True)
        before['evidence'].pop()
        after = copy.deepcopy(before)
        after['reports'][0]['study_ids'].append('added without results')
        comparison = compare_protocols(before, after)
        result = comparison['report_study_comparison']
        text = render_text(comparison)
        heading = 'Explicit report-study comparison (exact supplied pairs, not verified identity):'
        self.assertIn(heading, text)
        self.assertNotIn(heading, render_text(compare_protocols(fixture(False), fixture(False))))
        self.assertIn('Added pairs: ' + quoted_display(result['added_memberships']), text)
        self.assertIn('Removed pairs: ' + quoted_display(result['removed_memberships']), text)
        for row in result['memberships']:
            self.assertIn('Pair: ' + quoted_display(dict(report_id=row['report_id'], study_id=row['study_id'])), text)
            self.assertIn('Membership status: ' + row['membership_status'], text)
            self.assertIn('Pair cues: ' + quoted_display(row['comparison_cues']), text)
            self.assertIn('Changed report fields: ' + quoted_display(row['changed_report_fields']), text)
            self.assertIn('Linked result changes: ' + quoted_display(row['linked_evidence_changes']), text)
            for side in ('before', 'after'):
                if row[side] is not None:
                    self.assertIn(quoted_display(row[side]['input_pointer']), text)
        self.assertIn(result['boundary'], text)
        self.assertIn('"has_result_rows": false', text)

    def test_comparison_never_constructs_csv_writer_for_any_declaration_form(self):
        scalar, plural = fixture(False), fixture()
        for before, after in ((scalar, scalar), (scalar, plural), (plural, scalar), (plural, plural)):
            expected = compare_protocols(before, after)
            with self.subTest(before_plural='study_ids' in before['reports'][0],
                              after_plural='study_ids' in after['reports'][0]):
                with patch('prisma_reports.csv.writer', side_effect=AssertionError('comparison must not serialize CSV')) as writer:
                    self.assertEqual(compare_protocols(before, after), expected)
                    writer.assert_not_called()

    def test_no_csv_report_flow_is_exact_default_projection(self):
        protocols = [fixture(False), fixture(), fixture(second_study=True), second_report(fixture())]
        empty = fixture()
        empty['reports'] = []
        empty['evidence'] = []
        protocols.append(empty)
        for protocol in protocols:
            with self.subTest(reports=protocol['reports']):
                original = copy.deepcopy(protocol)
                expected = report_flow(protocol)
                self.assertIn('report_csv', expected)
                self.assertEqual(report_flow(protocol, include_csv=True), expected)
                expected.pop('report_csv')
                with patch('prisma_reports.csv.writer', side_effect=AssertionError('CSV was disabled')) as writer:
                    actual = report_flow(protocol, include_csv=False)
                    writer.assert_not_called()
                self.assertNotIn('report_csv', actual)
                self.assertEqual(actual, expected)
                self.assertEqual(protocol, original)

    def test_no_csv_path_preserves_nul_literal_ids_without_serialization(self):
        protocol = fixture()
        protocol['reports'][0]['report_id'] = 'report\x00literal'
        protocol['reports'][0]['study_ids'] = ['study\x00literal']
        protocol['evidence'][0]['study_id'] = 'study\x00literal'
        with patch('prisma_reports.csv.writer', side_effect=AssertionError('CSV was disabled')):
            result = report_flow(protocol, include_csv=False)
            comparison = block(protocol, protocol)
        self.assertEqual(result['report_ledger'][0]['report_id'], 'report\x00literal')
        self.assertEqual(result['report_ledger'][0]['study_ids'], ['study\x00literal'])
        self.assertEqual(comparison['memberships'][0]['report_id'], 'report\x00literal')
        self.assertEqual(comparison['memberships'][0]['study_id'], 'study\x00literal')

    def test_no_csv_and_default_paths_enforce_same_report_validation(self):
        invalid = []
        for plural in (False, True):
            bad = fixture(plural)
            bad['evidence'][0]['study_id'] = 'undeclared'
            invalid.append(bad)
            bad = fixture(plural)
            bad['reports'][0]['locator'] = ''
            invalid.append(bad)
            bad = fixture(plural)
            bad['reports'][0]['record_ids'] = ['not-an-included-record']
            invalid.append(bad)
            bad = fixture(plural)
            bad['reports'].append(copy.deepcopy(bad['reports'][0]))
            invalid.append(bad)
        bad = fixture()
        bad['reports'][0]['study_ids'] = []
        invalid.append(bad)
        for protocol in invalid:
            errors = []
            for include_csv in (True, False):
                with self.subTest(protocol=protocol, include_csv=include_csv):
                    with self.assertRaises(ValueError) as error:
                        report_flow(protocol, include_csv=include_csv)
                    errors.append(str(error.exception))
            self.assertEqual(errors[0], errors[1])

    def test_include_csv_requires_keyword_and_strict_boolean(self):
        protocol = fixture()
        for invalid in (None, 0, 1, '', 'false', [], {}, object()):
            with self.subTest(value=invalid), self.assertRaises((TypeError, ValueError)):
                report_flow(protocol, include_csv=invalid)
        with self.assertRaises(TypeError):
            report_flow(protocol, False)

    def test_portable_cli_json_text_unicode_control_escaping_and_read_only(self):
        before = fixture()
        hostile = '합성-🧪\n\r\t\x1b\u202e'
        before['reports'][0]['report_id'] = hostile
        before['reports'][0]['study_ids'] = [hostile]
        before['evidence'][0]['study_id'] = hostile
        after = copy.deepcopy(before)
        after['evidence'][0]['result'] += ' changed'
        expected = compare_protocols(before, after)
        rendered = render_text(expected)
        self.assertIn(quoted_display(hostile), rendered)
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('\u202e', rendered)
        self.assertIn('NOT_ASSESSED', rendered)
        self.assertIn('NOT_ESTABLISHED', rendered)
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('before.json', 'after.json')]
            for path, value in zip(paths, (before, after)):
                path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').replace('\n', '\r\n').encode('utf-8'))
            originals = [p.read_bytes() for p in paths]
            command = [sys.executable, str(ROOT / 'compare_runs.py'), *map(str, paths)]
            env = dict(os.environ, PYTHONIOENCODING='ascii:strict', PYTHONUTF8='0')
            for text in (False, True):
                args = command + (['--text'] if text else [])
                output = subprocess.run(args, cwd=directory, env=env, capture_output=True, timeout=30)
                self.assertEqual(output.returncode, 0, output.stderr.decode('utf-8'))
                self.assertEqual(output.stderr, b'')
                actual = output.stdout.decode('utf-8').replace('\r\n', '\n')
                self.assertEqual(actual if text else json.loads(actual), rendered if text else expected)
                self.assertEqual(subprocess.run(args, cwd=directory, env=env, capture_output=True, timeout=30).stdout, output.stdout)
            self.assertEqual([p.read_bytes() for p in paths], originals)


if __name__ == '__main__':
    unittest.main()
