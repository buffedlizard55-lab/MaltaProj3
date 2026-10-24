"""Originate an independently researched line and pick for every Hotspawn CS2 fixture.

The featured pipeline (scripts/collect.py) resolves picks with strict exact-name
joins. Fixtures it cannot resolve still deserve picks: this module researches
them the way the project brief asks — HLTV identity research first, then
esportsbook / betting-line sources (Polymarket series-winner markets, Thunderpick
match-winner prices), then an explicitly labeled Valve-rating research model.

Identity joins may use only the reviewed alias registry
(data/origination/aliases.json), where every alias carries official source
links. Nothing is fuzzy-matched and nothing is invented: values that cannot be
confirmed stay blank and are published as unresolved with the full research
trail.

Usage:
    python -m scripts.originate            # replay saved evidence (offline)
    python -m scripts.originate --live     # refetch first-party sources first
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from urllib.parse import quote, urlencode

import requests

from scripts.domain import iso, name_key, no_vig, normalize_pair, timestamp, finite, array, polymarket_candidate
from scripts.github_auth import auth_headers
from scripts import egw_live
from scripts import form_model
from scripts import hltv_ranking
from scripts import network_model
from scripts import pinnacle_lines
from scripts import smarkets_lines
from scripts import reference_odds

UTC = timezone.utc
VALVE_RD = 75  # Fixed-RD assumption in Valve's published model/fit.js.
START_TOLERANCE_SEC = 60  # No relaxed matching for delayed or rescheduled fixtures.
TIME_DISAGREEMENT_SEC = 60  # Beyond this, the disagreement is published as a flag.
# Price freshness is domain.is_fresh (MAX_PRICE_AGE_HOURS = 8). A former unused 12-hour
# constant here contradicted it and was removed (session c07e1b40 review).
#
# Two tiers, deliberately different:
#   * The featured exact-name collector (scripts/domain.py MAX_SPREAD) keeps the
#     strict 0.12 ceiling. A featured pick is never widened by this fallback.
#   * The origination ladder runs only when the featured method produced no pick.
#     It accepts a two-sided book up to 0.15 and marks anything wider than 0.12
#     as `thin`, so a 13-cent book (Infinite vs Insiders on 2026-10-18) can be
#     used with an explicit limitation instead of staying blank. Books wider
#     than 0.15 are still rejected and never become a pick.
THIN_SPREAD = 0.12
MAX_ACCEPTED_SPREAD = 0.15
# bo3.gg relays a named bookmaker's own two-sided prematch decimal prices in the
# ``bet_updates`` block of the fixtures its pages list. That is a *second-hand*
# copy of a first-party price, so session 15fc6bca's rung treats it as its own
# evidence class: it is used only when no first-party market or esportsbook quote
# resolved the fixture, it is never folded into a first-party consensus (which
# would double-count the same bookmaker), and every published row names the
# bookmaker, the bo3.gg page the numbers were read from and the bookmaker match
# page bo3.gg links to. The join is exactly as strict as every other money rung:
# both team names must resolve exactly or through the reviewed alias registry, and
# the start time must agree inside the project-wide 60-second window (a delayed or
# rescheduled fixture must never inherit a price from another slot). Every observed
# bo3.gg fixture that did not bind is recorded with its own reason, including the
# start-time delta, so a skipped price stays visible instead of silently dropped.
RELAY_START_TOLERANCE_SEC = START_TOLERANCE_SEC
RELAY_FAMILY = 'relay'

FIXTURES_API = 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?' + urlencode({'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1})
POLY_INDEX = 'https://polymarket.com/esports/cs2'
POLY_EVENTS = 'https://gamma-api.polymarket.com/events/'
CLOB_BOOK = 'https://clob.polymarket.com/book?token_id='
THUNDERPICK_API = 'https://thunderpick.io/api/matches'
THUNDERPICK_PAGE = 'https://thunderpick.io/esports/counter-strike'
VALVE_REPO = 'https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings'
BO3_API = 'https://api.bo3.gg/api/v1'
BO3_HEADERS = {'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/', 'Accept': 'application/json'}
HLTV_EVENT = 'https://www.hltv.org/events/9332/elisa-breakout-series-2'
# Independent money sources added by session c07e1b40 for fixtures the featured
# pipeline cannot price. Both are public, unauthenticated first-party feeds:
# Kalshi is a CFTC-regulated exchange with an officially documented market-data
# API; Bovada's coupon feed is the sportsbook's own public client contract.
KALSHI_EVENTS = 'https://api.elections.kalshi.com/trade-api/v2/events'
REFERENCE_INDEX = 'https://egamersworld.com/counterstrike/matches'
KALSHI_DOCS = 'https://docs.kalshi.com/api-reference/market/get-markets'
KALSHI_PAGE = 'https://kalshi.com/markets/kxcs2game/counterstrike-2-game/'
KALSHI_SERIES = 'KXCS2GAME'
BOVADA_API = ('https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/counter-strike-2?'
              + urlencode({'marketFilterId': 'def', 'preMatchOnly': 'true', 'lang': 'en'}))
BOVADA_SITE = 'https://www.bovada.lv/sports'
# Pinnacle public guest market board (first-party esportsbook prices). Added by
# session c03ef201 alongside the HLTV world-ranking research model: both rungs
# exist so low-tier fixtures the exchange books never list still get researched
# picks before anything is published as unresolved.
PINNACLE_PAGE = pinnacle_lines.SOURCE_URL
PINNACLE_API = 'https://guest.api.arcadia.pinnacle.com/0.1'
HLTV_RANKING_URL = hltv_ranking.RANKING_URL
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


# ---------------------------------------------------------------------------
# Reviewed alias registry
# ---------------------------------------------------------------------------

def load_registry(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data.get('aliases'), list) or not data['aliases']:
        raise ValueError('Alias registry is empty or unrecognized')
    for entry in data['aliases']:
        if not entry.get('alias') or not entry.get('canonical') or not entry.get('evidence'):
            raise ValueError('Every alias needs alias, canonical and evidence links')
        scope = entry.get('applies_to')
        if not isinstance(scope, list) or not scope or not all(isinstance(s, str) and s.strip() for s in scope):
            raise ValueError(f"Alias {entry.get('alias')!r} must declare the exact competitions it applies to")
        for ev in entry['evidence']:
            if not str(ev.get('url', '')).startswith('https://'):
                raise ValueError('Alias evidence must carry an https source link')
    return data


def scoped_aliases(registry: dict, competition) -> list:
    """Only aliases that explicitly declare this fixture's competition."""
    key = name_key(competition or '')
    return [e for e in registry['aliases'] if key in {name_key(s) for s in e.get('applies_to', [])}]


def resolve_name(name: str, registry: dict, competition=None) -> tuple[str, list]:
    """Map a provider display name to its canonical Hotspawn-side name.

    Returns (canonical_name, alias_records). Exact names pass through. An alias
    applies only when the provider name is not in that alias's must_not_match
    list and, whenever the fixture competition is known, only inside the
    competitions that alias explicitly declares. No fuzzy matching.
    """
    key = name_key(name)
    used = []
    pool = registry['aliases'] if competition is None else scoped_aliases(registry, competition)
    for entry in pool:
        excluded = {name_key(x) for x in entry.get('must_not_match', [])}
        if key in excluded:
            continue
        if key == name_key(entry['alias']):
            used.append({'alias': entry['alias'], 'canonical': entry['canonical'], 'kind': entry['kind'],
                         'applies_to': list(entry.get('applies_to', [])), 'evidence': entry['evidence']})
            return name_key(entry['canonical']), used
    return key, used


def pair_join(source_names: list, source_start, match: dict, registry: dict) -> tuple[list | None, list, str]:
    """Try to join a provider two-team row onto a Hotspawn fixture.

    Returns (aligned_values_placeholder None, alias_records, status) where
    status is one of 'matched', 'names', 'time'.
    """
    if len(source_names) != 2 or not all(isinstance(n, str) and n.strip() for n in source_names):
        return None, [], 'names'
    canon, used = [], []
    for n in source_names:
        c, u = resolve_name(n, registry, match.get('competition'))
        canon.append(c)
        used.extend(u)
    wanted = [name_key(t['name']) for t in match['teams'] if t.get('name')]
    if len(wanted) != 2 or set(canon) != set(wanted) or len(set(canon)) != 2:
        return None, [], 'names'
    dt, md = timestamp(source_start), timestamp(match.get('starts_at'))
    if dt is None or md is None:
        return None, used, 'time'
    delta = abs((dt - md).total_seconds())
    if delta > START_TOLERANCE_SEC:
        return None, used, 'time'
    return [canon, [name_key(n) for n in source_names]], used, 'matched'


def align_by_name(values: list, source_names: list, match: dict, registry: dict) -> list:
    mapping = {}
    for value, name in zip(values, source_names):
        canon, _ = resolve_name(name, registry, match.get('competition'))
        mapping[canon] = value
    out = []
    for team in match['teams']:
        key = name_key(team['name'])
        if key not in mapping:
            raise ValueError('Outcome mapping incomplete')
        out.append(mapping[key])
    return out


# ---------------------------------------------------------------------------
# First-party collection (live mode)
# ---------------------------------------------------------------------------

class Collector:
    def __init__(self, evidence_dir: Path):
        self.dir = evidence_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'HotspawnCS2Origination/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)', 'Accept': 'application/json'})
        self.requests = []
        self.last = 0.0

    def save(self, label: str, data) -> str:
        path = self.dir / f'{label}.json'
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        return path.name

    def fetch_html(self, url: str, label: str):
        delay = 0.25 - (time.monotonic() - self.last)
        if delay > 0:
            time.sleep(delay)
        self.last = time.monotonic()
        entry = {'id': label, 'url': url, 'method': 'GET', 'observed_at': iso(datetime.now(UTC)), 'status': 'error'}
        self.requests.append(entry)
        try:
            response = self.session.get(url, headers=auth_headers(url), timeout=(15, 45))
            entry.update(http_status=response.status_code,
                         response_sha256=hashlib.sha256(response.content).hexdigest())
            response.raise_for_status()
            entry['status'] = 'ok'
            path = self.dir / f'{label}.json'
            path.write_text(json.dumps({'url': url, 'observed_at': entry['observed_at'], 'html': response.text}))
            entry['evidence'] = path.name
            return response.text, entry
        except requests.RequestException as exc:
            entry['error'] = str(exc)[:300]
            raise RuntimeError(f'{label}: {entry["error"]}') from exc

    def get_json(self, url: str, label: str, *, method='GET', payload=None, save=True, headers=None):
        delay = 0.25 - (time.monotonic() - self.last)
        if delay > 0:
            time.sleep(delay)
        self.last = time.monotonic()
        entry = {'id': label, 'url': url, 'method': method, 'observed_at': iso(datetime.now(UTC)), 'status': 'error'}
        self.requests.append(entry)
        try:
            merged = dict(headers or {})
            merged.update(auth_headers(url))
            response = self.session.request(method, url, json=payload, headers=merged, timeout=(15, 45))
            entry.update(http_status=response.status_code,
                         response_sha256=hashlib.sha256(response.content).hexdigest())
            response.raise_for_status()
            data = response.json()
            entry['status'] = 'ok'
            if save:
                entry['evidence'] = self.save(label, data)
            return data, entry
        except (requests.RequestException, ValueError) as exc:
            entry['error'] = str(exc)[:300]
            raise RuntimeError(f'{label}: {entry["error"]}') from exc


def aliased_series_market(event: dict, fixture: dict, registry: dict, now: datetime):
    """Same unique full-series contract as featured, with scoped name aliases."""
    originals = event.get('markets', [])
    canonical = [dict(m, outcomes=[resolve_name(n, registry, fixture.get('competition'))[0]
                                  for n in array(m.get('outcomes'))]) for m in originals]
    candidate, reason = polymarket_candidate(dict(event, markets=canonical), fixture, now)
    if candidate is None:
        return None, reason
    return next(original for original, mapped in zip(originals, canonical) if mapped is candidate), ''


def supplement_polymarket_discovery(directory_games: list, repo_data: Path, now: datetime) -> tuple[list, dict]:
    """Reuse tagged identities that the featured collector already discovered.

    The visible directory is windowed. The featured collector already paginates
    the official CS2-tag API, but used to discard alias-only joins before the
    research collector looked at them. Reuse only identities that replay from
    their retained original page AND a fresh successful request. This supplies
    no price: each selected event and both books must still be fetched again.
    """
    from scripts.domain import is_fresh
    from scripts.sources import gamma_games

    games = list(directory_games)
    directory_keys = set()
    accepted, limitations, requests_used = 0, [], []
    index_path = repo_data / 'evidence/polymarket-index.json'
    snapshot_path = repo_data / 'latest.json'
    try:
        index = load_json(index_path) if index_path.exists() else []
        requests_ = load_json(snapshot_path).get('requests', []) if snapshot_path.exists() else []
        if not isinstance(index, list) or not isinstance(requests_, list):
            raise ValueError('Retained discovery index/request manifest is not an array')
    except (OSError, ValueError, TypeError) as exc:
        index, requests_ = [], []
        limitations.append('Retained tagged discovery could not be read: ' + str(exc))
    pages = {}
    for game in index:
        if not isinstance(game, dict) or not game.get('discovery_evidence'):
            continue  # Only tagged originals have a replayable identity contract here.
        origin = game['discovery_evidence']
        if not isinstance(origin, str) or not re.fullmatch(r'data/evidence/polymarket-discovery-\d+\.json', origin):
            limitations.append('Retained discovery identity has an unsafe original-page reference; ignored.')
            continue
        label = Path(origin).stem
        observations = [r for r in requests_ if isinstance(r, dict) and r.get('id') == label
                        and r.get('status') == 'ok' and r.get('evidence') == origin
                        and str(r.get('url', '')).startswith('https://gamma-api.polymarket.com/events?')
                        and is_fresh(r.get('observed_at'), now)]
        if len(observations) != 1:
            limitations.append(label + ': no unique fresh successful original request; identity ignored.')
            continue
        try:
            if origin not in pages:
                pages[origin] = gamma_games(load_json(repo_data / 'evidence' / Path(origin).name), origin)
            if game not in pages[origin]:
                raise ValueError('Index identity does not replay from the original tagged page')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            limitations.append(label + ': ' + str(exc) + '; identity ignored.')
            continue
        games.append(game)
        accepted += 1
        request = {k: observations[0].get(k) for k in ('url', 'observed_at', 'evidence')}
        if request not in requests_used:
            requests_used.append(request)
    unique = {}
    for position, game in enumerate(games):
        if not isinstance(game, dict) or not game.get('id'):
            continue
        names = [game.get('homeName'), game.get('awayName')]
        if not all(isinstance(n, str) and n.strip() for n in names):
            continue
        start = timestamp(game.get('startTime'))
        if start is None:
            continue
        key = (str(game['id']), tuple(sorted(name_key(n) for n in names)), iso(start))
        unique.setdefault(key, game)
        if position < len(directory_games):
            directory_keys.add(key)
    return list(unique.values()), {
        'source': 'Polymarket directory plus replayed retained CS2-tag discovery',
        'role': 'Identity discovery only; selected original event and both order books are re-fetched.',
        'supplemental_identities': len(set(unique) - directory_keys),
        'retained_identities_replayed': accepted, 'discovered_identities': len(unique),
        'directory_is_exhaustive': False, 'tagged_discovery_available': bool(requests_used),
        'prices_used': False, 'reused_requests': requests_used,
        'limitations': list(dict.fromkeys(limitations)),
    }


def collect_bo3_results(client, evidence_dir: Path, matches: list, registry: dict,
                        known: set | None = None) -> dict:
    """Bind fixtures on bo3.gg and save the series history the results model uses.

    The bridge is an exact start time (within 90 minutes) plus at least one
    matching team name; the other side is then the opponent of that same
    fixture. Nothing is inferred from a name alone and every saved sample keeps
    its own bo3.gg match URL.
    """
    rows, pages = [], 0
    while pages < 4:
        query = ('/matches?page[offset]=' + str(pages * 100) + '&page[limit]=100&sort=start_date'
                 '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
                 '&with=teams,tournament')
        body, _ = client.get_json(BO3_API + query, f'live-bo3-upcoming-{pages}', headers=BO3_HEADERS)
        chunk = body.get('results') or []
        rows.extend(chunk)
        pages += 1
        if len(chunk) < 100:
            break
    bindings, cache, observed = {}, {}, iso(datetime.now(UTC))
    for match in matches:
        if match.get('availability') == 'past':
            continue
        start = timestamp(match.get('starts_at'))
        if start is None:
            continue
        # Only fixtures with a team the official table cannot rate need this.
        wanted = []
        for team in match.get('teams') or []:
            if known is None:
                wanted.append(team)
                continue
            reverse = {}
            for entry in scoped_aliases(registry, match.get('competition')):
                reverse.setdefault(name_key(entry['canonical']), []).append(name_key(entry['alias']))
            candidates = {name_key(team.get('name') or '')} | set(reverse.get(name_key(team.get('name') or ''), []))
            if not candidates & known:
                wanted.append(team)
        if not wanted:
            continue
        alias_names = {}
        for entry in scoped_aliases(registry, match.get('competition')):
            alias_names.setdefault(form_model.key(entry['canonical']), set()).add(form_model.key(entry['alias']))
        names = set()
        for t in match.get('teams') or []:
            raw_key = form_model.key(t.get('name') or '')
            names.add(raw_key)
            names.update(alias_names.get(raw_key, ()))
        candidates = []
        for row in rows:
            other = timestamp(row.get('start_date'))
            if other is None or abs((other - start).total_seconds()) > 5400:
                continue
            sides = {form_model.key((row.get('team1') or {}).get('name') or ''),
                     form_model.key((row.get('team2') or {}).get('name') or '')}
            if sides & names:
                candidates.append(row)
        if len(candidates) != 1:
            continue
        fixture = candidates[0]
        record = {'bo3_id': fixture.get('id'),
                  'source_url': 'https://bo3.gg/matches/' + str(fixture.get('slug')),
                  'observed_at': observed, 'bridge': 'start_time_and_team_name',
                  # Exact bo3.gg team ids for both sides. Session 541cd43a's own
                  # network model needs a machine identity, not a display name:
                  # names are joined to ratings through the reviewed registry and
                  # an ambiguous name is never guessed.
                  'sides': [{'name': (fixture.get(side) or {}).get('name'),
                             'team_id': (fixture.get(side) or {}).get('id')}
                            for side in ('team1', 'team2')],
                  'results': {}}
        for side in ('team1', 'team2'):
            team = fixture.get(side) or {}
            team_id = team.get('id')
            if not team_id:
                continue
            canonical_side, _ = resolve_name(team.get('name') or '', registry, match.get('competition'))
            if known is not None and (name_key(team.get('name') or '') in known
                                      or name_key(canonical_side or '') in known):
                continue
            if team_id not in cache:
                query = ('/matches?page[offset]=0&page[limit]=40&sort=-start_date'
                         '&filter[matches.status][in]=finished&filter[matches.discipline_id][eq]=1'
                         f'&filter[matches.team_ids][overlap]={team_id}&with=teams')
                body, entry = client.get_json(BO3_API + query, f'live-bo3-results-{team_id}', headers=BO3_HEADERS)
                samples = []
                for game in body.get('results') or []:
                    involves = game.get('team1_id') == team_id
                    opponent = game.get('team2') if involves else game.get('team1')
                    samples.append({'date': str(game.get('start_date') or '')[:10],
                                    'opponent': (opponent or {}).get('name'),
                                    'won': game.get('winner_team_id') == team_id,
                                    'bo': game.get('bo_type'),
                                    'parsed': game.get('parsed_status'),
                                    'source_url': 'https://bo3.gg/matches/' + str(game.get('slug'))})
                cache[team_id] = {'team_id': team_id, 'name': team.get('name'),
                                  'source_url': entry.get('url'), 'observed_at': entry.get('observed_at'),
                                  'samples': samples}
                (evidence_dir / f'live-bo3-results-{team_id}.json').write_text(json.dumps(
                    cache[team_id], ensure_ascii=False, indent=2) + '\n')
            record['results'][form_model.key(team.get('name') or '')] = cache[team_id]['samples']
            if canonical_side:
                record['results'][form_model.key(canonical_side)] = cache[team_id]['samples']
        bindings[str(match['id'])] = record
    # Identity fallback for the own network model (session 541cd43a): bo3.gg does
    # not list every low-tier fixture, but it does list most teams. An exact
    # normalised team-name lookup that returns exactly one team is recorded as a
    # name bridge; anything ambiguous or missing is left unbindable, so the model
    # stays blank instead of pricing the wrong roster.
    for match in matches:
        if str(match['id']) in bindings or match.get('availability') == 'past':
            continue
        if match.get('analysis') is not None and match['analysis'].get('method') != 'model':
            continue
        sides, bridge_ok = [], True
        for team in match.get('teams') or []:
            name = team.get('name') or ''
            if not name:
                bridge_ok = False
                break
            query = ('/teams?page[offset]=0&page[limit]=10&filter[teams.name][eq]='
                     + quote(name, safe=''))
            try:
                body, _ = client.get_json(BO3_API + query, 'live-bo3-team-' + str(team.get('id')),
                                          headers=BO3_HEADERS, save=False)
            except RuntimeError as exc:
                bridge_ok = False
                break
            rows = [r for r in body.get('results') or []
                    if name_key(r.get('name') or '') == name_key(name)]
            if len(rows) != 1 or not rows[0].get('id'):
                bridge_ok = False
                break
            sides.append({'name': rows[0].get('name'), 'team_id': rows[0].get('id')})
        if bridge_ok and len(sides) == 2:
            bindings[str(match['id'])] = {
                'bo3_id': None, 'source_url': 'https://bo3.gg/teams/' + str(sides[0]['team_id']),
                'observed_at': observed, 'bridge': 'exact_team_name_lookup', 'sides': sides,
                'results': {}}
    form_model.save_bindings(evidence_dir, {'observed_at': observed, 'matches': bindings})
    return {'fixtures_bound': len(bindings), 'teams_saved': len(cache),
            'samples': sum(len(v['samples']) for v in cache.values())}


def relay_join(source_names: list, source_start, match: dict, registry: dict,
               tolerance: int = RELAY_START_TOLERANCE_SEC) -> tuple[list | None, list, str]:
    """Join a bo3.gg relay row onto a Hotspawn fixture.

    Identical to ``pair_join`` except for the published relay tolerance: both
    team names must resolve exactly or through the reviewed alias registry, and
    the start time must agree within ``RELAY_START_TOLERANCE_SEC``. Returns
    (canonical names, alias records, status).
    """
    if len(source_names) != 2 or not all(isinstance(n, str) and n.strip() for n in source_names):
        return None, [], 'names'
    canon, used = [], []
    for name in source_names:
        canonical, records = resolve_name(name, registry, match.get('competition'))
        canon.append(canonical)
        used.extend(records)
    wanted = [name_key(t['name']) for t in match['teams'] if t.get('name')]
    if len(wanted) != 2 or set(canon) != set(wanted) or len(set(canon)) != 2:
        return None, [], 'names'
    source_then, match_then = timestamp(source_start), timestamp(match.get('starts_at'))
    if source_then is None or match_then is None:
        return None, used, 'time'
    if abs((source_then - match_then).total_seconds()) > tolerance:
        return None, used, 'time'
    return canon, used, 'matched'


def collect_bo3_relay(client, evidence_dir: Path, matches: list, registry: dict) -> dict:
    """Save the two-sided bookmaker prices bo3.gg relays for these fixtures.

    bo3.gg publishes, on the match objects its own pages load, a ``bet_updates``
    block naming a bookmaker, that bookmaker's match page and both decimal
    coefficients with an ``active`` flag. The block is copied verbatim: nothing
    is averaged, de-vigged or defaulted here, and a fixture that cannot be bound
    by BOTH sides plus a start time inside the relay tolerance is recorded as a
    rejection instead of being priced.
    """
    rows, pages = [], 0
    while pages < 3:
        query = ('/matches?page[offset]=' + str(pages * 100) + '&page[limit]=100&sort=start_date'
                 '&filter[matches.status][in]=upcoming&filter[matches.discipline_id][eq]=1'
                 '&with=teams,tournament')
        try:
            body, _ = client.get_json(BO3_API + query, f'live-bo3-relay-upcoming-{pages}',
                                      headers=BO3_HEADERS, save=False)
        except RuntimeError:
            break
        chunk = body.get('results') or []
        rows.extend(chunk)
        pages += 1
        if len(chunk) < 100:
            break
    observed = iso(datetime.now(UTC))
    fixtures, rejections = [], []
    for match in matches:
        if match.get('availability') == 'past':
            continue
        start = timestamp(match.get('starts_at'))
        if start is None:
            continue
        bound, near = [], []
        for row in rows:
            names = [(row.get('team1') or {}).get('name'), (row.get('team2') or {}).get('name')]
            _, used, status = relay_join(names, row.get('start_date'), match, registry)
            if status == 'names':
                continue  # does not name this fixture's two sides at all
            other = timestamp(row.get('start_date'))
            near.append({'slug': row.get('slug'), 'start': row.get('start_date'), 'teams': names,
                         'status': status,
                         'start_delta_sec': (int(abs((other - start).total_seconds()))
                                             if other is not None else None)})
            if status == 'matched':
                bound.append((row, used))
        if len(bound) != 1:
            if near:
                rejections.append({'hotspawn_id': str(match['id']),
                                   'teams': [t.get('name') for t in match.get('teams') or []],
                                   'reason': ('ambiguous: several bo3.gg fixtures join this fixture'
                                              if len(bound) > 1 else
                                              'no single bo3.gg fixture matched both team names inside the '
                                              f'{RELAY_START_TOLERANCE_SEC}s start window'),
                                   'candidates': near[:5]})
            continue
        row, used = bound[0]
        relay_block = row.get('bet_updates')
        record = {'hotspawn_id': str(match['id']),
                  'bo3_id': row.get('id'),
                  'bo3_url': 'https://bo3.gg/matches/' + str(row.get('slug')),
                  'tournament': (row.get('tournament') or {}).get('name'),
                  'bo_type': row.get('bo_type'),
                  'start': row.get('start_date'),
                  'start_delta_sec': int(abs((timestamp(row.get('start_date')) - start).total_seconds())),
                  'observed_at': observed,
                  'provider': None, 'book_url': None, 'sides': [],
                  'aliases_used': [{'alias': a['alias'], 'canonical': a['canonical']} for a in used]}
        if not isinstance(relay_block, dict):
            rejections.append({'hotspawn_id': str(match['id']),
                               'teams': [t.get('name') for t in match.get('teams') or []],
                               'reason': 'bo3.gg lists the fixture without a bookmaker quote block',
                               'candidates': [{'slug': row.get('slug'), 'status': 'matched'}]})
            continue
        record['provider'] = relay_block.get('provider')
        record['book_url'] = relay_block.get('path')
        sides = {}
        for side, block in (('team1', relay_block.get('team_1') or {}),
                            ('team2', relay_block.get('team_2') or {})):
            sides[side] = {'team_id': block.get('team_id'), 'name': block.get('name'),
                           'coeff': block.get('coeff'), 'active': block.get('active')}
        # bo3.gg can print the bookmaker's sides in either order. Align them to
        # bo3.gg's own team1/team2 using the team id when it prints one, and only
        # then fall back to the name bo3.gg itself uses for the fixture side.
        team1_id, team2_id = (row.get('team1') or {}).get('id'), (row.get('team2') or {}).get('id')
        if sides['team1'].get('team_id') and sides['team2'].get('team_id'):
            if sides['team1']['team_id'] == team2_id and sides['team2']['team_id'] == team1_id:
                sides['team1'], sides['team2'] = sides['team2'], sides['team1']
            elif not (sides['team1']['team_id'] == team1_id and sides['team2']['team_id'] == team2_id):
                rejections.append({'hotspawn_id': str(match['id']),
                                   'teams': [t.get('name') for t in match.get('teams') or []],
                                   'reason': 'relayed quote team ids do not match the fixture sides',
                                   'candidates': [{'slug': row.get('slug'), 'status': 'matched'}]})
                continue
        record['sides'] = [sides['team1'], sides['team2']]
        fixtures.append(record)
    document = {'source': 'bo3.gg public match API (relayed bookmaker quote)',
                'api_url': BO3_API + '/matches', 'documentation': 'https://api.bo3.gg/api/v1',
                'observed_at': observed, 'rows_fetched': len(rows),
                'policy': ('Verbatim copy of the bookmaker quote bo3.gg relays. No probability, pick or alias '
                           'is decided here; the ladder validates the pair before it can become an estimate.'),
                'fixtures': fixtures, 'rejections': rejections}
    (evidence_dir / 'live-bo3-relay.json').write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
    return {'fixtures_bound': len(fixtures), 'rows_fetched': len(rows),
            'with_quote': sum(1 for f in fixtures if f.get('sides')),
            'rejections': len(rejections)}


def bo3_relay_rows(evidence_dir: Path) -> list:
    """Load the saved relay document as normalized quote rows (never re-priced)."""
    path = evidence_dir / 'live-bo3-relay.json'
    if not path.exists():
        return []
    try:
        document = load_json(path)
    except (ValueError, OSError):
        return []
    out = []
    for entry in document.get('fixtures') or []:
        sides = entry.get('sides') or []
        if len(sides) != 2 or any(not s.get('name') for s in sides):
            continue
        out.append({'family': RELAY_FAMILY, 'provider': entry.get('provider') or 'Unnamed bookmaker',
                    'names': [s.get('name') for s in sides],
                    'odds': [s.get('coeff') for s in sides],
                    'active': [s.get('active') for s in sides],
                    'start': entry.get('start'), 'start_delta_sec': entry.get('start_delta_sec'),
                    'observed_at': entry.get('observed_at'),
                    'source_url': entry.get('bo3_url'), 'book_url': entry.get('book_url'),
                    'event_id': entry.get('bo3_id'), 'fixture_id': entry.get('hotspawn_id'),
                    'evidence_file': 'data/origination/evidence/live-bo3-relay.json'})
    return out


def collect_bo3_graph(client, evidence_dir: Path, *, max_pages: int = 100,
                      max_age_days: int = network_model.WINDOW_DAYS) -> dict:
    """Fetch the finished-series graph the own network model fits on.

    Reads bo3.gg's public finished-match listing, newest first, 100 series per
    request, and stops at the model's 120-day window or the page cap. Every edge
    keeps its bo3.gg match URL, so each observation behind a published rating is
    linked. Raw listing responses are not duplicated into evidence: the fitted
    document (``live-bo3-graph.json``) is the replay record and lists every edge.
    """
    edges, pages, rows_seen, oldest = [], 0, 0, None
    missing_winner = 0
    samples = []
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    while pages < max_pages:
        query = ('/matches?page[offset]=' + str(pages * 100) + '&page[limit]=100&sort=-start_date'
                 '&filter[matches.status][in]=finished&filter[matches.discipline_id][eq]=1&with=teams')
        body, _ = client.get_json(BO3_API + query, f'live-bo3-graph-{pages}',
                                  headers=BO3_HEADERS, save=False)
        rows = body.get('results') or []
        rows_seen += len(rows)
        for row in rows:
            start = timestamp(row.get('start_date'))
            if start is None:
                continue
            oldest = start if oldest is None or start < oldest else oldest
            if start < cutoff:
                continue
            team1, team2 = row.get('team1') or {}, row.get('team2') or {}
            winner = row.get('winner_team_id')
            if not team1.get('id') or not team2.get('id') or winner is None:
                if winner is None and len(samples) < 2:
                    samples.append({k: row.get(k) for k in
                                    ('id', 'slug', 'start_date', 'status', 'parsed_status', 'bo_type',
                                     'team1_score', 'team2_score', 'scores', 'results', 'winner_team_id')})
                missing_winner += 1
                continue
            edges.append({'id': row.get('id') or row.get('slug'),
                          'date': str(row.get('start_date'))[:10],
                          'a': int(team1['id']), 'b': int(team2['id']),
                          'a_name': team1.get('name'), 'b_name': team2.get('name'),
                          'winner': int(winner), 'parsed': row.get('parsed_status'),
                          'url': 'https://bo3.gg/matches/' + str(row.get('slug'))})
        pages += 1
        if len(rows) < 100 or (oldest is not None and oldest < cutoff):
            break
    return {'edges': edges, 'pages': pages, 'rows': rows_seen,
            'rows_without_winner': missing_winner, 'missing_winner_samples': samples,
            'observed_at': iso(datetime.now(UTC)), 'cutoff': iso(cutoff)}


def live_collect(evidence_dir: Path, matches: list, registry: dict) -> dict:
    """Refetch every first-party source used by the origination ladder.

    Polymarket discovery reuses the pipeline's public HTML decoder; events and
    order books are fetched for every game that joins an active fixture through
    exact names or the verified alias registry, so aliased low-tier matches get
    fresh books even though the featured pipeline skips them.
    """
    client = Collector(evidence_dir)
    out = {'requests': [], 'observed_at': iso(datetime.now(UTC))}
    # A model-only row has not been resolved by a money line, and an equal-estimate
    # featured tie (selection(...) is None) has no directional pick because the
    # exact-name collector missed aliased markets or exchanges. Run the same
    # research for those rows too.
    active = [m for m in matches if m.get('availability') != 'past'
              and (m.get('analysis') is None or m['analysis'].get('method') == 'model'
                   or selection(m['analysis'].get('probabilities')) is None)]
    # Fetch only exact, already discovered HLTV identities for primary gaps.
    # Old proof files are removed before refetch so an access failure cannot
    # leave yesterday's lineup looking newly observed.
    for stale in evidence_dir.glob('live-hltv-match-*.json'):
        stale.unlink()
    for match in active:
        if match.get('analysis') is not None:
            continue
        urls = {r['source_url'] for r in match.get('research', [])
                if r.get('stage') == 'HLTV research' and r.get('status') == 'checked'
                and str(r.get('source_url', '')).startswith('https://www.hltv.org/matches/')}
        if len(urls) == 1:
            try:
                client.fetch_html(next(iter(urls)), 'live-hltv-match-' + str(match['id']))
            except RuntimeError:
                pass  # The request manifest keeps the actual failure; no guessed lineup.
    try:
        body, _ = client.get_json(THUNDERPICK_API, 'live-thunderpick-matches', method='POST', payload={'gameIds': [6]})
        out['thunderpick'] = body
    except RuntimeError as exc:
        out['thunderpick_error'] = str(exc)
    games = []
    try:
        html_text, _ = client.fetch_html(POLY_INDEX, 'live-polymarket-index')
        from scripts.sources import polymarket_games
        games = polymarket_games(html_text)
        out['polymarket_games'] = len(games)
    except (RuntimeError, ValueError) as exc:
        out['polymarket_index_error'] = str(exc)
    games, out['polymarket_discovery'] = supplement_polymarket_discovery(
        games, evidence_dir.parent.parent, datetime.now(UTC))
    if not out['polymarket_discovery'].get('tagged_discovery_available'):
        from scripts.sources import gamma_games
        tagged_pages = 0
        while tagged_pages < 20:
            query = urlencode({
                'tag_slug': 'counter-strike-2', 'active': 'true', 'closed': 'false',
                'limit': 100, 'offset': tagged_pages * 100,
            })
            try:
                page_events, _ = client.get_json(
                    f'https://gamma-api.polymarket.com/events?{query}',
                    f'live-polymarket-discovery-{tagged_pages * 100}',
                )
            except RuntimeError:
                break
            if not isinstance(page_events, list) or not page_events:
                break
            games.extend(gamma_games(
                page_events,
                f'data/origination/evidence/live-polymarket-discovery-{tagged_pages * 100}.json',
            ))
            tagged_pages += 1
            if len(page_events) < 100:
                break
    client.save('live-discovery-audit', out['polymarket_discovery'])
    events = []
    books = []
    seen_event_ids = set()
    for game in games:
        event_key = str(game.get('id') or '')
        if not event_key or event_key in seen_event_ids:
            continue
        names = [game.get('homeName', ''), game.get('awayName', '')]
        joined = [m for m in active if pair_join(names, game.get('startTime'), m, registry)[2] == 'matched']
        if len(joined) != 1:
            continue
        seen_event_ids.add(event_key)
        fixture = joined[0]
        try:
            event, event_request = client.get_json(POLY_EVENTS + str(game['id']), 'live-polymarket-event-' + str(game['id']))
        except RuntimeError as exc:
            continue
        if event.get('active') is not True or event.get('closed') is not False or event.get('live') is True:
            continue
        # Reuse the featured market contract after a scoped alias-only name
        # mapping. It requires ONE active full-series market with both teams,
        # matching future start and accepting orders; never select the first
        # map/prop or silently pick among duplicate moneylines.
        moneyline, _ = aliased_series_market(event, fixture, registry, datetime.now(UTC))
        if not moneyline:
            continue
        tokens = moneyline.get('clobTokenIds')
        if isinstance(tokens, str):
            try:
                tokens = json.loads(tokens)
            except ValueError:
                continue
        if not tokens or len(tokens) != 2:
            continue
        bid, ask = [], []
        for token in tokens:
            try:
                book, _ = client.get_json(CLOB_BOOK + str(token), 'live-polymarket-book-' + str(game['id']) + '-' + str(len(bid)))
            except RuntimeError:
                book = None
            if book is None:
                bid, ask = [], []
                break
            bids = [finite(x.get('price')) for x in book.get('bids', [])
                    if finite(x.get('size')) is not None and float(x['size']) > 0]
            asks = [finite(x.get('price')) for x in book.get('asks', [])
                    if finite(x.get('size')) is not None and float(x['size']) > 0]
            from scripts.domain import is_fresh
            stamp = timestamp(book.get('timestamp'))
            if not stamp or not is_fresh(iso(stamp), datetime.now(UTC)) or str(book.get('asset_id')) != str(token) or book.get('market') != moneyline.get('conditionId'):
                bid, ask = [], []
                break
            if not bids or not asks or any(p is None or not 0 < p < 1 for p in bids + asks):
                bid, ask = [], []
                break
            bid.append(max(bids))
            ask.append(min(asks))
            books.append({'asset_id': str(token), 'best_bid': max(bids), 'best_ask': min(asks),
                          'last_trade_price': finite(book.get('last_trade_price')),
                          'source_url': CLOB_BOOK + str(token)})
        record = {
            'event_id': str(event.get('id')), 'slug': event.get('slug'), 'title': moneyline.get('question'),
            'source_url': POLY_EVENTS + str(event.get('id')),
            'public_page': 'https://polymarket.com/event/' + str(event.get('slug', '')),
            'observed_at': event_request['observed_at'], 'active': event.get('active'), 'closed': event.get('closed'),
            'moneyline_market_id': str(moneyline.get('id')),
            'outcomes': json.loads(moneyline['outcomes']) if isinstance(moneyline.get('outcomes'), str) else moneyline.get('outcomes'),
            'game_start_time': moneyline.get('gameStartTime') or event.get('startTime'),
            'clob_token_ids': [str(x) for x in tokens],
        }
        if len(bid) == 2:
            record['book_bid'] = bid
            record['book_ask'] = ask
        events.append(record)
    (evidence_dir / 'live-polymarket-observations.json').write_text(
        json.dumps({'schema_version': 2, 'observed_at': out['observed_at'], 'polymarket_events': events, 'polymarket_books': books},
                   ensure_ascii=False, indent=2) + '\n')
    # Kalshi CS2 match-winner events (officially documented public API). Pages are
    # bounded; an unfinished cursor is recorded rather than claimed complete.
    # A failed refetch must never leave an older observation looking current.
    for stale in ['live-kalshi-events.json', 'live-bovada-cs2.json']:
        (evidence_dir / stale).unlink(missing_ok=True)
    pages, cursor, complete = [], '', False
    for page in range(10):
        query = {'series_ticker': KALSHI_SERIES, 'status': 'open', 'with_nested_markets': 'true', 'limit': 200}
        if cursor:
            query['cursor'] = cursor
        url = KALSHI_EVENTS + '?' + urlencode(query)
        try:
            body, entry = client.get_json(url, f'live-kalshi-events-{page}', save=False)
        except RuntimeError as exc:
            out['kalshi_error'] = str(exc)
            break
        if not isinstance(body, dict) or not isinstance(body.get('events'), list):
            out['kalshi_error'] = 'Kalshi events contract unrecognized'
            break
        pages.append({'url': url, 'observed_at': entry['observed_at'], 'response': body})
        cursor = body.get('cursor') or ''
        if not cursor:
            complete = True
            break
    if pages:
        (evidence_dir / 'live-kalshi-events.json').write_text(json.dumps(
            {'source': 'Kalshi public market data API', 'docs': KALSHI_DOCS, 'pagination_complete': complete,
             'observed_at': pages[0]['observed_at'], 'pages': pages}, ensure_ascii=False) + '\n')
    # Bovada public Counter-Strike 2 coupon (prematch only).
    try:
        body, entry = client.get_json(BOVADA_API, 'live-bovada-cs2', save=False)
        if isinstance(body, list):
            (evidence_dir / 'live-bovada-cs2.json').write_text(json.dumps(
                {'source': 'Bovada public sportsbook coupon', 'url': BOVADA_API,
                 'observed_at': entry['observed_at'], 'response': body}, ensure_ascii=False) + '\n')
        else:
            out['bovada_error'] = 'Bovada coupon contract unrecognized'
    except RuntimeError as exc:
        out['bovada_error'] = str(exc)
    # Smarkets exchange board (session 46ade650). Public documented read-only
    # API; it lists academy/tier-3 CS2 fixtures the other exchanges skip. An
    # outage records a reason and prices nothing — never a guessed quote.
    (evidence_dir / smarkets_lines.EVIDENCE_NAME).unlink(missing_ok=True)
    try:
        out['smarkets'] = smarkets_lines.collect(client, evidence_dir, matches)
    except Exception as exc:  # noqa: BLE001 - research must never block a refresh
        out['smarkets_error'] = f'{type(exc).__name__}: {exc}'[:300]
    for stale in ('live-valve-directory.json', 'live-valve-standings.json', 'live-valve-standings-text.json'):
        (evidence_dir / stale).unlink(missing_ok=True)
    # Pinnacle public guest board (first-party esportsbook prices). Non-fatal:
    # an outage records a reason and prices nothing. Period-0 series moneylines
    # only; the loader rejects specials and per-map periods by construction.
    (evidence_dir / 'live-pinnacle-cs.json').unlink(missing_ok=True)
    try:
        leagues_body, _ = client.get_json(PINNACLE_API + '/sports/12/leagues', 'live-pinnacle-leagues', save=False)
        matchups_body, _ = client.get_json(PINNACLE_API + '/sports/12/matchups', 'live-pinnacle-matchups', save=False)
        straight = []
        for lg in leagues_body or []:
            if not isinstance(lg, dict) or lg.get('id') is None:
                continue
            if not str(lg.get('name') or '').startswith('CS2'):
                continue
            try:
                rows, entry = client.get_json(f"{PINNACLE_API}/leagues/{lg['id']}/markets/straight",
                                              f'live-pinnacle-straight-{lg["id"]}', save=False)
            except RuntimeError as exc:
                out['pinnacle_error'] = str(exc)
                continue
            straight.append({'league_id': lg['id'], 'observed_at': entry['observed_at'], 'markets': rows})
        (evidence_dir / 'live-pinnacle-cs.json').write_text(json.dumps({
            'source': 'Pinnacle public guest market board', 'url': PINNACLE_PAGE,
            'api_url': PINNACLE_API, 'docs': 'https://www.pinnacle.com/en/esports',
            'observed_at': iso(datetime.now(UTC)),
            'leagues': [l for l in leagues_body or [] if isinstance(l, dict)],
            'matchups': [m for m in matchups_body or [] if isinstance(m, dict)],
            'straight': straight}, ensure_ascii=False, indent=2) + '\n')
        out['pinnacle'] = {'cs2_leagues': len(straight),
                           'matchups': sum(1 for m in matchups_body or [] if isinstance(m, dict))}
    except RuntimeError as exc:
        out['pinnacle_error'] = str(exc)
    # Official HLTV weekly world ranking (research-model rung; never a money
    # line). Pages are read with the same public GET as every other source and
    # saved for replay; a failed fetch leaves the rung inactive.
    (evidence_dir / 'live-hltv-ranking.json').unlink(missing_ok=True)
    try:
        pages = []
        for offset in (0, 30, 60, 90):
            url = HLTV_RANKING_URL + (f'?offset={offset}' if offset else '')
            try:
                text, req = client.fetch_html(url, 'live-hltv-ranking-' + str(offset))
            except RuntimeError as exc:
                out['hltv_ranking_error'] = str(exc)
                break
            rows = hltv_ranking.parse_ranking_page(text)
            for position, row in enumerate(rows):
                row['rank'] = offset + position + 1
            final_url = req.get('final_url') or url
            pages.append({'url': final_url, 'status': 'ok', 'observed_at': req.get('observed_at') or iso(datetime.now(UTC)),
                          'rows': rows})
            # The whole world ranking renders on one page when it carries at
            # least 200 rows; offset pages exist only for older split layouts.
            if len(rows) < 25 or len(rows) >= 200:
                break
        if pages:
            observed_at = pages[0]['observed_at']
            # HLTV's canonical page redirects to a dated publication slug such
            # as /ranking/teams/2026/october/12; that date is the publication
            # date the model runs against, not the fetch wall clock.
            dated = re.search(r'/ranking/teams/(\d{4})/([a-z]+)/(\d{1,2})', pages[0]['url'] or '')
            if dated:
                month = MONTHS.index(dated.group(2)[:3].title()) + 1
                snapshot_date = f'{int(dated.group(1)):04d}-{month:02d}-{int(dated.group(3)):02d}'
            else:
                snapshot_date = observed_at[:10]
            (evidence_dir / 'live-hltv-ranking.json').write_text(json.dumps({
                'source': 'HLTV official weekly world ranking', 'source_url': HLTV_RANKING_URL,
                'observed_at': observed_at, 'snapshot_date': snapshot_date,
                'pages': pages}, ensure_ascii=False, indent=2) + '\n')
            out['hltv_ranking'] = {'pages': len(pages),
                                   'teams': sum(len(p['rows']) for p in pages),
                                   'snapshot_date': snapshot_date}
    except RuntimeError as exc:
        out['hltv_ranking_error'] = str(exc)
    valve_text = None
    try:
        now = datetime.now(UTC)
        directory, _ = client.get_json(f'{VALVE_REPO}/contents/live/{now.year}', 'live-valve-directory')
        names = []
        for entry in directory:
            m = re.fullmatch(r'standings_global_(\d{4})_(\d{2})_(\d{2})\.md', entry['name'])
            if m:
                day = '-'.join(m.groups())
                if day <= now.date().isoformat():
                    names.append((day, entry['path']))
        if names:
            day, path = max(names)
            content, _ = client.get_json(f'{VALVE_REPO}/contents/{path}', 'live-valve-standings')
            text = base64.b64decode(content['content']).decode('utf-8')
            valve_text = text
            (evidence_dir / 'live-valve-standings-text.json').write_text(
                json.dumps({'snapshot_date': day, 'source_url': content['html_url'],
                            'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'text': text},
                           ensure_ascii=False, indent=2) + '\n')
            out['valve'] = {'snapshot_date': day, 'source_url': content['html_url']}
    except RuntimeError as exc:
        out['valve_error'] = str(exc)
    # Relayed bookmaker quotes (session 15fc6bca): a stale document must never be
    # reused, so the previous file is removed before the refetch.
    (evidence_dir / 'live-bo3-relay.json').unlink(missing_ok=True)
    try:
        out['bo3_relay'] = collect_bo3_relay(client, evidence_dir, matches, registry)
    except Exception as exc:  # noqa: BLE001 - a relay outage prices nothing
        out['bo3_relay_error'] = f'{type(exc).__name__}: {exc}'[:200]
    try:
        known = set()
        if valve_text:
            try:
                from scripts.domain import parse_valve_table
                groups = {}
                for row in parse_valve_table(valve_text, '', '2000-01-01'):
                    groups.setdefault(name_key(row['name']), []).append(row)
                # "Known" means usable by rating_row: exactly one complete row.
                known = {name for name, rows in groups.items()
                         if len([r for r in rows if len(r.get('roster') or []) == 5]) == 1}
            except (ValueError, KeyError, TypeError):
                known = set()
        out['bo3_results'] = collect_bo3_results(client, evidence_dir, matches, registry, known or None)
    except Exception as exc:  # noqa: BLE001 - a results outage prices nothing
        out['bo3_results_error'] = f'{type(exc).__name__}: {exc}'[:200]
    # Own-line network model (session 541cd43a): the results graph is only
    # fetched when at least one active fixture has no money-backed featured
    # estimate, i.e. exactly the rows the research rungs must price. A failure
    # here leaves the rung inactive and is published as a reason, never a value.
    needs_graph = any(m.get('availability') != 'past'
                      and (m.get('analysis') is None or m.get('analysis', {}).get('method') == 'model')
                      for m in matches)
    if needs_graph:
        try:
            out['bo3_graph'] = collect_bo3_graph(client, evidence_dir)
        except Exception as exc:  # noqa: BLE001 - a results outage prices nothing
            out['bo3_graph_error'] = f'{type(exc).__name__}: {exc}'[:200]
    # Automated EGamersWorld aggregated reference (session arena-43110640):
    # the reviewed reference rung used to depend on manual capture files and
    # went stale after eight hours. The index is fetched and saved verbatim
    # like every other source; entries are derived from it in the reviewed
    # schema and still pass reference_odds.quote()'s fail-closed gate
    # (identical placeholder odds, stale or start-mismatched rows price
    # nothing). Non-fatal: an outage records a reason and prices nothing.
    (evidence_dir / egw_live.EVIDENCE_NAME).unlink(missing_ok=True)
    try:
        egw_html, egw_req = client.fetch_html(egw_live.INDEX_URL, egw_live.INDEX_EVIDENCE)
        egw_entries = egw_live.entries_for(egw_html, active, registry,
                                           egw_req.get('observed_at') or iso(datetime.now(UTC)))
        (evidence_dir / egw_live.EVIDENCE_NAME).write_text(json.dumps({
            'source': 'EGamersWorld CS2 matches index (automated capture)',
            'url': egw_live.INDEX_URL,
            'observed_at': egw_req.get('observed_at'),
            'entries': egw_entries}, ensure_ascii=False, indent=2) + '\n')
        out['egw_live'] = {'entries': len(egw_entries),
                           'policy': 'Only independently source-timed, exact named-price captures; unverified index leads price nothing.'}
    except Exception as exc:  # noqa: BLE001 - an aggregator outage prices nothing
        out['egw_live_error'] = f'{type(exc).__name__}: {exc}'[:300]
    out['requests'] = client.requests
    (evidence_dir / 'live-collection-manifest.json').write_text(json.dumps(out['requests'], ensure_ascii=False, indent=2) + '\n')
    return out


# ---------------------------------------------------------------------------
# Observation loading (replay from saved evidence)
# ---------------------------------------------------------------------------

def load_json(path: Path):
    return json.loads(path.read_text())


def thunderpick_rows(repo_data: Path, live: dict | None) -> list:
    rows = []
    if live and isinstance(live.get('thunderpick'), dict):
        if live['thunderpick'].get('ok') is not True:
            return []
        body = (live['thunderpick'].get('data') or {})
        if not isinstance(body, dict):
            return []
        rows = body.get('upcoming') or body.get('matches') or []
        observed = next((r.get('observed_at') for r in live.get('requests', []) if r.get('id') == 'live-thunderpick-matches' and r.get('status') == 'ok'), None)
        source = ('data/origination/evidence/live-thunderpick-matches.json', observed)
    else:
        path = repo_data / 'evidence' / 'thunderpick-matches.json'
        if not path.exists():
            return []
        body = load_json(path)
        if not isinstance(body, dict) or body.get('ok') is not True:
            return []
        inner = body.get('data') or {}
        if not isinstance(inner, dict):
            return []
        rows = inner.get('upcoming') or inner.get('matches') or []
        snapshot = load_json(repo_data / 'latest.json')
        observed = next((r.get('observed_at') for r in snapshot.get('requests', []) if r.get('id') == 'thunderpick-matches' and r.get('status') == 'ok'), None)
        source = ('data/evidence/thunderpick-matches.json', observed)
    out = []
    if not isinstance(rows, list):
        return []
    for row in rows:
        if not isinstance(row, dict):
            continue
        teams, market = row.get('teams'), row.get('market')
        if not isinstance(teams, dict) or not isinstance(market, dict) or not isinstance(market.get('name'), str):
            continue
        if any(not isinstance(teams.get(k), dict) for k in ('home', 'away')):
            continue
        names = [teams[k].get('name') for k in ('home', 'away')]
        if name_key(market['name']) not in {'match winner', 'match winner incl. overtime', 'match winner inc. overtime'}:
            continue
        if row.get('gameId') != 6 or row.get('isLive') is not False or not row.get('id') or market.get('status') != 1 or market.get('draw') is not None:
            continue
        sides = [market.get(k) or {} for k in ['home', 'away']]
        if any(not isinstance(s, dict) or s.get('status') != 1 for s in sides):
            continue
        # Preserve the event's own team pair before reading outcome labels.
        # Comparing the outcome names to themselves used to accept a market
        # nested under an unrelated or malformed event.
        outcome_names = [s.get('name') for s in sides]
        if (not all(isinstance(n, str) and n.strip() for n in names + outcome_names)
                or len(set(map(name_key, names))) != 2
                or set(map(name_key, outcome_names)) != set(map(name_key, names))):
            continue
        odds = [finite(s.get('odds')) for s in sides]
        if any(o is None or o <= 1 for o in odds):
            continue
        out.append({'family': 'bookmaker', 'provider': 'Thunderpick', 'names': outcome_names,
                    'start': row.get('startTime'), 'odds': odds,
                    'event_id': str(row.get('id')), 'source_url': THUNDERPICK_PAGE, 'observed_at': source[1],
                    'api_url': THUNDERPICK_API, 'evidence_file': source[0]})
    return out


def polymarket_rows(repo_data: Path, orig_evidence: Path) -> list:
    """Build Polymarket market rows from saved pipeline evidence plus research fetches."""
    rows = []
    index_path = repo_data / 'evidence' / 'polymarket-index.json'
    games = load_json(index_path) if index_path.exists() else []
    by_id = {str(g.get('id')): g for g in games}
    # Events saved by the featured pipeline.
    for path in sorted((repo_data / 'evidence').glob('polymarket-event-*.json')):
        event = load_json(path)
        rows.extend(_rows_from_event(event, path.name, repo_data / 'evidence'))
    # Fresh aliased events captured by --live collection.
    live_path = orig_evidence / 'live-polymarket-observations.json'
    if live_path.exists():
        live = load_json(live_path)
        books = {b['asset_id']: b for b in live.get('polymarket_books', [])}
        for ev in live.get('polymarket_events', []):
            if ev.get('closed') is True or ev.get('active') is False:
                continue
            rows.extend(_rows_from_research_event(ev, books, 'data/origination/evidence/live-polymarket-observations.json'))
    # Prefer the freshest retained source per event, preserving ambiguity within it.
    priority = {'live-polymarket-observations': 2, 'research-fetches': 1}
    by_event = {}
    for row in rows:
        rank = 0
        for key, value in priority.items():
            if key in (row.get('evidence_file') or ''):
                rank = value
        current = by_event.get(row['event_id'])
        if current is None or rank > current[0]:
            by_event[row['event_id']] = (rank, [row])
        elif rank == current[0] and row not in current[1]:
            # Preserve duplicate full-series candidates so the resolver can
            # reject ambiguity instead of silently selecting the final row.
            current[1].append(row)
    return [row for entry in by_event.values() for row in entry[1]]


def _rows_from_event(event: dict, evidence_file: str, evidence_dir: Path) -> list:
    rows = []
    if event.get('closed') is not False or event.get('active') is not True or event.get('live') is True:
        return rows
    for market in event.get('markets', []):
        scope = market.get('sportsMarketType') or (market.get('sports') or {}).get('sports_market_type')
        question = market.get('question', '')
        if scope != 'moneyline' or market.get('active') is not True or market.get('closed') is not False or market.get('acceptingOrders') is not True:
            continue
        if re.search(r'\b(map\s*\d|game\s*\d|handicap|spread|total|outright|over/under)\b', question, re.I):
            continue
        outcomes = market.get('outcomes')
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except ValueError:
                outcomes = None
        tokens = market.get('clobTokenIds')
        if isinstance(tokens, str):
            try:
                tokens = json.loads(tokens)
            except ValueError:
                tokens = None
        if not outcomes or len(outcomes) != 2 or not tokens or len(tokens) != 2:
            continue
        start = market.get('gameStartTime') or event.get('startTime') or event.get('eventStartTime')
        bids, asks, ok = [], [], True
        for token in tokens:
            book_path = evidence_dir / f'polymarket-book-{event.get("id")}-{len(bids)}.json'
            if book_path.exists():
                book = load_json(book_path)
                from scripts.domain import book_midpoint
                try:
                    levels = book_midpoint(book, str(token), market.get('conditionId'), datetime.now(UTC))
                    bids.append(levels['bid'])
                    asks.append(levels['ask'])
                except (ValueError, TypeError):
                    ok = False
                    break
            else:
                ok = False
        row = {'family': 'market', 'provider': 'Polymarket', 'names': [str(o) for o in outcomes],
               'start': start, 'event_id': str(event.get('id')), 'market_id': str(market.get('id')),
               'source_url': 'https://polymarket.com/event/' + str(event.get('slug', '')),
               'api_url': POLY_EVENTS + str(event.get('id')), 'evidence_file': evidence_file,
               'question': question}
        if ok and all(b is not None and a is not None for b, a in zip(bids, asks)):
            row['bid'] = bids
            row['ask'] = asks
        rows.append(row)
    return rows


def _rows_from_research_event(ev: dict, books: dict, evidence_file: str) -> list:
    row = {'family': 'market', 'provider': 'Polymarket', 'names': list(ev.get('outcomes', [])),
           'start': ev.get('game_start_time'), 'event_id': str(ev.get('event_id')),
           'market_id': str(ev.get('moneyline_market_id')),
           'source_url': ev.get('public_page'), 'api_url': ev.get('source_url'),
           'evidence_file': evidence_file,
           'question': ev.get('title', ''), 'observed_at': ev.get('observed_at')}
    if ev.get('book_bid') and ev.get('book_ask') and len(ev['book_bid']) == 2:
        row['bid'] = [float(x) for x in ev['book_bid']]
        row['ask'] = [float(x) for x in ev['book_ask']]
        return [row]
    bids, asks = [], []
    for token in ev.get('clob_token_ids', []):
        book = books.get(str(token))
        if not book or book.get('best_bid') is None or book.get('best_ask') is None:
            return [row]
        bids.append(float(book['best_bid']))
        asks.append(float(book['best_ask']))
    if len(bids) == 2:
        row['bid'] = bids
        row['ask'] = asks
    return [row]


def out_rows(rows: list) -> list:
    return rows


_KALSHI_SCHEDULE = re.compile(r'originally scheduled for ([A-Z][a-z]{2}) (\d{1,2}), (\d{4}) at (\d{1,2}):(\d{2}) (AM|PM) (EDT|EST)\b')
_KALSHI_TICKER = re.compile(r'^KXCS2GAME-(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})[A-Z0-9]+$')


def kalshi_start(event: dict):
    """Scheduled start from the contract rules, cross-checked with the event ticker.

    Every market's rules must state the same 'originally scheduled for <date> at
    <time> EDT/EST' and the ticker's encoded US-Eastern date/time must agree.
    Anything else returns None (unverified start → no join).
    """
    starts = set()
    markets = event.get('markets') or []
    if not markets:
        return None
    for market in markets:
        m = _KALSHI_SCHEDULE.search(market.get('rules_primary') or '')
        if not m or m.group(1) not in MONTHS:
            return None
        mon, day, year, hh, mm, ampm, zone = m.groups()
        hour = int(hh) % 12 + (12 if ampm == 'PM' else 0)
        tz = timezone(timedelta(hours=-4 if zone == 'EDT' else -5))
        try:
            local = datetime(int(year), MONTHS.index(mon) + 1, int(day), hour, int(mm), tzinfo=tz)
        except ValueError:
            return None
        starts.add(local)
    if len({s.astimezone(UTC) for s in starts}) != 1:
        return None
    local = next(iter(starts))
    t = _KALSHI_TICKER.match(event.get('event_ticker') or '')
    if not t:
        return None
    yy, mon, dd, hh, mm = t.groups()
    if (local.year % 100, local.strftime('%b').upper(), local.day, local.hour, local.minute) != (int(yy), mon, int(dd), int(hh), int(mm)):
        return None
    return iso(local.astimezone(UTC))


def kalshi_rows(orig_evidence: Path) -> list:
    """Kalshi CS2 match-winner rows from the saved original API response."""
    path = orig_evidence / 'live-kalshi-events.json'
    if not path.exists():
        return []
    saved = load_json(path)
    rows = []
    for page in saved.get('pages', []):
        observed = page.get('observed_at')
        for ev in (page.get('response') or {}).get('events', []):
            if ev.get('series_ticker') != KALSHI_SERIES or (ev.get('product_metadata') or {}).get('competition') != 'CS2':
                continue
            markets = ev.get('markets') or []
            if ev.get('mutually_exclusive') is not True or len(markets) != 2:
                continue
            start = kalshi_start(ev)
            names = [m.get('yes_sub_title') for m in markets]
            if not start or not all(isinstance(n, str) and n.strip() for n in names):
                continue
            # In-play or already-started observations are never prematch lines.
            if timestamp(observed) is None or timestamp(start) <= timestamp(observed):
                continue
            ticker = str(ev.get('event_ticker'))
            row = {'family': 'market', 'provider': 'Kalshi', 'names': names, 'start': start,
                   'event_id': ticker, 'market_tickers': [str(m.get('ticker')) for m in markets],
                   'source_url': KALSHI_PAGE + ticker.lower(), 'api_url': KALSHI_EVENTS + '/' + ticker,
                   'evidence_file': 'data/origination/evidence/live-kalshi-events.json', 'observed_at': observed,
                   'question': ev.get('title', ''), 'rules': markets[0].get('rules_primary', '')}
            bids = [finite(m.get('yes_bid_dollars')) for m in markets]
            asks = [finite(m.get('yes_ask_dollars')) for m in markets]
            if all(m.get('status') == 'active' for m in markets) and all(v is not None for v in bids + asks):
                row['bid'], row['ask'] = bids, asks
            rows.append(row)
    return rows


def bovada_rows(orig_evidence: Path) -> list:
    """Bovada prematch series moneylines from the saved original coupon response."""
    path = orig_evidence / 'live-bovada-cs2.json'
    if not path.exists():
        return []
    saved = load_json(path)
    observed = saved.get('observed_at')
    rows = []
    for group in saved.get('response') or []:
        if not isinstance(group, dict):
            continue
        league = ' / '.join(str(p.get('description')) for p in group.get('path', []) if isinstance(p, dict))
        for ev in group.get('events', []):
            if ev.get('type') != 'GAMEEVENT' or ev.get('live') is not False or not isinstance(ev.get('startTime'), (int, float)):
                continue
            start = iso(datetime.fromtimestamp(ev['startTime'] / 1000, UTC))
            if timestamp(observed) is None or timestamp(start) <= timestamp(observed):
                continue
            lines = [m for g in ev.get('displayGroups', []) for m in g.get('markets', [])
                     if m.get('key') == '2W-12' and m.get('description') == 'Moneyline'
                     and (m.get('period') or {}).get('main') is True and (m.get('period') or {}).get('live') is False
                     and m.get('status') == 'O']
            if len(lines) != 1:
                continue
            outcomes = lines[0].get('outcomes') or []
            if len(outcomes) != 2 or any(o.get('status') != 'O' for o in outcomes):
                continue
            names = [o.get('description') for o in outcomes]
            competitors = {name_key(c.get('name') or '') for c in ev.get('competitors', [])}
            if not all(isinstance(n, str) and n.strip() for n in names) or {name_key(n) for n in names} != competitors:
                continue
            odds = [finite((o.get('price') or {}).get('decimal')) for o in outcomes]
            if any(o is None or o <= 1 for o in odds):
                continue
            rows.append({'family': 'bookmaker', 'provider': 'Bovada', 'names': names, 'start': start, 'odds': odds,
                         'event_id': str(ev.get('id')), 'market_id': str(lines[0].get('id')),
                         'source_url': BOVADA_SITE + str(ev.get('link') or ''), 'api_url': BOVADA_API,
                         'evidence_file': 'data/origination/evidence/live-bovada-cs2.json', 'observed_at': observed,
                         'league': league})
    return rows


def pinnacle_rows(orig_evidence: Path) -> list:
    """Pinnacle guest-board two-way series moneylines from the saved response.

    Series lines only (lowest period, per pinnacle_lines.series_moneyline —
    period 0 when present, higher periods are per-map prices and are never
    taken for a series). American prices are converted to decimal by the same
    module; "Yes/No", "Odd/Even" and score-grid specials are rejected there by
    participant text before any price is read.
    """
    path = orig_evidence / 'live-pinnacle-cs.json'
    if not path.exists():
        return []
    saved = load_json(path)
    if not isinstance(saved, dict):
        return []
    observed = saved.get('observed_at')
    out = []
    for m in saved.get('matchups') or []:
        if not isinstance(m, dict):
            continue
        league = (m.get('league') or {}).get('name') or ''
        if not league.startswith('CS2'):
            continue
        if m.get('isLive') is not False:
            continue
        lid = (m.get('league') or {}).get('id')
        block = next((b for b in saved.get('straight') or []
                      if isinstance(b, dict) and str(b.get('league_id')) == str(lid)), None)
        found = pinnacle_lines.series_moneyline(m, (block or {}).get('markets') or [])
        if not found:
            continue
        # Period 0 is the series line on this board (verified 2026-10-18: the
        # higher periods repeat identical per-map prices). A matchup priced
        # only on periods >= 1 has NO series line and is never quoted here.
        if found['period'] != 0:
            continue
        names = [p.get('name') for p in m.get('participants') or []]
        # The quote's prices follow the price array's own keying; realign the
        # converted decimals onto the participant order carried in 'names',
        # exactly as align_by_name does for every other provider.
        odds_by_name = dict(zip(found['participants'], found['decimal']))
        if len(odds_by_name) != 2 or any(n not in odds_by_name for n in names):
            continue
        out.append({'family': 'bookmaker', 'provider': 'Pinnacle', 'names': names,
                    'start': m.get('startTime'), 'odds': [odds_by_name[n] for n in names],
                    'event_id': str(m.get('id')), 'market_id': 'series-moneyline-period-0',
                    'source_url': PINNACLE_PAGE,
                    'api_url': f'{PINNACLE_API}/leagues/{lid}/markets/straight',
                    'evidence_file': 'data/origination/evidence/live-pinnacle-cs.json',
                    'observed_at': (block or {}).get('observed_at') or observed,
                    'league': league, 'best_of': m.get('bestOfX')})
    return out


def _verified_valve_rows(repo_data: Path, live: bool, manifest: list):
    """Verify decoded rows against the official Contents response and blob ID."""
    from scripts.domain import parse_valve_table
    if live:
        folder = repo_data / 'origination/evidence'
        payload = load_json(folder / 'live-valve-standings-text.json')
        original = load_json(folder / 'live-valve-standings.json')
        directory = load_json(folder / 'live-valve-directory.json')
        label, original_reference = 'live-valve-standings', 'live-valve-standings.json'
        reference = 'data/origination/evidence/live-valve-standings-text.json'
    else:
        folder = repo_data / 'evidence'
        payload = load_json(folder / 'valve-ratings.json')
        original = load_json(folder / 'valve-standings-response.json')
        directory = load_json(folder / 'valve-directory.json')
        label, original_reference = 'valve-standings-response', 'data/evidence/valve-standings-response.json'
        reference = 'data/evidence/valve-ratings.json'
    day = payload.get('snapshot_date')
    if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('Valve snapshot date is unverified')
    path = 'live/' + day[:4] + '/standings_global_' + day.replace('-', '_') + '.md'
    url = 'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/' + path
    if (original.get('encoding') != 'base64' or original.get('path') != path
            or original.get('html_url') != url or payload.get('source_url') != url):
        raise ValueError('Valve decoded source does not match the official Contents identity')
    raw = base64.b64decode(''.join(original['content'].split()), validate=True)
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob != original.get('sha'):
        raise ValueError('Valve original content does not match its Git blob ID')
    entries = [e for e in directory if isinstance(e, dict) and e.get('path') == path]
    if len(entries) != 1 or entries[0].get('sha') != blob:
        raise ValueError('Valve standings do not match the original directory entry')
    observations = [r for r in manifest if r.get('id') == label and r.get('status') == 'ok']
    if (len(observations) != 1 or not timestamp(observations[0].get('observed_at'))
            or observations[0].get('url') != VALVE_REPO + '/contents/' + path
            or observations[0].get('method') != 'GET'
            or observations[0].get('evidence') != original_reference):
        raise ValueError('Valve source lacks its original unique successful request')
    text = raw.decode('utf-8')
    rows = parse_valve_table(text, url, day)
    if live:
        if payload.get('text') != text or payload.get('text_sha256') != hashlib.sha256(raw).hexdigest():
            raise ValueError('Decoded Valve text differs from the original official content')
    elif payload.get('rows') != rows or payload.get('git_blob_sha') != blob:
        raise ValueError('Derived Valve rating rows differ from the original official content')
    return rows, {'source_url': url, 'snapshot_date': day, 'evidence_file': reference,
                  'observed_at': observations[0]['observed_at'], 'git_blob_sha': blob}


def valve_rows(repo_data: Path, live: dict | None, *, evidence_file: str | None = None) -> tuple[list | None, dict | None]:
    """Select a verified original, preserving source time and the replayed path.

    A failed live attempt may fall back only to the independently verified
    featured original. A publisher replay explicitly selecting live evidence must
    reject missing/altered originals, never quietly change its evidence source.
    """
    live_reference = 'data/origination/evidence/live-valve-standings-text.json'
    if evidence_file not in (None, live_reference, 'data/evidence/valve-ratings.json'):
        raise ValueError('Unrecognized Valve evidence reference')
    forced_live = evidence_file == live_reference
    limitation = None
    if forced_live or live is not None:
        try:
            manifest = (live.get('requests', []) if live is not None
                        else load_json(repo_data / 'origination/evidence/live-collection-manifest.json'))
            return _verified_valve_rows(repo_data, True, manifest)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            if forced_live:
                raise ValueError('Original live Valve source rejected: ' + str(exc)) from exc
            limitation = 'Live Valve source was not verified; only the separately verified dated featured original is available: ' + str(exc)
    if not (repo_data / 'evidence/valve-ratings.json').exists():
        return None, None
    snapshot = load_json(repo_data / 'latest.json')
    rows, meta = _verified_valve_rows(repo_data, False, snapshot.get('requests', []))
    if limitation:
        meta['limitations'] = [limitation]
    return rows, meta


# ---------------------------------------------------------------------------
# Origination ladder
# ---------------------------------------------------------------------------

def market_estimate(row: dict, match: dict, registry: dict, now: datetime):
    """Two complete, fresh paired books; no missing-time or first-row default."""
    from scripts.domain import is_fresh
    if not is_fresh(row.get('observed_at'), now):
        return None, 'Market observation is missing, future-dated or stale'
    observed, start = timestamp(row.get('observed_at')), timestamp(row.get('start'))
    if start and observed and observed >= start:
        return None, 'Market observation is not prematch'
    bid, ask = row.get('bid'), row.get('ask')
    if not isinstance(bid, list) or not isinstance(ask, list) or len(bid) != 2 or len(ask) != 2:
        return None, 'No complete paired executable prices in the saved response'
    bid, ask = [finite(b) for b in bid], [finite(a) for a in ask]
    if any(v is None for v in bid + ask):
        return None, 'Paired book prices are not finite numbers'
    if any(not 0 < b <= a < 1 for b, a in zip(bid, ask)):
        return None, 'Crossed or invalid order book rejected'
    spreads = [round(a - b, 8) for b, a in zip(bid, ask)]
    worst = max(spreads)
    if worst > MAX_ACCEPTED_SPREAD:
        seen = ', '.join(f'{n} bid/ask {b:.2f}/{a:.2f}' for n, b, a in zip(row['names'], bid, ask))
        return None, (f'Order book spread {worst:.2f} exceeds the {MAX_ACCEPTED_SPREAD:.2f} indicative ceiling '
                      f'({seen}); observation recorded, not used as a pick input.')
    try:
        probs = normalize_pair(*[(b + a) / 2 for b, a in zip(bid, ask)])
        aligned = align_by_name(probs, row['names'], match, registry)
        ordered_bid = align_by_name(bid, row['names'], match, registry)
        ordered_ask = align_by_name(ask, row['names'], match, registry)
    except (ValueError, KeyError, TypeError):
        return None, 'Paired outcome identity or probability mapping is invalid'
    quote = {'provider': row.get('provider') or 'Polymarket', 'family': 'market', 'probabilities': aligned,
             'bid': ordered_bid, 'ask': ordered_ask,
             'spread': worst, 'thin': worst > THIN_SPREAD, 'observed_at': row['observed_at'],
             'source_url': row['source_url'], 'event_id': row['event_id'], 'evidence_file': row['evidence_file']}
    for key in ('api_url', 'market_id'):
        if row.get(key):
            quote[key] = row[key]
    return quote, 'Verified paired order-book midpoints.'


def bookmaker_estimate(row: dict, match: dict, registry: dict, *, now: datetime | None = None):
    from scripts.domain import is_fresh
    # Replay at the snapshot's evaluation time, not an unrelated wall clock.
    now = now or datetime.now(UTC)
    if not is_fresh(row.get('observed_at'), now):
        return None, 'Bookmaker observation is missing, future-dated or stale'
    observed, start = timestamp(row.get('observed_at')), timestamp(row.get('start'))
    if start and observed and observed >= start:
        return None, 'Bookmaker observation is not prematch'
    try:
        probs = no_vig(row['odds'])
        aligned = align_by_name(probs, row['names'], match, registry)
        odds = align_by_name(row['odds'], row['names'], match, registry)
    except (ValueError, KeyError, TypeError) as exc:
        return None, str(exc)
    quote = {'provider': row['provider'], 'family': 'bookmaker', 'probabilities': aligned, 'odds': odds,
             'observed_at': row['observed_at'], 'source_url': row['source_url'],
             'api_url': row.get('api_url'), 'event_id': row['event_id'], 'evidence_file': row['evidence_file']}
    for key in ('market_id', 'league'):
        if row.get(key):
            quote[key] = row[key]
    return quote, 'Verified paired prematch decimal prices; margin removed by proportional normalization.'


def relayed_bookmaker_estimate(row: dict, match: dict, registry: dict, *, now: datetime | None = None):
    """Price a fixture from the two-sided bookmaker quote bo3.gg relays.

    Fail-closed on every input: stale or future-dated observation, observation
    that is not prematch, a suspended side, a non-numeric or sub-1.01
    coefficient, a paired margin outside ``domain.no_vig``'s acceptance band, or
    a name that cannot be mapped to a Hotspawn side. The returned quote is
    labelled ``family='relay'`` so it can never be counted as a first-party
    money vote, and it carries both the bo3.gg page the numbers were read from
    and the bookmaker page bo3.gg links to.
    """
    from scripts.domain import is_fresh
    now = now or datetime.now(UTC)
    if not is_fresh(row.get('observed_at'), now):
        return None, 'Relayed bookmaker observation is missing, future-dated or stale'
    observed, start = timestamp(row.get('observed_at')), timestamp(row.get('start'))
    if start and observed and observed >= start:
        return None, 'Relayed bookmaker observation is not prematch'
    active = row.get('active') or []
    if len(active) != 2 or any(value is not True for value in active):
        return None, 'The relayed quote is suspended on at least one side (active is not true)'
    try:
        probs = no_vig(row['odds'])
        aligned = align_by_name(probs, row['names'], match, registry)
        odds = align_by_name(row['odds'], row['names'], match, registry)
    except (ValueError, KeyError, TypeError) as exc:
        return None, str(exc)
    implied = [1 / float(o) for o in odds]
    # bo3.gg prints provider keys in lower case ("thunderpick"); a provider that
    # already uses its own capitalisation ("GG.BET") is left exactly as printed.
    provider = str(row['provider']).strip()
    display = provider.title() if provider.islower() else provider
    quote = {'provider': f'{display} (relayed by bo3.gg)', 'family': RELAY_FAMILY,
             'probabilities': aligned, 'odds': odds,
             'overround': round(sum(implied) - 1, 6),
             'observed_at': row['observed_at'], 'source_url': row['source_url'],
             'book_url': row.get('book_url'), 'event_id': row.get('event_id'),
             'start_delta_sec': row.get('start_delta_sec'),
             'evidence_file': row.get('evidence_file')}
    detail = (f"Two-sided prematch decimal prices {odds[0]} / {odds[1]} published by {display} and "
              f"relayed verbatim by bo3.gg (overround {quote['overround'] * 100:.2f}%); margin removed by "
              "proportional normalization. The number was read from the bo3.gg relay, not from the bookmaker's "
              'own page.')
    return quote, detail


def wide_book_quote(row: dict, match: dict, registry: dict, now: datetime):
    """Indicative midpoint of an otherwise-rejected two-sided book (guidance only).

    When the entire ladder has no compliant input but a prediction-market book
    was actually observed and simply too wide for the published ceilings, the
    brief still asks for a researched percentage. This returns that observed
    midpoint, labelled ``family='guidance'``. It never becomes a book-validated
    pick, never enters MONEY_METHODS, never overrides any compliant quote, and
    is only ever used as the very last rung. Returns (quote, worst_spread) or
    (None, reason).
    """
    from scripts.domain import is_fresh
    if not is_fresh(row.get('observed_at'), now):
        return None, 'Observation is missing, future-dated or stale'
    observed, start = timestamp(row.get('observed_at')), timestamp(row.get('start'))
    if start and observed and observed >= start:
        return None, 'Observation is not prematch'
    bid, ask = row.get('bid'), row.get('ask')
    if not isinstance(bid, list) or not isinstance(ask, list) or len(bid) != 2 or len(ask) != 2:
        return None, 'No complete paired prices'
    bid, ask = [finite(b) for b in bid], [finite(a) for a in ask]
    if any(v is None for v in bid + ask):
        return None, 'Paired prices are not finite numbers'
    if any(not 0 < b <= a < 1 for b, a in zip(bid, ask)):
        return None, 'Crossed or invalid order book'
    spreads = [round(a - b, 8) for b, a in zip(bid, ask)]
    worst = max(spreads)
    try:
        probs = normalize_pair(*[(b + a) / 2 for b, a in zip(bid, ask)])
        aligned = align_by_name(probs, row['names'], match, registry)
        ordered_bid = align_by_name(bid, row['names'], match, registry)
        ordered_ask = align_by_name(ask, row['names'], match, registry)
    except (ValueError, KeyError, TypeError):
        return None, 'Paired outcome identity or probability mapping is invalid'
    quote = {'provider': row.get('provider') or 'Polymarket', 'family': 'guidance',
             'probabilities': aligned, 'bid': ordered_bid, 'ask': ordered_ask,
             'spread': worst, 'observed_at': row['observed_at'],
             'source_url': row['source_url'], 'event_id': row.get('event_id'),
             'evidence_file': row.get('evidence_file')}
    for key in ('api_url', 'market_id'):
        if row.get(key):
            quote[key] = row[key]
    return quote, worst


def hltv_lineup_proof(evidence_dir: Path, match: dict, registry: dict, now: datetime):
    """Fresh, fixture-bound HLTV-listed lineup, replayed from original markup."""
    from scripts.domain import is_fresh
    from scripts.hltv_match import parse_match
    label = 'live-hltv-match-' + str(match['id'])
    path = evidence_dir / (label + '.json')
    manifest = evidence_dir / 'live-collection-manifest.json'
    if not path.exists() or not manifest.exists():
        return None
    try:
        raw = load_json(path)
        requests_ = [r for r in load_json(manifest) if r.get('id') == label and r.get('status') == 'ok']
        if len(requests_) != 1:
            return None
        req = requests_[0]
        if (raw.get('url') != req.get('url') or raw.get('observed_at') != req.get('observed_at')
                or not str(raw.get('url', '')).startswith('https://www.hltv.org/matches/')
                or not is_fresh(raw.get('observed_at'), now)
                or hashlib.sha256(raw['html'].encode()).hexdigest() != req.get('response_sha256')):
            return None
        parsed = parse_match(raw['html'])
        if (pair_join(parsed['teams'], parsed['starts_at'], match, registry)[2] != 'matched'
                or parsed['finished'] or not timestamp(parsed['starts_at']) or timestamp(parsed['starts_at']) <= now):
            return None
        rosters = {}
        for team in parsed['lineups']:
            name, _ = resolve_name(team['name'], registry, match.get('competition'))
            if name in rosters or not team['roster']:
                return None
            rosters[name] = team['roster']
        wanted = {name_key(t['name']) for t in match['teams']}
        if set(rosters) != wanted:
            return None
        return {'fixture_id': match['id'], 'source_url': raw['url'], 'observed_at': raw['observed_at'],
                'starts_at': parsed['starts_at'], 'names': parsed['teams'], 'rosters': rosters,
                'evidence_file': 'data/origination/evidence/' + path.name}
    except (ValueError, TypeError, KeyError):
        return None


def rating_row(name: str, ratings: list, registry: dict, competition: str | None):
    """One unique, complete five-player Valve row for this name, or None.

    Same identity rule as ``model_estimate``: incomplete remnants are ignored
    before the uniqueness test, and two complete rows stay ambiguous. Used by
    the results model so both rungs read the same official table.
    """
    if not ratings:
        return None
    by_name = {}
    for row in ratings:
        by_name.setdefault(name_key(row['name']), []).append(row)
    reverse = {}
    for entry in scoped_aliases(registry, competition):
        reverse.setdefault(name_key(entry['canonical']), []).append(name_key(entry['alias']))
    for candidate in [name_key(name)] + reverse.get(name_key(name), []):
        complete = [r for r in by_name.get(candidate) or [] if len(r.get('roster') or []) == 5]
        if len(complete) == 1:
            return complete[0]
        if len(complete) > 1:
            return None
    return None


def model_estimate(match: dict, ratings: list, registry: dict, meta: dict, now: datetime, *, lineup=None):
    """Alias-aware Valve-rating research estimate (explicitly uncalibrated)."""
    if not ratings:
        return None, 'Official Valve ratings unavailable'
    by_name = {}
    for row in ratings:
        by_name.setdefault(name_key(row['name']), []).append(row)
    reverse = {}
    for entry in scoped_aliases(registry, match.get('competition')):
        reverse.setdefault(name_key(entry['canonical']), []).append(name_key(entry['alias']))
    inputs = []
    used = []
    disambiguated = []
    for team in match['teams']:
        team_key = name_key(team['name'])
        candidates = [team_key] + reverse.get(team_key, [])
        found = []
        matched_as = None
        for candidate in candidates:
            found = by_name.get(candidate) or []
            if found:
                matched_as = candidate
                break
        if not found:
            return None, f'{team["name"]}: no Valve rating row found (including registry aliases)'
        # The published method requires a *unique exact-name, five-player record*.
        # Name-matching rows whose roster is not a complete five-player record are
        # excluded before the uniqueness test (verified on the 2026-10-05 snapshot:
        # ex-RUSTEC has one complete five-player row plus a four-player remnant;
        # Banda Chuya has one complete row plus a two-player remnant). A name with
        # several *complete* five-player rows stays rejected as ambiguous (Leo and
        # Just Players on the same snapshot), because nothing in the row data says
        # which lineup plays today.
        complete = [r for r in found if len(r.get('roster') or []) == 5]
        if len(complete) > 1:
            from scripts.domain import is_fresh
            proof_ok = (lineup and lineup.get('fixture_id') == match['id']
                        and is_fresh(lineup.get('observed_at'), now)
                        and pair_join(lineup.get('names', []), lineup.get('starts_at'), match, registry)[2] == 'matched')
            roster = (lineup.get('rosters') or {}).get(team_key) if proof_ok else None
            current = {name_key(p) for p in roster or []}
            exact = [r for r in complete if len(current) == 5
                     and len({name_key(p) for p in r['roster']}) == 5
                     and {name_key(p) for p in r['roster']} == current]
            # A single four-of-five core is also an identity proof, but only when
            # no exact five-player row exists: one current HLTV player differs from
            # the historical Valve row. This is the same evidence class as the
            # reviewed ex-6666 alias (4/5, one roster change) and is published with
            # an explicit limitation; it never overrides a money line.
            near = []
            if not exact and len(current) == 5:
                for row in complete:
                    shared = current & {name_key(p) for p in row['roster']}
                    if len(shared) >= 4:
                        near.append((row, len(shared)))
            if len(exact) != 1:
                if len(exact) == 0 and len(near) == 1:
                    row, overlap = near[0]
                    complete = [row]
                    disambiguated.append({'team': team['name'], 'standing': row['standing'], 'roster': roster,
                                          'overlap': overlap, 'roster_change': True,
                                          **{k: lineup[k] for k in ('source_url', 'observed_at', 'evidence_file')}})
                else:
                    return None, f'{team["name"]}: multiple Valve rosters share this name; no unique exact-five-player HLTV proof'
            else:
                complete = exact
                disambiguated.append({'team': team['name'], 'standing': exact[0]['standing'], 'roster': roster,
                                      'overlap': 5, 'roster_change': False,
                                      **{k: lineup[k] for k in ('source_url', 'observed_at', 'evidence_file')}})
        if not complete:
            return None, f'{team["name"]}: a complete five-player Valve roster is not confirmed'
        row = complete[0]
        if name_key(row['name']) != team_key:
            used.append({'alias': row['name'], 'canonical': team['name'], 'kind': 'registry reverse lookup',
                         'evidence': [{'url': meta['source_url'], 'source': 'Valve official standings', 'detail': f'Valve publishes this roster under the name {row["name"]}; the reviewed alias registry links the two names.'}]})
        day = timestamp(row['snapshot_date'] + 'T00:00:00Z')
        if day is None or not 0 <= (now - day).total_seconds() <= 35 * 86400:
            return None, 'Valve snapshot is future-dated or older than 35 days'
        inputs.append(row)
    exact_proof = any(d.get('overlap', 5) == 5 for d in disambiguated)
    near_proof = any(d.get('overlap', 5) < 5 for d in disambiguated)
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * VALVE_RD ** 2 / math.pi ** 2)
    p = 1 / (1 + 10 ** (g * (inputs[1]['points'] - inputs[0]['points']) / 400))
    probs = normalize_pair(p, 1 - p)
    # Every input row keeps its own official source link and snapshot date: the
    # dashboard renders one linked row per Valve input, and dropping these keys
    # crashed the production build (KeyError 'source_url') whenever a fallback
    # was resolved by this model (scheduled runs 38742696250 / 38797535468).
    quote = {'provider': 'Valve official standings', 'family': 'model', 'probabilities': probs,
             'inputs': [{'name': r['name'], 'points': r['points'], 'standing': r['standing'], 'roster': r['roster'],
                         'snapshot_date': r.get('snapshot_date') or meta['snapshot_date'],
                         'source_url': r.get('source_url') or meta['source_url']} for r in inputs],
             'snapshot_date': meta['snapshot_date'], 'source_url': meta['source_url'],
             'evidence_file': meta['evidence_file'], 'rd_assumption': VALVE_RD, 'g': g,
             'aliases_used': used, 'observed_at': meta.get('observed_at'), 'evaluation_at': iso(now)}
    if disambiguated:
        quote['lineup_disambiguation'] = disambiguated
    detail = ('Alias-aware exact-name Valve rating rows; uncalibrated research model (Valve fit.js formula).'
              + (' Ambiguous names selected only by exact five-player equality with the linked, freshly observed HLTV lineup.' if exact_proof else '')
              + (' One ambiguous name was selected by a four-of-five roster core with the linked, freshly observed HLTV lineup; one current player differs from the historical Valve row (roster change). This is an identity join, not a current-lineup adjustment.' if near_proof else ''))
    return quote, detail


def model_label(model: dict) -> str:
    """Label a research-model row by the rung that actually produced it."""
    family = (model or {}).get('family')
    if family == 'network':
        return 'Own network estimate (bo3.gg results graph)'
    if family == 'form':
        return 'Own results-based estimate (bo3.gg series results)'
    return 'Research model estimate (Valve official ratings)'


def network_limitation(model: dict) -> str:
    """The published limitation for a bo3.gg network-model row."""
    interval = model.get('interval') or [0.0, 1.0]
    text = (
        'Own uncalibrated network model, not observed betting odds: no money line, no aggregated '
        'reference and no complete official rating row existed for this fixture. Both ratings come from '
        f"a Bradley–Terry fit over {model.get('graph_matches')} finished bo3.gg series, anchored on "
        f"Valve's official points for {model.get('graph_anchors')} teams; the rating-difference "
        f"one-sigma interval is {model.get('rating_sd_diff')} points "
        f'(probability interval {interval[0]:.3f}-{interval[1]:.3f}). '
        'Current lineups, stand-ins and map vetoes are unverified.')
    if model.get('low_confidence'):
        text += (' Low confidence: the interval crosses 50% or a side has fewer than ten '
                 'finished series. Treat the direction as indicative only.')
    return text


def selection(probs) -> int | None:
    a, b = probs
    return None if abs(a - b) < 1e-8 else (0 if a > b else 1)


def ranked_tie_break(quote: dict | None) -> tuple[int, dict] | None:
    """Give an exactly even *research model* a side from the provider's own order.

    Session 4c972a51. Some low-tier fixtures have no market and no bookmaker, so
    the last rung is a research model built from published ranking points. When
    both sides carry exactly the same published points the model's estimate is
    exactly 50/50 and ``selection`` returns no side — the pick'em game still needs
    a team, and the brief asks for a pick on every listed match.

    This tie-break is deliberately narrow:

    * it applies only to a ``family='model'`` quote, never to a money line;
    * it applies only when the two probabilities are exactly equal;
    * both inputs must carry a positive published rank (``rank`` for HLTV,
      ``standing`` for Valve) and the ranks must differ;
    * it changes **no probability** — the published estimate stays 50/50 — and
      the row records which rule produced the direction.

    Anything else returns ``None`` and the fixture keeps its honest blank side.
    """
    if not isinstance(quote, dict) or quote.get('family') != 'model':
        return None
    probs = quote.get('probabilities') or []
    if len(probs) != 2 or abs(float(probs[0]) - float(probs[1])) >= 1e-8:
        return None
    inputs = quote.get('inputs') or []
    if len(inputs) != 2:
        return None
    ranks = []
    for row in inputs:
        rank = row.get('rank', row.get('standing')) if isinstance(row, dict) else None
        if isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0:
            return None
        ranks.append(rank)
    if ranks[0] == ranks[1]:
        return None
    winner = 0 if ranks[0] < ranks[1] else 1
    source = quote.get('provider') or 'Research model'
    record = {
        'rule': 'published-rank tie-break',
        'ranks': ranks,
        'winner': winner,
        'source': source,
        'source_url': quote.get('source_url'),
        'detail': (f'{source} publishes exactly equal points for both teams '
                   f'({", ".join(str(r) for r in ranks)} are the published positions), so the '
                   'model estimate is exactly 50.0% each and carries no probability edge. '
                   f'The direction is set by {source}\'s own published order: {inputs[winner].get("name")} '
                   f'is ranked {ranks[winner]} against {ranks[1 - winner]}. This decides the pick only; '
                   'it does not change either probability, and it is not a betting line.'),
    }
    return winner, record


def originate_match(match: dict, poly_rows: list, book_rows: list, ratings, valve_meta, registry: dict, now: datetime, *, hltv: list | None = None,
                    reference: list | None = None, hltv_rank: list | None = None,
                    hltv_meta: dict | None = None, relay: list | None = None) -> dict:
    if not timestamp(match.get('starts_at')) or len(match.get('teams', [])) != 2 or not all(t.get('name') and t.get('id') for t in match.get('teams', [])):
        reason = 'Fixture start time or team identity is unverified; no price join or model pick is permitted.'
        return {'origination': None, 'pick_index': None, 'aliases_used': [], 'time_flags': [],
                'limitations': [reason], 'research': [{'stage': 'Fixture identity', 'status': 'unresolved',
                'source_url': match.get('source_url') or 'https://play.hotspawn.com/lobby', 'detail': reason}]}
    trail = []
    aliases = []
    estimates = {'market': [], 'bookmaker': []}
    guidance_candidates = []
    time_flags = []
    network_quote = match.get('_network')

    # 1-2. Money sources, one provider at a time: prediction markets/exchanges
    # (Polymarket, Kalshi) and esportsbooks (Thunderpick, Bovada, Pinnacle).
    # Every provider gets its own audit-trail stage, including rejected
    # observations.
    stage_names = {
        ('market', 'Polymarket'): ('Betting market (Polymarket series winner)', POLY_INDEX),
        ('market', 'Kalshi'): ('Exchange market (Kalshi CS2 match winner)', KALSHI_PAGE.rstrip('/')),
        # Session 46ade650: a public exchange board that lists academy and
        # tier-3 CS2 matches the US exchanges and big books skip.
        ('market', 'Smarkets'): ('Exchange market (Smarkets CS2 match winner)', smarkets_lines.SOURCE_URL),
        ('bookmaker', 'Thunderpick'): ('Esportsbook line (Thunderpick original prices)', THUNDERPICK_PAGE),
        ('bookmaker', 'Bovada'): ('Esportsbook line (Bovada original prices)', BOVADA_SITE),
        ('bookmaker', 'Pinnacle'): ('Esportsbook line (Pinnacle original prices)', PINNACLE_PAGE),
    }
    notes = {key: [] for key in stage_names}
    matched = {}
    for family, rows in (('market', poly_rows), ('bookmaker', book_rows)):
        for row in rows:
            provider = row.get('provider') or ('Polymarket' if family == 'market' else 'Thunderpick')
            key = (family, provider)
            notes.setdefault(key, [])
            joined, used, status = pair_join(row['names'], row['start'], match, registry)
            if status == 'matched':
                matched.setdefault(key, [])
                item = (row, used)
                if item not in matched[key]:
                    matched[key].append(item)
    for key, candidates in matched.items():
        family, provider = key
        if len(candidates) != 1:
            ids = sorted({str(r.get('event_id')) + '/' + str(r.get('market_id') or 'series')
                          for r, _ in candidates})
            detail = (f'Ambiguous {provider} series-winner evidence: multiple matching events/markets or '
                      f'conflicting observations ({", ".join(ids)}). No first-row default is allowed.')
            notes[key].append((detail, candidates[0][0].get('source_url')))
            continue
        row, used = candidates[0]
        aliases.extend(used)
        if used:
            notes[key].append(('joined via verified alias registry', None))
        if family == 'market':
            quote, detail = market_estimate(row, match, registry, now)
        else:
            quote, detail = bookmaker_estimate(row, match, registry, now=now)
        if quote:
            estimates[family].append((quote, detail))
        else:
            notes[key].append((f'{provider} event {row.get("event_id")}: {detail}', row.get('source_url')))
            # A valid two-sided book that only failed the spread ceilings still
            # carries money information; keep the narrowest one as the final
            # guidance rung (used only if every compliant rung fails).
            if family == 'market':
                wide, spread = wide_book_quote(row, match, registry, now)
                if wide:
                    guidance_candidates.append((spread, wide))
    for key, (stage, fallback_url) in stage_names.items():
        family, provider = key
        hits = [(q, d) for q, d in estimates[family] if q['provider'] == provider]
        aliased = any(url is None for _, url in notes[key])
        rejected = [(text, url) for text, url in notes[key] if url is not None]
        if hits:
            quote, detail = hits[0]
            trail.append({'stage': stage, 'status': 'resolved',
                          'source_url': quote['source_url'], 'detail': detail + (' Joined via verified alias registry.' if aliased else '')})
        else:
            detail = (' '.join(text for text, _ in rejected) if rejected else
                      f'No alias-verified {provider} match-winner line found for these teams and start time.')
            url = rejected[0][1] if rejected and str(rejected[0][1]).startswith('https://') else fallback_url
            trail.append({'stage': stage, 'status': 'unresolved', 'source_url': url, 'detail': detail})

    # 2b. Bookmaker prices bo3.gg relays for fixtures the first-party ladder left
    # blank (session 15fc6bca). bo3.gg publishes, per upcoming match, a
    # ``bet_updates`` block naming the bookmaker, its match page and both decimal
    # coefficients. This is a second-hand copy of a first-party price, so it is
    # its own evidence class: it never joins a first-party consensus (that would
    # double count the same book), it is used only when no first-party quote
    # resolved the fixture, and every published row names the bookmaker, the
    # bo3.gg page the numbers were read from and the bookmaker page bo3.gg links
    # to. Rejected relays keep their reason in the trail; nothing is defaulted.
    relay_quotes = []
    relay_reasons = []
    for row in relay or []:
        # A row bound to a different Hotspawn fixture is never re-used, even when
        # the team names happen to line up: the collector writes the fixture id it
        # proved, and this is where that proof is enforced.
        if row.get('fixture_id') is not None and str(row.get('fixture_id')) != str(match.get('id')):
            continue
        quote, detail = relayed_bookmaker_estimate(row, match, registry, now=now)
        if quote:
            relay_quotes.append((quote, detail))
        else:
            relay_reasons.append((row, detail))
    relay_quotes.sort(key=lambda item: item[0].get('overround', 1))
    relay_row = next((r for r, _ in relay_quotes), None)
    relay_stage = 'Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes)'
    if relay_quotes:
        quote, detail = relay_quotes[0]
        trail.append({'stage': relay_stage, 'status': 'resolved',
                      'source_url': quote['source_url'],
                      'detail': detail + ('' if not relay_reasons else
                                          ' Narrowest of ' + str(len(relay_quotes)) + ' relayed pairs.')})
        if quote.get('book_url'):
            # The bookmaker's own page is linked by bo3.gg's record; publishing it
            # lets a reader check the price at the source, which this project does
            # not read directly.
            trail.append({'stage': f"Bookmaker page named by bo3.gg ({quote['provider'].split(' (')[0]})",
                          'status': 'checked', 'source_url': quote['book_url'],
                          'detail': "bo3.gg's record links this bookmaker match page for the fixture. "
                                    'This dashboard did not read that page; the coefficients above are '
                                    "bo3.gg's copy of the provider's price."})
    elif relay_reasons:
        row, detail = relay_reasons[0]
        trail.append({'stage': relay_stage, 'status': 'unresolved',
                      'source_url': row.get('source_url') or 'https://bo3.gg/matches',
                      'detail': f"{row.get('provider') or 'Bookmaker'} via bo3.gg: {detail}"})
    else:
        trail.append({'stage': relay_stage, 'status': 'unresolved',
                      'source_url': 'https://bo3.gg/matches',
                      'detail': 'bo3.gg lists no fixture bound by both team names and the start time, or lists it '
                                'without a bookmaker quote block, so no relayed price exists for this fixture.'})

    # 3. Reviewed aggregated-bookmaker fallback (EGamersWorld averages).
    # Only for fixtures the entire first-party ladder left blank; never used to
    # outvote a first-party market or esportsbook quote. Identical prices are
    # rejected as placeholders, and the exact captured sentence is hash-checked.
    reference_quote = None
    reference_reason = 'No reviewed aggregated-bookmaker capture matches this fixture.'
    for entry in reference or []:
        candidate, reason = reference_odds.quote(entry, match, now)
        if candidate:
            reference_quote, reference_reason = candidate, reason
            break
        if str(entry.get('fixture_id')) == str(match.get('id')):
            reference_reason = reason
    reference_trail = {'stage': 'Aggregated bookmaker reference (EGamersWorld)',
                       'status': 'resolved' if reference_quote else 'unresolved',
                       'source_url': reference_quote['source_url'] if reference_quote else 'https://egamersworld.com/counterstrike/matches',
                       'detail': (reference_reason + ' Third-party aggregation, not a first-party bookmaker quote; '
                                  'used only when every first-party market and bookmaker check failed.')
                       if reference_quote else reference_reason}
    trail.append(reference_trail)

    # 4. Research model cross-check (always attempted, never overrides money lines).
    model, model_detail = model_estimate(match, ratings, registry, valve_meta or {}, now, lineup=match.get('_hltv_lineup'))
    if model:
        aliases.extend(model.get('aliases_used') or [])
        trail.append({'stage': 'Research model cross-check (Valve official ratings)', 'status': 'resolved',
                      'source_url': model['source_url'],
                      'detail': model_detail + ' Cross-check only unless no market or bookmaker line exists.'})
    else:
        trail.append({'stage': 'Research model cross-check (Valve official ratings)', 'status': 'unresolved',
                      'source_url': (valve_meta or {}).get('source_url', 'https://github.com/ValveSoftware/counter-strike_regional_standings'),
                      'detail': model_detail})
        # Lowest rung: our own results-based rating, only when one side has no
        # official row at all. Every input is an observed finished series on
        # bo3.gg; nothing is copied from a bookmaker or another model.
        if match.get('_form'):
            model = dict(match['_form'])
            model['evidence_file'] = (valve_meta or {}).get('evidence_file')
            model['snapshot_date'] = (valve_meta or {}).get('snapshot_date')
            model['observed_at'] = model.get('observed_at') or (valve_meta or {}).get('observed_at')
            model_detail = ('Own results-based fit from observed bo3.gg series results; '
                            f'{model.get("n_series")} anchored series, posterior SD '
                            f'{model.get("rating_sd")} points.')
            trail.append({'stage': 'Results model (own, bo3.gg series results)', 'status': 'resolved',
                          'source_url': model['source_url'], 'detail': model_detail})
        elif match.get('_form_reason'):
            trail.append({'stage': 'Results model (own, bo3.gg series results)', 'status': 'unresolved',
                          'source_url': 'https://bo3.gg/matches', 'detail': match['_form_reason']})
        # Own network model (session 541cd43a): a Bradley–Terry fit over the whole
        # bo3.gg results graph, expressed on Valve's official scale through
        # anchored teams. It is the only rung that can price a fixture whose
        # *both* sides are missing from every official rating table.
        if match.get('_network'):
            model = dict(match['_network'])
            model_detail = (f"Own Bradley–Terry network fit over {model.get('graph_matches')} bo3.gg finished "
                            f"series with {model.get('graph_anchors')} Valve-anchored teams; "
                            f"{model.get('n_series')} series for the thinner side, rating-difference SD "
                            f"{model.get('rating_sd_diff')} points.")
            trail.append({'stage': 'Own network model (bo3.gg results graph)', 'status': 'resolved',
                          'source_url': model['source_url'], 'detail': model_detail})
        elif match.get('_network_reason'):
            trail.append({'stage': 'Own network model (bo3.gg results graph)', 'status': 'unresolved',
                          'source_url': 'https://bo3.gg/matches', 'detail': match['_network_reason']})

    # 4b. HLTV world-ranking research model — same uncalibrated evidence class
    # as the Valve rung, but sourced from HLTV's official weekly ranking and
    # used only when the Valve rung has no row (which is exactly the low-tier
    # gap the brief asks to close). It never overrides money, reference or
    # Valve estimates.
    hltv_model, hltv_model_detail = hltv_ranking.estimate(match, hltv_rank or [], registry, now, meta=hltv_meta)
    if hltv_model:
        aliases.extend(hltv_model.get('aliases_used') or [])
        trail.append({'stage': 'Research model cross-check (HLTV world ranking)', 'status': 'resolved',
                      'source_url': hltv_model['source_url'],
                      'detail': hltv_model_detail + ' Cross-check only unless every money and Valve rung fails.'})
    else:
        trail.append({'stage': 'Research model cross-check (HLTV world ranking)', 'status': 'unresolved',
                      'source_url': (hltv_meta or {}).get('source_url', HLTV_RANKING_URL),
                      'detail': hltv_model_detail})

    for proof in (model or {}).get('lineup_disambiguation', []):
        overlap = proof.get('overlap', 5)
        if overlap == 5:
            stage = 'HLTV exact-five-player identity'
            detail = (f"{proof['team']}: five listed players exactly match Valve standing {proof['standing']} "
                      f"({', '.join(proof['roster'])}). This disambiguates a historical rating row, not final "
                      'match-day lineup confirmation or a form adjustment.')
        else:
            stage = 'HLTV four-of-five roster identity'
            detail = (f"{proof['team']}: four of five listed players match Valve standing {proof['standing']} "
                      f"({', '.join(proof['roster'])}); one current HLTV player differs. The selected row is a "
                      'historical rating, not a current-lineup rating or a quantified roster-change adjustment.')
        trail.insert(0, {'stage': stage, 'status': 'checked',
                         'source_url': proof['source_url'], 'detail': detail})

    # HLTV research stage (identity/rank context always recorded with its link).
    # Prefer the collector's own fixture-specific HLTV records (exact match page,
    # identity and published format) over a generic placeholder.
    hltv_records = [dict(r) for r in (hltv or []) if str(r.get('stage', '')).startswith('HLTV') and str(r.get('source_url', '')).startswith('https://www.hltv.org/')]
    if hltv_records:
        for record in reversed(hltv_records):
            # Session 4c972a51: keep the collector's observation time with the
            # HLTV identity record. Without it a reader cannot tell whether
            # "checked" means today's roster or a capture from a week ago.
            trail.insert(0, {k: record[k] for k in ('stage', 'status', 'source_url', 'detail', 'observed_at') if k in record})
    elif name_key(match.get('competition') or '') in {'elisa breakout series #2', 'elisa breakout series 2'}:
        trail.insert(0, {'stage': 'HLTV identity research', 'status': 'checked', 'source_url': HLTV_EVENT,
                         'detail': 'Event identity evidence is listed in the reviewed alias registry. HLTV fan votes are never probability inputs; current lineups remain unverified.'})
    else:
        trail.insert(0, {'stage': 'HLTV research', 'status': 'unresolved', 'source_url': 'https://www.hltv.org/matches',
                         'detail': 'See the featured pipeline research trail; no additional fixture-specific HLTV identity was verified by this fallback.'})

    # 5. Choose the originated line: consensus of money sources, else model.
    # One vote per independent provider (Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle).
    families = {}
    for quote, _ in estimates['market'] + estimates['bookmaker']:
        families.setdefault(quote['provider'], quote)
    chosen = None
    method = None
    label = None
    limitations = []
    # Last-resort rungs, in published order: Valve research model, HLTV
    # world-ranking research model, then — only if every rung above failed —
    # the narrowest observed wide-book midpoint as guidance-only output.
    guidance_candidates.sort(key=lambda item: item[0])
    guidance_spread, guidance_quote = (guidance_candidates[0] if guidance_candidates else (None, None))
    # Session f2b91672: a two-team HLTV world-ranking row outranks wide-book guidance,
    # and a one-ranked-team `unranked_floor` row still outranks unquoted placeholder
    # stubs (e.g. 0.04/0.96). However, when one side is unranked on HLTV (0.0-pt
    # synthetic floor) AND a real-money book posts a resting bid strictly above 50%
    # (`max(bid) > 0.5`), defer to the observed resting book rather than letting a
    # synthetic 0.0-point floor invert a priced favorite (e.g. 1082919 Tropa do KinGui
    # [4/5 ex-Keyd Stars Valve #144, unranked on HLTV] vs Martians [#240, 1.0 pt]).
    directional_guidance = bool(guidance_quote and max((guidance_quote.get('bid') or [0.0])) > 0.5)
    if families:
        probs_list = [q['probabilities'] for q in families.values()]
        p0 = median(pr[0] for pr in probs_list)
        probs = normalize_pair(p0, 1 - p0)
        sources = [q['provider'] for q in families.values()]
        thin = any(q.get('thin') for q in families.values())
        only = next(iter(families.values()))
        method = 'consensus' if len(families) > 1 else only['family']
        label = ('Originated consensus line (median of independent money sources)' if len(families) > 1
                 else (f'Originated market line ({only["provider"]})' if method == 'market'
                       else f'Originated esportsbook line ({only["provider"]}, no-vig)'))
        chosen = {'method': method, 'label': label, 'probabilities': probs,
                  'fair_decimal': [round(1 / p, 3) for p in probs],
                  'quotes': list(families.values()), 'source': ' + '.join(sources),
                  'source_url': list(families.values())[0]['source_url'],
                  'observed_at': min(q['observed_at'] for q in families.values()),
                  'model_crosscheck': model}
        if thin:
            limitations.append('At least one contributing market is thin/wide; treat the estimate as indicative, not executable.')
        if len(families) == 1:
            limitations.append('Single independent source; not a multi-source consensus.')
        limitations.append('Margin removed where applicable. Estimate is not a guaranteed outcome.')
    elif relay_quotes:
        # Session 15fc6bca: a named bookmaker's own two-sided price, read through
        # bo3.gg's relay. It outranks the aggregated third-party average and every
        # research model, and it is labelled as a relay wherever it is published.
        quote, detail = relay_quotes[0]
        chosen = dict(quote)
        chosen.update({'method': 'bookmaker',
                       'label': f"Esportsbook line relayed by bo3.gg ({quote['provider'].split(' (')[0]}, no-vig)",
                       'fair_decimal': [round(1 / p, 3) for p in quote['probabilities']],
                       'quotes': [quote], 'source': quote['provider'],
                       'model_crosscheck': model})
        limitations.append(
            'Bookmaker price relayed by bo3.gg, not read from the bookmaker\'s own page: bo3.gg publishes the '
            'coefficient pair it receives from the provider, and that page is linked on this row. Confirm the live '
            'price with the bookmaker before relying on it.')
        if quote.get('start_delta_sec'):
            limitations.append(
                f"bo3.gg's start time for this fixture differs from Hotspawn's by {quote['start_delta_sec']} seconds; "
                f'the join tolerance for a relayed price is {RELAY_START_TOLERANCE_SEC} seconds.')
    elif reference_quote:
        chosen = dict(reference_quote)
        chosen.update({'method': 'reference',
                       'label': 'Aggregated bookmaker average (EGamersWorld, no-vig)',
                       'fair_decimal': [round(1 / p, 3) for p in reference_quote['probabilities']],
                       'quotes': [reference_quote], 'source': 'EGamersWorld (bookmaker average)',
                       'model_crosscheck': model})
        limitations.append('Aggregated third-party bookmaker average, not a first-party bookmaker quote. '
                           'Dated observation; confirm the price before relying on it.')
    elif model:
        chosen = dict(model)
        results_model = model.get('family') == 'form'
        # Session fbdc97d6: the network rung is assigned to `model` above, so a
        # row priced by the bo3.gg results graph used to be labelled "Valve
        # official ratings" - a source the row never used. The label now follows
        # the rung that actually produced the number.
        chosen.update({'method': 'model',
                       'label': model_label(model),
                       'fair_decimal': [round(1 / p, 3) for p in model['probabilities']],
                       'quotes': [model],
                       'source': model.get('provider') or 'Valve official standings',
                       'model_crosscheck': None})
        if model.get('family') == 'network':
            limitations.append(network_limitation(model))
        elif results_model:
            limitations.append(
                'Own uncalibrated results model, not observed betting odds: a single rating was fitted to '
                f'{model.get("n_series")} finished series against officially rated opponents (posterior SD '
                f'{model.get("rating_sd")} points, one-sigma interval '
                f'{model.get("interval")[0]:.3f}-{model.get("interval")[1]:.3f}). '
                'The sample is small, opponent strength is taken from a dated official snapshot and '
                'current lineups, stand-ins and map vetoes are unverified.')
            if model.get('low_confidence'):
                limitations.append('Low confidence: the one-sigma interval or the sample size is wide. '
                                   'Treat the direction as indicative only.')
        else:
            limitations.append('Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified.')
        for proof in (chosen.get('lineup_disambiguation') or []):
            if proof.get('overlap', 5) < 5:
                limitations.append(f"{proof['team']}: the current HLTV lineup shares four of five players with the "
                                   'selected historical Valve row; the one-player change is not quantified.')
    elif network_quote:
        # Session 541cd43a: our own line from observed results, used only after
        # every money line, the aggregated reference and both official-rating
        # models have failed. It is a labelled research model, never odds.
        chosen = dict(network_quote)
        chosen.update({'method': 'model',
                       'label': 'Own network estimate (bo3.gg results graph)',
                       'fair_decimal': [round(1 / p, 3) for p in network_quote['probabilities']],
                       'quotes': [network_quote],
                       'source': 'Own network model (bo3.gg results graph)',
                       'model_crosscheck': model})
        limitations.append(
            'Own uncalibrated network model, not observed betting odds: no money line, no aggregated '
            'reference and no complete official rating row existed for this fixture. Both ratings come from '
            f"a Bradley–Terry fit over {network_quote.get('graph_matches')} finished bo3.gg series, anchored on "
            f"Valve's official points for {network_quote.get('graph_anchors')} teams; the rating-difference "
            f"one-sigma interval is {network_quote.get('rating_sd_diff')} points "
            f"(probability interval {network_quote['interval'][0]:.3f}-{network_quote['interval'][1]:.3f}). "
            'Current lineups, stand-ins and map vetoes are unverified.')
        if network_quote.get('low_confidence'):
            limitations.append('Low confidence: the interval crosses 50% or a side has fewer than ten '
                               'finished series. Treat the direction as indicative only.')
    elif hltv_model and not (hltv_model.get('unranked_floor') and directional_guidance):
        chosen = dict(hltv_model)
        floor = hltv_model.get('unranked_floor') or []
        chosen.update({'method': 'model',
                       'label': ('Research model estimate (HLTV world ranking · unranked floor)'
                                 if floor else 'Research model estimate (HLTV world ranking)'),
                       'fair_decimal': [round(1 / p, 3) for p in hltv_model['probabilities']],
                       'quotes': [hltv_model], 'source': 'HLTV world ranking',
                       'model_crosscheck': model})
        limitations.append('Research model, not observed betting odds. Uncalibrated HLTV ranking transform; '
                           'current lineups, stand-ins, form and map veto unverified.')
        if floor:
            limitations.append(
                f'Unranked floor: {", ".join(floor)} has no HLTV world-ranking row, so the model gives that '
                'side HLTV\'s floor of 0.0 published points. That is a stated assumption, not a measured '
                'rating — the estimate is low confidence and only says the ranked side is the stronger side '
                'on the published ranking. No market, esportsbook or Valve rating input resolved this fixture.')
    elif guidance_quote:
        chosen = dict(guidance_quote)
        trail.append({'stage': 'Wide-book guidance fallback', 'status': 'resolved',
                      'source_url': guidance_quote['source_url'],
                      'detail': f'The only observed two-sided book (spread {guidance_spread:.2f}, above every '
                                'published ceiling) is shown as guidance-only output after all compliant rungs '
                                'failed. This is not a validated price.'})
        chosen.update({'method': 'guidance',
                       'label': 'Wide-book indicative midpoint (guidance only)',
                       'fair_decimal': [round(1 / p, 3) for p in guidance_quote['probabilities']],
                       'quotes': [guidance_quote], 'source': guidance_quote['provider'],
                       'model_crosscheck': model})
        limitations.append(
            f'GUIDANCE ONLY — not a pick under the published book contract. The only observed two-sided book '
            f'has a spread of {guidance_spread:.2f}, far wider than the {MAX_ACCEPTED_SPREAD:.2f} acceptance '
            'ceiling, so the midpoint is barely a price. It is shown because the brief asks for a researched '
            'percentage even when no compliant source lists the match. Do not treat it as a validated line.')
        if hltv_model and hltv_model.get('unranked_floor'):
            limitations.append(
                f'HLTV unranked-floor model deferred: {", ".join(hltv_model["unranked_floor"])} has no HLTV '
                'world-ranking row (0.0-point synthetic floor), whereas an observed resting market bid exceeds '
                '50%. Real-money resting order-book bids take precedence over a synthetic 0.0-point floor.')
    else:
        trail.append({'stage': 'Origination result', 'status': 'unresolved',
                      'source_url': match.get('source_url') or POLY_INDEX,
                      'detail': 'No alias-verified market, bookmaker or rating input could be confirmed. The pick stays blank.'})
        limitations.append('No verified inputs; probabilities intentionally left blank (no default 50/50).')

    if relay_quotes and (chosen or {}).get('family') != RELAY_FAMILY:
        # A relayed price exists but a first-party quote, the aggregated
        # reference or a research model already resolved the fixture. Say so,
        # instead of showing the relay as the source of a number it did not set.
        for entry in trail:
            if entry.get('stage') == relay_stage and entry.get('status') == 'resolved':
                entry['status'] = 'not needed'
                entry['detail'] = ('A higher-ranked rung resolved this fixture, so the relayed price was not used. '
                                   + entry['detail'])
                break
    if reference_quote and (chosen or {}).get('method') != 'reference':
        # The capture exists but a first-party line won; say so instead of
        # presenting an unused fallback as a resolved source.
        reference_trail['status'] = 'not needed'
        reference_trail['detail'] = ('A first-party market or esportsbook quote resolved this fixture, so the '
                                     'aggregated reference was not used. ' + reference_trail['detail'])
    if time_flags:
        limitations.append('Provider start-time disagreement: ' + '; '.join(sorted(set(time_flags))) + '. Times are never silently overwritten.')
    pick = selection(chosen['probabilities']) if chosen else None
    if pick is None and chosen:
        # Session 4c972a51: an exactly even research estimate still gets a side
        # when the provider publishes an order for the two teams. The estimate
        # and its fair line are untouched; only the direction is decided.
        tie = ranked_tie_break(chosen)
        if tie:
            pick, tie_record = tie
            chosen['tie_break'] = tie_record
            limitations.append(tie_record['detail'])
            trail.append({'stage': 'Tie-break (published ranking order)', 'status': 'resolved',
                          'source_url': tie_record.get('source_url') or POLY_INDEX,
                          'detail': tie_record['detail']})
    deduped = []
    seen = set()
    for a in aliases:
        key = (a['alias'], a['canonical'])
        if key not in seen:
            seen.add(key)
            deduped.append(a)
    if deduped:
        # Make the identity basis explicit next to the HLTV record: a registry join is
        # competition-scoped and evidence-linked, unlike a same-slot observation.
        position = sum(1 for r in trail if str(r.get('stage', '')).startswith('HLTV'))
        evidence_url = next((ev['url'] for a in deduped for ev in a.get('evidence', []) if str(ev.get('url', '')).startswith('https://')),
                            'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/origination/aliases.json')
        trail.insert(position, {'stage': 'Identity join (verified alias registry)', 'status': 'resolved', 'source_url': evidence_url,
                                'detail': '; '.join(f"{a['alias']} → {a['canonical']}" for a in deduped)
                                + '. Competition-scoped registry entries with official evidence links; this supersedes any earlier '
                                  '"equivalence not verified" observation for these names in this competition only.'})
    return {
        'origination': chosen,
        'pick_index': pick,
        'aliases_used': deduped,
        'research': trail,
        'limitations': limitations,
        'time_flags': sorted(set(time_flags)),
    }


MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference'}


def resolve_match(match: dict, poly_rows: list, book_rows: list, ratings, valve_meta, registry: dict, now: datetime, *,
                  reference: list | None = None, hltv_rank: list | None = None,
                  hltv_meta: dict | None = None, relay: list | None = None) -> dict:
    """One fixture's origination row.

    Featured estimates from the exact-name collector are preserved unchanged, with two exceptions:
    (1) a featured *model* estimate is the lowest rung of the ladder, and the exact-name join can miss a market that
        exists under a provider's display name ("Aurora Gaming" for Aurora);
    (2) a featured equal-estimate tie (no directional pick) can occur when the exact-name collector hits an even
        esportsbook line while missing aliased markets or exchange order books.
    For such fixtures the alias-aware money research runs too. A verified money-backed line (or a directional
    money-backed line for a featured tie) replaces the featured estimate and the row says so. Without one, the featured
    estimate is kept exactly as it was.
    """
    featured = match.get('analysis')
    featured_pick = match.get('pick_index') if match.get('pick_index') is not None else (
        selection(featured.get('probabilities')) if featured else None)

    def keep_featured():
        return {'origination': dict(featured, quotes=[dict(q, source_url=q.get('source_url') or featured['source_url'], provider=q.get('provider') or featured['source'], family=q.get('family') or featured['method']) for q in featured.get('quotes', [])], model_crosscheck=None),
                      'pick_index': match.get('pick_index'), 'aliases_used': [],
                      'research': match.get('research', []), 'limitations': match.get('limitations', []), 'time_flags': []}

    if featured and featured.get('method') != 'model' and featured_pick is not None:
        return keep_featured()
    result = originate_match(match, poly_rows, book_rows, ratings, valve_meta, registry, now, hltv=match.get('research'),
                             reference=reference, hltv_rank=hltv_rank, hltv_meta=hltv_meta, relay=relay)
    if not featured:
        return result
    method = (result.get('origination') or {}).get('method')
    if featured.get('method') == 'model' and method in MONEY_METHODS:
        return dict(result, upgraded_from_featured_model=True)
    if featured_pick is None and method in MONEY_METHODS and result.get('pick_index') is not None:
        return dict(result, upgraded_from_featured_model=True)
    return keep_featured()


def run(output: Path, *, live: bool = False) -> dict:
    output = Path(output)
    orig_dir = output / 'origination'
    evidence_dir = orig_dir / 'evidence'
    registry = load_registry(orig_dir / 'aliases.json')
    now = datetime.now(UTC)
    snapshot = load_json(output / 'latest.json')
    live_payload = live_collect(evidence_dir, snapshot['matches'], registry) if live else None
    reference_capture = reference_odds.load(output)
    reference_rows = list(reference_capture.get('entries') or []) + list(reference_capture.get('rejected') or [])
    # Session arena-5260ef4e: the automated EGamersWorld index capture written by
    # every live refresh (`scripts/egw_live.py` -> `live-egw-reference.json`) had no
    # reader, so the rung it was added for priced nothing. It is replayed here, but
    # *after* the reviewed manual captures: a hand-checked price always outranks an
    # automated one. Both go through the same fail-closed gate in
    # `reference_odds.quote()` (fixture id + both names + 60 s start tolerance,
    # 8 h freshness, no-vig band, identical 1.8/1.8 placeholders refused).
    # BE integration: reparse the original response and bind actual fixture
    # identity/scoped registry before the canonical reviewed quote gate.
    egw_live_rows = egw_live.load_live(evidence_dir, snapshot['matches'], registry)
    reference_rows = reference_rows + egw_live_rows
    poly_rows = polymarket_rows(output, evidence_dir) + kalshi_rows(evidence_dir) + smarkets_lines.rows(evidence_dir)
    book_rows = thunderpick_rows(output, live_payload) + bovada_rows(evidence_dir) + pinnacle_rows(evidence_dir)
    ratings, valve_meta = valve_rows(output, live_payload)
    hltv_rank_rows, hltv_meta = hltv_ranking.load(evidence_dir)
    # Bookmaker prices bo3.gg relays (session 15fc6bca). Loaded from the dated
    # evidence document whether this run collected live or replayed; the ladder
    # validates freshness and the join before a single row can be priced.
    relay_rows = bo3_relay_rows(evidence_dir)
    # Preserve original source observation timestamps. Never stamp retained quotes as new.
    for row in poly_rows:
        if not row.get('observed_at'):
            event_id = row.get('event_id')
            row['observed_at'] = next((r.get('observed_at') for r in snapshot.get('requests', []) if r.get('id') == 'polymarket-event-' + str(event_id) and r.get('status') == 'ok'), None)

    matches_out = []
    form_bindings = form_model.load_bindings(evidence_dir)
    # Own-line network model (session 541cd43a). The graph is fitted once per run
    # and saved as dated evidence; the gate inside the model fails closed when the
    # graph is thin, unanchored, stale or too uncertain for a fixture.
    network_document = None
    network_error = None
    if live_payload and live_payload.get('bo3_graph'):
        try:
            network_document = network_model.build(live_payload['bo3_graph']['edges'], ratings or [], now, registry)
            network_model.save(network_document, evidence_dir)
        except Exception as exc:  # noqa: BLE001 - evidence outage, never a value
            network_error = f'{type(exc).__name__}: {exc}'[:200]
    elif live_payload and live_payload.get('bo3_graph_error'):
        network_error = 'Results graph unavailable this run: ' + str(live_payload['bo3_graph_error'])
    elif not live_payload:
        network_document = network_model.load(evidence_dir)
    for match in snapshot['matches']:
        if match.get('availability') == 'past':
            continue
        featured = match.get('analysis')
        proof = hltv_lineup_proof(evidence_dir, match, registry, now)
        form, form_reason = (form_model.estimate_fixture(match, form_bindings.get(str(match['id'])),
                                                         ratings, registry, now)
                             if ratings else (None, 'Official Valve ratings unavailable'))
        network, network_reason = network_model.estimate_fixture(
            match, form_bindings.get(str(match['id'])), network_document, now)
        if network is None and network_error and network_reason:
            network_reason = network_reason + ' (' + network_error + ')'
        result = resolve_match(dict(match, _hltv_lineup=proof, _form=form, _form_reason=form_reason,
                                    _network=network, _network_reason=network_reason),
                               poly_rows, book_rows, ratings, valve_meta, registry, now,
                               reference=reference_rows, hltv_rank=hltv_rank_rows, hltv_meta=hltv_meta,
                               relay=relay_rows)
        matches_out.append({
            'id': match['id'],
            'teams': match['teams'],
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'),
            'locks_at': match.get('locks_at'),
            'availability': match.get('availability'),
            'tier': match.get('tier'),
            'source_url': match.get('source_url'),
            'lobby_url': match.get('lobby_url'),
            'featured_method': featured.get('method') if featured else None,
            'featured_probabilities': featured.get('probabilities') if featured else None,
            'featured_pick_index': match.get('pick_index'),
            'featured_source_url': featured.get('source_url') if featured else None,
            **result,
        })
    matches_out.sort(key=lambda m: (m['starts_at'] or '9999', m['id']))

    unresolved = [m['id'] for m in matches_out if m['origination'] is None]
    counts = {
        'active': len(matches_out),
        'resolved': len(matches_out) - len(unresolved),
        'unresolved': len(unresolved),
        'with_pick': sum(m['pick_index'] is not None for m in matches_out),
        'consensus': sum((m['origination'] or {}).get('method') == 'consensus' for m in matches_out),
        'market': sum((m['origination'] or {}).get('method') == 'market' for m in matches_out),
        'bookmaker': sum((m['origination'] or {}).get('method') == 'bookmaker' for m in matches_out),
        'reference': sum((m['origination'] or {}).get('method') == 'reference' for m in matches_out),
        'model': sum((m['origination'] or {}).get('method') == 'model' for m in matches_out),
        'network': sum((m['origination'] or {}).get('family') == 'network' for m in matches_out),
        # Rows priced from the bookmaker quote bo3.gg relays: a subset of the
        # 'bookmaker' method, published separately so no reader mistakes a
        # second-hand copy for a first-party bookmaker observation.
        'relay': sum((m['origination'] or {}).get('family') == RELAY_FAMILY for m in matches_out),
        'guidance': sum((m['origination'] or {}).get('method') == 'guidance' for m in matches_out),
        'alias_joined': sum(bool(m['aliases_used']) for m in matches_out),
    }
    flags = []
    for m in matches_out:
        if m['origination'] is None:
            flags.append({'id': 'origination-unresolved-' + m['id'], 'severity': 'warning',
                          'title': 'Unresolved: ' + ' vs '.join(t['name'] or 'Unverified team' for t in m['teams']),
                          'detail': 'No alias-verified market, esportsbook or rating input was confirmed. Blank pick is intentional.',
                          'match_ids': [m['id']],
                          'source_urls': [m['source_url']] + [r['source_url'] for r in m['research']]})
        for note in m['time_flags']:
            flags.append({'id': 'start-time-' + m['id'], 'severity': 'notice',
                          'title': 'Provider start-time disagreement', 'detail': note,
                          'match_ids': [m['id']], 'source_urls': [m['source_url']]})
    reference_ids = [m['id'] for m in matches_out if (m['origination'] or {}).get('method') == 'reference']
    if reference_ids:
        flags.append({'id': 'aggregated-reference-lines', 'severity': 'notice',
                      'title': 'Aggregated third-party bookmaker averages used for otherwise unpriced fixtures',
                      'detail': 'These fixtures had no usable Polymarket, Kalshi, Thunderpick, Bovada or Valve-rating input. '
                                'Their estimates replay a dated EGamersWorld published bookmaker-average sentence (hash-checked) and are labelled '
                                'as an aggregation, not a first-party bookmaker quote. Confirm the live price before relying on one. '
                                'Identical prices and contradictory observations were rejected and the affected fixtures stay unresolved.',
                      'match_ids': reference_ids, 'source_urls': [REFERENCE_INDEX]})
    thin = [m['id'] for m in matches_out if any(q.get('thin') for q in (m['origination'] or {}).get('quotes', []) if isinstance(q, dict))]
    guidance_ids = [m['id'] for m in matches_out if (m['origination'] or {}).get('method') == 'guidance']
    if guidance_ids:
        flags.append({'id': 'wide-book-guidance-only', 'severity': 'warning',
                      'title': 'Wide-book indicative midpoints published as guidance only',
                      'detail': 'These fixtures had no compliant market, esportsbook, aggregated or research-model '
                                'input. Their displayed percentages are the midpoints of observed two-sided books '
                                'far wider than every published spread ceiling, labelled guidance only. They are '
                                'not validated picks and must never be treated as executable prices. See each '
                                "row's research trail for the exact spreads.",
                      'match_ids': guidance_ids, 'source_urls': [POLY_INDEX, KALSHI_PAGE.rstrip('/')]})
    relay_ids = [m['id'] for m in matches_out if (m['origination'] or {}).get('family') == RELAY_FAMILY]
    if relay_ids:
        flags.append({'id': 'relayed-bookmaker-lines', 'severity': 'notice',
                      'title': 'Bookmaker prices relayed by bo3.gg used where no first-party quote existed',
                      'detail': 'These fixtures had no usable first-party Polymarket, Kalshi, Thunderpick, Bovada or '
                                'Pinnacle quote. Their estimates replay the two-sided decimal coefficients bo3.gg '
                                'publishes for the fixture, naming the bookmaker and linking both the bo3.gg match '
                                'page the numbers were read from and the bookmaker page bo3.gg links to. The price is '
                                'a second-hand copy, not an observation of the bookmaker\'s own feed, and it is '
                                'never folded into a first-party consensus.',
                      'match_ids': relay_ids,
                      'source_urls': ['https://bo3.gg/matches', BO3_API + '/matches']})
    network_ids = [m['id'] for m in matches_out
                   if (m['origination'] or {}).get('family') == 'network']
    if network_ids:
        flags.append({'id': 'own-network-model-lines', 'severity': 'notice',
                      'title': 'Own network model used where no money line or official rating exists',
                      'detail': 'These fixtures had no usable Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle, '
                                'aggregated-reference, Valve or HLTV-ranking input. Their estimates come from a '
                                'Bradley–Terry fit over bo3.gg finished series anchored on Valve official points; '
                                'each row publishes its ratings, sample sizes, rating-difference standard error and '
                                'probability interval, and is a research model, not betting odds. Confirm the '
                                'current lineup and market before relying on one.',
                      'match_ids': network_ids, 'source_urls': ['https://bo3.gg/matches',
                                                                (valve_meta or {}).get('source_url', 'https://github.com/ValveSoftware/counter-strike_regional_standings')]})
    hltv_model_ids = [m['id'] for m in matches_out
                      if (m['origination'] or {}).get('method') == 'model'
                      and (m['origination'] or {}).get('source') == 'HLTV world ranking']
    if hltv_model_ids:
        flags.append({'id': 'hltv-ranking-model-lines', 'severity': 'notice',
                      'title': 'HLTV world-ranking research model used for otherwise unpriced fixtures',
                      'detail': 'These fixtures had no usable Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle, '
                                'aggregated-reference or Valve-rating input. Their estimates are the uncalibrated '
                                '400-scale logistic transform of HLTV\'s official weekly ranking points and are '
                                'labelled research models, not betting odds.',
                      'match_ids': hltv_model_ids, 'source_urls': [HLTV_RANKING_URL]})
    if thin:
        flags.append({'id': 'thin-markets', 'severity': 'notice',
                      'title': 'Thin/wide markets used as indicative inputs',
                      'detail': 'These estimates include at least one order book wider than 12 cents. Values are labeled indicative and must not be treated as executable prices.',
                      'match_ids': thin, 'source_urls': [POLY_INDEX]})
    flags.append({'id': 'alias-registry', 'severity': 'notice',
                  'title': 'Verified alias registry used for provider name joins',
                  'detail': f'{counts["alias_joined"]} active fixtures required a registry alias to join provider names. Every alias and its evidence links are published on the origination page and in data/origination/aliases.json.',
                  'match_ids': [], 'source_urls': [HLTV_EVENT, 'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/data/origination/aliases.json']})

    result = {
        'schema_version': 1,
        'generated_at': iso(now),
        'source_snapshot_at': snapshot.get('inventory_observed_at'),
        'source_generated_at': snapshot.get('generated_at'),
        'registry_updated_at': registry.get('updated_at'),
        'live_collection': bool(live),
        'collection': ({key: live_payload.get(key) for key in
                        ('bo3_results', 'bo3_results_error', 'bo3_relay', 'bo3_relay_error', 'valve', 'valve_error',
                         'vrs_mirror_error', 'thunderpick_error', 'egw_live', 'egw_live_error',
                         'polymarket_discovery')} if live_payload else None),
        # Session arena-5260ef4e: how many automated EGamersWorld rows this run
        # independently rebound to originals/fixtures/registry. Zero may be the
        # correct refusal of an unverified capture, not a wiring regression.
        'egw_live_replay': {'entries': len(egw_live_rows)},
        'network_collection': (None if not live_payload else {
            'graph_edges': len((live_payload.get('bo3_graph') or {}).get('edges') or []),
            'graph_pages': (live_payload.get('bo3_graph') or {}).get('pages'),
            'graph_rows_seen': (live_payload.get('bo3_graph') or {}).get('rows'),
            'graph_cutoff': (live_payload.get('bo3_graph') or {}).get('cutoff'),
            'rows_without_winner': (live_payload.get('bo3_graph') or {}).get('rows_without_winner'),
            'missing_winner_samples': (live_payload.get('bo3_graph') or {}).get('missing_winner_samples'),
            'graph_error': live_payload.get('bo3_graph_error'),
            'fit_matches': (network_document or {}).get('graph_matches'),
            'fit_teams': (network_document or {}).get('graph_teams'),
            'fit_anchors': len((network_document or {}).get('anchors') or {}),
            'fit_error': network_error,
        }),
        'research_discovery': (live_payload or {}).get('polymarket_discovery'),
        'counts': counts,
        'policy': {
            'hotspawn_votes_used': False,
            'fan_votes_used': False,
            'start_tolerance_sec': START_TOLERANCE_SEC,
            'thin_spread': THIN_SPREAD,
            'max_accepted_spread': MAX_ACCEPTED_SPREAD,
            'ladder': ['verified-alias Polymarket series-winner books', 'verified-alias Kalshi CS2 match-winner books',
                       'verified-alias Smarkets CS2 match-winner exchange books (session 46ade650; public documented API, '
                       'bid/ask midpoints, spread ceiling 0.15, flagged thin above 0.12)',
                       'verified-alias esportsbook paired prices (Thunderpick, Bovada, Pinnacle; no-vig)',
                       'bookmaker prices relayed by bo3.gg (session 15fc6bca; labelled second-hand copy, used only '
                       'when no first-party quote exists and never mixed into a first-party consensus)',
                       'median consensus across independent money providers',
                       'reviewed aggregated bookmaker average (EGamersWorld; labelled third-party aggregate, never overrides a first-party price)',
                       'Valve-rating research model fallback',
                       'own Bradley–Terry network model over bo3.gg results, anchored on Valve points '
                       '(session 541cd43a; prices fixtures where both sides lack an official row)',
                       'HLTV world-ranking research model fallback (session c03ef201)',
                       'wide-book indicative midpoint, guidance only (session c03ef201; never a validated pick)',
                       'blank + flagged'],
            'money_providers': ['Polymarket', 'Kalshi', 'Smarkets', 'Thunderpick', 'Bovada', 'Pinnacle'],
            'relay_providers': ['bo3.gg published bookmaker relay (provider named per fixture)'],
            'relay_start_tolerance_sec': RELAY_START_TOLERANCE_SEC,
            'aggregated_reference': ['EGamersWorld published bookmaker average (manual, dated, hash-checked capture)'],
        },
        'matches': matches_out,
        'unresolved_ids': unresolved,
        'flags': flags,
        'sources': [
            {'name': 'Hotspawn fixture inventory', 'url': snapshot.get('sources', [{}])[0].get('url', 'https://play.hotspawn.com/lobby') if snapshot.get('sources') else 'https://play.hotspawn.com/lobby', 'role': 'match list only; Hotspawn popularity is never a probability input'},
            {'name': 'Polymarket CS2', 'url': POLY_INDEX, 'role': 'series-winner order books (money source)'},
            {'name': 'Kalshi CS2 match markets', 'url': KALSHI_PAGE.rstrip('/'), 'api_url': KALSHI_EVENTS, 'docs': KALSHI_DOCS, 'role': 'CFTC-regulated exchange; paired yes bid/ask books (money source, 12-cent spread ceiling)'},
            {'name': 'Thunderpick esportsbook', 'url': THUNDERPICK_PAGE, 'api_url': THUNDERPICK_API, 'role': 'original paired prematch prices (money source)'},
            {'name': 'Bovada esportsbook', 'url': BOVADA_SITE, 'api_url': BOVADA_API, 'role': 'original paired prematch series moneylines (money source)'},
            {'name': 'Pinnacle esportsbook', 'url': PINNACLE_PAGE, 'api_url': PINNACLE_API,
             'role': 'public guest board two-way series moneylines (money source; period 0 only, specials rejected)'},
            {'name': 'bo3.gg relayed bookmaker quotes', 'url': 'https://bo3.gg/matches', 'api_url': BO3_API + '/matches',
             'role': 'second-hand two-sided bookmaker prices, labelled as a relay, used only when no first-party '
                     'quote exists (session 15fc6bca)'},
            {'name': 'HLTV.org', 'url': HLTV_EVENT, 'role': 'identity research and published ranks; fan votes never a probability input'},
            {'name': 'HLTV world ranking', 'url': HLTV_RANKING_URL,
             'role': 'uncalibrated ranking research-model fallback only (session c03ef201)'},
            {'name': 'EGamersWorld aggregated bookmaker average', 'url': REFERENCE_INDEX,
             'role': 'dated third-party bookmaker-average fallback for otherwise unpriced fixtures; never overrides a first-party price'},
            {'name': 'Valve official standings', 'url': (valve_meta or {}).get('source_url', 'https://github.com/ValveSoftware/counter-strike_regional_standings'), 'role': 'uncalibrated research-model fallback only'},
            {'name': 'bo3.gg finished-series results', 'url': 'https://bo3.gg/matches', 'api_url': BO3_API + '/matches',
             'role': 'own-line network model only (session 541cd43a); every rating links its series results, never a bookmaker price'},
        ],
        'alias_registry': registry,
    }
    (output / 'origination.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data'))
    parser.add_argument('--live', action='store_true', help='refetch first-party sources before resolving')
    args = parser.parse_args()
    result = run(args.output, live=args.live)
    print(json.dumps({'counts': result['counts'], 'unresolved': result['unresolved_ids'],
                      'generated_at': result['generated_at']}, indent=2))


if __name__ == '__main__':
    main()
