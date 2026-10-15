"""Local gateway core. A future trusted transport adapter supplies caller identity.

Only explicitly configured GET and JSON POST routes are executable. This module does not expose
an HTTP/MCP listener or establish company authentication.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import logging
import math
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import time
from dataclasses import dataclass
from urllib.parse import quote, urlencode, urlsplit
from uuid import uuid4


class ConfigurationError(ValueError):
    """Configuration is invalid; messages deliberately omit input values."""


class OutputRejected(Exception):
    pass


@dataclass(frozen=True)
class UpstreamResponse:
    status: int
    body: bytes


class HTTPSGetTransport:
    """One HTTPS GET, system certificate verification, no redirects or proxies."""

    def __init__(self, *, cafile=None):
        self.cafile = cafile

    def get(self, url: str, headers: dict[str, str], timeout: float,
            max_bytes: int) -> UpstreamResponse:
        return self.request("GET", url, headers, None, timeout, max_bytes)

    def request(self, method, url, headers, body, timeout, max_bytes):
        target = urlsplit(url)
        connection = http.client.HTTPSConnection(
            target.hostname, target.port or 443, timeout=timeout,
            context=ssl.create_default_context(cafile=self.cafile),
        )
        deadline = time.monotonic() + timeout
        try:
            kwargs = {"headers": headers}
            if body is not None:
                kwargs["body"] = body
            connection.request(method, target.path + ("?" + target.query if target.query else ""), **kwargs)
            response = connection.getresponse()
            # Redirects and upstream errors are returned as safe metadata only.
            if not 200 <= response.status < 300:
                return UpstreamResponse(response.status, b"")
            chunks = []
            size = 0
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                if connection.sock is not None:
                    connection.sock.settimeout(remaining)
                chunk = response.read1(min(65536, max_bytes + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise OutputRejected
                chunks.append(chunk)
            return UpstreamResponse(response.status, b"".join(chunks))
        finally:
            connection.close()


def _object(value, keys, required=()):
    if not isinstance(value, dict) or set(value) - set(keys) or not set(required) <= set(value):
        raise ConfigurationError("Check configuration fields")


def _path(value):
    # Exact routes with conservative ASCII syntax avoid URL/parser ambiguity.
    return (isinstance(value, str) and bool(re.fullmatch(r"/[A-Za-z0-9_./~-]*", value))
            and "//" not in value and all(p not in (".", "..") for p in value.split("/")))


def _secret(path: Path) -> str:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600):
                raise ConfigurationError("Secret files require service ownership and mode 0600")
            raw = stream.read(4097)
        value = raw.decode("ascii").removesuffix("\n")
        if not 8 <= len(value) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise ConfigurationError("Use a bounded, single-line credential")
        return value
    except (OSError, UnicodeError):
        raise ConfigurationError("Check local secret file access and encoding") from None


class Gateway:
    """Internal executor; caller_verified is supplied ONLY by a trusted adapter.

    Never bind this parameter to caller-controlled request data. The current
    component is used in-process by mock clients pending transport verification.
    """

    def __init__(self, config_path: str | Path, *, transport=None, logger=None):
        self.logger = logger or logging.getLogger("macmini_gateway")
        self.transport = transport or HTTPSGetTransport()
        config_path = Path(config_path).absolute()
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ConfigurationError("Check configuration JSON and access") from None
        _object(config, ("version", "timeout_seconds", "max_response_bytes", "services"),
                ("version", "services"))
        if type(config["version"]) is not int or config["version"] != 1:
            raise ConfigurationError("Use configuration version 1")
        self.timeout = config.get("timeout_seconds", 15)
        self.max_bytes = config.get("max_response_bytes", 1048576)
        if (type(self.timeout) not in (float, int) or not math.isfinite(self.timeout)
                or not 0 < self.timeout <= 120 or type(self.max_bytes) is not int
                or not 1 <= self.max_bytes <= 16777216):
            raise ConfigurationError("Check timeout and response size bounds")
        services = config["services"]
        if not isinstance(services, dict) or not services:
            raise ConfigurationError("Configure at least one service")
        self._services = {}
        self._secrets = []
        for name, service in services.items():
            self._alias(name)
            _object(service, ("origin", "routes", "accounts"), ("origin", "routes", "accounts"))
            origin = service["origin"]
            if not isinstance(origin, str) or not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]{1,5})?", origin):
                raise ConfigurationError("Configure a fixed HTTPS origin")
            try:
                parsed = urlsplit(origin)
                if not parsed.hostname or parsed.port == 0:
                    raise ValueError
            except ValueError:
                raise ConfigurationError("Check HTTPS origin") from None
            routes = service["routes"]
            if not isinstance(routes, dict) or not routes:
                raise ConfigurationError("Configure explicit business routes")
            for route, settings in routes.items():
                if not _path(route):
                    raise ConfigurationError("Use canonical absolute route paths")
                _object(settings, ("response", "query", "method", "body_fields", "max_body_bytes"), ("response", "query"))
                if settings["response"] not in ("json", "file"):
                    raise ConfigurationError("Select json or file response")
                method = settings.get("method", "GET")
                if method not in ("GET", "POST"):
                    raise ConfigurationError("Select GET or JSON POST")
                if method == "POST":
                    fields = settings.get("body_fields")
                    limit = settings.get("max_body_bytes", 16384)
                    if (settings["response"] != "json" or not isinstance(fields, list) or not fields
                            or any(not isinstance(k, str) for k in fields)
                            or type(limit) is not int or not 1 <= limit <= 65536):
                        raise ConfigurationError("Configure bounded JSON POST fields")
                query = settings["query"]
                if (not isinstance(query, list)
                        or any(not isinstance(k, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", k) for k in query)
                        or len(query) != len(set(query))):
                    raise ConfigurationError("Configure query parameter names")
            accounts = service["accounts"]
            if not isinstance(accounts, dict) or not accounts:
                raise ConfigurationError("Configure at least one account")
            credentials = {}
            for account, auth in accounts.items():
                self._alias(account)
                _object(auth, ("type", "secret_file", "header"), ("type", "secret_file"))
                if auth["type"] not in ("bearer", "api_key"):
                    raise ConfigurationError("Select an available authentication adapter")
                header = "Authorization" if auth["type"] == "bearer" else auth.get("header")
                if auth["type"] == "api_key" and (not isinstance(header, str) or not re.fullmatch(r"[Xx]-[A-Za-z0-9-]{1,60}", header)):
                    raise ConfigurationError("API key header must be an explicit X- header")
                if not isinstance(auth["secret_file"], str) or not auth["secret_file"]:
                    raise ConfigurationError("Configure a local secret file")
                secret = _secret(config_path.parent / auth["secret_file"])
                self._secrets.append(secret)
                credentials[account] = (header, ("Bearer " if auth["type"] == "bearer" else "") + secret)
            self._services[name] = (origin, routes, credentials)
        self._markers = set()
        for secret in self._secrets:
            raw = secret.encode()
            self._markers.update((raw, quote(secret, safe="").encode(),
                                  base64.b64encode(raw), base64.urlsafe_b64encode(raw),
                                  secret.encode("utf-16-le"), secret.encode("utf-16-be")))

    @staticmethod
    def _alias(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
            raise ConfigurationError("Use bounded service and account aliases")

    def _check_output(self, raw: bytes):
        if any(marker in raw for marker in self._markers):
            raise OutputRejected

    def _check_json(self, value):
        if isinstance(value, str):
            self._check_output(value.encode())
        elif isinstance(value, list):
            for item in value:
                self._check_json(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                self._check_json(key)
                self._check_json(item)

    def execute(self, request: dict, *, caller_verified: bool = False) -> dict:
        started = time.monotonic()
        request_id = str(uuid4())
        result = None

        def fail(code, message):
            return {"request_id": request_id, "ok": False,
                    "error": {"code": code, "message": message, "retryable": False}}

        try:
            if caller_verified is not True:
                result = fail("UNAUTHENTICATED", "Use a verified company connection")
                return result
            if (not isinstance(request, dict)
                    or set(request) - {"service", "account", "method", "path", "query", "body"}
                    or not {"service", "account", "method", "path"} <= set(request)
                    or request["method"] not in ("GET", "POST")
                    or not _path(request["path"])
                    or not isinstance(request["service"], str)
                    or not isinstance(request["account"], str)):
                result = fail("INVALID_REQUEST", "Use a configured business route")
                return result
            service = self._services.get(request["service"])
            if service is None or request["account"] not in service[2]:
                result = fail("UNKNOWN_CONNECTION", "Use configured service and account aliases")
                return result
            origin, routes, accounts = service
            route = routes.get(request["path"])
            query = request.get("query", {})
            if (route is None or not isinstance(query, dict) or set(query) - set(route["query"])
                    or len(query) > 32 or any(not isinstance(v, str) or len(v) > 2048 for v in query.values())):
                result = fail("INVALID_REQUEST", "Use configured query parameters and route")
                return result
            method = request["method"]
            body = request.get("body")
            if method != route.get("method", "GET") or (method == "GET" and body is not None):
                result = fail("INVALID_REQUEST", "Use the configured method and body")
                return result
            encoded = None
            if method == "POST":
                try:
                    if not isinstance(body, dict) or set(body) - set(route["body_fields"]):
                        raise ValueError
                    encoded = json.dumps(body, allow_nan=False).encode()
                    if len(encoded) > route.get("max_body_bytes", 16384) or (body.get("stream") is not None and body.get("stream") is not False):
                        raise ValueError
                except (ValueError, TypeError, RecursionError):
                    result = fail("INVALID_REQUEST", "Use a bounded non-streaming JSON body")
                    return result
            suffix = urlencode(query)
            url = origin + request["path"] + ("?" + suffix if suffix else "")
            header, credential = accounts[request["account"]]
            headers = {header: credential, "Accept-Encoding": "identity", "User-Agent": "macmini-gateway-e2e/1.0"}
            if method == "GET":
                response = self.transport.get(url, headers, self.timeout, self.max_bytes)
            else:
                headers["Content-Type"] = "application/json"
                response = self.transport.request(method, url, headers, encoded, self.timeout, self.max_bytes)
            if not 200 <= response.status < 300:
                result = fail("UPSTREAM_ERROR", "Check upstream status before another request")
                result["status"] = response.status
                return result
            if len(response.body) > self.max_bytes:
                raise OutputRejected
            self._check_output(response.body)
            result = {"request_id": request_id, "ok": True, "status": response.status}
            if route["response"] == "json":
                def invalid_constant(_):
                    raise ValueError
                data = json.loads(response.body, parse_constant=invalid_constant)
                self._check_json(data)
                result["data"] = data
            else:
                result["file"] = {"encoding": "base64", "content": base64.b64encode(response.body).decode(),
                                  "size": len(response.body), "sha256": hashlib.sha256(response.body).hexdigest()}
            return result
        except (TimeoutError, socket.timeout):
            result = fail("TIMEOUT", "Execution state requires verification before another request")
            return result
        except ssl.SSLCertVerificationError:
            result = fail("UPSTREAM_ERROR", "Check the configured trusted CA bundle")
            return result
        except (OutputRejected, ValueError, UnicodeError, RecursionError):
            result = fail("INVALID_RESPONSE", "Upstream output did not pass validation")
            return result
        except Exception:
            # Raw exceptions may contain URLs, headers, credentials or response bodies.
            result = fail("UPSTREAM_ERROR", "Check local service and upstream availability")
            return result
        finally:
            outcome = "INTERNAL_ERROR" if result is None else ("OK" if result["ok"] else result["error"]["code"])
            self.logger.info("request_id=%s outcome=%s duration_ms=%d", request_id, outcome,
                             int((time.monotonic() - started) * 1000))
