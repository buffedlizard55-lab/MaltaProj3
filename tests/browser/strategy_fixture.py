"""Build a synthetic leaderboard-plan page for the browser tests.

Writes site/_fixture/strategy/index.html (plus assets and data) from hand-made inputs and a pinned
clock, so the UI checks never depend on live data or the time they run at. The research files are the
committed, static ones in data/research/1112299f/.
"""
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '.')
from scripts import build_strategy as bs  # noqa: E402
from tests.test_strategy import fixture, match  # noqa: E402

NOW = datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc)


def main():
    out = Path('site/_fixture')
    if out.exists():
        shutil.rmtree(out)
    matches = [
        match('2001', 'Aurora', '9z', [0.69, 0.31], tier='s', starts='2026-10-16T14:00:00Z', locks='2026-10-16T13:54:00Z'),
        match('2002', 'Heroic', 'Envy', [0.635, 0.365], tier='b', starts='2026-10-16T10:00:00Z', locks='2026-10-16T09:54:00Z'),
        match('2003', 'MIBR', 'BC.Game', [0.55, 0.45], tier='b', starts='2026-10-16T10:00:00Z', locks='2026-10-16T09:54:00Z'),
        match('2004', 'Phantom', 'RoundsGG', [0.92, 0.08], tier='c', starts='2026-10-16T12:00:00Z', locks='2026-10-16T11:54:00Z'),
        match('2005', 'EAC', 'BOJONG', [0.961, 0.039], method='model', tier='c', starts='2026-10-16T12:00:00Z', locks='2026-10-16T11:54:00Z'),
        match('2006', 'Infinite', 'Insiders', None, tier='b', starts='2026-10-19T09:00:00Z', locks='2026-10-19T08:54:00Z', research=[
            {'stage': 'Primary: Polymarket', 'status': 'unresolved', 'detail': 'No unique exact-name, exact-start-time fixture.', 'source_url': 'https://polymarket.com/esports/cs2'},
            {'stage': 'Esportsbook line', 'status': 'unavailable', 'detail': 'No validated pair of prices.', 'source_url': 'https://thunderpick.io/esports/counter-strike'}]),
        match('2007', 'Gone', 'Already', [0.6, 0.4], tier='c', starts='2026-10-16T08:30:00Z', locks='2026-10-16T08:24:00Z'),
    ]
    fixtures = [fixture('2001', points=7, shares=(89, 11), n=20, tier_mult=3), fixture('2002', shares=(91, 9), n=80), fixture('2003', shares=(35, 65), n=79),
                fixture('2004', points=2, shares=(96, 4), n=51, tier_mult=1), fixture('2005', points=2, shares=(95, 5), n=59, tier_mult=1),
                fixture('2007', points=2, shares=(50, 50), n=10, tier_mult=1)]
    # Fixture 2001 mirrors the real Aurora vs 9z Day-3 decider (in the tournament pick'em) so the context block and the score slip render.
    matches[0]['competition'] = 'Thunderpick World Championship 2026'
    research = Path('data/research/1112299f')
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / 'data'
        (src / 'research/1112299f').mkdir(parents=True)
        (src / 'evidence').mkdir()
        shutil.copy('data/strategy-rules.json', src / 'strategy-rules.json')
        for name in ('hotspawn-contract.json', 'twc-results.json', 'hotspawn-tournament.json'):
            shutil.copy(research / name, src / 'research/1112299f' / name)
        (src / 'latest.json').write_text(json.dumps({'coverage_complete': True, 'inventory_observed_at': '2026-10-16T08:30:00Z'}))
        (src / 'origination.json').write_text(json.dumps({'source_snapshot_at': '2026-10-16T08:30:00Z', 'matches': matches}))
        (src / 'evidence/hotspawn-fixtures.json').write_text(json.dumps(fixtures))
        bs.build(src, out, now=NOW)
    shutil.copytree('assets', out / 'assets')
    shutil.copy('data/strategy-rules.json', out / 'data/strategy-rules.json')
    print('fixture page written to', out / 'strategy/index.html')


if __name__ == '__main__':
    main()
