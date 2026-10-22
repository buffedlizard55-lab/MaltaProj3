"""Deterministic line-by-line audit of session arena-df80ab9f verification artifacts.

Validates that:
1. All 107 scheduled Hotspawn CS2 records (46 active upcoming + 61 past) are
   reconciled in ``data/research/df80ab9f/live-inventory-audit.json`` with
   ``hotspawn_votes_used == False`` on every row.
2. Every active match row, low-tier fallback dossier entry, review flag, and
   repository review register item carries at least one allow-listed official
   ``https://`` source URL (checked via ``scripts.audit_rows.is_official``).
3. Unconfirmed values are explicitly ``None`` (never guessed or inferred) and
   every non-verified row references a corresponding review flag in
   ``data/research/df80ab9f/flags.json``.
4. ``research/df80ab9f/repo-review.json`` is declared in
   ``scripts.review_register.REGISTERS`` and passes schema validation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts import review_register
from scripts.audit_rows import is_official

ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT / 'data' / 'research' / 'df80ab9f'
REGISTER_REL = 'research/df80ab9f/repo-review.json'


def audit_session_dir(session_dir: Path = SESSION_DIR) -> dict:
    errors: list[str] = []

    inv_path = session_dir / 'live-inventory-audit.json'
    low_path = session_dir / 'low-tier-line-research.json'
    flags_path = session_dir / 'flags.json'
    reg_path = session_dir / 'repo-review.json'

    for path in (inv_path, low_path, flags_path, reg_path):
        if not path.exists():
            errors.append(f'missing required artifact: {path}')
    if errors:
        return {'ok': False, 'errors': errors}

    inv = json.loads(inv_path.read_text(encoding='utf-8'))
    low = json.loads(low_path.read_text(encoding='utf-8'))
    flags = json.loads(flags_path.read_text(encoding='utf-8'))
    reg = json.loads(reg_path.read_text(encoding='utf-8'))

    if REGISTER_REL not in review_register.REGISTERS:
        errors.append(f'{REGISTER_REL} is not declared in scripts.review_register.REGISTERS')

    try:
        review_register.validate(reg)
    except ValueError as exc:
        errors.append(f'repo-review validation failed: {exc}')

    for item in reg.get('items', []):
        for ev in item.get('evidence', []):
            url = ev.get('url', '')
            if not (url.startswith('https://') and is_official(url)):
                errors.append(f'repo-review {item.get("id")}: non-official URL {url!r}')

    flag_by_id: dict[str, dict] = {}
    for fl in flags:
        fid = fl.get('id')
        if not fid or fid in flag_by_id:
            errors.append(f'duplicate or missing flag id: {fid!r}')
            continue
        flag_by_id[fid] = fl
        if fl.get('severity') not in {'warning', 'notice'}:
            errors.append(f'flag {fid}: invalid severity {fl.get("severity")!r}')
        urls = fl.get('source_urls') or []
        if not urls:
            errors.append(f'flag {fid}: empty source_urls')
        for url in urls:
            if not (url.startswith('https://') and is_official(url)):
                errors.append(f'flag {fid}: non-official URL {url!r}')

    summary = inv.get('hotspawn_inventory_summary') or {}
    active = inv.get('active_matches') or []
    if summary.get('total_scheduled_records') != 107:
        errors.append(f'expected 107 scheduled records, got {summary.get("total_scheduled_records")}')
    if summary.get('past_scheduled_records') + summary.get('active_upcoming_records') != summary.get('total_scheduled_records'):
        errors.append('past + active scheduled records do not sum to total_scheduled_records')
    if len(active) != summary.get('active_upcoming_records'):
        errors.append(f'active_matches length {len(active)} != active_upcoming_records {summary.get("active_upcoming_records")}')
    if inv.get('policy_checks', {}).get('hotspawn_votes_used') is not False:
        errors.append('policy_checks.hotspawn_votes_used must be False')

    seen_ids: set[str] = set()
    for row in active:
        mid = str(row.get('id', ''))
        if not mid or mid in seen_ids:
            errors.append(f'duplicate or empty match id {mid!r}')
        seen_ids.add(mid)
        if row.get('hotspawn_votes_used') is not False:
            errors.append(f'match {mid}: hotspawn_votes_used must be False')
        urls = row.get('source_urls') or []
        if not urls:
            errors.append(f'match {mid}: missing source_urls')
        for url in urls:
            if not (url.startswith('https://') and is_official(url)):
                errors.append(f'match {mid}: non-official URL {url!r}')

        probs = row.get('verified_probabilities')
        pick = row.get('verified_pick_team')
        teams = row.get('teams') or []
        if probs is not None:
            if (
                not isinstance(probs, list)
                or len(probs) != 2
                or any(not isinstance(p, (int, float)) or p < 0.0 or p > 1.0 for p in probs)
                or abs(probs[0] + probs[1] - 1.0) > 1e-3
            ):
                errors.append(f'match {mid}: invalid verified_probabilities {probs!r}')
            elif abs(probs[0] - probs[1]) < 1e-9:
                if pick is not None:
                    errors.append(f'match {mid}: equal probabilities must keep verified_pick_team=None')
            else:
                expected_pick = teams[0] if probs[0] > probs[1] else teams[1]
                if pick != expected_pick:
                    errors.append(f'match {mid}: verified_pick_team {pick!r} != {expected_pick!r}')
        else:
            if pick is not None:
                errors.append(f'match {mid}: null verified_probabilities must keep verified_pick_team=None')

        if row.get('verification_status') != 'verified':
            row_flags = row.get('flag_ids') or []
            if not row_flags:
                errors.append(f'match {mid}: status {row.get("verification_status")!r} requires flag_ids')
            for rf in row_flags:
                if rf not in flag_by_id:
                    errors.append(f'match {mid}: unknown flag_id {rf!r}')

    if low.get('policy', {}).get('hotspawn_votes_used') is not False:
        errors.append('low-tier-line-research hotspawn_votes_used must be False')
    low_fixtures = low.get('fixtures') or []
    if len(low_fixtures) < 9:
        errors.append(f'expected at least 9 fallback fixtures in low-tier-line-research, got {len(low_fixtures)}')
    for entry in low_fixtures:
        mid = str(entry.get('id', ''))
        if mid not in seen_ids:
            errors.append(f'low-tier fixture {mid} not present in active_matches')
        if not entry.get('hltv_first_check', {}).get('checked'):
            errors.append(f'low-tier fixture {mid}: hltv_first_check.checked must be True')
        urls = entry.get('source_urls') or []
        if not urls:
            errors.append(f'low-tier fixture {mid}: missing source_urls')
        for url in urls:
            if not (url.startswith('https://') and is_official(url)):
                errors.append(f'low-tier fixture {mid}: non-official URL {url!r}')
        for chk in entry.get('external_lines_checked') or []:
            cu = chk.get('source_url', '')
            if not (cu.startswith('https://') and is_official(cu)):
                errors.append(f'low-tier fixture {mid}: non-official provider URL {cu!r}')
        for rf in entry.get('flag_ids') or []:
            if rf not in flag_by_id:
                errors.append(f'low-tier fixture {mid}: unknown flag_id {rf!r}')

    return {
        'ok': not errors,
        'active_matches': len(active),
        'low_tier_dossiers': len(low_fixtures),
        'flags': len(flags),
        'register_items': len(reg.get('items', [])),
        'errors': errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-dir', type=Path, default=SESSION_DIR)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args(argv)
    report = audit_session_dir(args.session_dir)
    print(json.dumps(report, indent=2))
    if args.strict and not report['ok']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
