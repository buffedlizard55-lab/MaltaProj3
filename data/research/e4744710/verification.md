# E474-1 · Independent verification — 2026-10-24 (arena-e4744710)

Scope: the deployed GitHub Pages site (branch root, snapshot **2026-10-23T20:10:00Z**),
the live Hotspawn lobby, and the official sources behind each pick. Every statement below
was read first-hand in this session; each has a link. Nothing was inferred or filled in.

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| R01 | Deployed snapshot identity + local parity | pass | [live latest.json](https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json) = `2026-10-23T20:10:00Z`; branch-root stamp matches (commit `2f966a9`) |
| R02 | Pick for every active fixture | pass **19/19** (freshness caveat R07) | [summary](https://buffedlizard55-lab.github.io/MaltaProj3/), [complete list](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks) |
| R03 | Separate unresolved/limitations section, included in the summary | pass | summary register lists all 7 no-line picks with blockers; [full page](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/) |
| R04 | Summary links in-site to the updated picks | pass | `#picks-at-a-glance`, `./origination/#picks`, `./picks/`, `./unresolved/` on the deployed HTML |
| R05 | Phone readability (real browser, deployed HTML) | pass | 0 px overflow at 320/390 px on 6 pages; 48 px nav targets; `phone-deployed-root.json`; existing browser suite **104 passed**, new spec **2 passed** |
| R06 | Build audits + targeted suites | pass | replay PASS (80 rows); 767-row source audit (0 sourceless, 9 flagged unverified); acceptance 9/1/0; 829 links OK; **125 tests OK** |
| R07 | 4–8 h refresh cadence | **FAIL — flagged** | snapshot ~9.4 h old at observation; scheduled publisher failed 4 consecutive runs ([latest](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40063011446)) at the clock-bound regression test (owned by 3 claiming sessions; observed here, not edited) |
| R08 | Live lobby coverage vs site | **GAP — 9 cards — flagged** | [lobby](https://play.hotspawn.com/lobby) read 05:36–05:45Z: 25 cards, 16 covered, 9 CCT Europe Series #11/#12 cards absent from the 20:09:44Z inventory and from every prior dossier → new cards during the outage; details `lobby-coverage.json` |
| R09 | Polymarket row replay (1079193 FOKUS–ex-6666) | pass | published 76.5/23.5 from 76–77¢/23–24¢ book; live 05:47Z **79¢/22¢** — same pick, documented drift ([event](https://polymarket.com/event/cs2-fokus-66661-2026-10-24), BO3, 4:00 AM ET = 08:00Z ✓) |
| R10 | Valve model rows vs official standings | pass — **all 6 exact** | official file fetched first-hand via api.github.com; recomputed: Acend/UNiTY 54.2/45.8, Metizport/BakS 79.9/20.1, Color/ex-ZTA 73.6/26.4, Rooster/Abyssal 47.8/52.2, HOTU/Huns 94.1/5.9 (944-pt roster join), 5star/1WIN 17.8/82.2 — every pair matches the published decimal ([standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md)) |
| R11 | Bookmaker arithmetic (1082923, Thunderpick 1.22/3.80) | pass | 1/1.22 vs 1/3.80 normalized = 75.7/24.3 = published ([API](https://thunderpick.io/api/matches), [HLTV identity](https://www.hltv.org/matches/2399908/alka-vs-los-ninos-cct-2026-south-america-series-7)) |
| R12 | Duplicate HTML id | **FAIL — flagged**, claimed by arena-be019782 | `id="no-line-research"` renders twice on the deployed summary (the reproduced `2 != 1` test failure); only real duplicate across 4 main pages; files untouched here |
| R13 | Row-source policy | pass | deployed audit: 334 rows, **0 violations**, 0 flagged, 8 navigation; fixture audit: 0 sourceless, 9 flagged unverified (kept blank per policy) |

## The 19 deployed picks and their sources (enumerated from the deployed cards)

| id | match | pick | probs | method | official sources on the card |
| --- | --- | --- | --- | --- | --- |
| 1083025 | paiN vs Imperial | Imperial | 35.0 / 65.0 | market | [Hotspawn](https://www.hotspawn.com/matches/imperial-vs-pain-circuit-x-curitiba-4-1083025) · [Polymarket](https://polymarket.com/event/cs2-pain-imp11-2026-10-23) |
| 1082923 | Alka vs LOS NINOS | Alka | 75.7 / 24.3 | bookmaker | [Hotspawn](https://www.hotspawn.com/matches/alka-vs-los-ninos-cct-south-america-2026-series-7-1082923) · [Thunderpick](https://thunderpick.io/api/matches) · [HLTV](https://www.hltv.org/matches/2399908/alka-vs-los-ninos-cct-2026-south-america-series-7) |
| 1083045 | Chinggis Warriors vs Rare Atom | Chinggis Warriors | 59.0 / 41.0 | market | [Hotspawn](https://www.hotspawn.com/matches/chinggis-warriors-vs-rare-atom-void-autumn-cup-2026-1083045) · [Polymarket](https://polymarket.com/event/cs2-cw-ra1-2026-10-23) |
| 1079193 | FOKUS vs ex-6666 | FOKUS | 76.5 / 23.5 | market | [Hotspawn](https://www.hotspawn.com/matches/fokus-vs-ex-6666-nodwin-clutch-series-13-1079193) · [Polymarket](https://polymarket.com/event/cs2-fokus-66661-2026-10-24) |
| 1079195 | Nuclear TigeRES vs FORZE Reload | Nuclear TigeRES | 62.5 / 37.5 | market | [Hotspawn](https://www.hotspawn.com/matches/nuclear-tigeres-vs-forze-reload-nodwin-clutch-series-13-1079195) · [Polymarket](https://polymarket.com/event/cs2-ntr-forzer-2026-10-24) |
| 1082996 | Acend vs UNiTY | Acend | 54.2 / 45.8 | Valve model (no line) | [Hotspawn](https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996) · [Valve standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| 1079198 | Metizport vs BakS | Metizport | 79.9 / 20.1 | Valve model (no line) | [Hotspawn](https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198) · [Valve standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| 1079199 | Infinite vs BRUTE | BRUTE | 48.0 / 52.0 | market | [Hotspawn](https://www.hotspawn.com/matches/infinite-vs-brute-nodwin-clutch-series-13-1079199) · [Polymarket](https://polymarket.com/event/cs2-inf6-brute-2026-10-25) |
| 1079200 | Color vs ex-Zero Tenacity | Color | 73.6 / 26.4 | Valve model (no line) | [Hotspawn](https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200) · [Valve standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| 1082858 | Ground Zero vs Off Chops | Off Chops | 44.9 / 55.1 | network model (no line) | [Hotspawn](https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858) · [bo3.gg](https://bo3.gg/matches) |
| 1082859 | NEXVOID vs Alter Ego | NEXVOID | 57.6 / 42.4 | bookmaker | [Hotspawn](https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859) · [Thunderpick](https://thunderpick.io/api/matches) |
| 1082860 | FlyQuest vs Staqued | FlyQuest | 92.3 / 7.7 | bookmaker/market | [Hotspawn](https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860) · [Polymarket](https://polymarket.com/event/cs2-fly-staque-2026-10-26) · [Thunderpick](https://thunderpick.io/api/matches) |
| 1082861 | Rooster vs Abyssal | Abyssal | 47.8 / 52.2 | Valve model (no line) | [Hotspawn](https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861) · [Valve standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| 1082897 | B8 vs K27 | B8 | 62.0 / 38.0 | market | [Hotspawn](https://www.hotspawn.com/matches/b8-vs-k27-tesla-cup-2026-1082897) · [Polymarket](https://polymarket.com/event/cs2-b8-k271-2026-10-27) |
| 1082898 | Alliance vs FaZe | FaZe | 35.0 / 65.0 | market | [Hotspawn](https://www.hotspawn.com/matches/alliance-vs-faze-tesla-cup-2026-1082898) · [Polymarket](https://polymarket.com/event/cs2-all-faze-2026-10-27) |
| 1082900 | Luminosity vs HOTU | Luminosity | 52.5 / 47.5 | market | [Hotspawn](https://www.hotspawn.com/matches/luminosity-vs-hotu-tesla-cup-2026-1082900) · [Polymarket](https://polymarket.com/event/cs2-lg6-hotu-2026-10-27) |
| 1082901 | Envy vs GamerLegion | GamerLegion | 46.5 / 53.5 | market | [Hotspawn](https://www.hotspawn.com/matches/envy-vs-gamerlegion-tesla-cup-2026-1082901) · [Polymarket](https://polymarket.com/event/cs2-envy-gl1-2026-10-27) |
| 1082792 | HOTU vs The Huns | HOTU | 94.1 / 5.9 | Valve model (no line) | [Hotspawn](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) · [Valve standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |
| 1082793 | 5star vs 1WIN | 1WIN | 17.8 / 82.2 | Valve model (no line) | [Hotspawn](https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793) · [Valve standings](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md) |

Probabilities are printed as first/second team in percent, exactly as published on the deployed
cards. Model rows are labelled research estimates, never betting lines. The lobby's "% picked"
popularity values were read only as page text and never entered any probability.

## Irregularities flagged (published on /review/, non-blocking)

1. `e4744710-publisher-outage-four-failed-runs` — refresh cadence broken; snapshot beyond 8 h.
2. `e4744710-nine-new-lobby-cards-await-refresh` — the 9 uncovered lobby cards, with per-card links.
3. `e4744710-duplicate-no-line-research-id` — duplicate HTML id on the summary (claimed by be019782).
4. `e4744710-triple-claim-collision-test-file` — three sessions claim `tests/test_ca7e10e5_snapshot.py`.
