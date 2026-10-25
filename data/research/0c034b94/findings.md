# Session arena-0c034b94 — picks for every Hotspawn CS2 match, verified line by line

Observed **2026-10-25T13:45:44Z** from a GitHub Actions runner, because the authoring
sandbox cannot reach `play.hotspawn.com`, `hltv.org`, `egamersworld.com` or the exchange
APIs at all (every request fails before a status line). Raw responses are archived in [`raw/`](raw/) with their SHA-256 — HTML as
`.html.gz`, the repository's convention, because the publisher copies this tree into the
site and treats a bare `.html` there as one of its own pages — and every parse can be
re-run offline:

```
python -m scripts.0c034b94_probe --parse-raw     # rebuild the dossier from the archive
python -m scripts.0c034b94_verify --write        # replay the published snapshot
```

## 1. What the question actually is, measured

| Question | Answer at 13:45:44Z | Source |
| --- | --- | --- |
| Open CS2 fixtures on Hotspawn | **17** | official fixture API (78 records, 17 future starts) |
| Fixture ids in the rendered lobby | **17**, identical set | cache-busted `play.hotspawn.com/lobby?cb=1792935939` |
| Matches on the lobby with **no pick published** | **3** — `1086696`, `1082697`, `1086697` | published `data/origination.json` (generated 05:12:40Z) |
| Age of the published snapshot | **8 h 33 m** (bound is 8 h) | published `data/latest.json` generated 05:12:25Z |
| Rows in the published complete-picks feed | **18**, of which **0** lack a pick | published `data/origination.json` |

So the picks are not missing because a book refuses to price a low-tier match. They are
missing because the published feed predates the three fixtures, and the four-hour
publisher has been failing since the 08:17Z slot: runs
[40174233578](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40174233578)
and [40196457503](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40196457503)
both die at `test_group_a_are_snapshot_unresolved`, a dated expectation in
`tests/test_b72154e1_guided_picks.py` pinned to the 2026-10-23 dossier snapshot, which
called `1082858` unresolved before Polymarket opened a market on it. Every later step —
collect, originate, build, deploy — is skipped, so the site stops moving while Hotspawn
keeps adding matches.

That file is claimed by three parallel sessions (`04174d83` PR #326, `db6ecc61` PR #327,
`824a2780` PR #328) at the time of writing, so this session logged the defect instead of
editing it (review item `0C-R02`), and published through its own branch so the workflow
runs again.

## 2. Every published number replayed from its own evidence

`scripts/0c034b94_verify.py` re-derives the published probabilities instead of trusting
them:

| Method | Rows | Replay |
| --- | --- | --- |
| Valve research model | 5 | `g = 1/sqrt(1 + 3*(ln10/400)^2*75^2/pi^2) = 0.9728209910486895`, `p = 1/(1+10^(g*Δpoints/400))` from the two official points values |
| Prediction market (Polymarket) | 9 | two-sided order-book midpoints, proportionally normalised |
| Esportsbook (Thunderpick) | 2 | `(1/o_i)/Σ(1/o)` on the quoted decimals |
| No featured analysis | 2 (`1081156`, `1082792`) | carried by the researched layer; both publish limitations and https trails |

**0 violations.** Every row also passes the presentation invariants: two probabilities in
(0,1) summing to 1 within 1e-6, `fair_decimal = 1/p`, the pick is the higher-probability
side (and no side at all when the numbers are exactly equal), a UTC observation stamp, an
https source link, and no crowd/fan percentage anywhere in the analysis. The Valve input
used as a spot check: 5star 1110 points (standing 80) vs 1WIN 1383 (standing 38) in
[`standings_global_2026_10_05.md`](https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md)
→ **0.17816902** for 5star, exactly what the snapshot publishes.

## 3. HLTV first, then esportsbooks — only for the fixtures the featured method leaves blank

Six live fixtures were not resolved by a featured market line. HLTV answered HTTP 200 to
the runner (44 upcoming cards parsed before de-duplication, 35 after; the official weekly
ranking page `2026/october/19` yielded 253 team rows):

| Fixture | Start (Hotspawn) | HLTV match | Start delta | HLTV ranking |
| --- | --- | --- | --- | --- |
| `1086696` BORRACHEIROS vs RED Canids Academy | 16:00Z | [2399917](https://www.hltv.org/matches/2399917/borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7) | 0 s | 176 / 170 |
| `1082697` BESTIA vs paiN | 18:00Z | [2399819](https://www.hltv.org/matches/2399819/pain-vs-bestia-circuit-x-curitiba-season-4) | 0 s | 76 / 32 |
| `1086697` Projeto do KinGui vs Yawara | 19:00Z | [2399918](https://www.hltv.org/matches/2399918/tropa-do-kingui-vs-yawara-cct-2026-south-america-series-7) | 0 s | — / 157 |
| `1082861` Rooster vs Abyssal | 2026-10-27 03:00Z | [2399891](https://www.hltv.org/matches/2399891/rooster-vs-abyssal-dfrag-invitational-2026) | 0 s | 181 / 128 |
| `1082792` HOTU vs The Huns | 2026-10-31 09:00Z | [2399437](https://www.hltv.org/matches/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) | 0 s | 38 / 134 |
| `1082793` 5star vs 1WIN | 2026-10-31 13:00Z | [2399438](https://www.hltv.org/matches/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) | 0 s | — |

Every one of those HLTV cards links its own odds overview
(`/betting/analytics/<match id>/…`), and the probe read those pages for the six targets:

| HLTV odds overview | HTTP | What the served HTML carries |
| --- | --- | --- |
| [2399917 BORRACHEIROS vs RED Canids Academy](https://www.hltv.org/betting/analytics/2399917/borracheiros-vs-red-canids-academy-cct-2026-south-america-series-7) | 200 | title "odds and prediction"; no two-way bookmaker table; one promo value `1.23` repeated 6× |
| [2399819 paiN vs BESTIA](https://www.hltv.org/betting/analytics/2399819/pain-vs-bestia-circuit-x-curitiba-season-4) | 200 | same |
| [2399891 Rooster vs Abyssal](https://www.hltv.org/betting/analytics/2399891/rooster-vs-abyssal-dfrag-invitational-2026) | 200 | same |
| [2399437 HOTU vs The Huns](https://www.hltv.org/betting/analytics/2399437/hotu-vs-the-huns-gluck-moscow-cyber-games-2026) | 200 | same |
| [2399438 1WIN vs 5star](https://www.hltv.org/betting/analytics/2399438/1win-vs-5star-gluck-moscow-cyber-games-2026) | 200 | same |

The identical `1.23` on all five pages is a placeholder, not a price, so it was refused
rather than converted into a probability. HLTV therefore supplies identity and ranking for
these fixtures, not a money line — the same boundary the repository already draws, now
demonstrated on the exact fixtures it matters for.

Two identity facts come out of this that no probability is derived from:

* the earlier "multiple Valve rosters share the name *The Huns*" blocker is an artefact of
  Valve's table only — HLTV binds `HOTU vs The Huns` to one fixture at the exact Hotspawn
  start, so the *fixture* is identified even though the *Valve row* stays ambiguous;
* Hotspawn's `Projeto do KinGui` and HLTV's `Tropa do KinGui` are the same 19:00Z slot
  against Yawara, but no official page proving the two names are one organisation was
  read, so they are **not** aliased (review item `0C-R06`). An unverified alias would
  attach another team's rating to this fixture.

## 4. What a reader can check by hand

| Claim | Page |
| --- | --- |
| Live inventory and starts | <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1> |
| Rendered lobby (cache-busted) | <https://play.hotspawn.com/lobby?cb=1792935939> |
| Published snapshot age and counts | <https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json> |
| Published picks and their trails | <https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json> |
| HLTV schedule and identity | <https://www.hltv.org/matches> |
| HLTV official world ranking | <https://www.hltv.org/ranking/teams/2026/october/19> |
| Valve official standings (model input) | <https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md> |

## 5. Limitations of this session's evidence

* EGamersWorld answered **HTTP 403** to the runner; GG.BET and Stake do the same in the
  snapshot's own trails, and Pinnacle and Rivalry redirect to generic landing pages. A
  refused page is not proof that no market exists, and no price was inferred from a gap.
* The Playwright phone suite (320/390/768/1440 px, axe WCAG A/AA) runs in CI; the
  authoring sandbox cannot download the browser, so the phone claims here are limited to
  what was measured: the seven in-site routes, the unresolved-register section, the
  viewport declaration and the navigation landmarks (pinned by 13 tests).
* Nothing in this dossier was hand-written into a probability, a pick or an alias. Hotspawn
  `% picked` and HLTV fan votes were never read as inputs.
