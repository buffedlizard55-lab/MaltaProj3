# arena-3a5448de — research for fixtures the featured method cannot resolve

Observed: 2026-10-23T09:51:55Z (GitHub Actions runner)
Snapshot: latest 2026-10-23T09:50:31Z · origination 2026-10-23T09:50:46Z · counts {'active': 30, 'resolved': 30, 'unresolved': 0, 'with_pick': 30, 'consensus': 2, 'market': 16, 'bookmaker': 4, 'reference': 0, 'model': 8, 'network': 1, 'relay': 1, 'guidance': 0, 'alias_joined': 2}
Targets (featured-blank or non-money resolution): 8

## Surfaces (HLTV first, then esportsbooks/aggregators)

- **HLTV match listing** — HTTP 403 — https://www.hltv.org/matches — teams listed: Color
- **HLTV world ranking** — HTTP 403 — https://www.hltv.org/ranking/teams — teams listed: Color
- **EGamersWorld CS2 matches** — HTTP 403 — https://egamersworld.com/counterstrike/matches — teams listed: —
- **DraftKings CS2** — HTTP 404 — https://sportsbook.draftkings.com/leagues/esports/counter-strike-2 — teams listed: Color
- **Stake CS2** — HTTP 403 — https://stake.com/sports/esports/counter-strike-2 — teams listed: Color
- **OddsPortal CS2** — HTTP 200 — https://www.oddsportal.com/esports/counter-strike/ — teams listed: Color, UNiTY
- **Rivalry CS2** — HTTP 200 — https://www.rivalry.com/esports/counter-strike-2-betting — teams listed: Color
- **GG.BET CS** — HTTP 403 — https://gg.bet/en/counter-strike — teams listed: —
- **BetBoom CS2** — HTTP 401 — https://betboom.ru/sport/cs2 — teams listed: —
- **1xBet CS2** — HTTP 203 — https://1xbet.com/en/line/counter-strike-2 — teams listed: —
- **Marathonbet CS2** — HTTP 403 — https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/ — teams listed: —
- **Betway CS2** — HTTP 404 — https://www.betway.com/en/sports/esports/counter-strike-2 — teams listed: Color
- **Luckbox CS2** — HTTP None — https://luckbox.com/esports/csgo — teams listed: —
- **Oddspedia CS2** — HTTP 410 — https://www.oddspedia.com/esports/counter-strike-2 — teams listed: Color, UNiTY
- **bo3.gg matches** — HTTP 200 — https://bo3.gg/matches — teams listed: Color
- **bo3.gg teams** — HTTP 200 — https://bo3.gg/teams — teams listed: Color
- **Pinnacle guest leagues (sport 12)** — HTTP 200 — https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues — teams listed: —

## Per-fixture

### Phantom Academy vs Banda chuya (CCT Europe 2026 Challengers #8, 2026-10-23T11:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/phantom-academy-vs-banda-chuya-cct-europe-2026-challengers-8-1081605
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.47482128, 0.52517872]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Acend vs UNiTY (NODWIN Clutch Series #13, 2026-10-25T09:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.54190155, 0.45809845]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Metizport vs BakS (NODWIN Clutch Series #13, 2026-10-25T12:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.79860558, 0.20139442]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Color vs ex-Zero Tenacity (NODWIN Clutch Series #13, 2026-10-25T18:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.7359068, 0.2640932]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Ground Zero vs Off Chops (DFRAG Invitational 2026, 2026-10-26T03:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858
- Featured method: None · current: model Own network estimate (bo3.gg results graph) pick_index=1 probs=[0.44851883439263457, 0.5514811656073655]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Exchange market (Smarkets CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld), Research model cross-check (Valve official ratings), Results model (own, bo3.gg series results)
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Own uncalibrated network model, not observed betting odds: no money line, no aggregated reference and no complete official rating row existed for this fixture. Both ratings come from a Bradley–Terry fit over 4681 finished bo3.gg series, anchored on Valve's official points for 268 teams; the rating-difference one-sigma interval is 156.9 points (probability interval 0.118-0.832). Current lineups, stand-ins and map vetoes are unverified. Low confidence: the interval crosses 50% or a side has fewer than ten finished series. Treat the direction as indicative only.

### Rooster vs Abyssal (DFRAG Invitational 2026, 2026-10-27T03:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.47761494, 0.52238506]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### HOTU vs The Huns (Moscow Cyber Games 2026, 2026-10-31T09:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=0 probs=[0.94052062, 0.05947938]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Exchange market (Smarkets CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified. | The Huns: the current HLTV lineup shares four of five players with the selected historical Valve row; the one-player change is not quantified.

### 5star vs 1WIN (Moscow Cyber Games 2026, 2026-10-31T13:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.17816902, 0.82183098]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

## Conclusions

{
  "with_directional_pick": 8,
  "resolved_no_pick_even": 0,
  "still_blank": 0,
  "bo3_relay_two_sided": 0
}
