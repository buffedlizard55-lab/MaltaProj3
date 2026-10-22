# arena-3a5448de — findings (2026-10-22)

Full machine evidence: `live-research.json` / `live-research.md` in this directory
(runner probe at 2026-10-22T08:06:21Z, snapshot origination 2026-10-22T08:04:52Z).

## Coverage at probe time
- 43 active Hotspawn CS2 fixtures; 43 with probabilities; **42 with a directional
  pick; 0 still blank; 1 resolved-but-even with no side** (Isurus vs Hacha).
- 19 fixtures were not resolved the same way as the featured picks (no first-party
  money line). Their current resolutions: 10 Valve-rating research estimates
  (featured model), 3 Valve research-model fallback, 2 HLTV world-ranking,
  2 HLTV world-ranking · unranked floor, 2 own bo3.gg network estimates.
  Each keeps both probabilities, the pick, the failed money sources and its
  limitation in *Picks without a betting line* on the executive summary.

## HLTV first (per brief)
- HLTV match listing and world ranking: **HTTP 403** Cloudflare challenge from the
  GitHub runner. HLTV therefore remains an identity/ranking source (the ranking
  rung uses the saved official capture); it publishes no two-sided prematch price,
  and its "Pick a winner" fan vote is never an input.
- For Isurus vs Hacha the collector did confirm exact teams/time on HLTV
  ("HLTV research · checked" in the fixture trail) — identity yes, price no.

## Esportsbooks / betting lines second
| Surface | Runner result 2026-10-22T08:06Z | Price verified? |
| --- | --- | --- |
| Stake CS2 | 403 challenge | no |
| GG.BET | 403 | no |
| Marathonbet | 403 challenge | no |
| EGamersWorld | 403 challenge (reviewed capture remains a separate dated rung) | no new |
| BetBoom | 401 | no |
| 1xBet | 203 challenge | no |
| DraftKings CS2 | 404 on probed path | no |
| Betway CS2 | 404 on probed path | no |
| Oddspedia CS2 | 410 (deleted) | no |
| Luckbox | DNS failure | no |
| OddsPortal | 200, no target team listed, prices client-side | no |
| Rivalry | 200, no target team listed | no |
| Pinnacle guest API | 200 (already a ladder rung; no line for these fixtures per trails) | no new |
| bo3.gg | 200; bound 14/19 target fixtures, `bet_updates` block on **0** of them | no new |

Already in the ladder and retried every refresh for every target: Polymarket,
Kalshi, Thunderpick, Bovada, Pinnacle, bo3.gg relayed bookmaker quotes,
EGamersWorld reviewed average, Valve ratings, own bo3.gg results/network models,
HLTV world ranking, wide-book guidance. Their per-fixture outcomes are the
`sources_tried_from_published_trail` records in `live-research.json`.

## Rejected lead
bo3.gg team records publish `rank` and `six_month_earned` (e.g. Butterfly rank 88).
The record states no strength methodology and sits beside `avg_views`; it was
**not** wired as a rating and not used to break the Isurus–Hacha tie.

## Decision (S3-2)
No new source met the bar (a verified two-sided first-party prematch price, or a
published official rating with a stated methodology), so **no probability, pick
or alias changed**. The one pick-less fixture stays even/no-side with its reason
in the separate register — inventing a side for an exactly equal published
rating would be fabrication.

## Executive summary / mobile (S3-3)
The summary carried two H2s titled "Unresolved picks & limitations" with
different counts; hero/briefing shortcuts landed on the bottom (featured-method)
one while the jump bar landed on the top register. Now: one canonical register
(`#unresolved-register`), the bottom section retitled "Featured-method gaps,
before research fallback", all summary unresolved shortcuts → the register.
Pinned by `tests/test_3a5448de_summary.py`; phone spec updated in
`tests/browser/dashboard.spec.mjs`.

## Addendum after merging main (PR #174, session 4c972a51)
Main merged a *published-rank tie-break* while this session ran: an exactly even
research-model estimate (50/50) now gets a direction from the provider's own
published ranking order (Isurus HLTV #215 over Hacha #229), with probabilities
unchanged and the rule recorded on the row. That gives every active fixture a
pick at the latest live snapshot (43/43 in the 08:5xZ originate audit). This
session also fixed the replay validator (`scripts/build_origination.py`), which
still asserted an even row could never carry a pick and therefore failed the
live build whenever the tie-break fired, and updated
`tests/test_review_flags.py` for 4c972a51's deliberate published-JSON
reconciliation keys. The tie-break direction is a convention, not an edge —
flagged as such in `flags.json`.
