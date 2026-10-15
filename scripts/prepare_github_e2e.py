"""Add an exact, read-only GitHub org route to an existing local test directory."""
import argparse
import json
from pathlib import Path
import re
from prepare_e2e import write_new, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--org', required=True)
    parser.add_argument('--directory', type=Path, default=ROOT / 'macmini_gateway/local/e2e')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', args.org):
        parser.error('Use a GitHub organization login')
    config = {'version': 1, 'timeout_seconds': 30, 'max_response_bytes': 1048576, 'services': {
        'github': {'origin': 'https://api.github.com', 'accounts': {
            'personal': {'type': 'bearer', 'secret_file': 'github.secret'}}, 'routes': {
                f'/orgs/{args.org}/repos': {'method': 'GET', 'response': 'json',
                    'query': ['type', 'sort', 'direction', 'per_page', 'page']}}}}}
    write_new(args.directory / 'github.json', json.dumps(config, indent=2).encode())
    opencode = args.directory / 'opencode.json'
    if opencode.exists():
        combined = json.loads(opencode.read_text())
        combined['services'].update(config['services'])
        write_new(args.directory / 'real.json', json.dumps(combined, indent=2).encode())
    print('Prepared GitHub read-only org route; credential remains local.')


if __name__ == '__main__':
    main()
