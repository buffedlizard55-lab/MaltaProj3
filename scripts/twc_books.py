"""Original esportsbook fallback for unresolved final-day tournament fixtures.

Uses the existing reviewed source parsers, exact pair/start join, and no-vig
estimator. Temporary file adaptation is needed only because the existing Bovada
parser accepts an evidence directory; it is not a second probability engine.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts import originate
from scripts.domain import timestamp
from scripts.sources import SourceError

PROVIDERS = {
    'Thunderpick': {'api': originate.THUNDERPICK_API, 'page': originate.THUNDERPICK_PAGE,
                   'method': 'POST', 'payload': {'gameIds': [6]}},
    'Bovada': {'api': originate.BOVADA_API, 'page': originate.BOVADA_SITE, 'method': 'GET'},
}


def quote(provider, payload, observed, fixture, registry, now):
    start = timestamp(fixture.get('starts_at'))
    if not start or start <= now:
        return None, 'Past start or unverified fixture time; no current prematch line.'
    if provider == 'Thunderpick':
        if not isinstance(payload, dict):
            return None, 'Unrecognized Thunderpick original response.'
        # Label adaptation only: the parser's established request ID is retained
        # in its interface, while the real dated response is the input here.
        rows = originate.thunderpick_rows(Path('.'), {
            'thunderpick': payload, 'requests': [{'id': 'live-thunderpick-matches',
                                                  'status': 'ok', 'observed_at': observed}]})
    elif provider == 'Bovada':
        if not isinstance(payload, list):
            return None, 'Unrecognized Bovada original coupon response.'
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'live-bovada-cs2.json').write_text(json.dumps({'observed_at': observed, 'response': payload}))
            rows = originate.bovada_rows(folder)
    else:
        return None, 'Unsupported original bookmaker.'
    hits = [r for r in rows if originate.pair_join(r['names'], r['start'], fixture, registry)[2] == 'matched']
    if len(hits) != 1:
        return None, ('No unique exact-team/start two-way prematch series winner in the original coupon. '
                      f'Validated candidate count: {len(hits)}; map/prop/live or ambiguous rows are not accepted.')
    priced, reason = originate.bookmaker_estimate(hits[0], fixture, registry, now=now)
    if not priced:
        return None, reason
    return {**priced, 'bid': None, 'ask': None, 'activity': None}, reason


def collect(client, fixture, registry, now, stamp):
    """Only invoked after no primary tournament market returned a valid quote."""
    from scripts.twc_lines import _record_evidence
    rows = []
    for name, spec in PROVIDERS.items():
        label = f'twc-day5-book-{name.lower()}-{fixture["id"]}-{stamp}'
        try:
            payload, request = client.json(spec['api'], label, method=spec['method'], payload=spec.get('payload'))
            priced, reason = quote(name, payload, request['observed_at'], fixture, registry, now)
            evidence = _record_evidence(client, [label])
        except SourceError as exc:
            priced, reason, evidence = None, str(exc)[:400], []
            request = client.manifest[-1] if client.manifest else {}
        rows.append({'provider': name, 'status': 'resolved' if priced else 'unresolved',
                     'reason': reason, 'source_url': spec['page'], 'observed_at': request.get('observed_at'),
                     'quote': priced, 'evidence': evidence})
    return rows


def replay(provider, payloads, observations, fixture, registry, now):
    """Payload hashes are checked by the caller; bind origin and timestamp too."""
    name = provider['provider']
    spec = PROVIDERS[name]
    evidence = provider.get('evidence') or []
    if len(evidence) != 1 or len(payloads) != 1:
        return None, 'No single original bookmaker response retained.'
    item = evidence[0]
    if item.get('url') != spec['api'] or item.get('method') != spec['method']:
        raise ValueError('Tournament bookmaker original source/method mismatch')
    if item.get('observed_at') != provider.get('observed_at'):
        raise ValueError('Tournament bookmaker observation timestamp mismatch')
    return quote(name, payloads[item['label']], observations[item['label']], fixture, registry, now)
