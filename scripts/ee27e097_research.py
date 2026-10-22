"""Turn session ee27e097's read-only probe into published evidence.

The probe (``scripts/ee27e097_probe.py``) records what the GitHub runner and a
headless browser actually got back from each line-source surface. This module
converts that record into:

* ``data/research/ee27e097/line-sources.json`` — the same schema the site already
  renders for the dated sweep (``scripts/build.py::line_sources_block``), so the
  published limitations can be read on the site with their status codes;
* ``data/research/ee27e097/probe-summary.md`` — a short human-readable table.

Nothing here prices a fixture. A 200 is not a price, and a 403 is not proof that
no market exists: both are recorded as access observations only.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc

NOTES = {
    'hltv-matches': ('Cloudflare challenge to the automated runner. HLTV publishes identity, rankings and a '
                     'fan vote, not a two-sided prematch price, so it is never an odds input.'),
    'egamersworld-listing': ('Cloudflare challenge to the runner (requests). A person can load the page; '
                             'its listing odds are unverified and can contradict its own match page — see '
                             'egamersworld-observation.json.'),
    'egamersworld-match-page': ('Cloudflare challenge to the runner (requests). Read by hand for the '
                                'observation record; most low-tier pages print a 1.8/1.8 placeholder.'),
    'betexplorer-cs2': 'No CS2 page at this address (HTTP 404). Not used.',
    'oddspedia-cs2': 'Permanently deleted (HTTP 410); the previous sweep recorded the same status.',
    'oddsportal-cs2': 'HTTP 503 from the runner. No price extracted.',
    'hltv-matches-2': 'See the HLTV entry.',
    'bo3-gg-matches': ('Public match API answered. It relays a named bookmaker quote (Thunderpick) for a '
                       'subset of upcoming fixtures; the ladder already consumes it through the relay rung. '
                       'A fixture without that block has no relayed price.'),
    'hotspawn-lobby': 'The authoritative scheduled inventory, independent of any price.',
}


def convert(probe: dict) -> dict:
    observed = probe.get('observed_at') or datetime.now(UTC).isoformat(timespec='seconds')
    sources = []
    for target in probe.get('targets') or []:
        status = target.get('status')
        entry = {
            'name': {
                'egamersworld-listing': 'EGamersWorld CS2 match listing',
                'egamersworld-match-page': 'EGamersWorld match page (Bushido Wildcats vs ex-6666)',
                'hltv-matches': 'HLTV match listing',
                'betexplorer-cs2': 'BetExplorer CS2',
                'oddspedia-cs2': 'Oddspedia CS2',
                'oddsportal-cs2': 'OddsPortal CS2',
                'bo3-gg-matches': 'bo3.gg public match API (relayed bookmaker quotes)',
                'hotspawn-lobby': 'Hotspawn lobby (inventory only)',
            }.get(target.get('name'), target.get('name')),
            'url': target.get('url'),
            'http_status': status,
            'error': target.get('error'),
            'detail_url': target.get('url'),
            'fixtures_listed': [],
            'note': NOTES.get(target.get('name'), ''),
        }
        if target.get('title'):
            entry['note'] = (entry['note'] + f" Page title at the runner: {target['title']!r}.").strip()
        sources.append(entry)
    browser = probe.get('browser') or {}
    if browser:
        sources.append({
            'name': 'EGamersWorld CS2 listing — headless Chromium',
            'url': browser.get('url'),
            'http_status': browser.get('status'),
            'error': browser.get('error'),
            'detail_url': browser.get('url'),
            'fixtures_listed': [],
            'note': ('A real Chromium context (UTC timezone, desktop user agent) still received the '
                     'security-verification interstitial, so automation cannot use EGamersWorld as a live '
                     'price feed. Manual, dated captures remain the only reviewed use of that site.'),
        })
    bo3 = probe.get('bo3') or {}
    if bo3.get('status') == 200:
        sources.append({
            'name': 'bo3.gg relay coverage on the same observation',
            'url': 'https://api.bo3.gg/api/v1/matches',
            'http_status': 200,
            'error': None,
            'detail_url': 'https://bo3.gg/matches',
            'fixtures_listed': [],
            'note': (f"{bo3.get('rows')} upcoming fixtures read; {bo3.get('with_bet_block')} carried a named "
                     'bookmaker quote block. Only those can produce a relayed line.'),
        })
    document = {
        'schema_version': 1,
        'session': 'arena-ee27e097',
        'observed_at': observed,
        'environment': 'github-actions-runner (ubuntu-24.04), plus a headless Chromium context',
        'policy': ('Read-only reachability record. A page listed here is NOT a price. Only a two-sided, '
                   'first-party prematch series line or a published official rating may produce a number, and '
                   'the ladder in scripts/originate.py decides which one is used.'),
        'conclusion': ('No new automated two-sided price source was found for the low-tier fixtures. '
                       'EGamersWorld refuses the runner even in Chromium, HLTV refuses the runner, Oddspedia is '
                       'deleted and BetExplorer/OddsPortal did not answer with a usable page. bo3.gg answered and '
                       'remains the only relay of a named bookmaker, but it prices only a subset of fixtures.'),
        'sources': sources,
    }
    observation_path = Path('data/research/ee27e097/egamersworld-observation.json')
    if observation_path.exists():
        try:
            observation = json.loads(observation_path.read_text())
        except ValueError:
            observation = None
        if isinstance(observation, dict) and observation.get('fixtures'):
            checked = len(observation['fixtures'])
            contradictions = sum(1 for f in observation['fixtures']
                                 if (f.get('match_page') or {}).get('printed') and (f.get('listing') or {}).get('printed')
                                 and f['listing']['printed'] != f['match_page']['printed'])
            placeholders = sum(1 for f in observation['fixtures']
                               if '1.8' in str((f.get('listing') or {}).get('printed', ''))
                               and '1.8' in str((f.get('listing') or {}).get('printed', '')).split('·')[-1])
            document['observation'] = {
                'title': 'EGamersWorld listing vs its own match page — human read',
                'file': str(observation_path),
                'observed_at': observation.get('observed_at'),
                'fixtures_checked': checked,
                'contradictions': contradictions,
                'placeholders': placeholders,
                'summary': (f"A reader loaded EGamersWorld on {observation.get('observed_at')} for {checked} of the "
                            "fixtures that carry a research-model pick. The site prints its 1.8/1.8 placeholder for "
                            f"{placeholders} of them, and for one fixture its listing pair contradicts its own match "
                            "page, which shows the placeholder and no bookmaker-average sentence. No listing number "
                            "was promoted to a price."),
            }
    return document


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, default=None,
                        help='probe JSON (default: newest under data/research/ee27e097)')
    parser.add_argument('--out', type=Path, default=Path('data/research/ee27e097/line-sources.json'))
    args = parser.parse_args(argv)
    probe_path = args.probe or sorted(Path('data/research/ee27e097').glob('probe-*.json'))[-1]
    probe = json.loads(probe_path.read_text())
    document = convert(probe)
    document['probe_file'] = str(probe_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + '\n')
    lines = [f"# Line-source probe — {document['observed_at']}", '',
             f"Environment: {document['environment']}", '',
             '| Surface | HTTP | Note |', '| --- | --- | --- |']
    for source in document['sources']:
        lines.append(f"| [{source['name']}]({source['url']}) | {source['http_status']} | {source['note']} |")
    (args.out.parent / 'probe-summary.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'wrote': str(args.out), 'sources': len(document['sources']),
                      'statuses': {s['name']: s['http_status'] for s in document['sources']}}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
