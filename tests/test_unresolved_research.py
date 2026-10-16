"""The dedicated unresolved-picks research section must stay honest and dated.

These tests protect the contract of ``data/research/35440d12/unresolved-research.json``
and its renderer:

1. every published observation carries an official https source and its own
   observation time, so a reviewer can re-check it,
2. every fixture states an explicit resolution status — expected at the next
   refresh, or stays blank — and nothing renders as a guessed 50/50,
3. guidance-only quotes (wide books, placeholder odds) are visibly marked and
   never labeled book-validated,
4. the alias joins listed by the dossier are present in the reviewed registry
   with evidence and a declared competition scope.
"""
import json
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.unresolved_research import load_research, render_section

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data' / 'research' / '35440d12' / 'unresolved-research.json'
ALIASES = ROOT / 'data' / 'origination' / 'aliases.json'
FLAGS = ROOT / 'data' / 'research' / '35440d12' / 'flags.json'


def research():
    return load_research(DOSSIER)


class DossierContractTests(unittest.TestCase):
    def test_every_observation_is_https_and_timestamped(self):
        data = research()
        seen = 0
        for fixture in data['fixtures']:
            for check in fixture['checks']:
                self.assertTrue(check['sources'], check['stage'])
                for src in check['sources']:
                    self.assertTrue(src['url'].startswith('https://'), src)
                    self.assertTrue(src.get('observed_at'), src)
                    seen += 1
        for block in data.get('model_upgrades_available') or []:
            for src in block['sources']:
                self.assertTrue(src['url'].startswith('https://') and src.get('observed_at'))
                seen += 1
        self.assertGreater(seen, 25, 'the dossier should stay densely sourced')

    def test_every_fixture_has_identity_and_explicit_resolution(self):
        data = research()
        ids = []
        for fixture in data['fixtures']:
            ids.append(str(fixture['hotspawn_id']))
            stages = [c['stage'] for c in fixture['checks']]
            self.assertTrue(any('HLTV' in s for s in stages), fixture['hotspawn_id'])
            self.assertIn(fixture['resolution'], ('stays-unresolved', 'expected-at-next-refresh'))
            self.assertTrue(fixture.get('resolution_detail'))
        self.assertEqual(len(ids), 8, 'the 19:38Z snapshot had exactly eight unresolved fixtures')

    def test_no_guessed_default_probability(self):
        data = research()
        for fixture in data['fixtures']:
            for check in fixture['checks']:
                quote = check.get('guidance_quote')
                if not quote:
                    continue
                if quote.get('usable_under_contract') is False:
                    continue
                self.assertIn(check['verdict'], ('resolvable-via-verified-alias',), quote)

    def test_guidance_only_quotes_are_never_book_validated(self):
        data = research()
        for fixture in data['fixtures']:
            for check in fixture['checks']:
                quote = check.get('guidance_quote') or {}
                if quote.get('usable_under_contract') is False:
                    self.assertNotEqual(check['verdict'], 'resolvable-via-verified-alias')

    def test_preparation_sits_inside_the_research_window(self):
        data = research()
        window = data['research_window']
        self.assertLess(window['from'], window['to'])
        self.assertLessEqual(window['to'], data['prepared_at'])

    def test_reported_aliases_exist_in_the_reviewed_registry(self):
        data = research()
        registry = json.loads(ALIASES.read_text())['aliases']
        by_alias = {(entry['alias'], tuple(entry.get('applies_to') or [])): entry for entry in registry}
        for joined in data['aliases_added_this_session']:
            key = (joined['alias'], tuple(joined['applies_to']))
            self.assertIn(key, by_alias, key)
            entry = by_alias[key]
            self.assertEqual(entry['canonical'], joined['canonical'])
            self.assertTrue(entry.get('evidence'), 'every registry entry needs evidence links')
            self.assertTrue(entry.get('applies_to'), 'every registry entry must declare its scope')
            for ev in entry['evidence']:
                self.assertTrue(ev['url'].startswith('https://'), ev)

    def test_flags_file_is_in_the_published_shape(self):
        flags = json.loads(FLAGS.read_text())
        self.assertIsInstance(flags, list)
        self.assertGreaterEqual(len(flags), 1)
        for flag in flags:
            for key in ('id', 'severity', 'title', 'detail', 'match_ids', 'source_urls'):
                self.assertIn(key, flag)
            self.assertIn(flag['severity'], ('notice', 'warning'))
            for url in flag['source_urls']:
                self.assertTrue(url.startswith('https://'), url)


class RendererTests(unittest.TestCase):
    def body(self):
        return render_section(research(), '../')

    def test_sections_and_fixture_rows_render(self):
        soup = BeautifulSoup(self.body(), 'html.parser')
        for anchor in ['unresolved-research', 'unresolved-aliases', 'unresolved-limitations']:
            self.assertIsNotNone(soup.find(id=anchor), anchor)
        rows = soup.select('#unresolved-research tbody tr')
        self.assertEqual(len(rows), 8)

    def test_every_row_carries_a_source_or_an_unverified_marker(self):
        soup = BeautifulSoup(self.body(), 'html.parser')
        for row in soup.select('#unresolved-research tbody tr'):
            text = row.get_text(' ', strip=True)
            self.assertTrue('https://' in str(row) or 'unverified' in text, text[:80])

    def test_guidance_only_prices_render_with_the_rejection_marker(self):
        html = self.body()
        self.assertIn('guidance only', html)
        self.assertIn('book-validated', html)
        self.assertIn('stays blank', html)

    def test_limitations_are_published(self):
        from html import escape
        html = self.body()
        for item in research()['limitations']:
            self.assertIn(escape(item)[:60], html, item[:40])

    def test_loader_rejects_missing_sources(self):
        import tempfile
        data = json.loads(DOSSIER.read_text())
        broken = json.loads(json.dumps(data))
        broken['fixtures'][0]['checks'][0]['sources'] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'd.json'
            path.write_text(json.dumps(broken))
            with self.assertRaises(ValueError):
                load_research(path)
        unstamped = json.loads(json.dumps(data))
        unstamped['fixtures'][0]['checks'][0]['sources'][0].pop('observed_at')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'd.json'
            path.write_text(json.dumps(unstamped))
            with self.assertRaises(ValueError):
                load_research(path)


if __name__ == '__main__':
    unittest.main()
