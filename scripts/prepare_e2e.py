"""Prepare local-only credentials, configs and reviewable launchd files."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import secrets
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]


def write_new(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=ROOT / 'macmini_gateway/local/e2e')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    local = args.directory.resolve()
    local.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(local.iterdir()):
        parser.error('Use an empty directory to preserve existing credentials and configuration')
    local.chmod(0o700)
    write_new(local / 'caller.secret', (secrets.token_urlsafe(32) + '\n').encode())
    write_new(local / 'demo.secret', b'MOCK_ONLY_gateway_e2e_secret\n')
    mock = {'version': 1, 'timeout_seconds': 90, 'max_response_bytes': 1048576, 'services': {
        'demo': {'origin': 'https://example.invalid', 'accounts': {
            'demo_account': {'type': 'bearer', 'secret_file': 'demo.secret'}}, 'routes': {
                '/items': {'response': 'json', 'query': ['page']},
                '/slow': {'response': 'json', 'query': []},
                '/error': {'response': 'json', 'query': []},
                '/leak': {'response': 'json', 'query': []},
                '/download': {'response': 'file', 'query': []},
                '/chat': {'method': 'POST', 'response': 'json', 'query': [],
                          'body_fields': ['model', 'messages', 'max_tokens', 'stream']}}}}}
    write_new(local / 'mock.json', json.dumps(mock, indent=2).encode())
    real = {'version': 1, 'timeout_seconds': 90, 'max_response_bytes': 1048576, 'services': {
        'opencode_go': {'origin': 'https://opencode.ai', 'accounts': {
            'personal': {'type': 'bearer', 'secret_file': 'opencode.secret'}}, 'routes': {
                '/inference/go/v1/models': {'response': 'json', 'query': []},
                '/inference/go/v1/chat/completions': {'method': 'POST', 'response': 'json', 'query': [],
                    'body_fields': ['model', 'messages', 'max_tokens', 'stream'], 'max_body_bytes': 16384}}}}}
    write_new(local / 'opencode.json', json.dumps(real, indent=2).encode())
    for mode in ('mock', 'opencode'):
        argv = [sys.executable, '-m', 'macmini_gateway.server', '--config', str(local / f'{mode}.json'),
                '--caller-secret', str(local / 'caller.secret'), '--port', str(args.port)]
        if mode == 'mock':
            argv += ['--mock']
        plist = {'Label': 'com.cuhk.macmini-gateway.e2e', 'ProgramArguments': argv,
                 'WorkingDirectory': str(ROOT), 'RunAtLoad': True, 'KeepAlive': True,
                 'ThrottleInterval': 5, 'Umask': 63,
                 'StandardOutPath': str(local / 'service.log'), 'StandardErrorPath': str(local / 'service.log')}
        write_new(local / f'gateway-{mode}.plist', plistlib.dumps(plist))
    bridge = '#!/bin/sh\ncd ' + shlex.quote(str(ROOT)) + ' || exit 1\nexec ' + shlex.join([
        sys.executable, '-m', 'macmini_gateway.tunnel_stdio', '--caller-secret', str(local / 'caller.secret'),
        '--port', str(args.port)]) + '\n'
    write_new(local / 'tunnel-bridge.sh', bridge.encode())
    (local / 'tunnel-bridge.sh').chmod(0o700)
    print('Prepared local configs, credentials and launchd files at: ' + str(local))


if __name__ == '__main__':
    main()
