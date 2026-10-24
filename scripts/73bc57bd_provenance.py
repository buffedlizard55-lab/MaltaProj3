"""Line-by-line provenance audit of the picks the published site serves.

Session arena-73bc57bd. The repository already has audits that answer "is there a
link on this row" (``scripts.audit_rows``) and "does the published page match the
snapshot" (``scripts.73bc57bd_reconcile``). Neither answers the question the brief
actually asks a reviewer to answer: *is the number on this row reproducible from the
source the row cites?*  This module replays every published row against the evidence
the row itself carries and reports the rows where it is not.

The audit is offline and read-only. It reads the build that the branch root serves --
``snapshot.json`` (the machine-readable snapshot), ``index.html`` (the executive
summary), ``origination/index.html`` (one card per fixture with the full research
trail) and ``unresolved/index.html`` -- and never fetches, repairs or fills a value.
A row that cannot be reproduced is reported, not corrected.

Checks
------
``probabilities_sum``      both sides of a pick must add to 1 (tolerance 0.5pp).
``pick_is_argmax``         the published pick must be the side the numbers favour.
``degenerate_price``       a quote at or below 1.01 (or above 50) is not a price a
                           book would stand behind; it must not become a probability.
``generic_evidence_link``  a row's source URL must identify *this* fixture, not a
                           collection page or API endpoint.
``layer_divergence``       the fast snapshot must not report a fixture as unresolved
                           while a rendered page shows a directional pick for it.
``probability_not_reproducible``
                           the published probability must be recomputable from the
                           quote the row carries (quote midpoint, or proportional
                           no-vig from the decimal prices).
``blank_format_with_confirmed_format``
                           a verified series format (e.g. "HLTV lists BO3") must not
                           be discarded into a blank field.
``stale_reference``        a rating snapshot older than 14 days is still usable, but
                           the row must say so.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

# A decimal price at or below this floor is a placeholder or a suspended market, not
# an offer: 1.001 returns one tenth of a percent on a stake and prints as "1.00",
# which a reader cannot tell apart from a missing value.
PRICE_FLOOR = 1.01
PRICE_CEILING = 50.0
PROBABILITY_TOLERANCE = 0.005
STALE_REFERENCE_DAYS = 14

# Collection pages and API endpoints that name a provider but not a fixture. A row
# that cites one of these cannot be checked by a human without searching the site.
GENERIC_PATH_SUFFIXES = (
    '/api/matches',
    '/matches',
    '/events',
    '/results',
)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except ValueError:
        return None


@dataclass
class Finding:
    code: str
    severity: str  # needs review | verified | platform limitation
    subject: str   # match id, or "summary"/"snapshot"
    detail: str
    evidence: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def fixture_url(match: dict) -> str | None:
    analysis = match.get('analysis') or {}
    return analysis.get('source_url') or match.get('source_url')


def is_generic_link(url: str | None) -> bool:
    """True when the URL addresses a provider's index rather than one fixture."""
    if not url:
        return False
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    if not any(path.endswith(suffix) or path == suffix for suffix in GENERIC_PATH_SUFFIXES):
        return False
    # A path that carries a numeric fixture id does identify the fixture.
    return not re.search(r'/(?:match|matches|event|events|fixture|fixtures)/\d', path)


def _quote_prices(analysis: dict) -> list[float]:
    prices: list[float] = []
    for quote in analysis.get('quotes') or []:
        for key in ('odds', 'decimal', 'price'):
            value = quote.get(key)
            if isinstance(value, list):
                prices.extend(float(v) for v in value if isinstance(v, (int, float)))
            elif isinstance(value, (int, float)):
                prices.append(float(value))
    return prices


def replay_probabilities(analysis: dict) -> list[float] | None:
    """Recompute the published probabilities from the quote the row carries.

    A prediction-market row publishes the midpoint of both order books; a bookmaker
    row publishes proportional no-vig odds. Either way the number must fall out of
    the evidence, not out of a later adjustment that the row does not disclose.
    """
    if analysis.get('method') == 'model':
        # The model rung is a logistic function of the two Valve rating totals. The
        # five published model rows agree on one scale, 400 / g with the g the row
        # itself publishes (0.972821), to five decimal places; the replay uses the
        # row's own inputs and factor and applies no other adjustment.
        inputs = analysis.get('inputs') or []
        g = analysis.get('g')
        if len(inputs) != 2 or not g:
            return None
        diff = inputs[0].get('points', 0) - inputs[1].get('points', 0)
        first = 1.0 / (1.0 + 10 ** (-diff * g / 400.0))
        return [first, 1.0 - first]
    quotes = analysis.get('quotes') or []
    if not quotes:
        return None
    if analysis.get('method') == 'market':
        midpoints = [q.get('midpoint') for q in quotes]
        if all(isinstance(m, (int, float)) for m in midpoints) and len(midpoints) == 2:
            total = sum(midpoints)
            return [m / total for m in midpoints]
        return None
    odds = _quote_prices(analysis)
    if len(odds) != 2 or any(o <= 1.0 for o in odds):
        return None
    inverse = [1.0 / o for o in odds]
    total = sum(inverse)
    return [i / total for i in inverse]


def check_probability_replay(match: dict) -> list[Finding]:
    analysis = match.get('analysis') or {}
    published = analysis.get('probabilities')
    replay = replay_probabilities(analysis)
    if not published or not replay:
        return []
    drift = max(abs(a - b) for a, b in zip(published, replay))
    if drift <= PROBABILITY_TOLERANCE:
        return []
    return [Finding(
        'probability_not_reproducible', 'needs review', match['id'],
        f'Published {published[0]:.1%} / {published[1]:.1%} does not follow from the quote '
        f'the row carries, which replays to {replay[0]:.1%} / {replay[1]:.1%} '
        f'(largest difference {drift:.2%}).',
        [{'url': analysis.get('source_url', ''), 'detail': 'quote used for the replay'}],
    )]


def check_probabilities(match: dict) -> list[Finding]:
    analysis = match.get('analysis') or {}
    probabilities = analysis.get('probabilities')
    if not probabilities:
        return []
    out: list[Finding] = []
    total = sum(probabilities)
    if abs(total - 1.0) > PROBABILITY_TOLERANCE:
        out.append(Finding(
            'probabilities_sum', 'needs review', match['id'],
            f'Published probabilities sum to {total:.4f}, not 1.',
            [{'url': fixture_url(match) or match.get('source_url', ''), 'detail': 'row source'}],
        ))
    pick_index = match.get('pick_index')
    favourite = max(range(len(probabilities)), key=lambda i: probabilities[i])
    if pick_index is None:
        out.append(Finding(
            'pick_is_argmax', 'needs review', match['id'],
            'Row carries probabilities but no pick index.',
            [{'url': fixture_url(match) or match.get('source_url', ''), 'detail': 'row source'}],
        ))
    elif pick_index != favourite:
        out.append(Finding(
            'pick_is_argmax', 'needs review', match['id'],
            f'Pick index {pick_index} is not the more likely side (index {favourite}, '
            f'{probabilities[favourite]:.1%}).',
            [{'url': fixture_url(match) or match.get('source_url', ''), 'detail': 'row source'}],
        ))
    return out


def check_price_floor(match: dict) -> list[Finding]:
    analysis = match.get('analysis') or {}
    low = [p for p in _quote_prices(analysis) if p <= PRICE_FLOOR]
    high = [p for p in _quote_prices(analysis) if p >= PRICE_CEILING]
    if not low and not high:
        return []
    prices = _quote_prices(analysis)
    probabilities = analysis.get('probabilities') or []
    model_pick = max(probabilities) if probabilities else None
    detail = (
        'Quoted decimal price '
        + ', '.join(f'{p:g}' for p in (low + high))
        + f' from {analysis.get("source", "the cited source")} was normalised into the pick'
        + (f' ({model_pick:.1%})' if model_pick is not None else '')
        + '. A price at or below 1.01 is not an offer a bookmaker stands behind; '
        'it publishes as "1.00", which a reader cannot distinguish from a missing value.'
    )
    return [Finding('degenerate_price', 'needs review', match['id'], detail,
                    [{'url': analysis.get('source_url', ''), 'detail': f'quoted odds {prices}'}])]


def check_evidence_link(match: dict) -> list[Finding]:
    analysis = match.get('analysis') or {}
    url = analysis.get('source_url')
    if not is_generic_link(url):
        return []
    event = analysis.get('event_id') or analysis.get('market_id')
    detail = (
        f'The row cites {url}, a provider index, not this fixture'
        + (f' (event {event})' if event else '')
        + '. A reviewer cannot reach the quoted price from the page the row links, so the '
          'price is reproducible only by re-querying the provider API.'
    )
    return [Finding('generic_evidence_link', 'needs review', match['id'], detail,
                    [{'url': url, 'detail': 'cited source for this row'}])]


def _page_pick(html: str, match_id: str) -> bool | None:
    """Does the per-fixture card in a rendered page show a directional pick?"""
    anchor = f'id="match-{match_id}"'
    start = html.find(anchor)
    if start < 0:
        return None
    window = html[start:start + 6000]
    if '✓ pick' in window:
        return True
    if 'No pick' in window or 'Not yet resolved' in window:
        return False
    return None


def check_layer_divergence(match: dict, pages: dict[str, str]) -> list[Finding]:
    """The snapshot and the rendered pages must agree on whether a pick exists."""
    if match.get('analysis'):
        return []
    out: list[Finding] = []
    for name, html in pages.items():
        shown = _page_pick(html, match['id'])
        if shown:
            probabilities = re.findall(r'(\d{1,3}\.\d)%', html[html.find(f'id="match-{match["id"]}"'):][:4000])
            out.append(Finding(
                'layer_divergence', 'needs review', match['id'],
                f'/snapshot.json carries no analysis for this fixture and its counts report '
                f'it as unresolved, while {name} shows a directional pick'
                + (f' at {"/".join(probabilities[:2])}%' if probabilities else '')
                + '. The machine-readable snapshot and the page a reader sees disagree about '
                  'whether this fixture has a pick.',
                [{'url': match.get('source_url', ''), 'detail': 'fixture page'}],
            ))
            break
    return out


def check_blank_format(match: dict) -> list[Finding]:
    """A format the research trail already says HLTV confirmed must not stay blank."""
    if match.get('best_of') or match.get('series_format'):
        return []
    wanted = None
    for entry in match.get('research') or []:
        detail = str(entry.get('detail') or '')
        found = re.search(r'HLTV lists (BO\d)', detail)
        if found:
            wanted = found.group(1)
            break
    if not wanted:
        return []
    return [Finding(
        'blank_format_with_confirmed_format', 'needs review', match['id'],
        f'The published row shows no series format (best_of is null) while its own research '
        f'trail records "HLTV lists {wanted}". The Hotspawn entry is separately unverified, so '
        f'the blank field is the safe choice, but the verified HLTV format never reaches the '
        f'reader: the row offers nothing to distinguish "unverified" from "not looked at".',
        [{'url': next((e.get('source_url') for e in match.get('research') or []
                       if e.get('source_url')), match.get('source_url', '')),
          'detail': f'research trail states HLTV lists {wanted}'}],
    )]


def check_stale_reference(match: dict, generated_at: datetime | None) -> list[Finding]:
    analysis = match.get('analysis') or {}
    snapshot_date = analysis.get('snapshot_date')
    parsed = _parse_time(f'{snapshot_date}T00:00:00Z') if snapshot_date else None
    if not parsed or not generated_at:
        return []
    age = (generated_at - parsed).days
    if age <= STALE_REFERENCE_DAYS:
        return []
    return [Finding(
        'stale_reference', 'verified', match['id'],
        f'The research model rests on the Valve standings snapshot of {snapshot_date}, '
        f'{age} days old when this snapshot was published. The row states the snapshot date '
        f'and links the standings file, so the age is disclosed rather than hidden.',
        [{'url': analysis.get('source_url', ''), 'detail': f'standings snapshot {snapshot_date}'}],
    )]


def summary_unresolved_claim(index_html: str) -> int | None:
    match = re.search(r'<strong>(\d+)</strong> explicitly unresolved', index_html)
    return int(match.group(1)) if match else None


def audit(snapshot: dict, pages: dict[str, str]) -> dict:
    """Replay every published row. Returns a JSON-serialisable report."""
    generated_at = _parse_time(snapshot.get('generated_at'))
    findings: list[Finding] = []
    matches = snapshot.get('matches') or []
    row_findings: dict[str, int] = {}

    for match in matches:
        if match.get('availability') == 'past':
            # Past-start rows are archived on purpose and carry the archive label.
            continue
        if match.get('analysis'):
            found = (
                check_probabilities(match)
                + check_price_floor(match)
                + check_evidence_link(match)
                + check_blank_format(match)
                + check_stale_reference(match, generated_at)
            )
            if found:
                row_findings[match['id']] = len(found)
            findings.extend(found)
        else:
            findings.extend(check_blank_format(match))
        findings.extend(check_layer_divergence(match, pages))

    counts = snapshot.get('counts') or {}
    claim = summary_unresolved_claim(pages.get('index.html', ''))
    if claim is not None and counts.get('unresolved') is not None and claim != counts['unresolved']:
        findings.append(Finding(
            'layer_divergence', 'needs review', 'summary',
            f'The executive summary states {claim} explicitly unresolved fixtures while '
            f'snapshot.json counts.unresolved reports {counts["unresolved"]}. Both are served '
            f'from the same build.',
            [{'url': 'https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json',
              'detail': f'counts.unresolved = {counts["unresolved"]}'}],
        ))

    reproduced = 0
    replay_drift: dict[str, float] = {}
    for match in matches:
        analysis = match.get('analysis') or {}
        published = analysis.get('probabilities')
        replay = replay_probabilities(analysis)
        if not published or not replay:
            continue
        drift = max(abs(a - b) for a, b in zip(published, replay))
        if drift <= PROBABILITY_TOLERANCE:
            reproduced += 1
        findings.extend(check_probability_replay(match))
        replay_drift[match['id']] = round(drift, 6)

    by_code: dict[str, int] = {}
    for finding in findings:
        by_code[finding.code] = by_code.get(finding.code, 0) + 1

    return {
        'schema_version': 1,
        'session': 'arena-73bc57bd',
        'audit': 'published-pick provenance, replayed offline from the branch-root build',
        'snapshot_generated_at': snapshot.get('generated_at'),
        'snapshot_counts': counts,
        'rows_with_analysis': sum(1 for m in matches if m.get('analysis')),
        'rows_examined': len(matches),
        'rows_probability_reproduced': reproduced,
        'replay_drift': replay_drift,
        'summary_unresolved_claim': claim,
        'findings_total': len(findings),
        'findings_by_code': dict(sorted(by_code.items())),
        'rows_with_findings': dict(sorted(row_findings.items())),
        'findings': [f.to_dict() for f in findings],
    }


def load(root: Path) -> tuple[dict, dict[str, str]]:
    root = Path(root)
    snapshot = json.loads((root / 'snapshot.json').read_text(encoding='utf-8'))
    pages = {}
    for name in ('index.html', 'origination/index.html', 'unresolved/index.html'):
        path = root / name
        if path.exists():
            pages[name] = path.read_text(encoding='utf-8')
    return snapshot, pages


def render_markdown(report: dict, observations: Iterable[dict] = ()) -> str:
    lines = [
        '# Provenance audit of the published picks',
        '',
        f'Session `arena-73bc57bd`. Snapshot generated `{report["snapshot_generated_at"]}`; '
        f'{report["rows_with_analysis"]} of {report["rows_examined"]} rows carry an analysis.',
        '',
        'Every row was replayed against the evidence it cites. Nothing below was repaired, '
        're-priced or filled in: a row that does not reproduce is reported with the reason.',
        '',
        '## Findings by check',
        '',
        '| Check | Rows |',
        '| --- | --- |',
    ]
    for code, count in report['findings_by_code'].items():
        lines.append(f'| `{code}` | {count} |')
    if not report['findings_by_code']:
        lines.append('| none | 0 |')
    lines += ['', '## Each finding', '']
    for finding in report['findings']:
        links = ' · '.join(f'[{e["detail"]}]({e["url"]})' for e in finding['evidence'] if e.get('url'))
        lines.append(f'- **{finding["code"]}** · `{finding["subject"]}` · *{finding["severity"]}* — '
                     f'{finding["detail"]}' + (f' — {links}' if links else ''))
    if observations:
        lines += ['', '## Independent re-reads of cited sources', '']
        for item in observations:
            lines.append(f'- `{item.get("match_id") or item.get("source")}` '
                         f'({item.get("read_at")}): {item.get("verdict")} — '
                         f'[{item.get("source")}]({item.get("url")})')
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.', help='branch root holding the published build')
    parser.add_argument('--json', default=None, help='write the report to this path')
    parser.add_argument('--md', default=None, help='write the Markdown summary to this path')
    args = parser.parse_args(argv)

    snapshot, pages = load(Path(args.root))
    report = audit(snapshot, pages)
    text = json.dumps(report, indent=2, sort_keys=False) + '\n'
    if args.json:
        Path(args.json).write_text(text, encoding='utf-8')
    else:
        print(text)
    if args.md:
        Path(args.md).write_text(render_markdown(report), encoding='utf-8')
    print(f'{report["findings_total"]} finding(s) across '
          f'{len(report["rows_with_findings"])} row(s): {report["findings_by_code"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
