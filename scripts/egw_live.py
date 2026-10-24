"""Automated EGamersWorld aggregated-line capture (session arena-43110640).

Why this exists
---------------
The brief asks for a pick for *every* Hotspawn CS2 match, including low-tier
fixtures no first-party market prices. The ladder already tries, in order:
Polymarket/Kalshi/Smarkets exchanges, Thunderpick/Bovada/Pinnacle esportsbooks,
bo3.gg-relayed bookmaker prices, the reviewed EGamersWorld aggregated reference,
then Valve/HLTV research models. Until now the EGamersWorld rung depended on
*manually reviewed* capture files (`data/research/*/reference-odds.json`), so
it went stale eight hours after a human last looked and low-tier fixtures fell
back to models or stayed unresolved.

This module automates that rung with the same fail-closed contract:

* the source is EGamersWorld's own CS2 matches index
  (``https://egamersworld.com/counterstrike/matches``), fetched live by the
  origination collector and saved verbatim as evidence
  (``live-egw-index.json``), so every derived entry replays offline;
* an entry is produced only when the index links a match page whose URL slug
  names *both* teams of an active Hotspawn fixture (exact normalised names,
  or the reviewed competition-scoped alias registry — never fuzzy matching)
  and the listing prints exactly two decimal odds for that match;
* entries are written in the reviewed ``reference_odds`` schema (fixture id,
  both team orders, published start, hash-checked verbatim excerpt), so the
  existing ``reference_odds.quote()`` gate decides: identical prices
  (EGamersWorld's 1.8/1.8 placeholder banner) are rejected, the start time
  must match to the second, and the observation must be under eight hours old;
* it remains an *aggregated third-party reference*, labelled as such, and it
  never overrides a first-party market or esportsbook line (enforced by the
  ladder order in ``originate_match``, unchanged).

Start-time note: the index does not print a UTC instant per match, so the
entry's ``starts_at`` is taken from the Hotspawn fixture itself and the
excerpt says so. The identity proof is the two team names in EGamersWorld's
own match-page URL plus the fixture id; ``reference_odds.quote()`` still
rejects the entry if the fixture's start ever differs from the recorded one.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import name_key

UTC = timezone.utc
INDEX_URL = 'https://egamersworld.com/counterstrike/matches'
PROVIDER = 'EGamersWorld (published bookmaker average)'
EVIDENCE_NAME = 'live-egw-reference.json'
INDEX_EVIDENCE = 'live-egw-index'

_SLUG_CLEAN = re.compile(r'[^a-z0-9]+')
_ODDS_RE = re.compile(r'(?<![\d.])(\d{1,3}\.\d{1,2})(?![\d.])')


def slugify(name: str) -> str:
    """EGamersWorld URL slug for a team name (lowercase, hyphen-separated)."""
    return _SLUG_CLEAN.sub('-', (name or '').casefold()).strip('-')


def _slug_keys(name: str) -> set[str]:
    slug = slugify(name)
    return {slug, slug.replace('-', '')} if slug else set()


def parse_index(html: str) -> list[dict]:
    """Match-page links on the EGW CS2 index, each with its printed odds pair.

    Returns [{'url', 'slug', 'teams_slug', 'odds'}]. An anchor qualifies only
    when its href is an EGW counterstrike match page and the anchor's own
    text (which EGW renders as the two team names) yields exactly two decimal
    odds. Anything else is skipped, never repaired.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or '', 'html.parser')
    out, seen = [], set()
    for anchor in soup.select('a[href*="/counterstrike/match/"]'):
        href = anchor.get('href') or ''
        if not href.startswith('https://egamersworld.com/counterstrike/match/'):
            continue
        slug = href.rstrip('/').rsplit('/', 1)[-1]
        if not slug or href in seen:
            continue
        text = anchor.get_text(' ', strip=True)
        odds = [float(x) for x in _ODDS_RE.findall(text)]
        if len(odds) != 2:
            continue
        seen.add(href)
        out.append({'url': href, 'slug': slug, 'odds': odds})
    return out


def entries_for(html: str, matches: list, registry: dict, observed_at: str) -> list[dict]:
    """Reviewed-schema reference entries joining the EGW index to fixtures.

    A fixture joins only when one match-page slug contains the slugs of both
    of its teams (in either order; odds are re-ordered to Hotspawn's order and
    the provider's printed order is kept in ``provider_teams``). Alias-registry
    names are tried for the slug search and recorded when used.
    """
    from scripts.originate import resolve_name  # local: avoids a module cycle

    rows = parse_index(html)
    entries = []
    for match in matches or []:
        teams = [t.get('name') or '' for t in match.get('teams') or []]
        if len(teams) != 2 or not match.get('starts_at'):
            continue
        candidates = []  # (display name used for the slug, canonical team)
        for team in teams:
            canonical, _ = resolve_name(team, registry, match.get('competition'))
            candidates.append((canonical, team))
        hit = None
        for row in rows:
            slug_flat = row['slug'].replace('-', '')
            positions = []
            for display, _team in candidates:
                pos = next((slug_flat.find(k.replace('-', ''))
                            for k in _slug_keys(display)
                            if k.replace('-', '') in slug_flat), -1)
                positions.append(pos)
            if all(p >= 0 for p in positions) and positions[0] != positions[1]:
                hit = (row, positions)
                break
        if hit is None:
            continue
        row, positions = hit
        provider_order = [0, 1] if positions[0] < positions[1] else [1, 0]
        provider_teams = [candidates[i][0] for i in provider_order]
        odds = row['odds'] if provider_order == [0, 1] else [row['odds'][1], row['odds'][0]]
        excerpt = (f"EGamersWorld CS2 matches index ({INDEX_URL}) lists "
                   f"{provider_teams[0]} vs {provider_teams[1]} at decimal odds "
                   f"{row['odds'][0]:g} / {row['odds'][1]:g} (automated capture "
                   f"{observed_at}; odds re-ordered to Hotspawn team order where "
                   f"the listing order differs).")
        entries.append({
            'fixture_id': str(match['id']),
            'teams': teams,
            'provider_teams': provider_teams,
            'starts_at': match['starts_at'],
            'odds': odds,
            'source_url': row['url'],
            'observed_at': observed_at,
            'excerpt': excerpt,
            'excerpt_sha256': hashlib.sha256(excerpt.encode('utf-8')).hexdigest(),
            'provider': PROVIDER,
            'capture': 'automated EGW index capture (scripts/egw_live.py)',
        })
    return entries


def load_live(evidence_dir: Path) -> list[dict]:
    """Replay entries from the saved live capture; missing/malformed is inert."""
    path = Path(evidence_dir) / EVIDENCE_NAME
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    return [e for e in data.get('entries') or [] if isinstance(e, dict)]
