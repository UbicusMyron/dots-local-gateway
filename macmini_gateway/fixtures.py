"""Deterministic fixtures for transport acceptance; performs no outbound requests."""
import json
import time
from urllib.parse import urlsplit, parse_qs
from .core import UpstreamResponse


class FixtureTransport:
    def get(self, url, headers, timeout, max_bytes):
        parsed = urlsplit(url)
        if parsed.path.startswith('/orgs/') and parsed.path.endswith('/repos'):
            org = parsed.path.split('/')[2]
            query = parse_qs(parsed.query)
            page, size = int(query.get('page', ['1'])[0]), int(query.get('per_page', ['50'])[0])
            rows = [{'id': i, 'full_name': f'{org}/fixture-{i}', 'private': i % 2 == 0,
                     'html_url': f'https://github.com/{org}/fixture-{i}'} for i in range(1, 8)]
            return UpstreamResponse(200, json.dumps(rows[(page-1)*size:page*size]).encode())
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
