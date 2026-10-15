"""GitHub API requests are authenticated, other hosts never see the token, and nothing records it.

Evidence (run 38824422956, GitHub-hosted runner): unauthenticated api.github.com answered HTTP 403 with
x-ratelimit-remaining 0 of 60; the workflow token got HTTP 200 and a limit of 5000. Synthetic inputs only.
"""
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_edge, originate, sources
from scripts.github_auth import auth_headers

ROOT = Path(__file__).resolve().parents[1]
VALVE_DIR = 'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/contents/live/2026'


class AuthHeaders(unittest.TestCase):
    def test_the_token_goes_to_the_github_api_over_https_only(self):
        env = {'GITHUB_TOKEN': 'tok-123'}
        headers = auth_headers(VALVE_DIR, env)
        self.assertEqual(headers['Authorization'], 'Bearer tok-123')
        self.assertEqual(headers['X-GitHub-Api-Version'], '2022-11-28')

    def test_no_other_host_ever_gets_it(self):
        env = {'GITHUB_TOKEN': 'tok-123'}
        for url in ['https://raw.githubusercontent.com/ValveSoftware/x/main/a.md', 'https://github.com/ValveSoftware/x', 'https://polymarket.com/esports/cs2',
                    'https://gamma-api.polymarket.com/events', 'https://thunderpick.io/api/matches', 'https://www.hltv.org/matches',
                    'https://api.github.com.evil.example/repos', 'https://evil.example/api.github.com', 'http://api.github.com/repos/x',
                    'https://play.hotspawn.com/lobby', '']:
            self.assertEqual(auth_headers(url, env), {}, url)

    def test_without_a_token_nothing_is_added_and_gh_token_is_a_fallback(self):
        self.assertEqual(auth_headers(VALVE_DIR, {}), {})
        self.assertEqual(auth_headers(VALVE_DIR, {'GITHUB_TOKEN': ''}), {})
        self.assertEqual(auth_headers(VALVE_DIR, {'GH_TOKEN': 'alt'})['Authorization'], 'Bearer alt')
        self.assertEqual(auth_headers(VALVE_DIR, {'GITHUB_TOKEN': 'first', 'GH_TOKEN': 'alt'})['Authorization'], 'Bearer first')


class FakeResponse:
    status_code = 200
    content = b'[]'
    headers = {'Content-Type': 'application/json'}
    text = '[]'
    url = 'https://example.test/'

    def raise_for_status(self):
        pass

    def json(self):
        return []


class FakeSession:
    def __init__(self):
        self.calls = []
        self.headers = {}

    def request(self, method, url, **kw):
        self.calls.append((url, kw.get('headers') or {}))
        return FakeResponse()

    def get(self, url, **kw):
        return self.request('GET', url, **kw)


class ClientsAttachTheTokenCorrectly(unittest.TestCase):
    def check(self, make_client, fetch):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'GITHUB_TOKEN': 'tok-secret-123'}):
            client = make_client(Path(tmp))
            client.session = FakeSession()
            client.last_request = client.last = 0.0  # no politeness delay needed in a test
            fetch(client, VALVE_DIR, 'valve-directory')
            fetch(client, 'https://gamma-api.polymarket.com/events/1', 'polymarket-event-1')
            by_url = dict(client.session.calls)
            self.assertEqual(by_url[VALVE_DIR].get('Authorization'), 'Bearer tok-secret-123')
            self.assertNotIn('Authorization', by_url['https://gamma-api.polymarket.com/events/1'])
            manifest = getattr(client, 'manifest', None) or getattr(client, 'requests', [])
            self.assertTrue(manifest)
            self.assertNotIn('tok-secret-123', json.dumps(manifest))
            for path in Path(tmp).rglob('*.json'):
                self.assertNotIn('tok-secret-123', path.read_text())

    def test_featured_collector_client(self):
        self.check(sources.Client, lambda c, url, label: c.json(url, label))

    def test_origination_collector(self):
        self.check(originate.Collector, lambda c, url, label: c.get_json(url, label))


class EdgeEvidenceLink(unittest.TestCase):
    def test_link_only_when_the_file_exists_otherwise_an_unverified_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / 'evidence').mkdir()
            self.assertIn('not present in this snapshot', build_edge.saved_evidence_link('data/evidence/valve-ratings.json', data))
            self.assertIn('unverified', build_edge.saved_evidence_link('data/evidence/valve-ratings.json', data))
            (data / 'evidence' / 'valve-ratings.json').write_text('{}')
            link = build_edge.saved_evidence_link('data/evidence/valve-ratings.json', data)
            self.assertIn('<a href="../data/evidence/valve-ratings.json">', link)

    def test_without_a_data_directory_the_old_behaviour_is_kept(self):
        self.assertIn('<a href="../data/evidence/valve-ratings.json">', build_edge.saved_evidence_link('data/evidence/valve-ratings.json', None))


class WorkflowsPassTheToken(unittest.TestCase):
    def steps(self, name):
        text = (ROOT / '.github/workflows' / name).read_text()
        return [b for b in re.split(r'\n      - ', text) if 'run:' in b]

    def test_every_step_that_runs_a_collector_receives_the_workflow_token(self):
        for name in ('pages.yml', 'origination.yml'):
            seen = 0
            for block in self.steps(name):
                if re.search(r'run: python -m scripts\.(collect|originate --live)(\n|$)', block):
                    seen += 1
                    self.assertIn('GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}', block, name + ': ' + block.split('\n')[0])
            self.assertEqual(seen, 2, name)


if __name__ == '__main__':
    unittest.main()
