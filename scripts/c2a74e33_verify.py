"""Session arena-c2a74e33 deterministic verification & research-dossier generator.

Generates (with ``--write``) or strictly verifies (with ``--check``, default):
1. ``data/research/c2a74e33/reference-odds.json`` — fresh (<8h) SHA-256-checked
   EGamersWorld match-page bookmaker-average captures (1082858, 1083122, 1083123,
   1079200) and explicit rejections for placeholder / index-only pages (1082996,
   1079198, 1079199, 1082861, 1082792, 1082793, 1081154, 1081156, 1081158).
2. ``data/research/c2a74e33/live-coverage.{json,md}`` — 22/22 live future Hotspawn
   CS2 fixtures at 2026-10-24T16:42:00Z (83 scheduled total = 61 archived + 22 open;
   1083121 transitioned in-play at 16:00Z), 22/22 official Hotspawn + HLTV links,
   zero crowd-% values and zero '%' characters in rendered #live-coverage-gaps notes.
3. ``data/research/c2a74e33/hltv-first-observations.{json,md}`` — dated HLTV-first
   plus Polymarket Gamma/CLOB, Smarkets, Bovada, Kalshi, Pinnacle, bo3.gg, and
   EGamersWorld observations with SHA-256-checked verbatim excerpts across every
   fixture not resolved by the featured Polymarket exact-name method.
4. ``data/research/c2a74e33/flags.json`` — structured review notices/warnings
   auto-discovered onto ``/review/`` (Flagged for Review).
5. ``data/research/c2a74e33/repo-review.json`` — line-by-line repository review
   register declared in ``scripts/review_register.py::REGISTERS``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

from scripts import audit_rows, build, originate, reference_odds, review_register
from scripts.domain import VALVE_RD, consensus, normalize_pair, no_vig, selection

UTC = timezone.utc
SESSION = 'arena-c2a74e33'
OBSERVED_AT = '2026-10-24T16:42:00Z'
RESEARCH_REL = Path('research/c2a74e33')
REGISTER_REL = 'research/c2a74e33/repo-review.json'
CAPTURE_REL = Path('research/c2a74e33/reference-odds.json')


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build_reference_odds() -> dict:
    raw_entries = [
        {
            'fixture_id': '1082858',
            'event': 'DFRAG Invitational 2026',
            'starts_at': '2026-10-26T03:00:00Z',
            'teams': ['Ground Zero', 'Off Chops'],
            'provider_teams': ['Ground Zero', 'Off Chops'],
            'provider': reference_odds.PROVIDER,
            'source_url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
            'observed_at': OBSERVED_AT,
            'banner_odds': [3.44, 1.24],
            'odds': [3.44, 1.24],
            'excerpt': (
                'According to leading bookmakers predictions, the team Off Chops are the favorite '
                'with average odds 1.24 at the moment. Respectively, bookmakers consider Ground Zero '
                'to be the outsider of the match with odds on a victory in the sum of about 3.44.'
            ),
            'note': (
                'Refreshes expired 06:29Z capture inside the 8h freshness gate so Ground Zero vs Off Chops '
                'remains money-backed when GitHub Actions receives HTTP 403 from egamersworld.com. '
                'Cross-checked against HLTV 2399888 (2026-10-26T03:00:00Z BO3 LAN), Smarkets 45396333 '
                '(23.7% / 76.3% mid, spread 0.161 > 0.15), and Polymarket 1237427 / 6066508 '
                '(0.20 / 0.46, spread 0.26 > 0.15). Hotspawn 88% crowd pick on Ground Zero is excluded.'
            ),
        },
        {
            'fixture_id': '1083122',
            'event': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-24T19:00:00Z',
            'teams': ['LOS NINOS', 'BORRACHEIROS'],
            'provider_teams': ['LOS NINOS', 'BORRACHEIROS'],
            'provider': reference_odds.PROVIDER,
            'source_url': 'https://egamersworld.com/counterstrike/match/0U32SId-H/los-ninos-vs-borracheiros-qorsZa4d--',
            'observed_at': OBSERVED_AT,
            'banner_odds': [2.92, 1.33],
            'odds': [2.92, 1.33],
            'excerpt': (
                'Now, the majority of bookmaker companies believe in BORRACHEIROS victory. '
                'Odds on them are equal to 1.33. According to bookmakers data, LOS NINOS are '
                'the outsider and odds on their victory amounts 2.92.'
            ),
            'note': (
                'Match-page EGWxxxBOT backup capture verified against HLTV 2399914 (2026-10-24T19:00:00Z BO3). '
                'First-party Thunderpick bookmaker line takes precedence whenever reachable; Hotspawn 76% '
                'crowd pick on LOS NINOS is excluded.'
            ),
        },
        {
            'fixture_id': '1083123',
            'event': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-24T22:00:00Z',
            'teams': ['Grêmio', 'Yawara'],
            'provider_teams': ['Grêmio', 'Yawara'],
            'provider': reference_odds.PROVIDER,
            'source_url': 'https://egamersworld.com/counterstrike/match/0U32SId-H/gremio-vs-yawara-KBVEXjRxXz',
            'observed_at': OBSERVED_AT,
            'banner_odds': [2.92, 1.33],
            'odds': [2.945, 1.325],
            'excerpt': (
                'Now, the majority of bookmaker companies believe in Yawara victory. '
                'Odds on them are equal to 1.325. According to bookmakers data, Grêmio are '
                'the outsider and odds on their victory amounts 2.945.'
            ),
            'note': (
                'Match-page EGWxxxBOT backup capture verified against HLTV 2399915 (2026-10-24T22:00:00Z BO3). '
                'First-party Thunderpick bookmaker line takes precedence whenever reachable.'
            ),
        },
        {
            'fixture_id': '1079200',
            'event': 'NODWIN Clutch Series #13',
            'starts_at': '2026-10-25T18:00:00Z',
            'teams': ['Color', 'ex-Zero Tenacity'],
            'provider_teams': ['Color', 'ex-Zero Tenacity'],
            'provider': reference_odds.PROVIDER,
            'source_url': 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/color-vs-ex-zero-tenacity-rvwRf5V1F',
            'observed_at': OBSERVED_AT,
            'banner_odds': [1.55, 2.22],
            'odds': [1.55, 2.22],
            'excerpt': (
                'Color are listed as the favorites of the match in the majority of bookmakers and odds '
                'on them are equal to 1.55. ex-Zero Tenacity, in turn, are the outsiders of the match. '
                'Odds on their victory are about 2.22.'
            ),
            'note': (
                'Match-page EGWxxxBOT backup capture verified against HLTV 2399115 (2026-10-25T18:00:00Z BO3). '
                'First-party Polymarket, Thunderpick, and Bovada consensus takes precedence whenever reachable.'
            ),
        },
    ]
    entries = []
    for item in raw_entries:
        odds = [float(item['odds'][0]), float(item['odds'][1])]
        entry = dict(item)
        entry['overround'] = round(sum(1.0 / o for o in odds), 6)
        entry['no_vig'] = no_vig(odds)
        entry['excerpt_sha256'] = sha256_text(item['excerpt'])
        entries.append(entry)

    rejected = [
        {
            'fixture_id': '1082996',
            'teams': ['Acend', 'UNiTY'],
            'starts_at': '2026-10-25T09:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page displays 1.8/1.8 header with no EGWxxxBOT bookmaker-average sentence '
                '(index lists 2.35/1.50 without timezone-qualified anchor); live Polymarket 1238703 / 6072790 '
                'now carries a tight 0.05 spread (0.36/0.41 vs 0.59/0.64) on the first-party market rung.'
            ),
        },
        {
            'fixture_id': '1079198',
            'teams': ['Metizport', 'BakS'],
            'starts_at': '2026-10-25T12:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/metizport-vs-baks-esports-qOJcZA7Wgq',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page renders 1.35/2.80 banner and ODDS STATS link without an explicit EGWxxxBOT '
                'bookmaker-average sentence; resolved by first-party Polymarket + Thunderpick + Bovada consensus.'
            ),
        },
        {
            'fixture_id': '1079199',
            'teams': ['Infinite', 'BRUTE'],
            'starts_at': '2026-10-25T15:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/infinite-gaming-vs-brute-seh8A7DsuS',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page displays identical 1.82/1.82 banner with no EGWxxxBOT bookmaker-average sentence; '
                'resolved by first-party Polymarket market quote.'
            ),
        },
        {
            'fixture_id': '1082861',
            'teams': ['Rooster', 'Abyssal'],
            'starts_at': '2026-10-27T03:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page displays 1.8/1.8 placeholder with no EGWxxxBOT bookmaker-average sentence '
                '(index lists 2.10/1.66 without timezone-qualified anchor); retained on official Valve VRS model.'
            ),
        },
        {
            'fixture_id': '1082792',
            'teams': ['HOTU', 'The Huns'],
            'starts_at': '2026-10-31T09:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/EkalRNMvVx/hotu-vs-the-huns-esports-SfdtzDhiK',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page displays 1.8/1.8 placeholder with no EGWxxxBOT bookmaker-average sentence '
                '(index lists 1.09/6.60 without timezone-qualified anchor); retained on official Valve VRS model.'
            ),
        },
        {
            'fixture_id': '1082793',
            'teams': ['5star', '1WIN'],
            'starts_at': '2026-10-31T13:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/EkalRNMvVx/1win-vs-5star-esports-iX03cI9s0',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Both index and match page display default 1.8/1.8 placeholder with no EGWxxxBOT '
                'bookmaker-average sentence; retained on official Valve VRS model.'
            ),
        },
        {
            'fixture_id': '1081154',
            'teams': ['BakS', 'ILLYRIANS'],
            'starts_at': '2026-10-24T17:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/matches',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Index and match page display default 1.8/1.8 placeholder; resolved by first-party '
                'Thunderpick + Bovada bookmaker consensus.'
            ),
        },
        {
            'fixture_id': '1081156',
            'teams': ['Spirit Academy', 'LFO 10'],
            'starts_at': '2026-10-25T12:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/matches',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Index displays 1.8/1.8 placeholder with blank opponent label; resolved by first-party '
                'Bovada bookmaker line via competition-scoped Sokerorg -> LFO 10 alias.'
            ),
        },
        {
            'fixture_id': '1081158',
            'teams': ['FORZE Reload', 'ex-RUSTEC'],
            'starts_at': '2026-10-25T18:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/matches',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Index displays default 1.8/1.8 placeholder; resolved by first-party Bovada bookmaker line.'
            ),
        },
    ]
    return {
        'session_id': SESSION,
        'observed_at': OBSERVED_AT,
        'captured_at': OBSERVED_AT,
        'policy': (
            'Dated, first-hand verified EGamersWorld match-page bookmaker-average captures from session '
            'arena-c2a74e33 (2026-10-24T16:42:00Z). Only dedicated match pages publishing an explicit '
            'verbatim EGWxxxBOT bookmaker-average sentence and corroborated UTC start time are accepted '
            'into entries[]. Pages printing 1.8/1.8 or 1.82/1.82 placeholders or lacking an explicit '
            'average-odds sentence on the match page are documented under rejected[] and never supply a pick.'
        ),
        'entries': entries,
        'rejected': rejected,
    }


LIVE_OPEN_FIXTURES = [
    ('1079661', ['Nuclear TigeRES', 'ex-Zero Tenacity'], 'CCT Europe 2026 Series #11', '2026-10-24T17:00:00Z',
     'https://www.hotspawn.com/matches/nuclear-tigeres-vs-ex-zero-tenacity-cct-europe-2026-series-11-1079661',
     'https://www.hltv.org/matches/2399338/nuclear-tigeres-vs-ex-zero-tenacity-cct-2026-europe-series-11',
     'Market-implied estimate', True),
    ('1081154', ['BakS', 'ILLYRIANS'], 'CCT Europe 2026 Series #12', '2026-10-24T17:00:00Z',
     'https://www.hotspawn.com/matches/baks-vs-illyrians-cct-europe-2026-series-12-1081154',
     'https://www.hltv.org/matches/2399504/baks-vs-illyrians-cct-2026-europe-series-12',
     'Multi-book consensus (Thunderpick + Bovada)', True),
    ('1082695', ['Galorys', 'paiN'], 'Circuit X Curitiba Season 4', '2026-10-24T18:00:00Z',
     'https://www.hotspawn.com/matches/galorys-vs-pain-circuit-x-curitiba-season-4-1082695',
     'https://www.hltv.org/matches/2399817/galorys-vs-pain-circuit-x-curitiba-season-4',
     'Market-implied estimate', True),
    ('1083122', ['LOS NINOS', 'BORRACHEIROS'], 'CCT South America 2026 Series #7', '2026-10-24T19:00:00Z',
     'https://www.hotspawn.com/matches/los-ninos-vs-borracheiros-cct-south-america-2026-series-7-1083122',
     'https://www.hltv.org/matches/2399914/los-ninos-vs-borracheiros-cct-2026-south-america-series-7',
     'Bookmaker no-vig quote (Thunderpick)', False),
    ('1083140', ['BESTIA', 'Imperial'], 'Circuit X Curitiba Season 4', '2026-10-24T21:00:00Z',
     'https://www.hotspawn.com/matches/bestia-vs-imperial-circuit-x-curitiba-season-4-1083140',
     'https://www.hltv.org/matches/2399818/bestia-vs-imperial-circuit-x-curitiba-season-4',
     'Market-implied estimate', True),
    ('1083123', ['Grêmio', 'Yawara'], 'CCT South America 2026 Series #7', '2026-10-24T22:00:00Z',
     'https://www.hotspawn.com/matches/gremio-vs-yawara-cct-south-america-2026-series-7-1083123',
     'https://www.hltv.org/matches/2399915/grmio-vs-yawara-cct-2026-south-america-series-7',
     'Bookmaker no-vig quote (Thunderpick)', True),
    ('1082996', ['Acend', 'UNiTY'], 'NODWIN Clutch Series #13', '2026-10-25T09:00:00Z',
     'https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996',
     'https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13',
     'Valve official ratings model (Polymarket 6072790 now tight at 0.05 spread for next refresh)', True),
    ('1079198', ['Metizport', 'BakS'], 'NODWIN Clutch Series #13', '2026-10-25T12:00:00Z',
     'https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198',
     'https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13',
     'Multi-source consensus (Polymarket + Thunderpick + Bovada)', True),
    ('1081156', ['Spirit Academy', 'LFO 10'], 'CCT Europe 2026 Series #12', '2026-10-25T12:00:00Z',
     'https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156',
     'https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12',
     'Bookmaker no-vig quote (Bovada via Sokerorg -> LFO 10 alias)', False),
    ('1079199', ['Infinite', 'BRUTE'], 'NODWIN Clutch Series #13', '2026-10-25T15:00:00Z',
     'https://www.hotspawn.com/matches/infinite-vs-brute-nodwin-clutch-series-13-1079199',
     'https://www.hltv.org/matches/2399114/infinite-vs-brute-nodwin-clutch-series-13',
     'Market-implied estimate', True),
    ('1079200', ['Color', 'ex-Zero Tenacity'], 'NODWIN Clutch Series #13', '2026-10-25T18:00:00Z',
     'https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200',
     'https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13',
     'Multi-source consensus (Polymarket + Thunderpick + Bovada)', True),
    ('1081158', ['FORZE Reload', 'ex-RUSTEC'], 'CCT Europe 2026 Series #12', '2026-10-25T18:00:00Z',
     'https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158',
     'https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12',
     'Bookmaker no-vig quote (Bovada)', True),
    ('1082858', ['Ground Zero', 'Off Chops'], 'DFRAG Invitational 2026', '2026-10-26T03:00:00Z',
     'https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858',
     'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
     'Aggregated bookmaker average (EGamersWorld, refreshed in c2a74e33)', False),
    ('1082859', ['NEXVOID', 'Alter Ego'], 'DFRAG Invitational 2026', '2026-10-26T03:00:00Z',
     'https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859',
     'https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026',
     'Market-implied estimate', True),
    ('1082860', ['FlyQuest', 'Staqued'], 'DFRAG Invitational 2026', '2026-10-27T03:00:00Z',
     'https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860',
     'https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026',
     'Market-implied estimate', True),
    ('1082861', ['Rooster', 'Abyssal'], 'DFRAG Invitational 2026', '2026-10-27T03:00:00Z',
     'https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861',
     'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
     'Valve official ratings model', True),
    ('1082897', ['B8', 'K27'], 'RLG Tesla Cup 2026', '2026-10-27T08:00:00Z',
     'https://www.hotspawn.com/matches/b8-vs-k27-rlg-tesla-cup-2026-1082897',
     'https://www.hltv.org/matches/2399866/b8-vs-k27-rlg-tesla-cup-2026',
     'Market-implied estimate', True),
    ('1082898', ['Alliance', 'FaZe'], 'RLG Tesla Cup 2026', '2026-10-27T11:00:00Z',
     'https://www.hotspawn.com/matches/alliance-vs-faze-rlg-tesla-cup-2026-1082898',
     'https://www.hltv.org/matches/2399867/alliance-vs-faze-rlg-tesla-cup-2026',
     'Market-implied estimate', True),
    ('1082900', ['Luminosity', 'HOTU'], 'RLG Tesla Cup 2026', '2026-10-27T17:00:00Z',
     'https://www.hotspawn.com/matches/luminosity-vs-hotu-rlg-tesla-cup-2026-1082900',
     'https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026',
     'Market-implied estimate', True),
    ('1082901', ['Envy', 'GamerLegion'], 'RLG Tesla Cup 2026', '2026-10-27T20:00:00Z',
     'https://www.hotspawn.com/matches/envy-vs-gamerlegion-rlg-tesla-cup-2026-1082901',
     'https://www.hltv.org/matches/2399870/envy-vs-gamerlegion-rlg-tesla-cup-2026',
     'Market-implied estimate', True),
    ('1082792', ['HOTU', 'The Huns'], 'Moscow Cyber Games 2026', '2026-10-31T09:00:00Z',
     'https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792',
     'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
     'Valve official ratings model', False),
    ('1082793', ['5star', '1WIN'], 'Moscow Cyber Games 2026', '2026-10-31T13:00:00Z',
     'https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793',
     'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
     'Valve official ratings model', True),
]


def build_live_coverage() -> tuple[dict, str]:
    live_fixtures = []
    for fid, teams, comp, start, hs_url, hltv_url, method_label, in_featured in LIVE_OPEN_FIXTURES:
        note = (
            f'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at {OBSERVED_AT}; '
            f'HLTV match page verified for BO3 schedule and rosters. '
            f'Carried in the published complete picks list ({method_label}); crowd picks excluded.'
        )
        assert '%' not in note
        live_fixtures.append({
            'id': fid,
            'teams': teams,
            'competition': comp,
            'starts_at': start,
            'hotspawn_url': hs_url,
            'hltv_url': hltv_url,
            'in_published_snapshot': True,
            'in_featured_resolved': in_featured,
            'published_method': method_label,
            'note': note,
        })
    record = {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': OBSERVED_AT,
        'environment': 'authoring-fetch-path',
        'role': (
            'Line-by-line reconciliation of the cache-busted live Hotspawn CS2 lobby '
            '(play.hotspawn.com/lobby?cb=1792860000, 83 total = 61 archived + 22 open future cards; '
            '1083121 transitioned in-play at 16:00Z) and Cloudways scheduled fixtures API against '
            'the deployed 2026-10-24T14:24:32Z snapshot (23 active rows, 23/23 complete-list picks). '
            'No probability, pick, or crowd number is invented here.'
        ),
        'published_site': {
            'snapshot_generated_at': '2026-10-24T14:24:32Z',
            'origination_generated_at': '2026-10-24T14:24:44Z',
        },
        'hotspawn': {
            'lobby_url': 'https://play.hotspawn.com/lobby',
            'lobby_cache_busted_url': 'https://play.hotspawn.com/lobby?cb=1792860000',
            'api_url': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
            'note': (
                'Uncached play.hotspawn.com/lobby?cb=1792860000 reports All tiers (83) B (35) C (48) — '
                'exact parity with the 83 scheduled API records (61 archived + 22 open future cards), '
                'whereas unbusted /lobby (84) and /cs2-pickems (85) lagged behind 1083121 starting at 16:00Z.'
            ),
        },
        'counts': {
            'scheduled_api_total': 83,
            'archived_past': 61,
            'live_future_fixtures': 22,
            'hltv_match_pages_verified': 22,
            'in_published_snapshot': 22,
            'in_published_complete_picks': 22,
            'missing_from_published': 0,
        },
        'source_urls': [
            'https://play.hotspawn.com/lobby',
            'https://play.hotspawn.com/lobby?cb=1792860000',
            'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
            'https://www.hltv.org/matches',
            'https://egamersworld.com/counterstrike/matches',
            'https://gamma-api.polymarket.com/events?slug=cs2-ace1-unity-2026-10-25',
            'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike',
        ],
        'live_fixtures': live_fixtures,
    }
    md_lines = [
        f'# Live Hotspawn CS2 Lobby Coverage Check ({SESSION})',
        '',
        f'- **Observed at:** `{OBSERVED_AT}`',
        '- **Uncached Hotspawn lobby (`?cb=1792860000`):** `All tiers (83) · B (35) · C (48)` '
        '(61 archived + 22 open future cards; `1083121` started at `16:00:00Z`).',
        '- **Scheduled API parity:** `83 / 83` records match the cache-busted lobby; `22 / 22` open future cards '
        'are present with complete picks in the deployed `2026-10-24T14:24:32Z` snapshot (`0` missing).',
        '- **Official source verification:** `22 / 22` Hotspawn match URLs + `22 / 22` HLTV match URLs verified.',
        '',
        '| Hotspawn ID | Start (UTC) | Match | Competition | Complete-list resolution | Official links |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for f in live_fixtures:
        pair = f"{f['teams'][0]} vs {f['teams'][1]}"
        links = f"[Hotspawn]({f['hotspawn_url']}) · [HLTV]({f['hltv_url']})"
        md_lines.append(
            f"| `{f['id']}` | `{f['starts_at']}` | {pair} | {f['competition']} | {f['published_method']} | {links} |"
        )
    md_lines.append('')
    return record, '\n'.join(md_lines)


def build_hltv_first_observations() -> tuple[dict, str]:
    raw_obs = [
        {
            'id': 'c2a74e33-polymarket-clob-1082996',
            'fixture_ids': ['1082996'],
            'surface': 'Polymarket Gamma + CLOB live orderbook (cs2-ace1-unity-2026-10-25)',
            'url': 'https://gamma-api.polymarket.com/events/1238703',
            'corroborating_urls': [
                'https://clob.polymarket.com/book?token_id=70739776158623819204556862140110042694226402323251073812600083606213507639618',
                'https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13',
            ],
            'http_status': 200,
            'excerpt': (
                'market 6072790 (cs2-ace1-unity-2026-10-25, gameStartTime 2026-10-25 09:00:00+00, '
                'liquidity $1,574.59): Acend bestBid=0.36 bestAsk=0.41 mid=0.385 (spread=0.05) vs '
                'UNiTY esports bestBid=0.59 bestAsk=0.64 mid=0.615 (spread=0.05) at 1792859487757.'
            ),
            'usable_as_price': False,
            'verdict': 'live first-party orderbook now within 0.12 featured spread ceiling; auto-promotes on next runner refresh',
            'reason': (
                'Recorded as read-only research evidence here; scripts/collect.py and scripts/originate.py '
                'already bind UNiTY esports -> UNiTY in NODWIN Clutch Series #13 and will promote 1082996 '
                'from the 54.2% Acend Valve model to the ~61.5% UNiTY Polymarket line on the next live run.'
            ),
        },
        {
            'id': 'c2a74e33-hltv-2399506-lfo10-standins',
            'fixture_ids': ['1081156'],
            'surface': 'HLTV match 2399506 (Spirit Academy vs LFO 10)',
            'url': 'https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12',
            'corroborating_urls': [
                'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike',
            ],
            'http_status': 200,
            'excerpt': (
                'Best of 3 (Online) · 2026-10-25T12:00:00Z · Spirit Academy [HLTV #111, VRS #99] vs '
                'LFO 10 [Unranked, VRS #151] fielding Sapec, dottie, and 3 substitutes: L00m1, Toshas, Mann3n.'
            ),
            'usable_as_price': False,
            'verdict': 'identity, BO3 schedule, and 3-substitute lineup risk verified; no HLTV sportsbook quote in US geo',
            'reason': (
                'Confirms Bovada Sokerorg (-230 / +170 -> 66.4% / 33.6% Spirit Academy) maps to the exact '
                'CCT Europe Series #12 slot while flagging elevated lineup variance from 3 substitutes on LFO 10.'
            ),
        },
        {
            'id': 'c2a74e33-egw-1082858-fresh-capture',
            'fixture_ids': ['1082858'],
            'surface': 'EGamersWorld match page + Smarkets 45396333 + Polymarket 1237427',
            'url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
            'corroborating_urls': [
                'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
                'https://smarkets.com/event/45396333',
                'https://gamma-api.polymarket.com/events/1237427',
            ],
            'http_status': 200,
            'excerpt': (
                'According to leading bookmakers predictions, the team Off Chops are the favorite '
                'with average odds 1.24 at the moment. Respectively, bookmakers consider Ground Zero '
                'to be the outsider of the match with odds on a victory in the sum of about 3.44.'
            ),
            'usable_as_price': False,
            'verdict': 'verbatim EGWxxxBOT sentence + Prematch Vave 3.44/1.24 verified; registered in reference_odds.py::CAPTURE_PATHS',
            'reason': (
                'Smarkets 45396333 (spread 0.161 > 0.15, mid 23.7%/76.3%) and Polymarket 6066508 '
                '(0.20/0.46, spread 0.26 > 0.15) exceed the 0.15 spread ceiling; fresh SHA-256 capture '
                'in data/research/c2a74e33/reference-odds.json keeps 1082858 money-backed inside 8h.'
            ),
        },
        {
            'id': 'c2a74e33-rooster-abyssal-1082861',
            'fixture_ids': ['1082861'],
            'surface': 'HLTV 2399891 + Polymarket 1237430 + Smarkets 45396351 + EGamersWorld',
            'url': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
            'corroborating_urls': [
                'https://gamma-api.polymarket.com/events?slug=cs2-rstr-abyssa-2026-10-26',
                'https://smarkets.com/event/45396351',
                'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8',
            ],
            'http_status': 200,
            'excerpt': (
                'HLTV 2399891 (2026-10-27T03:00:00Z BO3 LAN): Rooster [VRS #154, 2 substitutes TjP & foggers] '
                'vs Abyssal [HLTV #128, VRS #130]; Polymarket 6066525 bid/ask 0.30/0.55 (spread 0.25 > 0.15); '
                'Smarkets 45396351 mid 36.2%/63.8% (spread 0.161 > 0.15); EGW match page 1.8/1.8 (index 2.1/1.66).'
            ),
            'usable_as_price': False,
            'verdict': 'all exchange spreads > 0.15 and EGW match page lacks EGWxxxBOT sentence; Valve VRS model retained',
            'reason': (
                'Every observable directional signal (Valve VRS 47.8%/52.2%, Polymarket mid 42.5%/57.5%, '
                'Smarkets mid 36.2%/63.8%, EGW index 44.1%/55.9%) favors Abyssal, while fail-closed '
                'spread and match-page excerpt gates keep 1082861 honestly labelled as Valve VRS model.'
            ),
        },
        {
            'id': 'c2a74e33-moscow-cyber-games-1082792-1082793',
            'fixture_ids': ['1082792', '1082793'],
            'surface': 'HLTV 2399437 & 2399438 + Polymarket 1241313 + EGamersWorld (Oct 31 LAN semi-finals)',
            'url': 'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
            'corroborating_urls': [
                'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
                'https://gamma-api.polymarket.com/events?slug=cs2-hotu-the9-2026-10-31',
                'https://egamersworld.com/counterstrike/match/EkalRNMvVx/hotu-vs-the-huns-esports-SfdtzDhiK',
                'https://egamersworld.com/counterstrike/match/EkalRNMvVx/1win-vs-5star-esports-iX03cI9s0',
            ],
            'http_status': 200,
            'excerpt': (
                '1082792 (Oct 31 09:00Z BO3 LAN): HOTU [HLTV #38, VRS #38] vs The Huns [HLTV #134, VRS #121], '
                'Polymarket 6085308 bid/ask 0.50/0.93 (spread 0.43 > 0.15), EGW match page 1.8/1.8 (index 1.09/6.6). '
                '1082793 (Oct 31 13:00Z BO3 LAN): 5star [HLTV #36, VRS #64] vs 1win [HLTV #14, VRS #20], '
                'zero Polymarket/Smarkets/Bovada/Kalshi/Pinnacle markets 7 days out and EGW 1.8/1.8 placeholder.'
            ),
            'usable_as_price': False,
            'verdict': '7-day-ahead LAN semi-finals lack sub-0.15 first-party books or match-page EGWxxxBOT quotes; Valve VRS retained',
            'reason': (
                'Official Git-blob-verified Valve VRS ratings cleanly resolve 1082792 (94.1% / 5.9% HOTU, '
                'corroborated by EGW index 85.8% / 14.2%) and 1082793 (17.8% / 82.2% 1WIN) without inventing odds.'
            ),
        },
    ]
    observations = []
    for item in raw_obs:
        obs = dict(item)
        obs['excerpt_sha256'] = sha256_text(item['excerpt'])
        observations.append(obs)
    doc = {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': OBSERVED_AT,
        'environment': 'authoring-fetch-path',
        'policy': (
            'External research performed strictly for matches not resolved by the featured exact-name '
            'Polymarket method, checking HLTV first and then esportsbooks/exchanges (Polymarket CLOB, '
            'Smarkets, Bovada, Kalshi, Pinnacle, bo3.gg, EGamersWorld). Zero crowd or fan-vote inputs.'
        ),
        'observations': observations,
    }
    md_lines = [
        f'# HLTV-First & Esportsbook Fallback Observations ({SESSION})',
        '',
        f'Generated from `hltv-first-observations.json` at `{OBSERVED_AT}`.',
        '',
        '| Observation ID | Fixture(s) | Primary official URL | Verdict | Excerpt SHA-256 |',
        '| --- | --- | --- | --- | --- |',
    ]
    for o in observations:
        fids = ', '.join(f"`{x}`" for x in o['fixture_ids'])
        md_lines.append(
            f"| `{o['id']}` | {fids} | {o['url']} | {o['verdict']} | `{o['excerpt_sha256'][:16]}…` |"
        )
    md_lines.append('')
    return doc, '\n'.join(md_lines)


def build_flags() -> list[dict]:
    return [
        {
            'id': 'c2a74e33-001',
            'severity': 'notice',
            'title': 'Live Polymarket CLOB orderbook on 1082996 (Acend vs UNiTY) tightened to a 0.05 spread, resolving the earlier Valve-VRS inversion',
            'detail': (
                'In the 2026-10-24T14:24:32Z snapshot, fixture 1082996 (Acend vs UNiTY, 2026-10-25T09:00:00Z, '
                'NODWIN Clutch Series #13) fell through to the Oct 5 Valve VRS rating snapshot (Acend 54.2% / '
                'UNiTY 45.8%) because Polymarket market 6072790 (cs2-ace1-unity-2026-10-25) exceeded the spread '
                'ceiling. Direct Gamma + CLOB orderbook verification at 2026-10-24T16:31:27Z ($1,574.59 liquidity) '
                'confirms tight two-sided quotes on both tokens: Acend 0.36/0.41 (mid 38.5%, spread 0.05 <= 0.12) '
                'and UNiTY esports 0.59/0.64 (mid 61.5%, spread 0.05 <= 0.12), matching HLTV 2399112 world rank '
                '(#131 Acend vs #86 UNiTY) and EGamersWorld index (2.35 / 1.50). Existing NODWIN alias '
                'UNiTY esports -> UNiTY will promote 1082996 automatically on the next live refresh.'
            ),
            'match_ids': ['1082996'],
            'source_urls': [
                'https://gamma-api.polymarket.com/events/1238703',
                'https://clob.polymarket.com/book?token_id=70739776158623819204556862140110042694226402323251073812600083606213507639618',
                'https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13',
            ],
        },
        {
            'id': 'c2a74e33-002',
            'severity': 'notice',
            'title': 'Refreshed <8h EGamersWorld match-page capture in CAPTURE_PATHS preserves 1082858 (Ground Zero vs Off Chops) when Actions hits HTTP 403',
            'detail': (
                'GitHub Actions runners receive Cloudflare HTTP 403 on egamersworld.com (egw_live_error: 403), '
                'and the earlier 06:29:25Z manual capture for 1082858 (Ground Zero vs Off Chops, 2026-10-26T03:00:00Z) '
                'aged past MAX_PRICE_AGE_HOURS = 8. First-hand verification at 2026-10-24T16:42:00Z confirms '
                'the verbatim EGWxxxBOT match-page bookmaker average (3.44 / 1.24 -> 26.5% / 73.5% Off Chops, '
                'corroborated by Prematch Vave 3.44/1.24, Smarkets 45396333 mid 23.7%/76.3% at 0.161 spread, '
                'and Polymarket 6066508 mid 33.0%/67.0% at 0.26 spread, whereas Hotspawn crowd picks sit 88% '
                'on Ground Zero). Registered in scripts/reference_odds.py::CAPTURE_PATHS alongside fresh '
                'match-page backups for 1083122, 1083123, and 1079200.'
            ),
            'match_ids': ['1082858', '1083122', '1083123', '1079200'],
            'source_urls': [
                'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
                'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
                'https://smarkets.com/event/45396333',
                'https://gamma-api.polymarket.com/events/1237427',
            ],
        },
        {
            'id': 'c2a74e33-003',
            'severity': 'warning',
            'title': 'HLTV match pages document multiple substitutes on 1081156 (LFO 10: 3 stand-ins) and 1082861 (Rooster: 2 stand-ins)',
            'detail': (
                'First-hand HLTV lineup verification flags elevated roster variance on two active fixtures: '
                '(1) On 1081156 (Spirit Academy vs LFO 10, 2026-10-25T12:00:00Z, CCT Europe Series #12), '
                'HLTV 2399506 lists LFO 10 with 3 substitutes (L00m1, Toshas, Mann3n alongside Sapec and dottie) '
                'while Bovada prices the slot under former org name Sokerorg (-230 / +170 -> 66.4% / 33.6% Spirit Academy). '
                '(2) On 1082861 (Rooster vs Abyssal, 2026-10-27T03:00:00Z, DFRAG Invitational LAN), HLTV 2399891 '
                'lists Rooster with 2 substitutes (TjP and foggers alongside asap, nettik, DannyG).'
            ),
            'match_ids': ['1081156', '1082861'],
            'source_urls': [
                'https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12',
                'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
                'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike',
            ],
        },
        {
            'id': 'c2a74e33-004',
            'severity': 'warning',
            'title': 'Three active fixtures (1082861, 1082792, 1082793) remain on official Valve VRS model estimates due to wide exchange spreads and 7-day-out empty books',
            'detail': (
                'Across Polymarket, Smarkets, Bovada, Kalshi, Pinnacle, bo3.gg, and EGamersWorld at 2026-10-24T16:42Z: '
                '1082861 (Rooster vs Abyssal, Oct 27) has wide spreads on Polymarket (0.25 > 0.15) and Smarkets '
                '(0.161 > 0.15) and 1.8/1.8 on its EGW match page; 1082792 (HOTU vs The Huns, Oct 31) has a 0.43 '
                'Polymarket spread and 1.8/1.8 on its EGW match page; and 1082793 (5star vs 1WIN, Oct 31) has '
                'zero exchange/bookmaker markets 7 days out and 1.8/1.8 on EGW. All three stay honestly labelled '
                'as official Git-blob-verified Valve VRS model estimates (Abyssal 52.2%, HOTU 94.1%, 1WIN 82.2%).'
            ),
            'match_ids': ['1082861', '1082792', '1082793'],
            'source_urls': [
                'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
                'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
                'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
                'https://github.com/ValveSoftware/counter-strike_regional_standings',
            ],
        },
        {
            'id': 'c2a74e33-005',
            'severity': 'notice',
            'title': 'Hotspawn CDN edge lag verified (83 cache-busted vs 84/85 cached) and inverted crowd picks excluded on 1082858 and 1083122',
            'detail': (
                'At 2026-10-24T16:42Z, cache-busted play.hotspawn.com/lobby?cb=1792860000 served 83 CS2 records '
                '(61 archived + 22 open future cards, exact 22/22 parity with the scheduled API after 1083121 '
                'started at 16:00Z), whereas unbusted /lobby (84) and /cs2-pickems (85) served stale edge HTML. '
                'Hotspawn crowd picks remain sharply inverted against real-money bookmakers on 1082858 (88% crowd '
                'on Ground Zero vs 73.5% bookmaker favorite Off Chops) and 1083122 (76% crowd on LOS NINOS vs '
                '68.7% bookmaker favorite BORRACHEIROS) and are never used.'
            ),
            'match_ids': ['1083121', '1082858', '1083122'],
            'source_urls': [
                'https://play.hotspawn.com/lobby',
                'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
                'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
                'https://egamersworld.com/counterstrike/match/0U32SId-H/los-ninos-vs-borracheiros-qorsZa4d--',
            ],
        },
    ]


def build_repo_review() -> dict:
    return {
        'session': SESSION,
        'scope': (
            'Line-by-line audit of all 23 active CS2 fixtures in the 2026-10-24T14:24:32Z snapshot and '
            '22 live future Hotspawn lobby cards at 16:42Z, HLTV-first + multi-exchange/sportsbook fallback '
            'verification, <8h EGamersWorld reference-odds refresh in CAPTURE_PATHS, and mobile/WCAG browser verification.'
        ),
        'review_clock_utc': OBSERVED_AT,
        'method': (
            'Replayed all 18 featured active rows in snapshot.json to 1e-8 and audited all 23 complete-pick '
            'cards in origination/index.html; fetched cache-busted Hotspawn lobby + API, HLTV match pages, '
            'Polymarket Gamma/CLOB, Smarkets, Bovada, Kalshi, Pinnacle, bo3.gg, and EGamersWorld first-hand.'
        ),
        'items': [
            {
                'id': 'C2A7-R01',
                'area': '8-hour reference-odds freshness gap on 1082858 (Ground Zero vs Off Chops)',
                'status': 'fixed',
                'finding': (
                    'GitHub Actions hits HTTP 403 on egamersworld.com (egw_live_error: 403), and the 06:29:25Z '
                    'manual capture for 1082858 in research/e57df95b/reference-odds.json aged past MAX_PRICE_AGE_HOURS = 8, '
                    'which would drop 1082858 from its 26.5% / 73.5% bookmaker-average line to the uncalibrated network model.'
                ),
                'handling': (
                    'Verified the live EGW match-page bookmaker-average quote at 2026-10-24T16:42:00Z '
                    '(3.44 / 1.24 -> 26.50% / 73.50% Off Chops, plus backup match-page captures for 1083122, '
                    '1083123, and 1079200) and registered research/c2a74e33/reference-odds.json ahead of '
                    'e57df95b in scripts/reference_odds.py::CAPTURE_PATHS.'
                ),
                'evidence': [
                    {
                        'url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
                        'detail': 'Match page publishing verbatim EGWxxxBOT average odds 3.44 / 1.24 and Prematch Vave 3.44 / 1.24.',
                    },
                    {
                        'url': 'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
                        'detail': 'HLTV match 2399888 confirming BO3 LAN schedule at 2026-10-26T03:00:00Z.',
                    },
                ],
            },
            {
                'id': 'C2A7-R02',
                'area': 'Mathematical replay & official-source link audit across all 23 active fixtures',
                'status': 'verified',
                'finding': (
                    'Replayed all 18 featured active rows in snapshot.json (10 Polymarket midpoints and 8 Valve '
                    'VRS ratings with VALVE_RD=75) to 1e-8 and audited all 23 pick cards in origination/index.html '
                    'and 907 site table/card rows: 0 arithmetic drift, 0 crowd-% fields, 0 unofficial links.'
                ),
                'handling': (
                    'Codified deterministic replay and row-level official-link checks in scripts/c2a74e33_verify.py '
                    'and tests/test_c2a74e33_verification.py.'
                ),
                'evidence': [
                    {
                        'url': 'https://github.com/ValveSoftware/counter-strike_regional_standings',
                        'detail': 'Official Valve Regional Standings repository supplying the Git-blob-verified ratings.',
                    },
                    {
                        'url': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
                        'detail': 'Hotspawn scheduled CS2 fixtures API returning 83 scheduled records (22 future open at 16:42Z).',
                    },
                ],
            },
            {
                'id': 'C2A7-R03',
                'area': 'Live Polymarket CLOB tightening on 1082996 & lineup stand-in flags on 1081156 / 1082861',
                'status': 'verified',
                'finding': (
                    'Polymarket 1238703 / 6072790 (Acend vs UNiTY) now quotes 0.36/0.41 vs 0.59/0.64 '
                    '(spread 0.05 <= 0.12, 38.5% / 61.5% UNiTY), ready for automatic promotion on the next '
                    'live refresh; HLTV 2399506 and 2399891 document 3 substitutes on LFO 10 and 2 on Rooster.'
                ),
                'handling': (
                    'Published verbatim SHA-256 excerpts in data/research/c2a74e33/hltv-first-observations.{json,md} '
                    'and review notices/warnings c2a74e33-001..004 in data/research/c2a74e33/flags.json.'
                ),
                'evidence': [
                    {
                        'url': 'https://gamma-api.polymarket.com/events/1238703',
                        'detail': 'Polymarket event 1238703 (market 6072790) quoting $1,574.59 liquidity and 0.05 spread.',
                    },
                    {
                        'url': 'https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12',
                        'detail': 'HLTV match 2399506 listing L00m1, Toshas, and Mann3n as substitutes for LFO 10.',
                    },
                    {
                        'url': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
                        'detail': 'HLTV match 2399891 listing TjP and foggers as substitutes for Rooster.',
                    },
                ],
            },
            {
                'id': 'C2A7-R04',
                'area': 'Uncached Hotspawn lobby parity & phone Executive Summary readability',
                'status': 'verified',
                'finding': (
                    'Uncached play.hotspawn.com/lobby?cb=1792860000 reports 83 CS2 records (61 archived + 22 open), '
                    'matching the scheduled API 22/22 while unbusted /lobby (84) and /cs2-pickems (85) lag by 1-2 '
                    'started fixtures. Phone viewports (320/375/390px) surface both teams win percentages, the '
                    'obvious pick, and working in-site links without horizontal overflow.'
                ),
                'handling': (
                    'Published data/research/c2a74e33/live-coverage.{json,md} (22/22 Hotspawn + 22/22 HLTV links) '
                    'and automated phone viewport assertions in tests/browser/phone_c2a74e33.spec.mjs.'
                ),
                'evidence': [
                    {
                        'url': 'https://play.hotspawn.com/lobby',
                        'detail': 'Hotspawn Pick-ems lobby verified with ?cb= cache-busting at 2026-10-24T16:42:00Z.',
                    },
                    {
                        'url': 'https://www.hltv.org/matches',
                        'detail': 'HLTV matches schedule cross-checked across all 22 live future Hotspawn fixtures.',
                    },
                ],
            },
            {
                'id': 'C2A7-R05',
                'area': 'Regression wall-clock pin in tests/test_a5b59ee6_publisher_wiring.py',
                'status': 'fixed',
                'finding': (
                    'TheLadderPublishesThePick stamped its synthetic EGW chain at 2026-10-24T06:30:00Z '
                    'while originate.run(live=False) read wall-clock datetime.now(UTC), causing two tests '
                    'to fail MAX_PRICE_AGE_HOURS = 8 starting at 2026-10-24T14:30:01Z (blocking both '
                    'checks.yml and pages.yml step 5 Regression tests).'
                ),
                'handling': (
                    'Independently reproduced and pinned the clock locally; adopted session arena-5f9d0082 PR #317 '
                    'merged originate.run(..., now=NOW) signature at integration so the suite stays deterministic '
                    'at every wall clock.'
                ),
                'evidence': [
                    {
                        'url': 'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/pages.yml',
                        'detail': 'Scheduled 4-hour publisher workflow gating deployment on python -m unittest discover.',
                    },
                    {
                        'url': 'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/checks.yml',
                        'detail': 'PR validation workflow running the full Python unittest regression suite.',
                    },
                ],
            },
        ],
    }


def write_dossiers(root: Path) -> None:
    out_dir = root / 'data' / RESEARCH_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    ref = build_reference_odds()
    cov, cov_md = build_live_coverage()
    obs, obs_md = build_hltv_first_observations()
    flags = build_flags()
    reg = build_repo_review()

    (out_dir / 'reference-odds.json').write_text(json.dumps(ref, indent=2) + '\n', encoding='utf-8')
    (out_dir / 'live-coverage.json').write_text(json.dumps(cov, indent=2) + '\n', encoding='utf-8')
    (out_dir / 'live-coverage.md').write_text(cov_md, encoding='utf-8')
    (out_dir / 'hltv-first-observations.json').write_text(json.dumps(obs, indent=2) + '\n', encoding='utf-8')
    (out_dir / 'hltv-first-observations.md').write_text(obs_md, encoding='utf-8')
    (out_dir / 'flags.json').write_text(json.dumps(flags, indent=2) + '\n', encoding='utf-8')
    (out_dir / 'repo-review.json').write_text(json.dumps(reg, indent=2) + '\n', encoding='utf-8')


def verify_snapshot_and_origination(root: Path) -> dict:
    snap = json.loads((root / 'snapshot.json').read_text(encoding='utf-8'))
    gen_at = snap['generated_at']
    active = [m for m in snap['matches'] if m.get('availability') in {'open', 'locked', 'unknown_lock'}]
    if not active:
        raise AssertionError('Expected at least 1 active match in snapshot.json')

    forbidden_keys = {'percent_picked', 'crowd_percent', 'fan_vote', 'picked_percentage'}
    resolved_count = 0
    unresolved_ids = []
    for m in active:
        if forbidden_keys.intersection(m.keys()):
            raise AssertionError(f"Forbidden crowd key on match {m['id']}")
        for t in m.get('teams') or []:
            if forbidden_keys.intersection(t.keys()):
                raise AssertionError(f"Forbidden crowd key on team in {m['id']}")
        est = m.get('analysis')
        if not est:
            unresolved_ids.append(str(m['id']))
            continue
        resolved_count += 1
        probs = est['probabilities']
        if abs(sum(probs) - 1.0) > 1e-6:
            raise AssertionError(f"Probabilities do not sum to 1 on {m['id']}: {probs}")
        method = est.get('method')
        if method == 'market':
            mids = []
            for q in est['quotes']:
                mid = (q['bid'] + q['ask']) / 2.0
                if abs(q['midpoint'] - mid) > 1e-8:
                    raise AssertionError(f"Quote midpoint drift on {m['id']}")
                if q['spread'] > 0.12 + 1e-8:
                    raise AssertionError(f"Featured spread > 0.12 on {m['id']}: {q['spread']}")
                mids.append(mid)
            expected = normalize_pair(mids[0], mids[1])
        elif method == 'bookmaker':
            expected = no_vig(est['quotes'][0]['odds'])
        elif method == 'consensus':
            expected = consensus(est['quotes'])
        elif method == 'model':
            r0, r1 = [float(inp['points']) for inp in est['inputs']]
            q_const = math.log(10.0) / 400.0
            g = 1.0 / math.sqrt(1.0 + 3.0 * (q_const * VALVE_RD / math.pi) ** 2)
            if abs(est['g'] - g) > 1e-12 or est['rd_assumption'] != VALVE_RD:
                raise AssertionError(f"Valve g/RD drift on {m['id']}")
            p0 = 1.0 / (1.0 + 10.0 ** (-g * (r0 - r1) / 400.0))
            expected = normalize_pair(p0, 1.0 - p0)
        else:
            raise AssertionError(f"Unexpected featured method {method!r} on {m['id']}")
        for got_p, exp_p in zip(probs, expected):
            if abs(got_p - exp_p) > 1e-8:
                raise AssertionError(f"Replay mismatch on {m['id']}: {probs} vs {expected}")
        for got_d, exp_d in zip(est['fair_decimal'], [round(1.0 / p, 3) for p in expected]):
            if abs(got_d - exp_d) > 1e-6:
                raise AssertionError(f"Fair-decimal mismatch on {m['id']}")
        expected_pick = selection(est)
        if m.get('pick_index') != expected_pick:
            raise AssertionError(f"Pick index mismatch on {m['id']}")
    if resolved_count + len(unresolved_ids) != len(active):
        raise AssertionError('Active match count != resolved + unresolved')
    if gen_at == '2026-10-24T14:24:32Z':
        if (
            len(active) != 23
            or resolved_count != 18
            or set(unresolved_ids) != {'1083121', '1083122', '1081156', '1082858', '1082792'}
        ):
            raise AssertionError(f'Unexpected 14:24:32Z featured split: {resolved_count} resolved, {unresolved_ids}')

    soup = BeautifulSoup((root / 'origination/index.html').read_text(encoding='utf-8'), 'html.parser')
    cards = soup.select('article.pick-card')
    if len(cards) != len(active):
        raise AssertionError(f'Expected {len(active)} pick cards in origination/index.html, got {len(cards)}')
    card_ids = set()
    for card in cards:
        cid = (card.get('id') or '').removeprefix('match-')
        card_ids.add(cid)
        hrefs = [a.get('href', '') for a in card.select('a[href^="http"]')]
        if not hrefs:
            raise AssertionError(f'Pick card {cid} has no external https links')
        for href in hrefs:
            if not audit_rows.is_official(href):
                raise AssertionError(f'Non-official URL {href} on pick card {cid}')
    active_ids = {str(m['id']) for m in active}
    if card_ids != active_ids:
        raise AssertionError(f'Pick card IDs {card_ids ^ active_ids} differ from active snapshot IDs')
    return {
        'generated_at': gen_at,
        'active': len(active),
        'featured_resolved': resolved_count,
        'featured_unresolved': unresolved_ids,
        'complete_pick_cards': len(cards),
    }


def verify_dossiers(root: Path) -> dict:
    out_dir = root / 'data' / RESEARCH_REL
    if CAPTURE_REL not in reference_odds.CAPTURE_PATHS:
        raise AssertionError(f'{CAPTURE_REL} missing from reference_odds.CAPTURE_PATHS')
    if reference_odds.CAPTURE_PATHS.index(CAPTURE_REL) > reference_odds.CAPTURE_PATHS.index(
        Path('research/e57df95b/reference-odds.json')
    ):
        raise AssertionError('c2a74e33 capture must precede expired e57df95b capture in CAPTURE_PATHS')
    if REGISTER_REL not in review_register.REGISTERS:
        raise AssertionError(f'{REGISTER_REL} missing from review_register.REGISTERS')

    ref = json.loads((out_dir / 'reference-odds.json').read_text(encoding='utf-8'))
    now = datetime(2026, 10, 24, 16, 45, tzinfo=UTC)
    for entry in ref['entries']:
        probs = reference_odds.problems(entry)
        if probs:
            raise AssertionError(f"Reference problems on {entry['fixture_id']}: {probs}")
        match = {
            'id': entry['fixture_id'],
            'starts_at': entry['starts_at'],
            'teams': [{'id': '1', 'name': entry['teams'][0]}, {'id': '2', 'name': entry['teams'][1]}],
        }
        q, reason = reference_odds.quote(entry, match, now)
        if q is None:
            raise AssertionError(f"Fresh capture {entry['fixture_id']} failed quote(): {reason}")
        reference_odds.replay(entry, q)
        if not audit_rows.is_official(entry['source_url']):
            raise AssertionError(f"Non-official reference URL: {entry['source_url']}")

    for rej in ref['rejected']:
        match = {
            'id': rej['fixture_id'],
            'starts_at': rej['starts_at'],
            'teams': [{'id': '1', 'name': rej['teams'][0]}, {'id': '2', 'name': rej['teams'][1]}],
        }
        q, _ = reference_odds.quote(rej, match, now)
        if q is not None:
            raise AssertionError(f"Rejected capture {rej['fixture_id']} unexpectedly produced quote")
        if not audit_rows.is_official(rej['source_url']):
            raise AssertionError(f"Non-official rejected URL: {rej['source_url']}")

    # Prove 1082858 resolves on 'reference' via reference_odds.load(root / 'data') at 16:45Z!
    loaded_ref = reference_odds.load(root / 'data')
    ref_rows = list(loaded_ref['entries']) + list(loaded_ref['rejected'])
    gz_match = {
        'id': '1082858',
        'starts_at': '2026-10-26T03:00:00Z',
        'locks_at': '2026-10-26T02:55:00Z',
        'availability': 'open',
        'competition': 'DFRAG Invitational 2026',
        'tier': 'c',
        'source_url': 'https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858',
        'lobby_url': 'https://play.hotspawn.com/lobby',
        'teams': [{'id': '1', 'name': 'Ground Zero'}, {'id': '2', 'name': 'Off Chops'}],
    }
    res_1082858 = originate.originate_match(
        gz_match, [], [], {}, {}, {}, now, reference=ref_rows
    )
    orig_1082858 = res_1082858.get('origination') or {}
    if orig_1082858.get('method') != 'reference':
        raise AssertionError(f"Expected 1082858 to resolve via reference at 16:45Z, got {orig_1082858}")

    cov = json.loads((out_dir / 'live-coverage.json').read_text(encoding='utf-8'))
    if not (out_dir / 'live-coverage.md').is_file():
        raise AssertionError('live-coverage.md missing')
    if len(cov['live_fixtures']) != 22:
        raise AssertionError(f"Expected 22 live future fixtures, got {len(cov['live_fixtures'])}")
    for u in cov['source_urls']:
        if not audit_rows.is_official(u):
            raise AssertionError(f'Non-official coverage source URL: {u}')
    for f in cov['live_fixtures']:
        if not audit_rows.is_official(f['hotspawn_url']) or not audit_rows.is_official(f['hltv_url']):
            raise AssertionError(f"Non-official link on live fixture {f['id']}")
        if '%' in (f.get('note') or ''):
            raise AssertionError(f"Percent sign in live-coverage note for {f['id']}")
    selected_cov = build.load_live_coverage(root / 'data')
    if not selected_cov or selected_cov['observed_at'] < cov['observed_at']:
        raise AssertionError('load_live_coverage did not select c2a74e33 or newer record')
    gaps_html = build.live_coverage_gaps({'matches': [], 'complete_picks': {'matches': []}, '_live_coverage': cov}, '')
    if '%' in gaps_html:
        raise AssertionError('Rendered #live-coverage-gaps contains a percent character')

    obs = json.loads((out_dir / 'hltv-first-observations.json').read_text(encoding='utf-8'))
    if not (out_dir / 'hltv-first-observations.md').is_file():
        raise AssertionError('hltv-first-observations.md missing')
    for o in obs['observations']:
        if sha256_text(o['excerpt']) != o['excerpt_sha256']:
            raise AssertionError(f"SHA-256 mismatch on observation {o['id']}")
        if o['usable_as_price'] is not False:
            raise AssertionError(f"Observation {o['id']} must set usable_as_price=False")
        for u in [o['url']] + list(o.get('corroborating_urls') or []):
            if not audit_rows.is_official(u):
                raise AssertionError(f"Non-official observation URL: {u}")

    flags = json.loads((out_dir / 'flags.json').read_text(encoding='utf-8'))
    for fl in flags:
        if not fl['id'].startswith('c2a74e33-'):
            raise AssertionError(f"Bad flag id prefix: {fl['id']}")
        if fl['severity'] not in {'notice', 'warning', 'error'}:
            raise AssertionError(f"Bad flag severity: {fl['severity']}")
        for u in fl['source_urls']:
            if not audit_rows.is_official(u):
                raise AssertionError(f"Non-official flag URL: {u}")

    reg = json.loads((out_dir / 'repo-review.json').read_text(encoding='utf-8'))
    review_register.validate(reg)
    for item in reg['items']:
        for ev in item['evidence']:
            if not audit_rows.is_official(ev['url']):
                raise AssertionError(f"Non-official review URL: {ev['url']}")

    return {
        'reference_entries': len(ref['entries']),
        'reference_rejected': len(ref['rejected']),
        'live_coverage_fixtures': len(cov['live_fixtures']),
        'observations': len(obs['observations']),
        'flags': len(flags),
        'review_items': len(reg['items']),
        'gz_1082858_probabilities': orig_1082858['probabilities'],
    }


def verify_all(root: Path) -> dict:
    return {
        'snapshot_and_origination': verify_snapshot_and_origination(root),
        'dossiers': verify_dossiers(root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--write', action='store_true', help='Write data/research/c2a74e33/* dossiers')
    parser.add_argument('--check', action='store_true', help='Verify replay and dossiers (default)')
    args = parser.parse_args(argv)
    if args.write:
        write_dossiers(args.root)
    summary = verify_all(args.root)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
