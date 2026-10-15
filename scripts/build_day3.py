"""Render the dated Day-2-results / Day-3-guide section from data/day3-guide.json.

Same contract as the Day-1 upset review (scripts/build_edge.py): dated
first-party research with an official source link and observation time on
every row, never a pricing input for the automated pipeline, and no
probability for a fixture whose market had no traded price at observation.

Usage: python -m scripts.build_day3 [--source data]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.domain import timestamp
from scripts.validate import require

DAY3_SCHEMA = 1
REQUIRED_KEYS = ['schema_version', 'title', 'prepared_at', 'research_window', 'policy',
                 'event', 'day_two_results', 'standings_after_day_two', 'day_three', 'limitations']


def load_day3(path: Path) -> dict:
    data = json.loads(Path(path).read_text())
    for key in REQUIRED_KEYS:
        require(key in data, f'day3-guide.json is missing {key!r}')
    require(data['schema_version'] == DAY3_SCHEMA, 'Unsupported day3-guide schema')
    require(timestamp(data['prepared_at']) is not None, 'day3-guide.json needs a prepared_at timestamp')
    window = data['research_window']
    require(timestamp(window.get('from')) is not None and timestamp(window.get('to')) is not None,
            'day3-guide.json needs a research window with both ends')
    for group in ['day_two_results', 'standings_after_day_two', 'day_three', 'limitations']:
        require(isinstance(data[group], list) and data[group], f'day3-guide.json {group} must be a non-empty list')
    for row in data['day_two_results'] + data['day_three']:
        require(row.get('sources'), 'every Day-2/Day-3 row needs at least one official source link')
        for src in row['sources']:
            require(str(src.get('url', '')).startswith('https://'), 'day3-guide sources must be https links')
            require(src.get('observed_at'), 'day3-guide sources must carry an observation time')
    for row in data['day_two_results']:
        require(row.get('score') and row.get('maps'), 'every Day-2 result needs a series score and map scores')
    for row in data['day_three']:
        require(row.get('guidance'), 'every Day-3 fixture needs pick guidance text')
        market = row.get('market') or {}
        prices = market.get('prices')
        if prices is None:
            require(row.get('primary_pick') is None, 'an unpriced fixture cannot carry a priced primary pick')
        else:
            require(set(prices) == {row['team_a'], row['team_b']}, 'Day-3 prices must cover both teams exactly')
            require(abs(sum(prices.values()) - 1) < 0.02, 'Day-3 provider prices must sum to ~100%')
            require(row.get('primary_pick') in prices, 'Day-3 primary pick must be one of the priced teams')
    return data


def render_section(guide: dict, prefix: str) -> str:
    # Imported lazily to avoid a circular import with scripts.build_edge,
    # which reuses the same table/badge helpers from scripts.build.
    from scripts.build import badge, e, external, local_time
    from scripts.build_edge import maps_text, source_lines

    out = ['<section class="content-section" id="day-two-results"><div class="section-heading"><div>'
           '<p class="eyebrow">Day 2 · verified results</p><h2>Day two: every series, every map</h2></div>'
           + badge('HLTV verified', 'green') + '</div>',
           '<p class="section-intro">All four Day 2 series went three maps except Aurora\'s elimination win. '
           'Falcons and FURIA won their groups; NiP and PARIVISION are out. Map scores below are HLTV\'s '
           'published values for these specific series.</p>',
           '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-two results at '
           'Thunderpick World Championship 2026 with official source links</caption><thead><tr>'
           '<th scope="col">Series</th><th scope="col">Score &amp; maps</th>'
           '<th scope="col">What the result actually said</th></tr></thead><tbody>']
    for row in guide['day_two_results']:
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} {e(row["score"])} {e(row["team_b"])}</strong>'
                   f'<small>15 Oct 2026 · {e(row["slot"])} · bo3</small></th>'
                   f'<td>{maps_text(row)}<small>Series {e(row["score"])}</small></td>'
                   f'<td><p>{e(row["read"])}</p>{source_lines(row["sources"])}'
                   f'{external(row["url"], "HLTV match page")}</td></tr>')
    out.append('</tbody></table></div>')
    out.append('<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Group standings '
               'after day two</caption><thead><tr><th scope="col">Group</th><th scope="col">Team</th>'
               '<th scope="col">Record</th><th scope="col">Status</th></tr></thead><tbody>')
    for row in guide['standings_after_day_two']:
        out.append(f'<tr><th scope="row">{e(row["group"])}</th><td><strong>{e(row["team"])}</strong></td>'
                   f'<td>{e(row["record"])}</td><td>{e(row["status"])}</td></tr>')
    out.append('</tbody></table></div></section>')

    out.append('<section class="content-section" id="day-three-guide"><div class="section-heading"><div>'
               '<p class="eyebrow">Day 3 · 16 Oct 2026 · deciders · updated priced guide</p><h2>Day three pick guide</h2></div>'
               f'<a class="internal-link" href="{prefix}picks/">Open the full picks list →</a></div>'
               '<p class="section-intro">Two deciders, two semi-final slots. The calculated probabilities for '
               'these fixtures — once the four-hour pipeline joins them — live on the '
               f'<a href="{prefix}picks/">match picks page</a> and in the '
               f'<a href="{prefix}origination/#picks">complete researched picks list</a>. '
               'Guidance below is pick\'em strategy from the verified Day 1–2 evidence; it never overwrites '
               'those probabilities. This priced update (prepared ' + local_time(guide['prepared_at']) + ') supersedes '
               'the unpriced day-three preview above wherever start times or prices differ.</p>'
               '<div class="table-scroll"><table class="simple-table"><caption class="sr-only">Day-three '
               'decider fixtures with observed market prices, guidance and official sources</caption>'
               '<thead><tr><th scope="col">Fixture &amp; start (UTC)</th>'
               '<th scope="col">Observed market price</th><th scope="col">Guidance</th></tr></thead><tbody>')
    for row in guide['day_three']:
        market = row.get('market') or {}
        prices = market.get('prices')
        if prices:
            price_rows = ''.join(
                f'<div class="prob-line"><span>{e(name)}</span><strong>{value * 100:.1f}%</strong></div>'
                for name, value in prices.items())
            observed = (f'<small>{e(market.get("provider") or "Provider")} · observed '
                        f'{local_time(market["observed_at"])}</small>') if market.get('observed_at') else ''
            note = f'<p class="tiny">{e(market["note"])}</p>' if market.get('note') else ''
            price_cell = price_rows + observed + note
        else:
            price_cell = ('<strong class="unresolved-text">— unverified</strong>'
                          '<p class="tiny">No traded price at observation; no probability is published '
                          'for this fixture.</p>'
                          + (f'<p class="tiny">{e(market["note"])}</p>' if market.get('note') else ''))
        links = ''.join(external(url, label) for url, label in
                        [(market.get('event_url'), 'Polymarket event'), (market.get('api_url'), 'Gamma record')] if url)
        primary = (f'<p><strong>Primary:</strong> {e(row["primary_pick"])}</p>' if row.get('primary_pick')
                   else '<p><strong>Primary:</strong> — <small>awaiting a priced line</small></p>')
        contrarian = (f'<p><strong>Contrarian candidate:</strong> {e(row["contrarian_candidate"])}</p>'
                      if row.get('contrarian_candidate')
                      else '<p><strong>Contrarian candidate:</strong> none designated</p>')
        out.append('<tr>'
                   f'<th scope="row"><strong>{e(row["team_a"])} vs {e(row["team_b"])}</strong>'
                   f'<small>{e(row["slot"])}</small>'
                   f'<small>Start {local_time(row["starts_at"])} · {e(row.get("best_of") or "bo unverified")}</small>'
                   f'<small>HLTV match {e(row["hltv_match_id"])}</small></th>'
                   f'<td>{price_cell}<div class="evidence-links">{links}</div></td>'
                   f'<td>{primary}{contrarian}<p>{e(row["guidance"])}</p>'
                   f'{source_lines(row["sources"])}{external(row["hltv_url"], "HLTV match page")}</td></tr>')
    out.append('</tbody></table></div>')
    out.append('<div class="limitations-callout"><strong>How to climb without gambling the card</strong>'
               '<p>One designated contrarian flip (9z) backed by a head-to-head win over this exact '
               'opponent two days ago — not a blanket fade of both favorites. The second decider has no '
               'priced line yet, so it gets a labeled form lean and a pointer to the live picks page '
               'instead of an invented number.</p>'
               f'<div class="inline-links"><a href="{prefix}origination/#picks">Complete researched picks →</a>'
               f'<a href="{prefix}edge/#day-two-results">Day 2 results ↑</a>'
               f'<a href="{prefix}review/">Flagged for Review →</a></div></div>')
    out.append('<div class="limitations-callout"><strong>Day-3 limitations</strong><ul>'
               + ''.join(f'<li>{e(x)}</li>' for x in guide['limitations']) + '</ul></div>')
    out.append('</section>')
    return ''.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data'))
    args = parser.parse_args()
    guide = load_day3(args.source / 'day3-guide.json')
    print(f"PASS: day3-guide validated: {len(guide['day_two_results'])} Day-2 results, "
          f"{len(guide['day_three'])} Day-3 fixtures.")


if __name__ == '__main__':
    main()
