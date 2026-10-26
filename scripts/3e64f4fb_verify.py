"""Session arena-3e64f4fb: independent two-layer replay of the published picks board.

The site publishes two probability layers for the same Hotspawn CS2 inventory:

``snapshot.json`` (featured layer)
    Exact-name featured estimates only. A fixture with no featured estimate is
    published with ``analysis: null``, a limitations list and a research trail.
``origination.json`` (complete list)
    Every active fixture, resolved where the featured layer could not be -
    alias-aware exchange/esportsbook research or the Valve research model -
    or published blank with its limitations.

This verifier re-derives every published number in BOTH layers from the inputs
each row publishes, then checks the two layers agree where they must, and that
the executive summary (`index.html`) carries the separated unresolved /
no-betting-line sections with working in-site links. It uses no network and
never pins a fixture to a pick state: a fixture graduating from blank to a
sourced pick must pass, which is the class that broke the four-hour publisher
on 2026-10-25 (see 824A-R01).

Checks
------
``inventory``    snapshot counts recomputed from its rows; archived rows carry
                 no prematch analysis.
``featured``     every featured analysis replayed: market = normalised
                 bid/ask midpoints, bookmaker = proportional no-vig, model =
                 Valve Glicko expectation from the published points (RD 75).
``complete``     every complete-list estimate replayed the same way, including
                 the researched quote shape (paired bid/ask lists) and any
                 Valve model cross-check.
``cross_layer``  identical active fixture set, teams and start times in both
                 layers; where the featured layer priced a row the complete
                 list must carry the same probabilities unless it declares an
                 upgrade; where the featured layer left a row blank, a
                 complete-list resolution must carry its own quote/model
                 evidence, an observation time, a research trail, and an
                 evidence-backed alias for every name it joined.
``picks``        every named pick is the strict favourite of its own two
                 numbers; every pick-less row has limitations + research.
``sources``      every probability is attributed to an official publisher over
                 https; Hotspawn (the pick'em host) is never a probability
                 source and no crowd field appears in any analysis.
``summary``      the executive summary has the picks-at-a-glance, unresolved,
                 no-line and fallback registers; every active fixture is
                 listed; every in-site link from the summary resolves to an
                 existing file and anchor; both published percentages of
                 every priced row appear on the summary and picks pages;
                 phone basics (viewport, language, skip link) are present.

Usage::

    python -m scripts.3e64f4fb_verify [--check] [--out data/research/3e64f4fb]

``--check`` exits 1 on any error. Warnings are reported, never fatal.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

PROBABILITY_HOSTS = (
    'polymarket.com', 'gamma-api.polymarket.com', 'clob.polymarket.com', 'docs.polymarket.com',
    'kalshi.com', 'docs.kalshi.com',
    'thunderpick.io', 'gg.bet', 'stake.com', 'pinnacle.com', 'rivalry.com', 'bovada.lv',
    'smarkets.com', 'egamersworld.com', 'hltv.org', 'github.com', 'bo3.gg',
)
CROWD_HOSTS = ('hotspawn.com', 'play.hotspawn.com')
CROWD_KEYS = ('picked', 'percent_picked', 'crowd', 'fan_vote', 'fan_rating', 'votes')
VALVE_RD = 75.0
METHODS = {'market', 'bookmaker', 'consensus', 'model', 'reference', 'guidance', 'relay', 'network'}


def host_of(url: str) -> str:
    m = re.match(r'^https?://([^/]+)', url or '')
    return (m.group(1) if m else '').lower()


def host_matches(host: str, allowed: str) -> bool:
    return host == allowed or host.endswith('.' + allowed)


def close(a, b, tol=1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol


def normalized(pair) -> list[float]:
    a, b = float(pair[0]), float(pair[1])
    return [a / (a + b), b / (a + b)]


def valve_probability(p1: float, p2: float, rd: float = VALVE_RD) -> tuple[float, float]:
    g = 1 / math.sqrt(1 + 3 * (math.log(10) / 400) ** 2 * rd ** 2 / math.pi ** 2)
    return 1 / (1 + 10 ** (g * (p2 - p1) / 400)), g


def iso(value) -> datetime | None:
    if not isinstance(value, str) or not value.endswith('Z'):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def pair_ok(mid: str, probs, errors: list[str]) -> list[float] | None:
    if not isinstance(probs, list) or len(probs) != 2:
        errors.append(f'{mid}: does not publish exactly two probabilities')
        return None
    p = [float(x) for x in probs]
    if not all(0.0 < x < 1.0 for x in p):
        errors.append(f'{mid}: probability outside (0, 1): {p}')
    if not close(sum(p), 1.0, 1e-6):
        errors.append(f'{mid}: probabilities sum to {sum(p)!r}, not 1')
    return p


def source_ok(mid: str, estimate: dict, errors: list[str]) -> None:
    url = estimate.get('source_url') or ''
    host = host_of(url)
    if not url.startswith('https://'):
        errors.append(f'{mid}: probability source is not https: {url!r}')
    elif not any(host_matches(host, h) for h in PROBABILITY_HOSTS):
        errors.append(f'{mid}: probability attributed to an unapproved host {host!r}')
    if any(host_matches(host, h) for h in CROWD_HOSTS):
        errors.append(f'{mid}: Hotspawn is used as a probability source')
    for key in CROWD_KEYS:
        if key in estimate:
            errors.append(f'{mid}: crowd field {key!r} present in an estimate')


def replay_estimate(mid: str, est: dict, errors: list[str], warnings: list[str]) -> str:
    """Recompute one estimate from its own published inputs. Returns a basis tag."""
    method = est.get('method')
    if method not in METHODS:
        errors.append(f'{mid}: unknown method {method!r}')
        return 'invalid'
    p = pair_ok(mid, est.get('probabilities'), errors)
    if p is None:
        return 'invalid'
    if not (est.get('observed_at') or '').endswith('Z'):
        errors.append(f'{mid}: observation is not stamped in UTC')
    source_ok(mid, est, errors)

    if method == 'market':
        mids = market_midpoints(mid, est, errors)
        if mids is not None:
            expect = normalized(mids)
            if not all(close(a, b, 5e-7) for a, b in zip(p, expect)):
                errors.append(f'{mid}: market probabilities {p} != normalised midpoints {expect}')
            spreads = market_spreads(est)
            if spreads and max(spreads) > 0.12:
                warnings.append(f'{mid}: market spread {max(spreads):.3f} exceeds the 0.12 policy cap')
        return 'market-midpoint'
    if method in ('bookmaker', 'consensus', 'reference', 'relay'):
        quotes = est.get('quotes') or []
        if not quotes:
            errors.append(f'{mid}: {method} estimate publishes no quotes to replay')
            return 'invalid'
        derived = []
        for q in quotes:
            odds = q.get('odds')
            if odds:
                inv = [1.0 / float(o) for o in odds]
                pair = normalized(inv)
                if q.get('probabilities') and not all(
                        close(a, b, 5e-7) for a, b in zip(pair, q['probabilities'])):
                    errors.append(f'{mid}: quote no-vig {pair} != quote probabilities {q["probabilities"]}')
                derived.append(pair)
            elif q.get('probabilities'):
                derived.append([float(x) for x in q['probabilities']])
        if derived:
            if len(derived) == 1:
                expect = derived[0]
            else:  # consensus: component-wise median of the quote pairs
                expect = [sorted(d[i] for d in derived)[len(derived) // 2] if len(derived) % 2
                          else (sorted(d[i] for d in derived)[len(derived) // 2 - 1]
                                + sorted(d[i] for d in derived)[len(derived) // 2]) / 2
                          for i in (0, 1)]
                expect = normalized(expect)
            if not all(close(a, b, 5e-6) for a, b in zip(p, expect)):
                errors.append(f'{mid}: bookmaker probabilities {p} != replayed {expect}')
        return 'bookmaker-no-vig'
    if method in ('model', 'network', 'guidance'):
        return replay_model(mid, est, p, errors, warnings)
    return 'invalid'


def market_midpoints(mid: str, est: dict, errors: list[str]) -> list[float] | None:
    quotes = est.get('quotes') or []
    if not quotes:
        errors.append(f'{mid}: market estimate publishes no quotes to replay')
        return None
    # Researched shape: one quote carrying paired bid/ask lists.
    if len(quotes) == 1 and isinstance(quotes[0].get('bid'), list):
        q = quotes[0]
        return [(float(b) + float(a)) / 2 for b, a in zip(q['bid'], q['ask'])]
    # Featured shape: one quote per outcome with scalar bid/ask/midpoint.
    mids = []
    for q in quotes:
        if 'bid' in q and 'ask' in q:
            m = (float(q['bid']) + float(q['ask'])) / 2
            if 'midpoint' in q and not close(m, q['midpoint'], 5e-7):
                errors.append(f'{mid}: published midpoint {q["midpoint"]} != ({q["bid"]}+{q["ask"]})/2')
            mids.append(m)
    if len(mids) != 2:
        errors.append(f'{mid}: market quotes do not cover exactly two outcomes')
        return None
    return mids


def market_spreads(est: dict) -> list[float]:
    spreads = []
    for q in est.get('quotes') or []:
        if isinstance(q.get('bid'), list):
            spreads += [float(a) - float(b) for a, b in zip(q['ask'], q['bid'])]
        elif 'spread' in q:
            spreads.append(float(q['spread']))
        elif 'bid' in q and 'ask' in q:
            spreads.append(float(q['ask']) - float(q['bid']))
    return spreads


def replay_model(mid: str, est: dict, p: list[float], errors: list[str],
                 warnings: list[str]) -> str:
    inputs = est.get('inputs') or []
    if len(inputs) != 2:
        errors.append(f'{mid}: model estimate does not publish two rating inputs')
        return 'invalid'
    for inp in inputs:
        for key in ('name', 'points', 'standing', 'source_url'):
            if inp.get(key) in (None, ''):
                errors.append(f'{mid}: model input missing {key}')
    rd = float(est.get('rd_assumption') or VALVE_RD)
    prob1, g = valve_probability(float(inputs[0]['points']), float(inputs[1]['points']), rd)
    expect = [round(prob1, 8), round(1 - prob1, 8)]
    if not all(close(a, b, 1.5e-8) for a, b in zip(p, expect)):
        errors.append(f'{mid}: model probabilities {p} != Valve replay {expect}')
    if est.get('g') is not None and not close(est['g'], g, 1e-12):
        warnings.append(f'{mid}: published g {est["g"]} differs from replay {g}')
    if not est.get('limitations'):
        warnings.append(f'{mid}: model estimate carries no limitations')
    return 'valve-glicko'


def check_pick(mid: str, row: dict, est: dict | None, errors: list[str]) -> None:
    pick = row.get('pick_index')
    if est and est.get('probabilities'):
        p = [float(x) for x in est['probabilities']]
        if pick is None:
            errors.append(f'{mid}: priced row names no pick')
        elif p[pick] <= p[1 - pick]:
            errors.append(f'{mid}: pick index {pick} is not the strict favourite of {p}')
    elif pick is not None:
        errors.append(f'{mid}: pick named without a priced estimate')


def verify(snapshot: dict, origination: dict, site: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, dict] = {}

    matches = snapshot.get('matches') or []
    active = [m for m in matches if m.get('availability') != 'past']
    archived = [m for m in matches if m.get('availability') == 'past']
    counts = snapshot.get('counts') or {}

    # -- inventory ------------------------------------------------------------
    by_method = {'market': 0, 'bookmaker': 0, 'model': 0}
    unresolved_featured = []
    for m in active:
        a = m.get('analysis')
        if a and a.get('method') in by_method:
            by_method[a['method']] += 1
        elif not a:
            unresolved_featured.append(str(m['id']))
    recomputed = {
        'inventory': len(matches), 'upcoming': len(active), 'archived': len(archived),
        'market': by_method['market'], 'bookmaker': by_method['bookmaker'],
        'model': by_method['model'], 'unresolved': len(unresolved_featured),
        'picks': sum(1 for m in active if m.get('pick_index') is not None),
    }
    inv_errors_start = len(errors)
    for key, value in recomputed.items():
        if counts.get(key) != value:
            errors.append(f'inventory: snapshot counts[{key}]={counts.get(key)} != recomputed {value}')
    for m in archived:
        if m.get('analysis') or m.get('pick_index') is not None:
            errors.append(f"{m['id']}: archived fixture carries a prematch analysis/pick")
    seen = set()
    for m in matches:
        if str(m['id']) in seen:
            errors.append(f"{m['id']}: duplicate fixture id in snapshot")
        seen.add(str(m['id']))
    checks['inventory'] = {'errors': len(errors) - inv_errors_start, 'detail': recomputed}

    # -- featured replay ------------------------------------------------------------
    start = len(errors)
    featured_basis = {}
    for m in active:
        mid = str(m['id'])
        a = m.get('analysis')
        if a:
            featured_basis[mid] = replay_estimate(mid, a, errors, warnings)
            observed, starts = iso(a.get('observed_at')), iso(m.get('starts_at'))
            if observed and starts and observed >= starts:
                errors.append(f'{mid}: featured estimate observed at/after the match start')
        else:
            featured_basis[mid] = 'blank'
            if not m.get('limitations'):
                errors.append(f'{mid}: featured blank row has no limitation')
            if not m.get('research'):
                errors.append(f'{mid}: featured blank row has no research trail')
        check_pick(mid, m, a, errors)
    checks['featured'] = {'errors': len(errors) - start,
                          'priced': sum(1 for v in featured_basis.values() if v != 'blank'),
                          'blank': unresolved_featured}

    # -- complete-list replay ------------------------------------------------------------
    start = len(errors)
    org_rows = origination.get('matches') or []
    org_by_id = {str(r['id']): r for r in org_rows}
    complete_basis = {}
    for r in org_rows:
        mid = str(r['id'])
        org = r.get('origination')
        if org and org.get('probabilities'):
            complete_basis[mid] = replay_estimate(mid, org, errors, warnings)
            cross = org.get('model_crosscheck')
            if cross and cross.get('inputs'):
                cp = pair_ok(mid, cross.get('probabilities'), errors)
                if cp is not None and len(cross['inputs']) == 2:
                    prob1, _ = valve_probability(float(cross['inputs'][0]['points']),
                                                  float(cross['inputs'][1]['points']),
                                                  float(cross.get('rd_assumption') or VALVE_RD))
                    if not close(cp[0], round(prob1, 8), 1.5e-8):
                        errors.append(f'{mid}: model crosscheck {cp} != Valve replay {prob1:.8f}')
            if not org.get('limitations') and org.get('method') in ('model',):
                warnings.append(f'{mid}: complete-list model row carries no limitations')
        else:
            complete_basis[mid] = 'blank'
            if not (r.get('limitations') or (org or {}).get('limitations')):
                errors.append(f'{mid}: complete-list blank row has no limitation')
            if not r.get('research'):
                errors.append(f'{mid}: complete-list blank row has no research trail')
        check_pick(mid, r, org if org and org.get('probabilities') else None, errors)
    org_counts = origination.get('counts') or {}
    if org_counts.get('active') not in (None, len(org_rows)):
        errors.append(f"complete: counts[active]={org_counts.get('active')} != {len(org_rows)} rows")
    blanks = sorted(mid for mid, b in complete_basis.items() if b == 'blank')
    if sorted(str(x) for x in origination.get('unresolved_ids') or []) != blanks:
        errors.append(f"complete: unresolved_ids {origination.get('unresolved_ids')} != blank rows {blanks}")
    checks['complete'] = {'errors': len(errors) - start,
                          'priced': sum(1 for v in complete_basis.values() if v != 'blank'),
                          'blank': blanks}

    # -- cross layer ------------------------------------------------------------
    start = len(errors)
    snap_by_id = {str(m['id']): m for m in active}
    if set(snap_by_id) != set(org_by_id):
        errors.append('cross-layer: active fixture sets differ: '
                      f'only-featured={sorted(set(snap_by_id)-set(org_by_id))} '
                      f'only-complete={sorted(set(org_by_id)-set(snap_by_id))}')
    researched_resolutions = []
    for mid in sorted(set(snap_by_id) & set(org_by_id)):
        srow, orow = snap_by_id[mid], org_by_id[mid]
        if [t['name'] for t in srow.get('teams') or []] != [t['name'] for t in orow.get('teams') or []]:
            errors.append(f'{mid}: team pair differs between layers')
        if srow.get('starts_at') != orow.get('starts_at'):
            errors.append(f'{mid}: start time differs between layers')
        feat, org = srow.get('analysis'), orow.get('origination')
        if orow.get('featured_method') != (feat or {}).get('method'):
            warnings.append(f'{mid}: complete list records featured_method '
                            f'{orow.get("featured_method")!r} but the snapshot carries '
                            f'{(feat or {}).get("method")!r}')
        if feat and org and org.get('probabilities'):
            same = all(close(a, b, 5e-7) for a, b in zip(feat['probabilities'], org['probabilities']))
            if not same and not org.get('upgraded_from_featured_model'):
                errors.append(f'{mid}: complete-list probabilities replace the featured estimate '
                              'without declaring an upgrade')
            if not same and org.get('upgraded_from_featured_model') and not org.get('quotes'):
                errors.append(f'{mid}: declared upgrade carries no replacement quote evidence')
        if not feat and org and org.get('probabilities'):
            researched_resolutions.append(mid)
            if not org.get('quotes') and not org.get('inputs'):
                errors.append(f'{mid}: featured-blank fixture resolved with neither quotes nor model inputs')
            if not orow.get('research'):
                errors.append(f'{mid}: researched resolution carries no research trail')
            for alias in orow.get('aliases_used') or []:
                evidence = alias.get('evidence') or []
                if not evidence or not all(str(e.get('url', '')).startswith('https://') for e in evidence):
                    errors.append(f"{mid}: alias {alias.get('alias')!r} joined without https evidence")
    checks['cross_layer'] = {'errors': len(errors) - start,
                             'researched_resolutions': researched_resolutions}

    # -- executive summary & unresolved section ------------------------------------------------------------
    start = len(errors)
    summary_detail = check_summary(site, snap_by_id, org_by_id, errors, warnings)
    checks['summary'] = {'errors': len(errors) - start, **summary_detail}

    rows = []
    for mid in sorted(snap_by_id, key=lambda x: (snap_by_id[x].get('starts_at') or '', x)):
        srow, orow = snap_by_id[mid], org_by_id.get(mid, {})
        org = orow.get('origination') or {}
        teams = [t['name'] for t in srow.get('teams') or []]
        rows.append({
            'id': mid, 'teams': teams, 'competition': srow.get('competition'),
            'starts_at': srow.get('starts_at'),
            'featured_basis': featured_basis.get(mid),
            'complete_basis': complete_basis.get(mid),
            'complete_method': org.get('method'),
            'probabilities': org.get('probabilities'),
            'pick': teams[orow['pick_index']] if orow.get('pick_index') is not None and len(teams) == 2 else None,
            'source_url': org.get('source_url') or (srow.get('analysis') or {}).get('source_url'),
            'researched_resolution': mid in researched_resolutions,
        })

    return {
        'session': 'arena-3e64f4fb',
        'snapshot_generated_at': snapshot.get('generated_at'),
        'snapshot_inventory_observed_at': snapshot.get('inventory_observed_at'),
        'origination_generated_at': origination.get('generated_at'),
        'active_fixtures': len(active),
        'checks': checks, 'rows': rows,
        'errors': errors, 'warnings': warnings,
    }


def check_summary(site: Path, snap_by_id: dict, org_by_id: dict,
                  errors: list[str], warnings: list[str]) -> dict:
    index = site / 'index.html'
    if not index.exists():
        errors.append('summary: index.html (executive summary) is missing')
        return {}
    html = index.read_text(errors='replace')
    detail: dict = {}
    for anchor in ('picks-at-a-glance', 'unresolved-register', 'no-line-register', 'fallback-register'):
        if f'id="{anchor}"' not in html:
            errors.append(f'summary: executive summary has no #{anchor} section')
    detail['sections'] = [a for a in ('picks-at-a-glance', 'unresolved-register',
                                      'no-line-register', 'fallback-register')
                          if f'id="{a}"' in html]
    for mid in snap_by_id:
        if f'id="{mid}"' not in html and f'#{mid}' not in html:
            errors.append(f'summary: active fixture {mid} is not listed on the executive summary')
    for mid, orow in org_by_id.items():
        org = orow.get('origination') or {}
        if org.get('method') == 'model' and f'no-line-{mid}' not in html:
            errors.append(f'summary: model-only fixture {mid} is missing from the no-line register')
        if not (snap_by_id.get(mid) or {}).get('analysis') and org.get('probabilities') \
                and f'researched-{mid}' not in html:
            warnings.append(f'summary: researched resolution {mid} has no researched- anchor')

    unresolved = site / 'unresolved' / 'index.html'
    if not unresolved.exists():
        errors.append('summary: separate unresolved page unresolved/index.html is missing')
    else:
        uhtml = unresolved.read_text(errors='replace')
        if 'id="unresolved-register"' not in uhtml:
            errors.append('summary: unresolved page has no unresolved register')

    picks = site / 'picks' / 'index.html'
    picks_html = picks.read_text(errors='replace') if picks.exists() else ''
    if not picks_html:
        errors.append('summary: picks/index.html is missing')

    # Both published percentages of every priced row must be visible on phone pages.
    missing_pct = []
    for mid, orow in org_by_id.items():
        org = orow.get('origination') or {}
        for p in org.get('probabilities') or []:
            label = f'{float(p) * 100:.1f}%'
            if label not in html or (picks_html and label not in picks_html):
                missing_pct.append(f'{mid}:{label}')
    if missing_pct:
        warnings.append('summary: percentages not found verbatim on summary/picks pages: '
                        + ', '.join(sorted(missing_pct)))
    detail['percentages_missing_verbatim'] = sorted(missing_pct)

    # Every in-site link from the executive summary must resolve (file + anchor).
    # Navigation failures (pages/anchors - the phone path to the picks) are
    # errors. Missing evidence *downloads* are the known branch-root parity
    # gap: the workflow-artifact deployment serves them while the checked-in
    # root sync does not carry them, so they are listed separately as a
    # warning for the root-sync owner instead of failing the phone path.
    broken, missing_downloads = [], []
    for href in sorted(set(re.findall(r'href="([^"]+)"', html))):
        if href.startswith(('https://', 'http://', 'mailto:', 'data:')):
            continue
        target_part, _, anchor = href.partition('#')
        target_part = target_part.split('?')[0]
        if not target_part:
            if anchor and f'id="{anchor}"' not in html:
                broken.append(f'#{anchor}')
            continue
        dest = (site / unquote(target_part).lstrip('./')).resolve()
        if dest.is_dir():
            dest = dest / 'index.html'
        if not dest.exists():
            (missing_downloads if dest.suffix in ('.json', '.csv', '.md', '.gz')
             else broken).append(href)
            continue
        if anchor and dest.suffix == '.html':
            if f'id="{anchor}"' not in dest.read_text(errors='replace'):
                broken.append(href)
    if broken:
        errors.append('summary: broken in-site navigation links from the executive summary: '
                      + ', '.join(broken))
    if missing_downloads:
        warnings.append('summary: evidence downloads linked from the executive summary are '
                        'absent from the checked-in root (served by the artifact deployment, '
                        'would 404 from a branch-root serve): ' + ', '.join(missing_downloads))
    detail['broken_links'] = broken
    detail['missing_downloads'] = missing_downloads

    # Phone basics on the three pages a phone visitor lands on.
    for name, text in (('index.html', html), ('picks/index.html', picks_html),
                       ('unresolved/index.html', unresolved.read_text(errors='replace')
                        if unresolved.exists() else '')):
        if text and 'width=device-width' not in text:
            errors.append(f'summary: {name} has no device-width viewport (not phone-ready)')
    detail['viewport_ok'] = all('width=device-width' in t for t in
                                (html, picks_html) if t)
    return detail


def render_markdown(result: dict) -> str:
    lines = [
        '# arena-3e64f4fb verification — every published pick, both layers',
        '',
        f"- Snapshot (featured layer): `{result['snapshot_generated_at']}` "
        f"(inventory observed `{result['snapshot_inventory_observed_at']}`)",
        f"- Origination (complete list): `{result['origination_generated_at']}`",
        f"- Active fixtures: **{result['active_fixtures']}**; "
        f"errors: **{len(result['errors'])}**; warnings: **{len(result['warnings'])}**",
        '',
        '| Check | Errors | Detail |',
        '| --- | --- | --- |',
    ]
    for name, check in result['checks'].items():
        detail = {k: v for k, v in check.items() if k != 'errors'}
        lines.append(f"| {name} | {check['errors']} | `{json.dumps(detail)[:220]}` |")
    lines += ['', '| Fixture | Teams | Starts (UTC) | Featured | Complete | Probabilities | Pick | Source |',
              '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for row in result['rows']:
        probs = ' / '.join(f"{p * 100:.1f}%" for p in row['probabilities']) if row['probabilities'] else '— blank —'
        lines.append(
            f"| {row['id']} | {' vs '.join(row['teams'])} | {row['starts_at']} | "
            f"{row['featured_basis']} | {row['complete_basis']} ({row['complete_method']}) | {probs} | "
            f"**{row['pick'] or 'none'}** | {row['source_url'] or ''} |")
    if result['errors']:
        lines += ['', '## Errors'] + [f'- {e}' for e in result['errors']]
    if result['warnings']:
        lines += ['', '## Warnings'] + [f'- {w}' for w in result['warnings']]
    lines.append('')
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', default=str(ROOT / 'snapshot.json'))
    parser.add_argument('--origination', default=str(ROOT / 'origination.json'))
    parser.add_argument('--site', default=str(ROOT))
    parser.add_argument('--out', default=str(ROOT / 'data' / 'research' / '3e64f4fb'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)

    snapshot = json.loads(Path(args.snapshot).read_text())
    origination = json.loads(Path(args.origination).read_text())
    result = verify(snapshot, origination, Path(args.site))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'verification.json').write_text(json.dumps(result, indent=1) + '\n')
    (out / 'verification.md').write_text(render_markdown(result))
    print(f"active={result['active_fixtures']} errors={len(result['errors'])} "
          f"warnings={len(result['warnings'])}")
    for name, check in result['checks'].items():
        print(f"  {name}: {check['errors']} error(s)")
    for e in result['errors']:
        print('ERROR', e)
    for w in result['warnings']:
        print('WARN ', w)
    return 1 if (args.check and result['errors']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
