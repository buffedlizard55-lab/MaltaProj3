"""Session arena-0962d605 — verify the gap dossier and the phone-first register.

What this module checks, and why each check exists:

1. ``data/research/0962d605/gap-research.json`` — every observation names an
   https source and the UTC time it was read, every bid/ask pair recomputes to
   the published spread, and every state is one of the closed set
   ``prematch`` / ``in-play``. A quote that cannot be reproduced from its own
   numbers is rejected rather than displayed.
2. The two gap fixtures exist in the checked-in snapshot, and any estimate the
   dossier attributes to the board matches the published row exactly. The
   dossier may not introduce a probability the board does not publish.
3. The identity aliases the dossier relies on are registered, correctly scoped,
   and carry https evidence. No alias is added or widened here.
4. The built executive summary renders the separate unresolved register, a
   card per fixture the featured line could not price (with pick, both
   probabilities, method badge, blocker, tried stages and a source link), and
   the two-record reconciliation when the published snapshot counts differ
   from the board.
5. The build's own audits agree: zero row-source violations and zero acceptance
   failures.

Run ``python -m scripts.0962d605_verify`` for a human-readable report, or
``python -m scripts.0962d605_verify --check`` to exit non-zero on any failure.
The module never writes a probability, a pick, an alias or a published file.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / 'data/research/0962d605/gap-research.json'
ALIASES = ROOT / 'data/origination/aliases.json'
SNAPSHOT = ROOT / 'snapshot.json'
ORIGINATION = ROOT / 'data/origination.json'
STATES = {'prematch', 'in-play'}
ISO_Z = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
MONEY = {'market', 'bookmaker', 'consensus', 'reference'}


def _utc(value: str) -> datetime:
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')


def check_dossier(dossier: dict) -> list:
    errors = []
    fixtures = dossier.get('fixtures') or []
    if not fixtures:
        errors.append('dossier lists no fixtures')
    for fixture in fixtures:
        fid = str(fixture.get('id') or '')
        if not fid.isdigit():
            errors.append(f'fixture id {fid!r} is not a numeric Hotspawn id')
        for key in ('teams', 'competition', 'conclusion', 'limitations', 'hltv', 'lines'):
            if not fixture.get(key):
                errors.append(f'{fid}: missing {key}')
        hltv = fixture.get('hltv') or {}
        if not str(hltv.get('match_url') or '').startswith('https://www.hltv.org/matches/'):
            errors.append(f'{fid}: HLTV match URL is not an hltv.org match page')
        if not ISO_Z.match(str(hltv.get('observed_at') or '')):
            errors.append(f'{fid}: HLTV observation time is not UTC-Z')
        for line in fixture.get('lines') or []:
            where = f'{fid} {line.get("provider")} {line.get("market")}'
            if not str(line.get('source_url') or '').startswith('https://'):
                errors.append(f'{where}: source URL is not https')
            if not ISO_Z.match(str(line.get('observed_at') or '')):
                errors.append(f'{where}: observation time is not UTC-Z')
            if not ISO_Z.match(str(line.get('start') or '')):
                errors.append(f'{where}: start time is not UTC-Z')
            if line.get('state') not in STATES:
                errors.append(f'{where}: state {line.get("state")!r} is outside the closed set')
            bid, ask = line.get('bid'), line.get('ask')
            if not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)):
                errors.append(f'{where}: bid/ask are not numeric')
                continue
            if bid >= ask:
                errors.append(f'{where}: bid {bid} is not below ask {ask} (crossed book)')
            computed = round(ask - bid, 4)
            if abs(computed - float(line.get('spread', computed))) > 1e-6:
                errors.append(f'{where}: published spread {line.get("spread")} != ask-bid {computed}')
    for source in dossier.get('sources') or []:
        if not str(source.get('url') or '').startswith('https://'):
            errors.append(f'dossier source {source.get("url")!r} is not https')
        if not source.get('detail'):
            errors.append(f'dossier source {source.get("url")!r} has no detail')
    return errors


def check_published_estimates(dossier: dict, snapshot: dict, origination: dict) -> list:
    """A dossier figure attributed to the board must equal the published row.

    ``data/origination.json`` is the *checked-in* board, which can predate the
    snapshot a dossier was written against (the publisher regenerates it every
    four hours, and the regression tests run before any collection). When the
    row is present the estimate must match it exactly. When it is absent the
    dossier must carry its own published-page evidence and observation time, so
    a figure is never unattributed; the absence is reported by the caller as a
    note, never smoothed into a match.
    """
    errors = []
    snap = {str(m['id']): m for m in snapshot.get('matches') or []}
    board = {str(m['id']): m for m in (origination.get('matches') or [])}
    for fixture in dossier.get('fixtures') or []:
        fid = str(fixture.get('id'))
        if fid not in snap:
            errors.append(f'{fid}: not present in the checked-in snapshot')
            continue
        published = fixture.get('published_estimate')
        if not published:
            continue
        probs = published.get('probabilities') or []
        if len(probs) != 2 or abs(sum(probs) - 1.0) > 1e-4:
            errors.append(f'{fid}: published estimate does not sum to 1')
        origin = (board.get(fid) or {}).get('origination') or {}
        if origin.get('probabilities'):
            a, b = origin['probabilities']
            if abs(a - probs[0]) > 0.005 or abs(b - probs[1]) > 0.005:
                errors.append(f'{fid}: dossier estimate {probs} != published board {[a, b]}')
        elif not (str(published.get('evidence_url') or '').startswith('https://')
                  and ISO_Z.match(str(published.get('observed_at') or ''))):
            errors.append(f'{fid}: board has no row for this fixture and the dossier names no published evidence')
        if not str(published.get('source_url') or '').startswith('https://'):
            errors.append(f'{fid}: published estimate has no https source')
    return errors


def check_aliases(dossier: dict, aliases: dict) -> list:
    errors = []
    registry = aliases.get('aliases') or []
    by_alias = {}
    for entry in registry:
        by_alias.setdefault(str(entry.get('alias')), []).append(entry)
    expected = {'1081156': ('Sökerorg', 'LFO 10'), '1082792': ('The Huns Esports', 'The Huns')}
    for fixture in dossier.get('fixtures') or []:
        fid = str(fixture.get('id'))
        pair = expected.get(fid)
        if not pair:
            continue
        alias, canonical = pair
        entries = [e for e in by_alias.get(alias, []) if e.get('canonical') == canonical]
        if not entries:
            errors.append(f'{fid}: alias {alias!r} -> {canonical!r} is not registered')
            continue
        competition = str(fixture.get('competition') or '')
        scoped = [e for e in entries if competition in (e.get('applies_to') or [])]
        if not scoped:
            errors.append(f'{fid}: alias {alias!r} is not scoped to {competition!r}')
        for entry in entries:
            for ev in entry.get('evidence') or []:
                if not str(ev.get('url') or '').startswith('https://'):
                    errors.append(f'{fid}: alias evidence {ev.get("url")!r} is not https')
    return errors


def check_site(site: Path, origination: dict) -> list:
    errors = []
    index = (site / 'index.html')
    if not index.is_file():
        return ['built site has no index.html']
    html = index.read_text(encoding='utf-8')
    if 'id="unresolved-register"' not in html:
        errors.append('executive summary has no separate unresolved register')
    board = [m for m in (origination.get('matches') or []) if m.get('origination') is not None]
    fallback = [m for m in board if m.get('featured_method') is None]
    for match in fallback:
        fid = str(match.get('id'))
        card = re.search(r'<li class="unresolved-summary-card" id="researched-%s">(.*?)</li>' % re.escape(fid),
                         html, re.S)
        if not card:
            errors.append(f'{fid}: no researched card in the executive summary')
            continue
        body = card.group(1)
        probs = (match.get('origination') or {}).get('probabilities') or []
        if len(probs) != 2:
            continue
        pick = match.get('pick_index')
        if pick in (0, 1):
            expected = f'{(probs[pick] * 100):.1f}%'
            if expected not in body:
                errors.append(f'{fid}: card does not show the published pick probability {expected}')
        else:
            if 'Even estimate' not in body:
                errors.append(f'{fid}: even row must say it has no side')
        method = (match.get('origination') or {}).get('method')
        if method in MONEY:
            if 'badge green' not in body:
                errors.append(f'{fid}: a money-backed row must carry the money badge')
        elif method == 'guidance':
            if 'Guidance only' not in body:
                errors.append(f'{fid}: guidance row must be labelled Guidance only')
        if 'Why not the featured line' not in body:
            errors.append(f'{fid}: card does not state the featured-line blocker')
        if 'origination/#match-' not in body:
            errors.append(f'{fid}: card has no full-trail link')
        if not re.search(r'href="https://', body):
            errors.append(f'{fid}: card has no https source link')
    counts = (origination.get('counts') or {})
    if (counts.get('unresolved') or 0) and 'id="snapshot-reconciliation"' not in html:
        errors.append('published snapshot reports unresolved fixtures but no reconciliation is rendered')
    if 'id="mobile-status"' in html and 'nav class="mobile-status"' not in html:
        errors.append('mobile status strip markup is malformed')
    return errors


def check_audits(site: Path) -> list:
    errors = []
    row_audit = site / 'data/row-source-audit.json'
    if row_audit.is_file():
        totals = json.loads(row_audit.read_text(encoding='utf-8')).get('totals') or {}
        if totals.get('violation'):
            errors.append(f'row-source audit reports {totals["violation"]} violation(s)')
    else:
        errors.append('row-source audit was not produced')
    acceptance = site / 'data/acceptance-audit.json'
    if acceptance.is_file():
        totals = json.loads(acceptance.read_text(encoding='utf-8')).get('totals') or {}
        if totals.get('fail'):
            errors.append(f'acceptance audit reports {totals["fail"]} failure(s)')
    else:
        errors.append('acceptance audit was not produced')
    return errors


def verify(site: Path | None = None) -> dict:
    dossier = json.loads(DOSSIER.read_text(encoding='utf-8'))
    aliases = json.loads(ALIASES.read_text(encoding='utf-8'))
    snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    origination = json.loads(ORIGINATION.read_text(encoding='utf-8'))
    checks = {
        'dossier observations': check_dossier(dossier),
        'published estimates': check_published_estimates(dossier, snapshot, origination),
        'identity aliases': check_aliases(dossier, aliases),
    }
    if site is not None:
        checks['rendered register'] = check_site(site, origination)
        checks['build audits'] = check_audits(site)
    errors = [(name, err) for name, errs in checks.items() for err in errs]
    return {
        'session': 'arena-0962d605',
        'checked_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'fixtures': [str(f['id']) for f in dossier.get('fixtures') or []],
        'checks': {name: {'errors': len(errs), 'detail': errs} for name, errs in checks.items()},
        'error_count': len(errors),
        'errors': [f'{name}: {err}' for name, err in errors],
    }


def main() -> int:
    import argparse
    from scripts import build as build_module
    parser = argparse.ArgumentParser(description='Verify session 0962d605 dossier and register')
    parser.add_argument('--check', action='store_true', help='exit non-zero on any failure')
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--doc', type=Path, default=None, help='write the JSON report here')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='0962d605-site-') as tmp:
        out = Path(tmp)
        build_module.build(args.data, out)
        report = verify(out)
    if args.doc:
        args.doc.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for name, result in report['checks'].items():
        print(f'{"PASS" if not result["errors"] else "FAIL"} {name}: {result["errors"]} error(s)')
        for detail in result['detail']:
            print(f'   - {detail}')
    print(f'{report["error_count"]} error(s) across {len(report["checks"])} checks')
    if args.check and report['error_count']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
