"""Synthetic offline coverage. Never invokes an external service."""
import base64
import copy
import errno
import http.client
import io
import json
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import bibliographic_intake
import pubmed_discovery as p

ROOT = Path(__file__).resolve().parents[1]
STAMP = '2026-01-01T00:00:00+00:00'


def spec(**changes):
    result = dict(schema_version=1, request_id='synthetic-discovery', query='fictional mechanism', sort='pub_date',
                  date_filter=None, page_size=2, max_records=6, max_requests=3)
    result.update(changes)
    return result


def native(ids, count=None, offset=0, **extra):
    result = dict(count=str(len(ids) if count is None else count), retstart=str(offset), retmax=str(len(ids)),
                  idlist=ids, querytranslation='fictional mechanism')
    result.update(extra)
    return json.dumps(dict(esearchresult=result)).encode()


def attempt(s, raw, offset=0, status=200, error=None, complete=True):
    return dict(parameters=p.parameters(s, offset, s['max_records'] - offset), status=status,
                headers={'content-type': 'application/json'}, started_at=STAMP, elapsed_seconds=0.1,
                body_base64=base64.b64encode(raw).decode(), body_complete=complete, error=error)


def artifact(s, records, stop):
    return p.from_responses(s, dict(started_at=STAMP, attempts=records, stop_reason=stop))


def protocol(s):
    base = json.loads((ROOT / 'examples/bibliographic-base.json').read_text())
    dates = s['date_filter']
    window = 'query_defined' if dates is None else dates['datetype'] + ':' + dates['mindate'] + '..' + dates['maxdate']
    base['search_plan'] = [dict(search_id='discovery-primary', source='pubmed', query=s['query'], window=window)]
    return base


class FakeResponse(io.BytesIO):
    def __init__(self, raw, code=200, headers=None):
        super().__init__(raw)
        self.code = code
        self.headers = headers or {'Content-Type': 'application/json'}


class DiscoveryTests(unittest.TestCase):
    def test_strict_spec_preview_and_changed_digest(self):
        s = spec()
        with patch.object(p, '_transport', side_effect=AssertionError('network')):
            preview = p.preview(s)
            self.assertEqual(preview['external_calls'], 0)
            with self.assertRaises(ValueError):
                p.fetch(spec(query='changed'), preview['preview_sha256'])
        for change in ({'page_size': True}, {'max_records': 1001}, {'max_requests': 11}, {'sort': 'relevance'},
                       {'date_filter': {'datetype': 'pdat', 'mindate': '2026/02/30', 'maxdate': '2026/03/01'}},
                       {'query': ' '}, {'query': 'x' * 4001}, {'email': 'example' + '@' + 'example.test'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.preview(spec(**change))

    def test_paging_and_zero_hit_and_regeneration(self):
        s = spec()
        a = artifact(s, [attempt(s, native(['11', '12'], 3)), attempt(s, native(['13'], 3, 2), 2)], 'reported_count_reached')
        self.assertTrue(p.verify(a)['valid'])
        self.assertEqual([r['pmid'] for r in a['derived']['occurrences']], ['11', '12', '13'])
        self.assertEqual(a['search_completeness'], 'NOT_ESTABLISHED')
        self.assertEqual(a['conclusion'], 'NOT_READY')
        z = artifact(s, [attempt(s, native([]))], 'reported_count_reached')
        self.assertTrue(z['derived']['observed_reported_count_accounted_for'])
        with self.assertRaisesRegex(ValueError, 'zero-hit discovery'):
            p.to_intake(z, protocol(s), 'discovery-primary')
        changed = copy.deepcopy(a)
        changed['derived']['occurrences'][0]['pmid'] = '999'
        with self.assertRaises(ValueError):
            p.verify(changed)

    def test_partial_budget_and_absolute_limit(self):
        for s, stop in [(spec(max_records=2), 'max_records'), (spec(max_requests=1), 'max_requests')]:
            a = artifact(s, [attempt(s, native(['11', '12'], 10001))], stop)
            self.assertTrue(a['derived']['reported_count_exceeds_pubmed_10000_limit'])
            self.assertFalse(a['derived']['observed_reported_count_accounted_for'])
        a = artifact(spec(), [], 'elapsed_limit')
        with self.assertRaises(ValueError):
            p.to_intake(a, protocol(spec()), 'discovery-primary')

    def test_diagnostic_pages_preserve_occurrences(self):
        s = spec()
        first = attempt(s, native(['11', '12'], 4))
        cases = [(native(['13', '14'], 5, 2), 'reported_count_changed'),
                 (native(['13', '14'], 4, 2, querytranslation='changed'), 'query_translation_changed'),
                 (native(['12', '14'], 4, 2), 'duplicate_or_paging_overlap'),
                 (native(['13'], 4, 2), 'count_or_page_length_mismatch'),
                 (native(['13', '14'], 4, 3), 'unexpected_offset')]
        for raw, stop in cases:
            with self.subTest(stop=stop):
                a = artifact(s, [first, attempt(s, raw, 2)], stop)
                self.assertGreaterEqual(len(a['derived']['occurrences']), 3)
                self.assertTrue(p.verify(a)['valid'])
        duplicate = artifact(s, [attempt(s, native(['11', '11'], 2))], 'duplicate_or_paging_overlap')
        intake = p.to_intake(duplicate, protocol(s), 'discovery-primary')
        self.assertEqual(len(intake['parsed_export']['record_rows']), 2)
        self.assertTrue(intake['parsed_export']['duplicate_record_ids'])

    def test_error_shapes_and_stop_rules(self):
        s = spec()
        for raw, stop in [(b'{"error":"API rate limit exceeded"}', 'provider_error'),
                          (b'<html>challenge</html>', 'malformed_response'),
                          (b'\xff', 'malformed_response'),
                          (b'{"error":null,"error":null}', 'malformed_response'),
                          (native([], errorlist={'phrasesnotfound': ['fictional']}), 'provider_error_or_warning'),
                          (native(['11'], 0), 'count_or_page_length_mismatch'),
                          (native(['11', '12', '13'], 3), 'retmax_or_list_mismatch')]:
            with self.subTest(stop=stop):
                a = artifact(s, [attempt(s, raw)], stop)
                self.assertFalse(a['derived']['observed_reported_count_accounted_for'])
        for status in (301, 401, 403, 407, 429, 500):
            a = artifact(s, [attempt(s, b'synthetic error', status=status)], 'http_status')
            with self.assertRaises(ValueError):
                p.to_intake(a, protocol(s), 'discovery-primary')
        artifact(s, [attempt(s, native([], warninglist={}, errorlist=[]))], 'reported_count_reached')
        warning_only = artifact(s, [attempt(s, native([], warninglist={'outputmessages': ['synthetic warning']}))], 'provider_error_or_warning')
        with self.assertRaises(ValueError):
            p.to_intake(warning_only, protocol(s), 'discovery-primary')
        with self.assertRaises(ValueError):
            artifact(s, [attempt(s, native([])), attempt(s, native([]))], 'reported_count_reached')

    def test_conversion_provenance_and_exact_plan(self):
        s = spec(date_filter=dict(datetype='pdat', mindate='2020/01/01', maxdate='2026/01/01'))
        a = artifact(s, [attempt(s, native(['11'], 1))], 'reported_count_reached')
        original = protocol(s)
        snapshot = copy.deepcopy(original)
        intake = p.to_intake(a, original, 'discovery-primary')
        self.assertEqual(original, snapshot)
        self.assertTrue(bibliographic_intake.verify(intake)['valid'])
        text = intake['source_export']['text']
        self.assertIn(p.digest(a), text)
        self.assertIn(s['request_id'], text)
        self.assertIn(a['derived']['occurrences'][0]['response_sha256'], text)
        for key, value in [('window', '2020-2026'), ('query', 'changed'), ('source', 'other'), ('extra_filter', 'extra')]:
            changed = copy.deepcopy(original)
            changed['search_plan'][0][key] = value
            with self.assertRaises(ValueError):
                p.to_intake(a, changed, 'discovery-primary')

    def test_real_urllib_setup_safe_headers_and_redirects(self):
        s = spec()
        calls = []
        response = FakeResponse(native([]), headers={'Content-Type': 'application/json', 'Set-Cookie': 'secret', 'Authorization': 'secret'})
        def fake_open(opener, request, timeout):
            calls.append((opener, request, timeout))
            return response
        with patch.object(urllib.request.OpenerDirector, 'open', fake_open):
            record = p._transport(p.parameters(s, 0, 6), 10)
        opener, request, timeout = calls[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertTrue(request.full_url.startswith(p.ENDPOINT + '?'))
        self.assertIn('term=fictional+mechanism', request.full_url)
        self.assertEqual(record['headers'], {'content-type': 'application/json'})
        handlers = opener.handlers
        https = next(h for h in handlers if isinstance(h, urllib.request.HTTPSHandler))
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(https._context.check_hostname)
        self.assertTrue(any(isinstance(h, p._NoRedirect) for h in handlers))
        self.assertIsNone(p._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.test'))
        self.assertFalse(any(isinstance(h, urllib.request.HTTPBasicAuthHandler) for h in handlers))

    def test_transport_error_body_caps_and_partial(self):
        params = p.parameters(spec(), 0, 6)
        for response, expected in [(FakeResponse(b'x' * (p.MAX_BODY_BYTES + 1)), 'body_too_large'),
                                   (FakeResponse(b'abc', headers={'Content-Length': '5'}), 'incomplete_body')]:
            with patch.object(urllib.request.OpenerDirector, 'open', return_value=response):
                record = p._transport(params, 10)
            self.assertEqual(record['error'], expected)
            self.assertFalse(record['body_complete'])
            self.assertLessEqual(len(base64.b64decode(record['body_base64'])), p.MAX_BODY_BYTES)
        for failure, expected in [(TimeoutError('secret'), 'timeout'), (urllib.error.URLError(ssl.SSLError('secret')), 'tls_error'),
                                  (urllib.error.URLError('secret'), 'network_error')]:
            with patch.object(urllib.request.OpenerDirector, 'open', side_effect=failure):
                record = p._transport(params, 10)
            self.assertEqual(record['error'], expected)
            self.assertNotIn('secret', json.dumps(record))
        response = FakeResponse(b'')
        response.read1 = lambda n: (_ for _ in ()).throw(http.client.IncompleteRead(b'partial'))
        with patch.object(urllib.request.OpenerDirector, 'open', return_value=response):
            record = p._transport(params, 10)
        self.assertEqual(base64.b64decode(record['body_base64']), b'partial')
        failure = urllib.error.HTTPError(p.ENDPOINT, 429, 'secret', {'Retry-After': '10', 'Set-Cookie': 'secret'}, io.BytesIO(b'error'))
        with patch.object(urllib.request.OpenerDirector, 'open', side_effect=failure):
            record = p._transport(params, 10)
        self.assertEqual(record['status'], 429)
        self.assertEqual(record['headers'], {'retry-after': '10'})
        self.assertEqual(base64.b64decode(record['body_base64']), b'error')

    def test_fetch_injected_rate_and_no_retries(self):
        s = spec()
        timer = [0.0]
        starts = []
        def transport(params, timeout):
            starts.append(timer[0])
            offset = int(params['retstart'])
            return attempt(s, native(['11', '12'] if offset == 0 else ['13'], 3, offset), offset)
        def sleep(seconds):
            timer[0] += seconds
        with patch.object(p, '_utcnow', return_value=STAMP), patch.object(p, '_LAST_REQUEST', None), patch.object(p.time, 'monotonic', side_effect=lambda: timer[0]), patch.object(p.time, 'sleep', side_effect=sleep):
            a = p.fetch(s, p.preview(s)['preview_sha256'], transport=transport)
        self.assertEqual(starts, [0.0, 1.0])
        self.assertEqual(a['derived']['stop_reason'], 'reported_count_reached')
        with patch.object(p, '_utcnow', return_value=STAMP), patch.object(p, '_LAST_REQUEST', None), patch.object(p, '_transport', return_value=attempt(s, b'', status=429)) as fake:
            a = p.fetch(s, p.preview(s)['preview_sha256'])
        self.assertEqual(fake.call_count, 1)
        self.assertEqual(a['derived']['stop_reason'], 'http_status')

    def test_elapsed_deadlines_and_oversleep(self):
        s = spec()
        record = attempt(s, native([]))
        record['elapsed_seconds'] = 99_999_999
        with self.assertRaisesRegex(ValueError, 'time bound'):
            artifact(s, [record], 'reported_count_reached')
        record['error'] = 'timeout'
        self.assertEqual(artifact(s, [record], 'timeout')['derived']['stop_reason'], 'timeout')
        record = attempt(s, native([]))
        record['started_at'] = '2026-01-01T00:00:59+00:00'
        record['elapsed_seconds'] = 2
        with self.assertRaisesRegex(ValueError, 'time bound'):
            artifact(s, [record], 'reported_count_reached')
        timer = [0.0]
        def oversleep(seconds):
            timer[0] += 61
        with patch.object(p, '_utcnow', return_value=STAMP), patch.object(p, '_LAST_REQUEST', 0.0), patch.object(p.time, 'monotonic', side_effect=lambda: timer[0]), patch.object(p.time, 'sleep', side_effect=oversleep), patch.object(p, '_transport') as transport:
            a = p.fetch(s, p.preview(s)['preview_sha256'])
        transport.assert_not_called()
        self.assertEqual(a['derived']['stop_reason'], 'elapsed_limit')

    def _assert_cli_output_preflight(self, dangling=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / 'spec.json'
            input_path.write_text(json.dumps(spec()))
            output = root / 'output.json'
            if dangling:
                try:
                    output.symlink_to(root / 'absent')
                except NotImplementedError:
                    self.skipTest('symlink creation unavailable')
                except OSError as error:
                    if getattr(error, 'winerror', None) in (50, 1314) or error.errno in (errno.ENOSYS, errno.ENOTSUP):
                        self.skipTest('symlink creation unsupported or requires Windows privilege')
                    raise
            else:
                output.write_text('untouched')
            with patch.object(sys, 'argv', ['pubmed_discovery.py', 'fetch', str(input_path), '--preview-sha256', p.preview(spec())['preview_sha256'], '--output', str(output)]), patch.object(p, 'fetch', side_effect=AssertionError('must not fetch')), patch('sys.stderr', new=io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    p.main()
                self.assertEqual(raised.exception.code, 1)
            if dangling:
                self.assertTrue(output.is_symlink())
                self.assertFalse((root / 'absent').exists())
            else:
                self.assertEqual(output.read_text(), 'untouched')

    def test_cli_existing_output_preflight_before_network(self):
        self._assert_cli_output_preflight()

    def test_cli_dangling_output_preflight_before_network(self):
        self._assert_cli_output_preflight(dangling=True)


if __name__ == '__main__':
    unittest.main()
