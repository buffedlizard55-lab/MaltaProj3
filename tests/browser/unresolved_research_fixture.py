"""Build a fixture site that carries a *current* unresolved-pick research dossier.

The committed dossier in ``data/research/35440d12/`` is deliberately skipped by
``scripts.build.load_unresolved_research`` — it is older than
``UNRESOLVED_RESEARCH_MAX_AGE_HOURS`` and describes an inventory that has since
rotated. That is correct behaviour, but it means a browser check against the
real ``site/`` could never see the section this session wired in.

So this builder copies ``data/`` to a throwaway source directory, drops a
dossier dated at the pinned clock into it, and builds the whole site into
``site/_fixture/93c7475a/``. Nothing under ``data/`` is modified.
"""
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '.')
from scripts.build import build  # noqa: E402

NOW = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
OBSERVED = '2026-10-25T14:40:00Z'
OUT = Path('site/_fixture/93c7475a')

DOSSIER = {
    'schema_version': 1,
    'title': 'Unresolved and non-featured-line picks — HLTV first, then the esportsbooks',
    'prepared_at': OBSERVED,
    'research_window': {'from': '2026-10-25T14:39:00Z', 'to': OBSERVED},
    'prepared_by': 'arena-93c7475a (browser fixture)',
    'policy': ('Fixture data for the browser suite. Dated first-hand research on every open Hotspawn CS2 fixture '
               'whose pick is not a featured market line. Nothing here is a probability invented by a session.'),
    'method_order': [
        'HLTV identity and the official weekly world ranking (never a probability input by itself)',
        'Polymarket unique full-series match-winner books',
        'Thunderpick / Pinnacle / Rivalry / Stake / GG.BET prematch series prices',
        'Valve official regional standings model',
    ],
    'fixtures': [
        {
            'hotspawn_id': '1082697',
            'teams': ['BESTIA', 'paiN'],
            'competition': 'Circuit X Curitiba #4',
            'starts_at': '2026-10-25T18:00:00Z',
            'hltv_url': 'https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4',
            'checks': [
                {'stage': 'HLTV identity', 'verdict': 'confirmed',
                 'detail': 'Exact team names on HLTV\u2019s upcoming listing; start time agrees exactly; HLTV lists bo3.',
                 'sources': [{'url': 'https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4',
                              'source': 'HLTV.org match listing',
                              'detail': 'Upcoming-match card for these exact two names.', 'observed_at': OBSERVED}]},
                {'stage': 'HLTV world ranking', 'verdict': 'both-ranked',
                 'detail': 'BESTIA: rank 76 with 12 points; paiN: rank 32 with 55 points.',
                 'sources': [{'url': 'https://www.hltv.org/ranking/teams/2026/october/19',
                              'source': 'HLTV.org official world ranking',
                              'detail': '253 ranked teams on the dated publication.', 'observed_at': OBSERVED}]},
                {'stage': 'thunderpick-matches', 'verdict': 'refused-or-failed',
                 'detail': ('HTTP 403 \u2014 this surface did not answer the runner, so nothing can be said about its '
                            'coverage of this fixture. That is a limitation of the runner, not proof that no market '
                            'exists.'),
                 'sources': [{'url': 'https://thunderpick.io/esports/counter-strike',
                              'source': 'Thunderpick esportsbook',
                              'detail': 'Thunderpick surface read for the gap fixtures.', 'observed_at': OBSERVED}]},
            ],
            'resolution': 'stays-unresolved',
            'resolution_detail': ('A published pick exists but it is not a featured market line \u2014 it comes from an '
                                  'explicitly uncalibrated research rung.'),
        },
        {
            'hotspawn_id': '1086696',
            'teams': ['BORRACHEIROS', 'RED Canids Academy'],
            'competition': 'CCT South America 2026 Series #7',
            'starts_at': '2026-10-25T16:00:00Z',
            'hltv_url': ('https://www.hltv.org/matches/2399917/'
                         'borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7'),
            'checks': [
                {'stage': 'HLTV identity', 'verdict': 'confirmed-with-clock-delta',
                 'detail': 'Exact team names on HLTV\u2019s upcoming listing; HLTV start differs by -3600 s.',
                 'sources': [{'url': 'https://www.hltv.org/matches/2399917/'
                                     'borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7',
                              'source': 'HLTV.org match listing',
                              'detail': 'Upcoming-match card for these exact two names.', 'observed_at': OBSERVED}]},
                {'stage': 'polymarket-cs2-tag', 'verdict': 'reachable-no-exact-row',
                 'detail': 'HTTP 200 \u2014 surface readable, but no row with these exact two names.',
                 'sources': [{'url': 'https://polymarket.com/esports/counter-strike',
                              'source': 'Polymarket CS2 tag',
                              'detail': 'Polymarket surface read for the gap fixtures.', 'observed_at': OBSERVED}]},
            ],
            'resolution': 'expected-at-next-refresh',
            'resolution_detail': ('This fixture is not in the published snapshot at all: it appeared on Hotspawn after '
                                  'the last successful collection.'),
        },
    ],
    'limitations': [
        'This dossier records dated observations only. It writes no probability, no pick and no alias.',
        'Hotspawn "% picked" shares and HLTV fan votes are excluded from every calculation by policy.',
        'Current lineups, stand-ins and map vetoes are unverified for every fixture in this dossier.',
    ],
}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'data'
        shutil.copytree('data', source)
        dossier = source / 'research' / '93c7475a' / 'unresolved-research.json'
        dossier.parent.mkdir(parents=True, exist_ok=True)
        dossier.write_text(json.dumps(DOSSIER, indent=2))
        build(source, OUT, now=NOW)
    print(f'fixture site with a current dossier built into {OUT}')


if __name__ == '__main__':
    main()
