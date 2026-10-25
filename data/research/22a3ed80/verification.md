# Session arena-22a3ed80 — published-state verification (2026-10-25)

**Snapshot verified:** `2026-10-25T16:20:19Z` — 14 active Hotspawn CS2 fixtures, 13 with a priced pick and **1 published as explicitly unresolved** (1086697 Projeto do KinGui vs Yawara). The earlier `14:32:11Z` publish was also verified (16 active, 16 priced) and the defect below was found there.
**Page verified:** `index.html` (executive summary) + `snapshot.json`, both from the same publish.
**Command:** `python -m scripts.22a3ed80_verify --site . --check`
**Result:** 15 hard checks, 0 failures, 14 rows checked, 14 of 14 rows link an official source.
Machine-readable copy: `data/research/22a3ed80/verification.json`.

## What was checked, line by line

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | The page's `data-snapshot-generated` stamp equals `snapshot.json.generated_at` | pass — both `2026-10-25T16:20:19Z` | `index.html`, `snapshot.json` |
| 2 | One picks-at-a-glance row per active fixture, no extra and none missing | pass — 14 upcoming, 14 rows | `#glance-list` |
| 3 | Every rendered row carries at least one `https://` source link | pass — 14 of 14 | per-row link list in `verification.json` |
| 4 | Every featured pick and both percentages re-derived from the fixture's own `analysis` block | pass — 12 featured rows, 0 mismatches | `snapshot.json` → `analysis.probabilities` + `pick_index` |
| 5 | Every non-featured row is either a labelled researched fallback with a usable probability or an explicitly unresolved row with its reason linked | pass — 1 labelled fallback (`1082792` HOTU 84.0%) and 1 unresolved row (`1086697`, "No validated two-team estimate", reason link present) | row badges / `#unresolved` |
| 6 | Headline sentence reconciles with the snapshot's own counts and the rows' declared methods | pass — active 14, picked 13, external 11, research model 2, unresolved 1 | `snapshot.counts` / rendered rows |
| 7 | Phone status matches the snapshot | pass — "13 picks ready of 14 · 1 unresolved" | `.mobile-status` |
| 8 | In-site picks routes resolve and contain their anchors | pass — `origination/#picks`, `origination/#unresolved`, `unresolved/` | rendered files |
| 9 | The summary links the dedicated registers | pass — `#picks-at-a-glance`, `#unresolved-register`, `#no-line-register`, `#fallback-register` | `index.html` |

Featured rows re-derived, with the arithmetic shown:

- 10 market rows: published pick = `teams[pick_index]`, published percentages = `round(p×100, 1)` for both sides (for example `1079199` Infinite vs BRUTE, `0.445 / 0.555`, `pick_index 1` → **BRUTE 55.5% · Infinite 44.5%**).
- 1 bookmaker row: same identity and rounding rule from a two-way no-vig pair.
- 2 model rows inside the featured set: identity and rounding rule still replay exactly; the model coefficients themselves are replayed by the model's own dossier, not here.

Non-featured rows (not re-derived here; each keeps its own dossier and blocker):

| Fixture | Published | Probabilities | Method | Why |
| --- | --- | --- | --- | --- |
| HOTU vs The Huns (`1082792`) | HOTU | 84.0% / 16.0% | labelled researched fallback (`bo3.gg` results-network model) | no two-sided external price above the spread ceiling |
| Projeto do KinGui vs Yawara (`1086697`) | **Unresolved** | blank | none — explicitly unresolved | HLTV 403 to the runner, and no alias-verified Polymarket / Kalshi / Smarkets / Thunderpick line for these teams and start time; the earlier consensus capture aged past the 8-hour window |

## Defect found and repaired

The `2026-10-25T14:23:33Z` build rendered **"Live Hotspawn fixtures missing from this snapshot — 9 missing at that observation"** and listed nine cards whose notes in the very same record read *"Carried in the published complete picks list (…); crowd picks excluded"*.
`data/research/c2a74e33/live-coverage.json` marks **all 22** compared cards `in_published_snapshot: true`, so none of them was ever a coverage gap; they had left the snapshot only because they started.

`scripts/build.py::live_coverage_gaps` now drops any card the record marks as carried from the missing count and names those cards separately, with their own Hotspawn links, under `#live-coverage-rotated` — "not counted above … never a coverage gap". Cards with no published row are still counted and listed exactly as before.

Pinned by:

- `tests/test_22a3ed80_coverage_register.py` — 11 tests (shipped record, carried-and-rotated, genuinely missing, mixed, already-in-snapshot, phone banner).
- `tests/test_22a3ed80_verification.py` — 6 tests (hard checks, row coverage, source links, re-derivation, phone status, no carried card rendered as missing).

Neither module pins a fixture id, team name, probability or timestamp belonging to a mutable snapshot, so the four-hour publish cannot fail them the way the dated dossier test froze the publisher earlier today.

## Build and repository checks run on this branch

- `python -m unittest discover -s tests` — **OK** (1,815 tests, 16 skipped) after these edits.
- `python -m scripts.build --data data --output <build>` — 9 pages, **80 source rows reconciled**, every published probability and pick replayed.
- `python -m scripts.audit_rows --site <build> --strict` — 971 rows, **0 without a source**, 0 violations on every page.
- `python -m scripts.acceptance_audit` — **9 pass / 1 info / 0 fail**.
- Link/asset/anchor audit — **865 internal links and anchors pass**, project-subpath routing and mobile landmarks included.

## Live coverage at the verified publication

13 of 14 active fixtures carry a priced pick. **`1086697` Projeto do KinGui vs Yawara carries none**, and the page states why per source: HLTV answered `403` to the runner, and no alias-verified Polymarket, Kalshi, Smarkets or Thunderpick match-winner line exists for that pair and start time. Two things would close it, and neither may be invented: an official page proving `Projeto do KinGui` (Hotspawn) and `Tropa do KinGui` (HLTV) are the same organisation, which would let the ranking rung price it, or a fresh two-sided prematch book quote. Both are logged for review.

## Limitations of this session (published, not hidden)

1. **No live reachability from this sandbox.** `play.hotspawn.com`, `www.hltv.org`, the Hotspawn fixtures API, Polymarket and the public Pages host all fail before any HTTP response here, so freshness is evidenced by the publisher run that produced the snapshot, not by a first-hand read. Repository-side probes that need those hosts run in GitHub Actions.
2. **Scheduled publisher reliability.** Six scheduled runs failed between 2026-10-24T17:36Z and 2026-10-25T13:11Z, all at the same regression step (`test_group_a_are_snapshot_unresolved`), which froze the published site. PR #326 guarded that block; the 14:23:33Z snapshot is the first fresh publish since, so the next scheduled slot should be read on its run page.
3. **Legacy branch-root mode.** The tracked replay fixtures under `data/` are still dated 2026-10-15; the current observation is served from `snapshot.json` (and from the freshly built tree on the artifact path). This is documented in `scripts/root_publish.py` and is a platform limitation, not a data error.

All of the above is published on **Flagged for Review** through `data/research/22a3ed80/repo-review.json`.
