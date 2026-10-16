"""Synthetic, isolated Day-4 UI vectors; removed after browser tests."""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '.')
from scripts import build, build_twc
from tests.test_twc_day4 import example, record, NOW

out = Path('site/_twc_day4_fixture')
out.mkdir(parents=True, exist_ok=True)
with patch('scripts.build_twc.datetime', wraps=datetime) as clock, patch('scripts.build.datetime', wraps=datetime) as shell_clock, patch('scripts.twc_research.load', return_value={'pages': [record()]}):
    clock.now.return_value = shell_clock.now.return_value = NOW
    data = example()
    body = build_twc.render(data, '../', Path('data'))
    (out / 'index.html').write_text(build.shell(data, 'twc', body, '../'))
