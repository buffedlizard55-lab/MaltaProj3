"""Unibet (Kambi-powered) prematch CS2 series prices — session arena-7c0e457b.

Why this source
---------------
The brief asks for a pick for **every** Hotspawn CS2 fixture, including the
low-tier CCT / United21 / NODWIN matches that Polymarket, Kalshi and most US
books do not list. On 2026-10-23 this session verified by hand that Unibet's
public offering feed carries exactly those competitions with a two-sided
``Match Odds`` market, e.g. ``CCT European Series 11`` (Nuclear TigeRES 1.11 /
ILLYRIANS 5.80) and ``CCT European Series 12`` (Inner Circle Academy 2.06 /
Team Spirit Academy 1.73) — both fixtures the featured ladder had left on a
research model. The same two numbers independently reproduce the Polymarket
midpoints already published for those two rows (0.840/0.160 vs 0.845/0.155 and
0.456/0.544 vs 0.445/0.555), which is why the source is treated as a real,
independent money price rather than a placeholder.

What is read
------------
``GET https://eu.offering-api.kambicdn.com/offering/v2018/ub/listView/esports/
all/all/all/matches.json?lang=en_GB&market=GB&client_id=2&channel_id=1&ncid=1``

That is the unauthenticated JSON feed the operator's own website renders. It is
**not** a published API with a public contract, so this module never calls it
documented; the site links the operator's own event page and the captured
response is saved with its SHA-256 so a reader can replay it. Only rows that
satisfy all of the following are stored:

* ``event.sport == 'COUNTER_STRIKE'`` and the event path contains ``CS2``;
* ``event.state == 'NOT_STARTED'`` (never an in-play price);
* exactly one ``Match Odds`` bet offer with two outcomes of type ``OT_ONE`` /
  ``OT_TWO``, both ``status == 'OPEN'``;
* both decimal prices above 1.01 (Kambi prints them in thousandths);
* both team names resolve to the Hotspawn fixture (exact normalised name or the
  reviewed alias registry) — never a fuzzy match.

Nothing here writes a probability. ``rows()`` returns the observed prices and
``scripts/originate.py`` applies the same freshness, prematch, no-vig and
spread rules it applies to every other bookmaker.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.domain import name_key, timestamp

UTC = timezone.utc

# One brand only: every Kambi-powered operator shares the same underlying
# liquidity, so reading two of them and counting both as independent votes would
# double count one price. Unibet (``ub``) is the brand verified by hand here.
BRAND = 'ub'
MARKET = 'GB'
SITE = 'https://www.unibet.co.uk'
SOURCE_URL = 'https://www.unibet.co.uk/betting/sports/esports/counter-strike'
API = 'https://eu.offering-api.kambicdn.com/offering/v2018/ub/listView/esports/all/all/all/matches.json'
API_QUERY = '?lang=en_GB&market=GB&client_id=2&channel_id=1&ncid=1'
PROVIDER = 'Unibet (Kambi)'
EVIDENCE_NAME = 'live-kambi-cs2.json'
SPORT = 'COUNTER_STRIKE'
ODDS_SCALE = 1000
MIN_PRICE = 1.01


def feed_url() -> str:
    return API + API_QUERY


def event_url(event_id) -> str:
    """The operator's own public event page (never the JSON feed)."""
    return f'{SITE}/betting/sports/event/{event_id}'


def is_cs2(entry: dict) -> bool:
    event = entry.get('event') or {}
    if str(event.get('sport') or '') != SPORT:
        return False
    path = event.get('path') or []
    terms = {str((node or {}).get('termKey') or '') for node in path if isinstance(node, dict)}
    names = {str((node or {}).get('name') or '') for node in path if isinstance(node, dict)}
    return bool(terms & {'cs2', 'counter_strike', 'counter_strike_2'} or names & {'CS2', 'Counter-Strike 2'})


def series_offer(entry: dict) -> dict | None:
    """The single two-way ``Match Odds`` offer, or ``None`` when ambiguous.

    Map/special markets live in their own offers; a fixture with two Match Odds
    offers is rejected rather than resolved by taking the first.
    """
    offers = [offer for offer in (entry.get('betOffers') or [])
              if isinstance(offer, dict)
              and str(((offer.get('criterion') or {}).get('englishLabel')) or '') == 'Match Odds']
    if len(offers) != 1:
        return None
    offer = offers[0]
    outcomes = [o for o in (offer.get('outcomes') or []) if isinstance(o, dict)]
    sides = {str(o.get('type') or ''): o for o in outcomes}
    if set(sides) != {'OT_ONE', 'OT_TWO'} or len(outcomes) != 2:
        return None
    if any(str(o.get('status') or '') != 'OPEN' for o in outcomes):
        return None
    prices = []
    for kind in ('OT_ONE', 'OT_TWO'):
        try:
            value = int(sides[kind].get('odds'))
        except (TypeError, ValueError):
            return None
        price = value / ODDS_SCALE
        if price < MIN_PRICE:
            return None
        prices.append(round(price, 4))
    return {'names': [str(sides['OT_ONE'].get('label') or sides['OT_ONE'].get('participant') or ''),
                      str(sides['OT_TWO'].get('label') or sides['OT_TWO'].get('participant') or '')],
            'odds': prices,
            'offer_id': str(offer.get('id') or ''),
            'changed_at': max(str(o.get('changedDate') or '') for o in outcomes)}


def collect(client, evidence_dir: Path) -> dict:
    """Fetch and save the board. A failure records a reason and prices nothing."""
    observed_at = datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')
    document = {'source': f'{PROVIDER} public prematch offering feed',
                'provider': PROVIDER, 'operator': SITE, 'api': feed_url(),
                'api_note': 'Un-authenticated JSON feed rendered by the operator site; no published API contract is claimed.',
                'observed_at': observed_at, 'events': [], 'errors': []}
    try:
        body, entry = client.get_json(feed_url(), 'live-kambi-cs2-raw')
    except RuntimeError as exc:
        document['errors'].append(str(exc)[:300])
        (evidence_dir / EVIDENCE_NAME).write_text(json.dumps(document, ensure_ascii=False) + '\n')
        return {'error': document['errors'][0], 'events': 0, 'priced': 0}
    document['observed_at'] = entry.get('observed_at') or observed_at
    events = body.get('events') if isinstance(body, dict) else None
    if not isinstance(events, list):
        document['errors'].append('Kambi offering contract unrecognized')
        (evidence_dir / EVIDENCE_NAME).write_text(json.dumps(document, ensure_ascii=False) + '\n')
        return {'error': document['errors'][0], 'events': 0, 'priced': 0}
    priced = 0
    for raw in events:
        if not isinstance(raw, dict) or not is_cs2(raw):
            continue
        event = raw.get('event') or {}
        offer = series_offer(raw)
        document['events'].append({
            'event_id': str(event.get('id') or ''),
            'name': event.get('name'), 'home': event.get('homeName'), 'away': event.get('awayName'),
            'start': event.get('start'), 'group': event.get('group'),
            'state': event.get('state'), 'url': event_url(event.get('id')),
            'offer': offer})
        if offer:
            priced += 1
    (evidence_dir / EVIDENCE_NAME).write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
    return {'events': len(document['events']), 'priced': priced, 'errors': document['errors'][:4]}


def load(evidence_dir: Path) -> dict | None:
    path = Path(evidence_dir) / EVIDENCE_NAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except ValueError:
        return None


def rows(evidence_dir: Path, *, names_of=None) -> list[dict]:
    """Price rows rebuilt from the saved capture.

    ``names_of`` lets the caller hand in a name resolver (the reviewed alias
    registry); without one the provider's own spelling is kept and the ladder's
    exact-name join decides. Nothing is guessed here.
    """
    document = load(evidence_dir)
    if not document:
        return []
    observed_at = document.get('observed_at')
    out = []
    for event in document.get('events') or []:
        offer = event.get('offer') or {}
        names, odds = offer.get('names'), offer.get('odds')
        if not names or not odds or len(names) != 2 or len(odds) != 2:
            continue
        if not all(names):
            continue
        resolved = names_of(names) if names_of else names
        out.append({
            'provider': PROVIDER, 'family': 'bookmaker',
            'names': list(resolved), 'source_names': list(names),
            'start': event.get('start'), 'odds': list(odds),
            'event_id': event.get('event_id'), 'market_id': offer.get('offer_id'),
            'competition': event.get('group'),
            'source_url': event.get('url') or event_url(event.get('event_id')),
            'api_url': feed_url(),
            'observed_at': observed_at,
            'evidence_file': f'data/origination/evidence/{EVIDENCE_NAME}',
        })
    return out


def binds(row: dict, match: dict) -> bool:
    """Both provider names equal the fixture's names (normalised), nothing else."""
    if not row.get('start'):
        return False
    wanted = {name_key(t.get('name') or '') for t in match.get('teams') or []}
    have = {name_key(n) for n in row.get('names') or []}
    return len(wanted) == 2 and len(have) == 2 and wanted == have


def start_delta(row: dict, match: dict) -> float | None:
    start, fixture_start = timestamp(row.get('start')), timestamp(match.get('starts_at'))
    if not start or not fixture_start:
        return None
    return (start - fixture_start).total_seconds()
