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
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.domain import iso, timestamp
from scripts.hltv_match import parse_match
from scripts.sources import Client, SourceError
from scripts import twc_lines

EVENT_URL = 'https://www.hltv.org/events/8932/thunderpick-world-championship-2026'
TARGET_DAY = '2026-10-17'
FINAL_DAY = '2026-10-18'
OBSERVATIONS = Path('research/138f48b7/day4-market-observations.json')
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



def retained_discovery_urls(source: Path):
    """Previously observed links are discovery leads only, never current facts.

    Event schedules can stop linking completed rounds. Replay retained originals
    to keep those known match pages in the refresh, without guessing URL slugs.
    """
    urls = set()
    for relative in [FOLDER, Path('research/8a6a5a84/twc-current')]:
        folder = source / relative
        manifest = folder / 'source-report.json'
        if not manifest.exists():
            continue
        report = json.loads(manifest.read_text())
        for page in report.get('pages', []):
            if page.get('request', {}).get('status') != 'ok' or not page.get('original_response'):
                continue
            original = folder / page['original_response']
            if original.resolve().parent != folder.resolve():
                raise ValueError('TWC discovery path escapes research folder')
            raw = gzip.decompress(original.read_bytes())
            if hashlib.sha256(raw).hexdigest() != page.get('stored_sha256'):
                raise ValueError('TWC discovery original hash mismatch')
            url = page['request']['url']
            if url.startswith('https://www.hltv.org/'):
                urls.update(discovered_urls(raw.decode()))
                if re.fullmatch(r'https://www\.hltv\.org/matches/\d+/[a-z0-9-]*thunderpick-world-championship-2026', url):
                    urls.add(url)
    # One request per stable match ID, even when the source changes the slug.
    return set({url.split('/')[4]: url for url in sorted(urls)}.values())


def collect(source: Path):
    folder = source / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    client = Client(folder)
    pages, urls = [], set(DAY3_URLS) | retained_discovery_urls(source)
    for label, url in [('event', EVENT_URL), ('matches', 'https://www.hltv.org/events/8932/matches'),
                       ('results', 'https://www.hltv.org/results?event=8932'),
                       ('hotspawn-tournament', 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/tournaments/thunderpick-world-championships?tenantId=1'),
                       ('hotspawn-tournament-page', 'https://play.hotspawn.com/tournaments/thunderpick-world-championships')]:
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
    for url in sorted({url.split('/')[4]: url for url in sorted(urls)}.values())[:24]:
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
    # Tournament-card lines for the target day. The weekly Hotspawn lobby feed
    # does not carry TWC playoff fixtures, so without this step they could never
    # have a probability. External first-party markets only; blanks stay blank.
    rows = [{'source_url': page['request']['url'], 'observed_at': page['request'].get('observed_at'),
             'facts': page['facts']} for page in pages if page.get('facts')]
    registry_path = Path('data/origination/aliases.json')
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {'aliases': []}
    lines = twc_lines.collect(client, rows, registry, TARGET_DAY, datetime.now(timezone.utc))
    resolved = [r for r in lines['records'] if any(p.get('quote') for p in r['providers'])]
    report['day4_lines'] = {
        'report': 'evidence/twc-day4-lines.json', 'fixtures': len(lines['records']),
        'resolved': len(resolved), 'observed_at': lines['observed_at'],
        'detail': 'External Polymarket/Kalshi full-series books for TWC fixtures that are absent from the weekly '
                  'Hotspawn inventory. Probabilities are recomputed from the retained originals at build time.'}
    print('::notice title=TWC day4 lines::' + json.dumps({'observed_at': lines['observed_at'],
                                                          'fixtures': len(lines['records']),
                                                          'resolved': len(resolved)}))
    day5 = twc_lines.collect(client, rows, registry, FINAL_DAY, datetime.now(timezone.utc),
                             report_path=twc_lines.DAY5_REPORT)
    report['day5_lines'] = {'report': twc_lines.DAY5_REPORT.as_posix(),
                            'fixtures': len(day5['records']),
                            'resolved': sum(any(p.get('quote') for p in r['providers']) for r in day5['records']),
                            'observed_at': day5['observed_at']}
    print('::notice title=TWC day5 lines::' + json.dumps(report['day5_lines']))
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
        if not re.fullmatch(r'https://www\.hltv\.org/matches/\d+/[a-z0-9-]*thunderpick-world-championship-2026', request['url']):
            continue
        facts = parse_match(raw.decode('utf-8'))
        # A malformed or unrelated page cannot introduce a fixture/result.
        if facts.get('event_url') != EVENT_URL or not all(facts.get('teams', [])):
            continue
        records.append({'source_url': request['url'], 'observed_at': request['observed_at'], 'facts': facts})
    return {'pages': records, 'target_day': TARGET_DAY}


def load_observations(source: Path) -> list:
    """Dated market observations captured by a scoped research fetch.

    These are display-only context for fixtures the pipeline has not collected
    yet. They are never merged into a canonical pair, never used as a pricing
    input and never presented as freshly collected evidence.
    """
    path = source / OBSERVATIONS
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except ValueError:
        return []
    return payload.get('fixtures') or []


def derive_day4(data, source: Path, now, *, target_day=TARGET_DAY, line_report=twc_lines.REPORT):
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
                and str(m.get('starts_at') or '').startswith(target_day)]
    records = [r for r in research['pages'] if str(r['facts'].get('starts_at') or '').startswith(target_day)]
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
    # Tournament-card lines are replayed from retained external originals. They
    # are attached beside the canonical pair, never over it, and only a fixture
    # without a supported estimate is allowed to use one as its own line.
    lines = (twc_lines.load(source, now) if line_report == twc_lines.REPORT else
             twc_lines.load(source, now, report_file=line_report))
    for row in rows:
        if row['analysis'] is None:
            row['line'] = twc_lines.for_fixture(lines, row['teams'], row['fixture']['starts_at'])
            row['line_underdog'] = twc_lines.underdog(row['line']) if row.get('line') else None
    for record in unlisted:
        record['line'] = twc_lines.for_fixture(lines, record['facts']['teams'], record['facts']['starts_at'])
        record['line_underdog'] = twc_lines.underdog(record['line']) if record.get('line') else None
    day3 = []
    for r in research['pages']:
        facts = r['facts']
        if str(facts.get('starts_at') or '').startswith('2026-10-16'):
            day3.append({'label': r['source_url'].split('/')[4], 'teams': facts['teams'],
                         'score': facts['score'], 'maps': facts['maps'], 'finished': facts['finished'],
                         'source_url': r['source_url'], 'observed_at': r['observed_at'],
                         'lesson': 'Use the completed series as matchup context, not a new win-rate sample or proof the earlier odds were wrong.' if facts['score'] else 'Result unverified. A past scheduled start does not establish a winner.'})
    return {'schema_version': 1, 'generated_at': data.get('generated_at'), 'source_snapshot_at': data.get('inventory_observed_at'), 'evaluated_at': iso(now), 'event_day': target_day, 'research_available': bool(research['pages']), 'matches': rows, 'not_in_hotspawn_snapshot': unlisted,
            'day3_results': day3, 'research_report': str(FOLDER / 'source-report.json') if (source / FOLDER / 'source-report.json').exists() else 'research/8a6a5a84/twc-current/source-report.json',
            'lines': {'available': lines['available'], 'day': lines['day'], 'observed_at': lines['observed_at'],
                      'report_path': lines['report_path'], 'policy': lines['policy'],
                      'resolved': len([m for m in lines['matches'] if m.get('probabilities')]),
                      'total': len(lines['matches']),
                      'fixtures': [{'fixture_id': m['fixture_id'], 'teams': m['teams'], 'starts_at': m['starts_at'],
                                    'probabilities': m.get('probabilities'), 'pick_index': m.get('pick_index'),
                                    'method': m.get('method'), 'label': m.get('label'), 'observed_at': m.get('observed_at'),
                                    'providers': m.get('providers') or [], 'attempts': m.get('attempts') or [],
                                    'limitations': m.get('limitations') or [], 'source_url': m.get('source_url')}
                                   for m in lines['matches']]},
            'observations': load_observations(source),
            'observations_path': OBSERVATIONS.as_posix(),
            'policy': 'Exact canonical probabilities; no historical, roster, crowd, rest or result premium.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    args = parser.parse_args()
    collect(args.data)


if __name__ == '__main__':
    main()
