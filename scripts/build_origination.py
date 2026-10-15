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


def pick_row(m):
    o = m['origination']
    names = team_names(m)
    pick = m['pick_index']
    out = [f'<article class="pick-card" id="match-{e(m["id"])}">']
    out.append(f'<header class="card-head"><span class="comp">{e(m["competition"] or "Unverified tournament")}</span>'
               f'<span class="tier">{e((m.get("tier") or "").upper() and "Tier " + str(m.get("tier")).upper() or "Tier unverified")}</span></header>')
    out.append(f'<h3 class="teams"><strong>{e(names[0])}</strong><span class="vs">vs</span><strong>{e(names[1])}</strong></h3>')
    out.append(f'<p class="when">{local_time(m["starts_at"])}</p>')
    if o:
        p0, p1 = o['probabilities']
        favored = pick
        out.append('<ul class="probs">')
        for i, (name, p) in enumerate(zip(names, o['probabilities'])):
            cls = ' class="fav"' if i == favored else ''
            marker = ' ✓ pick' if i == favored else ''
            out.append(f'<li{cls}><span>{e(name)}{marker}</span><strong>{p * 100:.1f}%</strong></li>')
        out.append('</ul>')
        w = max(0.0, min(100.0, p0 * 100))
        out.append(f'<div class="bar" role="presentation"><span class="a" style="width:{w:.3f}%"></span><span class="b" style="width:{100 - w:.3f}%"></span></div>')
        if pick is not None:
            out.append(f'<p class="pick-line">Pick: <strong>{e(names[pick])}</strong> <small>({o["probabilities"][pick] * 100:.1f}% · fair line {e(o["fair_decimal"][pick])})</small></p>')
        else:
            out.append('<p class="pick-line">Pick: <strong>No directional edge</strong> <small>(equal estimate)</small></p>')
        money = 'market' in {q.get('family') for q in o.get('quotes', []) if isinstance(q, dict)} or 'bookmaker' in {q.get('family') for q in o.get('quotes', []) if isinstance(q, dict)}
        kind = 'green' if money else 'purple'
        label = 'Money-backed line' if money else 'Research model'
        if any(isinstance(q, dict) and q.get('thin') for q in o.get('quotes', [])):
            label += ' · thin market'
            kind = 'amber'
        out.append(f'<p class="basis">{badge(label, kind)} <span class="method">{e(o["label"])}</span></p>')
        links = [ext(m['source_url'], 'Hotspawn')]
        for q in o.get('quotes', []):
            if isinstance(q, dict) and q.get('source_url'):
                provider = q.get('provider', 'source')
                links.append(ext(q['source_url'], provider))
        if o.get('model_crosscheck'):
            mc = o['model_crosscheck']
            links.append(ext(mc['source_url'], 'Valve model cross-check'))
        out.append('<p class="row-srcs">' + ' · '.join(links) + '</p>')
    else:
        out.append('<ul class="probs"><li><span>' + e(names[0]) + '</span><strong class="unverified">—</strong></li>'
                   f'<li><span>{e(names[1])}</span><strong class="unverified">—</strong></li></ul>')
        out.append('<p class="pick-line">Pick: <strong class="unverified">Unresolved</strong> <small>no verified inputs — see limitations</small></p>')
        out.append('<p class="row-srcs">' + ext(m['source_url'], 'Hotspawn') + '</p>')
    if m.get('aliases_used'):
        used = ', '.join(f"{a['alias']} → {a['canonical']}" for a in m['aliases_used'])
        out.append(f'<p class="alias-note">Verified alias join: {e(used)}</p>')
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


def section_unresolved(data):
    rows = [m for m in data['matches'] if m['origination'] is None]
    out = ['<section class="block" id="unresolved"><h2>Unresolved picks &amp; limitations</h2>']
    out.append('<p class="lede">Every match without a verified pick is listed here with the exact reason. '
               'Missing values stay blank — no default 50/50, no invented lines. '
               'An unavailable source is never treated as proof that a market does not exist.</p>')
    if not rows:
        out.append(f'<div class="ok-note"><strong>No unresolved fixtures in this snapshot.</strong> '
                   f'All {data["counts"]["active"]} active Hotspawn CS2 fixtures have a researched pick as of {local_time(data["generated_at"])}. '
                   'This is a dated observation, not a permanent guarantee — the inventory refreshes every four hours and new fixtures can appear without lines.</div>')
    else:
        out.append('<div class="table-wrap"><table class="simple"><caption class="sr-only">Unresolved matches and missing evidence</caption>'
                   '<thead><tr><th>Match</th><th>Why no pick?</th><th>Research trail</th></tr></thead><tbody>')
        for m in rows:
            reason = next((r['detail'] for r in reversed(m.get('research', [])) if r['status'] == 'unresolved'), 'No verified inputs')
            out.append(f'<tr><th scope="row">{e(" vs ".join(team_names(m)))}<small>{local_time(m["starts_at"])}</small></th>'
                       f'<td>{e(reason)}</td><td>{ext(m["source_url"], "Hotspawn")}<a class="src" href="#match-{e(m["id"])}">Full trail ↓</a></td></tr>')
        out.append('</tbody></table></div>')
    out.append('<h3>Standing limitations for originated picks</h3><ul class="limits">')
    out.append('<li>Hotspawn participation percentages are <strong>never</strong> a probability input, and neither are HLTV fan votes. '
               'Only paired betting/market prices and official published ratings produce numbers.</li>')
    out.append('<li>Thin prediction markets (order-book spread wider than 12 cents) are shown as <strong>indicative</strong> inputs only and are labeled on each row.</li>')
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
        out.append(f'<article class="alias-card"><h3>{e(a["alias"])} <span aria-hidden="true">→</span> {e(a["canonical"])} {badge(a["kind"], "neutral")}</h3>')
        out.append('<ul class="limits">')
        for ev in a['evidence']:
            out.append(f'<li>{e(ev.get("detail", ""))} {ext(ev["url"], ev.get("source", "source"))}</li>')
        out.append('</ul></article>')
    out.append(f'<p class="tiny">Registry file: <code>data/origination/aliases.json</code> · last reviewed {e(registry.get("updated_at", ""))} · policy: {e(registry.get("policy", ""))}</p></section>')
    return ''.join(out)


def section_method(data):
    p = data['policy']
    out = ['<section class="block" id="method"><h2>How each pick is produced</h2>',
           '<p class="lede">The ladder below runs top to bottom. The first rung that verifies a full pair of prices decides the number; '
           'the later rungs are cross-checks or last resorts. Every rung is outside information — Hotspawn supplies the match list only.</p>',
           '<ol class="ladder">']
    for step in p['ladder']:
        out.append(f'<li>{e(step)}</li>')
    out.append('</ol>')
    out.append('<h3>Model note</h3><p>When a research model is used, win probability comes from the published Valve standings points with the '
               'formula in Valve\'s own <a class="src" href="https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/model/fit.js">model/fit.js</a> '
               f'(fixed rating deviation {e(p.get("rd_assumption", 75))}). It is labeled on every row and never overrides market or esportsbook prices.</p>')
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
    out = ['<section class="hero" id="summary"><p class="kicker">EXECUTIVE SUMMARY · FULL COVERAGE · INDEPENDENT LINES</p>',
           '<h2>Every Hotspawn CS2 match.<br>One researched pick each.</h2>']
    out.append(f'<p class="hero-stats"><strong>{c["active"]}</strong> active fixtures · <strong>{c["with_pick"]}</strong> with a pick · '
               f'<strong>{c["unresolved"]}</strong> unresolved · {c["consensus"]} consensus, {c["market"] + c["bookmaker"]} single-source, {c["model"]} model-backed.</p>')
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
               'never from Hotspawn popularity. Pick percentages are estimates, not guarantees.</p></section>')
    return ''.join(out)


def page(data):
    c = data['counts']
    stale = not is_fresh(data['source_snapshot_at'], datetime.now(timezone.utc))
    warn = ('<div class="stale" role="status"><strong>Snapshot is older than eight hours.</strong> '
            'Treat these lines as historical. <a class="src" href="../coverage/">Check source status →</a></div>') if stale else ''
    picks = [m for m in data['matches']]
    cards = ''.join(pick_row(m) for m in picks) if picks else '<div class="ok-note">No active fixtures in this snapshot. Check the <a class="src" href="../coverage/">source status</a>.</div>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Originated CS2 picks — every Hotspawn match · Spawn Scout</title>
<meta name="description" content="A researched pick and win probability for every Hotspawn CS2 fixture, from external betting lines, HLTV identity research and official Valve ratings. Mobile-friendly.">
<meta name="theme-color" content="#142534">
<link rel="icon" href="../assets/scout-mark.svg" type="image/svg+xml">
<link rel="stylesheet" href="../assets/origination.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><p class="brand"><a href="../">spawn<strong>scout</strong></a> <span>· originated picks</span></p>
<p class="snap">Snapshot {local_time(data['source_snapshot_at'])} · generated {local_time(data['generated_at'])}</p></header>
<main id="main">
{warn}
{executive_summary(data)}
<section class="block" id="picks"><h2>Updated picks — all matches</h2>
<p class="lede">Every active Hotspawn CS2 fixture, sorted by start time. The check-marked team is our pick; the percentages are our originated win probabilities from the sources linked on each row.</p>
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


def build(source: Path, output: Path):
    data = json.loads((source / 'origination.json').read_text())
    if not isinstance(data.get('matches'), list):
        raise ValueError('data/origination.json is missing its match rows')
    target = output / 'origination'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'index.html').write_text(page(data))
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
