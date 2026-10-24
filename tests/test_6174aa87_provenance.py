"""Offline checks for the pick-provenance sweep (session arena-6174aa87).

The sweep itself runs on a GitHub runner because the coding sandbox has no
egress. These tests drive the same pure functions with saved bodies, so the
verdict logic, the flag schema and the rendered dossier are provable without a
network read. No probability, pick or alias is asserted here: every fixture
below is synthetic.
"""
from __future__ import annotations

import importlib
import json
import re
import unittest

# Module names may not start with a digit in an import statement; existing
# session tests in this repository load theirs the same way.
probe = importlib.import_module('scripts.6174aa87_probe')


def fake_fetch(bodies: dict, default: str = 'ok'):
    """A fetcher that answers from a URL -> body map."""

    def fetcher(url: str, **kwargs) -> dict:
        body = bodies.get(url)
        if body is None:
            return {'name': 'citation', 'url': url, 'http': 403, 'status': 'http-403',
                    'bytes': 0, 'sha256': None, 'title': '', 'challenge': False,
                    'error': None, '_body': ''}
        if isinstance(body, tuple):
            status, text = body
            return {'name': 'citation', 'url': url, 'http': status,
                    'status': 'ok' if status < 400 else 'http-%d' % status,
                    'bytes': len(text), 'sha256': probe.sha(text), 'title': '',
                    'challenge': False, 'error': None, '_body': text}
        return {'name': 'citation', 'url': url, 'http': 200, 'status': 'ok',
                'bytes': len(body), 'sha256': probe.sha(body), 'title': '',
                'challenge': False, 'error': None, '_body': body}

    return fetcher


SNAPSHOT = {
    'generated_at': '2026-10-24T14:24:32Z',
    'matches': [
        {
            'id': '1083121',
            'teams': [{'id': '1', 'name': 'Projeto do KinGui'},
                      {'id': '2', 'name': 'MEIA NOITE'}],
            'competition': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-24T16:00:00Z',
            'locks_at': '2026-10-24T15:54:00Z',
            'availability': 'open',
            'source_url': 'https://www.hotspawn.com/matches/meia-noite-vs-projeto-do-kingui-cct-south-america-2026-series-7-1083121',
            'analysis': None,
            'pick_index': None,
            'research': [
                {'stage': 'HLTV identity review',
                 'source_url': 'https://www.hltv.org/matches/2399913/tropa-do-kingui-vs-meia-noite',
                 'status': 'checked', 'detail': 'identity only'},
                {'stage': 'GG.BET esportsbook',
                 'source_url': 'https://gg.bet/en-is/next-to-go?hoursAhead=168',
                 'status': 'unavailable', 'detail': '403'},
            ],
        },
        {
            'id': '1082996',
            'teams': [{'name': 'Acend'}, {'name': 'UNiTY'}],
            'competition': 'NODWIN Clutch Series #13',
            'starts_at': '2026-10-25T09:00:00Z',
            'availability': 'open',
            'source_url': 'https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996',
            'analysis': {'method': 'model', 'label': 'Valve-rating research estimate',
                         'probabilities': [0.542, 0.458], 'source': 'Valve',
                         'source_url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                         'observed_at': '2026-10-24T14:24:28Z'},
            'pick_index': 0,
            'research': [],
        },
        {
            'id': '1083999',
            'teams': [{'name': 'Ghost A'}, {'name': 'Ghost B'}],
            'competition': 'Unlisted Cup',
            'starts_at': '2026-10-26T09:00:00Z',
            'availability': 'open',
            'source_url': 'https://www.hotspawn.com/matches/ghost-a-vs-ghost-b-unlisted-cup-1083999',
            'analysis': None,
            'pick_index': None,
            'research': [],
        },
    ],
}

ORIGINATION = {
    'generated_at': '2026-10-24T14:24:30Z',
    'matches': [
        {
            'id': '1083121',
            'pick_index': 0,
            'aliases_used': ['Tropa do KinGui -> Projeto do KinGui'],
            'origination': {
                'method': 'market', 'label': 'Originated consensus line',
                'probabilities': [0.666, 0.334], 'source': 'Polymarket',
                'source_url': 'https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24',
                'observed_at': '2026-10-24T14:24:20Z',
                'quotes': [
                    {'provider': 'Polymarket', 'family': 'polymarket',
                     'odds': [1.55, 2.75], 'observed_at': '2026-10-24T14:24:20Z',
                     'source_url': 'https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24',
                     'event_id': None},
                    {'provider': 'Thunderpick', 'family': 'thunderpick',
                     'odds': [1.50, 2.80], 'observed_at': '2026-10-24T14:24:22Z',
                     'source_url': 'https://thunderpick.io/api/matches',
                     'event_id': '2767837'},
                ],
                'model_crosscheck': None, 'limitations': ['thin market'],
            },
            'research': [],
        },
    ],
}

API_BODY = json.dumps([
    {'id': 1083121, 'participants0_name': 'Projeto do KinGui',
     'participants1_name': 'MEIA NOITE', 'competition_name': 'CCT South America 2026 Series #7',
     'scheduled_start_time': 1792857600000},
    {'id': 1083999, 'participants0_name': 'Ghost A', 'participants1_name': 'Ghost B',
     'competition_name': 'Unlisted Cup', 'scheduled_start_time': 1792944000000},
    {'id': 1083777, 'participants0_name': 'Late One', 'participants1_name': 'Late Two',
     'competition_name': 'Late Cup', 'scheduled_start_time': 1793030400000},
])


class NormalisationTests(unittest.TestCase):
    def test_accents_and_punctuation_are_removed(self):
        self.assertEqual(probe.normalize('Grêmio  vs  Yawara!'), 'gremio vs yawara')
        self.assertEqual(probe.normalize('LFO 10'), 'lfo 10')

    def test_distinctive_tokens_drop_generic_words(self):
        self.assertEqual(probe.tokens('Spirit Academy'), ['spirit'])
        self.assertIn('kingui', probe.tokens('Projeto do KinGui'))

    def test_name_presence_levels(self):
        body = 'Tropa do KinGui will face MEIA NOITE tonight'
        self.assertEqual(probe.name_presence(body, 'MEIA NOITE')['level'], 'full')
        self.assertEqual(probe.name_presence(body, 'Projeto do KinGui')['level'], 'token')
        self.assertEqual(probe.name_presence(body, 'Some Other Team')['level'], 'absent')

    def test_title_is_extracted(self):
        self.assertEqual(probe.extract_title('<html><title> A  &amp; B </title></html>'),
                         'A &amp; B')

    def test_generic_endpoints_are_recognised(self):
        self.assertTrue(probe.generic_endpoint('https://thunderpick.io/api/matches'))
        self.assertTrue(probe.generic_endpoint('https://www.hltv.org/matches'))
        self.assertFalse(probe.generic_endpoint(
            'https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24'))


class CitationTests(unittest.TestCase):
    def test_pick_uses_the_origination_layer_first(self):
        match = SNAPSHOT['matches'][0]
        orig = ORIGINATION['matches'][0]
        pick = probe.pick_of(match, orig)
        self.assertEqual(pick['layer'], 'origination')
        self.assertEqual(pick['pick'], 'Projeto do KinGui')
        self.assertEqual(pick['probabilities'], [0.666, 0.334])
        self.assertEqual(pick['aliases_used'], ['Tropa do KinGui -> Projeto do KinGui'])

    def test_pick_falls_back_to_the_featured_analysis(self):
        match = SNAPSHOT['matches'][1]
        pick = probe.pick_of(match, None)
        self.assertEqual(pick['layer'], 'featured')
        self.assertEqual(pick['pick'], 'Acend')

    def test_citations_dedupe_and_label_roles(self):
        match = SNAPSHOT['matches'][0]
        orig = ORIGINATION['matches'][0]
        pick = probe.pick_of(match, orig)
        citations = probe.citations_for(match, orig, pick)
        urls = [c['url'] for c in citations]
        self.assertEqual(len(urls), len(set(urls)))
        polymarket = next(c for c in citations if 'polymarket.com' in c['url'])
        self.assertIn('Quote: Polymarket', polymarket['roles'])
        self.assertEqual(polymarket['kind'], 'price')
        hltv = next(c for c in citations if 'hltv.org' in c['url'])
        self.assertEqual(hltv['kind'], 'identity')
        # An unavailable stage is documented in the record, not cited as a source of the pick.
        self.assertFalse(any('gg.bet' in url for url in urls))


class AlternateTests(unittest.TestCase):
    def test_public_json_alternates_are_derived_from_the_cited_page(self):
        poly = probe.alternates('https://polymarket.com/event/cs2-ntr-zerote-2026-10-24')
        self.assertEqual(poly[0]['url'],
                         'https://gamma-api.polymarket.com/events?slug=cs2-ntr-zerote-2026-10-24')
        raw = probe.alternates('https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md')
        self.assertEqual(raw[0]['url'],
                         'https://raw.githubusercontent.com/ValveSoftware/counter-strike_regional_standings/main/live/2026/standings_global_2026_10_05.md')
        kalshi = probe.alternates('https://kalshi.com/markets/kxcs2game/counterstrike-2-game/kxcs2game-26oct241300illbaks')
        self.assertEqual(kalshi[0]['url'],
                         'https://api.elections.kalshi.com/trade-api/v2/markets/kxcs2game-26oct241300illbaks')
        thunderpick = probe.alternates('https://thunderpick.io/api/matches')
        self.assertEqual(thunderpick[0]['method'], 'POST')
        self.assertEqual(thunderpick[0]['payload'], {'gameIds': [6]})
        self.assertTrue(probe.alternates('https://bo3.gg/matches')[0]['url'].startswith(
            'https://api.bo3.gg/'))
        self.assertEqual(probe.alternates('https://www.hotspawn.com/matches/x-1083121'), [])

    def test_a_generic_endpoint_bound_by_event_id_is_confirmed_through_its_post_api(self):
        citation = {'url': 'https://thunderpick.io/api/matches', 'roles': ['Quote'],
                    'kind': 'price', 'generic': True, 'event_id': '2870940'}
        calls = []

        def post_only(url, **kwargs):
            calls.append(kwargs.get('method', 'GET'))
            if kwargs.get('method') != 'POST':
                return {'name': 'citation', 'url': url, 'http': 200, 'status': 'ok',
                        'bytes': 0, 'sha256': None, 'title': '', 'challenge': False,
                        'error': None, '_body': '[]'}
            return {'name': 'citation', 'url': url, 'http': 200, 'status': 'ok',
                    'bytes': 10, 'sha256': None, 'title': '', 'challenge': False,
                    'error': None, '_body': '{"id": 2870940}'}

        entry = probe.verify_citation(post_only, citation, ['NEXVOID', 'Alter Ego'])
        self.assertEqual(entry['verdict'], 'confirmed-via-alternate')
        self.assertIn('POST', calls)
        self.assertEqual(entry['fallback']['label'], 'Thunderpick prematch event list (POST, gameIds=[6])')

    def test_a_walled_page_confirmed_by_the_source_api_counts(self):
        citation = {'url': 'https://polymarket.com/event/cs2-ntr-zerote-2026-10-24',
                    'roles': ['Quote'], 'kind': 'price', 'generic': False}
        alternate = probe.alternates(citation['url'])[0]['url']
        fetcher = fake_fetch({alternate: '[{"title": "Nuclear TigeRES vs ex-Zero Tenacity"}]'})
        entry = probe.verify_citation(fetcher, citation, ['Nuclear TigeRES', 'ex-Zero Tenacity'])
        self.assertEqual(entry['verdict'], 'confirmed-via-alternate')
        self.assertEqual(entry['fallback']['url'], alternate)

    def test_a_walled_fixture_page_is_corroborated_by_the_fixture_feed(self):
        citation = {'url': 'https://www.hotspawn.com/matches/a-vs-b-1083121',
                    'roles': ['Hotspawn fixture'], 'kind': 'fixture', 'generic': False}
        api_record = {'id': '1083121', 'teams': ['Projeto do KinGui', 'MEIA NOITE'],
                      'competition': 'CCT', 'starts_at': '2026-10-24T16:00:00Z', 'future': True}
        entry = probe.verify_citation(fake_fetch({}), citation,
                                      ['Projeto do KinGui', 'MEIA NOITE'], api_record)
        self.assertEqual(entry['verdict'], 'confirmed-via-alternate')
        self.assertEqual(entry['fallback']['url'], probe.FIXTURES_API)


class VerdictTests(unittest.TestCase):
    def test_confirmed_when_both_names_are_on_the_page(self):
        citation = {'url': 'https://polymarket.com/event/x', 'roles': ['Quote'],
                    'kind': 'price', 'generic': False}
        entry = probe.verify_citation(
            fake_fetch({citation['url']: '<title>e</title> Projeto do KinGui vs MEIA NOITE'}),
            citation, ['Projeto do KinGui', 'MEIA NOITE'])
        self.assertEqual(entry['verdict'], 'confirmed')

    def test_event_id_binding_confirms_a_generic_endpoint(self):
        citation = {'url': 'https://thunderpick.io/api/matches', 'roles': ['Quote'],
                    'kind': 'price', 'generic': True, 'event_id': '2767837'}
        entry = probe.verify_citation(
            fake_fetch({citation['url']: '{"id": 2767837, "markets": []}'}),
            citation, ['Projeto do KinGui', 'MEIA NOITE'])
        self.assertEqual(entry['verdict'], 'confirmed')
        self.assertTrue(entry['event_bound'])

    def test_unbound_generic_endpoint_is_not_a_failure(self):
        citation = {'url': 'https://thunderpick.io/api/matches', 'roles': ['Quote'],
                    'kind': 'price', 'generic': True, 'event_id': '999'}
        entry = probe.verify_citation(fake_fetch({citation['url']: '{"id": 1}'}),
                                      citation, ['A Team', 'B Team'])
        self.assertEqual(entry['verdict'], 'endpoint-unbound')

    def test_absent_when_a_fixture_page_names_neither_team(self):
        citation = {'url': 'https://book.example/match/abc', 'roles': ['Quote'],
                    'kind': 'price', 'generic': False}
        entry = probe.verify_citation(fake_fetch({citation['url']: '<html>Sign in</html>'}),
                                      citation, ['A Team', 'B Team'])
        self.assertEqual(entry['verdict'], 'absent')

    def test_refusal_is_blocked_never_absent(self):
        citation = {'url': 'https://book.example/match/abc', 'roles': ['Quote'],
                    'kind': 'price', 'generic': False}
        entry = probe.verify_citation(fake_fetch({}), citation, ['A Team', 'B Team'])
        self.assertEqual(entry['verdict'], 'blocked')
        self.assertEqual(entry['read']['http'], 403)

    def test_fixture_verdict_is_verified_only_with_a_confirmed_price_citation(self):
        match = SNAPSHOT['matches'][0]
        orig = ORIGINATION['matches'][0]
        fetcher = fake_fetch({
            match['source_url']: 'meia-noite vs projeto do kingui',
            'https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24': 'Projeto do KinGui vs MEIA NOITE',
            'https://thunderpick.io/api/matches': '{"id": 2767837}',
            'https://www.hltv.org/matches/2399913/tropa-do-kingui-vs-meia-noite': 'Tropa do KinGui vs MEIA NOITE',
        })
        result = probe.verify_fixture(fetcher, match, orig)
        self.assertEqual(result['verdict'], 'verified')
        self.assertEqual(result['summary']['unreachable'], 0)

    def test_fixture_needs_review_when_no_price_citation_can_be_read(self):
        match = SNAPSHOT['matches'][0]
        orig = ORIGINATION['matches'][0]
        result = probe.verify_fixture(fake_fetch({}), match, orig)
        self.assertEqual(result['verdict'], 'needs-review')
        self.assertGreater(result['summary']['unreachable'], 0)
        self.assertEqual(result['summary']['confirmed_via_alternate'], 0)


class ReportTests(unittest.TestCase):
    def _report(self, bodies):
        return probe.build_report(SNAPSHOT, ORIGINATION, API_BODY, fake_fetch(bodies),
                                  '2026-10-24T16:30:00Z')

    def test_counts_and_coverage(self):
        report = self._report({
            'https://www.hotspawn.com/matches/meia-noite-vs-projeto-do-kingui-cct-south-america-2026-series-7-1083121': 'Projeto do KinGui vs MEIA NOITE',
            'https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24': 'Projeto do KinGui vs MEIA NOITE',
            'https://thunderpick.io/api/matches': '{"id": 2767837}',
            'https://www.hltv.org/matches/2399913/tropa-do-kingui-vs-meia-noite': 'Tropa do KinGui vs MEIA NOITE',
            'https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996': 'Acend vs UNiTY',
            'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md': 'Acend UNiTY',
        })
        counts = report['provenance']['counts']
        self.assertEqual(counts['active'], 3)
        self.assertEqual(counts['no_pick'], 1)
        self.assertEqual(counts['with_pick'], 2)
        # 1083999 is a future fixture absent from the published inventory: it is
        # reported, never silently dropped.
        self.assertTrue(report['coverage']['live_future_missing'])
        self.assertIn('1083777', [row['id'] for row in report['coverage']['live_future_missing']])

    def test_flags_follow_the_review_schema(self):
        report = self._report({})
        flags = probe.flags_for(report)
        ids = [flag['id'] for flag in flags]
        self.assertIn('6174aa87-provenance-sweep', ids)
        self.assertIn('6174aa87-active-fixture-without-pick', ids)
        self.assertIn('6174aa87-cited-source-unreachable-on-recheck', ids)
        self.assertIn('6174aa87-live-fixtures-not-yet-in-the-published-inventory', ids)
        for flag in flags:
            self.assertEqual(set(flag), {'id', 'severity', 'match_ids', 'title', 'detail',
                                         'source_urls'})
            self.assertIn(flag['severity'], {'review', 'notice'})
            self.assertTrue(flag['detail'].strip())
            for url in flag['source_urls']:
                self.assertRegex(url, r'^https://')

    def test_no_absent_names_flag_when_pages_name_the_teams(self):
        report = self._report({
            'https://www.hotspawn.com/matches/meia-noite-vs-projeto-do-kingui-cct-south-america-2026-series-7-1083121': 'Projeto do KinGui vs MEIA NOITE',
            'https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24': 'Projeto do KinGui vs MEIA NOITE',
            'https://thunderpick.io/api/matches': '{"id": 2767837}',
            'https://www.hltv.org/matches/2399913/tropa-do-kingui-vs-meia-noite': 'Tropa do KinGui vs MEIA NOITE',
        })
        ids = [flag['id'] for flag in probe.flags_for(report)]
        self.assertNotIn('6174aa87-cited-page-did-not-name-both-teams', ids)

    def test_markdown_dossier_links_every_fixture_and_citation(self):
        report = self._report({
            'https://www.hotspawn.com/matches/meia-noite-vs-projeto-do-kingui-cct-south-america-2026-series-7-1083121': 'Projeto do KinGui vs MEIA NOITE',
            'https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24': 'Projeto do KinGui vs MEIA NOITE',
            'https://thunderpick.io/api/matches': '{"id": 2767837}',
        })
        md = probe.render_md(report)
        self.assertIn('Pick provenance sweep', md)
        self.assertIn('https://polymarket.com/event/cs2-tdkg-meiano-2026-10-24', md)
        self.assertIn('## Coverage against the live Hotspawn feed', md)
        self.assertIn('Missing ids', md)
        self.assertRegex(md, re.compile(r'\| 1 \| \[Projeto do KinGui vs MEIA NOITE\]'))

    def test_unreadable_feed_is_reported_never_assumed_complete(self):
        # An unreadable fixture feed says nothing about coverage: it must not read
        # like "0 missing", and it must raise its own notice.
        report = probe.build_report(SNAPSHOT, ORIGINATION, '', fake_fetch({}),
                                    '2026-10-24T16:30:00Z')
        coverage_block = report['coverage']
        self.assertFalse(coverage_block['feed_read'])
        self.assertIn('unreadable', coverage_block['feed_status'])
        ids = [flag['id'] for flag in probe.flags_for(report)]
        self.assertIn('6174aa87-hotspawn-feed-unreadable-on-sweep', ids)
        self.assertIn('not verified', probe.render_md(report))

    def test_a_no_pick_row_still_links_its_fixture(self):
        match = SNAPSHOT['matches'][2]
        result = probe.verify_fixture(fake_fetch({}), match, None)
        self.assertEqual(result['verdict'], 'no-pick')
        self.assertEqual([c['url'] for c in result['citations']], [match['source_url']])

    def test_fixture_rows_parse_epoch_milliseconds(self):
        rows = probe.fixture_rows(API_BODY, probe.parse_iso('2026-10-24T16:30:00Z'))
        self.assertEqual(len(rows), 3)
        self.assertTrue(any(row['future'] for row in rows))
        self.assertEqual(rows[0]['teams'], ['Projeto do KinGui', 'MEIA NOITE'])

    def test_probe_writes_no_probability_of_its_own(self):
        report = self._report({})
        for fixture in report['provenance']['fixtures']:
            if fixture['pick']['layer'] == 'featured' and fixture['pick']['probabilities']:
                # The probability is the record's own, carried through unchanged.
                self.assertEqual(fixture['pick']['probabilities'], [0.542, 0.458])
        text = json.dumps(report)
        self.assertNotIn('"hand_written', text)


class PublisherClockHygieneTests(unittest.TestCase):
    """The wall-clock defect this session found in a shipped test module.

    `scripts/originate.run` applies an 8-hour price-freshness gate against the
    wall clock. On 2026-10-24 two tests in tests/test_a5b59ee6_publisher_wiring.py
    wrote a capture observed at 2026-10-24T06:30Z and called `originate.run`
    without a reference clock, so they passed until 14:30Z and then failed
    forever. That is the same class of failure that stopped the four-hour
    publisher for 10.5 hours (runs 40028653350, 40037957529, 40048429858,
    40063011446), and it would have blocked the next scheduled refresh.
    """

    def test_run_accepts_and_honours_an_injected_clock(self):
        from scripts import originate
        from datetime import datetime, timezone
        moment = datetime(2026, 10, 24, 6, 30, tzinfo=timezone.utc)
        self.assertIn('now', originate.run.__code__.co_varnames)
        self.assertEqual(originate.iso(moment), '2026-10-24T06:30:00Z')

    def test_the_shipped_module_that_owns_the_dated_capture_pins_its_clock(self):
        import ast
        from pathlib import Path
        source = (Path(__file__).resolve().parent
                  / 'test_a5b59ee6_publisher_wiring.py').read_text(encoding='utf-8')
        calls = [node for node in ast.walk(ast.parse(source))
                 if isinstance(node, ast.Call)
                 and (getattr(node.func, 'attr', '') or '') == 'run'
                 and (getattr(node.func, 'value', None) is not None)
                 and getattr(node.func.value, 'id', '') == 'originate']
        self.assertGreaterEqual(len(calls), 3, 'the module must still exercise the ladder end to end')
        for call in calls:
            self.assertTrue(any(kw.arg == 'now' for kw in call.keywords),
                            'originate.run() against a dated capture must pin its clock (line %d)'
                            % call.lineno)

    def test_an_expired_capture_prices_nothing_rather_than_being_repriced(self):
        """Reproduce the production rule the pin exists for, deterministically."""
        from datetime import datetime, timedelta, timezone
        from scripts import reference_odds
        import hashlib
        sentence = ('Ground Zero carry published bookmaker-average odds of 3.44 to win '
                    'against Off Chops at 1.24.')
        entry = {'fixture_id': '1082858', 'teams': ['Ground Zero', 'Off Chops'],
                 'starts_at': '2026-10-26T03:00:00Z', 'observed_at': '2026-10-24T06:20:00Z',
                 'odds': [3.44, 1.24], 'source_url': 'https://egamersworld.com/counterstrike/match/x',
                 'provider_teams': ['Ground Zero', 'Off Chops'],
                 'excerpt': sentence,
                 'excerpt_sha256': hashlib.sha256(sentence.encode('utf-8')).hexdigest()}
        match = {'id': '1082858', 'starts_at': '2026-10-26T03:00:00Z',
                 'teams': [{'name': 'Ground Zero'}, {'name': 'Off Chops'}],
                 'availability': 'future'}
        fresh = datetime(2026, 10, 24, 6, 30, tzinfo=timezone.utc)
        expired = fresh + timedelta(hours=9)
        reference_odds.quote(entry, match, fresh)
        self.assertEqual(reference_odds.quote(entry, match, expired),
                         (None, 'Aggregated line is older than eight hours or undated'))


if __name__ == '__main__':
    unittest.main()
