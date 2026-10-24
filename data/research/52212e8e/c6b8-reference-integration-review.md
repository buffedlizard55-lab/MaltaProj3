# C6B8 reference-capture integration review

- Observed: `2026-10-24T07:14:33Z`
- Base: main `06618b31` (PR #265).
- Method: exact fixture ID + ordered teams + exact start + freshness + schema/no-vig replay using the unchanged production `reference_odds.quote` gate and C6B8's own 31-row inventory.
- **Result: 7 schema-valid entries, but only 3 exact-inventory gate accepts; 4 start-mismatch rejects. Only 1 of the 3 linked pages directly displays the captured price. No production price or capture path was changed.**

## Candidate entries vs actual inventory

| Fixture | Match | Captured odds | Inventory start | Capture start | Gate | Official-page evidence review | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `1083122` | LOS NINOS vs BORRACHEIROS | 2.92 / 1.33 | `2026-10-24T19:00:00Z` | `2026-10-24T19:00:00Z` | **ACCEPT** | direct-price-confirmed; linked page shows [2.92, 1.33] | [EGW](https://egamersworld.com/counterstrike/match/0U32SId-H/los-ninos-vs-borracheiros-qorsZa4d--) · [Hotspawn](https://www.hotspawn.com/matches/los-ninos-vs-borracheiros-cct-south-america-2026-series-7-1083122) · [HLTV](https://www.hltv.org/matches/2399914/los-ninos-vs-borracheiros-cct-2026-south-america-series-7) |
| `1082858` | Ground Zero vs Off Chops | 3.44 / 1.24 | `2026-10-26T03:00:00Z` | `2026-10-27T00:00:00Z` | **REJECT** | not used: exact start differs; direct-match-page | [EGW](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d) · [Hotspawn](https://www.hotspawn.com/matches/ground-zero-vs-off-chops-dfrag-invitational-2026-1082858) · [HLTV](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026) |
| `1082996` | Acend vs UNiTY | 2.42 / 1.5 | `2026-10-25T09:00:00Z` | `2026-10-25T08:00:00Z` | **REJECT** | not used: exact start differs; EGW-index-only-in-retained-excerpt | [EGW](https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf) · [Hotspawn](https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996) · [HLTV](https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13) |
| `1079198` | Metizport vs BakS | 1.34 / 2.85 | `2026-10-25T12:00:00Z` | `2026-10-25T11:00:00Z` | **REJECT** | not used: exact start differs; EGW-index-only-in-retained-excerpt | [EGW](https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/metizport-vs-baks-esports-qOJcZA7Wgq) · [Hotspawn](https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198) · [HLTV](https://www.hltv.org/matches/2399113/metizport-vs-baks-nodwin-clutch-series-13) |
| `1079200` | Color vs ex-Zero Tenacity | 1.44 / 2.5 | `2026-10-25T18:00:00Z` | `2026-10-25T15:00:00Z` | **REJECT** | not used: exact start differs; EGW-index-only-in-retained-excerpt | [EGW](https://egamersworld.com/counterstrike/match/HiXMAaC8L/color-vs-ex-zero-tenacity-rvwRf5V1F) · [Hotspawn](https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200) · [HLTV](https://www.hltv.org/matches/2399115/color-vs-ex-zero-tenacity-nodwin-clutch-series-13) |
| `1082861` | Rooster vs Abyssal | 2.1 / 1.66 | `2026-10-27T03:00:00Z` | `2026-10-27T03:00:00Z` | **ACCEPT** | linked-page-shows-placeholder; linked page shows [1.8, 1.8] | [EGW](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8) · [Hotspawn](https://www.hotspawn.com/matches/rooster-vs-abyssal-dfrag-invitational-2026-1082861) · [HLTV](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) |
| `1082792` | HOTU vs The Huns | 1.09 / 6.8 | `2026-10-31T09:00:00Z` | `2026-10-31T09:00:00Z` | **ACCEPT** | linked-page-shows-placeholder; linked page shows [1.8, 1.8] | [EGW](https://egamersworld.com/counterstrike/match/cN3l69-7b/hotu-vs-the-huns-esports-SfdtzDhiK) · [Hotspawn](https://www.hotspawn.com/matches/hotu-vs-the-huns-moscow-cyber-games-2026-1082792) · [HLTV](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) |

### Direct recheck of the three gate accepts

- **`1083122` — direct-price-confirmed:** linked page displays `[2.92, 1.33]`; title start `24.10.2026 at 19:00`; body start `24.10.26 15:00`. The linked official EGW match page directly displays 2.92/1.33 and the EGWxxxBOT bookmaker-average sentence. Its title/body clock labels differ; no timezone is inferred. HLTV match 2399914 independently reconciles the fixture and inventory start.
- **`1082861` — linked-page-shows-placeholder:** linked page displays `[1.8, 1.8]`; title start `27.10.2026 at 03:00`; body start `26.10.26 23:00`. The linked official EGW match page displays 1.8/1.8, not the captured 2.10/1.66. The quoted values are index-only in the retained excerpt and need an exact, reviewable index capture before production use.
- **`1082792` — linked-page-shows-placeholder:** linked page displays `[1.8, 1.8]`; title start `31.10.2026 at 09:00`; body start `31.10.26 05:00`. The linked official EGW match page displays 1.8/1.8, not the captured 1.09/6.80. The quoted values are index-only in the retained excerpt and need an exact, reviewable index capture before production use. The fetch redirected to the current EkalRNMvVx event URL; no redirect target is invented in the source record.

## Rejected equal-side placeholders

These six rows already have no production pricing effect. Five nevertheless contain team/start mismatches and must not be reused as fixture evidence.

| Fixture | Inventory match | Capture start | Inventory start | Identity differences | Sources |
| --- | --- | --- | --- | --- | --- |
| `1081152` | HAVU vs Azuolas | `2026-10-24T11:00:00Z` | `2026-10-24T11:00:00Z` | none | [EGW](https://egamersworld.com/counterstrike/match/HiXMAaC8L/havu-vs-azuolas-Dm2JAvY3OO) · [Hotspawn](https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152) · [HLTV](https://www.hltv.org/matches/2399502/havu-vs-azuolas-cct-2026-europe-series-12) |
| `1081153` | Saint Sinners vs 6yuBoJlbl | `2026-10-24T14:00:00Z` | `2026-10-24T14:00:00Z` | teams: capture=['Oxuji', 'ex-Zero Tenacity'] vs inventory=['Saint Sinners', '6yuBoJlbl'] | [EGW](https://egamersworld.com/counterstrike/match/HiXMAaC8L/oxuji-esports-vs-ex-zero-tenacity-T73a9g-yU) · [Hotspawn](https://www.hotspawn.com/matches/saint-sinners-vs-6yubojlbl-cct-europe-2026-series-12-1081153) · [HLTV](https://www.hltv.org/matches/2399503/6yubojlbl-vs-saint-sinners-cct-2026-europe-series-12) |
| `1081154` | BakS vs ILLYRIANS | `2026-10-24T17:00:00Z` | `2026-10-24T17:00:00Z` | teams: capture=['Nuclear TigeRES', 'BakS'] vs inventory=['BakS', 'ILLYRIANS'] | [EGW](https://egamersworld.com/counterstrike/match/HiXMAaC8L/nuclear-tigeres-vs-baks-esports-b9c6p-3aA) · [Hotspawn](https://www.hotspawn.com/matches/baks-vs-illyrians-cct-europe-2026-series-12-1081154) · [HLTV](https://www.hltv.org/matches/2399504/baks-vs-illyrians-cct-2026-europe-series-12) |
| `1081156` | Spirit Academy vs LFO 10 | `2026-10-25T11:00:00Z` | `2026-10-25T12:00:00Z` | start: capture=2026-10-25T11:00:00Z vs inventory=2026-10-25T12:00:00Z | [EGW](https://egamersworld.com/counterstrike/match/HiXMAaC8L/spirit-academy-vs-lfo-10-c1t2sP4xX) · [Hotspawn](https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156) · [HLTV](https://www.hltv.org/matches/2399506/spirit-academy-vs-lfo-10-cct-2026-europe-series-12) |
| `1081158` | FORZE Reload vs ex-RUSTEC | `2026-10-25T17:00:00Z` | `2026-10-25T18:00:00Z` | teams: capture=['WOPA', 'ex-6666'] vs inventory=['FORZE Reload', 'ex-RUSTEC']<br>start: capture=2026-10-25T17:00:00Z vs inventory=2026-10-25T18:00:00Z | [EGW](https://egamersworld.com/counterstrike/match/HiXMAaC8L/wopa-esport-vs-ex-6666-m8v4wR9zK) · [Hotspawn](https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158) · [HLTV](https://www.hltv.org/matches/2399508/forze-reload-vs-ex-rustec-cct-2026-europe-series-12) |
| `1082793` | 5star vs 1WIN | `2026-10-31T15:00:00Z` | `2026-10-31T13:00:00Z` | start: capture=2026-10-31T15:00:00Z vs inventory=2026-10-31T13:00:00Z | [EGW](https://egamersworld.com/counterstrike/match/cN3l69-7b/1win-vs-5star-B08F8lTce) · [Hotspawn](https://www.hotspawn.com/matches/5star-vs-1win-moscow-cyber-games-2026-1082793) · [HLTV](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) |

## Integration decision

- **1083122:** direct EGW page price 2.92/1.33 independently rechecked; retain as a candidate only. This audit does not deploy it.
- **1082861, 1082792:** exact-start gate accepts, but the linked pages show 1.8/1.8; obtain exact index evidence and a reviewable source association before any production use.
- **1082858, 1082996, 1079198, 1079200:** reject on start mismatch. Never “fix” these by copying Hotspawn's start into the provider capture.
- **1081152, 1081153, 1081154, 1081156, 1081158, 1082793:** equal-side placeholders remain rejected; five rows also have the identity differences tabulated above.
- C6B8's reference path is not registered in production `CAPTURE_PATHS`; the claimed seven priced entries therefore do not represent seven deployed or exactly joinable upgrades.

See `c6b8-reference-integration-review.json` for complete structured values, gate reasons, capture-path state, and limitations.
