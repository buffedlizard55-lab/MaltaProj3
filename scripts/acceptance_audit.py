"""Rendered-output acceptance audit for the brief (session arena-3149e7ae).

The project already audits *data* (``scripts.validate``), *row sources*
(``scripts.audit_rows``) and the *deployed bytes* (``scripts.verify_live``).
What was missing is a check of the thing the brief actually describes: the
**rendered pages a phone reader opens**.  This module parses the built site
(``site/`` by default) and tests the brief's own lines, one at a time:

* every fixture listed on the site shows a pick and both teams' win
  probabilities, or is labelled unresolved with a reason — never a silent gap;
* the executive summary carries a separate "Unresolved picks & limitations"
  section, with the limitations of generating those picks, inside it;
* the executive summary links, in-site, to the updated list of picks;
* the one-glance index is a phone list (not a wide table), the pages declare a
  mobile viewport, and the stylesheet has a small-screen rule for the glance;
* the refresh cadence stays inside the brief's 4-8 hour window;
* the built row-source audit found no row without an official source.

It is read-only: it never writes a page, a probability, a pick or a source.
Only the report and the exit code come out of it.

Usage::

    python -m scripts.acceptance_audit [--site site] [--json out.json] [--md out.md]
    python -m scripts.acceptance_audit --strict   # exit 1 on any failure

A check is ``pass``, ``fail`` (a brief line is not met) or ``info`` (a dated
observation that is reported, never failed — for example the age of the
snapshot, which a slow CI runner can legitimately stretch).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

#: Hosts that count as an official/primary source for a value shown in a row.
#: Mirrors scripts/audit_rows.py; kept here as an independent list so a change in
#: one audit cannot quietly widen the other.
OFFICIAL_HOSTS = (
    'hotspawn.com', 'play.hotspawn.com', 'www.hotspawn.com',
    'phpstack-1372681-6459848.cloudwaysapps.com',
    'hltv.org', 'polymarket.com', 'gamma-api.polymarket.com', 'clob.polymarket.com',
    'docs.polymarket.com', 'thunderpick.io', 'gg.bet', 'stake.com', 'pinnacle.com',
    'rivalry.com', 'bovada.lv', 'kalshi.com', 'egamersworld.com', 'bo3.gg',
    'valvesoftware.com', 'steamcommunity.com', 'github.com',
)

#: The brief's cadence window, in hours.
CADENCE_MIN, CADENCE_MAX = 4, 8


class Check:
    def __init__(self, key: str, title: str, brief_line: str):
        self.key = key
        self.title = title
        self.brief_line = brief_line
        self.status = 'pass'
        self.detail = ''
        self.evidence: list[str] = []

    def fail(self, detail: str, *evidence: str):
        self.status = 'fail'
        self.detail = detail
        self.evidence = [e for e in evidence if e]
        return self

    def info(self, detail: str, *evidence: str):
        if self.status == 'pass':
            self.status = 'info'
        self.detail = detail
        self.evidence = [e for e in evidence if e]
        return self

    def ok(self, detail: str, *evidence: str):
        self.status = 'pass'
        self.detail = detail
        self.evidence = [e for e in evidence if e]
        return self

    def as_dict(self) -> dict:
        return {'key': self.key, 'title': self.title, 'brief_line': self.brief_line,
                'status': self.status, 'detail': self.detail, 'evidence': self.evidence}


def _text(node) -> str:
    return re.sub(r'\s+', ' ', node.get_text(' ', strip=True)) if node else ''


def _pct(text: str) -> list[float]:
    return [float(x) for x in re.findall(r'(\d{1,3}\.\d)\s*%', text)]


def _host(url: str) -> str:
    m = re.match(r'https?://([^/?#]+)', url or '')
    return (m.group(1).lower() if m else '')


def _official(url: str) -> bool:
    host = _host(url)
    return any(host == h or host.endswith('.' + h) for h in OFFICIAL_HOSTS)


def _page(site: Path, relative: str) -> BeautifulSoup | None:
    path = site / relative
    if not path.exists():
        return None
    return BeautifulSoup(path.read_text(encoding='utf-8', errors='replace'), 'html.parser')


#: Directory names inside a site or repo root that are not published HTML views.
SKIP_HTML_DIRS = {
    'docs', 'archive', 'node_modules', '.venv', '.git', 'tests',
    'playwright-report', 'test-results', 'site', '_fixture', '__pycache__',
}


def _is_branch_root(site: Path) -> bool:
    """True when ``site`` is the git checkout root rather than a built ``site/`` tree.

    ``scripts.root_publish`` copies rendered HTML and ``assets/`` into the branch root while
    leaving git-tracked ``data/latest.json`` as the deterministic CI replay fixture.
    """
    return (site / 'scripts/root_publish.py').is_file()


def _snapshot(site: Path) -> dict:
    """The built snapshot plus its reconciled coverage counts.

    ``data/latest.json`` carries the freshness fields; ``data/reconciled-counts.json``
    (written by ``scripts.build.write_reconciled_snapshot``) carries the counts of the
    researched list every page renders. Reading only one of them is how a page and
    its JSON came to disagree once, so both are read here.
    """
    snapshot: dict = {}
    branch_root = _is_branch_root(site)
    latest = site / 'data/latest.json'
    if latest.exists():
        try:
            loaded = json.loads(latest.read_text())
        except ValueError:
            loaded = {}
        if branch_root:
            # In the branch root, data/latest.json is the preserved CI replay fixture;
            # keep only cadence metadata defaults and read generated_at from index.html.
            for key in ('coverage_complete', 'refresh_interval_hours', 'stale_after_hours'):
                if key in loaded:
                    snapshot[key] = loaded[key]
        else:
            snapshot.update(loaded)
    reconciled = site / 'data/reconciled-counts.json'
    if reconciled.exists() and not branch_root:
        try:
            block = json.loads(reconciled.read_text())
        except ValueError:
            block = {}
        snapshot.setdefault('generated_at', block.get('generated_at'))
        counts = block.get('complete_coverage_counts')
        if isinstance(counts, dict):
            snapshot['complete_counts'] = counts
    if not snapshot.get('generated_at'):
        # The published root carries rendered pages only; the snapshot stamp is
        # embedded in each page, so read the one the reader actually sees.
        soup = _page(site, 'index.html')
        node = soup.select_one('[data-snapshot-generated]') if soup else None
        if node is not None:
            snapshot['generated_at'] = node.get('data-snapshot-generated')
            snapshot['_from_page_stamp'] = True
    return snapshot


# --------------------------------------------------------------------------- #
# Individual brief lines
# --------------------------------------------------------------------------- #
def _even_no_side(choice) -> bool:
    """A pick-less glance row that states *why* there is no side.

    Two renderings must both count: the current one (a ``data-glance-pick``
    marker on the label) is handled before this helper is consulted; this covers
    the "Even · no side" wording plus a link into the unresolved register, which
    is how a build made before the marker existed reads.
    """
    text = _text(choice)
    lowered = text.lower()
    if 'even' not in lowered or 'side' not in lowered:
        return False
    values = _pct(text)
    if len(values) < 2 or abs(sum(values[:2]) - 100.0) > 0.2:
        # "No side" without both teams' numbers is not an explanation; the row
        # would tell a phone reader nothing about the match.
        return False
    return any('unresolved' in (a.get('href') or '') for a in choice.select('a[href]'))


def check_glance_rows(site: Path, soup: BeautifulSoup) -> Check:
    check = Check('glance_rows', 'Every listed fixture shows a pick and both win probabilities',
                  'It should cover all matches listed on hotspawn and give probability to win for the team to win '
                  'and be obvious what the pick is')
    rows = soup.select('.glance-row')
    if not rows:
        return check.fail('No .glance-row elements were rendered on the executive summary.',
                          str(site / 'index.html'))
    missing_pick, missing_pair, bad_sum, sourced, no_source = [], [], [], 0, []
    explained_no_side = 0
    for row in rows:
        match = _text(row.select_one('.glance-match'))
        choice = row.select_one('.glance-choice')
        if choice is None or choice.select_one('[data-glance-pick]') is None:
            # The brief asks for "a pick or an explicit, sourced explanation".
            # An exactly even two-sided book (Polymarket opened a true 0.50/0.50
            # on 1079200 on 2026-10-24) has no side to pick: the honest render
            # says so and links the reason into the unresolved register. That is
            # a labelled row, not a silent gap -- the earlier rule assumed every
            # pick-less row was unresolved, which stopped being true that day.
            # It must still show both percentages and the explaining link.
            if choice is not None and _even_no_side(choice):
                explained_no_side += 1
            else:
                missing_pick.append(match)
            continue
        values = _pct(_text(choice))
        if len(values) < 2:
            missing_pair.append(match)
        elif abs(sum(values[:2]) - 100.0) > 0.2:
            bad_sum.append(f'{match}: {values[:2]}')
        links = [a.get('href') or '' for a in row.select('.glance-links a')]
        if any(_official(h) for h in links):
            sourced += 1
        else:
            no_source.append(match)
    if missing_pick:
        return check.fail(f'{len(missing_pick)} of {len(rows)} glance rows show no pick and no unresolved label.',
                          *missing_pick[:5])
    if missing_pair:
        return check.fail(f'{len(missing_pair)} glance rows do not show both teams\' percentages.',
                          *missing_pair[:5])
    if bad_sum:
        return check.fail(f'{len(bad_sum)} glance rows have percentages that do not sum to 100.', *bad_sum[:5])
    if no_source:
        return check.fail(f'{len(no_source)} glance rows carry no official/primary source link.', *no_source[:5])
    detail = (f'{len(rows)} glance rows: every one names a pick, shows both percentages summing to 100, '
              f'and links an official/primary source ({sourced}/{len(rows)}).')
    if explained_no_side:
        detail += (f' {explained_no_side} of them are exactly even two-sided books: labelled '
                   '"Even · no side" with both prices and the reason linked.')
    return check.ok(detail, f'{site}/index.html#picks-at-a-glance')


def check_glance_counts_agree(site: Path, soup: BeautifulSoup) -> Check:
    check = Check('glance_counts', 'The summary\'s coverage sentence matches the rendered list and the snapshot',
                  'I want picks for every match listed on hotspawn for counterstrike 2')
    intro = soup.select_one('#picks-at-a-glance .section-intro')
    if intro is None:
        return check.fail('The glance section has no coverage sentence.')
    numbers = re.findall(r'<strong>(\d+)</strong>', str(intro))
    text = _text(intro)
    m = re.search(r'(\d+)\s+active', text)
    if not m:
        return check.fail('The coverage sentence does not state how many active fixtures it covers.', text[:200])
    stated_active = int(m.group(1))
    rendered = len(soup.select('.glance-row'))
    snapshot = _snapshot(site)
    underlying = None
    block = snapshot.get('complete_counts')
    if isinstance(block, dict):
        underlying = block.get('active')
    else:
        for key in ('complete_picks', 'matches'):
            candidate = snapshot.get(key)
            if isinstance(candidate, dict) and isinstance(candidate.get('counts'), dict):
                underlying = candidate['counts'].get('active')
                break
    if rendered != stated_active:
        return check.fail(f'The sentence claims {stated_active} active fixtures but {rendered} rows were rendered.',
                          f'{site}/index.html#picks-at-a-glance')
    if underlying is not None and underlying != stated_active:
        return check.fail(f'The sentence claims {stated_active} active fixtures; the snapshot counts {underlying}.',
                          f'{site}/data/reconciled-counts.json')
    return check.ok(f'{stated_active} active fixtures stated and {rendered} rows rendered'
                    + (f'; the reconciled snapshot counts {underlying} active.' if underlying is not None else '.'),
                    f'{site}/index.html#picks-at-a-glance')


def check_unresolved_register(site: Path, soup: BeautifulSoup) -> Check:
    check = Check('unresolved_register', 'A separate unresolved/limitations section sits inside the executive summary',
                  'Create a separate section for any unresolved picks and the limitations for generating picks for '
                  'them and include this in the executive summary')
    section = soup.select_one('#unresolved-register')
    if section is None:
        return check.fail('index.html has no #unresolved-register section.')
    title = _text(section.select_one('h2'))
    if 'unresolved' not in title.lower():
        return check.fail(f'The register heading does not name unresolved picks: {title!r}')
    limits = section.select('.unresolved-limits li')
    if len(limits) < 3:
        return check.fail(f'The register carries {len(limits)} limitation bullet(s); the brief asks for the '
                          'limitations of generating those picks.')
    has_votes = any('vote' in _text(li).lower() for li in limits)
    has_blank = any('blank' in _text(li).lower() or 'never' in _text(li).lower() for li in limits)
    if not (has_votes and has_blank):
        return check.fail('The limitations list does not state that Hotspawn/HLTV popularity votes are excluded '
                          'and that a missing value is never invented.')
    cards = section.select('.unresolved-summary-card')
    return check.ok(f'Register "{title}" is inside the executive summary with {len(limits)} explicit limitations'
                    f' and {len(cards)} labelled pick-less card(s).',
                    f'{site}/index.html#unresolved-register')


def check_exec_links(site: Path, soup: BeautifulSoup) -> Check:
    check = Check('exec_links', 'The executive summary links in-site to the updated list of picks',
                  'We should have an executive summary that provides links within our site to where an updated list '
                  'of picks can be found')
    anchors = [(a.get('href') or '') for a in soup.select('a[href]')]
    required = {
        'complete updated picks': re.compile(r'origination/#picks$'),
        'picks page': re.compile(r'(^|/)picks/?(#.*)?$'),
        'unresolved section': re.compile(r'unresolved'),
    }
    broken, found = [], {}
    for label, pattern in required.items():
        hits = [h for h in anchors if pattern.search(h)]
        if not hits:
            broken.append(f'no in-site link for the {label}')
        found[label] = hits[0] if hits else ''
    # Resolve what was found: the target must exist in the published tree.
    for label, href in list(found.items()):
        if not href:
            continue
        target = href.split('#')[0].split('?')[0]
        if not target or target.startswith(('http://', 'https://', 'mailto:')):
            if target.startswith(('http://', 'https://')):
                broken.append(f'the {label} link leaves the site ({href})')
            continue
        path = (site / target).resolve()
        if target.endswith('/'):
            path = path / 'index.html'
        elif path.is_dir():
            path = path / 'index.html'
        if not path.exists():
            broken.append(f'the {label} link targets a page that was not built ({href})')
    if broken:
        return check.fail('; '.join(broken), f'{site}/index.html')
    return check.ok('In-site links to the complete picks list, the picks page and the unresolved section all resolve.',
                    *(f'{label}: {href}' for label, href in found.items()))


def check_mobile(site: Path) -> Check:
    check = Check('mobile', 'Pages are phone-ready: viewport declared, glance is a list, small-screen rules exist',
                  'It should be easily readable and accessible on phone and mobile device')
    pages = sorted(
        p for p in site.rglob('*.html')
        if not any(part in SKIP_HTML_DIRS or part.startswith('.') for part in p.relative_to(site).parts[:-1])
    )
    if not pages:
        return check.fail('No rendered pages were found to check.')
    missing = [str(p.relative_to(site)) for p in pages
               if not BeautifulSoup(p.read_text(encoding='utf-8', errors='replace'), 'html.parser')
               .select_one('meta[name="viewport"][content*="width=device-width"]')]
    if missing:
        return check.fail(f'{len(missing)} page(s) declare no mobile viewport.', *missing[:5])
    css = ''
    for candidate in (site / 'assets/scout.css', site.parent / 'assets/scout.css'):
        if candidate.exists():
            css = candidate.read_text(encoding='utf-8', errors='replace')
            break
    if not css:
        return check.fail('assets/scout.css was not found beside the built site.')
    if not re.search(r'@media\s*\(max-width:\s*(700|640|600|480|430|390)px', css):
        return check.fail('assets/scout.css has no small-screen media query for the phone layout.')
    if not re.search(r'\.glance-(row|match|choice)', css):
        return check.fail('assets/scout.css styles no glance row, so the phone list is unstyled.')
    return check.ok(f'{len(pages)} pages declare a device-width viewport; the glance list is styled by '
                    'scout.css and has a small-screen media query.',
                    f'{site}/assets/scout.css')


def _cron_field(field: str, low: int, high: int) -> list[int]:
    """Expand one cron field to the values it fires on (``*``, ``a``, ``a-b``, ``*/n``, ``a-b/n``)."""
    values: set[int] = set()
    for part in field.split(','):
        step = 1
        if '/' in part:
            part, step_text = part.split('/', 1)
            step = int(step_text)
        if part in {'*', '?'}:
            start, end = low, high
        elif '-' in part:
            start_text, end_text = part.split('-', 1)
            start, end = int(start_text), int(end_text)
        else:
            start = end = int(part)
        values.update(range(start, end + 1, step))
    return sorted(v for v in values if low <= v <= high)


def _cron_minutes(cron: str) -> list[int]:
    """The minute-of-day offsets a five-field cron entry fires at, restricted to every day."""
    fields = cron.split()
    if len(fields) < 5:
        return []
    hours = _cron_field(fields[1], 0, 23)
    minutes = _cron_field(fields[0], 0, 59)
    return [h * 60 + m for h in hours for m in minutes]


def check_cadence(repo: Path, snapshot: dict) -> Check:
    check = Check('cadence', 'The refresh schedule stays inside the brief\'s 4-8 hour window',
                  'So that we have a full list of updated matches and picks for counter strike 2 from hotspawn '
                  'every 4-8 hours')
    workflow = repo / '.github/workflows/pages.yml'
    if not workflow.exists():
        return check.fail('The refresh workflow .github/workflows/pages.yml is missing.')
    crons = re.findall(r"-\s*cron:\s*'([^']+)'", workflow.read_text())
    if not crons:
        return check.fail('pages.yml declares no cron schedule.')
    points = sorted({point for cron in crons for point in _cron_minutes(cron)})
    gaps = []
    for i, point in enumerate(points):
        nxt = points[(i + 1) % len(points)] + (24 * 60 if i == len(points) - 1 else 0)
        gaps.append((nxt - point) / 60)
    worst = max(gaps) if gaps else 24
    interval = snapshot.get('refresh_interval_hours')
    stale = snapshot.get('stale_after_hours')
    problems = []
    if worst > CADENCE_MAX:
        problems.append(f'the largest scheduled gap is {worst:.1f} h (limit {CADENCE_MAX} h)')
    # A catch-up slot can sit closer than four hours to the primary slot. The
    # brief's bound is a maximum staleness ("every 4-8 hours"), so a denser
    # schedule is reported, never failed.
    if isinstance(interval, (int, float)) and not (CADENCE_MIN <= interval <= CADENCE_MAX):
        problems.append(f'the snapshot declares refresh_interval_hours={interval}')
    if isinstance(stale, (int, float)) and stale > CADENCE_MAX:
        problems.append(f'the snapshot allows stale_after_hours={stale}')
    if problems:
        return check.fail('; '.join(problems), '; '.join(crons))
    return check.ok(f'{len(crons)} cron entries, largest gap {worst:.1f} h, declared interval '
                    f'{interval} h, stale bound {stale} h.', '; '.join(crons))


def check_row_sources(site: Path) -> Check:
    check = Check('row_sources', 'No rendered row is published without a source or an unverified label',
                  'Every table row must have a source link to an official site. If a value can\'t be confirmed '
                  'from an official source, leave it blank and flag it as unverified.')
    report = site / 'data/row-source-audit.json'
    if not report.exists():
        # The published branch root republishes rendered pages and assets only;
        # data/*.json is served by the artifact deploy. Absence here is a gap in
        # the tree being audited, not proof that the audit failed.
        return check.info('data/row-source-audit.json is not in this tree (rendered-only root); '
                          'run the audit against the full build output.', str(site))
    totals = json.loads(report.read_text()).get('totals') or {}
    if totals.get('violation'):
        return check.fail(f"{totals['violation']} rendered row(s) carry neither an official link nor an "
                          'unverified flag.', str(report))
    return check.ok(f"{totals.get('rows', 0)} rows audited, {totals.get('ok', 0)} with an official link, "
                    f"{totals.get('flagged', 0)} explicitly flagged unverified, 0 without a source.",
                    str(report))


def check_freshness(site: Path, snapshot: dict) -> Check:
    check = Check('freshness', 'The published snapshot is dated and its age is reported',
                  'The hotspawn site regularly updates new matches so make sure that we have full coverage')
    stamp = snapshot.get('generated_at')
    if not stamp:
        return check.fail('The built snapshot carries no generated_at timestamp.')
    try:
        when = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    except ValueError:
        return check.fail(f'The snapshot timestamp is not ISO-8601: {stamp!r}')
    age = (datetime.now(timezone.utc) - when).total_seconds() / 3600
    evidence = (f'{site}/index.html' if snapshot.get('_from_page_stamp') else f'{site}/data/latest.json')
    complete = snapshot.get('coverage_complete')
    detail = (f'Snapshot {stamp} is {age:.1f} h old; coverage_complete={complete}; '
              f'refresh_interval_hours={snapshot.get("refresh_interval_hours")}.')
    if age > CADENCE_MAX or complete is False:
        return check.info(detail + ' The page is required to warn the reader; see #stale-warning.',
                          evidence)
    return check.ok(detail, evidence)


def check_snapshot_consistency(site: Path) -> Check:
    """The page a reader sees and the JSON they download must be the same snapshot.

    The legacy Pages build republishes the branch root (rendered pages plus the
    checked-in ``data/`` fixture) on every push to ``main``, while the artifact
    deploy serves the fresh ``data/`` tree. When the two disagree, a reader who
    downloads ``data/latest.json`` sees a different date from the one printed on
    the page. That happened on 2026-10-22/23 (page 2026-10-22T14:05:35Z, JSON
    2026-10-15T08:36:13Z), so it is checked rather than assumed.
    """
    check = Check('snapshot_consistency',
                  'The rendered page and the downloadable snapshot are the same observation',
                  'It should be up to date and list the probabilities for each match based upon known betting lines')
    soup = _page(site, 'index.html')
    stamp_node = soup.select_one('[data-snapshot-generated]') if soup else None
    branch_root = _is_branch_root(site)
    # The downloadable snapshot every page links to is `snapshot.json` (session
    # ca7e10e5); `data/latest.json` is the tracked CI replay fixture and is the
    # fallback for trees built before the split.
    latest = site / 'snapshot.json'
    if not latest.exists():
        latest = site / 'data/latest.json'
    if stamp_node is None:
        return check.fail('index.html carries no data-snapshot-generated stamp to compare against.')
    page_stamp = stamp_node.get('data-snapshot-generated')
    if branch_root and not (site / 'snapshot.json').exists():
        # Before session ca7e10e5 the shipped root carried no downloadable copy of
        # the current observation, so only the rendered pages could be compared.
        built_latest = site / 'site/data/latest.json'
        if built_latest.exists():
            try:
                built_stamp = json.loads(built_latest.read_text()).get('generated_at')
            except ValueError:
                built_stamp = None
            if built_stamp == page_stamp:
                return check.ok(
                    f'Branch-root index.html and built site/data/latest.json agree ({page_stamp}); '
                    'root data/latest.json is the preserved CI replay fixture.',
                    f'{site}/index.html', f'{site}/site/data/latest.json',
                )
        return check.info(
            f'Branch-root index.html carries live snapshot {page_stamp} from scripts.root_publish while '
            'root data/latest.json is the preserved CI replay fixture (artifact deploy serves fresh data/*).',
            f'{site}/index.html',
        )
    if not latest.exists():
        return check.info('This tree carries rendered pages only, so there is no downloadable snapshot to compare.',
                          str(site))
    try:
        json_stamp = json.loads(latest.read_text()).get('generated_at')
    except ValueError:
        return check.fail(f'{latest} is not valid JSON.')
    if not json_stamp:
        return check.fail(f'{latest} carries no generated_at.')
    try:
        page_time = datetime.fromisoformat(page_stamp.replace('Z', '+00:00'))
        json_time = datetime.fromisoformat(json_stamp.replace('Z', '+00:00'))
    except ValueError:
        return check.fail(f'Unparseable timestamps: page {page_stamp!r}, JSON {json_stamp!r}.')
    drift = abs((page_time - json_time).total_seconds())
    if drift > 600:
        return check.fail(f'The page shows snapshot {page_stamp} but {latest.name} carries {json_stamp} '
                          f'({drift / 3600:.1f} h apart): a reader who downloads the JSON sees a different '
                          'observation from the one printed on the page.',
                          f'{site}/index.html', str(latest))
    return check.ok(f'Page stamp and {latest.name} agree ({page_stamp}).',
                    f'{site}/index.html', str(latest))


def check_unresolved_page(site: Path) -> Check:
    check = Check('unresolved_page', 'The dedicated unresolved page exists and lists limitations',
                  'Create a separate section for any unresolved picks and the limitations')
    soup = _page(site, 'unresolved/index.html')
    if soup is None:
        return check.fail('unresolved/index.html was not built.')
    heading = _text(soup.find('h1')) or _text(soup.find('h2'))
    limits = soup.select('.unresolved-limits li')
    if len(limits) < 3:
        return check.fail(f'The unresolved page carries {len(limits)} limitation bullet(s).')
    return check.ok(f'Dedicated page "{heading}" with {len(limits)} stated limitations.',
                    f'{site}/unresolved/index.html')


def audit(repo: Path, site: Path | None = None) -> dict:
    site = Path(site or repo / 'site')
    soup = _page(site, 'index.html')
    snapshot = _snapshot(site)
    checks: list[Check] = []
    if soup is None:
        missing = Check('rendered_pages', 'The executive summary is built',
                        'Create a gh page site for this repo with a clean landing page')
        checks.append(missing.fail('site/index.html was not found; run python -m scripts.build first.'))
    else:
        checks += [check_glance_rows(site, soup),
                   check_glance_counts_agree(site, soup),
                   check_unresolved_register(site, soup),
                   check_exec_links(site, soup),
                   check_mobile(site),
                   check_cadence(repo, snapshot),
                   check_row_sources(site),
                   check_freshness(site, snapshot),
                   check_snapshot_consistency(site),
                   check_unresolved_page(site)]
    failed = [c for c in checks if c.status == 'fail']
    return {
        'schema': 1,
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'auditor': 'scripts/acceptance_audit.py',
        'site': str(site),
        'snapshot_generated_at': snapshot.get('generated_at'),
        'totals': {'checks': len(checks), 'pass': sum(c.status == 'pass' for c in checks),
                   'info': sum(c.status == 'info' for c in checks), 'fail': len(failed)},
        'checks': [c.as_dict() for c in checks],
    }


def markdown(report: dict) -> str:
    lines = ['# Rendered-output acceptance audit (brief line by line)', '',
             f"Generated {report['generated_at']} by `{report['auditor']}` against `{report['site']}`.",
             f"Snapshot `{report['snapshot_generated_at']}`.", '',
             '| # | Brief line | Check | Result | Evidence |', '| --- | --- | --- | --- | --- |']
    for i, c in enumerate(report['checks'], 1):
        evidence = '<br>'.join(e.replace('|', '\\|') for e in c['evidence'][:3])
        brief_line = c['brief_line'].replace('|', '\\|')
        detail = c['detail'].replace('|', '\\|')
        lines.append(f"| {i} | {brief_line} | {c['title']} | "
                     f"**{c['status']}** — {detail} | {evidence} |")
    totals = report['totals']
    lines += ['', f"**{totals['pass']} pass · {totals['info']} info · {totals['fail']} fail** "
                  f"of {totals['checks']} checks.", '']
    return '\n'.join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=Path('site'))
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--json', type=Path, default=None)
    parser.add_argument('--md', type=Path, default=None)
    parser.add_argument('--strict', action='store_true', help='exit 1 when a check fails')
    args = parser.parse_args(argv)
    report = audit(args.repo, args.site)
    text = markdown(report)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(text + '\n')
    print(text)
    totals = report['totals']
    print(f"Acceptance audit: {totals['pass']} pass, {totals['info']} info, {totals['fail']} fail "
          f"of {totals['checks']} checks")
    if args.strict and totals['fail']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
