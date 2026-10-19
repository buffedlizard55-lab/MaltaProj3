"""Session arena-1fb85c47 — dispatch-only ground-truth probe.

The sandbox this session runs in has no egress to Hotspawn, HLTV, bo3.gg, 1xBet
or any bookmaker. The GitHub runner does. This module therefore runs there and
records, for the current unresolved Hotspawn fixtures:

* the HLTV match page the origination ladder already identified,
* whether that page carries a server-rendered betting/odds block, with its raw
  markup retained (truncated) so the parser can be written against the real
  contract rather than a guess,
* the HLTV betting-analytics page and every ranking/form sentence it publishes,
* both teams' HLTV team pages: ranking position, ranking points and recent
  results,
* whether bo3.gg's public API and 1xBet's public line feed answer at all.

It writes no probability and no pick. Every number in the report is copied from
the source response; where a field is absent it records ``null`` rather than a
guess. Nothing in the published site reads this file.

Usage: python -m scripts.session_probe
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '1fb85c47' / 'live-probe.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def fetch(url: str, *, headers=None, timeout: int = 35):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*',
                                               'Accept-Encoding': 'gzip, identity',
                                               **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.headers.get('Content-Encoding') == 'gzip':
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass
            return {'url': url, 'status': resp.status,
                    'content_type': resp.headers.get('Content-Type', ''),
                    'final_url': resp.geturl(),
                    'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                    'text': raw.decode('utf-8', 'replace')}
    except urllib.error.HTTPError as exc:
        return {'url': url, 'status': exc.code, 'error': f'HTTP {exc.code}'}
    except Exception as exc:  # transport, DNS, TLS — recorded, never fatal
        return {'url': url, 'status': None, 'error': f'{type(exc).__name__}: {exc}'}


def snippets(soup, needles=('bet', 'odd', 'rank', 'form', 'predict'), limit=6, width=900):
    """Retain the smallest visible containers that mention the interesting words."""
    out = []
    seen = set()
    for tag in soup.find_all(True):
        classes = ' '.join(tag.get('class') or []).lower()
        ident = (tag.get('id') or '').lower()
        if not any(n in classes or n in ident for n in needles):
            continue
        key = (tag.name, classes, ident)
        if key in seen:
            continue
        seen.add(key)
        text = tag.get_text(' ', strip=True)
        if not text:
            continue
        out.append({'tag': tag.name, 'class': classes, 'id': ident,
                    'text': text[:width], 'html': str(tag)[:width * 2]})
        if len(out) >= limit:
            break
    return out


def numeric_pairs(text: str):
    """Decimal odds-looking pairs printed next to each other (diagnostic only)."""
    return re.findall(r'\b([12]\.\d{2,3})\b[^0-9]{0,40}\b([12]\.\d{2,3})\b', text)[:12]


def hltv_url(match: dict):
    for record in match.get('research') or []:
        url = str(record.get('source_url') or '')
        if record.get('stage', '').startswith('HLTV') and url.startswith('https://www.hltv.org/matches/'):
            return url
    return None


def analyse_match(url: str):
    row = {'url': url, 'observed_at': now()}
    page = fetch(url)
    row['status'] = page.get('status')
    if page.get('error'):
        return row
    soup = BeautifulSoup(page['text'], 'html.parser')
    teams = []
    for a in soup.select('a[href^="/team/"]'):
        href = a['href']
        name = a.get_text(' ', strip=True)
        if name and href not in {t['url'] for t in teams}:
            teams.append({'name': name, 'url': 'https://www.hltv.org' + href})
    row['teams'] = teams[:4]
    # The match page's own betting block (server-rendered for some regions).
    blocks = []
    for selector in ('.betting', '#betting', '.betting-table', '.odds', '[class*=betting]', '[class*=odds]'):
        for el in soup.select(selector)[:3]:
            blocks.append({'selector': selector, 'text': el.get_text(' ', strip=True)[:1200],
                           'html': str(el)[:2400]})
    row['betting_blocks'] = blocks[:6]
    body = soup.get_text(' ', strip=True)
    row['betting_mentions'] = re.findall(r'.{0,120}(?:bookmaker|odds).{0,120}', body, flags=re.I)[:12]
    row['numeric_pairs'] = numeric_pairs(body)
    row['sha256'] = page['sha256']
    return row


def analyse_analytics(url: str):
    row = {'url': url, 'observed_at': now()}
    page = fetch(url)
    row['status'] = page.get('status')
    if page.get('error'):
        return row
    soup = BeautifulSoup(page['text'], 'html.parser')
    body = soup.get_text(' ', strip=True)
    row['rankings_mentioned'] = sorted(set(re.findall(r'ranked \(#(\d+)\)', body)))
    row['ranking_sentences'] = re.findall(r'[^.]{0,90}(?:better ranked|worse ranked|World ranking|ranking)[^.]{0,90}\.', body, flags=re.I)[:10]
    row['form_sentences'] = re.findall(r'[^.]{0,80}(?:last \d+ matches|winning streak|losing streak)[^.]{0,80}\.', body, flags=re.I)[:10]
    row['bookmaker_sentences'] = re.findall(r'[^.]{0,90}(?:bookmaker|best odds|favorite)[^.]{0,90}\.', body, flags=re.I)[:10]
    row['numeric_pairs'] = numeric_pairs(body)
    row['blocks'] = snippets(soup, needles=('odds', 'bet', 'rank', 'form'), limit=8)
    row['sha256'] = page['sha256']
    return row


def analyse_team(url: str):
    row = {'url': url, 'observed_at': now()}
    page = fetch(url)
    row['status'] = page.get('status')
    if page.get('error'):
        return row
    soup = BeautifulSoup(page['text'], 'html.parser')
    body = soup.get_text(' ', strip=True)
    valve = re.search(r'Valve ranking\s*VRS.*?#(\d+)', body, flags=re.S)
    world = re.search(r'World ranking.*?#(\d+)', body, flags=re.S)
    points = re.search(r'(\d+(?:\.\d+)?)\s*(?:HLTV )?[Pp]oints', body)
    row['valve_ranking'] = int(valve.group(1)) if valve else None
    row['world_ranking'] = int(world.group(1)) if world else None
    row['ranking_points'] = float(points.group(1)) if points else None
    lineup = re.search(r'main lineup of [^ ]+ is (.*?)\.', body)
    row['hltv_main_lineup'] = [x.strip() for x in lineup.group(1).split(',')] if lineup else None
    row['ranking_snippets'] = re.findall(r'.{0,80}(?:World ranking|Ranking|points).{0,80}', body, flags=re.I)[:8]
    recent = []
    for a in soup.select('a[href^="/matches/"]'):
        href = a['href']
        text = a.get_text(' ', strip=True)
        parent = a.find_parent(['div', 'li', 'tr'])
        context = parent.get_text(' ', strip=True)[:220] if parent else text
        if href and context and href not in {r['url'] for r in recent}:
            recent.append({'url': 'https://www.hltv.org' + href, 'text': context})
        if len(recent) >= 25:
            break
    row['recent_match_links'] = recent
    row['blocks'] = snippets(soup, needles=('ranking', 'matches', 'match'), limit=8)
    row['sha256'] = page['sha256']
    return row


def valve_ranking_probe(team_names):
    """HLTV's dated mirror of Valve's regional VRS, filtered to the teams of interest."""
    out = {'pages': [], 'teams': {}, 'observed_at': now(),
           'note': 'Points are Valve VRS points as printed by HLTV; the official Valve markdown lives in the repository.'}
    today = datetime.now(timezone.utc).date()
    for back in range(0, 21, 7):
        day = today.fromordinal(today.toordinal() - back)
        stamp = f'{day:%Y}/{day:%B}/{day.day:02d}'.lower()
        for region in ('Europe', 'Americas', 'Asia'):
            url = f'https://www.hltv.org/valve-ranking/teams/{stamp}/region/{region}'
            page = fetch(url)
            entry = {'url': url, 'status': page.get('status'), 'error': page.get('error')}
            if page.get('status') != 200:
                out['pages'].append(entry)
                continue
            text = BeautifulSoup(page['text'], 'html.parser').get_text(' ', strip=True)
            rows = re.findall(r'#(\d+)\s*(.+?)\s*\((\d+) Valve points\)', text)
            entry['rows'] = len(rows)
            entry['sha256'] = page['sha256']
            out['pages'].append(entry)
            for rank, blob, points in rows:
                # Team name is the last token run before the points parenthesis.
                name = re.sub(r'\s+', ' ', blob).strip().split(' ')[-1] if blob else ''
                for wanted in team_names:
                    if wanted and wanted.casefold() in blob.casefold():
                        out['teams'].setdefault(wanted, []).append(
                            {'region': region, 'rank': int(rank), 'points': int(points),
                             'printed': blob[-80:], 'url': url, 'observed_at': now()})
            if rows:
                out['latest_date'] = day.isoformat()
                break
        if out.get('latest_date'):
            break
    return out


def bo3_probe():
    headers = {'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/', 'Accept': 'application/json'}
    out = {}
    base = 'https://api.bo3.gg/api/v1/matches'
    query = ('?scope=widget-matches&page[offset]=0&page[limit]=50&sort=-start_date'
             '&filter[matches.status][in]=upcoming,current&filter[matches.discipline_id][eq]=1'
             '&with=teams,tournament,odds,ai_predictions,games')
    page = fetch(base + query, headers=headers)
    out['matches_status'] = page.get('status')
    out['matches_error'] = page.get('error')
    if page.get('status') == 200:
        try:
            payload = json.loads(page['text'])
            results = payload.get('results') or []
            out['count'] = len(results)
            out['keys'] = sorted({k for r in results[:20] for k in r})
            out['sample'] = results[:3]
        except ValueError as exc:
            out['parse_error'] = str(exc)
            out['text_head'] = page['text'][:600]
    return out


def onexbet_probe():
    urls = [
        'https://1xbet.com/LineFeed/Get1x2_VZip?sports=3&count=50&lng=en&mode=4&country=1&partner=51&getEmpty=true',
        'https://1xbet.com/LineFeed/GetSportsShortZip?sports=3&lng=en&country=1&partner=51',
    ]
    out = []
    for url in urls:
        page = fetch(url, headers={'Accept': 'application/json'})
        row = {'url': url, 'status': page.get('status'), 'error': page.get('error'),
               'bytes': page.get('bytes')}
        if page.get('status') == 200:
            row['text_head'] = page['text'][:500]
        out.append(row)
    return out


def main() -> int:
    orig_path = ROOT / 'data' / 'origination.json'
    latest_path = ROOT / 'data' / 'latest.json'
    orig = json.loads(orig_path.read_text()) if orig_path.exists() else {}
    latest = json.loads(latest_path.read_text()) if latest_path.exists() else {}
    by_id = {m['id']: m for m in latest.get('matches', [])}
    fixtures = []
    seen = set()
    for match in orig.get('matches') or []:
        if match.get('origination') is not None:
            continue
        url = hltv_url(match)
        if not url or url in seen:
            continue
        seen.add(url)
        base = by_id.get(match['id'], {})
        fixtures.append({'hotspawn_id': match['id'],
                         'teams': [t.get('name') for t in match.get('teams') or []],
                         'competition': match.get('competition'),
                         'starts_at': match.get('starts_at'),
                         'hotspawn_url': base.get('source_url') or match.get('source_url'),
                         'match': analyse_match(url),
                         'analytics': analyse_analytics(url.replace('/matches/', '/betting/analytics/')),
                         'team_pages': []})
        for team in fixtures[-1]['match'].get('teams') or []:
            if team.get('url') and '/team/' in team['url']:
                fixtures[-1]['team_pages'].append(analyse_team(team['url']))
    wanted = sorted({t.get('name') for f in fixtures for t in (f.get('match') or {}).get('teams') or [] if t.get('name')})
    report = {
        'probe': 'arena-1fb85c47 unresolved-fixture ground truth',
        'valve_ranking': valve_ranking_probe(wanted),
        'generated_at': now(),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'counts': orig.get('counts'),
        'unresolved_count': len(fixtures),
        'fixtures': fixtures,
        'bo3': bo3_probe(),
        'onexbet': onexbet_probe(),
        'policy': ('Diagnostic only. No probability, pick or alias is written by this probe. '
                   'Hotspawn "% picked" and HLTV "Pick a winner" fan votes are recorded only if '
                   'present and are never used as inputs.'),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'unresolved': len(fixtures), 'out': str(OUT),
                      'bo3_status': report['bo3'].get('matches_status')}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
