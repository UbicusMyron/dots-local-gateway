import json
from pathlib import Path
import tempfile
import traceback
import unittest

from dots_request import Client, RequestError
from dots_request.examples.mock_businesses import MockGateway


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.gateway = MockGateway()
        self.client = Client(self.gateway, services={"demo": ["demo_account"]})

    def get(self, **kwargs):
        return self.client.get("demo", "demo_account", "/items", **kwargs)

    def assert_code(self, code, call):
        with self.assertRaises(RequestError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_business_loop_and_isolation(self):
        for page in range(3):
            response = self.get(query={"page": str(page)})
            self.assertEqual(response["data"], {"items": [str(page)]})
            self.assertNotIn(self.gateway._credential, repr(response))
        self.assertEqual(len(self.gateway.calls), 3)
        self.assertNotIn(self.gateway._credential, repr(self.gateway.calls))
        self.assertEqual(self.gateway.calls[0]["method"], "GET")

    def test_invalid_requests_never_dispatch(self):
        for path in ["https://evil/x", "//evil/x", "/../secret", "/%252e%252e/x",
                     "/x?token=a", "/x#fragment", "/x\\y", "/x\n", "/%2fhost/x"]:
            with self.subTest(path=path):
                self.assert_code("INVALID_REQUEST", lambda: self.client.get("demo", "demo_account", path))
        self.assert_code("UNKNOWN_CONNECTION", lambda: self.client.get("demo", "wrong", "/x"))
        self.assert_code("INVALID_REQUEST", lambda: self.get(query={"page": 1}))
        self.assertEqual(self.gateway.calls, [])

    def test_safe_errors_and_single_attempt(self):
        for exception, code in [(RuntimeError("SIMULATED_SECRET"), "TRANSPORT_ERROR"),
                                (TimeoutError("SIMULATED_SECRET"), "TIMEOUT")]:
            calls = []
            def fail(request, *, timeout):
                calls.append(timeout)
                raise exception
            self.gateway.send = fail
            try:
                self.get()
            except RequestError as error:
                self.assertEqual(error.code, code)
                self.assertFalse(error.retryable)
                self.assertNotIn("SIMULATED_SECRET", traceback.format_exc())
            else:
                self.fail("Expected RequestError")
            self.assertEqual(calls, [30])

    def respond(self, response):
        self.gateway.send = lambda request, **kwargs: response

    def test_gateway_error_metadata(self):
        for code in ["UNAUTHENTICATED", "INVALID_REQUEST", "UNKNOWN_CONNECTION", "UPSTREAM_ERROR", "TIMEOUT"]:
            self.respond(dict(request_id="req-1", ok=False, error=dict(
                code=code, message="SIMULATED_SECRET", retryable=True)))
            error = self.assert_code(code, self.get)
            self.assertEqual(error.request_id, "req-1")
            self.assertTrue(error.retryable)
            self.assertNotIn("SIMULATED_SECRET", repr(error))

    def test_malformed_responses(self):
        for response in [None, {}, dict(request_id="x", ok=1),
                         dict(request_id="x", ok=True, status=True, data={}),
                         dict(request_id="x", ok=True, status=500, data={}),
                         dict(request_id="x", ok=True, status=200),
                         dict(request_id="x", ok=False, error={}),
                         dict(request_id="x", ok=True, status=200, data=float("nan"))]:
            self.respond(response)
            self.assert_code("INVALID_RESPONSE", self.get)

    def test_config_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"services": {"demo": ["demo_account"]}}))
            client = Client.from_config(path, self.gateway)
            self.assertTrue(client.get("demo", "demo_account", "/items")["ok"])
            for value in [[], {}, {"services": {}}, {"services": {"demo": ["a"]}, "token": "secret"},
                          {"services": {"demo": ["a"]}, "timeout": float("inf")}]:
                path.write_text(json.dumps(value))
                self.assert_code("INVALID_CONFIG", lambda: Client.from_config(path, self.gateway))

    def test_download_integrity_and_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.csv"
            self.client.download("demo", "demo_account", "/report", path)
            self.assertEqual(path.read_bytes(), b"item,count\nexample,3\n")
            self.assert_code("DESTINATION_EXISTS", lambda: self.client.download("demo", "demo_account", "/report", path))
            self.assertEqual(list(Path(tmp).iterdir()), [path])
            link = Path(tmp) / "symlink"
            link.symlink_to(path)
            self.assert_code("DESTINATION_EXISTS", lambda: self.client.download("demo", "demo_account", "/report", link))
            self.assertEqual(path.read_bytes(), b"item,count\nexample,3\n")

    def test_download_save_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent" / "file"
            self.assert_code("FILE_SAVE_ERROR", lambda: self.client.download("demo", "demo_account", "/report", path))
            self.assert_code("EXPECTED_FILE", lambda: self.client.download("demo", "demo_account", "/items", path))
            self.assertFalse(path.exists())

    def test_bad_download_never_publishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file"
            self.respond(dict(request_id="x", ok=True, status=200,
                              file=dict(content=b"abc", sha256="0" * 64)))
            self.assert_code("CHECKSUM_MISMATCH", lambda: self.client.download("demo", "demo_account", "/report", path))
            self.client._max_download_bytes = 2
            self.assert_code("FILE_TOO_LARGE", lambda: self.client.download("demo", "demo_account", "/report", path))
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
