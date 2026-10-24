# What HLTV and the esportsbooks actually published — dated direct read (2026-10-24)

Session `arena-8aa401c8`. Record: `data/research/8aa401c8/direct-observations.json`
(machine-readable, hash-checked excerpts). Read window **2026-10-24T05:36Z – 06:44Z**
through the agent's page fetcher, not a GitHub Actions runner.

This is the brief's fallback path in its stated order: **HLTV first**, then esportsbooks
and esports betting-line surfaces, for every active fixture the published snapshot can
only price with a research model. It writes no probability, no pick and no alias.

## Why these seven fixtures

Snapshot `2026-10-23T20:10:00Z`: 19 active Hotspawn CS2 fixtures. Twelve carry an
external betting line (9 market, 3 bookmaker). Seven carry a labelled research estimate
only, or no external line at all:

| Hotspawn | Fixture | Competition | Start (UTC) | Published method |
| --- | --- | --- | --- | --- |
| `1082996` | Acend vs UNiTY | NODWIN Clutch Series #13 | 2026-10-25T09:00Z | research model |
| `1079198` | Metizport vs BakS | NODWIN Clutch Series #13 | 2026-10-25T12:00Z | research model |
| `1079200` | Color vs ex-Zero Tenacity | NODWIN Clutch Series #13 | 2026-10-25T18:00Z | research model |
| `1082858` | Ground Zero vs Off Chops | DFRAG Invitational 2026 | 2026-10-26T03:00Z | research model |
| `1082861` | Rooster vs Abyssal | DFRAG Invitational 2026 | 2026-10-27T03:00Z | research model |
| `1082792` | HOTU vs The Huns | Moscow Cyber Games 2026 | 2026-10-31T09:00Z | research model |
| `1082793` | 5star vs 1WIN | Moscow Cyber Games 2026 | 2026-10-31T13:00Z | research model |

All seven are live lobby inventory with permalinks and lock times
([lobby](https://play.hotspawn.com/lobby), read 05:39Z), so none is a stale snapshot row.

## What each surface published

### 1. HLTV — read first

[Ground Zero vs Off Chops, HLTV 2399888](https://www.hltv.org/matches/2399888/ground-zero-vs-off-chops-dfrag-invitational-2026)
answered **HTTP 200** and confirmed the page title, the event, Ground Zero's five-player
lineup (apocdud, Omichella, vision, tucks, **sliimey** marked *Substitute*) and
**Off Chops [HLTV: #142] [VRS: #132]**, plus map-by-map lineup win rates.
It publishes **no winner market with a decimal price on both sides**, so it cannot price
the row. HLTV fan polls are crowd votes and are excluded by the project's rule 2.

The other six HLTV pages were already read for identity and Bo3 format by the pipeline's
own `HLTV research` stage (visible on each fixture card); this sweep re-read one of them
rather than restating the others as new evidence.

### 2. EGamersWorld publishes two different surfaces, and the difference is the finding

**(a) Event pages and the match listing — the 1.8 / 1.8 template.** Every one of the
seven shows the identical pair:

* **NODWIN Clutch Series 13** ([event page](https://egamersworld.com/counterstrike/event/nodwin-clutch-series-13-Nk9F-Ov54e), 05:42Z):
  Acend `1.8` — `1.8` UNITY Esports (25.10.26 05:00 Bo3);
  Metizport `1.8` — `1.8` BakS eSports (08:00);
  Color `1.8` — `1.8` ex-Zero Tenacity (14:00).
* **DFRAG Invitational 2026** ([event page](https://egamersworld.com/counterstrike/event/dfrag-invitational-2026-4kaAQWgKEx), 05:44Z):
  Ground Zero `1.8` — `1.8` Off Chops (25.10.26 23:00 Bo3);
  Rooster `1.8` — `1.8` Team Abyssal (26.10.26 23:00 Bo3).
* **GLuck Moscow Cyber Games 2026** ([event page](https://egamersworld.com/counterstrike/event/gluck-moscow-cyber-games-2026-EkalRNMvVx), 05:46Z):
  HOTU `1.8` — `1.8` The Huns Esports (31.10.26 05:00 Bo3);
  1WIN `1.8` — `1.8` 5star eSports (09:00).

**Why 1.8/1.8 is refused, in one line:** 1/1.8 + 1/1.8 = **1.111**, a 111 % book with zero
information about either team. The control sits in the same widget on the same pages:
fixtures it *does* price are asymmetric — Fokus `1.22` / `3.8` ex-6666, Nuclear TigeRES
`1.5` / `2.4` FORZE Reload, Infinite Gaming `1.78` / `1.92` Brute (NODWIN); NEXVOID `1.6` /
`2.17` Alter Ego, FlyQuest `1.001` / `12` Staqued (DFRAG). A scraper reading the first
decimal it found would have published a fabricated 50/50 for seven fixtures.

**(b) Match pages — one real aggregated average, and the proof that the template is not a
rendering artefact.**

* [Ground Zero vs Off Chops match page](https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d)
  (06:40Z) shows **Ground Zero 3.44 — 1.24 Off Chops**, with the page's own sentence:
  *"According to leading bookmakers predictions, the team Off Chops are the favorite with
  average odds 1.24 at the moment. Respectively, bookmakers consider Ground Zero to be the
  outsider of the match with odds on a victory in the sum of about 3.44."*
  That is an **aggregated average attributed to "leading bookmakers"**, not a named book,
  with no per-book price and no timestamp on the quote. It is the basis on which
  `arena-43110640` published a *guided* pick (Off Chops 73.5 % after de-vig, PR #240), and
  it is what the merged `scripts/egw_live.py` rung may replay on a later refresh. This
  record does not re-price it.
* [Acend vs UNITY Esports match page](https://egamersworld.com/counterstrike/match/Nk9F-Ov54e/acend-vs-unity-esports-iwaKSVfgf)
  (06:43Z) shows **1.8 — 1.8** again, and its *Betting tips* section carries **no
  bookmaker sentence** at all — only "ODDS STATS … View stats". So the uniform pair is a
  listing default, not a compact rendering of a real market.

One snippet correction stays on the record: a search-engine excerpt of the EGamersWorld
match *listing* showed `1.09 / 6.8` for HOTU vs The Huns. The live event page at 05:46Z
returns `1.8 / 1.8`; the snippet could not be reproduced and is **not used**.

### 3. Polymarket — listed, but the readable book is placeholder-wide

[`cs2-gz1-offcho-2026-10-25`](https://gamma-api.polymarket.com/markets?slug=cs2-gz1-offcho-2026-10-25)
(05:40Z) binds by exact names and start ("initially scheduled for October 25, 2026 at
11:00 PM ET" ⇒ 2026-10-26T03:00Z, Hotspawn `1082858`). Its series market shows
`outcomePrices [0.29, 0.71]` with `liquidity 6029.83`; those are last/mid prices, **not** a
two-sided quote. The Map 1 child market on the same event shows `bestBid 0.07` against
`bestAsk 0.93` — a **0.87 spread**, far outside the ladder's 12-cent ceiling, read at
`updatedAt 2026-10-24T05:34:37Z`.

The other six have no Polymarket event bound by exact name and start, which is precisely
the brief's "not covered on some betting sites like polymarket" case.

## Limitations of this research

1. **A relayed or averaged price is not a first-party price.** EGamersWorld exposes no
   market id, no per-book price and no timestamp on the Ground Zero quote, so the ladder
   cannot replay it from saved evidence on its own; the merged `egw_live.py` rung and the
   published guided-pick flag are where that reference is handled.
2. **Two surfaces of the same site can disagree.** The event page says 1.8/1.8 and the
   match page says 3.44/1.24 for the same fixture at the same hour. Reading only one of
   them would have produced either a fabricated 50/50 or an unverified "real" price.
3. **A 403 is not evidence that no market exists.** This path reaches HLTV (200) where the
   runner records 403; the runner reaches Thunderpick's POST API where this path cannot.
4. **Prices move.** Every number above is a timestamped observation, superseded by any
   later refresh.
5. **This record is inert.** `scripts/build.py::load_no_line_research` accepts only
   `github-actions-runner` records, so nothing here can enter the priced ladder. It is
   displayed as dated evidence on the executive summary and the unresolved register.
6. **Nothing was inferred.** Where a value could not be read it is absent rather than
   guessed: no probability, no pick, no alias, no rank.

## Relation to the other sweeps

* `arena-a7128fdd` (`data/research/a7128fdd/direct-observations.json`, 2026-10-23T11:05Z)
  read ten surfaces for the previous fixture set, including HLTV's betting-analytics
  template (a uniform `1.23`), bo3.gg and esports-news.co.uk. Not contradicted here.
* `arena-43110640` (`data/research/43110640/unresolved-guided-picks.json`, 2026-10-24T05:26Z)
  read the EGW match pages for the two previously unpicked fixtures and published the
  guided picks this record refers to. This sweep independently confirms its Ground Zero
  observation at a later time and adds the Acend-vs-UNITY control that separates a
  template from a price.

**Result: 7 fixtures re-checked, 0 first-party replayable quotes, 1 aggregated bookmaker
average (Ground Zero–Off Chops, already published as a guided pick), 1 new identity/format
confirmation, 0 probabilities changed, 0 picks changed, 0 aliases added.**
