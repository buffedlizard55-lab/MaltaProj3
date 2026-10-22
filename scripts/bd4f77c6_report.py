"""Session bd4f77c6 — live verification report (session-only tooling).

Runs after `scripts.collect`, `scripts.originate --live` and `scripts.build` in
`.github/workflows/bd4f77c6-live.yml`. It writes a compact, dated snapshot and a
provenance check into `data/research/bd4f77c6/live/` so the branch carries the
evidence it verified against. It never edits a value: it only reads the files
the pipeline produced.

Checks:
  * every active fixture has a pick or an explicit unresolved entry;
  * every model-labelled pick names the rung that actually produced it (a
    network quote may never be published as a Valve estimate, and vice versa);
  * the executive summary credits only the rungs present in the snapshot;
  * the built pages carry the phone viewport and the picks link.

Usage: python -m scripts.bd4f77c6_report
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
OUT = Path('data/research/bd4f77c6/live')


def load(path: Path):
    return json.loads(path.read_text())


def main() -> int:
    now = datetime.now(UTC)
    latest = load(Path('data/latest.json'))
    origination = load(Path('data/origination.json'))
    complete = origination.get('complete_picks') or {}
    matches = complete.get('matches') or []
    active = [m for m in matches if m.get('availability') != 'past']

    rows, problems = [], []
    for m in active:
        o = m.get('origination') or {}
        quote = (o.get('quotes') or [{}])[0] if o else {}
        family = quote.get('family') or o.get('method')
        label = o.get('label')
        names = [t.get('name') for t in m.get('teams') or []]
        trail = m.get('research') or []
        money = [r for r in trail if str(r.get('stage', '')).startswith(('Primary:', 'Betting market', 'Exchange market', 'Esportsbook line'))]
        rows.append({
            'id': m.get('id'),
            'teams': names,
            'competition': m.get('competition'),
            'starts_at': m.get('starts_at'),
            'featured_method': m.get('featured_method'),
            'resolved': bool(o),
            'pick_index': m.get('pick_index'),
            'pick': names[m['pick_index']] if m.get('pick_index') is not None and o else None,
            'probability': round(o['probabilities'][m['pick_index']], 4) if o and m.get('pick_index') is not None else None,
            'method': o.get('method'),
            'family': family,
            'label': label,
            'source': o.get('source'),
            'source_url': o.get('source_url'),
            'money_stages': [{'stage': r.get('stage'), 'status': r.get('status'), 'url': r.get('source_url')} for r in money],
            'limitations': m.get('limitations') or [],
        })
        if not o and m.get('pick_index') is not None:
            problems.append(f'{m.get("id")}: pick without an origination record')
        if o and m.get('pick_index') is None:
            problems.append(f'{m.get("id")}: resolved estimate without a side')
        if label and str(family) == 'network' and 'Valve' in str(label):
            problems.append(f'{m.get("id")}: network quote labelled as a Valve estimate')
        if label and str(family) == 'valve' and 'network' in str(label).lower():
            problems.append(f'{m.get("id")}: Valve quote labelled as a network estimate')

    counts = complete.get('counts') or {}
    if counts.get('active') not in (None, len(active)):
        problems.append(f'counts.active {counts.get("active")} != {len(active)} active rows')

    site = Path('site')
    summary_html = (site / 'index.html').read_text() if (site / 'index.html').exists() else ''
    picks_html = (site / 'picks/index.html').read_text() if (site / 'picks/index.html').exists() else ''
    orig_html = (site / 'origination/index.html').read_text() if (site / 'origination/index.html').exists() else ''
    ui = {
        'viewport': 'name="viewport"' in summary_html,
        'picks_link': 'origination/#picks' in summary_html,
        'unresolved_register': 'unresolved-register' in summary_html,
        'model_register': 'model-picks' in summary_html,
        'hardcoded_thunderpick_credit': 'verified Thunderpick paired-price book' in summary_html,
        'picks_page_rows': len(re.findall(r'class="pick-card', picks_html)),
        'origination_cards': len(re.findall(r'class="pick-card', orig_html)),
    }
    if not ui['viewport']:
        problems.append('executive summary has no phone viewport')
    if not ui['picks_link']:
        problems.append('executive summary does not link the picks list')
    if not ui['unresolved_register']:
        problems.append('executive summary has no unresolved register')
    if ui['hardcoded_thunderpick_credit']:
        problems.append('executive summary still credits a Thunderpick price to every blank row')

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'active-fixtures.json').write_text(json.dumps({
        'observed_at': now.isoformat(timespec='seconds').replace('+00:00', 'Z'),
        'inventory_observed_at': latest.get('inventory_observed_at'),
        'inventory_crosscheck': latest.get('inventory_crosscheck'),
        'counts': latest.get('counts'),
        'complete_counts': counts,
        'fixtures': rows,
        'problems': problems,
        'ui': ui,
        'hashes': {
            'latest_sha256': __import__('hashlib').sha256(Path('data/latest.json').read_bytes()).hexdigest(),
            'origination_sha256': __import__('hashlib').sha256(Path('data/origination.json').read_bytes()).hexdigest(),
        },
    }, indent=2, sort_keys=False))
    (OUT / 'latest.json').write_text(Path('data/latest.json').read_text())
    (OUT / 'origination.json').write_text(Path('data/origination.json').read_text())
    pages = OUT / 'pages'
    pages.mkdir(exist_ok=True)
    for name in ('index.html', 'picks/index.html', 'origination/index.html'):
        source = site / name
        if source.exists():
            target = pages / name.replace('/', '-')
            target.write_text(source.read_text())
    print(json.dumps({'active': len(active), 'problems': problems, 'ui': ui}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
