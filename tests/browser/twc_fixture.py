"""Isolated synthetic TWC browser fixture; never part of the published feed."""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '.')
from scripts import build, build_twc
from tests.test_twc import example_data, NOW

out = Path('site/_twc_fixture')
out.mkdir(parents=True, exist_ok=True)
with patch('scripts.build_twc.datetime', wraps=datetime) as clock, patch('scripts.build.datetime', wraps=datetime) as shell_clock:
    clock.now.return_value = shell_clock.now.return_value = NOW
    data = example_data()
    body = build_twc.render(data, '../', Path('data'))
    (out / 'index.html').write_text(build.shell(data, 'twc', body, '../'))
