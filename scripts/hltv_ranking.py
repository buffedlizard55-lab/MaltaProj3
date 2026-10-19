"""HLTV world-ranking research model — last-resort ranking-based estimate.

Why this exists
---------------
The brief asks for a pick for every Hotspawn CS2 match, and says HLTV may be
used to originate our own lines when no market or sportsbook covers a match.
The money ladder (Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle), the
reviewed aggregated reference and the Valve-rating model all require sources
that low-tier fixtures simply do not have. HLTV's official weekly world ranking
covers far more of the scene, including many academy and low-tier sides that
never appear in Valve's regional standings.

What this is
------------
A clearly labelled, uncalibrated research model — the same evidence class as
the Valve-rating rung, and the last rung before a fixture is published as
unresolved:

* inputs are team rows from HLTV's own published weekly ranking pages
  (``https://www.hltv.org/ranking/...``), each row carrying its page URL;
* both teams must appear on the **same dated publication** (the ranking pages
  fetched in one collection pass), with exact or reviewed-alias names only;
* the published HLTV points go through the same 400-scale logistic transform
  the Valve rung uses (Valve's ``fit.js`` expectation with g = 1, since HLTV
  publishes no rating deviation): ``p = 1 / (1 + 10 ** ((pts_b - pts_a) / 400))``
  for team A, then proportional normalization;
* the publication must be no older than 14 days (HLTV republishes weekly).

What this is not
----------------
It is not betting odds, not a calibrated probability, and it never overrides a
market, esportsbook, aggregated or Valve-model estimate. It does not confirm
today's lineup, stand-ins, form or map veto. Every published value links the
exact HLTV ranking page it was read from.

Usage:  from scripts import hltv_ranking
        rows, meta = hltv_ranking.load(Path('data/origination/evidence'))
        quote, detail = hltv_ranking.estimate(match, rows, registry, now, meta=meta)
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import is_fresh, name_key, normalize_pair, timestamp

UTC = timezone.utc
RANKING_URL = 'https://www.hltv.org/ranking/teams'
MAX_RANKING_AGE_DAYS = 14  # HLTV republishes the world ranking weekly.
POINTS_SCALE = 400.0       # Same logistic scale as the Valve fit.js expectation.


def parse_ranking_page(text: str) -> list:
    """Official HLTV world-ranking rows: team name, published points, team link.

    One ``.ranked-team`` block per team with a ``.points`` value such as
    "754 points". Ranks are the sequential page position; the caller adds the
    page offset. Anything missing a name or a parseable points value is
    skipped, never filled in.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, 'html.parser')
    rows = []
    for block in soup.select('.ranked-team'):
        name = block.select_one('.ranked-team-header .name') or block.select_one('.name')
        points = block.select_one('.points')
        team_link = block.select_one('a[href*="/team/"]')
        if not name or not points:
            continue
        m = re.search(r'(-?\d+(?:\.\d+)?)', points.get_text(' ', strip=True))
        if not m:
            continue
        href = (team_link.get('href') if team_link else '') or ''
        rows.append({
            'team': name.get_text(' ', strip=True),
            'points': float(m.group(1)),
            'team_url': ('https://www.hltv.org' + href.split('?')[0])
                        if href.startswith('/team/') else None,
        })
    return rows


def load(evidence_dir: Path) -> tuple[list, dict | None]:
    """Load the saved ranking capture written by live_collect.

    Returns (rows, meta). A missing or malformed capture yields ([], None) and
    the rung simply stays unresolved — never fatal, never fabricated.
    """
    path = evidence_dir / 'live-hltv-ranking.json'
    if not path.exists():
        return [], None
    try:
        saved = json.loads(path.read_text())
    except (OSError, ValueError):
        return [], None
    if not isinstance(saved, dict) or not isinstance(saved.get('pages'), list):
        return [], None
    rows, seen = [], set()
    for page in saved['pages']:
        if not isinstance(page, dict) or page.get('status') != 'ok':
            continue
        for row in page.get('rows') or []:
            if not isinstance(row, dict) or not row.get('team') or row.get('points') is None:
                continue
            key = name_key(row['team'])
            if key in seen:
                continue
            seen.add(key)
            rows.append({'name': row['team'], 'points': float(row['points']),
                         'rank': row.get('rank'), 'source_url': page.get('url'),
                         'snapshot_date': saved.get('snapshot_date')})
    meta = {'source_url': saved.get('source_url') or RANKING_URL,
            'snapshot_date': saved.get('snapshot_date'),
            'observed_at': saved.get('observed_at'),
            'evidence_file': 'data/origination/evidence/live-hltv-ranking.json',
            'publication_pages': len(saved['pages'])}
    return rows, meta


def estimate(match: dict, rows: list, registry: dict, now: datetime, *, meta: dict | None = None):
    """Alias-aware HLTV-ranking research estimate (explicitly uncalibrated).

    Mirrors model_estimate()'s contract: returns (quote, detail) or (None, reason).
    """
    if not rows:
        return None, 'No official HLTV world-ranking capture is available'
    meta = meta or {}
    observed = timestamp(meta.get('observed_at'))
    day = timestamp((meta.get('snapshot_date') or '') + 'T00:00:00Z') if meta.get('snapshot_date') else None
    if day is None and observed is not None:
        day = observed
    if day is None:
        return None, 'HLTV ranking publication date is unverified'
    if (now - day).total_seconds() < -86400 or (now - day).total_seconds() > MAX_RANKING_AGE_DAYS * 86400:
        return None, f'HLTV ranking publication is future-dated or older than {MAX_RANKING_AGE_DAYS} days'
    by_name = {}
    for row in rows:
        by_name.setdefault(name_key(row['name']), []).append(row)
    reverse = {}
    # Competition-scoped alias filtering, same rule as scripts/originate.py's
    # resolve_name/scoped_aliases (inlined to avoid a module cycle).
    if match.get('competition') is None:
        pool = (registry or {}).get('aliases', [])
    else:
        competition_key = name_key(match.get('competition'))
        pool = [e for e in (registry or {}).get('aliases', [])
                if competition_key in {name_key(s) for s in e.get('applies_to', [])}]
    for entry in pool:
        reverse.setdefault(name_key(entry['canonical']), []).append(name_key(entry['alias']))
    inputs = []
    for team in match['teams']:
        team_key = name_key(team['name'])
        candidates = [team_key] + reverse.get(team_key, [])
        found, matched_as = [], None
        for candidate in candidates:
            found = by_name.get(candidate) or []
            if found:
                matched_as = candidate
                break
        if not found:
            return None, f'{team["name"]}: no HLTV world-ranking entry found (including registry aliases)'
        if len(found) != 1:
            return None, f'{team["name"]}: multiple HLTV ranking rows share this name; ambiguous'
        row = dict(found[0])
        row['matched_as'] = matched_as
        inputs.append(row)
    pa = 1 / (1 + 10 ** ((inputs[1]['points'] - inputs[0]['points']) / POINTS_SCALE))
    probs = normalize_pair(pa, 1 - pa)
    alias_used = []
    for row, team in zip(inputs, match['teams']):
        if name_key(row['name']) != name_key(team['name']):
            alias_used.append({'alias': row['name'], 'canonical': team['name'],
                               'kind': 'registry reverse lookup',
                               'evidence': [{'url': row.get('source_url') or meta['source_url'],
                                             'source': 'HLTV world ranking',
                                             'detail': f'HLTV publishes this team under the name {row["name"]}; '
                                                       'the reviewed alias registry links the two names.'}]})
    quote = {
        'provider': 'HLTV world ranking', 'family': 'model', 'probabilities': probs,
        'inputs': [{'name': r['name'], 'points': r['points'], 'rank': r.get('rank'),
                    'matched_as': r.get('matched_as'),
                    'snapshot_date': r.get('snapshot_date') or meta.get('snapshot_date'),
                    'source_url': r.get('source_url') or meta['source_url']} for r in inputs],
        'snapshot_date': meta.get('snapshot_date'), 'source_url': meta['source_url'],
        'evidence_file': meta.get('evidence_file'), 'observed_at': meta.get('observed_at'),
        'points_scale': POINTS_SCALE,
        'aliases_used': alias_used,
        'evaluation_at': now.replace(microsecond=0).isoformat(),
    }
    detail = ('Alias-aware exact-name HLTV world-ranking rows; uncalibrated research model '
              '(400-scale logistic transform of the published HLTV points). Team-level ranking '
              'only: lineups, stand-ins, form and map veto are not confirmed.')
    return quote, detail
