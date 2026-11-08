"""Real http.client parsing with synthetic socket bytes only; never live network."""
import base64
import copy
import http.client
import io
import ssl
import unittest
from unittest.mock import patch
import urllib.request
import urllib.response

import pubmed_discovery as discovery
import pubmed_metadata as metadata
from tests.test_pubmed_discovery import spec, native as discovery_native, artifact as discovery_artifact
from tests.test_pubmed_metadata import artifact as metadata_artifact


class SocketBytes:
    def __init__(self, raw):
        self.raw = raw

    def makefile(self, mode):
        return io.BytesIO(self.raw)


def response(body, headers, chunked=False):
    wire_body = (f'{len(body):x}\r\n'.encode() + body + b'\r\n0\r\n\r\n') if chunked else body
    raw = b'HTTP/1.1 200 OK\r\n' + b''.join(key.encode() + b': ' + value.encode() + b'\r\n' for key, value in headers) + b'\r\n' + wire_body
    value = http.client.HTTPResponse(SocketBytes(raw))
    value.begin()
    value.code = value.status
    return value


class FramingRegressionTests(unittest.TestCase):
    def test_duplicate_content_length_real_httpresponse_never_completes(self):
        for module, body, params in [(metadata, b'PMID- 11\n\nPMID- 13\n', metadata.parameters(['11', '13'])),
                                    (discovery, discovery_native([]), discovery.parameters(spec(), 0, 6))]:
            for lengths in [(len(body) + 100, len(body)), (len(body), len(body)), (len(body), len(body) + 100)]:
                with self.subTest(module=module.__name__, lengths=lengths):
                    native = response(body, [('Content-Length', str(length)) for length in lengths])
                    with patch.object(urllib.request.OpenerDirector, 'open', return_value=native):
                        record = module._transport(params, 10)
                    self.assertEqual(record['error'], 'incomplete_body')
                    self.assertFalse(record['body_complete'])
                    self.assertEqual(record['headers']['content-length'], ', '.join(str(length) for length in lengths))
                    self.assertEqual(base64.b64decode(record['body_base64']), body)
                    record['started_at'] = '2026-01-01T01:00:00+00:00' if module is metadata else '2026-01-01T00:00:00+00:00'
                    result = metadata_artifact([record], 'incomplete_body') if module is metadata else discovery_artifact(spec(), [record], 'incomplete_body')
                    self.assertEqual(result['derived']['stop_reason'], 'incomplete_body')
                    self.assertEqual(result['derived']['candidates' if module is metadata else 'occurrences'], [])
                    forged = copy.deepcopy(record)
                    forged.update(body_complete=True, error=None)
                    with self.assertRaises(ValueError):
                        module._attempt(forged)

    def test_transfer_encoding_with_length_and_duplicate_transfer_encoding_fail_closed(self):
        body = b'PMID- 11\n\nPMID- 13\n'
        for module in (metadata, discovery):
            for headers in [[('Transfer-Encoding', 'chunked'), ('Content-Length', str(len(body)))],
                            [('Transfer-Encoding', 'chunked'), ('Transfer-Encoding', 'chunked')],
                            [('Transfer-Encoding', 'gzip')]]:
                with self.subTest(module=module.__name__, headers=headers):
                    native = response(body, headers, chunked=headers[0][1] == 'chunked')
                    with patch.object(urllib.request.OpenerDirector, 'open', return_value=native):
                        record = module._transport({'db': 'pubmed'}, 10)
                    self.assertEqual(record['error'], 'incomplete_body')
                    self.assertFalse(record['body_complete'])
                    self.assertEqual(base64.b64decode(record['body_base64']), body)
                    forged = copy.deepcopy(record)
                    forged.update(body_complete=True, error=None)
                    with self.assertRaises(ValueError):
                        module._attempt(forged)

    def test_single_content_length_and_single_chunked_still_work(self):
        body = b'PMID- 11\n\nPMID- 13\n'
        for module in (metadata, discovery):
            for headers, chunked in [([('Content-Length', str(len(body)))], False), ([('Transfer-Encoding', 'chunked')], True)]:
                with self.subTest(module=module.__name__, headers=headers):
                    with patch.object(urllib.request.OpenerDirector, 'open', return_value=response(body, headers, chunked)):
                        record = module._transport({'db': 'pubmed'}, 10)
                    self.assertIsNone(record['error'])
                    self.assertTrue(record['body_complete'])
                    self.assertEqual(module._attempt(record), body)


class TransportRegressionTests(unittest.TestCase):
    def test_redirect_through_real_urllib_chain(self):
        for p, parameters in [(discovery, discovery.parameters(spec(), 0, 6)), (metadata, metadata.parameters(['11', '13']))]:
            class SyntheticHTTPS(urllib.request.HTTPSHandler):
                def __init__(self):
                    super().__init__(context=ssl.create_default_context())
                    self.urls = []
                def https_open(self, request):
                    self.urls.append(request.full_url)
                    response = urllib.response.addinfourl(
                        io.BytesIO(b'redirect-body'),
                        {'Location': 'https://other.test/', 'Content-Type': 'text/plain'},
                        request.full_url, 302)
                    response.msg = 'Found'
                    return response
            handler = SyntheticHTTPS()
            with patch.object(urllib.request, 'HTTPSHandler', return_value=handler):
                record = p._transport(parameters, 10)
            self.assertEqual(len(handler.urls), 1)
            self.assertTrue(handler.urls[0].startswith(p.ENDPOINT + '?'))
            self.assertEqual(record['status'], 302)
            self.assertEqual(base64.b64decode(record['body_base64']), b'redirect-body')
            self.assertTrue(record['body_complete'])
            self.assertIsNone(record['error'])

    def test_slow_buffered_body_checks_deadline_between_reads(self):
        for p, parameters in [(discovery, discovery.parameters(spec(), 0, 6)), (metadata, metadata.parameters(['11', '13']))]:
            timer = [0.0]
            class TrickleRaw(io.RawIOBase):
                def __init__(self):
                    self.header = bytearray(b'HTTP/1.1 200 OK\r\nContent-Length: 8\r\n\r\n')
                    self.body = bytearray(b'xxxxxxxx')
                def readable(self):
                    return True
                def readinto(self, target):
                    if self.header:
                        n = min(len(target), len(self.header))
                        target[:n] = self.header[:n]
                        del self.header[:n]
                        return n
                    if not self.body:
                        return 0
                    timer[0] += 9.0
                    target[0] = self.body.pop(0)
                    return 1
            buffered = io.BufferedReader(TrickleRaw())
            class SyntheticSocket:
                def makefile(self, mode):
                    return buffered
            response = http.client.HTTPResponse(SyntheticSocket())
            response.begin()
            with patch.object(urllib.request.OpenerDirector, 'open', return_value=response), \
                    patch.object(p.time, 'monotonic', side_effect=lambda: timer[0]):
                record = p._transport(parameters, 10)
            self.assertEqual(record['error'], 'timeout')
            self.assertFalse(record['body_complete'])
            self.assertEqual(base64.b64decode(record['body_base64']), b'xx')
            self.assertEqual(record['elapsed_seconds'], 18.0)
            self.assertTrue(response.closed)


if __name__ == '__main__':
    unittest.main()
