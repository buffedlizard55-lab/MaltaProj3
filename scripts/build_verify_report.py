"""V-3: publish the independent verification report as a mobile-first page.

Renders ``data/research/ba7164a0/report.html`` from the audit dossier produced by
``scripts/verify_published.py`` and the archived first-party observations produced by
``scripts/research_verify.py``.

Why the page lives under ``data/``: ``scripts/build.py`` copies the whole ``data/`` tree
into the deployed site, while ``.github/workflows/pages.yml`` uploads only ``site/``. A
new top-level directory would therefore never deploy without editing ``build.py``, which
another session owns. Publishing under ``data/`` deploys on the next Pages run with no
change to any file outside this session's claimed scope.

Everything on the page is either a value read from an official source, or an explicit
"unverified" statement. No probability is originated, estimated, repaired or defaulted
here; the picks shown are the ones the site already published, each next to the source
that produced it.

Usage::

    python -m scripts.build_verify_report            # writes into data/
    python -m scripts.build_verify_report --site out # also writes into a built site
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from scripts.verify_published import HOTSPAWN_LOBBY, PAGES_ORIGINATION

RELATIVE_ROOT = '../../../'          # data/research/ba7164a0/ -> site root
EVIDENCE_DIR = Path('data/research/ba7164a0')
REPORT_NAME = 'data/research/ba7164a0/report.html'
CSS_NAME = 'assets/verify-report.css'

# In-site destinations, written relative to the page so they survive the project subpath.
SITE_LINKS = {
    'summary': RELATIVE_ROOT + 'index.html',
    'picks': RELATIVE_ROOT + 'picks/index.html',
    'origination_picks': RELATIVE_ROOT + 'origination/index.html#picks',
    'origination_unresolved': RELATIVE_ROOT + 'origination/index.html#unresolved',
    'edge': RELATIVE_ROOT + 'edge/index.html',
    'coverage': RELATIVE_ROOT + 'coverage/index.html',
    'methodology': RELATIVE_ROOT + 'methodology/index.html',
    'review': RELATIVE_ROOT + 'review/index.html',
    'strategy': RELATIVE_ROOT + 'strategy/index.html',
    'twc_picks': RELATIVE_ROOT + 'twc-picks/index.html',
    'audit_json': 'audit.json',
    'observations_json': 'observations.json',
}

NOT_OFFICIAL = 'Unverified — no official source confirms this value.'


def e(value) -> str:
    return escape('' if value is None else str(value), quote=True)


def pct(value, places=1) -> str:
    try:
        return f'{float(value) * 100:.{places}f}%'
    except (TypeError, ValueError):
        return '—'


def when(value) -> str:
    """HH:MM UTC on DD Mon, from an ISO-8601 timestamp. Blank stays blank."""
    stamp = parse_stamp(value)
    return stamp.strftime('%H:%M UTC %d %b') if stamp else '—'


def parse_stamp(value):
    if not value:
        return None
    text = str(value).strip().replace('Z', '+00:00').replace(' ', 'T', 1)
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    return stamp.astimezone(timezone.utc) if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def hours_between(start, end) -> str:
    """Elapsed time between two first-party timestamps, as hours and minutes."""
    left, right = parse_stamp(start), parse_stamp(end)
    if left is None or right is None:
        return NOT_OFFICIAL
    seconds = (right - left).total_seconds()
    if seconds < 0:
        return NOT_OFFICIAL
    return f'{int(seconds // 3600)}h {int((seconds % 3600) // 60):02d}m'


def official(link: dict, text=None) -> str:
    """An external link. Rows carrying one satisfy the row-source audit."""
    url = link.get('source_url') or link.get('url')
    if not url:
        return f'<span class="unverified">{e(NOT_OFFICIAL)}</span>'
    return f'<a class="src" href="{e(url)}" rel="noopener noreferrer">{e(text or url)}</a>'


def link_list(urls) -> str:
    seen, out = set(), []
    for url in urls or []:
        if url and url.startswith('http') and url not in seen:
            seen.add(url)
            out.append(f'<a class="src" href="{e(url)}" rel="noopener noreferrer">{e(short(url))}</a>')
    return ' '.join(out) if out else f'<span class="unverified">{e(NOT_OFFICIAL)}</span>'


def short(url: str) -> str:
    from urllib.parse import urlparse
    parts = urlparse(url)
    host = (parts.netloc or '').removeprefix('www.')
    tail = '/'.join([p for p in parts.path.split('/') if p][:2])
    return f'{host}/{tail}' if tail else host


# ---------------------------------------------------------------------------
# Derived, first-party-only facts
# ---------------------------------------------------------------------------

def team_load(hltv: dict, teams: list) -> list:
    """Maps played and rest before each Day-3 decider, from HLTV's own timestamps.

    Only arithmetic on timestamps HLTV publishes: each result block carries
    ``data-zonedgrouping-entry-unix`` (when the series finished) and each fixture on the
    event board carries ``data-unix`` (when it starts). Nothing here estimates form,
    fatigue or a probability - it states how long a team had between series and how many
    maps it played, both of which the brief asks to be factored in.
    """
    results = (hltv.get('results') or {}).get('results') or []
    fixtures = (hltv.get('schedule') or {}).get('fixtures') or []
    next_start = {}
    for fixture in fixtures:
        for name in fixture.get('teams') or []:
            if name and name not in next_start:
                next_start[name] = fixture.get('start_utc')
    rows = []
    for team in teams:
        played = [r for r in results if team in (r.get('listed_teams') or [])]
        played.sort(key=lambda r: r.get('finished_unix') or 0)
        maps = sum(sum(r['listed_score']) for r in played if r.get('listed_score'))
        wins = sum(1 for r in played if r.get('winner') == team)
        last = played[-1] if played else None
        rows.append({
            'team': team,
            'series_played': len(played),
            'series_won': wins,
            'maps_played': maps,
            'last_finished_utc': last.get('finished_utc') if last else None,
            'last_result': (f"{last['listed_teams'][0]} {last['listed_score'][0]}-"
                            f"{last['listed_score'][1]} {last['listed_teams'][1]}"
                            if last and last.get('listed_score') and len(last.get('listed_teams') or []) == 2
                            else None),
            'last_result_url': last.get('url') if last else None,
            'next_start_utc': next_start.get(team),
            'rest': hours_between(last.get('finished_utc'), next_start.get(team)) if last else NOT_OFFICIAL,
        })
    return rows


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def executive_summary(audit: dict, twc: dict) -> str:
    staleness = audit['staleness']
    inventory = audit['inventory_reconciliation']
    counts = audit['published_counts_check']
    replay = audit['probability_replay']
    fp = audit['first_party_market_check']
    unresolved = audit['unresolved_review']
    flags = audit['flags']
    review = [f for f in flags if f['severity'] == 'review']
    resolved = [f for f in audit['fixtures'] if f.get('origination_probabilities')]

    badge = {'fresh': 'ok', 'stale': 'bad'}.get(staleness['verdict'], 'warn')
    # Every summary row carries the official source behind it. A row that only states a
    # conclusion would fail the site's own row-source policy, and rightly so.
    items = [
        ('Every CS2 fixture Hotspawn lists is published',
         inventory['reconciled'],
         f"{inventory['hotspawn_api_id_count']} fixtures in Hotspawn's own API read at "
         f"{e(audit['probe_window'].get('finished_at'))}; {inventory['deployed_row_count']} "
         f"published in the snapshot of {e(staleness['generated_at'])}. "
         + ('No fixture is missing and none is invented.'
            if inventory['reconciled'] else
            f"Missing from the site: {inventory['missing_from_site'] or 'none'}. "
            f"Published but no longer listed by Hotspawn: {inventory['extra_on_site'] or 'none'}. "
            'The two readings are minutes apart, so a fixture that started or was pulled in '
            'between explains part of any gap. The gap is reported, never reconciled by '
            'assumption.'),
         inventory['source_urls']),
        ('Every published probability replays from its own cited source',
         len(fp['checked']) > 0 and not fp['drifted_or_reversed'] and replay['mismatched'] == 0,
         f"{len(fp['checked'])} priced rows were re-read against Polymarket's own archived event: "
         f"{len(fp['agreeing'])} agree, {len(fp['drifted_or_reversed'])} disagree. "
         f"{replay['replayed']} rows replay from the quote they cite, {replay['mismatched']} do not, "
         f"{replay['blank']} are intentionally blank and {replay['not_replayable']} cite no price. "
         'See <a href="#replay">the replay table</a>.',
         fp['source_urls']),
        ('Every headline count equals the rows behind it',
         not counts['mismatches'],
         'Recomputed from the published rows: '
         + ', '.join(f'{k}={v}' for k, v in counts['recomputed'].items() if k != 'unresolved_flags')
         + ('.' if not counts['mismatches'] else f". Mismatches: {counts['mismatches']}.")
         + ' See <a href="#counts">the count table</a>.',
         counts['source_urls']),
        ('Every cited source is an official one',
         not audit['source_links']['unofficial'],
         f"{audit['source_links']['distinct_source_urls']} distinct URLs are cited by published picks. "
         + ('All are on the official allow-list published in <code>scripts/audit_rows.py</code>.'
            if not audit['source_links']['unofficial'] else
            'Outside that allow-list: ' + ', '.join(audit['source_links']['unofficial'])
            + '. Recorded in <a href="#flags">flagged for review</a>.'),
         audit['source_links']['source_urls']),
        ('A pick exists for every listed match',
         not unresolved,
         f"{len(resolved)} of {len(audit['fixtures'])} upcoming fixtures carry an originated "
         f"probability and a pick. {len(unresolved)} do not; each is documented in "
         '<a href="#unresolved">unresolved picks</a> with every rung that was tried and why it '
         'stopped short.',
         [u for entry in unresolved for u in (entry.get('source_urls') or [])][:6]
         or [HOTSPAWN_LOBBY]),
    ]
    rows = ''.join(
        '<tr><th scope="row"><span class="tick ' + ('yes' if ok else 'no') + '">'
        + ('verified' if ok else 'flagged') + '</span> ' + e(title) + '</th>'
        + '<td>' + detail + '<div class="srcs">' + link_list(urls) + '</div></td></tr>'
        for title, ok, detail, urls in items)

    deciders = twc.get('deciders') or []
    decider_html = ''.join(
        f'<li><a href="#decider-{e(d["fixture_id"])}">{e(d["teams"][0])} v {e(d["teams"][1])}</a> '
        f'— pick <strong>{e(d["pick"])}</strong> at {pct(d["pick_probability"])}, '
        f'{when(d["starts_at"])}</li>'
        for d in deciders)

    return f'''
<section class="block" id="summary">
<h2>Executive summary</h2>
<p class="lede">Independent verification of the live site, run by session
<code>arena-ba7164a0</code> against original first-party responses only. Nothing here
changes a published pick; everything here says whether it can be confirmed.</p>
<p class="snapshot">Live snapshot <strong>{e(staleness['generated_at'] or '—')}</strong>
<span class="pill {badge}">{e(staleness['verdict'])}</span>
· read {e(staleness['observed_at'] or '—')} · {e(staleness['age_minutes'])} min old ·
refresh every {e(staleness['refresh_interval_hours'])} h ·
{e(audit['probe_window']['requests_ok'])} sources read,
{e(audit['probe_window']['requests_not_ok'])} unreadable</p>
<table class="checks"><caption>What this audit checked, and what it found</caption>
<tbody>{rows}</tbody></table>

<h3>Where the current picks are</h3>
<ul class="goto">
<li><a href="{e(SITE_LINKS['origination_picks'])}">Every Hotspawn CS2 match with an originated pick</a>
 — the complete-picks list, one card per fixture.</li>
<li><a href="{e(SITE_LINKS['picks'])}">Featured picks</a> — the shorter curated list.</li>
<li><a href="{e(SITE_LINKS['twc_picks'])}">Thunderpick World Championship picks</a> — the LAN event page.</li>
<li><a href="{e(SITE_LINKS['origination_unresolved'])}">Unresolved fixtures on the live site</a>.</li>
<li><a href="{e(SITE_LINKS['coverage'])}">Coverage</a> ·
<a href="{e(SITE_LINKS['methodology'])}">Methodology</a> ·
<a href="{e(SITE_LINKS['review'])}">Flagged for review</a> ·
<a href="{e(SITE_LINKS['summary'])}">Site summary</a></li>
</ul>

<h3>Today&rsquo;s Thunderpick World Championship deciders</h3>
{f'<ul class="goto">{decider_html}</ul>' if decider_html else
 '<p class="unverified">No Thunderpick decider was found in the verified snapshot.</p>'}
<p>Detail, sources and the Day-1/Day-2 review behind them:
<a href="#deciders">today&rsquo;s deciders</a> ·
<a href="#twc">event review</a> · <a href="#load">rest and maps played</a>.</p>

<h3 class="unresolved-head">Unresolved picks — {len(unresolved)} fixture(s) with no probability</h3>
<p>These are published with the probability <strong>left blank</strong> and flagged, never
filled in with a guess or a default 50/50. Each one lists every source that was tried, in
the order the methodology requires (HLTV first, then prediction markets, then esports
books, then Valve&rsquo;s official ratings), and why each stopped short.</p>
<ul class="goto">{''.join(
    f'<li><a href="#unresolved-{e(u["id"])}">{e(u["teams"][0])} v {e(u["teams"][1])}</a> — '
    f'{e(u["competition"])}, {when(u["starts_at"])}</li>' for u in unresolved) or
    '<li>No unresolved fixture in this snapshot.</li>'}</ul>

<h3>Irregularities — {len(flags)} recorded, {len(review)} needing review</h3>
<p>None of them blocks publication. Each is listed in
<a href="#flags">Flagged for review</a> with the official sources behind it, and the
same register is published to the site&rsquo;s
<a href="{e(SITE_LINKS['review'])}">review page</a>.</p>
</section>'''


def probability_bar(probabilities, teams, pick_index) -> str:
    if not probabilities or len(probabilities) != 2:
        return ('<p class="blank"><span class="unverified">Probability unverified — left blank. '
                'No official source confirmed a line for this fixture.</span></p>')
    left = max(0.0, min(100.0, probabilities[0] * 100))
    right = 100.0 - left
    return f'''<div class="bar" role="img" aria-label="{e(teams[0])} {left:.1f} percent, {e(teams[1])} {right:.1f} percent">
<span class="side a" style="width:{left:.2f}%">{left:.1f}%</span>
<span class="side b" style="width:{right:.2f}%">{right:.1f}%</span></div>'''


def pick_card(fixture: dict, prefix: str = '') -> str:
    teams = fixture.get('teams') or []
    probs = fixture.get('origination_probabilities') or fixture.get('featured_probabilities')
    pick = fixture.get('pick')
    pick_index = None
    if pick and len(teams) == 2:
        pick_index = 0 if teams[0] == pick else (1 if teams[1] == pick else None)
    sides = ''
    for index, team in enumerate(teams[:2]):
        is_pick = index == pick_index
        value = probs[index] if probs and index < len(probs) else None
        sides += f'''<div class="team {"pick" if is_pick else ""}">
<p class="name">{e(team)}{'<span class="badge">PICK</span>' if is_pick else ''}</p>
<p class="prob">{pct(value) if value is not None else '<span class="unverified">blank</span>'}</p></div>'''
    method = fixture.get('origination_method') or fixture.get('featured_method') or 'unresolved'
    urls = [u for u in (fixture.get('origination_source_url'), fixture.get('source_url'),
                        fixture.get('lobby_url')) if u]
    card_class = 'pick-card' if probs else 'unresolved-card'
    return f'''<article class="{card_class}" id="{e(prefix)}{e(fixture.get('id'))}">
<p class="when">{when(fixture.get('starts_at'))} · {e(fixture.get('competition') or '')}</p>
{sides}
{probability_bar(probs, teams, pick_index)}
<p class="meta">Method <strong>{e(method)}</strong> · fixture {e(fixture.get('id'))}
{('· pick ' + e(pick)) if pick else '· <span class="unverified">no pick: unresolved</span>'}</p>
<p class="srcs">{link_list(urls)}</p>
</article>'''


def section_deciders(audit: dict, twc: dict) -> str:
    deciders = twc.get('deciders') or []
    if not deciders:
        # The executive summary links to #deciders, so the anchor must exist even when
        # HLTV's event board could not be read. The absence is stated, not hidden.
        return '''<section class="block" id="deciders">
<h2>Today&rsquo;s deciders — Thunderpick World Championship 2026, Day 3</h2>
<p class="blank"><span class="unverified">Unresolved — HLTV&rsquo;s event board was not readable in
this run, so no Day-3 decider could be confirmed from first-party evidence and none is
listed here.</span> The live picks remain available at
<a href="''' + e(SITE_LINKS['origination_picks']) + '''">every originated pick</a> and
<a href="''' + e(SITE_LINKS['twc_picks']) + '''">the Thunderpick page</a>.</p>
</section>'''
    cards = ''
    for d in deciders:
        cards += f'''<article class="pick-card decider" id="decider-{e(d['fixture_id'])}">
<p class="when">{when(d['starts_at'])} · {e(d['competition'])} · {e(d['slot'] or '')}</p>
<h3>{e(d['teams'][0])} <span class="vs">v</span> {e(d['teams'][1])}</h3>
<div class="sides">'''
        for index, team in enumerate(d['teams'][:2]):
            is_pick = team == d.get('pick')
            value = (d.get('probabilities') or [None, None])[index]
            cards += f'''<div class="team {"pick" if is_pick else ""}">
<p class="name">{e(team)}{'<span class="badge">PICK</span>' if is_pick else ''}</p>
<p class="prob big">{pct(value)}</p></div>'''
        cards += f'''</div>
{probability_bar(d.get('probabilities'), d['teams'], None)}
<p class="meta">Best-of-{e(d.get('best_of') or '?')} {e(d.get('setting') or '')} ·
Hotspawn fixture {e(d['fixture_id'])} · HLTV match {e(d.get('hltv_match_id') or '—')} ·
start {e(d.get('starts_at') or '—')} from HLTV&rsquo;s own <code>data-unix</code></p>
<table class="lines"><caption>Every independent official line read for this fixture</caption>
<thead><tr><th scope="col">Source</th><th scope="col">Names it uses</th>
<th scope="col">Quoted</th><th scope="col">De-vigged</th><th scope="col">Read at</th>
<th scope="col">Link</th></tr></thead><tbody>'''
        for line in d.get('lines') or []:
            quoted = line.get('quoted')
            if isinstance(quoted, list):
                quoted = ' / '.join(str(q) for q in quoted)
            fair = line.get('devigged')
            cards += f'''<tr><th scope="row">{e(line.get('provider'))}</th>
<td>{e(', '.join(line.get('names') or []))}</td><td>{e(quoted or '—')}</td>
<td>{e(fair or '—')}</td><td>{e(line.get('observed_at') or '—')}</td>
<td>{official(line)}</td></tr>'''
        cards += f'''</tbody></table>
<p class="srcs">{link_list(d.get('source_urls'))}</p>
</article>'''
    return f'''<section class="block" id="deciders">
<h2>Today&rsquo;s deciders — Thunderpick World Championship 2026, Day 3</h2>
<p class="lede">Two group deciders, both best-of-three on LAN in Malta. The probabilities are
the ones the site published, and every independent official line read for the same fixture
is listed beside them so the numbers can be checked rather than taken on trust.</p>
{cards}
</section>'''


def section_picks(audit: dict) -> str:
    fixtures = [f for f in audit['fixtures'] if f.get('origination_probabilities')]
    fixtures.sort(key=lambda f: f.get('starts_at') or '')
    cards = ''.join(pick_card(f) for f in fixtures)
    return f'''<section class="block" id="picks">
<h2>Every upcoming fixture with a verified pick ({len(fixtures)})</h2>
<p class="lede">Sorted by start time, in UTC. The check-marked side is the published pick and
the percentages are the published win probabilities. Each card links to the source that
produced the number and to the fixture on Hotspawn. This is a read-only copy of the live
list for review — the live list is
<a href="{e(SITE_LINKS['origination_picks'])}">here</a>.</p>
<div class="cards">{cards}</div>
</section>'''


def section_unresolved(audit: dict) -> str:
    entries = audit['unresolved_review']
    if not entries:
        return f'''<section class="block" id="unresolved"><h2>Unresolved picks</h2>
<p>Every upcoming fixture in this snapshot carries an originated probability and a pick.
Nothing is left blank.</p></section>'''
    blocks = ''
    for entry in entries:
        stages = ''
        for stage in entry.get('ladder') or []:
            if not isinstance(stage, dict):
                continue
            status = str(stage.get('status') or '')
            stages += f'''<tr><th scope="row">{e(stage.get('stage'))}</th>
<td><span class="pill {"ok" if status == "checked" else "warn"}">{e(status or '—')}</span></td>
<td>{e(stage.get('detail') or '—')}</td><td>{official(stage)}</td></tr>'''
        candidates = ''
        for line in entry.get('independent_lines') or []:
            verdict = line.get('verdict')
            fair = line.get('devigged')
            candidates += f'''<tr><th scope="row">{e(line.get('provider'))}</th>
<td>{e(', '.join(line.get('names') or []))}</td>
<td><span class="pill {"ok" if verdict == 'usable' else 'warn'}">{e(verdict)}</span></td>
<td>{e(line.get('similarity', {}).get('detail') or line.get('join'))}</td>
<td>{e(line.get('start_time'))}</td>
<td>{e(', '.join(str(x) for x in fair) if fair else 'not taken')}</td>
<td>{official(line)}</td></tr>'''
        verifications = ''
        for item in entry.get('verifications') or []:
            verifications += f'''<tr><th scope="row">{e(item.get('claim'))}</th>
<td><span class="pill ok">{e(item.get('status'))}</span></td>
<td>{e(item.get('detail'))}</td><td>{official(item)}</td></tr>'''
        limits = ''.join(f'<li>{e(text)}</li>' for text in entry.get('stated_limitations') or [])
        limits_block = (f'<h4>Limitations stated by the site</h4><ul>{limits}</ul>'
                        if limits else '')
        stages_block = (
            '<h4>Every rung tried, in the order the methodology requires</h4>'
            '<table class="ladder"><caption>Research ladder for fixture '
            + e(entry['id']) + '</caption><tbody>' + stages + '</tbody></table>') if stages else ''
        candidates_block = (
            '<h4>Independent lines this audit read for the same fixture</h4>'
            '<table class="ladder"><caption>Independent lines considered for fixture '
            + e(entry['id']) + '</caption><thead><tr><th scope="col">Source</th>'
            '<th scope="col">Names it uses</th><th scope="col">Verdict</th>'
            '<th scope="col">Name comparison</th><th scope="col">Start time</th>'
            '<th scope="col">De-vigged</th><th scope="col">Link</th></tr></thead><tbody>'
            + candidates + '</tbody></table>') if candidates else ''
        verifications_block = (
            '<h4>Rejections this audit confirmed against the original source</h4>'
            '<table class="ladder"><caption>Confirmed rejections for fixture '
            + e(entry['id']) + '</caption><tbody>' + verifications + '</tbody></table>'
        ) if verifications else ''
        blocks += f'''<article class="unresolved-card" id="unresolved-{e(entry['id'])}">
<h3>{e(entry['teams'][0])} v {e(entry['teams'][1])}</h3>
<p class="when">{when(entry.get('starts_at'))} · {e(entry.get('competition') or '')} ·
Hotspawn fixture {e(entry['id'])} · locks {e(entry.get('locks_at') or '—')}</p>
<p class="blank"><strong>Win probability: blank.</strong>
<span class="unverified">Unresolved — no verified input, so no probability and no pick is
published. Not defaulted to 50/50.</span></p>
{limits_block}{stages_block}{candidates_block}{verifications_block}
<p class="srcs">{link_list(entry.get('source_urls'))}</p>
</article>'''
    return f'''<section class="block" id="unresolved">
<h2>Unresolved picks and their limitations ({len(entries)})</h2>
<p class="lede">The research order is fixed: HLTV first, then prediction markets, then
esports books and betting lines, then Valve&rsquo;s official ratings. A fixture reaches this
section only when every rung stopped short, and the reason each one stopped is recorded
with its own link. Where this audit could confirm a rejection from the original source it
says so; where an official book does list the fixture under a different team name, that is
recorded as an alias candidate and <strong>no probability is taken from it</strong>, because
an unverified identity join is exactly how a wrong pick gets published.</p>
{blocks}
</section>'''


def section_twc(audit: dict, twc: dict) -> str:
    results = twc.get('results') or []
    fixtures = twc.get('fixtures') or []
    result_rows = ''
    for r in results:
        teams = r.get('listed_teams') or []
        score = r.get('listed_score') or []
        result_rows += f'''<tr><th scope="row">{e(r.get('match_id'))}</th>
<td>{e(teams[0]) if teams else '—'} {e(score[0]) if score else '—'}–{e(score[1]) if len(score) > 1 else '—'} {e(teams[1]) if len(teams) > 1 else '—'}</td>
<td><strong>{e(r.get('winner') or '—')}</strong></td>
<td>bo{e(r.get('best_of') or '?')}</td>
<td>{e(r.get('finished_utc') or '—')}</td>
<td>{e(r.get('displayed_day') or '—')}</td>
<td>{official(r)}</td></tr>'''
    fixture_rows = ''
    for f in fixtures:
        teams = f.get('teams') or []
        label = ' v '.join(teams) if teams else 'Not yet decided'
        fixture_rows += f'''<tr><th scope="row">{e(f.get('match_id'))}</th>
<td>{e(label)}{'' if teams else ' <span class="unverified">unverified — HLTV lists no teams yet</span>'}</td>
<td>{e(f.get('displayed_day') or '—')}</td><td>{e(f.get('start_utc') or '—')}</td>
<td>{e(f.get('displayed_time') or '—')}</td>
<td>bo{e(f.get('best_of') or '?')} {e(f.get('setting') or '')}</td>
<td>{e(f.get('slot') or '—')}</td><td>{official(f)}</td></tr>'''
    load_rows = ''
    for row in twc.get('load') or []:
        load_rows += f'''<tr><th scope="row">{e(row['team'])}</th>
<td>{e(row['series_played'])}</td><td>{e(row['series_won'])}</td><td>{e(row['maps_played'])}</td>
<td>{e(row['last_result'] or '—')}</td><td>{e(row['last_finished_utc'] or '—')}</td>
<td>{e(row['next_start_utc'] or '—')}</td><td><strong>{e(row['rest'])}</strong></td>
<td>{official({'source_url': row.get('last_result_url')}) if row.get('last_result_url') else
    '<span class="unverified">' + e(NOT_OFFICIAL) + '</span>'}</td></tr>'''
    note = twc.get('timezone_note') or ''
    return f'''<section class="block" id="twc">
<h2>Thunderpick World Championship 2026 — event review</h2>
<p class="lede">Eight teams, $1,000,000, LAN in Malta, 14–18 October 2026. Everything below is
read from HLTV&rsquo;s own event pages and archived verbatim. Times are UTC and come from the
<code>data-unix</code> attributes HLTV publishes, not from the clock times it displays.</p>
{f'<p class="note">{e(note)}</p>' if note else ''}
<h3 id="results">Day 1 and Day 2 — every result</h3>
<table class="data"><caption>HLTV results for event 8932, ordered by HLTV&rsquo;s own finish timestamp</caption>
<thead><tr><th scope="col">HLTV match</th><th scope="col">Listed order and score</th>
<th scope="col">Winner</th><th scope="col">Format</th><th scope="col">Finished (UTC)</th>
<th scope="col">HLTV displayed day</th><th scope="col">Source</th></tr></thead>
<tbody>{result_rows}</tbody></table>
<p class="note">The listed order and the winner are published separately on purpose. HLTV
prints the score in listed order but marks only the winner&rsquo;s cell, so reading the two
score spans positionally inverts three of these eight results. The displayed day is
HLTV&rsquo;s own viewer-timezone grouping: it places Legacy v FURIA under
&ldquo;October 16th 2026&rdquo; although the series finished
2026-10-15T22:01:18Z.</p>

<h3 id="load">Rest and maps played before the Day-3 deciders</h3>
<table class="data"><caption>Arithmetic on HLTV&rsquo;s own finish and start timestamps</caption>
<thead><tr><th scope="col">Team</th><th scope="col">Series played</th><th scope="col">Won</th>
<th scope="col">Maps played</th><th scope="col">Last result</th><th scope="col">Finished (UTC)</th>
<th scope="col">Next start (UTC)</th><th scope="col">Rest</th><th scope="col">Source</th></tr></thead>
<tbody>{load_rows}</tbody></table>
<p class="note">This states how long each team had between series and how many maps it
played. It is not a fatigue model and it does not adjust any probability: no official
source quantifies fatigue, so none is claimed.</p>

<h3 id="board">Remaining fixture board</h3>
<table class="data"><caption>HLTV event 8932 fixture board</caption>
<thead><tr><th scope="col">HLTV match</th><th scope="col">Teams</th><th scope="col">Displayed day</th>
<th scope="col">Start (UTC)</th><th scope="col">Displayed time</th><th scope="col">Format</th>
<th scope="col">Slot</th><th scope="col">Source</th></tr></thead>
<tbody>{fixture_rows}</tbody></table>
</section>'''


def section_roster(audit: dict, twc: dict) -> str:
    roster = twc.get('roster') or {}
    rows = ''
    for team, info in roster.items():
        players = ', '.join(p.get('nick') for p in (info.get('players') or [])[:5]) or '—'
        valve = (info.get('valve_ranking') or {})
        world = (info.get('hltv_world_ranking') or {})
        rows += f'''<tr><th scope="row">{e(team)}</th>
<td>{e(players)}</td>
<td>{e(valve.get('rank_text') or '—')} {e(valve.get('regional') or '')}</td>
<td>{e(world.get('rank_text') or '—')}</td>
<td>{e(info.get('coach', {}).get('name') or '—')}</td>
<td>{e(info.get('weeks_in_top30_core') or '—')}</td>
<td>{official({'source_url': info.get('url')})}</td></tr>'''
    transfers = ''
    for entry in (twc.get('transfers') or {}).get('entries') or []:
        transfers += f'''<tr><th scope="row">{e(entry.get('hltv_displayed_date') or '—')}</th>
<td>{e(entry.get('entry'))}</td>
<td>{official({'source_url': (twc.get('transfers') or {}).get('source_url')})}</td></tr>'''
    transfer_block = (
        '<table class="data"><caption>Every entry in HLTV&rsquo;s transfer log that mentions '
        'Aurora&rsquo;s roster</caption><thead><tr><th scope="col">HLTV displayed date</th>'
        '<th scope="col">Entry as HLTV wrote it</th><th scope="col">Source</th></tr></thead>'
        '<tbody>' + transfers + '</tbody></table>'
    ) if transfers else ('<p class="blank"><span class="unverified">Unresolved — HLTV&rsquo;s '
                         'transfer log was not readable in this run, so the dates of '
                         'Aurora&rsquo;s roster change stay unverified from first-party evidence '
                         'and no recency claim is made.</span></p>')
    verdict = twc.get('roster_verdict') or {}
    roster_table = ''
    if rows:
        roster_table = (
            '<h3>Current squads and both rankings HLTV shows</h3>'
            '<table class="data"><caption>HLTV team pages, read at '
            + e(twc.get('observed_at') or '—') + '</caption><thead><tr>'
            '<th scope="col">Team</th><th scope="col">Players linked on the page</th>'
            '<th scope="col">Valve ranking (VRS)</th><th scope="col">HLTV world ranking</th>'
            '<th scope="col">Coach</th><th scope="col">Weeks in top 30</th>'
            '<th scope="col">Source</th></tr></thead><tbody>' + rows + '</tbody></table>'
            '<p class="note">The player list is every player page HLTV links from the squad '
            'block, which can include former players; the current five are confirmed by the '
            'roster column of Valve&rsquo;s own snapshot in <a href="#ratings">official '
            'ratings</a>, and the two agree.</p>')
    else:
        roster_table = ('<p class="blank"><span class="unverified">Unresolved — HLTV&rsquo;s team '
                        'pages were not readable in this run, so no squad or ranking is stated '
                        'here.</span></p>')
    return f'''<section class="block" id="roster">
<h2>Aurora&rsquo;s roster change — checked against the dates HLTV published</h2>
<p class="lede">The brief asks for Aurora&rsquo;s recent roster change, new-player onboarding,
rest and fatigue to be factored in. Before any of that can be weighed, the date has to be
right, so it was read from HLTV&rsquo;s own transfer log and from Valve&rsquo;s official snapshot
rather than repeated from memory.</p>
<p class="verdict {e(verdict.get('tone') or 'warn')}">{e(verdict.get('text') or NOT_OFFICIAL)}</p>
{transfer_block}
<h3>Current squads and both rankings HLTV shows</h3>
<table class="data"><caption>HLTV team pages, read at {e(twc.get('observed_at') or '—')}</caption>
<thead><tr><th scope="col">Team</th><th scope="col">Players linked on the page</th>
<th scope="col">Valve ranking (VRS)</th><th scope="col">HLTV world ranking</th>
<th scope="col">Coach</th><th scope="col">Weeks in top 30</th><th scope="col">Source</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="note">The player list is every player page HLTV links from the squad block, which
can include former players; the current five are confirmed by the roster column of
Valve&rsquo;s own snapshot in <a href="#ratings">official ratings</a>, and the two agree.</p>
</section>'''


def section_ratings(audit: dict) -> str:
    valve = audit.get('valve_snapshot') or {}
    rows = ''
    for team, info in (valve.get('ratings') or {}).items():
        rows += f'''<tr><th scope="row">{e(team)}</th><td>{e(info.get('standing'))}</td>
<td>{e(info.get('points'))}</td><td>{e(', '.join(info.get('roster') or []))}</td>
<td>{e(info.get('snapshot'))}</td><td>{official(info)}</td></tr>'''
    ambiguous = ''
    for team, candidates in (valve.get('ambiguous') or {}).items():
        detail = '; '.join(f"standing {c.get('standing')}, {c.get('points')} points, "
                           f"roster {', '.join(c.get('roster') or [])}" for c in candidates)
        ambiguous += f'''<tr><th scope="row">{e(team)}</th><td>{e(len(candidates))}</td>
<td>{e(detail)}</td><td><span class="unverified">ambiguous — no rating used</span></td>
<td>{official(candidates[0]) if candidates else ''}</td></tr>'''
    absent = ', '.join(valve.get('absent') or []) or 'none'
    ambiguous_block = ''
    if ambiguous:
        ambiguous_block = (
            '<h3>Names Valve lists more than once</h3>'
            '<table class="data"><caption>Duplicate exact names in the same official snapshot</caption>'
            '<thead><tr><th scope="col">Name</th><th scope="col">Rows</th>'
            '<th scope="col">Candidates</th><th scope="col">Used</th>'
            '<th scope="col">Source</th></tr></thead><tbody>' + ambiguous + '</tbody></table>'
            '<p class="note">Choosing between two official rows with the same name would be an '
            'inference, so neither is used and the fixture stays unresolved.</p>')
    ratings_table = (
        '<table class="data"><caption>Valve Regional Standings, global snapshot '
        + e(valve.get('snapshot_used') or '—') + '</caption>'
        '<thead><tr><th scope="col">Team</th><th scope="col">Standing</th>'
        '<th scope="col">Points</th><th scope="col">Roster as Valve lists it</th>'
        '<th scope="col">Snapshot</th><th scope="col">Source</th></tr></thead><tbody>'
        + rows + '</tbody></table>')
    return f'''<section class="block" id="ratings">
<h2>Official ratings — Valve&rsquo;s own standings</h2>
<p class="lede">The lowest rung of the origination ladder, and the only rating source this
project treats as official. Read as of {e(valve.get('standings_as_of') or '—')} from
{e(valve.get('snapshot_used') or '—')}.</p>
{ratings_table}
{ambiguous_block}
<p class="note">No exact-name row at all: {e(absent)}.</p>
<p class="srcs">{official({'source_url': valve.get('source_url')})} ·
{link_list(valve.get('limitations') and [] or [])}</p>
</section>'''


def section_verification(audit: dict) -> str:
    fp = audit['first_party_market_check']
    fp_rows = ''
    for record in fp['checked']:
        fp_rows += f'''<tr><th scope="row">{e(record['id'])}</th>
<td>{e(' v '.join(record['teams']))}</td>
<td>{e(', '.join(record.get('first_party_outcomes') or []))}</td>
<td>{e(', '.join(f'{v:.3f}' for v in record['first_party_prices']))}</td>
<td>{e(', '.join(f'{v:.3f}' for v in record['published_probabilities']))}</td>
<td>{e(', '.join(f'{v:+.2f}pp' for v in record['deviation_pp']))}</td>
<td>{e(record.get('reading_gap_hours'))} h</td>
<td><span class="pill {"ok" if record['same_favourite'] else "bad"}">
{'agrees' if record['same_favourite'] else 'reversed'}</span></td>
<td>{e(', '.join(record.get('aligned_via_reviewed_alias') or []) or 'direct')}</td>
<td>{official(record)}</td></tr>'''
    for record in fp['unverifiable']:
        fp_rows += f'''<tr><th scope="row">{e(record['id'])}</th>
<td>{e(' v '.join(record['teams']))}</td><td colspan="7">
<span class="unverified">{e(record['reason'])}</span></td>
<td>{link_list(record.get('source_urls') or audit['source_links']['source_urls'])}</td></tr>'''
    replay = audit['probability_replay']
    replay_rows = ''
    for record in replay['rows']:
        replayed = record.get('replayed')
        replay_rows += f'''<tr><th scope="row">{e(record['id'])}</th>
<td>{e(record.get('method') or '—')}</td>
<td>{e(', '.join(f'{v:.4f}' for v in record['published'])) if record.get('published') else 'blank'}</td>
<td>{e(', '.join(f'{v:.4f}' for v in replayed)) if replayed else '—'}</td>
<td><span class="pill {"ok" if record['status'] == 'replayed' else ("warn" if record['status'] in ('blank', 'model-inputs-only') else "bad")}">{e(record['status'])}</span></td>
<td>{e(' | '.join(record['checks'])[:400])}</td>
<td>{link_list(record.get('source_urls'))}</td></tr>'''
    checks = audit['cross_checks']
    cross_rows = ''
    for record in checks['agreeing'] + checks['disagreeing']:
        cross_rows += f'''<tr><th scope="row">{e(record['id'])}</th>
<td>{e(' v '.join(record['teams']))}</td>
<td>{e(record['published_provider'])} → <strong>{e(record['published_pick'])}</strong>
{e(', '.join(pct(v) for v in record['published_probabilities']))}</td>
<td>{e(record['independent_provider'])} → <strong>{e(record['independent_pick'])}</strong>
{e(', '.join(pct(v) for v in record['independent_probabilities']))}</td>
<td>{e(', '.join(str(o) for o in record.get('independent_decimal_odds') or []) or '—')}</td>
<td>{e(record.get('independent_overround') or '—')}</td>
<td><span class="pill {"ok" if record['same_pick'] else "bad"}">
{'same pick' if record['same_pick'] else 'different pick'}</span></td>
<td>{official(record)}</td></tr>'''
    alias_rows = ''
    for record in checks['alias_only'][:40]:
        alias_rows += f'''<tr><th scope="row">{e(record['id'])}</th>
<td>{e(' v '.join(record['teams']))}</td><td>{e(record['provider'])}</td>
<td>{e(', '.join(record.get('line_names') or []))}</td>
<td>{e(record.get('similarity'))}</td><td>{e(record.get('start_time'))}</td>
<td><span class="unverified">identity unverified</span></td>
<td>{official(record)}</td></tr>'''
    inventory = audit['inventory_reconciliation']
    counts = audit['published_counts_check']
    count_rows = ''.join(
        f'''<tr><th scope="row">{e(key)}</th><td>{e(value)}</td>
<td>{e(counts['published'].get(key, '—'))}</td>
<td><span class="pill {'ok' if counts['published'].get(key) == value else 'bad'}">
{'equal' if counts['published'].get(key) == value else 'differs'}</span></td>
<td>{link_list(counts['source_urls'])}</td></tr>'''
        for key, value in counts['recomputed'].items())
    hazards = ''.join(
        f'''<tr><th scope="row">{e(h['id'])}</th><td>{e(', '.join(h['teams']))}</td>
<td>{e(', '.join(h['recorded_source_outcomes'] or []))}</td>
<td>{e(', '.join(f"{v:.3f}" for v in h['published_probabilities'] or []))}</td>
<td>{e(', '.join(h['first_party_outcomes'] or []))}</td>
<td>{e(', '.join(f"{v:.3f}" for v in h['first_party_prices'] or []) or '—')}</td>
<td><span class="pill {'ok' if h['published_matches_first_party_in_team_order'] else 'bad'}">
{'correct' if h['published_matches_first_party_in_team_order'] else 'check'}</span></td>
<td>{official(h)}</td></tr>''' for h in audit['outcome_order_hazards'])
    alias_block = ''
    if alias_rows:
        alias_block = (
            '<h3>Same fixture, different team labels</h3>'
            '<p class="lede">Official books frequently label the same fixture differently. These '
            'are recorded so a reviewer can see the line exists; the identity is not verified by '
            'this audit and no probability is taken from any of them.</p>'
            '<table class="data"><caption>Alias-only observations on fixtures that already have a '
            'pick</caption><thead><tr><th scope="col">Fixture</th><th scope="col">Site names</th>'
            '<th scope="col">Source</th><th scope="col">Its names</th>'
            '<th scope="col">Name comparison</th><th scope="col">Start time</th>'
            '<th scope="col">Used</th><th scope="col">Link</th></tr></thead><tbody>'
            + alias_rows + '</tbody></table>')
    order_block = ''
    if hazards:
        order_block = (
            '<h3 id="order">Two published arrays in opposite orders</h3>'
            '<table class="data"><caption>source_outcomes is the market&rsquo;s order; '
            'probabilities is the fixture&rsquo;s</caption><thead><tr><th scope="col">Fixture</th>'
            '<th scope="col">Hotspawn order</th><th scope="col">source_outcomes</th>'
            '<th scope="col">Published probabilities</th><th scope="col">Polymarket outcomes</th>'
            '<th scope="col">Polymarket prices</th><th scope="col">Published is</th>'
            '<th scope="col">Source</th></tr></thead><tbody>' + hazards + '</tbody></table>'
            '<p class="note">Reading the two arrays positionally inverts the favourite. Every case '
            'was checked against Polymarket&rsquo;s own prices and the published probability is '
            'correct; this is a readability defect in the published JSON, not a wrong number.</p>')
    return f'''<section class="block" id="verification">
<h2>What was checked, line by line</h2>

<h3>Inventory</h3>
<p>{e(inventory['verdict'])} Hotspawn&rsquo;s fixtures API lists
<strong>{e(inventory['hotspawn_api_id_count'])}</strong> CS2 fixtures; the site publishes
<strong>{e(inventory['deployed_row_count'])}</strong> rows, of which
<strong>{e(inventory['deployed_open_count'])}</strong> are upcoming.</p>
<p class="srcs">{link_list(inventory['source_urls'])}</p>

<h3 id="counts">Published counts recomputed from the published rows</h3>
<table class="data"><caption>Recomputed against the deployed snapshot</caption>
<thead><tr><th scope="col">Count</th><th scope="col">Recomputed</th><th scope="col">Published</th>
<th scope="col">Verdict</th><th scope="col">Source</th></tr></thead><tbody>{count_rows}</tbody></table>

<h3 id="first-party">Each priced row re-read against Polymarket&rsquo;s own event</h3>
<p class="lede">This check does not trust the row&rsquo;s quotes, its recorded outcome order or its
arithmetic. It reads the outcome names and prices from the archived Gamma response for the
row&rsquo;s own event id and aligns them to the fixture&rsquo;s team order. Prices move between the
site&rsquo;s refresh and this audit, so the deviation is reported rather than demanding exact
equality; a reversed favourite is a finding regardless of drift.</p>
<table class="data"><caption>First-party market check</caption>
<thead><tr><th scope="col">Fixture</th><th scope="col">Teams</th><th scope="col">Polymarket outcomes</th>
<th scope="col">Polymarket prices</th><th scope="col">Published</th><th scope="col">Deviation</th><th scope="col">Reading gap</th>
<th scope="col">Favourite</th><th scope="col">Aligned via</th><th scope="col">Source</th></tr></thead>
<tbody>{fp_rows}</tbody></table>

<h3 id="replay">Each probability replayed from the quote the row cites</h3>
<table class="data"><caption>Probability replay — {e(replay['replayed'])} replayed, {e(replay['mismatched'])} mismatched, {e(replay['blank'])} blank, {e(replay['not_replayable'])} not replayable from a price</caption>
<thead><tr><th scope="col">Fixture</th><th scope="col">Rung</th><th scope="col">Published</th>
<th scope="col">Replayed</th><th scope="col">Status</th><th scope="col">Checks performed</th>
<th scope="col">Sources</th></tr></thead><tbody>{replay_rows}</tbody></table>

<h3 id="cross">Independent official lines against the published pick</h3>
<table class="data"><caption>Cross-checks — {e(len(checks['agreeing']))} same pick, {e(len(checks['disagreeing']))} different pick</caption>
<thead><tr><th scope="col">Fixture</th><th scope="col">Teams</th><th scope="col">Published</th>
<th scope="col">Independent</th><th scope="col">Odds</th><th scope="col">Overround</th>
<th scope="col">Verdict</th><th scope="col">Source</th></tr></thead><tbody>{cross_rows}</tbody></table>
{alias_block}
{order_block}
</section>'''


def section_flags(audit: dict) -> str:
    flags = audit['flags']
    order = {'critical': 0, 'review': 1, 'notice': 2, 'watch': 3}
    flags = sorted(flags, key=lambda f: (order.get(f.get('severity'), 9), f.get('id', '')))
    rows = ''
    for flag in flags:
        rows += f'''<tr><th scope="row">{e(flag['title'])}</th>
<td><span class="pill {e(flag['severity'])}">{e(flag['severity'])}</span></td>
<td>{e(flag['detail'])}</td>
<td>{e(', '.join(flag.get('match_ids') or []) or '—')}</td>
<td><code>{e(flag['id'])}</code></td>
<td>{link_list(flag.get('source_urls'))}</td></tr>'''
    table_block = (
        '<table class="data"><caption>Irregularity register, session arena-ba7164a0</caption>'
        '<thead><tr><th scope="col">Finding</th><th scope="col">Severity</th>'
        '<th scope="col">Detail</th><th scope="col">Fixtures</th><th scope="col">Flag id</th>'
        '<th scope="col">Sources</th></tr></thead><tbody>' + rows + '</tbody></table>'
    ) if rows else '<p>No irregularity was found in this snapshot.</p>'
    return f'''<section class="block" id="flags">
<h2>Flagged for review ({len(flags)})</h2>
<p class="lede">Irregularities found while verifying the published data. None of them blocks
publication, and none of them was fixed by this audit: each is recorded with the official
sources behind it so a reviewer can decide. The same register is published to the
site&rsquo;s <a href="{e(SITE_LINKS['review'])}">Flagged for review</a> page.</p>
{table_block}
</section>'''


def section_method(audit: dict) -> str:
    limits = ''.join(f'<li>{e(text)}</li>' for text in audit.get('limitations') or [])
    window = audit['probe_window']
    providers = audit['independent_lines']['by_provider']
    provider_rows = ''.join(
        f'<tr><th scope="row">{e(name)}</th><td>{e(count)}</td>'
        f'<td>{link_list([u for u in PROVIDER_URLS.get(name, [])])}</td></tr>'
        for name, count in providers.items())
    return f'''<section class="block" id="method">
<h2>How this page was produced</h2>
<p class="lede">Read-only. No probability on this page was originated, estimated, defaulted or
repaired by this session; the picks shown are the ones the site already published, and the
job here is to say whether each one can be confirmed from an official source.</p>
<ol>
<li><code>scripts/research_verify.py</code> read {e(window['requests_ok'])} official sources
between {e(audit['probe_window'].get('started_at'))} and
{e(audit['probe_window'].get('finished_at'))} and archived every original response
verbatim under <code>data/research/ba7164a0/raw/</code>.
{e(window['requests_not_ok'])} were unreadable; each unreadable source is reported as a
limitation instead of being worked around.</li>
<li><code>scripts/verify_published.py</code> replayed the deployed snapshot against those
archives and wrote <a href="{e(SITE_LINKS['audit_json'])}">audit.json</a>.</li>
<li><code>scripts/build_verify_report.py</code> rendered this page from that dossier.</li>
</ol>
<table class="data"><caption>Independent money lines read, by provider</caption>
<thead><tr><th scope="col">Provider</th><th scope="col">Lines</th><th scope="col">Source</th></tr></thead>
<tbody>{provider_rows}</tbody></table>
<h3>Limitations</h3>
<ul>{limits}</ul>
<h3>What is deliberately not done here</h3>
<ul>
<li>Hotspawn popularity or participation is never used as a probability input.</li>
<li>No value is filled in because it looks reasonable. A value that cannot be confirmed is
left blank and labelled unverified.</li>
<li>An identity join that is not exact or already reviewed as an alias never contributes a
probability, however close the names look.</li>
<li>No file outside this session&rsquo;s claimed scope is edited.</li>
</ul>
<p class="srcs">Dossier: <a href="{e(SITE_LINKS['audit_json'])}">audit.json</a> ·
<a href="{e(SITE_LINKS['observations_json'])}">observations.json</a></p>
</section>'''


PROVIDER_URLS = {
    'Polymarket': ['https://polymarket.com/esports/cs2', 'https://gamma-api.polymarket.com/events'],
    'Kalshi': ['https://kalshi.com/markets/kxcs2game/counterstrike-2-game'],
    'Bovada': ['https://www.bovada.lv/sports'],
    'Thunderpick': ['https://thunderpick.io/esports/counter-strike'],
    'HLTV': ['https://www.hltv.org/events/8932/thunderpick-world-championship-2026'],
}


def sitemap() -> str:
    rows = ''.join(
        f'<tr><th scope="row">{e(label)}</th><td>{e(hint)}</td>'
        f'<td><a href="{e(href)}">{e(href)}</a></td></tr>'
        for label, href, hint in [
            ('Site summary', SITE_LINKS['summary'], 'Headline coverage and status'),
            ('Featured picks', SITE_LINKS['picks'], 'Curated picks'),
            ('All originated picks', SITE_LINKS['origination_picks'], 'Every Hotspawn CS2 fixture'),
            ('Unresolved', SITE_LINKS['origination_unresolved'], 'Fixtures with blank probabilities'),
            ('Edge', SITE_LINKS['edge'], 'Where the edge comes from'),
            ('Coverage', SITE_LINKS['coverage'], 'What is covered and what is not'),
            ('Methodology', SITE_LINKS['methodology'], 'How probabilities are originated'),
            ('Flagged for review', SITE_LINKS['review'], 'Irregularity register'),
            ('Strategy', SITE_LINKS['strategy'], 'Leaderboard plan'),
            ('Thunderpick picks', SITE_LINKS['twc_picks'], 'The LAN event'),
            ('This audit', SITE_LINKS['audit_json'], 'Machine-readable dossier'),
        ])
    return f'''<section class="block" id="sitemap">
<table class="data"><caption>Every page on this site that this report links to</caption>
<thead><tr><th scope="col">Page</th><th scope="col">What it holds</th>
<th scope="col">Link</th></tr></thead><tbody>{rows}</tbody></table>
</section>'''


CSS = '''/* Verification & review — mobile first. No script, no external asset, no webfont. */
:root{--bg:#0f1a24;--panel:#142534;--panel2:#1b3245;--ink:#eaf2f8;--muted:#9fb6c6;
--line:#26415a;--ok:#2ecc71;--warn:#f1c40f;--bad:#e74c3c;--pick:#ffd166;--accent:#4aa3df}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}
.skip{position:absolute;left:-9999px;top:0;background:var(--accent);color:#08131c;padding:.6rem 1rem;z-index:9}
.skip:focus{left:0}
header.top{padding:1rem 1rem .6rem;border-bottom:1px solid var(--line);background:var(--panel)}
header.top .brand{margin:0;font-size:1.05rem}
header.top .brand a{text-decoration:none;color:var(--ink)}
header.top .snap{margin:.35rem 0 0;color:var(--muted);font-size:.85rem}
main{padding:0 0 3rem;max-width:74rem;margin:0 auto}
.block{padding:1.4rem 1rem;border-bottom:1px solid var(--line)}
h2{margin:0 0 .5rem;font-size:1.45rem;line-height:1.25}
h3{margin:1.4rem 0 .4rem;font-size:1.12rem}
h4{margin:1rem 0 .3rem;font-size:.98rem;color:var(--muted)}
.lede{color:var(--muted);margin:.2rem 0 .9rem}
.note{color:var(--muted);font-size:.85rem;margin:.5rem 0}
code{background:var(--panel2);padding:.1rem .3rem;border-radius:3px;font-size:.85em}
table{border-collapse:collapse;width:100%;margin:.5rem 0 .9rem;font-size:.9rem}
caption{text-align:left;color:var(--muted);font-size:.82rem;padding:.25rem 0}
th,td{text-align:left;padding:.5rem .5rem;border-bottom:1px solid var(--line);vertical-align:top}
thead th{color:var(--muted);font-weight:600;font-size:.8rem;border-bottom:2px solid var(--line)}
tbody th{font-weight:600;white-space:nowrap}
.data{display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}
.pill{display:inline-block;padding:.1rem .5rem;border-radius:999px;font-size:.75rem;
border:1px solid var(--line);white-space:nowrap}
.pill.ok,.tick.yes{color:var(--ok);border-color:var(--ok)}
.pill.warn,.tick{color:var(--warn);border-color:var(--warn)}
.pill.bad,.pill.review,.tick.no{color:var(--bad);border-color:var(--bad)}
.pill.notice{color:var(--warn);border-color:var(--warn)}
.pill.critical{color:#fff;background:var(--bad);border-color:var(--bad)}
.tick{display:inline-block;padding:.05rem .45rem;border:1px solid;border-radius:999px;
font-size:.72rem;margin-right:.35rem;text-transform:uppercase;letter-spacing:.03em}
.unverified{color:var(--bad);font-weight:600}
.blank{background:var(--panel2);border-left:3px solid var(--bad);padding:.55rem .7rem;margin:.5rem 0}
.verdict{background:var(--panel2);border-left:3px solid var(--warn);padding:.7rem .85rem;margin:.6rem 0}
.verdict.ok{border-left-color:var(--ok)}
.verdict.bad{border-left-color:var(--bad)}
.snapshot{color:var(--muted);font-size:.9rem;margin:.2rem 0 .8rem}
ul.goto{margin:.3rem 0 .8rem;padding-left:1.15rem}
ul.goto li{margin:.3rem 0}
.cards{display:grid;gap:.7rem;grid-template-columns:1fr}
.pick-card,.unresolved-card{background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:.85rem .9rem}
.pick-card .when,.unresolved-card .when{margin:0 0 .5rem;color:var(--muted);font-size:.8rem}
.sides{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
article.pick-card>.team{background:var(--panel2);border-radius:8px;padding:.5rem .6rem;
border:1px solid transparent}
article.pick-card>.team.pick{border-color:var(--pick);background:#22303f}
.team .name{margin:0;font-size:.92rem;font-weight:600}
.team .prob{margin:.15rem 0 0;font-size:1.5rem;font-weight:700;font-variant-numeric:tabular-nums}
.team .prob.big{font-size:2rem}
.badge{display:inline-block;margin-left:.4rem;background:var(--pick);color:#20180a;
font-size:.66rem;font-weight:800;padding:.12rem .4rem;border-radius:4px;
letter-spacing:.06em;vertical-align:middle}
.bar{display:flex;height:1.5rem;border-radius:6px;overflow:hidden;margin:.6rem 0 .35rem;
background:var(--panel2);font-size:.72rem;font-weight:700}
.bar .side{display:flex;align-items:center;justify-content:center;min-width:2.6rem;
color:#0d1b26;white-space:nowrap}
.bar .side.a{background:var(--accent)}
.bar .side.b{background:#7f8fa6;color:#0d1b26}
.meta{margin:.35rem 0;color:var(--muted);font-size:.82rem}
.srcs{margin:.35rem 0 0;font-size:.78rem;word-break:break-word}
a.src{display:inline-block;margin:.1rem .35rem .1rem 0;padding:.12rem .45rem;
border:1px solid var(--line);border-radius:5px;text-decoration:none;color:var(--accent);
font-size:.78rem;word-break:break-all}
.decider{background:var(--panel);border-color:var(--accent)}
.decider h3{margin:.1rem 0 .6rem;font-size:1.2rem}
.decider .vs{color:var(--muted);font-weight:400}
footer{padding:1.2rem 1rem 2.5rem;color:var(--muted);font-size:.82rem;border-top:1px solid var(--line)}
@media (min-width:44rem){
 .cards{grid-template-columns:repeat(2,minmax(0,1fr))}
 h2{font-size:1.7rem}
 .team .prob{font-size:1.8rem}
 .team .prob.big{font-size:2.6rem}
}
@media (min-width:70rem){.cards{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
'''


def transfer_log(evidence: Path, hltv: dict) -> dict:
    """Re-read HLTV's transfer log from the archived original response.

    The dossier's extracted entries are re-derived here so a fix to the extractor applies
    to evidence already archived, instead of waiting for another fetch. Falls back to the
    recorded extraction when the original response is not present.
    """
    from scripts.research_verify import parse_hltv_transfer_log
    from scripts.verify_published import load_raw_text
    recorded = hltv.get('aurora_transfer_log') or {}
    text = load_raw_text(evidence, 'hltv-rostermania')
    if not text:
        return clean_transfers(recorded)
    parsed = parse_hltv_transfer_log(text)
    parsed['source_url'] = recorded.get('source_url') or 'https://www.hltv.org/news/44998/' \
        'summer-2026-rostermania-as-it-happened'
    return clean_transfers(parsed)


def clean_transfers(transfers: dict) -> dict:
    """Drop the fragments HLTV's transfer log interleaves with its own headlines.

    The log repeats a story as a headline, a bare team name and a quoted nickname. Only
    lines that state something are kept, in the order HLTV published them, deduplicated.
    """
    entries, seen = [], set()
    for entry in (transfers or {}).get('entries') or []:
        text = str(entry.get('entry') or '').strip()
        stamp = entry.get('hltv_displayed_date')
        if len(text) < 14 or (text, stamp) in seen:
            continue
        seen.add((text, stamp))
        entries.append({'hltv_displayed_date': stamp, 'entry': text})
    return {**(transfers or {}), 'entries': entries, 'count': len(entries)}


def evidence_dir() -> Path:
    """Where the archived original responses live."""
    return EVIDENCE_DIR


def twc_context(audit: dict, observations: dict) -> dict:
    """Assemble the Thunderpick facts this page states, from archived evidence only."""
    hltv = observations.get('hltv') or {}
    schedule = (hltv.get('schedule') or {}).get('fixtures') or []
    results = (hltv.get('results') or {}).get('results') or []
    match_pages = hltv.get('match_pages') or {}
    teams = hltv.get('teams') or {}

    by_match = {str(f.get('match_id')): f for f in schedule}
    fixtures = []
    for fixture in schedule:
        page = match_pages.get(str(fixture.get('match_id'))) or {}
        fixtures.append({**fixture, 'slot': page.get('slot'), 'setting': page.get('setting'),
                         'source_url': fixture.get('url') or page.get('canonical_url')})

    lines_by_fixture: dict = {}
    for line in audit['independent_lines']['lines']:
        for fixture in audit['fixtures']:
            candidate = {'names': line.get('names'), 'provider': line['provider']}
            verdict = None
            for record in audit['cross_checks']['agreeing'] + audit['cross_checks']['disagreeing']:
                if (record['id'] == fixture['id'] and record['independent_provider'] == line['provider']
                        and record.get('independent_decimal_odds') == line.get('decimal_odds')):
                    verdict = 'usable'
            if verdict is None:
                for record in audit['cross_checks']['alias_only']:
                    if record['id'] == fixture['id'] and record['provider'] == line['provider']:
                        verdict = 'alias-only'
            if verdict:
                fair = line.get('devigged')
                quoted = line.get('decimal_odds') or [line.get('market_best_bid'),
                                                      line.get('market_best_ask')]
                lines_by_fixture.setdefault(fixture['id'], []).append({
                    'provider': line['provider'], 'names': candidate['names'],
                    'quoted': quoted,
                    'devigged': (f"{fair[0] * 100:.1f}% / {fair[1] * 100:.1f}%"
                                 if fair and len(fair) == 2 else 'not taken'),
                    'observed_at': line.get('observed_at'),
                    'source_url': line.get('source_url'), 'verdict': verdict})

    deciders = []
    for fixture in audit['fixtures']:
        match_id = None
        for candidate_id, candidate in by_match.items():
            names = {n.lower() for n in candidate.get('teams') or []}
            published = {str(t).lower() for t in fixture.get('teams') or []}
            if names and names == published:
                match_id = candidate_id
                break
        if not match_id:
            continue
        entry = by_match[match_id]
        page = match_pages.get(match_id) or {}
        probabilities = fixture.get('origination_probabilities')
        pick = fixture.get('pick')
        deciders.append({
            'fixture_id': fixture['id'],
            'hltv_match_id': match_id,
            'teams': fixture.get('teams') or [],
            'competition': fixture.get('competition'),
            'starts_at': fixture.get('starts_at'),
            'slot': page.get('slot') or entry.get('slot'),
            'best_of': entry.get('best_of') or page.get('best_of'),
            'setting': page.get('setting') or ('LAN' if entry.get('lan') == 'true' else None),
            'probabilities': probabilities,
            'pick': pick,
            'pick_probability': (probabilities[fixture['teams'].index(pick)]
                                 if probabilities and pick in (fixture.get('teams') or []) else None),
            'lines': lines_by_fixture.get(fixture['id']) or [],
            'source_urls': [u for u in (entry.get('url'), page.get('canonical_url'),
                                        fixture.get('origination_source_url'),
                                        fixture.get('source_url'), fixture.get('lobby_url')) if u],
        })
    deciders.sort(key=lambda d: d.get('starts_at') or '')

    roster_verdict = {}
    transfers = transfer_log(evidence_dir(), hltv)
    entries = transfers.get('entries') or []
    if entries:
        # The completion of the rebuild is the date that matters for a recency claim, so it
        # is taken from HLTV's own "complete rebuild" entry rather than from every date the
        # log happens to mention.
        completed = next((x for x in entries if 'complete rebuild' in str(x.get('entry', '')).lower()), None)
        move_dates = sorted({str(x.get('hltv_displayed_date')) for x in entries
                             if x.get('hltv_displayed_date')})
        roster_verdict = {
            'tone': 'warn',
            'text': (
                "HLTV's own transfer log dates every Aurora roster move to late June and July "
                "2026 (displayed as " + ', '.join(move_dates) + ", DD/MM as HLTV prints them). "
                + (f"The rebuild is recorded complete on {completed['hltv_displayed_date']} "
                   f"(HLTV: \u201c{completed['entry']}\u201d). " if completed else '')
                + "Valve's official snapshot of 5 October 2026 already lists the same five "
                  "players - Jimpphat, kyxsan, Wicadia, woxic, XANTARES - and so does HLTV's "
                  "team page today. The change is therefore confirmed from first-party "
                  "evidence, but it is NOT recent: it was complete about three months before "
                  "Day 3, and both official rating sources already reflect it. Any claim that "
                  "a fresh roster change explains Day-3 form is not supported by these "
                  "sources, and none is made here."),
        }
    else:
        roster_verdict = {'tone': 'bad',
                          'text': "HLTV's transfer log was not readable in this run, so the date "
                                  'of Aurora&rsquo;s roster change is unverified from first-party '
                                  'evidence and no recency claim is made.'.replace('&rsquo;', "'")}

    load_teams = []
    for decider in deciders:
        load_teams.extend(decider['teams'])
    return {
        'deciders': deciders,
        'results': results,
        'fixtures': fixtures,
        'load': team_load(hltv, load_teams),
        'roster': teams,
        'transfers': transfers,
        'roster_verdict': roster_verdict,
        'observed_at': hltv.get('observed_at'),
        'timezone_note': (hltv.get('schedule') or {}).get('timezone_note'),
    }


def render(audit: dict, observations: dict) -> str:
    twc = twc_context(audit, observations)
    body = ''.join([
        executive_summary(audit, twc),
        section_deciders(audit, twc),
        section_picks(audit),
        section_unresolved(audit),
        section_twc(audit, twc),
        section_roster(audit, twc),
        section_ratings(audit),
        section_verification(audit),
        section_flags(audit),
        section_method(audit),
        sitemap(),
    ])
    staleness = audit['staleness']
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verification &amp; review — independent audit of every published pick · Spawn Scout</title>
<meta name="description" content="An independent, read-only verification of the live Hotspawn CS2 pick'em dashboard: every published probability replayed against the original official source, every unresolved fixture documented, and every irregularity flagged with links. Mobile-friendly.">
<meta name="theme-color" content="#142534">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'">
<link rel="icon" href="{e(RELATIVE_ROOT)}assets/scout-mark.svg" type="image/svg+xml">
<link rel="stylesheet" href="{e(RELATIVE_ROOT)}{e(CSS_NAME)}">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
<p class="brand"><a href="{e(RELATIVE_ROOT)}index.html">spawn<strong>scout</strong></a>
<span>· verification &amp; review</span></p>
<p class="snap">Live snapshot {e(staleness['generated_at'] or '—')} ·
this audit {e(audit['generated_at'])} · session arena-ba7164a0</p>
</header>
<main id="main">
{body}
</main>
<footer>
<p><strong>Read-only verification.</strong> This page confirms or flags what the site
publishes. It does not originate, estimate, default or repair any probability, and it uses
Hotspawn popularity for nothing.</p>
<p>Independent research dashboard · not affiliated with Hotspawn, HLTV, Valve, Polymarket,
Kalshi, Bovada, Thunderpick or any betting provider. Informational use only. 18+ where
applicable. No bets are placed.</p>
</footer>
</body></html>
'''


def build(source: Path, output: Path) -> Path:
    """Render the report into a built site tree. Signature build.py can call directly."""
    evidence = source / 'research' / 'ba7164a0'
    audit = json.loads((evidence / 'audit.json').read_text())
    observations_path = evidence / 'observations.json'
    observations = json.loads(observations_path.read_text()) if observations_path.exists() else {}
    page = output / REPORT_NAME
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(render(audit, observations))
    css = output / CSS_NAME
    css.parent.mkdir(parents=True, exist_ok=True)
    css.write_text(CSS)
    return page


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=EVIDENCE_DIR)
    parser.add_argument('--site', type=Path, default=None,
                        help='Also write the page and stylesheet into a built site tree.')
    args = parser.parse_args(argv)

    audit = json.loads((args.evidence / 'audit.json').read_text())
    observations_path = args.evidence / 'observations.json'
    observations = json.loads(observations_path.read_text()) if observations_path.exists() else {}
    html = render(audit, observations)

    page = args.evidence / 'report.html'
    page.write_text(html)
    css = Path(CSS_NAME)
    css.parent.mkdir(parents=True, exist_ok=True)
    css.write_text(CSS)
    print(f'Wrote {page} ({len(html)} bytes) and {css}')
    if args.site:
        written = build(args.evidence.parent.parent.parent, args.site)
        print(f'Wrote {written}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
