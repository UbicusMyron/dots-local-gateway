import unittest
from dots_request.github_repos import list_repositories
from dots_request import RequestError


def repo(i, private=False):
    return {'id': i, 'full_name': f'example/repo{i}', 'private': private,
            'html_url': f'https://github.com/example/repo{i}'}


class Client:
    def __init__(self, pages):
        self.pages, self.calls = pages, []
    def get(self, *args, query):
        self.calls.append((args, query))
        return {'request_id': str(len(self.calls)), 'data': self.pages[len(self.calls)-1]}


class GithubTests(unittest.TestCase):
    def test_pagination_private_and_dedup(self):
        client = Client([[repo(1), repo(2, True)], [repo(2, True), repo(3)], []])
        result = list_repositories(client, 'example', per_page=2)
        self.assertEqual((result['total'], result['private_count'], result['public_count']), (3, 1, 2))
        self.assertEqual([c[1]['page'] for c in client.calls], ['1', '2', '3'])
        self.assertTrue(result['complete'])

    def test_empty(self):
        self.assertEqual(list_repositories(Client([[]]), 'example')['total'], 0)

    def test_stalled_and_truncated(self):
        for pages, limit, code in [([[repo(1)], [repo(1)]], 5, 'PAGINATION_STALLED'),
                                   ([[repo(1)]], 1, 'PAGINATION_LIMIT')]:
            with self.assertRaises(RequestError) as error:
                list_repositories(Client(pages), 'example', per_page=1, max_pages=limit)
            self.assertEqual(error.exception.code, code)

    def test_bad_response(self):
        for rows in ({}, [{'id': 1}], [repo(1) | {'private': 'true'}],
                     [repo(1) | {'full_name': 'other/repo'}]):
            with self.assertRaises(RequestError):
                list_repositories(Client([rows]), 'example')
