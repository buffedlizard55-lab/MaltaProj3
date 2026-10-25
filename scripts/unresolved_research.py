"""Render the dedicated unresolved-picks research section from
``data/research/<session>/unresolved-research.json``.

Every Hotspawn CS2 fixture must ship a pick or an explicit reason it stays
blank. This renderer publishes the research dossier behind those blanks:
per-fixture check trails (HLTV identity → verified exchange books →
bookmakers → Valve model) where every observation carries an official https
link and its own timestamp, the verified alias joins that unblocked two
fixtures, and the honest limitations.

The section is a pure renderer: it never writes a probability into a pick
file and it never fills a blank. Values that failed the published book
contract render as "guidance only" next to an explicit unverified marker.

Usage: ``from scripts.unresolved_research import load_research, render_section``.
The site build (scripts/build.py) links this section from the executive
summary; until that integration hook lands, the dossier and its flags are
still published through data/research/ and the Flagged for Review page.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.build import badge, e, external, heading
from scripts.domain import timestamp

SCHEMA = 1


def load_research(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get('schema_version') != SCHEMA:
        raise ValueError('unsupported unresolved-research schema')
    if not data.get('title') or not data.get('policy'):
        raise ValueError('unresolved-research needs title and policy')
    if timestamp(data.get('prepared_at')) is None:
        raise ValueError('unresolved-research needs a prepared_at timestamp')
    fixtures = data.get('fixtures')
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError('unresolved-research fixtures must be a non-empty list')
    for fixture in fixtures:
        if not fixture.get('hotspawn_id') or not fixture.get('teams') or not fixture.get('checks'):
            raise ValueError('every fixture needs hotspawn_id, teams and checks')
        if fixture.get('resolution') not in ('stays-unresolved', 'expected-at-next-refresh'):
            raise ValueError('fixture resolution must stay explicit')
        for check in fixture['checks']:
            if not check.get('stage') or not check.get('verdict'):
                raise ValueError('every check needs a stage and a verdict')
            if not check.get('sources'):
                raise ValueError('every check needs at least one official source link')
            for src in check['sources']:
                if not str(src.get('url', '')).startswith('https://'):
                    raise ValueError('unresolved-research sources must be https links')
                if not src.get('observed_at'):
                    raise ValueError('unresolved-research sources must carry an observation time')
        quote = fixture.get('guidance_quote')
        if quote is not None and not quote.get('observed_at'):
            raise ValueError('guidance quotes must carry an observation time')
    # Session arena-93c7475a: an alias join asserts that two names are the same
    # team, so its evidence is held to the same rule as every other observation.
    # Entries without inline evidence still load — they simply render with an
    # explicit unverified marker instead of a link.
    for entry in data.get('aliases_added_this_session') or []:
        if not entry.get('alias') or not entry.get('canonical'):
            raise ValueError('every alias join needs an alias and a canonical name')
        for src in entry.get('evidence') or []:
            if not str(src.get('url', '')).startswith('https://'):
                raise ValueError('alias-join evidence must be https links')
            if not src.get('observed_at'):
                raise ValueError('alias-join evidence must carry an observation time')
    for block in data.get('model_upgrades_available') or []:
        if not block.get('sources'):
            raise ValueError('model upgrades need their evidence links')
        for src in block['sources']:
            if not str(src.get('url', '')).startswith('https://') or not src.get('observed_at'):
                raise ValueError('model upgrade sources must be https and timestamped')
    if not data.get('limitations'):
        raise ValueError('unresolved-research must publish its limitations')
    return data


def source_lines(sources):
    out = '<ul class="limitations">'
    for src in sources or []:
        detail = src.get('detail') or ''
        out += f'<li>{e(detail)} {external(src["url"], src.get("source") or "Source")}'
        if src.get('observed_at'):
            out += f' <small class="tiny">observed {e(src["observed_at"])}</small>'
        out += '</li>'
    return out + '</ul>' if sources else ''


def _quote_cell(quote):
    if not quote:
        return '<span class="unverified">no usable price — unverified</span>'
    usable = quote.get('usable_under_contract')
    mark = badge('guidance only', 'amber') if usable is False else badge('book-validated', 'green')
    values = ' · '.join(f'{e(name)} {value * 100:.1f}%' for name, value in quote.items()
                        if isinstance(value, (int, float)))
    note = f'<p class="tiny">{e(quote.get("note"))}</p>' if quote.get('note') else ''
    return (f'{mark}<p class="tiny"><strong>{e(quote.get("provider") or "quoted line")}</strong> '
            f'· observed {e(quote.get("observed_at") or "")}</p>'
            f'<p class="tiny">{values}</p>{note}')


def render_section(data: dict, prefix: str = '../') -> str:
    """Render the research dossier as one mobile-friendly page section."""
    window = data.get('research_window') or {}
    out = heading('Unresolved picks · resolution research', data['title'],
                  'Every Hotspawn CS2 match ships a pick or an explicit reason it stays blank. These are the dated '
                  'research trails behind the blanks — HLTV identity first, then verified exchange books and '
                  'bookmakers, then the Valve model. Nothing here is invented: quotes that fail the published book '
                  'contract are marked guidance only and the pick stays blank.')
    out += (f'<div class="limitations-callout"><strong>Dated research, retried automatically.</strong>'
            f'<p>Prepared {e(data.get("prepared_at") or "")} · research window {e(window.get("from") or "")} → '
            f'{e(window.get("to") or "")} · {e(data.get("prepared_by") or "")}</p>'
            f'<p>{e(data.get("policy") or "")}</p>'
            f'<div class="inline-links"><a href="{prefix}picks/">Current picks →</a>'
            f'<a href="{prefix}origination/#picks">Complete researched picks →</a>'
            f'<a href="{prefix}methodology/">How probabilities are calculated →</a>'
            f'<a href="{prefix}review/">Flagged for Review →</a></div></div>')

    out += ('<section class="content-section" id="unresolved-research"><div class="section-heading"><div>'
            '<p class="eyebrow">Research trails</p><h2>Fixture by fixture</h2></div>'
            + badge(f'{len(data["fixtures"])} fixtures', 'neutral') + '</div>'
            '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Per-fixture research '
            'trails for unresolved Hotspawn CS2 picks, with verdicts and official sources</caption><thead><tr>'
            '<th scope="col">Fixture</th><th scope="col">Checks &amp; verdicts</th>'
            '<th scope="col">Resolution status</th></tr></thead><tbody>')
    for fixture in data['fixtures']:
        teams = ' vs '.join(e(t) for t in fixture['teams'])
        checks = ['<ul class="limitations">']
        for check in fixture['checks']:
            checks.append(f'<li><strong>{e(check["stage"])}</strong> — {e(check["verdict"])}: '
                          f'{e(check.get("detail") or "")}</li>')
            checks.append(_quote_cell(check.get('guidance_quote')) if check.get('guidance_quote') else '')
            checks.append(source_lines(check.get('sources')))
        checks.append('</ul>')
        resolved = fixture['resolution'] == 'expected-at-next-refresh'
        out += ('<tr>'
                f'<th scope="row"><strong>{teams}</strong>'
                f'<small>{e(fixture.get("competition") or "")} · starts {e(fixture.get("starts_at") or "")}</small>'
                f'<small>Hotspawn {e(str(fixture.get("hotspawn_id") or ""))}</small>'
                + (f'{external(fixture["hltv_url"], "HLTV match page")}' if fixture.get('hltv_url')
                   else '<span class="unverified">HLTV row — unverified</span>') + '</th>'
                f'<td>{"".join(checks)}</td>'
                f'<td>{badge("resolution expected at next refresh", "green") if resolved else badge("stays blank", "amber")}'
                f'<p class="tiny">{e(fixture.get("resolution_detail") or "")}</p></td></tr>')
    out += '</tbody></table></div></section>'

    aliases = data.get('aliases_added_this_session') or []
    if aliases:
        out += ('<section class="content-section" id="unresolved-aliases"><div class="section-heading"><div>'
                '<p class="eyebrow">Identity registry</p><h2>Verified alias joins added</h2></div>'
                + badge(f'{len(aliases)} entries', 'purple') + '</div>'
                '<p class="section-intro">Scoped display-name joins only — each one is evidence-linked in the reviewed '
                'registry and applies solely inside the competition it declares. No sponsor-only or fuzzy join was used.</p>'
                '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Alias joins added to the '
                'reviewed identity registry</caption><thead><tr><th scope="col">Alias</th><th scope="col">Canonical</th>'
                '<th scope="col">Scoped to</th></tr></thead><tbody>')
        for entry in aliases:
            scopes = ', '.join(e(s) for s in entry.get('applies_to') or [])
            # Session arena-93c7475a: this table had never been rendered, so its
            # rows had never met the site's own row-source rule — an alias join
            # published with no official link and no unverified marker. Each row
            # now links its own registry evidence, and a join whose evidence was
            # not recorded inline is visibly marked unverified rather than
            # quietly asserting a name equivalence.
            links = ''.join(
                external(src['url'], src.get('source') or 'Registry evidence')
                + (f' <small class="tiny">observed {e(src["observed_at"])}</small>'
                   if src.get('observed_at') else '')
                for src in (entry.get('evidence') or [])
                if str(src.get('url', '')).startswith('https://'))
            if not links:
                links = '<span class="unverified">no inline registry evidence — unverified</span>'
            registry_note = (f' <a class="source-link" href="{prefix}data/origination/aliases.json">'
                             f'{e(entry.get("registry") or "reviewed alias registry")}</a>'
                             if entry.get('registry') else '')
            out += ('<tr>'
                    f'<th scope="row">{e(entry.get("alias") or "")}</th>'
                    f'<td>{e(entry.get("canonical") or "")}</td>'
                    f'<td>{scopes} {links}{registry_note}</td></tr>')
        out += '</tbody></table></div></section>'

    upgrades = data.get('model_upgrades_available') or []
    if upgrades:
        out += '<section class="content-section prose" id="unresolved-upgrades"><p class="eyebrow">Money over model</p><h2>Model upgrades queued</h2>'
        for block in upgrades:
            teams = ' vs '.join(block.get('teams') or []) or '(fixture)'
            out += (f'<p><strong>{e(teams)}</strong> — '
                    f'{e(block.get("current_estimate") or "")} · observed money line: '
                    f'{e(block.get("observed_money_line") or "")} · effect: {e(block.get("effect") or "")}</p>'
                    + source_lines(block.get('sources')))
        out += '</section>'

    out += ('<section class="content-section prose" id="unresolved-limitations"><p class="eyebrow">What stays blank and why</p>'
            '<h2>Limitations of picking these matches</h2><ul>'
            + ''.join(f'<li>{e(item)}</li>' for item in data['limitations']) + '</ul></section>')
    return out
