"""Leaderboard plan: a points-aware "contrarian but not stupid" pick for every active fixture.

Inputs (all already produced by the pipeline or saved as dated research):
  data/origination.json      complete picks: our own probabilities and their basis per fixture
  data/latest.json           canonical inventory (freshness / coverage flags)
  data/evidence/hotspawn-fixtures.json   raw fixture API (points, pick counts) when present
  data/strategy-rules.json   the thresholds below, in plain data
  data/research/1112299f/    dated first-party research: Hotspawn contract, TWC results

Output: strategy/index.html - a self-contained, mobile-first page.

What it does NOT do: it never reads Hotspawn "% picked" as a probability, never
changes a number in origination.json, and never invents a pick for a fixture that
has no external line or rating (those go to an explicit Unresolved section).

Usage: python -m scripts.build_strategy [--source data] [--output site]
"""
from __future__ import annotations

import argparse
import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.domain import timestamp
from scripts.pick_safety import (body_attributes, card_attributes, presentation, status_html)

MALTA = ZoneInfo('Europe/Malta')
REPO = 'https://github.com/buffedlizard55-lab/MaltaProj3'
LOBBY = 'https://play.hotspawn.com/lobby'
MONEY = {'market', 'bookmaker', 'consensus'}
METHOD_LABEL = {'market': 'Prediction market', 'bookmaker': 'Bookmaker line', 'consensus': 'Median of money sources',
                'reference': 'Aggregated bookmaker average (third-party)', 'model': 'Research model (uncalibrated)'}
RESEARCH_DIR = 'research/1112299f'


def e(value) -> str:
    return html.escape(str(value), quote=True)


def ext(url, text) -> str:
    return f'<a class="src" href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(text)} <span aria-hidden="true">↗</span></a>'


def when(value) -> str:
    dt = timestamp(value)
    if not dt:
        return '<span class="unverified">— unverified</span>'
    return f'<time datetime="{e(dt.strftime("%Y-%m-%dT%H:%M:%SZ"))}">{e(dt.astimezone(MALTA).strftime("%a %d %b, %H:%M"))} <small>({e(dt.strftime("%H:%M"))} UTC)</small></time>'


def pct(x) -> str:
    return f'{x * 100:.1f}%'


# ----------------------------------------------------------------------------- inputs

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def load_inputs(source: Path) -> dict:
    rules = read_json(source / 'strategy-rules.json')
    if not rules:
        raise FileNotFoundError('data/strategy-rules.json is required')
    fixtures = {}
    raw = read_json(source / 'evidence/hotspawn-fixtures.json')
    if isinstance(raw, list):
        fixtures = {str(r.get('id')): r for r in raw if isinstance(r, dict) and r.get('id') is not None}
    return {
        'rules': rules,
        'latest': read_json(source / 'latest.json') or {},
        'orig': read_json(source / 'origination.json'),
        'fixtures': fixtures,
        'contract': read_json(source / RESEARCH_DIR / 'hotspawn-contract.json'),
        'twc': read_json(source / RESEARCH_DIR / 'twc-results.json'),
        'tournament': read_json(source / RESEARCH_DIR / 'hotspawn-tournament.json'),
        'edge': read_json(source / 'edge-review.json'),
    }


def valid_pair(p) -> bool:
    return (isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0 < x < 1 for x in p)
            and abs(sum(p) - 1) < 1e-4)


def points_for(m: dict, raw: dict | None, rules: dict):
    """Offered points: the fixture API's own number, else the documented tier table, else blank."""
    if raw is not None:
        value = raw.get('offered_points')
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return int(value), 'Hotspawn fixture API'
    table = rules['scoring']['tier_points_when_api_omits_points']
    tier = str(m.get('tier') or '').lower()
    if tier in table:
        return table[tier], 'Computed from the tier table (API points missing)'
    return None, 'Points unverified'


def points_formula_ok(raw: dict | None, rules: dict) -> bool | None:
    """Re-derive offered_points from the API's own multipliers; None when they are absent."""
    if not raw or not isinstance(raw.get('points_breakdown'), dict):
        return None
    try:
        product = float(raw['base_points'])
        for key, value in raw['points_breakdown'].items():
            product *= float(value)
        return math.floor(product + 1e-9) == int(raw['offered_points'])
    except (KeyError, TypeError, ValueError):
        return None


def field_info(m: dict, raw: dict | None):
    """Hotspawn field shares by team, joined on team ids. Leverage context only."""
    if not raw:
        return None
    ids = [str(raw.get('participants0_id')), str(raw.get('participants1_id'))]
    team_ids = [str(t.get('id')) for t in m.get('teams') or []]
    if len(team_ids) != 2 or sorted(ids) != sorted(team_ids):
        return None
    shares = {ids[0]: raw.get('participants0_picked_percent'), ids[1]: raw.get('participants1_picked_percent')}
    values = [shares[t] for t in team_ids]
    n = raw.get('total_picks')
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 100 for v in values) or not isinstance(n, int) or n < 0:
        return None
    return {'pct': values, 'n': n}


def classify(p_dog: float, rules: dict) -> str:
    t = rules['thresholds']
    if p_dog < t['lock_underdog_below']:
        return 'lock'
    if p_dog < t['lean_underdog_below']:
        return 'lean'
    if p_dog < t['live_dog_underdog_below']:
        return 'live_dog'
    return 'coin_flip'


def bo3_score_probabilities(p_fav: float) -> dict | None:
    """Series-score probabilities for a best-of-3, from the favorite's series win probability.

    Our own derivation, not a source fact: it assumes the favorite has the same, independent win chance q on every
    map and solves q^2 (3 - 2q) = p_fav. Real map pools differ, so the result is uncalibrated and is labelled that way.
    """
    if not isinstance(p_fav, (int, float)) or isinstance(p_fav, bool) or not (0.5 <= p_fav < 1):
        return None
    lo, hi = 0.5, 1.0
    for _ in range(60):
        q = (lo + hi) / 2
        if q * q * (3 - 2 * q) < p_fav:
            lo = q
        else:
            hi = q
    q = (lo + hi) / 2
    r = 1 - q
    return {'q': q, 'fav_2_0': q * q, 'fav_2_1': 2 * q * q * r, 'dog_2_1': 2 * r * r * q, 'dog_2_0': r * r}


def match_context(m: dict, twc: dict | None):
    """Dated research notes for a fixture, matched on both team names; None when none exist."""
    if not twc:
        return None
    names = {str(t.get('name') or '').strip().lower() for t in m.get('teams') or []}
    for item in twc.get('day_three') or []:
        if {str(x).strip().lower() for x in item.get('teams') or []} == names:
            return item
    return None


# ----------------------------------------------------------------------------- the plan

def plan(inputs: dict, now: datetime) -> dict:
    rules, latest, orig = inputs['rules'], inputs['latest'], inputs['orig']
    th = rules['thresholds']
    inventory_at = latest.get('inventory_observed_at')
    inventory_time = timestamp(inventory_at)
    inventory_age = (now - inventory_time).total_seconds() / 3600 if inventory_time else None
    inventory_ok = (latest.get('coverage_complete') is True and inventory_age is not None
                    and -0.1 <= inventory_age <= th['max_line_age_hours'])
    snapshot_bound = orig is None or (bool(inventory_at) and orig.get('source_snapshot_at') == inventory_at)
    matches = (orig or {}).get('matches')
    basis_note = None
    if matches is None:
        # No originated list: fall back to the featured estimates in the canonical snapshot.
        matches = []
        for m in latest.get('matches') or []:
            if m.get('availability') in {'open', 'locked', 'unknown_lock'}:
                a = m.get('analysis')
                matches.append({**m, 'origination': ({**a, 'method': a.get('method')} if a else None)})
        basis_note = 'data/origination.json was not available; showing the featured estimates only.'

    rows, unresolved, closed = [], [], []
    for m in matches:
        if len(m.get('teams') or []) != 2:
            continue
        mid = str(m.get('id'))
        raw = inputs['fixtures'].get(mid)
        names = [t.get('name') or 'Unverified team' for t in m['teams']]
        locks, starts = timestamp(m.get('locks_at')), timestamp(m.get('starts_at'))
        deadline = locks or starts
        o = m.get('origination') or {}
        probs = o.get('probabilities')
        base = {'id': mid, 'names': names, 'competition': m.get('competition') or 'Unverified tournament', 'tier': str(m.get('tier') or '').lower(),
                'starts_at': m.get('starts_at'), 'locks_at': m.get('locks_at'), 'hotspawn_url': m.get('source_url') or LOBBY, 'lobby_url': m.get('lobby_url')}
        if deadline is not None and now >= deadline:
            closed.append({**base, 'closed_reason': 'locked' if locks else 'started'})
            continue
        if not valid_pair(probs):
            research = [r for r in (m.get('research') or []) if isinstance(r, dict) and r.get('status') != 'resolved']
            unresolved.append({**base, 'research': research, 'limitations': list(m.get('limitations') or []),
                               'reason': 'No external line or official rating covers both teams.' if not probs else 'The stored probability pair failed validation, so it is not shown.'})
            continue
        points, points_source = points_for(m, raw, rules)
        method = o.get('method') or ''
        money = method in MONEY
        observed = timestamp(o.get('observed_at'))
        age_h = (now - observed).total_seconds() / 3600 if observed else None
        fresh = age_h is not None and -0.1 <= age_h <= th['max_line_age_hours']
        fav = 0 if probs[0] > probs[1] else 1 if probs[1] > probs[0] else (m.get('pick_index') if m.get('pick_index') in (0, 1) else None)
        dog = None if fav is None else (1 - fav)
        p_dog = 0.5 if dog is None else probs[dog]
        p_fav = 0.5 if fav is None else probs[fav]
        klass = classify(p_dog, rules)
        context = match_context({'teams': [{'name': n} for n in names]}, inputs['twc'])
        tour = inputs.get('tournament') or {}
        score_model = None
        if fav is not None and context and str(context.get('format') or '').startswith('Best of 3') and base['competition'] in (tour.get('tournament') or {}).get('competition_names', []):
            raw_model = bo3_score_probabilities(p_fav)
            if raw_model:
                sc = tour['scoring']
                team_pts, score_pts = sc['team_points'], sc['score_points']
                score_model = {**raw_model, 'team_points': team_pts, 'score_points': score_pts,
                               'chalk_ev': team_pts * p_fav + score_pts * raw_model['fav_2_0'], 'dog_ev': team_pts * p_dog + score_pts * raw_model['dog_2_1']}
        field = field_info(m, raw)
        f_dog = None
        if dog is not None and field and field['n'] >= th['field_min_sample_for_filter']:
            f_dog = field['pct'][dog] / 100
        crowd_on_dog = bool(rules.get('use_field_for_leverage') and f_dog is not None and f_dog >= th['max_field_share_on_underdog'])
        blockers = []
        if not inventory_ok:
            blockers.append('inventory is incomplete, stale or its time is unverified')
        if not snapshot_bound:
            blockers.append('lines belong to a different inventory snapshot')
        if m.get('availability') != 'open' or not locks or not starts or locks > starts:
            blockers.append('open status and a valid future lock/start are not confirmed')
        if not money:
            blockers.append('aggregated line, not a first-party money line' if method == 'reference' else 'model-only line')
        if not fresh:
            blockers.append('line older than 8 hours')
        if fav is None:
            blockers.append('equal 50/50 line (no favorite or underdog)')
        if p_dog < th['swap_min_underdog_probability']:
            blockers.append('underdog under 30%')
        if points is None or points < th['swap_min_points']:
            blockers.append('under 3 points')
        if crowd_on_dog:
            blockers.append('the field is already on this side')
        eligible = not blockers
        weight = (1 - f_dog) if (f_dog is not None and rules.get('use_field_for_leverage')) else th['leverage_weight_when_field_unknown']
        row = {**base, 'points': points, 'points_source': points_source, 'points_formula_ok': points_formula_ok(raw, rules),
               'p': probs, 'method': method, 'money': money, 'label': o.get('label') or METHOD_LABEL.get(method, 'Estimate'),
               'source': o.get('source') or 'Source unverified', 'source_url': o.get('source_url'), 'observed_at': o.get('observed_at'), 'age_h': age_h, 'fresh': fresh,
               'fav': fav, 'dog': dog, 'p_dog': p_dog, 'p_fav': p_fav, 'klass': klass, 'eligible': eligible, 'blockers': blockers, 'swap': False,
               'cost': (points * (p_fav - p_dog)) if points is not None else None, 'upside': (points * p_dog) if points is not None else None,
               'field': field, 'field_dog': f_dog, 'crowd_on_dog': crowd_on_dog, 'leverage_weight': weight,
               'rank_value': (points * p_dog * weight) if points is not None else 0.0,
               'context': context,
               'score_model': score_model,
               'limitations': list(o.get('limitations') or []) + list(m.get('limitations') or []),
               'availability': m.get('availability'),
               'presentation': presentation(m, inventory_at, latest.get('coverage_complete'), now,
                                            snapshot_bound=snapshot_bound, max_age_hours=th['max_line_age_hours']),
               'quotes': o.get('quotes') or [], 'model_crosscheck': o.get('model_crosscheck'),
               'upgraded': bool(m.get('upgraded_from_featured_model'))}
        rows.append(row)

    # Swaps: eligible underdogs ranked by points x probability, capped per UTC day of the start time.
    by_day: dict[str, list] = {}
    for r in rows:
        if r['eligible']:
            start = timestamp(r['starts_at'])
            by_day.setdefault(start.strftime('%Y-%m-%d') if start else 'unknown', []).append(r)
    for day_rows in by_day.values():
        day_rows.sort(key=lambda r: (-r['rank_value'], r['id']))
        for r in day_rows[:th['max_swaps_per_utc_day']]:
            r['swap'] = True
    for r in rows:
        r['default'] = r['dog'] if r['swap'] else r['fav']

    rows.sort(key=lambda r: (timestamp(r['locks_at']) or timestamp(r['starts_at']) or datetime.max.replace(tzinfo=timezone.utc), r['id']))
    stale = not inventory_ok or not snapshot_bound
    summary = {
        'active': len(rows) + len(unresolved), 'open': len(rows), 'closed': len(closed), 'unresolved': len(unresolved), 'swaps': sum(r['swap'] for r in rows),
        'classes': {k: sum(1 for r in rows if r['klass'] == k) for k in ('lock', 'lean', 'live_dog', 'coin_flip')},
        'points_on_table': sum(r['points'] or 0 for r in rows), 'unknown_points': sum(1 for r in rows if r['points'] is None),
        'swap_cost': sum(r['cost'] or 0 for r in rows if r['swap']), 'swap_points': sum(r['points'] or 0 for r in rows if r['swap']),
        'stale': stale, 'inventory_observed_at': inventory_at, 'inventory_age_h': inventory_age, 'coverage_complete': latest.get('coverage_complete'),
        'originated_snapshot_at': (orig or {}).get('source_snapshot_at'), 'basis_note': basis_note,
        'snapshot_bound': snapshot_bound, 'current': sum(r['presentation']['current'] for r in rows),
        'current_swaps': sum(r['swap'] and r['presentation']['current'] for r in rows),
        'max_line_age_hours': th['max_line_age_hours'],
    }
    return {'rows': rows, 'unresolved': unresolved, 'closed': closed, 'summary': summary, 'generated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ')}


# ----------------------------------------------------------------------------- rendering

def money_chip(r) -> str:
    if r['money']:
        return f'<span class="chip money">{e(METHOD_LABEL.get(r["method"], "Money-backed line"))}</span>'
    return '<span class="chip model">Research model · uncalibrated</span>'


def prob_row(name, p, is_default, current=True) -> str:
    hidden = '' if current else ' hidden'
    mark = f'<span class="tick" data-current-only aria-hidden="true"{hidden}>✓</span> ' if is_default else ''
    hint = f' <span class="sr-only" data-current-only{hidden}>(plan pick)</span>' if is_default else ''
    cls = 'prob default' if is_default else 'prob'
    return (f'<div class="{cls}"><span class="who">{mark}{e(name)}{hint}</span>'
            f'<span class="num">{pct(p)}</span><span class="bar" aria-hidden="true"><i style="width:{p * 100:.1f}%"></i></span></div>')


def why_swap(r) -> str:
    dog, fav = r['names'][r['dog']], r['names'][r['fav']]
    items = [
        f'Our line gives <strong>{e(dog)} {pct(r["p_dog"])}</strong> (fair price {1 / r["p_dog"]:.2f}) — about one chance in {1 / r["p_dog"]:.1f}, not a longshot.',
        f'It costs <strong>{r["cost"]:.1f} expected points</strong> against taking {e(fav)}, and pays <strong>{r["points"]} points</strong> when it lands.',
        f'The line is money-backed ({e(r["source"])}) and was observed {r["age_h"]:.1f} h before this page was built.',
    ]
    f = r['field']
    if f and r['field_dog'] is not None:
        share = f['pct'][r['dog']]
        small = ' (small sample)' if f['n'] < 30 else ''
        items.append(f'Hotspawn field, used only to check leverage and never as a probability: <strong>{share:g}%</strong> of {f["n"]} pickers{small} are on {e(dog)}. If it lands you gain {r["points"]} points on the other {100 - share:g}%.')
    else:
        items.append('Hotspawn field: too few pickers on record to say whether the crowd is on this side, so no leverage is claimed.')
    return '<ul class="why">' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def context_block(r) -> str:
    c = r.get('context')
    if not c:
        return ''
    lines = []
    if c.get('round'):
        lines.append(f'{e(c.get("group") and "Group " + c["group"] or "")} {e(c["round"]).lower()} match' + (f' · {e(c["format"])}' if c.get('format') else ''))
    ranks = c.get('ranks_hltv_vrs') or {}
    if ranks:
        lines.append('Ranks (HLTV · Valve VRS): ' + ' · '.join(f'{e(t)} #{v.get("hltv", "—")} · #{v.get("vrs", "—")}' for t, v in ranks.items()))
    lineups = c.get('lineups_hltv') or {}
    if lineups:
        lines.append('Lineups on HLTV: ' + ' | '.join(f'<strong>{e(t)}</strong> {e(", ".join(p))}' for t, p in lineups.items()))
    links = ext(c['hltv_url'], 'HLTV match page') if c.get('hltv_url') else ''
    if c.get('polymarket_url'):
        links += ' ' + ext(c['polymarket_url'], 'Polymarket market')
    return '<details class="ctx"><summary>Situation &amp; sources</summary><ul>' + ''.join(f'<li>{x}</li>' for x in lines) + f'</ul><p class="links">{links}</p></details>'


def card(r) -> str:
    a, b = r['names']
    default_name = r['names'][r['default']] if r['default'] in (0, 1) else 'No directional pick (50/50)'
    fav_name = r['names'][r['fav']] if r['fav'] in (0, 1) else 'Equal 50/50'
    klass = r['klass']
    safety = r['presentation']
    current = safety['current']
    hidden = '' if current else ' hidden'
    historical_hidden = ' hidden' if current else ''
    source_match = {**r, 'origination': {'observed_at': r['observed_at'], 'probabilities': r['p']}}
    if r['swap']:
        verdict = f'<span class="ribbon swap">Upset play</span>'
        pick_line = f'<p class="pickline">Plan pick <strong>{e(default_name)}</strong><small>Most likely winner: {e(fav_name)} {pct(r["p_fav"])}</small></p>'
    elif r['default'] not in (0, 1):
        verdict = f'<span class="ribbon {e(klass)}">No edge (50/50)</span>'
        pick_line = f'<p class="pickline">Plan pick <strong>— unverified</strong><small>Equal 50.0% / 50.0% estimate; no arbitrary side chosen</small></p>'
    else:
        verdict = f'<span class="ribbon {e(klass)}">{e({"lock": "Lock", "lean": "Lean", "live_dog": "Live dog", "coin_flip": "Coin flip"}[klass])}</span>'
        pick_line = f'<p class="pickline">Plan pick <strong>{e(default_name)}</strong><small>Same as the most likely winner</small></p>'
    chips = [money_chip(r)]
    chips.append(f'<span class="chip pts">{r["points"]} pts</span>' if r['points'] is not None else '<span class="chip unverified">points unverified</span>')
    chips.append(f'<span class="chip tier">Tier {e(r["tier"].upper() or "?")}</span>')
    if not r['fresh']:
        chips.append('<span class="chip stale">line older than 8 h</span>')
    if r.get('upgraded'):
        chips.append('<span class="chip derived">money line replaced the model estimate</span>')
    if not r['swap'] and r['klass'] in {'live_dog', 'coin_flip'}:
        why = ('Money-backed and close, but not among the day\'s top plays.' if r['eligible'] else 'Close, but no upset play: ' + '; '.join(r['blockers']) + '.')
        chips.append(f'<span class="chip note">{e(why)}</span>')
    link_line = ext(r['hotspawn_url'], 'Hotspawn match')
    if r['source_url']:
        link_line += ' ' + ext(r['source_url'], r['source'])
    for q in r['quotes'][:3]:
        if q.get('source_url') and q.get('source_url') != r['source_url']:
            link_line += ' ' + ext(q['source_url'], q.get('provider') or 'Line source')
    body = f'''<article class="pick-card strat {"swap" if r["swap"] else ""}{" is-historical" if not current else ""}" id="match-{e(r["id"])}" {card_attributes(source_match, safety)} data-was-current="{str(current).lower()}" data-id="{e(r["id"])}">
<header><p class="comp">{e(r["competition"])}</p><h3>{e(a)} <span>vs</span> {e(b)}</h3>
<p class="when">Locks {when(r["locks_at"])} · starts {when(r["starts_at"])}</p>
<p class="status" hidden>Locked — can no longer be picked</p></header>
{status_html(safety)}
<div class="verdict" data-current-only{hidden}>{verdict}{pick_line}</div>
<p class="snapshot-plan" data-historical-only{historical_hidden}>Snapshot plan <strong>{e(default_name)}</strong><small>Historical / unverified for current use. Not a current recommendation.</small></p>
<div class="probs" role="group" aria-label="Our win probabilities">{prob_row(a, r["p"][0], r["default"] == 0, current)}{prob_row(b, r["p"][1], r["default"] == 1, current)}</div>
<div class="chips">{"".join(chips)}</div>
<div data-current-only{hidden}>{why_swap(r) if r["swap"] else ""}{score_block(r)}</div>
{context_block(r) if r.get("context") else ""}
<details class="more"><summary>Sources &amp; limits</summary>
<p class="tiny">{e(r["label"])} · observed {when(r["observed_at"])} · points from {e(r["points_source"])}{"" if r["points_formula_ok"] is not False else " · <strong>points do not match the API multipliers; check the rules</strong>"}</p>
{("<ul class='tiny'>" + "".join(f"<li>{e(x)}</li>" for x in r["limitations"]) + "</ul>") if r["limitations"] else ""}
<p class="links">{link_line}</p></details>
</article>'''
    return body


def score_block(r) -> str:
    sm = r.get('score_model')
    if not sm:
        return ''
    fav, dog = r['names'][r['fav']], r['names'][r['dog']]
    items = ''.join(f'<li><span>{e(label)}</span><strong>{pct(value)}</strong></li>' for label, value in [
        (f'{fav} 2-0', sm['fav_2_0']), (f'{fav} 2-1', sm['fav_2_1']), (f'{dog} 2-1', sm['dog_2_1']), (f'{dog} 2-0', sm['dog_2_0'])])
    plan_is_dog = r['default'] == r['dog']
    best = f'{dog} 2-1' if plan_is_dog else f'{fav} 2-0'
    return (f'<div class="scoreblock"><h4>Tournament pick\'em slip: team + score ({sm["team_points"]} + {sm["score_points"]} points)</h4>'
            f'<ul class="scores">{items}</ul>'
            f'<p>With the plan pick, the best score to enter is <strong>{e(best)}</strong>. Expected points: <strong>{sm["chalk_ev"]:.1f}</strong> for {e(fav)} 2-0 against '
            f'<strong>{sm["dog_ev"]:.1f}</strong> for {e(dog)} 2-1; the upset slip gives up {sm["chalk_ev"] - sm["dog_ev"]:.1f} expected points and pays up to {sm["team_points"] + sm["score_points"]}.</p>'
            f'<p class="tiny muted">Model-derived from the series line, not a source fact: it assumes the same chance on every map (per-map chance {sm["q"]:.0%} for {e(fav)}), so it is uncalibrated. Best of 3 per HLTV; Hotspawn says best of 3 until the weekend.</p></div>')


def swaps_block(pl) -> str:
    swaps = [r for r in pl['rows'] if r['swap'] and r['presentation']['current']]
    if not swaps and (pl['summary']['stale'] or not pl['summary']['current']
                      or pl['summary']['current'] != pl['summary']['open']):
        return '<div class="callout"><strong>No current upset recommendation.</strong> Not every retained line is usable for a current pick. Check each card status and source time; historical or unverified choices are not submission recommendations.</div>'
    if not swaps:
        return ('<div class="callout calm" data-safety-synopsis><strong>No upset play in this slate.</strong> No underdog clears all published probability, points, field and eligibility checks. '
                'For the currently usable cards, take the most likely winner; that is the plan, not a gap.</div>')
    items = ''
    for r in swaps:
        items += (f'<li data-safety-link="match-{e(r["id"])}"><a href="#match-{e(r["id"])}"><strong>{e(r["names"][r["dog"]])}</strong> over {e(r["names"][r["fav"]])}</a>'
                  f'<span>{pct(r["p_dog"])} · {r["points"]} pts · costs {r["cost"]:.1f} expected</span></li>')
    return f'<div class="callout swapbox"><strong>Current upset plays (<span data-current-swap-count>{len(swaps)}</span>)</strong><ul class="swaplist">{items}</ul></div>'


def unresolved_block(pl) -> str:
    rows = pl['unresolved']
    if not rows:
        return '<p class="ok-note">Every active fixture in this snapshot has a probability and a plan pick.</p>'
    out = ''
    for r in rows:
        trail = ''
        for step in r['research']:
            link = ext(step['source_url'], 'source') if step.get('source_url') else ''
            trail += f'<li><strong>{e(step.get("stage", "Check"))}</strong> · {e(step.get("status", "unverified"))}<br><span class="tiny">{e(str(step.get("detail", ""))[:240])}</span> {link}</li>'
        if not trail:
            trail = '<li>No research trail was recorded for this fixture. <span class="unverified">unverified</span></li>'
        out += (f'<article class="pick-card strat unres" id="unresolved-{e(r["id"])}"><header><p class="comp">{e(r["competition"])} · Tier {e(r["tier"].upper() or "?")}</p>'
                f'<h3>{e(r["names"][0])} <span>vs</span> {e(r["names"][1])}</h3><p class="when">Locks {when(r["locks_at"])} · starts {when(r["starts_at"])}</p></header>'
                f'<p><span class="chip unverified">— no pick · unverified</span> {e(r["reason"])}</p>'
                f'<details class="more" open><summary>What was checked</summary><ul class="tiny">{trail}</ul></details>'
                f'<p class="links">{ext(r["hotspawn_url"], "Hotspawn match")}</p></article>')
    return out


def day3_4_lessons_block(edge, tour=None, rules=None) -> str:
    if not isinstance(edge, dict):
        return ''
    d3 = edge.get('day_three_results') or []
    d4 = edge.get('day_four') or []
    if not d3 and not d4:
        return ''
    th = ((rules or {}).get('thresholds') or {})
    floor = float(th.get('swap_min_underdog_probability', 0.30))
    sc_cfg = ((tour or {}).get('scoring') or {})
    t_pts = int(sc_cfg.get('team_points') or 7)
    s_pts = int(sc_cfg.get('score_points') or 5)
    parts = []
    if d3:
        rows = ''
        for r in d3:
            res = r.get('result') or {}
            loser = r.get('team_b') if res.get('winner') == r.get('team_a') else r.get('team_a')
            maps = ', '.join(
                f"{m.get('map')} {m.get('a')}–{m.get('b')}"
                for m in (res.get('maps') or [])
                if m.get('map') is not None
            )
            srcs = ' '.join(
                ext(s.get('url'), s.get('source') or 'HLTV')
                for s in (r.get('sources') or [])
                if s.get('url')
            ) or (ext(r.get('hltv_url'), 'HLTV') if r.get('hltv_url') else '<span class="unverified">unverified</span>')
            rows += (
                f'<tr><th scope="row">{e(r.get("slot"))}<small>{e(r.get("starts_at"))}</small></th>'
                f'<td data-label="Result"><strong>{e(res.get("winner"))} {e(res.get("score"))} {e(loser)}</strong>'
                f'<small>{e(maps)}</small></td>'
                f'<td data-label="Leaderboard takeaway">{e(r.get("assessment"))}</td>'
                f'<td data-label="Sources">{srcs}</td></tr>'
            )
        parts.append(
            '<h3 class="sub" id="day3-completed-results">Day 3 decider results (16 Oct · verified from HLTV)</h3>'
            '<div class="table-scroll"><table class="simple">'
            '<caption>Day 3 decider results and map scores (HLTV)</caption>'
            '<thead><tr><th scope="col">Slot</th><th scope="col">Result</th>'
            '<th scope="col">Leaderboard takeaway</th><th scope="col">Sources</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
        )
    if d4:
        rows = ''
        for m in d4:
            ta = m.get('team_a') or ''
            tb = m.get('team_b') or ''
            mkt = m.get('market') or {}
            prices = mkt.get('prices') or {}
            pa = prices.get(ta)
            pb = prices.get(tb)
            if isinstance(pa, (int, float)) and isinstance(pb, (int, float)):
                if pa >= pb:
                    fav, p_fav, dog, p_dog = ta, float(pa), tb, float(pb)
                else:
                    fav, p_fav, dog, p_dog = tb, float(pb), ta, float(pa)
                ev_cost = p_fav - p_dog
                sc = bo3_score_probabilities(p_fav) or {'fav_2_0': 0.0, 'dog_2_1': 0.0}
                p_fav_20 = sc['fav_2_0']
                p_dog_21 = sc['dog_2_1']
                ev_fav_slip = p_fav * t_pts + p_fav_20 * s_pts
                ev_dog_slip = p_dog * t_pts + p_dog_21 * s_pts
                prob_cell = (
                    f'{e(ta)} {pct(pa)} · {e(tb)} {pct(pb)}'
                    f'<small>{e(mkt.get("provider"))} · read {e(mkt.get("observed_at"))}</small>'
                )
                if p_dog >= floor:
                    verdict_cell = (
                        f'<strong>Default: {e(fav)} ({pct(p_fav)}) · Contrarian play: {e(dog)} ({pct(p_dog)})</strong>'
                        f'<small>Clears the {floor:.0%} underdog floor (costs {ev_cost:.3f} expected pts per base pt). '
                        f'Tournament BO3 slip ({t_pts}+{s_pts} pts, uncalibrated): chalk {e(fav)} 2-0 ({pct(p_fav_20)}, EV {ev_fav_slip:.1f} pts) '
                        f'or contrarian {e(dog)} 2-1 ({pct(p_dog_21)}, EV {ev_dog_slip:.1f} pts).</small>'
                    )
                else:
                    verdict_cell = (
                        f'<strong>Plan pick: {e(fav)} ({pct(p_fav)}) · Lock — do not fade</strong>'
                        f'<small>{e(dog)} ({pct(p_dog)}) sits below the {floor:.0%} underdog floor (fading costs {ev_cost:.3f} expected pts per base pt). '
                        f'Tournament BO3 slip ({t_pts}+{s_pts} pts, uncalibrated): {e(fav)} 2-0 ({pct(p_fav_20)}, EV {ev_fav_slip:.1f} pts).</small>'
                    )
            else:
                prob_cell = '<span class="unverified">unverified</span>'
                verdict_cell = '<span class="unverified">unverified</span>'
            srcs = ' '.join(
                ext(s.get('url'), s.get('source') or 'Source')
                for s in (m.get('sources') or [])
                if s.get('url')
            ) or (ext(m.get('hltv_url'), 'HLTV') if m.get('hltv_url') else '<span class="unverified">unverified</span>')
            rows += (
                f'<tr><th scope="row">{e(ta)} vs {e(tb)}<small>{e(m.get("slot"))} · {e(m.get("starts_at"))}</small></th>'
                f'<td data-label="External market">{prob_cell}</td>'
                f'<td data-label="Contrarian &amp; BO3 slip plan">{verdict_cell}</td>'
                f'<td data-label="Sources">{srcs}</td></tr>'
            )
        parts.append(
            '<h3 class="sub" id="day4-semifinals-plan">Day 4 TWC 2026 semifinal plan &amp; BO3 score-slip math (17 Oct)</h3>'
            '<div class="table-scroll"><table class="simple">'
            '<caption>Day 4 TWC 2026 semifinals: external market probabilities, contrarian screen and BO3 score-slip guidance</caption>'
            '<thead><tr><th scope="col">Semifinal</th><th scope="col">External market</th>'
            '<th scope="col">Contrarian &amp; BO3 slip plan</th><th scope="col">Sources</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            '<p class="tiny muted">For full provider order-book depth, Day 1–3 map-veto breakdowns, and Day 5 bracket links, open '
            '<a class="src" href="../twc-picks/#day-four-picks">the dedicated TWC 2026 picks page (/twc-picks/)</a> or jump to '
            '<a class="src" href="../origination/#picks">the complete CS2 picks list</a>.</p>'
        )
    return ''.join(parts)


def lessons_block(twc, edge=None, tour=None, rules=None) -> str:
    if not twc or not twc.get('series'):
        return '<p class="ok-note">No Day 1–2 research file is present in this build.</p>'
    series = twc['series']
    rows = ''
    for s in series:
        fs = s.get('field_share')
        field = '—'
        miss = ''
        if fs:
            field = f'{fs["winner_pct"]}% picked the winner (n={fs["total_picks"]})'
            miss = ' class="miss"' if fs['winner_pct'] < 50 else ''
        score = f'{e(s["winner"])} {e(s["score"])} {e(s["loser"])}'
        api = s.get('hotspawn_api')
        if api:
            mark = '✓ agrees' if api.get('agrees_with_hltv') else '✗ differs'
            score += f'<small>Hotspawn API: {e(api["winner"])} {e(api["score"])} {mark}</small>'
        rows += (f'<tr{miss}><th scope="row">Day {s["day"]} · Group {e(s["group"])} {e(s["round"]).lower()}<small>{e(s["date"])}</small></th><td data-label="Result">{score}</td><td data-label="Hotspawn field">{field}</td>'
                 f'<td data-label="Source">{ext(s["hltv_url"], "HLTV")}</td></tr>')
    three = sum(1 for s in series if s['maps_played'] == 3)
    d2 = [s for s in series if s['day'] == 2 and s.get('field_share')]
    api_rows = [s for s in series if s.get('hotspawn_api')]
    api_agree = sum(1 for s in api_rows if s['hotspawn_api'].get('agrees_with_hltv'))
    hit = sum(1 for s in d2 if s['field_share']['winner_pct'] > 50)
    facts = [f'{len(series)} series played: {len(series) - three} ended 2–0 and {three} went to a third map (all three third-map series were on Day 2).']
    if api_rows:
        facts.append(f"Hotspawn's own tournament API reports the same winner and series score as HLTV for {api_agree} of {len(api_rows)} series.")
    if d2:
        facts.append(f'Day 2: the Hotspawn field (13–16 pickers each, 08:36Z snapshot) picked the winner in {hit} of {len(d2)} S-tier series; the miss is shown in amber.')
    d3 = ''
    for item in twc.get('day_three') or []:
        status = ('On Hotspawn: fixture ' + e(item['hotspawn_fixture_id'])) if item.get('on_hotspawn') else 'Not on the Hotspawn lobby at the 22:25Z read'
        cents = item.get('polymarket_listing_cents') or {}
        price = ' · '.join(f'{e(k)} {v}¢' for k, v in cents.items())
        d3 += (f'<tr><th scope="row">{e(item["teams"][0])} vs {e(item["teams"][1])}<small>Group {e(item["group"])} {e(item["round"]).lower()} · {e(item.get("date", ""))}</small></th>'
               f'<td data-label="Hotspawn">{status}</td><td data-label="Price (not a pick input here)">Polymarket listing: {price or "—"}</td><td data-label="Sources">{ext(item["hltv_url"], "HLTV")} {ext(item["polymarket_url"], "Polymarket") if item.get("polymarket_url") else ""}</td></tr>')
    return (f'<div class="table-scroll"><table class="simple"><caption>Thunderpick World Championship 2026 results, Days 1–2 (HLTV)</caption><thead><tr><th scope="col">Series</th><th scope="col">Result</th><th scope="col">Hotspawn field</th><th scope="col">Source</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<ul class="facts">{"".join(f"<li>{x}</li>" for x in facts)}</ul>'
            f'<p class="tiny muted">Read from HLTV on {e((twc.get("results_observed_at") or "")[:10])}. These results do not change any probability on this page; probabilities come from the lines.</p>'
            f'<h3 class="sub">Next: the Day 3 deciders</h3><div class="table-scroll"><table class="simple"><caption>Day 3 deciders: Hotspawn status and listed prices</caption><thead><tr><th scope="col">Decider</th><th scope="col">Hotspawn</th><th scope="col">Price (not a pick input here)</th><th scope="col">Sources</th></tr></thead><tbody>{d3}</tbody></table></div>'
            + day3_4_lessons_block(edge, tour=tour, rules=rules))


def tournament_block(t) -> str:
    if not t:
        return '<p class="ok-note">No tournament research file is present in this build.</p>'
    tour, sc, pr, lb, cb, fx = t['tournament'], t['scoring'], t['prizes'], t['leaderboard'], t['crystal_ball'], t['fixtures_api']
    rows = fx['rows']
    ended = sum(1 for r in rows if r['status'] == 'ended')
    open_ = [r for r in rows if r['status'] == 'scheduled']
    prizes = ' · '.join(f'#{k} {e(v)}' for k, v in pr['tournament'].items())
    top = ', '.join(str(x) for x in lb['top5_points'])
    perfect = sc['team_points'] + sc['score_points']
    cards = [
        ('Scoring', f'<strong>{sc["team_points"]} points</strong> for the correct team and <strong>{sc["score_points"]} more</strong> for the correct score, so a perfect slip is {perfect}. '
                    f'{e(sc["text_pick"])}. Your tournament score is the sum of your daily scores.', ext(sc['source_url'], 'Hotspawn tournament API'), sc['observed_at']),
        ('Prizes', f'{prizes}. Daily: {e(pr["daily"])}. {e(pr["note"])}', ext(pr['source_url'], 'Hotspawn tournament page'), pr['observed_at']),
        ('Leaderboard snapshot', f'Top five scores at the read: <strong>{e(top)}</strong>. {e(lb["rule"])}', ext(lb['source_url'], 'Hotspawn tournament page'), lb['observed_at']),
        ('Fixtures', f'{fx["records"]} of {tour["fixture_count"]} fixtures exist so far ({ended} ended with results, {len(open_)} still scheduled). Later matches appear once both teams are confirmed. {e(fx["irregularity"])}',
         ext(fx['source_url'], 'Hotspawn tournament page'), fx['observed_at']),
        ('Crystal Ball (daily side-question)', f'“{e(cb["question"])}” Day 1 final value: <strong>{cb["days"][0]["final_value"]}</strong>. <span class="unverified">Scoring unverified</span>: {e(cb["note"])}',
         ext(cb['source_url'], 'Hotspawn tournament API'), cb['observed_at']),
        ('Player props', f'{e(t["player_props"]["seen"])}. <span class="unverified">Not analysed</span>: {e(t["player_props"]["note"])}', ext(t['player_props']['source_url'], 'Hotspawn tournament page'), tour['observed_at']),
    ]
    body = ''.join(f'<div class="def"><dt>{e(a)}</dt><dd>{b}<p class="links">{c} <small class="muted">read {e(d)}</small></p></dd></div>' for a, b, c, d in cards)
    lede = ("The Thunderpick World Championship has its own pick'em on Hotspawn, separate from the weekly lobby: you pick the team <em>and</em> the series score. "
            f'It runs {e(tour["window_utc"][0][:10])} to {e(tour["window_utc"][1][:10])}. ' + ext(tour['page_url'], "Open the tournament pick'em"))
    return f'<p class="lede">{lede}</p><dl class="defs" aria-label="Tournament pick\'em facts">{body}</dl>'


def rules_block(rules) -> str:
    t = rules['thresholds']
    cls = rules['classes']
    rows = [
        ('Lock', f'under {t["lock_underdog_below"]:.0%}', cls['lock']['advice']),
        ('Lean', f'{t["lock_underdog_below"]:.0%} to {t["lean_underdog_below"]:.0%}', cls['lean']['advice']),
        ('Live dog', f'{t["lean_underdog_below"]:.0%} to {t["live_dog_underdog_below"]:.0%}', cls['live_dog']['advice']),
        ('Coin flip', f'{t["live_dog_underdog_below"]:.0%} and up', cls['coin_flip']['advice']),
    ]
    body = ''.join(f'<div class="def"><dt>{e(a)} <span class="range">underdog {e(b)}</span></dt><dd>{e(c)}</dd></div>' for a, b, c in rows)
    swap = ''.join(f'<li>{e(x)}</li>' for x in rules['swap_rule'])
    never = ''.join(f'<li>{e(x)}</li>' for x in rules['probability_inputs']['never_used'])
    unverified = ''.join(f'<li>{e(x)}</li>' for x in rules.get('unverified', []))
    return (f'<p>Every probability comes from our own external-line pipeline. This page only decides <em>which side to submit</em>. The rules file is <a class="src" href="../data/strategy-rules.json">data/strategy-rules.json</a> (version {e(rules["version"])}).</p>'
            f'<h3 class="sub">Classes</h3><dl class="defs" aria-label="How the underdog probability maps to a class">{body}</dl>'
            f'<h3 class="sub">When we recommend the underdog (an "upset play")</h3><p>All of these must hold:</p><ul>{swap}</ul>'
            f'<p><strong>Why this is not stupid:</strong> Hotspawn awards points for correct picks only, so the price of an upset play is the expected points you give up, {t["swap_min_points"]}+ points × (favorite − underdog probability), shown on every upset card. The upside is variance: a hit moves you past rivals who all took the favorite. A lock (under 25%) never qualifies, because its cost is high and its chance of paying is low.</p>'
            f'<h3 class="sub">Never used as a probability</h3><ul>{never}</ul><p class="tiny">{e(rules["field_share_policy"])}</p>'
            f'<h3 class="sub">Left blank on purpose</h3><ul>{unverified}</ul>')


def contract_block(contract) -> str:
    if not contract:
        return '<p class="ok-note">No Hotspawn contract research file is present in this build.</p>'
    rows = ''
    for o in contract['observations']:
        kind = {'verified': 'verified', 'derived': 'derived', 'unverified': 'unverified'}.get(o['status'], 'unverified')
        rows += (f'<tr id="{e(o["id"].lower())}"><th scope="row"><span class="chip {kind}">{e(o["status"])}</span> {e(o["claim"])}</th><td data-label="How it was verified">{e(o["how_verified"])}<small>Observed {e(o["observed_at"])}</small></td>'
                 f'<td data-label="Source">{ext(o["source_url"], "Source")}</td></tr>')
    return (f'<p class="tiny muted">{e(contract["note"])}</p><div class="table-scroll"><table class="simple"><caption>Hotspawn pick\'em scoring, locking and leaderboard contract (reverse-engineered and dated)</caption>'
            f'<thead><tr><th scope="col">Fact</th><th scope="col">How it was verified</th><th scope="col">Source</th></tr></thead><tbody>{rows}</tbody></table></div>')


def closed_block(pl) -> str:
    if not pl['closed']:
        return ''
    items = ''.join(f'<li>{e(r["names"][0])} vs {e(r["names"][1])} · {e(r["competition"])} · {ext(r["hotspawn_url"], "Hotspawn")}</li>' for r in pl['closed'])
    return f'<details class="more closed"><summary>{len(pl["closed"])} fixture(s) already locked when this page was built</summary><ul class="tiny">{items}</ul></details>'


def page(inputs: dict, pl: dict) -> str:
    s = pl['summary']
    stale = ''
    if s['stale']:
        age = f'{s["inventory_age_h"]:.1f} h old' if s['inventory_age_h'] is not None else 'time unverified'
        stale = (f'<div class="stale" role="status"><strong>Not a current snapshot.</strong> The Hotspawn inventory is incomplete, outside the eight-hour freshness window, or not bound to these lines ({e(age)}). '
                 f'Probabilities keep their own observation times; check each card before relying on it. <a href="../coverage/">Source status →</a></div>')
    if s['basis_note']:
        stale += f'<div class="stale" role="status">{e(s["basis_note"])}</div>'
    cards = ''.join(card(r) for r in pl['rows']) or '<p class="ok-note">No open fixture with a probability in this snapshot.</p>'
    cls = s['classes']
    unresolved_n = s['unresolved']
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Leaderboard plan — contrarian, not stupid · Spawn Scout</title>
<meta name="description" content="One obvious Hotspawn CS2 pick per match and the few underdogs worth an upset play, from our own external-line probabilities. Mobile-friendly.">
<meta name="theme-color" content="#142534">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'">
<link rel="icon" href="../assets/scout-mark.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/strategy.css">
<script src="../assets/pick-safety.js" defer></script>
<script src="../assets/strategy.js" defer></script>
</head><body {body_attributes(s["inventory_observed_at"], s["coverage_complete"], snapshot_bound=s["snapshot_bound"], max_age_hours=s["max_line_age_hours"])}>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><p class="brand"><a href="../">spawn<strong>scout</strong></a> <span>· leaderboard plan</span></p>
<nav aria-label="Pages" class="topnav"><a href="../">Summary</a><a href="../origination/#picks">All picks</a><a href="../edge/">Upset review</a><a href="../review/">Flagged</a></nav></header>
<main id="main">
{stale}
<section class="hero" id="top"><p class="kicker">LEADERBOARD PLAN · CONTRARIAN, NOT STUPID</p>
<h1>One pick per match. Underdogs only when the lines say they have a real shot.</h1>
<p class="hero-stats"><strong>{s["open"]}</strong> snapshot fixtures with sourced lines · <strong data-current-count>{s["current"]}</strong> currently usable · <strong data-current-swap-count>{s["current_swaps"]}</strong> current upset play{"" if s["current_swaps"] == 1 else "s"} · <strong>{unresolved_n}</strong> unresolved · <strong>{s["points_on_table"]}</strong> snapshot Hotspawn points</p>
<p class="hero-note">Probabilities are ours, from external lines and official ratings — never Hotspawn popularity. Snapshot: inventory {when(s["inventory_observed_at"])}; page built {when(pl["generated_at"])}.</p>
<p class="quick"><a class="btn" href="#slate">See the picks ↓</a><a class="btn alt" href="#unresolved">Unresolved &amp; limitations ({unresolved_n}) ↓</a><a class="btn alt" href="../origination/#picks">Most-likely-winner list →</a></p></section>
<section class="block" id="plan"><h2>The plan in 20 seconds</h2>
<ul class="plan-list" data-safety-synopsis{' hidden' if s["stale"] or s["current"] != s["open"] else ''}><li><strong>Default:</strong> submit the most likely winner. {cls["lock"]} lock{"" if cls["lock"] == 1 else "s"} and {cls["lean"]} lean{"" if cls["lean"] == 1 else "s"} are not worth fading.</li>
<li><strong>Upset plays:</strong> {s["swaps"]} across the listed fixtures (capped per UTC day), costing about {s["swap_cost"]:.1f} expected points in total against the favorites, and worth {s["swap_points"]} Hotspawn points if every one lands.</li>
<li><strong>Close calls:</strong> {cls["live_dog"]} live dog{"" if cls["live_dog"] == 1 else "s"} and {cls["coin_flip"]} coin flip{"" if cls["coin_flip"] == 1 else "s"}; the card says which side the lines favour.</li>
<li><strong>Thunderpick World Championship:</strong> its tournament pick'em also pays <strong>5 points for the correct score</strong>. See the <a href="#tournament">tournament section</a> and the score line on each TWC card.</li>
<li><strong>Unresolved:</strong> {unresolved_n} fixture{"" if unresolved_n == 1 else "s"} have no external line or rating. They stay blank, with the reason, in the <a href="#unresolved">unresolved section</a>.</li></ul>
{swaps_block(pl)}
<p class="stale" data-runtime-safety-notice role="status"{' hidden' if s['current'] == s['open'] else ''}>{s['current']} currently usable line(s). Retired plan choices are historical only, not current recommendations.</p>
<noscript><p class="stale">JavaScript is off: the plan's lock and freshness checks are as of page build time. Labels cannot expire in an open tab; compare the printed deadlines and observation times and reload before relying on a pick.</p></noscript></section>
<section class="block" id="slate"><h2>The slate, in lock order</h2>
<p class="lede">The ✓ team is the plan pick. Hotspawn locks picks before the start (its rules page says 5 minutes, its fixture API says 6): submit with margin. Times are Malta time with UTC beside them. A “Situation &amp; sources” note appears only where a dated HLTV read exists; its absence means nothing was verified, not that nothing matters.</p>
<p class="tools"><label><input type="checkbox" id="hide-locked" checked> Hide fixtures that have locked</label></p>
<div class="cards">{cards}</div>{closed_block(pl)}</section>
<section class="block" id="unresolved"><h2>Unresolved picks &amp; limitations</h2>
<p class="lede">No pick is shown when no external line or official rating covers both teams. Nothing is inferred and there is no default 50/50. An unavailable source is not proof that no market exists. The collector re-checks every four hours.</p>
{unresolved_block(pl)}</section>
<section class="block" id="tournament"><h2>TWC tournament pick'em: team + score</h2>{tournament_block(inputs.get("tournament"))}</section>
<section class="block" id="lessons"><h2>What Days 1–2 showed, and what is next</h2>{lessons_block(inputs.get("twc"), edge=inputs.get("edge"), tour=inputs.get("tournament"), rules=inputs.get("rules"))}</section>
<section class="block" id="rules"><h2>How the plan picks are chosen</h2>{rules_block(inputs["rules"])}</section>
<section class="block" id="hotspawn"><h2>How Hotspawn scores and locks</h2>{contract_block(inputs.get("contract"))}</section>
</main>
<footer><p><strong>Better context. Clearer picks.</strong></p>
<p>Independent research dashboard · not affiliated with Hotspawn, HLTV, Valve, Polymarket or any betting provider. Informational use only. 18+ where applicable. No bets are placed.</p>
<p class="tiny"><a class="src" href="../methodology/">Methodology</a> · <a class="src" href="../review/">Flagged for Review</a> · <a class="src" href="{REPO}">Source repository</a></p></footer>
</body></html>'''


def build(source: Path, output: Path, now: datetime | None = None) -> Path:
    inputs = load_inputs(Path(source))
    pl = plan(inputs, now or datetime.now(timezone.utc))
    target = Path(output) / 'strategy'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'index.html').write_text(page(inputs, pl), encoding='utf-8')
    (Path(output) / 'data').mkdir(parents=True, exist_ok=True)
    public = {k: pl[k] for k in ('summary', 'generated_at')}
    public['rows'] = [{k: v for k, v in r.items() if k not in {'quotes', 'model_crosscheck', 'context'}} for r in pl['rows']]
    public['unresolved'] = [{k: v for k, v in r.items() if k != 'research'} for r in pl['unresolved']]
    public['rules_version'] = inputs['rules']['version']
    edge = inputs.get('edge')
    if isinstance(edge, dict):
        public['twc_day3_results'] = edge.get('day_three_results') or []
        public['twc_day4_semifinals'] = edge.get('day_four') or []
    (Path(output) / 'data' / 'strategy.json').write_text(json.dumps(public, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return target / 'index.html'


def placeholder(output: Path, reason: str) -> Path:
    """Written when the plan cannot be built, so links to it never break and the data refresh still publishes."""
    target = Path(output) / 'strategy'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'index.html').write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Leaderboard plan unavailable · Spawn Scout</title><link rel="stylesheet" href="../assets/strategy.css"></head><body><main id="main">'
        '<section class="block"><h1>Leaderboard plan temporarily unavailable</h1>'
        f'<p>The plan could not be built from this snapshot ({e(reason)}). The complete picks list is unaffected: '
        '<a href="../origination/#picks">open the most-likely-winner list</a> · <a href="../review/">Flagged for Review</a>.</p></section></main></body></html>', encoding='utf-8')
    return target / 'index.html'


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('site'))
    args = parser.parse_args()
    print('wrote', build(args.source, args.output))


if __name__ == '__main__':
    main()
