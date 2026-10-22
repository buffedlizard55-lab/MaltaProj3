# arena-3a5448de — research for fixtures the featured method cannot resolve

Observed: 2026-10-22T08:06:21Z (GitHub Actions runner)
Snapshot: latest 2026-10-22T08:04:37Z · origination 2026-10-22T08:04:52Z · counts {'active': 43, 'resolved': 43, 'unresolved': 0, 'with_pick': 42, 'consensus': 3, 'market': 15, 'bookmaker': 6, 'reference': 0, 'model': 19, 'network': 2, 'relay': 1, 'guidance': 0, 'alias_joined': 5}
Targets (featured-blank or non-money resolution): 19

## Surfaces (HLTV first, then esportsbooks/aggregators)

- **HLTV match listing** — HTTP 403 — https://www.hltv.org/matches — teams listed: —
- **HLTV world ranking** — HTTP 403 — https://www.hltv.org/ranking/teams — teams listed: —
- **EGamersWorld CS2 matches** — HTTP 403 — https://egamersworld.com/counterstrike/matches — teams listed: —
- **DraftKings CS2** — HTTP 404 — https://sportsbook.draftkings.com/leagues/esports/counter-strike-2 — teams listed: —
- **Stake CS2** — HTTP 403 — https://stake.com/sports/esports/counter-strike-2 — teams listed: —
- **OddsPortal CS2** — HTTP 200 — https://www.oddsportal.com/esports/counter-strike/ — teams listed: —
- **Rivalry CS2** — HTTP 200 — https://www.rivalry.com/esports/counter-strike-2-betting — teams listed: —
- **GG.BET CS** — HTTP 403 — https://gg.bet/en/counter-strike — teams listed: —
- **BetBoom CS2** — HTTP 401 — https://betboom.ru/sport/cs2 — teams listed: —
- **1xBet CS2** — HTTP 203 — https://1xbet.com/en/line/counter-strike-2 — teams listed: —
- **Marathonbet CS2** — HTTP 403 — https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/ — teams listed: —
- **Betway CS2** — HTTP 404 — https://www.betway.com/en/sports/esports/counter-strike-2 — teams listed: —
- **Luckbox CS2** — HTTP None — https://luckbox.com/esports/csgo — teams listed: —
- **Oddspedia CS2** — HTTP 410 — https://www.oddspedia.com/esports/counter-strike-2 — teams listed: —
- **bo3.gg matches** — HTTP 200 — https://bo3.gg/matches — teams listed: —
- **bo3.gg teams** — HTTP 200 — https://bo3.gg/teams — teams listed: —
- **Pinnacle guest leagues (sport 12)** — HTTP 200 — https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues — teams listed: —

## Per-fixture

### Butterfly vs Lavked (CCT Europe 2026 Series #11, 2026-10-22T11:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/butterfly-vs-lavked-cct-europe-2026-series-11-1079651
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.77416873, 0.22583127]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Projeto do KinGui vs Martians (CCT South America 2026 Series #7, 2026-10-22T13:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/projeto-do-kingui-vs-martians-cct-south-america-2026-series-7-1082919
- Featured method: None · current: model Research model estimate (HLTV world ranking · unranked floor) pick_index=1 probs=[0.49856089, 0.50143911]
- Unresolved stages: HLTV identity review, Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld), Research model cross-check (Valve official ratings), Results model (own, bo3.gg series results), Own network model (bo3.gg results graph)
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated HLTV ranking transform; current lineups, stand-ins, form and map veto unverified. | Unranked floor: Projeto do KinGui has no HLTV world-ranking row, so the model gives that side HLTV's floor of 0.0 published points. That is a stated assumption, not a measured rating — the estimate is low confidence and only says the ranked side is the stronger side on the published ranking. No market, esportsbook or Valve rating input resolved this fixture.

### Donstu vs Banda chuya (CCT Europe 2026 Challengers #8, 2026-10-22T13:45:00Z)
- Hotspawn: https://www.hotspawn.com/matches/donstu-vs-banda-chuya-cct-europe-2026-challengers-8-1081600
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.4045841, 0.5954159]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Low Cortisol BR vs Grêmio (CCT South America 2026 Series #7, 2026-10-22T22:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/low-cortisol-br-vs-gremio-cct-south-america-2026-series-7-1082922
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.66195106, 0.33804894]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Lynn Vision vs Chinggis Warriors (VOID Autumn Cup 2026, 2026-10-23T03:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/lynn-vision-vs-chinggis-warriors-void-autumn-cup-2026-1081871
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=0 probs=[0.64419091, 0.35580909]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified. | Chinggis Warriors: the current HLTV lineup shares four of five players with the selected historical Valve row; the one-player change is not quantified.

### ex-Zero Tenacity vs ex-RUSTEC (CCT Europe 2026 Series #11, 2026-10-23T08:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/ex-zero-tenacity-vs-ex-rustec-cct-europe-2026-series-11-1079654
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.49888, 0.50112]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### Nuclear TigeRES vs ILLYRIANS (CCT Europe 2026 Series #11, 2026-10-23T11:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/nuclear-tigeres-vs-illyrians-cct-europe-2026-series-11-1079655
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.93003347, 0.06996653]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### FORZE Reload vs LFO 10 (CCT Europe 2026 Series #12, 2026-10-23T14:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/forze-reload-vs-lfo-10-cct-europe-2026-series-12-1081149
- Featured method: None · current: model Research model estimate (HLTV world ranking) pick_index=0 probs=[0.51007245, 0.48992755]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld), Research model cross-check (Valve official ratings), Results model (own, bo3.gg series results), Own network model (bo3.gg results graph)
- bo3.gg bound: 0 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated HLTV ranking transform; current lineups, stand-ins, form and map veto unverified.

### BORRACHEIROS vs QUINTESSÊNCIA (CCT South America 2026 Series #7, 2026-10-23T16:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/borracheiros-vs-quintessencia-cct-south-america-2026-series-7-1082924
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.47621793, 0.52378207]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### BakS vs BRUTE (CCT Europe 2026 Series #11, 2026-10-23T17:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/baks-vs-brute-cct-europe-2026-series-11-1079657
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=1 probs=[0.40054361, 0.59945639]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated; current lineups and map vetoes unverified.

### ex-RUSTEC vs Saint Sinners (CCT Europe 2026 Series #12, 2026-10-23T17:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/ex-rustec-vs-saint-sinners-cct-europe-2026-series-12-1081150
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.80746193, 0.19253807]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### BESTIA Academy vs RED Canids Academy (CCT South America 2026 Series #7, 2026-10-23T19:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/bestia-academy-vs-red-canids-academy-cct-south-america-2026-series-7-1082925
- Featured method: None · current: model Own network estimate (bo3.gg results graph) pick_index=1 probs=[0.2115926832824933, 0.7884073167175067]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld), Research model cross-check (Valve official ratings), Results model (own, bo3.gg series results)
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Own uncalibrated network model, not observed betting odds: no money line, no aggregated reference and no complete official rating row existed for this fixture. Both ratings come from a Bradley–Terry fit over 4647 finished bo3.gg series, anchored on Valve's official points for 269 teams; the rating-difference one-sigma interval is 130.0 points (probability interval 0.057-0.545). Current lineups, stand-ins and map vetoes are unverified. Low confidence: the interval crosses 50% or a side has fewer than ten finished series. Treat the direction as indicative only.

### Isurus vs Hacha (CCT South America 2026 Series #7, 2026-10-23T22:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/isurus-vs-hacha-cct-south-america-2026-series-7-1082926
- Featured method: None · current: model Research model estimate (HLTV world ranking) pick_index=None probs=[0.5, 0.5]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld), Research model cross-check (Valve official ratings), Results model (own, bo3.gg series results), Own network model (bo3.gg results graph)
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated HLTV ranking transform; current lineups, stand-ins, form and map veto unverified.

### Ground Zero vs Off Chops (DFRAG Invitational 2026, 2026-10-26T03:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858
- Featured method: None · current: model Own network estimate (bo3.gg results graph) pick_index=1 probs=[0.4439669300944456, 0.5560330699055545]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld), Research model cross-check (Valve official ratings), Results model (own, bo3.gg series results)
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Own uncalibrated network model, not observed betting odds: no money line, no aggregated reference and no complete official rating row existed for this fixture. Both ratings come from a Bradley–Terry fit over 4647 finished bo3.gg series, anchored on Valve's official points for 269 teams; the rating-difference one-sigma interval is 156.5 points (probability interval 0.116-0.829). Current lineups, stand-ins and map vetoes are unverified. Low confidence: the interval crosses 50% or a side has fewer than ten finished series. Treat the direction as indicative only.

### NEXVOID vs Alter Ego (DFRAG Invitational 2026, 2026-10-26T03:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/nexvoid-vs-alter-ego-dfrag-invitational-2026-1082859
- Featured method: model · current: model Valve-rating research estimate pick_index=0 probs=[0.72821824, 0.27178176]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### FlyQuest vs Staqued (DFRAG Invitational 2026, 2026-10-27T03:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/flyquest-vs-staqued-dfrag-invitational-2026-1082860
- Featured method: None · current: model Research model estimate (HLTV world ranking · unranked floor) pick_index=0 probs=[0.52300959, 0.47699041]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld), Research model cross-check (Valve official ratings), Results model (own, bo3.gg series results), Own network model (bo3.gg results graph)
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Research model, not observed betting odds. Uncalibrated HLTV ranking transform; current lineups, stand-ins, form and map veto unverified. | Unranked floor: Staqued has no HLTV world-ranking row, so the model gives that side HLTV's floor of 0.0 published points. That is a stated assumption, not a measured rating — the estimate is low confidence and only says the ranked side is the stronger side on the published ranking. No market, esportsbook or Valve rating input resolved this fixture.

### Rooster vs Abyssal (DFRAG Invitational 2026, 2026-10-27T03:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861
- Featured method: model · current: model Valve-rating research estimate pick_index=1 probs=[0.47761494, 0.52238506]
- Unresolved stages: Primary: Polymarket, Original esportsbook lines, GG.BET esportsbook, Pinnacle esportsbook, Rivalry esportsbook, Stake esportsbook
- bo3.gg bound: 1 · two-sided relay quote: False
- Limitations: Hotspawn best-of format is unverified; left blank.

### HOTU vs The Huns (Moscow Cyber Games 2026, 2026-10-31T09:00:00Z)
- Hotspawn: https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792
- Featured method: None · current: model Research model estimate (Valve official ratings) pick_index=0 probs=[0.94052062, 0.05947938]
- Unresolved stages: Betting market (Polymarket series winner), Exchange market (Kalshi CS2 match winner), Esportsbook line (Thunderpick original prices), Esportsbook line (Bovada original prices), Esportsbook line (Pinnacle original prices), Esportsbook line relayed by bo3.gg (bookmaker prices bo3.gg publishes), Aggregated bookmaker reference (EGamersWorld)
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
  "with_directional_pick": 18,
  "resolved_no_pick_even": 1,
  "still_blank": 0,
  "bo3_relay_two_sided": 0
}
