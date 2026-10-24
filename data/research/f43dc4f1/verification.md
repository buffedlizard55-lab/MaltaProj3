# Session arena-f43dc4f1 — independent verification record (2026-10-24)

Branch `arena/f43dc4f1-maltaproj3`, branched from `origin/main` `2f966a9`.
This environment has **no network route** to Hotspawn, HLTV, Polymarket,
Thunderpick or Smarkets (`curl` answers HTTP 000 for each), so this session
re-queried no source. Every statement below is either read from the repository,
read from the GitHub API (the official record of what the pipeline did), or
produced by running the repository's own build and tests locally. No
probability, pick, alias, count or date was hand-written anywhere.

## 1. State at claim time (2026-10-24T05:30Z)

| What | Value read | Official source |
| --- | --- | --- |
| Last successful refresh | 2026-10-23T19:57:15Z | `actions/workflows/pages.yml/runs` |
| Failures since | 40028653350 (21:41Z), 40037957529 (23:08Z), 40048429858 (01:08Z), 40063011446 (04:36Z) | same |
| Failing job and step | `verify-and-deploy` → "Regression tests (repository fixtures, before any cache restore)" | `actions/runs/<id>/jobs` |
| Failing tests | 3 × `test_ca7e10e5_snapshot.RootPublisherCarriesTheSnapshot` | `check-runs/120780438497/annotations` |
| Published page observation | `data-snapshot-generated="2026-10-23T20:10:00Z"` | branch-root `index.html` |
| Published coverage | 19 active fixtures, 19 with a directional pick (12 external-line, 7 research-model), 0 unresolved | branch-root `index.html` (`#picks-at-a-glance` intro, mobile status strip) |
| Pages build type | `legacy`, source `main//` (documented limitation, unchanged) | `GET /repos/.../pages` |

The 20:10Z observation is 9.4 hours old at read time, i.e. outside the
dashboard's own 8-hour freshness bound.

## 2. Defect A — a date, not a change, turned the publisher red

`scripts/root_publish.build_plan()` raises `PublishRefused` for a snapshot
older than `max_age_hours` (12). Three tests in `tests/test_ca7e10e5_snapshot.py`
built a fixture stamped `2026-10-23T09:23:57Z` and called `build_plan()`
**without** a clock, so the wall clock was compared against a fixed date. The
fixture crossed the 12-hour bound at `2026-10-23T21:23Z` — exactly between the
19:57Z success and the 21:41Z failure — and every scheduled run after it
stopped before collection, build or deploy. The same class of bug had already
been fixed once in `tests/test_96fbe295.py`.

Reproduced locally on main `2f966a9` before any edit: the three tests error with
`PublishRefused: snapshot 2026-10-23T09:23:57+00:00 is 20.0h old (limit 12.0h)`.

## 3. Defect B — the executive summary rendered the same section twice

Built `site/index.html` from main `2f966a9` carried `id="no-line-research"`
**twice**: once from `unresolved_register(..., compact=True)` (the separate
"Unresolved picks & limitations" section) and once from an unconditional
`no_line_research_block(data, prefix)` call in `summary()`. Both copies are the
identical dated source-status table, so a phone reader scrolled through the same
~8 KB block and the same `<h3>` twice, and the duplicate id is invalid HTML —
anchor navigation silently resolves to the first copy, which is why the defect
survived. A sweep of every rendered page found this to be the only duplicate id
in the build. This is the concrete cause of the "site is a bit confusing"
observation.

## 4. Coordination: the scope belongs to another session

Session `arena-be019782` claimed `tests/test_ca7e10e5_snapshot.py` at
**05:22:48Z** and `scripts/build.py` + `scripts/validate.py` at **05:28Z**, on
its own branch (PR #237). The claim was not visible on `main`'s copy of
COORDINATION.md when this session read it at 05:30Z, so both sessions
independently reproduced and fixed the same two defects. Their fix is the same
fix: `now=` pinned to the fixture observation time, the redundant `summary()`
call removed, and a duplicate-id rejection added to
`scripts.validate.check_links`. Because their claim is earlier and active, this
session **withdrew its copies of all three files** and landed no overlapping
code; the second, independent reproduction is recorded here and on
`/review/` (`f43dc4f1-two-sessions-fixed-the-same-defects`). Process suggestion
recorded with it: publish a claim to `main` before editing shared files.

## 5. Brief lines re-checked against a local build

`python -m scripts.build` on `2f966a9` (pre-merge state of the data):

* Replay: `PASS: 80 source rows reconciled; every published probability and pick replayed from first-party evidence.`
* Row-source audit: `767 rows, 748 with an official link, 9 flagged unverified, 10 site-map, 0 without a source`.
* Acceptance audit: `9 pass, 1 info, 0 fail of 10 brief-line checks` (`site/data/acceptance-audit.md`). The single `info` is the age of the checked-in CI replay fixture (15 October by design; the live site is built from a fresh runner collection).
* Links and landmarks: `PASS: 826 internal links/assets/anchors; project-subpath routing and mobile landmarks checked.`
* Cross-session audit: `scripts.eea4c104_audit.audit_site(site)` → `ok: true`, 17 active rows checked, 5 flags checked, 0 errors — i.e. `#no-line-research` is still present on the executive summary after the duplicate removal.

| Brief line | Where it is met (rendered) |
| --- | --- |
| A pick for every Hotspawn CS2 fixture | `#picks-at-a-glance`: "17 active … 17 with a directional pick … 0 explicitly unresolved"; published observation 19/19 |
| A separate unresolved-picks section with its limitations, inside the executive summary | `#unresolved-register` → `#no-line-register` digest, the dated `#no-line-research` block, and per-fixture blockers with sources |
| Executive summary links in-site to the updated picks | `#start-here` jump bar, the mobile status strip ("17 picks ready of 17", "0 unresolved · why"), `#picks-status` |
| Phone and mobile readability | device-width viewport on every page, `.mobile-status` and `#start-here` above the picks, glance list with 44 px targets, `scout.css` small-screen rules; CI re-checks 320/390 px |
| 4–8 hour refresh | cron `17 */4 * * *` + catch-up `47 2-22/4 * * *`, `refresh_interval_hours 4`, `stale_after_hours 8` — the schedule was correct; it was not being *honoured* because of defect A |
| Every row links an official source or is flagged unverified | 0 rows without a source |

## 6. What this session deliberately did not do

* No fresh HLTV or esportsbook research: no route to those hosts from here.
  Inventing a line, or presenting a cached one as current, would violate the
  brief. The four-hour pipeline does that research on the GitHub runner, where
  the sources answer, and retries every source on every run.
* No change to any probability, pick, alias, or to the checked-in replay
  fixtures (`data/latest.json`, `data/origination.json`).
* No overlapping edit to `scripts/build.py`, `scripts/validate.py` or
  `tests/test_ca7e10e5_snapshot.py` while session `arena-be019782` holds them.

## 7. Post-merge reconciliation (2026-10-24T08:10Z)

Between this session's start and 08:10Z, `main` moved from `2f966a9` to `39946cd`
through nine merges, and two other sessions integrated parts of this session's
work and their own fixes for the same two defects:

| What | Landed as | State on `main` |
| --- | --- | --- |
| Date-dependent publisher tests (`build_plan` with no clock) | `7493ea8` (PR #240) | fixed |
| Dated `#no-line-research` block rendered twice on the summary | `e360f4c`, then PR #237 | fixed |
| Duplicate-`id` build guard in `scripts/validate.py` | PR #237 / `a0f2afd` | fixed |
| `egw_live` never imported, so `live_collect` raised `NameError` on every run (7493ea8 → 07:29Z) | PR #237 | fixed; this branch keeps `tests/test_f43dc4f1_egw_import.py` as the regression guard |
| Findings-register search + severity filter | `a0f2afd` | present, but the first version rendered every severity button unconditionally |

This branch is rebased onto `39946cd` and now carries only the delta that is
still missing: the severity buttons are rendered only when their count is
non-zero, superseded findings are counted (and filtered) as retained evidence
rather than open findings, and `data-finding-severity` distinguishes the three.
That keeps the three filters summing exactly to the "All" count — 392 rows =
178 Needs review + 212 Notice + 2 Superseded at 08:12Z — so no reader is left
wondering where the difference went.
