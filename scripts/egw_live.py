"""Fail-closed automated EGamersWorld reference capture.

The index remains useful for discovery, but its URL/team mentions alone are
not quote evidence. Promotion requires one unambiguous match anchor whose own
markup supplies a timezone-qualified ISO start and a decimal price immediately
associated with each exact outcome name. Never copy Hotspawn's time into provider
evidence or bind a first substring hit. When the index omits these facts it
produces no quote; the existing first-party and research-model rungs remain.

Original HTML is saved by originate.Client. Captures retain the literal anchor
excerpt and its hash; offline loading reparses that original response and refuses
old, forged or independently unbound derived entries. Existing reference_odds
freshness, margin, identical-placeholder and exact-start gates stay unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import iso, name_key, timestamp

UTC = timezone.utc
INDEX_URL = 'https://egamersworld.com/counterstrike/matches'
PROVIDER = 'EGamersWorld (published bookmaker average)'
EVIDENCE_NAME = 'live-egw-reference.json'
INDEX_EVIDENCE = 'live-egw-index'

_SLUG_CLEAN = re.compile(r'[^a-z0-9]+')
_ODDS_RE = re.compile(r'(?<![\d.])(\d{1,3}\.\d{1,2})(?![\d.])')
_ZONE = re.compile(r'(?:Z|[+-]\d{2}:\d{2})$', re.I)


def slugify(name: str) -> str:
    """EGamersWorld URL slug for a team name (lowercase, hyphen-separated)."""
    return _SLUG_CLEAN.sub('-', (name or '').casefold()).strip('-')


def _slug_keys(name: str) -> set[str]:
    slug = slugify(name)
    return {slug, slug.replace('-', '')} if slug else set()


def _source_start(anchor) -> str | None:
    clocks = set()
    for node in anchor.select('time[datetime]'):
        value = node.get('datetime') or ''
        # Naive/local clocks are unverified; no guessed timezone is permitted.
        parsed = timestamp(value) if _ZONE.search(value) else None
        if parsed is None:
            return None
        clocks.add(iso(parsed))
    return next(iter(clocks)) if len(clocks) == 1 else None


def _literal_anchor(html: str, anchor) -> str | None:
    if anchor.sourceline is None or anchor.sourcepos is None:
        return None
    lines = html.splitlines(keepends=True)
    start = sum(map(len, lines[:anchor.sourceline - 1])) + anchor.sourcepos
    closing = re.search(r'</a\s*>', html[start:], re.I)
    if closing is None:
        return None
    excerpt = html[start:start + closing.end()]
    # Invalid/nested anchors cannot establish a single outcome/quote block.
    if len(re.findall(r'<a(?:\s|>)', excerpt, re.I)) != 1:
        return None
    return excerpt


def parse_index(html: str) -> list[dict]:
    """Retain two-price discovery anchors, including unverified-time leads.

    All qualifying observations are retained. Duplicate/conflicting events are
    checked at binding time, not silently hidden by a first-URL-wins scan.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or '', 'html.parser')
    out = []
    for anchor in soup.select('a[href*="/counterstrike/match/"]'):
        href = anchor.get('href') or ''
        if href.startswith('/counterstrike/match/'):
            href = 'https://egamersworld.com' + href
        if not href.startswith('https://egamersworld.com/counterstrike/match/'):
            continue
        slug = href.rstrip('/').rsplit('/', 1)[-1]
        text = anchor.get_text(' ', strip=True)
        odds = [float(x) for x in _ODDS_RE.findall(text)]
        if not slug or len(odds) != 2:
            continue
        out.append({'url': href, 'slug': slug, 'odds': odds, 'text': text,
                    'starts_at': _source_start(anchor),
                    'excerpt': _literal_anchor(html, anchor)})
    return out


def _named_price(text: str, names: list[str]) -> tuple[str, float] | None:
    found = {}
    for name in names:
        if not name:
            continue
        # A price must follow the complete displayed name, not a substring of
        # an academy/sister team, or an unlabelled positional price list.
        pattern = r'(?<![\w])' + re.escape(name) + r'\s+(' + _ODDS_RE.pattern + r')(?![\w.])'
        for match in re.finditer(pattern, text, re.I):
            found[match.span()] = (match.group(0)[:match.group(0).rfind(match.group(1))].strip(),
                                   float(match.group(1)))
    return next(iter(found.values())) if len(found) == 1 else None


def entries_for(html: str, matches: list, registry: dict, observed_at: str) -> list[dict]:
    """Bind exact named prices and an independently published source start.

    No UTC source clock, ambiguous event or unassociated prices => no entry.
    The provider time is preserved, never filled from the Hotspawn fixture.
    """
    from scripts.originate import resolve_name  # local: avoids a module cycle

    rows = parse_index(html)
    entries = []
    for match in matches or []:
        teams = [t.get('name') or '' for t in match.get('teams') or []]
        start = timestamp(match.get('starts_at'))
        if len(teams) != 2 or len({name_key(n) for n in teams}) != 2 or start is None:
            continue
        names = []
        for team in teams:
            canonical, _ = resolve_name(team, registry, match.get('competition'))
            names.append(list(dict.fromkeys([team, canonical])))
        candidates = {}
        for row in rows:
            # The reviewed reference gate is exact to the second. Keep that
            # stronger rule instead of manufacturing the fixture's timestamp.
            if not row['excerpt'] or timestamp(row['starts_at']) != start:
                continue
            paired = [_named_price(row['text'], side) for side in names]
            if any(p is None for p in paired):
                continue
            provider_names = [p[0] for p in paired]
            odds = [p[1] for p in paired]
            slugs = [slugify(n) for n in provider_names]
            if not any(row['slug'].startswith(slugs[i] + '-vs-' + slugs[1-i] + '-')
                       for i in (0, 1)):
                continue
            # Both displayed outcome-price associations must account for the
            # two prices on the source; URL order is never used to infer odds.
            if sorted(odds) != sorted(row['odds']):
                continue
            positions = [row['text'].casefold().find(n.casefold()) for n in provider_names]
            order = sorted(range(2), key=lambda i: positions[i])
            signature = (row['url'], row['starts_at'], tuple(odds))
            candidates[signature] = (row, provider_names, odds, order)
        if len(candidates) != 1:
            continue
        row, provider_names, odds, order = next(iter(candidates.values()))
        excerpt = row['excerpt']
        entries.append({
            'fixture_id': str(match['id']), 'teams': teams,
            'provider_teams': [provider_names[i] for i in order],
            'starts_at': row['starts_at'], 'odds': odds,
            'source_url': row['url'], 'source_index_url': INDEX_URL,
            'observed_at': observed_at, 'excerpt': excerpt,
            'excerpt_sha256': hashlib.sha256(excerpt.encode('utf-8')).hexdigest(),
            'provider': PROVIDER,
            'capture': 'automated EGW source-clock and named-price capture',
        })
    return entries


def load_live(evidence_dir: Path, matches: list | None = None,
              registry: dict | None = None) -> list[dict]:
    """Replay original HTML; derived-only or tampered captures price nothing."""
    root = Path(evidence_dir)
    try:
        data = json.loads((root / EVIDENCE_NAME).read_text())
        original = json.loads((root / (INDEX_EVIDENCE + '.json')).read_text())
        if (not isinstance(data, dict) or not isinstance(original, dict)
                or original.get('url') != INDEX_URL or data.get('url') != INDEX_URL
                or not original.get('observed_at')
                or original['observed_at'] != data.get('observed_at')
                or not isinstance(original.get('html'), str)):
            return []
        replayed = entries_for(original['html'], matches or [], registry or {}, original['observed_at'])
        saved = data.get('entries')
        if not isinstance(saved, list):
            return []
        return [entry for entry in replayed if entry in saved]
    except (OSError, ValueError, TypeError, KeyError):
        return []
