"""Explicit synthetic offline windows; no PubMed requests."""
import copy
import json
import io
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pubmed_partition as p
import pubmed_discovery as d
from tests.test_pubmed_discovery import spec, native, attempt, artifact

ROOT = Path(__file__).resolve().parents[1]


def plan():
    dates = dict(datetype='pdat', mindate='2024/02/28', maxdate='2024/03/01')
    a = spec(request_id='a', date_filter={**dates, 'maxdate': '2024/02/29'})
    b = spec(request_id='b', date_filter={**dates, 'mindate': '2024/03/01'})
    return dict(schema_version=1, query=a['query'], date_filter=dates, specs=[a, b])


def observation(s, ids, count=None, stop='reported_count_reached'):
    return artifact(s, [attempt(s, native(ids, count))], stop)


class PartitionTests(unittest.TestCase):
    def test_existing_products_engine_examples_schemas_and_workflows_unchanged(self):
        proof = json.loads((ROOT / 'tests/pubmed_partition_prior_bytes.json').read_bytes())
        paths = [*ROOT.glob('*.py'), *(ROOT / 'examples').rglob('*'),
                 *(ROOT / 'schemas').rglob('*'), *(ROOT / '.github').rglob('*')]
        observed = {path.relative_to(ROOT).as_posix(): path for path in paths if path.is_file()}
        self.assertEqual(set(observed), set(proof) | {'pubmed_partition.py'})
        for name, digest in proof.items():
            self.assertEqual(hashlib.sha256(observed[name].read_bytes()).hexdigest(), digest, name)
        import research_bundle
        self.assertNotIn('pubmed_partition.py', research_bundle.ENGINE_FILES)

    def test_calendar_and_replay_preserve_duplicates_without_authority(self):
        value = plan()
        records = [observation(value['specs'][0], ['11', '12']), observation(value['specs'][1], ['12'])]
        before = copy.deepcopy((value, records))
        with patch.object(d, '_transport', side_effect=AssertionError('network forbidden')):
            report = p.review(value, records)
            self.assertTrue(p.verify(value, report, list(reversed(records)))['valid'])
        self.assertEqual((value, records), before)
        self.assertTrue(report['calendar']['exact_nonoverlapping_partition'])
        self.assertEqual(report['observed_occurrence_count'], 3)
        self.assertEqual(report['observed_unique_pmid_count'], 2)
        self.assertEqual(report['repeated_pmids'][0]['pmid'], '12')
        self.assertTrue(report['repeated_pmids'][0]['crosses_windows'])
        self.assertEqual([r['occurrence']['pmid'] for r in report['occurrences']], ['11', '12', '12'])
        for name in ('census', 'search_completeness'):
            self.assertEqual(report[name], 'NOT_ESTABLISHED')
        self.assertEqual(report['conclusion'], 'NOT_READY')
        self.assertEqual(report['external_calls'], 0)

    def test_gaps_overlaps_outside_and_extreme_calendar(self):
        value = plan()
        value['specs'][0]['date_filter']['maxdate'] = '2024/02/28'
        self.assertEqual(p.review(value)['calendar']['gaps'], [dict(mindate='2024/02/29', maxdate='2024/02/29')])
        value['specs'][1]['date_filter']['mindate'] = '2024/02/28'
        value['specs'][0]['date_filter']['mindate'] = '2024/02/27'
        result = p.review(value)['calendar']
        self.assertFalse(result['exact_nonoverlapping_partition'])
        self.assertTrue(result['covers_outer_calendar'])
        self.assertEqual(result['outside_request_ids'], ['a'])
        self.assertEqual(result['overlaps'][0]['mindate'], '2024/02/28')
        for date in ('0001/01/01', '9999/12/31'):
            dates = dict(datetype='mdat', mindate=date, maxdate=date)
            value['date_filter'] = dates
            value['specs'] = [spec(date_filter=dates)]
            self.assertTrue(p.review(value)['calendar']['exact_nonoverlapping_partition'])

    def test_missing_zero_capped_single_day_and_count_drift(self):
        value = plan()
        missing = p.review(value)
        self.assertEqual(missing['supplied_window_count'], 0)
        self.assertFalse(missing['all_supplied_counts_accounted_for'])
        a = observation(value['specs'][0], [])
        partial = p.review(value, [a])
        self.assertTrue(partial['all_supplied_counts_accounted_for'])
        self.assertFalse(partial['all_windows_supplied'])
        s = value['specs'][1]
        s['max_records'] = 2
        b = observation(s, ['21', '22'], count=10001, stop='max_records')
        report = p.review(value, [a, b])
        self.assertTrue(report['windows'][1]['reported_count_exceeds_local_record_cap'])
        self.assertTrue(report['windows'][1]['reported_count_exceeds_pubmed_10000_limit'])
        self.assertFalse(report['all_supplied_counts_accounted_for'])
        s['max_records'] = 6
        drift = artifact(s, [attempt(s, native(['21', '22'], 4)),
                             attempt(s, native(['23'], 3, 2), 2)], 'reported_count_changed')
        result = p.review(value, [drift])
        self.assertEqual(result['windows'][1]['stop_reason'], 'reported_count_changed')
        self.assertEqual([r['count'] for r in result['windows'][1]['pages']], [4, 3])

    def test_exact_spec_artifact_and_report_bindings(self):
        value = plan()
        a = observation(value['specs'][0], ['11'])
        for records in ([a, a], [observation(spec(), ['11'])]):
            with self.assertRaises(ValueError): p.review(value, records)
        for change in ('query', 'max_records', 'page_size', 'date_filter'):
            changed = copy.deepcopy(a['spec'])
            if change == 'query': changed[change] += ' different'
            elif change == 'date_filter': changed[change]['maxdate'] = '2024/03/01'
            else: changed[change] += 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.review(value, [observation(changed, ['11'])])
        bad = copy.deepcopy(a)
        bad['derived']['occurrences'][0]['pmid'] = '99'
        with self.assertRaises(ValueError): p.review(value, [bad])
        report = p.review(value, [a])
        for key, new in [('external_calls', False), ('conclusion', 'READY'), ('observed_unique_pmid_count', 999)]:
            bad = copy.deepcopy(report); bad[key] = new
            with self.assertRaises(ValueError): p.verify(value, bad, [a])
        with self.assertRaises(ValueError): p.verify(value, report)

    def test_strict_plan_and_bounds(self):
        for change in ({'schema_version': True}, {'extra': 1}, {'specs': []}, {'specs': [spec()]},
                       {'date_filter': None}, {'specs': plan()['specs'] * 51}):
            with self.subTest(change=change), self.assertRaises(ValueError): p.review({**plan(), **change})
        value = plan()
        value['specs'][1]['request_id'] = 'a'
        with self.assertRaises(ValueError): p.review(value)
        value = plan(); value['specs'][0]['max_records'] = 1001
        with self.assertRaises(ValueError): p.review(value)
        value = plan(); value['specs'][0]['date_filter']['mindate'] = '2023/02/29'
        with self.assertRaises(ValueError): p.review(value)
        with patch.object(p, 'MAX_BYTES', 16), self.assertRaises(ValueError): p.review(plan())
        with self.assertRaises(ValueError): p.review(plan(), [None] * 101)

    def test_byte_bounds_parse_order_output_preflight_and_translation(self):
        value = plan()
        a = observation(value['specs'][0], ['11'])
        b = artifact(value['specs'][1], [attempt(value['specs'][1],
                     native(['12'], querytranslation='different supplied translation'))], 'reported_count_reached')
        self.assertTrue(p.review(value, [a, b])['differing_supplied_query_translations'])
        report = p.review(value, [a])
        size = len(p.canonical_json_bytes(report))
        with patch.object(p, 'MAX_BYTES', size):
            self.assertEqual(p._bounded(report), p.canonical_json_bytes(report))
        with patch.object(p, 'MAX_BYTES', size - 1), self.assertRaises(ValueError):
            p._bounded(report)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.json'
            path.write_bytes(b' ' * 33)
            with patch.object(sys, 'argv', ['pubmed_partition.py', 'review', str(path)]), \
                 patch.object(p, 'MAX_BYTES', 32), patch.object(p, 'parse_json') as parse, \
                 patch.object(p, 'configure_utf8_stdio'), patch('sys.stderr', new_callable=io.StringIO), \
                 self.assertRaises(SystemExit) as stopped:
                p.main()
            self.assertEqual(stopped.exception.code, 1)
            parse.assert_not_called()
            path.write_bytes(p.canonical_json_bytes(value))
            link = Path(temp) / 'existing-link'
            try:
                link.symlink_to(Path(temp) / 'not-created')
            except (OSError, NotImplementedError):
                return  # Native Windows may not grant symlink creation.
            with patch.object(sys, 'argv', ['pubmed_partition.py', 'review', str(path), '--output', str(link)]), \
                 patch.object(p, 'configure_utf8_stdio'), patch.object(p, 'parse_json') as parse, \
                 patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit):
                p.main()
            parse.assert_not_called()
            self.assertFalse((Path(temp) / 'not-created').exists())

    def test_actual_cli_exclusive_output_failure_and_no_input_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            value = plan(); data = observation(value['specs'][0], ['11'])
            source, discovery, output = (folder / n for n in ('계획.json', 'discovery.json', 'report.json'))
            source.write_bytes(json.dumps(value).encode())
            discovery.write_bytes(json.dumps(data).encode())
            originals = (source.read_bytes(), discovery.read_bytes())
            def run(*args):
                return subprocess.run([sys.executable, str(ROOT / 'pubmed_partition.py'), *map(str, args)],
                                      capture_output=True, timeout=15)
            args = ('review', source, '--discovery', discovery, '--output', output)
            completed = run(*args)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout), json.loads(output.read_bytes()))
            checked = run('verify', source, output, '--discovery', discovery)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)['valid'])
            before = output.read_bytes()
            for args in (args, ('verify', source, output), ('review', source, '--discovery', folder / 'SECRET-missing.json')):
                failed = run(*args)
                self.assertEqual(failed.returncode, 1)
                self.assertEqual(failed.stdout, b'')
                self.assertNotIn(b'SECRET', failed.stderr)
                self.assertNotIn(b'Traceback', failed.stderr)
                self.assertEqual(output.read_bytes(), before)
            self.assertEqual((source.read_bytes(), discovery.read_bytes()), originals)
            self.assertEqual(run('fetch', source).returncode, 2)


if __name__ == '__main__':
    unittest.main()
