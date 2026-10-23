# arena-3a5448de — research for fixtures the featured method cannot resolve

Observed: 2026-10-23T05:41:16Z (GitHub Actions runner)
Snapshot: latest 2026-10-23T05:40:17Z · origination 2026-10-23T05:40:18Z · counts {'active': 17, 'resolved': 17, 'unresolved': 0, 'with_pick': 17, 'consensus': 0, 'market': 7, 'bookmaker': 1, 'reference': 0, 'model': 9, 'network': 0, 'relay': 0, 'guidance': 0, 'alias_joined': 4}
Targets (featured-blank or non-money resolution): 9

## Surfaces (HLTV first, then esportsbooks/aggregators)

- **HLTV match listing** — HTTP 403 — https://www.hltv.org/matches — teams listed: 9z
- **HLTV world ranking** — HTTP 403 — https://www.hltv.org/ranking/teams — teams listed: 9z
- **EGamersWorld CS2 matches** — HTTP 403 — https://egamersworld.com/counterstrike/matches — teams listed: —
- **DraftKings CS2** — HTTP 200 — https://sportsbook.draftkings.com/leagues/esports/counter-strike-2 — teams listed: 9z, EAC, ENCE, Falcons
- **Stake CS2** — HTTP 403 — https://stake.com/sports/esports/counter-strike-2 — teams listed: 9z
- **OddsPortal CS2** — HTTP 429 — https://www.oddsportal.com/esports/counter-strike/ — teams listed: —
- **Rivalry CS2** — HTTP 200 — https://www.rivalry.com/esports/counter-strike-2-betting — teams listed: 9z, ENCE
- **GG.BET CS** — HTTP 403 — https://gg.bet/en/counter-strike — teams listed: —
- **BetBoom CS2** — HTTP 401 — https://betboom.ru/sport/cs2 — teams listed: BetBoom
- **1xBet CS2** — HTTP 203 — https://1xbet.com/en/line/counter-strike-2 — teams listed: —
- **Marathonbet CS2** — HTTP 403 — https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/ — teams listed: —
- **Betway CS2** — HTTP 404 — https://www.betway.com/en/sports/esports/counter-strike-2 — teams listed: EAC, ENCE
- **Luckbox CS2** — HTTP None — https://luckbox.com/esports/csgo — teams listed: —
- **Oddspedia CS2** — HTTP 410 — https://www.oddspedia.com/esports/counter-strike-2 — teams listed: EAC, ENCE
- **bo3.gg matches** — HTTP 200 — https://bo3.gg/matches — teams listed: —
- **bo3.gg teams** — HTTP 200 — https://bo3.gg/teams — teams listed: —
- **Pinnacle guest leagues (sport 12)** — HTTP 200 — https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues — teams listed: EAC, ENCE

## Per-fixture

### 9z vs Falcons (Thunderpick World Championship 2026, 2026-10-15T11:00:00Z)
- Hotspawn: https://play.hotspawn.com/cs2-pickems#fixture-1080202
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.15709516, 0.84290484]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### WROTBERRY vs ENCE (Elisa BreakOut Series #2, 2026-10-15T12:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/wrotberry-vs-ence-elisa-breakout-series-2-1080281
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=0 probs=[0.72821824, 0.27178176]
- Unresolved stages: HLTV identity review, Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified.

### PARIVISION vs BetBoom (Thunderpick World Championship 2026, 2026-10-15T13:30:00Z)
- Hotspawn: https://play.hotspawn.com/cs2-pickems#fixture-1080203
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.26192226, 0.73807774]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### EAC vs BOJONG (Elisa BreakOut Series #2, 2026-10-15T14:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/eac-vs-bojong-elisa-breakout-series-2-1080282
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.96095469, 0.03904531]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### WROTBERRY vs BOJONG (Elisa BreakOut Series #2, 2026-10-15T16:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/wrotberry-vs-bojong-elisa-breakout-series-2-1080283
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=0 probs=[0.98421533, 0.01578467]
- Unresolved stages: HLTV identity review, Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified.

### EAC vs ENCE (Elisa BreakOut Series #2, 2026-10-15T18:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/eac-vs-ence-elisa-breakout-series-2-1080284
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.51399636, 0.48600364]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### HAVU vs RoundsGG (Elisa BreakOut Series #2, 2026-10-16T10:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/havu-vs-roundsgg-elisa-breakout-series-2-1080286
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=0 probs=[0.89829326, 0.10170674]
- Unresolved stages: HLTV identity review, Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified.

### mellren vs Privateer (CCT Europe 2026 Series #12 Play-In, 2026-10-16T14:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/mellren-vs-privateer-cct-europe-2026-series-12-play-in-1081120
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.85989312, 0.14010688]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### RoundsGG vs Voca (Elisa BreakOut Series #2, 2026-10-16T16:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/roundsgg-vs-voca-elisa-breakout-series-2-1080289
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=1 probs=[0.02791158, 0.97208842]
- Unresolved stages: HLTV identity review, Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified.

## Conclusions

{
  "with_directional_pick": 9,
  "resolved_no_pick_even": 0,
  "still_blank": 0,
  "bo3_relay_two_sided": 0
}
