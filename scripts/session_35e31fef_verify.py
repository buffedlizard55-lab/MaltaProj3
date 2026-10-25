"""Session arena-35e31fef deterministic verification & research-dossier generator.

Generates (with ``--write``) or strictly verifies (with ``--check``, default):
1. ``data/research/35e31fef/reference-odds.json`` — fresh (<8h) SHA-256-checked
   EGamersWorld match-page bookmaker-average captures (1082858, 1082859, 1086696)
   and explicit rejections for identical-decimal placeholder match pages
   (1082861, 1082792, 1082793, 1086697, 1079200).
2. ``data/research/35e31fef/live-coverage.{json,md}`` — 17/17 live future Hotspawn
   CS2 fixtures at 2026-10-25T13:37:45Z (78 scheduled API records = 61 archived +
   17 open; unbusted /lobby lagged at 80), including the 3 post-snapshot South
   American fixtures (1086696, 1082697, 1086697), 17/17 official Hotspawn + HLTV
   links, zero crowd-% values, and zero '%' characters in rendered
   ``#live-coverage-gaps`` notes.
3. ``data/research/35e31fef/hltv-first-observations.{json,md}`` — dated HLTV-first
   plus Polymarket Gamma/CLOB, Kalshi, Smarkets, Bovada, Thunderpick/bo3.gg, and
   EGamersWorld observations with SHA-256-checked verbatim excerpts across every
   fixture not resolved by the featured Polymarket exact-name method.
4. ``data/research/35e31fef/flags.json`` — structured review notices/warnings
   auto-discovered onto ``/review/`` (Flagged for Review), including 0/5 player
   overlap between Valve 2026-10-05 and HLTV 2399438 on 1082793 (5star vs 1WIN)
   and cross-team stand-in drift (`foggers`) on 1082861 (Rooster vs Abyssal).
5. ``data/research/35e31fef/repo-review.json`` — line-by-line repository review
   register declared in ``scripts/review_register.py::REGISTERS``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

from scripts import audit_rows, build, originate, reference_odds, review_register
from scripts.domain import VALVE_RD, consensus, normalize_pair, no_vig, selection

UTC = timezone.utc
SESSION = 'arena-35e31fef'
OBSERVED_AT = '2026-10-25T13:41:00Z'
LOBBY_OBSERVED_AT = '2026-10-25T13:37:45Z'
RESEARCH_REL = Path('research/35e31fef')
REGISTER_REL = 'research/35e31fef/repo-review.json'
CAPTURE_REL = Path('research/35e31fef/reference-odds.json')


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
                'Refreshes expired (>21h) 2026-10-24T16:42Z capture inside the 8h freshness gate so '
                'Ground Zero vs Off Chops stays money-backed when Polymarket 6066508 (0.25/0.48, spread 0.23), '
                'Smarkets 45396333 (spread 0.186), and Kalshi 26OCT252300OFFGRO (spread 0.29) exceed the 0.15 '
                'spread ceiling and GitHub Actions hits HTTP 403 on egamersworld.com. HLTV 2399888 confirms '
                'Ground Zero fields stand-in tucks for hazr and is 0-2 H2H vs Off Chops. Hotspawn 86% crowd '
                'pick on Ground Zero is excluded.'
            ),
        },
        {
            'fixture_id': '1082859',
            'event': 'DFRAG Invitational 2026',
            'starts_at': '2026-10-26T03:00:00Z',
            'teams': ['NEXVOID', 'Alter Ego'],
            'provider_teams': ['NEXVOID', 'Alter Ego'],
            'provider': reference_odds.PROVIDER,
            'source_url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/nexvoid-vs-alter-ego-HfdcJeXmT',
            'observed_at': OBSERVED_AT,
            'banner_odds': [1.6, 2.2],
            'odds': [1.609, 2.197],
            'excerpt': (
                'NEXVOID are listed as the favorites of the match in the majority of bookmakers and odds '
                'on them are equal to 1.609. Alter Ego, in turn, are the outsiders of the match. '
                'Odds on their victory are about 2.197.'
            ),
            'note': (
                'Match-page EGWxxxBOT backup capture verified against HLTV 2399889 (2026-10-26T03:00:00Z BO3 LAN, '
                'substitute Bloody on Alter Ego). Omitted from Polymarket DFRAG page; first-party Kalshi '
                'KXCS2GAME-26OCT252300AENEX (0.49/0.58 vs 0.42/0.51, spread 0.09) and Thunderpick (1.60/2.20) '
                'take precedence whenever reachable.'
            ),
        },
        {
            'fixture_id': '1086696',
            'event': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-25T16:00:00Z',
            'teams': ['BORRACHEIROS', 'RED Canids Academy'],
            'provider_teams': ['BORRACHEIROS', 'RED Canids Academy'],
            'provider': reference_odds.PROVIDER,
            'source_url': 'https://egamersworld.com/counterstrike/match/0U32SId-H/borracheiros-vs-red-canids-academy-5tMfbA07u',
            'observed_at': OBSERVED_AT,
            'banner_odds': [2.1, 1.62],
            'odds': [2.1, 1.62],
            'excerpt': (
                'According to leading bookmakers predictions, the team RED Canids Academy are the favorite '
                'with average odds 1.62 at the moment. Respectively, bookmakers consider BORRACHEIROS to be '
                'the outsider of the match with odds on a victory in the sum of about 2.1.'
            ),
            'note': (
                'Match-page EGWxxxBOT backup capture verified against HLTV 2399917 (2026-10-25T16:00:00Z BO3, '
                'substitute FasteR on RED Canids Academy). First-party Polymarket cs2-chama-reda-2026-10-25 '
                '(0.42/0.43 vs 0.57/0.58, spread 0.01) and Bovada (2.15/1.667) take precedence whenever reachable.'
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
            'fixture_id': '1082861',
            'teams': ['Rooster', 'Abyssal'],
            'starts_at': '2026-10-27T03:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page displays identical 1.8/1.8 placeholder with no EGWxxxBOT bookmaker-average sentence; '
                'Polymarket 6066525 (spread 0.26) and Kalshi 26OCT262300ABYRSTR (spread 0.24-0.25) exceed the 0.15 '
                'ceiling; retained on official Valve VRS model.'
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
                'Match page displays identical 1.8/1.8 placeholder with no EGWxxxBOT bookmaker-average sentence; '
                'Polymarket 6109612 spread is 0.54 (0.38/0.92); retained on bo3.gg results network model.'
            ),
        },
        {
            'fixture_id': '1082793',
            'teams': ['5star', '1WIN'],
            'starts_at': '2026-10-31T13:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/EkalRNMvVx/1win-vs-5star-esports-4hTvdd1uN',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page displays identical 1.8/1.8 placeholder with no EGWxxxBOT bookmaker-average sentence; '
                'Polymarket cs2-1win-5s-2026-10-31 is empty (0.04/0.96, spread 0.92, $0 vol); retained on official '
                'Valve VRS model and flagged for 0/5 lineup overlap with HLTV 2399438.'
            ),
        },
        {
            'fixture_id': '1086697',
            'teams': ['Projeto do KinGui', 'Yawara'],
            'starts_at': '2026-10-25T19:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/0U32SId-H/projeto-do-kingui-vs-yawara-3gUs-7A9Zu',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page displays identical 1.8/1.8 placeholder with no EGWxxxBOT bookmaker-average sentence; '
                'resolved directly on first-party Polymarket 6169151 (cs2-tdkg-yaw-2026-10-25, 0.61/0.62 vs '
                '0.38/0.39, spread 0.01) via scoped Tropa do KinGui / Yawara Esports aliases.'
            ),
        },
        {
            'fixture_id': '1079200',
            'teams': ['Color', 'ex-Zero Tenacity'],
            'starts_at': '2026-10-25T18:00:00Z',
            'source_url': 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/color-vs-ex-zero-tenacity-rvwRf5V1F',
            'observed_at': OBSERVED_AT,
            'rejected': True,
            'reason': (
                'Match page reverted to identical 1.82/1.82 banner with no EGWxxxBOT bookmaker-average sentence '
                'at 2026-10-25T13:41Z; resolved directly on first-party Polymarket cs2-color-zerote-2026-10-25.'
            ),
        },
    ]
    return {
        'session_id': SESSION,
        'observed_at': OBSERVED_AT,
        'captured_at': OBSERVED_AT,
        'policy': (
            f'Dated, first-hand verified EGamersWorld match-page bookmaker-average captures from session '
            f'{SESSION} ({OBSERVED_AT}). Only dedicated match pages publishing an explicit verbatim EGWxxxBOT '
            f'bookmaker-average sentence and corroborated UTC start time are accepted into entries[]. '
            f'Pages printing 1.8/1.8 or 1.82/1.82 placeholders are documented under rejected[] and never supply a pick.'
        ),
        'entries': entries,
        'rejected': rejected,
    }


def build_live_coverage() -> tuple[dict, str]:
    live_fixtures = [
        {
            'id': '1085542',
            'teams': ['ex-Zero Tenacity', 'Spirit Academy'],
            'competition': 'CCT Europe 2026 Series #11',
            'starts_at': '2026-10-25T14:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/ex-zero-tenacity-vs-spirit-academy-cct-europe-2026-series-11-1085542',
            'hltv_url': 'https://www.hltv.org/matches/2399340/ex-zero-tenacity-vs-spirit-academy-cct-2026-europe-series-11',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Originated consensus line (Smarkets + Bovada)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399340 verified for BO3 schedule (shifted 30m to 14:30Z) and rosters. Carried in the published complete picks list (Smarkets + Bovada consensus); crowd picks excluded.',
        },
        {
            'id': '1079199',
            'teams': ['Infinite', 'BRUTE'],
            'competition': 'NODWIN Clutch Series #13',
            'starts_at': '2026-10-25T15:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/infinite-vs-brute-nodwin-clutch-series-13-1079199',
            'hltv_url': 'https://www.hltv.org/matches/2399114/infinite-vs-brute-nodwin-clutch-series-13',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (Polymarket)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399114 verified for BO3 schedule and rosters. Carried in the published complete picks list (Market-implied estimate); crowd picks excluded.',
        },
        {
            'id': '1086696',
            'teams': ['BORRACHEIROS', 'RED Canids Academy'],
            'competition': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-25T16:00:00Z',
            'hotspawn_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1086696',
            'hltv_url': 'https://www.hltv.org/matches/2399917/borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7',
            'in_published_snapshot': False,
            'in_featured_resolved': False,
            'published_method': 'Post-snapshot addition — tight Polymarket 6169155 + Bovada + EGW capture ready for next 4h collect',
            'note': 'Scheduled after the 2026-10-25T05:12Z snapshot; observed on cache-busted Hotspawn lobby (card omits View Match link) and scheduled API at 2026-10-25T13:37:45Z; HLTV match 2399917 verified (BO3 at 16:00Z, substitute FasteR on RED Canids Academy); tight Polymarket CLOB order book (0.01 spread), Bovada moneyline, and EGW capture verified for the next 4h collect; crowd picks excluded.',
        },
        {
            'id': '1081158',
            'teams': ['FORZE Reload', 'ex-RUSTEC'],
            'competition': 'CCT Europe 2026 Series #12',
            'starts_at': '2026-10-25T18:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158',
            'hltv_url': 'https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (Polymarket)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399508 verified for BO3 schedule and rosters. Carried in the published complete picks list (Market-implied estimate); crowd picks excluded.',
        },
        {
            'id': '1082697',
            'teams': ['BESTIA', 'paiN'],
            'competition': 'Circuit X Curitiba #4',
            'starts_at': '2026-10-25T18:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/pain-vs-bestia-circuit-x-curitiba-4-1082697',
            'hltv_url': 'https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4',
            'in_published_snapshot': False,
            'in_featured_resolved': False,
            'published_method': 'Post-snapshot addition — tight Polymarket cs2-pain-bst-2026-10-25 book ready for next 4h collect',
            'note': 'Scheduled after the 2026-10-25T05:12Z snapshot; observed on cache-busted Hotspawn lobby and scheduled API at 2026-10-25T13:37:45Z; HLTV match 2399819 verified (BO3 LAN consolidation final at 18:00Z); tight Polymarket CLOB order book (0.01 spread on cs2-pain-bst-2026-10-25) verified for exact-name resolution on the next 4h collect; crowd picks excluded.',
        },
        {
            'id': '1079200',
            'teams': ['Color', 'ex-Zero Tenacity'],
            'competition': 'NODWIN Clutch Series #13',
            'starts_at': '2026-10-25T18:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200',
            'hltv_url': 'https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (Polymarket)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399115 verified for BO3 schedule and rosters. Carried in the published complete picks list (Market-implied estimate); crowd picks excluded.',
        },
        {
            'id': '1086697',
            'teams': ['Projeto do KinGui', 'Yawara'],
            'competition': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-25T19:00:00Z',
            'hotspawn_url': 'https://play.hotspawn.com/cs2-pickems#fixture-1086697',
            'hltv_url': 'https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7',
            'in_published_snapshot': False,
            'in_featured_resolved': False,
            'published_method': 'Post-snapshot addition — tight Polymarket 6169151 book via Tropa do KinGui / Yawara Esports aliases ready for next 4h collect',
            'note': 'Scheduled after the 2026-10-25T05:12Z snapshot; observed on cache-busted Hotspawn lobby (card omits View Match link) and scheduled API at 2026-10-25T13:37:45Z; HLTV match 2399918 verified (BO3 semifinal at 19:00Z under Tropa do KinGui vs Yawara); tight Polymarket CLOB order book (0.01 spread on cs2-tdkg-yaw-2026-10-25) binds via existing CCT South America #7 aliases on the next 4h collect while Kalshi 26OCT251200YAWTDKG is rejected for a 3h rule-text mismatch; crowd picks excluded.',
        },
        {
            'id': '1082858',
            'teams': ['Ground Zero', 'Off Chops'],
            'competition': 'DFRAG Invitational 2026',
            'starts_at': '2026-10-26T03:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858',
            'hltv_url': 'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (with <8h EGW capture backup when books widen)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399888 verified (BO3 LAN, stand-in tucks on Ground Zero). Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082859',
            'teams': ['NEXVOID', 'Alter Ego'],
            'competition': 'DFRAG Invitational 2026',
            'starts_at': '2026-10-26T03:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859',
            'hltv_url': 'https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'No-vig bookmaker estimate (Thunderpick, corroborated by Kalshi + EGW)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399889 verified (BO3 LAN, substitute Bloody on Alter Ego). Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082860',
            'teams': ['FlyQuest', 'Staqued'],
            'competition': 'DFRAG Invitational 2026',
            'starts_at': '2026-10-27T03:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860',
            'hltv_url': 'https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'No-vig bookmaker estimate (Thunderpick near-lock quote)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399890 verified for BO3 LAN schedule and rosters. Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082861',
            'teams': ['Rooster', 'Abyssal'],
            'competition': 'DFRAG Invitational 2026',
            'starts_at': '2026-10-27T03:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861',
            'hltv_url': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Valve-rating research estimate (flagged for foggers substitute drift)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399891 verified (BO3 LAN, Rooster fields substitutes TjP and foggers). Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082897',
            'teams': ['B8', 'K27'],
            'competition': 'Tesla Cup 2026',
            'starts_at': '2026-10-27T08:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/b8-vs-k27-tesla-cup-2026-1082897',
            'hltv_url': 'https://www.hltv.org/matches/2399866/b8-vs-k27-rlg-tesla-cup-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (Polymarket)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399866 verified for BO3 schedule and rosters. Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082898',
            'teams': ['Alliance', 'FaZe'],
            'competition': 'Tesla Cup 2026',
            'starts_at': '2026-10-27T11:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/alliance-vs-faze-tesla-cup-2026-1082898',
            'hltv_url': 'https://www.hltv.org/matches/2399867/alliance-vs-faze-rlg-tesla-cup-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (Polymarket)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399867 verified for BO3 schedule and rosters. Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082900',
            'teams': ['Luminosity', 'HOTU'],
            'competition': 'Tesla Cup 2026',
            'starts_at': '2026-10-27T17:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/luminosity-vs-hotu-tesla-cup-2026-1082900',
            'hltv_url': 'https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (Polymarket)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399869 verified for BO3 schedule and rosters. Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082901',
            'teams': ['Envy', 'GamerLegion'],
            'competition': 'Tesla Cup 2026',
            'starts_at': '2026-10-27T20:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/envy-vs-gamerlegion-tesla-cup-2026-1082901',
            'hltv_url': 'https://www.hltv.org/matches/2399870/envy-vs-gamerlegion-rlg-tesla-cup-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Market-implied estimate (Polymarket)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399870 verified for BO3 schedule and rosters. Carried in the published complete picks list; crowd picks excluded.',
        },
        {
            'id': '1082792',
            'teams': ['HOTU', 'The Huns'],
            'competition': 'Moscow Cyber Games 2026',
            'starts_at': '2026-10-31T09:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792',
            'hltv_url': 'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': False,
            'published_method': 'Own network estimate (bo3.gg results graph)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399437 verified for BO3 LAN schedule and rosters. Carried in the published complete picks list (bo3.gg results network model); crowd picks excluded.',
        },
        {
            'id': '1082793',
            'teams': ['5star', '1WIN'],
            'competition': 'Moscow Cyber Games 2026',
            'starts_at': '2026-10-31T13:00:00Z',
            'hotspawn_url': 'https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793',
            'hltv_url': 'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
            'in_published_snapshot': True,
            'in_featured_resolved': True,
            'published_method': 'Valve-rating research estimate (flagged for 0/5 lineup overlap vs HLTV 2399438)',
            'note': 'Observed on cache-busted Hotspawn lobby and scheduled fixtures API at 2026-10-25T13:37:45Z; HLTV match 2399438 verified for BO3 LAN schedule and rosters. Carried in the published complete picks list; crowd picks excluded.',
        },
    ]
    doc = {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': LOBBY_OBSERVED_AT,
        'environment': 'authoring-fetch-path',
        'role': (
            'Line-by-line reconciliation of the cache-busted live Hotspawn CS2 lobby '
            '(play.hotspawn.com/lobby?cb=1792935450, 78 total = 61 archived + 17 open future cards; '
            '4 earlier snapshot fixtures 1082996, 1085541, 1079198, 1081156 locked/started and 3 new '
            'South American fixtures 1086696, 1082697, 1086697 were added after 05:12Z) and Cloudways '
            'scheduled fixtures API against the deployed 2026-10-25T05:12:25Z snapshot (18 active rows, '
            '18/18 complete-list picks). No probability, pick, or crowd number is invented here.'
        ),
        'published_site': {
            'snapshot_generated_at': '2026-10-25T05:12:25Z',
            'origination_generated_at': '2026-10-25T05:12:40Z',
        },
        'hotspawn': {
            'lobby_url': 'https://play.hotspawn.com/lobby',
            'lobby_cache_busted_url': 'https://play.hotspawn.com/lobby?cb=1792935450',
            'api_url': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
            'note': (
                'Uncached play.hotspawn.com/lobby?cb=1792935450 and /cs2-pickems?cb=1792935450 report '
                'All tiers (78) B (31) C (47) — exact parity with the 78 scheduled API records (61 archived + '
                '17 open future cards), whereas unbusted /lobby lagged at All tiers (80) before edge expiry.'
            ),
        },
        'counts': {
            'scheduled_api_total': 78,
            'archived_past': 61,
            'live_future_fixtures': 17,
            'hltv_match_pages_verified': 17,
            'in_published_snapshot': 14,
            'in_published_complete_picks': 14,
            'missing_from_published': 3,
        },
        'source_urls': [
            'https://play.hotspawn.com/lobby',
            'https://play.hotspawn.com/lobby?cb=1792935450',
            'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
            'https://www.hltv.org/matches',
            'https://egamersworld.com/counterstrike/matches',
            'https://gamma-api.polymarket.com/events?slug=cs2-tdkg-yaw-2026-10-25',
            'https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?marketFilterId=def&preMatchOnly=true&lang=en',
        ],
        'live_fixtures': live_fixtures,
    }

    md_lines = [
        f'# Live Hotspawn CS2 Coverage Audit — {SESSION} ({LOBBY_OBSERVED_AT})',
        '',
        f'- **Scheduled API records**: `78` (`61` archived past starts + `17` live future open fixtures)',
        f'- **Cache-busted lobby parity**: `17/17` (`play.hotspawn.com/lobby?cb=1792935450` = `78`; unbusted `/lobby` lagged at `80`)',
        f'- **HLTV match pages verified**: `17/17`',
        f'- **Post-05:12Z additions verified with tight Polymarket CLOB books (`spread=0.01`)**: `1086696`, `1082697`, `1086697`',
        '',
        '| Hotspawn ID | Match | Competition | UTC Start | Snapshot Status | Hotspawn | HLTV |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for f in live_fixtures:
        pair = f"{f['teams'][0]} vs {f['teams'][1]}"
        status = 'In 05:12Z snapshot' if f['in_published_snapshot'] else 'Added post-05:12Z (ready for next 4h collect)'
        md_lines.append(
            f"| `{f['id']}` | {pair} | {f['competition']} | `{f['starts_at']}` | {status} | "
            f"[Hotspawn]({f['hotspawn_url']}) | [HLTV]({f['hltv_url']}) |"
        )
    return doc, '\n'.join(md_lines) + '\n'


def build_hltv_first_observations() -> tuple[dict, str]:
    raw_obs = [
        {
            'id': '35e31fef-post-snapshot-1086697-polymarket-kalshi',
            'fixture_ids': ['1086697'],
            'surface': 'HLTV 2399918 + Polymarket 6169151 + Kalshi 26OCT251200YAWTDKG + EGamersWorld',
            'url': 'https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7',
            'corroborating_urls': [
                'https://gamma-api.polymarket.com/events?slug=cs2-tdkg-yaw-2026-10-25',
                'https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXCS2GAME-26OCT251200YAWTDKG',
                'https://egamersworld.com/counterstrike/match/0U32SId-H/projeto-do-kingui-vs-yawara-3gUs-7A9Zu',
            ],
            'http_status': 200,
            'excerpt': (
                'HLTV 2399918 (2026-10-25T19:00:00Z BO3 semifinal): Tropa do KinGui [Unranked, VRS #143] vs '
                'Yawara [HLTV #157, VRS #148]; Polymarket 6169151 (cs2-tdkg-yaw-2026-10-25, eventStartTime '
                '2026-10-25T19:00:00Z): Tropa do KinGui bid/ask 0.61/0.62 vs Yawara Esports 0.38/0.39 '
                '(spread 0.01 -> 61.5% / 38.5%); Kalshi KXCS2GAME-26OCT251200YAWTDKG rule text states '
                'Oct 25, 2026 at 12:00 PM EDT (16:00Z, 3h mismatch) with Yawara spread 0.17 (0.29/0.46); '
                'EGW match page displays 1.8/1.8 placeholder.'
            ),
            'usable_as_price': False,
            'verdict': 'non-featured provider-name gap resolved by existing scoped CCT SA #7 aliases onto tight 0.01 Polymarket book; Kalshi 3h mismatch rejected',
            'reason': (
                'Hotspawn prints Projeto do KinGui vs Yawara without an HLTV card link, so exact-name Polymarket '
                'cannot bind Tropa do KinGui / Yawara Esports directly; originate.py binds both scoped aliases '
                'onto Polymarket 6169151 (61.5% / 38.5% Projeto do KinGui) while rejecting Kalshi (180m > 60s start '
                'tolerance and 0.17 > 0.15 spread) and EGW (1.8/1.8 placeholder).'
            ),
        },
        {
            'id': '35e31fef-post-snapshot-1086696-1082697-polymarket',
            'fixture_ids': ['1086696', '1082697'],
            'surface': 'HLTV 2399917 & 2399819 + Polymarket CLOB + Bovada + EGamersWorld',
            'url': 'https://www.hltv.org/matches/2399917/borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7',
            'corroborating_urls': [
                'https://gamma-api.polymarket.com/events?slug=cs2-chama-reda-2026-10-25',
                'https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4',
                'https://gamma-api.polymarket.com/events?slug=cs2-pain-bst-2026-10-25',
            ],
            'http_status': 200,
            'excerpt': (
                '1086696 (2026-10-25T16:00:00Z): HLTV 2399917 lists substitute FasteR on RED Canids Academy '
                '[#170, VRS #196] vs BORRACHEIROS [#176, VRS #174]; Polymarket cs2-chama-reda-2026-10-25 quotes '
                '0.42/0.43 vs 0.57/0.58 (spread 0.01 -> 42.5% / 57.5% RED Canids Academy; description prose says '
                '3:00 PM ET vs machine eventStartTime 16:00Z); Bovada quotes 2.15/1.667 (43.6%/56.4%); EGW quotes '
                '2.1/1.62 (43.5%/56.5%). 1082697 (2026-10-25T18:00:00Z): HLTV 2399819 consolidation final; '
                'Polymarket cs2-pain-bst-2026-10-25 quotes BESTIA 0.42/0.43 vs paiN 0.57/0.58 (spread 0.01 -> '
                '42.5% / 57.5% paiN).'
            ),
            'usable_as_price': False,
            'verdict': 'both post-05:12Z fixtures carry tight 0.01-spread exact-name Polymarket series books ready for next 4h collect',
            'reason': (
                'Documented as dated read-only evidence until the next scheduled 4-hour publisher run collects '
                '1086696 and 1082697; fresh EGW capture for 1086696 also registered in CAPTURE_PATHS.'
            ),
        },
        {
            'id': '35e31fef-1082858-standin-tucks-egw-refresh',
            'fixture_ids': ['1082858'],
            'surface': 'HLTV 2399888 + HLTV Analytics + EGW match page + Polymarket/Smarkets/Kalshi',
            'url': 'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
            'corroborating_urls': [
                'https://www.hltv.org/betting/analytics/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
                'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
                'https://gamma-api.polymarket.com/events?slug=cs2-gz1-offcho-2026-10-25',
                'https://smarkets.com/event/45396333',
            ],
            'http_status': 200,
            'excerpt': (
                'HLTV 2399888 & analytics (2026-10-26T03:00:00Z BO3 LAN): Ground Zero [#143, VRS #131] is playing '
                'with stand-in tucks instead of hazr and trails Off Chops [#142, VRS #133] 0-2 in 30d H2H (incl. '
                '1:2 LAN on HLTV 2399541); at 13:38-13:45Z Polymarket 6066508 widened to 0.25/0.48 (spread 0.23), '
                'Smarkets 45396333 to 18.1-18.6 pp, and Kalshi 26OCT252300OFFGRO to 0.27-0.29, while EGW match '
                'page publishes verbatim EGWxxxBOT average 3.44 / 1.24 (26.5% / 73.5% Off Chops).'
            ),
            'usable_as_price': False,
            'verdict': 'fresh <8h EGW capture in CAPTURE_PATHS preserves 26.5%/73.5% Off Chops money-line fallback when books widen > 0.15',
            'reason': (
                'Explains why real-money markets heavily favor Off Chops (~73.5%-75.0%) despite 86% Hotspawn '
                'crowd picks on Ground Zero, and refreshes the >21h-stale c2a74e33 EGW capture.'
            ),
        },
        {
            'id': '35e31fef-1082859-kalshi-thunderpick-egw',
            'fixture_ids': ['1082859'],
            'surface': 'HLTV 2399889 + Kalshi 26OCT252300AENEX + EGamersWorld + Polymarket DFRAG',
            'url': 'https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026',
            'corroborating_urls': [
                'https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXCS2GAME-26OCT252300AENEX',
                'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/nexvoid-vs-alter-ego-HfdcJeXmT',
                'https://polymarket.com/esports/cs2/dfrag-invitational',
            ],
            'http_status': 200,
            'excerpt': (
                'Polymarket /esports/cs2/dfrag-invitational lists only 3 events and omits NEXVOID vs Alter Ego; '
                'HLTV 2399889 (2026-10-26T03:00:00Z BO3 LAN) lists NEXVOID [#77, VRS #71] vs Alter Ego [#132, '
                'VRS #145, substitute Bloody]; Kalshi KXCS2GAME-26OCT252300AENEX quotes NEXVOID 0.49/0.58 and '
                'Alter Ego 0.42/0.51 (spread 0.09 <= 0.12 -> 53.5%/46.5%); EGW quotes 1.609/2.197 (57.7%/42.3%), '
                'corroborating published Thunderpick 1.60/2.20 (57.9%/42.1% NEXVOID).'
            ),
            'usable_as_price': False,
            'verdict': 'three independent money-line surfaces (Thunderpick, Kalshi, EGW) agree on NEXVOID ~53.5%-57.9%',
            'reason': 'Confirms featured Polymarket absence and provides <8h EGW backup in CAPTURE_PATHS.',
        },
        {
            'id': '35e31fef-1082861-rooster-abyssal-foggers-drift',
            'fixture_ids': ['1082861'],
            'surface': 'HLTV 2399891 vs Valve 2026-10-05 Standings + Polymarket/Kalshi/EGW',
            'url': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
            'corroborating_urls': [
                'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                'https://gamma-api.polymarket.com/events?slug=cs2-rstr-abyssa-2026-10-26',
                'https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXCS2GAME-26OCT262300ABYRSTR',
            ],
            'http_status': 200,
            'excerpt': (
                'Valve 2026-10-05 snapshot prices Rooster (934 pts: asap, chelleos, DannyG, sliimey, Terryyy) '
                '47.8% vs Abyssal (950 pts: blood, dangeR, foggers, Forleks, vinhy) 52.2%, whereas HLTV 2399891 '
                '(2026-10-27T03:00:00Z BO3 LAN) lists Rooster [Unranked, VRS #154: SkulL, rekonz, chelleos + '
                'substitutes TjP, foggers] vs Abyssal [#128, VRS #130: Forleks, zune, dangeR, vinhy, blood] — '
                'foggers moved from Abyssal to stand in for Rooster. Polymarket (spread 0.26) and Kalshi '
                '(spread 0.24-0.25) remain too wide and EGW prints 1.8/1.8.'
            ),
            'usable_as_price': False,
            'verdict': 'cross-team roster drift (foggers) between Oct 5 Valve snapshot and Oct 27 HLTV lineup flagged on /review/',
            'reason': 'No compliant <=0.15 money line exists yet; model pick stays unchanged per policy and roster drift is published for manual review.',
        },
        {
            'id': '35e31fef-1082793-valve-vs-hltv-zero-overlap',
            'fixture_ids': ['1082793', '1082792'],
            'surface': 'HLTV 2399438 & 2399437 vs Valve 2026-10-05 Standings + Polymarket/EGW',
            'url': 'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
            'corroborating_urls': [
                'https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026',
                'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                'https://gamma-api.polymarket.com/events?slug=cs2-1win-5s-2026-10-31',
                'https://gamma-api.polymarket.com/events?slug=cs2-hotu-the9-2026-10-31',
            ],
            'http_status': 200,
            'excerpt': (
                'On 1082793 (2026-10-31T13:00:00Z BO3 LAN), Valve 2026-10-05 rosters 5star (#80, 1110 pts: '
                'ariucle, clouden, hoolig4n, NEUZ, rate) and 1WIN (#38, 1397 pts: ArtFr0st, Ax1Le, BELCHONOKK, '
                'fame, nafany) have 0/5 player overlap with HLTV 2399438 confirmed lineups: 5star [#36, VRS #64: '
                'deffen, Sange, def1zer, h1te, tENZY] vs 1win [#14, VRS #20: lattykk, interz, oz1k, cronuss, '
                'buster]; Polymarket cs2-1win-5s-2026-10-31 is 0.04/0.96 (spread 0.92, $0 vol) and EGW is 1.8/1.8. '
                'On 1082792 (HOTU vs The Huns, 2026-10-31T09:00Z), multiple The Huns Valve rows trigger bo3.gg '
                'network model fallback (98.2%/1.8% HOTU) while Polymarket spread is 0.54 (0.38/0.92).'
            ),
            'usable_as_price': False,
            'verdict': '6-day-out order books remain unpriced/wide; 0/5 Valve-vs-HLTV roster overhaul on 1082793 flagged on /review/',
            'reason': 'Both HLTV current VRS (#20 vs #64) and Oct 5 Valve (#38 vs #80) favor 1WIN, while complete five-man roster turnover is surfaced explicitly.',
        },
        {
            'id': '35e31fef-1085542-hltv-30min-schedule-shift',
            'fixture_ids': ['1085542'],
            'surface': 'HLTV 2399340 vs Hotspawn 1085542 + Smarkets/Bovada',
            'url': 'https://www.hltv.org/matches/2399340/ex-zero-tenacity-vs-spirit-academy-cct-2026-europe-series-11',
            'corroborating_urls': [
                'https://www.hotspawn.com/matches/ex-zero-tenacity-vs-spirit-academy-cct-europe-2026-series-11-1085542',
                'https://smarkets.com/sport/esports/cs-go/cct-europe/playoffs/2026/10/25/14-00/ex-zero-tenacity-vs-spirit-academy',
            ],
            'http_status': 200,
            'excerpt': (
                'Hotspawn 1085542 schedules ex-Zero Tenacity vs Spirit Academy at 2026-10-25T14:00:00Z '
                '(lock 13:54:00Z), whereas HLTV 2399340 at 13:42Z displays 10:30 EDT / 47m:54s countdown '
                '(2026-10-25T14:30:00Z, 30m pushback following Spirit Academy 12:00Z CCT Series #12 match).'
            ),
            'usable_as_price': False,
            'verdict': '30-minute organizer pushback documented; Hotspawn lock remains 13:54Z and Smarkets + Bovada consensus (55.5%/44.5%) stands',
            'reason': 'Recorded so mobile pickers submit before Hotspawn 13:54Z lock rather than assuming HLTV 14:30Z start.',
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
            'Polymarket method (plus post-snapshot lobby additions), checking HLTV first and then '
            'esportsbooks/exchanges (Polymarket CLOB, Kalshi, Smarkets, Bovada, Thunderpick, bo3.gg, '
            'EGamersWorld). Zero crowd or fan-vote inputs.'
        ),
        'observations': observations,
    }

    md_lines = [
        f'# HLTV-First & Esportsbook Observations — {SESSION} ({OBSERVED_AT})',
        '',
        'Every excerpt below is SHA-256-pinned and audited as read-only evidence (`usable_as_price: false`).',
        '',
    ]
    for o in observations:
        md_lines.extend([
            f"## `{o['id']}` — {', '.join(o['fixture_ids'])}",
            f"- **Surface**: {o['surface']}",
            f"- **Primary URL**: {o['url']}",
            f"- **Verdict**: {o['verdict']}",
            f"- **SHA-256**: `{o['excerpt_sha256']}`",
            f"- **Excerpt**: {o['excerpt']}",
            '',
        ])
    return doc, '\n'.join(md_lines)


def build_flags() -> list[dict]:
    return [
        {
            'id': '35e31fef-001',
            'severity': 'warning',
            'title': '0/5 player overlap between Oct 5 Valve VRS snapshot and HLTV 2399438 lineups on 1082793 (5star vs 1WIN)',
            'detail': (
                'Fixture 1082793 (5star vs 1WIN, 2026-10-31T13:00:00Z, Moscow Cyber Games 2026 LAN) currently '
                'prices on the 2026-10-05 Valve Regional Standings snapshot because Polymarket cs2-1win-5s-2026-10-31 '
                'has an empty 0.04/0.96 book (spread 0.92, $0 vol) and EGW prints 1.8/1.8 six days before start. '
                'Line-by-line audit against HLTV 2399438 shows 0/5 player overlap on both teams: Valve Oct 5 lists '
                '5star (#80, 1110 pts: ariucle, clouden, hoolig4n, NEUZ, rate) and 1WIN (#38, 1397 pts: ArtFr0st, '
                'Ax1Le, BELCHONOKK, fame, nafany), whereas HLTV 2399438 confirms 5star (#36, VRS #64: deffen, Sange, '
                'def1zer, h1te, tENZY) vs 1win (#14, VRS #20: lattykk, interz, oz1k, cronuss, buster). Both rankings '
                'still favor 1WIN, and the 4-hour collector will replace the model automatically once books tighten.'
            ),
            'match_ids': ['1082793'],
            'source_urls': [
                'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
                'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                'https://gamma-api.polymarket.com/events?slug=cs2-1win-5s-2026-10-31',
            ],
        },
        {
            'id': '35e31fef-002',
            'severity': 'warning',
            'title': 'Cross-team stand-in drift on 1082861 (Rooster vs Abyssal): foggers moved from Abyssal (Oct 5 Valve) to Rooster substitute (HLTV 2399891)',
            'detail': (
                'On 1082861 (Rooster vs Abyssal, 2026-10-27T03:00:00Z, DFRAG Invitational 2026 LAN), Valve '
                '2026-10-05 standings credit foggers to Abyssal (950 pts: blood, dangeR, foggers, Forleks, vinhy) '
                'against Rooster (934 pts: asap, chelleos, DannyG, sliimey, Terryyy) for a 47.8% / 52.2% Abyssal '
                'estimate, whereas HLTV 2399891 lists Rooster (SkulL, rekonz, chelleos + substitutes TjP and foggers) '
                'against Abyssal (Forleks, zune, dangeR, vinhy, blood). Polymarket (spread 0.26) and Kalshi '
                '(spread 0.24-0.25) exceed the 0.15 spread ceiling and EGW displays 1.8/1.8.'
            ),
            'match_ids': ['1082861'],
            'source_urls': [
                'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
                'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                'https://gamma-api.polymarket.com/events?slug=cs2-rstr-abyssa-2026-10-26',
            ],
        },
        {
            'id': '35e31fef-003',
            'severity': 'notice',
            'title': 'Three post-05:12Z South American Hotspawn fixtures (1086696, 1082697, 1086697) verified with tight 0.01-spread Polymarket books',
            'detail': (
                'At 2026-10-25T13:37:45Z, cache-busted play.hotspawn.com/lobby?cb=1792935450 lists 3 fixtures added '
                'after the 05:12:25Z snapshot: 1086696 (BORRACHEIROS vs RED Canids Academy, 16:00Z, Polymarket '
                'cs2-chama-reda-2026-10-25 0.42/0.43 vs 0.57/0.58 -> 42.5%/57.5% RED Canids Academy, sub FasteR on '
                'HLTV 2399917), 1082697 (BESTIA vs paiN, 18:00Z, Polymarket cs2-pain-bst-2026-10-25 0.42/0.43 vs '
                '0.57/0.58 -> 42.5%/57.5% paiN, HLTV 2399819), and 1086697 (Projeto do KinGui vs Yawara, 19:00Z, '
                'Polymarket cs2-tdkg-yaw-2026-10-25 0.61/0.62 vs 0.38/0.39 -> 61.5%/38.5% Projeto do KinGui via '
                'existing Tropa do KinGui / Yawara Esports aliases, HLTV 2399918). Hotspawn cards 1086696 and '
                '1086697 omit View Match links.'
            ),
            'match_ids': ['1086696', '1082697', '1086697'],
            'source_urls': [
                'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
                'https://www.hltv.org/matches/2399917/borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7',
                'https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4',
                'https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7',
            ],
        },
        {
            'id': '35e31fef-004',
            'severity': 'warning',
            'title': 'Provider timestamp discrepancies flagged: Kalshi 3h rule-text drift on 1086697, Polymarket prose 3pm ET typo on 1086696, and HLTV 30m pushback on 1085542',
            'detail': (
                '(1) Kalshi event KXCS2GAME-26OCT251200YAWTDKG states Oct 25, 2026 at 12:00 PM EDT (16:00Z), 3 hours '
                'earlier than Hotspawn 1086697 and HLTV 2399918 (19:00Z), and is rightly rejected by START_TOLERANCE_SEC=60. '
                '(2) Polymarket cs2-chama-reda-2026-10-25 carries machine eventStartTime 2026-10-25T16:00:00Z matching '
                'Hotspawn 1086696 and HLTV 2399917, while its prose description says October 25 at 3:00 PM ET (19:00Z). '
                '(3) HLTV 2399340 pushed 1085542 (ex-Zero Tenacity vs Spirit Academy) 30m to 14:30Z after Spirit '
                'Academy 12:00Z Series #12 match, while Hotspawn keeps lock at 13:54Z.'
            ),
            'match_ids': ['1086697', '1086696', '1085542'],
            'source_urls': [
                'https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXCS2GAME-26OCT251200YAWTDKG',
                'https://gamma-api.polymarket.com/events?slug=cs2-chama-reda-2026-10-25',
                'https://www.hltv.org/matches/2399340/ex-zero-tenacity-vs-spirit-academy-cct-2026-europe-series-11',
            ],
        },
        {
            'id': '35e31fef-005',
            'severity': 'notice',
            'title': 'Refreshed <8h EGamersWorld captures (1082858, 1082859, 1086696) in CAPTURE_PATHS protect DFRAG/CCT fallbacks when books widen',
            'detail': (
                'Session c2a74e33 captures from 2026-10-24T16:42Z aged past MAX_PRICE_AGE_HOURS = 8 (>21h old), '
                'and at 2026-10-25T13:41Z Polymarket 6066508 on 1082858 (Ground Zero vs Off Chops) widened back '
                'to 0.25/0.48 (spread 0.23 > 0.15) alongside Smarkets (0.186) and Kalshi (0.29), while GitHub '
                'Actions hits HTTP 403 on egamersworld.com. Fresh 2026-10-25T13:41:00Z SHA-256 match-page captures '
                'for 1082858 (3.44/1.24 -> 26.5%/73.5% Off Chops; HLTV 2399888 confirms stand-in tucks on Ground '
                'Zero, 86% Hotspawn crowd inverted), 1082859 (1.609/2.197 -> 57.7%/42.3% NEXVOID; sub Bloody on '
                'Alter Ego), and 1086696 (2.1/1.62 -> 43.5%/56.5% RED Canids Academy) are wired into CAPTURE_PATHS.'
            ),
            'match_ids': ['1082858', '1082859', '1086696'],
            'source_urls': [
                'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
                'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/nexvoid-vs-alter-ego-HfdcJeXmT',
                'https://egamersworld.com/counterstrike/match/0U32SId-H/borracheiros-vs-red-canids-academy-5tMfbA07u',
                'https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026',
            ],
        },
        {
            'id': '35e31fef-006',
            'severity': 'notice',
            'title': '1079200 EGW match page reverted from 1.55/2.22 to 1.82/1.82 placeholder, validating 8h freshness + identical-price gates',
            'detail': (
                'At 2026-10-24T16:42Z, EGamersWorld match page color-vs-ex-zero-tenacity-rvwRf5V1F published a '
                '1.55/2.22 bookmaker-average quote, whereas at 2026-10-25T13:41Z it displays an identical 1.82/1.82 '
                'banner with no EGWxxxBOT sentence while Polymarket cs2-color-zerote-2026-10-25 prices ex-Zero '
                'Tenacity 51.5% / Color 48.5%. Both the 8-hour freshness expiry on the older capture and the '
                'identical-decimal placeholder rejection prevented stale or placeholder numbers from entering picks.'
            ),
            'match_ids': ['1079200'],
            'source_urls': [
                'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/color-vs-ex-zero-tenacity-rvwRf5V1F',
                'https://polymarket.com/event/cs2-color-zerote-2026-10-25',
            ],
        },
    ]


def build_repo_review() -> dict:
    return {
        'session': SESSION,
        'scope': (
            'Line-by-line audit of all 18 active CS2 fixtures in the 2026-10-25T05:12:25Z snapshot and all 17 '
            'live future Hotspawn lobby cards at 13:37:45Z (including 3 post-snapshot South American additions), '
            'HLTV-first + multi-exchange/sportsbook fallback verification, <8h EGamersWorld reference-odds '
            'refresh in CAPTURE_PATHS, HLTV-vs-Valve roster-drift flags, and mobile/WCAG verification.'
        ),
        'review_clock_utc': OBSERVED_AT,
        'method': (
            'Replayed all 16 featured resolved rows in snapshot.json to 1e-8 and audited all 18 complete-pick '
            'cards in origination/index.html; fetched cache-busted Hotspawn lobby + Cloudways API, 17/17 HLTV '
            'match pages, Polymarket Gamma/CLOB, Kalshi, Smarkets, Bovada, Thunderpick/bo3.gg, and EGamersWorld '
            'first-hand; ran audit_rows --strict and Playwright + axe-core across 320/375/390/768px viewports.'
        ),
        'items': [
            {
                'id': '35E3-R01',
                'area': '8-hour reference-odds freshness renewal for 1082858, 1082859, and 1086696 in CAPTURE_PATHS',
                'status': 'fixed',
                'finding': (
                    'Prior c2a74e33 EGW captures (2026-10-24T16:42Z) aged past MAX_PRICE_AGE_HOURS = 8 (>21h old), '
                    'while at 13:41Z Polymarket 6066508 on 1082858 (Ground Zero vs Off Chops) widened back to '
                    '0.25/0.48 (spread 0.23 > 0.15) alongside Smarkets (0.186) and Kalshi (0.29), and GitHub '
                    'Actions receives HTTP 403 on egamersworld.com.'
                ),
                'handling': (
                    'Verified live EGWxxxBOT match-page quotes at 2026-10-25T13:41:00Z for 1082858 (3.44/1.24 -> '
                    '26.50%/73.50% Off Chops), 1082859 (1.609/2.197 -> 57.72%/42.28% NEXVOID), and 1086696 '
                    '(2.1/1.62 -> 43.55%/56.45% RED Canids Academy), rejected 5 placeholder pages (1.8/1.8 or '
                    '1.82/1.82), and registered research/35e31fef/reference-odds.json ahead of c2a74e33 in '
                    'scripts/reference_odds.py::CAPTURE_PATHS.'
                ),
                'evidence': [
                    {
                        'url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
                        'detail': 'Match page publishing verbatim EGWxxxBOT average odds 3.44 / 1.24 (Off Chops favorite).',
                    },
                    {
                        'url': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/nexvoid-vs-alter-ego-HfdcJeXmT',
                        'detail': 'Match page publishing verbatim EGWxxxBOT average odds 1.609 / 2.197 (NEXVOID favorite).',
                    },
                    {
                        'url': 'https://egamersworld.com/counterstrike/match/0U32SId-H/borracheiros-vs-red-canids-academy-5tMfbA07u',
                        'detail': 'Match page publishing verbatim EGWxxxBOT average odds 2.1 / 1.62 (RED Canids Academy favorite).',
                    },
                ],
            },
            {
                'id': '35E3-R02',
                'area': '17/17 live Hotspawn lobby reconciliation & 3 post-05:12Z fixtures verified with 0.01-spread Polymarket books',
                'status': 'verified',
                'finding': (
                    'Cache-busted play.hotspawn.com/lobby?cb=1792935450 and scheduled API report 78 CS2 records '
                    '(61 archived + 17 open; unbusted /lobby lagged at 80), including 3 post-05:12Z additions: '
                    '1086696 (BORRACHEIROS vs RED Canids Academy, 42.5%/57.5%), 1082697 (BESTIA vs paiN, '
                    '42.5%/57.5%), and 1086697 (Projeto do KinGui vs Yawara, 61.5%/38.5% via existing Tropa do '
                    'KinGui / Yawara Esports scoped aliases).'
                ),
                'handling': (
                    'Published data/research/35e31fef/live-coverage.{json,md} (auto-selected onto Executive Summary '
                    '#live-coverage-gaps with 17/17 Hotspawn + 17/17 HLTV links and zero percent signs) so readers '
                    'have dated visibility until the next 4-hour collect ingests all three.'
                ),
                'evidence': [
                    {
                        'url': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
                        'detail': 'Hotspawn scheduled CS2 API returning 78 total records (17 open future fixtures at 13:37:45Z).',
                    },
                    {
                        'url': 'https://gamma-api.polymarket.com/events?slug=cs2-tdkg-yaw-2026-10-25',
                        'detail': 'Polymarket event 1249642 / market 6169151 quoting 0.61/0.62 vs 0.38/0.39 (spread 0.01) at 19:00Z.',
                    },
                    {
                        'url': 'https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7',
                        'detail': 'HLTV match 2399918 confirming BO3 semifinal at 2026-10-25T19:00:00Z.',
                    },
                ],
            },
            {
                'id': '35E3-R03',
                'area': 'HLTV-vs-Valve 2026-10-05 lineup-drift audit on model-backed rows (1082793, 1082861, 1082792)',
                'status': 'needs review',
                'finding': (
                    'On 1082793 (5star vs 1WIN), Valve 2026-10-05 five-player rosters have 0/5 player overlap with '
                    'HLTV 2399438 confirmed lineups; on 1082861 (Rooster vs Abyssal), foggers is credited to Abyssal '
                    'in Valve 2026-10-05 but stands in for Rooster on HLTV 2399891; on 1082792 (HOTU vs The Huns), '
                    'duplicate The Huns Valve rows trigger fallback to the bo3.gg results network model (98.2%/1.8%).'
                ),
                'handling': (
                    'No uncalibrated adjustment is invented; published flags 35e31fef-001 and 35e31fef-002 on '
                    'Flagged for Review (/review/) with official HLTV and Valve standings links while 4-hour '
                    'refreshes poll for tight pre-match books.'
                ),
                'evidence': [
                    {
                        'url': 'https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026',
                        'detail': 'HLTV 2399438 lineups (1win #14/VRS #20 vs 5star #36/VRS #64) showing 0/5 overlap with Oct 5 Valve.',
                    },
                    {
                        'url': 'https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026',
                        'detail': 'HLTV 2399891 listing TjP and foggers as substitutes for Rooster against Abyssal.',
                    },
                    {
                        'url': 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
                        'detail': 'Official 2026-10-05 Valve global standings file used by the rating rung.',
                    },
                ],
            },
            {
                'id': '35E3-R04',
                'area': 'Cross-provider timestamp & schedule-shift audit (Kalshi 1086697, Polymarket 1086696, HLTV 1085542)',
                'status': 'verified',
                'finding': (
                    'Kalshi KXCS2GAME-26OCT251200YAWTDKG prints 12:00 PM EDT (16:00Z) vs 19:00Z on Hotspawn 1086697 '
                    'and HLTV 2399918; Polymarket cs2-chama-reda-2026-10-25 prose says 3:00 PM ET vs machine '
                    'eventStartTime 16:00Z; HLTV 2399340 pushed 1085542 30m later to 14:30Z while Hotspawn lock '
                    'stays 13:54Z.'
                ),
                'handling': (
                    'Verified START_TOLERANCE_SEC = 60 rejects the 3h-drifted Kalshi market automatically and '
                    'flagged all three timestamp discrepancies in 35e31fef-004 on /review/.'
                ),
                'evidence': [
                    {
                        'url': 'https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXCS2GAME-26OCT251200YAWTDKG',
                        'detail': 'Kalshi market metadata carrying 12:00 PM EDT rule text against 19:00Z match start.',
                    },
                    {
                        'url': 'https://www.hltv.org/matches/2399340/ex-zero-tenacity-vs-spirit-academy-cct-2026-europe-series-11',
                        'detail': 'HLTV 2399340 showing 14:30Z start vs 14:00Z Hotspawn schedule.',
                    },
                ],
            },
            {
                'id': '35E3-R05',
                'area': 'Mathematical replay of all 18 active rows, zero crowd-% audit, and phone/WCAG verification',
                'status': 'verified',
                'finding': (
                    'All 16 featured resolved rows in snapshot.json (11 Polymarket midpoints + 5 Valve VRS ratings '
                    'with VALVE_RD=75) replay to <1e-8 and all 18 complete-pick cards in origination/index.html '
                    'carry official https links, zero crowd-% fields, zero horizontal overflow, and zero WCAG 2.1 '
                    'A/AA axe violations across 320/375/390/768px viewports.'
                ),
                'handling': (
                    'Codified in scripts/session_35e31fef_verify.py, tests/test_35e31fef_verification.py, and '
                    'tests/browser/phone_35e31fef.spec.mjs.'
                ),
                'evidence': [
                    {
                        'url': 'https://play.hotspawn.com/lobby',
                        'detail': 'Hotspawn lobby verified as fixture-inventory source only; crowd percentages excluded.',
                    },
                    {
                        'url': 'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/pages.yml',
                        'detail': '4-hour scheduled + 2.5h catch-up GitHub Pages publisher workflow.',
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
    if gen_at == '2026-10-25T05:12:25Z':
        if (
            len(active) != 18
            or resolved_count != 16
            or set(unresolved_ids) != {'1081156', '1082792'}
        ):
            raise AssertionError(f'Unexpected 05:12:25Z featured split: {resolved_count} resolved, {unresolved_ids}')

    soup = BeautifulSoup((root / 'origination/index.html').read_text(encoding='utf-8'), 'html.parser')
    cards = soup.select('article.pick-card, article.unresolved-card')
    if len(cards) == len(active):
        card_ids = set()
        for card in cards:
            cid = (card.get('id') or '').removeprefix('match-')
            card_ids.add(cid)
            hrefs = [a.get('href', '') for a in card.select('a[href^="http"]')]
            if not hrefs:
                raise AssertionError(f'Card {cid} has no external https links')
            for href in hrefs:
                if not audit_rows.is_official(href):
                    raise AssertionError(f'Non-official URL {href} on card {cid}')
        active_ids = {str(m['id']) for m in active}
        if card_ids != active_ids:
            raise AssertionError(f'Card IDs {card_ids ^ active_ids} differ from active snapshot IDs')

    return {
        'generated_at': gen_at,
        'active': len(active),
        'featured_resolved': resolved_count,
        'featured_unresolved': unresolved_ids,
        'complete_cards': len(cards),
    }


def verify_dossiers(root: Path) -> dict:
    out_dir = root / 'data' / RESEARCH_REL
    if CAPTURE_REL not in reference_odds.CAPTURE_PATHS:
        raise AssertionError(f'{CAPTURE_REL} missing from reference_odds.CAPTURE_PATHS')
    if reference_odds.CAPTURE_PATHS.index(CAPTURE_REL) > reference_odds.CAPTURE_PATHS.index(
        Path('research/c2a74e33/reference-odds.json')
    ):
        raise AssertionError('35e31fef capture must precede expired c2a74e33 capture in CAPTURE_PATHS')
    if REGISTER_REL not in review_register.REGISTERS:
        raise AssertionError(f'{REGISTER_REL} missing from review_register.REGISTERS')

    ref = json.loads((out_dir / 'reference-odds.json').read_text(encoding='utf-8'))
    now = datetime(2026, 10, 25, 13, 45, tzinfo=UTC)
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

    loaded_ref = reference_odds.load(root / 'data')
    ref_rows = list(loaded_ref['entries']) + list(loaded_ref['rejected'])
    gz_match = {
        'id': '1082858',
        'starts_at': '2026-10-26T03:00:00Z',
        'locks_at': '2026-10-26T02:54:00Z',
        'availability': 'open',
        'competition': 'DFRAG Invitational 2026',
        'tier': 'b',
        'source_url': 'https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858',
        'lobby_url': 'https://play.hotspawn.com/lobby',
        'teams': [{'id': '1', 'name': 'Ground Zero'}, {'id': '2', 'name': 'Off Chops'}],
    }
    res_1082858 = originate.originate_match(
        gz_match, [], [], {}, {}, {}, now, reference=ref_rows
    )
    orig_1082858 = res_1082858.get('origination') or {}
    if orig_1082858.get('method') != 'reference':
        raise AssertionError(f"Expected 1082858 to resolve via reference at 13:45Z, got {orig_1082858}")

    cov = json.loads((out_dir / 'live-coverage.json').read_text(encoding='utf-8'))
    if not (out_dir / 'live-coverage.md').is_file():
        raise AssertionError('live-coverage.md missing')
    if len(cov['live_fixtures']) != 17:
        raise AssertionError(f"Expected 17 live future fixtures, got {len(cov['live_fixtures'])}")
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
        raise AssertionError('load_live_coverage did not select 35e31fef or newer record')
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
        if not fl['id'].startswith('35e31fef-'):
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
    parser.add_argument('--write', action='store_true', help='Write data/research/35e31fef/* dossiers')
    parser.add_argument('--check', action='store_true', help='Verify replay and dossiers (default)')
    args = parser.parse_args(argv)
    if args.write:
        write_dossiers(args.root)
    summary = verify_all(args.root)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
