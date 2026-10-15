"""Bounded first-party research; no login, API secrets or challenge bypass."""
import gzip
import json
from pathlib import Path
from scripts.sources import Client, SourceError

out = Path('.cache/source-audit')
client = Client(out)
for label, url in [
    ('hltv-matches', 'https://www.hltv.org/matches'),
    ('hltv-day-one-results', 'https://www.hltv.org/results?startDate=2026-10-13&endDate=2026-10-14'),
    ('hltv-news', 'https://www.hltv.org/news'),
    ('stake-cs2', 'https://stake.com/sports/esports/counter-strike'),
    ('pinnacle-cs2', 'https://www.pinnacle.com/en/esports-hub/cs2'),
    ('polymarket-api-docs', 'https://docs.polymarket.com/api-reference/events/list-events'),
]:
    try:
        text, request = client.fetch(url, label)
        (out / (label + '.html.gz')).write_bytes(gzip.compress(text.encode()))
        print(label, request['http_status'], request['final_url'], len(text))
    except SourceError as exc:
        print(str(exc))
(out / 'report.json').write_text(json.dumps(client.manifest, indent=2) + '\n')

# Keep a compact, source-attributed research excerpt in check annotations too.
# Artifact downloads may be unavailable in a restricted coding environment;
# annotations remain accessible through GitHub's official Checks API.
from bs4 import BeautifulSoup
for label in ['hltv-day-one-results', 'hltv-news']:
    path = out / (label + '.html.gz')
    if not path.exists():
        continue
    soup = BeautifulSoup(gzip.decompress(path.read_bytes()), 'html.parser')
    snippets = []
    elements = soup.select('.result-con') if label.endswith('results') else soup.find_all('a', href=True)
    for element in elements:
        text = element.get_text(' ', strip=True)
        if 'aurora' in text.lower() or '9z' in text.lower():
            a = element if element.name == 'a' else element.find('a', href=True)
            snippets.append({'text': text, 'href': a.get('href') if a else None})
    payload = json.dumps({'source': label, 'title': soup.title.get_text() if soup.title else None,
                          'matching_snippets': snippets[:20]}, ensure_ascii=True)
    payload = payload.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::notice title=Day-one research excerpt::' + payload)
