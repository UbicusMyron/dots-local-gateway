"""Transport-independent GET client; provisional adapter boundary, not a wire protocol."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Protocol
from urllib.parse import unquote


class RequestError(Exception):
    """Safe diagnostic metadata; raw adapter exceptions and payloads stay out of repr."""

    def __init__(self, code: str, request_id: str | None = None, *, retryable=False):
        self.code = code
        self.request_id = request_id
        self.retryable = retryable
        super().__init__(f"{code}" + (f" (request_id={request_id})" if request_id else ""))


class Transport(Protocol):
    def send(self, request: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        """Submit once; enforce timeout and return a decoded envelope.

        The adapter owns company connection authentication and normalizes files
        to bytes. It must check gateway output before returning it to this client.
        """
        ...


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_CODES = {"UNAUTHENTICATED", "INVALID_REQUEST", "UNKNOWN_CONNECTION", "UPSTREAM_ERROR", "TIMEOUT", "INVALID_RESPONSE"}


def _token(value):
    return isinstance(value, str) and _TOKEN.fullmatch(value) is not None


def _positive(value):
    return type(value) in (float, int) and math.isfinite(value) and value > 0


class Client:
    def __init__(self, transport: Transport, *, services: dict[str, list[str]],
                 timeout: float = 30, max_download_bytes: int = 10 * 1024 * 1024):
        if (not isinstance(services, dict) or not services or
                any(not _token(s) or not isinstance(a, list) or not a or
                    any(not _token(x) for x in a) for s, a in services.items()) or
                not _positive(timeout) or type(max_download_bytes) is not int or
                max_download_bytes <= 0):
            raise RequestError("INVALID_CONFIG")
        self._services = {s: frozenset(a) for s, a in services.items()}
        self._transport = transport
        self._timeout = timeout
        self._max_download_bytes = max_download_bytes

    @classmethod
    def from_config(cls, path: str | Path, transport: Transport) -> Client:
        try:
            config = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise RequestError("INVALID_CONFIG") from None
        if not isinstance(config, dict) or set(config) - {"services", "timeout", "max_download_bytes"}:
            raise RequestError("INVALID_CONFIG")
        if "services" not in config:
            raise RequestError("INVALID_CONFIG")
        return cls(transport, **config)

    def get(self, service: str, account: str, path: str, *, query=None) -> dict[str, Any]:
        return self.request(service, account, path, method="GET", query=query)

    def post(self, service, account, path, *, body):
        return self.request(service, account, path, method="POST", body=body)

    def request(self, service, account, path, *, method="GET", query=None, body=None):
        if method not in ("GET", "POST") or (method == "GET" and body is not None):
            raise RequestError("INVALID_REQUEST")
        if method == "POST":
            try:
                if not isinstance(body, dict) or len(json.dumps(body, allow_nan=False).encode()) > 65536:
                    raise ValueError
            except (ValueError, TypeError, RecursionError):
                raise RequestError("INVALID_REQUEST") from None
        if not _token(service) or not _token(account) or account not in self._services.get(service, ()):
            raise RequestError("UNKNOWN_CONNECTION")
        if not isinstance(path, str) or not path.startswith("/"):
            raise RequestError("INVALID_REQUEST")
        decoded = path
        # Check encoded separators and dot segments before transport dispatch.
        for _ in range(8):
            next_value = unquote(decoded)
            if next_value == decoded:
                break
            decoded = next_value
        else:
            raise RequestError("INVALID_REQUEST")
        if (decoded.startswith("//") or
                any(c in decoded for c in "\\?#") or
                any(ord(c) < 32 or ord(c) == 127 for c in decoded) or
                any(p in (".", "..") for p in decoded.split("/"))):
            raise RequestError("INVALID_REQUEST")
        if query is None:
            query = {}
        if not isinstance(query, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                              for k, v in query.items()):
            raise RequestError("INVALID_REQUEST")
        payload = dict(service=service, account=account, method=method, path=path,
                       query=dict(query), body=body)
        failed = None
        try:
            response = self._transport.send(payload, timeout=self._timeout)
        except TimeoutError:
            failed = "TIMEOUT"
        except Exception:
            failed = "TRANSPORT_ERROR"
        # Raise outside the handler to keep raw exception context out of diagnostics.
        if failed:
            raise RequestError(failed)
        return self._response(response)

    def _response(self, response):
        if not isinstance(response, dict) or not _token(response.get("request_id")):
            raise RequestError("INVALID_RESPONSE")
        request_id = response["request_id"]
        if type(response.get("ok")) is not bool:
            raise RequestError("INVALID_RESPONSE", request_id)
        if not response["ok"]:
            error = response.get("error")
            if (not isinstance(error, dict) or not isinstance(error.get("code"), str) or
                    type(error.get("retryable")) is not bool):
                raise RequestError("INVALID_RESPONSE", request_id)
            code = error["code"] if error["code"] in _CODES else "GATEWAY_ERROR"
            raise RequestError(code, request_id, retryable=error["retryable"])
        status = response.get("status")
        if type(status) is not int or not 200 <= status < 300:
            raise RequestError("INVALID_RESPONSE", request_id)
        if ("data" in response) == ("file" in response):
            raise RequestError("INVALID_RESPONSE", request_id)
        if "data" in response:
            try:
                data = json.loads(json.dumps(response["data"], allow_nan=False))
            except (TypeError, ValueError, RecursionError):
                raise RequestError("INVALID_RESPONSE", request_id) from None
            return dict(request_id=request_id, ok=True, status=status, data=data)
        file = response["file"]
        if (not isinstance(file, dict) or type(file.get("content")) is not bytes or
                not isinstance(file.get("sha256"), str) or
                not re.fullmatch(r"[0-9a-f]{64}", file["sha256"])):
            raise RequestError("INVALID_RESPONSE", request_id)
        content = file["content"]
        if len(content) > self._max_download_bytes:
            raise RequestError("FILE_TOO_LARGE", request_id)
        if hashlib.sha256(content).hexdigest() != file["sha256"]:
            raise RequestError("CHECKSUM_MISMATCH", request_id)
        return dict(request_id=request_id, ok=True, status=status,
                    file=dict(content=content, sha256=file["sha256"]))

    def download(self, service: str, account: str, path: str, destination: str | Path,
                 *, query=None) -> Path:
        """Publish a complete verified file at a caller-selected, new path."""
        result = self.get(service, account, path, query=query)
        request_id = result["request_id"]
        if "file" not in result:
            raise RequestError("EXPECTED_FILE", request_id)
        destination = Path(destination)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".dots-", delete=False) as out:
                temporary = Path(out.name)
                out.write(result["file"]["content"])
                out.flush()
                os.fsync(out.fileno())
            # Same-filesystem hard link is atomic and fails for existing files/symlinks.
            os.link(temporary, destination)
        except FileExistsError:
            raise RequestError("DESTINATION_EXISTS", request_id) from None
        except OSError:
            raise RequestError("FILE_SAVE_ERROR", request_id) from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return destination
