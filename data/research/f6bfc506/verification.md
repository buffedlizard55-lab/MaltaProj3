# Session arena-f6bfc506 — refresh restored, coverage verified against the public site (2026-10-23)

This dossier is the dated evidence behind the review flags `f6bfc506-*`. Machine-readable twin:
[`verification.json`](verification.json).

## What was wrong

The scheduled publisher had failed **six runs in a row** at its first gating step, so nothing downstream
ever ran: no inventory refresh, no line research, no rebuild, no deploy.

| run | created (UTC) | head | event | conclusion |
| --- | --- | --- | --- | --- |
| [39807044948](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39807044948) | 2026-10-22T15:40:30Z | cdd77b58 | schedule | failure |
| [39845991470](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39845991470) | 2026-10-22T20:06:48Z | cdd77b58 | schedule | failure |
| [39861117407](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39861117407) | 2026-10-22T21:55:48Z | cdd77b58 | schedule | failure |
| [39871371551](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39871371551) | 2026-10-22T23:22:44Z | cdd77b58 | schedule | failure |
| [39881298806](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39881298806) | 2026-10-23T00:58:37Z | cdd77b58 | schedule | failure |
| [39902353982](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39902353982) | 2026-10-23T04:49:13Z | cdd77b58 | schedule | failure |

Failing step in every one: `Regression tests (repository fixtures, before any cache restore)`. The
annotations on run 39902353982 name exactly:

```
FAIL: test_check_mode_reports_a_current_root_and_then_drift (test_96fbe295.PlanTests…)
FAIL: test_only_the_bound_fixture_is_saved_with_its_quote (test_15fc6bca_relay.RelayCollectionTest…)
```

Reproduced on the checkout of `cdd77b5`: `Ran 985 tests … FAILED (failures=2)` — the same two. Both are
date-bound (the code reads the wall clock, the fixtures were pinned to 2026-10-22), not product defects.
They were fixed upstream by [PR #191](https://github.com/buffedlizard55-lab/MaltaProj3/pull/191); this
session adopted those fixes (`--theirs`) rather than shipping a second version of them.

## What this session changed

* `scripts/root_publish.py` — `republish_regression()` and `--refuse-if-older-than-live` (exit 3 when the
  saved build predates the public snapshot). The fast `republish-last-verified` job restores the newest
  **successful** artifact first; with six failures in a row that artifact was a day old and would have
  moved the site backwards.
* `.github/workflows/pages.yml` — every deploy step of that job is gated on the guard, and the job checks
  out `scripts/` **before** the artifact is extracted (checkout runs `git clean -ffdx`).
* `tests/test_f6bfc506_republish_guard.py` — refused / allowed / exactly-equal / unreadable / CLI exits.

## Recovery, verified on the public site

Publisher run [39912686322](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39912686322)
(`d2788544`, 06:38Z → 07:23Z) completed **every** step, including
`Verify the public site` and `Verify the public site after root-sync re-deploy`. Root publish commit:
`99c7b76`.

Read back from <https://buffedlizard55-lab.github.io/MaltaProj3/> at 07:05Z:

* freshness label **“Source snapshot available”**, inventory **23 Oct 2026, 08:42** (Europe/Malta);
* **32 active Hotspawn CS2 fixtures, 32 with a directional pick — 23 external-line, 9 research-model, 0 explicitly unresolved**;
* all 32 rows in the glance index show **both** teams’ percentages, the named pick and its basis badge;
* the register states *“No unresolved fixtures in this snapshot … as of 23 Oct 2026, 08:42”*;
* internal links present on the same page: `/origination/#picks` (updated picks), `/picks/` (featured
  feed), `/unresolved/` (unresolved & limitations), `/methodology/`, `/coverage/`, and a per-row
  `Full detail` anchor `/origination/#match-<id>`.

## Coverage cross-check against Hotspawn

Read directly from <https://play.hotspawn.com/cs2-pickems> at 07:05Z: **197 matches this week**, **93**
fixtures in the tier filter. The 30 future fixtures visible in its *Closing Soon* and *Upcoming*
sections were listed by id and **every one appears on the site with a pick**:

1081149, 1079654, 1081605, 1081148, 1079655, 1081606, 1082926, 1083014, 1082924, 1081150, 1079657,
1082693, 1082925, 1082923, 1079193, 1079195, 1082996, 1079198, 1079199, 1079200, 1082858, 1082859,
1082860, 1082861, 1082897, 1082898, 1082900, 1082901, 1082792, 1082793.

The site publishes two more, `1082980` (LPH vs WBT Academy) and `1083025` (Imperial vs paiN). The second
was confirmed on its own page —
<https://www.hotspawn.com/matches/imperial-vs-pain-circuit-x-curitiba-4-1083025> renders
“Imperial vs paiN · 21:00 · 23 OCT · Circuit X Curitiba #4” with a Pick’Ems prompt. The site’s inventory
is the scheduled-fixture API, a superset of the lobby’s rendered list, so extra fixtures are additional
coverage. The direction that would be a defect — a lobby fixture missing from the site — was not found.

## Row-level replay (one row, end to end)

`1082901` **Envy vs GamerLegion**, published as *GamerLegion 53.5% / Envy 46.5% · Market line ·
Polymarket*. The cited market (<https://polymarket.com/event/cs2-envy-gl1-2026-10-27>) showed
**envy 48c / gl1 55c** at 07:10Z:

```
1/0.48 = 2.08333 ; 1/0.55 = 1.81818 ; overround = 3.0%
normalised: Envy 46.6%  GamerLegion 53.4%
published:  Envy 46.5%  GamerLegion 53.5%   → confirmed (two-cent display rounding)
```

`1083025` was **not** replayed against its cited market in this pass; it is published unchanged and
flagged `f6bfc506-row-1083025-not-replayed` instead of being re-derived.

## Phone-first check (measured, not asserted)

Playwright, same renderer, 320×844 and 390×844, on a local build of this branch:

| width | horizontal overflow | “Start here” first tap | first pick row |
| --- | --- | --- | --- |
| 320 px | 0 px | 503 px | 1256 px |
| 390 px | 0 px | 485 px | 1098 px |

No page among `/`, `/picks/`, `/unresolved/`, `/review/`, `/coverage/`, `/methodology/`,
`/origination/` scrolls horizontally at either width. Pick, both percentages and the basis badge sit in
the same row. The full browser suite is **89/89** (includes the phone navigation and pick-safety specs).

## Standing limitations (also published on Flagged for Review)

1. This sandbox has **no general egress**; live pages were read through a fetch tool at the timestamps
   shown, and the collector itself ran on GitHub’s runner.
2. `…/data/latest.json` still serves the **checked-in 2026-10-15** copy while the rendered pages are
   current — by design (the root publisher never writes `data/*`), but confusing for a reader following
   the footer’s *Open data* link.
3. The lobby’s rendered list is a subset of the fixtures API and is delivered in chunks: set equality was
   established in one direction only.
4. One row was replayed against its market; the other 31 rest on the pipeline’s row-source audit
   (0 rows without an official source).

## Verification performed

* `python -m unittest discover -s tests` → **1020 tests, OK** (merged tree).
* `npx playwright test` → **89/89 passed**.
* `python -m scripts.build` → `PASS: 80 source rows reconciled`, row-source audit **700 rows / 681 with
  an official link / 9 flagged unverified / 0 without a source**, **806** internal links/assets/anchors OK
  (on the build that integrates main as of 2026-10-23T08:00Z; the row count grows as other sessions'
  registers merge — the invariant this dossier stands behind is **0 rows without a source**).
