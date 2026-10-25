# Live probe — a pick for every Hotspawn CS2 match

Observed 2026-10-25T16:10:27Z (live).
Facts only: this file records what each source served. No probability, pick or alias is written here.

## Sources read

| Source | Status | HTTP | Bytes | SHA-256 |
| --- | --- | --- | --- | --- |
| published-latest-json | ok | 200 | 201016 | `16c4437804abd527…` |
| published-snapshot-json | ok | 200 | 195845 | `26914d8df5c5a89b…` |
| published-origination-json | ok | 200 | 88452 | `661ac8ff3a202e6f…` |
| hotspawn-fixtures-api | ok | 200 | 58714 | `baf295bbbc60f3f1…` |
| hotspawn-lobby | ok | 200 | 273309 | `0a77a8ab096aa0a4…` |
| hotspawn-cs2-pickems | ok | 200 | 299140 | `b048582101282413…` |
| hltv-matches | ok | 200 | 603849 | `4980da5aa2ddaa98…` |
| hltv-ranking | ok | 200 | 1151449 | `97ee985a9fd3c7c2…` |
| polymarket-cs2-tag | ok | 200 | 530744 | `5ec3fd74eb14b68d…` |
| thunderpick-matches | ok | 200 | 136018 | `d002987ae7bd5382…` |
| kalshi-cs2-events | ok | 200 | 147067 | `e62350d98768a002…` |
| pinnacle-esports | error | 204 | 0 | `e3b0c44298fc1c14…` |
| smarkets-cs2 | ok | 200 | 14044 | `7bcb039cbae42874…` |
| bo3gg-matches | ok | 200 | 13188 | `ed918ceec359c157…` |
| egamersworld-matches | error | 403 | 5672 | `520a78da5d517399…` |
| ggbet-cs2 | error | 403 | 126 | `7583d10fb1a03d33…` |
| stake-cs2 | error | 403 | 5668 | `67852d7f309d67be…` |
| rivalry-cs2 | ok | 200 | 61219 | `712ad0f3cfa3baba…` |
| hltv-odds-2399918 | ok | 200 | 249036 | `be846f496ba7b3ae…` |
| hltv-odds-2399888 | ok | 200 | 248203 | `481a6e10fa90c33b…` |
| hltv-odds-2399891 | ok | 200 | 250039 | `1fcfe13269c0aeaf…` |
| hltv-odds-2399437 | ok | 200 | 248908 | `180fd1e726413fa0…` |
| hltv-odds-2399438 | ok | 200 | 250183 | `762b6e0da2de7766…` |

## Coverage

| Fact | Value |
| --- | --- |
| fixture API records | 75 |
| open fixtures in the API | 14 |
| fixture ids in the rendered lobby | 14 |
| open in the API but not in the lobby | [] |
| in the lobby but not open in the API | [] |
| published snapshot generated | 2026-10-25T14:32:11Z |
| open fixtures with **no published row** | 3 |
| open fixtures with a **non-featured-line** pick | 2 |

## Esportsbook / betting-line surfaces

| Surface | Status | HTTP | Rows parsed |
| --- | --- | --- | --- |
| polymarket-cs2-tag | ok | 200 | 25 |
| thunderpick-matches | ok | 200 | 42 |
| kalshi-cs2-events | ok | 200 | 0 |
| pinnacle-esports | error | 204 | 0 |
| smarkets-cs2 | ok | 200 | 20 |
| bo3gg-matches | ok | 200 | 0 |
| egamersworld-matches | error | 403 | 0 |
| ggbet-cs2 | error | 403 | 0 |
| stake-cs2 | error | 403 | 0 |
| rivalry-cs2 | ok | 200 | 1 |

## Research targets (HLTV first, then the books)

### 1086697 — Projeto do KinGui vs Yawara

- start (Hotspawn API): 2026-10-25T19:00:00Z
- competition: CCT South America 2026 Series #7
- reason researched: no-published-row
- HLTV exact-name listing: not found
- HLTV one-name-only rows (review only): Tropa do KinGui vs Yawara https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7', 'observed_at': '2026-10-25T16:10:34Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Projeto do KinGui': None, 'Yawara': 'rank 157, 4 points'}
- books with an exact-name row: none

### 1082858 — Ground Zero vs Off Chops

- start (Hotspawn API): 2026-10-26T03:00:00Z
- competition: DFRAG Invitational 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026', 'observed_at': '2026-10-25T16:10:35Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Ground Zero': 'rank 143, 5 points', 'Off Chops': 'rank 142, 5 points'}
- books with an exact-name row: ['smarkets-cs2']

### 1082861 — Rooster vs Abyssal

- start (Hotspawn API): 2026-10-27T03:00:00Z
- competition: DFRAG Invitational 2026
- reason researched: pick-not-a-featured-line (published method `model`)
- HLTV exact-name listing: https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399891/rooster-vs-abyssal-dfrag-invitational-2026', 'observed_at': '2026-10-25T16:10:36Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'Rooster': 'rank 181, 3 points', 'Abyssal': 'rank 128, 6 points'}
- books with an exact-name row: ['smarkets-cs2']

### 1082792 — HOTU vs The Huns

- start (Hotspawn API): 2026-10-31T09:00:00Z
- competition: Moscow Cyber Games 2026
- reason researched: no-published-row
- HLTV exact-name listing: https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026 (start delta 0s)
- HLTV one-name-only rows (review only): Luminosity vs HOTU https://www.hltv.org/matches/2399869/luminosity-vs-hotu-rlg-tesla-cup-2026
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026', 'observed_at': '2026-10-25T16:10:36Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'HOTU': 'rank 38, 43 points', 'The Huns': 'rank 134, 5 points'}
- books with an exact-name row: none

### 1082793 — 5star vs 1WIN

- start (Hotspawn API): 2026-10-31T13:00:00Z
- competition: Moscow Cyber Games 2026
- reason researched: pick-not-a-featured-line (published method `model`)
- HLTV exact-name listing: https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026 (start delta 0s)
- HLTV one-name-only rows (review only): none
- HLTV odds page: {'url': 'https://www.hltv.org/betting/analytics/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026', 'observed_at': '2026-10-25T16:10:37Z', 'http_status': 200, 'distinct_odds': ['1.23'], 'distinct_odds_count': 1, 'usable_two_way_price': False}
- HLTV ranking positions: {'5star': 'rank 36, 50 points', '1WIN': 'rank 14, 158 points'}
- books with an exact-name row: none

