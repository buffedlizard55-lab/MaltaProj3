"""Render the mobile-first 'Originated picks' section from data/origination.json.

Output: one self-contained page (origination/index.html) with:
  1. an executive summary with one-tap links to every part of the site,
  2. the full picks list — every active Hotspawn CS2 fixture with both team
     probabilities and one obvious pick,
  3. a separate Unresolved Picks & Limitations section (empty-state honest),
  4. the methodology ladder, verified alias registry and source register.

Every table row links to its original first-party sources. Values that could
not be confirmed render as '— unverified' and are never inferred.

Usage: python -m scripts.build_origination [--output site] [--source data]
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.domain import is_fresh, timestamp
from scripts.pick_safety import (body_attributes, card_attributes, presentation, status_html, valid_pair)

MALTA = ZoneInfo('Europe/Malta')
REPO = 'https://github.com/buffedlizard55-lab/MaltaProj3'
LOBBY = 'https://play.hotspawn.com/lobby'


def e(value):
    return html.escape(str(value), quote=True)


def local_time(value):
    dt = timestamp(value)
    if not dt:
        return '<span class="unverified">— <small>unverified</small></span>'
    malta = dt.astimezone(MALTA).strftime('%d %b, %H:%M')
    utc = dt.astimezone(timezone.utc).strftime('%H:%M UTC')
    return f'<time datetime="{e(value)}">{e(malta)} <small>({e(utc)})</small></time>'


def ext(url, text):
    return f'<a class="src" href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(text)} <span aria-hidden="true">↗</span></a>'


def badge(text, kind='neutral'):
    return f'<span class="badge {e(kind)}">{e(text)}</span>'


def team_names(m):
    return [t['name'] or 'Unverified team' for t in m['teams']]


def pick_row(m, safety=None, now=None):
    sourced = m.get('origination')
    o = sourced if sourced and valid_pair(sourced.get('probabilities')) else None
    names = team_names(m)
    pick = m['pick_index']
    safety = safety or presentation(m, None, False, now or datetime.now(timezone.utc))
    current = safety['current']
    hidden = '' if current else ' hidden'
    historical_hidden = ' hidden' if current else ''
    card_class = "pick-card" if current else "pick-card is-historical"
    out = [f'<article class="{card_class}" id="match-{e(m["id"])}" '
           f'{card_attributes(m, safety)} data-was-current="{str(current).lower()}">']
    out.append(f'<header class="card-head"><span class="comp">{e(m["competition"] or "Unverified tournament")}</span>'
               f'<span class="tier">{e((m.get("tier") or "").upper() and "Tier " + str(m.get("tier")).upper() or "Tier unverified")}</span></header>')
    out.append(f'<h3 class="teams"><strong>{e(names[0])}</strong><span class="vs">vs</span><strong>{e(names[1])}</strong></h3>')
    out.append(f'<p class="when">Starts {local_time(m["starts_at"])}<br>Locks {local_time(m.get("locks_at"))}</p>')
    out.append(status_html(safety))
    if o:
        p0, p1 = o['probabilities']
        favored = pick
        out.append('<ul class="probs">')
        for i, (name, p) in enumerate(zip(names, o['probabilities'])):
            cls = ' class="fav"' if i == favored else ''
            marker = f'<span data-current-only{hidden}> ✓ pick</span>' if i == favored else ''
            out.append(f'<li{cls}><span>{e(name)}{marker}</span><strong>{p * 100:.1f}%</strong></li>')
        out.append('</ul>')
        w = max(0.0, min(100.0, p0 * 100))
        out.append(f'<div class="bar" role="presentation"><span class="a" style="width:{w:.3f}%"></span><span class="b" style="width:{100 - w:.3f}%"></span></div>')
        if pick is not None:
            out.append(f'<p class="pick-line"><span data-current-only{hidden}>Pick: </span><span data-historical-only{historical_hidden}>Snapshot lean: </span><strong>{e(names[pick])}</strong> <small>({o["probabilities"][pick] * 100:.1f}% · fair line {e(o["fair_decimal"][pick])})</small></p>')
        else:
            out.append('<p class="pick-line">Pick: <strong>No directional edge</strong> <small>(equal estimate)</small></p>')
        out.append(f'<p class="line-time">Estimate observed {local_time(o.get("observed_at"))}.<span data-historical-only{historical_hidden}> Historical / unverified for current use.</span></p>')
        money = o['method'] in {'market', 'bookmaker', 'consensus', 'reference'}
        kind = 'green' if money else 'purple'
        label = 'Money-backed line' if money else 'Research model'
        if o['method'] == 'reference':
            label = 'Aggregated money line · third-party bookmaker average'
        if o['method'] == 'guidance':
            label = 'Wide-book guidance · indicative only'
            kind = 'amber'
        if any(isinstance(q, dict) and q.get('thin') for q in o.get('quotes', [])):
            label += ' · thin market'
            kind = 'amber'
        out.append(f'<p class="basis">{badge(label, kind)} <span class="method">{e(o["label"])}</span></p>')
        # One link per distinct source URL (featured market rows carry one quote per
        # outcome, which used to print the same Polymarket link three times).
        links, seen = [], set()

        def add(url, text):
            if url and url not in seen:
                seen.add(url)
                links.append(ext(url, text))
        add(m['source_url'], 'Hotspawn')
        quotes = [q for q in o.get('quotes', []) if isinstance(q, dict) and q.get('source_url')]
        for q in quotes:
            add(q['source_url'], q.get('provider', 'source'))
        if not quotes:
            add(o['source_url'], o.get('source', 'Analysis source'))
        if o.get('model_crosscheck'):
            add(o['model_crosscheck'].get('source_url'), 'Valve model cross-check')
        out.append('<p class="row-srcs">' + ' · '.join(links) + '</p>')
    else:
        out.append('<ul class="probs"><li><span>' + e(names[0]) + '</span><strong class="unverified">—</strong></li>'
                   f'<li><span>{e(names[1])}</span><strong class="unverified">—</strong></li></ul>')
        out.append('<p class="pick-line">Pick: <strong class="unverified">Unresolved</strong> <small>no verified inputs — see limitations</small></p>')
        out.append('<p class="row-srcs">' + ext(m['source_url'], 'Hotspawn') + '</p>')
    if m.get('aliases_used'):
        used = ', '.join(f"{a['alias']} → {a['canonical']}" for a in m['aliases_used'])
        out.append(f'<p class="alias-note">Verified alias join: {e(used)}</p>')
    if m.get('upgraded_from_featured_model') and m.get('featured_probabilities'):
        fp = m['featured_probabilities']
        if (m.get('origination') or {}).get('tie_break_of'):
            out.append(f'<p class="alias-note">Tie-break direction: the featured official-rating estimate was exactly level '
                       f'({fp[0] * 100:.1f}% / {fp[1] * 100:.1f}%). A dated independent research rung separates the teams; '
                       'the level pair is retained for audit and the result is not a bookmaker price.</p>')
        elif m.get('featured_method') == 'model':
            out.append(f'<p class="alias-note">Upgraded from the featured Valve-model estimate ({fp[0] * 100:.1f}% / {fp[1] * 100:.1f}%): the alias-aware research found a verified money-backed line, which replaces the uncalibrated model.</p>')
        else:
            out.append(f'<p class="alias-note">Upgraded from the featured {e(m.get("featured_method") or "equal")} tie ({fp[0] * 100:.1f}% / {fp[1] * 100:.1f}%): the alias-aware research found a directional money-backed line.</p>')
    details = '<details><summary>Research trail &amp; limitations</summary>'
    details += '<ol class="trail">'
    for r in m.get('research', []):
        details += (f'<li><strong>{e(r["stage"])}</strong> · {e(r["status"])}<p>{e(r["detail"])}</p>'
                    + ext(r['source_url'], 'Original source') + '</li>')
    details += '</ol>'
    if m.get('limitations'):
        details += '<ul class="limits">' + ''.join(f'<li>{e(x)}</li>' for x in m['limitations']) + '</ul>'
    for a in m.get('aliases_used', []):
        details += f'<p class="tiny"><strong>Alias evidence for {e(a["alias"])} → {e(a["canonical"])}</strong></p><ul class="limits">'
        for ev in a['evidence']:
            details += f'<li>{e(ev.get("detail", ""))} {ext(ev["url"], ev.get("source", "source"))}</li>'
        details += '</ul>'
    details += '</details>'
    out.append(details)
    out.append('</article>')
    return ''.join(out)


SHORT_STAGE = [
    ('HLTV', 'HLTV'), ('Betting market (Polymarket', 'Polymarket'), ('Exchange market (Kalshi', 'Kalshi'),
    ('Esportsbook line (Thunderpick', 'Thunderpick'), ('Esportsbook line (Bovada', 'Bovada'),
    ('Esportsbook line', 'Esportsbook'), ('Research model', 'Valve rating model'), ('Fixture identity', 'Fixture identity'),
]


def short_stage(stage):
    return next((label for prefix, label in SHORT_STAGE if str(stage).startswith(prefix)), str(stage))


def unresolved_card(m):
    """Phone-first card: what every source showed for a match that has no verified pick."""
    names = team_names(m)
    # Deliberately NOT .pick-card: the picks list owns exactly one .pick-card per fixture
    # (scripts/verify_live.py asserts that set after every deployment).
    out = [f'<article class="unresolved-card" id="unresolved-{e(m["id"])}">',
           f'<header class="card-head"><span class="comp">{e(m.get("competition") or "Unverified tournament")}</span>'
           f'<span class="tier">{badge("No verified pick", "amber")}</span></header>',
           f'<h3 class="teams"><strong>{e(names[0])}</strong><span class="vs">vs</span><strong>{e(names[1])}</strong></h3>',
           f'<p class="when">{local_time(m["starts_at"])}</p>',
           '<p class="pick-line">Pick: <strong class="unverified">Unresolved</strong> '
           '<small>both win % left blank — no default 50/50</small></p>',
           '<ul class="findings">']
    for r in m.get('research', []):
        if r.get('stage') == 'Origination result':
            continue
        out.append(f'<li><strong>{e(short_stage(r["stage"]))}</strong> <span class="status">{e(r["status"])}</span> — '
                   f'{e(r["detail"])} {ext(r["source_url"], "source")}</li>')
    out.append('</ul>')
    out.append('<p class="row-srcs">' + ext(m['source_url'], 'Hotspawn fixture')
               + f' · <a class="src" href="#match-{e(m["id"])}">Full research trail ↓</a></p></article>')
    return ''.join(out)


def section_unresolved(data):
    rows = [m for m in data['matches'] if m['origination'] is None]
    out = ['<section class="block" id="unresolved"><h2>Unresolved picks &amp; limitations</h2>']
    out.append('<p class="lede">Every match without a verified pick is listed here with what each source actually showed — '
               'HLTV identity first, then every betting market and esportsbook, then the rating model. '
               'Thin or wide books are recorded for guidance but never turned into a pick. '
               'Missing values stay blank — no default 50/50, no invented lines. '
               'An unavailable source is never treated as proof that a market does not exist.</p>')
    if not rows:
        out.append(f'<div class="ok-note"><strong>No unresolved fixtures in this snapshot.</strong> '
                   f'All {data["counts"]["active"]} active Hotspawn CS2 fixtures have a researched pick as of {local_time(data["generated_at"])}. '
                   'This is a dated observation, not a permanent guarantee — the inventory refreshes every four hours and new fixtures can appear without lines.</div>')
    else:
        out.append(f'<p class="tiny">{len(rows)} of {data["counts"]["active"]} active fixtures are unresolved in this snapshot. '
                   'Lines for low-tier and later-dated matches often open closer to start time; every four-hour refresh retries all sources.</p>')
        out.append('<div class="cards">' + ''.join(unresolved_card(m) for m in rows) + '</div>')
    out.append('<h3>Standing limitations for originated picks</h3><ul class="limits">')
    out.append('<li>Hotspawn participation percentages are <strong>never</strong> a probability input, and neither are HLTV fan votes. '
               'Only paired betting/market prices and official published ratings produce numbers.</li>')
    out.append('<li>Prediction-market and exchange books (Polymarket, Kalshi) pass the featured path only at a spread of 12 cents or less. '
               'The fallback ladder accepts a two-sided book up to 15 cents and marks anything above 12 cents as thin; '
               'wider books are rejected, and their observed quotes are shown on unresolved cards for guidance only.</li>')
    out.append('<li>The aggregated bookmaker rung is a <strong>third-party average published by EGamersWorld</strong>, not a first-party bookmaker quote. It is used only for fixtures the entire first-party ladder leaves blank, must be fresh and hash-matched to its captured sentence, and is rejected when both sides print identical prices or observations contradict each other. Those rejected captures are listed below with their reason.</li>')
    out.append('<li>The Valve-rating fallback model is <strong>uncalibrated</strong>: it is not observed betting odds and has not been backtested. '
               'It is used only when no money source resolves a match.</li>')
    out.append('<li>Provider display names are joined only through the verified alias registry below. Unregistered names stay unmatched.</li>')
    out.append('<li>Series format (best-of) is unverified on Hotspawn fixtures; estimates target the full-series winner where the market does, else the match winner as published.</li>')
    out.append('<li>Past-start fixtures are never given retrospective prematch picks; the source archive retains them without manufactured probabilities.</li>')
    out.append('</ul></section>')
    return ''.join(out)


def section_aliases(data):
    registry = data['alias_registry']
    out = ['<section class="block" id="aliases"><h2>Verified alias registry</h2>',
           '<p class="lede">Provider name joins are the hardest failure mode for low-tier coverage: the same team appears as '
           '"WROTBERRY" on Hotspawn, "WBT" on HLTV/Polymarket/Thunderpick and in Valve\'s standings. '
           'Each join below is backed by official source links. Names outside this registry are never force-matched.</p>']
    for a in registry['aliases']:
        scope = a.get('applies_to') or ['any competition (legacy unscoped entry)']
        out.append(f'<article class="alias-card"><h3>{e(a["alias"])} <span aria-hidden="true">→</span> {e(a["canonical"])} {badge(a["kind"], "neutral")}</h3>')
        out.append(f'<p class="tiny">Applies only inside: {e(", ".join(scope))}</p>')
        if a.get('review_note'):
            out.append(f'<p class="review-note" role="note"><strong>⚑ Flagged for review:</strong> {e(a["review_note"])}</p>')
        out.append('<ul class="limits">')
        for ev in a['evidence']:
            out.append(f'<li>{e(ev.get("detail", ""))} {ext(ev["url"], ev.get("source", "source"))}</li>')
        out.append('</ul></article>')
    out.append(f'<p class="tiny">Registry file: <code>data/origination/aliases.json</code> · last reviewed {e(registry.get("updated_at", ""))} · policy: {e(registry.get("policy", ""))}</p></section>')
    return ''.join(out)


def section_method(data):
    p = data['policy']
    out = ['<section class="block" id="method"><h2>How each pick is produced</h2>',
           '<p class="lede">Featured money-line estimates remain unchanged. For unresolved or model-only fixtures, recorded HLTV research informs identity checks, then paired external prices are validated; accepted money lines may replace the lowest-rung model. Accepted independent money sources can be combined; official ratings are a final fallback. Hotspawn supplies the match list only.</p>',
           '<ol class="ladder">']
    for step in p['ladder']:
        out.append(f'<li>{e(step)}</li>')
    out.append('</ol>')
    out.append('<h3>Model note</h3><p>When a research model is used, the win probability is a 400-point logistic transform, '
               'the scale in Valve\'s own <a class="src" href="https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js">model/fit.js</a> '
               f'(fixed rating deviation {e(p.get("rd_assumption", 75))}). The inputs differ by rung and are named on every row: '
               'official Valve standings points; a results-based fit for one unrated side; our own Bradley–Terry network fit over '
               'bo3.gg finished series anchored on Valve points (session 541cd43a); or HLTV\'s published weekly world-ranking points. '
               'Each model row publishes its own inputs, sample size and uncertainty, and no model ever overrides a market or esportsbook price.</p>')
    out.append(f'<p class="tiny">Start-time join tolerance: ±{int(p["start_tolerance_sec"] / 60)} min; any disagreement beyond 60 seconds is published as a flag, never silently corrected. '
               f'Thin-market threshold: spread &gt; {e(p["thin_spread"])}; rejection ceiling: spread &gt; {e(p["max_accepted_spread"])}.</p></section>')
    return ''.join(out)


def section_sources(data):
    out = ['<section class="block" id="sources"><h2>Source register</h2>',
           '<div class="table-wrap"><table class="simple"><thead><tr><th>Source</th><th>Role in origination</th></tr></thead><tbody>']
    for s in data['sources']:
        links = ext(s['url'], s['name'])
        if s.get('api_url'):
            links += ' ' + ext(s['api_url'], 'API')
        out.append(f'<tr><th scope="row">{links}</th><td>{e(s["role"])}</td></tr>')
    out.append('</tbody></table></div>')
    out.append(f'<p class="tiny">Snapshot {e(data["source_snapshot_at"] or "unverified")} · page generated {e(data["generated_at"])} · '
               f'open data: <a class="src" href="../data/origination.json">data/origination.json</a> · '
               f'saved evidence: <a class="src" href="../data/origination/aliases.json">alias evidence registry</a></p></section>')
    return ''.join(out)


def executive_summary(data):
    c = data['counts']
    out = ['<section class="hero" id="summary"><p class="kicker">EXECUTIVE SUMMARY · COMPLETE SOURCE SNAPSHOT · INDEPENDENT LINES</p>',
           '<h1>Hotspawn CS2 match picks.<br>Source-backed or explicitly unresolved.</h1>']
    out.append(f'<p class="hero-stats"><strong>{c["active"]}</strong> snapshot fixtures · <strong>{c["with_pick"]}</strong> with a sourced lean · '
               f'<strong>{c["unresolved"]}</strong> unresolved · {c["consensus"]} consensus, {c["market"] + c["bookmaker"]} single-source, '
               f'{c.get("reference", 0)} aggregated, {c["model"]} model-backed.</p>')
    out.append('<nav class="quick" aria-label="Jump to section">'
               '<a class="q primary" href="#picks">📋 Updated picks list <small>all matches</small></a>'
               '<a class="q" href="#unresolved">🚩 Unresolved &amp; limitations <small>what we can’t verify</small></a>'
               '<a class="q" href="#method">🧭 Methodology <small>how the line is made</small></a>'
               '<a class="q" href="#aliases">🔗 Verified aliases <small>name joins</small></a>'
               '<a class="q" href="#sources">📚 Sources <small>first-party links</small></a>'
               '<a class="q" href="../">🏠 Main dashboard <small>executive summary</small></a>'
               '<a class="q" href="../picks/">🎯 Featured picks feed <small>market pipeline</small></a>'
               '<a class="q" href="../review/">🚩 Flagged for review <small>main register</small></a>'
               '</nav>')
    out.append('<p class="hero-note">Probabilities are calculated from external betting markets and official ratings — '
               'never from Hotspawn popularity. Pick percentages are estimates, not guarantees. Featured money-backed estimates are preserved. Alias-aware research also runs for fixtures the featured methods did not resolve and for fixtures whose featured estimate is only the uncalibrated Valve model; a verified money line replaces that model and the card says so.</p></section>')
    return ''.join(out)


def page(data, inventory_complete=True, *, now=None):
    c = data['counts']
    now = now or datetime.now(timezone.utc)
    states = {m['id']: presentation(m, data['source_snapshot_at'], inventory_complete, now) for m in data['matches']}
    current_count = sum(s['current'] for s in states.values())
    stale = not is_fresh(data['source_snapshot_at'], now)
    warn = ('<div class="stale" role="status"><strong>Snapshot freshness is unverified.</strong> Inventory is outside the eight-hour window or its time is unverified. '
            'Treat these lines as historical. <a class="src" href="../coverage/">Check source status →</a></div>') if stale else ''
    if not inventory_complete:
        warn = ('<div class="stale" role="status" id="inventory-warning"><strong>Current Hotspawn inventory is unverified.</strong> '
                'This page retains the last observed fixtures and their original timestamps. New or changed matches may be missing; '
                'a pick for every retained row does not establish current full coverage. Do not treat this as a fully current picks list. '
                '<a class="src" href="../coverage/">Source status</a> · <a class="src" href="../review/">Flagged for Review</a></div>') + warn
    picks = [m for m in data['matches']]
    cards = ''.join(pick_row(m, states[m['id']]) for m in picks) if picks else '<div class="ok-note">No active fixtures in this snapshot. Check the <a class="src" href="../coverage/">source status</a>.</div>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Originated CS2 picks — every Hotspawn match · Spawn Scout</title>
<meta name="description" content="A researched pick and win probability for every Hotspawn CS2 fixture, from external betting lines, HLTV identity research and official Valve ratings. Mobile-friendly.">
<meta name="theme-color" content="#142534">
<link rel="icon" href="../assets/scout-mark.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/origination.css">
<script src="../assets/pick-safety.js" defer></script>
</head><body {body_attributes(data["source_snapshot_at"], inventory_complete)}>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><p class="brand"><a href="../">spawn<strong>scout</strong></a> <span>· originated picks</span></p>
<p class="snap">Snapshot {local_time(data['source_snapshot_at'])} · generated {local_time(data['generated_at'])}</p></header>
<main id="main">
{warn}
{executive_summary(data)}
<p class="availability-summary"><strong data-current-count>{current_count}</strong> currently usable line(s). Snapshot counts above include unresolved, locked and historical rows; no fixture is dropped.</p>
<p class="stale" data-runtime-safety-notice role="status"{' hidden' if current_count == len(picks) else ''}>{current_count} currently usable line(s). Other cards are unresolved, closed or historical; their estimates and sources remain visible.</p>
<noscript><p class="stale">JavaScript is off: lock/freshness labels were checked when this page was built and will not update while it stays open. Check the printed lock and observation times before using a pick; reload for the latest verified snapshot.</p></noscript>
<section class="block" id="picks"><h2>Updated picks — all matches</h2>
<p class="lede">Every active Hotspawn CS2 fixture, sorted by start time. The check-marked team is a current pick only while its line, inventory and confirmed lock remain usable. A “Snapshot lean” is historical or unverified for current use, not a submission recommendation. Both teams’ sourced estimates and original observation times stay visible.</p>
<div class="cards">{cards}</div></section>
{section_unresolved(data)}
{section_method(data)}
{section_aliases(data)}
{section_sources(data)}
</main>
<footer><p><strong>Better context. Clearer picks.</strong></p>
<p>Independent research dashboard · not affiliated with Hotspawn, HLTV, Valve, Polymarket or any betting provider. Informational use only. 18+ where applicable. No bets are placed.</p>
<p class="tiny"><a class="src" href="../methodology/">Main methodology</a> · <a class="src" href="../review/">Flagged for Review</a> · <a class="src" href="{REPO}">Source repository</a></p></footer>
</body></html>'''


def validate_origination(data, source):
    """Replay fallback quotes from saved first-party responses before rendering."""
    from scripts.originate import load_registry, align_by_name
    from scripts.domain import no_vig, normalize_pair
    from statistics import median
    canonical = json.loads((source / 'latest.json').read_text())
    registry = load_registry(source / 'origination/aliases.json')
    originals = {m['id']: m for m in canonical['matches'] if m['availability'] != 'past'}
    assert len({m['id'] for m in data['matches']}) == len(data['matches']), 'Duplicate originated fixture ID'
    assert set(originals) == {m['id'] for m in data['matches']}, 'Origination inventory differs from canonical snapshot'
    assert data['source_snapshot_at'] == canonical['inventory_observed_at'], 'Origination belongs to another inventory observation'
    for m in data['matches']:
        raw = originals[m['id']]
        facts = ('teams', 'starts_at', 'locks_at', 'availability', 'competition', 'tier', 'source_url', 'lobby_url')
        assert all(m.get(k) == raw.get(k) for k in facts), 'Fixture facts or confirmed pick deadline changed'
        o = m.get('origination')
        if raw.get('analysis'):
            # Session arena-13bdd12a: a featured model that produced an exact
            # tie may be replaced by a documented tie-break direction. That is
            # not a money line, so it has its own branch: the published
            # probabilities must differ, the level primary pair must be kept
            # verbatim in `tie_break_of`, and the row must be marked.
            tie_break_upgrade = bool(o) and bool(o.get('tie_break_of')) and (
                raw['analysis'].get('method') == 'model'
                and raw.get('pick_index') is None and m.get('pick_index') is not None
            )
            upgraded = bool(o) and o.get('method') in {'market', 'bookmaker', 'consensus', 'reference'} and (
                raw['analysis'].get('method') == 'model'
                or (raw.get('pick_index') is None and m.get('pick_index') is not None)
            )
            if not upgraded and not tie_break_upgrade:
                assert o and o['probabilities'] == raw['analysis']['probabilities'], 'Featured probabilities changed'
                assert m['pick_index'] == raw['pick_index'], 'Featured pick changed'
                continue
            if tie_break_upgrade:
                assert o['tie_break_of']['probabilities'] == raw['analysis']['probabilities'], \
                    'Tie-break row must preserve the level featured pair'
                assert m.get('upgraded_from_featured_model') is True, \
                    'Tie-break row replaced a featured model without being marked'
                assert any(r.get('stage') == 'Tie-break research' for r in m.get('research') or []), \
                    'Tie-break row has no dated research record'
                # Fall through: the underlying research rung must still replay
                # from its own saved evidence exactly like any other model row.
            else:
                # Permitted changes to a featured estimate: a verified money-backed line replaces a featured
                # *model* estimate, or a directional money-backed line resolves a featured 50/50 tie.
                # Either must be marked and is replayed from its saved first-party responses below.
                assert m.get('upgraded_from_featured_model') is True, 'Money-backed line replaced a featured model without being marked'
        if not o:
            assert m['pick_index'] is None
            continue
        if o['method'] == 'model' and o.get('source') == 'HLTV world ranking':
            from scripts import hltv_ranking
            rows, meta = hltv_ranking.load(source / 'origination/evidence')
            expected, reason = hltv_ranking.estimate(raw, rows, registry, timestamp(data['generated_at']), meta=meta)
            assert expected and expected['probabilities'] == o['probabilities'], \
                'HLTV ranking model differs from the saved official ranking capture: ' + str(reason)
            if 'evaluation_at' in o:
                assert expected['observed_at'] == o['observed_at'], 'HLTV ranking source observation restamped'
                assert expected['inputs'] == o['inputs'], 'HLTV ranking input records changed'
                assert expected['evidence_file'] == o['evidence_file'], 'HLTV ranking original source changed'
        elif o['method'] == 'model' and (o.get('family') == 'form'
                                       or any((q or {}).get('family') == 'form' for q in o.get('quotes') or [])):
            # Lowest rung: re-derive the published probability from the
            # published inputs only. Each unrated side carries the sample size
            # its rating deviation came from, so the check needs no live
            # evidence and cannot drift with a rebuild.
            import math
            from scripts import form_model
            inputs = o.get('inputs') or []
            assert len(inputs) == 2, 'Results-model quote must publish two inputs'
            for row in inputs:
                assert str(row.get('source_url') or '').startswith('https://'), row.get('name')
            assert any(str(row.get('source_url') or '').startswith('https://bo3.gg/')
                       for row in inputs if row.get('fitted')), 'Fitted input lacks its bo3.gg link'
            fitted_n = [row['fitted']['n'] for row in inputs if row.get('fitted')]
            assert fitted_n, 'Results-model quote must show the sample it was fitted on'
            rd = min(400.0, 150.0 + 300.0 / math.sqrt(max(1, min(fitted_n))))
            expected = form_model.win_probability(inputs[0]['points'], inputs[1]['points'], rd)
            assert abs(expected - o['probabilities'][0]) < 1e-9, 'Results-model arithmetic differs from its published inputs'
            assert o.get('samples'), 'Results-model quote must publish the series it used'
            for sample in o['samples']:
                assert str(sample.get('source_url') or '').startswith('https://bo3.gg/')
        elif o['method'] == 'model' and o.get('family') == 'network':
            # Session 541cd43a own-line network model: the published probability
            # must re-derive from its own two published ratings and the saved
            # results-graph evidence; a changed rating, graph or hash fails.
            from scripts import network_model
            document = network_model.load(source / 'origination/evidence')
            network_model.replay_check(o, document)
        elif o['method'] == 'model':
            from scripts.originate import valve_rows, model_estimate, hltv_lineup_proof
            rows, meta = valve_rows(source, None, evidence_file=o.get('evidence_file'))
            proof = hltv_lineup_proof(source / 'origination/evidence', raw, registry, timestamp(data['generated_at']))
            expected, reason = model_estimate(raw, rows, registry, meta, timestamp(data['generated_at']), lineup=proof)
            assert (expected or {}).get('lineup_disambiguation') == o.get('lineup_disambiguation'), 'Lineup identity proof differs from original HLTV markup'
            assert expected and expected['probabilities'] == o['probabilities'], 'Model calculation differs from original Valve ratings'
            if 'evaluation_at' in o:
                assert expected['observed_at'] == o['observed_at'], 'Valve source observation restamped'
                assert expected['inputs'] == o['inputs'], 'Valve input records changed'
                assert expected['evidence_file'] == o['evidence_file'], 'Valve original source changed'
        values = []
        for q in o.get('quotes', []):
            if q.get('family') == 'guidance':
                # Guidance rows replay exactly like the ladder builds them:
                # unique per-provider match, market book fails every ceiling,
                # narrowest remaining wide book wins, midpoint recomputed.
                from scripts import originate
                from scripts.originate import (kalshi_rows, market_estimate, polymarket_rows,
                                               wide_book_quote)
                now_ts = timestamp(data['generated_at'])
                grouped = {}
                for row in polymarket_rows(source, source / 'origination/evidence') + kalshi_rows(source / 'origination/evidence'):
                    if originate.pair_join(row['names'], row['start'], raw, registry)[2] == 'matched':
                        grouped.setdefault((row.get('family'), row.get('provider') or 'Polymarket'), []).append(row)
                candidates = []
                for rows_ in grouped.values():
                    if len(rows_) != 1:
                        continue
                    row = rows_[0]
                    ok, _ = market_estimate(row, raw, registry, now_ts)
                    if ok:
                        continue
                    wide, spread = wide_book_quote(row, raw, registry, now_ts)
                    if wide:
                        candidates.append((spread, wide))
                assert candidates, 'No wide-book observation replays for this guidance row'
                candidates.sort(key=lambda item: item[0])
                expected = candidates[0][1]
                assert expected['probabilities'] == q['probabilities'], 'Guidance midpoint changed'
                assert expected['bid'] == q['bid'] and expected['ask'] == q['ask'], 'Guidance book changed'
                assert expected['provider'] == q['provider'] and expected['event_id'] == q['event_id'], \
                    'Guidance identity changed'
                values.append(q['probabilities'][0])
                continue
            if q.get('family') == 'reference':
                from scripts import reference_odds
                capture = reference_odds.load(source)
                pooled = list(capture.get('entries') or []) + list(capture.get('rejected') or [])
                entry = next((item for item in pooled if str(item.get('fixture_id')) == str(m['id'])), None)
                assert entry is not None, 'Reference capture for this fixture is missing'
                reference_odds.replay(entry, q)
                values.append(q['probabilities'][0])
                continue
            if q.get('provider') in {'Thunderpick', 'Kalshi', 'Bovada', 'Pinnacle'}:
                from scripts.pipeline_audit import replay_provider_quote
                values.append(replay_provider_quote(q, raw, registry, source, timestamp(data['generated_at'])))
            elif q.get('family') == 'bookmaker':
                raise AssertionError('Unsupported bookmaker replay provider; no generic odds-only fallback is permitted')
            elif q.get('family') == 'market':
                observations = json.loads((source / 'origination/evidence/live-polymarket-observations.json').read_text())
                ev = next((e for e in observations['polymarket_events'] if e['event_id'] == q['event_id']), None)
                assert ev is not None, f"Polymarket event {q['event_id']} missing from saved live observations"
                if observations.get('schema_version', 1) >= 2:
                    # New observations retain full original event + book responses.
                    # A summarized bid/ask is not enough: replay statuses, alias
                    # identity, unique series market, token/condition, timestamps
                    # and positive-size executable levels from those originals.
                    from scripts.originate import aliased_series_market, MAX_ACCEPTED_SPREAD
                    from scripts.domain import array, book_midpoint
                    folder = source / 'origination/evidence'
                    event = json.loads((folder / f"live-polymarket-event-{q['event_id']}.json").read_text())
                    market, reason = aliased_series_market(event, raw, registry, timestamp(data['generated_at']))
                    assert market is not None, 'Original Polymarket series market rejected: ' + reason
                    assert str(event.get('id')) == q['event_id']
                    assert array(market.get('outcomes')) == ev['outcomes'], 'Original market outcomes changed'
                    assert (market.get('gameStartTime') or event.get('startTime')) == ev['game_start_time'], 'Original market start changed'
                    tokens = array(market.get('clobTokenIds'))
                    assert [str(t) for t in tokens] == ev['clob_token_ids'], 'Original market token IDs changed'
                    levels = [book_midpoint(json.loads((folder / f"live-polymarket-book-{q['event_id']}-{i}.json").read_text()),
                                            str(t), market['conditionId'], timestamp(data['generated_at']),
                                            max_spread=MAX_ACCEPTED_SPREAD)
                              for i, t in enumerate(tokens)]
                    assert [l['bid'] for l in levels] == ev['book_bid'], 'Summarized bids differ from original executable books'
                    assert [l['ask'] for l in levels] == ev['book_ask'], 'Summarized asks differ from original executable books'
                    manifest = json.loads((folder / 'live-collection-manifest.json').read_text())
                    attempts = [r for r in manifest if r.get('id') == 'live-polymarket-event-' + q['event_id'] and r.get('status') == 'ok']
                    assert len(attempts) == 1 and attempts[0]['observed_at'] == ev['observed_at'], 'Market observation restamped'
                bid = align_by_name(ev['book_bid'], ev['outcomes'], raw, registry)
                ask = align_by_name(ev['book_ask'], ev['outcomes'], raw, registry)
                assert bid == q['bid'] and ask == q['ask'], 'Market quotes differ from saved observations'
                expected = normalize_pair(*[(b+a)/2 for b,a in zip(bid,ask)])
                assert expected == q['probabilities'], 'Market calculation changed'
                values.append(q['probabilities'][0])
        if values:
            p0 = median(values)
            assert normalize_pair(p0, 1-p0) == o['probabilities'], 'Fallback combined line changed'
        from scripts.originate import selection
        assert m['pick_index'] == selection(o['probabilities']), 'Fallback pick differs from its probabilities'
        assert o['fair_decimal'] == [round(1 / p, 3) for p in o['probabilities']], 'Fallback fair lines changed'
        assert abs(sum(o['probabilities']) - 1) < 1e-7, 'Probabilities must sum to one'
        assert all(0 < p < 1 for p in o['probabilities']), 'Invalid probabilities'


def _evidence(source: Path, evidence_file: str) -> Path:
    return source.parent / evidence_file if source.name == 'data' else source / evidence_file.removeprefix('data/')


def _replay_extra_quote(q, raw, registry, source, now=None):
    """Compatibility entry point; all original states/identities now replay."""
    from scripts.pipeline_audit import replay_provider_quote
    clock = now or timestamp(q.get('observed_at'))
    assert clock is not None, 'Missing original source observation time'
    return replay_provider_quote(q, raw, registry, source, clock)


def build(source: Path, output: Path):
    data = json.loads((source / 'origination.json').read_text())
    validate_origination(data, source)
    if not isinstance(data.get('matches'), list):
        raise ValueError('data/origination.json is missing its match rows')
    target = output / 'origination'
    target.mkdir(parents=True, exist_ok=True)
    canonical = json.loads((source / 'latest.json').read_text())
    (target / 'index.html').write_text(page(data, inventory_complete=canonical['coverage_complete']))
    return target / 'index.html'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('site'))
    args = parser.parse_args()
    path = build(args.source, args.output)
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
