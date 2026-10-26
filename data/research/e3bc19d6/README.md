# Session arena-e3bc19d6 — live coverage read, pick status for every open Hotspawn CS2 fixture, and a line-by-line replay

Read window: **2026-10-26T00:44Z–01:05Z**. Every figure below is read directly from the source named in the same row or recomputed from it by [`scripts/e3bc19d6_verify.py`](../../../scripts/e3bc19d6_verify.py). Nothing in this dossier is an estimate that the site published.

## 1. What was read

| Source | URL | What it gave |
| --- | --- | --- |
| Hotspawn scheduled-fixture API (the endpoint its own lobby client calls) | <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1> | **19 future-start CS2 records** at the read time; ids, teams, competition, start and lock times are in `live-inventory.json` |
| Hotspawn CS2 lobby | <https://play.hotspawn.com/cs2-pickems> | the per-fixture route (`#fixture-<id>`) linked from every row that is not yet in a build |
| HLTV event match lists | <https://www.hltv.org/events/9457/matches> · <https://www.hltv.org/events/9440/matches> | identity, series format and UTC start for the **nine** fixtures added since the published snapshot (`hltv-identities.json`) |
| HLTV odds & prediction page | <https://www.hltv.org/betting/analytics/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12> | ranks for both sides (#167 / #72); **no readable two-way price** — the odds block is client-side |
| Official Valve Regional Standings | <https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md> | the rating row behind every `model` row and the pricing verdict for each new fixture (`valve-coverage.json`) |
| The published build | `origination.json` + `snapshot.json` in the branch root, snapshot generated **2026-10-25T23:03:48Z** | the ten picks that were already live, replayed from their own evidence (`replay.json`) |

## 2. The answer to "why is there no pick for this match?"

- **19 fixtures were open** on Hotspawn at the read time. The published snapshot carries **10** of them, each with a pick that replays exactly from its own evidence (10/10).
- **9 fixtures were created after that snapshot** — five CCT Europe 2026 Series #12 and four NODWIN Clutch Series 13 quarter-finals. They are not missing because of a rule: the four-hour refresh had not run since the bracket was drawn.
- **7 of those 9 can be priced by a rung already in the ladder** — both sides carry exactly one complete five-player row in Valve's official standings.
- **2 depend on the HLTV rungs**: `1081159` LFO 10 vs ex-6666 (no Valve row for either side; HLTV ranks them #167 and #72) and `1079203` Metizport vs BRUTE (two complete Valve rows share the name BRUTE, so the Valve rung must fail closed until an HLTV lineup proves which roster plays).
- **0 open fixtures are left with no pricing rung at all.** Each of the 19 has a verifiable path to a probability that does not invent one.

## 3. Every open fixture, line by line

| # | Fixture (Hotspawn) | Competition | Starts (UTC) | Published pick | Probabilities | Basis | Valve rows | HLTV | Pricing path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Ground Zero vs Off Chops](https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858) | DFRAG Invitational 2026 | 2026-10-26T03:00:00Z | **Off Chops** | 20.0% / 80.0% | [Polymarket](https://polymarket.com/event/cs2-gz1-offcho-2026-10-25) · market · replayed | absent: Off Chops | — | already published |
| 2 | [NEXVOID vs Alter Ego](https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859) | DFRAG Invitational 2026 | 2026-10-26T03:00:00Z | **NEXVOID** | 57.5% / 42.5% | [Thunderpick](https://thunderpick.io/api/matches) · bookmaker · replayed | both unique | — | already published |
| 3 | [INOX Division vs Nemesis](https://play.hotspawn.com/cs2-pickems#fixture-1079201) | NODWIN Clutch Series #13 | 2026-10-26T09:00:00Z | — not in snapshot | — | — | both unique | [bo3](https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13) | Valve official-rating model rung |
| 4 | [LFO 10 vs ex-6666](https://play.hotspawn.com/cs2-pickems#fixture-1081159) | CCT Europe 2026 Series #12 | 2026-10-26T12:00:00Z | — not in snapshot | — | — | absent: LFO 10, ex-6666 | [bo3](https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12) | HLTV world-ranking rung |
| 5 | [FOKUS vs ex-Zero Tenacity](https://play.hotspawn.com/cs2-pickems#fixture-1079202) | NODWIN Clutch Series #13 | 2026-10-26T12:00:00Z | — not in snapshot | — | — | both unique | [bo3](https://www.hltv.org/matches/2399117/fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13) | Valve official-rating model rung |
| 6 | [HAVU vs ILLYRIANS](https://play.hotspawn.com/cs2-pickems#fixture-1081160) | CCT Europe 2026 Series #12 | 2026-10-26T15:00:00Z | — not in snapshot | — | — | both unique | [bo3](https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12) | Valve official-rating model rung |
| 7 | [Metizport vs BRUTE](https://play.hotspawn.com/cs2-pickems#fixture-1079203) | NODWIN Clutch Series #13 | 2026-10-26T15:00:00Z | — not in snapshot | — | — | ambiguous: BRUTE | [bo3](https://www.hltv.org/matches/2399118/metizport-vs-brute-nodwin-clutch-series-13) | HLTV lineup-proof disambiguation, then HLTV world-ranking rung |
| 8 | [Nuclear TigeRES vs UNiTY](https://play.hotspawn.com/cs2-pickems#fixture-1093218) | NODWIN Clutch Series #13 | 2026-10-26T18:00:00Z | — not in snapshot | — | — | both unique | [bo3](https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13) | Valve official-rating model rung |
| 9 | [FlyQuest vs Staqued](https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860) | DFRAG Invitational 2026 | 2026-10-27T03:00:00Z | **FlyQuest** | 92.5% / 7.5% | [Polymarket](https://polymarket.com/event/cs2-fly-staque-2026-10-26) · market · replayed | absent: Staqued | — | already published |
| 10 | [Rooster vs Abyssal](https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861) | DFRAG Invitational 2026 | 2026-10-27T03:00:00Z | **Abyssal** | 47.8% / 52.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model · replayed | both unique | — | already published |
| 11 | [B8 vs K27](https://www.hotspawn.com/matches/b8-vs-k27-tesla-cup-2026-1082897) | Tesla Cup 2026 | 2026-10-27T08:00:00Z | **B8** | 59.5% / 40.5% | [Polymarket](https://polymarket.com/event/cs2-b8-k271-2026-10-27) · market · replayed | both unique | — | already published |
| 12 | [Alliance vs FaZe](https://www.hotspawn.com/matches/alliance-vs-faze-tesla-cup-2026-1082898) | Tesla Cup 2026 | 2026-10-27T11:00:00Z | **FaZe** | 37.5% / 62.5% | [Polymarket](https://polymarket.com/event/cs2-all-faze-2026-10-27) · market · replayed | both unique | — | already published |
| 13 | [ex-RUSTEC vs Spirit Academy](https://play.hotspawn.com/cs2-pickems#fixture-1081162) | CCT Europe 2026 Series #12 | 2026-10-27T12:00:00Z | — not in snapshot | — | — | both unique | [bo3](https://www.hltv.org/matches/2399512/ex-rustec-vs-spirit-academy-cct-2026-europe-series-12) | Valve official-rating model rung |
| 14 | [BakS vs Saint Sinners](https://play.hotspawn.com/cs2-pickems#fixture-1081163) | CCT Europe 2026 Series #12 | 2026-10-27T15:00:00Z | — not in snapshot | — | — | both unique | [bo3](https://www.hltv.org/matches/2399513/baks-vs-saint-sinners-cct-2026-europe-series-12) | Valve official-rating model rung |
| 15 | [Luminosity vs HOTU](https://www.hotspawn.com/matches/luminosity-vs-hotu-tesla-cup-2026-1082900) | Tesla Cup 2026 | 2026-10-27T17:00:00Z | **Luminosity** | 52.5% / 47.5% | [Polymarket](https://polymarket.com/event/cs2-lg6-hotu-2026-10-27) · market · replayed | both unique | — | already published |
| 16 | [Inner Circle Academy vs Lavked](https://play.hotspawn.com/cs2-pickems#fixture-1081164) | CCT Europe 2026 Series #12 | 2026-10-27T18:00:00Z | — not in snapshot | — | — | both unique | [bo3](https://www.hltv.org/matches/2399514/inner-circle-academy-vs-lavked-cct-2026-europe-series-12) | Valve official-rating model rung |
| 17 | [Envy vs GamerLegion](https://www.hotspawn.com/matches/envy-vs-gamerlegion-tesla-cup-2026-1082901) | Tesla Cup 2026 | 2026-10-27T20:00:00Z | **GamerLegion** | 45.5% / 54.5% | [Polymarket](https://polymarket.com/event/cs2-envy-gl1-2026-10-27) · market · replayed | absent: Envy | — | already published |
| 18 | [HOTU vs The Huns](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) | Moscow Cyber Games 2026 | 2026-10-31T09:00:00Z | **HOTU** | 87.0% / 13.0% | [Polymarket](https://polymarket.com/event/cs2-hotu-the9-2026-10-31) · market · replayed | ambiguous: The Huns | — | already published |
| 19 | [5star vs 1WIN](https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793) | Moscow Cyber Games 2026 | 2026-10-31T13:00:00Z | **1WIN** | 17.8% / 82.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model · replayed | both unique | — | already published |

The fixture link is the canonical Hotspawn match page where the published build already carries it, and the official lobby anchor `#fixture-<id>` otherwise — no slug is guessed.

## 4. Replay of every published probability

| Fixture | Method | Evidence read | Published | Recomputed | Delta |
| --- | --- | --- | --- | --- | --- |
| 1082858 Ground Zero vs Off Chops | market | bid [0.18, 0.78] · ask [0.22, 0.82] | 20.00% / 80.00% | 20.00% / 80.00% | 0e+00 |
| 1082859 NEXVOID vs Alter Ego | bookmaker | decimal odds [1.61, 2.18] | 57.52% / 42.48% | 57.52% / 42.48% | 0e+00 |
| 1082860 FlyQuest vs Staqued | market | bid [0.91, 0.06] · ask [0.94, 0.09] | 92.50% / 7.50% | 92.50% / 7.50% | 0e+00 |
| 1082861 Rooster vs Abyssal | model | Valve points [718, 734] | 47.76% / 52.24% | 47.76% / 52.24% | 0e+00 |
| 1082897 B8 vs K27 | market | bid [0.59, 0.4] · ask [0.6, 0.41] | 59.50% / 40.50% | 59.50% / 40.50% | 0e+00 |
| 1082898 Alliance vs FaZe | market | bid [0.37, 0.62] · ask [0.38, 0.63] | 37.50% / 62.50% | 37.50% / 62.50% | 0e+00 |
| 1082900 Luminosity vs HOTU | market | bid [0.51, 0.46] · ask [0.54, 0.49] | 52.50% / 47.50% | 52.50% / 47.50% | 0e+00 |
| 1082901 Envy vs GamerLegion | market | bid [0.45, 0.54] · ask [0.46, 0.55] | 45.50% / 54.50% | 45.50% / 54.50% | 0e+00 |
| 1082792 HOTU vs The Huns | market | bid [0.82, 0.08] · ask [0.92, 0.18] | 87.00% / 13.00% | 87.00% / 13.00% | 0e+00 |
| 1082793 5star vs 1WIN | model | Valve points [1110, 1383] | 17.82% / 82.18% | 17.82% / 82.18% | 0e+00 |

All ten rows replay to better than 1e-8. The rules are the publisher's own: normalised order-book midpoints for a prediction market, proportional margin removal on a bookmaker's raw decimal odds, and Valve's `fit.js` logistic (`p = 1/(1+10**(g*(points_b − points_a)/400))`, with `g` from the published RD assumption of 75) for a research-model row.

## 5. Limitations of this dossier

1. **It cannot publish.** This sandbox reaches source hosts through a server-side fetch, not through the collector, so the dossier states which rung *can* price each fixture. The proof that the publisher actually priced them is the next refreshed snapshot — verified after the merge and recorded in `COORDINATION.md`.
2. **HLTV prices are not readable.** For `1081159` the odds page lists ranks and map records, but its bookmaker odds block is client-side and the fetched document carries no numeric price. That is a rendering limitation, not proof that no bookmaker prices the match, and no odds value is quoted from it.
3. **The Valve input is the dated official snapshot.** `data/evidence/valve-ratings.json` carries the 2026-10-05 publication because the tracked file is the deterministic replay fixture; the live publisher re-reads the current official file on every run and the code refuses an input older than 35 days.
4. **Hotspawn leaves `best_of` null** for every CS2 record, so the format is verified on HLTV per fixture (all nine checked are best-of-3) and never inferred for the Hotspawn record.
5. **No community vote is an input.** Hotspawn's community vote percentages are present in the source payload and deliberately not transcribed here; the verifier fails if one appears.

## 6. How to re-check it

```bash
python -m scripts.e3bc19d6_verify          # replays every row, cross-checks the official files
python -m unittest tests.test_e3bc19d6_verification
```

The verifier also compares the transcribed inventory against the collector's own `data/evidence/hotspawn-fixtures.json` whenever that file carries the same fixture id, so after the next refresh a transcription error cannot survive; when the published evidence is a different vintage it reports `absent-from-vintage` instead of passing silently.

## 7. Review flags published by this session

- **warning** · `e3bc19d6-nine-fixtures-added-after-the-published-snapshot` — Nine open fixtures exist on Hotspawn that the published 23:03:48Z snapshot does not carry yet
- **warning** · `e3bc19d6-brute-ambiguous-valve-rows` — 1079203 Metizport vs BRUTE: two complete official Valve rows share the name BRUTE, so the Valve rung fails closed
- **warning** · `e3bc19d6-hltv-odds-block-has-no-readable-price` — HLTV's odds-and-prediction page for 1081159 carries ranks but no readable two-way price
- **info** · `e3bc19d6-hotu-the-huns-book-is-now-tight` — The HOTU vs The Huns exchange book is now 0.82/0.92 and 0.08/0.18, so the fixture is priced from a real line
- **info** · `e3bc19d6-valve-input-vintage` — The committed Valve rating input is dated 2026-10-05, 21 days old, because it is the replay fixture
- **info** · `e3bc19d6-hotspawn-best-of-is-null` — All 19 open fixtures carry a null Hotspawn best-of while HLTV lists best-of-3 for the nine checked
