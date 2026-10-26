# Session arena-e3bc19d6 — live coverage read, picks for every open Hotspawn CS2 fixture, and a line-by-line replay

Read window **2026-10-26T00:44Z–01:25Z**. Every figure below is read directly from the source named beside it or recomputed from it by [`scripts/e3bc19d6_verify.py`](../../../scripts/e3bc19d6_verify.py). Nothing here is an estimate that the site invented.

## 1. Headline

- The official Hotspawn fixture endpoint returned **19 future-start CS2 fixtures** at the read time.
- The build published **41 minutes later** (`2026-10-26T01:04:30Z`, main `179f519a`) carries **19 of 19 with a pick**, and **all 19 replay exactly** from the evidence their own row carries.
- **7** picks came from a prediction-market book, **3** from a single bookmaker's two-way line, **1** from a two-book consensus and **8** from a labelled research model (7 official Valve rating rows and 1 own results-based fit).
- **No fixture was left blank**, and no probability, price, alias or identity was invented to fill a gap.

## 2. What was read

| Source | URL | What it gave |
| --- | --- | --- |
| Hotspawn scheduled-fixture API (the endpoint its own lobby client calls) | <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1> | the 19 future-start records, with ids, teams, competition, start and lock times (`live-inventory.json`) |
| Hotspawn CS2 lobby | <https://play.hotspawn.com/cs2-pickems> | the per-fixture route (`#fixture-<id>`) linked from every row not yet in a build |
| HLTV event match lists | <https://www.hltv.org/events/9457/matches> · <https://www.hltv.org/events/9440/matches> | identity, series format and UTC start for the nine fixtures added since the previous snapshot (`hltv-identities.json`) |
| HLTV odds & prediction page | <https://www.hltv.org/betting/analytics/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12> | ranks for both sides (#167 / #72); **no readable two-way price** — the odds block is client-side |
| Official Valve Regional Standings | <https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md> | the rating row behind every `model` row and the pricing verdict for each new fixture (`valve-coverage.json`) |
| The build published after this read | <https://github.com/buffedlizard55-lab/MaltaProj3/blob/179f519a2cb40a9e3b4cbb6f57e3dd5956da6ebb/origination.json> | every pick and both probabilities, replayed row by row (`published-verification.json`) |
| The build that was live at the read time | `snapshot.json` 2026-10-25T23:03:48Z + `origination.json` | the ten picks then live, replayed row by row (`replay.json`) |

## 3. Every open fixture, line by line

| # | Fixture (Hotspawn) | Competition | Starts (UTC) | Pick | Both probabilities | Basis | Valve rows | HLTV | Replay |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | [Ground Zero vs Off Chops](https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858) | DFRAG Invitational 2026 | 2026-10-26T03:00:00Z | **Off Chops** | 20.5% / 79.5% | [Polymarket](https://polymarket.com/event/cs2-gz1-offcho-2026-10-25) · market | absent: Off Chops | — | pass |
| 2 | [NEXVOID vs Alter Ego](https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859) | DFRAG Invitational 2026 | 2026-10-26T03:00:00Z | **NEXVOID** | 59.2% / 40.8% | [Thunderpick](https://thunderpick.io/api/matches) · bookmaker | both unique | — | pass |
| 3 | [INOX Division vs Nemesis](https://play.hotspawn.com/cs2-pickems#fixture-1079201) | NODWIN Clutch Series #13 | 2026-10-26T09:00:00Z | **Nemesis** | 12.3% / 87.7% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model | both unique | [bo3](https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13) | pass |
| 4 | [LFO 10 vs ex-6666](https://play.hotspawn.com/cs2-pickems#fixture-1081159) | CCT Europe 2026 Series #12 | 2026-10-26T12:00:00Z | **ex-6666** | 39.0% / 61.0% | [Own results-based model (bo3.gg series results)](https://bo3.gg/matches/sokerorg-vs-ex-6666-26-10-2026) · model | absent: LFO 10, ex-6666 | [bo3](https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12) | pass |
| 5 | [FOKUS vs ex-Zero Tenacity](https://play.hotspawn.com/cs2-pickems#fixture-1079202) | NODWIN Clutch Series #13 | 2026-10-26T12:00:00Z | **FOKUS** | 68.2% / 31.8% | [Thunderpick](https://thunderpick.io/api/matches) · bookmaker | both unique | [bo3](https://www.hltv.org/matches/2399117/fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13) | pass |
| 6 | [HAVU vs ILLYRIANS](https://play.hotspawn.com/cs2-pickems#fixture-1081160) | CCT Europe 2026 Series #12 | 2026-10-26T15:00:00Z | **HAVU** | 60.3% / 39.7% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model | both unique | [bo3](https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12) | pass |
| 7 | [Metizport vs BRUTE](https://play.hotspawn.com/cs2-pickems#fixture-1079203) | NODWIN Clutch Series #13 | 2026-10-26T15:00:00Z | **Metizport** | 61.5% / 38.5% | [Thunderpick](https://thunderpick.io/api/matches) · bookmaker | ambiguous: BRUTE | [bo3](https://www.hltv.org/matches/2399118/metizport-vs-brute-nodwin-clutch-series-13) | pass |
| 8 | [Nuclear TigeRES vs UNiTY](https://play.hotspawn.com/cs2-pickems#fixture-1093218) | NODWIN Clutch Series #13 | 2026-10-26T18:00:00Z | **Nuclear TigeRES** | 58.3% / 41.7% | [Thunderpick + Bovada](https://thunderpick.io/esports/counter-strike) · consensus | both unique | [bo3](https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13) | pass |
| 9 | [FlyQuest vs Staqued](https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860) | DFRAG Invitational 2026 | 2026-10-27T03:00:00Z | **FlyQuest** | 92.5% / 7.5% | [Polymarket](https://polymarket.com/event/cs2-fly-staque-2026-10-26) · market | absent: Staqued | — | pass |
| 10 | [Rooster vs Abyssal](https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861) | DFRAG Invitational 2026 | 2026-10-27T03:00:00Z | **Abyssal** | 47.8% / 52.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model | both unique | — | pass |
| 11 | [B8 vs K27](https://www.hotspawn.com/matches/b8-vs-k27-tesla-cup-2026-1082897) | Tesla Cup 2026 | 2026-10-27T08:00:00Z | **B8** | 59.5% / 40.5% | [Polymarket](https://polymarket.com/event/cs2-b8-k271-2026-10-27) · market | both unique | — | pass |
| 12 | [Alliance vs FaZe](https://www.hotspawn.com/matches/alliance-vs-faze-tesla-cup-2026-1082898) | Tesla Cup 2026 | 2026-10-27T11:00:00Z | **FaZe** | 34.0% / 66.0% | [Polymarket](https://polymarket.com/event/cs2-all-faze-2026-10-27) · market | both unique | — | pass |
| 13 | [ex-RUSTEC vs Spirit Academy](https://play.hotspawn.com/cs2-pickems#fixture-1081162) | CCT Europe 2026 Series #12 | 2026-10-27T12:00:00Z | **ex-RUSTEC** | 61.7% / 38.3% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model | both unique | [bo3](https://www.hltv.org/matches/2399512/ex-rustec-vs-spirit-academy-cct-2026-europe-series-12) | pass |
| 14 | [BakS vs Saint Sinners](https://play.hotspawn.com/cs2-pickems#fixture-1081163) | CCT Europe 2026 Series #12 | 2026-10-27T15:00:00Z | **BakS** | 78.8% / 21.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model | both unique | [bo3](https://www.hltv.org/matches/2399513/baks-vs-saint-sinners-cct-2026-europe-series-12) | pass |
| 15 | [Luminosity vs HOTU](https://www.hotspawn.com/matches/luminosity-vs-hotu-tesla-cup-2026-1082900) | Tesla Cup 2026 | 2026-10-27T17:00:00Z | **Luminosity** | 52.5% / 47.5% | [Polymarket](https://polymarket.com/event/cs2-lg6-hotu-2026-10-27) · market | both unique | — | pass |
| 16 | [Inner Circle Academy vs Lavked](https://play.hotspawn.com/cs2-pickems#fixture-1081164) | CCT Europe 2026 Series #12 | 2026-10-27T18:00:00Z | **Inner Circle Academy** | 75.6% / 24.4% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model | both unique | [bo3](https://www.hltv.org/matches/2399514/inner-circle-academy-vs-lavked-cct-2026-europe-series-12) | pass |
| 17 | [Envy vs GamerLegion](https://www.hotspawn.com/matches/envy-vs-gamerlegion-tesla-cup-2026-1082901) | Tesla Cup 2026 | 2026-10-27T20:00:00Z | **GamerLegion** | 45.5% / 54.5% | [Polymarket](https://polymarket.com/event/cs2-envy-gl1-2026-10-27) · market | absent: Envy | — | pass |
| 18 | [HOTU vs The Huns](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) | Moscow Cyber Games 2026 | 2026-10-31T09:00:00Z | **HOTU** | 87.0% / 13.0% | [Polymarket](https://polymarket.com/event/cs2-hotu-the9-2026-10-31) · market | ambiguous: The Huns | — | pass |
| 19 | [5star vs 1WIN](https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793) | Moscow Cyber Games 2026 | 2026-10-31T13:00:00Z | **1WIN** | 17.8% / 82.2% | [Valve official standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) · model | both unique | — | pass |

The fixture link is the canonical Hotspawn match page where the build carries it and the official lobby anchor `#fixture-<id>` otherwise — no slug is guessed. `Valve rows` is the state of the official standings input **at the read time**; the build published afterwards is what `Pick`/`Basis` describe.

## 4. Replay of the 19 picks in the published build

| Fixture | Method | Source | Pick | Published | Recomputed | Delta |
| --- | --- | --- | --- | --- | --- | --- |
| 1082858 Ground Zero vs Off Chops | market | Polymarket | Off Chops (79.5%) | 20.50% / 79.50% | 20.50% / 79.50% | 0e+00 |
| 1082859 NEXVOID vs Alter Ego | bookmaker | Thunderpick | NEXVOID (59.2%) | 59.16% / 40.84% | 59.16% / 40.84% | 3e-09 |
| 1079201 INOX Division vs Nemesis | model | Valve official standings | Nemesis (87.7%) | 12.35% / 87.65% | 12.35% / 87.65% | 3e-09 |
| 1079202 FOKUS vs ex-Zero Tenacity | bookmaker | Thunderpick | FOKUS (68.2%) | 68.24% / 31.76% | 68.24% / 31.76% | 1e-09 |
| 1081159 LFO 10 vs ex-6666 | model | Own results-based model (bo3.gg series results) | ex-6666 (61.0%) | 39.04% / 60.96% | 39.04% / 60.96% | 0e+00 |
| 1079203 Metizport vs BRUTE | bookmaker | Thunderpick | Metizport (61.5%) | 61.54% / 38.46% | 61.54% / 38.46% | 5e-09 |
| 1081160 HAVU vs ILLYRIANS | model | Valve official standings | HAVU (60.3%) | 60.35% / 39.65% | 60.35% / 39.65% | 5e-10 |
| 1093218 Nuclear TigeRES vs UNiTY | consensus | Thunderpick + Bovada | Nuclear TigeRES (58.3%) | 58.28% / 41.72% | 58.28% / 41.72% | 8e-09 |
| 1082860 FlyQuest vs Staqued | market | Polymarket | FlyQuest (92.5%) | 92.50% / 7.50% | 92.50% / 7.50% | 0e+00 |
| 1082861 Rooster vs Abyssal | model | Valve official standings | Abyssal (52.2%) | 47.76% / 52.24% | 47.76% / 52.24% | 3e-09 |
| 1082897 B8 vs K27 | market | Polymarket | B8 (59.5%) | 59.50% / 40.50% | 59.50% / 40.50% | 0e+00 |
| 1082898 Alliance vs FaZe | market | Polymarket | FaZe (66.0%) | 34.00% / 66.00% | 34.00% / 66.00% | 0e+00 |
| 1081162 ex-RUSTEC vs Spirit Academy | model | Valve official standings | ex-RUSTEC (61.7%) | 61.68% / 38.32% | 61.68% / 38.32% | 4e-09 |
| 1081163 BakS vs Saint Sinners | model | Valve official standings | BakS (78.8%) | 78.76% / 21.24% | 78.76% / 21.24% | 3e-09 |
| 1082900 Luminosity vs HOTU | market | Polymarket | Luminosity (52.5%) | 52.50% / 47.50% | 52.50% / 47.50% | 0e+00 |
| 1081164 Inner Circle Academy vs Lavked | model | Valve official standings | Inner Circle Academy (75.6%) | 75.61% / 24.39% | 75.61% / 24.39% | 3e-09 |
| 1082901 Envy vs GamerLegion | market | Polymarket | GamerLegion (54.5%) | 45.50% / 54.50% | 45.50% / 54.50% | 0e+00 |
| 1082792 HOTU vs The Huns | market | Polymarket | HOTU (87.0%) | 87.00% / 13.00% | 87.00% / 13.00% | 0e+00 |
| 1082793 5star vs 1WIN | model | Valve official standings | 1WIN (82.2%) | 17.82% / 82.18% | 17.82% / 82.18% | 3e-09 |

The rules are the publisher's own, re-implemented here and never copied from the row: normalised order-book midpoints; proportional margin removal on a bookmaker's raw decimal odds; the median of each source's no-vig probability for a consensus; Valve's `fit.js` logistic for an official-rating row; and the same logistic with `rd = min(400, 150 + 300/sqrt(n))` for the project's own results-based fit. Published values are rounded to 8 decimals, so a delta below 1e-6 counts as exact.

## 5. Replay of the ten picks that were live at the read time

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


## 6. Prediction vs outcome

The first build published after this read (2026-10-26T01:04:30Z, main 179f519a) carries all 19 open fixtures with a pick, and all 19 replay from their own evidence (published-verification.json). Seven of the nine new fixtures took exactly the predicted Valve-rating path. Two did not, and both resolved at a STRONGER evidence class than predicted: 1079203 Metizport vs BRUTE was priced by a verified Thunderpick two-way line (1.50/2.40 -> 61.5%/38.5%) instead of needing HLTV lineup disambiguation, and 1093218 Nuclear TigeRES vs UNiTY was priced by a two-book consensus (Thunderpick 1.58/2.20 + Bovada 1.606/2.25 -> 58.3%/41.7%) instead of the Valve model. 1081159 LFO 10 vs ex-6666 was priced by the project's own results-based fit over 10 anchored bo3.gg series (LFO 10 fitted 825 points, 90% interval 18.4%-64.5%, flagged low-confidence) rather than the HLTV ranking rung. No prediction was retro-fitted; both files are kept.

| Fixture | Path predicted at the read time | What the build actually used | Stronger or weaker evidence class |
| --- | --- | --- | --- |
| 1079201 | Valve official-rating model rung | Valve official standings (model) | as predicted |
| 1081159 | HLTV world-ranking rung | Own results-based model (bo3.gg series results) (model) | different, same class |
| 1079202 | Valve official-rating model rung | Thunderpick (bookmaker) | stronger |
| 1081160 | Valve official-rating model rung | Valve official standings (model) | as predicted |
| 1079203 | HLTV lineup-proof disambiguation, then HLTV world-ranking rung | Thunderpick (bookmaker) | different, same class |
| 1093218 | Valve official-rating model rung | Thunderpick + Bovada (consensus) | stronger |
| 1081162 | Valve official-rating model rung | Valve official standings (model) | as predicted |
| 1081163 | Valve official-rating model rung | Valve official standings (model) | as predicted |
| 1081164 | Valve official-rating model rung | Valve official standings (model) | as predicted |


## 7. Limitations

1. **This dossier does not price anything.** Every probability belongs to the publisher's own ladder; this session read sources, checked identities and replayed arithmetic.
2. **HLTV prices are not readable.** For `1081159` the odds page lists ranks and map records, but its bookmaker odds block is client-side and the fetched document carries no numeric price. That is a rendering limitation, not proof that no bookmaker prices the match, and no odds value is quoted from it.
3. **One published row is a research model on thin data.** `1081159` rests on 10 anchored bo3.gg series, is flagged low-confidence by the publisher, and carries a 90% interval of 18.4%–64.5% around LFO 10's 39.0%. It is published as a labelled model, not as a market price.
4. **The Valve input is a dated official snapshot.** `data/evidence/valve-ratings.json` carries the 2026-10-05 publication because the tracked file is the deterministic replay fixture; the publisher re-reads the current official file every run and refuses an input older than 35 days.
5. **Hotspawn leaves `best_of` null** on every CS2 record, so the format is verified on HLTV per fixture (all nine checked are best-of-3) and never inferred for the Hotspawn record.
6. **No community vote is an input.** Hotspawn's community vote percentages appear in the source payload and are deliberately not transcribed here; the verifier fails if one appears.

## 8. How to re-check it

```bash
python -m scripts.e3bc19d6_verify                    # replays every row, cross-checks the official files
python -m scripts.e3bc19d6_verify --published .      # every open fixture in a built tree has a pick or an explicit blocker
python -m unittest tests.test_e3bc19d6_verification  # 42 tests, including mutations that must fail
```

The verifier also compares the transcribed inventory with the collector's own `data/evidence/hotspawn-fixtures.json` whenever that file carries the same fixture id, so after a refresh a transcription error cannot survive; when the published evidence is a different vintage it reports `absent-from-vintage` instead of passing silently.

## 9. Review flags published by this session

- **warning** · `e3bc19d6-nine-fixtures-added-after-the-published-snapshot` — Nine open fixtures exist on Hotspawn that the published 23:03:48Z snapshot does not carry yet
- **warning** · `e3bc19d6-brute-ambiguous-valve-rows` — 1079203 Metizport vs BRUTE: two complete official Valve rows share the name BRUTE, so the Valve rung fails closed
- **warning** · `e3bc19d6-hltv-odds-block-has-no-readable-price` — HLTV's odds-and-prediction page for 1081159 carries ranks but no readable two-way price
- **info** · `e3bc19d6-hotu-the-huns-book-is-now-tight` — The HOTU vs The Huns exchange book is now 0.82/0.92 and 0.08/0.18, so the fixture is priced from a real line
- **info** · `e3bc19d6-valve-input-vintage` — The committed Valve rating input is dated 2026-10-05, 21 days old, because it is the replay fixture
- **info** · `e3bc19d6-hotspawn-best-of-is-null` — All 19 open fixtures carry a null Hotspawn best-of while HLTV lists best-of-3 for the nine checked
