"""Bounded first-party research; no login, API secrets or challenge bypass."""
import gzip
import json
from pathlib import Path
from scripts.sources import Client, SourceError

out = Path('.cache/source-audit')
client = Client(out)
for label, url in [
    ('hltv-matches', 'https://www.hltv.org/matches'),
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
