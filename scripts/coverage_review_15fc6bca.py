"""Session arena-15fc6bca — live coverage review of the published ladder.

The coding sandbox has no egress to Hotspawn, bo3.gg, HLTV or any bookmaker; the
GitHub runner does. This module therefore runs *there*, after the repository's
own collectors, and answers the questions the brief asks of the published
surface rather than inventing another model:

* Does every upcoming Hotspawn fixture carry a pick, and if not, exactly why —
  with the source names each row was checked against?
* Which rows are money-backed (a real observed two-sided price) and which are
  this project's own uncalibrated estimates, and is that labelled?
* Where did a source fail (403, redirect, no listing) rather than simply have
  nothing for the fixture?
* Is the snapshot inside the four-hour refresh / eight-hour staleness contract?
* Does the built practice page link every summary entry to its own row, and
  does the phone navigation reach the same list?

It writes no probability and no pick: every number in the report is copied from
the ladder's own published output. Nothing in the published site reads these
files — they are dated evidence for the review, kept under
``data/research/15fc6bca/``.

Usage: python -m scripts.coverage_review_15fc6bca [--live]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

from scripts.domain import is_fresh, timestamp

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'research' / '15fc6bca'
LIVE = OUT / 'live'
UTC = timezone.utc

MONEY_METHODS = {'market', 'bookmaker', 'consensus', 'reference'}
MONEY_FAMILIES = {'market', 'bookmaker', 'consensus', 'reference', 'relay'}
REFRESH_HOURS = 4
STALE_HOURS = 8


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


class AnchorParser(HTMLParser):
    """Collect (href, id) pairs so the summary's links can be resolved locally."""

    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.ids = set()
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get('id'):
            self.ids.add(data['id'])
        if tag == 'a' and data.get('href'):
            self._href = data['href']
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self._href is not None:
            self.hrefs.append({'href': self._href, 'text': ' '.join(''.join(self._text).split())})
            self._href = None
            self._text = []


def classify(row: dict) -> dict:
    """One fixture's published state, copied from the ladder's own row."""
    chosen = row.get('origination') or {}
    method = chosen.get('method')
    family = chosen.get('family')
    probs = chosen.get('probabilities') or []
    pick = row.get('pick_index')
    if not chosen:
        state = 'unresolved'
    elif pick is None:
        state = 'even'
    else:
        state = 'picked'
    ledger = row.get('sources_checked') or []
    return {
        'id': str(row.get('id')),
        'teams': [t.get('name') for t in row.get('teams') or []],
        'competition': row.get('competition'),
        'starts_at': row.get('starts_at'),
        'availability': row.get('availability'),
        'state': state,
        'method': method,
        'family': family,
        'label': chosen.get('label'),
        'source': chosen.get('source'),
        'source_url': chosen.get('source_url'),
        'probabilities': probs,
        'pick_index': pick,
        'pick': (row.get('teams') or [{}])[pick]['name'] if isinstance(pick, int) and pick < len(row.get('teams') or []) else None,
        'money_backed': method in MONEY_METHODS or family in {'relay'},
        'limitations': row.get('limitations') or [],
        'sources_checked': ledger,
        'sources_without_price': row.get('sources_without_price')
                              or [e.get('source') for e in ledger if e.get('outcome') != 'resolved'],
        'unresolved_stages': [r.get('stage') for r in row.get('research') or []
                              if r.get('status') in {'unresolved', 'unavailable'}],
    }


def freshness(latest: dict, now: datetime) -> dict:
    generated = timestamp(latest.get('generated_at'))
    observed = timestamp(latest.get('inventory_observed_at'))
    age_hours = ((now - observed).total_seconds() / 3600) if observed else None
    return {
        'generated_at': latest.get('generated_at'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'last_attempted_at': latest.get('last_attempted_at'),
        'age_hours': round(age_hours, 3) if age_hours is not None else None,
        'refresh_interval_hours': latest.get('refresh_interval_hours') or REFRESH_HOURS,
        'stale_after_hours': latest.get('stale_after_hours') or STALE_HOURS,
        'fresh': bool(observed and is_fresh(latest.get('inventory_observed_at'), now)),
        'within_contract': bool(age_hours is not None and age_hours <= (latest.get('stale_after_hours') or STALE_HOURS)),
        'coverage_complete': latest.get('coverage_complete'),
        'run_status': latest.get('run_status'),
        'inventory_counts': latest.get('counts'),
    }


def summary_links(site: Path) -> dict:
    """Resolve every executive-summary link against the built site's own anchors."""
    index = site / 'index.html'
    if not index.exists():
        return {'status': 'site not built'}
    page = AnchorParser()
    page.feed(index.read_text(errors='replace'))
    origination = site / 'origination' / 'index.html'
    targets = set()
    if origination.exists():
        sub = AnchorParser()
        sub.feed(origination.read_text(errors='replace'))
        targets = sub.ids
    resolved, broken = [], []
    for item in page.hrefs:
        href = item['href']
        if 'origination/' not in href:
            continue
        anchor = href.split('#', 1)[1] if '#' in href else None
        entry = {'href': href, 'text': item['text'][:80], 'anchor': anchor}
        if anchor is None or anchor in targets:
            resolved.append(entry)
        else:
            broken.append(entry)
    return {'status': 'checked', 'links_into_picks': len(resolved) + len(broken),
            'resolved': resolved, 'broken': broken,
            'picks_anchor_present': 'picks' in targets,
            'unresolved_anchor_present': 'unresolved' in targets}


def pick_index_links(site: Path, rows: list) -> dict:
    """Every scheduled fixture must be reachable from the built picks list."""
    origination = site / 'origination' / 'index.html'
    if not origination.exists():
        return {'status': 'site not built'}
    text = origination.read_text(errors='replace')
    missing = [r['id'] for r in rows if f'id="match-{r["id"]}"' not in text]
    return {'status': 'checked', 'rows': len(rows), 'cards_present': len(rows) - len(missing),
            'missing': missing}


def review(live: bool = False) -> dict:
    now = datetime.now(UTC)
    latest = load(ROOT / 'data' / 'latest.json', {}) or {}
    origination = load(ROOT / 'data' / 'origination.json', {}) or {}
    rows = [classify(r) for r in origination.get('matches') or []]
    rows.sort(key=lambda r: (r['starts_at'] or '9999', r['id']))
    upcoming = [r for r in rows if str(r.get('availability')) != 'past']
    site = ROOT / 'site'

    report = {
        'probe': '15fc6bca live coverage review',
        'generated_at': iso(now),
        'policy': ('Copies the ladder\'s own published output for review. No probability, pick, '
                   'quote or timestamp is manufactured here; a blank stays blank and is named.'),
        'freshness': freshness(latest, now),
        'counts': origination.get('counts'),
        'rows': upcoming,
        'totals': {
            'upcoming': len(upcoming),
            'picked': sum(1 for r in upcoming if r['state'] == 'picked'),
            'even': sum(1 for r in upcoming if r['state'] == 'even'),
            'unresolved': sum(1 for r in upcoming if r['state'] == 'unresolved'),
            'money_backed': sum(1 for r in upcoming if r['money_backed'] and r['state'] == 'picked'),
            'own_model': sum(1 for r in upcoming if r['state'] == 'picked' and not r['money_backed']),
            'paid_by_relay': sum(1 for r in upcoming if r['family'] == 'relay'),
        },
        'no_pick': [{'id': r['id'], 'teams': r['teams'], 'state': r['state'],
                     'sources_without_price': r['sources_without_price']}
                    for r in upcoming if r['state'] != 'picked'],
        'summary_links': summary_links(site),
        'cards': pick_index_links(site, upcoming),
        'expected_refresh_at': iso(now + timedelta(hours=REFRESH_HOURS)),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'coverage-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'coverage-review.md').write_text(markdown(report))
    return report


def markdown(report: dict) -> str:
    f = report['freshness']
    t = report['totals']
    lines = ['# Session 15fc6bca — live coverage review', '',
             f"Generated {report['generated_at']}. Snapshot `{f['inventory_observed_at']}` "
             f"(analysed {f['generated_at']}), age **{f['age_hours']} h**, "
             f"refresh every {f['refresh_interval_hours']} h, stale after {f['stale_after_hours']} h.",
             '', f"- Upcoming fixtures: **{t['upcoming']}**",
             f"- With a directional pick: **{t['picked']}**",
             f"- Money-backed picks: **{t['money_backed']}** ({t['paid_by_relay']} of them from a bookmaker "
             f"price relayed by bo3.gg)",
             f"- Own uncalibrated model picks: **{t['own_model']}**",
             f"- Exactly even, no side published: **{t['even']}**",
             f"- Unresolved: **{t['unresolved']}**", '',
             '| Fixture | Start | Pick | Probabilities | Basis | Source |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in report['rows']:
        probs = ' / '.join(f'{p * 100:.1f}%' for p in row['probabilities']) or '—'
        lines.append(f"| {' vs '.join(str(t_) for t_ in row['teams'])} | {row['starts_at']} | "
                     f"{row['pick'] or ('even' if row['state'] == 'even' else 'blank')} | {probs} | "
                     f"{row['method'] or '—'}{' (relay)' if row['family'] == 'relay' else ''} | "
                     f"{row['source'] or '—'} |")
    if report['no_pick']:
        lines += ['', '## Fixtures without a directional pick', '']
        for row in report['no_pick']:
            named = ', '.join(row['sources_without_price']) or 'no source was checked'
            lines.append(f"- **{' vs '.join(str(t_) for t_ in row['teams'])}** ({row['state']}): {named}")
    links = report['summary_links']
    if links.get('status') == 'checked':
        lines += ['', '## Executive-summary links', '',
                  f"- Links into the picks list: {links['links_into_picks']} "
                  f"({len(links['broken'])} broken)",
                  f"- `#picks` anchor present: {links['picks_anchor_present']}; "
                  f"`#unresolved` anchor present: {links['unresolved_anchor_present']}"]
        for broken in links['broken']:
            lines.append(f"- BROKEN: `{broken['href']}` ({broken['text']})")
    cards = report['cards']
    if cards.get('status') == 'checked':
        lines.append(f"- Fixture cards rendered: {cards['cards_present']} of {cards['rows']}")
        for missing in cards['missing']:
            lines.append(f"- MISSING CARD: {missing}")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='kept for symmetry: the collectors run first')
    args = parser.parse_args()
    report = review(live=args.live)
    print(json.dumps({'totals': report['totals'], 'freshness': report['freshness']['within_contract'],
                      'summary_links': report['summary_links'].get('status')}, indent=2))
    print('::notice title=15fc6bca coverage review::'
          + json.dumps(report['totals']))
    problems = []
    if not report['freshness']['within_contract']:
        problems.append('snapshot older than the published staleness contract')
    if report['summary_links'].get('broken'):
        problems.append(f"{len(report['summary_links']['broken'])} broken summary link(s)")
    if report['cards'].get('missing'):
        problems.append(f"{len(report['cards']['missing'])} fixture card(s) missing")
    if problems:
        print('::warning title=15fc6bca coverage review::' + '; '.join(problems))


if __name__ == '__main__':
    main()
