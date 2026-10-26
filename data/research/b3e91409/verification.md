# Independent verification — 2026-10-26T01:20:14Z

Rows checked: **19** · verified: **18** · blank (explained): **0** · errors: **20** · live coverage gaps: **0** · notes: **3**

## Inputs

- `data/research/b3e91409/published/origination.json` · generated 2026-10-26T01:04:30Z · sha256 `6c14cb1e7c9ac7fd…`
- `data/research/b3e91409/published/snapshot.json` · generated 2026-10-26T01:04:20Z · sha256 `6ec8e288ed36ab15…`

## Rows

| Fixture | Teams | Method | Probabilities | Pick | Replay | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1082858 | Ground Zero vs Off Chops | market | 20.5% / 79.5% | Off Chops | 0.0e+00 | verified |
| 1082859 | NEXVOID vs Alter Ego | bookmaker | 59.2% / 40.8% | NEXVOID | 3.4e-09 | verified |
| 1079201 | INOX Division vs Nemesis | model | 12.3% / 87.7% | Nemesis | 2.9e-09 | verified |
| 1079202 | FOKUS vs ex-Zero Tenacity | bookmaker | 68.2% / 31.8% | FOKUS | 1.2e-09 | verified |
| 1081159 | LFO 10 vs ex-6666 | model | 39.0% / 61.0% | ex-6666 | — | unreplayable |
| 1079203 | Metizport vs BRUTE | bookmaker | 61.5% / 38.5% | Metizport | 4.6e-09 | verified |
| 1081160 | HAVU vs ILLYRIANS | model | 60.3% / 39.7% | HAVU | 5.0e-10 | verified |
| 1093218 | Nuclear TigeRES vs UNiTY | consensus | 58.3% / 41.7% | Nuclear TigeRES | 5.0e-09 | verified |
| 1082860 | FlyQuest vs Staqued | market | 92.5% / 7.5% | FlyQuest | 0.0e+00 | verified |
| 1082861 | Rooster vs Abyssal | model | 47.8% / 52.2% | Abyssal | 2.8e-09 | verified |
| 1082897 | B8 vs K27 | market | 59.5% / 40.5% | B8 | 0.0e+00 | verified |
| 1082898 | Alliance vs FaZe | market | 34.0% / 66.0% | FaZe | 0.0e+00 | verified |
| 1081162 | ex-RUSTEC vs Spirit Academy | model | 61.7% / 38.3% | ex-RUSTEC | 4.5e-09 | verified |
| 1081163 | BakS vs Saint Sinners | model | 78.8% / 21.2% | BakS | 2.8e-09 | verified |
| 1082900 | Luminosity vs HOTU | market | 52.5% / 47.5% | Luminosity | 0.0e+00 | verified |
| 1081164 | Inner Circle Academy vs Lavked | model | 75.6% / 24.4% | Inner Circle Academy | 3.3e-09 | verified |
| 1082901 | Envy vs GamerLegion | market | 45.5% / 54.5% | GamerLegion | 0.0e+00 | verified |
| 1082792 | HOTU vs The Huns | market | 87.0% / 13.0% | HOTU | 0.0e+00 | verified |
| 1082793 | 5star vs 1WIN | model | 17.8% / 82.2% | 1WIN | 3.1e-09 | verified |

## Findings

- **note** `1081159` — the analysis publishes no limitation text
- **error** `1081159` — cannot replay the published numbers: a fitted results model does not publish the predictive formula that turns its posterior means [825.0, 923.0] into a probability; a standard 400-point Elo on the same points gives 0.362592
- **note** `1093218` — the analysis publishes no limitation text
- **note** `1082792` — the analysis publishes no limitation text
- **error** `1082858` — the executive summary has no in-site deep link to this published row
- **error** `1082859` — the executive summary has no in-site deep link to this published row
- **error** `1079201` — the executive summary has no in-site deep link to this published row
- **error** `1079202` — the executive summary has no in-site deep link to this published row
- **error** `1081159` — the executive summary has no in-site deep link to this published row
- **error** `1079203` — the executive summary has no in-site deep link to this published row
- **error** `1081160` — the executive summary has no in-site deep link to this published row
- **error** `1093218` — the executive summary has no in-site deep link to this published row
- **error** `1082860` — the executive summary has no in-site deep link to this published row
- **error** `1082861` — the executive summary has no in-site deep link to this published row
- **error** `1082897` — the executive summary has no in-site deep link to this published row
- **error** `1082898` — the executive summary has no in-site deep link to this published row
- **error** `1081162` — the executive summary has no in-site deep link to this published row
- **error** `1081163` — the executive summary has no in-site deep link to this published row
- **error** `1082900` — the executive summary has no in-site deep link to this published row
- **error** `1081164` — the executive summary has no in-site deep link to this published row
- **error** `1082901` — the executive summary has no in-site deep link to this published row
- **error** `1082792` — the executive summary has no in-site deep link to this published row
- **error** `1082793` — the executive summary has no in-site deep link to this published row

## Limits of this check

- Offline replay only: each number is re-derived from the inputs the row itself publishes. The live sources captured by scripts.b3e91409_probe are compared for coverage and identity, not re-priced after the fact.
- A verified row means "the published probabilities follow from the published inputs"; it does not mean the source price was profitable, liquid or still current.
