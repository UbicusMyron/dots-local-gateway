"""Deterministic fixtures for transport acceptance; performs no outbound requests."""
import json
import time
from .core import UpstreamResponse


class FixtureTransport:
    def get(self, url, headers, timeout, max_bytes):
        if url.endswith('/slow'):
            time.sleep(.5)
        if url.endswith('/error'):
            return UpstreamResponse(500, b'private diagnostic')
        if url.endswith('/leak'):
            return UpstreamResponse(200, json.dumps({'echo': headers['Authorization']}).encode())
        if url.endswith('/download'):
            return UpstreamResponse(200, b'gateway e2e fixture\n')
        return UpstreamResponse(200, b'{"items":[1,2,3],"source":"gateway-fixture"}')

    def request(self, method, url, headers, body, timeout, max_bytes):
        data = json.loads(body)
        return UpstreamResponse(200, json.dumps({
            'choices': [{'message': {'content': 'GATEWAY_E2E_OK'}}],
            'model': data.get('model'), 'source': 'gateway-fixture'}).encode())
