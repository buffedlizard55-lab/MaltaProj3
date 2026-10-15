"""Render the dated 'Upset review & contrarian edge' page from data/edge-review.json.

This page is deliberately separate from the automated picks pipeline:

* it publishes a *dated* first-party research review (day-one results, roster
  changes, market observations) where every displayed value carries its own
  official source link and observation time,
* it never overwrites a featured or researched estimate produced by
  ``scripts.collect`` / ``scripts.originate``,
* anything that could not be confirmed from an official source renders as
  '— unverified' instead of being inferred,
* Hotspawn community percentages are never read, so no crowd-fade advice is
  produced; 'contrarian' here means disagreeing with the external market or
  ranking consensus only when verified evidence supports it.

Usage: python -m scripts.build_edge [--source data] [--output site]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.build import PAGES, badge, blank, e, external, heading, icon, local_time
from scripts.domain import timestamp
from scripts.validate import require

EDGE_SCHEMA = 1
REQUIRED_KEYS = ['schema_version', 'title', 'prepared_at', 'research_window', 'policy',
                 'event', 'headline', 'day_one', 'roster_watch', 'edge_rules', 'day_two', 'limitations']


def load_edge(path: Path) -> dict:
    data = json.loads(path.read_text())
    for key in REQUIRED_KEYS:
        require(key in data, f'edge-review.json is missing {key!r}')
    require(data['schema_version'] == EDGE_SCHEMA, 'Unsupported edge-review schema')
    for key in ['prepared_at', 'research_window']:
        pass
    require(timestamp(data['prepared_at']) is not None, 'edge-review.json needs a prepared_at timestamp')
    window = data['research_window']
    require(timestamp(window.get('from')) is not None and timestamp(window.get('to')) is not None,
            'edge-review.json needs a research window with both ends')
    for group in ['day_one', 'day_two', 'roster_watch', 'edge_rules']:
        require(isinstance(data[group], list), f'edge-review.json {group} must be a list')
    if 'day_three' in data:
        require(isinstance(data['day_three'], list), 'edge-review.json day_three must be a list')
        for row in data['day_three']:
            require(row.get('sources'), 'every reviewed match needs at least one official source link')
            for src in row['sources']:
                require(str(src.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
                require(src.get('observed_at'), 'edge-review sources must carry an observation time')
    for row in data['day_one'] + data['day_two']:
        require(row.get('sources'), 'every reviewed match needs at least one official source link')
        for src in row['sources']:
            require(str(src.get('url', '')).startswith('https://'), 'edge-review sources must be https links')
            require(src.get('observed_at'), 'edge-review sources must carry an observation time')
    for rule in data['edge_rules']:
        require(rule.get('id') and rule.get('title') and rule.get('body'), 'every edge rule needs id, title and body')
        require(rule.get('sources'), 'every edge rule needs its evidence links')
    return data


def source_list(sources, prefix=''):
    out = '<div class="evidence-links">'
    for src in sources:
        label = src.get('source') or 'Source'
        observed = src.get('observed_at')
        stamp = f' <small>observed {e(observed)}</small>' if observed else ''
        out += external(src['url'], label) if not stamp else external(src['url'], label)
    out += '</div>'
    return out


def source_lines(sources):
    out = '<ul class="limitations">'
    for src in sources:
        detail = src.get('detail') or ''
        out += f'<li>{e(detail)} {external(src["url"], src.get("source") or "Source")}'
        if src.get('observed_at'):
            out += f' <span class="tiny muted">observed {local_time(src["observed_at"])}</span>'
        out += '</li>'
    return out + '</ul>'


def maps_text(row):
    maps = row.get('maps') or []
    if not maps:
        return blank()
    return e(' · '.join(f'{m["map"]} {m["a"]}-{m["b"]}' for m in maps))


def day_one_section(data):
    out = ['<section class="content-section" id="day-one"><div class="section-heading"><div>'
           '<p class="eyebrow">Official results, not recollections</p><h2>Day one: every series, every map</h2></div>'
           + badge('HLTV verified', 'green') + '</div>',
           '<p class="section-intro">Four series, four 2-0 scorelines — and only one of them was the result the rankings '
           'implied. Map scores, standout ratings and lineups below are HLTV’s published values for these specific series.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-one results at Thunderpick '
           'World Championship 2026 with official source links</caption><thead><tr><th scope="col">Series</th>'
           '<th scope="col">Score &amp; maps</th><th scope="col">What the result actually said</th></tr></thead><tbody>']
    for row in data['day_one']:
        flag = badge('Upset', 'amber') if row.get('upset') else badge('Favorite won', 'neutral')
        lineup = ''
        for key, label in [('verified_lineup_a', row['team_a']), ('verified_lineup_b', row['team_b'])]:
            values = row.get(key)
            lineup += f'<p class="tiny"><strong>{e(label)}</strong>: ' + (e(', '.join(values)) if values else '— <small>unverified</small>') + '</p>'
        standout = f'<p class="tiny"><strong>Standout</strong>: {e(row["standout"])}</p>' if row.get('standout') else ''
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} {e(row["score"])} {e(row["team_b"])}</strong>'
                   f'<small>{e(row["date"])} · {e(row["group"])} · {e(row.get("best_of") or "bo unverified")} {flag}</small></th>'
                   f'<td>{maps_text(row)}<small>Series {e(row["score"])}</small></td>'
                   f'<td><p>{e(row["read"])}</p>{lineup}{standout}{source_lines(row["sources"])}'
                   f'{external(row["url"], "HLTV match page")}</td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def roster_section(data):
    out = ['<section class="content-section" id="rosters"><div class="section-heading"><div>'
           '<p class="eyebrow">Roster changes, onboarding and rest</p><h2>Who changed, and what it costs them</h2></div>'
           + badge('Official transfer news', 'green') + '</div>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Verified roster changes and '
           'lineup continuity for the reviewed teams</caption><thead><tr><th scope="col">Team</th>'
           '<th scope="col">Verified lineup &amp; ranking</th><th scope="col">Change and what it means</th>'
           '</tr></thead><tbody>']
    for row in data['roster_watch']:
        lineup = e(', '.join(row['current_lineup'])) if row.get('current_lineup') else '— <small>unverified</small>'
        coach = e(row['coach']) if row.get('coach') else '— <small>unverified</small>'
        ranks = e(row['rankings']) if row.get('rankings') else '— <small>unverified</small>'
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team"])}</strong><small>{badge(row["status"], "amber" if "not verified" in row["status"] or "Rebuilt" in row["status"] else "green")}</small></th>'
                   f'<td><p><strong>Lineup</strong>: {lineup}</p><p class="tiny"><strong>Coach</strong>: {coach}</p>'
                   f'<p class="tiny"><strong>Rankings</strong>: {ranks}</p>'
                   f'{external(row["url"], "HLTV team page")}</td>'
                   f'<td><p>{e(row["change"])}</p><p class="tiny"><strong>So what:</strong> {e(row["so_what"])}</p>'
                   + valve_snapshot_note(row.get('valve_snapshot')) +
                   f'{source_lines(row["sources"])}</td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def rules_section(data):
    out = ['<section class="content-section resolution-steps" id="rules"><div class="section-heading"><div>'
           '<p class="eyebrow">Contrarian, but not stupid</p><h2>The seven rules this review applies</h2></div>'
           + badge('Evidence required', 'neutral') + '</div>']
    for rule in data['edge_rules']:
        out.append(f'<article class="resolution-step"><span>{e(rule["id"])}</span><div><h2>{e(rule["title"])}</h2>'
                   f'<p>{e(rule["body"])}</p>')
        if rule.get('sources'):
            out.append('<div class="evidence-links">' + ''.join(external(s['url'], s.get('source') or 'Source') for s in rule['sources']) + '</div>')
        out.append('</div></article>')
    out.append('</section>')
    return ''.join(out)


def day_two_section(data, inventory):
    by_id = {str(m['id']): m for m in inventory.get('matches', [])}
    out = ['<section class="content-section" id="day-two"><div class="section-heading"><div>'
           '<p class="eyebrow">Applying the review to the current card</p><h2>Day two: lines, reads and confidence</h2></div>'
           '<a class="internal-link" href="../picks/">Open the full picks list →</a></div>',
           '<p class="section-intro">Provider prices below are dated observations from Polymarket’s official Gamma record, '
           'shown as context. The current calculated estimates for these fixtures live on the '
           '<a href="../picks/">match picks page</a> and in the '
           '<a href="../origination/#picks">complete researched picks list</a>.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-two fixtures with observed '
           'market prices, assessment and official sources</caption><thead><tr><th scope="col">Fixture &amp; start</th>'
           '<th scope="col">Observed market price</th><th scope="col">Review read</th></tr></thead><tbody>']
    for row in data['day_two']:
        fixture = by_id.get(str(row['hotspawn_id']))
        hotspawn_link = external(fixture['source_url'], 'Hotspawn fixture') if fixture else '<span class="unverified">— <small>Hotspawn row not in this snapshot</small></span>'
        lock = f'<small>Pick lock {local_time(fixture["locks_at"])}</small>' if fixture and fixture.get('locks_at') else '<small>Pick lock — <small>unverified</small></small>'
        market = row.get('market') or {}
        prices = market.get('prices') or {}
        price_rows = ''.join(f'<div class="prob-line"><span>{e(name)}</span><strong>{value * 100:.1f}%</strong></div>'
                             for name, value in prices.items()) or blank()
        observed = f'<small>{e(market.get("provider") or "Provider")} · observed {local_time(market["observed_at"])}</small>' if market.get('observed_at') else ''
        state = badge('Market open' if market.get('market_open') else 'Market closed', 'green' if market.get('market_open') else 'amber')
        note = f'<p class="tiny">{e(market["note"])}</p>' if market.get('note') else ''
        links = ''.join(external(url, label) for url, label in
                        [(market.get('event_url'), 'Polymarket event'), (market.get('api_url'), 'Gamma record')] if url)
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["competition"])} · {e(row["slot"])}</small>'
                   f'<small>Start {local_time(row["starts_at"])}</small>{lock}'
                   f'<small>Hotspawn ID {e(row["hotspawn_id"])} · HLTV match {e(row["hltv_match_id"])}</small></th>'
                   f'<td>{price_rows}{observed}{state}{note}<div class="evidence-links">{links}</div></td>'
                   f'<td><p>{e(row["assessment"])}</p><p class="tiny"><strong>Status at observation:</strong> {e(row["status_at_observation"])}</p>'
                   f'{source_lines(row["sources"])}{external(row["hltv_url"], "HLTV match page")}'
                   f'<div class="evidence-links">{hotspawn_link}</div></td></tr>')
    out.append('</tbody></table></div>')
    discrepancy = data.get('time_discrepancy')
    if discrepancy:
        out.append('<div class="limitations-callout"><strong>Start-time discrepancy, recorded not smoothed</strong>'
                   f'<p>{e(discrepancy["detail"])}</p><div class="inline-links">'
                   + ''.join(external(s['url'], s.get('source') or 'Source') for s in discrepancy.get('sources', []))
                   + '</div></div>')
    out.append('</section>')
    return ''.join(out)

def day_three_section(data, inventory):
    out = ['<section class="content-section" id="day-three"><div class="section-heading"><div>'
           '<p class="eyebrow">Looking ahead to day three</p><h2>Day three: elimination matches and what day two changed</h2></div>'
           + badge('HLTV schedule', 'green') + '</div>',
           '<p class="section-intro">These fixtures are not in the Hotspawn scheduled-fixture feed captured on 14 Oct 2026, '
           'so no Hotspawn link or pick is produced for them. Market prices were not captured in this window and are left '
           'unpriced rather than estimated. Assessments below rest only on the verified day-one and day-two results above.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-three elimination fixtures '
           'with HLTV links and review reads</caption><thead><tr><th scope="col">Fixture &amp; start</th>'
           '<th scope="col">Observed market price</th><th scope="col">Review read</th></tr></thead><tbody>']
    for row in data.get('day_three', []):
        market = row.get('market') or {}
        prices = market.get('prices') or {}
        price_rows = ''.join(f'<div class="prob-line"><span>{e(name)}</span><strong>{value * 100:.1f}%</strong></div>'
                             for name, value in prices.items()) or blank()
        observed = f'<small>{e(market.get("provider") or "Provider")} · observed {local_time(market["observed_at"])}</small>' if market.get('observed_at') else '<small>— unverified (not captured)</small>'
        links = ''.join(external(url, label) for url, label in
                        [(market.get('event_url'), 'Polymarket event'), (market.get('api_url'), 'Gamma record')] if url)
        hotspawn_link = '<span class="unverified">— <small>Hotspawn row not in this snapshot</small></span>'
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["competition"])} · {e(row["slot"])}</small>'
                   f'<small>Start {local_time(row["starts_at"])}</small>'
                   f'<small>HLTV match {e(row["hltv_match_id"])}</small></th>'
                   f'<td>{price_rows}{observed}<div class="evidence-links">{links}</div></td>'
                   f'<td><p>{e(row["assessment"])}</p><p class="tiny"><strong>Status at observation:</strong> {e(row["status_at_observation"])}</p>'
                   f'{source_lines(row["sources"])}{external(row["hltv_url"], "HLTV match page")}'
                   f'<div class="evidence-links">{hotspawn_link}</div></td></tr>')
    out.append('</tbody></table></div></section>')
    return ''.join(out)


def valve_snapshot_note(snapshot):
    if not snapshot:
        return ''
    roster = ', '.join(snapshot.get('roster') or []) or '— unverified'
    return ('<div class="evidence-box"><p class="eyebrow">Official rating snapshot</p>'
            f'<p class="tiny"><strong>Valve standings {e(snapshot.get("snapshot_date") or "undated")}</strong>: '
            f'#{e(snapshot.get("standing"))} · {e(snapshot.get("points"))} points · {e(roster)}</p>'
            f'<p class="tiny">{e(snapshot.get("caveat") or "")}</p>'
            f'{external(snapshot["source_url"], "Valve official standings")}</div>')


def saved_evidence_link(evidence_file: str, data_dir) -> str:
    """Link the saved evidence file only if this snapshot actually has it; otherwise say so (blank and flagged)."""
    if data_dir is not None and not (Path(data_dir) / str(evidence_file).removeprefix('data/')).exists():
        return '<span class="unverified">saved evidence file not present in this snapshot (the Valve source was unreachable) — unverified</span>'
    return f'<a href="../{e(evidence_file)}">Saved first-party evidence ↓</a>'


def standings_section(data, data_dir=None):
    block = data.get('valve_standings')
    if not block or not block.get('rows'):
        return ''
    out = ['<section class="content-section" id="standings"><div class="section-heading"><div>'
           '<p class="eyebrow">Official rating inputs</p><h2>Valve standings for the day-two field</h2></div>'
           + badge('Valve snapshot ' + str(block.get('snapshot_date') or ''), 'purple') + '</div>',
           f'<p class="section-intro">{e(block["note"])}</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Valve regional standings '
           'snapshot for the day-two teams, with rosters and official source</caption><thead><tr>'
           '<th scope="col">Team</th><th scope="col">Standing &amp; points</th><th scope="col">Published roster</th>'
           '</tr></thead><tbody>']
    for row in block['rows']:
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["name"])}</strong><small>Snapshot {e(row["snapshot_date"])}</small></th>'
                   f'<td>#{e(row["standing"])}<small>{e(row["points"])} points</small></td>'
                   f'<td>{e(", ".join(row["roster"]))}{external(row["source_url"], "Valve record")}</td></tr>')
    out.append('</tbody></table></div><div class="inline-links downloads">'
               + external(block['source_url'], 'Valve official standings')
               + saved_evidence_link(block.get('evidence_file', 'data/evidence/valve-ratings.json'), data_dir)
               + '</div></section>')
    return ''.join(out)


def edge_review(data, prefix, edge_path: Path):
    review = load_edge(edge_path)
    window = review['research_window']
    out = heading('Dated first-party research', review['title'],
                  'What day one at Thunderpick World Championship 2026 actually told us — the 9z upset over Aurora, the roster '
                  'churn behind it, and the rules we apply before disagreeing with a market.')
    out += ('<div class="limitations-callout"><strong>This review is dated research, not a live feed.</strong>'
            f'<p>Prepared {local_time(review["prepared_at"])}. Research window {local_time(window["from"])} → {local_time(window["to"])}. '
            'Market prices on this page are historical observations with their own timestamps. Current probabilities stay on the '
            f'<a href="{prefix}picks/">match picks page</a>. {e(review["policy"])}</p>'
            f'<div class="inline-links"><a href="{prefix}picks/">Current picks →</a>'
            f'<a href="{prefix}origination/#picks">Complete researched picks →</a>'
            f'<a href="{prefix}review/">Flagged for Review →</a></div></div>')
    out += ('<section class="content-section"><div class="section-heading"><div><p class="eyebrow">The upset</p>'
            '<h2>9z 2-0 Aurora</h2></div>' + badge('Day one · Group A', 'amber') + '</div>'
            f'<div class="prose"><p>{e(review["headline"]["text"])}</p>{source_lines(review["headline"]["sources"])}'
            f'<p class="tiny">{e(review["event"]["name"])} · {e(review["event"]["dates"])} · {e(review["event"]["location"])} · '
            f'{e(review["event"]["teams"])} teams · {external(review["event"]["url"], "HLTV event page")}</p>'
            f'<p class="tiny">{e(review["event"]["format_note"])}</p></div></section>')
    out += day_one_section(review)
    out += roster_section(review)
    out += rules_section(review)
    out += day_two_section(review, data)
    out += day_three_section(review, data)
    day3_path = edge_path.parent / 'day3-guide.json'
    if day3_path.exists():
        from scripts.build_day3 import load_day3, render_section
        out += render_section(load_day3(day3_path), prefix)
    out += standings_section(review, edge_path.parent)
    out += ('<section class="content-section prose" id="edge-limitations"><p class="eyebrow">What this review cannot tell you</p>'
            '<h2>Limitations</h2><ul>' + ''.join(f'<li>{e(x)}</li>' for x in review['limitations']) + '</ul>'
            f'<p>{external("https://www.hltv.org/results?event=8932", "HLTV official event results")} '
            f'{external("https://docs.polymarket.com/api-reference/market-data/get-order-book", "Polymarket official market-data contract")} '
            f'<a href="{prefix}methodology/">How current probabilities are calculated →</a></p></section>')
    return out


def build(source: Path, output: Path):
    data = json.loads((source / 'latest.json').read_text())
    review = load_edge(source / 'edge-review.json')
    target = output / 'edge'
    target.mkdir(parents=True, exist_ok=True)
    body = edge_review(data, '../', source / 'edge-review.json')
    from scripts.build import shell
    (target / 'index.html').write_text(shell(data, 'edge', body, '../'))
    return target / 'index.html', review


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('site'))
    args = parser.parse_args()
    path, review = build(args.source, args.output)
    print(f'Built {path} · {len(review["day_one"])} day-one series · {len(review["day_two"])} day-two fixtures · {len(review.get("day_three", []))} day-three fixtures reviewed')
