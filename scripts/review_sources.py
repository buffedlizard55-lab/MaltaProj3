"""Bounded research-only first-party verification; never a probability input.

Uses the normal public HLTV pages linked by the existing audit and canonical
match research, with no login or challenge bypass. Saves original compressed
responses, their hashes and source-attributed extracts for manual inspection.
The live snapshot excerpt is a dated diagnostic, NOT a second current feed.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path

from bs4 import BeautifulSoup

from scripts.sources import Client, SourceError

MATCHES = {
    'day1-9z-aurora': '2399384/9z-vs-aurora-thunderpick-world-championship-2026',
    'day1-falcons-nip': '2399385/falcons-vs-ninjas-in-pyjamas-thunderpick-world-championship-2026',
    'day1-legacy-parivision': '2399386/legacy-vs-parivision-thunderpick-world-championship-2026',
    'day1-furia-betboom': '2399387/furia-vs-betboom-thunderpick-world-championship-2026',
    'day2-aurora-nip': '2399408/aurora-vs-ninjas-in-pyjamas-thunderpick-world-championship-2026',
    'day2-9z-falcons': '2399409/9z-vs-falcons-thunderpick-world-championship-2026',
    'day2-parivision-betboom': '2399410/parivision-vs-betboom-thunderpick-world-championship-2026',
    'day2-legacy-furia': '2399411/legacy-vs-furia-thunderpick-world-championship-2026',
    'day3-aurora-9z': '2399412/aurora-vs-9z-thunderpick-world-championship-2026',
    'day3-betboom-legacy': '2399413/betboom-vs-legacy-thunderpick-world-championship-2026',
}


def extract(text):
    soup = BeautifulSoup(text, 'html.parser')
    for node in soup.select('script, style, nav, footer'):
        node.decompose()
    main = soup.select_one('.match-page') or soup.select_one('main') or soup
    return {
        'title': soup.title.get_text(' ', strip=True) if soup.title else None,
        'match_info': [n.get_text(' ', strip=True) for n in soup.select('.timeAndEvent, .team1-gradient, .team2-gradient')],
        'maps': [n.get_text(' ', strip=True) for n in soup.select('.mapholder')],
        'lineups': [str(n) for n in soup.select('.lineup')][:4],
        'article': [n.get_text(' ', strip=True) for n in soup.select('.newstext-con p, .news-article p')][:40],
        'text_excerpt': main.get_text(' ', strip=True)[:35000],
    }


def run(data, output):
    output.mkdir(parents=True, exist_ok=True)
    client = Client(output)
    snapshot = json.loads((data / 'latest.json').read_text())
    complete = json.loads((data / 'origination.json').read_text())
    by_id = {m['id']: m for m in snapshot['matches']}
    report = {
        'schema_version': 1,
        'policy': 'Dated source research, not live picks. No source fact is verified solely by an HTTP success. Original responses are retained for inspection.',
        'inventory_observed_at': snapshot.get('inventory_observed_at'),
        'coverage_complete': snapshot.get('coverage_complete'),
        'counts': complete.get('counts'),
        'fixtures': [], 'pages': [],
    }
    urls = {'twc-results': 'https://www.hltv.org/results?event=8932',
            'aurora-rebuild': 'https://www.hltv.org/news/45082/official-aurora-complete-rebuild-with-kyxsan'}
    urls.update({label: 'https://www.hltv.org/matches/' + suffix for label, suffix in MATCHES.items()})
    for match in complete['matches']:
        report['fixtures'].append(match)
        if match.get('origination') is None:
            for r in by_id[match['id']].get('research', []):
                url = r.get('source_url', '')
                if url.startswith('https://www.hltv.org/matches/'):
                    urls['unresolved-' + match['id']] = url
    # Exact URLs already present in source evidence, max 24 pages, normal GETs.
    for label, url in list(urls.items())[:24]:
        try:
            text, request = client.fetch(url, label)
            original = label + '.html.gz'
            (output / original).write_bytes(gzip.compress(text.encode(), mtime=0))
            row = {'label': label, 'request': dict(request), 'original_response': original, **extract(text)}
            report['pages'].append(row)
            compact = {k: row[k] for k in ['label', 'match_info', 'maps']}
            compact['source_url'] = url
            compact['observed_at'] = request['observed_at']
            message = json.dumps(compact).replace('%', '%25').replace('\n', '%0A').replace('\r', '%0D')
            print('::notice title=First-party match review::' + message)
        except SourceError:
            report['pages'].append({'label': label, 'request': dict(client.manifest[-1])})
        time.sleep(0.4)
    report['requests'] = client.manifest
    (output / 'source-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('::notice title=Live coverage review::' + json.dumps({k: report[k] for k in ['inventory_observed_at', 'coverage_complete', 'counts']}))
    for row in report['fixtures']:
        if row.get('origination') is None:
            print('::notice title=Unresolved source review::' + json.dumps(row))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('.cache/source-review'))
    args = parser.parse_args()
    run(args.data, args.output)


if __name__ == '__main__':
    main()
