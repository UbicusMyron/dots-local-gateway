"""Bounded MCP Streamable HTTP adapter for a reachable, authenticated endpoint."""
import asyncio
import base64
import json
import logging
import os
from pathlib import Path
import stat
from urllib.parse import urlsplit

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .client import RequestError


def read_token(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as f:
            info = os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError
            token = f.read(4097).decode('ascii').removesuffix('\n')
        if not 8 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError
        return token
    except (OSError, ValueError, UnicodeError):
        raise RequestError('INVALID_CONFIG') from None


class LimitedStream(httpx.AsyncByteStream):
    def __init__(self, stream, limit):
        self.stream, self.limit = stream, limit

    async def __aiter__(self):
        size = 0
        async for chunk in self.stream:
            size += len(chunk)
            if size > self.limit:
                raise ValueError('Response limit exceeded')
            yield chunk

    async def aclose(self):
        await self.stream.aclose()


class LimitedTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        if response.headers.get('content-encoding', 'identity') != 'identity':
            await response.aclose()
            raise ValueError('Use identity encoding')
        response.stream = LimitedStream(response.stream, 4 * 1024 * 1024)
        return response


class MCPTransport:
    def __init__(self, url, token_file):
        try:
            target = urlsplit(url)
            if (target.username or target.password or target.fragment or target.query
                    or not target.hostname or target.port == 0
                    or not (target.scheme == 'https' or
                            target.scheme == 'http' and target.hostname == '127.0.0.1')):
                raise ValueError
        except ValueError:
            raise RequestError('INVALID_CONFIG') from None
        self.url, self.token = url, read_token(token_file)
        for name in ('mcp', 'httpx', 'httpcore'):
            logging.getLogger(name).setLevel(logging.CRITICAL)

    def send(self, request, *, timeout):
        failed = None
        try:
            result = asyncio.run(self.call(request, timeout))
        except TimeoutError:
            failed = 'TIMEOUT'
        except Exception:
            failed = 'TRANSPORT_ERROR'
        if failed == 'TIMEOUT':
            raise TimeoutError
        if failed:
            raise RequestError(failed)
        return result

    async def call(self, request, timeout):
        async with asyncio.timeout(timeout):
            async with httpx.AsyncClient(
                headers={'Authorization': 'Bearer ' + self.token, 'Accept-Encoding': 'identity'},
                transport=LimitedTransport(), timeout=timeout, follow_redirects=False,
                trust_env=False,
            ) as http:
                async with streamable_http_client(self.url, http_client=http) as (reader, writer, _):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        result = await session.call_tool('gateway_request', {'request': request})
                        if result.isError:
                            raise ValueError('MCP tool failed')
                        payload = result.structuredContent
                        if payload is None:
                            if len(result.content) != 1 or result.content[0].type != 'text':
                                raise ValueError('Invalid result')
                            payload = json.loads(result.content[0].text)
        if isinstance(payload, dict) and 'file' in payload:
            file = payload['file']
            if not isinstance(file, dict) or file.get('encoding') != 'base64':
                raise ValueError('Invalid file')
            content = base64.b64decode(file['content'], validate=True)
            if type(file.get('size')) is not int or len(content) != file['size']:
                raise ValueError('Invalid file size')
            payload['file'] = {'content': content, 'sha256': file['sha256']}
        return payload
