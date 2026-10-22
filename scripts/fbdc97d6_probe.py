"""Session-only (arena-fbdc97d6) esportsbook / line-source reachability probe.

Read-only. It fetches a fixed list of public pages that could carry a two-sided
prematch CS2 series price for the low-tier fixtures on the Hotspawn lobby,
records what each one actually returned, and reports whether the exact team
names of the open fixtures appear in the response.

It never writes a probability, a pick or an alias. The output is evidence for
``data/research/fbdc97d6/`` and is deleted from the tooling before the merge
(the captured JSON stays).

Usage: python -m scripts.fbdc97d6_probe [--out data/research/fbdc97d6]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')

# Exact Hotspawn team names of the fixtures open on 2026-10-22 (from the
# scheduled-fixture API snapshot). Used only to test whether a page even lists
# the fixture; no join and no price is taken from this script.
TEAMS = [
    'Vitalem Aerem', 'Rare Atom', 'benched gods', 'TitanFlow', 'Donstu',
    'Banda chuya', 'UNiTY', 'Apogee Betclic', 'Imperial', 'Turma do Pagode',
    'BESTIA', 'ShindeN', 'Ground Zero', 'Off Chops', 'NEXVOID', 'Alter Ego',
    'FlyQuest', 'Staqued', 'Rooster', 'Abyssal', 'HOTU', 'The Huns', '5star', '1WIN',
]

PAGES = [
    ('HLTV match listing', 'https://www.hltv.org/matches'),
    ('HLTV known match page', 'https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026'),
    ('HLTV world ranking', 'https://www.hltv.org/ranking/teams'),
    ('EGamersWorld CS2 matches', 'https://egamersworld.com/counterstrike/matches'),
    ('EGamersWorld known match', 'https://egamersworld.com/counterstrike/match/rW6Ymkl0D/benched-gods-vs-titanflow-EcLgERbZn'),
    ('bo3.gg matches', 'https://bo3.gg/matches'),
    ('bo3.gg known match', 'https://bo3.gg/matches/unity-vs-betclic-apogee-esports-22-10-2026'),
    ('Oddspedia CS2', 'https://www.oddspedia.com/esports/counter-strike-2'),
    ('Oddspedia match list API', 'https://oddspedia.com/api/v1/getMatchList?sport=counter-strike-2'),
    ('OddsPortal CS2', 'https://www.oddsportal.com/esports/counter-strike/'),
    ('Polymarket CS2', 'https://polymarket.com/esports/cs2'),
    ('Kalshi CS2 game series', 'https://kalshi.com/markets/kxcs2game/counter-strike-2-game'),
    ('Thunderpick CS', 'https://thunderpick.io/esports/counter-strike'),
    ('Bovada CS2', 'https://www.bovada.lv/sports/esports/counter-strike-2'),
    ('Pinnacle CS2', 'https://www.pinnacle.com/en/esports/counter-strike-2'),
    ('GG.BET CS', 'https://gg.bet/en/counter-strike'),
    ('BetBoom CS2', 'https://betboom.ru/sport/cs2'),
    ('1xBet CS2', 'https://1xbet.com/en/line/counter-strike-2'),
    ('Marathonbet CS2', 'https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/'),
    ('Betway CS2', 'https://www.betway.com/en/sports/esports/counter-strike-2'),
    ('DraftKings CS2', 'https://sportsbook.draftkings.com/leagues/esports/counter-strike-2'),
    ('Luckbox CS2', 'https://luckbox.com/esports/csgo'),
]

CHALLENGE = ('just a moment', 'cf-chl', 'challenge-platform', 'attention required',
             'enable javascript and cookies', 'captcha', 'access denied')
ODDS_RE = re.compile(r'\b([1-9]\.\d{1,2})\b')


def _title(html: str) -> str:
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip()[:180] if m else ''


def probe(name: str, url: str, teams: list[str]) -> dict:
    record = {'name': name, 'url': url, 'observed_at': datetime.now(UTC).isoformat(timespec='seconds')}
    try:
        r = requests.get(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'},
                         timeout=25, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001 - evidence records the actual failure
        record.update(status=None, error=f'{type(exc).__name__}: {exc}'[:300])
        return record
    body = r.text or ''
    record.update(status=r.status_code, final_url=r.url, bytes=len(body),
                  content_type=(r.headers.get('content-type') or '')[:80],
                  title=_title(body))
    lowered = body.lower()
    record['challenge_markers'] = [m for m in CHALLENGE if m in lowered][:4]
    found = {}
    for team in teams:
        index = lowered.find(team.lower())
        if index < 0:
            continue
        window = body[max(0, index - 260): index + 320]
        numbers = [n for n in ODDS_RE.findall(window) if 1.01 <= float(n) <= 100][:8]
        found[team] = {'offset': index, 'decimal_numbers_near_name': numbers,
                       'snippet': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', window)).strip()[:320]}
    record['teams_on_page'] = found
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('data/research/fbdc97d6'))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = [probe(name, url, TEAMS) for name, url in PAGES]
    document = {
        'session': 'arena-fbdc97d6',
        'purpose': ('Read-only reachability probe of line sources that could price low-tier Hotspawn '
                    'CS2 fixtures. A page appearing here is not a price and no value is used as a pick.'),
        'observed_at': datetime.now(UTC).isoformat(timespec='seconds'),
        'team_names_checked': TEAMS,
        'results': results,
    }
    (args.out / 'esportsbook-probe.json').write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n')
    lines = ['# Esportsbook / line-source probe — arena-fbdc97d6', '',
             f"Observed {document['observed_at']}. Read-only. A page appearing here is not a price.", '',
             '| Source | HTTP | Teams of the open fixtures found | Challenge markers | Title |',
             '| --- | --- | --- | --- | --- |']
    for r in results:
        status = r.get('status') if r.get('status') is not None else f"error: {r.get('error', '')[:60]}"
        teams = ', '.join(r.get('teams_on_page') or {}) or '—'
        marks = ', '.join(r.get('challenge_markers') or []) or '—'
        lines.append(f"| {r['name']} | {status} | {teams} | {marks} | {r.get('title') or '—'} |")
    (args.out / 'esportsbook-probe.md').write_text('\n'.join(lines) + '\n')
    print(f"probed {len(results)} sources -> {args.out / 'esportsbook-probe.json'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
