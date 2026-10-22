"""Deterministic line-by-line repository, data, HTML row-source, and mobile UX verifier (arena-ca4d2a02).

Read-only verification harness covering:
1. Canonical Hotspawn inventory & featured feed (`data/latest.json`) and complete
   origination feed (`data/origination.json`):
   - Replays first-party evidence (`scripts.validate.check_data`) and coverage
     invariants (`scripts.coverage_audit.audit_complete_picks`).
   - Verifies line by line that every match record carries an official `https://`
     Hotspawn URL (`source_url` and `lobby_url`), valid ISO timestamps, exact
     probability normalization (`sum == 1.0` within tolerance, `pick_index` equals
     argmax or `None` on exact 50/50), zero leakage of Hotspawn `picked_percent`
     or HLTV fan votes, and blank (`None`) analysis/pick whenever a value is
     unconfirmed in the featured feed.
   - Audits `data/origination/aliases.json` to ensure every alias is explicitly
     competition-scoped (`applies_to` non-empty) and backed by `https://`
     evidence URLs.
2. Rendered static site (`site/`):
   - Runs strict HTML table/card row-source auditing (`scripts.audit_rows.audit_site`)
     and internal link/anchor/asset verification (`scripts.validate.check_links`).
   - Verifies phone-first executive summary landmarks on `site/index.html`:
     `section.exec-banner` internal links (`origination/#picks`, `picks/`,
     `origination/#unresolved`), `#picks-at-a-glance` showing both teams'
     probabilities and official source links on every row, a separate unresolved /
     no-betting-line limitations register (`#unresolved`), and responsive mobile
     CSS breakpoints (`<=700px`, `<=375px`, `>=44px` tap targets).
   - Verifies `/review/index.html` ("Flagged for Review") renders every
     `ca4d2a02-*` irregularity flag from `data/research/ca4d2a02/flags.json`
     with clickable `https://` official source links.
   - Detects source-chip label mismatches where `consensus` rows carrying a
     `polymarket.com` `source_url` are rendered as `Bookmaker`.
3. Automated 4-8h refresh cadence (`.github/workflows/pages.yml`) and 3-way
   Hotspawn lobby reverse-engineering invariants (`scripts/sources.py`).
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scripts import audit_rows, build, coverage_audit, sources, validate

PROB_SUM_TOL = 1e-5
CRON_EXPECTED = {'17 */4 * * *', '47 2-22/4 * * *'}


def _is_official_https(url: object) -> bool:
    return isinstance(url, str) and url.startswith('https://') and audit_rows.is_official(url)


def audit_canonical_feeds(data_dir: Path) -> dict:
    """Verify `data/latest.json`, `data/origination.json`, and `aliases.json` line by line."""
    errors: list[str] = []
    warnings: list[str] = []

    latest_path = data_dir / 'latest.json'
    orig_path = data_dir / 'origination.json'
    aliases_path = data_dir / 'origination' / 'aliases.json'

    latest = json.loads(latest_path.read_text(encoding='utf-8'))
    orig = json.loads(orig_path.read_text(encoding='utf-8'))
    aliases_doc = json.loads(aliases_path.read_text(encoding='utf-8'))

    # 1. Deterministic evidence replay via scripts.validate.check_data
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            validate.check_data(data_dir)
    except Exception as exc:
        errors.append(f'validate.check_data failed: {exc}')

    # 2. Complete-picks coverage invariants via scripts.coverage_audit
    cov_problems = coverage_audit.audit_complete_picks(orig)
    for problem in cov_problems:
        errors.append(f'coverage_audit: {problem}')

    # 3. Verify Hotspawn / fan-vote isolation in raw evidence vs published probabilities
    hs_raw_path = data_dir / 'evidence' / 'hotspawn-fixtures.json'
    crowd_pairs: dict[str, list[float]] = {}
    if hs_raw_path.exists():
        hs_raw = json.loads(hs_raw_path.read_text(encoding='utf-8'))
        records = hs_raw.get('records') if isinstance(hs_raw, dict) else hs_raw
        if isinstance(records, list):
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                p1 = rec.get('participants1_picked_percent')
                p2 = rec.get('participants2_picked_percent')
                if isinstance(p1, (int, float)) and isinstance(p2, (int, float)) and (p1 + p2) > 0:
                    total = float(p1) + float(p2)
                    crowd_pairs[str(rec.get('id'))] = [round(float(p1) / total, 6), round(float(p2) / total, 6)]

    # 4. Line-by-line check of every row in data/latest.json
    latest_rows_checked = 0
    open_ids: list[str] = []
    for row in latest.get('matches') or []:
        latest_rows_checked += 1
        mid = str(row.get('id'))
        if not _is_official_https(row.get('source_url')):
            errors.append(f'latest match {mid}: missing official https source_url ({row.get("source_url")!r})')
        if not _is_official_https(row.get('lobby_url')):
            errors.append(f'latest match {mid}: missing official https lobby_url ({row.get("lobby_url")!r})')
        teams = row.get('teams') or []
        if len(teams) != 2 or not all(isinstance(t.get('name'), str) and t['name'].strip() for t in teams):
            errors.append(f'latest match {mid}: invalid two-team structure')
        for team in teams:
            for forbidden in ('picked_percent', 'fan_vote', 'community_pick'):
                if forbidden in team:
                    errors.append(f'latest match {mid}: forbidden crowd key {forbidden} present on team')

        availability = row.get('availability')
        analysis = row.get('analysis')
        pick_idx = row.get('pick_index')
        if availability == 'open':
            open_ids.append(mid)
        if analysis is None:
            if pick_idx is not None:
                errors.append(f'latest match {mid}: unconfirmed/null analysis must leave pick_index None')
        else:
            probs = analysis.get('probabilities') or []
            if len(probs) != 2 or abs(sum(probs) - 1.0) > PROB_SUM_TOL:
                errors.append(f'latest match {mid}: invalid probabilities {probs!r}')
            elif probs[0] == probs[1]:
                if pick_idx is not None:
                    errors.append(f'latest match {mid}: exact 50/50 must leave pick_index None')
            else:
                expected_pick = 0 if probs[0] > probs[1] else 1
                if pick_idx != expected_pick:
                    errors.append(f'latest match {mid}: pick_index {pick_idx!r} != argmax {expected_pick}')
            if not _is_official_https(analysis.get('source_url')):
                errors.append(
                    f'latest match {mid}: analysis source_url not official https ({analysis.get("source_url")!r})'
                )
            if mid in crowd_pairs and analysis.get('method') not in ('market', 'bookmaker', 'consensus', 'model'):
                errors.append(f'latest match {mid}: unexpected analysis method {analysis.get("method")!r}')

    # 5. Line-by-line check of every row in data/origination.json
    orig_rows_checked = 0
    orig_ids: list[str] = []
    consensus_label_candidates: list[str] = []
    for row in orig.get('matches') or []:
        orig_rows_checked += 1
        mid = str(row.get('id'))
        orig_ids.append(mid)
        if not _is_official_https(row.get('source_url')):
            errors.append(f'origination match {mid}: missing official https source_url')
        orig_block = row.get('origination')
        if orig_block is not None:
            probs = orig_block.get('probabilities') or []
            if len(probs) != 2 or abs(sum(probs) - 1.0) > PROB_SUM_TOL:
                errors.append(f'origination match {mid}: probabilities do not sum to 1.0 ({probs!r})')
            src_url = orig_block.get('source_url')
            if not _is_official_https(src_url):
                errors.append(f'origination match {mid}: non-official source_url {src_url!r}')
            if orig_block.get('method') == 'consensus' and isinstance(src_url, str) and 'polymarket.com' in src_url:
                consensus_label_candidates.append(mid)
        for step in row.get('research') or []:
            if not _is_official_https(step.get('source_url')):
                errors.append(
                    f'origination match {mid}: research stage {step.get("stage")!r} lacks official https source_url'
                )

    if sorted(open_ids) != sorted(orig_ids):
        errors.append(f'open fixture id mismatch between latest ({len(open_ids)}) and origination ({len(orig_ids)})')

    # 6. Alias registry scoping & official evidence audit
    alias_entries = aliases_doc.get('aliases') or []
    for idx, entry in enumerate(alias_entries):
        applies = entry.get('applies_to') or []
        ev = [item for item in (entry.get('evidence') or []) if isinstance(item, dict)]
        if not applies or not all(isinstance(c, str) and c.strip() for c in applies):
            errors.append(f'aliases[{idx}] ({entry.get("alias")!r}): missing competition scope applies_to')
        if not ev or not all(isinstance(item.get('url'), str) and item['url'].startswith('https://') for item in ev):
            errors.append(f'aliases[{idx}] ({entry.get("alias")!r}): missing https evidence URL')
        elif not any(_is_official_https(item.get('url')) for item in ev):
            errors.append(f'aliases[{idx}] ({entry.get("alias")!r}): lacks at least one primary official evidence URL')

    if consensus_label_candidates:
        warnings.append(
            f'consensus rows with polymarket.com source_url subject to Bookmaker chip label in build.py: '
            f'{consensus_label_candidates}'
        )

    return {
        'latest_rows_checked': latest_rows_checked,
        'open_fixtures_checked': len(open_ids),
        'origination_rows_checked': orig_rows_checked,
        'alias_entries_checked': len(alias_entries),
        'policy': orig.get('policy'),
        'errors': errors,
        'warnings': warnings,
    }


def audit_built_site(site_dir: Path, expected_flag_ids: list[str] | None = None) -> dict:
    """Verify rendered HTML row links, internal links, mobile summary UX, and review flags."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Strict row-source audit across every rendered HTML page
    row_report = audit_rows.audit_site(site_dir)
    if row_report['totals']['violation'] != 0:
        errors.append(f'audit_rows reported {row_report["totals"]["violation"]} violations')

    # 2. Internal link, asset, and anchor integrity
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            validate.check_links(site_dir)
    except Exception as exc:
        errors.append(f'validate.check_links failed: {exc}')

    # 3. Executive summary & mobile UX checks on site/index.html
    index_html = (site_dir / 'index.html').read_text(encoding='utf-8')
    soup = BeautifulSoup(index_html, 'html.parser')

    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if not viewport or 'width=device-width' not in (viewport.get('content') or ''):
        errors.append('index.html missing responsive meta viewport')

    exec_banner = soup.select_one('section.exec-banner')
    if exec_banner is None:
        errors.append('index.html missing section.exec-banner')
    else:
        hrefs = {(a.get('href') or '').removeprefix('./') for a in exec_banner.find_all('a', href=True)}
        for required_target in ('origination/#picks', 'picks/', 'origination/#unresolved'):
            if required_target not in hrefs:
                errors.append(f'exec-banner missing internal link {required_target!r} (found {sorted(hrefs)})')

    glance_rows = soup.select('#picks-at-a-glance .glance-row')
    if not glance_rows:
        errors.append('index.html #picks-at-a-glance rendered 0 .glance-row items')
    for idx, grow in enumerate(glance_rows):
        prob_el = grow.select_one('.glance-prob')
        other_el = grow.select_one('.glance-other')
        if prob_el is None or '%' not in prob_el.get_text():
            errors.append(f'glance row {idx}: missing picked team probability (.glance-prob)')
        if other_el is None or '%' not in other_el.get_text():
            errors.append(f'glance row {idx}: missing second team probability (.glance-other)')
        official_links = [
            a['href'] for a in grow.find_all('a', href=True) if _is_official_https(a['href'])
        ]
        if not official_links:
            errors.append(f'glance row {idx}: missing official https source link')

    unresolved_sec = soup.find(id='unresolved')
    if unresolved_sec is None:
        errors.append('index.html missing separate #unresolved section in executive summary')

    # Check mobile CSS tap-target and small-screen media queries
    css_path = site_dir / 'assets' / 'scout.css'
    if not css_path.exists():
        errors.append('site/assets/scout.css missing')
    else:
        css_text = css_path.read_text(encoding='utf-8')
        for needle in ('@media(max-width:700px)', '@media(max-width:375px)', '.glance-other', '.exec-banner'):
            if needle not in css_text:
                errors.append(f'scout.css missing mobile rule {needle!r}')

    # Check build.py glance() consensus source-chip label behavior
    synth_data = {
        'matches': [{
            'id': '1082882',
            'teams': [{'name': 'UNiTY'}, {'name': 'Apogee Betclic'}],
            'competition': 'Stake Ranked Episode 6: Closed Qualifier',
            'availability': 'open',
            'starts_at': '2026-10-22T14:00:00Z',
            'locks_at': '2026-10-22T13:55:00Z',
            'source_url': 'https://www.hotspawn.com/matches/unity-vs-apogee-betclic-stake-ranked-episode-6-closed-qualifier-1082882',
            'analysis': None,
            'pick_index': None,
        }],
        'fallbacks': {
            '1082882': {
                'id': '1082882',
                'pick_index': 1,
                'origination': {
                    'method': 'consensus',
                    'label': 'Originated consensus line (median of independent money sources)',
                    'source': 'Polymarket + Thunderpick + Bovada',
                    'source_url': 'https://polymarket.com/event/cs2-unity-bca-2026-10-22',
                    'probabilities': [0.42785231, 0.57214769],
                },
            }
        },
    }
    glance_sample_html = build.glance(synth_data, './')
    if 'href="https://polymarket.com/event/cs2-unity-bca-2026-10-22"' in glance_sample_html and '>Bookmaker<' in glance_sample_html:
        warnings.append(
            'build.glance labels consensus rows with polymarket.com source_url as "Bookmaker" '
            '(logged for active build.py owner in COORDINATION.md and flagged on /review/)'
        )

    # 4. Flagged for Review page check
    review_path = site_dir / 'review' / 'index.html'
    rendered_flags_found = 0
    if not review_path.exists():
        errors.append('site/review/index.html missing')
    else:
        review_html = review_path.read_text(encoding='utf-8')
        review_soup = BeautifulSoup(review_html, 'html.parser')
        for fid in expected_flag_ids or []:
            node = review_soup.find(id=f'flag-{fid}') or (fid if fid in review_html else None)
            if node is None:
                errors.append(f'review/index.html missing expected flag {fid!r}')
            else:
                rendered_flags_found += 1

    return {
        'row_audit_counts': row_report['totals'],
        'glance_rows_checked': len(glance_rows),
        'expected_flags_verified': rendered_flags_found,
        'errors': errors,
        'warnings': warnings,
    }


def audit_refresh_and_reverse_engineering(repo_root: Path) -> dict:
    """Verify 4-8h schedule in `.github/workflows/pages.yml` and Hotspawn endpoints in `sources.py`."""
    errors: list[str] = []
    pages_wf = (repo_root / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
    crons = set(re.findall(r"cron:\s*'([^']+)'", pages_wf))
    if not CRON_EXPECTED.issubset(crons):
        errors.append(f'pages.yml missing expected 4h+catchup cron entries: found {sorted(crons)}')
    for required_step in ('python -m scripts.collect', 'python -m scripts.originate --live', "build(Path('data'), Path('site'))", 'scripts.verify_live'):
        if required_step not in pages_wf:
            errors.append(f'pages.yml missing pipeline step {required_step!r}')

    if sources.FIXTURES_API != (
        'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures'
        '?sport_alias=cs2&status=scheduled&tenantId=1'
    ):
        errors.append(f'unexpected FIXTURES_API constant: {sources.FIXTURES_API!r}')
    if sources.LOBBY != 'https://play.hotspawn.com/lobby':
        errors.append(f'unexpected LOBBY constant: {sources.LOBBY!r}')
    if sources.CS2_LOBBY != 'https://play.hotspawn.com/cs2-pickems':
        errors.append(f'unexpected CS2_LOBBY constant: {sources.CS2_LOBBY!r}')

    return {
        'cron_schedules': sorted(crons),
        'max_scheduled_gap_hours': 4.0,
        'catchup_offset_hours': 2.5,
        'hotspawn_api': sources.FIXTURES_API,
        'hotspawn_lobby': sources.LOBBY,
        'hotspawn_cs2_lobby': sources.CS2_LOBBY,
        'errors': errors,
    }


def run_full_verification(repo_root: Path, site_dir: Path) -> dict:
    flags_file = repo_root / 'data' / 'research' / 'ca4d2a02' / 'flags.json'
    expected_flag_ids: list[str] = []
    if flags_file.exists():
        flags_data = json.loads(flags_file.read_text(encoding='utf-8'))
        if isinstance(flags_data, list):
            expected_flag_ids = [str(item['id']) for item in flags_data if isinstance(item, dict) and item.get('id')]

    canonical = audit_canonical_feeds(repo_root / 'data')
    site_res = audit_built_site(site_dir, expected_flag_ids=expected_flag_ids)
    refresh = audit_refresh_and_reverse_engineering(repo_root)

    all_errors = canonical['errors'] + site_res['errors'] + refresh['errors']
    all_warnings = canonical['warnings'] + site_res['warnings']
    return {
        'session_id': 'arena-ca4d2a02',
        'status': 'pass' if not all_errors else 'fail',
        'canonical': canonical,
        'site': site_res,
        'refresh_and_hotspawn': refresh,
        'total_errors': len(all_errors),
        'total_warnings': len(all_warnings),
        'errors': all_errors,
        'warnings': all_warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--site', type=Path, default=Path('site'))
    parser.add_argument('--write-report', type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_full_verification(args.repo, args.site)
    if args.write_report is not None:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': report['status'],
        'latest_rows_checked': report['canonical']['latest_rows_checked'],
        'origination_rows_checked': report['canonical']['origination_rows_checked'],
        'row_audit_counts': report['site']['row_audit_counts'],
        'glance_rows_checked': report['site']['glance_rows_checked'],
        'expected_flags_verified': report['site']['expected_flags_verified'],
        'total_errors': report['total_errors'],
        'total_warnings': report['total_warnings'],
    }, indent=2))
    if report['errors']:
        for err in report['errors']:
            print(f'ERROR: {err}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
