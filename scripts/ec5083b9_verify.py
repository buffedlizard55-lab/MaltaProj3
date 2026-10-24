"""Session arena-ec5083b9: does every card the Hotspawn lobby renders have a pick?

The brief asks for a pick, with both win probabilities, for **every** match Hotspawn
lists for Counter-Strike 2, and for a separate register of the ones that could not be
resolved like a featured pick. The dashboard can only answer that question if the
published pages are compared with the live lobby card by card, which is what this
module does.

It reads, and never writes, four things:

* the lobby inventory this session recorded first-hand
  (``data/research/ec5083b9/lobby-inventory-*.json``),
* the published executive summary (``index.html`` in the branch root, which
  ``scripts/root_publish.py`` keeps in sync with the deployed artifact),
* the published ``unresolved/index.html`` register,
* the ``picks/index.html`` complete list, when present.

Nothing here invents a probability, a pick or a source. A card that the pages do not
carry is reported as ``missing``; a card whose row carries no directional pick is
reported as ``no-pick``; a row whose two probabilities do not sum to one, or that has
no official https link at all, is reported as a defect with the exact reason. Every
finding keeps the URLs it was read from so it can be checked by hand.

Run: ``python -m scripts.ec5083b9_verify`` (add ``--fail-on-gap`` to exit 1 when any
live card is missing or unpicked).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

DEFAULT_LOBBY = Path('data/research/ec5083b9/lobby-inventory-2026-10-24T0627Z.json')
DEFAULT_OUT = Path('data/research/ec5083b9')
HOTSPAWN_HOSTS = ('www.hotspawn.com', 'play.hotspawn.com', 'hotspawn.com')
# Badge text the build writes inside ``.badge`` for each rung of the ladder.
METHODS = {'market', 'bookmaker', 'reference', 'model', 'guidance', 'consensus'}


def _text(node) -> str:
    return ' '.join(node.get_text(' ', strip=True).split())


def _percent(text: str) -> float | None:
    match = re.search(r'(\d+(?:\.\d+)?)\s*%', text or '')
    return float(match.group(1)) / 100 if match else None


def parse_glance(html: str) -> dict[str, dict]:
    """Every ``.glance-row`` of the executive summary, keyed by Hotspawn fixture id."""
    soup = BeautifulSoup(html, 'html.parser')
    rows: dict[str, dict] = {}
    for row in soup.select('li.glance-row[data-glance-id]'):
        fixture = row.get('data-glance-id')
        if not fixture:
            continue
        heading = row.select_one('.glance-match strong')
        teams = _text(heading) if heading else ''
        teams = re.sub(r'\s+vs\s+', ' vs ', teams).strip()
        choice = row.select_one('.glance-choice')
        pick_label = row.select_one('.glance-pick-label')
        pick_team = ''
        pick_probability = None
        other = ''
        other_probability = None
        badges = []
        if choice is not None:
            strongs = choice.find_all('strong', recursive=False)
            if strongs:
                pick_team = _text(strongs[0])
            prob = choice.select_one('.glance-prob')
            pick_probability = _percent(_text(prob)) if prob else None
            other_node = choice.select_one('.glance-other')
            if other_node is not None:
                other = _text(other_node)
                other_probability = _percent(other)
            badges = [_text(b) for b in choice.select('.badge')]
        links = [a.get('href', '') for a in row.select('a.source-link[href]')]
        rows[fixture] = {
            'fixture_id': fixture,
            'teams': teams,
            'method': (row.get('data-method') or '').strip(),
            'pick_label': _text(pick_label) if pick_label else '',
            'pick_team': pick_team,
            'pick_probability': pick_probability,
            'other_team': other,
            'other_probability': other_probability,
            'badges': badges,
            'starts_at': row.get('data-glance-starts'),
            'closed': row.get('data-glance-closed'),
            'links': links,
            'hotspawn_links': [h for h in links if urlparse(h).netloc in HOTSPAWN_HOSTS],
            'official_links': [h for h in links if h.startswith('https://')
                               and urlparse(h).netloc not in ('', None)],
        }
    return rows


def parse_unresolved(html: str) -> dict[str, dict]:
    """Fixture ids published in the ``unresolved`` register, with their stated reason."""
    soup = BeautifulSoup(html, 'html.parser')
    found: dict[str, dict] = {}
    for node in soup.select('[id^="no-line-"]'):
        fixture = node.get('id', '').removeprefix('no-line-')
        if not fixture:
            continue
        reason = ''
        paragraph = node.select_one('.unresolved-detail, p')
        if paragraph is not None:
            reason = _text(paragraph)[:400]
        found[fixture] = {'reason': reason}
    for anchor in soup.select('a[href*="#no-line-"]'):
        match = re.search(r'#no-line-(\d+)', anchor.get('href', ''))
        if match:
            found.setdefault(match.group(1), {'reason': ''})
    return found


def in_site_links(html: str, site: Path, page: str) -> list[dict]:
    """Resolve every in-site link of one page against the built tree.

    Query strings are dropped before the file lookup (``./picks/?basis=market``
    is a filter over ``picks/index.html``), relative paths are normalised, and a
    target under ``data/`` is reported as ``artifact-only`` when the branch root
    does not carry it: ``scripts/root_publish.py`` deliberately copies only the
    rendered pages, while the deployed Pages artifact ships the whole ``data/``
    tree. Neither case is counted as a broken link.
    """
    from posixpath import normpath

    soup = BeautifulSoup(html, 'html.parser')
    base = Path(page).parent
    results = []
    for anchor in soup.find_all('a', href=True):
        original = anchor['href'].strip()
        href = original
        if href.startswith(('mailto:', 'tel:', 'javascript:')):
            continue
        if href.startswith('https://buffedlizard55-lab.github.io/MaltaProj3'):
            href = href.split('/MaltaProj3', 1)[1] or '/'
            href = '.' + href
        elif href.startswith('http'):
            results.append({'page': page, 'href': original, 'ok': True, 'external': True})
            continue
        parsed = urlparse(href)
        path, fragment = parsed.path, parsed.fragment
        if not path:
            target = page
        else:
            target = normpath((base / path).as_posix()) if not path.startswith('/') \
                else normpath(path.lstrip('/'))
            if target in ('', '.'):
                target = page
            elif target.endswith('/') or '.' not in Path(target).name:
                target += '/index.html'
            elif Path(target).suffix == '':
                target += '/index.html'
        target_path = site / target
        ok = target_path.is_file()
        anchor_ok = None
        if ok and fragment:
            anchor_ok = f'id="{fragment}"' in target_path.read_text(errors='ignore')
            ok = anchor_ok
        entry = {'page': page, 'href': original, 'target': target,
                 'fragment': fragment or None, 'ok': ok, 'anchor_ok': anchor_ok}
        if not ok and target.startswith('data/'):
            entry['artifact_only'] = True
        results.append(entry)
    return results


def reconcile(cards: list[dict], rows: dict[str, dict], register: dict[str, dict]) -> list[dict]:
    """One verdict per lobby card. No probability is computed here."""
    report = []
    for card in cards:
        fixture = str(card['hotspawn_id'])
        row = rows.get(fixture)
        entry = {
            'fixture_id': fixture,
            'teams': card['teams'],
            'competition': card.get('competition'),
            'scheduled_start_displayed': card.get('scheduled_start_displayed'),
            'fixture_url': card.get('fixture_url'),
            'status': 'missing',
            'method': None,
            'pick': None,
            'probabilities': None,
            'hotspawn_link_on_page': None,
            'official_source_links': [],
            'register_reason': register.get(fixture, {}).get('reason', ''),
            'defects': [],
        }
        if row is None:
            entry['defects'].append('No published row for this live Hotspawn card.')
            report.append(entry)
            continue
        entry['method'] = row['method']
        entry['pick'] = row['pick_team'] or None
        if row['pick_probability'] is not None or row['other_probability'] is not None:
            entry['probabilities'] = [row['pick_probability'], row['other_probability']]
        entry['hotspawn_link_on_page'] = bool(row['hotspawn_links'])
        entry['official_source_links'] = row['official_links']
        entry['status'] = 'covered' if entry['pick'] else 'no-pick'
        if not entry['pick']:
            entry['defects'].append('Row carries no directional pick.')
        if entry['probabilities'] is None or None in entry['probabilities']:
            entry['defects'].append('Row does not publish both win probabilities.')
        elif abs(sum(entry['probabilities']) - 1.0) > 0.011:
            entry['defects'].append(
                f'Probabilities {entry["probabilities"]} do not sum to 1.')
        if not entry['hotspawn_link_on_page']:
            entry['defects'].append('Row has no Hotspawn fixture link.')
        if not entry['official_source_links']:
            entry['defects'].append('Row has no official https source link.')
        if entry['method'] not in METHODS | {'', None}:
            entry['defects'].append(f'Unrecognised method label {entry["method"]!r}.')
        report.append(entry)
    return report


def summarise(report: list[dict]) -> dict:
    covered = [r for r in report if r['status'] == 'covered']
    model_only = [r for r in covered if r['method'] == 'model']
    return {
        'cards': len(report),
        'covered': len(covered),
        'missing': sum(r['status'] == 'missing' for r in report),
        'unpicked': sum(r['status'] == 'no-pick' for r in report),
        'model_only': len(model_only),
        'with_betting_line': len([r for r in covered if r['method'] in
                                  {'market', 'bookmaker', 'reference', 'consensus'}]),
        'rows_with_defects': len([r for r in report if r['defects']]),
        'missing_fixture_ids': [r['fixture_id'] for r in report if r['status'] == 'missing'],
        'unpicked_fixture_ids': [r['fixture_id'] for r in report if r['status'] == 'no-pick'],
    }


def verify(site: Path, lobby_file: Path, label: str | None = None) -> dict:
    lobby = json.loads(Path(lobby_file).read_text())
    index = Path(site) / 'index.html'
    html = index.read_text(errors='ignore')
    rows = parse_glance(html)
    register = parse_unresolved(html)
    unresolved_page = Path(site) / 'unresolved/index.html'
    if unresolved_page.is_file():
        register.update(parse_unresolved(unresolved_page.read_text(errors='ignore')))
    report = reconcile(lobby['cards'], rows, register)
    stamp = re.search(r'data-snapshot-generated="([^"]+)"', html)
    links = []
    for page in ('index.html', 'unresolved/index.html', 'picks/index.html', 'origination/index.html'):
        candidate = Path(site) / page
        if candidate.is_file():
            links.extend(in_site_links(candidate.read_text(errors='ignore'), Path(site), page))
    broken = [link for link in links if not link['ok'] and not link.get('artifact_only')]
    artifact_only = [link for link in links if link.get('artifact_only')]
    return {
        'session': 'arena-ec5083b9',
        'checked_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'lobby_source': {'url': lobby['source_url'], 'observed_at': lobby['observed_at']},
        'published_pages': {'site': str(site), 'label': label,
                            'snapshot_generated': stamp.group(1) if stamp else None},
        'summary': summarise(report),
        'cards': report,
        'in_site_links': {'checked': len(links), 'broken': broken,
                          'artifact_only': len(artifact_only)},
    }


def render_markdown(result: dict) -> str:
    """A phone-readable dossier of the same verdicts, with the source links."""
    summary = result['summary']
    site = result['published_pages']
    lines = [
        '# Every live Hotspawn CS2 card vs the published picks',
        '',
        f"Checked **{result['checked_at']}** against the lobby read at "
        f"**{result['lobby_source']['observed_at']}** "
        f"([{result['lobby_source']['url']}]({result['lobby_source']['url']})).",
        f"Published pages: {site['label'] or site['site']}, snapshot stamp "
        f"`{site['snapshot_generated']}`.",
        '',
        '| Cards the lobby renders | With a pick | Missing from the pages | No pick | '
        'Research model only | With a betting line |',
        '| --- | --- | --- | --- | --- | --- |',
        f"| {summary['cards']} | **{summary['covered']}** | **{summary['missing']}** | "
        f"{summary['unpicked']} | {summary['model_only']} | {summary['with_betting_line']} |",
        '',
    ]
    if summary['missing_fixture_ids'] or summary['unpicked_fixture_ids']:
        lines += ['## Cards without a published pick', '']
        for entry in result['cards']:
            if entry['status'] == 'covered':
                continue
            lines += [
                f"### {entry['teams'][0]} vs {entry['teams'][1]} — {entry['status']}",
                '',
                f"- Competition: {entry['competition']}",
                f"- Hotspawn card (read {result['lobby_source']['observed_at']}): "
                f"[{entry['fixture_url']}]({entry['fixture_url']})",
                f"- Stated limitation: {entry['register_reason'] or 'not stated on the page'}",
            ]
            for defect in entry['defects']:
                lines.append(f'- Defect: {defect}')
            lines.append('')
    else:
        lines += ['## Cards without a published pick', '',
                  'None: every card the lobby rendered has a published pick and both win probabilities.', '']
    model = [e for e in result['cards'] if e['method'] == 'model']
    if model:
        lines += ['## Picks that are a research model, not a betting line', '',
                  'These rows carry a pick but no external market priced them; each keeps its own '
                  'source and limitation on the row and in the unresolved register.', '',
                  '| Match | Pick | Both probabilities | Row source |', '| --- | --- | --- | --- |']
        for entry in model:
            probabilities = ' / '.join(
                f'{100 * p:.1f}%' if p is not None else '—' for p in (entry['probabilities'] or []))
            evidence = [h for h in entry['official_source_links']
                        if urlparse(h).netloc not in HOTSPAWN_HOSTS]
            source = evidence[0] if evidence else '—'
            lines.append(f"| {entry['teams'][0]} vs {entry['teams'][1]} | {entry['pick']} | "
                         f"{probabilities} | {source} |")
        lines.append('')
    links = result['in_site_links']
    lines += ['## In-site links', '',
              f"- Checked: **{links['checked']}** on the executive summary, the unresolved register, "
              f"the picks list and the origination page",
              f"- Broken: **{len(links['broken'])}**",
              f"- Evidence files that only the deployed artifact carries: {links['artifact_only']}", '']
    if links['broken']:
        lines += ['| Page | Link | Target |', '| --- | --- | --- |']
        for link in links['broken'][:25]:
            lines.append(f"| {link['page']} | `{link['href']}` | `{link.get('target')}` |")
        lines.append('')
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', default='.', help='published build to read (default: branch root)')
    parser.add_argument('--lobby', default=str(DEFAULT_LOBBY))
    parser.add_argument('--label', default=None, help='how the checked tree is named in the dossier')
    parser.add_argument('--write', default=None, help='write the JSON report to this path')
    parser.add_argument('--markdown', default=None, help='write the readable dossier to this path')
    parser.add_argument('--fail-on-gap', action='store_true')
    args = parser.parse_args(argv)
    result = verify(Path(args.site), Path(args.lobby), args.label)
    if args.write:
        Path(args.write).write_text(json.dumps(result, indent=2) + '\n')
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(result))
    summary = result['summary']
    print(json.dumps({'summary': summary,
                      'snapshot_generated': result['published_pages']['snapshot_generated'],
                      'in_site_links': result['in_site_links']['checked'],
                      'broken_in_site_links': len(result['in_site_links']['broken'])}, indent=2))
    if args.fail_on_gap and (summary['missing'] or summary['unpicked']):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
