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
    REGISTER,
    'research/534ae9e5/repo-review.json',
    'research/c03ef201/repo-review.json',
    'research/f5223859/repo-review.json',
    'research/7e8bed83/repo-review.json',
    'research/416d93ee/repo-review.json',
    'research/df80ab9f/repo-review.json',
    'research/52aee465/repo-review.json',
    'research/92a3e9fb/repo-review.json',
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
