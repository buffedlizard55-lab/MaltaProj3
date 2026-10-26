"""Session arena-500519ba: pin the verifier rule for a money-backed upgrade.

`scripts/build.py::selected_fallback` lets a labelled money-backed researched
estimate replace a lowest-rung *model* row on purpose.  The four-hour publisher's
regression gate (`tests/test_22a3ed80_verification.py`, run before every collect
in `.github/workflows/pages.yml`) compares the rendered glance row with the
snapshot's own `analysis` block, so on the 2026-10-26T01:04:20Z publish it called
that documented replacement a hard failure for fixture 1093218 - a red gate that
would have frozen the next refresh.

These tests build a tiny synthetic site: the replacement must pass only when the
rendered numbers are exactly the published origination row's, on the same side,
and must still fail when the page shows something the published data does not.
"""
import importlib
import json
import tempfile
import unittest
from pathlib import Path

VERIFY = importlib.import_module('scripts.22a3ed80_verify')

SNAPSHOT = {
    'generated_at': '2026-10-26T01:04:20Z',
    'counts': {'inventory': 81, 'upcoming': 1, 'picks': 1, 'unresolved': 0},
    'matches': [{
        'id': '1093218',
        'teams': [{'id': '1', 'name': 'Nuclear TigeRES'}, {'id': '2', 'name': 'UNiTY'}],
        'starts_at': '2026-10-26T18:00:00Z',
        'availability': 'open',
        'analysis': {'method': 'model', 'label': 'Valve-rating research estimate',
                     'probabilities': [0.70665667, 0.29334333],
                     'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings'},
        'pick_index': 0,
        'source_url': 'https://www.hotspawn.com/matches/x-1093218',
    }],
}

ORIGINATION = {
    'generated_at': '2026-10-26T01:04:30Z',
    'counts': {'active': 1, 'with_pick': 1, 'unresolved': 0},
    'matches': [{
        'id': '1093218',
        'teams': [{'id': '1', 'name': 'Nuclear TigeRES'}, {'id': '2', 'name': 'UNiTY'}],
        'pick_index': 0,
        'featured_method': 'model',
        'upgraded_from_featured_model': True,
        'origination': {
            'method': 'consensus', 'label': 'Originated consensus line',
            'probabilities': [0.58275378, 0.41724622],
            'source_url': 'https://thunderpick.io/api/matches',
            'limitations': ['median of independent money sources'],
        },
    }],
}


def page(pick='Nuclear TigeRES', prob='58.3', other='41.7', method='consensus',
         source='https://thunderpick.io/api/matches'):
    return f'''<html><body>
<p>Picks at a glance</p>
<p id="picks-at-a-glance">1 active Hotspawn CS2 fixture, 1 with a directional pick</p>
<div class="mobile-status"><a>1</a> picks ready of 1 <a>0</a> unresolved</div>
<a class="internal-link" href="#picks-at-a-glance">picks</a>
<a class="internal-link" href="#unresolved-register">unresolved</a>
<a class="internal-link" href="#no-line-register">no line</a>
<a class="internal-link" href="#fallback-register">fallback</a>
<ol>
<li class="glance-row" data-glance-id="1093218" data-method="{method}">
  <span class="glance-pick-label">Pick</span><strong>{pick}</strong>
  <span class="glance-prob">{prob}%</span>
  <span class="glance-other">{other}%</span>
  <span class="badge">Median of books</span>
  <a href="https://www.hotspawn.com/matches/x-1093218">Hotspawn</a>
  <a href="{source}">Thunderpick</a>
</li>
</ol>
</body></html>'''


class UpgradeRuleTests(unittest.TestCase):
    def verify(self, html):
        directory = tempfile.mkdtemp()
        root = Path(directory)
        (root / 'snapshot.json').write_text(json.dumps(SNAPSHOT))
        (root / 'origination.json').write_text(json.dumps(ORIGINATION))
        (root / 'index.html').write_text(html)
        return VERIFY.verify(root)

    def row_problems(self, result):
        """Only the row-replay checks: the synthetic page does not impersonate
        the full executive summary, so the page-stamp/headline checks are out of
        scope here and are covered against the real build by 22a3ed80's suite."""
        return [c['detail'] for c in result['checks'] if c['name'] == 'row_problem']

    def replay_ok(self, result):
        return next(c['ok'] for c in result['checks'] if c['name'] == 'featured_rows_replay_exactly')

    def test_the_documented_upgrade_replays_from_the_published_row(self):
        result = self.verify(page())
        self.assertEqual(self.row_problems(result), [])
        self.assertTrue(self.replay_ok(result))
        row = result['rows'][0]
        self.assertIn('money-backed replacement', row['verification'])
        self.assertEqual(row['displayed_method'], 'consensus')
        self.assertEqual(row['rendered_probabilities'], [58.3, 41.7])

    def test_a_number_that_does_not_replay_from_the_published_row_still_fails(self):
        result = self.verify(page(prob='61.0', other='39.0'))
        self.assertFalse(self.replay_ok(result))
        self.assertIn('analysis gives', json.dumps(self.row_problems(result)))

    def test_a_different_side_is_not_accepted_as_the_same_upgrade(self):
        result = self.verify(page(pick='UNiTY'))
        self.assertFalse(self.replay_ok(result))

    def test_without_the_published_upgrade_flag_the_model_number_is_required(self):
        self.assertTrue(self.replay_ok(self.verify(page())))  # baseline
        ORIGINATION['matches'][0]['upgraded_from_featured_model'] = False
        try:
            result = self.verify(page())
        finally:
            ORIGINATION['matches'][0]['upgraded_from_featured_model'] = True
        self.assertFalse(self.replay_ok(result))

    def test_a_model_row_that_replays_unchanged_still_passes(self):
        result = self.verify(page(prob='70.7', other='29.3', method='model'))
        self.assertEqual(self.row_problems(result), [])
        self.assertTrue(self.replay_ok(result))
        self.assertIn('re-derived from the fixture analysis block',
                      result['rows'][0]['verification'])


if __name__ == '__main__':
    unittest.main()
