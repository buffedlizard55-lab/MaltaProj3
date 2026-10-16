"""Time-safe presentation of already sourced picks; never a probability input.

The collector/replay validator decides whether a line is supported. This module
only decides whether that saved line may be labelled a *current* pick at render
time. The same guards run in assets/pick-safety.js while a page stays open.
Missing deadlines are not guessed from Hotspawn's conflicting 5/6 minute rules.
"""
from __future__ import annotations

import html
import math
from datetime import datetime, timedelta, timezone

from scripts.domain import MAX_PRICE_AGE_HOURS, iso, timestamp

# Slight runner/client clock skew is tolerated, as in the canonical source policy.
CLOCK_SKEW_SECONDS = 300
STATUS = {
    'current': ('Open for picks', 'Fresh source snapshot and line; submit before the confirmed lock.'),
    'started': ('Past start', 'Scheduled start has passed; result unverified. Estimate retained for audit, not a current pick.'),
    'locked': ('Locked', 'Closed for picks. Estimate retained for audit, not a current pick.'),
    'unknown-lock': ('Deadline unverified', 'A future lock/start and open status are not confirmed. No current pick is recommended.'),
    'inventory-unverified': ('Inventory unverified', 'Current coverage is not confirmed. Retained estimate only, not a current pick.'),
    'stale-inventory': ('Snapshot needs refresh', 'Inventory is older than eight hours or its observation time is unverified. Not a current pick.'),
    'unbound-snapshot': ('Snapshot mismatch', 'These lines are not bound to this inventory observation. Not a current pick.'),
    'stale-line': ('Line needs refresh', 'Line is older than eight hours or its observation time is unverified. Not a current pick.'),
    'unresolved': ('Unresolved', 'No validated two-team estimate. Probabilities and pick stay blank; no default 50/50.'),
}


def valid_pair(values) -> bool:
    return (isinstance(values, (list, tuple)) and len(values) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) and 0 < v < 1 for v in values)
            and abs(sum(values) - 1) < 1e-4)


def fresh(value, now: datetime, hours=MAX_PRICE_AGE_HOURS) -> bool:
    dt = timestamp(value)
    return dt is not None and -CLOCK_SKEW_SECONDS <= (now - dt).total_seconds() <= hours * 3600


def presentation(match: dict, inventory_at, inventory_complete: bool, now: datetime,
                 *, snapshot_bound=True, max_age_hours=MAX_PRICE_AGE_HOURS) -> dict:
    """Return labels and expiry only; do not mutate match, pick, odds or inputs."""
    line = match.get('origination') or match.get('analysis') or {}
    start, lock = timestamp(match.get('starts_at')), timestamp(match.get('locks_at'))
    observed, inventory = timestamp(line.get('observed_at')), timestamp(inventory_at)
    if not valid_pair(line.get('probabilities')):
        status = 'unresolved'
    elif start and now >= start:
        status = 'started'
    elif (lock and now >= lock) or match.get('availability') in {'locked', 'past'}:
        status = 'locked'
    elif not start or not lock or lock > start or match.get('availability') != 'open':
        status = 'unknown-lock'
    elif inventory_complete is not True:
        status = 'inventory-unverified'
    elif not fresh(inventory_at, now, max_age_hours):
        status = 'stale-inventory'
    elif snapshot_bound is not True:
        status = 'unbound-snapshot'
    elif not fresh(line.get('observed_at'), now, max_age_hours):
        status = 'stale-line'
    else:
        status = 'current'
    expires = None
    if status == 'current':
        expires = iso(min(lock, start, observed + timedelta(hours=max_age_hours),
                          inventory + timedelta(hours=max_age_hours)))
    label, detail = STATUS[status]
    return {'status': status, 'current': status == 'current', 'label': label,
            'detail': detail, 'expires_at': expires}


def card_attributes(match: dict, state: dict) -> str:
    line = match.get('origination') or match.get('analysis') or {}
    attrs = {'data-safety-card': '', 'data-starts': match.get('starts_at') or '',
             'data-locks': match.get('locks_at') or '', 'data-observed': line.get('observed_at') or '',
             'data-availability': match.get('availability') or '',
             'data-line-valid': str(valid_pair(line.get('probabilities'))).lower(),
             'data-safety-status': state['status']}
    return ' '.join(f'{key}="{html.escape(str(value), quote=True)}"' for key, value in attrs.items())


def body_attributes(inventory_at, inventory_complete, *, snapshot_bound=True,
                    max_age_hours=MAX_PRICE_AGE_HOURS) -> str:
    attrs = {'data-pick-safety': '', 'data-inventory-at': inventory_at or '',
             'data-inventory-complete': str(inventory_complete is True).lower(),
             'data-snapshot-bound': str(snapshot_bound is True).lower(),
             'data-max-age-hours': max_age_hours}
    return ' '.join(f'{key}="{html.escape(str(value), quote=True)}"' for key, value in attrs.items())


def status_html(state: dict) -> str:
    hidden = ' hidden' if state['current'] else ''
    return (f'<p class="pick-safety" data-safety-message role="status"{hidden}>'
            f'<strong>{html.escape(state["label"])}.</strong> {html.escape(state["detail"])}</p>')
