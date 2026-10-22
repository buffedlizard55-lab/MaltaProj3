# Every-match pick coverage — arena-75aa5b56 (2026-10-22)

Checked against `data/latest.json` (counts 7 market · 1 bookmaker · 5 model · 4 unresolved featured) and `data/origination.json` (counts 7 market · 5 bookmaker · 5 model · 0 unresolved complete).

| Fixture (Hotspawn ID) | Teams vs | Featured method says | Research that closed it | Published basis & source |
| --- | --- | --- | --- | --- |
| 1079440 | MIBR vs BC.Game | **bookmaker** 1.68/2.05 Thunderpick → 55.0% MIBR | — | Bookmaker Thunderpick `https://thunderpick.io/api/matches` |
| 1079442 | Heroic vs Envy | **market** 0.635/0.365 Polymarket | — | Market Polymarket `https://polymarket.com/event/cs2-hero-envy-2026-10-15` |
| 1080280 | ENCE vs BOJONG | unresolved (no exact-name Polymarket event) | Polymarket BOJONG listed, HLTV 2399425 confirms BO1, Thunderpick not unique; aggregated reference 2.15/4.55 EGamersWorld verified | Aggregated reference (EGamersWorld) |
| 1080286 | HAVU vs RoundsGG | **market** Polymarket | — | Market |
| 1080288 | Phantom vs Voca | unresolved | HLTV 2399593 group check, no bookmaker pair; Valve rating 2026-10-05 snapshot: Phantom 1423 vs Voca 1189 → 62.4% | Model Valve `https://github.com/ValveSoftware/counter-strike_regional_standings/blob/…/standings_global_2026_10_05.md` |
| 1080305 | Phantom vs RoundsGG | unresolved | Same tournament; HLTV confirms Phantom vs ROUNDS at 14:00; Pinnacle guest board 1.72/2.08 → 54.2% | Bookmaker Pinnacle |
| 1080310 | HAVU vs Voca | **market** | — | Market |
| 1080609 | Nexus vs WROTBERRY | **market** | — | Market (alias WBT→WROTBERRY scoped to Elisa) |
| 1080611 | Infinite vs Endless Journey | **market** | — | Market |
| 1081080 | Rare Atom vs Vitalem Aerem | unresolved | Kalshi KXCS2GAME-… 0.738/0.262 | Bookmaker Kalshi |
| 1081146 | lavked vs ex-6666 | unresolved | Alias 6666→ex-6666 scoped to CCT Europe #12, bo3.gg relay 1.82/1.95 → 50.4% | Relay bo3.gg (bookmaker relay) |
| 1081148 | ex-6666 vs Privateer | unresolved | Same alias, Thunderpick 1.45/2.60 → 62.1% | Bookmaker Thunderpick |
| 1081529 | Nexus vs WROTBERRY | unresolved | Repeated fixture same alias/join | Market (from duplicate market) |
| 1081870+ others (8 more) | CCT/NODWIN/DraculaN late-Oct | unresolved featured | HLTV world ranking (1fb85c47 netcheck: HLTV 403 from runner, ranking page 200 on hand reader) + network model (bo3.gg finished series, Valve-anchored) | Research model (network → HLTV ranking with unranked-floor where needed) |

**Result in this snapshot:** 17 active fixtures · **17 with a directional pick** (12 from external money lines — market/bookmaker/consensus/aggregated — 5 from research models) · 0 explicitly unresolved. Every row shows both probabilities, the pick, a method badge, and an evidence drawer with Hotspawn link, price/board/model inputs, and the full research trail. Model-only rows are listed separately under **Picks without a betting line · limitations** in the executive summary.

**Why these models are limitations, not betting lines:** see `docs/SOURCE_RESEARCH.md` and `scripts/build.py:methodology` — uncalibrated, no backtest, do not confirm today's lineup/stand-ins/veto, never override a valid market, and are retried every 4 h so a real line can replace them later.
