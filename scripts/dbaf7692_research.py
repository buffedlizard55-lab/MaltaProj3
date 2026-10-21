"""Session research: capture HLTV match pages and any listed betting odds.

Read-only. For every active fixture that still has no directional pick (and for
a small control sample with a market pick), this probe:

1. locates the fixture's HLTV match page (reusing the URL already recorded in
   the origination research trail, otherwise searching HLTV's upcoming list),
2. saves the original HTML/JSON response and its SHA-256,
3. records the published match facts (teams, start, event, best-of),
4. dumps every element whose class/id mentions odds or betting, so the exact
   markup contract can be reviewed rather than guessed.

It never writes a probability, a pick or an alias. Output is evidence for the
unresolved-pick dossier in ``data/research/dbaf7692/``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from scripts.domain import name_key, timestamp

BASE = 'https://www.hltv.org'
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/127.0 Safari/537.36 HotspawnCS2Coverage/1.0 (+https://github.com/buffedlizard55-lab/MaltaProj3)'),
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
}
OUT = Path('data/research/dbaf7692')


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def fetch(session: requests.Session, url: str, name: str, raw_dir: Path) -> dict:
    started = datetime.now(timezone.utc)
    entry = {'url': url, 'observed_at': iso_now(), 'name': name}
    try:
        response = session.get(url, headers=HEADERS, timeout=30)
        entry.update({'http_status': response.status_code, 'final_url': response.url,
                      'content_type': response.headers.get('Content-Type'),
                      'response_date': response.headers.get('Date'),
                      'response_sha256': hashlib.sha256(response.content).hexdigest(),
                      'bytes': len(response.content)})
        if response.status_code == 200:
            (raw_dir / name).write_bytes(response.content)
            entry['text'] = response.text
        else:
            entry['text'] = ''
    except requests.RequestException as exc:
        entry.update({'http_status': None, 'error': f'{type(exc).__name__}: {exc}', 'text': ''})
    entry['elapsed_ms'] = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    return entry


def odds_blocks(soup: BeautifulSoup) -> list:
    """Every element that mentions odds/betting in class or id, with its text."""
    found, seen = [], set()
    for tag in soup.find_all(True):
        blob = ' '.join(tag.get('class') or []) + ' ' + (tag.get('id') or '')
        if not re.search(r'odd|betting|coef|price', blob, re.I):
            continue
        text = tag.get_text(' ', strip=True)
        if len(text) > 400 or not text:
            continue
        key = (blob.strip(), text[:120])
        if key in seen:
            continue
        seen.add(key)
        found.append({'tag': tag.name, 'class': tag.get('class'), 'id': tag.get('id'),
                      'text': text, 'data': {k: v for k, v in tag.attrs.items() if k.startswith('data-')}})
    odds = []
    for tag in soup.find_all(True):
        for attr, value in tag.attrs.items():
            if attr.startswith('data-') and re.search(r'odd|coef|price', attr, re.I):
                odds.append({'tag': tag.name, 'attr': attr, 'value': value,
                             'text': tag.get_text(' ', strip=True)[:200],
                             'class': tag.get('class')})
    return [{'elements': found[:40], 'data_attributes': odds[:40]}]


def parse_match(text: str) -> dict:
    soup = BeautifulSoup(text, 'html.parser')
    facts = {'teams': [], 'start': None, 'event': None, 'best_of': None,
             'rank_badges': [], 'fan_vote': None}
    for side in ('team1', 'team2'):
        panel = soup.select_one(f'.{side}-gradient')
        if panel:
            name = panel.select_one('.teamName')
            facts['teams'].append(name.get_text(' ', strip=True) if name else None)
    date = soup.select_one('.timeAndEvent .date[data-unix]')
    if date:
        facts['start'] = timestamp(date.get('data-unix'))
    event = soup.select_one('.timeAndEvent .event a[href^="/events/"]')
    facts['event'] = event.get_text(' ', strip=True) if event else None
    veto = soup.select_one('.veto-box')
    if veto:
        m = re.search(r'\bBest of ([1357])\b', veto.get_text(' ', strip=True))
        facts['best_of'] = int(m.group(1)) if m else None
    for badge in soup.select('.lineup .teamRank, .teamRank'):
        text = badge.get_text(' ', strip=True)
        if text:
            facts['rank_badges'].append(text)
    vote = soup.select_one('.pick-a-winner, .vote-container')
    if vote:
        facts['fan_vote'] = vote.get_text(' ', strip=True)[:200]
    return facts


def find_hltv_url(session, match, raw_dir) -> tuple[str | None, dict]:
    """Prefer the URL recorded by the pipeline; otherwise search HLTV's list."""
    for record in match.get('research') or []:
        url = str(record.get('source_url') or '')
        if url.startswith(BASE + '/matches/'):
            return url, {'found_by': 'origination research trail'}
    listing = fetch(session, BASE + '/matches', 'hltv-matches.html', raw_dir)
    if not listing.get('text'):
        return None, {'found_by': 'none', 'listing_status': listing.get('http_status')}
    soup = BeautifulSoup(listing['text'], 'html.parser')
    wanted = {name_key(t.get('name') or '') for t in match.get('teams') or []}
    for block in soup.select('.match-day .match, .upcomingMatchesSection .match'):
        names = {name_key(a.get_text(' ', strip=True)) for a in block.select('.matchTeamName')}
        link = block.select_one('a.match[href^="/matches/"], a[href^="/matches/"]')
        if wanted and wanted <= names and link:
            href = link.get('href')
            return BASE + href, {'found_by': 'hltv upcoming list', 'listing_sha256': listing.get('response_sha256')}
    return None, {'found_by': 'none', 'listing_sha256': listing.get('response_sha256'),
                  'listing_status': listing.get('http_status'),
                  'wanted': sorted(wanted)}


def main() -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    data = json.loads((args.data / 'latest.json').read_text())
    orig_path = args.data / 'origination.json'
    origination = json.loads(orig_path.read_text()) if orig_path.exists() else {'matches': []}
    rows = {str(row['id']): row for row in origination.get('matches', [])}
    raw_dir = args.out / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    targets = []
    for match in data.get('matches', []):
        if match.get('availability') == 'past':
            continue
        row = rows.get(str(match['id'])) or {}
        chosen = row.get('origination')
        if chosen and row.get('pick_index') is not None:
            continue
        targets.append(match)

    report = {'generated_at': iso_now(), 'fixtures': [], 'limitations': [
        'Read-only research. No probability, pick or alias is written by this probe.',
        "HLTV 'Pick a winner' fan votes and Hotspawn '% picked' are never probability inputs.",
    ]}
    for match in targets:
        row = rows.get(str(match['id'])) or {}
        entry = {'id': match['id'], 'teams': [t.get('name') for t in match.get('teams', [])],
                 'starts_at': match.get('starts_at'), 'competition': match.get('competition'),
                 'hotspawn_url': match.get('source_url'),
                 'previous_method': (row.get('origination') or {}).get('method'),
                 'previous_pick_index': row.get('pick_index')}
        url, how = find_hltv_url(session, dict(match, research=(row.get('research') or match.get('research') or [])), raw_dir)
        entry['hltv_match_url'] = url
        entry['discovery'] = how
        if url:
            page = fetch(session, url, f'hltv-match-{match["id"]}.html', raw_dir)
            entry['match_page'] = {k: page.get(k) for k in ('http_status', 'response_sha256', 'bytes', 'observed_at', 'error')}
            if page.get('text'):
                entry['match_facts'] = parse_match(page['text'])
                soup = BeautifulSoup(page['text'], 'html.parser')
                entry['odds_blocks'] = odds_blocks(soup)
                analytics = url.replace(BASE + '/matches/', BASE + '/betting/analytics/')
                page2 = fetch(session, analytics, f'hltv-analytics-{match["id"]}.html', raw_dir)
                entry['analytics_page'] = {k: page2.get(k) for k in ('http_status', 'response_sha256', 'bytes', 'observed_at', 'error')}
                if page2.get('text'):
                    soup2 = BeautifulSoup(page2['text'], 'html.parser')
                    entry['analytics_odds_blocks'] = odds_blocks(soup2)
                    summary = soup2.select_one('.analytics-summary, .analytics')
                    entry['analytics_summary'] = summary.get_text(' | ', strip=True)[:1500] if summary else None
        report['fixtures'].append(entry)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'hltv-odds-probe.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'targets': len(targets), 'with_hltv_page': sum(1 for f in report['fixtures'] if f.get('hltv_match_url'))}, indent=2))
    return report


if __name__ == '__main__':
    main()
