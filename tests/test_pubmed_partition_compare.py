"""Offline comparisons of synthetic window observations through the API and real CLI."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pubmed_partition as partition
import pubmed_partition_compare as comparison
from pubmed_discovery import digest
from tests.test_pubmed_discovery import artifact, attempt, native
from tests.test_pubmed_partition import observation, plan

ROOT = Path(__file__).resolve().parents[1]


class ComparisonTests(unittest.TestCase):
    def test_order_duplicates_and_window_identity(self):
        value = plan()
        a, b = value['specs']
        a['page_size'] = 5
        before = [observation(a, ['11', '12', '11', '13'], stop='duplicate_or_paging_overlap'),
                  observation(b, ['14'])]
        after = [observation(b, ['13']), observation(a, ['14', '11', '12'])]
        original = copy.deepcopy((value, before, after))
        with patch('socket.socket', side_effect=AssertionError('offline')):
            report = comparison.compare(value, before, after)
            self.assertTrue(comparison.verify(value, report, before[::-1], after[::-1])['valid'])
        self.assertEqual(original, (value, before, after))
        self.assertEqual(report['before_review_sha256'], digest(partition.review(value, before)))
        self.assertEqual(report['after_review_sha256'], digest(partition.review(value, after)))
        self.assertEqual(report['window_counts']['different_artifact'], 2)
        self.assertEqual([window['request_id'] for window in report['windows']], ['a', 'b'])
        first, second = report['windows']
        self.assertEqual([(r['pmid'], r['change'], r['before_positions'], r['after_positions'])
                          for r in first['pmid_position_changes']], [
            ('11', 'multiplicity_changed', [0, 2], [1]), ('12', 'position_changed', [1], [2]),
            ('13', 'before_only', [3], []), ('14', 'after_only', [], [0])])
        self.assertEqual([r['pmid'] for r in second['pmid_position_changes']], ['14', '13'])
        self.assertEqual(first['before']['stop_reason'], 'duplicate_or_paging_overlap')
        self.assertEqual(first['after']['stop_reason'], 'reported_count_reached')
        self.assertEqual((report['external_calls'], report['census'], report['search_completeness'],
                          report['conclusion']), (0, 'NOT_ESTABLISHED', 'NOT_ESTABLISHED', 'NOT_READY'))

    def test_missing_zero_error_and_unchanged(self):
        value = plan()
        a, b = value['specs']
        zero = observation(a, [])
        stopped = artifact(a, [attempt(a, b'', status=503)], 'http_status')
        visible = observation(a, ['15'])
        cases = [
            ([], [], 'missing_both', None),
            ([], [zero], 'after_only', None),
            ([visible], [], 'before_only', None),
            ([stopped], [visible], 'different_artifact', None),
            ([stopped], [stopped], 'same_artifact', None),
            ([zero], [zero], 'same_artifact', []),
            ([visible], [visible], 'same_artifact', []),
            ([zero], [visible], 'different_artifact',
             [dict(pmid='15', change='after_only', before_positions=[], after_positions=[0])])
        ]
        for old, new, status, expected in cases:
            with self.subTest(status=status, expected=expected):
                report = comparison.compare(value, old, new)
                row = report['windows'][0]
                self.assertEqual((row['status'], row['pmid_position_changes']), (status, expected))
                self.assertEqual(sum(report['window_counts'].values()), 2)
                self.assertEqual(report['windows'][1]['status'], 'missing_both')
                self.assertEqual(row['before'] is None, not old)
                self.assertEqual(row['after'] is None, not new)
        error = comparison.compare(value, [stopped], [zero])['windows'][0]
        self.assertIsNone(error['before']['initial_reported_count'])
        self.assertEqual(error['after']['initial_reported_count'], 0)

    def test_changed_page_observations_without_pmid_changes(self):
        value = plan()
        a = value['specs'][0]
        rows = [attempt(a, native(['11', '12'], 3)), attempt(a, native(['13'], 3, 2), 2)]
        before = artifact(a, rows, 'reported_count_reached')
        rows[1] = attempt(a, native(['13'], 4, 2, querytranslation='alternate synthetic translation'), 2)
        after = artifact(a, rows, 'reported_count_changed')
        row = comparison.compare(value, [before], [after])['windows'][0]
        self.assertEqual(row['pmid_position_changes'], [])
        self.assertEqual(row['status'], 'different_artifact')
        self.assertEqual(row['before']['pages'][1]['count'], 3)
        self.assertEqual(row['after']['pages'][1]['count'], 4)
        self.assertFalse(row['after']['observed_reported_count_accounted_for'])
        self.assertEqual(row['after']['pages'][1]['querytranslation'], 'alternate synthetic translation')
        self.assertEqual(set(row['changed_fields']), {'stop_reason', 'observed_reported_count_accounted_for',
                                                      'pages.count', 'pages.querytranslation'})

    def test_identical_observations_survive_metadata_only_artifact_change(self):
        value = plan()
        a = value['specs'][0]
        before = observation(a, ['11'])
        recorded = attempt(a, native(['11']))
        recorded['elapsed_seconds'] = 0.75
        after = artifact(a, [recorded], 'reported_count_reached')
        row = comparison.compare(value, [before], [after])['windows'][0]
        self.assertEqual(row['status'], 'different_artifact')
        self.assertEqual((row['changed_fields'], row['pmid_position_changes']), ([], []))

    def test_capped_observations_keep_local_counts_and_positions(self):
        value = plan()
        a = value['specs'][0]
        a['max_records'] = 2
        old = observation(a, ['11', '12'], count=10001, stop='max_records')
        new = observation(a, ['12', '13'], count=10002, stop='max_records')
        row = comparison.compare(value, [old], [new])['windows'][0]
        self.assertTrue(row['before']['reported_count_exceeds_local_record_cap'])
        self.assertTrue(row['after']['reported_count_exceeds_pubmed_10000_limit'])
        self.assertFalse(row['after']['observed_reported_count_accounted_for'])
        self.assertEqual([r['change'] for r in row['pmid_position_changes']],
                         ['before_only', 'position_changed', 'after_only'])

    def test_fails_closed_on_mismatch_reauthored_output_and_wrong_side(self):
        value = plan()
        a = value['specs'][0]
        original = observation(a, ['11'])
        altered = copy.deepcopy(original)
        altered['derived']['occurrences'][0]['pmid'] = '77'
        for records in ([altered], [original, original], [observation(dict(a, max_requests=1), ['11'])]):
            for old, new in ((records, []), ([], records)):
                with self.assertRaises(ValueError):
                    comparison.compare(value, old, new)
        report = comparison.compare(value, [original])
        with self.assertRaises(ValueError):
            comparison.verify(value, report, [], [original])
        for edit in (dict(external_calls=False), dict(before_review_sha256='other'), dict(windows=[])):
            with self.assertRaises(ValueError):
                comparison.verify(value, dict(report, **edit), [original])
        self.assertEqual(report['implementation_sha256']['pubmed_partition.py'],
                         '6342d1ed8fd1295a61bdd56bc2b90dc539ac6cd9aefb1d9fa251972b1c89b664')
        self.assertEqual(report['implementation_sha256']['pubmed_partition_compare.py'],
                         hashlib.sha256((ROOT / 'pubmed_partition_compare.py').read_bytes()).hexdigest())

    def test_bounded_reads_and_early_path_count_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'input.json'
            source.write_bytes(b' {} ')
            self.assertEqual(comparison._read(source, 4), ({}, 0))
            with patch.object(comparison, 'parse_json', side_effect=AssertionError('over budget')):
                with self.assertRaises(ValueError):
                    comparison._read(source, 3)
        args = ['tool', 'compare', 'missing'] + ['--before', 'unused'] * 101
        with patch.object(sys, 'argv', args), patch.object(comparison, 'configure_utf8_stdio'), \
             patch.object(comparison, '_read', side_effect=AssertionError('read before count check')), \
             patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit) as stopped:
            comparison.main()
        self.assertEqual(stopped.exception.code, 1)
        with self.assertRaises(ValueError):
            comparison.compare(plan(), after=[None] * 101)
        a = observation(plan()['specs'][0], ['11'])
        size = len(comparison.canonical_json_bytes(dict(plan=plan(), before=[a], after=[a])))
        with patch.object(partition, 'MAX_BYTES', size - 1), patch.object(partition, 'review') as replay:
            with self.assertRaises(ValueError):
                comparison.compare(plan(), [a], [a])
            replay.assert_not_called()

    def test_cli_create_replay_and_exclusive_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            value = plan()
            paths = [folder / name for name in ('계획.json', 'before.json', 'after.json')]
            items = [value, observation(value['specs'][0], []), observation(value['specs'][0], ['17'])]
            for path, item in zip(paths, items):
                path.write_bytes(json.dumps(item).encode('utf-8'))
            saved = {path: path.read_bytes() for path in paths}
            target = folder / 'comparison.json'
            def run(*args):
                return subprocess.run([sys.executable, str(ROOT / 'pubmed_partition_compare.py'), *map(str, args)],
                                      cwd=folder, capture_output=True, timeout=20)
            sides = ['--before', paths[1], '--after', paths[2]]
            result = run('compare', paths[0], *sides, '--output', target)
            self.assertEqual((result.returncode, result.stderr), (0, b''))
            raw = target.read_bytes()
            self.assertEqual(raw, result.stdout)
            result = run('verify', paths[0], target, *sides)
            self.assertEqual((result.returncode, result.stderr), (0, b''))
            self.assertTrue(json.loads(result.stdout)['valid'])
            for args in (('compare', paths[0], *sides, '--output', target),
                         ('verify', paths[0], target, '--after', paths[2]),
                         ('compare', paths[0], '--after', folder / 'private-input')):
                failed = run(*args)
                self.assertEqual((failed.returncode, failed.stdout), (1, b''))
                self.assertNotIn(b'private-input', failed.stderr)
                self.assertNotIn(b'Traceback', failed.stderr)
            self.assertEqual(target.read_bytes(), raw)
            self.assertEqual({path: path.read_bytes() for path in paths}, saved)
            self.assertEqual(set(folder.iterdir()), {*paths, target})

    def test_cli_text_summary_escapes_request_id_and_still_saves_replayable_json(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            value = plan()
            a, b = value['specs']
            a['request_id'] = 'fictional\nline\u202e'
            paths = [folder / name for name in ('plan', 'before', 'after')]
            for path, item in zip(paths, (value, observation(a, []), observation(a, ['19']))):
                path.write_bytes(comparison.canonical_json_bytes(item))
            output = folder / 'comparison.json'
            result = subprocess.run([sys.executable, str(ROOT / 'pubmed_partition_compare.py'), 'compare',
                                     str(paths[0]), '--before', str(paths[1]), '--after', str(paths[2]),
                                     '--text', '--output', str(output)], cwd=folder, capture_output=True, timeout=20)
            self.assertEqual((result.returncode, result.stderr), (0, b''))
            text = result.stdout.decode('utf-8')
            self.assertIn(r'"fictional\nline\u202e"', text)
            self.assertIn('before: reported=0, occurrences=0', text)
            self.assertIn('Changed PMIDs: after_only=1', text)
            self.assertIn('PMID positions: unavailable', text)
            self.assertIn('before: missing', text)
            self.assertNotIn('fictional\nline', text)
            self.assertTrue(comparison.verify(value, json.loads(output.read_bytes()),
                                              [observation(a, [])], [observation(a, ['19'])])['valid'])
