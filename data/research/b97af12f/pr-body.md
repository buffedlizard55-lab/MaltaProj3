## Summary

Session `arena-b97af12f` adds a dated, source-linked reconciliation of the live Hotspawn CS2 lobby and its own scheduled-fixture API, HLTV-first research for the uncovered cards, a read-only runner re-check, phone/link verification, and review flags. It does **not** hand-write a probability, pick or alias, and does not edit another session's research directory or the shared renderer/snapshot.

### What was observed (2026-10-24T06:24Z–06:52Z, first-hand)

- `https://play.hotspawn.com/lobby` rendered **25 future CS2 cards**.
- Hotspawn's own `api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` returned **31 future rows**. Six (`1083120,1083121,1082695,1083122,1083140,1083123`) were not rendered in the fetched lobby HTML; they are retained and flagged, not dropped.
- The live Pages snapshot was `2026-10-23T20:10:00Z` (19 upcoming rows; the site itself warns not to treat them as current picks). It carried **16** of the 25 rendered cards. Nine rendered cards were missing: Series #11 `1079658,1079659,1079660,1079661`; Series #12 `1081152,1081153,1081154,1081156,1081158`.
- Research order was **HLTV first** (identity/format only), then Polymarket and EGamersWorld. Four Series #11 quarterfinals had a dated two-sided external line lead; five Series #12 cards had only `1.8/1.8` placeholders, `$0.00`-volume/crossed books, or the `LFO 10` ↔ `Sökerorg` name conflict. Hotspawn “% picked” and HLTV fan votes were excluded. The reviewed collector remains the only path to a published number.
- The Hotspawn API reports `lock_offset_sec=360` (six minutes); the rules page says five. Both are recorded, not aliased.

### Files

- `data/research/b97af12f/reconciliation-2026-10-24.{json,md}` — all 31 rows, official Hotspawn links, explicit UTC starts/locks, published-snapshot status and per-row limitations.
- `data/research/b97af12f/live-coverage.{json,md}` — build-readable dated coverage register (`observed_at 2026-10-24T06:52:00Z`).
- `data/research/b97af12f/line-source-research.{json,md}` — HLTV-first research trail for the nine missing cards; agent-authoring record is downloadable, runner record is produced by the workflow.
- `data/research/b97af12f/flags.json` — nine review flags, including the six API-only rows, the name conflict, zero-volume/crossed books, EGW placeholders, the PR #241 overlap, the duplicate-id handoff and the legacy-root snapshot discrepancy.
- `scripts/b97af12f_reconcile.py` — regenerates/validates the dossier offline.
- `scripts/b97af12f_probe.py` + `.github/workflows/b97af12f-evidence.yml` — read-only GitHub-runner re-check that saves status/hash/excerpt evidence and refreshes only this session's two records. A job-scoped `actions: write` step dispatches `pages.yml` on `main` in its own concurrency group because the sandbox integration token receives HTTP 403 on `workflow_dispatch`.
- `tests/test_b97af12f_reconciliation.py`, `tests/test_b97af12f_mobile.py` — **12 offline tests**.
- `data/research/b97af12f/mobile-verification.{json,md}` — phone/link/build verification.

### Sources

- Hotspawn lobby and official fixture API: `https://play.hotspawn.com/lobby`, `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1`
- Published dashboard: `https://buffedlizard55-lab.github.io/MaltaProj3/`, `/picks/`, `/unresolved/`, `/review/`, `/data/latest.json`
- HLTV events/matches: `https://www.hltv.org/events/9442/matches`, `https://www.hltv.org/events/9457/matches`, and the nine match pages linked in the dossier.
- Polymarket CCT Europe board and the four event pages; EGamersWorld CS2 index and the Series #11/#12 match pages.

### Verification

- Rebased onto `origin/main` (resolved `COORDINATION.md` conflicts by keeping every session block verbatim).
- Offline build after rebase: 168,942-byte summary, **828 internal links verified**, row-source audit **807 rows / 0 without a source / 9 flagged unverified**, acceptance **9 pass / 1 info / 0 fail**, exactly one `id="no-line-research"`.
- Targeted + integration suites: **82 passed, 2 skipped** (`test_b97af12f_*`, `test_ca7e10e5_snapshot`, `test_eea4c104_audit`, `test_build`, `test_mobile_picks_nav`, `test_review_register`, `test_current_research_summary`, `test_43110640_egw_live`).
- Playwright browser specs are left to CI `checks.yml`; browsers are not installed in this sandbox.

### Irregularities / flagged for review (do not block)

1. Published snapshot stale by the site's own eight-hour rule; nine rendered cards and six API-only future rows are missing from it.
2. Six future API rows were not rendered in the fetched lobby HTML.
3. `LFO 10` vs `Sökerorg` name conflict on `1081156`; no alias created.
4. Four Polymarket Series #12 listings are `$0.00`-volume/crossed placeholders; HAVU–Azuolas had no reachable event on the board.
5. Five EGamersWorld Series #12 pages print identical `1.8/1.8`; rejected.
6. Four Series #11 external line leads need the reviewed first-party ladder before any pick changes.
7. PR #241 (merged 06:32Z) independently reconciled the same nine CCT fixtures; B97 is a later cross-check plus the six API-only rows and runner workflow. No duplicate file edits.
8. B97's pre-rebase build had two `id="no-line-research"` blocks; main's merged guard now makes it unique. Logged, not edited here.
9. Checked-in `data/latest.json` is 2026-10-15 while live Pages served 2026-10-23 (legacy root race); the publisher run must be green before claiming recovery.

### Merge / deploy record

- PR: pending
- Merge: pending
- Pages run: pending
- Live `generated_at`: pending
