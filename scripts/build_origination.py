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


def method_label(o):
    if o.get('family') == 'network':
        return 'Own network estimate (bo3.gg finished-series graph)'
    return o['label']


def match_source_links(m, o):
    """Deduplicated official source links for one fixture row or card."""
    links, seen = [], set()

    def add(url, text):
        if url and url not in seen:
            seen.add(url)
            links.append(ext(url, text))

    add(m['source_url'], 'Hotspawn')
    if o:
        quotes = [q for q in o.get('quotes', []) if isinstance(q, dict) and q.get('source_url')]
        for q in quotes:
            add(q['source_url'], q.get('provider', 'source'))
            if q.get('book_url'):
                add(q['book_url'], 'Bookmaker page')
        if not quotes:
            add(o.get('source_url'), o.get('source', 'Analysis source'))
        for inp in o.get('inputs') or []:
            if isinstance(inp, dict) and inp.get('source_url'):
                label = f"{inp.get('name', 'Roster')} rating" if len(o.get('inputs') or []) > 1 else o.get('source', 'Rating source')
                add(inp['source_url'], label)
        if o.get('model_crosscheck'):
            add(o['model_crosscheck'].get('source_url'), 'Valve model cross-check')
    return links


def basis_meta(o):
    money = o['method'] in {'market', 'bookmaker', 'consensus', 'reference'}
    kind = 'green' if money else 'purple'
    label = 'Money-backed line' if money else 'Research model'
    group = 'money' if money else 'model'
    if o.get('family') == 'relay':
        label = 'Relayed money line · bo3.gg bookmaker feed'
    if o['method'] == 'reference':
        label = 'Aggregated money line · third-party bookmaker average'
    if o['method'] == 'guidance':
        label = 'Wide-book guidance · indicative only'
        kind = 'amber'
        group = 'unresolved'
    if any(isinstance(q, dict) and q.get('thin') for q in o.get('quotes', [])):
        label += ' · thin market'
        kind = 'amber'
    return label, kind, group


def picks_overview_table(picks, states):
    if not picks:
        return ''
    counts = {'all': len(picks), 'money': 0, 'model': 0, 'unresolved': 0}
    rows_html = []
    for m in picks:
        sourced = m.get('origination')
        o = sourced if sourced and valid_pair(sourced.get('probabilities')) else None
        names = team_names(m)
        pick = m.get('pick_index')
        safety = states[m['id']]
        current = safety['current']
        if o and pick is not None:
            b_label, b_kind, group = basis_meta(o)
            counts[group] += 1
            p0, p1 = o['probabilities']
            probs_cell = (
                f'<span class="tbl-prob{" is-fav" if pick == 0 else ""}">{e(names[0])}: <strong>{p0 * 100:.1f}%</strong></span>'
                f'<span class="tbl-prob{" is-fav" if pick == 1 else ""}">{e(names[1])}: <strong>{p1 * 100:.1f}%</strong></span>'
            )
            prefix = '✓ ' if current else 'Snapshot: '
            pick_cell = (
                f'<strong class="tbl-pick">{e(prefix + names[pick])}</strong>'
                f'<small>{o["probabilities"][pick] * 100:.1f}% · fair {e(o["fair_decimal"][pick])}</small>'
            )
            basis_cell = f'{badge(b_label, b_kind)}<small>{e(method_label(o))}</small>'
        elif o and pick is None:
            counts['unresolved'] += 1
            p0, p1 = o['probabilities']
            probs_cell = (
                f'<span class="tbl-prob">{e(names[0])}: <strong>{p0 * 100:.1f}%</strong></span>'
                f'<span class="tbl-prob">{e(names[1])}: <strong>{p1 * 100:.1f}%</strong></span>'
            )
            pick_cell = '<span class="unverified">— unverified <small>(even estimate · no side)</small></span>'
            basis_cell = f'{badge("Even estimate · no side", "amber")}<small>{e(method_label(o))}</small>'
        else:
            counts['unresolved'] += 1
            probs_cell = '<span class="unverified">— unverified</span>'
            pick_cell = '<span class="unverified">Unresolved <small>(no verified inputs)</small></span>'
            basis_cell = badge('No verified pick', 'amber')
        links = ' · '.join(match_source_links(m, o))
        rows_html.append(
            f'<tr id="row-{e(m["id"])}" data-filter-group="{e(group if (o and pick is not None) else "unresolved")}">'
            f'<th scope="row"><a class="src" href="#match-{e(m["id"])}">{e(names[0])} vs {e(names[1])}</a>'
            f'<small>{e(m.get("competition") or "Unverified tournament")} · {local_time(m["starts_at"])}</small></th>'
            f'<td data-label="Win %">{probs_cell}</td>'
            f'<td data-label="Pick">{pick_cell}</td>'
            f'<td data-label="Analysis &amp; sources">{basis_cell}<div class="tbl-srcs">{links}</div></td>'
            '</tr>'
        )
    toolbar = (
        '<div class="filter-bar" role="toolbar" aria-label="Filter picks table">'
        f'<button type="button" class="filter-btn is-active" data-filter="all" aria-pressed="true">All ({counts["all"]})</button>'
        f'<button type="button" class="filter-btn" data-filter="money" aria-pressed="false">Money-backed ({counts["money"]})</button>'
        f'<button type="button" class="filter-btn" data-filter="model" aria-pressed="false">Research models ({counts["model"]})</button>'
        f'<button type="button" class="filter-btn" data-filter="unresolved" aria-pressed="false">Unresolved / even ({counts["unresolved"]})</button>'
        '</div>'
    )
    return (
        f'{toolbar}<div class="table-wrap picks-table-wrap">'
        '<table class="simple picks-table" aria-label="All active Hotspawn CS2 picks overview">'
        '<thead><tr><th scope="col">Match &amp; schedule</th><th scope="col">Win probabilities</th>'
        '<th scope="col">Clear pick</th><th scope="col">Analysis &amp; official sources</th></tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table></div>'
    )


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
        label, kind, _ = basis_meta(o)
        out.append(f'<p class="basis">{badge(label, kind)} <span class="method">{e(method_label(o))}</span></p>')
        links = match_source_links(m, o)
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
        if m.get('featured_method') == 'model':
            out.append(f'<p class="alias-note">Upgraded from the featured Valve-model estimate ({fp[0] * 100:.1f}% / {fp[1] * 100:.1f}%): the alias-aware research found a verified money-backed line, which replaces the uncalibrated model.</p>')
        else:
            out.append(f'<p class="alias-note">Upgraded from the featured {e(m.get("featured_method") or "equal")} tie ({fp[0] * 100:.1f}% / {fp[1] * 100:.1f}%): the alias-aware research found a directional money-backed line.</p>')
    details = '<details><summary>Research trail &amp; limitations</summary>'
    if o and o.get('inputs'):
        details += '<ul class="limits">'
        for inp in o['inputs']:
            if not isinstance(inp, dict):
                continue
            pts_note = f"{inp.get('points')} pts"
            if inp.get('rounded_points') is not None and inp.get('rounded_points') != inp.get('points'):
                pts_note += f" (summary rounded: {inp['rounded_points']})"
            standing = f"#{inp['standing']} " if inp.get('standing') is not None else ''
            src_html = ' ' + ext(inp['source_url'], 'official record') if inp.get('source_url') else ''
            details += f'<li><strong>{e(standing + str(inp.get("name", "Roster")))}</strong>: {e(pts_note)}{src_html}</li>'
        details += '</ul>'
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
    sourced = m.get('origination')
    is_even = sourced is not None and m.get('pick_index') is None
    # Keep id="unresolved-<id>" strictly on blank (origination is None) cards so
    # deployment_audit.py's blank-unresolved ID check preserves exact 1-to-1 parity.
    card_id = f'even-{e(m["id"])}' if is_even else f'unresolved-{e(m["id"])}'
    header_badge = badge('Even estimate · no side', 'amber') if is_even else badge('No verified pick', 'amber')
    if is_even and valid_pair(sourced.get('probabilities')):
        p0, p1 = sourced['probabilities']
        pick_html = (f'<p class="pick-line">Pick: <strong class="unverified">No directional edge</strong> '
                     f'<small>({p0 * 100:.1f}% / {p1 * 100:.1f}% — unverified tie, no side chosen)</small></p>')
    else:
        pick_html = ('<p class="pick-line">Pick: <strong class="unverified">Unresolved</strong> '
                     '<small>both win % left blank — no default 50/50</small></p>')
    out = [f'<article class="unresolved-card" id="{card_id}">',
           f'<header class="card-head"><span class="comp">{e(m.get("competition") or "Unverified tournament")}</span>'
           f'<span class="tier">{header_badge}</span></header>',
           f'<h3 class="teams"><strong>{e(names[0])}</strong><span class="vs">vs</span><strong>{e(names[1])}</strong></h3>',
           f'<p class="when">{local_time(m["starts_at"])}</p>',
           pick_html,
           '<ul class="findings">']
    for r in m.get('research', []):
        if r.get('stage') == 'Origination result':
            continue
        out.append(f'<li><strong>{e(short_stage(r["stage"]))}</strong> <span class="status">{e(r["status"])}</span> — '
                   f'{e(r["detail"])} {ext(r["source_url"], "source")}</li>')
    out.append('</ul>')
    extra_srcs = ' · '.join(match_source_links(m, sourced if is_even else None))
    out.append(f'<p class="row-srcs">{extra_srcs} · <a class="src" href="#match-{e(m["id"])}">Full research trail ↓</a></p></article>')
    return ''.join(out)


def section_unresolved(data):
    blank_rows = [m for m in data['matches'] if m['origination'] is None]
    even_rows = [m for m in data['matches'] if m['origination'] is not None and m['pick_index'] is None]
    rows = blank_rows + even_rows
    out = ['<section class="block" id="unresolved"><h2>Unresolved picks &amp; limitations</h2>']
    out.append('<p class="lede">Every match without a verified directional pick is listed here with what each source actually showed — '
               'HLTV identity first, then every betting market and esportsbook, then the rating model. '
               'Thin or wide books are recorded for guidance but never turned into a pick. '
               'Missing values stay blank — no default 50/50, no invented lines. '
               'An unavailable source is never treated as proof that a market does not exist.</p>')
    if not rows:
        out.append(f'<div class="ok-note"><strong>No unresolved fixtures in this snapshot.</strong> '
                   f'All {data["counts"]["active"]} active Hotspawn CS2 fixtures have a researched directional pick as of {local_time(data["generated_at"])}. '
                   'This is a dated observation, not a permanent guarantee — the inventory refreshes every four hours and new fixtures can appear without lines.</div>')
    elif not blank_rows:
        out.append(f'<p class="tiny">0 blank fixtures and {len(even_rows)} equal-probability estimate(s) without a directional side '
                   f'({data["counts"]["with_pick"]} of {data["counts"]["active"]} active fixtures carry a directional pick) as of {local_time(data["generated_at"])}.</p>')
        out.append('<div class="cards">' + ''.join(unresolved_card(m) for m in rows) + '</div>')
    else:
        out.append(f'<p class="tiny">{len(blank_rows)} unresolved fixture(s)'
                   + (f' and {len(even_rows)} equal-probability estimate(s) without a side' if even_rows else '')
                   + f' across {data["counts"]["active"]} active fixtures in this snapshot. '
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
    overview = picks_overview_table(picks, states)
    cards = ''.join(pick_row(m, states[m['id']]) for m in picks) if picks else '<div class="ok-note">No active fixtures in this snapshot. Check the <a class="src" href="../coverage/">source status</a>.</div>'
    filter_script = '''<script>
document.addEventListener('click', function (ev) {
  var btn = ev.target.closest('.filter-btn');
  if (!btn) return;
  var group = btn.getAttribute('data-filter');
  document.querySelectorAll('.filter-btn').forEach(function (b) {
    var active = b === btn;
    b.classList.toggle('is-active', active);
    b.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  document.querySelectorAll('.picks-table tbody tr').forEach(function (tr) {
    tr.hidden = group !== 'all' && tr.getAttribute('data-filter-group') !== group;
  });
});
</script>'''
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
<p class="lede">Every active Hotspawn CS2 fixture, sorted by start time, in a scannable overview table followed by full evidence cards. The check-marked team is a current pick only while its line, inventory and confirmed lock remain usable. A “Snapshot lean” is historical or unverified for current use, not a submission recommendation. Both teams’ sourced estimates and original observation times stay visible.</p>
{overview}
<div class="cards">{cards}</div></section>
{section_unresolved(data)}
{section_method(data)}
{section_aliases(data)}
{section_sources(data)}
</main>
<footer><p><strong>Better context. Clearer picks.</strong></p>
<p>Independent research dashboard · not affiliated with Hotspawn, HLTV, Valve, Polymarket or any betting provider. Informational use only. 18+ where applicable. No bets are placed.</p>
<p class="tiny"><a class="src" href="../methodology/">Main methodology</a> · <a class="src" href="../review/">Flagged for Review</a> · <a class="src" href="{REPO}">Source repository</a></p></footer>
{filter_script}
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
            upgraded = bool(o) and o.get('method') in {'market', 'bookmaker', 'consensus', 'reference'} and (
                raw['analysis'].get('method') == 'model'
                or (raw.get('pick_index') is None and m.get('pick_index') is not None)
            )
            if not upgraded:
                assert o and o['probabilities'] == raw['analysis']['probabilities'], 'Featured probabilities changed'
                assert m['pick_index'] == raw['pick_index'], 'Featured pick changed'
                continue
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
            elif q.get('family') == 'relay':
                from scripts.originate import bo3_relay_rows, relay_join, relayed_bookmaker_estimate
                rows = [
                    row for row in bo3_relay_rows(source / 'origination/evidence')
                    if str(row.get('fixture_id')) == str(m['id'])
                    and relay_join(row['names'], row['start'], raw, registry)[2] == 'matched'
                ]
                assert len(rows) == 1, 'Unique saved bo3.gg relay record missing for this fixture'
                expected, reason = relayed_bookmaker_estimate(rows[0], raw, registry, now=timestamp(data['generated_at']))
                assert expected is not None, 'Relayed bookmaker quote rejected on replay: ' + str(reason)
                assert expected['probabilities'] == q['probabilities'], 'Relayed probabilities differ from saved capture'
                assert expected['odds'] == q['odds'] and expected['event_id'] == q['event_id'], 'Relayed odds or event_id changed'
                assert expected['observed_at'] == q['observed_at'], 'Relayed observation restamped'
                values.append(q['probabilities'][0])
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
        expected_pick = selection(o['probabilities'])
        # Session 4c972a51 (already on main) may label a 50/50 research estimate
        # with a published-rank direction without changing either probability.
        # selection() still returns None in that case; the labelled winner is
        # the pick. Accept that documented side so the live replay does not
        # reject a fixture the origination ladder already resolved.
        if expected_pick is None and isinstance(o.get('tie_break'), dict):
            winner = o['tie_break'].get('winner')
            if winner in (0, 1):
                expected_pick = winner
        assert m['pick_index'] == expected_pick, 'Fallback pick differs from its probabilities'
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
