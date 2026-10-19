"""Own results-based rating for a team the official Valve table does not list.

Why this exists
---------------
The ladder prices every fixture from a published line first and from Valve's
official VRS second. Some low-tier fixtures have neither: no bookmaker prices
them and at least one team has no five-player row in Valve's weekly snapshots.

This module fits a single rating for such a team from *observed series results*
only, anchored on opponents that do have a published Valve rating. It is an
explicitly labelled, uncalibrated research model — not a bookmaker price, not a
copy of anyone else's prediction, and never a filled-in "fact".

Rules (all fail closed)
-----------------------
* Only finished, fully parsed best-of series with a published winner are used.
* Only opponents with exactly one complete five-player Valve row are anchors.
* A side needs at least 8 anchored series against at least 3 distinct opponents
  inside 120 days; anything less produces no estimate.
* The rating is a maximum-a-posteriori fit under Valve's own published logistic
  scale, with a Gaussian prior centred on the median anchor rating (250 points
  SD). It is shrunk toward its opponents instead of being allowed to run to an
  extreme on a handful of games.
* The published probability also carries a one-standard-deviation interval.
  When that interval crosses 50%, the fixture is flagged low-confidence rather
  than presented as a confident pick.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
SCALE = math.log(10) / 400
MAX_AGE_DAYS = 120
MIN_SERIES = 8
MIN_OPPONENTS = 3
PRIOR_SD = 250.0
GRID = range(300, 2601, 5)


def key(value: str) -> str:
    import re
    return re.sub(r'[^a-z0-9]+', '', (value or '').casefold())


def _g(rd: float) -> float:
    return 1 / math.sqrt(1 + 3 * SCALE ** 2 * rd ** 2 / math.pi ** 2)


def win_probability(target: float, opponent: float, rd: float) -> float:
    return 1 / (1 + 10 ** (_g(rd) * (opponent - target) / 400))


def fit(samples: list[dict]) -> dict:
    """MAP rating on a fixed grid. ``samples`` need opponent_points and won."""
    clean = [s for s in samples if isinstance(s.get('opponent_points'), (int, float)) and s['opponent_points'] > 0]
    if not clean:
        return {'ok': False, 'reason': 'no anchored results'}
    center = sorted(s['opponent_points'] for s in clean)[len(clean) // 2]
    scored = []
    for rating in GRID:
        logpost = -0.5 * ((rating - center) / PRIOR_SD) ** 2
        for sample in clean:
            p = win_probability(rating, sample['opponent_points'], 75)
            p = min(max(p, 1e-6), 1 - 1e-6)
            logpost += math.log(p) if sample['won'] else math.log(1 - p)
        scored.append((logpost, rating))
    best_logpost, best = max(scored)
    weights = [(math.exp(lp - best_logpost), r) for lp, r in scored]
    total = sum(w for w, _ in weights)
    mean = sum(w * r for w, r in weights) / total
    variance = sum(w * (r - mean) ** 2 for w, r in weights) / total
    return {'ok': True, 'points': best, 'posterior_sd': round(math.sqrt(variance), 1),
            'prior_center': center, 'n': len(clean),
            'opponents': len({key(s.get('opponent') or str(s['opponent_points'])) for s in clean})}


def usable(samples: list[dict], now: datetime) -> list[dict]:
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    out = []
    for sample in samples:
        try:
            day = datetime.fromisoformat(str(sample.get('date'))[:10]).replace(tzinfo=UTC)
        except (ValueError, TypeError):
            continue
        if day < cutoff or day > now + timedelta(days=1):
            continue
        if sample.get('won') not in (True, False) or sample.get('parsed') != 'done':
            continue
        if sample.get('opponent_points') in (None, 0):
            continue
        out.append(dict(sample, date=day.date().isoformat()))
    return out


def estimate_fixture(match: dict, binding: dict | None, ratings: list, registry: dict,
                     now: datetime) -> tuple[dict | None, str]:
    """Return a labelled form quote for this fixture, or (None, reason)."""
    from scripts.originate import rating_row  # local import: one rule for identity

    if not binding:
        return None, 'No bo3.gg fixture binding (results model needs an observed series history)'
    sides = []
    for team in match.get('teams') or []:
        name = team.get('name') or ''
        official = rating_row(name, ratings, registry, match.get('competition'))
        side = {'name': name, 'official': official, 'fit': None, 'samples': []}
        if official is None:
            raw = (binding.get('results') or {}).get(key(name)) or []
            side['fit'] = None
            if not raw:
                return None, f'{name}: no published Valve rating and no saved results history'
            anchored = []
            for sample in raw:
                row = rating_row(sample.get('opponent') or '', ratings, registry, match.get('competition'))
                if row:
                    anchored.append(dict(sample, opponent_points=row['points']))
            samples = usable(anchored, now)
            if len(samples) < MIN_SERIES:
                return None, (f'{name}: no published Valve rating; only {len(samples)} anchored series '
                              f'in the last {MAX_AGE_DAYS} days (needs {MIN_SERIES})')
            fitted = fit(samples)
            if not fitted.get('ok'):
                return None, f'{name}: results sample produced no usable fit'
            if fitted['opponents'] < MIN_OPPONENTS:
                return None, (f'{name}: results sample covers only {fitted["opponents"]} distinct rated '
                              f'opponents (needs {MIN_OPPONENTS})')
            side['fit'] = fitted
            side['samples'] = samples
        sides.append(side)
    missing = [s for s in sides if s['fit']]
    if not missing:
        return None, 'Both teams already have published Valve rows; results model not needed'
    values = []
    for side in sides:
        if side['official']:
            values.append((side['official']['points'], 75.0,
                           {'name': side['name'], 'points': side['official']['points'],
                            'source_url': side['official'].get('source_url'),
                            'source': 'Valve official standings',
                            'roster': side['official'].get('roster')}))
        else:
            rd = min(400.0, 150.0 + 300.0 / math.sqrt(max(1, side['fit']['n'])))
            values.append((side['fit']['points'], rd,
                           {'name': side['name'], 'points': side['fit']['points'],
                            'source': 'Own results-based fit (bo3.gg series results)',
                            'source_url': binding.get('source_url'),
                            'roster': None,
                            'fitted': {'n': side['fit']['n'], 'posterior_sd': side['fit']['posterior_sd'],
                                       'prior_center': side['fit']['prior_center']}}))
    p = win_probability(values[0][0], values[1][0], max(values[0][1], values[1][1]))
    sd = max((s['fit']['posterior_sd'] for s in missing), default=0)
    low = win_probability(values[0][0] - sd, values[1][0] + sd, max(values[0][1], values[1][1]))
    high = win_probability(values[0][0] + sd, values[1][0] - sd, max(values[0][1], values[1][1]))
    n = min(s['fit']['n'] for s in missing)
    samples = sorted((s for side in missing for s in side['samples']), key=lambda s: s['date'])[-12:]
    return ({'provider': 'Own results-based model (bo3.gg series results)', 'family': 'form',
             'probabilities': [p, 1 - p], 'inputs': [v[2] for v in values],
             'rating_sd': round(sd, 1), 'interval': [round(low, 4), round(high, 4)],
             'n_series': n, 'low_confidence': bool(sd > 100 or n < 12),
             'samples': [{'date': s['date'], 'opponent': s.get('opponent'), 'won': s['won'],
                          'bo': s.get('bo'), 'source_url': s.get('source_url')} for s in samples],
             'source_url': binding.get('source_url'),
             'observed_at': binding.get('observed_at')}, '')


def load_bindings(evidence_dir: Path) -> dict:
    path = Path(evidence_dir) / 'live-bo3-bindings.json'
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (ValueError, OSError):
        return {}
    return payload.get('matches') or {}


def save_bindings(evidence_dir: Path, data: dict) -> Path:
    path = Path(evidence_dir) / 'live-bo3-bindings.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return path
