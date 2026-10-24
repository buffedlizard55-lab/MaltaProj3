"""Read-only probe for the fallback-line question (session 3877d48d).

Why this exists
---------------
Every active Hotspawn CS2 fixture currently has a pick, but 15 of them do not
come from the featured Polymarket order book: 5 consensus, 5 single-bookmaker,
1 aggregated EGamersWorld reference and 4 Valve-rating research models.  The
brief asks for an independently researched way to price *those* fixtures, HLTV
first and esportsbooks second, and for the limits of each method to be
published.

This probe only **records** what a source publishes.  It never writes a
probability, a pick or an alias: the publisher's ladder remains the only path to
a published number.  It exists because the research sandbox cannot reach these
hosts, while a GitHub runner can.

Output
------
`data/research/3877d48d/probe.json` with, per source: URL, HTTP status, byte
count, SHA-256, the literal discovery facts (``<time datetime>`` attributes,
schema.org ``startDate`` values and the decimal-odds tokens on the page) and a
short text excerpt.  Raw HTML is archived beside it (``raw/``) so a reviewer can
check the parse offline.

CLI
---
    python -m scripts.3877d48d_probe            # fetch, parse, write the dossier
    python -m scripts.3877d48d_probe --parse raw/  # re-parse archived HTML only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('data/research/3877d48d')
UTC = timezone.utc

#: One entry per active fixture whose pick is not a featured Polymarket line.
#: ``egw``/``hltv`` are the first-hand pages read while researching them on
#: 2026-10-24; a missing page is recorded as a limitation, never guessed.
TARGETS = [
    {'id': '1083121', 'teams': ['Projeto do KinGui', 'MEIA NOITE'], 'method': 'consensus',
     'egw': None,
     'hltv_query': 'Tropa do KinGui MEIA NOITE'},
    {'id': '1081154', 'teams': ['BakS', 'ILLYRIANS'], 'method': 'consensus',
     'egw': None, 'hltv_query': 'BAKS ILLYRIANS CCT Europe Series 12'},
    {'id': '1083122', 'teams': ['LOS NINOS', 'BORRACHEIROS'], 'method': 'consensus',
     'egw': None, 'hltv_query': 'LOS NINOS BORRACHEIROS'},
    {'id': '1083123', 'teams': ['Grêmio', 'Yawara'], 'method': 'consensus',
     'egw': None, 'hltv_query': 'Gremio Yawara CCT South America'},
    {'id': '1079200', 'teams': ['Color', 'ex-Zero Tenacity'], 'method': 'consensus',
     'egw': None, 'hltv_query': 'Color ex-Zero Tenacity NODWIN'},
    {'id': '1079198', 'teams': ['Metizport', 'BakS'], 'method': 'bookmaker',
     'egw': 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/metizport-vs-baks-esports-qOJcZA7Wgq',
     'hltv_query': 'Metizport BAKS NODWIN Clutch Series 13'},
    {'id': '1081156', 'teams': ['Spirit Academy', 'LFO 10'], 'method': 'bookmaker',
     'egw': None,
     'hltv_query': 'Spirit Academy LFO 10 CCT Europe Series 12'},
    {'id': '1081158', 'teams': ['FORZE Reload', 'ex-RUSTEC'], 'method': 'bookmaker',
     'egw': None,
     'hltv_query': 'FORZE Reload RUSTEC CCT Europe Series 12'},
    {'id': '1082859', 'teams': ['NEXVOID', 'Alter Ego'], 'method': 'bookmaker',
     'egw': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/nexvoid-vs-alter-ego-HfdcJeXmT',
     'hltv_query': 'NEXVOID Alter Ego DFRAG Invitational'},
    {'id': '1082860', 'teams': ['FlyQuest', 'Staqued'], 'method': 'bookmaker',
     'egw': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/flyquest-vs-staqued-zawJ-Q52S3',
     'hltv_query': 'FlyQuest Staqued DFRAG Invitational'},
    {'id': '1082858', 'teams': ['Ground Zero', 'Off Chops'], 'method': 'reference',
     'egw': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d',
     'hltv_query': 'Ground Zero Off Chops DFRAG Invitational'},
    {'id': '1082996', 'teams': ['Acend', 'UNiTY'], 'method': 'model',
     'egw': 'https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf',
     'hltv_query': 'Acend UNiTY NODWIN Clutch Series 13'},
    {'id': '1082861', 'teams': ['Rooster', 'Abyssal'], 'method': 'model',
     'egw': 'https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8',
     'hltv_query': 'Rooster Abyssal DFRAG Invitational'},
    {'id': '1082792', 'teams': ['HOTU', 'The Huns'], 'method': 'model',
     'egw': 'https://egamersworld.com/counterstrike/match/EkalRNMvVx/hotu-vs-the-huns-esports-SfdtzDhiK',
     'hltv_query': 'HOTU The Huns GLuck Moscow Cyber Games'},
    {'id': '1082793', 'teams': ['5star', '1WIN'], 'method': 'model',
     'egw': 'https://egamersworld.com/counterstrike/match/EkalRNMvVx/1win-vs-5star-esports-4hTvdd1uN',
     'hltv_query': '1win 5star GLuck Moscow Cyber Games'},
]

HOTSPAWN_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
                '?sport_alias=cs2&status=scheduled&tenantId=1')

_TIME = re.compile(r'<time[^>]*\bdatetime="([^"]+)"', re.I)
_START = re.compile(r'"(?:startDate|start_date)"\s*:\s*"([^"]+)"')
_ISO = re.compile(r'20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})')
_ODDS = re.compile(r'(?<![\d.])(\d{1,3}\.\d{1,3})(?![\d.])')


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()


def facts(html: str) -> dict:
    """Literal discovery facts from one response; no inference, no joining."""
    times = []
    for value in _TIME.findall(html) + _START.findall(html):
        times.append(value)
    # Keep every distinct ISO-8601 instant the page states, in page order.
    iso = []
    for value in times + _ISO.findall(html):
        if value not in iso:
            iso.append(value)
    # Decimal tokens that look like odds, with a little surrounding context so a
    # reviewer can see whether a price really belongs to a team name.
    odds = []
    for m in _ODDS.finditer(html):
        value = float(m.group(1))
        if 1.0 <= value <= 60.0:
            context = re.sub(r'<[^>]+>', ' ', html[max(0, m.start() - 120):m.end() + 60])
            odds.append({'value': m.group(1),
                         'context': re.sub(r'\s+', ' ', context).strip()[:180]})
        if len(odds) >= 40:
            break
    return {'time_attributes': times[:24], 'iso_instants': iso[:24], 'odds_tokens': odds[:12]}


def fetch(url: str, artifact: Path, session) -> dict:
    from scripts.domain import iso
    record = {'url': url, 'observed_at': iso(datetime.now(UTC))}
    try:
        response = session.get(url, timeout=45, headers={
            'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/131.0 Safari/537.36'),
            'Accept-Language': 'en-US,en;q=0.9',
        })
        record['status'] = response.status_code
        record['bytes'] = len(response.content)
        record['sha256'] = _sha(response.text)
        if response.status_code == 200:
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(response.text, encoding='utf-8')
            record['raw'] = str(artifact)
            record.update(facts(response.text))
        else:
            record['error'] = f'HTTP {response.status_code}'
    except Exception as exc:  # noqa: BLE001 - recorded, never retried silently here
        record['error'] = f'{type(exc).__name__}: {exc}'[:300]
    return record


def main(argv=None) -> int:
    import requests  # declared in requirements.txt

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parse', type=Path, help='re-parse archived HTML instead of fetching')
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    if args.parse:
        result = {'schema_version': 1, 'mode': 'offline-reparse',
                  'parsed_at': datetime.now(UTC).isoformat(),
                  'pages': [{'raw': str(p), 'sha256': _sha(p.read_text(encoding='utf-8', errors='replace')),
                             **facts(p.read_text(encoding='utf-8', errors='replace'))}
                            for p in sorted(args.parse.glob('*.html'))]}
        (args.output / 'probe.json').write_text(json.dumps(result, indent=1) + '\n')
        print(json.dumps(result, indent=1))
        return 0

    session = requests.Session()
    result = {'schema_version': 1, 'mode': 'live',
              'generated_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
              'policy': ('Read-only. No probability, pick or alias is written here. '
                         'Fan votes and Hotspawn "% picked" are never recorded as prices.'),
              'inventory': fetch(HOTSPAWN_API, args.output / 'raw' / 'hotspawn-fixtures.json', session),
              'fixtures': []}
    for target in TARGETS:
        entry = {'id': target['id'], 'teams': target['teams'], 'published_method': target['method']}
        if target.get('egw'):
            entry['egw'] = fetch(target['egw'], args.output / 'raw' / f'egw-{target["id"]}.html', session)
        else:
            entry['egw'] = {'url': None, 'error': 'no EGamersWorld match page found by exact team pair'}
        result['fixtures'].append(entry)
        print(f"{target['id']} {target['teams'][0]} vs {target['teams'][1]}: "
              f"egw={entry['egw'].get('status') or entry['egw'].get('error')}", flush=True)
    (args.output / 'probe.json').write_text(json.dumps(result, indent=1) + '\n')
    print(f"wrote {args.output / 'probe.json'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
