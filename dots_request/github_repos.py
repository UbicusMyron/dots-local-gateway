"""Enumerate the configured organization's visible repository metadata."""
import re
from .client import RequestError


def list_repositories(client, org, *, per_page=50, max_pages=1000):
    if not isinstance(org, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', org):
        raise RequestError('INVALID_REQUEST')
    if type(per_page) is not int or not 1 <= per_page <= 100 or type(max_pages) is not int or max_pages < 1:
        raise RequestError('INVALID_REQUEST')
    repos, ids, seen_pages = {}, [], set()
    for page in range(1, max_pages + 1):
        response = client.get('github', 'personal', f'/orgs/{org}/repos', query={
            'type': 'all', 'sort': 'full_name', 'direction': 'asc',
            'per_page': str(per_page), 'page': str(page)})
        ids.append(response['request_id'])
        rows = response['data']
        if not isinstance(rows, list) or len(rows) > per_page:
            raise RequestError('INVALID_RESPONSE', response['request_id'])
        page_ids = []
        for row in rows:
            if (not isinstance(row, dict) or type(row.get('id')) is not int
                    or not isinstance(row.get('full_name'), str)
                    or not row['full_name'].lower().startswith(org.lower() + '/')
                    or type(row.get('private')) is not bool
                    or not isinstance(row.get('html_url'), str)):
                raise RequestError('INVALID_RESPONSE', response['request_id'])
            page_ids.append(row['id'])
            repos[row['id']] = {k: row[k] for k in ('full_name', 'private', 'html_url')}
        signature = tuple(page_ids)
        if rows and signature in seen_pages:
            raise RequestError('PAGINATION_STALLED', response['request_id'])
        seen_pages.add(signature)
        if len(rows) < per_page:
            result = sorted(repos.values(), key=lambda r: r['full_name'].lower())
            private = sum(r['private'] for r in result)
            return {'ok': True, 'complete': True, 'org': org, 'total': len(result),
                    'private_count': private, 'public_count': len(result) - private,
                    'request_ids': ids, 'repositories': result,
                    'scope': 'Repository metadata visible to this token in the specified organization'}
    raise RequestError('PAGINATION_LIMIT', ids[-1])
