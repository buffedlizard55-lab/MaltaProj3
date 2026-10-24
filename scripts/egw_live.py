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
* an entry is produced only when a match link's own ``Title VS Title`` label
  resolves to both Hotspawn teams by exact normalized names or the reviewed
  competition-scoped alias registry. URL substrings are not identity evidence;
* the listing prints exactly two decimal odds and supplies an independent
  machine-readable start timestamp with an explicit ``Z`` or numeric offset.
  Hotspawn's start is never copied into provider evidence. Missing/naive times
  and same-team rematches with another provider start price nothing;
* entries are written in the reviewed ``reference_odds`` schema (fixture id,
  both team orders, provider start, hash-checked excerpt), so the existing
  ``reference_odds.quote()`` gate still rejects placeholders, stale evidence,
  identity drift and start mismatches;
* it remains an *aggregated third-party reference*, labelled as such, and it
  never overrides a first-party market or esportsbook line (enforced by the
  ladder order in ``originate_match``, unchanged).

The human-readable EGW title/body can present different timezone representations
without naming a zone in the title. Those strings are deliberately not guessed.
Only an explicit machine-readable timestamp is accepted.
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
_TIME_ATTRIBUTES = ('datetime', 'data-datetime', 'data-start', 'data-starts-at', 'data-start-time')


def slugify(name: str) -> str:
    """Retained for slug diagnostics; never sufficient as a team join."""
    return _SLUG_CLEAN.sub('-', (name or '').casefold()).strip('-')


def _title_teams(anchor) -> list[str] | None:
    """Read the provider's exact two-team link title, never a slug substring."""
    title = (anchor.get('title') or '').strip()
    parts = [part.strip() for part in re.split(r'\s+[Vv][Ss]\s+', title, maxsplit=1)]
    if len(parts) != 2 or not all(parts) or name_key(parts[0]) == name_key(parts[1]):
        return None
    return parts


def _explicit_start(anchor) -> str | None:
    """Return a provider timestamp only when its timezone is explicit."""
    for node in (anchor, *anchor.find_all(True)):
        for attribute in _TIME_ATTRIBUTES:
            raw = node.get(attribute)
            if not isinstance(raw, str) or not raw.strip():
                continue
            value = raw.strip()
            try:
                moment = datetime.fromisoformat(value[:-1] + '+00:00'
                                                if value.endswith('Z') else value)
            except ValueError:
                continue
            if moment.tzinfo is None or moment.utcoffset() is None:
                continue
            return moment.astimezone(UTC).isoformat().replace('+00:00', 'Z')
    return None


def parse_index(html: str) -> list[dict]:
    """Parse exact team titles, two odds and any explicit provider start.

    Returns dictionaries with ``url``, ``slug``, ``provider_teams``, ``odds``
    and ``starts_at``. ``starts_at`` is None when the provider has no explicit
    timezone-bearing machine timestamp; ``entries_for`` rejects that row.
    Anything with missing/ambiguous team labels or odds is skipped, never
    repaired from another fixture.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or '', 'html.parser')
    out, seen = [], set()
    for anchor in soup.select('a[href*="/counterstrike/match/"]'):
        href = anchor.get('href') or ''
        if href.startswith('/counterstrike/match/'):
            href = 'https://egamersworld.com' + href
        if not href.startswith('https://egamersworld.com/counterstrike/match/'):
            continue
        slug = href.rstrip('/').rsplit('/', 1)[-1]
        if not slug or href in seen:
            continue
        provider_teams = _title_teams(anchor)
        if provider_teams is None:
            continue
        text = anchor.get_text(' ', strip=True)
        odds = [float(x) for x in _ODDS_RE.findall(text)]
        if len(odds) != 2:
            continue
        seen.add(href)
        out.append({'url': href, 'slug': slug, 'provider_teams': provider_teams,
                    'odds': odds, 'starts_at': _explicit_start(anchor)})
    return out


def entries_for(html: str, matches: list, registry: dict, observed_at: str) -> list[dict]:
    """Build reviewed-schema entries only for exact identity and provider time.

    The provider's two title names are independently resolved through the same
    competition-scoped alias registry as other sources. Odds are reordered to
    Hotspawn's team order only after that exact two-team join. The provider's
    own timestamp is retained so ``reference_odds.quote()`` can reject a
    same-team rematch or schedule mismatch; no timestamp is copied from the
    Hotspawn row.
    """
    from scripts.originate import resolve_name  # local: avoids a module cycle

    rows = parse_index(html)
    entries = []
    for match in matches or []:
        teams = [t.get('name') or '' for t in match.get('teams') or []]
        wanted = [name_key(team) for team in teams]
        if len(teams) != 2 or len(set(wanted)) != 2 or not match.get('starts_at'):
            continue
        for row in rows:
            provider_start = row.get('starts_at')
            if not provider_start:
                continue
            provider_names = row['provider_teams']
            canonical, aliases_used = [], []
            for name in provider_names:
                resolved, used = resolve_name(name, registry, match.get('competition'))
                canonical.append(resolved)
                aliases_used.extend(used)
            if len(set(canonical)) != 2 or set(canonical) != set(wanted):
                continue
            hotspawn_order = [canonical.index(wanted[0]), canonical.index(wanted[1])]
            odds = [row['odds'][hotspawn_order[0]], row['odds'][hotspawn_order[1]]]
            excerpt = (f"EGamersWorld CS2 matches index ({INDEX_URL}) lists "
                       f"{provider_names[0]} vs {provider_names[1]} at decimal odds "
                       f"{row['odds'][0]:g} / {row['odds'][1]:g}, provider start "
                       f"{provider_start} (automated capture {observed_at}; exact "
                       "title/alias identity; odds re-ordered to Hotspawn team order "
                       "where the listing order differs).")
            entries.append({
                'fixture_id': str(match['id']),
                'teams': teams,
                'provider_teams': provider_names,
                'starts_at': provider_start,
                'odds': odds,
                'source_url': row['url'],
                'observed_at': observed_at,
                'excerpt': excerpt,
                'excerpt_sha256': hashlib.sha256(excerpt.encode('utf-8')).hexdigest(),
                'provider': PROVIDER,
                'capture': 'automated EGW index capture (scripts/egw_live.py)',
                'aliases_used': aliases_used,
            })
            break
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
