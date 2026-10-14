"""Publication permission/order tests; synthetic metadata, never match data."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from scripts.publication import configure


def response(body, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode()
    result.url = 'https://api.github.com/repos/example/project/pages'
    return result


def legacy_run(status='completed'):
    return response({'workflow_runs': [{'name': 'pages-build-deployment', 'id': 1, 'head_sha': 'synthetic', 'status': status, 'conclusion': 'success' if status == 'completed' else None}]})


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.original = {'flags': [], 'sources': [], 'requests': [], 'inventory_observed_at': '2026-10-14T04:00:00Z', 'coverage_complete': True, 'counts': {'inventory': 0}}
        (self.root / 'latest.json').write_text(json.dumps(self.original))
        self.session = Mock()

    def tearDown(self):
        self.temporary.cleanup()

    def configure(self, **kwargs):
        with patch('builtins.print'):
            return configure(self.root, 'example/project', 'synthetic', 'secret-token', session=self.session, pause=0, **kwargs)

    def test_workflow_mode_does_not_request_an_unnecessary_setting_change(self):
        self.session.get.return_value = response({'build_type': 'workflow'})
        result = self.configure()
        self.assertEqual(result['final_build_type'], 'workflow')
        self.session.put.assert_not_called()
        self.assertFalse(json.loads((self.root / 'latest.json').read_text())['flags'])

    def test_legacy_build_finishes_before_mode_change_or_publication(self):
        self.session.get.side_effect = [response({'build_type': 'legacy'}), legacy_run('in_progress'), legacy_run(), response({'build_type': 'workflow'})]
        self.session.put.return_value = response({}, 204)
        result = self.configure()
        self.assertEqual(result['legacy_runs'][0]['status'], 'completed')
        self.assertEqual(result['final_build_type'], 'workflow')
        self.assertEqual(self.session.get.call_count, 4)
        self.assertEqual(self.session.put.call_count, 1)

    def test_restricted_setting_is_flagged_not_a_deployment_blocker(self):
        self.session.get.side_effect = [response({'build_type': 'legacy'}), legacy_run(), response({'build_type': 'legacy'})]
        self.session.put.return_value = response({'message': 'Restricted secret-token'}, 403)
        result = self.configure()
        data = json.loads((self.root / 'latest.json').read_text())
        self.assertEqual(result['final_build_type'], 'legacy')
        self.assertEqual(data['flags'][0]['id'], 'pages-publication-mode')
        self.assertEqual(data['inventory_observed_at'], self.original['inventory_observed_at'])
        self.assertEqual(data['counts'], self.original['counts'])
        self.assertNotIn('secret-token', (self.root / 'evidence/pages-configuration.json').read_text())
        self.assertNotIn('secret-token', (self.root / 'latest.json').read_text())


    def test_setting_network_failure_can_publish_after_verified_readback(self):
        self.session.get.side_effect = [response({'build_type': 'legacy'}), legacy_run(), response({'build_type': 'legacy'})]
        self.session.put.side_effect = requests.Timeout('Setting update timed out')
        result = self.configure()
        self.assertEqual(result['final_build_type'], 'legacy')
        self.assertIsNone(result['update_http_status'])
        self.assertIn('timed out', result['update_error'])
        self.assertTrue(json.loads((self.root / 'latest.json').read_text())['flags'])

    def test_building_site_does_not_treat_delayed_run_listing_as_complete(self):
        self.session.get.side_effect = [response({'build_type': 'legacy', 'status': 'building'}), response({'workflow_runs': []}), legacy_run(), response({'build_type': 'workflow'})]
        self.session.put.return_value = response({}, 204)
        result = self.configure()
        self.assertEqual(result['legacy_runs'][0]['status'], 'completed')
        self.assertEqual(self.session.get.call_count, 4)

    def test_running_legacy_publisher_times_out_without_mutating_data(self):
        self.session.get.side_effect = [response({'build_type': 'legacy'}), legacy_run('in_progress'), legacy_run('queued')]
        with self.assertRaisesRegex(TimeoutError, 'refusing a competing deployment'):
            self.configure(attempts=2)
        self.session.put.assert_not_called()
        self.assertEqual(json.loads((self.root / 'latest.json').read_text()), self.original)

    def test_unknown_mode_is_not_invented(self):
        self.session.get.return_value = response({'build_type': 'unknown'})
        with self.assertRaisesRegex(ValueError, 'Unrecognized Pages build mode'):
            self.configure()
        self.assertEqual(json.loads((self.root / 'latest.json').read_text()), self.original)

    def test_unverified_api_response_does_not_mutate_data(self):
        self.session.get.return_value = response({'message': 'Forbidden'}, 403)
        with self.assertRaises(requests.HTTPError):
            self.configure()
        self.assertEqual(json.loads((self.root / 'latest.json').read_text()), self.original)


if __name__ == '__main__':
    unittest.main()
