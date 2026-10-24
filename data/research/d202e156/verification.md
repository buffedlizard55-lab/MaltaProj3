# Session arena-d202e156 — verification record

**Branch:** `arena/d202e156-maltaproj3` · **Head verified:** `621d56f2` (`origin/main` when this record was finalised; the `egw_live` import fix, the `pytest` declaration and the unittest conversion all landed on `main` during this session) · **Recorded:** 2026-10-24T07:35Z

## Scope, and why it changed

This session claimed the `NameError: name 'egw_live' is not defined` regression that
had failed every scheduled `pages.yml` refresh. While reproducing it, session
**arena-5260ef4e** landed the identical fix on `main` as PR #261 (commit `292ea222`),
and session **arena-a5b59ee6** published the deeper follow-up (the live EGamersWorld
capture was written but never read) as PR #260. Rather than duplicate either, this
session re-scoped to what was still missing: a **repo-wide static guard** for the
class of defect, a **rendered-output contract test** for the three brief lines the
reviewer named, and a **line-by-line verification dossier** of the published site.
Nothing here writes a probability, a pick, an alias or a source.

## Line-by-line verification

| # | Checked | Result | How |
| --- | --- | --- | --- |
| D20-1 | The `egw_live` NameError that failed every scheduled refresh is fixed on `main` | **pass** | `scripts/originate.py:37` now reads `from scripts import egw_live`; `import scripts.originate` succeeds; `test_origination_upgrade`, `test_source_integrity`, `test_f9d0a5a2` pass (81 tests) where 9 tests previously raised `NameError` |
| D20-2 | No `scripts/*.py` module references a sibling module it never imports | **pass** | AST scan of all 64 identifier-named modules: every loaded `Name` matching a sibling module is bound by an import, a local `def`/`class`/assignment or a parameter. Zero findings; the `egw_live` occurrence on `bdb4fc9` was the only one |
| D20-2b | Every third-party import the suite makes is installed by `requirements.txt`, and every test module is collectable by the runner CI uses | **fail on `main` at `06f56c2b`, fixed on `main` by `0427b814` + `6c051a73`, pinned here** | PR #267 (commit `d29a5602`) added `tests/test_b97af12f_reconciliation.py` with a module-level `import pytest`, never declared in `requirements.txt`. `python -m unittest discover -s tests` then reported `ERROR: test_b97af12f_reconciliation (ImportError: No module named 'pytest')` and exited non-zero, so `pages.yml`'s regression step went red **and the four-hour refresh died a second time**, one commit after the `egw_live` NameError was fixed. The module was also pytest-style, so unittest collected **zero** of its six checks. Reproduced locally on a clean worktree of `origin/main`: *"Ran 1419 tests … FAILED (errors=1)"*. Both halves are fixed on `main`: `0427b814` declared the dependency and `6c051a73` (owner arena-b97af12f) converted the module to `unittest.TestCase`. This session pins the contract with `tests/test_d202e156_declared_imports.py` |
| D20-3 | The build replays every published probability and pick from first-party evidence | **pass** | `python -m scripts.build` → *"PASS: 80 source rows reconciled; every published probability and pick replayed from first-party evidence."* |
| D20-4 | Every rendered table row links an official/primary source or is flagged unverified | **pass** | `site/data/row-source-audit.json`: **826 rows, 807 ok, 9 flagged, 10 navigation, 0 violation**. The 9 flagged rows sit on `final-day/index.html` (5) and `review/index.html` (4) |
| D20-5 | The executive summary links, in-site, to where the updated picks are | **pass** | `#start-here` carries five in-site links, all resolving: `./#picks-at-a-glance`, `./origination/#picks`, `./strategy/`, `./origination/#unresolved`, `./#unresolved-register`. Every internal `<a>` on all 11 built pages resolves to an existing page and anchor |
| D20-6 | A separate unresolved-picks-and-limitations section sits inside the executive summary | **pass** | `#unresolved-register` + `#unresolved-register-title` (*"Unresolved picks & limitations"*), plus the separate `#no-line-register` (*"Picks without a betting line · limitations"*) with one card per model-only fixture, each stating *"No betting line"* and linking a source; a dedicated `/unresolved/` page also exists |
| D20-7 | The site is phone-ready | **pass, one recorded exception** | All 11 pages declare a device-width viewport; `assets/scout.css` collapses `.matches-table` to block cards at ≤850 px, shows `.mobile-status` only at ≤700 px, sets 44 px minimum tap targets and `overflow-wrap:anywhere`, and fixes `.mobile-nav` to the bottom; no element declares a width above 320 px. Exception: the phone status strip is absent on `/origination/` and `/strategy/` |
| D20-8 | Every active fixture appears on the summary with both probabilities and a source | **pass** | For each non-past match in `site/snapshot.json` a `.glance-row` was located containing both team names; each renders ≥2 percentages and ≥1 external source link (17 rows on the CI replay fixture) |
| D20-9 | The live published site covers every active Hotspawn CS2 fixture | **pass** | Live executive summary (snapshot `2026-10-23T20:10:00Z`): **19 active, 19 with a directional pick — 12 from an external betting line, 7 from a research model — 0 explicitly unresolved**; all 19 rows list both percentages, the pick, the observed price and a source |
| D20-10 | The refresh schedule stays inside the brief's 4–8 hour window | **pass (code), fail (execution)** | Two cron entries (`17 */4 * * *`, `47 2-22/4 * * *`; largest gap 2.5 h), `refresh_interval_hours: 4`, `stale_after_hours: 8`; acceptance-audit check 6 passes. Execution is starved by parallel push runs |
| D20-11 | Hotspawn "% picked" and HLTV fan votes are never used as probabilities | **pass** | Every probability row is badged *Market line*, *Bookmaker* or *Model/Researched* and links Polymarket, Thunderpick, the Valve official standings or bo3.gg; no row cites a crowd percentage or an HLTV vote |
| D20-12 | No value was inferred from a page that could not be opened | **pass** | This session wrote no probability, pick, alias or source |

## What changed in the tree

| File | Change |
| --- | --- |
| `tests/test_d202e156_module_wiring.py` (new) | AST guard: no module may reference a sibling module it does not import; every `scripts/*.py` imports cleanly; `originate.egw_live` is wired and carries `EVIDENCE_NAME`/`INDEX_URL`/`INDEX_EVIDENCE`/`entries_for` |
| `tests/test_d202e156_brief_contract.py` (new) | 14 tests pinning the executive-summary links, the in-summary unresolved register, the phone contract and the per-fixture pick coverage on the **built** site |
| `data/research/d202e156/verification.json`, `verification.md` (new) | This record |
| `data/research/d202e156/flags.json` (new) | Five findings published on Flagged for Review |
| `requirements.txt` | Keeps `pytest==8.4.2` and `pyflakes==4.0.3` (both already on `main`) with a comment recording why `pytest` is declared: CI installs exactly this file before running `unittest discover` |
| `COORDINATION.md` | Claim, re-scope, results and cross-session requests |

## Irregularities (published on Flagged for Review, not blocking)

1. **`d202e156-phone-status-strip-missing-on-two-views`** *(needs review)* — `scripts/build.py::shell()` renders the phone status strip on every page it builds, but `scripts/build_origination.py` and `scripts/build_strategy.py` overwrite `/origination/index.html` and `/strategy/index.html` with shells that do not carry it. A phone reader on the complete picks list or the leaderboard plan loses the one-tap route back to the picks and the unresolved register. Verified by reading the built HTML: 9 of 11 pages contain exactly one `nav.mobile-status`, those two contain none. A fix is **requested in COORDINATION.md rather than applied**, because `scripts/build_origination.py` is touched by open PRs #245 and #238.
2. **`d202e156-four-hour-publisher-starved-by-parallel-push-runs`** *(needs review)* — the regression is fixed on `main`, but between 07:08Z and 07:31Z on 2026-10-24 seven push-triggered `pages.yml` runs were each cancelled while queued behind the next session's push, and no scheduled run has completed. The live site still serves the `2026-10-23T20:10:00Z` snapshot and shows its own stale warning. Coordination load, not a data defect.
3. **`d202e156-no-general-egress-in-this-sandbox`** *(platform limitation)* — Hotspawn, HLTV, Polymarket, EGamersWorld, Thunderpick, Pinnacle and the published Pages host all refuse TLS from this sandbox, and `npx playwright install chromium` cannot download Chrome for Testing. No live collection, no live lobby read and no local browser run were possible; every value verified here came from the repository's own replay fixture, the build it produces, or pages read through the platform fetcher.
4. **`d202e156-pytest-only-test-module-never-runs-in-ci`** *(fixed)* — PR #267 added `tests/test_b97af12f_reconciliation.py` as six pytest-style `def test_*` functions, one taking the `tmp_path` fixture. `unittest discover`, which both workflows run, does not collect plain functions, so none of the six checks ever executed in CI, and the same module's undeclared `import pytest` turned the regression step red. Fixed on `main` by `0427b814` (declared the dependency) and `6c051a73` (owner arena-b97af12f converted the module to `unittest.TestCase`, so its six checks now run). This session pins both halves so neither can regress.
5. **`d202e156-live-lobby-cards-not-in-the-published-snapshot`** *(notice)* — the dated 2026-10-23T14:17Z lobby check found 8 live cards outside that snapshot (1081606, 1082980, 1083014, 1082924, 1081150, 1079657, 1082693, 1082925). The rendered page now labels each *"In the published snapshot"*, so the gap was closed by a later collect; the count is a dated observation, not a live claim.

## Cross-session requests (logged, not edited)

| Request | File | Owner |
| --- | --- | --- |
| Add the `nav.mobile-status` strip (or an equivalent one-tap picks/unresolved jump) to the `/origination/` and `/strategy/` shells so the phone route exists on the pages a reader is most likely to open | `scripts/build_origination.py`, `scripts/build_strategy.py` | open PRs #245 and #238 |

## Verification commands

```bash
python3 -m unittest tests.test_d202e156_module_wiring tests.test_d202e156_brief_contract
python3 -m scripts.build
python3 -m scripts.acceptance_audit --site site     # 9 pass / 1 info / 0 fail
python3 -m unittest discover -s tests               # full suite
```

| Add the `nav.mobile-status` strip to the `/origination/` and `/strategy/` shells | `scripts/build_origination.py`, `scripts/build_strategy.py` | open PRs #245 and #238 |
