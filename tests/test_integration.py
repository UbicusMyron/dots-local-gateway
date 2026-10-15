import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dots_request import Client, RequestError
from dots_request.mcp_transport import MCPTransport

ROOT = Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.local = Path(cls.tmp.name) / 'runtime'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        subprocess.run([sys.executable, 'scripts/prepare_e2e.py', '--directory', str(cls.local),
                        '--port', str(cls.port)], cwd=ROOT, check=True, capture_output=True)
        cls.log = open(cls.local / 'test.log', 'w+')
        cls.process = subprocess.Popen([sys.executable, '-m', 'macmini_gateway.server',
            '--config', str(cls.local / 'mock.json'), '--caller-secret', str(cls.local / 'caller.secret'),
            '--port', str(cls.port), '--mock'], cwd=ROOT, stdout=cls.log, stderr=cls.log)
        cls.url = f'http://127.0.0.1:{cls.port}/mcp'
        for _ in range(100):
            if cls.process.poll() is not None:
                cls.log.seek(0)
                raise RuntimeError(cls.log.read())
            try:
                with socket.create_connection(('127.0.0.1', cls.port), timeout=.1):
                    break
            except OSError:
                time.sleep(.05)
        else:
            cls.process.terminate()
            raise RuntimeError('Service did not start')

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.log.close()
        cls.tmp.cleanup()

    def client(self):
        return Client(MCPTransport(self.url, self.local / 'caller.secret'), services={'demo': ['demo_account']})

    def test_loop_and_file_cli(self):
        result = subprocess.run([sys.executable, '-m', 'dots_request.e2e', '--url', self.url,
            '--caller-secret', str(self.local / 'caller.secret'), '--download', str(self.local / 'result.txt')],
            cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(len(set(report['request_ids'])), 3)
        self.assertEqual((self.local / 'result.txt').read_bytes(), b'gateway e2e fixture\n')

    def test_post_and_method_policy(self):
        client = self.client()
        result = client.post('demo', 'demo_account', '/chat', body={'model': 'mock', 'stream': False})
        self.assertEqual(result['data']['choices'][0]['message']['content'], 'GATEWAY_E2E_OK')
        for path, body in [('/items', {}), ('/chat', {'stream': True}),
                           ('/chat', {'headers': {}}), ('/chat', {'messages': 'x'*17000})]:
            with self.assertRaises(RequestError) as error:
                client.post('demo', 'demo_account', path, body=body)
            self.assertEqual(error.exception.code, 'INVALID_REQUEST')

    def test_auth_and_size_gate(self):
        with httpx.Client(trust_env=False) as client:
            for headers in ({}, {'Authorization': 'Bearer invalid-token'}):
                self.assertEqual(client.post(self.url, json={}, headers=headers).status_code, 401)
            token = (self.local / 'caller.secret').read_text().strip()
            self.assertEqual(client.post(self.url, content=b'x'*131073,
                headers={'Authorization': 'Bearer ' + token}).status_code, 413)

    def test_caller_verified_injection(self):
        result = MCPTransport(self.url, self.local / 'caller.secret').send({
            'service': 'demo', 'account': 'demo_account', 'method': 'GET', 'path': '/items',
            'caller_verified': True}, timeout=10)
        self.assertEqual(result['error']['code'], 'INVALID_REQUEST')

    def test_stdio_bridge(self):
        async def run():
            params = StdioServerParameters(command=sys.executable, args=[
                '-m', 'macmini_gateway.tunnel_stdio', '--caller-secret', str(self.local / 'caller.secret'),
                '--port', str(self.port)], cwd=str(ROOT))
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertEqual([t.name for t in tools.tools], ['gateway_request'])
                    result = await session.call_tool('gateway_request', {'request': {
                        'service': 'demo', 'account': 'demo_account', 'method': 'GET', 'path': '/items'}})
                    self.assertFalse(result.isError)
                    payload = result.structuredContent or json.loads(result.content[0].text)
                    self.assertTrue(payload['ok'])
        asyncio.run(asyncio.wait_for(run(), timeout=20))

    def test_log_secrets(self):
        self.client().get('demo', 'demo_account', '/items')
        self.log.flush()
        text = (self.local / 'test.log').read_text()
        self.assertIn('request_id=', text)
        for name in ('caller.secret', 'demo.secret'):
            self.assertNotIn((self.local / name).read_text().strip(), text)

    def test_upstream_failure_and_secret_isolation(self):
        client = self.client()
        for path, code in [('/error', 'UPSTREAM_ERROR'), ('/leak', 'INVALID_RESPONSE')]:
            with self.assertRaises(RequestError) as error:
                client.get('demo', 'demo_account', path)
            self.assertEqual(error.exception.code, code)
            self.assertNotIn('MOCK_ONLY', str(error.exception))

    def test_whole_call_timeout(self):
        adapter = MCPTransport(self.url, self.local / 'caller.secret')
        with self.assertRaises(TimeoutError):
            adapter.send({'service': 'demo', 'account': 'demo_account', 'method': 'GET', 'path': '/slow'}, timeout=.1)

    def test_url_policy(self):
        for url in ['http://example.com/mcp', 'https://user:pw@example.com/mcp', 'https://example.com/mcp?key=x']:
            with self.assertRaises(RequestError):
                MCPTransport(url, self.local / 'caller.secret')


if __name__ == '__main__':
    unittest.main()
