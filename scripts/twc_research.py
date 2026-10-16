"""Bounded TWC Day-3/4 source research, independent of pricing.

Ordinary public HLTV GETs only; original markup and hashes are retained.
This collector never invents fixtures, scores, lines or roster adjustments.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.domain import iso, timestamp
from scripts.hltv_match import parse_match
from scripts.sources import Client, SourceError

EVENT_URL = 'https://www.hltv.org/events/8932/thunderpick-world-championship-2026'
TARGET_DAY = '2026-10-17'
FOLDER = Path('research/twc-current')
DAY3_URLS = [
    'https://www.hltv.org/matches/2399412/aurora-vs-9z-thunderpick-world-championship-2026',
    'https://www.hltv.org/matches/2399413/betboom-vs-legacy-thunderpick-world-championship-2026',
]


def discovered_urls(text):
    """Only match links actually published on the event's own pages."""
    soup = BeautifulSoup(text, 'html.parser')
    return sorted({urljoin('https://www.hltv.org', a['href']) for a in soup.select('a[href^="/matches/"]')
                   if re.fullmatch(r'/matches/\d+/[a-z0-9-]*thunderpick-world-championship-2026', a['href'])})


def collect(source: Path):
    folder = source / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    client = Client(folder)
    pages, urls = [], set(DAY3_URLS)
    for label, url in [('event', EVENT_URL), ('matches', 'https://www.hltv.org/events/8932/matches'),
                       ('results', 'https://www.hltv.org/results?event=8932')]:
        try:
            text, req = client.fetch(url, 'twc-' + label)
            raw = text.encode('utf-8')
            filename = label + '.html.gz'
            (folder / filename).write_bytes(gzip.compress(raw, mtime=0))
            pages.append({'label': label, 'request': dict(req), 'original_response': filename,
                          'stored_sha256': hashlib.sha256(raw).hexdigest()})
            urls.update(discovered_urls(text))
        except SourceError:
            pages.append({'label': label, 'request': dict(client.manifest[-1])})
    # The event has a small finite bracket. Never follow arbitrary embedded links.
    for url in sorted(urls)[:24]:
        label = 'match-' + url.split('/')[4]
        try:
            text, req = client.fetch(url, 'twc-' + label)
            raw = text.encode('utf-8')
            filename = label + '.html.gz'
            (folder / filename).write_bytes(gzip.compress(raw, mtime=0))
            facts = parse_match(text)
            pages.append({'label': label, 'request': dict(req), 'original_response': filename,
                          'stored_sha256': hashlib.sha256(raw).hexdigest(), 'facts': facts})
            print('::notice title=TWC source facts::' + json.dumps({'source_url': url, 'observed_at': req['observed_at'], **facts}))
        except SourceError:
            pages.append({'label': label, 'request': dict(client.manifest[-1])})
    report = {'schema_version': 1, 'policy': 'Source research only; canonical picks supply all probabilities. HLTV is an independent reporter, not tournament organizer verification.',
              'target_day': TARGET_DAY, 'pages': pages}
    (folder / 'source-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def load(source: Path):
    """Replay originals, not stored extracted facts. Fail closed on tampering."""
    folder = source / FOLDER
    path = folder / 'source-report.json'
    if not path.exists():
        folder = source / 'research/8a6a5a84/twc-current'
        path = folder / 'source-report.json'
    if not path.exists():
        return {'pages': [], 'target_day': TARGET_DAY}
    report = json.loads(path.read_text())
    records = []
    for page in report['pages']:
        request = page['request']
        if request.get('status') != 'ok' or not page.get('original_response'):
            continue
        original = folder / page['original_response']
        if original.resolve().parent != folder.resolve():
            raise ValueError('TWC current original path escapes research folder')
        raw = gzip.decompress(original.read_bytes())
        if hashlib.sha256(raw).hexdigest() != page.get('stored_sha256'):
            raise ValueError('TWC current original hash mismatch')
        if '/matches/' not in request['url']:
            continue
        facts = parse_match(raw.decode('utf-8'))
        # A malformed or unrelated page cannot introduce a fixture/result.
        if facts.get('event_url') != EVENT_URL or not all(facts.get('teams', [])):
            continue
        records.append({'source_url': request['url'], 'observed_at': request['observed_at'], 'facts': facts})
    return {'pages': records, 'target_day': TARGET_DAY}


def derive_day4(data, source: Path, now):
    """Join only exact teams/event/date/time; use canonical prices unchanged."""
    from scripts.domain import name_key
    from scripts.pick_safety import presentation, valid_pair
    research = load(source)
    complete = data.get('complete_picks') or {}
    if complete and complete.get('source_snapshot_at') != data.get('inventory_observed_at'):
        raise ValueError('Day-4 picks belong to another inventory observation')
    by_id = {m['id']: m for m in complete.get('matches', [])}
    event_name = 'Thunderpick World Championship 2026'
    fixtures = [m for m in data['matches'] if name_key(m.get('competition') or '') == name_key(event_name)
                and str(m.get('starts_at') or '').startswith(TARGET_DAY)]
    records = [r for r in research['pages'] if str(r['facts'].get('starts_at') or '').startswith(TARGET_DAY)]
    rows, consumed = [], set()
    for fixture in fixtures:
        row = by_id.get(fixture['id'])
        if row and any(row.get(k) != fixture.get(k) for k in ['teams', 'starts_at', 'locks_at']):
            raise ValueError('Day-4 canonical fixture mismatch')
        names = [t.get('name') for t in fixture['teams']]
        pair = {name_key(n or '') for n in names}
        candidates = [r for r in records if {name_key(n) for n in r['facts']['teams']} == pair
                      and r['facts']['starts_at'] == fixture['starts_at']]
        record = candidates[0] if len(candidates) == 1 else None
        if record:
            consumed.add(record['source_url'])
        analysis = row.get('origination') if row else None
        pick = row.get('pick_index') if row and analysis else None
        if analysis:
            p = analysis.get('probabilities')
            if not valid_pair(p):
                raise ValueError('Invalid canonical Day-4 probability pair')
            expected = None if abs(p[0] - p[1]) < 1e-8 else (0 if p[0] > p[1] else 1)
            if pick != expected:
                raise ValueError('Day-4 direction differs from canonical higher probability')
        canonical = dict(fixture, origination=analysis)
        state = presentation(canonical, data.get('inventory_observed_at'), data.get('coverage_complete'), now)
        alternative = None
        if state['current'] and pick is not None and analysis['method'] in {'market', 'bookmaker', 'consensus'}:
            dog = 1 - pick
            if 0.30 <= analysis['probabilities'][dog] < 0.50:
                alternative = {'team': names[dog], 'probability': analysis['probabilities'][dog],
                               'cost_per_base_point': round(analysis['probabilities'][pick] - analysis['probabilities'][dog], 8)}
        rows.append({'fixture': canonical, 'hltv': record, 'teams': names, 'analysis': analysis,
                     'pick_index': pick, 'pick': names[pick] if pick is not None else None,
                     'state': state, 'alternative': alternative,
                     'limitation': None if analysis else 'No supported estimate. HLTV, first-party exchange/books and exact-five Valve fallback could not establish usable inputs; see the complete match research trail.'})
    # Report independently listed fixtures even before Hotspawn adds them, but
    # never claim they are in the pick-em inventory or manufacture a lock/price.
    unlisted = [r for r in records if r['source_url'] not in consumed]
    day3 = []
    for r in research['pages']:
        facts = r['facts']
        if str(facts.get('starts_at') or '').startswith('2026-10-16'):
            day3.append({'label': r['source_url'].split('/')[4], 'teams': facts['teams'],
                         'score': facts['score'], 'maps': facts['maps'], 'finished': facts['finished'],
                         'source_url': r['source_url'], 'observed_at': r['observed_at'],
                         'lesson': 'Use the completed series as matchup context, not a new win-rate sample or proof the earlier odds were wrong.' if facts['score'] else 'Result unverified. A past scheduled start does not establish a winner.'})
    return {'event_day': TARGET_DAY, 'research_available': bool(research['pages']), 'matches': rows, 'not_in_hotspawn_snapshot': unlisted,
            'day3_results': day3, 'research_report': str(FOLDER / 'source-report.json') if (source / FOLDER / 'source-report.json').exists() else 'research/8a6a5a84/twc-current/source-report.json',
            'policy': 'Exact canonical probabilities; no historical, roster, crowd, rest or result premium.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    args = parser.parse_args()
    collect(args.data)


if __name__ == '__main__':
    main()
