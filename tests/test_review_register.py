"""Session c07e1b40 review register: every finding is source-linked and published."""
import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import review_register

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / 'data' / review_register.REGISTER


class ReviewRegisterTests(unittest.TestCase):
    def setUp(self):
        self.register = json.loads(REGISTER.read_text())

    def test_every_item_has_a_known_status_and_https_evidence(self):
        review_register.validate(self.register)
        for item in self.register['items']:
            self.assertIn(item['status'], review_register.STATUS)
            self.assertTrue(all(ev['url'].startswith('https://') for ev in item['evidence']), item['id'])

    def test_unlinked_or_unknown_items_are_rejected(self):
        bad = copy.deepcopy(self.register)
        bad['items'][0]['evidence'][0]['url'] = 'http://example.com'
        with self.assertRaises(ValueError):
            review_register.validate(bad)
        bad = copy.deepcopy(self.register)
        bad['items'][0]['status'] = 'probably fine'
        with self.assertRaises(ValueError):
            review_register.validate(bad)

    def test_render_escapes_text_and_lists_every_item(self):
        data = copy.deepcopy(self.register)
        data['items'][0]['finding'] = '<script>x</script>'
        html = review_register.render(data, '../')
        self.assertNotIn('<script>x', html)
        for item in self.register['items']:
            self.assertIn(f'id="review-{item["id"]}"', html)

    def test_flagged_for_review_page_publishes_the_register(self):
        from scripts.build import build
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site'
            build(ROOT / 'data', out)
            page = (out / 'review' / 'index.html').read_text()
            self.assertIn('id="session-review"', page)
            self.assertIn('id="lineup-disambiguation"', page)
            self.assertTrue((out / 'data' / review_register.REGISTER).exists())


if __name__ == '__main__':
    unittest.main()
