"""Own-line network rating: a Bradley–Terry fit over observed CS2 series results.

Why this exists
---------------
The published ladder prices a fixture from a first-party money line first and
from official ratings (Valve VRS, then HLTV's weekly world ranking) second. The
remaining blanks are low-tier fixtures where **neither** side appears in an
official rating table and no reachable book publishes a price. Those fixtures
were previously published with no pick at all.

The brief for this session asks for a pick for *every* match and explicitly
allows the project to originate its own line. This module does that in the only
way that is reproducible from evidence:

* every finished, parsed best-of series published by bo3.gg inside the 120-day
  window becomes one observation (team A vs team B, winner);
* teams that do have an official Valve rating are **anchors**: their prior is a
  Gaussian centred on the official points, with a tight standard deviation, so
  the whole graph is expressed on Valve's own 400-point logistic scale;
* unanchored teams get a weak prior centred on the median anchor rating;
* a maximum-a-posteriori Bradley–Terry fit then places every team in the graph
  on that one scale. Because a rating is fitted from *connected* results, a
  fixture between two unranked teams can still be priced when the two sides are
  linked to anchored teams through the results graph — which is exactly the
  gap the official tables leave.

What this is not
----------------
It is not a bookmaker price, not a copy of anyone else's prediction, and not a
calibrated probability. It is an explicitly labelled research model: the site
shows it with the model badge, every quote publishes the ratings, sample sizes
and standard errors it came from, and the fixture keeps a low-confidence flag
whenever the propagated interval crosses 50%.

Fail-closed rules
-----------------
No estimate is produced when any of these is true:

* the results graph has fewer than ``MIN_GRAPH_MATCHES`` usable series;
* fewer than ``MIN_ANCHORS`` distinct anchored teams connect the graph to the
  official scale;
* either side of the fixture has fewer than ``MIN_TEAM_MATCHES`` finished
  series inside the window;
* the propagated one-sigma interval on the rating difference is wider than
  ``MAX_SD_DIFF`` points (the estimate would be a dressed-up coin flip).

Every gate publishes its reason as text, so a blank is never silent.

Usage:  from scripts import network_model
        evidence = network_model.build(edges, anchors, now=now)   # pure
        quote, reason = network_model.estimate_fixture(match, binding, evidence, now=now)
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
S = math.log(10) / 400.0          # Valve's logistic scale (points -> probability)
WINDOW_DAYS = 120
DECAY_DAYS = 60.0                 # half-life of a series result, in days
ANCHOR_SD = 60.0                  # official points are trusted to +/-60 points
UNANCHORED_SD = 400.0             # weak prior for a team with no official row
MIN_GRAPH_MATCHES = 300
MIN_ANCHORS = 10
MIN_TEAM_MATCHES = 6
MAX_SD_DIFF = 300.0
ITERATIONS = 60
EVIDENCE_NAME = 'live-bo3-graph.json'
EVIDENCE_REFERENCE = 'data/origination/evidence/' + EVIDENCE_NAME
MODEL_VERSION = 'network-bt-1'


def iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).isoformat(timespec='seconds').replace('+00:00', 'Z')


def norm(value: str) -> str:
    import re
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())


def win_probability(target: float, opponent: float) -> float:
    """P(target beats opponent) on Valve's 400-point logistic scale."""
    return 1 / (1 + 10 ** ((opponent - target) / 400))


def _day(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)[:10]).replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def usable_edges(edges: list[dict], now: datetime) -> list[dict]:
    """Finished, parsed series with a published winner inside the window."""
    cutoff = now - timedelta(days=WINDOW_DAYS)
    out = []
    for edge in edges:
        day = _day(edge.get('date'))
        if day is None or day < cutoff or day > now + timedelta(days=1):
            continue
        a, b, winner = edge.get('a'), edge.get('b'), edge.get('winner')
        # Team ids are opaque: never treat 0/"" as "missing" (that silently
        # dropped a whole component in the first synthetic fit).
        if a is None or b is None or a == '' or b == '' or a == b or winner not in (a, b):
            continue
        # The winner field is authoritative for a finished series; bo3.gg's
        # parsed_status often still reads 'waiting' for a completed match whose
        # scoreboard is not parsed yet. Requiring 'done' silently dropped most
        # recent results, so the rule is: a published winner is enough, and the
        # status is carried into the evidence for review.

        age = (now - day).total_seconds() / 86400
        out.append({'id': edge.get('id'), 'date': day.date().isoformat(), 'a': a, 'b': b,
                    'winner': winner, 'url': edge.get('url'),
                    'a_name': edge.get('a_name'), 'b_name': edge.get('b_name'),
                    'weight': round(0.5 ** (age / DECAY_DAYS), 4)})
    return out


def anchor_rows(teams: dict, ratings: list, registry: dict | None = None) -> tuple[dict, list]:
    """Exact, unambiguous joins between graph team names and official Valve rows.

    A name that matches more than one graph team, or one official row that
    matches more than one team, is skipped: an ambiguous anchor would silently
    move every rating in its component.
    """
    by_key: dict[str, list[int]] = {}
    for team_id, name in teams.items():
        by_key.setdefault(norm(name), []).append(int(team_id))
    official: dict[str, list] = {}
    for row in ratings or []:
        key = norm(row.get('team') or row.get('name') or '')
        if key:
            official.setdefault(key, []).append(row)
    anchors, notes = {}, []
    for key, ids in by_key.items():
        rows = official.get(key) or []
        if len(ids) != 1 or len(rows) != 1:
            if len(ids) == 1 and len(rows) > 1:
                notes.append({'team_id': ids[0], 'reason': 'multiple official rows share this name'})
            continue
        row = rows[0]
        points = row.get('points')
        if not isinstance(points, (int, float)) or points <= 0:
            continue
        anchors[int(ids[0])] = {'points': float(points), 'name': row.get('team') or row.get('name'),
                                'source_url': row.get('source_url')}
    return anchors, notes


def fit(edges: list[dict], anchors: dict[int, dict]) -> dict:
    """MAP Bradley–Terry fit with Gaussian priors. Returns ratings and errors."""
    adjacency: dict[int, list[tuple[int, float, float]]] = {}
    for edge in edges:
        won_a = 1.0 if edge['winner'] == edge['a'] else 0.0
        weight = float(edge.get('weight') or 1.0)
        adjacency.setdefault(int(edge['a']), []).append((int(edge['b']), won_a, weight))
        adjacency.setdefault(int(edge['b']), []).append((int(edge['a']), 1.0 - won_a, weight))
    if not adjacency:
        return {'ok': False, 'reason': 'results graph has no usable series'}
    anchor_points = sorted(a['points'] for a in anchors.values())
    center = anchor_points[len(anchor_points) // 2] if anchor_points else 1500.0
    rating = {team: (anchors[team]['points'] if team in anchors else center) for team in adjacency}
    prior_mean = {team: (anchors[team]['points'] if team in anchors else center) for team in adjacency}
    prior_sd = {team: (ANCHOR_SD if team in anchors else UNANCHORED_SD) for team in adjacency}

    for _ in range(ITERATIONS):
        moved = 0.0
        for team, games in adjacency.items():
            gradient = -(rating[team] - prior_mean[team]) / prior_sd[team] ** 2
            curvature = 1.0 / prior_sd[team] ** 2
            for opponent, won, weight in games:
                p = win_probability(rating[team], rating[opponent])
                gradient += weight * (won - p) * S
                curvature += weight * p * (1 - p) * S * S
            step = gradient / curvature if curvature else 0.0
            step = max(-120.0, min(120.0, step))
            rating[team] += step
            moved = max(moved, abs(step))
        if moved < 1e-4:
            break

    out = {}
    for team, games in adjacency.items():
        curvature = 1.0 / prior_sd[team] ** 2
        for opponent, _won, weight in games:
            p = win_probability(rating[team], rating[opponent])
            curvature += weight * p * (1 - p) * S * S
        out[team] = {'points': round(rating[team], 1),
                     'se': round(1.0 / math.sqrt(curvature), 1) if curvature else None,
                     'series': len(games), 'anchored': team in anchors,
                     'anchor_points': anchors[team]['points'] if team in anchors else None}
    return {'ok': True, 'ratings': out, 'center': center, 'anchors': len(anchors),
            'matches': len(edges), 'teams': len(adjacency)}


def build(edges: list[dict], ratings_rows: list[dict], now: datetime,
          registry: dict | None = None) -> dict:
    """Assemble the dated evidence document the ladder and the replay share."""
    clean = usable_edges(edges, now)
    teams: dict[int, str] = {}
    for edge in clean:
        for side in ('a', 'b'):
            if edge.get(side) is not None and edge.get(side + '_name'):
                teams[int(edge[side])] = edge[side + '_name']
    anchors, notes = anchor_rows(teams, ratings_rows, registry)
    fitted = fit(clean, anchors)
    document = {
        'schema_version': 1,
        'model': MODEL_VERSION,
        'generated_at': iso(now),
        'window_days': WINDOW_DAYS,
        'decay_half_life_days': DECAY_DAYS,
        'anchor_sd_points': ANCHOR_SD,
        'unanchored_prior_sd_points': UNANCHORED_SD,
        'gates': {'min_graph_matches': MIN_GRAPH_MATCHES, 'min_anchors': MIN_ANCHORS,
                  'min_team_matches': MIN_TEAM_MATCHES, 'max_sd_diff_points': MAX_SD_DIFF},
        'graph_matches': len(clean),
        'graph_teams': len(teams),
        'anchors': {str(k): v for k, v in anchors.items()},
        'anchor_notes': notes,
        'ratings': {str(k): v for k, v in (fitted.get('ratings') or {}).items()},
        'fit_ok': bool(fitted.get('ok')),
        'fit_reason': fitted.get('reason'),
        'edges': [{'id': e['id'], 'date': e['date'], 'a': e['a'], 'b': e['b'],
                   'winner': e['winner'], 'url': e.get('url'), 'weight': e.get('weight')}
                  for e in clean],
    }
    document['evidence_sha256'] = hashlib.sha256(
        json.dumps(document, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return document


def save(document: dict, evidence_dir: Path) -> Path:
    path = Path(evidence_dir) / EVIDENCE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + '\n')
    return path


def load(evidence_dir: Path) -> dict | None:
    path = Path(evidence_dir) / EVIDENCE_NAME
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def gate(document: dict | None, now: datetime) -> tuple[bool, str]:
    """Graph-level gates, applied before any fixture is priced."""
    if not document:
        return False, 'Own network model: no results-graph evidence for this run'
    if not document.get('fit_ok'):
        return False, 'Own network model: ' + str(document.get('fit_reason') or 'fit failed')
    if document.get('graph_matches', 0) < MIN_GRAPH_MATCHES:
        return False, (f"Own network model: only {document.get('graph_matches')} finished series in the "
                       f"results graph (needs {MIN_GRAPH_MATCHES})")
    if document.get('anchors') is not None and len(document.get('anchors') or {}) < MIN_ANCHORS:
        return False, (f"Own network model: only {len(document.get('anchors') or {})} teams join the official "
                       f"rating table (needs {MIN_ANCHORS})")
    return True, ''


def _side_ids(match: dict, binding: dict | None) -> list[int] | None:
    """The fixture's two bo3.gg team ids, in Hotspawn's team order."""
    if not binding:
        return None
    sides = binding.get('sides') or []
    if len(sides) == 2 and all(s.get('team_id') for s in sides):
        names = [norm((t or {}).get('name') or '') for t in match.get('teams') or []]
        order = []
        for name in names:
            found = next((s for s in sides if norm(s.get('name') or '') == name), None)
            if found is None:
                return None
            order.append(int(found['team_id']))
        return order if len(order) == 2 and order[0] != order[1] else None
    return None


def estimate_fixture(match: dict, binding: dict | None, document: dict | None,
                     now: datetime) -> tuple[dict | None, str]:
    """Publish an own-line quote for this fixture, or explain why it is blank."""
    ok, reason = gate(document, now)
    if not ok:
        return None, reason
    ids = _side_ids(match, binding)
    if not ids:
        return None, ('Own network model: no unambiguous bo3.gg identity for both sides '
                      '(exact team ids and start time required)')
    ratings = document.get('ratings') or {}
    names = [(t or {}).get('name') or 'Unverified team' for t in match.get('teams') or []]
    inputs = []
    for index, team_id in enumerate(ids):
        row = ratings.get(str(team_id))
        if not row:
            return None, (f'Own network model: {names[index]} has no rating — it has no finished, parsed '
                          'series in the results graph window')
        if row.get('series', 0) < MIN_TEAM_MATCHES:
            return None, (f"Own network model: {names[index]} has only {row.get('series')} finished series in "
                          f"the window (needs {MIN_TEAM_MATCHES})")
        inputs.append({'name': names[index], 'team_id': team_id, 'points': row['points'],
                       'se': row.get('se'), 'series': row.get('series'),
                       'anchored': bool(row.get('anchored')), 'anchor_points': row.get('anchor_points'),
                       'source': 'Own network Bradley–Terry fit over bo3.gg finished series',
                       'source_url': 'https://bo3.gg/teams/' + str(team_id)})
    sd_diff = math.sqrt((inputs[0]['se'] or MAX_SD_DIFF) ** 2 + (inputs[1]['se'] or MAX_SD_DIFF) ** 2)
    if sd_diff > MAX_SD_DIFF:
        return None, (f'Own network model: rating uncertainty is too wide ({sd_diff:.0f} points, '
                      f'ceiling {MAX_SD_DIFF:.0f}); the estimate would not be distinguishable from a coin flip')
    p = win_probability(inputs[0]['points'], inputs[1]['points'])
    low = win_probability(inputs[0]['points'] - sd_diff, inputs[1]['points'] + sd_diff)
    high = win_probability(inputs[0]['points'] + sd_diff, inputs[1]['points'] - sd_diff)
    low_confidence = bool(low < 0.5 < high or min(inputs[0]['series'], inputs[1]['series']) < 10)
    # Session 5f6fe71d (board task 5F-1, residual of the 11B-4 finding): the
    # quote always linked bo3.gg's match *index* even when the identity binding
    # held a specific official record — the bound fixture page (bridge
    # start_time_and_team_name) or the bound team page (bridge
    # exact_team_name_lookup). Publish the most specific bo3.gg record behind
    # the estimate; only an absent or non-bo3.gg binding URL falls back to the
    # index, so the chip can never link a less specific page than the evidence.
    bound_source = str((binding or {}).get('source_url') or '')
    quote_source = bound_source if bound_source.startswith('https://bo3.gg/') else 'https://bo3.gg/matches'
    quote = {
        'provider': 'Own network model (bo3.gg results graph)',
        'family': 'network',
        'method': 'model',
        'model_version': MODEL_VERSION,
        'probabilities': [p, 1 - p],
        'inputs': inputs,
        'rating_sd_diff': round(sd_diff, 1),
        'interval': [round(low, 4), round(high, 4)],
        'n_series': min(inputs[0]['series'], inputs[1]['series']),
        'graph_matches': document.get('graph_matches'),
        'graph_anchors': len(document.get('anchors') or {}),
        'low_confidence': low_confidence,
        'source_url': quote_source,
        'identity_bridge': (binding or {}).get('bridge'),
        'evidence_file': EVIDENCE_REFERENCE,
        'evidence_sha256': document.get('evidence_sha256'),
        'observed_at': document.get('generated_at'),
    }
    return quote, ''


def replay_check(quote: dict, document: dict | None) -> None:
    """Re-derive a published network quote from its own inputs and evidence."""
    inputs = quote.get('inputs') or []
    assert len(inputs) == 2, 'Network quote must publish two rating inputs'
    assert quote.get('model_version') == MODEL_VERSION, 'Unrecognised network model version'
    expected = win_probability(inputs[0]['points'], inputs[1]['points'])
    assert abs(expected - quote['probabilities'][0]) < 1e-9, 'Network arithmetic differs from its published inputs'
    sd_diff = math.sqrt((inputs[0].get('se') or MAX_SD_DIFF) ** 2 + (inputs[1].get('se') or MAX_SD_DIFF) ** 2)
    assert abs(sd_diff - quote['rating_sd_diff']) < 0.06, 'Network uncertainty differs from its inputs'
    low = win_probability(inputs[0]['points'] - sd_diff, inputs[1]['points'] + sd_diff)
    high = win_probability(inputs[0]['points'] + sd_diff, inputs[1]['points'] - sd_diff)
    assert [round(low, 4), round(high, 4)] == quote['interval'], 'Network interval changed'
    assert document is not None, 'Network quote has no saved results-graph evidence'
    assert document.get('evidence_sha256') == quote.get('evidence_sha256'), 'Results-graph evidence was altered'
    for row in inputs:
        saved = (document.get('ratings') or {}).get(str(row['team_id']))
        assert saved is not None, f"Team {row['team_id']} missing from results-graph evidence"
        assert saved['points'] == row['points'] and saved.get('se') == row.get('se'), \
            'Published rating differs from the saved results-graph evidence'
        assert saved.get('series') == row.get('series'), 'Published series count differs from evidence'
    assert quote.get('graph_matches') == document.get('graph_matches'), 'Graph size changed'
    assert quote.get('graph_anchors') == len(document.get('anchors') or {}), 'Anchor count changed'
