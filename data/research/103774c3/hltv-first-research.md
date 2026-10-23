# HLTV-first line research for every fixture without a betting line — arena-103774c3

Observed **2026-10-23T09:44Z–09:53Z** (agent platform egress, which reaches `hltv.org`;
the GitHub Actions runner records HTTP 403 from HLTV). Companion runner sweep:
[`line-source-research.json`](line-source-research.json) (observed 2026-10-23T09:51:39Z).

**Scope:** every active Hotspawn CS2 fixture whose published pick rests only on a labelled
research model — **8 of 30** in the snapshot generated 2026-10-23T09:23:57Z (the runner's
fresh 09:50:52Z collection selected the same 8). All 8 already carry a pick and both win
probabilities on the site; this research asked whether a real external betting line exists
for any of them, HLTV first, then esportsbooks/exchanges. Nothing here writes a probability
or changes a pick; exchange numbers are copied verbatim.

| Match (Hotspawn) | Starts (UTC) | Current site pick (09:23Z snapshot) | HLTV first | Esportsbooks / exchanges | Result |
| --- | --- | --- | --- | --- | --- |
| Phantom Academy vs Banda chuya | 2026-10-23T11:00Z | Banda chuya 52.5% (Valve model) | [2399699](https://www.hltv.org/matches/2399699/phantom-academy-vs-banda-chuya-cct-2026-challengers-europe-series-8): identity + bo3 confirmed; Betting block = promo only, **no odds** | No Polymarket event; not on Smarkets; no bo3.gg binding; Pinnacle guest: no | No line anywhere; model estimate stands |
| Acend vs UNiTY | 2026-10-25T09:00Z | Acend 54.2% (Valve model) | [2399112](https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13): bo3 R16; Acend HLTV #131/VRS #75; **no odds** | Polymarket event exists (placeholder books); **Smarkets lists it ("UNiTY esports") but the book is empty** — zero bids/offers ([quotes](https://api.smarkets.com/v3/markets/172971947/quotes/)) | Listed, but no price exists yet |
| Metizport vs BakS | 2026-10-25T12:00Z | Metizport 79.9% (Valve model) | [2399113](https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13): bo3 R16; Metizport HLTV #59; **no odds** | Polymarket event exists (placeholder books); Smarkets lists a *different* BakS match, not joined | No usable line |
| Color vs ex-Zero Tenacity | 2026-10-25T18:00Z | Color 73.6% (Valve model) | [2399115](https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13): bo3 R16; Color HLTV Unranked/VRS #73; **no odds** | [Polymarket event 1238707](https://polymarket.com/event/cs2-color-zerote-2026-10-25) created today; books placeholder-wide (0.04/0.96 seen) | Book outside ceilings |
| Ground Zero vs Off Chops | 2026-10-26T03:00Z | Off Chops 55.5% (network model) | [2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026): bo3 LAN; Ground Zero HLTV #143/VRS #131; **no odds** | **Smarkets has a live two-sided book**: Ground Zero 0.1429/0.3279, Off Chops 0.6711/0.8547 ([copied quotes](https://api.smarkets.com/v3/markets/172960355/quotes/)) — spreads 0.185/0.184 vs the ladder's 0.15 ceiling; Polymarket series book 0.33 at 09:23Z | Real book exists, too wide to price yet |
| Rooster vs Abyssal | 2026-10-27T03:00Z | Abyssal 52.2% (Valve model) | [2399891](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026): bo3 LAN; Rooster HLTV Unranked/VRS #154; **no odds** | [Polymarket event 1237430](https://polymarket.com/event/cs2-rstr-abyssa-2026-10-26) exists; placeholder books; Smarkets list ends 26 Oct | No usable line yet |
| HOTU vs The Huns | 2026-10-31T09:00Z | HOTU 94.1% (Valve model) | [2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026): bo3 LAN semi; HOTU HLTV #38/VRS #36; **no odds** | Not listed on Polymarket/Smarkets/bo3.gg/Pinnacle eight days out | No line yet |
| 5star vs 1WIN | 2026-10-31T13:00Z | 1WIN 82.2% (Valve model) | [2399438](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026): bo3 LAN semi; 1WIN HLTV #14/VRS #18; **no odds** | Not listed anywhere checked | No line yet |

## What this proves, per fixture class

- **HLTV is an identity/ranking source, not a price source for these fixtures.** All 8 HLTV
  match pages render a "Betting" table whose only row is a Stake US sweepstake promotion
  ("No promocode available") — zero bookmaker decimal odds. HLTV's "Pick a winner" fan poll
  was seen on every page and excluded by policy (a crowd poll, like Hotspawn's community
  percentage; e.g. Rooster 100% / Abyssal 0%).
- **One live two-sided book exists** (Ground Zero–Off Chops, Smarkets) but at ~0.184 spread
  it exceeds the site ladder's published 0.15 ceiling, so the rung correctly leaves the
  model estimate in place. The runner bound the same event at 09:51Z independently.
- **Five fixtures are listed but priceless** (empty or placeholder books) and **three are
  listed nowhere** reachable. Blocked bookmaker pages (GG.BET 403, Bet365 403, EGamersWorld
  403, Oddspedia 410, Unibet 503 — runner sweep) are limitations, not proof of no market.
- **No pick changes today, by design.** The four-hour pipeline re-reads Polymarket, Kalshi,
  Smarkets, Thunderpick, Bovada, Pinnacle and the bo3.gg relay on every refresh and upgrades
  any of these 8 automatically the moment a compliant two-sided line exists.

Runner detail (HTTP status per surface, per-fixture bo3/Pinnacle/Polymarket bindings):
[`line-source-research.md`](line-source-research.md) · [`line-source-research.json`](line-source-research.json).
Full structured record of this page: [`hltv-first-research.json`](hltv-first-research.json).
