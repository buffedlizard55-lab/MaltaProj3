"""Session arena-b97af12f: dated lobby/API reconciliation and research register.

The evidence below was read first-hand on 2026-10-24T06:24Z-06:35Z from the
public Hotspawn lobby, Hotspawn's own scheduled-fixture API, the published
Spawn Scout snapshot, HLTV event/match pages, Polymarket's CCT Europe board
and EGamersWorld's CS2 index/match pages.  Every row keeps its own source URL.
Nothing in this module invents a probability: Hotspawn ``% picked`` and HLTV
fan votes are recorded only to say they were excluded.

Usage:
  python -m scripts.b97af12f_reconcile            # validate embedded evidence
  python -m scripts.b97af12f_reconcile --write    # regenerate the dossier files
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
SESSION = 'arena-b97af12f'
# End of the verification window: the inventory/API rows were read at 06:24Z,
# the HLTV/Polymarket/EGW sweep at 06:30-06:35Z, and the Series 11 EGW pages
# were re-read first-hand at 06:52Z before the dossier was regenerated.
OBSERVED_AT = '2026-10-24T06:52:00Z'
SNAPSHOT_GENERATED_AT = '2026-10-23T20:10:00Z'
OUT_DIR = Path('data/research/b97af12f')
LOBBY_URL = 'https://play.hotspawn.com/lobby'
CS2_LOBBY_URL = 'https://play.hotspawn.com/cs2-pickems'
API_URL = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
           '?sport_alias=cs2&status=scheduled&tenantId=1')
PUBLISHED_DATA_URL = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json'
PUBLISHED_PICKS_URL = 'https://buffedlizard55-lab.github.io/MaltaProj3/picks/'
PUBLISHED_ORIGINATION_URL = 'https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks'

# Exact scheduled_start_time epoch milliseconds transcribed from the official
# fixture API chunks read on 2026-10-24T06:24Z-06:35Z.  The same API reports
# lock_offset_sec=360, so lock_at is start - 360 s (the rules page separately
# says five minutes; that discrepancy is already flagged in existing research).
LOBBY_FIXTURES = [
    ('1079658', ['Acend', 'FORZE Reload'], 'CCT Europe 2026 Series #11', 1792828800000,
     'acend-vs-forze-reload-cct-europe-2026-series-11-1079658', False),
    ('1079193', ['FOKUS', 'ex-6666'], 'NODWIN Clutch Series #13', 1792828800000,
     'fokus-vs-ex-6666-nodwin-clutch-series-13-1079193', True),
    ('1081152', ['HAVU', 'Azuolas'], 'CCT Europe 2026 Series #12', 1792839600000,
     'havu-vs-azuolas-cct-europe-2026-series-12-1081152', False),
    ('1079659', ['Spirit Academy', 'Lavked'], 'CCT Europe 2026 Series #11', 1792839600000,
     'spirit-academy-vs-lavked-cct-europe-2026-series-11-1079659', False),
    ('1081153', ['Saint Sinners', '6yuBoJlbl'], 'CCT Europe 2026 Series #12', 1792850400000,
     'saint-sinners-vs-6yubojlbl-cct-europe-2026-series-12-1081153', False),
    ('1079660', ['INOX Division', 'BRUTE'], 'CCT Europe 2026 Series #11', 1792850400000,
     'inox-division-vs-brute-cct-europe-2026-series-11-1079660', False),
    ('1079195', ['Nuclear TigeRES', 'FORZE Reload'], 'NODWIN Clutch Series #13', 1792850400000,
     'nuclear-tigeres-vs-forze-reload-nodwin-clutch-series-13-1079195', True),
    ('1081154', ['BakS', 'ILLYRIANS'], 'CCT Europe 2026 Series #12', 1792861200000,
     'baks-vs-illyrians-cct-europe-2026-series-12-1081154', False),
    ('1079661', ['Nuclear TigeRES', 'ex-Zero Tenacity'], 'CCT Europe 2026 Series #11', 1792861200000,
     'nuclear-tigeres-vs-ex-zero-tenacity-cct-europe-2026-series-11-1079661', False),
    ('1082996', ['Acend', 'UNiTY'], 'NODWIN Clutch Series #13', 1792918800000,
     'acend-vs-unity-nodwin-clutch-series-13-1082996', True),
    ('1081156', ['Spirit Academy', 'LFO 10'], 'CCT Europe 2026 Series #12', 1792929600000,
     'spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156', False),
    ('1079198', ['Metizport', 'BakS'], 'NODWIN Clutch Series #13', 1792929600000,
     'metizport-vs-baks-nodwin-clutch-series-13-1079198', True),
    ('1079199', ['Infinite', 'BRUTE'], 'NODWIN Clutch Series #13', 1792940400000,
     'infinite-vs-brute-nodwin-clutch-series-13-1079199', True),
    ('1081158', ['FORZE Reload', 'ex-RUSTEC'], 'CCT Europe 2026 Series #12', 1792951200000,
     'forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158', False),
    ('1079200', ['Color', 'ex-Zero Tenacity'], 'NODWIN Clutch Series #13', 1792951200000,
     'color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200', True),
    ('1082858', ['Ground Zero', 'Off Chops'], 'DFRAG Invitational 2026', 1792983600000,
     'ground-zero-vs-off-chops-dfrag-invitational-2026-1082858', True),
    ('1082859', ['NEXVOID', 'Alter Ego'], 'DFRAG Invitational 2026', 1792983600000,
     'nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859', True),
    ('1082860', ['FlyQuest', 'Staqued'], 'DFRAG Invitational 2026', 1793070000000,
     'flyquest-vs-staqued-dfrag-invitational-2026-1082860', True),
    ('1082861', ['Rooster', 'Abyssal'], 'DFRAG Invitational 2026', 1793070000000,
     'rooster-vs-abyssal-dfrag-invitational-2026-1082861', True),
    ('1082897', ['B8', 'K27'], 'Tesla Cup 2026', 1793088000000,
     'b8-vs-k27-tesla-cup-2026-1082897', True),
    ('1082898', ['Alliance', 'FaZe'], 'Tesla Cup 2026', 1793098800000,
     'alliance-vs-faze-tesla-cup-2026-1082898', True),
    ('1082900', ['Luminosity', 'HOTU'], 'Tesla Cup 2026', 1793120400000,
     'luminosity-vs-hotu-tesla-cup-2026-1082900', True),
    ('1082901', ['Envy', 'GamerLegion'], 'Tesla Cup 2026', 1793131200000,
     'envy-vs-gamerlegion-tesla-cup-2026-1082901', True),
    ('1082792', ['HOTU', 'The Huns'], 'Moscow Cyber Games 2026', 1793437200000,
     'hotu-vs-the-huns-moscow-cyber-games-2026-1082792', True),
    ('1082793', ['5star', '1WIN'], 'Moscow Cyber Games 2026', 1793451600000,
     '5star-vs-1win-moscow-cyber-games-2026-1082793', True),
]

# Six future API rows in the same response were NOT visible in the fetched
# lobby HTML.  They are published as an inventory irregularity, not discarded.
API_ONLY_FIXTURES = [
    ('1083120', ['Isurus', 'RED Canids Academy'], 'CCT South America 2026 Series #7', 1792846800000),
    ('1083121', ['Projeto do KinGui', 'MEIA NOITE'], 'CCT South America 2026 Series #7', 1792857600000),
    ('1082695', ['Galorys', 'paiN'], 'Circuit X Curitiba #4', 1792864800000),
    ('1083122', ['LOS NINOS', 'BORRACHEIROS'], 'CCT South America 2026 Series #7', 1792868400000),
    ('1083140', ['BESTIA', 'Imperial'], 'Circuit X Curitiba #4', 1792875600000),
    ('1083123', ['Grêmio', 'Yawara'], 'CCT South America 2026 Series #7', 1792879200000),
]

# Dated stale published snapshot rows.  These are NOT current picks; the page
# itself warns that the inventory check is older than eight hours.
PUBLISHED = {
    '1079193': ('Market-implied estimate', 'FOKUS 76.5% / ex-6666 23.5%'),
    '1079195': ('Market-implied estimate', 'Nuclear TigeRES 62.5% / FORZE Reload 37.5%'),
    '1082996': ('Valve-rating research estimate', 'Acend 54.2% / UNiTY 45.8%'),
    '1079198': ('Valve-rating research estimate', 'Metizport 79.9% / BakS 20.1%'),
    '1079199': ('Market-implied estimate', 'BRUTE 52.0% / Infinite 48.0%'),
    '1079200': ('Valve-rating research estimate', 'Color 73.6% / ex-Zero Tenacity 26.4%'),
    '1082858': ('Own network estimate (bo3.gg results graph)', 'Off Chops 55.1% / Ground Zero 44.9%'),
    '1082859': ('Bookmaker line', 'NEXVOID 57.6% / Alter Ego 42.4%'),
    '1082860': ('Bookmaker line', 'FlyQuest 92.3% / Staqued 7.7%'),
    '1082861': ('Valve-rating research estimate', 'Abyssal 52.2% / Rooster 47.8%'),
    '1082897': ('Market-implied estimate', 'B8 62.0% / K27 38.0%'),
    '1082898': ('Market-implied estimate', 'FaZe 65.0% / Alliance 35.0%'),
    '1082900': ('Market-implied estimate', 'Luminosity 52.5% / HOTU 47.5%'),
    '1082901': ('Market-implied estimate', 'GamerLegion 53.5% / Envy 46.5%'),
    '1082792': ('Research model estimate (Valve official ratings)', 'HOTU 94.1% / The Huns 5.9%'),
    '1082793': ('Valve-rating research estimate', '1WIN 82.2% / 5star 17.8%'),
}

# First-hand research order: HLTV first, then Polymarket / EGamersWorld.
# ``usable_line`` is a dated research classification only; the automated ladder
# still has to replay any price before it becomes a published pick.
RESEARCH = {
    '1079658': {
        'usable_line': True, 'hltv_match_id': '2399335',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399335/acend-vs-forze-reload-cct-2026-europe-series-11',
             'Quarter-final, Best of 3 confirmed at 04:00 on 24 Oct. HLTV fan poll 61.5%/38.5% was seen and excluded.'),
            ('Polymarket CCT Europe board', 'https://polymarket.com/esports/cs2/cct-europe/cs2-ace1-forzer-2026-10-24',
             'Acend 37¢ / FORZE Reload 67¢, $136.37 volume; two-sided active series moneyline.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/_rW8GEyWK/acend-vs-forze-reload-FZO8bqMyg',
             'Match page prints Acend 2.85 / FORZE Reload 1.34; index prints 2.8 / 1.35. Aggregated reference, not a first-party quote.'),
        ],
        'irregularity': 'Polymarket rule text says “initially scheduled … 10:00 AM ET” while its board/countdown and the Hotspawn API both point to 04:00 AM ET / 08:00Z; do not alias on the rule-text time.',
    },
    '1081152': {
        'usable_line': False, 'hltv_match_id': '2399502',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399502/havu-vs-azuolas-cct-2026-europe-series-12',
             'Swiss round 3 elimination, Best of 3 confirmed. HLTV fan poll 91.7%/8.3% excluded; Betting block carries only a Stake US promo row.'),
            ('Polymarket CCT Europe board', 'https://polymarket.com/esports/cs2/cct-europe',
             'No HAVU–Azuolas event was present on the CCT Europe board read at 06:31Z; absence of a reachable market is not proof that none exists.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/havu-vs-azuolas-Dm2JAvY3OO',
             'Both sides print the identical 1.8 / 1.8 placeholder; rejected by the reviewed reference gate.'),
        ],
        'irregularity': 'No compliant two-sided prematch price. Hotspawn 100%/0% picked is excluded by policy.',
    },
    '1079659': {
        'usable_line': True, 'hltv_match_id': '2399336',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399336/spirit-academy-vs-lavked-cct-2026-europe-series-11',
             'Quarter-final, Best of 3 confirmed on the event Matches page.'),
            ('Polymarket CCT Europe board', 'https://polymarket.com/esports/cs2/cct-europe/cs2-tsa-lavked-2026-10-24',
             'Spirit Academy 66¢ / Lavked 35¢, $60.60 volume; two-sided active series moneyline.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/_rW8GEyWK/spirit-academy-vs-lavked-mNEJAmoc0',
             'Match page prints Spirit Academy 1.5 / Lavked 2.49; index prints 1.49 / 2.47.'),
        ],
        'irregularity': 'None beyond the stale published snapshot.',
    },
    '1081153': {
        'usable_line': False, 'hltv_match_id': '2399503',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399503/6yubojlbl-vs-saint-sinners-cct-2026-europe-series-12',
             'Best of 3 confirmed on the HLTV Series 12 Matches page (provider order 6yuBoJlbl vs Saint Sinners).'),
            ('Polymarket event', 'https://polymarket.com/esports/cs2/cct-europe/cs2-6yuboj-ssins-2026-10-24',
             '6yuBoJlbl 85¢ / Saint Sinners 78¢ on $0.00 volume; the two displayed series prices sum to 163¢ and both map-winner cells are 96–97¢. Treated as a zero-volume placeholder, not a price.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/6yubojlbl-vs-saint-sinners-cCSiulSZ3S',
             'Both sides print 1.8 / 1.8; rejected as identical placeholder odds.'),
        ],
        'irregularity': 'Zero-volume crossed book plus identical EGW placeholder. No compliant price; do not use Hotspawn 82%/18% picked.',
    },
    '1079660': {
        'usable_line': True, 'hltv_match_id': '2399337',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399337/inox-division-vs-brute-cct-2026-europe-series-11',
             'Quarter-final, Best of 3 confirmed on the event Matches page.'),
            ('Polymarket CCT Europe board', 'https://polymarket.com/esports/cs2/cct-europe/cs2-inox-brute-2026-10-24',
             'INOX Division 55¢ / Brute 46¢, $247.26 volume; two-sided active series moneyline.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/_rW8GEyWK/inox-division-vs-brute-nZfqxPvnH',
             'Match page prints INOX Division 1.72 / Brute 1.92; index prints 1.75 / 1.96.'),
        ],
        'irregularity': 'Provider capitalisation “Brute” vs Hotspawn “BRUTE” is a display difference, not an alias decision; exact normalized names still join.',
    },
    '1081154': {
        'usable_line': False, 'hltv_match_id': '2399504',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399504/baks-vs-illyrians-cct-2026-europe-series-12',
             'Best of 3 confirmed on the HLTV Series 12 Matches page.'),
            ('Polymarket event', 'https://polymarket.com/esports/cs2/cct-europe/cs2-baks-ill4-2026-10-24',
             'BakS eSports 74¢ / ILLYRIANS 62¢ on $0.00 volume; map-winner cells 96–97¢. Rejected as a zero-volume placeholder.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/baks-esports-vs-illyrians-IG9Tsqw9TJ',
             'Both sides print 1.8 / 1.8; rejected as identical placeholder odds.'),
        ],
        'irregularity': 'Zero-volume crossed book plus identical EGW placeholder. Hotspawn 100%/0% picked excluded.',
    },
    '1079661': {
        'usable_line': True, 'hltv_match_id': '2399338',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399338/nuclear-tigeres-vs-ex-zero-tenacity-cct-2026-europe-series-11',
             'Quarter-final, Best of 3 confirmed on the event Matches page.'),
            ('Polymarket CCT Europe board', 'https://polymarket.com/esports/cs2/cct-europe/cs2-ntr-zerote-2026-10-24',
             'Nuclear TigeRES 62¢ / ex-Zero Tenacity 43¢ on $0.00 volume; recorded but not used as a primary price.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/_rW8GEyWK/nuclear-tigeres-vs-ex-zero-tenacity-rgEVBIE-Y',
             'Match page prints Nuclear TigeRES 1.43 / ex-Zero Tenacity 2.47; index prints 1.49 / 2.47. A two-sided aggregated reference exists.'),
        ],
        'irregularity': 'Polymarket book is zero-volume and wide; EGW aggregated line is a lead for the automated ladder, not a hand-written probability.',
    },
    '1081156': {
        'usable_line': False, 'hltv_match_id': '2399506',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12',
             'Best of 3 and the Hotspawn name LFO 10 confirmed on the HLTV Series 12 Matches page.'),
            ('Polymarket event', 'https://polymarket.com/esports/cs2/cct-europe/cs2-tsa-skr2-2026-10-25',
             'Same date/time slot is named “Spirit Academy vs Sökerorg”, 93¢/93¢ on $0.00 volume. No alias is created between LFO 10 and Sökerorg.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/spirit-academy-vs-zgh7PZE301',
             'Provider title is “Spirit Academy VS ” with the second team blank; both sides print 1.8 / 1.8. Rejected.'),
        ],
        'irregularity': 'Genuine name conflict (Hotspawn/HLTV LFO 10 vs Polymarket Sökerorg) plus zero-volume identical placeholder. Needs review; no silent alias.',
    },
    '1081158': {
        'usable_line': False, 'hltv_match_id': '2399508',
        'stages': [
            ('HLTV first', 'https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12',
             'Best of 3 confirmed on the HLTV Series 12 Matches page.'),
            ('Polymarket event', 'https://polymarket.com/esports/cs2/cct-europe/cs2-forzer-rustec-2026-10-25',
             'FORZE Reload 68¢ / ex-RUSTEC 94¢ on $0.00 volume; the displayed series prices sum to 162¢. Rejected as a zero-volume placeholder.'),
            ('EGamersWorld published odds', 'https://egamersworld.com/counterstrike/match/HiXMAaC8L/forze-reload-vs-ex-rustec-_GZF4CT4kR',
             'Both sides print 1.8 / 1.8; rejected as identical placeholder odds.'),
        ],
        'irregularity': 'Zero-volume crossed book plus identical EGW placeholder. Hotspawn 100%/0% picked excluded.',
    },
}

HLTV_EVENTS = [
    'https://www.hltv.org/events/9442/matches',
    'https://www.hltv.org/events/9457/matches',
]
POLYMARKET_BOARD = 'https://polymarket.com/esports/cs2/cct-europe'
EGW_INDEX = 'https://egamersworld.com/counterstrike/matches'


def iso_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).isoformat().replace('+00:00', 'Z')


def permalink(slug: str) -> str:
    return f'https://www.hotspawn.com/matches/{slug}'


def fixture_row(row, *, in_lobby: bool) -> dict:
    if in_lobby:
        fixture_id, teams, competition, start_ms, slug, in_published = row
        hotspawn_url = permalink(slug)
    else:
        fixture_id, teams, competition, start_ms = row
        in_published = False
        hotspawn_url = f'{CS2_LOBBY_URL}#fixture-{fixture_id}'
    published = PUBLISHED.get(fixture_id)
    research = RESEARCH.get(fixture_id) or {}
    hltv_url = next((url for stage, url, _ in research.get('stages', [])
                     if stage.startswith('HLTV') and 'hltv.org/matches/' in url), None)
    return {
        'id': fixture_id,
        'teams': list(teams),
        'competition': competition,
        'starts_at': iso_ms(start_ms),
        'locks_at': iso_ms(start_ms - 360_000),
        'scheduled_start_time_ms': start_ms,
        'in_lobby_rendered': in_lobby,
        'in_published_snapshot': in_published,
        'published_method': published[0] if published else None,
        'published_pick': published[1] if published else None,
        'published_snapshot_generated_at': SNAPSHOT_GENERATED_AT if published else None,
        'hotspawn_url': hotspawn_url,
        'source_api': API_URL,
        'hltv_url': hltv_url,
        'research': [
            {'stage': stage, 'url': url, 'finding': finding}
            for stage, url, finding in research.get('stages', [])
        ],
        'research_usable_external_line': research.get('usable_line'),
        'irregularity': research.get('irregularity'),
        'note': ('Stale published snapshot; its own page warns not to treat it as a current pick.'
                 if in_published else
                 ('Missing from the stale published snapshot.' if in_lobby else
                  'Future Hotspawn API row not rendered in the fetched lobby HTML; flagged for review.')),
        'policy': 'Hotspawn % picked and HLTV fan votes are never probabilities; no probability or pick is written by this dossier.',
    }


def build_reconciliation() -> dict:
    lobby = [fixture_row(r, in_lobby=True) for r in LOBBY_FIXTURES]
    api_only = [fixture_row(r, in_lobby=False) for r in API_ONLY_FIXTURES]
    missing_lobby = [r['id'] for r in lobby if not r['in_published_snapshot']]
    return {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': OBSERVED_AT,
        'environment': 'agent-authoring-path (first-hand page fetcher; the dispatch-only workflow re-checks the live sources)',
        'role': 'Dated read-only inventory and source research. No value here is a probability or a pick.',
        'sources': {
            'hotspawn_lobby': {'url': LOBBY_URL, 'observed_at': '2026-10-24T06:24:00Z',
                               'finding': 'Rendered 25 future CS2 cards in Closing Soon + Upcoming; crowd % picked present and excluded.'},
            'hotspawn_fixture_api': {'url': API_URL, 'observed_at': '2026-10-24T06:24:00Z',
                                     'finding': 'Official scheduled array; exact epoch times transcribed for all 25 lobby cards plus 6 additional future rows not rendered in the fetched lobby.'},
            'published_snapshot': {'url': PUBLISHED_DATA_URL, 'generated_at': SNAPSHOT_GENERATED_AT,
                                   'counts': {'inventory': 82, 'upcoming': 19, 'picks': 17, 'unresolved': 2},
                                   'warning': 'Site labels this snapshot stale and says not to treat the rows as current picks.'},
            'published_picks_page': PUBLISHED_PICKS_URL,
            'published_complete_picks': PUBLISHED_ORIGINATION_URL,
            'hltv_events': HLTV_EVENTS,
            'polymarket_board': {'url': POLYMARKET_BOARD, 'observed_at': '2026-10-24T06:31:00Z'},
            'egamersworld_index': {'url': EGW_INDEX, 'observed_at': '2026-10-24T06:33:00Z'},
            'egamersworld_recheck': {'url': 'https://egamersworld.com/counterstrike/match/_rW8GEyWK/acend-vs-forze-reload-FZO8bqMyg',
                                     'observed_at': '2026-10-24T06:52:00Z',
                                     'finding': 'Series 11 quarterfinal page still prints non-identical 2.85/1.34; NODWIN model rows print identical 1.8/1.8 placeholders.'},
        },
        'counts': {
            'lobby_future_cards': len(lobby),
            'lobby_cards_in_published_snapshot': len(lobby) - len(missing_lobby),
            'lobby_cards_missing_from_published': len(missing_lobby),
            'api_future_rows_not_rendered_in_lobby': len(api_only),
            'total_api_future_rows': len(lobby) + len(api_only),
            'rows_with_first_hand_hltv_identity': sum(bool(r['hltv_url']) for r in lobby + api_only),
            'researched_missing_cards_with_usable_external_line': sum(
                bool(RESEARCH.get(i, {}).get('usable_line')) for i in missing_lobby),
            'researched_missing_cards_without_usable_line': sum(
                not RESEARCH.get(i, {}).get('usable_line') for i in missing_lobby),
        },
        'missing_lobby_ids': missing_lobby,
        'api_only_ids': [r['id'] for r in api_only],
        'fixtures': sorted(lobby + api_only, key=lambda r: (r['starts_at'], r['id'])),
        'limitations': [
            'A stale published row is not a current pick; the site itself warns not to use it.',
            'The fetched lobby did not render six future API rows. They are retained and flagged rather than silently dropped.',
            'HLTV identity pages and fan polls are not two-sided prematch odds; fan votes are excluded.',
            'Polymarket zero-volume/crossed books and EGamersWorld identical 1.8/1.8 banners are placeholders and are not prices.',
            'An EGamersWorld aggregated line is a dated lead only until the automated reviewed ladder replays it.',
            'The Hotspawn fixture API reports lock_offset_sec=360 (six minutes) while the how-it-works page says five; submit with margin and do not silently alias them.',
        ],
    }


def build_live_coverage(recon: dict) -> dict:
    live = []
    for f in recon['fixtures']:
        live.append({
            'id': f['id'],
            'teams': f['teams'],
            'competition': f['competition'],
            'starts_at': f['starts_at'],
            'hotspawn_url': f['hotspawn_url'],
            'in_published_snapshot': f['in_published_snapshot'],
            'published_method': f['published_method'],
            'published_pick': (f['published_pick'] + ' (STALE snapshot, not a current pick)'
                               if f['published_pick'] else None),
            'in_lobby_rendered': f['in_lobby_rendered'],
            'note': f['note'],
        })
    missing = sum(not r['in_published_snapshot'] for r in live)
    return {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': OBSERVED_AT,
        'observer': 'agent-authoring-path (first-hand page fetcher)',
        'role': 'Dated inventory and identity research only. No value here is a probability or a pick.',
        'published_site': {
            'latest_json': PUBLISHED_DATA_URL,
            'generated_at': SNAPSHOT_GENERATED_AT,
            'site_warning': 'Snapshot needs attention: inventory check failed or successful snapshot older than eight hours.',
        },
        'hotspawn': {
            'lobby_url': LOBBY_URL,
            'cs2_lobby_url': CS2_LOBBY_URL,
            'api_url': API_URL,
            'future_fixtures_compared': len(live),
            'note': 'The API is sorted from historical scheduled rows; only starts after 2026-10-24T06:24Z are compared. Six future API rows were not rendered in the fetched lobby HTML and are flagged.',
        },
        'counts': {
            'live_future_fixtures': len(live),
            'in_published_snapshot': len(live) - missing,
            'missing_from_published': missing,
            'api_only_rows': recon['counts']['api_future_rows_not_rendered_in_lobby'],
        },
        'limitations': recon['limitations'],
        'live_fixtures': live,
    }


def build_line_research(recon: dict, *, environment: str = 'agent-authoring-path') -> dict:
    targets = [f for f in recon['fixtures'] if f['id'] in recon['missing_lobby_ids']]
    per_fixture = []
    for f in targets:
        per_fixture.append({
            'id': f['id'],
            'teams': f['teams'],
            'competition': f['competition'],
            'starts_at': f['starts_at'],
            'hotspawn_url': f['hotspawn_url'],
            'hltv_url': f['hltv_url'],
            'current_method': None,
            'current_label': 'Missing from the stale published snapshot',
            'money_line_lead': bool(f['research_usable_external_line']),
            'usable_external_line_observed': f['research_usable_external_line'],
            'smarkets_evidence': None,
            'sources': f['research'],
            'irregularity': f['irregularity'],
            'verdict': ('dated external line exists; collector must replay it' if f['research_usable_external_line']
                        else 'no compliant two-sided price at this observation; flagged unresolved'),
        })
    return {
        'schema_version': 1,
        'session': SESSION,
        'observed_at': OBSERVED_AT,
        'environment': environment,
        'policy': ('Read-only research in brief order: HLTV first for identity, then Polymarket/'
                   'EGamersWorld esportsbook and betting-line surfaces. Nothing here writes a '
                   'probability or a pick. Hotspawn % picked and HLTV fan votes are excluded.'),
        'target_source': {
            'source': 'first-hand Hotspawn lobby + official fixture API reconciliation',
            'url': API_URL,
            'targets': len(per_fixture),
            'active_future_rows': recon['counts']['total_api_future_rows'],
            'snapshot_generated_at': SNAPSHOT_GENERATED_AT,
        },
        'sources': [
            {'url': POLYMARKET_BOARD, 'kind': 'prediction-exchange board', 'observed_at': '2026-10-24T06:31:00Z'},
            {'url': EGW_INDEX, 'kind': 'esports odds aggregator index', 'observed_at': '2026-10-24T06:33:00Z'},
            *[{'url': u, 'kind': 'official HLTV event match list'} for u in HLTV_EVENTS],
        ],
        'per_fixture': per_fixture,
        'counts': {
            'fixtures_researched': len(per_fixture),
            'dated_external_line_leads': sum(bool(f['money_line_lead']) for f in per_fixture),
            'no_compliant_line': sum(not f['money_line_lead'] for f in per_fixture),
        },
    }


def render_reconciliation_md(recon: dict) -> str:
    c = recon['counts']
    lines = [
        f'# {SESSION} — dated Hotspawn CS2 reconciliation',
        '',
        f'Observed **{recon["observed_at"]}**. Read {c["lobby_future_cards"]} future cards on '
        f'[Hotspawn lobby]({LOBBY_URL}); the [official scheduled-fixture API]({API_URL}) returned '
        f'{c["total_api_future_rows"]} future rows, including {c["api_future_rows_not_rendered_in_lobby"]} '
        'not rendered in the fetched lobby HTML.',
        '',
        f'The [published snapshot]({PUBLISHED_DATA_URL}) was generated **{SNAPSHOT_GENERATED_AT}** and '
        f'carries only {c["lobby_cards_in_published_snapshot"]} of those lobby cards; '
        f'**{c["lobby_cards_missing_from_published"]} lobby cards and '
        f'{c["api_future_rows_not_rendered_in_lobby"]} API-only rows are missing**. Its own page warns '
        '“do not treat these as current picks.”',
        '',
        'Hotspawn “% picked” and HLTV fan votes were seen and excluded. No probability or pick is '
        'written by this dossier; a dated external line is a lead for the automated reviewed ladder.',
        '',
        '| Hotspawn ID | Teams | Competition | Start (UTC) | Rendered? | In stale snapshot? | First-hand research | Official / source links |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for f in recon['fixtures']:
        links = [f'[Hotspawn]({f["hotspawn_url"]})']
        if f['hltv_url']:
            links.append(f'[HLTV]({f["hltv_url"]})')
        links.extend(f'[{s["stage"]}]({s["url"]})' for s in f['research'])
        src = ' · '.join(links)
        if f['id'] in recon['missing_lobby_ids']:
            verdict = 'external line lead' if f['research_usable_external_line'] else 'no compliant line'
        elif not f['in_lobby_rendered']:
            verdict = 'API-only row; collector must research'
        else:
            verdict = 'published (stale)'
        lines.append(
            f'| {f["id"]} | {" vs ".join(f["teams"])} | {f["competition"]} | {f["starts_at"]} | '
            f'{"yes" if f["in_lobby_rendered"] else "API only"} | '
            f'{"yes" if f["in_published_snapshot"] else "NO"} | {verdict} | {src} |')
    lines += ['', '## Flagged irregularities', '']
    for f in recon['fixtures']:
        if f['irregularity']:
            lines.append(f'- **{f["id"]} {" vs ".join(f["teams"])}** — {f["irregularity"]} '
                         f'[Hotspawn]({f["hotspawn_url"]})'
                         + (f' · [HLTV]({f["hltv_url"]})' if f['hltv_url'] else ''))
    lines += ['', '- Six future API rows were not rendered in the fetched lobby HTML: '
              + ', '.join(recon['api_only_ids']) + '. They are retained here and in the live-coverage register.',
              '- Published snapshot rows are stale by the site’s own eight-hour rule.',
              '', '## Limitations', '']
    lines += [f'- {x}' for x in recon['limitations']]
    lines.append('')
    return '\n'.join(lines)


def render_live_coverage_md(record: dict) -> str:
    c = record['counts']
    lines = [
        f'# {SESSION} — live coverage comparison',
        '',
        f'Observed **{record["observed_at"]}**. Compared **{c["live_future_fixtures"]}** future '
        f'Hotspawn CS2 rows against [published data]({PUBLISHED_DATA_URL}) generated '
        f'**{SNAPSHOT_GENERATED_AT}**. **{c["missing_from_published"]}** are missing; '
        f'**{c["api_only_rows"]}** were API future rows not rendered in the fetched lobby.',
        '',
        'This is a dated observation, not a live claim. Hotspawn crowd percentages are never probabilities.',
        '',
        '| ID | Teams | Start (UTC) | In stale snapshot | Note | Source |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for r in record['live_fixtures']:
        lines.append(f'| {r["id"]} | {" vs ".join(r["teams"])} | {r["starts_at"]} | '
                     f'{"yes" if r["in_published_snapshot"] else "NO"} | {r["note"]} | '
                     f'[Hotspawn]({r["hotspawn_url"]}) |')
    return '\n'.join(lines) + '\n'


def render_line_research_md(record: dict) -> str:
    c = record['counts']
    lines = [
        f'# {SESSION} — HLTV-first no-line research',
        '',
        f'Observed **{record["observed_at"]}** in **{record["environment"]}**. '
        f'Researched **{c["fixtures_researched"]}** lobby cards missing from the stale published snapshot. '
        f'**{c["dated_external_line_leads"]}** had a dated two-sided external line lead; '
        f'**{c["no_compliant_line"]}** had no compliant price at this observation.',
        '',
        'Order: HLTV first (identity/format only), then Polymarket and EGamersWorld. '
        'HLTV fan votes and Hotspawn participation percentages are excluded. A dated lead is not '
        'a published pick until the automated ladder replays it from first-party evidence.',
        '',
    ]
    for f in record['per_fixture']:
        lines += [
            f'## {f["id"]} — {" vs ".join(f["teams"])}',
            '',
            f'- Competition: {f["competition"]}',
            f'- Start: {f["starts_at"]}',
            f'- Verdict: **{f["verdict"]}**',
            f'- Limitation: {f["irregularity"]}',
            '',
        ]
        for s in f['sources']:
            lines.append(f'- {s["stage"]}: {s["finding"]} [Source]({s["url"]})')
        lines.append('')
    return '\n'.join(lines)


def validate(recon: dict) -> list[str]:
    problems = []
    if recon['counts']['lobby_future_cards'] != 25:
        problems.append('expected 25 rendered lobby cards')
    if recon['counts']['api_future_rows_not_rendered_in_lobby'] != 6:
        problems.append('expected 6 API-only future rows')
    if len(recon['missing_lobby_ids']) != 9:
        problems.append('expected 9 lobby cards missing from the published snapshot')
    ids = [f['id'] for f in recon['fixtures']]
    if len(ids) != len(set(ids)):
        problems.append('duplicate fixture id')
    for f in recon['fixtures']:
        if not f['hotspawn_url'].startswith('https://'):
            problems.append(f'{f["id"]}: missing official Hotspawn source URL')
        if not f['starts_at'].endswith('Z'):
            problems.append(f'{f["id"]}: start is not explicit UTC')
        if 'probability' in f:
            problems.append(f'{f["id"]}: dossier must not contain a probability')
    for fid in recon['missing_lobby_ids']:
        if fid not in RESEARCH:
            problems.append(f'{fid}: missing first-hand research trail')
        elif not RESEARCH[fid]['stages'][0][0].startswith('HLTV'):
            problems.append(f'{fid}: research order did not start with HLTV')
    return problems


def write_dossier(out_dir: Path = OUT_DIR, *, environment: str = 'agent-authoring-path') -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    recon = build_reconciliation()
    problems = validate(recon)
    if problems:
        raise ValueError('; '.join(problems))
    live = build_live_coverage(recon)
    research = build_line_research(recon, environment=environment)
    files = {
        'reconciliation-2026-10-24.json': recon,
        'live-coverage.json': live,
        'line-source-research.json': research,
    }
    for name, payload in files.items():
        (out_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out_dir / 'reconciliation-2026-10-24.md').write_text(render_reconciliation_md(recon), encoding='utf-8')
    (out_dir / 'live-coverage.md').write_text(render_live_coverage_md(live), encoding='utf-8')
    (out_dir / 'line-source-research.md').write_text(render_line_research_md(research), encoding='utf-8')
    return recon


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true', help='Regenerate the dated dossier files')
    ap.add_argument('--out', type=Path, default=OUT_DIR)
    ap.add_argument('--environment', default='agent-authoring-path',
                    help='Only the dispatch workflow should pass github-actions-runner')
    args = ap.parse_args(argv)
    if args.write:
        recon = write_dossier(args.out, environment=args.environment)
    else:
        recon = build_reconciliation()
    problems = validate(recon)
    print(json.dumps({'counts': recon['counts'], 'problems': problems,
                      'observed_at': recon['observed_at']}, indent=2))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
