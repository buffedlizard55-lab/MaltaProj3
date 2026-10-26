"""Publish session c07e1b40's line-by-line repository review on Flagged for Review.

Unlike the inherited de176356 audit register (rendered as reported, unverified claims),
every item here was reproduced and checked against the linked official or first-party
sources by the reviewing session, so its status is shown as recorded: fixed, verified,
needs review or platform limitation. Evidence details stay visible for manual review.
"""
from __future__ import annotations

from html import escape
from urllib.parse import urlparse

REGISTER = 'research/c07e1b40/repo-review.json'
# Every session review register that is published on the Flagged for Review
# page. Each file is a dated, source-linked register; a register that is not
# present in the tree is simply not rendered.
REGISTERS = (
    'research/f644ed1b/repo-review.json',
    REGISTER,
    # Session 39680a42: source-side verification of the picks the deployed
    # dashboard already publishes - the 1082792 identity chain (Hotspawn ->
    # Polymarket cs2-hotu-the9-2026-10-31 -> HLTV 2399437), the nine-fixture live
    # coverage gap, the headline-vs-snapshot count, and the landing-page contract.
    'research/39680a42/repo-review.json',
    # Session 35e31fef: 17/17 live future Hotspawn CS2 lobby parity (13:37Z),
    # 18/18 active pick replay, <8h EGW match-page refresh in CAPTURE_PATHS
    # (1082858, 1082859, 1086696), 3 post-snapshot Polymarket tight books
    # (1086696, 1082697, 1086697), and HLTV-vs-Valve 2026-10-05 roster-drift flags.
    'research/35e31fef/repo-review.json',
    'research/534ae9e5/repo-review.json',
    'research/c03ef201/repo-review.json',
    'research/f5223859/repo-review.json',
    'research/7e8bed83/repo-review.json',
    'research/416d93ee/repo-review.json',
    'research/df80ab9f/repo-review.json',
    'research/52aee465/repo-review.json',
    'research/92a3e9fb/repo-review.json',
    'research/81c1058a/repo-review.json',
    # Session bf1f9ce5: import-safety fix for audit_sources/discover_sources,
    # cached (80) vs cache-busted (78) Hotspawn lobby reconciliation, 17/17 live
    # pick replay, HLTV-first sweep on all 5 no-line fixtures, and Chromium phone check.
    'research/bf1f9ce5/repo-review.json',
    # Session 9c4b1f7a: independent re-verification of the 2026-10-23T09:23Z
    # snapshot (inventory, coverage, ratings arithmetic, line provenance) plus
    # the observed-price chip added to the phone summary.
    'research/9c4b1f7a/repo-review.json',
    # Session ca7e10e5: published-state verification and the snapshot.json split.
    'research/ca7e10e5/repo-review.json',
    # Session 73bc57bd: every future Hotspawn CS2 Pick'ems card (25, read
    # 2026-10-24T05:31Z) reconciled with the pick rows the published site serves
    # (19), the four failed publisher runs that caused the nine uncovered cards,
    # and the HLTV-first/esportsbook evidence for each of them.
    'research/73bc57bd/repo-review.json',
    # Session dd433e7f: 2026-10-24 publisher clock-pin fix, #no-line-research
    # deduplication, 25/25 HLTV-first sweep, and competition-scoped aliases.
    'research/dd433e7f/repo-review.json',
    # Session c6b8d58b: 31/31 Hotspawn + 31/31 HLTV match-page reconciliation
    # (closing the 6 South American fixtures), EGW consensus capture across the
    # 13 model-only fixtures, and scoped CCT South America #7 aliases.
    'research/c6b8d58b/repo-review.json',
    # Session c2a74e33: 22/22 live future Hotspawn lobby parity (16:42Z), 23/23
    # complete-pick replay, <8h EGW match-page refresh for 1082858 in
    # CAPTURE_PATHS, Polymarket CLOB tightening on 1082996, and HLTV stand-in flags.
    'research/c2a74e33/repo-review.json',
    # Session arena-b3e91409: independent replay of all 10 published rows (exact
    # re-derivation from each row's own bid/ask, odds or rating points), the nine
    # open Hotspawn fixtures absent from the 23:03:48Z publication, and the
    # identity/clock conflicts that decide which external line may price them.
    'research/b3e91409/repo-review.json',
    # Session arena-0db056f7: publisher freeze root cause (stale Group A
    # snapshot test), three post-snapshot lobby fixtures, EGW capture for
    # 1086696, and the flagged 98.2% network estimate on 1082792.
    'research/0db056f7/repo-review.json',
    # Session 0c034b94: every published number replayed from its own evidence
    # (16/16 featured rows, 0 violations), live Hotspawn inventory vs the
    # published picks at 2026-10-25T13:45Z (17 open, 3 with no row because the
    # four-hour publisher is red), HLTV-first identity/ranking for every
    # no-money-line fixture, the 14:00Z/14:30Z schedule disagreement on 1085542,
    # the Projeto/Tropa do KinGui name variant, and the esportsbook access limits.
    'research/0c034b94/repo-review.json',
    # Session 9e0e601d: full replay of every published method (17/17 complete-list
    # and 13/13 featured rows, 0 violations), the publisher's stale-dossier
    # regression at 14:34Z, 15 of 24 local downloads answering 404 because Pages
    # serves the branch root, the page/download parity gap, live inventory parity,
    # and the source interfaces that refuse runners.
    'research/9e0e601d/repo-review.json',
    # Session 22a3ed80: independent replay of the published 2026-10-25T14:23:33Z
    # summary (16/16 active rows, 13 featured re-derived, 3 labelled fallbacks),
    # the repair of a false "9 missing" lobby-gap count on cards the record says
    # were already carried, the scheduled-publisher failure class, and the
    # legacy branch-root / sandbox egress limitations.
    'research/22a3ed80/repo-review.json',
    # Session 824a2780: independent replay of the 2026-10-25T14:23:33Z build
    # (13/13 priced rows, 4/4 Valve inputs re-checked against the official file),
    # the pick-less fixtures' reasons checked against that same file, the
    # odds-floor bookmaker row, the blocked esportsbooks, and the phone path to
    # the picks.
    'research/824a2780/repo-review.json',
    # Session c333bb27: 2026-10-26 81-record / 19-open Hotspawn CS2 lobby
    # reconciliation, HLTV-first + esportsbook/exchange/Valve research for the
    # 10 non-featured fixtures, 19/19 exact probability replay, and provider
    # start-time / alias-scope flags.
    'research/c333bb27/repo-review.json',
)
STATUS = {
    'fixed': ('Fixed', 'green'),
    'verified': ('Verified', 'green'),
    'needs review': ('Needs review', 'amber'),
    'platform limitation': ('Platform limitation', 'purple'),
}


def e(value) -> str:
    return escape(str(value), quote=True)


def host(url: str) -> str:
    """Distinguishable link text: host plus up to two leading path segments."""
    parsed = urlparse(url)
    parts = [x for x in parsed.path.split('/') if x][:2]
    return '/'.join([parsed.netloc.removeprefix('www.') or 'source'] + parts)


def validate(register: dict) -> None:
    items = register.get('items')
    if not isinstance(items, list) or not items:
        raise ValueError('Review register has no items')
    seen = set()
    for item in items:
        for key in ('id', 'area', 'status', 'finding', 'handling', 'evidence'):
            if not item.get(key):
                raise ValueError(f'Review item {item.get("id")!r} is missing {key}')
        if item['id'] in seen:
            raise ValueError(f'Duplicate review item {item["id"]}')
        seen.add(item['id'])
        if item['status'] not in STATUS:
            raise ValueError(f'Review item {item["id"]} has unknown status {item["status"]!r}')
        for ev in item['evidence']:
            if not str(ev.get('url', '')).startswith('https://') or not ev.get('detail'):
                raise ValueError(f'Review item {item["id"]} needs https evidence links with details')


def render(register: dict, prefix: str, section_id: str = 'session-review',
           register_path: str = REGISTER, include_shared: bool = True) -> str:
    validate(register)
    counts = {}
    for item in register['items']:
        counts[item['status']] = counts.get(item['status'], 0) + 1
    summary = ' · '.join(f'{n} {STATUS[s][0].lower()}' for s, n in counts.items())
    out = [f'<section class="content-section" id="{e(section_id)}"><div class="section-heading"><div>'
           f'<p class="eyebrow">Line-by-line review · {e(register["session"])}</p><h2>Repository review register</h2></div>'
           f'<span class="muted small">{e(summary)}</span></div>',
           f'<p>{e(register["scope"])} Reviewed {e(register["review_clock_utc"])}. {e(register["method"])} '
           f'<a style="text-decoration:underline" href="{prefix}data/{e(register_path)}">Original register (JSON) ↓</a></p>',
           '<div class="table-scroll"><table class="simple-table review-table"><caption class="sr-only">'
           'Repository review findings with status, handling and evidence links</caption><thead><tr>'
           '<th scope="col">Finding</th><th scope="col">Handling</th><th scope="col">Evidence</th></tr></thead><tbody>']
    for item in register['items']:
        label, kind = STATUS[item['status']]
        out.append(f'<tr id="review-{e(item["id"])}"><th scope="row"><span class="badge {e(kind)}">{e(label)}</span>'
                   f'<strong>{e(item["id"])} · {e(item["area"])}</strong><small>{e(item["finding"])}</small></th>'
                   f'<td>{e(item["handling"])}</td><td><details><summary>{len(item["evidence"])} source links</summary><ul>')
        for ev in item['evidence']:
            out.append(f'<li>{e(ev["detail"])} <a class="source-link" href="{e(ev["url"])}" target="_blank" '
                       f'rel="noopener noreferrer">{e(host(ev["url"]))}</a></li>')
        out.append('</ul></details></td></tr>')
    out.append('</tbody></table></div></section>')
    if include_shared:
        out.append(shared_disambiguation_section(prefix))
    return ''.join(out)


def shared_disambiguation_section(prefix: str) -> str:
    """The lineup-disambiguation block is page-wide, not part of a register.

    It is rendered once for the page, never once per register, so a page that
    carries two registers never repeats an element id.
    """
    from scripts.lineup_disambiguation import DISAMBIGUATION_PATH, VALVE_EVIDENCE_PATH, load_disambiguation, render_disambiguation_section
    if DISAMBIGUATION_PATH.exists() and VALVE_EVIDENCE_PATH.exists():
        return render_disambiguation_section(load_disambiguation(DISAMBIGUATION_PATH, VALVE_EVIDENCE_PATH), prefix)
    return ''


def render_all(registers: list, prefix: str, paths: list | None = None) -> str:
    """Render every session review register, in the order they are declared.

    Each register gets its own section id so a page that carries more than one
    register never repeats an element id.
    """
    out = []
    for index, register in enumerate(registers):
        path = (paths[index] if paths and index < len(paths) else REGISTER)
        section_id = 'session-review' if index == 0 else f'session-review-{index}'
        out.append(render(register, prefix, section_id=section_id, register_path=path,
                          include_shared=(index == 0)))
    return ''.join(out)
