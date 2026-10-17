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


class EverySessionRegisterTests(unittest.TestCase):
    """Every declared register is valid, published and uniquely identified."""

    def test_every_declared_register_exists_and_validates(self):
        self.assertGreaterEqual(len(review_register.REGISTERS), 2)
        for relative in review_register.REGISTERS:
            path = ROOT / 'data' / relative
            self.assertTrue(path.exists(), relative)
            review_register.validate(json.loads(path.read_text()))

    def test_every_register_item_carries_a_source_link(self):
        for relative in review_register.REGISTERS:
            register = json.loads((ROOT / 'data' / relative).read_text())
            for item in register['items']:
                self.assertTrue(item['evidence'], item['id'])
                for evidence in item['evidence']:
                    self.assertTrue(evidence['url'].startswith('https://'), item['id'])
                    self.assertTrue(evidence['detail'].strip(), item['id'])

    def test_the_review_page_publishes_every_register_without_repeating_an_id(self):
        from scripts.build import build
        from bs4 import BeautifulSoup
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site'
            build(ROOT / 'data', out)
            soup = BeautifulSoup((out / 'review' / 'index.html').read_text(), 'html.parser')
            sections = soup.select('section[id^="session-review"]')
            self.assertEqual(len(sections), len(review_register.REGISTERS))
            ids = [s.get('id') for s in sections]
            self.assertEqual(len(ids), len(set(ids)))
            for relative in review_register.REGISTERS:
                self.assertTrue((out / 'data' / relative).exists(), relative)
            # Every published finding is visible on the page with its evidence.
            for relative in review_register.REGISTERS:
                register = json.loads((ROOT / 'data' / relative).read_text())
                for item in register['items']:
                    self.assertIsNotNone(soup.find(id='review-' + item['id']), item['id'])

    def test_no_element_id_is_repeated_on_the_review_page(self):
        """Two registers must not emit the page-wide blocks twice.

        The lineup-disambiguation block belongs to the page, not to a register.
        Rendering it once per register repeated its element ids, which breaks
        every in-page anchor that points at them.
        """
        from scripts.build import build
        from bs4 import BeautifulSoup
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'site'
            build(ROOT / 'data', out)
            soup = BeautifulSoup((out / 'review' / 'index.html').read_text(), 'html.parser')
            ids = [element.get('id') for element in soup.select('[id]')]
            repeated = sorted({i for i in ids if ids.count(i) > 1})
            self.assertEqual(repeated, [], 'repeated element ids: ' + ', '.join(repeated))

    def test_render_all_keeps_one_section_id_per_register(self):
        registers = [json.loads((ROOT / 'data' / relative).read_text())
                     for relative in review_register.REGISTERS]
        html = review_register.render_all(registers, '../', list(review_register.REGISTERS))
        self.assertEqual(html.count('id="session-review"'), 1)
        self.assertEqual(html.count('id="session-review-1"'), 1)


if __name__ == '__main__':
    unittest.main()
