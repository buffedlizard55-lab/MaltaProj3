# Live lobby vs deployed coverage — 542dfb58

Observed 2026-10-26T01:04:33Z on the GitHub Actions runner. Dated observation only: no probability, pick or alias is written here.

- Hotspawn fixture-API records: **81**; open CS2 fixtures: **19**; rendered-lobby crosscheck: **complete**
- Deployed snapshot `generated_at`: **2026-10-25T23:03:48Z**
- Active fixtures with a published pick: **9 of 19**
- Unpicked: **['1079201', '1081159', '1079202', '1081160', '1079203', '1093218', '1081162', '1081163', '1081164', '1082792']**
- Present in the live lobby but in neither deployed layer: **['1079201', '1081159', '1079202', '1081160', '1079203', '1093218', '1081162', '1081163', '1081164']**

| fixture | starts | pick on the site | method | priced by money? |
| --- | --- | --- | --- | --- |
| Ground Zero vs Off Chops | 2026-10-26T03:00:00Z | Off Chops | market | yes |
| NEXVOID vs Alter Ego | 2026-10-26T03:00:00Z | NEXVOID | bookmaker | yes |
| INOX Division vs Nemesis | 2026-10-26T09:00:00Z | — | none | no |
| LFO 10 vs ex-6666 | 2026-10-26T12:00:00Z | — | none | no |
| FOKUS vs ex-Zero Tenacity | 2026-10-26T12:00:00Z | — | none | no |
| HAVU vs ILLYRIANS | 2026-10-26T15:00:00Z | — | none | no |
| Metizport vs BRUTE | 2026-10-26T15:00:00Z | — | none | no |
| Nuclear TigeRES vs UNiTY | 2026-10-26T18:00:00Z | — | none | no |
| FlyQuest vs Staqued | 2026-10-27T03:00:00Z | FlyQuest | market | yes |
| Rooster vs Abyssal | 2026-10-27T03:00:00Z | Abyssal | model | no |
| B8 vs K27 | 2026-10-27T08:00:00Z | B8 | market | yes |
| Alliance vs FaZe | 2026-10-27T11:00:00Z | FaZe | market | yes |
| ex-RUSTEC vs Spirit Academy | 2026-10-27T12:00:00Z | — | none | no |
| BakS vs Saint Sinners | 2026-10-27T15:00:00Z | — | none | no |
| Luminosity vs HOTU | 2026-10-27T17:00:00Z | Luminosity | market | yes |
| Inner Circle Academy vs Lavked | 2026-10-27T18:00:00Z | — | none | no |
| Envy vs GamerLegion | 2026-10-27T20:00:00Z | GamerLegion | market | yes |
| HOTU vs The Huns | 2026-10-31T09:00:00Z | — | market | yes |
| 5star vs 1WIN | 2026-10-31T13:00:00Z | 1WIN | model | no |

Limitations:
- One observation. Hotspawn adds and retires cards continuously; the four-hour ladder re-reads the same API, so a card that appeared after this sweep is resolved on the next publish.
- A rendered-lobby page is a cross-check, not the inventory: when Hotspawn serves a cached lobby the fixture API stays authoritative and the crosscheck field says so.
- This record counts coverage. It never claims a probability is right, and it never fills a blank.
