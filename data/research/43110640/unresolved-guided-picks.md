# Picks for every match — unresolved-fixture research (arena-43110640, 2026-10-24)

Scope: the **2 fixtures with no pick** in the published snapshot
`2026-10-23T20:10:00Z` (19 active, 17 with picks, 2 unresolved). Research
order per the brief: **HLTV first, then esportsbooks / betting lines**.
Hotspawn "% picked" and HLTV fan votes were seen on every page and excluded —
they are never probabilities. Full machine-readable record:
[`unresolved-guided-picks.json`](unresolved-guided-picks.json).

## 1082858 — Ground Zero vs Off Chops (DFRAG Invitational 2026, 2026-10-26T03:00Z)

- **HLTV first** — [match 2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026):
  identity + BO3 (LAN) confirmed; Ground Zero HLTV #143/VRS #131, Off Chops
  HLTV #142. Betting block: only a Stake US sweepstake promo — **no odds**.
- **Esportsbooks** — Polymarket's event book is crossed/wider than every
  ceiling; Smarkets' live book (~0.185 spreads, 2026-10-23) is guidance only.
  [EGamersWorld](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d)
  publishes a named bookmaker line (Vave): **Ground Zero 3.44 / Off Chops 1.24**.
- **Guided pick: Off Chops — 73.5% vs 26.5%** (no-vig of 3.44/1.24).
  *Limitations:* single aggregated reference, not a first-party quote; from
  this session `scripts/egw_live.py` retries the EGW index automatically every
  refresh and prices it only inside the existing freshness/placeholder gates.

## 1082792 — HOTU vs The Huns (Moscow Cyber Games 2026, 2026-10-31T09:00Z)

- **HLTV first** — [match 2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026):
  identity + BO3 (LAN) semi-final confirmed; HOTU HLTV #38 (rating 1.14),
  The Huns HLTV #134. Betting block: promo only — **no odds**.
- **Esportsbooks** — EGamersWorld shows only the identical **1.8/1.8
  placeholder** (rejected by the reviewed gate); no priced Polymarket fixture.
- **Identity join** — [Valve 2026-10-05 standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md):
  HOTU 1437 pts (unique). The Huns' current HLTV lineup shares **4/5** players
  with the 944-pt row (standing 122) and 2/5 with the 701-pt row, so the
  documented four-of-five join selects **944 pts**.
- **Guided pick: HOTU — model 94.1% vs 5.9%** (Valve fit.js logistic, RD 75).
  *Limitations:* uncalibrated — trust the direction, not the extreme number;
  the one-player change is not quantified; the automated ladder replays this
  join only when the runner's HLTV lineup fetch succeeds (HLTV returns 403 to
  the runner; read first-hand here on 2026-10-24).

## What changed in the pipeline

1. **CI unblock:** scheduled `pages.yml` runs were failing before collecting
   (time-bomb regression test, wall-clock vs a fixed 2026-10-23 snapshot).
   Fixed in `tests/test_ca7e10e5_snapshot.py` by pinning the reference clock.
2. **Automated EGW rung:** `scripts/egw_live.py` fetches the EGW CS2 index
   every refresh, joins match-page slugs to fixtures by exact team names,
   and emits reviewed-schema entries that must still pass
   `reference_odds.quote()` (placeholder, freshness and start-time gates).
3. These two fixtures therefore resolve automatically on a future refresh
   when a compliant line (or the HLTV lineup proof) is reachable; until then
   the guided picks above are the published guidance, with limitations, on
   the Unresolved page via the flags below.
