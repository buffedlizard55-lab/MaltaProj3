"""Post-deploy parity checks exercised against a real build; no network access."""
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import Mock, patch

import requests

from scripts.build import build
from scripts.verify_live import verify

ROOT = Path(__file__).resolve().parents[1]


class PublicArtifactParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.site = Path(cls.temp.name) / 'site'
        build(ROOT / 'data', cls.site)
        cls.expected = json.loads((ROOT / 'data/latest.json').read_text())

    def setUp(self):
        self.overrides = {}

    def fetch(self, url, **kwargs):
        route = urlparse(url).path.removeprefix('/MaltaProj3/')
        file = self.site / (route or 'index.html')
        if file.is_dir(): file = file / 'index.html'
        response = requests.Response()
        response.url = url
        response.status_code = 200 if file.exists() else 404
        response._content = self.overrides.get(route, file.read_bytes() if file.exists() else b'Not found')
        return response

    def verify(self):
        session = Mock(headers={}, get=Mock(side_effect=self.fetch))
        with patch('scripts.verify_live.requests.Session', return_value=session), patch('builtins.print'):
            return verify('https://example.invalid/MaltaProj3/', self.expected)

    def twc_data(self):
        return json.loads((self.site / 'data/twc-day3-picks.json').read_text())

    def test_all_public_views_verify_for_the_generated_artifact(self):
        self.assertEqual(self.verify(), 'https://example.invalid/MaltaProj3/')

    def test_twc_json_cannot_silently_omit_both_deciders(self):
        data = self.twc_data(); data['day3_matches'] = []
        self.overrides['data/twc-day3-picks.json'] = json.dumps(data).encode()
        with self.assertRaisesRegex(ValueError, 'omits or invents a decider'): self.verify()

    def test_twc_cannot_use_another_inventory_snapshot(self):
        data = self.twc_data(); data['source_snapshot_at'] = '2020-01-01T00:00:00Z'
        self.overrides['data/twc-day3-picks.json'] = json.dumps(data).encode()
        with self.assertRaisesRegex(ValueError, 'this inventory snapshot'): self.verify()

    def test_same_date_but_old_static_twc_template_is_rejected(self):
        self.overrides['twc-picks/'] = (self.site / 'picks/index.html').read_bytes()
        with self.assertRaisesRegex(ValueError, 'replaced'): self.verify()

    def test_even_blank_probability_cells_must_match_generated_json(self):
        from bs4 import BeautifulSoup
        html = BeautifulSoup((self.site / 'twc-picks/index.html').read_text(), 'html.parser')
        html.select_one('.twc-prob strong').string = '55.5%'
        self.overrides['twc-picks/'] = str(html).encode()
        with self.assertRaisesRegex(ValueError, 'HTML probabilities'): self.verify()
