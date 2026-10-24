# Live coverage reconciliation — arena-fc985c7b

Lobby observed **2026-10-24T07:35Z** · fixtures API sampled **2026-10-24T07:47Z** · published snapshot **2026-10-23T20:10:00Z**.

Both observations were made by opening the official pages directly; every id below comes from Hotspawn's own rendered *View Match* links or its fixtures API. No probability, pick or alias is written anywhere in this record.

## What the two sides say

- Rendered lobby: **25** open CS2 cards (9 in *Closing soon*, 16 in *Upcoming*), out of 88 CS2 matches this week.
- Published snapshot: **19** active fixtures — 17 with a pick (9 market, 3 bookmaker, 5 research model) and **2** unresolved.

## Cards the published snapshot has no row for

| Fixture | Teams | Competition | Starts (UTC) | In the fixtures API now |
| --- | --- | --- | --- | --- |
| 1079658 | Acend vs FORZE Reload | CCT Europe 2026 Series #11 | 2026-10-24T02:00:00Z | not sampled |
| 1081152 | HAVU vs Azuolas | CCT Europe 2026 Series #12 | 2026-10-24T05:00:00Z | not sampled |
| 1079659 | Spirit Academy vs Lavked | CCT Europe 2026 Series #11 | 2026-10-24T05:00:00Z | not sampled |
| 1081153 | Saint Sinners vs 6yuBoJlbl | CCT Europe 2026 Series #12 | 2026-10-24T08:00:00Z | not sampled |
| 1079660 | INOX Division vs BRUTE | CCT Europe 2026 Series #11 | 2026-10-24T08:00:00Z | not sampled |
| 1081154 | BakS vs ILLYRIANS | CCT Europe 2026 Series #12 | 2026-10-24T11:00:00Z | not sampled |
| 1079661 | Nuclear TigeRES vs ex-Zero Tenacity | CCT Europe 2026 Series #11 | 2026-10-24T11:00:00Z | not sampled |
| 1081156 | Spirit Academy vs LFO 10 | CCT Europe 2026 Series #12 | 2026-10-25T06:00:00Z | yes |
| 1081158 | FORZE Reload vs ex-RUSTEC | CCT Europe 2026 Series #12 | 2026-10-25T12:00:00Z | yes |

All nine are 24–25 October fixtures. Two of them (1081156 Spirit Academy vs LFO 10 and 1081158 FORZE Reload vs ex-RUSTEC) were confirmed present in the fixtures API at 2026-10-24T07:47Z, and the lobby's own tournament filter lists *CCT Europe 2026 Series #12 (5)* — exactly the five Series #12 ids above.

## Why, and what closes it

The published snapshot is 20:10Z on 23 October. No refresh has succeeded since: every `pages.yml` run failed at *Regression tests (repository fixtures, before any cache restore)*, the publisher's pre-collection gate. Running all 99 test modules one by one isolated the cause as a single defect — `scripts/originate.py` calls `egw_live.EVIDENCE_NAME` at line 1044 but PR #240 never imported the module, so `live_collect()` raised `NameError: name 'egw_live' is not defined` before the `try:` that was meant to make an aggregator outage non-fatal. Nine tests in `test_f9d0a5a2`, `test_origination_upgrade` and `test_source_integrity` failed on it; with the import present the full gate is **1270 tests, 0 failures**. The import is on `main` as of `292ea222` (session arena-5260ef4e reached the same file independently).

Because the collector reads the very API that already lists these fixtures, a successful refresh is what adds them. This record does **not** price them: no probability is inferred for a card that has no row.

## Sources

- https://play.hotspawn.com/lobby (rendered at 2026-10-24T07:35Z)
- https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1 (sampled at 2026-10-24T07:47Z)
- https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json (snapshot 2026-10-23T20:10:00Z)
