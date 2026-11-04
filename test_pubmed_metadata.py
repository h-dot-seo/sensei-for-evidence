"""Synthetic offline acquisition coverage. Never invokes an external service."""
import base64
import copy
import csv
import hashlib
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
import urllib.parse
import urllib.request

import bibliographic_intake
from evidence_workflow import run
import pubmed_discovery as discovery
import pubmed_metadata as p

ROOT = Path(__file__).resolve().parent
STAMP = '2026-01-01T01:00:00+00:00'


def discovery_artifact(ids=('11', '12', '13')):
    s = dict(schema_version=1, request_id='synthetic-discovery', query='fictional mechanism', sort='pub_date',
             date_filter=None, page_size=min(100, len(ids) or 1), max_records=max(1, len(ids)), max_requests=1)
    raw = json.dumps(dict(esearchresult=dict(count=str(len(ids)), retstart='0', retmax=str(len(ids)),
                     idlist=list(ids), querytranslation=s['query']))).encode()
    record = dict(parameters=discovery.parameters(s, 0, s['max_records']), status=200, headers={},
                  started_at='2026-01-01T00:00:00+00:00', elapsed_seconds=0.1,
                  body_base64=base64.b64encode(raw).decode(), body_complete=True, error=None)
    stop = 'duplicate_or_paging_overlap' if len(set(ids)) != len(ids) else 'reported_count_reached'
    return discovery.from_responses(s, dict(started_at=record['started_at'], attempts=[record], stop_reason=stop))


def selection(**changes):
    result = dict(schema_version=1, request_id='synthetic-metadata', occurrence_indices=[0, 2], batch_size=20, max_requests=1)
    result.update(changes)
    return result


def native(pmids):
    return b'\n'.join(('PMID- ' + pmid + '\nTI  - Fictional candidate ' + pmid + '.\n').encode() for pmid in pmids)


def attempt(pmids, raw=None, **changes):
    result = dict(parameters=p.parameters(pmids), status=200, headers={'content-type': 'text/plain'},
                  started_at=STAMP, elapsed_seconds=0.1, body_base64=base64.b64encode(native(pmids) if raw is None else raw).decode(),
                  body_complete=True, error=None)
    result.update(changes)
    return result


def artifact(records, stop='selected_ids_received', source=None, choice=None):
    return p.from_responses(source or discovery_artifact(), choice or selection(),
        dict(started_at=STAMP, attempts=records, stop_reason=stop))


def protocol(source=None):
    source = source or discovery_artifact()
    value = json.loads((ROOT / 'examples/bibliographic-base.json').read_text())
    dates = source['spec']['date_filter']
    window = 'query_defined' if dates is None else dates['datetype'] + ':' + dates['mindate'] + '..' + dates['maxdate']
    value['search_plan'] = [dict(search_id='discovery-primary', source='pubmed', query=source['spec']['query'], window=window)]
    return value


class FakeResponse(io.BytesIO):
    def __init__(self, raw, code=200, headers=None):
        super().__init__(raw)
        self.code = code
        self.headers = headers or {'Content-Type': 'text/plain'}


class MetadataTests(unittest.TestCase):
    def test_preview_explicit_exact_selection_and_digest(self):
        source = discovery_artifact()
        choice = selection(occurrence_indices=[2, 0])
        before = copy.deepcopy((source, choice))
        result = p.preview(source, choice)
        self.assertEqual(result['request_batches'][0]['parameters'],
                         {'db': 'pubmed', 'rettype': 'medline', 'retmode': 'text', 'id': '13,11'})
        self.assertEqual([row['discovery_occurrence']['occurrence_index'] for row in result['selected_occurrences']], [2, 0])
        self.assertEqual(result['discovery_sha256'], p.digest(source))
        self.assertEqual(result['external_calls'], 0)
        self.assertEqual((source, choice), before)
        self.assertLessEqual(result['max_response_bytes'], 1_000_000)
        self.assertLessEqual(result['max_artifact_bytes'], 50_000_000)
        for name in ('pubmed_metadata.py', 'pubmed_discovery.py', 'nbib_export_parser.py', 'json_io.py'):
            self.assertIn(name, result['implementation_sha256'])
        with patch.object(p, '_transport', side_effect=AssertionError('network')):
            for altered in (selection(occurrence_indices=[0, 1]), selection(request_id='changed')):
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    p.fetch(source, altered, result['preview_sha256'])
            with self.assertRaises(ValueError):
                p.fetch(source, choice, True)
        changed = copy.deepcopy(source)
        changed['derived']['occurrences'][0]['pmid'] = '99'
        with self.assertRaises(ValueError):
            p.preview(changed, choice)

    def test_selection_strict_schema_and_bounds(self):
        source = discovery_artifact()
        changes = [dict(occurrence_indices=[]), dict(occurrence_indices=[0, 0]), dict(occurrence_indices=[True]),
                   dict(occurrence_indices=[-1]), dict(occurrence_indices=[3]), dict(occurrence_indices=['0']),
                   dict(occurrence_indices=(0,)), dict(batch_size=True), dict(batch_size=0), dict(batch_size=21),
                   dict(max_requests=0), dict(max_requests=11), dict(schema_version=True), dict(request_id=' '),
                   dict(request_id='a' * 201), dict(request_id='a\x00b'), dict(api_key='never'), dict(request_id='\ud800')]
        for changed in changes:
            with self.subTest(change=changed), self.assertRaises(ValueError):
                p.preview(source, selection(**changed))
        with self.assertRaises(ValueError):
            p.preview(discovery_artifact(()), selection(occurrence_indices=[0]))
        cycle = selection()
        cycle['occurrence_indices'] = [cycle]
        with self.assertRaises(ValueError):
            p.preview(source, cycle)

    def test_reordered_ids_raw_spans_fields_and_abstract_derivatives(self):
        raw = b'\xef\xbb\xbfPMID- 13\r\nTI  - First title\r\n      second line\r\nAB  - First abstract\r\n      second line\r\nAB  - Repeated abstract.\r\n\r\nPMID- 11\nTI  - Other.\n'
        a = artifact([attempt(['11', '13'], raw)])
        self.assertTrue(p.verify(a)['valid'])
        self.assertEqual(a['derived']['responses'][0]['returned_pmids'], ['13', '11'])
        self.assertTrue(a['derived']['responses'][0]['reconciliation']['exact_literal_id_match'])
        candidates = a['derived']['candidates']
        self.assertEqual([row['pmid'] for row in candidates], ['13', '11'])
        self.assertEqual(candidates[0]['title_fields'], [dict(field_index=1, unfolded_text='First title second line')])
        self.assertEqual([row['unfolded_text'] for row in candidates[0]['abstract_fields']], ['First abstract second line', 'Repeated abstract.'])
        self.assertEqual(candidates[1]['abstract_status'], 'NOT_PRESENT')
        self.assertEqual(candidates[1]['abstract_fields'], [])
        self.assertEqual([row['candidate_id'] for row in a['derived']['selected_occurrence_mapping']],
                         [candidates[1]['candidate_id'], candidates[0]['candidate_id']])
        self.assertEqual(a['derived']['mapped_selected_occurrence_count'], 2)
        response = a['derived']['responses'][0]
        self.assertEqual(response['response_sha256'], hashlib.sha256(raw).hexdigest())
        parsed = response['parsed_export']
        self.assertTrue(parsed['initial_utf8_bom'])
        self.assertTrue(parsed['ignored_blank_spans'])
        for row in parsed['records']:
            for value in [row] + row['fields']:
                span = value['source_span']
                part = raw[span['byte_start']:span['byte_end']]
                self.assertEqual(value['raw_text'].encode(), part)
                self.assertEqual(span['sha256'], hashlib.sha256(part).hexdigest())
        self.assertEqual(base64.b64decode(a['execution']['attempts'][0]['body_base64']), raw)

    def test_repeated_discovery_pmid_maps_every_selected_occurrence(self):
        source = discovery_artifact(('11', '11', '13'))
        choice = selection(occurrence_indices=[1, 2, 0])
        preview = p.preview(source, choice)
        self.assertEqual(preview['request_batches'][0]['parameters']['id'], '11,13')
        self.assertEqual(preview['literal_pmid_groups'][0]['selected_occurrence_indices'], [1, 0])
        a = artifact([attempt(['11', '13'], native(['13', '11']))], source=source, choice=choice)
        self.assertEqual(a['derived']['received_native_record_count'], 2)
        self.assertEqual(a['derived']['mapped_selected_occurrence_count'], 3)
        self.assertEqual(a['derived']['candidates'][1]['selected_discovery_occurrence_indices'], [1, 0])
        mapping = a['derived']['selected_occurrence_mapping']
        self.assertEqual([row['discovery_occurrence']['occurrence_index'] for row in mapping], [1, 2, 0])
        self.assertEqual(mapping[0]['candidate_id'], mapping[2]['candidate_id'])
        intake = p.to_intake(a, protocol(source), 'discovery-primary')
        rows = intake['parsed_export']['record_rows']
        self.assertEqual(len(rows), 2)
        self.assertFalse(intake['parsed_export']['duplicate_record_ids'])
        self.assertEqual(json.loads(rows[1]['original_values']['selected_discovery_occurrence_indices_json']), [1, 0])

    def test_missing_extra_duplicate_and_literal_nonpositional_reconciliation(self):
        for ids, stop in [(['11'], 'missing_returned_pmid'), (['11', '13', '14'], 'unexpected_returned_pmid'),
                          (['11', '13', '13'], 'duplicate_returned_pmid'), (['011', '13'], 'unexpected_returned_pmid')]:
            with self.subTest(ids=ids):
                a = artifact([attempt(['11', '13'], native(ids))], stop)
                response = a['derived']['responses'][0]
                self.assertEqual(response['returned_pmids'], ids)
                self.assertEqual(len(response['parsed_export']['records']), len(ids))
                self.assertFalse(response['reconciliation']['exact_literal_id_match'])
                self.assertEqual(a['derived']['candidates'], [])
                self.assertTrue(all(row['metadata_status'] == 'RESPONSE_DIAGNOSTIC' for row in a['derived']['selected_occurrence_mapping']))
                self.assertTrue(p.verify(a)['valid'])
                with self.assertRaisesRegex(ValueError, 'no fully reconciled'):
                    p.to_intake(a, protocol(), 'discovery-primary')

    def test_only_complete_success_is_parsed_and_native_errors_retained(self):
        cases = [(attempt(['11', '13'], b'<html>provider error</html>'), 'unsupported_native_response'),
                 (attempt(['11', '13'], b'PMID- 11\nTI  - x\nPMID- 13\n'), 'unsupported_native_response'),
                 (attempt(['11', '13'], b'PMID- 11\nAB - bad padding\n'), 'unsupported_native_response'),
                 (attempt(['11', '13'], b'PMID- 11\nTI  - \xff'), 'unsupported_native_response'),
                 (attempt(['11', '13'], b''), 'unsupported_native_response'),
                 (attempt(['11', '13'], b'PMID- 11\nTI  - \x00'), 'unsupported_native_response'),
                 (attempt(['11', '13'], b'\n' * (p.MAX_PARSE_LINES + 1)), 'native_expansion_limit'),
                 (attempt(['11', '13'], b'PMID- 11\n' + b'TI  - x\n' * p.MAX_PARSE_FIELDS), 'native_expansion_limit'),
                 (attempt(['11', '13'], native(['11'] * (p.MAX_PARSE_RECORDS + 1))), 'native_expansion_limit'),
                 (attempt(['11', '13'], body_complete=False), 'incomplete_body'),
                 (attempt(['11', '13'], error='timeout'), 'timeout')]
        cases.extend((attempt(['11', '13'], status=status), 'http_status') for status in (301, 302, 401, 403, 407, 429, 500))
        for record, stop in cases:
            with self.subTest(stop=stop, status=record['status']):
                a = artifact([record], stop)
                self.assertIsNone(a['derived']['responses'][0]['parsed_export'])
                self.assertEqual(a['execution']['attempts'][0], record)
                self.assertTrue(p.verify(a)['valid'])

    def test_prior_results_preserved_on_later_error_and_request_limit(self):
        choice = selection(occurrence_indices=[0, 1, 2], batch_size=1, max_requests=3)
        first = attempt(['11'])
        for second, stop in [(attempt(['12'], b'bad'), 'unsupported_native_response'),
                             (attempt(['12'], native(['99'])), 'unexpected_returned_pmid'),
                             (attempt(['12'], b'partial bytes', error='timeout', body_complete=False), 'timeout')]:
            a = artifact([first, second], stop, choice=choice)
            self.assertEqual([row['pmid'] for row in a['derived']['candidates']], ['11'])
            self.assertEqual([row['metadata_status'] for row in a['derived']['selected_occurrence_mapping']],
                             ['AVAILABLE_UNREVIEWED', 'RESPONSE_DIAGNOSTIC', 'NOT_REQUESTED'])
            intake = p.to_intake(a, protocol(), 'discovery-primary')
            self.assertEqual(len(intake['parsed_export']['record_rows']), 1)
            self.assertEqual(intake['parsed_export']['record_rows'][0]['original_values']['metadata_acquisition_status'], 'INCOMPLETE')
        choice['max_requests'] = 1
        a = artifact([first], 'max_requests', choice=choice)
        self.assertEqual(a['derived']['received_native_record_count'], 1)
        self.assertEqual(len(p.preview(discovery_artifact(), choice)['request_batches']), 1)
        self.assertEqual(a['derived']['selected_occurrence_mapping'][1]['scheduled_within_request_limit'], False)
        self.assertTrue(p.verify(a)['valid'])
        a = artifact([], 'elapsed_limit', choice=choice)
        self.assertEqual(a['derived']['mapped_selected_occurrence_count'], 0)

    def test_serialized_native_expansion_stops_with_raw_preserved(self):
        raw = b'PMID- 11\nTI  - ' + b'\x01' * 100000 + b'\n\nPMID- 13\n'
        self.assertLess(len(raw), p.MAX_BODY_BYTES)
        a = artifact([attempt(['11', '13'], raw)], 'native_expansion_limit')
        self.assertEqual(base64.b64decode(a['execution']['attempts'][0]['body_base64']), raw)
        self.assertIsNone(a['derived']['responses'][0]['parsed_export'])
        self.assertTrue(p.verify(a)['valid'])
        self.assertEqual(p.preview(discovery_artifact(), selection())['max_parsed_response_bytes'], p.MAX_PARSED_RESPONSE_BYTES)

    def test_live_execution_snapshots_hash_bound_inputs(self):
        source, choice = discovery_artifact(), selection()
        approved = p.preview(source, choice)['preview_sha256']
        def transport(params, timeout):
            source['derived']['occurrences'][0]['pmid'] = '999'
            choice['occurrence_indices'] = [1]
            return attempt(['11', '13'])
        with patch.object(p, '_utcnow', return_value=STAMP), patch.object(discovery, '_LAST_REQUEST', None):
            a = p.fetch(source, choice, approved, transport=transport)
        self.assertEqual(a['preview_sha256'], approved)
        self.assertEqual(a['selection']['occurrence_indices'], [0, 2])
        self.assertEqual(a['discovery_artifact']['derived']['occurrences'][0]['pmid'], '11')
        self.assertTrue(p.verify(a)['valid'])

    def test_strict_attempt_execution_and_replay_tampering(self):
        base = attempt(['11', '13'])
        changes = [dict(parameters=p.parameters(['13', '11'])), dict(status=True), dict(status=None), dict(elapsed_seconds=True),
                   dict(elapsed_seconds=-1), dict(elapsed_seconds=float('nan')), dict(body_complete=1), dict(body_base64='YWJj\n'),
                   dict(body_base64=base64.b64encode(b'x' * (p.MAX_BODY_BYTES + 1)).decode()), dict(error=[]),
                   dict(error='secret-error'), dict(headers={'set-cookie': 'secret'}), dict(headers={'content-length': '999'}),
                   dict(started_at='2026-01-01T01:00:00'), dict(extra='not-allowed')]
        for changed in changes:
            with self.subTest(change=list(changed)), self.assertRaises(ValueError):
                artifact([dict(base, **changed)])
        with self.assertRaises(ValueError):
            artifact([base, base])
        with self.assertRaises(ValueError):
            artifact([base], 'elapsed_limit')
        with self.assertRaises(ValueError):
            p.from_responses(discovery_artifact(), selection(), dict(started_at=STAMP, attempts=[], stop_reason='elapsed_limit', extra=1))
        a = artifact([base])
        for mutate in [lambda x: x.update(extra=1), lambda x: x['derived']['candidates'][0].update(pmid='99'),
                       lambda x: x['derived']['responses'][0]['parsed_export']['records'][0]['fields'][1].update(raw_text='changed'),
                       lambda x: x['implementation_sha256'].update({'pubmed_metadata.py': '0' * 64}),
                       lambda x: x.update(discovery_sha256='0' * 64), lambda x: x.update(schema_version=True)]:
            changed = copy.deepcopy(a)
            mutate(changed)
            with self.assertRaises(ValueError):
                p.verify(changed)

    def test_duration_bounds_and_truthful_timeout_overrun(self):
        for seconds, start in [(10, STAMP), (9999999, STAMP), (2, '2026-01-01T01:00:59+00:00')]:
            record = attempt(['11', '13'], elapsed_seconds=seconds, started_at=start)
            with self.assertRaisesRegex(ValueError, 'time bound'):
                artifact([record])
            record['error'] = 'timeout'
            self.assertEqual(artifact([record], 'timeout')['derived']['stop_reason'], 'timeout')
        for start in ('2026-01-01T00:59:59+00:00', '2026-01-01T01:01:00+00:00'):
            with self.assertRaises(ValueError):
                artifact([attempt(['11', '13'], started_at=start)])

    def test_conversion_preserves_provenance_plan_and_scientific_gates(self):
        a = artifact([attempt(['11', '13'], native(['13', '11']))])
        original = protocol()
        before = copy.deepcopy((a, original))
        flow_before = run(original)
        intake = p.to_intake(a, original, 'discovery-primary')
        self.assertTrue(bibliographic_intake.verify(intake)['valid'])
        self.assertEqual((a, original), before)
        self.assertEqual(run(original), flow_before)
        self.assertEqual(intake['protocol_snapshot'], original)
        self.assertEqual(intake['search_request']['searched_at'], a['discovery_artifact']['execution']['started_at'])
        self.assertEqual(intake['search_completion'], 'NOT_ESTABLISHED')
        self.assertFalse(intake['effects']['protocol_changed'])
        self.assertEqual(intake['conclusion_readiness'], 'NOT_READY')
        for row in intake['parsed_export']['record_rows']:
            values = row['original_values']
            self.assertEqual(values['metadata_acquisition_sha256'], p.digest(a))
            self.assertEqual(values['discovery_sha256'], p.digest(a['discovery_artifact']))
            self.assertEqual(values['response_sha256'], a['derived']['responses'][0]['response_sha256'])
            self.assertEqual(values['native_format'], p.FORMAT)
            self.assertTrue(json.loads(values['native_fields_json']))
        for key, value in [('query', 'changed'), ('source', 'other'), ('window', 'changed'), ('extra', 'ignored?')]:
            changed = copy.deepcopy(original)
            changed['search_plan'][0][key] = value
            with self.assertRaises(ValueError):
                p.to_intake(a, changed, 'discovery-primary')

    def test_real_urllib_fixed_endpoint_tls_and_no_credential_handlers(self):
        calls = []
        response = FakeResponse(native(['11', '13']), headers={'Content-Type': 'text/plain', 'Set-Cookie': 'secret', 'Authorization': 'secret'})
        def opened(opener, request, timeout):
            calls.append((opener, request, timeout))
            return response
        with patch.object(urllib.request.OpenerDirector, 'open', opened):
            record = p._transport(p.parameters(['11', '13']), 10)
        opener, request, timeout = calls[0]
        self.assertEqual(request.get_method(), 'GET')
        parsed = urllib.parse.urlsplit(request.full_url)
        self.assertEqual(parsed.scheme + '://' + parsed.netloc + parsed.path, p.ENDPOINT)
        self.assertEqual(urllib.parse.parse_qs(parsed.query), {'db': ['pubmed'], 'rettype': ['medline'], 'retmode': ['text'], 'id': ['11,13']})
        self.assertEqual(record['headers'], {'content-type': 'text/plain'})
        self.assertFalse(request.has_header('Authorization'))
        self.assertFalse(request.has_header('Cookie'))
        https = next(handler for handler in opener.handlers if isinstance(handler, urllib.request.HTTPSHandler))
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(https._context.check_hostname)
        self.assertTrue(any(isinstance(handler, p._NoRedirect) for handler in opener.handlers))
        self.assertIsNone(p._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://unrelated.test'))
        self.assertFalse(any(isinstance(handler, (urllib.request.HTTPBasicAuthHandler, urllib.request.HTTPCookieProcessor)) for handler in opener.handlers))
        self.assertFalse(any(hasattr(handler, 'proxy_open') and getattr(handler, 'proxies', {}) for handler in opener.handlers))
        self.assertTrue(record['body_complete'])
        self.assertIsNone(record['error'])

    def test_read1_raw_error_bytes_body_caps_incomplete_and_safe_errors(self):
        params = p.parameters(['11', '13'])
        for response, expected in [(FakeResponse(b'x' * (p.MAX_BODY_BYTES + 1)), 'body_too_large'),
                                   (FakeResponse(b'abc', headers={'Content-Length': '5'}), 'incomplete_body'),
                                   (FakeResponse(b'abc', headers={'Content-Length': '9' * 1000}), 'incomplete_body')]:
            response.read = lambda *args: (_ for _ in ()).throw(AssertionError('must use read1'))
            with patch.object(urllib.request.OpenerDirector, 'open', return_value=response):
                record = p._transport(params, 10)
            self.assertEqual(record['error'], expected)
            self.assertFalse(record['body_complete'])
            self.assertLessEqual(len(base64.b64decode(record['body_base64'])), p.MAX_BODY_BYTES)
        for failure, expected in [(TimeoutError('secret'), 'timeout'), (ssl.SSLError('secret'), 'tls_error'),
                                  (urllib.error.URLError(ssl.SSLError('secret')), 'tls_error'),
                                  (urllib.error.URLError(TimeoutError('secret')), 'timeout'),
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
        self.assertEqual(record['error'], 'incomplete_body')
        failure = urllib.error.HTTPError(p.ENDPOINT, 429, 'secret', {'Retry-After': '10', 'Set-Cookie': 'secret'}, io.BytesIO(b'error'))
        with patch.object(urllib.request.OpenerDirector, 'open', side_effect=failure):
            record = p._transport(params, 10)
        self.assertEqual(record['status'], 429)
        self.assertEqual(record['headers'], {'retry-after': '10'})
        self.assertEqual(base64.b64decode(record['body_base64']), b'error')

    def test_transport_post_read_timeout_retains_raw_bytes(self):
        clock = [0.0]
        response = FakeResponse(b'')
        def read1(amount):
            clock[0] += 11
            return b'late bounded bytes'
        response.read1 = read1
        with patch.object(urllib.request.OpenerDirector, 'open', return_value=response), patch.object(p.time, 'monotonic', side_effect=lambda: clock[0]):
            record = p._transport(p.parameters(['11']), 10)
        self.assertEqual(record['error'], 'timeout')
        self.assertEqual(record['elapsed_seconds'], 11)
        self.assertEqual(base64.b64decode(record['body_base64']), b'late bounded bytes')
        self.assertFalse(record['body_complete'])

    def test_fetch_shared_throttle_no_retry_and_post_sleep_deadline(self):
        source = discovery_artifact()
        choice = selection(occurrence_indices=[0, 1, 2], batch_size=1, max_requests=3)
        clock, starts = [0.0], []
        def sleep(seconds):
            clock[0] += seconds
        def transport(params, timeout):
            starts.append(clock[0])
            return attempt(params['id'].split(','))
        with patch.object(p, '_utcnow', return_value=STAMP), patch.object(discovery, '_LAST_REQUEST', 0.0), patch.object(p.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(p.time, 'sleep', side_effect=sleep):
            a = p.fetch(source, choice, p.preview(source, choice)['preview_sha256'], transport=transport)
            self.assertEqual(discovery._LAST_REQUEST, 3.0)
        self.assertEqual(starts, [1, 2, 3])
        self.assertEqual(a['derived']['acquisition_status'], 'SELECTED_IDS_RECEIVED')
        with patch.object(p, '_utcnow', return_value=STAMP), patch.object(discovery, '_LAST_REQUEST', None), patch.object(p, '_transport', return_value=attempt(['11'], b'error', status=429)) as mocked:
            a = p.fetch(source, choice, p.preview(source, choice)['preview_sha256'])
        mocked.assert_called_once()
        self.assertEqual(a['derived']['stop_reason'], 'http_status')
        clock[0] = 0.0
        def oversleep(seconds):
            clock[0] += 61
        with patch.object(p, '_utcnow', return_value=STAMP), patch.object(discovery, '_LAST_REQUEST', 0.0), patch.object(p.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(p.time, 'sleep', side_effect=oversleep), patch.object(p, '_transport') as mocked:
            a = p.fetch(source, choice, p.preview(source, choice)['preview_sha256'])
        mocked.assert_not_called()
        self.assertEqual(a['derived']['stop_reason'], 'elapsed_limit')

    def test_cli_existing_and_dangling_output_preflight_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path, selection_path, output = root / 'discovery.json', root / 'selection.json', root / 'output.json'
            input_path.write_text(json.dumps(discovery_artifact()))
            selection_path.write_text(json.dumps(selection()))
            output.write_text('untouched')
            dangling = root / 'dangling'
            dangling.symlink_to(root / 'absent')
            for path in (output, dangling):
                with patch.object(sys, 'argv', ['pubmed_metadata.py', 'fetch', str(input_path), str(selection_path), '--preview-sha256', '0' * 64, '--output', str(path)]), patch.object(p, 'fetch', side_effect=AssertionError('must not fetch')), patch('sys.stderr', new=io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        p.main()
                    self.assertEqual(raised.exception.code, 1)
            self.assertEqual(output.read_text(), 'untouched')

    def test_synthetic_fixtures_cli_offline_roundtrip(self):
        source = discovery.from_responses(json.loads((ROOT / 'examples/pubmed-discovery-spec.json').read_text()),
                                         json.loads((ROOT / 'examples/pubmed-discovery-execution.json').read_text()))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path, output = root / 'discovery.json', root / 'metadata.json'
            input_path.write_text(json.dumps(source))
            result = subprocess.run([sys.executable, str(ROOT / 'pubmed_metadata.py'), 'from-responses', str(input_path),
                str(ROOT / 'examples/pubmed-metadata-selection.json'), str(ROOT / 'examples/pubmed-metadata-execution.json'), '--output', str(output)],
                capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            a = json.loads(output.read_text())
            self.assertEqual(a['derived']['responses'][0]['returned_pmids'], ['13', '11'])
            result = subprocess.run([sys.executable, str(ROOT / 'pubmed_metadata.py'), 'verify', str(output)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['valid'])


if __name__ == '__main__':
    unittest.main()
