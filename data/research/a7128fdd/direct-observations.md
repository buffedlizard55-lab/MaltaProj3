# Direct HLTV / Polymarket / esportsbook observations for the model-only fixtures (arena-a7128fdd)

- Observed: **2026-10-23T10:05:00Z**
- Capture path: **authoring-fetch-path** — not a GitHub Actions runner.
- Brief line: Look for information sources to guide pick selections only for any matches that cannot be resolved in the same way as the featured picks. Try hltv, then try looking at esportsbooks and esports betting lines.
- Runner run for the live manifest: [39934809201](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39934809201)

## Why this record exists

Captured by direct page fetch from the authoring sandbox, NOT from a GitHub Actions runner. This distinction is the finding: ten earlier sessions recorded HLTV, EGamersWorld and the aggregators as 403/410 from the runner and concluded no external evidence existed for the model-only fixtures. On this path HLTV answers HTTP 200. The runner-only loader in scripts/build.py::load_no_line_research deliberately ignores this record, so nothing here can enter the priced ladder; it is published as evidence and as a correction to the reachability claim.

## Scope: the 8 fixtures the live ladder could only price with a research model

Live snapshot `2026-10-23T09:52:16Z`: **30 active · 22 money-backed · 8 model-only · 0 with no pick**.

| Hotspawn id | Teams | Competition | Starts (UTC) | Published method |
| --- | --- | --- | --- | --- |
| 1081605 | Phantom Academy vs Banda chuya | CCT Europe 2026 Challengers #8 | 2026-10-23T11:00:00Z | Valve-rating research estimate |
| 1082996 | Acend vs UNiTY | NODWIN Clutch Series #13 | 2026-10-25T09:00:00Z | Valve-rating research estimate |
| 1079198 | Metizport vs BakS | NODWIN Clutch Series #13 | 2026-10-25T12:00:00Z | Valve-rating research estimate |
| 1079200 | Color vs ex-Zero Tenacity | NODWIN Clutch Series #13 | 2026-10-25T18:00:00Z | Valve-rating research estimate |
| 1082858 | Ground Zero vs Off Chops | DFRAG Invitational 2026 | 2026-10-26T03:00:00Z | Own network estimate (bo3.gg results graph) |
| 1082861 | Rooster vs Abyssal | DFRAG Invitational 2026 | 2026-10-27T03:00:00Z | Valve-rating research estimate |
| 1082792 | HOTU vs The Huns | Moscow Cyber Games 2026 | 2026-10-31T09:00:00Z | Research model estimate (Valve official ratings) |
| 1082793 | 5star vs 1WIN | Moscow Cyber Games 2026 | 2026-10-31T13:00:00Z | Valve-rating research estimate |

## What each surface actually published

### a7128fdd-hltv-reachable-200

- **Surface:** HLTV match listing and match page
- **URL:** <https://www.hltv.org/matches/2399849/k27-vs-virtuspro-winline-mpkbk-cis-lan-season-9>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1083014
- **Names as published:** K27, Virtus.pro
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** reachable, identity and format confirmed, no price

Verbatim excerpt (SHA-256 `038a8c521d97e957ce20722999cd22854d39e976bf52a39d63951e41c2229462`):

> Best of 3 (LAN) · * Semi-final · K27 [HLTV: #46] [VRS: #33] · countdown '3h : 14m : 49s' read at 09:47Z, resolving the start to 13:00 UTC, which is Hotspawn 1083014's published 2026-10-23T13:00:00Z

**Why it is not a price.** HLTV answered HTTP 200 on this fetch path, not the 403 every earlier session recorded from a GitHub runner. The match page publishes format, both five-player lineups and both world/VRS ranks, which is official dated evidence. It publishes no two-sided prematch decimal price: the Betting block carried a Stake social-casino promotion only.

### a7128fdd-hltv-analytics-template-odds

- **Surface:** HLTV betting analytics page
- **URL:** <https://www.hltv.org/betting/analytics/2399849/k27-vs-virtuspro-winline-mpkbk-cis-lan-season-9>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1083014
- **Names as published:** K27, Virtus.pro
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** reachable, publishes no real price — every bookmaker cell renders the template value 1.23

Verbatim excerpt (SHA-256 `8be831a6a6cfb87cbbd46c798e6e856af65c01b53b6aee0343f0be1fec8e9ffd`):

> Handicap data, past 3 months | 2 - 0 wins | 34.1% | 1.23 eOddset | ... | 0 - 2 losses | 26.8% | 1.23 Betway | ... Virtus.pro is playing with stand-in: Patsi instead of F0R3VER · Patsi has played less than 5 matches with core · Virtus.pro is worse ranked (#56)

**Why it is not a price.** The page is titled 'odds & prediction' but the handicap table prints the identical value 1.23 against eOddset and Betway on every row for both teams, which is an unpopulated template, not a quote. A scraper that read the first decimal it found would publish a fabricated 1.23/1.23 price; the repository's identical-price placeholder rule rejects exactly this. The stand-in and ranking sentences are real official observations and are recorded as evidence.

### a7128fdd-hltv-fan-vote-excluded

- **Surface:** HLTV 'Pick a winner' fan vote
- **URL:** <https://www.hltv.org/matches/2399849/k27-vs-virtuspro-winline-mpkbk-cis-lan-season-9>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1083014
- **Names as published:** K27, Virtus.pro
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** excluded by rule 2 — a fan vote is not a price

Verbatim excerpt (SHA-256 `a77d47d839151ed3fbbfac219a0862d7502fe31506ad1b14ca32009d61629167`):

> Pick a winner · Please login to vote · K27 33.6% · Virtus.pro 66.4%

**Why it is not a price.** Recorded because it materially contradicts the money line for the same fixture (Hotspawn 1083014 is priced K27 0.565 / Virtus.pro 0.435 from an external market, and esports-news.co.uk's bookmaker prices K27 1.76 / Virtus.pro 2.05, a 0.538/0.462 de-vig). The community vote favours the side that both the market and HLTV's own ranking sentence disfavour, and HLTV notes Virtus.pro is fielding a stand-in. It changes nothing: rule 2 excludes fan votes and Hotspawn participation percentages alike. Published as a review item so the disagreement is visible rather than hidden.

### a7128fdd-polymarket-dfrag-zero-volume

- **Surface:** Polymarket CS2 event directory (DFRAG Invitational)
- **URL:** <https://polymarket.com/esports/cs2/dfrag-invitational>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1082858, 1082861
- **Names as published:** Ground Zero, Off Chops, Rooster, Abyssal, FlyQuest, Staqued
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** the fixtures ARE listed on Polymarket by exact name and start, but every market has zero traded volume, so there is no two-sided book to normalize

Verbatim excerpt (SHA-256 `83128c184a17967c002bfd40f7823b2a8b5e085444666449360c4f096292113d`):

> Ground Zero vs Off Chops · Oct 25, 11:00 PM · $0 vol · Ground Zero 3.70x 27% · Off Chops 1.35x 74% || Rooster vs Abyssal · Oct 26, 11:00 PM · $0 vol · Rooster 2.00x 50% · Abyssal 2.00x 50% || FlyQuest vs Staqued · $0 vol · 1.96x 51% / 2.04x 49%

**Why it is not a price.** This is the direct answer to the brief's 'not covered on some betting sites like polymarket'. Two of the three DFRAG events bind to Hotspawn fixtures by exact team names and by start time (Oct 25 11:00 PM ET = 2026-10-26T03:00:00Z = Hotspawn 1082858; Oct 26 11:00 PM ET = 2026-10-27T03:00:00Z = Hotspawn 1082861). Both are labelled $0 vol, so rule 3's positive bid/ask size and non-crossed-book tests cannot pass and no order book is fetched. Rooster vs Abyssal displays 2.00x/2.00x at 50%/50%, which is an unpriced listing default; adopting it would fabricate the exact 50/50 the repository forbids. Directory percentages are excluded inputs by rule 3, so Ground Zero 27% / Off Chops 74% is recorded as evidence of the listing and NOT adopted; it disagrees with our own results-network estimate (0.4492 / 0.5508) and is flagged for review rather than used.

### a7128fdd-egamersworld-placeholder-1p8

- **Surface:** EGamersWorld match pages (NODWIN Clutch Series 13)
- **URL:** <https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1082996, 1079198
- **Names as published:** Acend, UNITY Esports, Metizport, BakS eSports
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** reachable, but both pages display the identical 1.8/1.8 site placeholder — no bookmaker-average sentence, so nothing to replay

Verbatim excerpt (SHA-256 `71d0fddc7ccd9230ac04fafa2f6a30eb67111744282b55a5d4b46461bcf1f57d`):

> Acend 1.8 ... UNITY Esports 1.8 ... [1.8] [Make a bet] [1.8] || Metizport 1.8 ... BakS eSports 1.8 ... [1.8] [Make a bet] [1.8]

**Why it is not a price.** EGamersWorld answered HTTP 200 on this fetch path (earlier sessions recorded 403 from the runner). Both fixtures bind by exact names, tournament and Bo3 format, and both publish five-player lineups, which is usable identity evidence. Neither publishes a price: 1.8 on both sides is the site's unpopulated default and scripts/reference_odds.py already rejects identical prices as placeholders. A cached search snippet for the same fixtures showed 2.39/1.51 and 1.36/2.88 on 19 October, so EGamersWorld's odds do appear and disappear; only a same-session read is admissible, and this one had none.

### a7128fdd-egamersworld-rooster-abyssal

- **Surface:** EGamersWorld match page (DFRAG Invitational 2026)
- **URL:** <https://egamersworld.com/counterstrike/match/4kaAQWgKEx/rooster-vs-team-abyssal-P1tTp3RAg8>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1082861
- **Names as published:** Rooster, Team Abyssal
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** start time binds exactly to Hotspawn 1082861, price is the 1.8 placeholder, and two identity/location conflicts are recorded

Verbatim excerpt (SHA-256 `fb3bc9d3e4b01cc455935070fb03d10613e39fb26317dd225d22a6219329690f`):

> Rooster 1.8 · 26.10.26 23:00 Bo3 · JSON-LD {"startDate":"2026-10-27T03:00:00.000Z","location":{"name":"Sydney, Australia"},"competitor":[{"name":"Rooster"},{"name":"Team Abyssal"}]}

**Why it is not a price.** The page's own schema.org JSON-LD gives startDate 2026-10-27T03:00:00.000Z, which is Hotspawn 1082861's published start to the second — the strongest binding available for this fixture. It still prices nothing (1.8/1.8). Two conflicts are flagged, not resolved: EGamersWorld calls the away side 'Team Abyssal' where Hotspawn says 'Abyssal', which is an unregistered alias and is not auto-joined; and its location says Sydney while HLTV's DFRAG Invitational 2026 event page and Liquipedia both say Brisbane, Australia.

### a7128fdd-bo3gg-relay-board

- **Surface:** bo3.gg match centre (relay board)
- **URL:** <https://bo3.gg/matches/current>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1081148, 1082926, 1081606, 1082924, 1079657, 1082925, 1082923, 1082980, 1081605
- **Names as published:** Inner Circle Academy, Spirit Academy, Isurus, Hacha, Eternal Fire, JiJieHao, BORRACHEIROS, QUINTESSÊNCIA, BRUTE, BAKS, BESTIA Academy, RED Canids Academy, ALKA, Los Niños, WBT Academy, LPH, los kogutos, Phantom Academy
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** the relay board corroborates fixtures the ladder already priced and carries no quote for the model-only class

Verbatim excerpt (SHA-256 `81e2dbd09ca90dbd24220fae0ad0f49bd273ae2dd2cfb634c40ca83e3dddd0ee`):

> ALKA 1.30 / Los Niños 3.20 · WBT Academy 1.49 / LPH 2.45 · Inner Circle Academy 2.10 / Spirit Academy 1.65 · Isurus 1.13 / Hacha 5.00 · Eternal Fire 1.78 / JiJieHao 1.93 · BORRACHEIROS 1.52 / QUINTESSÊNCIA 2.35 · BESTIA Academy 2.70 / RED Canids Academy 1.40 · BRUTE 1.71 / BAKS 2.02 · los kogutos vs Phantom Academy 'All odds are on' (no numbers)

**Why it is not a price.** Two of the relay quotes reproduce published rows exactly after de-vigging, which independently confirms the ladder is reading this board correctly: ALKA 1.30/3.20 de-vigs to 0.711/0.289, the published bookmaker row for Hotspawn 1082923; WBT Academy 1.49/LPH 2.45 de-vigs to 0.622/0.378, the published row for 1082980. For the low-tier fixtures the board shows the label 'All odds are on' with no numbers at all, so there is no relay quote to replay for 1081605 today. Recorded as corroboration, never as a second pick.

### a7128fdd-esportsnews-bookmaker-table

- **Surface:** esports-news.co.uk CS2 match centre
- **URL:** <https://esports-news.co.uk/matches/cs2/>
- **HTTP:** 200 at 2026-10-23T10:05:00Z
- **Hotspawn fixtures:** 1079655, 1081148, 1081606, 1083014, 1081605
- **Names as published:** Nuclear TigeRES, ILLYRIANS, Inner Circle Academy, Spirit Academy, JiJieHao, Eternal Fire, K27, Virtus.pro, Phantom Academy, los kogutos
- **Two-sided price found:** **no**
- **Usable as a price:** **no**
- **Verdict:** a reachable aggregator that names five bookmakers per match, but it carries no price for the model-only fixtures, and its own power rating is not an input

Verbatim excerpt (SHA-256 `94b45e6828a6da5f911c9c6965ac739d39b155815f678ea6b11a39ea9fe72244`):

> Nuclear TigeRES 1.11 / ILLYRIANS 6.5 · Inner Circle Academy 2.17 / Spirit Academy 1.72 · JiJieHao 2.00 / Eternal Fire 1.83 · K27 1.76 / Virtus.pro 2.05 · Phantom Academy vs los kogutos 'CCT Europe Challengers Series season 8 2026 Today 12:00 · Bo3' with 43%/57% and no odds

**Why it is not a price.** This surface was not in any earlier session's ladder. It publishes decimal prices inline for fixtures the repository already prices from first-party sources (corroboration only) and a per-match 'Match odds (5 bookmakers)' table naming Bet365, 1xbet, Betway, Stake and GG.bet. For Hotspawn 1081605's slot it publishes no odds, only the site's own 43%/57% power rating, which is that site's model and is excluded exactly like Hotspawn participation percentages. Operational limitation verified: the finished match page /matches/cs2/6yubojlbl-vs-ex-6666-1746763/ renders no odds table at all, so the bookmaker table is prematch-only and must be captured before the start, or it is gone.

## Conclusions

- Fixtures in scope: **8**
- Fixtures that gained a new two-sided price: **0**
- Fixtures that gained new official identity/format evidence: **5**
- Probabilities changed: **0** · Picks changed: **0** · Aliases added: **0**
- HLTV HTTP status on this path: **200** · on the runner path: **403**

No two-sided prematch price exists for any of the 8 model-only fixtures on any surface read at 2026-10-23T09:47Z-10:05Z, so every published estimate stands unchanged and nothing was invented. What IS new: HLTV is reachable on this path and publishes the format, both lineups and both world/VRS ranks for the fixtures checked; Polymarket does list two of them by exact name and start but at $0 traded volume, which is the precise, source-linked reason the featured method cannot resolve them; and three surfaces publish placeholder prices (EGamersWorld 1.8/1.8, HLTV analytics 1.23, Polymarket 2.00x/2.00x) that a naive scraper would have turned into fabricated probabilities.

## Placeholder prices this sweep refused (each would have fabricated a probability)

| Surface | Placeholder | Fixture | What a naive read would have published |
| --- | --- | --- | --- |
| EGamersWorld | `1.8 / 1.8` identical both sides | 1082996 Acend vs UNiTY, 1079198 Metizport vs BakS, 1082861 Rooster vs Abyssal | a 50/50 default the repository forbids |
| HLTV betting analytics | `1.23` in every bookmaker cell (eOddset, Betway) | 1083014 K27 vs Virtus.pro | a 50/50 default from an unpopulated template |
| Polymarket directory | `2.00x / 2.00x`, `50% / 50%`, `$0 vol` | 1082861 Rooster vs Abyssal | a 50/50 default from an unpriced listing |
| HLTV `Pick a winner` | fan vote `33.6% / 66.4%` | 1083014 K27 vs Virtus.pro | a crowd preference contradicting the money line |
| esports-news.co.uk | own power rating `43% / 57%` | 1081605 slot (Phantom Academy) | a third-party model presented as a market |

Each is recorded as evidence with its URL, and none entered a probability, a pick or an alias.
