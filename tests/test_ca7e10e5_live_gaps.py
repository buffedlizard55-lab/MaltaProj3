"""Session ca7e10e5: the live-coverage gap list must not contradict the snapshot.

The block renders "Live Hotspawn fixtures missing from this snapshot" from a
*dated research record* (``data/research/9fd5fbf1/live-coverage.json``). On the
published site at 2026-10-23T09:51Z that record (04:58Z) was compared by
Hotspawn id only, so JiJieHao vs Eternal Fire — whose record carried a blank id
— was published as "not in this snapshot" on the same page that resolved it
(1081606, open, market line). The section also described a 4.9-hour-old check
as cards "on Hotspawn right now".

These tests pin both corrections. They use synthetic data only; nothing here
reads or writes a published probability.
"""
from __future__ import annotations

import re
import unittest
from datetime import datetime, timezone

from scripts.build import live_coverage_gaps


def match(i, name_a, name_b, start='2099-01-01T10:00:00Z'):
    return {
        'id': str(i), 'competition': 'DraculaN Season 7', 'starts_at': start,
        'locks_at': start, 'availability': 'open',
        'source_url': 'https://www.hotspawn.com/matches/x',
        'teams': [{'name': name_a}, {'name': name_b}],
        'analysis': {'method': 'market', 'source': 'Polymarket',
                     'source_url': 'https://polymarket.com/event/x',
                     'probabilities': [0.555, 0.445]},
        'pick_index': 0,
    }


def gap_record(observed_at, fixtures):
    return {'_live_coverage': {'observed_at': observed_at, 'live_fixtures': fixtures}}


def text(html: str) -> str:
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html)).strip()


def section(html: str) -> str:
    found = re.search(r'<section class="content-section" id="live-coverage-gaps">.*?</section>',
                      html, re.S)
    assert found, 'the gap section was not rendered'
    return found.group(0)


class GapListNeverContradictsTheSnapshot(unittest.TestCase):
    """A fixture this build resolves is never also published as missing."""

    def setUp(self):
        self.data = {
            'generated_at': '2026-10-23T09:50:31Z',
            'matches': [match('1081606', 'JiJieHao', 'Eternal Fire')],
            **gap_record('2026-10-23T04:58:00Z', [{
                'id': None,
                'teams': ['JiJieHao', 'Eternal Fire'],
                'competition': 'DraculaN Season 7',
                'hltv_url': 'https://www.hltv.org/matches/2399638/jijiehao-vs-eternal-fire',
                'note': 'Lobby card had no permalink.',
            }]),
        }

    def test_a_blank_id_is_matched_by_team_names(self):
        html = live_coverage_gaps(self.data, '')
        self.assertIn('id="live-coverage-gaps"', html)
        self.assertNotIn('JiJieHao vs Eternal Fire', text(section(html)))

    def test_name_matching_is_order_and_whitespace_insensitive(self):
        # name_key normalises case, Unicode and whitespace only; the project does
        # not allow fuzzy or punctuation-only joins, so that is what is asserted.
        self.data['matches'] = [match('1', 'ex-Zero Tenacity', 'BESTIA Academy')]
        self.data.update(gap_record('2026-10-23T04:58:00Z', [{
            'id': '999',
            'teams': ['BESTIA  Academy', 'EX-ZERO  TENACITY'],
            'competition': 'Test',
        }]))
        html = live_coverage_gaps(self.data, '')
        self.assertNotIn('BESTIA Academy vs EX-ZERO TENACITY', text(section(html)))

    def test_a_different_pairing_with_the_same_first_team_is_still_reported(self):
        self.data['matches'] = [match('1', 'JiJieHao', 'Somebody Else')]
        html = live_coverage_gaps(self.data, '')
        self.assertIn('JiJieHao vs Eternal Fire', text(section(html)))

    def test_the_header_count_matches_the_rendered_rows(self):
        self.data['matches'] = [match('1', 'A', 'B')]
        self.data.update(gap_record('2026-10-23T04:58:00Z', [
            {'id': '1081605', 'teams': ['Phantom Academy', 'Banda chuya'],
             'competition': 'CCT', 'hotspawn_url': 'https://www.hotspawn.com/matches/p-1081605'},
            {'id': '1081149', 'teams': ['FORZE Reload', 'LFO 10'],
             'competition': 'CCT', 'hotspawn_url': 'https://www.hotspawn.com/matches/f-1081149'},
        ]))
        html = live_coverage_gaps(self.data, '')
        self.assertEqual(text(section(html)).count('Not in this snapshot'), 2)
        self.assertEqual(text(section(html)).count('1081605'), 1)
        header = re.search(r'<span class="muted small">(\d+)', html)
        self.assertIsNotNone(header, 'the section header carries no count')
        self.assertEqual(header.group(1), '2')


class GapListNeverClaimsAnUnverifiedState(unittest.TestCase):
    """The record is dated; the page must not describe it as live truth."""

    def setUp(self):
        self.data = {
            'generated_at': '2026-10-23T09:50:31Z',
            'matches': [],
            **gap_record('2026-10-23T04:58:00Z', [{
                'id': '1081872',
                'teams': ['NEXVOID', 'Rare Atom'],
                'competition': 'VOID Autumn Cup 2026',
                'hotspawn_url': 'https://www.hotspawn.com/matches/nexvoid-vs-rare-atom-1081872',
                'in_published_snapshot': True,
            }]),
        }

    def test_the_phrase_right_now_is_gone(self):
        html = live_coverage_gaps(self.data, '')
        self.assertNotIn('right now', text(section(html)).lower())

    def test_the_section_describes_itself_as_a_dated_observation(self):
        # The merged implementation (sessions 9c4b1f7a / ca7e10e5) states that the
        # list is a dated observation rather than a live claim, and prints the
        # record's own observation time next to the snapshot it was compared with.
        html = live_coverage_gaps(self.data, '')
        body = text(section(html))
        self.assertIn('dated observation', body)
        self.assertIn('not a live claim', body)
        self.assertIn('data-time="2026-10-23T04:58:00Z"', html)

    def test_a_card_that_is_still_absent_keeps_its_own_note(self):
        # This record's only card is the one the snapshot already resolves, so it
        # is correctly dropped from the list above (that is the point of the
        # preceding test). An absent card's own note has to survive, so add a
        # second card that this build genuinely does not contain.
        self.data['_live_coverage']['live_fixtures'][0]['note'] = 'Lobby card had no permalink.'
        self.data['_live_coverage']['live_fixtures'].append({
            'id': None,
            'teams': ['Some Other Team', 'Another Team'],
            'competition': 'DraculaN Season 7',
            'hltv_url': 'https://www.hltv.org/matches/1/x',
            'note': 'Lobby card had no permalink.',
        })
        body = text(section(live_coverage_gaps(self.data, '')))
        self.assertIn('Lobby card had no permalink.', body)
        self.assertIn('Some Other Team vs Another Team', body)

    def test_no_probability_or_percent_is_ever_added(self):
        for html in (live_coverage_gaps(self.data, ''),
                     live_coverage_gaps({**self.data, 'matches': [
                         match('1', 'JiJieHao', 'Eternal Fire')]}, '')):
            self.assertNotIn('%', section(html))
            self.assertNotIn('pick:', text(section(html)).lower())


class PublishedRecordStaysDated(unittest.TestCase):
    """The shared research record this section renders is still dated and linked."""

    def test_record_carries_an_observation_time_and_official_urls(self):
        import json
        from pathlib import Path
        record = json.loads(Path('data/research/9fd5fbf1/live-coverage.json').read_text())
        self.assertRegex(record['observed_at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
        self.assertTrue(all(url.startswith('https://') for url in record['source_urls']))
        datetime.strptime(record['observed_at'], '%Y-%m-%dT%H:%M:%SZ').replace(
            tzinfo=timezone.utc)


if __name__ == '__main__':
    unittest.main()


class EvidenceStaysOutOfTheLinkChecker(unittest.TestCase):
    """Captured third-party pages must never be saved as .html inside data/.

    scripts.build copies data/ into site/data/, and scripts.validate.check_links
    walks every *.html under the site. A captured page saved as index.html was
    therefore parsed as one of this site's own pages, and its relative asset URLs
    (./assets/scout-mark.svg) failed the build on 2026-10-23. Evidence files keep
    a .txt or .json suffix instead.
    """

    def test_no_html_file_is_kept_under_data(self):
        from pathlib import Path
        offenders = [str(p) for p in Path('data').rglob('*.html')]
        self.assertEqual(offenders, [], 'captured HTML under data/ breaks the link check')

    def test_the_probe_writes_txt_suffixed_captures(self):
        from pathlib import Path
        source = Path('scripts/ca7e10e5_probe.py').read_text()
        self.assertIn("'published-index.html.txt'", source)
        self.assertIn("'published-latest.json'", source)
        self.assertNotIn("('index.html', page)", source)
