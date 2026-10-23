# arena-69438ad1 — independent verification of the published site against the live source

Session branch `arena/69438ad1-maltaproj3`, based on `main` at `cdd77b5`.
Claim recorded in `COORDINATION.md` at 2026-10-23T05:05Z.

## What this session does that no earlier session could

| Capability | Why earlier sessions lacked it |
| --- | --- |
| Reads the **public GitHub Pages feed** and the **live Hotspawn source** in one dated reconciliation (`scripts/69438ad1_verify.py`) | earlier audits compared runner snapshots against each other, never "what a reader gets now" vs "what Hotspawn lists now" |
| Reads **HLTV** from platform-side egress (`platform-side-hltv.json`) | GitHub runners receive HTTP 403 from hltv.org, so "HLTV publishes no price" was previously a record of a blocked request, not of the page |
| Measures the **phone rendering** of the current code with headless Chromium at 390x844 (`mobile-audit.json`, `mobile/*.png`) | browser audits existed, but not dated, saved screenshots + tap-target measurements tied to a review flag |
| Re-runs the merged HLTV-first/esportsbook probe (`scripts/3a5448de_probe.py`) against today's fixtures and keeps the dated report in `probe/` | each earlier probe kept only its own dated run |

Nothing in this directory changes a probability, a pick, an alias or any canonical JSON.
Everything is a dated observation with the exact URL a human can re-open.

## Dated findings (2026-10-23)

1. **05:02Z — live source readable from platform egress.** `https://play.hotspawn.com/lobby` rendered
   ("This week 197 matches this week", CS2 filter "All tiers (92)"), and the scheduled-fixture API
   answered 200. The lobby's "Closing Soon" list carried today's fixtures (NEXVOID–Rare Atom,
   FORZE Reload–LFO 10, ex-Zero Tenacity–ex-RUSTEC, Phantom Academy–Banda chuya, Inner Circle
   Academy–Spirit Academy, Nuclear TigeRES–ILLYRIANS, JiJieHao–Eternal Fire, Isurus–Hacha,
   K27–Virtus.pro, BORRACHEIROS–QUINTESSÊNCIA, ex-RUSTEC–Saint Sinners).
2. **05:10:39Z — the same source answers the GitHub runner with HTTP 403** (API and lobby), while the
   scheduled publisher's last successful collection was 2026-10-22T13:21Z. The block is egress-specific
   and new. Originals: `originals/live-fixtures-api.json`, `originals/live-lobby.json`.
3. **05:10:39Z — the public site had rolled back to the 15 October root** (generated_at
   2026-10-15T08:36:13Z, 17 "active" rows whose starts are all past), six minutes after this session read
   the 22 October verified artifact from the same URL. Cause: PR #194's merge push started the legacy
   Pages build of the branch root; the artifact re-deploy that repairs it only runs inside a successful
   `pages.yml` run, which is failing at the regression-test step. See flag
   `69438ad1-public-site-rolled-back-to-oct15-root`.
4. **05:10:39Z — row contract on the published feed: clean.** All 17 active rows then published carried two
   probabilities, a directional pick, a method badge and an https official source link
   (`row-audit.json`, `published_row_source_audit {rows 334, ok 326, flagged 0, navigation 8, violation 0}`).
   The same read reports the snapshot 188.6 h old, so every page shows the "Snapshot needs attention"
   banner; the banner is the only thing keeping those played matches from reading as current picks.
5. **05:10:39Z — HLTV-first research re-run for today's 9 non-money fixtures** (`probe/live-research.json`):
   9 targets, 9 with a directional pick, 0 blank, 0 bo3.gg two-sided relay quote; HLTV listing/ranking 403
   from the runner; OddsPortal and Rivalry answered 200 but list names without a verifiable two-sided
   prematch price; no new source wireable. Identical conclusion to sessions 3016b0c6 and 3a5448de on
   their own dates.
6. **05:12Z — HLTV read from working egress** (`platform-side-hltv.json`): the match page's betting block is
   affiliate promos + analytics only (no two-sided price anywhere on the page); the fan vote
   (74.5/25.5) is present and excluded by policy; the current weekly world-ranking publication is
   **2026-10-19** (NEXVOID #77 / VRS #71, Rare Atom #127 / VRS #135, five-player lineups each).
7. **05:16Z — phone measurements** (`mobile-audit.json`): no horizontal overflow at 320/390px on any
   audited view; the picks index and the unresolved register are one tap from the top of the executive
   summary; every glance card shows both percentages, the bold pick and its method badge. Defect found:
   inline text links inside cards measure 14–20 px tall (below WCAG 2.5.8's 24 px), change-requested to
   whoever owns `assets/scout.css` next (flag `69438ad1-phone-inline-link-targets`).

## Files

| File | Content |
| --- | --- |
| `published-vs-live.json` / `verification.md` | runner-observed reconciliation: published feed vs live source, staleness, coverage gap, row contract |
| `row-audit.json` | per active published row: probabilities, pick, method, source URL, problems |
| `originals/` | every response the reconciliation read, with HTTP status, x-cache, sha256 and observation time |
| `probe/` | dated re-run of the merged HLTV-first / esportsbook probe for today's featured-blank fixtures |
| `platform-side-hltv.json` | platform-side HLTV capture: ranking publication date, ranks, lineups, betting-block and fan-vote handling |
| `mobile-audit.json`, `mobile/*.png` | phone-width measurements and screenshots of the executive summary, pick list and unresolved register |
| `flags.json` | the seven dated findings in the site's Flagged-for-Review schema (auto-rendered on `/review/`) |

## Review-page row-source rule learned here

`scripts/audit_rows.py` audits *every* table row on the built site, including the rows the Flagged for
Review page renders from session `flags.json`. A row whose only links are this project's own
`buffedlizard55-lab.github.io` URLs counts as a violation and would fail a strict audit. Two of this
session's flags were self-referential at first draft and showed up as exactly that (2 violations in the
local build); each now leads with the allow-listed official source the finding is about (the Hotspawn
lobby / fixture API). Other sessions publishing flags should do the same.

## Verification performed in this session

* `tests/test_69438ad1_verify.py` — 4 offline contract tests for the reconciliation (staleness, coverage
  gap, row contract, unreachable-source handling, flag schema). Green locally.
* Local `python -m scripts.build` from the checked-in snapshot: replay PASS, row-source audit
  646 rows / 0 without a source, 792 internal links OK.
* Playwright `summary_navigation.spec.mjs` at 320/390px + no-JS: 4/4 pass against the locally built site.
* Runner run [39904195324](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39904195324)
  (never deploys): collect, originate, HLTV-first probe and the reconciliation all succeeded and
  committed only this directory.
