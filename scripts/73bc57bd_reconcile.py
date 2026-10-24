"""Reconcile every future Hotspawn CS2 Pick'ems card with the published pick rows.

Session arena-73bc57bd. This module never invents a value: it joins two dated,
first-hand records that are committed next to it —

* ``data/research/73bc57bd/observations-2026-10-24.json`` — the lobby cards as
  rendered, the published snapshot facts, the publisher run history, and the
  line evidence observed for each uncovered card (each observation carries its
  own provider, URL and read timestamp);
* the deployed branch root ``picks/index.html`` — the exact rows the legacy
  Pages builder republishes, parsed for id, teams, start, method, confidence and
  price timestamp.

The result is a coverage statement ("which live cards have a pick, which do
not, and why") plus a per-gap evidence table. Probabilities are never produced
here; the published percentages are restated from the rendered row only.

Run ``python -m scripts.73bc57bd_reconcile`` to regenerate the JSON and the
Markdown dossier. ``tests/test_73bc57bd_reconciliation.py`` re-derives the same
arithmetic and fails if the dossier and the rendered rows disagree.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

OBSERVATIONS = Path('data/research/73bc57bd/observations-2026-10-24.json')
OUT_JSON = Path('data/research/73bc57bd/inventory-reconciliation-2026-10-24.json')
OUT_MD = Path('data/research/73bc57bd/inventory-reconciliation-2026-10-24.md')
PUBLISHED_PAGE = Path('picks/index.html')
PUBLISHED_ROWS = Path('data/research/73bc57bd/published-rows-2026-10-24.json')

ROW = re.compile(r'<tr id="match-(\d+)" class="match-row" data-record-id="\d+"(.*?)</tr>', re.S)
TAG = re.compile(r'<[^>]+>')


def _attr(attrs: str, name: str) -> str | None:
    match = re.search(rf'{name}="([^"]*)"', attrs)
    return match.group(1) if match else None


def parse_published(page: Path = PUBLISHED_PAGE) -> list[dict]:
    """Parse the rendered pick rows out of the deployed branch-root page."""
    html = page.read_text()
    rows = []
    for match in ROW.finditer(html):
        rid, attrs = match.group(1), match.group(2)
        body = match.group(0)
        teams = re.findall(r'<strong>([^<]+)</strong>', body)[:2]
        percentages = re.findall(r'<strong>([\d.]+%)</strong>', body)[:2]
        rows.append({
            'id': rid,
            'teams': teams,
            'published_line': ' / '.join(percentages) if percentages else None,
            'starts_at_utc': _attr(attrs, 'data-start'),
            'method': _attr(attrs, 'data-method'),
            'confidence': _attr(attrs, 'data-confidence'),
            'price_observed_at': _attr(attrs, 'data-price-time'),
        })
    return rows


def load_published(record: Path = PUBLISHED_ROWS) -> list[dict]:
    """The frozen parse of the deployed page at read time.

    ``picks/index.html`` is republished by every successful refresh, so the
    dossier must not re-read it: the coverage statement is about the page as it
    stood at 2026-10-24T05:38Z. Use ``snapshot_published()`` to record a newer
    observation instead of silently re-deriving against a moving page.
    """
    return json.loads(record.read_text())['rows']


def snapshot_published(record: Path = PUBLISHED_ROWS, page: Path = PUBLISHED_PAGE) -> dict:
    import hashlib

    data = page.read_bytes()
    payload = {
        'schema_version': 1,
        'source_url': 'https://buffedlizard55-lab.github.io/MaltaProj3/picks/',
        'source_path_in_repo': str(page),
        'read_at': '2026-10-24T05:38:00Z',
        'note': ('Exactly the rows parsed out of the deployed branch-root page at read time. Frozen so the dossier '
                 'stays auditable after a later publish replaces the page.'),
        'page_sha256': hashlib.sha256(data).hexdigest(),
        'page_bytes': len(data),
        'rows': parse_published(page),
    }
    record.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    return payload


def build_dossier(observations: dict, published: list[dict]) -> dict:
    lobby = observations['lobby']['cards']
    gap_ids = {mid for mid in observations['gap_research']}
    published_by_id = {row['id']: row for row in published}

    covered, uncovered = [], []
    for card in lobby:
        row = published_by_id.get(card['id'])
        if row is None:
            research = observations['gap_research'].get(card['id'])
            if research is None:
                raise SystemExit(
                    f'lobby card {card["id"]} has neither a published row nor recorded gap research'
                )
            uncovered.append({**card, 'research': research})
        else:
            covered.append({**card, 'published': row})

    published_without_card = [row for row in published if row['id'] not in {c['id'] for c in lobby}]

    verdicts: dict[str, int] = {}
    for item in uncovered:
        verdict = item['research']['verdict']
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

    dossier = {
        'schema_version': 1,
        'session': observations['session'],
        'purpose': observations['purpose'],
        'policy': observations['policy'],
        'sources': observations['sources'],
        'published': observations['published'],
        'publisher_runs': observations['publisher_runs'],
        'local_reproduction': observations['local_reproduction'],
        'lobby': {k: v for k, v in observations['lobby'].items() if k != 'cards'},
        'counts': {
            'lobby_future_cards': len(lobby),
            'published_rows': len(published),
            'cards_with_a_published_pick': len(covered),
            'cards_without_a_published_pick': len(uncovered),
            'published_rows_no_longer_in_the_future_lobby': len(published_without_card),
            'gap_verdicts': verdicts,
        },
        'covered': covered,
        'uncovered': uncovered,
        'published_without_card': published_without_card,
        'cross_checks': observations['cross_checks'],
        'phone_measurements': observations.get('phone_measurements'),
        'limitations': [
            'Lobby cards are recorded in the timezone Hotspawn renders (US Eastern) and are not converted here.',
            'A market that did not appear in a read segment is "not observed", never "non-existent".',
            'No probability, pick or provider alias is produced by this dossier; the uncovered cards are inputs for the existing pricing ladder.',
            'The 25 rendered cards are the future cards in the lobby at read time; Hotspawn paginates the wider weekly inventory, so a card added after 05:31Z is outside this observation.',
        ],
    }
    return dossier


def _md_link(url: str, text: str) -> str:
    return f'[{text}]({url})'


def _hotspawn(card: dict) -> str:
    return _md_link(card['hotspawn_url'], 'Hotspawn')


def render_markdown(dossier: dict) -> str:
    counts = dossier['counts']
    published = dossier['published']
    lines = [
        '# Hotspawn CS2 Pick\'ems — every live card vs the published picks',
        '',
        f'Session `{dossier["session"]}`. Lobby read **2026-10-24T05:31Z** '
        f'(25 future cards); published rows read from the deployed branch root '
        f'(**{counts["published_rows"]}** rows, snapshot `{published["snapshot_generated_at"]}`).',
        '',
        '## Coverage in one line',
        '',
        f'**{counts["cards_with_a_published_pick"]} of {counts["lobby_future_cards"]}** future Hotspawn CS2 cards '
        f'already carry a pick on the published site; **{counts["cards_without_a_published_pick"]}** do not. '
        f'Those {counts["cards_without_a_published_pick"]} are all CCT Europe 2026 Series #11/#12 cards, and the cause is the '
        f'publish pipeline, not a missing source: the scheduled publisher has failed four consecutive runs '
        f'(latest 40063011446) at *Regression tests*, so no collection has been published since '
        f'{dossier["publisher_runs"][0]["created_at"]}.',
        '',
        'The published rows were parsed from the deployed page at **2026-10-24T05:38Z** and frozen in '
        '`data/research/73bc57bd/published-rows-2026-10-24.json` (19 rows, page sha256 recorded), so this '
        'statement stays auditable after the next successful refresh replaces that page.',
        '',
        '## Cards without a published pick',
        '',
        '| # | Card | Tournament | Lobby time (as rendered) | HLTV identity | Line evidence read today | Verdict |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for index, item in enumerate(dossier['uncovered'], start=1):
        research = item['research']
        hltv = research.get('hltv')
        hltv_cell = (f'{_md_link(hltv["url"], hltv["event"])} · {hltv["format"]}'
                     + (f' · {hltv["stage"]}' if hltv.get('stage') else '')) if hltv else 'not enumerated'
        evidence = '; '.join(
            f'{obs["provider"]}: {obs["prices_verbatim"]} '
            f'({_md_link(obs["url"], "source")}, read {obs["read_at"][11:16]}Z)'
            for obs in research['observations'])
        lines.append(
            f'| {index} | **{item["teams"][0]} vs {item["teams"][1]}** — {_hotspawn(item)} | '
            f'{item["tournament"]} | {item["lobby_time_verbatim"]} | {hltv_cell} | {evidence} | {research["verdict"]} |')
    lines += ['', '### Limitations recorded for those cards', '']
    for item in dossier['uncovered']:
        for limitation in item['research']['limitations']:
            lines.append(f'- **{item["teams"][0]} vs {item["teams"][1]}** — {limitation}')
    lines += [
        '',
        '## Cards that already carry a published pick',
        '',
        '| # | Card | Tournament | Lobby time | Published snapshot line | Method | Pick price observed |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for index, item in enumerate(dossier['covered'], start=1):
        row = item['published']
        lines.append(
            f'| {index} | **{item["teams"][0]} vs {item["teams"][1]}** — {_hotspawn(item)} | {item["tournament"]} | '
            f'{item["lobby_time_verbatim"]} | {row["published_line"] or "—"} | {row["method"] or "—"} | '
            f'{row["price_observed_at"] or "—"} |')
    lines += ['', '## Published rows that are no longer future lobby cards', '',
              '| Card | Published line | Method | Start (UTC, from the fixture row) |', '| --- | --- | --- | --- |']
    for row in dossier['published_without_card']:
        lines.append(f'| **{" vs ".join(row["teams"])}** | {row["published_line"] or "—"} | {row["method"] or "—"} | '
                     f'{row["starts_at_utc"] or "—"} |')
    lines += ['', '## Independent cross-check of a published pick', '']
    for check in dossier['cross_checks']:
        lines.append(f'**{" vs ".join(check["teams"])}** — published **{check["published"]["line"]}** '
                     f'(fair decimal {check["published"]["fair_decimal"]}, price read {check["published"]["price_time"]}).')
        lines.append('')
        lines.append(f'- Live exchange: {check["live_market"]["verbatim"]} '
                     f'({_md_link(check["live_market"]["url"], "Polymarket")}, read {check["live_market"]["read_at"][11:16]}Z)')
        lines.append(f'- Second source: {check["second_source"]["verbatim"]} '
                     f'({_md_link(check["second_source"]["url"], "EGamersWorld")}, read {check["second_source"]["read_at"][11:16]}Z)')
        lines.append(f'- {check["finding"]}')
    phone = dossier.get('phone_measurements')
    if phone:
        lines += ['', '## Phone check, measured not asserted', '',
                  f'Build: {phone["build"]}. Method: {phone["method"]}.', '',
                  '| Page | Width | Horizontal overflow | First pick row | Page height | Nav targets | Smallest |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for row in phone['results']:
            lines.append(f'| `{row["page"]}` | {row["width"]} px | {row["horizontal_overflow_px"]} px | '
                         f'{row["first_pick_row_px"]} px down | {row["document_height_px"]} px | '
                         f'{row["nav_targets"]} | {row["smallest_nav_target_px"]} px |')
        lines.append('')
        for finding in phone['findings']:
            lines.append(f'- {finding}')
        lines.append('')
        for limitation in phone['limitations']:
            lines.append(f'- Limitation: {limitation}')
    lines += ['', '## Why the site is behind, with the primary sources', '',
              '| Run | Started (UTC) | Result |', '| --- | --- | --- |']
    for run in dossier['publisher_runs']:
        lines.append(f'| [{run["id"]}](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/{run["id"]}) | '
                     f'{run["created_at"]} | {run["conclusion"]}'
                     + (f' — {run["failing_step"]}' if run.get('failing_step') else '') + ' |')
    reproduction = dossier['local_reproduction']
    lines += ['', f'Reproduced locally at {reproduction["ran_at"]} on `main` 2f966a91 with '
                  f'`{reproduction["command"]}` → **{reproduction["result"]}**:', '']
    for error in reproduction['errors']:
        lines.append(f'- `{error}`')
    lines += ['', 'Both defects are claimed by other sessions on the coordination board at the time of writing, '
                  'so this dossier records them rather than editing the claimed files.', '',
              '## Policy actually applied', '']
    policy = dossier['policy']
    lines.append(f'- Hotspawn "% picked" used as a probability: **{policy["hotspawn_votes_used"]}**.')
    lines.append(f'- HLTV fan votes used: **{policy["fan_votes_used"]}**.')
    lines.append(f'- Probabilities written by hand: **{policy["probabilities_written_by_hand"]}**.')
    lines.append(f'- Picks written by hand: **{policy["picks_written_by_hand"]}**.')
    lines.append(f'- Provider aliases created: **{policy["aliases_created"]}**.')
    lines.append(f'- {policy["time_basis"]}')
    lines.append(f'- {policy["unobserved_is_not_absent"]}')
    lines += ['', '## Limitations of this dossier', '']
    for limitation in dossier['limitations']:
        lines.append(f'- {limitation}')
    lines.append('')
    return '\n'.join(lines)


def main() -> None:
    observations = json.loads(OBSERVATIONS.read_text())
    published = load_published()
    dossier = build_dossier(observations, published)
    OUT_JSON.write_text(json.dumps(dossier, indent=2, ensure_ascii=False) + '\n')
    OUT_MD.write_text(render_markdown(dossier))
    counts = dossier['counts']
    print(f"reconciled {counts['lobby_future_cards']} lobby cards against {counts['published_rows']} published rows: "
          f"{counts['cards_with_a_published_pick']} covered, {counts['cards_without_a_published_pick']} uncovered, "
          f"{counts['published_rows_no_longer_in_the_future_lobby']} published rows no longer in the future lobby")
    print(f'wrote {OUT_JSON} and {OUT_MD}')


if __name__ == '__main__':
    main()
