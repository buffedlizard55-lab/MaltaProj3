# Publisher stall, 2026-10-24 (session arena-da8067f5)

First-hand evidence collected on this branch, 2026-10-24T07:07Z–08:35Z. Nothing in
this file is inferred: every statement carries the run id, API field or command
output it came from.

## 1. Why the recovery publish failed (resolved)

* Run **40077233256** (`event=push`, created 08:14:05Z) — job
  `republish-last-verified` **failure**, job `verify-and-deploy` **skipped**.
* Same shape for **40078105941** (created 08:27:26Z): job failure at step 5
  *"Retire only publishers predating independently replayable sources"*,
  `verify-and-deploy` skipped.
* Cause, not a guess — the check-run annotation for job
  `120823116413` reads:

  > `failure: Recovery queue safety not established: Obsolete publisher has not
  > stopped; recovery cannot publish`

  i.e. `scripts/be019782_release.py` cancelled an obsolete queued `pages.yml`
  run and then waited its 90 s deadline for that run to reach `completed`; a
  queued job cannot be retired in 90 s when the runner pool is saturated, so the
  gate failed closed (correctly) and `queue_safe` was never written, which is why
  `verify-and-deploy`'s recovery guard skipped the deploy.
* Root trigger: the run's head commit message is
  `recovery: publish fully verified current picks on the available runner pool`
  (sha `96285815348bb681cb3a87dffde087cc5ea59f97`). The publisher guard
  `startsWith(github.event.head_commit.message, 'recovery:') || schedule == '47
  2-22/4 * * *'` therefore evaluated **true for a push run**, which is by design
  for recovery commits and not a stale step list.
* Follow-up fix is **not** in this file's scope: session `arena-34247d4e` landed
  the gate correction in `0e2c4ad` / `6b36af1` ("Handle documented cancellation
  immunity only for proved obsolete publishers").

`gh run view --log-failed` and the job-log blob both fail from this sandbox
(`results-receiver EOF` / `productionresultssa12.blob.core.windows.net` not
reachable), which is why this was resolved through the check-run annotations API
instead of the step log.

## 2. Why the site is still on the 2026-10-23T20:10:00Z snapshot

The deployed `data/latest.json` was re-read at 08:35Z with a cache buster
(`?t=0835`) and still reports `generated_at 2026-10-23T20:10:00Z`,
`counts.inventory 82`, `upcoming 19`, `picks 17`, `unresolved 2`,
`run_status partial-picks`. Nothing has published since.

At 08:35Z **every** workflow in the repository with a queued run was waiting for
a runner, not merely the publisher:

| run | workflow | event | created | status at 08:35Z |
| --- | --- | --- | --- | --- |
| 40078370106 | Refresh and deploy CS2 dashboard | push (recovery commit) | 08:31:25Z | `queued` — `republish-last-verified` queued (runs-on `macos-14`) |
| 40078527465 | Refresh and deploy CS2 dashboard | push | 08:33:48Z | `pending` (behind the same `pages-push` group) |
| 40078258563 | Refresh and deploy CS2 dashboard | push | 08:29:49Z | `completed/cancelled` without ever starting |
| 40078504758 | Validate dashboard | push | 08:33:26Z | `queued` |
| 40078333824 | Validate dashboard | push | 08:30:49Z | `queued` |
| 40078336217 | Validate dashboard | pull_request | 08:30:51Z | `queued` |

Earlier in the same hour a push run *did* start within seconds (40078105941,
created 08:27:26Z, failed by 08:28), so this is a runner-availability stall that
began around 08:28Z, not a concurrency-group deadlock: `freshness-watchdog.yml`
has a `*/30 * * * *` schedule and **zero** runs since it merged at 07:07Z
(`gh run list --workflow=freshness-watchdog.yml` returns nothing, 88 minutes after
it merged), so scheduled work was not being served either.

`githubstatus.com/api/v2/status.json` reported `indicator: none` at 07:09Z, so
this is documented as an observed stall of this repository's runner allocation,
not as a diagnosis of the network. The repository is public
(`gh api repos/... -q .private` → `false`), so per-minute billing limits are not
the explanation that the API evidence supports.

## 3. What is verified locally, so the snapshot is ready the moment a runner starts

* `python3 -m scripts.build` on this branch: **PASS** —
  80 source rows reconciled; row-source audit **892 rows, 872 with an official
  link, 10 flagged unverified, 10 site-map, 0 without a source**; acceptance
  audit 9 pass / 1 info / 0 fail of 10; **834** internal links/assets/anchors
  checked; 9 Pages views built.
* `python3 -m unittest tests.test_da8067f5_watchdog`: **14 tests OK**.

## 4. Watchdog correction landed with this record

`QUEUED_GRACE_MINUTES = 15` still applies to queued **push** runs, and an
`in_progress` run always blocks. The previously absolute rule "a queued
`workflow_dispatch` run always blocks" is now bounded by
`DISPATCH_GRACE_MINUTES = 45`, because of the stall above:

* dispatch run **40074120319** has been `queued` since 07:26:12Z and
* dispatch run **40074984702** has been `pending` since 07:39:16Z.

Under the old rule those two dead runs would silence the freshness watchdog
permanently — it would never dispatch again, even after the pool recovers. A
queued run has executed no step, so replacing it with a fresh dispatch loses no
work; a run with no parseable `created_at` still blocks, because its age is
unknown.

## 5. Flags (unchanged, never blocking)

* No new pick, price, alias or evidence value was created by this session's work
  here. The 9 CCT fixtures that entered the lobby after the frozen snapshot
  (`1079658, 1081152, 1079659, 1081153, 1079660, 1081154, 1079661, 1081156,
  1081158`) are priced by the ladder on the next successful collect; they are
  listed as gaps in `data/research/da8067f5/live-coverage.json` and are not
  hand-filled.
* The deployed snapshot is 12+ hours old at the time of writing. That is a
  publishing outage, not a data fabrication: no stale value was relabelled as
  fresh.
