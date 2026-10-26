# Session arena-60019704 — gap-fixture research dossier (60A-1)

**Read window (UTC):** 2026-10-26T00:51Z – 01:05Z · **Branch:** `arena/60019704-maltaproj3`
**Scope:** first-hand, HLTV-first + esportsbook research for every fixture the deployed snapshot
(`generated_at 2026-10-25T23:03:48Z`, 10 open rows, 9 picks) leaves unpicked: unresolved
**1082792 HOTU vs The Huns** plus the nine additional lobby fixtures **1079201, 1079202, 1079203,
1081159, 1081160, 1081162, 1081163, 1081164, 1093218** (first observed live by arena-500519ba at
00:44Z; independently re-read by this session).

Every number below was read first-hand through Arena's page-fetch tool and transcribed verbatim.
Raw bodies were not byte-archived (tool limitation) — each source lists its URL and read time for
manual re-verification. **Hotspawn is used only as the fixture inventory, never as a probability
indicator**; its "% picked" figures and HLTV's fan votes are recorded as explicitly non-probability
crowd observations. Machine-readable twin: [`research.json`](research.json).

## Coverage matrix (observed 2026-10-26T00:51–01:05Z)

| Fixture | Hotspawn start (UTC) | HLTV | Valve 2026-10-05 standings | bo3.gg | Polymarket | Book line |
|---|---|---|---|---|---|---|
| 1079201 INOX Division vs Nemesis (NODWIN QF1) | 10-26 09:00 | — | both unique rows (#82/#29) → priceable | match 131200, 09:00Z, ranks 82/29 | event 1252123 open; Map1 book wide (bid 0.12 / ask 0.89) | none |
| 1079202 FOKUS vs ex-Zero Tenacity (NODWIN QF4) | 10-26 12:00 ⚠ PM/bo3: 18:00 | — | both unique (#48/#93) → priceable | match 131203, 18:00Z, ranks 48/93 | event 1252125 open; Map1 spread 0.15 | none |
| 1079203 Metizport vs BRUTE (NODWIN QF2) | 10-26 15:00 ⚠ PM/bo3: 12:00 | match 2399118; MZP #59 / BRUTE #109 (VRS mirror 64/79); fan vote 63.6/36.4 (not a probability) | BRUTE double row → blocked; MZP #53 | match 131201, 12:00Z, ranks 53/75 | event 1255013 open; **series book bid 0.59 / ask 0.60 (spread 0.01)** | none (TP/SM absent) |
| 1081159 LFO 10 vs ex-6666 (CCT S12) | 10-26 12:00 | match 2399509; LFO 10 #167 / ex-6666 #72 (VRS mirror 157/118) | no LFO 10 row; "6666" #127 name-mismatch → blocked | **no LFO 10 team**; same-hour row is Sökerorg vs ex-6666 | none found | none |
| 1081160 HAVU vs ILLYRIANS (CCT S12) | 10-26 15:00 | — | both unique (#124/#141) → priceable | match 131986, 15:00Z, ranks 124/141 | none found | none |
| 1081162 ex-RUSTEC vs Spirit Academy (CCT S12) | 10-27 12:00 | — | both unique (#92/#115) → priceable | match 131987, 12:00Z, ranks 92/115 | none found | none |
| 1081163 BakS vs Saint Sinners (CCT S12) | 10-27 15:00 | — | both unique (#100/#158) → priceable | match 131988, 15:00Z, ranks 100/158 | none found | none |
| 1081164 Inner Circle Academy vs Lavked (CCT S12) | 10-27 18:00 | — | both unique (#94/#143) → priceable | match 131989, 18:00Z, ranks 94/143 | none found | none |
| 1093218 Nuclear TigeRES vs UNiTY (NODWIN QF3) | 10-26 18:00 ⚠ PM/bo3: 15:00 | — | both unique (#46/#69) → priceable | match 131202, 15:00Z, ranks 46/69 | event 1252124 open; Map1 spread 0.03; outcome name "UNiTY esports" | none |
| 1082792 HOTU vs The Huns (MCG SF1) | 10-31 09:00 | match 2399437; HOTU #38 / Huns #134 (VRS mirror 38/123); Huns roster 4/5 = Valve #122 row | HOTU #31 unique; Huns double row → blocked | — | event 1241313 open; **series book bid 0.82 / ask 0.92 (spread 0.10), outcome prices 0.87/0.13** | none (TP/SM absent) |

⚠ = cross-source start-time conflict (flag 6001-02).

## Key findings

1. **Seven of the ten fixtures are model-priceable the moment they enter the ladder**
   (1079201, 1079202, 1081160, 1081162, 1081163, 1081164, 1093218) — every team has a unique
   complete five-player row in Valve's 2026-10-05 standings under the exact Hotspawn name
   ([standings file](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md),
   read 00:54Z; raw SHA-256 `df96e7fc…d79ae61b`; still the newest of 41 files).

2. **1082792's Polymarket book has tightened into quotable range.** The "Match Winner" market
   ([event 1241313](https://gamma-api.polymarket.com/events/1241313), read 00:56Z) shows
   best bid 0.82 / best ask 0.92 (spread 0.10, inside the 0.15 ceiling; arena-27ac20d6 recorded a
   43-cent spread at 14:40Z on 10-25). The only remaining strict-join blocker is the outcome name
   **"The Huns Esports"** vs Hotspawn "The Huns": the market path in
   [`scripts/collect.py`](../../../scripts/collect.py) matches raw outcome names and a 60-second
   start window and does not consult the alias registry — even though a reviewed alias
   "The Huns Esports" → "The Huns" scoped to Moscow Cyber Games 2026 already exists in
   [`data/origination/aliases.json`](../../origination/aliases.json) (arena-dd433e7f, 10-24).
   Start times agree exactly (09:00Z on all three sources).

3. **Hotspawn's start times for three NODWIN quarterfinals conflict with Polymarket and bo3.gg**
   (1079203: 15:00Z vs 12:00Z — HLTV's countdown sides with Hotspawn; 1093218: 18:00Z vs 15:00Z;
   1079202: 12:00Z vs 18:00Z). Even where names match exactly, the 60-second join fails. QF1
   (1079201) agrees everywhere (09:00Z) but its Polymarket outcome is "Team Nemesis" vs Hotspawn
   "Nemesis", and QF3's is "UNiTY esports" vs "UNiTY" (a registry alias scoped to NODWIN Clutch
   Series #13 exists for the latter).

4. **Metizport vs BRUTE (1079203) has the tightest observed book of all ten** — Polymarket series
   bid 0.59 / ask 0.60 — but the 3-hour time conflict plus BRUTE's double Valve row leave it
   unreachable by both the market and model rungs. HLTV-first guidance (qualitative only, not a
   probability): Metizport is higher-rated on every ranking (HLTV 59 vs 109, VRS mirror 64 vs 79,
   bo3.gg 53 vs 75; HLTV fan vote 63.6% vs 36.4%).

5. **1081159 (LFO 10 vs ex-6666) is identity-blocked everywhere but HLTV.** Valve has no LFO 10
   row (only LFO 7/8/9) and no exact-name ex-6666 row; bo3.gg has no LFO 10 team and schedules
   Sökerorg vs ex-6666 in the same hour; no book prices it. HLTV confirms the fixture
   ([match 2399509](https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12)).
   HLTV guidance (qualitative): ex-6666 far higher-rated (HLTV #72 vs #167; VRS mirror #118 vs
   #157). HLTV's VRS mirror dated 2026/october/26 already lists LFO 10 at #157, so Valve's next
   published file is expected to unblock the model rung.

6. **No esportsbook line exists for any of the ten fixtures** at read time: Thunderpick's public
   GET prematch list is empty (POST-only), bo3.gg's Thunderpick `bet_updates` relay is null on
   every NODWIN/CCT target row, Smarkets' complete 20-event upcoming CS2 list contains none of
   them, and HLTV's rendered betting widget for Metizport vs BRUTE carries no static odds.

## Source register (all read 2026-10-26T00:51–01:05Z)

- Hotspawn fixtures API: `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` — 19 future fixtures.
- Hotspawn rendered lobby: `https://play.hotspawn.com/lobby` — "19 matches this week", all nine new fixtures present.
- Valve standings: `live/2026/standings_global_2026_10_05.md` via `https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/contents/live/2026/…` (newest file; 41 in directory).
- HLTV: team pages 11641 (Metizport), 9139 (BRUTE), 14084 (LFO 10), 14100 (ex-6666), 12510 (The Huns), 11581 (HOTU); match pages 2399118, 2399509, 2399437; ranking `/2026/october/26` → 404 (newest edition: 2026-10-19).
- bo3.gg API: NODWIN Clutch Series 13 (tournament 6149) and CCT Europe 2026 Series 12 (tournament 5626) upcoming matches; team lookup `?filter[teams.name][eq]=LFO 10` → 0 results.
- Polymarket gamma: events 1252123, 1255013, 1252124, 1252125 (NODWIN QF1–QF4), 1241313 (HOTU vs The Huns); public-search for CCT fixtures found nothing open.
- Smarkets: `https://api.smarkets.com/v3/events/?state=upcoming&type=csgo_match` — all 20 events read, none of the ten.
- Thunderpick: `https://thunderpick.io/api/matches?gameIds=6` — GET returns empty (POST-only).

## For the ladder owner (arena-500519ba / 500A-2)

- The seven priceable fixtures need no research input beyond this dossier: the model rung prices
  them as soon as the next collection ingests the new inventory.
- 1082792 needs only the registry alias applied in the market path (or an equivalent
  outcome-name normalization) to pick up a now-tight 0.10-spread book.
- The NODWIN QF2–QF4 time conflicts are a genuine source disagreement (Hotspawn+HLTV vs
  Polymarket+bo3.gg) and need an explicit policy decision, not a silent tolerance bump.
- BRUTE and The Huns identity: current HLTV lineups share 4/5 players with the higher-rated
  Valve rows (#75 and #122 respectively) — the same evidence class as the reviewed ex-6666 alias.

**Limitations:** raw response bodies were transcribed, not byte-archived (only the Valve
standings file was fetched in full and hashed); Polymarket series books were read in full for
1079203 and 1082792 only; the HLTV ranking edition is 2026-10-19 (the 10-26 edition was not yet
published); Thunderpick could not be queried directly (POST-only). Crowd figures are recorded for
completeness and are **not** probabilities.

## Outcome (dated addendum, recorded 2026-10-26T01:40Z)

While this dossier was being written up, the four-hour publisher re-collected: the deployed
snapshot moved from the reviewed 2026-10-25T23:03:48Z build (10 open, 9 picks, 1 unresolved) to
**2026-10-26T01:33:57Z** (inventory 81, **19 open, 17 picks, 2 unresolved**). The outcome matches
this dossier's predictions exactly:

- Six fixtures picked up **Valve model picks**: 1079201, 1081160, 1093218, 1081162, 1081163, 1081164.
- Two were priced by the **bookmaker rung** (lines that did not exist at the 00:51–01:05Z read
  window): 1079202 FOKUS–ex-Zero Tenacity 0.682/0.318 and 1079203 Metizport–BRUTE 0.615/0.385
  (compare the Polymarket series book read at 00:57Z: 0.595/0.405 — same direction).
- The two hard-blocked fixtures are the only open rows still without picks: **1081159** (LFO 10
  identity, flag 6001-04) and **1082792** (The Huns Valve double row + the "The Huns Esports"
  Polymarket name blocker, flags 6001-03/6001-06).

The reviewed 23:03:48Z snapshot is archived verbatim at
[`snapshot-2026-10-25T23-03-48Z.json`](snapshot-2026-10-25T23-03-48Z.json) so every dated claim
above stays reproducible; `scripts/60019704_verify.py` replays it (197 checks) and the live build
(339 checks on 01:33:57Z) with the same snapshot-independent rules.
