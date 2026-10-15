import base64
import hashlib
import io
import json
import logging
import ssl
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from macmini_gateway.core import Gateway, ConfigurationError, HTTPSGetTransport, UpstreamResponse, OutputRejected

SECRET = "MOCK_SECRET_account_one_1234"
OTHER_SECRET = "MOCK_SECRET_account_two_5678"


class MockThirdParty:
    def __init__(self):
        self.calls = []
        self.response = UpstreamResponse(200, b'{"items":[1,2]}')
        self.error = None

    def get(self, url, headers, timeout, max_bytes):
        self.calls.append((url, headers, timeout, max_bytes))
        if self.error:
            raise self.error
        return self.response


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, secret in (("one", SECRET), ("two", OTHER_SECRET)):
            path = self.root / name
            path.write_text(secret + "\n")
            path.chmod(0o600)
        self.config = {"version": 1, "max_response_bytes": 1024, "services": {
            "demo": {"origin": "https://api.example.invalid", "routes": {
                "/items": {"response": "json", "query": ["page"]},
                "/download": {"response": "file", "query": []}}, "accounts": {
                    "first": {"type": "bearer", "secret_file": "one"},
                    "second": {"type": "api_key", "header": "X-API-Key", "secret_file": "two"}}}}}
        self.transport = MockThirdParty()
        self.logs = io.StringIO()
        self.logger = logging.Logger("test")
        self.logger.addHandler(logging.StreamHandler(self.logs))
        self.gateway = self.load()
        self.request = {"service": "demo", "account": "first", "method": "GET", "path": "/items"}

    def load(self):
        path = self.root / "config.json"
        path.write_text(json.dumps(self.config))
        return Gateway(path, transport=self.transport, logger=self.logger)

    def execute(self, **changes):
        return self.gateway.execute(self.request | changes, caller_verified=True)

    def test_mock_client_loop_and_routing(self):
        ids = set()
        for page in range(3):
            result = self.execute(query={"page": str(page)})
            self.assertTrue(result["ok"])
            self.assertEqual(result["data"], {"items": [1, 2]})
            ids.add(result["request_id"])
        self.assertEqual(len(ids), 3)
        self.assertEqual(self.transport.calls[2][0], "https://api.example.invalid/items?page=2")
        self.assertEqual(self.transport.calls[0][1]["Authorization"], "Bearer " + SECRET)
        self.execute(account="second")
        self.assertEqual(self.transport.calls[-1][1]["X-API-Key"], OTHER_SECRET)
        self.assertNotIn("Authorization", self.transport.calls[-1][1])

    def test_authentication_gate(self):
        for identity in (False, None, "true", 1):
            result = self.gateway.execute(self.request, caller_verified=identity)
            self.assertEqual(result["error"]["code"], "UNAUTHENTICATED")
        self.assertEqual(self.transport.calls, [])

    def test_invalid_requests_never_reach_upstream(self):
        cases = [{"method": "POST"}, {"body": {}}, {"headers": {"Authorization": "bad"}},
                 {"caller_verified": True}, {"service": []}, {"account": {}},
                 {"path": "https://evil.invalid/items"}, {"path": "//evil.invalid/items"},
                 {"path": "/../items"}, {"path": "/%2e%2e/items"}, {"path": "/items?x=1"},
                 {"path": "/oauth/token"}, {"path": "/items\\evil"},
                 {"query": {"token": "evil"}}, {"query": {"page": []}},
                 {"query": {"page": "a" * 2049}}]
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(self.execute(**case)["error"]["code"], "INVALID_REQUEST")
        self.assertEqual(self.transport.calls, [])

    def test_unknown_alias(self):
        for changes in ({"service": "missing"}, {"account": "missing"}):
            self.assertEqual(self.execute(**changes)["error"]["code"], "UNKNOWN_CONNECTION")
        self.assertEqual(self.transport.calls, [])

    def test_query_values_are_encoded(self):
        self.execute(query={"page": "1&host=https://evil.invalid\r\nX:yes"})
        url = self.transport.calls[-1][0]
        self.assertNotIn("\r", url)
        self.assertIn("%26host%3D", url)

    def test_file_integrity(self):
        payload = b"mock file\x00\xff\n"
        self.transport.response = UpstreamResponse(200, payload)
        result = self.execute(path="/download")
        self.assertEqual(base64.b64decode(result["file"]["content"]), payload)
        self.assertEqual(result["file"]["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(result["file"]["size"], len(payload))

    def test_secret_isolation_across_accounts_and_encodings(self):
        escaped = ''.join('\\u%04x' % ord(c) for c in OTHER_SECRET)
        payloads = [json.dumps({"echo": SECRET}).encode(),
                    ('{"echo":"' + escaped + '"}').encode(),
                    json.dumps({"echo": base64.b64encode(OTHER_SECRET.encode()).decode()}).encode(),
                    json.dumps({"echo": OTHER_SECRET}).encode("utf-16")]
        for payload in payloads:
            self.transport.response = UpstreamResponse(200, payload)
            result = self.execute()
            self.assertEqual(result["error"]["code"], "INVALID_RESPONSE")
            self.assertNotIn(SECRET, json.dumps(result))
        for encoding in ("utf-8", "utf-16-le", "utf-16-be"):
            self.transport.response = UpstreamResponse(200, SECRET.encode(encoding))
            self.assertFalse(self.execute(path="/download")["ok"])
        self.assertNotIn(SECRET, self.logs.getvalue())
        self.assertNotIn(OTHER_SECRET, self.logs.getvalue())

    def test_size_invalid_json_and_nonfinite(self):
        for body in (b"a" * 1025, b"not JSON", b'{"value":NaN}', b"[" * 1100):
            self.transport.response = UpstreamResponse(200, body)
            self.assertEqual(self.execute()["error"]["code"], "INVALID_RESPONSE")

    def test_upstream_error_and_redirect_bodies_are_private(self):
        for status in (301, 302, 307, 401, 429, 500):
            self.transport.response = UpstreamResponse(status, SECRET.encode())
            result = self.execute()
            self.assertEqual(result["error"]["code"], "UPSTREAM_ERROR")
            self.assertEqual(result["status"], status)
            self.assertNotIn(SECRET, json.dumps(result))

    def test_exceptions_are_safe_and_never_retried(self):
        for error, code in ((TimeoutError(SECRET), "TIMEOUT"), (OSError(SECRET), "UPSTREAM_ERROR")):
            self.transport.error = error
            count = len(self.transport.calls)
            result = self.execute()
            self.assertEqual(result["error"]["code"], code)
            self.assertFalse(result["error"]["retryable"])
            self.assertEqual(len(self.transport.calls), count + 1)
            self.assertNotIn(SECRET, json.dumps(result) + self.logs.getvalue())

    def test_certificate_failure_is_safe_upstream_error(self):
        self.transport.error = ssl.SSLCertVerificationError('MOCK_PRIVATE_TLS_DIAGNOSTIC')
        result = self.execute()
        self.assertEqual(result['error']['code'], 'UPSTREAM_ERROR')
        self.assertNotIn('MOCK_PRIVATE_TLS_DIAGNOSTIC', json.dumps(result))

    def test_secret_permissions_and_symlink(self):
        path = self.root / "one"
        path.chmod(0o644)
        with self.assertRaises(ConfigurationError):
            self.load()
        path.unlink()
        path.symlink_to(self.root / "two")
        with self.assertRaises(ConfigurationError):
            self.load()

    def test_post_route_body_and_single_dispatch(self):
        calls = []
        def post(method, url, headers, body, timeout, max_bytes):
            calls.append((method, url, headers, json.loads(body)))
            return UpstreamResponse(200, b'{"ok":true}')
        self.transport.request = post
        self.config['services']['demo']['routes']['/chat'] = {
            'method': 'POST', 'response': 'json', 'query': [],
            'body_fields': ['messages', 'stream'], 'max_body_bytes': 100}
        self.gateway = self.load()
        result = self.execute(method='POST', path='/chat', body={'messages': ['hi'], 'stream': False})
        self.assertTrue(result['ok'])
        self.assertEqual(calls[0][0], 'POST')
        self.assertEqual(calls[0][2]['Authorization'], 'Bearer ' + SECRET)
        self.assertEqual(calls[0][2]['Content-Type'], 'application/json')
        for body in (None, [], {'headers': {}}, {'stream': True}, {'messages': 'x'*101},
                     {'messages': float('nan')}):
            self.assertEqual(self.execute(method='POST', path='/chat', body=body)['error']['code'], 'INVALID_REQUEST')
        self.assertEqual(len(calls), 1)

    def test_post_config_requires_explicit_fields(self):
        self.config['services']['demo']['routes']['/chat'] = {'method': 'POST', 'response': 'json', 'query': []}
        with self.assertRaises(ConfigurationError):
            self.load()

    def test_config_rejects_bad_origins(self):
        for origin in ("http://localhost", "https://user:pw@host", "https://host/path", "https://host:99999", "https://host?x=1"):
            self.config["services"]["demo"]["origin"] = origin
            with self.assertRaises(ConfigurationError):
                self.load()

    def test_config_rejects_reserved_header_and_query(self):
        self.config["services"]["demo"]["accounts"]["second"]["header"] = "Host"
        with self.assertRaises(ConfigurationError):
            self.load()
        self.config["services"]["demo"]["accounts"]["second"]["header"] = "X-Key"
        self.config["services"]["demo"]["routes"]["/items"]["query"] = [{}]
        with self.assertRaises(ConfigurationError):
            self.load()


class TransportTests(unittest.TestCase):
    @patch("macmini_gateway.core.http.client.HTTPSConnection")
    def test_https_get_no_redirect_following(self, connection_class):
        connection = connection_class.return_value
        response = connection.getresponse.return_value
        response.status = 302
        result = HTTPSGetTransport().get("https://api.example.invalid/items?page=1", {}, 5, 100)
        self.assertEqual(result, UpstreamResponse(302, b""))
        connection.request.assert_called_once_with("GET", "/items?page=1", headers={})
        response.read1.assert_not_called()
        connection.close.assert_called_once()

    @patch("macmini_gateway.core.http.client.HTTPSConnection")
    def test_post_bytes_are_sent_once(self, connection_class):
        response = connection_class.return_value.getresponse.return_value
        response.status = 200
        response.read1.side_effect = [b'{}', b'']
        result = HTTPSGetTransport().request('POST', 'https://api.example.invalid/chat',
                                             {'Content-Type': 'application/json'}, b'{"x":1}', 5, 100)
        self.assertEqual(result.body, b'{}')
        connection_class.return_value.request.assert_called_once_with(
            'POST', '/chat', headers={'Content-Type': 'application/json'}, body=b'{"x":1}')

    @patch("macmini_gateway.core.http.client.HTTPSConnection")
    def test_transport_bounds_actual_bytes(self, connection_class):
        connection = connection_class.return_value
        response = connection.getresponse.return_value
        response.status = 200
        response.read1.side_effect = [b"12345", b"6"]
        with self.assertRaises(OutputRejected):
            HTTPSGetTransport().get("https://api.example.invalid/file", {}, 5, 5)
        connection.close.assert_called_once()

    @patch("macmini_gateway.core.http.client.HTTPSConnection")
    def test_transport_collects_chunks(self, connection_class):
        response = connection_class.return_value.getresponse.return_value
        response.status = 200
        response.read1.side_effect = [b"abc", b"def", b""]
        result = HTTPSGetTransport().get("https://api.example.invalid/file", {}, 5, 10)
        self.assertEqual(result.body, b"abcdef")


if __name__ == "__main__":
    unittest.main()
