"""Isolated synthetic final-day UI. Never part of the deployed artifact."""
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
sys.path.insert(0, '.')
from scripts import day5, build
from tests.test_day5 import data, NOW, record

out = Path('site/_day5_fixture'); out.mkdir(parents=True, exist_ok=True)
d = data()
with patch('scripts.twc_research.load', return_value={'pages': [record(start='2026-10-18T14:00:00Z')]}), patch('scripts.twc_research.retained_discovery_urls', return_value=set()), patch('scripts.build.datetime', wraps=datetime) as clock:
    clock.now.return_value = NOW
    guide = day5.derive(d, Path('data'), NOW)
    html = build.heading('Synthetic test fixture', 'Day 5 UI safety tests', 'Not live data.') + day5.render(guide, '../')
    (out / 'index.html').write_text(build.shell(d, 'twc', html, '../'))
