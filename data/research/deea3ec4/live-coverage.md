# Live Hotspawn CS2 inventory vs the deployed snapshot — 2026-10-26T00:44Z
Session `arena-deea3ec4`. Observer: Arena's page-fetch path reading [the Hotspawn lobby](https://play.hotspawn.com/lobby), the [scheduled-fixture API](https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1) and [HLTV's upcoming list](https://www.hltv.org/matches?predefinedFilter=upcoming) at **2026-10-26T00:44Z**.
Compared against the deployed snapshot `2026-10-25T23:03:48Z` ([snapshot.json](https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json)).
**19 open CS2 fixtures were listed on Hotspawn.** 10 were already in the deployed snapshot; 9 were not, because the build predates them. An HLTV match page was located for 17 of the 19.
| Hotspawn id | Fixture | Tournament | Start (UTC) | In 23:03Z snapshot | HLTV |
| --- | --- | --- | --- | --- | --- |
| 1082858 | Ground Zero vs Off Chops | DFRAG Invitational 2026 | 2026-10-26 03:00:00 | yes | [2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026) |
| 1082859 | NEXVOID vs Alter Ego | DFRAG Invitational 2026 | 2026-10-26 03:00:00 | yes | [2399889](https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026) |
| 1079201 | INOX Division vs Nemesis | NODWIN Clutch Series #13 | 2026-10-26 09:00:00 | **no** | [2399116](https://www.hltv.org/matches/2399116/nemesis-vs-inox-division-nodwin-clutch-series-13) |
| 1081159 | LFO 10 vs ex-6666 | CCT Europe 2026 Series #12 | 2026-10-26 12:00:00 | **no** | [2399509](https://www.hltv.org/matches/2399509/lfo-10-vs-ex-6666-cct-2026-europe-series-12) |
| 1079202 | FOKUS vs ex-Zero Tenacity | NODWIN Clutch Series #13 | 2026-10-26 12:00:00 | **no** | [2399117](https://www.hltv.org/matches/2399117/fokus-vs-ex-zero-tenacity-nodwin-clutch-series-13) |
| 1081160 | HAVU vs ILLYRIANS | CCT Europe 2026 Series #12 | 2026-10-26 15:00:00 | **no** | [2399510](https://www.hltv.org/matches/2399510/havu-vs-illyrians-cct-2026-europe-series-12) |
| 1079203 | Metizport vs BRUTE | NODWIN Clutch Series #13 | 2026-10-26 15:00:00 | **no** | [2399118](https://www.hltv.org/matches/2399118/metizport-vs-brute-nodwin-clutch-series-13) |
| 1093218 | Nuclear TigeRES vs UNiTY | NODWIN Clutch Series #13 | 2026-10-26 18:00:00 | **no** | [2399119](https://www.hltv.org/matches/2399119/nuclear-tigeres-vs-unity-nodwin-clutch-series-13) |
| 1082860 | FlyQuest vs Staqued | DFRAG Invitational 2026 | 2026-10-27 03:00:00 | yes | [2399890](https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026) |
| 1082861 | Rooster vs Abyssal | DFRAG Invitational 2026 | 2026-10-27 03:00:00 | yes | [2399891](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) |
| 1082897 | B8 vs K27 | Tesla Cup 2026 | 2026-10-27 08:00:00 | yes | [2399866](https://www.hltv.org/matches/2399866/b8-vs-k27-rlg-tesla-cup-2026) |
| 1082898 | Alliance vs FaZe | Tesla Cup 2026 | 2026-10-27 11:00:00 | yes | [2399867](https://www.hltv.org/matches/2399867/alliance-vs-faze-rlg-tesla-cup-2026) |
| 1081162 | ex-RUSTEC vs Spirit Academy | CCT Europe 2026 Series #12 | 2026-10-27 12:00:00 | **no** | [2399512](https://www.hltv.org/matches/2399512/ex-rustec-vs-spirit-academy-cct-2026-europe-series-12) |
| 1081163 | BakS vs Saint Sinners | CCT Europe 2026 Series #12 | 2026-10-27 15:00:00 | **no** | [2399513](https://www.hltv.org/matches/2399513/baks-vs-saint-sinners-cct-2026-europe-series-12) |
| 1082900 | Luminosity vs HOTU | Tesla Cup 2026 | 2026-10-27 17:00:00 | yes | [2399869](https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026) |
| 1081164 | Inner Circle Academy vs Lavked | CCT Europe 2026 Series #12 | 2026-10-27 18:00:00 | **no** | [2399514](https://www.hltv.org/matches/2399514/inner-circle-academy-vs-lavked-cct-2026-europe-series-12) |
| 1082901 | Envy vs GamerLegion | Tesla Cup 2026 | 2026-10-27 20:00:00 | yes | [2399870](https://www.hltv.org/matches/2399870/envy-vs-gamerlegion-rlg-tesla-cup-2026) |
| 1082792 | HOTU vs The Huns | Moscow Cyber Games 2026 | 2026-10-31 09:00:00 | yes | not located |
| 1082793 | 5star vs 1WIN | Moscow Cyber Games 2026 | 2026-10-31 13:00:00 | yes | not located |

## What this record does not do

- It does not compute, adjust or repeat a probability. Every number on the site comes from the publisher's priced snapshot, which replays its own sources.
- It does not turn Hotspawn's crowd share ("% picked"), offered points or leaderboard into a probability.
- It does not treat an HLTV ranking page as a betting line. HLTV's per-match odds widget is client-rendered, so no bookmaker price is quotable from the fetched HTML; the ranking, form and stand-in sections are usable as research inputs only.

## Identity notes worth a reviewer's attention

- **1079201 · INOX Division vs Nemesis** — HLTV lists the sides in the reverse order (Nemesis first).
- **1081160 · HAVU vs ILLYRIANS** — HLTV spells the second side 'Illyrians'.
- **1081163 · BakS vs Saint Sinners** — HLTV spells the first side 'BAKS'.

## Limitations

- This is one dated observation, not a live feed. A card scheduled later than 2026-10-26T00:44Z is not in this list.
- The nine cards absent from the 23:03:48Z snapshot are absent because the deployed build predates them; this record cannot prove the minute they were scheduled on Hotspawn, only that the deployed build does not carry them and the live API does.
- HLTV's per-match odds widget is rendered client-side; the fetched HTML exposes the ranking, form, stand-in, head-to-head and map-pool sections but no bookmaker decimal price. It is used for identity and research only, never as a probability.
- Two Moscow Cyber Games cards (1082792, 1082793) had no HLTV match page located in the fetched upcoming list at this observation; they are left without an HLTV link rather than guessed.
- Hotspawn crowd percentages, offered points and leaderboard positions are excluded from every probability in this project.
