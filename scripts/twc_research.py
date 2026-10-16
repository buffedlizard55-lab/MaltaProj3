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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    args = parser.parse_args()
    collect(args.data)


if __name__ == '__main__':
    main()
