"""Reviewed aggregated-bookmaker fallback for fixtures the first-party ladder cannot price.

The primary ladder (Polymarket, Kalshi, Thunderpick, Bovada, then the Valve
rating model) leaves some low-tier fixtures blank because no first-party
bookmaker quote is reachable.  This module adds one deliberately narrow rung:
a *dated, manually reviewed* capture of EGamersWorld's published
"average odds" sentence, which EGamersWorld describes as the average price
across leading bookmakers.

It is an aggregation, not a first-party bookmaker quote.  Every rule is
fail-closed:

* join by the Hotspawn fixture id **and** exact normalised team names **and**
  the published start time (60-second tolerance, the project-wide rule);
* two decimal odds greater than 1.01 and a paired margin inside
  ``domain.no_vig``'s 0.85-1.35 acceptance band;
* identical prices on both sides are rejected as site placeholders (the two
  VOID Autumn Cup pages display exactly 1.8/1.8 and carry no bookmaker-average
  sentence, which is why they stay unresolved);
* the observation must be fresh (``domain.is_fresh``, eight hours);
* the exact sentence captured from the page is stored with a SHA-256 so the
  quote can be replayed and proved unchanged.

The quote is labelled ``family='reference'`` and never replaces a first-party
market or esportsbook price.  It may replace an uncalibrated model estimate,
which is the same rule the first-party money lines follow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import (MAX_PRICE_AGE_HOURS, identity_matches, is_fresh, name_key,
                            no_vig, timestamp)

UTC = timezone.utc
EVIDENCE_PATH = Path('research/57b1ee04/reference-odds.json')
LIVE_EVIDENCE_PATH = Path('origination/evidence/live-egw-reference.json')
CAPTURE_PATHS = (
    EVIDENCE_PATH,
    Path('research/b30bf88b/reference-odds.json'),
    Path('research/a34bc06b/reference-odds.json'),
    # Session arena-a5b59ee6: the *automated* capture written by
    # ``scripts/egw_live.py`` on every live refresh. It is listed last so a
    # hand-reviewed capture is always preferred when both cover a fixture, and
    # it is read here — not appended in ``originate`` — so the publisher and
    # the replay audit in ``build_origination.validate_origination`` resolve a
    # published reference row from exactly the same pool. Every entry still
    # passes ``quote()``'s freshness, identity, placeholder and hash gates.
    LIVE_EVIDENCE_PATH,
)
# The live capture is verified against the request manifest that produced it:
# an entry may only price a fixture when the recorded EGW index request exists,
# succeeded, and carries the same observation instant. Fail closed otherwise.
LIVE_REQUEST_ID = 'live-egw-index'
LIVE_CAPTURE_PREFIX = 'automated'
PROVIDER = 'EGamersWorld (published bookmaker average)'
FAMILY = 'reference'
MIN_ODDS, MAX_ODDS = 1.01, 100.0
REQUIRED = ('fixture_id', 'teams', 'starts_at', 'odds', 'source_url', 'observed_at',
            'excerpt', 'excerpt_sha256', 'provider_teams')


def _read_capture(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def load(source: Path) -> dict:
    """Read all reviewed captures; missing or malformed files are inert, never fatal."""
    root = Path(source)
    entries, rejected, loaded, latest_observed = [], [], [], None
    for rel in CAPTURE_PATHS:
        path = root / rel
        data = _read_capture(path)
        if data is None:
            continue
        loaded.append(str(path))
        rows = [e for e in data.get('entries') or [] if isinstance(e, dict)]
        if rel == LIVE_EVIDENCE_PATH:
            # An automated entry is usable only when the request manifest
            # proves the fetch it claims. Unwitnessed rows are kept, with a
            # reason, so the ladder reports why the fixture stayed blank.
            kept = []
            for row in rows:
                if _live_capture_is_witnessed(root, row):
                    kept.append(row)
                else:
                    rejected.append(dict(row, rejected=True,
                                         reason='automated EGW capture is not witnessed by the '
                                                'request manifest (missing, failed or restamped fetch)'))
            rows = kept
        entries.extend(rows)
        rejected.extend(e for e in data.get('rejected') or [] if isinstance(e, dict))
        obs = data.get('observed_at') or data.get('captured_at')
        if obs and (latest_observed is None or str(obs) > str(latest_observed)):
            latest_observed = obs
    if not loaded:
        return {'entries': [], 'rejected': [], 'path': str(root / EVIDENCE_PATH), 'missing': True}
    return {'entries': entries, 'rejected': rejected, 'path': loaded[0], 'paths': loaded,
            'missing': False, 'observed_at': latest_observed}


def _live_capture_is_witnessed(source: Path, entry: dict) -> bool:
    """True only when the request manifest proves the live capture's fetch.

    The automated rung stores the EGW index response verbatim and records the
    request in ``live-collection-manifest.json``. An entry that names an
    ``observed_at`` the manifest does not carry — or that survives with no
    manifest at all — is treated as unwitnessed and prices nothing.
    """
    manifest = Path(source) / 'origination/evidence/live-collection-manifest.json'
    try:
        requests_ = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    if not isinstance(requests_, list):
        return False
    asked = [r for r in requests_
             if isinstance(r, dict) and r.get('id') == LIVE_REQUEST_ID]
    return (len(asked) == 1 and asked[0].get('status') == 'ok'
            and asked[0].get('observed_at') == entry.get('observed_at'))


def entry_for(source: Path, fixture_id, quote_row: dict) -> dict | None:
    """The pooled capture a published reference quote was actually built from.

    Selection is by provenance, not by fixture id alone: a hand-reviewed
    capture and an automated one may both cover a fixture, and the publisher
    may have used either (for example when the reviewed copy went stale). The
    published quote carries the ``source_url``, ``observed_at`` and
    ``excerpt_sha256`` it was priced from, so the audit can replay exactly that
    entry instead of whichever one happens to come first in the tuple.
    """
    pooled = load(source)
    rows = list(pooled.get('entries') or []) + list(pooled.get('rejected') or [])
    for entry in rows:
        if str(entry.get('fixture_id')) != str(fixture_id):
            continue
        if (entry.get('source_url') == quote_row.get('source_url')
                and entry.get('observed_at') == quote_row.get('observed_at')
                and entry.get('excerpt_sha256') == quote_row.get('excerpt_sha256')):
            return entry
    return None


def problems(entry: dict) -> list[str]:
    """Every reason this entry may not produce a pick.  Empty list means valid."""
    out = []
    for key in REQUIRED:
        if key not in entry:
            out.append(f'missing {key}')
    if out:
        return out
    fixture_id = str(entry.get('fixture_id') or '')
    if not fixture_id.isdigit():
        out.append('fixture_id must be the numeric Hotspawn id')
    teams = entry.get('teams')
    if not isinstance(teams, list) or len(teams) != 2 or len({name_key(t) for t in teams if isinstance(t, str)}) != 2:
        out.append('teams must be two distinct names')
    provider_teams = entry.get('provider_teams')
    if not isinstance(provider_teams, list) or len(provider_teams) != 2 or not all(isinstance(t, str) and t.strip() for t in provider_teams):
        out.append('provider_teams must record the two names the provider printed')
    if timestamp(entry.get('starts_at')) is None:
        out.append('starts_at is not an ISO timestamp')
    if timestamp(entry.get('observed_at')) is None:
        out.append('observed_at is not an ISO timestamp')
    odds = entry.get('odds')
    if not isinstance(odds, list) or len(odds) != 2:
        out.append('odds must be a two-element list')
    else:
        try:
            a, b = float(odds[0]), float(odds[1])
            if not (MIN_ODDS < a <= MAX_ODDS and MIN_ODDS < b <= MAX_ODDS):
                out.append('odds outside the accepted decimal range')
            elif a == b:
                out.append('identical prices are treated as a site placeholder, not a market')
            else:
                no_vig([a, b])
        except (TypeError, ValueError) as exc:
            out.append(f'odds rejected: {exc}')
    url = entry.get('source_url')
    if not (isinstance(url, str) and url.startswith('https://egamersworld.com/')):
        out.append('source_url must be the original EGamersWorld match page')
    excerpt = entry.get('excerpt')
    if not (isinstance(excerpt, str) and len(excerpt) >= 40):
        out.append('excerpt must retain the published odds sentence')
    elif entry.get('excerpt_sha256') != hashlib.sha256(excerpt.encode('utf-8')).hexdigest():
        out.append('excerpt_sha256 does not match the retained sentence')
    return out


def quote(entry: dict, match: dict, now: datetime, *, max_age_hours: int = MAX_PRICE_AGE_HOURS):
    """Return (quote, reason).  A quote is only produced for an exact, fresh join."""
    if entry.get('rejected') is True or ('reason' in entry and 'odds' not in entry):
        return None, 'Reviewed capture rejected: ' + str(entry.get('reason') or 'no stated reason')
    bad = problems(entry)
    if bad:
        return None, 'Capture rejected: ' + '; '.join(bad)
    if str(match.get('id')) != str(entry['fixture_id']):
        return None, 'Different Hotspawn fixture id; no cross-fixture reuse'
    names = [t.get('name') or '' for t in match.get('teams') or []]
    if not identity_matches(names, match.get('starts_at'), match):
        return None, 'Fixture identity is unverified'
    if [name_key(n) for n in names] != [name_key(n) for n in entry['teams']]:
        return None, 'Hotspawn team names differ from the reviewed capture'
    if timestamp(match.get('starts_at')) != timestamp(entry['starts_at']):
        return None, 'Start time differs from the reviewed capture'
    if not is_fresh(entry['observed_at'], now):
        return None, 'Aggregated line is older than eight hours or undated'
    odds = [float(entry['odds'][0]), float(entry['odds'][1])]
    probs = no_vig(odds)
    return {
        'provider': PROVIDER,
        'family': FAMILY,
        'probabilities': probs,
        'odds': odds,
        'overround': round(sum(1 / o for o in odds), 6),
        'source_url': entry['source_url'],
        'observed_at': entry['observed_at'],
        'fixture_id': str(entry['fixture_id']),
        'excerpt_sha256': entry['excerpt_sha256'],
        'provider_teams': list(entry['provider_teams']),
        'aggregated': True,
        'thin': False,
        'method': 'reference',
        'label': 'Aggregated bookmaker average (EGamersWorld, no-vig)',
    }, 'Dated EGamersWorld bookmaker-average sentence replayed and hash-checked.'


def replay(entry: dict, quote_row: dict) -> None:
    """Recompute a published reference quote; raise on any drift."""
    bad = problems(entry)
    if bad:
        raise ValueError('Reference capture is invalid: ' + '; '.join(bad))
    expected = no_vig([float(entry['odds'][0]), float(entry['odds'][1])])
    if quote_row.get('probabilities') != expected:
        raise ValueError('Reference probabilities differ from the retained odds')
    for key in ('source_url', 'observed_at', 'excerpt_sha256'):
        if quote_row.get(key) != entry.get(key):
            raise ValueError(f'Reference {key} changed')
    if [float(x) for x in quote_row.get('odds') or []] != [float(x) for x in entry['odds']]:
        raise ValueError('Reference odds changed')


def rows(data: dict, now: datetime) -> list[dict]:
    out = []
    for entry in data.get('entries') or []:
        bad = problems(entry)
        out.append({'entry': entry, 'problems': bad})
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--now', default=None, help='ISO reference time (default: current UTC)')
    args = parser.parse_args(argv)
    now = timestamp(args.now) if args.now else datetime.now(UTC)
    data = load(args.source)
    print(json.dumps({'path': data['path'], 'missing': data.get('missing'),
                      'entries': len(data['entries']), 'rejected': len(data['rejected'])}, indent=2))
    status = 0
    for entry in data['entries']:
        bad = problems(entry)
        probs = None if bad else no_vig([float(x) for x in entry['odds']])
        print(json.dumps({'fixture_id': entry.get('fixture_id'), 'teams': entry.get('teams'),
                          'odds': entry.get('odds'), 'probabilities': probs,
                          'observed_at': entry.get('observed_at'), 'issues': bad}, indent=2))
        if bad:
            status = 1
        elif not is_fresh(entry.get('observed_at'), now):
            print('  note: stale at the reference time', file=sys.stderr)
    for entry in data.get('rejected') or []:
        print(json.dumps({'rejected': entry.get('fixture_id'), 'teams': entry.get('teams'),
                          'reason': entry.get('reason')}, indent=2))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
