"""Run a fully offline demonstration: python3 -m macmini_gateway."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile

from .core import Gateway, UpstreamResponse


class MockTransport:
    def get(self, url, headers, timeout, max_bytes):
        if url.endswith("/download"):
            return UpstreamResponse(200, b"gateway mock download\n")
        return UpstreamResponse(200, b'{"items":[{"id":"mock-1"}]}')


def main():
    with tempfile.TemporaryDirectory(prefix="macmini-gateway-mock-") as directory:
        root = Path(directory)
        config = Path(__file__).parent / "examples" / "config.mock.json"
        (root / "config.json").write_bytes(config.read_bytes())
        secret = root / "demo.secret"
        secret.touch(mode=0o600)
        secret.write_text("MOCK_ONLY_gateway_demo_secret\n")
        gateway = Gateway(root / "config.json", transport=MockTransport())
        request = {"service": "demo", "account": "demo_account", "method": "GET", "path": "/items"}
        for page in range(3):
            print(json.dumps(gateway.execute(request | {"query": {"page": str(page)}}, caller_verified=True)))
        result = gateway.execute(request | {"path": "/download"}, caller_verified=True)
        content = base64.b64decode(result["file"]["content"])
        assert content == b"gateway mock download\n"
        assert hashlib.sha256(content).hexdigest() == result["file"]["sha256"]
        print(json.dumps(result))


if __name__ == "__main__":
    main()
