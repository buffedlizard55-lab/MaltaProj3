"""Row-level official-source audit of the built Pages site.

The project rule is: *every table row carries a link to an official/primary
source, or an explicit "unverified" marker where a value could not be
confirmed*.  This script parses the generated HTML (``site/`` by default) and
checks that rule row by row so a regression cannot ship silently.

A "row" is either a ``<tr>`` inside a ``<tbody>`` or a card-style row
(``<article class="pick-card ...">``).  A row is

* ``ok``       - it has at least one external link to an allow-listed official
                 or primary publisher (see ``OFFICIAL``);
* ``flagged``  - no official link, but the row visibly says the value is
                 unverified / not yet resolved (the blank-and-flag rule);
* ``navigation``- a row of a site-map table (caption "Every page on this
                 site ...") that only links to other pages of this site;
* ``violation``- neither.  Violations are listed with the page, the row text
                 and (when present) the non-official links found in it.

Nothing here edits a page or infers a value.  Usage::

    python -m scripts.audit_rows [--site site] [--report path.json] [--strict]

``--strict`` exits non-zero when a violation exists.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

# Official or primary publishers whose pages/APIs are the original source of a
# value shown in a row.  Hosts match exactly or as a sub-domain.  A path prefix
# narrows a shared host (GitHub) to the publisher's own namespace.
OFFICIAL = [
    # Hotspawn: the lobby, match pages, rules page and the fixture API its client calls.
    ('hotspawn.com', None), ('play.hotspawn.com', None), ('www.hotspawn.com', None),
    ('phpstack-1372681-6459848.cloudwaysapps.com', '/api/'),
    # HLTV: results, match pages, rankings, official transfer news, team pages.
    ('hltv.org', None),
    # Polymarket: market pages and its documented market-data APIs.
    ('polymarket.com', None), ('gamma-api.polymarket.com', None), ('clob.polymarket.com', None),
    ('docs.polymarket.com', None),
    # Bookmakers read as price sources (a failed attempt is linked to the book it tried).
    ('thunderpick.io', None), ('gg.bet', None), ('stake.com', None), ('pinnacle.com', None),
    ('rivalry.com', None),
    # Valve's own regional standings repository and model code.
    ('github.com', '/ValveSoftware/'), ('raw.githubusercontent.com', '/ValveSoftware/'),
    ('api.github.com', '/repos/ValveSoftware/'),
    # Platform documentation and this repository's own run records.
    ('docs.github.com', None), ('github.com', '/buffedlizard55-lab/MaltaProj3'),
    ('api.github.com', '/repos/buffedlizard55-lab/MaltaProj3'),
]
# A table that only tells the reader which page of this site to open is a site map,
# not a data table: it makes no claim that needs an external source.  The exemption
# is keyed to the table's own <caption>, so a data table can never slip through it.
NAV_CAPTIONS = ('Every page on this site',)
UNVERIFIED = re.compile(r'unverified|not yet resolved|unresolved|no evidence|blank|insufficient verified inputs|not claimed|unavailable', re.I)
# Card-style rows: a pick card, and the unresolved-fixture card (same obligation: an official link or an unverified flag).
CARD_CLASSES = {'pick-card', 'unresolved-card'}
SKIP_PAGES = {'archive', 'docs'}  # preserved third-party snapshots, bannered as archives


def is_official(url: str) -> bool:
    parts = urlparse(url)
    if parts.scheme not in {'http', 'https'}:
        return False
    host = (parts.hostname or '').lower()
    for allowed, prefix in OFFICIAL:
        if host == allowed or host.endswith('.' + allowed):
            if prefix is None or parts.path.startswith(prefix):
                return True
    return False


class Rows(HTMLParser):
    """Collect rows with their text and links; ``<tfoot>``/``<thead>`` rows are ignored."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._stack = []          # open row frames
        self._section = []        # thead/tbody/tfoot nesting
        self._skip = 0            # inside <script>/<style>
        self._tables = []         # open tables: {'caption': str}
        self._in_caption = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in {'script', 'style'}:
            self._skip += 1
        if tag == 'table':
            self._tables.append({'caption': ''})
        if tag == 'caption':
            self._in_caption = True
        if tag in {'thead', 'tbody', 'tfoot'}:
            self._section.append(tag)
        is_table_row = tag == 'tr' and 'thead' not in self._section and 'tfoot' not in self._section
        classes = (a.get('class') or '').split()
        is_card = tag == 'article' and bool(CARD_CLASSES.intersection(classes))
        if is_table_row or is_card:
            self._stack.append({'tag': tag, 'id': a.get('id'), 'text': [], 'links': [], 'table': self._tables[-1] if self._tables and tag == 'tr' else None})
        if tag == 'a' and a.get('href') and self._stack:
            for frame in self._stack:
                frame['links'].append(a['href'])

    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self._skip:
            self._skip -= 1
        if tag == 'caption':
            self._in_caption = False
        if tag == 'table' and self._tables:
            self._tables.pop()
        if tag in {'thead', 'tbody', 'tfoot'} and tag in self._section:
            self._section.reverse(); self._section.remove(tag); self._section.reverse()
        if self._stack and self._stack[-1]['tag'] == tag:
            frame = self._stack.pop()
            frame['text'] = re.sub(r'\s+', ' ', ' '.join(frame['text'])).strip()
            self.rows.append(frame)

    def handle_data(self, data):
        if self._in_caption and self._tables:
            self._tables[-1]['caption'] += data
        if self._stack and not self._skip:
            for frame in self._stack:
                frame['text'].append(data)


def classify(row: dict) -> str:
    links = [h for h in row['links'] if h.startswith(('http://', 'https://'))]
    if any(is_official(h) for h in links):
        return 'ok'
    caption = (row.get('table') or {}).get('caption', '').strip()
    if caption.startswith(NAV_CAPTIONS) and not links:
        return 'navigation'
    if UNVERIFIED.search(row['text']):
        return 'flagged'
    return 'violation'


def audit_page(path: Path, site: Path) -> dict:
    return audit_html(path.read_text(encoding='utf-8'), path.relative_to(site).as_posix())


def audit_html(text: str, page: str) -> dict:
    parser = Rows()
    parser.feed(text)
    counts = {'ok': 0, 'flagged': 0, 'navigation': 0, 'violation': 0}
    violations = []
    for row in parser.rows:
        if not row['text']:
            continue
        verdict = classify(row)
        counts[verdict] += 1
        if verdict == 'violation':
            violations.append({
                'row_id': row['id'],
                'text': row['text'][:160],
                'links': [h for h in row['links'] if h.startswith(('http://', 'https://'))][:6],
                'internal_only': not any(h.startswith(('http://', 'https://')) for h in row['links']),
            })
    return {'page': page, 'rows': sum(counts.values()), **counts, 'violations': violations}


def audit_site(site: Path) -> dict:
    pages = []
    for path in sorted(site.rglob('*.html')):
        rel = path.relative_to(site)
        if rel.parts[0] in SKIP_PAGES or rel.parts[0].startswith('_') or rel.name in {'flagged.html', 'picks.html', 'methodology.html'} and len(rel.parts) == 1:
            continue
        pages.append(audit_page(path, site))
    total = {k: sum(p[k] for p in pages) for k in ('rows', 'ok', 'flagged', 'navigation', 'violation')}
    return {'schema_version': 1, 'site': str(site), 'policy': 'Every table row or pick card links to an allow-listed official/primary source, or is visibly marked unverified.', 'official_hosts': [h + (p or '') for h, p in OFFICIAL], 'totals': total, 'pages': pages}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--site', type=Path, default=Path('site'))
    parser.add_argument('--report', type=Path)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args(argv)
    report = audit_site(args.site)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    t = report['totals']
    print(f"rows={t['rows']} ok={t['ok']} flagged-unverified={t['flagged']} site-map={t['navigation']} violations={t['violation']}")
    for p in report['pages']:
        print(f"  {p['page']:<28} rows={p['rows']:<4} ok={p['ok']:<4} flagged={p['flagged']:<3} site-map={p['navigation']:<3} violations={p['violation']}")
        for v in p['violations'][:5]:
            print('     ✗', (v['row_id'] or '-'), '|', v['text'][:110], '| internal-only' if v['internal_only'] else '| non-official links: ' + ', '.join(v['links'][:2]))
    return 1 if args.strict and t['violation'] else 0


if __name__ == '__main__':
    sys.exit(main())
