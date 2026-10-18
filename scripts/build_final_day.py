"""Build the "Final day review" page (session arena-be84edde).

A single, phone-first page that answers one question the brief asked directly:
after Days 1-4 at the Thunderpick World Championship 2026, what should the
final-day picks be, and which — if any — underdog has a real case?

Everything on the page is read from two dated JSON files:

* ``data/edge-review.json`` — the repository's already-verified series record
  (Days 1-3) and the Day-4/Day-5 card. Nothing here re-derives a score.
* ``data/research/be84edde/twc-final-day.json`` — this session's dated research:
  the day-by-day reading, the roster-change verification, the final-day
  fixtures, the dated external line observations and the contrarian screens.

No probability is computed here. Where the priced card carries no market, the
page shows a blank and the reason, exactly like every other view.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_rows import is_official
from scripts.build import badge, blank, e, external, heading, icon, local_time, shell

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data' / 'research' / 'be84edde' / 'twc-final-day.json'
# Preferred: the runner's own reading of Pinnacle's public board, refreshed by
# the four-hour pipeline. Fallback: the dated copy this session committed.
PINNACLE_LIVE = ROOT / 'data' / 'research' / 'twc-current' / 'pinnacle.json'
PINNACLE_DATED = ROOT / 'data' / 'research' / 'be84edde' / 'pinnacle-day5.json'


def _pinnacle(source: Path | None = None):
    for path in (source / 'research/twc-current/pinnacle.json' if source else None,
                 PINNACLE_LIVE, PINNACLE_DATED):
        if path and Path(path).exists():
            try:
                return json.loads(Path(path).read_text())
            except (ValueError, OSError):
                continue
    return None


NO_PRICE = '<span class="unresolved-text">No price found \u2014 unverified</span>'


def _confirmation(url):
    """Per the site's own row-audit rule: a value that cannot be traced to an
    official/primary source is published, and visibly flagged as unverified."""
    if url and is_official(url):
        return '<span class="badge green">Official source</span>'
    return '<span class="badge amber">Unverified — not an official source</span>'


def _sources(rows):
    if not rows:
        return ''
    out = []
    for s in rows:
        label = s.get('source') or 'Source'
        out.append(external(s['url'], label) + _confirmation(s['url']))
    return '<div class="row-sources">' + ' '.join(out) + '</div>'


def _start_here(prefix, active_unresolved):
    """Phone-first jump bar: the reader asked to find the picks without hunting."""
    items = [
        (prefix + 'origination/#picks', 'All match picks', 'target',
         'Every Hotspawn CS2 fixture with both probabilities.'),
        (prefix + 'strategy/', 'Leaderboard plan', 'layers', 'One plan pick per open fixture.'),
        ('#final-day-picks', 'Final day (Day 5)', 'clock', 'The two 18 October fixtures.'),
        ('#upset-candidates', 'Upset shortlist', 'trend', 'The underdogs with a verified case.'),
        (prefix + 'origination/#unresolved', f'Unresolved ({active_unresolved})', 'flag',
         'Fixtures with no compliant price, and why.'),
    ]
    out = ('<nav class="start-here" id="start-here" aria-label="Start here">'
           '<p class="start-here-label">Start here · where the picks are</p><ul>')
    for href, title, sym, detail in items:
        out += (f'<li><a href="{e(href)}">{icon(sym)}<strong>{e(title)}</strong>'
                f'<span>{e(detail)}</span></a></li>')
    return out + '</ul></nav>'


def _results_table(review, prefix):
    rows = (review.get('group_stage_record') or {}).get('series') or []
    semis = (review.get('day_five_card') or {}).get('semifinal_results') or []
    out = ('<div class="table-scroll"><table class="simple-table">'
           '<caption class="sr-only">Every verified series at the tournament with its official source</caption>'
           '<thead><tr><th scope="col">Day</th><th scope="col">Series</th><th scope="col">Score</th>'
           '<th scope="col">Stage</th><th scope="col">Official source</th></tr></thead><tbody>')
    for s in rows:
        src = (s.get('sources') or [{}])[0]
        link = external(src.get('url', 'https://www.hltv.org/results?event=8932'), 'HLTV')
        out += (f'<tr><td>Day {e(s.get("day"))}<small>{e(s.get("date"))}</small></td>'
                f'<th scope="row">{e(s.get("team_a"))} vs {e(s.get("team_b"))}</th>'
                f'<td><strong>{e(s.get("score"))}</strong><small>{e(s.get("winner"))} won</small></td>'
                f'<td>{e(s.get("group"))} · {e(s.get("slot"))}</td><td>{link}</td></tr>')
    for s in semis:
        maps = ' · '.join(f'{m.get("map")} {m.get("a")}-{m.get("b")}' for m in (s.get('maps') or []))
        src = (s.get('sources') or [{}])[0]
        link = external(src.get('url', 'https://www.hltv.org/results?event=8932'), 'HLTV')
        out += (f'<tr><td>Day 4<small>2026-10-17</small></td>'
                f'<th scope="row">{e(s.get("team_a"))} vs {e(s.get("team_b"))}</th>'
                f'<td><strong>{e(s.get("score"))}</strong><small>{e(maps)}</small></td>'
                f'<td>{e(s.get("slot"))}</td><td>{link}</td></tr>')
    return out + '</tbody></table></div>'


def _day_read(dossier):
    out = '<div class="day-read">'
    for d in dossier.get('day_read') or []:
        out += (f'<article class="day-card"><p class="eyebrow">Day {e(d["day"])} · {e(d["date"])}</p>'
                f'<h3>{e(d["headline"])}</h3><p>{e(d["reading"])}</p>'
                + _sources(d.get('sources')) + '</article>')
    return out + '</div>'


def _roster(dossier):
    rv = dossier.get('roster_verification') or {}
    out = (f'<p class="section-intro"><strong>Finding.</strong> {e(rv.get("finding", ""))}</p>')
    out += ('<div class="table-scroll"><table class="simple-table">'
            '<caption class="sr-only">Most recent verified roster changes for the two final-day underdogs</caption>'
            '<thead><tr><th scope="col">Team</th><th scope="col">Date</th><th scope="col">Change</th>'
            '<th scope="col">Sources</th></tr></thead><tbody>')
    for c in rv.get('verified_changes') or []:
        out += (f'<tr><th scope="row">{e(c["team"])}</th><td>{e(c["date"])}</td>'
                f'<td>{e(c["change"])}</td><td>{_sources(c.get("sources"))}</td></tr>')
    out += '</tbody></table></div>'
    flags = rv.get('flags') or []
    if flags:
        out += '<div class="limitations-callout"><p class="eyebrow">What this does not prove</p><ul>'
        for f in flags:
            out += f'<li>{e(f)}</li>'
        out += '</ul></div>'
    return out


def _prob_cell(match, prefix):
    """Show the priced value or an explicit blank. Never invent one."""
    probs = match.get('probabilities')
    market = match.get('market')
    model = match.get('model_estimate')
    if probs and market:
        names = match.get('teams') or []
        body = ''.join(
            f'<div class="prob-side"><span>{e(names[i] if i < len(names) else "—")}</span>'
            f'<strong>{probs[i] * 100:.1f}%</strong></div>' for i in range(len(probs)))
        return ('<div class="prob-pair">' + body + '</div>'
                + badge('External market', 'market')
                + _sources(market.get('sources') if isinstance(market, dict) else None))
    if probs and model:
        names = match.get('teams') or []
        body = ''.join(
            f'<div class="prob-side"><span>{e(names[i] if i < len(names) else "—")}</span>'
            f'<strong>{probs[i] * 100:.1f}%</strong></div>' for i in range(len(probs)))
        fair = model.get('fair_decimal') or []
        return ('<div class="prob-pair">' + body + '</div>' + badge('Valve model · uncalibrated', 'model')
                + (f'<p class="tiny muted">Fair decimal {e(fair[0])} / {e(fair[1])} · rating snapshot '
                   f'{e(model.get("snapshot_date"))}. Higher-uncertainty research estimate; not betting odds.</p>'
                   if len(fair) == 2 else '')
                + external(model.get('source_url', ''), 'Valve standings'))
    if model:
        names = match.get('teams') or []
        p = model.get('probabilities') or []
        body = ''.join(
            f'<div class="prob-side"><span>{e(names[i] if i < len(names) else "—")}</span>'
            f'<strong>{p[i] * 100:.1f}%</strong></div>' for i in range(len(p)))
        return ('<div class="prob-pair">' + body + '</div>' + badge('Valve model · uncalibrated', 'model')
                + '<p class="tiny muted">No external money line was listed for this fixture, so the '
                  'labelled rating fallback is shown. It is a research estimate, not a price.</p>'
                + external(model.get('source_url', ''), 'Valve standings'))
    return ('<p class="unresolved-text"><strong>Unresolved — no compliant external price.</strong> '
            'The four-hour publisher retries Polymarket, Kalshi, Thunderpick and Bovada; the pick '
            'stays blank until one of them lists a two-sided book.</p>')


def _final_day(dossier, review, prefix):
    card = review.get('day_five_card') or {}
    card_matches = card.get('matches') or []
    by_id = {str(m.get('hltv_match_id')): m for m in card_matches}
    out = ''
    for fx in (dossier.get('final_day') or {}).get('fixtures') or []:
        mid = str(fx.get('hltv_match_id'))
        cm = by_id.get(mid, {})
        names = [fx.get('team_a'), fx.get('team_b')]
        ctx = ''.join(f'<li>{e(c)}</li>' for c in (fx.get('dated_context') or []))
        out += ('<article class="final-day-card" id="final-day-' + e(mid) + '">'
                f'<div class="final-day-head"><p class="eyebrow">{e(fx.get("slot"))}</p>'
                f'<h3>{e(names[0])} <span class="versus">vs</span> {e(names[1])}</h3>'
                f'<p class="final-day-time">{icon("clock")} {local_time(fx.get("starts_at_utc"))} '
                f'<span data-zone-label>Malta</span> · Best of {e(fx.get("best_of"))}</p></div>'
                + _prob_cell(dict(cm, teams=names), prefix)
                + (f'<ul class="dated-context">{ctx}</ul>' if ctx else '')
                + _sources(fx.get('sources'))
                + '</article>')
    if not out:
        out = ('<div class="limitations-callout"><strong>No final-day fixture is currently listed.</strong> '
               'The bracket had not been resolved when this snapshot was taken; nothing is invented.</div>')
    return out


def _dated_lines(dossier):
    out = ('<div class="table-scroll"><table class="simple-table">'
           '<caption class="sr-only">Dated external price observations for the final day</caption>'
           '<thead><tr><th scope="col">Fixture</th><th scope="col">Observation</th>'
           '<th scope="col">Source</th><th scope="col">Observed</th></tr></thead><tbody>')
    for row in dossier.get('dated_line_observations') or []:
        quote = row.get('quote') or NO_PRICE
        links = _sources(row.get('sources'))
        if row.get('url'):
            links += ' ' + external(row['url'], e(row['provider'])[:40])
        out += (f'<tr><th scope="row">{e(row["fixture"])}'
                f'<small>{e(row["label"])}</small></th>'
                f'<td>{quote}</td>'
                f'<td>{links}</td><td>{e(row.get("observed_at"))}</td></tr>')
    return out + '</tbody></table></div>'


def _contrarian(dossier):
    out = '<ol class="contrarian-list">'
    for i, rule in enumerate(dossier.get('contrarian_rules') or [], start=1):
        out += f'<li><span class="note-number">{i:02d}</span><p>{e(rule)}</p></li>'
    return out + '</ol>'


def _candidates(dossier):
    out = ''
    for c in dossier.get('upset_candidates') or []:
        verdict = c.get('verdict') or ''
        cls = 'amber' if 'No verified upset case' in verdict else 'neutral'
        out += (f'<article class="candidate-card"><div class="candidate-head"><h3>{e(c.get("team"))}</h3>'
                f'<p class="eyebrow">{e(c.get("fixture"))}</p></div>'
                f'<div class="candidate-body"><div><p class="eyebrow">Case for</p><p>{e(c.get("case_for"))}</p></div>'
                f'<div><p class="eyebrow">Case against</p><p>{e(c.get("case_against"))}</p></div></div>'
                f'<p class="candidate-verdict {e(cls)}"><strong>Verdict.</strong> {e(verdict)}</p>'
                + _sources(c.get('sources')) + '</article>')
    rest = dossier.get('rest_and_onboarding') or {}
    if rest:
        out += ('<div class="limitations-callout"><p class="eyebrow">Rest and onboarding — unquantified</p><ul>'
                + ''.join(f'<li>{e(o)}</li>' for o in (rest.get('observations') or []))
                + f'</ul><p class="tiny">{e(rest.get("limitation", ""))}</p></div>')
    return out


def _unresolved(dossier, probe, prefix):
    unresolved = dossier.get('unresolved') or {}
    live = probe or {}
    rows = live.get('unresolved_detail') or []
    counts = live.get('origination_counts') or {}
    out = (f'<p class="section-intro">Every match listed on Hotspawn is carried. A fixture is only '
           f'left without a pick when no compliant two-sided external price could be verified for it. '
           f'At the dated live observation below the complete researched list held '
           f'<strong>{e(counts.get("active"))}</strong> active fixtures, '
           f'<strong>{e(counts.get("resolved"))}</strong> resolved and '
           f'<strong>{e(counts.get("unresolved"))}</strong> unresolved.</p>')
    if rows:
        out += ('<div class="table-scroll"><table class="simple-table">'
                '<caption class="sr-only">Fixtures with no compliant price, with the reason recorded by the collector</caption>'
                '<thead><tr><th scope="col">Fixture</th><th scope="col">Competition</th>'
                '<th scope="col">Start (UTC)</th><th scope="col">Why it stayed blank</th>'
                '<th scope="col">Hotspawn source</th></tr></thead><tbody>')
        for r in rows:
            reasons = [t for t in r.get('research_trail') or [] if t.get('status') == 'unresolved']
            detail = reasons[-1]['detail'] if reasons else 'No compliant price was verified.'
            hltv = next((t['source_url'] for t in r.get('research_trail') or []
                         if 'hltv.org' in (t.get('source_url') or '')), None)
            links = external(r.get('hotspawn_source_url') or 'https://play.hotspawn.com/lobby', 'Hotspawn')
            if hltv:
                links += ' ' + external(hltv, 'HLTV')
            teams = ' vs '.join(r.get('teams') or [])
            out += (f'<tr><th scope="row">{e(teams)}</th><td>{e(r.get("competition"))}</td>'
                    f'<td>{e(r.get("starts_at"))}</td>'
                    f'<td class="unresolved-text">{e(detail[:260])}</td><td>{links}</td></tr>')
        out += '</tbody></table></div>'
    reasons = unresolved.get('reason_classes') or []
    if reasons:
        out += ('<div class="limitations-callout"><p class="eyebrow">Why a fixture can still be blank</p><ul>'
                + ''.join(f'<li>{e(x)}</li>' for x in reasons) + '</ul>')
        if live.get('generated_at'):
            out += (f'<p class="tiny">Live observation {e(live.get("generated_at"))} · '
                    f'inventory {e(live.get("inventory_observed_at"))} · '
                    f'<a href="{e(prefix)}data/research/be84edde/live-probe.json">Full probe JSON ↓</a></p>')
        out += f'<p class="tiny">{e(unresolved.get("limitation", ""))}</p></div>'
    return out


def _pinnacle_rows(book, prefix):
    """Pinnacle is a first-party bookmaker, so its line is shown as a real price
    with its own observation time — never merged with the model estimate."""
    if not book:
        return ('<div class="limitations-callout"><p><strong>No first-party bookmaker line '
                'is retained for the final day.</strong> Pinnacle\u2019s public board is read by '
                'the four-hour pipeline; when it lists a two-way series moneyline it appears '
                'here with its observation time. Nothing is filled in from another source.</p></div>')
    out = ('<div class="table-scroll"><table class="simple-table">'
           '<caption class="sr-only">First-party Pinnacle series moneylines for the final day</caption>'
           '<thead><tr><th scope="col">Fixture</th><th scope="col">Prices (American)</th>'
           '<th scope="col">Decimal</th><th scope="col">No-vig probability</th>'
           '<th scope="col">Observed</th><th scope="col">Source</th></tr></thead><tbody>')
    for fx in book.get('fixtures') or []:
        teams = f"{fx.get('team_a')} vs {fx.get('team_b')}"
        slot = f"{fx.get('slot')} · best of {fx.get('best_of')}"
        links = external(fx.get('hltv_url') or 'https://www.hltv.org/events/8932/matches', 'HLTV')
        quote = fx.get('quote')
        if quote:
            names = quote.get('participants') or [fx.get('team_a'), fx.get('team_b')]
            amer = quote.get('american') or []
            dec = quote.get('decimal') or []
            prob = quote.get('probabilities') or []
            prices = ' · '.join(f'{e(names[i] if i < len(names) else "?")} {e(amer[i])}'
                                for i in range(len(amer)))
            decs = ' · '.join(e(d) for d in dec)
            probs = ' · '.join(f'{(p * 100):.1f}%' for p in prob)
            links += ' ' + external(quote.get('source_url') or 'https://www.pinnacle.com', 'Pinnacle')
            out += (f'<tr><th scope="row">{e(teams)}<small>{e(slot)}</small></th>'
                    f'<td>{prices}</td><td>{decs}</td><td><strong>{probs}</strong></td>'
                    f'<td>{e(quote.get("observed_at"))}</td><td>{links}</td></tr>')
        else:
            reason = fx.get('reason') or 'No two-way series line was open.'
            links += ' ' + external('https://www.pinnacle.com/en/esports/counter-strike-2', 'Pinnacle')
            out += (f'<tr><th scope="row">{e(teams)}<small>{e(slot)}</small></th>'
                    f'<td colspan="3" class="unresolved-text">Unresolved — {e(reason)}</td>'
                    f'<td>{e(book.get("observed_at"))}</td><td>{links}</td></tr>')
    out += '</tbody></table></div>'
    if book.get('observed_at'):
        out += (f'<p class="tiny muted" style="padding:0 20px 18px">Pinnacle board observed '
                f'{e(book.get("observed_at"))}. '
                f'{e((book.get("policy") or ""))}</p>')
    return out


def render(data, prefix, edge_source=None, source=None):
    dossier = json.loads(DOSSIER.read_text())
    review = json.loads(Path(edge_source or ROOT / 'data/edge-review.json').read_text())
    probe_path = ROOT / 'data' / 'research' / 'be84edde' / 'live-probe.json'
    probe = json.loads(probe_path.read_text()) if probe_path.exists() else None
    live_counts = (probe or {}).get('origination_counts') or {}
    unresolved_n = live_counts.get('unresolved') or (dossier.get('unresolved') or {}).get('unresolved') or 0

    body = heading(
        'Thunderpick World Championship 2026',
        'Final day: Days 1–4 reviewed, Day 5 picked',
        'The two 18 October fixtures, the verified results behind them, and the one underdog with a case. '
        'Dated research — it never overwrites an automated price.',
        badge('Dated research · read-only', 'neutral'))
    body += _start_here(prefix, unresolved_n)
    body += ('<section class="content-section" id="policy"><div class="section-heading"><div>'
             '<p class="eyebrow">Before you read</p><h2>The rules this page obeys</h2></div></div><ol class="contrarian-list">'
             + ''.join(f'<li><span class="note-number">{i:02d}</span><p>{e(p)}</p></li>'
                       for i, p in enumerate(dossier.get('policy') or [], start=1))
             + '</ol></section>')
    body += ('<section class="content-section" id="day-one-to-four"><div class="section-heading"><div>'
             '<p class="eyebrow">Verified, not recalled</p><h2>Every series, Days 1–4</h2></div>'
             + external('https://www.hltv.org/results?event=8932', 'HLTV event results') + '</div>'
             '<p class="section-intro">Read from the repository\'s dated record, which was verified '
             'against HLTV\'s own event results list. One official link per row.</p>'
             + _results_table(review, prefix) + '</section>')
    body += ('<section class="content-section" id="day-read"><div class="section-heading"><div>'
             '<p class="eyebrow">What the results say</p><h2>Day by day</h2></div></div>'
             + _day_read(dossier) + '</section>')
    body += ('<section class="content-section" id="roster"><div class="section-heading"><div>'
             '<p class="eyebrow">Checked, not assumed</p><h2>Roster change: what is actually verified</h2></div></div>'
             + _roster(dossier) + '</section>')
    body += ('<section class="content-section" id="final-day-picks"><div class="section-heading"><div>'
             '<p class="eyebrow">Sunday 18 October</p><h2>Final-day picks</h2></div>'
             + external('https://www.hltv.org/events/8932/matches', 'HLTV event matches') + '</div>'
             + _final_day(dossier, review, prefix) + '</section>')
    book = _pinnacle(source)
    body += ('<section class="content-section" id="book-lines"><div class="section-heading"><div>'
             '<p class="eyebrow">First-party bookmaker</p><h2>Pinnacle board for the final day</h2></div>'
             + external('https://www.pinnacle.com/en/esports/counter-strike-2', 'Pinnacle CS2') + '</div>'
             '<p class="section-intro">Pinnacle is a bookmaker, so this is a real price rather than a '
             'model estimate: the number a book is actually offering, with the overround removed '
             'proportionally. It is read from Pinnacle\u2019s public guest endpoints, dated with its '
             'observation time, and only the lowest-period two-way series moneyline is accepted \u2014 '
             'per-map markets, \u201cYes/No\u201d specials and live games are rejected.</p>'
             + _pinnacle_rows(book, prefix) + '</section>')
    body += ('<section class="content-section" id="dated-lines"><div class="section-heading"><div>'
             '<p class="eyebrow amber-text">Context, not a price</p><h2>Dated external line observations</h2></div></div>'
             '<p class="section-intro">These were read outside the automated pipeline. They are dated '
             'observations of what third-party pages were quoting, and none of them is a first-party '
             'bookmaker feed or a substitute for the site\'s own priced card.</p>'
             + _dated_lines(dossier) + '</section>')
    body += ('<section class="content-section" id="contrarian-rules"><div class="section-heading"><div>'
             '<p class="eyebrow">Climbing the leaderboard</p><h2>Contrarian, not stupid</h2></div>'
             + badge('Screen, not a probability change', 'neutral') + '</div>'
             + _contrarian(dossier) + '</section>')
    body += ('<section class="content-section" id="upset-candidates"><div class="section-heading"><div>'
             '<p class="eyebrow">The shortlist</p><h2>Which underdog, if any</h2></div></div>'
             + _candidates(dossier) + '</section>')
    body += ('<section class="content-section" id="unresolved"><div class="section-heading"><div>'
             '<p class="eyebrow amber-text">Every gap stays visible</p><h2>Unresolved picks &amp; limitations</h2></div>'
             f'<a class="internal-link" href="{prefix}review/">All review flags {icon("arrow")}</a></div>'
             + _unresolved(dossier, probe, prefix)
             + '<div class="limitations-callout"><p class="eyebrow">Limits of this page</p><ul>'
             + ''.join(f'<li>{e(x)}</li>' for x in (dossier.get('limitations') or []))
             + '</ul></div></section>')
    body += ('<section class="content-section" id="sources"><div class="section-heading"><div>'
             '<p class="eyebrow">Audit</p><h2>Every source used</h2></div></div><div class="table-scroll">'
             '<table class="simple-table"><caption class="sr-only">Sources cited on this page</caption>'
             '<thead><tr><th scope="col">Source</th><th scope="col">Used for</th><th scope="col">Link</th>'
             '</tr></thead><tbody>')
    seen = set()
    for row in _collect_sources(dossier, review):
        if row['url'] in seen:
            continue
        seen.add(row['url'])
        body += (f'<tr><th scope="row">{e(row["source"])}</th><td>{e(row["detail"])}</td>'
                 f'<td>{external(row["url"], "Open")} {_confirmation(row["url"])}</td></tr>')
    body += ('</tbody></table></div>'
             f'<p class="tiny muted">Research window {e(dossier.get("research_window", {}).get("opened"))} → '
             f'{e(dossier.get("research_window", {}).get("closed"))}. '
             f'Raw dossier: <a href="{prefix}data/research/be84edde/twc-final-day.json">twc-final-day.json ↓</a></p>'
             '</section>')
    return body


def _collect_sources(dossier, review):
    """Every distinct source cited anywhere in the two input files."""
    out = []
    seen = set()

    def add(url, source, detail):
        if not url or url in seen:
            return
        seen.add(url)
        out.append({'url': url, 'source': source or 'Source', 'detail': (detail or '')[:240]})

    add('https://www.hltv.org/results?event=8932', 'HLTV.org event results',
        'All twelve series scores, Days 1-4.')
    for d in dossier.get('day_read') or []:
        for s in d.get('sources') or []:
            add(s.get('url'), s.get('source'), s.get('detail'))
    for c in (dossier.get('roster_verification') or {}).get('verified_changes') or []:
        for s in c.get('sources') or []:
            add(s.get('url'), s.get('source'), s.get('detail'))
    for fx in (dossier.get('final_day') or {}).get('fixtures') or []:
        for s in fx.get('sources') or []:
            add(s.get('url'), s.get('source'), s.get('detail'))
    for row in dossier.get('dated_line_observations') or []:
        for s in row.get('sources') or []:
            add(s.get('url'), s.get('source'), s.get('detail'))
    for c in dossier.get('upset_candidates') or []:
        for s in c.get('sources') or []:
            add(s.get('url'), s.get('source'), s.get('detail'))
    for s in (dossier.get('event') or {}).get('sources') or []:
        add(s.get('url'), s.get('source'), s.get('detail'))
    for s in ((review.get('group_stage_record') or {}).get('series') or [])[:1]:
        for x in s.get('sources') or []:
            add(x.get('url'), x.get('source'), x.get('detail'))
    return out


def build(source: Path, output: Path):
    """Rendered by the PAGES loop in scripts.build; kept here for direct use."""
    from scripts.build import build as build_site
    return build_site(source, output)


if __name__ == '__main__':
    from scripts.build import build as build_site
    raise SystemExit(build_site(Path('data'), Path('site')))
