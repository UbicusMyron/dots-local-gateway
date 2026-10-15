"""Run from repository root: python3 -m dots_request.examples.mock_businesses"""
import hashlib
from pathlib import Path
import tempfile

from dots_request import Client


class MockGateway:
    """Local fixture; holds only simulated credentials and performs no network I/O."""
    def __init__(self):
        self.calls = []
        self._credential = "SIMULATED_THIRD_PARTY_SECRET"

    def send(self, request, *, timeout):
        self.calls.append(request)
        result = dict(request_id=f"mock-{len(self.calls)}", ok=True, status=200)
        if request["path"] == "/report":
            content = b"item,count\nexample,3\n"
            result["file"] = dict(content=content, sha256=hashlib.sha256(content).hexdigest())
        else:
            result["data"] = {"items": [request["query"].get("page", "1")]}
        return result


def main():
    gateway = MockGateway()
    client = Client.from_config(Path(__file__).parents[1] / "config.example.json", gateway)
    # Business A owns pagination.
    for page in range(1, 4):
        result = client.get("demo", "demo_account", "/items", query={"page": str(page)})
        assert result["data"]["items"] == [str(page)]
    # Business B consumes a file through the same client.
    with tempfile.TemporaryDirectory() as directory:
        result = client.download("demo", "demo_account", "/report", Path(directory) / "report.csv")
        assert result.read_bytes() == b"item,count\nexample,3\n"
    print("Local mock: 3 script requests and 1 verified download passed.")


if __name__ == "__main__":
    main()
