"""Run on the dots cloud computer, or locally for transport QA."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from .client import Client, RequestError
from .mcp_transport import MCPTransport


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--caller-secret', required=True)
    parser.add_argument('--mode', choices=['mock', 'opencode', 'github'], default='mock')
    parser.add_argument('--per-page', type=int, default=50, help='GitHub page size (1-100)')
    parser.add_argument('--org', help='GitHub organization login')
    parser.add_argument('--model', help='A chat/completions model ID from the Go account')
    parser.add_argument('--download', default='gateway-e2e.txt')
    args = parser.parse_args(argv)
    try:
        client = Client(MCPTransport(args.url, args.caller_secret),
                        services={'demo': ['demo_account'], 'opencode_go': ['personal'], 'github': ['personal']}, timeout=110)
        if args.mode == 'mock':
            ids = []
            for page in range(3):
                response = client.get('demo', 'demo_account', '/items', query={'page': str(page)})
                if response['data'].get('source') != 'gateway-fixture':
                    raise RequestError('FIXTURE_MISMATCH')
                ids.append(response['request_id'])
            file = client.download('demo', 'demo_account', '/download', args.download)
            if file.read_bytes() != b'gateway e2e fixture\n':
                raise RequestError('FIXTURE_MISMATCH')
            print(json.dumps({'ok': True, 'request_ids': ids, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}))
        elif args.mode == 'github':
            if not args.org:
                parser.error('--org is required for github')
            from .github_repos import list_repositories
            print(json.dumps(list_repositories(client, args.org, per_page=args.per_page), ensure_ascii=False))
        else:
            if not args.model:
                parser.error('--model is required for opencode')
            result = client.post('opencode_go', 'personal', '/inference/go/v1/chat/completions', body={
                'model': args.model, 'messages': [{'role': 'user', 'content': 'Reply exactly GATEWAY_E2E_OK'}],
                'max_tokens': 32, 'stream': False})
            choices = result['data'].get('choices', [])
            if not choices or not isinstance(choices[0].get('message', {}).get('content'), str):
                raise RequestError('INVALID_RESPONSE', result['request_id'])
            print(json.dumps({'ok': True, 'request_id': result['request_id'],
                              'reply': choices[0]['message']['content']}))
    except RequestError as error:
        print(json.dumps({'ok': False, 'error': error.code, 'request_id': error.request_id}))
        sys.exit(1)


if __name__ == '__main__':
    main()
