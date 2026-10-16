"""Parse HLTV's own published match facts; no crowd votes or inferred scores.

The original page remains the evidence. A missing selector or incomplete value
stays None; the parser never derives a series score from a map or vice versa.
Epoch attributes, not the page's localized clock text, define the schedule.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scripts.domain import iso, timestamp, name_key


def parse_match(text: str) -> dict:
    soup = BeautifulSoup(text, 'html.parser')
    teams, scores = [], []
    for side in ('team1', 'team2'):
        panel = soup.select_one(f'.{side}-gradient')
        name = panel.select_one('.teamName') if panel else None
        score = panel.select_one(':scope > .won, :scope > .lost, :scope > .tie') if panel else None
        teams.append(name.get_text(' ', strip=True) if name else None)
        value = score.get_text(strip=True) if score else ''
        scores.append(int(value) if value.isdigit() else None)
    date = soup.select_one('.timeAndEvent .date[data-unix]')
    start = timestamp(date.get('data-unix')) if date else None
    event = soup.select_one('.timeAndEvent .event a[href^="/events/"]')
    status = soup.select_one('.timeAndEvent .countdown')
    finished = bool(status and status.get_text(' ', strip=True) == 'Match over')
    lineups = []
    for panel in soup.select('.lineup'):
        label = panel.select_one('.box-headline a[href^="/team/"]')
        players = [p.get_text(' ', strip=True) for p in panel.select('.players .text-ellipsis')]
        # A photo, a coach, six players or a duplicated nickname is not five
        # unique player names. Never pick the first five to fit a rating row.
        complete = len(players) == 5 and len({name_key(p) for p in players if p}) == 5
        if label:
            lineups.append({'name': label.get_text(' ', strip=True),
                            'roster': players if complete else None})
    maps = []
    for panel in soup.select('.mapholder'):
        label = panel.select_one('.mapname')
        values = [panel.select_one(f'.results-{side} .results-team-score') for side in ('left', 'right')]
        values = [v.get_text(strip=True) if v else '' for v in values]
        map_teams = [panel.select_one(f'.results-{side} .results-teamname') for side in ('left', 'right')]
        map_teams = [n.get_text(' ', strip=True) if n else None for n in map_teams]
        if label and all(v.isdigit() for v in values) and map_teams == teams:
            maps.append({'map': label.get_text(' ', strip=True), 'a': int(values[0]), 'b': int(values[1])})
    veto = soup.select_one('.veto-box')
    best = re.search(r'\bBest of ([1357])\b', veto.get_text(' ', strip=True) if veto else '')
    return {'teams': teams, 'starts_at': iso(start) if start else None,
            'event': event.get_text(' ', strip=True) if event else None,
            'event_url': 'https://www.hltv.org' + event['href'] if event else None,
            'finished': finished, 'score': scores if finished and all(v is not None for v in scores) else None,
            'maps': maps, 'lineups': lineups, 'best_of': int(best[1]) if best else None}
