# Live probe — a pick for every Hotspawn CS2 match

Observed 2026-10-25T14:44:30Z (live).
Facts only: this file records what each source served. No probability, pick or alias is written here.

## Sources read

| Source | Status | HTTP | Bytes | SHA-256 |
| --- | --- | --- | --- | --- |
| published-latest-json | ok | 200 | 201016 | `16c4437804abd527…` |
| published-origination-json | ok | 200 | 88452 | `661ac8ff3a202e6f…` |
| hotspawn-fixtures-api | ok | 200 | 61043 | `2357ffb1c53d8e21…` |
| hotspawn-lobby | ok | 200 | 290987 | `518b52016f4c904c…` |
| hotspawn-cs2-pickems | ok | 200 | 299140 | `b048582101282413…` |
| hltv-matches | ok | 200 | 623691 | `aa739f0c41ee765c…` |
| hltv-ranking | ok | 200 | 1152922 | `c656b629f5a780e7…` |
| polymarket-cs2-tag | ok | 200 | 530553 | `4f7829ea825ef7fc…` |
| thunderpick-matches | ok | 200 | 144497 | `16da35309daa9b35…` |
| kalshi-cs2-events | ok | 200 | 147067 | `e62350d98768a002…` |
| pinnacle-esports | error | 204 | 0 | `e3b0c44298fc1c14…` |
| smarkets-cs2 | ok | 200 | 13996 | `cda90bf990829ff2…` |
| bo3gg-matches | ok | 200 | 13188 | `ed918ceec359c157…` |
| egamersworld-matches | error | 403 | 5672 | `5b19fe529b8274a2…` |
| ggbet-cs2 | error | 403 | 126 | `7583d10fb1a03d33…` |
| stake-cs2 | error | 403 | 5689 | `a07e7f5bcf0da39c…` |
| rivalry-cs2 | ok | 200 | 61219 | `c42c7a0b84a315c6…` |
| hltv-odds-2399114 | ok | 200 | 251869 | `1319023b3a1879e2…` |
| hltv-odds-2399917 | ok | 200 | 229502 | `99e917cd79fde6f9…` |
| hltv-odds-2399508 | ok | 200 | 246137 | `3a5c2404e86b695d…` |
| hltv-odds-2399819 | ok | 200 | 257487 | `d49c66d2449dd0c1…` |
| hltv-odds-2399115 | ok | 200 | 243049 | `50f330c1e233ec6a…` |
| hltv-odds-2399918 | ok | 200 | 250635 | `e20451d1e3696231…` |
| hltv-odds-2399888 | ok | 200 | 249804 | `7feaa8c00a1136a2…` |
| hltv-odds-2399889 | ok | 200 | 248842 | `453552a8674d011e…` |
| hltv-odds-2399890 | ok | 200 | 247458 | `2c5179701521040b…` |
| hltv-odds-2399891 | ok | 200 | 251644 | `54539cdf68189aef…` |
| hltv-odds-2399866 | ok | 200 | 250012 | `0e64b9207814e174…` |
| hltv-odds-2399867 | ok | 200 | 251661 | `1b12d514808c7ea3…` |
| hltv-odds-2399869 | ok | 200 | 250856 | `86962c17057f2f01…` |
| hltv-odds-2399870 | ok | 200 | 251750 | `13cd92f3bbb737ab…` |
| hltv-odds-2399437 | ok | 200 | 250507 | `e5b07aab2f796201…` |
| hltv-odds-2399438 | ok | 200 | 251788 | `76b3cfee46cddd3c…` |

## Coverage

| Fact | Value |
| --- | --- |
| fixture API records | 78 |
| open fixtures in the API | 16 |
| fixture ids in the rendered lobby | 16 |
| open in the API but not in the lobby | [] |
| in the lobby but not open in the API | [] |
| published snapshot generated | 2026-10-15T08:36:13Z |
| open fixtures with **no published row** | 16 |
| open fixtures with a **non-featured-line** pick | 0 |

## Esportsbook / betting-line surfaces

| Surface | Status | HTTP | Rows parsed |
| --- | --- | --- | --- |
| polymarket-cs2-tag | ok | 200 | 25 |
| thunderpick-matches | ok | 200 | 0 |
| kalshi-cs2-events | ok | 200 | 200 |
| pinnacle-esports | error | 204 | 0 |
| smarkets-cs2 | ok | 200 | 0 |
| bo3gg-matches | ok | 200 | 0 |
| egamersworld-matches | error | 403 | 0 |
| ggbet-cs2 | error | 403 | 0 |
| stake-cs2 | error | 403 | 0 |
| rivalry-cs2 | ok | 200 | 1 |

## Research targets (HLTV first, then the books)

### 1079199 — Infinite vs BRUTE

- start (Hotspawn API): 2026-10-25T15:00:00Z
- competition: NODWIN Clutch Series #13
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399114/infinite-vs-brute-nodwin-clutch-series-13 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399114/infinite-vs-brute-nodwin-clutch-series-13', 'observed_at': '2026-10-25T14:44:38Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Infinite': 'rank 78, 11 points', 'BRUTE': 'rank 109, 8 points'}
- books with an exact-name row: none

### 1086696 — BORRACHEIROS vs RED Canids Academy

- start (Hotspawn API): 2026-10-25T16:00:00Z
- competition: CCT South America 2026 Series #7
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399917/borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7 (start delta -3600s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399917/borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7', 'observed_at': '2026-10-25T14:44:39Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'BORRACHEIROS': 'rank 176, 4 points', 'RED Canids Academy': 'rank 170, 4 points'}
- books with an exact-name row: none

### 1081158 — FORZE Reload vs ex-RUSTEC

- start (Hotspawn API): 2026-10-25T18:00:00Z
- competition: CCT Europe 2026 Series #12
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12', 'observed_at': '2026-10-25T14:44:39Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'FORZE Reload': 'rank 80, 11 points', 'ex-RUSTEC': 'rank 70, 13 points'}
- books with an exact-name row: none

### 1082697 — BESTIA vs paiN

- start (Hotspawn API): 2026-10-25T18:00:00Z
- competition: Circuit X Curitiba #4
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399819/pain-vs-bestia-circuit-x-curitiba-season-4', 'observed_at': '2026-10-25T14:44:40Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'BESTIA': 'rank 76, 12 points', 'paiN': 'rank 32, 55 points'}
- books with an exact-name row: none

### 1079200 — Color vs ex-Zero Tenacity

- start (Hotspawn API): 2026-10-25T18:00:00Z
- competition: NODWIN Clutch Series #13
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13 (start delta 0s)
- HLTV one-name-only rows (review only): ex-Zero Tenacity vs Spirit Academy https://www.hltv.org/matches/2399340/ex-zero-tenacity-vs-spirit-academy-cct-2026-europe-series-11
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13', 'observed_at': '2026-10-25T14:44:41Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Color': None, 'ex-Zero Tenacity': 'rank 67, 13 points'}
- books with an exact-name row: none

### 1086697 — Projeto do KinGui vs Yawara

- start (Hotspawn API): 2026-10-25T19:00:00Z
- competition: CCT South America 2026 Series #7
- reason researched: no-published-row
- HLTV exact-name listing: not found
- HLTV one-name-only rows (review only): Tropa do KinGui vs Yawara https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7', 'observed_at': '2026-10-25T14:44:42Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Projeto do KinGui': None, 'Yawara': 'rank 157, 4 points'}
- books with an exact-name row: none

### 1082858 — Ground Zero vs Off Chops

- start (Hotspawn API): 2026-10-26T03:00:00Z
- competition: DFRAG Invitational 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026', 'observed_at': '2026-10-25T14:44:43Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Ground Zero': 'rank 143, 5 points', 'Off Chops': 'rank 142, 5 points'}
- books with an exact-name row: none

### 1082859 — NEXVOID vs Alter Ego

- start (Hotspawn API): 2026-10-26T03:00:00Z
- competition: DFRAG Invitational 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399889/nexvoid-vs-alter-ego-dfrag-invitational-2026', 'observed_at': '2026-10-25T14:44:44Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'NEXVOID': 'rank 77, 11 points', 'Alter Ego': 'rank 132, 6 points'}
- books with an exact-name row: none

### 1082860 — FlyQuest vs Staqued

- start (Hotspawn API): 2026-10-27T03:00:00Z
- competition: DFRAG Invitational 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399890/flyquest-vs-staqued-dfrag-invitational-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399890/flyquest-vs-staqued-dfrag-invitational-2026', 'observed_at': '2026-10-25T14:44:44Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'FlyQuest': 'rank 61, 16 points', 'Staqued': None}
- books with an exact-name row: none

### 1082861 — Rooster vs Abyssal

- start (Hotspawn API): 2026-10-27T03:00:00Z
- competition: DFRAG Invitational 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399891/rooster-vs-abyssal-dfrag-invitational-2026', 'observed_at': '2026-10-25T14:44:45Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Rooster': 'rank 181, 3 points', 'Abyssal': 'rank 128, 6 points'}
- books with an exact-name row: none

### 1082897 — B8 vs K27

- start (Hotspawn API): 2026-10-27T08:00:00Z
- competition: Tesla Cup 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399866/b8-vs-k27-rlg-tesla-cup-2026 (start delta 0s)
- HLTV one-name-only rows (review only): HEROIC vs B8 https://www.hltv.org/matches/2399856/heroic-vs-b8-iem-beijing-2026
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399866/b8-vs-k27-rlg-tesla-cup-2026', 'observed_at': '2026-10-25T14:44:46Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'B8': 'rank 21, 98 points', 'K27': 'rank 46, 32 points'}
- books with an exact-name row: none

### 1082898 — Alliance vs FaZe

- start (Hotspawn API): 2026-10-27T11:00:00Z
- competition: Tesla Cup 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399867/alliance-vs-faze-rlg-tesla-cup-2026 (start delta 0s)
- HLTV one-name-only rows (review only): FURIA vs FaZe https://www.hltv.org/matches/2399857/furia-vs-faze-iem-beijing-2026
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399867/alliance-vs-faze-rlg-tesla-cup-2026', 'observed_at': '2026-10-25T14:44:46Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Alliance': 'rank 29, 68 points', 'FaZe': 'rank 17, 127 points'}
- books with an exact-name row: none

### 1082900 — Luminosity vs HOTU

- start (Hotspawn API): 2026-10-27T17:00:00Z
- competition: Tesla Cup 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026 (start delta 0s)
- HLTV one-name-only rows (review only): HOTU vs The Huns https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026', 'observed_at': '2026-10-25T14:44:47Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Luminosity': 'rank 28, 76 points', 'HOTU': 'rank 38, 43 points'}
- books with an exact-name row: none

### 1082901 — Envy vs GamerLegion

- start (Hotspawn API): 2026-10-27T20:00:00Z
- competition: Tesla Cup 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399870/envy-vs-gamerlegion-rlg-tesla-cup-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399870/envy-vs-gamerlegion-rlg-tesla-cup-2026', 'observed_at': '2026-10-25T14:44:48Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Envy': 'rank 22, 94 points', 'GamerLegion': 'rank 23, 87 points'}
- books with an exact-name row: none

### 1082792 — HOTU vs The Huns

- start (Hotspawn API): 2026-10-31T09:00:00Z
- competition: Moscow Cyber Games 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026 (start delta 0s)
- HLTV one-name-only rows (review only): Luminosity vs HOTU https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026', 'observed_at': '2026-10-25T14:44:49Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'HOTU': 'rank 38, 43 points', 'The Huns': 'rank 134, 5 points'}
- books with an exact-name row: none

### 1082793 — 5star vs 1WIN

- start (Hotspawn API): 2026-10-31T13:00:00Z
- competition: Moscow Cyber Games 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026', 'observed_at': '2026-10-25T14:44:49Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'5star': 'rank 36, 50 points', '1WIN': 'rank 14, 158 points'}
- books with an exact-name row: none

