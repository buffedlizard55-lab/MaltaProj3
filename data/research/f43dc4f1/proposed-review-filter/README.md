# Proposed: a search + severity filter for the findings register (/review/)

Session `arena-f43dc4f1`, 2026-10-24.

## Why this is a proposal and not a commit

`flag-f43dc4f1-review-page-not-phone-friendly` records the problem: the built
`/review/` page is **1,064 KB** with **417 table rows** and **428,533
characters** of text in `<main>` — 13 snapshot findings plus 288 auto-loaded
`data/research/*/flags.json` findings — in one flat table with no index, no
search and no grouping. The fix lives in `scripts/build.py::flags_table`, and
that file was claimed by session `arena-be019782` (PR #237) before this session
started. The board's rule is to log a cross-owned request instead of editing
another session's file, so the fix is delivered here as a tested patch.

## What the patch does

`findings-filter.patch` (in this directory) applies cleanly to the tree of PR
#237:

* `scripts/build.py::flags_table` — adds a `#findings` section id, a search box
  (`#finding-search`), two severity buttons (All / Needs review / Notice) and a
  live count. **Every row is still rendered server-side, in the same order,
  with the same title, detail and source links**; each row gains
  `data-finding-severity` so the filter can address it. Counts are computed
  from the rows (`len(flags)`), so the filter can never advertise a finding the
  table does not show.
* `assets/findings-filter.js` — new, self-hosted (the page CSP is
  `script-src 'self'`). It only sets `row.style.display` on matching rows; no
  network calls, no text written except the count, no source link touched. An
  inline style rather than the `hidden` attribute because `scout.css` sets
  `display: block` on these rows below 700 px, which beats the user-agent
  `[hidden]` rule — a real bug this patch avoids.
* `assets/scout.css` — 13 lines, scoped to `.findings-filter`, with 44 px tap
  targets on phones.
* `tests/test_f43dc4f1_findings_filter.py` — 12 assertions (no network, no
  text writes, rows unhidden by default in the built page, the script loads on
  `/review/` only, the count comes from the rows).
* `tests/browser/f43dc4f1_findings.spec.mjs` — phone checks at 320 px and
  390 px: every row visible on load, a no-match query hides all rows and says
  `0 of N`, each severity button narrows to exactly its count, clearing
  restores every row, and the page still does not scroll sideways.

## Verification already performed (in a throwaway worktree at PR #237's head, `b996fab`)

* `python -m scripts.build` — PASS: 80 source rows replayed, 772 rows / 0
  without a source, acceptance 9 pass · 1 info · 0 fail, 827 internal
  links/anchors.
* `tests.test_f43dc4f1_findings_filter` — **12 tests OK**.
* Playwright at 320 px and 390 px — **2 passed**.
* Rendered page: 305 findings, 305 rows with `data-finding-severity`
  (168 notice / 137 review), 2 superseded rows preserved, script loaded on
  `/review/` only, no row pre-hidden.
* Phone screenshot at 390 px confirms the register header and the existing
  content are unchanged and the page does not overflow.

## How to apply

```bash
git apply data/research/f43dc4f1/proposed-review-filter/findings-filter.patch
python -m scripts.build && python -m unittest tests.test_f43dc4f1_findings_filter
npx playwright test tests/browser/f43dc4f1_findings.spec.mjs
```

No probability, pick, alias, finding or source status is changed by the patch:
it is presentation only.
