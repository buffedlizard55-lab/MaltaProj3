"""Mount the dated upset review page for browser QA; removed after the run.

The page is rendered from the real ``data/edge-review.json`` so the browser test measures what
actually ships, and a manifest of the expected row counts and displayed percentages is written next
to it. The spec reads that manifest instead of hard-coding numbers, so the check cannot silently
drift away from the data it is supposed to prove.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '.')
from scripts import build, build_edge  # noqa: E402

OUT = Path('site/_edge_review_fixture')
EDGE = Path('data/edge-review.json')
LATEST = Path('data/latest.json')
NOW = datetime(2026, 10, 17, 6, 0, 0, tzinfo=timezone.utc)

OUT.mkdir(parents=True, exist_ok=True)
inventory = json.loads(LATEST.read_text())
with patch('scripts.build.datetime', wraps=datetime) as clock:
    clock.now.return_value = NOW
    body = build_edge.edge_review(inventory, '../', EDGE)
    (OUT / 'index.html').write_text(build.shell(inventory, 'edge', body, '../'))

data = build_edge.load_edge(EDGE)
displayed = []
for fixture in data['day_four_refresh']['fixtures']:
    for team, value in ((fixture.get('market') or {}).get('derived_probabilities') or {}).items():
        displayed.append({'team': team, 'text': f'{value * 100:.1f}%'})
(OUT / 'manifest.json').write_text(json.dumps({
    'group_series': len(data['group_stage_record']['series']),
    'series_urls': [x['url'] for x in data['group_stage_record']['series']],
    'sweeps': data['group_stage_record']['summary']['sweeps'],
    'refresh_rows': len(data['day_four_refresh']['fixtures']),
    'displayed_probabilities': displayed,
    'day_five_rows': len(data['day_five_card']['matches']),
    'day_five_blanks': sum(1 for x in data['day_five_card']['matches'] if x['teams'] is None),
    'guidance_principles': len(data['day_four_guidance']['principles']),
    'limitations': len(data['limitations']),
    'single_provider_notes': sum(1 for x in data['day_four_refresh']['fixtures'] if not (x.get('market') or {}).get('market_id')),
}) + '\n')
print('edge review fixture written for browser QA')
