# Session arena-34247d4e — why the picks stopped arriving, and what the site actually shows

Read **2026-10-24T06:40Z–06:53Z**. Machine-readable companion: [`publisher-and-verification-2026-10-24.json`](publisher-and-verification-2026-10-24.json).

This session wrote **no probability, no pick and no alias**. Everything below is either read out of a repository artefact, re-derived from a cited official endpoint, or reproduced locally.

## 1. The picks stopped because the publisher's own tests expired

The published site was serving snapshot **`2026-10-23T20:10:00Z`** at 06:51Z — **10.7 hours old** against the repository's own `stale_after_hours: 8`. Four consecutive scheduled refreshes had failed, all at the same step, all on the same commit:

| Run | Created (UTC) | Head | Failed job / step |
| --- | --- | --- | --- |
| [40028653350](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40028653350) | 2026-10-23T21:41:56Z | `2f966a9` | `verify-and-deploy` → *Regression tests (repository fixtures, before any cache restore)* |
| [40037957529](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40037957529) | 2026-10-23T23:08:44Z | `2f966a9` | same |
| [40048429858](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40048429858) | 2026-10-24T01:08:36Z | `2f966a9` | same |
| [40063011446](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40063011446) | 2026-10-24T04:36:29Z | `2f966a9` | same |

The last green refresh was [40015434337](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40015434337) at **19:57:15Z** on `205ebc0`.

The job log archive is hosted on `productionresultssa19.blob.core.windows.net`, which this sandbox cannot reach, so the failing test was found by **reproduction instead of by log-reading**. Checking out the exact head of those four runs into a separate worktree and running the regression command:

```
$ git worktree add /tmp/redtree 2f966a91a103398c4ae5513828c81e32897f8af8
$ python -m unittest tests.test_ca7e10e5_snapshot -v
ERROR: test_an_older_build_is_still_refused
ERROR: test_snapshot_json_is_published
ERROR: test_the_replay_fixture_is_still_never_published
Ran 15 tests in 0.015s
FAILED (errors=3, skipped=2)

scripts.root_publish.PublishRefused: snapshot 2026-10-23T09:23:57+00:00
is 21.3h old (limit 12.0h); pass --allow-stale to publish it anyway
```

`tests/test_ca7e10e5_snapshot.py` called `root_publish.build_plan(output, root)` **without a reference clock**, so it compared the wall clock against a fixed `2026-10-23T09:23:57Z` fixture. It passed for the first twelve hours after it was written and then failed permanently — every later scheduled run would have died the same way, which is exactly what happened four times.

**Fixed already, and verified here.** PR #240 (session `arena-43110640`, merge `bdb4fc9`) pins `now=datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)` on those calls. On the merged tree:

```
$ python -m unittest tests.test_ca7e10e5_snapshot -v
Ran 15 tests in 0.015s
OK (skipped=2)
```

**Guard added so it cannot come back.** `tests/test_34247d4e_publisher_clock.py` walks every `build_plan(` call in `tests/` with `ast` and fails if any of them uses the wall clock against a fixed fixture. Run against the two trees it reports **three unpinned calls (lines 73, 77, 84) in the pre-fix file** and **one pinned call in the fixed file** — i.e. the guard would have stopped this outage before it started.

## 2. A second, still-open irregularity: push-triggered refreshes are being cancelled

Between 06:32Z and 06:44Z three pushes to `main` created three `pages.yml` runs — [40070626757](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40070626757), [40071009969](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40071009969), [40071346040](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40071346040) — and **all three were cancelled while still pending**, because a newer run entered the same `pages-push` concurrency group. The workflow's own comment documents this behaviour. The 06:47Z scheduled slot (cron `47 2-22/4 * * *`) had not started by 06:53Z, and this session's token cannot create a dispatch run:

```
$ gh workflow run pages.yml --ref main
could not create workflow dispatch event: HTTP 403: Resource not accessible by integration
```

Consequence: while many sessions push `main` every minute, a merge does **not** reliably refresh the site, and the four-hourly schedule is the only dependable trigger. Not changed here — `.github/workflows/**` is shared scope and the concurrency design is deliberate. Reported on the Flagged for Review page instead.

## 3. What the deployed site actually shows (verified row by row)

`https://buffedlizard55-lab.github.io/MaltaProj3/` (branch-root `index.html`, 157,509 bytes, read 06:52Z) carries snapshot `2026-10-23T20:10:00Z`: **82 inventory records, 19 upcoming, 17 picks, 2 unresolved**, and a summary glance list of **19 rows**, each with both teams' percentages, the pick, a market/model badge and an in-site evidence anchor.

**One spot-check re-read from the primary source:**

| Hotspawn card | Published | Re-read now | Verdict |
| --- | --- | --- | --- |
| **1082897 B8 vs K27** (Tesla Cup 2026, starts 2026-10-27T08:00Z) | B8 **62.0 %** / K27 **38.0 %**, `market`, observed 2026-10-23T20:09:49Z | [Polymarket market 6024944](https://gamma-api.polymarket.com/markets?slug=cs2-b8-k271-2026-10-27) *“Counter-Strike: B8 vs K27 (BO3) – Tesla Cup Group A”*, `outcomePrices 0.615 / 0.385`, `updatedAt 2026-10-24T06:36:38Z`, `gameStartTime 2026-10-27 08:00:00+00` | **confirmed within one tick**; the market's start equals Hotspawn's start |

## 4. The inventory is behind the live feed — the actual "missing picks" cause

Reading Hotspawn's own scheduled-fixture API through the page-fetch proxy at 06:45Z–06:51Z and looking each returned id up in the published `snapshot.json`, these live cards are **absent from the published snapshot entirely**:

* **Returned to this session's own read** (API chunks 0, 7 and 8 of 9): `1081156`, `1081158`, `1083122`, `1083123`, `1083140`, `1082695`
* **From session `73bc57bd`'s 05:31Z lobby read** (PR #241), where this session confirmed only the absence from `snapshot.json`: `1079658`, `1079659`, `1079660`, `1081152`, `1081153`, `1081154`

The full nine-chunk payload was not re-read, so this is a spot reconciliation, not a complete live inventory re-derivation — session `dd433e7f` did the complete one in its runner sweep.

Samples confirmed live ([API](https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1)):

| Hotspawn id | Card | Competition | Starts (UTC) |
| --- | --- | --- | --- |
| 1081156 | Spirit Academy vs LFO 10 | CCT Europe 2026 Series #12 | 2026-10-25T12:00Z |
| 1081158 | FORZE Reload vs ex-RUSTEC | CCT Europe 2026 Series #12 | 2026-10-25T13:00Z |
| 1082996 | Acend vs UNiTY | NODWIN Clutch Series #13 | 2026-10-25T09:00Z — **present** in the published snapshot with a model pick (54.2/45.8), i.e. the pipeline does price low-tier fixtures |

So the cards the brief asks about ("low-tier, not on the betting sites") are missing **because no collection has completed since 19:57Z**, not because the resolver refuses them: session `73bc57bd` measured the same gap independently at 05:31Z (25 live cards vs 19 published) and recorded two-sided external prices for several of them ([dossier](../73bc57bd/inventory-reconciliation-2026-10-24.md)). Once a refresh runs, the existing ladder (Polymarket → Kalshi → Thunderpick → Bovada → EGamersWorld → Valve model) prices them automatically; nothing has to be written by hand.

## 5. Executive summary and phone — structural check

| Check | Result |
| --- | --- |
| In-site links from the summary to the updated picks | `./origination/#picks` ×17, `./picks/`, `./unresolved/` ×8, `./coverage/` ×8, `./methodology/` ×7, `./review/` ×7, plus one `./origination/#match-<id>` anchor per row |
| Viewport | `<meta name="viewport" content="width=device-width, initial-scale=1">` |
| Tables that could overflow a phone | **0** — all 8 tables on `/` sit inside `.table-scroll` or `.matches-wrap`, both `overflow-x:auto; max-width:100%` |
| Responsive coverage | `max-width:700px` (30 rules), `max-width:620px` (2), `max-width:375px` (9) |
| Phone-first element | `#picks-at-a-glance` renders above every table: 19 rows, both percentages, the pick, the price and the evidence anchor |

This agrees with session `73bc57bd`'s measured 0 px overflow at 320 px and 390 px. **No mobile defect found.**

## 6. Local build on the merged tree

```
$ python -m scripts.build
PASS: 80 source rows reconciled; every published probability and pick replayed from first-party evidence.
Row-source audit: 780 rows, 761 with an official link, 9 flagged unverified, 10 site-map, 0 without a source
Acceptance audit: 9 pass, 1 info, 0 fail of 10 brief-line checks
PASS: 827 internal links/assets/anchors; project-subpath routing and mobile landmarks checked.
Built 9 current Pages views, compatible old URLs and explicitly archived session views in site
```

## Limitations of this session (stated, not hidden)

1. The sandbox has **no direct egress** to `hltv.org`, `polymarket.com`, `egamersworld.com`, `smarkets.com`, `bovada.lv`, `kalshi` or the Actions log blob host (`curl` returns HTTP 000 for each). Page reads were made through the agent's page-fetch proxy, which returns rendered text/JSON but cannot write a byte-for-byte evidence file into `data/evidence/`; each re-read therefore carries its endpoint and read time instead of a saved payload.
2. **No live collection could be run from here**, so "a pick for every live card" can only be confirmed after a publisher run completes. This session verified the mechanism, the published rows and the structural coverage — not a fresh collection.
3. The publisher could not be dispatched (HTTP 403) and its push runs were being cancelled (section 2).
