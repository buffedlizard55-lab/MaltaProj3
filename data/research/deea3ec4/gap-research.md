# HLTV-first research for the nine uncovered live fixtures — 2026-10-26T00:59Z

Session `arena-deea3ec4`. Every fixture the deployed snapshot does not carry was taken through the brief's order of sources: [HLTV](https://www.hltv.org/matches?predefinedFilter=upcoming) first, then the betting market. Nothing in this file is a probability or a pick; it records what the primary sources published and what they did not.

| Hotspawn id | Fixture | Start (UTC) | What HLTV published | Two-sided price found |
| --- | --- | --- | --- | --- |
| 1079201 | INOX Division vs Nemesis | 2026-10-26 09:00:00 | HLTV world ranking #47 Nemesis, #84 INOX Division (read on the analytics page at 2026-10-26T00:47Z). Nemesis: 3 wins in the last 5; better form ranking. INOX Division: 4 wins in the last 5, but playing with stand-ins m1QUSE and gooddeph for k0s, and m1QUSE has fewer than five matches with the core. HLTV lists the sides in the reverse order of Hotspawn (Nemesis first). | No two-sided price is published in the HLTV document; its bookmaker odds block is client-rendered. Hotspawn's crowd share (Nemesis 80% / INOX 20%) is a popularity poll and is excluded. |
| 1081159 | LFO 10 vs ex-6666 | 2026-10-26 12:00:00 | HLTV world ranking #167 LFO 10, #72 ex-6666 (read at 2026-10-26T00:59Z). ex-6666 carries the better form ranking of the two. HLTV reports no further insight lines for either side. | Polymarket publishes this tournament: the public search API returns event 1244708 'Lavked vs mellren' for CCT Europe Series #12 Group Stage, so the family exists for the event. No event for LFO 10 vs ex-6666 was returned by the same search at the observation. |
| 1079202 | FOKUS vs ex-Zero Tenacity | 2026-10-26 12:00:00 | HLTV match page located and bound by exact names plus the same 12:00Z start; rankings were not transcribed in this observation. | Polymarket publishes NODWIN Clutch Series events (e.g. 1238705 'Metizport vs BakS' for the same playoff), so the family exists; no event for this exact fixture was confirmed in this observation. |
| 1081160 | HAVU vs ILLYRIANS | 2026-10-26 15:00:00 | Bound by exact names and start; HLTV spells the second side 'Illyrians'. | Not confirmed in this observation. |
| 1079203 | Metizport vs BRUTE | 2026-10-26 15:00:00 | Bound by exact names and start. | Polymarket priced the previous Metizport card in this playoff (event 1238705 vs BakS, now closed), so the family is active for the tournament; no event for this fixture was confirmed here. |
| 1093218 | Nuclear TigeRES vs UNiTY | 2026-10-26 18:00:00 | Bound by exact names and start. | Not confirmed in this observation. |
| 1081162 | ex-RUSTEC vs Spirit Academy | 2026-10-27 12:00:00 | Bound by exact names and start. | Not confirmed in this observation. |
| 1081163 | BakS vs Saint Sinners | 2026-10-27 15:00:00 | Bound by exact names and start; HLTV spells the first side 'BAKS'. | Not confirmed in this observation. |
| 1081164 | Inner Circle Academy vs Lavked | 2026-10-27 18:00:00 | Bound by exact names and start. | Polymarket priced Lavked's previous CCT Europe Series #12 round (event 1244708 vs mellren, now closed and resolved), so the family is active; no event for this fixture was confirmed here. |

## Why this cannot become a pick on its own

- Nine fixtures are listed above because the deployed snapshot predates them; the four-hour publisher is the only thing that can price them, and it replays its own first-party sources.
- HLTV's odds block is client-rendered, so HLTV supplies identity, ranking and form here, never a price.
- Polymarket 'family exists for the tournament' is evidence about availability, not a price for the fixture listed.
- Hotspawn crowd percentages are excluded from every line of this record.
- This sandbox cannot open a TCP connection to any esportsbook, so no first-party Thunderpick, Pinnacle, Smarkets or EGamersWorld response is quoted here; the collector retries them on every refresh.

## Sources

- <https://www.hltv.org/matches?predefinedFilter=upcoming>
- <https://www.hltv.org/betting/analytics/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13>
- <https://www.hltv.org/betting/analytics/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12>
- <https://gamma-api.polymarket.com/public-search?q=lavked>
- <https://gamma-api.polymarket.com/public-search?q=metizport>

## Resolution (checked 2026-10-26T02:12Z)

All nine fixtures this dossier researched are published with a pick and two probabilities by the
four-hour publisher's **2026-10-26T01:33:57Z (main 2bfff7f)** build. No number below was written by this session:

| Fixture | HLTV binding | Published method | A % | B % | Pick | Published source |
| --- | --- | --- | --- | --- | --- | --- |
| `1079201` | [nemesis-vs-inox-division-nodwin-clutch-series-13](https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13) | model | 12.3 | 87.7 | Nemesis | [github.com](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| `1081159` | [lfo-10-vs-ex-6666-cct-2026-europe-series-12](https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12) | model | 39.0 | 61.0 | ex-6666 | [bo3.gg](https://bo3.gg/matches/sokerorg-vs-ex-6666-26-10-2026) |
| `1079202` | [fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13](https://www.hltv.org/matches/2399117/fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13) | bookmaker | 68.2 | 31.8 | FOKUS | [thunderpick.io](https://thunderpick.io/api/matches) |
| `1081160` | [havu-vs-illyrians-cct-2026-europe-series-12](https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12) | model | 60.3 | 39.7 | HAVU | [github.com](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| `1079203` | [metizport-vs-brute-nodwin-clutch-series-13](https://www.hltv.org/matches/2399118/metizport-vs-brute-nodwin-clutch-series-13) | bookmaker | 61.5 | 38.5 | Metizport | [thunderpick.io](https://thunderpick.io/api/matches) |
| `1093218` | [nuclear-tigeres-vs-unity-nodwin-clutch-series-13](https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13) | consensus | 58.3 | 41.7 | Nuclear TigeRES | [thunderpick.io](https://thunderpick.io/esports/counter-strike) |
| `1081162` | [ex-rustec-vs-spirit-academy-cct-2026-europe-series-12](https://www.hltv.org/matches/2399512/ex-rustec-vs-spirit-academy-cct-2026-europe-series-12) | model | 61.7 | 38.3 | ex-RUSTEC | [github.com](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| `1081163` | [baks-vs-saint-sinners-cct-2026-europe-series-12](https://www.hltv.org/matches/2399513/baks-vs-saint-sinners-cct-2026-europe-series-12) | model | 78.8 | 21.2 | BakS | [github.com](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| `1081164` | [inner-circle-academy-vs-lavked-cct-2026-europe-series-12](https://www.hltv.org/matches/2399514/inner-circle-academy-vs-lavked-cct-2026-europe-series-12) | model | 75.6 | 24.4 | Inner Circle Academy | [github.com](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |

The dossier is HLTV-first research: rankings, the HLTV match binding and market availability. It states no probability of its own, and it does not feed the published numbers. The published estimate for each fixture comes from the repository ladder and is replayed row by row in data/research/deea3ec4/replay-2026-10-26T0133Z.json.

### Re-check against the 2026-10-26T02:51:32Z publish

The same replay was re-run on the next four-hour build (`main` after the 02:51:32Z collect):
**19 active rows, 0 violations**, every fixture still carrying a pick, and three rows now labelled as
superseded by a higher-ranked rung (the ladder moved `1082859`, `1079201` and `1093218` from a model
pair to a money/consensus pair). Those three are reported as warnings, not errors, because the row
publishes the superseding pair and it replays exactly.
