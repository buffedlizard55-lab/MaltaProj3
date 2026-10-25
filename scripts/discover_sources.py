"""Public-source diagnostics. No logins, private endpoints or challenge bypasses."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

OUT = Path('.cache/discovery')


def fetch(url: str, label: str, report: list[dict], out_dir: Path = OUT) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    entry = {'url': url, 'label': label, 'observed_at': datetime.now(timezone.utc).isoformat()}
    try:
        req = Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; HotspawnCoverage/1.0; public-source research)',
                'Accept': 'text/html,application/json',
            },
        )
        with urlopen(req, timeout=40) as response:
            body = response.read(6_000_000)
            entry.update(
                status=response.status,
                content_type=response.headers.get('Content-Type'),
                final_url=response.url,
                date=response.headers.get('Date'),
                sha256=hashlib.sha256(body).hexdigest(),
                bytes=len(body),
            )
        text = body.decode('utf-8', errors='replace')
        (out_dir / f'{label}.txt').write_text(text)
        print(f'{label}: {entry["status"]}, {len(body)} bytes; {url}', flush=True)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        entry.update(status=getattr(exc, 'code', None), error=str(exc))
        print(f'{label}: {exc}; {url}', flush=True)
        text = ''
    report.append(entry)
    return text


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: list[dict] = []

    if os.environ.get('SOURCE_STAGE') == 'contracts':
        urls = {
            'hotspawn-fixtures-client': 'https://play.hotspawn.com/chunk-KNRGAKZR.js',
            'hotspawn-fixtures-api': 'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1',
            'polymarket-cs2-tag': 'https://gamma-api.polymarket.com/tags/slug/cs2',
            'polymarket-cs2-events': 'https://gamma-api.polymarket.com/events?tag_slug=cs2&active=true&closed=false&limit=100&offset=0',
            'polymarket-cs2-events-page-2': 'https://gamma-api.polymarket.com/events?tag_slug=cs2&active=true&closed=false&limit=100&offset=100',
            'thunderpick-api': 'https://thunderpick.io/api/matches?gameIds=6',
            'ggbet-cs2': 'https://gg.bet/en-is/next-to-go?hoursAhead=168&sportId=esports_counter_strike',
            'rivalry-cs2': 'https://www.rivalry.com/esports/counter-strike-betting',
        }
        for label, url in urls.items():
            body = fetch(url, label, report, OUT)
            if label == 'polymarket-cs2-events':
                try:
                    events = json.loads(body)
                    event = next(e for e in events if 'gothic' in e.get('slug', ''))
                    market = next(m for m in event['markets'] if m.get('sportsMarketType') == 'moneyline')
                    token = json.loads(market['clobTokenIds'])[0]
                    fetch(f'https://clob.polymarket.com/book?token_id={token}', 'polymarket-example-book', report, OUT)
                except Exception as exc:  # noqa: BLE001
                    print('Order book discovery:', str(exc), flush=True)
            time.sleep(1)
        (OUT / 'report.json').write_text(json.dumps(report, indent=2))
        return 0

    urls = {
        'hotspawn-robots': 'https://play.hotspawn.com/robots.txt',
        'hotspawn-lobby': 'https://play.hotspawn.com/lobby',
        'hotspawn-cs2': 'https://play.hotspawn.com/cs2-pickems',
        'hltv-robots': 'https://www.hltv.org/robots.txt',
        'hltv-matches': 'https://www.hltv.org/matches',
        'polymarket-cs2': 'https://polymarket.com/esports/cs2',
        'polymarket-gamma': 'https://gamma-api.polymarket.com/events?active=true&closed=false&limit=5',
        'thunderpick-cs2': 'https://thunderpick.io/esports/counter-strike',
        'pinnacle-esports': 'https://www.pinnacle.com/en/esports-hub/cs2',
    }
    texts = {}
    for label, url in urls.items():
        texts[label] = fetch(url, label, report, OUT)
        time.sleep(1)

    for root in ['hotspawn-lobby', 'polymarket-cs2', 'thunderpick-cs2']:
        origin = urls[root]
        found_scripts = re.findall(r'<script[^>]*\bsrc=[\"\']([^\"\']+)', texts[root])
        print(f'{root}: script sources {found_scripts[:30]}', flush=True)
        for i, src in enumerate(found_scripts[:20]):
            script_url = urljoin(origin, src)
            if urlparse(script_url).netloc != urlparse(origin).netloc:
                continue
            body = fetch(script_url, f'{root}-script-{i}', report, OUT)
            if root == 'hotspawn-lobby':
                print('Hotspawn referenced URLs:', sorted(set(re.findall(r'https?://[^\s\"\'<>`]+', body)))[:80], flush=True)
            time.sleep(0.4)

    (OUT / 'report.json').write_text(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
