"""Authenticated, loopback-only Streamable HTTP MCP service."""
import argparse
import asyncio
import base64
from urllib.parse import quote
import hmac
import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
import uvicorn
import certifi

from .core import Gateway, ConfigurationError, HTTPSGetTransport, _secret
from pathlib import Path


class Guard:
    """Authenticate before parsing; cap incoming bodies and suppress raw diagnostics."""
    def __init__(self, app, token):
        self.app, self.token = app, token.encode('ascii')

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = scope.get('headers', [])
        auth = [v for k, v in headers if k == b'authorization']
        valid = len(auth) == 1 and hmac.compare_digest(auth[0], b'Bearer ' + self.token)
        if not valid:
            return await JSONResponse({'error': 'UNAUTHENTICATED'}, status_code=401)(scope, receive, send)
        # Buffer at most 128 KiB before the MCP parser. Uvicorn bounds concurrency.
        chunks, size = [], 0
        try:
            async with asyncio.timeout(15):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    size += len(message.get('body', b''))
                    if size > 131072:
                        return await JSONResponse({'error': 'REQUEST_TOO_LARGE'}, status_code=413)(scope, receive, send)
                    chunks.append(message.get('body', b''))
                    if not message.get('more_body', False):
                        break
        except TimeoutError:
            return await JSONResponse({'error': 'TIMEOUT'}, status_code=408)(scope, receive, send)
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': b''.join(chunks), 'more_body': False}
            return await receive()
        await self.app(scope, replay, send)


def create_app(gateway, token):
    gateway._markers.update((token.encode(), quote(token, safe='').encode(),
                             base64.b64encode(token.encode()), base64.urlsafe_b64encode(token.encode()),
                             token.encode('utf-16-le'), token.encode('utf-16-be')))
    # Host checks also reject browser-origin requests to loopback.
    mcp = FastMCP('macmini_gateway', stateless_http=True, json_response=True,
                  transport_security=TransportSecuritySettings(
                      enable_dns_rebinding_protection=True,
                      allowed_hosts=['127.0.0.1:*', 'localhost:*'], allowed_origins=[]))

    @mcp.tool()
    def gateway_request(request: dict) -> dict:
        """Execute one configured API request. Credentials are added locally by the gateway."""
        return gateway.execute(request, caller_verified=True)

    return Guard(mcp.streamable_http_app(), token)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--caller-secret', required=True)
    parser.add_argument('--ca-file', help='Administrator-provided CA bundle; default is certifi')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--mock', action='store_true', help='Use deterministic local fixture upstream')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    # SDK diagnostics can include invalid tool arguments; retain only gateway metadata.
    for name in ('mcp', 'httpx', 'httpcore'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    try:
        token = _secret(Path(args.caller_secret))
        transport = HTTPSGetTransport(cafile=args.ca_file or certifi.where())
        if args.mock:
            from .fixtures import FixtureTransport
            transport = FixtureTransport()
        gateway = Gateway(args.config, transport=transport)
        # Include company secret in the same output-isolation policy.
        gateway._markers.add(token.encode())
        app = create_app(gateway, token)
    except (ConfigurationError, OSError, ValueError):
        parser.exit(2, 'Gateway configuration failed; check local paths and permissions.\n')
    uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False,
                log_level='warning', limit_concurrency=16, timeout_keep_alive=5)


if __name__ == '__main__':
    main()
