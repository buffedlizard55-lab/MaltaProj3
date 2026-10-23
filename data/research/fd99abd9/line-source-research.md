# Line-source research for fixtures without a betting line — arena-fd99abd9

Observed 2026-10-23T05:00:19+00:00 (local checkout). Targets: 5 fixtures with no external line in snapshot 2026-10-15T09:31:24Z (checked-in snapshot).

HLTV first, then esportsbooks/aggregators. A reachable page is not a price.

| Fixture | Current basis | bo3.gg bound | Two-sided relay price | Pinnacle lists it | Verdict |
| --- | --- | --- | --- | --- | --- |
| 9z vs Falcons (Thunderpick World Championship 2026) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| PARIVISION vs BetBoom (Thunderpick World Championship 2026) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| EAC vs BOJONG (Elisa BreakOut Series #2) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| EAC vs ENCE (Elisa BreakOut Series #2) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |
| mellren vs Privateer (CCT Europe 2026 Series #12 Play-In) | Valve-rating research estimate | — | no | no | No two-sided price found on any probed surface; research-model pick remains, limitation stands |

## Surfaces probed

| Source | HTTP | Teams found | Challenge |
| --- | --- | --- | --- |
| HLTV match listing (https://www.hltv.org/matches) | SSLError: HTTPSConnectionPool(host='www.hltv.org', port=443): Max retries exceeded with url: /matches (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| HLTV world ranking (https://www.hltv.org/ranking/teams) | SSLError: HTTPSConnectionPool(host='www.hltv.org', port=443): Max retries exceeded with url: /ranking/teams (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| GG.BET CS2 (https://gg.bet/en/counter-strike) | SSLError: HTTPSConnectionPool(host='gg.bet', port=443): Max retries exceeded with url: /en/counter-strike (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| BetBoom CS2 (https://betboom.ru/sport/cs2) | SSLError: HTTPSConnectionPool(host='betboom.ru', port=443): Max retries exceeded with url: /sport/cs2 (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| Stake CS2 (https://stake.com/sports/esports/cs2) | SSLError: HTTPSConnectionPool(host='stake.com', port=443): Max retries exceeded with url: /sports/esports/cs2 (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| BC.Game CS2 (https://bc.game/sports/esports) | SSLError: HTTPSConnectionPool(host='bc.game', port=443): Max retries exceeded with url: /sports/esports (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| 1xBet CS2 (https://1xbet.com/en/line/counter-strike-2) | SSLError: HTTPSConnectionPool(host='1xbet.com', port=443): Max retries exceeded with url: /en/line/counter-strike-2 (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| Marathonbet CS2 (https://www.marathonbet.com/en/betting/Esports/Counter-Strike+2/) | SSLError: HTTPSConnectionPool(host='www.marathonbet.com', port=443): Max retries exceeded with url: /en/betting/Esports/Counter-Strike+2/ (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| Betway esports (https://www.betway.com/en/sports/esports/counter-strike-2) | SSLError: HTTPSConnectionPool(host='www.betway.com', port=443): Max retries exceeded with url: /en/sports/esports/counter-strike-2 (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| DraftKings CS2 (https://sportsbook.draftkings.com/leagues/esports/counter-strike-2) | SSLError: HTTPSConnectionPool(host='sportsbook.draftkings.com', port=443): Max retries exceeded with url: /leagues/esports/counter-strike-2 (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| OddsPortal CS2 (https://www.oddsportal.com/esports/counter-strike/) | SSLError: HTTPSConnectionPool(host='www.oddsportal.com', port=443): Max retries exceeded with url: /esports/counter-strike/ (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| EGamersWorld CS2 matches (https://egamersworld.com/counterstrike/matches) | SSLError: HTTPSConnectionPool(host='egamersworld.com', port=443): Max retries exceeded with url: /counterstrike/matches (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| Pinnacle CS2 page (https://www.pinnacle.com/en/esports/counter-strike-2) | SSLError: HTTPSConnectionPool(host='www.pinnacle.com', port=443): Max retries exceeded with url: /en/esports/counter-strike-2 (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| Rivalry CS2 (https://www.rivalry.com/betting/counter-strike) | SSLError: HTTPSConnectionPool(host='www.rivalry.com', port=443): Max retries exceeded with url: /betting/counter-strike (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| Thunderpick CS2 (https://thunderpick.io/esports/counter-strike) | SSLError: HTTPSConnectionPool(host='thunderpick.io', port=443): Max retries exceeded with url: /esports/counter-strike (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |
| Bovada CS2 (https://www.bovada.lv/sports/esports/counter-strike-2) | SSLError: HTTPSConnectionPool(host='www.bovada.lv', port=443): Max retries exceeded with url: /sports/esports/counter-strike-2 (Caused by SSLError(SSLZeroReturnError(6, 'TLS/SSL connection has been closed (EOF) (_ssl.c:992)'))) | — | — |

Pinnacle guest API: 0 esports matchups, 0 target-fixture hits, error: URLError: <urlopen error TLS/SSL connection has been closed (EOF) (_ssl.c:992)>

**New money-line leads: 0** of 5 target fixtures.

Featured-method unresolved (for audit): 4 fixture(s) — WROTBERRY vs ENCE (1080281), WROTBERRY vs BOJONG (1080283), HAVU vs RoundsGG (1080286), RoundsGG vs Voca (1080289).
