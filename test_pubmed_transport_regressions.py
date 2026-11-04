"""Exercise actual urllib handler and buffered-read behavior without network access."""
import base64
import http.client
import io
import ssl
import unittest
from unittest.mock import patch
import urllib.request
import urllib.response

import pubmed_discovery as p
from test_pubmed_discovery import spec


class TransportRegressionTests(unittest.TestCase):
    def test_redirect_through_real_urllib_chain(self):
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
            record = p._transport(p.parameters(spec(), 0, 6), 10)
        self.assertEqual(len(handler.urls), 1)
        self.assertTrue(handler.urls[0].startswith(p.ENDPOINT + '?'))
        self.assertEqual(record['status'], 302)
        self.assertEqual(base64.b64decode(record['body_base64']), b'redirect-body')
        self.assertTrue(record['body_complete'])
        self.assertIsNone(record['error'])

    def test_slow_buffered_body_checks_deadline_between_reads(self):
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
            record = p._transport(p.parameters(spec(), 0, 6), 10)
        self.assertEqual(record['error'], 'timeout')
        self.assertFalse(record['body_complete'])
        self.assertEqual(base64.b64decode(record['body_base64']), b'xx')
        self.assertEqual(record['elapsed_seconds'], 18.0)
        self.assertTrue(response.closed)


if __name__ == '__main__':
    unittest.main()
