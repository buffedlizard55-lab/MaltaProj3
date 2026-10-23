"""Session arena-3a010437: the dated re-read is published, and it stays honest.

Two renderings are pinned here:

* the compact strip on the executive summary — counts and a link only, never a
  new probability or pick, and never a silent claim about a snapshot it did not
  audit;
* the row-by-row table on the coverage page — every row keeps a link to an
  official source (the repo's row-source rule), and a research-model row says
  outright that there is no price to re-read instead of looking verified.

The loader is also pinned: other sessions' `verification.json` files have a
different schema and must not be rendered as if they were this record.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build import load_verification, verification_section, verification_strip


def record(rows=None, *, finished='2026-10-23T09:53:31Z', snapshot='2026-10-23T09:23:57Z',
           missing=None, **overrides):
    doc = {
        'schema_version': 1,
        'session': 'arena-3a010437',
        'finished_at': finished,
        'snapshot': {'inventory_generated_at': snapshot, 'active_rows': len(rows or [])},
        'thresholds': {'drift_ok': 0.05},
        'totals': {'confirmed': 1},
        'rows': rows if rows is not None else [row()],
        'live_inventory': {'checked': True, 'official_records': 92, 'not_in_snapshot': missing or []},
        '_path': 'data/research/3a010437/verification.json',
        '_markdown': 'data/research/3a010437/verification.md',
    }
    doc.update(overrides)
    return doc


def row(verdict='confirmed', method='market', **overrides):
    doc = {
        'id': '1079655', 'teams': ['Nuclear TigeRES', 'ILLYRIANS'],
        'competition': 'CCT Europe 2026 Series #11',
        'method': method, 'source': 'Polymarket',
        'source_url': 'https://polymarket.com/event/cs2-ntr-ill4-2026-10-23',
        'hotspawn_url': 'https://www.hotspawn.com/matches/nuclear-tigeres-vs-illyrians-cct-europe-2026-series-11-1079655',
        'published_probabilities': [0.845, 0.155], 'published_pick_index': 0,
        'identity': {'status': 'confirmed', 'api_start': '2026-10-23T11:00:00Z'},
        'price': {'checked': True, 'api': 'https://gamma-api.polymarket.com/events/1233761',
                  'comparisons': [{'outcome': 'Nuclear TigeRES', 'price': 0.85, 'delta': 0.005},
                                  {'outcome': 'ILLYRIANS', 'price': 0.15, 'delta': -0.005}],
                  'max_abs_delta': 0.005, 'price_survives': True, 'pick_still_favoured': True},
        'verdict': verdict,
    }
    doc.update(overrides)
    return doc


class Strip(unittest.TestCase):
    def test_absent_without_a_record(self):
        self.assertEqual(verification_strip({'generated_at': 'x'}, ''), '')

    def test_counts_links_and_no_new_probability(self):
        html = verification_strip({'_verification': record(), 'generated_at': '2026-10-23T09:23:57Z'}, '')
        self.assertIn('id="independent-verification"', html)
        self.assertIn('coverage/#independent-verification', html)
        self.assertIn('1 / 1', html)  # identity count uses the record's own row count
        self.assertIn('no betting price to re-read', html)
        self.assertNotIn('85%', html)
        self.assertNotIn('Pick ', html)

    def test_it_says_when_it_audited_a_different_snapshot(self):
        html = verification_strip({'_verification': record(), 'generated_at': '2026-10-24T00:00:00Z'}, '')
        self.assertIn('describes the previous publication', html)

    def test_a_conflict_is_announced_not_hidden(self):
        doc = record([row('pick_disagrees')])
        html = verification_strip({'_verification': doc, 'generated_at': doc['snapshot']['inventory_generated_at']}, '')
        self.assertIn('need review', html)


class Section(unittest.TestCase):
    def test_every_row_keeps_an_official_link(self):
        html = verification_section({'_verification': record([row(), row('model_not_a_line', method='model')]),
                                     'generated_at': '2026-10-23T09:23:57Z'}, '')
        self.assertEqual(html.count('<tr><th scope="row">'), 2)
        for chunk in html.split('<tr><th scope="row">')[1:]:
            self.assertTrue('https://www.hotspawn.com/matches/' in chunk or
                            'gamma-api.polymarket.com' in chunk or
                            'polymarket.com/event' in chunk)

    def test_a_model_row_does_not_look_price_verified(self):
        model = row('model_not_a_line', method='model',
                    source_url='https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/x.md',
                    price={'checked': False, 'reason': 'research-model estimate: there is no published price to re-read'})
        html = verification_section({'_verification': record([model]), 'generated_at': '2026-10-23T09:23:57Z'}, '')
        self.assertIn('no price exists to re-read (research model)', html)
        self.assertIn('cited model input', html)

    def test_reachability_is_labelled_and_linked(self):
        other = row('source_reachable', method='bookmaker',
                    source_url='https://bo3.gg/matches/x',
                    price={'checked': True, 'http_status': 200, 'url': 'https://bo3.gg/matches/x'})
        html = verification_section({'_verification': record([other]), 'generated_at': '2026-10-23T09:23:57Z'}, '')
        self.assertIn('reachability only', html)
        self.assertIn('https://bo3.gg/matches/x', html)


class Loader(unittest.TestCase):
    def test_it_picks_the_newest_eligible_record_and_ignores_foreign_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'research/a').mkdir(parents=True)
            (root / 'research/b').mkdir(parents=True)
            (root / 'research/c').mkdir(parents=True)
            (root / 'research/a/verification.json').write_text(json.dumps(record(finished='2026-10-23T01:00:00Z')))
            (root / 'research/b/verification.json').write_text(json.dumps(record(finished='2026-10-23T09:00:00Z')))
            # Another session's file with the same name but a different schema.
            (root / 'research/c/verification.json').write_text(json.dumps({'checks': [], 'generated_at': '2026-10-23T23:00:00Z'}))
            loaded = load_verification(root)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded['finished_at'], '2026-10-23T09:00:00Z')
            self.assertEqual(loaded['_path'], 'data/research/b/verification.json')

    def test_no_records_means_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_verification(Path(tmp)))


if __name__ == '__main__':
    unittest.main()


class LineResearchSection(unittest.TestCase):
    """The dated HLTV-first search behind the research-model rows."""

    def record(self):
        return {
            'observed_at': '2026-10-23T10:19:06Z',
            'surfaces': [{'name': 'HLTV match listing', 'url': 'https://www.hltv.org/matches',
                          'http_status': 200},
                         {'name': 'GG.BET esportsbook', 'url': 'https://gg.bet/x', 'http_status': 403}],
            'conclusions': {'bo3_relay_two_sided': 0},
            'fixtures': [{
                'hotspawn_id': '1081605',
                'teams': ['Phantom Academy', 'Banda chuya'],
                'competition': 'CCT Europe 2026 Challengers #8',
                'hotspawn_url': 'https://www.hotspawn.com/matches/phantom-academy-vs-banda-chuya-cct-europe-2026-challengers-8-1081605',
                'bo3_relay_two_sided_quote_present': False,
                'sources_tried_from_published_trail': [
                    {'stage': 'HLTV research', 'status': 'checked',
                     'source_url': 'https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya',
                     'detail': 'Exact teams/time confirmed on HLTV. No prematch price published.'},
                    {'stage': 'Original esportsbook lines', 'status': 'unresolved',
                     'source_url': 'https://thunderpick.io/esports/counter-strike',
                     'detail': 'No unique validated pair of original bookmaker odds available.'},
                ],
            }],
        }

    def test_absent_without_a_record(self):
        from scripts.build import line_research_section
        self.assertEqual(line_research_section({}, ''), '')

    def test_each_row_keeps_its_own_sources_and_says_no_price_was_taken(self):
        from scripts.build import line_research_section
        html = line_research_section({'_line_research': self.record()}, '')
        self.assertIn('id="no-line-line-research"', html)
        self.assertIn('Phantom Academy vs Banda chuya', html)
        self.assertIn('https://www.hltv.org/matches/2399699/', html)
        self.assertIn('no two-sided quote published', html)
        self.assertIn('Reachability is not a price', html)
        self.assertIn('1 of 2 probed surfaces answered', html)
        # No probability is introduced by this section.
        self.assertNotIn('%', html)
