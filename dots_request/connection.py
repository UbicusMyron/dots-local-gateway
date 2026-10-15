"""Local connection setup and repeatable business CLI for installed dots clients."""
import argparse
import getpass
import json
import os
from pathlib import Path
from .client import RequestError
from .mcp_transport import MCPTransport


def load(path):
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or set(data) != {'url', 'token_file', 'org', 'model'}:
            raise ValueError
        for value in data.values():
            if not isinstance(value, str): raise ValueError
        token_file = path.parent / data['token_file']
        MCPTransport(data['url'], token_file)
        return data, token_file
    except (OSError, ValueError, TypeError):
        raise RequestError('INVALID_CONFIG') from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['configure', 'mock', 'github', 'opencode'])
    parser.add_argument('--config', type=Path, default=Path('.dots-local/connection.json'))
    parser.add_argument('--url')
    parser.add_argument('--org', default='CUHK-Business-School-AI-Hub')
    parser.add_argument('--model', default='')
    parser.add_argument('--download', default='gateway-e2e.txt')
    args = parser.parse_args()
    try:
        if args.action == 'configure':
            if not args.url: parser.error('--url is required')
            if args.config.exists(): parser.error('Existing configuration preserved; use a new --config path')
            directory = args.config.resolve().parent
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            token = getpass.getpass('Connection credential (hidden; use endpoint credential, not third-party API keys): ')
            if not 8 <= len(token) <= 4096 or any(ord(c)<33 or ord(c)>126 for c in token):
                raise RequestError('INVALID_CONFIG')
            token_file = directory / (args.config.stem + '.secret')
            fd = os.open(token_file, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as f: f.write(token+'\n')
            try:
                MCPTransport(args.url, token_file)
                fd=os.open(args.config,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'w') as f:
                    json.dump({'url':args.url,'token_file':token_file.name,'org':args.org,'model':args.model},f,indent=2)
            except Exception:
                token_file.unlink()
                raise
            print('Connection saved locally. Run mock or a selected real test after endpoint validation.')
        else:
            data, token_file = load(args.config.resolve())
            from .e2e import main as run
            argv=['--url',data['url'],'--caller-secret',str(token_file),'--mode',args.action,
                  '--org',data['org'],'--download',args.download]
            if data['model']: argv += ['--model',data['model']]
            run(argv)
    except RequestError as error:
        parser.exit(1, error.code+'\n')


if __name__=='__main__':
    main()
