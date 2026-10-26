# Independent verification — 2026-10-26T00:56:24Z

Rows checked: **10** · verified: **10** · blank (explained): **0** · errors: **0** · live coverage gaps: **9** · notes: **1**

## Inputs

- `origination.json` · generated 2026-10-25T23:04:02Z · sha256 `30cc91ed42b5c58b…`
- `snapshot.json` · generated 2026-10-25T23:03:48Z · sha256 `1c8a8c9af0c5ca6e…`

## Rows

| Fixture | Teams | Method | Probabilities | Pick | Replay | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1082858 | Ground Zero vs Off Chops | market | 20.0% / 80.0% | Off Chops | 0.0e+00 | verified |
| 1082859 | NEXVOID vs Alter Ego | bookmaker | 57.5% / 42.5% | NEXVOID | 8.2e-10 | verified |
| 1082860 | FlyQuest vs Staqued | market | 92.5% / 7.5% | FlyQuest | 0.0e+00 | verified |
| 1082861 | Rooster vs Abyssal | model | 47.8% / 52.2% | Abyssal | 2.8e-09 | verified |
| 1082897 | B8 vs K27 | market | 59.5% / 40.5% | B8 | 0.0e+00 | verified |
| 1082898 | Alliance vs FaZe | market | 37.5% / 62.5% | FaZe | 0.0e+00 | verified |
| 1082900 | Luminosity vs HOTU | market | 52.5% / 47.5% | Luminosity | 0.0e+00 | verified |
| 1082901 | Envy vs GamerLegion | market | 45.5% / 54.5% | GamerLegion | 0.0e+00 | verified |
| 1082792 | HOTU vs The Huns | market | 87.0% / 13.0% | HOTU | 0.0e+00 | verified |
| 1082793 | 5star vs 1WIN | model | 17.8% / 82.2% | 1WIN | 3.1e-09 | verified |

## Findings

- **note** `1082792` — the analysis publishes no limitation text
- **coverage-gap** `1079201` — live open fixture INOX Division vs Nemesis (2026-10-26T09:00:00Z) has no published row
- **coverage-gap** `1079202` — live open fixture FOKUS vs ex-Zero Tenacity (2026-10-26T12:00:00Z) has no published row
- **coverage-gap** `1081159` — live open fixture LFO 10 vs ex-6666 (2026-10-26T12:00:00Z) has no published row
- **coverage-gap** `1079203` — live open fixture Metizport vs BRUTE (2026-10-26T15:00:00Z) has no published row
- **coverage-gap** `1081160` — live open fixture HAVU vs ILLYRIANS (2026-10-26T15:00:00Z) has no published row
- **coverage-gap** `1093218` — live open fixture Nuclear TigeRES vs UNiTY (2026-10-26T18:00:00Z) has no published row
- **coverage-gap** `1081162` — live open fixture ex-RUSTEC vs Spirit Academy (2026-10-27T12:00:00Z) has no published row
- **coverage-gap** `1081163` — live open fixture BakS vs Saint Sinners (2026-10-27T15:00:00Z) has no published row
- **coverage-gap** `1081164` — live open fixture Inner Circle Academy vs Lavked (2026-10-27T18:00:00Z) has no published row

## Live fixtures with no published row

| Fixture | Teams | Starts (UTC) | Competition | Hotspawn |
| --- | --- | --- | --- | --- |
| 1079201 | INOX Division vs Nemesis | 2026-10-26T09:00:00Z | NODWIN Clutch Series #13 | https://play.hotspawn.com/cs2-pickems#fixture-1079201 |
| 1079202 | FOKUS vs ex-Zero Tenacity | 2026-10-26T12:00:00Z | NODWIN Clutch Series #13 | https://play.hotspawn.com/cs2-pickems#fixture-1079202 |
| 1081159 | LFO 10 vs ex-6666 | 2026-10-26T12:00:00Z | CCT Europe 2026 Series #12 | https://play.hotspawn.com/cs2-pickems#fixture-1081159 |
| 1079203 | Metizport vs BRUTE | 2026-10-26T15:00:00Z | NODWIN Clutch Series #13 | https://play.hotspawn.com/cs2-pickems#fixture-1079203 |
| 1081160 | HAVU vs ILLYRIANS | 2026-10-26T15:00:00Z | CCT Europe 2026 Series #12 | https://play.hotspawn.com/cs2-pickems#fixture-1081160 |
| 1093218 | Nuclear TigeRES vs UNiTY | 2026-10-26T18:00:00Z | NODWIN Clutch Series #13 | https://play.hotspawn.com/cs2-pickems#fixture-1093218 |
| 1081162 | ex-RUSTEC vs Spirit Academy | 2026-10-27T12:00:00Z | CCT Europe 2026 Series #12 | https://play.hotspawn.com/cs2-pickems#fixture-1081162 |
| 1081163 | BakS vs Saint Sinners | 2026-10-27T15:00:00Z | CCT Europe 2026 Series #12 | https://play.hotspawn.com/cs2-pickems#fixture-1081163 |
| 1081164 | Inner Circle Academy vs Lavked | 2026-10-27T18:00:00Z | CCT Europe 2026 Series #12 | https://play.hotspawn.com/cs2-pickems#fixture-1081164 |

## Limits of this check

- Offline replay only: each number is re-derived from the inputs the row itself publishes. The live sources captured by scripts.b3e91409_probe are compared for coverage and identity, not re-priced after the fact.
- A verified row means "the published probabilities follow from the published inputs"; it does not mean the source price was profitable, liquid or still current.
