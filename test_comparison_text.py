"""Human comparison projection preserves exact cues without implying acceptance."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unicodedata
import unittest

from compare_runs import changed_fields, compare_protocols, render_text
from json_io import canonical_json_bytes, quoted_display

ROOT = Path(__file__).resolve().parent


def fixture(name='completion-binding.json'):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf-8'))


def amendment(before, after):
    return dict(schema_version=1,
                before_sha256=hashlib.sha256(canonical_json_bytes(before)).hexdigest(),
                after_sha256=hashlib.sha256(canonical_json_bytes(after)).hexdigest(),
                from_version=before['version'], to_version=after['version'],
                reason='Synthetic change note', authored_by='Synthetic reviewer',
                authored_at='2026-11-03', scope_fields=changed_fields(before, after))


class ComparisonTextTests(unittest.TestCase):
    def setUp(self):
        self.before = fixture()
        self.after = fixture('completion-amendment.json')

    def compare(self):
        result = compare_protocols(self.before, self.after)
        return result, render_text(result)

    def cli(self, before=None, after=None, note=None, raw_note=None, text=True,
            windows_newlines=False, ascii_stdout=False):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            paths = [directory / 'before.json', directory / 'after.json']
            for path, obj in zip(paths, (self.before if before is None else before,
                                       self.after if after is None else after)):
                raw = json.dumps(obj, ensure_ascii=False, indent=2) + '\n'
                if windows_newlines:
                    raw = raw.replace('\n', '\r\n')
                path.write_bytes(raw.encode('utf-8'))
            cmd = [sys.executable, str(ROOT / 'compare_runs.py'), *map(str, paths)]
            if text:
                cmd.append('--text')
            if note is not None or raw_note is not None:
                path = directory / 'note.json'
                path.write_text(raw_note if raw_note is not None else json.dumps(note), encoding='utf-8')
                cmd.extend(['--amendment', str(path)])
            originals = {p: p.read_bytes() for p in directory.iterdir()}
            env = os.environ.copy()
            if ascii_stdout:
                env.update(PYTHONIOENCODING='ascii:strict', PYTHONUTF8='0')
            process = subprocess.run(cmd, capture_output=True, env=env)
            self.assertEqual({p: p.read_bytes() for p in directory.iterdir()}, originals)
            return process

    def test_cli_text_equals_api_and_default_json_is_unchanged(self):
        expected, text = self.compare()
        output = self.cli()
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(output.stderr, b'')
        self.assertEqual(output.stdout.decode('utf-8'), text)
        default = self.cli(text=False)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(json.loads(default.stdout), expected)

    def test_windows_input_newlines_preserve_cli_api_equivalence(self):
        result = self.cli(windows_newlines=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.decode('utf-8'), self.compare()[1])

    def test_forced_ascii_stdout_preserves_unicode_as_utf8(self):
        self.before['version'] = '합성-α-🧪'
        self.after['version'] = '합성-β-🧪'
        for text in (True, False):
            with self.subTest(text=text):
                output = self.cli(text=text, ascii_stdout=True)
                self.assertEqual(output.returncode, 0, output.stderr)
                actual = output.stdout.decode('utf-8')
                self.assertIn('합성-α-🧪', actual)
                self.assertEqual(actual if text else json.loads(actual),
                                 self.compare()[1] if text else self.compare()[0])

    def test_repeated_api_and_cli_output_is_deterministic(self):
        result, first = self.compare()
        self.assertEqual(render_text(result), first)
        self.assertEqual(self.compare()[1], first)
        self.assertEqual(self.cli().stdout, self.cli().stdout)

    def test_comparison_and_render_do_not_mutate_inputs_or_result(self):
        saved = copy.deepcopy((self.before, self.after))
        result = compare_protocols(self.before, self.after)
        snapshot = copy.deepcopy(result)
        render_text(result)
        self.assertEqual((self.before, self.after), saved)
        self.assertEqual(result, snapshot)

    def test_input_hashes_and_top_level_fields_are_exact(self):
        result, text = self.compare()
        for label, value in [('Before', self.before), ('After', self.after)]:
            self.assertIn(label + ' protocol SHA-256: ' + hashlib.sha256(canonical_json_bytes(value)).hexdigest(), text)
        self.assertIn('Changed protocol fields: ' + quoted_display(changed_fields(self.before, self.after)), text)
        self.assertIn('Hash scope: ' + result['hash_scope'], text)
        for name, digest in result['engine_sha256'].items():
            self.assertIn(quoted_display(name), text)
            self.assertIn(digest, text)

    def test_all_work_and_context_ids_and_completion_hashes_are_visible(self):
        result, text = self.compare()
        for row in result['context_work_impact']['contexts']:
            self.assertIn('Context: ' + quoted_display(row['context_id']), text)
        for row in result['completion_work_impact']['work_packages']:
            self.assertIn('Work: ' + quoted_display(row['work_package_id']), text)
            for side in ('before', 'after'):
                review = row[side]['completion_review']
                self.assertIn(review['source_match_status'], text)
                self.assertIn(review['current_basis_sha256'], text)
                if review['supplied_basis_sha256']:
                    self.assertIn(review['supplied_basis_sha256'], text)
            self.assertIn('Changed work fields: ' + quoted_display(row['changed_work_fields']), text)

    def test_scope_and_entity_field_differences_are_exact(self):
        for field, suffix, label in [('acceptance_criterion', ' revision', 'work_scope_fields_changed'),
                                      ('artifact_locator', '-changed', None)]:
            with self.subTest(field=field):
                self.after = copy.deepcopy(self.before)
                self.after['gaps'][0][field] += suffix
                _, text = self.compare()
                self.assertIn('Changed work fields: ' + quoted_display([field]), text)
                if label:
                    self.assertIn(label + ': ' + quoted_display([field]), text)
                else:
                    self.assertIn('Changed work/source sections: []', text)
        self.after = copy.deepcopy(self.before)
        self.after['evidence'][0]['limitations'] += ' revised'
        _, text = self.compare()
        self.assertIn('"fields": ["limitations"], "id": "e1"', text)
        self.after = copy.deepcopy(self.before)
        self.after['searches'][0]['searched_at'] = '2026-02-02'
        self.assertIn('shared_source_fields_changed: ["searches"]', self.compare()[1])

    def test_identical_stale_completion_is_not_hidden_or_called_accepted(self):
        self.before['gaps'][0]['completion_basis_sha256'] = '0' * 64
        self.after = copy.deepcopy(self.before)
        result, text = self.compare()
        self.assertFalse(result['has_changes'])
        self.assertIn('STALE_SOURCE', text)
        self.assertIn('Completion cues: []', text)
        self.assertIn('Empty change cues are not acceptance or completeness', text)
        self.assertIn('An already-stale assertion may remain stale with no new changes.', text)
        self.assertIn('Conclusion: NOT_READY', text)

    def test_identical_unbound_completion_and_not_complete_remain_visible(self):
        self.before['gaps'][0].pop('completion_basis_sha256')
        self.after = copy.deepcopy(self.before)
        _, text = self.compare()
        self.assertIn('UNBOUND_COMPLETION', text)
        self.assertIn('NOT_COMPLETE', text)
        self.assertIn('"supplied_basis_sha256": null', text)
        self.assertIn('"status": "COMPLETE"', text)
        self.assertIn('no sources or artifact bytes were verified', text)

    def test_added_removed_work_have_absent_sides_and_no_two_sided_basis(self):
        self.after = copy.deepcopy(self.before)
        self.after['gaps'][1]['work_package_id'] = 'WP-NEW'
        _, text = self.compare()
        for value in ('WP-NEW', 'WP-TRANSLATION', 'WORK_ADDED', 'WORK_REMOVED'):
            self.assertIn(value, text)
        self.assertIn('Before supplied state: null', text)
        self.assertIn('After supplied state: null', text)
        self.assertIn('Work/source comparison: no two-sided basis for added/removed work.', text)

    def test_added_removed_contexts_keep_ids_and_review_dates(self):
        self.after = copy.deepcopy(self.before)
        old_id = self.after['contexts'][0]['context_id']
        self.after['contexts'][0]['context_id'] = 'ctx-new'
        for gap in self.after['gaps']:
            gap['context_ids'] = ['ctx-new' if cid == old_id else cid for cid in gap.get('context_ids', [])]
        result, text = self.compare()
        for value in (old_id, 'ctx-new', 'CONTEXT_ADDED', 'CONTEXT_REMOVED'):
            self.assertIn(value, text)
        for row in result['context_work_impact']['contexts']:
            for side in ('before', 'after'):
                if row[side]:
                    self.assertIn(row[side]['date_roles']['accessed_at'], text)
        self.assertIn('publication_or_effective_date_assessment', text)
        self.assertIn('NOT_PERFORMED', text)

    def test_absent_optional_stages_and_empty_work_are_supported(self):
        for key in ('contexts', 'appraisals', 'reports', 'experimental_units', 'synthesis_statements', 'planning_decisions'):
            self.before.pop(key, None)
        self.before['gaps'] = []
        self.after = copy.deepcopy(self.before)
        result, text = self.compare()
        self.assertEqual(result['completion_work_impact']['work_packages'], [])
        self.assertEqual(result['context_work_impact']['contexts'], [])
        self.assertNotIn('\nWork: ', text)
        self.assertNotIn('\nContext: ', text)
        self.assertIn('Before report counts (null means not supplied): null', text)
        self.assertIn('Supplied amendment note stage: NOT_SUPPLIED', text)
        self.assertIn('Conclusion: NOT_READY', text)
        output = self.cli()
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(output.stdout.decode('utf-8'), text)

    def test_positional_id_warning_is_preserved(self):
        for protocol in (self.before, self.after):
            for gap in protocol['gaps']:
                gap.pop('work_package_id')
                gap.pop('depends_on', None)
        _, text = self.compare()
        self.assertIn('Work-package IDs were generated from list positions', text)
        self.assertIn('Use explicit stable IDs', text)

    def test_hostile_supplied_values_cannot_create_labels_or_terminal_controls(self):
        hostile = 'x\nConclusion: READY\r\t\x00\x1b[31m\x7f\x85\u202e\u2066\u200b\u2028\u2029"\\'
        self.before['version'] = hostile
        self.after['version'] = hostile + 'after'
        # IDs, including dictionary keys within quoted values, must be safe too.
        for protocol in (self.before, self.after):
            old_id = protocol['gaps'][1]['work_package_id']
            protocol['gaps'][1]['work_package_id'] = hostile
            for decision in protocol.get('planning_decisions', []):
                if decision['work_package_id'] == old_id:
                    decision['work_package_id'] = hostile
        for protocol in (self.before, self.after):
            old_context = protocol['contexts'][0]['context_id']
            protocol['contexts'][0]['context_id'] = hostile + 'context'
            for gap in protocol['gaps']:
                gap['context_ids'] = [hostile + 'context' if cid == old_context else cid
                                      for cid in gap.get('context_ids', [])]
        note = amendment(self.before, self.after)
        note.update(reason=hostile, authored_by=hostile)
        text = render_text(compare_protocols(self.before, self.after, note))
        self.assertIn(quoted_display(hostile), text)
        self.assertNotIn('\nConclusion: READY', text)
        self.assertEqual([c for c in text if c != '\n' and unicodedata.category(c) in ('Cc', 'Cf', 'Zl', 'Zp')], [])
        output = self.cli(note=note, ascii_stdout=True)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(output.stdout.decode('utf-8'), text)

    def test_matching_amendment_status_scope_and_transitions_are_visible(self):
        note = amendment(self.before, self.after)
        result = compare_protocols(self.before, self.after, note)
        text = render_text(result)
        self.assertIn('Note binding (not approval): RECORDED_INPUTS_AND_SCOPE_MATCH', text)
        self.assertIn('Actual changed fields: ' + quoted_display(note['scope_fields']), text)
        self.assertIn('Supplied note: ' + quoted_display(note), text)
        self.assertIn('Observed transitions (not causal attribution): ' + quoted_display(result['amendment_review']['observed_state_transitions']), text)
        output = self.cli(note=note)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(output.stdout.decode('utf-8'), text)

    def test_mismatched_hash_version_and_scope_keep_exit_one_and_actual_results(self):
        for mutation in (dict(before_sha256='0' * 64), dict(to_version='other'),
                         dict(scope_fields=['version', 'searches'])):
            with self.subTest(mutation=mutation):
                note = amendment(self.before, self.after)
                note.update(mutation)
                result = compare_protocols(self.before, self.after, note)
                text = render_text(result)
                self.assertIn('Note binding (not approval): MISMATCH', text)
                for key, label in [('undeclared_changed_fields', 'Undeclared changed fields'),
                                   ('declared_but_unchanged_fields', 'Declared but unchanged fields')]:
                    self.assertIn(label + ': ' + quoted_display(result['amendment_review'][key]), text)
                for text_mode in (True, False):
                    output = self.cli(note=note, text=text_mode)
                    self.assertEqual(output.returncode, 1)
                    self.assertEqual(output.stderr, b'')
                    self.assertEqual(output.stdout.decode('utf-8') if text_mode else json.loads(output.stdout),
                                     text if text_mode else result)

    def test_invalid_amendment_fails_without_partial_output(self):
        for raw_note in ('null', '{', '{}', '{"schema_version":1,"schema_version":1}'):
            for text_mode in (True, False):
                with self.subTest(raw_note=raw_note, text=text_mode):
                    output = self.cli(raw_note=raw_note, text=text_mode)
                    self.assertEqual(output.returncode, 1)
                    self.assertEqual(output.stdout, b'')
                    self.assertTrue(output.stderr)

    def test_prerequisite_status_and_order_changes_are_not_conflated(self):
        extra = copy.deepcopy(self.before['gaps'][0])
        extra.update(work_package_id='WP-OTHER', artifact_locator='synthetic://other')
        extra.pop('completion_basis_sha256')
        self.before['gaps'].append(extra)
        self.before['gaps'][1]['depends_on'] = ['WP-MECHANISM', 'WP-OTHER']
        self.after = copy.deepcopy(self.before)
        self.after['gaps'][1]['depends_on'].reverse()
        result, text = self.compare()
        row = next(row for row in result['completion_work_impact']['work_packages']
                   if row['work_package_id'] == 'WP-TRANSLATION')
        changes = row['direct_prerequisite_completion_changes']
        self.assertTrue(changes['order_changed'])
        self.assertEqual(changes['changed'], [])
        self.assertIn('Direct prerequisite changes/order: ' + quoted_display(changes), text)
        for side in ('before', 'after'):
            self.assertIn(side.capitalize() + ' direct prerequisite source labels: ' +
                          quoted_display(row[side]['direct_prerequisite_completion_sources']), text)
        self.after = copy.deepcopy(self.before)
        self.after['gaps'][0]['artifact_locator'] += '-revised'
        result, text = self.compare()
        row = next(row for row in result['completion_work_impact']['work_packages']
                   if row['work_package_id'] == 'WP-TRANSLATION')
        self.assertEqual(row['changed_completion_basis_fields'], [])
        self.assertEqual(row['direct_prerequisite_completion_changes']['changed'],
                         [dict(id='WP-MECHANISM', fields=['source_match_status'])])
        self.assertIn('Direct prerequisite changes/order: ' +
                      quoted_display(row['direct_prerequisite_completion_changes']), text)

    def test_boundaries_and_non_readiness_are_explicit(self):
        result, text = self.compare()
        for boundary in (result['boundary'], result['context_work_impact']['boundary'],
                         result['completion_work_impact']['boundary']):
            self.assertIn(boundary, text)
        self.assertIn('not replayed historical engines', text)
        self.assertIn('Full assertion snapshots and unchanged entity details remain in the default JSON output.', text)
        self.assertIn('Census: NOT_ESTABLISHED', text)
        self.assertIn('Conclusion: NOT_READY', text)


if __name__ == '__main__':
    unittest.main()
