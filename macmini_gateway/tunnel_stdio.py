"""Tunnel stdio MCP bridge to the authenticated resident loopback service."""
import argparse
import base64
from mcp.server.fastmcp import FastMCP
from dots_request.mcp_transport import MCPTransport


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--caller-secret', required=True)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    adapter = MCPTransport(f'http://127.0.0.1:{args.port}/mcp', args.caller_secret)
    mcp = FastMCP('macmini_gateway_tunnel', log_level='CRITICAL')

    @mcp.tool()
    async def gateway_request(request: dict) -> dict:
        """Execute one API request through the resident gateway with local credentials."""
        try:
            result = await adapter.call(request, 110)
            if 'file' in result:
                file = result['file']
                result['file'] = {'encoding': 'base64', 'content': base64.b64encode(file['content']).decode(),
                                  'size': len(file['content']), 'sha256': file['sha256']}
            return result
        except Exception:
            from uuid import uuid4
            return {'request_id': str(uuid4()), 'ok': False, 'error': {
                'code': 'UPSTREAM_ERROR', 'message': 'Check local gateway availability', 'retryable': False}}

    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
