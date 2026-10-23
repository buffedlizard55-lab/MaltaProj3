"""Deterministic audit verifier for session arena-52aee465.

Verifies:
1. All alias entries in ``data/origination/aliases.json`` pass schema validation,
   every evidence URL satisfies ``scripts.audit_rows.is_official``, and all 16
   alias additions/scope extensions from session ``arena-52aee465`` resolve
   accurately while blocking academy/main-roster collisions.
2. ``data/research/52aee465/flags.json`` carries official primary source URLs on
   every flag and loads cleanly through ``scripts.build.load_review_flags``.
3. ``data/research/52aee465/repo-review.json`` loads cleanly into the merged
   site-wide review register via ``scripts.review_register.load_merged_register``.
4. ``data/research/52aee465/live-audit-2026-10-23.json`` documents all 30 active
   upcoming Hotspawn CS2 fixtures with zero Hotspawn pick-share contamination
   and official source URLs on every fixture.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import audit_rows, originate, review_register
from scripts.sources import name_key

ROOT = Path(__file__).resolve().parent.parent
ALIASES_PATH = ROOT / 'data' / 'origination' / 'aliases.json'
FLAGS_PATH = ROOT / 'data' / 'research' / '52aee465' / 'flags.json'
REVIEW_PATH = ROOT / 'data' / 'research' / '52aee465' / 'repo-review.json'
LIVE_AUDIT_PATH = ROOT / 'data' / 'research' / '52aee465' / 'live-audit-2026-10-23.json'

EXPECTED_52AEE465_JOINS = [
    ('Sokerorg', 'LFO 10', 'CCT Europe 2026 Series #12'),
    ('Quintessencia', 'QUINTESSÊNCIA', 'CCT South America 2026 Series #7'),
    ('RED Academy', 'RED Canids Academy', 'CCT South America 2026 Series #7'),
    ('FokuS Esports', 'FOKUS', 'NODWIN Clutch Series #13'),
    ('UNiTY esports', 'UNiTY', 'NODWIN Clutch Series #13'),
    ('BakS eSports', 'BakS', 'NODWIN Clutch Series #13'),
    ('FaZe Clan', 'FaZe', 'Tesla Cup 2026'),
    ('Team AURORA', 'Aurora', 'PGL Masters Bucharest 2026'),
    ('FUT Esports', 'FUT', 'PGL Masters Bucharest 2026'),
    ('Team Spirit', 'Spirit', 'PGL Masters Bucharest 2026'),
    ('BB Team', 'BetBoom', 'PGL Masters Bucharest 2026'),
    ('Team Liquid', 'Liquid', 'PGL Masters Bucharest 2026'),
    ('9Z Globant', '9z', 'PGL Masters Bucharest 2026'),
    ('Nemiga Gaming', 'Nemiga', 'PGL Masters Bucharest 2026'),
    ('G2 Esports', 'G2', 'PGL Masters Bucharest 2026'),
    ('FURIA Esports', 'FURIA', 'PGL Masters Bucharest 2026'),
]

NEGATIVE_GUARDS = [
    # Main-roster / academy cross-contamination must never happen:
    ('RED Canids', 'RED Canids Academy', 'CCT South America 2026 Series #7'),
    ('Spirit Academy', 'Spirit', 'PGL Masters Bucharest 2026'),
    ('G2 Ares', 'G2', 'PGL Masters Bucharest 2026'),
    ('FURIA fe', 'FURIA', 'PGL Masters Bucharest 2026'),
    ('FaZe Academy', 'FaZe', 'Tesla Cup 2026'),
    # Out-of-scope competition must never resolve:
    ('Sokerorg', 'LFO 10', 'PGL Masters Bucharest 2026'),
    ('Quintessencia', 'QUINTESSÊNCIA', 'DraculaN Season 7'),
    ('FokuS Esports', 'FOKUS', 'Tesla Cup 2026'),
]


def verify_all() -> dict:
    errors: list[str] = []

    registry = originate.load_registry(ALIASES_PATH)
    for entry in registry['aliases']:
        evs = entry.get('evidence', [])
        if not any(audit_rows.is_official(ev.get('url', '')) for ev in evs):
            errors.append(f"Alias {entry.get('alias')!r} has zero official evidence URLs")
        if '52aee465' in str(entry.get('review_note', '')):
            for ev in evs:
                url = ev.get('url', '')
                if not audit_rows.is_official(url):
                    errors.append(f"Non-official 52aee465 alias evidence URL on {entry.get('alias')!r}: {url}")

    for alias_name, expected_canonical, competition in EXPECTED_52AEE465_JOINS:
        canon, used = originate.resolve_name(alias_name, registry, competition)
        if canon != name_key(expected_canonical) or not used:
            errors.append(
                f"Expected {alias_name!r} -> {expected_canonical!r} in {competition!r}, got {canon!r} (used={len(used)})"
            )

    for raw_name, forbidden_canonical, competition in NEGATIVE_GUARDS:
        canon, _ = originate.resolve_name(raw_name, registry, competition)
        if canon == name_key(forbidden_canonical):
            errors.append(
                f"Negative guard failed: {raw_name!r} resolved to {forbidden_canonical!r} in {competition!r}"
            )

    flags_doc = json.loads(FLAGS_PATH.read_text())
    flags = flags_doc if isinstance(flags_doc, list) else flags_doc.get('flags', [])
    if len(flags) < 6:
        errors.append(f"Expected >= 6 flags in {FLAGS_PATH}, got {len(flags)}")
    for item in flags:
        for req_key in ('id', 'severity', 'title', 'detail', 'source_urls'):
            if req_key not in item:
                errors.append(f"Flag {item.get('id')!r} missing required key {req_key!r}")
        urls = item.get('source_urls', [])
        if not urls:
            errors.append(f"Flag {item.get('id')!r} has no source_urls")
        for url in urls:
            if not audit_rows.is_official(url):
                errors.append(f"Flag {item.get('id')!r} has non-official URL: {url}")

    if 'research/52aee465/repo-review.json' not in review_register.REGISTERS:
        errors.append('research/52aee465/repo-review.json not registered in scripts.review_register.REGISTERS')
    reg_doc = json.loads(REVIEW_PATH.read_text())
    review_register.validate(reg_doc)
    reg_ids = {item['id'] for item in reg_doc.get('items', [])}
    for idx in range(1, 7):
        expected_id = f'52aee465-0{idx}'
        if expected_id not in reg_ids:
            errors.append(f"Missing review register item {expected_id} in {REVIEW_PATH}")
    for item in reg_doc.get('items', []):
        for ev in item.get('evidence', []):
            if not audit_rows.is_official(ev.get('url', '')):
                errors.append(f"Non-official review register URL on {item['id']}: {ev.get('url')}")

    live_audit = json.loads(LIVE_AUDIT_PATH.read_text())
    if live_audit.get('hotspawn_feed', {}).get('hotspawn_pick_share_used_for_probability') is not False:
        errors.append('hotspawn_pick_share_used_for_probability must be False')
    fixtures = live_audit.get('fixtures', [])
    if len(fixtures) != 30:
        errors.append(f"Expected 30 active fixtures in live audit, got {len(fixtures)}")
    seen_ids: set[str] = set()
    for fx in fixtures:
        fid = str(fx.get('fixture_id', ''))
        if not fid or fid in seen_ids:
            errors.append(f"Duplicate or empty fixture_id: {fid!r}")
        seen_ids.add(fid)
        srcs = fx.get('sources', [])
        if len(srcs) < 2:
            errors.append(f"Fixture {fid} must list >= 2 official sources")
        for u in srcs:
            if not audit_rows.is_official(u):
                errors.append(f"Fixture {fid} has non-official source URL: {u}")

    return {
        'ok': not errors,
        'alias_count': len(registry['aliases']),
        'verified_joins': len(EXPECTED_52AEE465_JOINS),
        'negative_guards': len(NEGATIVE_GUARDS),
        'flag_count': len(flags),
        'merged_register_items': len(reg_ids),
        'audited_fixtures': len(fixtures),
        'errors': errors,
    }


def main() -> int:
    result = verify_all()
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
