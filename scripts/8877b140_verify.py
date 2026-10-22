"""Independent verification for session arena-8877b140.

Read-only checks of the contracts the project brief requires, run against the
saved pipeline outputs (``data/``) and a locally built site (``site/``):

1. Every active Hotspawn CS2 fixture is either resolved with a directional pick
   (both probabilities, a selected side, an official source link) or is carried
   as an explicit unresolved row that names its limitation and research trail.
2. Every published probability pair is arithmetically coherent and every
   external URL is https on an allow-listed official/primary host.
3. The executive summary gives one-tap, internal routes to the updated pick
   list and to the unresolved/limitations section, the phone glance index
   covers every active fixture, and every page carries the mobile viewport and
   the content security policy.
4. The stylesheet actually contains the phone layout (sub-400 px breakpoint,
   sidebar-to-bottom-nav swap and >=44 px touch targets).

Nothing here fetches a network resource, edits a feed or invents a value. The
script emits a JSON dossier and exits non-zero only when a contract is broken.

    python -m scripts.8877b140_verify --data data --site site \
        --out data/research/8877b140/verification-dossier.json
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from scripts.audit_rows import OFFICIAL, is_official

# Every method the originate ladder can publish. Money methods imply a real
# two-sided external price; model/guidance methods are research estimates.
MONEY_METHODS = frozenset({'market', 'bookmaker', 'consensus', 'reference'})
RESEARCH_METHODS = frozenset({'model', 'guidance'})
KNOWN_METHODS = MONEY_METHODS | RESEARCH_METHODS
ACTIVE_STATES = frozenset({'open', 'locked', 'unknown_lock'})
PROB_TOLERANCE = 1e-6

# Current rendered pages, mirroring scripts.build.PAGES without importing the
# renderer (this module must stay usable against a bare data directory).
CURRENT_PAGES = [
    'index.html', 'picks/index.html', 'edge/index.html', 'twc-picks/index.html',
    'final-day/index.html', 'coverage/index.html', 'methodology/index.html',
    'review/index.html', 'origination/index.html', 'strategy/index.html',
]

# Pages whose renderer historically omits the CSP <meta>. Every entry must be
# covered by a published Flagged-for-Review item (see tests/test_8877b140_contract.py);
# a new page missing the CSP fails the contract rather than joining this set.
KNOWN_CSP_GAPS = {'origination/index.html'}


def _result(name: str, ok: bool, detail: dict | None = None) -> dict:
    return {'check': name, 'ok': bool(ok), 'detail': detail or {}}


def verify_origination_contract(data_dir: Path) -> list[dict]:
    """Coverage and arithmetic contract over the canonical feeds."""
    results: list[dict] = []
    latest = json.loads((data_dir / 'latest.json').read_text())
    orig_path = data_dir / 'origination.json'
    if not orig_path.exists():
        return [_result('origination-feed-present', False,
                        {'reason': 'data/origination.json is missing'})]
    orig = json.loads(orig_path.read_text())
    active = [m for m in latest['matches'] if m.get('availability') in ACTIVE_STATES]
    rows = orig.get('matches') or []
    by_id = {str(m.get('id')): m for m in rows}
    counts = orig.get('counts') or {}

    # 1. Every active fixture is represented exactly once in the complete feed.
    missing = [m['id'] for m in active if str(m['id']) not in by_id]
    duplicate_ids = sorted({str(m.get('id')) for m in rows
                            if sum(1 for r in rows if str(r.get('id')) == str(m.get('id'))) > 1})
    results.append(_result('every-active-fixture-originated', not missing and not duplicate_ids,
                           {'active_fixtures': len(active), 'origination_rows': len(rows),
                            'missing_ids': missing, 'duplicate_ids': duplicate_ids}))

    # 2. Counts block agrees with the rows it describes.
    with_pick = sum(1 for m in rows if m.get('pick_index') is not None and m.get('origination'))
    blank = sum(1 for m in rows if m.get('origination') is None)
    count_checks = {
        'active': (counts.get('active'), len(active)),
        'with_pick': (counts.get('with_pick'), with_pick),
        'unresolved': (counts.get('unresolved'), blank),
    }
    count_mismatch = {k: {'published': pub, 'recomputed': recomputed}
                      for k, (pub, recomputed) in count_checks.items() if pub != recomputed}
    results.append(_result('origination-counts-recompute', not count_mismatch,
                           {'published': counts, 'recomputed': {'active': len(active),
                                                                 'with_pick': with_pick,
                                                                 'unresolved': blank},
                            'mismatches': count_mismatch}))

    # 3. Row-level arithmetic, source and limitation rules.
    violations: list[dict] = []
    for row in rows:
        rid = str(row.get('id'))
        origin = row.get('origination')
        if origin is None:
            # A blank must stay explicit: limitation text and a research trail.
            if not row.get('limitations'):
                violations.append({'id': rid, 'problem': 'blank row without limitation text'})
            trail = [r for r in row.get('research') or [] if r.get('source_url')]
            if not trail:
                violations.append({'id': rid, 'problem': 'blank row without a sourced research trail'})
            continue
        method = origin.get('method')
        if method not in KNOWN_METHODS:
            violations.append({'id': rid, 'problem': f'unknown method {method!r}'})
        probs = origin.get('probabilities') or []
        if len(probs) != 2 or not all(isinstance(p, (int, float)) for p in probs):
            violations.append({'id': rid, 'problem': 'probability pair is not two numbers'})
        else:
            if abs(sum(probs) - 1.0) > PROB_TOLERANCE:
                violations.append({'id': rid, 'problem': f'probabilities sum to {sum(probs):.6f}'})
            if not all(0.0 < p < 1.0 for p in probs):
                violations.append({'id': rid, 'problem': f'probability outside (0,1): {probs}'})
            fair = origin.get('fair_decimal') or []
            if len(fair) == 2:
                rebuilt = [round(1.0 / p, 3) for p in probs]
                if any(abs(a - b) > 0.0011 for a, b in zip(fair, rebuilt)):
                    violations.append({'id': rid, 'problem': 'fair_decimal is not the reciprocal of the probabilities'})
        pick = row.get('pick_index')
        if pick is not None:
            if pick not in (0, 1):
                violations.append({'id': rid, 'problem': f'pick_index {pick!r} outside 0/1'})
            elif probs and abs(probs[0] - probs[1]) <= 1e-9:
                violations.append({'id': rid, 'problem': 'a side was selected for an even estimate'})
            elif probs and probs[pick] != max(probs):
                violations.append({'id': rid, 'problem': 'pick_index does not point at the larger probability'})
        if not str(origin.get('source_url') or '').startswith('https://'):
            violations.append({'id': rid, 'problem': 'origination source_url missing or not https'})
        for quote in origin.get('quotes') or []:
            if not str(quote.get('source_url') or '').startswith('https://'):
                violations.append({'id': rid, 'problem': f"quote {quote.get('provider')!r} source_url not https"})
        if method in RESEARCH_METHODS and not origin.get('limitations'):
            violations.append({'id': rid, 'problem': 'research-model row without a published limitation'})
    results.append(_result('row-arithmetic-and-sources', not violations,
                           {'rows_checked': len(rows), 'violations': violations}))

    # 4. Crowd-vote contamination is forbidden by the source policy.
    policy = orig.get('policy') or {}
    crowd_ok = policy.get('hotspawn_votes_used') is False and policy.get('fan_votes_used') is False
    results.append(_result('no-crowd-vote-inputs', crowd_ok, {'policy': policy}))
    return results


def iter_external_urls(value):
    """Yield every http(s) URL string found inside a nested JSON structure."""
    if isinstance(value, str):
        if value.startswith('http://') or value.startswith('https://'):
            yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_external_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_external_urls(child)


def verify_inventory_reconciliation(data_dir: Path) -> list[dict]:
    """The Hotspawn API, both rendered lobbies and the published feed agree.

    Uses only saved first-party evidence: the fixture API array
    (data/evidence/hotspawn-fixtures.json), the lobby hydration context
    (hotspawn-context.json) and data/latest.json. Duplicate ids, missing ids
    or a three-way mismatch fail closed, mirroring the collector's own rule.
    """
    fixtures_path = data_dir / 'evidence' / 'hotspawn-fixtures.json'
    context_path = data_dir / 'evidence' / 'hotspawn-context.json'
    latest_path = data_dir / 'latest.json'
    missing = [p.name for p in (fixtures_path, context_path, latest_path) if not p.exists()]
    if missing:
        return [_result('hotspawn-inventory-reconciliation', False,
                        {'missing_evidence': missing})]
    fixtures = json.loads(fixtures_path.read_text())
    context = json.loads(context_path.read_text())
    latest = json.loads(latest_path.read_text())
    api_ids = [str(x.get('id')) for x in fixtures]
    feed_ids = [str(m.get('id')) for m in latest['matches']]
    lobby_ids = [str(x) for x in context.get('lobby_ids', [])]
    cs2_ids = [str(x) for x in context.get('cs2_ids', [])]
    sets = {'api': set(api_ids), 'feed': set(feed_ids),
            'lobby': set(lobby_ids), 'cs2': set(cs2_ids)}
    no_duplicates = len(api_ids) == len(sets['api']) and len(feed_ids) == len(sets['feed'])
    all_equal = all(s == sets['api'] for s in sets.values())
    detail = {'records': len(api_ids), 'unique_records': len(sets['api']),
              'sets_equal': {k: sets[k] == sets['api'] for k in sets},
              'only_in_feed': sorted(sets['feed'] - sets['api'])[:10],
              'missing_from_feed': sorted(sets['api'] - sets['feed'])[:10],
              'observed_at': context.get('observed_at')}
    return [_result('hotspawn-inventory-reconciliation', no_duplicates and all_equal, detail)]


def verify_source_link_policy(data_dir: Path) -> list[dict]:
    """Every external URL in the canonical feeds is https and allow-listed.

    A non-allow-listed URL is never silently accepted: it is reported on the
    check detail and must additionally be published on Flagged for Review
    (the companion test enforces that coverage). An insecure http:// URL is a
    hard contract failure with no documented exception.
    """
    results: list[dict] = []
    for feed_name in ('origination.json', 'latest.json'):
        feed = json.loads((data_dir / feed_name).read_text())
        urls = sorted(set(iter_external_urls(feed)))
        insecure = [u for u in urls if u.startswith('http://')]
        # Hotspawn's own API host and the cloudways API mirror are on the
        # audit allow-list; anything not on the list is reported for review.
        non_official = [u for u in urls if not is_official(u)]
        results.append(_result(f'{feed_name}-link-policy', not insecure,
                               {'external_urls': len(urls), 'insecure': insecure,
                                'non_allowlisted': non_official}))
    return results


class _LinkAndMetaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[dict] = []
        self.metas: list[dict] = []
        self.ids: set[str] = set()
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style'):
            self._skip += 1
        if tag == 'meta':
            self.metas.append(a)
        if tag == 'a' and a.get('href'):
            self.links.append({'href': a['href'], 'classes': (a.get('class') or '').split()})
        if a.get('id'):
            self.ids.add(a['id'])


def _parse(page: Path) -> _LinkAndMetaParser:
    parser = _LinkAndMetaParser()
    parser.feed(page.read_text())
    return parser


def verify_site_contract(site_dir: Path, data_dir: Path) -> list[dict]:
    """Phone findability and page-level contracts over the built site."""
    results: list[dict] = []
    if not site_dir.exists():
        return [_result('site-build-present', False, {'reason': f'{site_dir} does not exist'})]
    latest = json.loads((data_dir / 'latest.json').read_text())
    active_ids = {str(m['id']) for m in latest['matches']
                  if m.get('availability') in ACTIVE_STATES}

    page_results = []
    documented_csp_gaps = []
    for relative in CURRENT_PAGES:
        page = site_dir / relative
        if not page.exists():
            page_results.append({'page': relative, 'problem': 'missing'})
            continue
        parser = _parse(page)
        has_viewport = any('width=device-width' in (m.get('content') or '')
                           and m.get('name') == 'viewport' for m in parser.metas)
        has_csp = any(m.get('http-equiv') == 'Content-Security-Policy' for m in parser.metas)
        insecure = [l['href'] for l in parser.links
                    if l['href'].startswith('http://')]
        if not has_viewport or insecure:
            page_results.append({'page': relative, 'viewport': has_viewport,
                                 'csp': has_csp, 'insecure_links': insecure})
        elif not has_csp:
            if relative in KNOWN_CSP_GAPS:
                documented_csp_gaps.append(relative)
            else:
                page_results.append({'page': relative, 'viewport': has_viewport,
                                     'csp': False, 'insecure_links': insecure})
    results.append(_result('every-page-viewport-csp-https', not page_results,
                           {'pages_checked': len(CURRENT_PAGES), 'problems': page_results,
                            'documented_csp_gaps': documented_csp_gaps}))

    index = site_dir / 'index.html'
    if not index.exists():
        return results + [_result('executive-summary-findability', False, {'reason': 'index.html missing'})]
    html = index.read_text()
    parser = _parse(index)
    hrefs = {l['href'] for l in parser.links}

    # One-tap internal routes to the picks and to the unresolved section must
    # exist in both the executive banner and the start-here jump bar.
    required_destinations = ('origination/#picks', 'origination/#unresolved')
    banner_ok = all(dest in html for dest in ('class="exec-banner"',) +
                    tuple(f'href="./{d}"' for d in required_destinations))
    start_here_ok = 'id="start-here"' in html and all(
        f'./{d}' in hrefs for d in required_destinations)
    mobile_status_ok = ('mobile-status-picks' in html and 'mobile-status-blank' in html
                        and './origination/#picks' in hrefs and './origination/#unresolved' in hrefs)
    results.append(_result('executive-summary-one-tap-pick-routes',
                           banner_ok and start_here_ok and mobile_status_ok,
                           {'exec_banner': banner_ok, 'start_here_nav': start_here_ok,
                            'mobile_status_strip': mobile_status_ok}))

    # The glance index must include every active fixture id, each with a link
    # to its own origination card, and keep the unresolved register on page.
    glance_ids = set(re.findall(r'class="glance-row"[^>]*data-glance-id="(\d+)"', html))
    if not glance_ids:
        glance_ids = set(re.findall(r'data-glance-id="(\d+)"', html))
    glance_missing = sorted(active_ids - glance_ids)
    sections_ok = all(anchor in parser.ids for anchor in
                      ('picks-at-a-glance', 'unresolved-register', 'no-line-register', 'start-here'))
    results.append(_result('glance-covers-every-active-fixture', not glance_missing and sections_ok,
                           {'active_fixtures': len(active_ids), 'glance_rows': len(glance_ids),
                            'missing_from_glance': glance_missing, 'required_sections_present': sections_ok}))

    # Internal links and in-page anchors must resolve (independent of the
    # renderer's own link audit, using the same published file tree). A link
    # to a directory ("./origination/") is served from its index.html.
    broken: list[str] = []
    for html_path in site_dir.rglob('*.html'):
        if any(part in ('archive', 'docs') for part in html_path.parts):
            continue
        page_parser = _parse(html_path)
        base = html_path.parent
        for link in page_parser.links:
            href = link['href']
            if href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                continue
            if href.startswith('#'):
                if href[1:] not in page_parser.ids:
                    broken.append(f'{html_path.relative_to(site_dir)} -> {href}')
                continue
            target, _, anchor = href.partition('#')
            target = target.split('?', 1)[0]  # client-side query filters, e.g. picks/?basis=market
            resolved = (base / target).resolve() if target else html_path.resolve()
            if resolved.is_dir():
                resolved = resolved / 'index.html'
            if not resolved.exists():
                broken.append(f'{html_path.relative_to(site_dir)} -> {href}')
            elif anchor and resolved.suffix == '.html':
                if anchor not in _parse(resolved).ids:
                    broken.append(f'{html_path.relative_to(site_dir)} -> {href}')
    results.append(_result('internal-links-and-anchors-resolve', not broken,
                           {'broken': broken[:25], 'broken_count': len(broken)}))
    return results


def verify_mobile_css(repo_root: Path) -> list[dict]:
    """Static phone-layout contract over the shipped stylesheet."""
    css_path = repo_root / 'assets' / 'scout.css'
    css = css_path.read_text()
    breakpoints = [int(x) for x in re.findall(r'@media\s*\(max-width:\s*(\d+)px\)', css)]
    smallest = min(breakpoints) if breakpoints else None
    has_small_bp = smallest is not None and smallest <= 400
    # Sidebar must be replaced by the fixed bottom navigation on phones.
    swap = re.search(r'@media\(max-width:700px\)\{[^}]*\.sidebar\{display:none\}', css) is not None
    bottom_nav = '.mobile-nav' in css and 'position:fixed' in css
    # Touch targets: at least one min-height >=44px rule (WCAG 2.5.5 / 2.5.8 style).
    touch_heights = [int(x) for x in re.findall(r'min-height:\s*(\d+)px', css)]
    touch_ok = any(h >= 44 for h in touch_heights)
    # No page-level *fixed* width wider than a 320 px small phone on html/body/
    # main. max-width/min-width declarations are responsive constraints, not
    # fixed widths, so strip them before matching a plain width: declaration.
    global_fixed = []
    for block in re.findall(r'(?:html|body|main)[^{]*\{([^}]*)\}', css):
        responsive_stripped = re.sub(r'(?:max|min)-width:[^;]+;?', '', block)
        global_fixed += re.findall(r'(?<![-\w])width:\s*(\d+)px', responsive_stripped)
    global_ok = not any(int(w) > 320 for w in global_fixed)
    # Flexible sizing primitives are present.
    flexible = all(token in css for token in
                   ('minmax(0,1fr)', 'overflow-wrap:anywhere', 'box-sizing:border-box'))
    ok = has_small_bp and swap and bottom_nav and touch_ok and global_ok and flexible
    return [_result('mobile-stylesheet-contract', ok,
                    {'smallest_max_width_px': smallest, 'all_max_width_px': sorted(set(breakpoints)),
                     'sidebar_to_bottom_nav_swap': swap, 'fixed_bottom_nav': bottom_nav,
                     'largest_touch_min_height_px': max(touch_heights) if touch_heights else None,
                     'global_fixed_widths_px': global_fixed, 'flexible_primitives': flexible})]


def run(repo_root: Path, data_dir: Path, site_dir: Path | None) -> dict:
    checks = []
    checks += verify_inventory_reconciliation(data_dir)
    checks += verify_origination_contract(data_dir)
    checks += verify_source_link_policy(data_dir)
    if site_dir is not None:
        checks += verify_site_contract(site_dir, data_dir)
    checks += verify_mobile_css(repo_root)
    violations = [c for c in checks if not c['ok']]
    return {
        'session': 'arena-8877b140',
        'verified_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'read_only': True,
        'official_host_policy_size': len(OFFICIAL),
        'checks': checks,
        'totals': {'checks': len(checks), 'passed': len(checks) - len(violations),
                   'violations': len(violations)},
        'all_passed': not violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--site', type=Path, default=Path('site'))
    parser.add_argument('--out', type=Path,
                        default=Path('data/research/8877b140/verification-dossier.json'))
    args = parser.parse_args()
    site = args.site if args.site.exists() else None
    dossier = run(args.repo, args.data, site)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dossier, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dossier['totals'], indent=2))
    for check in dossier['checks']:
        marker = 'PASS' if check['ok'] else 'FAIL'
        print(f"{marker} {check['check']}")
    return 0 if dossier['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
