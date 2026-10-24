# Session arena-5260ef4e — why the four-hour refresh stopped publishing, and what was verified live

Observed **2026-10-24T06:20Z–07:30Z**. Every statement below is either a repository fact
(file and line named) or a first-hand read of the linked official page at the stated time.
No probability, pick or alias value was written by hand in this session.

## 1. Published state at claim time

| Check | Value | Source |
| --- | --- | --- |
| Published snapshot the live site serves | `generated_at 2026-10-23T20:10:00Z` (19 active, 17 picks, 2 unresolved) | <https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json> and the root `snapshot.json` in commit `2f966a9` |
| Last successful `pages.yml` publish | run [40015434337](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40015434337), 2026-10-23T19:57Z, head `205ebc0` | Actions API |
| Runs after it | [40028653350](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40028653350) 21:41Z, [40037957529](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40037957529) 23:08Z, [40048429858](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40048429858) 01:08Z, [40063011446](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40063011446) 04:36Z — **all failed at `Regression tests (repository fixtures, before any cache restore)`** | Actions API, job 120780438497 |
| Post-merge run | [40069088115](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40069088115), head `bdb4fc9`, queued 06:09Z, started ~06:45Z | Actions API |

At 07:15Z the live page still carried the 20:10Z snapshot, i.e. **~11 hours** behind — outside the
project's own 4 h refresh / 8 h staleness bound. The page said so itself ("Snapshot needs attention …
older than eight hours"), which is the site behaving correctly and the pipeline being broken.

## 2. Root cause, read line by line

`scripts/originate.py` (state at `bdb4fc9`) referenced a module it never imported:

```
$ .venv/bin/python -m pyflakes scripts/originate.py
scripts/originate.py:1044:21: undefined name 'egw_live'
scripts/originate.py:1046:47: undefined name 'egw_live'
scripts/originate.py:1046:67: undefined name 'egw_live'
scripts/originate.py:1047:23: undefined name 'egw_live'
scripts/originate.py:1049:25: undefined name 'egw_live'
scripts/originate.py:1051:20: undefined name 'egw_live'
```

Line 1044 is `(evidence_dir / egw_live.EVIDENCE_NAME).unlink(missing_ok=True)` and it sits **before**
the `try:` that was meant to make the capture non-fatal. So `live_collect()` raised
`NameError: name 'egw_live' is not defined` on every live refresh. Three test modules failed on the
same name — the exact failure the scheduled regression step reported:

```
$ .venv/bin/python -m unittest discover -s tests -v      # before the fix
ERROR: test_live_collect_deduplicates_duplicate_polymarket_game_ids (test_f9d0a5a2...)
ERROR: test_a_map_moneyline_is_not_a_series_moneyline (test_origination_upgrade...)
ERROR: test_duplicate_full_series_markets_stay_ambiguous (test_origination_upgrade...)
ERROR: test_featured_money_line_does_not_get_researched_or_overwritten (test_origination_upgrade...)
ERROR: test_model_only_rows_get_fresh_alias_aware_market_books (test_origination_upgrade...)
ERROR: test_previously_unresolved_rows_still_get_researched (test_origination_upgrade...)
ERROR: test_zero_size_levels_cannot_become_an_executable_quote (test_origination_upgrade...)
ERROR: test_alias_aware_live_collection_fetches_tag_only_original_event_and_both_books (test_source_integrity...) x2
Ran 9 FAIL/ERROR; the module `egw_live` was introduced by PR #240 (session arena-43110640)
```

### Second defect: the automation was write-only

`scripts/egw_live.py::load_live()` had **no caller anywhere in the repository**, and
`scripts/reference_odds.py::load()` reads only the three reviewed manual captures
(`research/57b1ee04`, `b30bf88b`, `a34bc06b`). The file every live refresh writes —
`data/origination/evidence/live-egw-reference.json` — was therefore never replayed, so the
"automated EGamersWorld rung" could not price a single fixture.

Fix (both in `scripts/originate.py`):

1. `from scripts import egw_live` (with the other `from scripts import …` lines).
2. `egw_live_rows = egw_live.load_live(evidence_dir)` appended **after** the reviewed manual
   captures, so a hand-checked price outranks an automated one; every row still passes
   `reference_odds.quote()`'s fail-closed gate (fixture id + both names + 60 s start tolerance,
   8 h freshness, no-vig margin band, identical 1.8/1.8 placeholders refused).
3. Observability: `collection.egw_live`, `collection.egw_live_error` and a top-level
   `egw_live_replay.entries` count, so a silent regression is visible in the published JSON.


### 2b. Independent convergence (recorded, not hidden)

While this session was verifying the fix, sessions `dd433e7f` (PR #252, commit `40d1c7b`) and
`da8067f5` (PR #257) found the same two defects and merged equivalent fixes to `main` at
~07:00Z–07:20Z. This session rebased onto `1e1da8a` and contributes only what `main` does not have:

* **ordering** — `main` places the automated rows *before* the reviewed manual captures, so an
  automated EGamersWorld row can win the ladder over a hand-checked one. Here the manual captures
  stay first and the automated capture is appended;
* **observability** — `collection.egw_live`, `collection.egw_live_error` and a top-level
  `egw_live_replay.entries` count are published in `data/origination.json`, so a future silent
  regression (a capture nobody replays) is visible in the deployed file;
* **end-to-end replay tests** — `tests/test_5260ef4e_egw_wiring.py` drives the replay through
  `originate.resolve_match`: a real pair prices 38.8/61.2, and placeholders (1.8/1.8), a 12-hour-old
  capture and a start-time mismatch each price nothing.

## 3. Live verification of published rows (first-hand, 2026-10-24)

| Row | Published on our site | What the official source says now | Verdict |
| --- | --- | --- | --- |
| Tesla Cup · Alliance vs FaZe (Hotspawn `1082898`, 27 Oct 12:00Z) | Pick **FaZe** 65.0% / Alliance 35.0%, "Market line, observed 32–38¢ / 62–68¢" | Polymarket series moneyline reads `all 38¢`, `faze 68¢`; header bars 38% / 68% — <https://polymarket.com/event/cs2-all-faze-2026-10-27> | consistent with bid/ask midpoints (35 = (32+38)/2, 65 = (62+68)/2); the market page is the cited source, no Hotspawn input |
| NODWIN Clutch Series 13 · Acend vs UNiTY (Hotspawn `1082996`, 25 Oct 05:00Z by HLTV's clock) | Pick **Acend** 54.2% / UNiTY 45.8%, labelled *Valve-rating research estimate* | HLTV <https://www.hltv.org/matches/2399112/acend-vs-unity-nodwin-clutch-series-13>: **Best of 3 (Online), Round of 16**, Acend HLTV **#131** / VRS **#75**; Betting panel shows only a Stake promo — **no bookmaker odds**; community vote 16.7% Acend / 83.3% UNiTY | fixture identity and format confirmed; the "no line" label is accurate; the pick stays a labelled model estimate. HLTV community votes are **not** a price and are not used (they point the other way — an inversion already on `/review/` as `2016c841-acend-unity-lean`) |

## 4. Local gate results after the fix

* `python -m unittest discover -s tests -v` → **OK, 0 failures** (the nine errors above disappear).
* `python -m scripts.build` → replay 80 rows PASS, row-source audit **790 rows / 771 official links / 9 flagged unverified / 0 without a source**, acceptance **9 pass · 1 info · 0 fail**, **826 internal links OK**.
* `python -m scripts.audit_rows --site site --strict` → **0 violations**.
* Built executive summary (`site/index.html`): `id="start-here"` quick links to `./#picks-at-a-glance`, `./origination/#picks`, `./origination/#unresolved`, `./#unresolved-register`, `./unresolved/` all present, plus `id="unresolved-register"` and `id="no-line-research"` sections; viewport meta present.

## 5. Limitations recorded by this session

* This sandbox has no egress to Hotspawn, HLTV, Polymarket or GitHub Pages; those reads used the
  platform's browser-side fetch, and the runner's own collection is the production path. Nothing
  here substitutes for the runner's dated capture.
* The scheduled publishers were queued/stalled during this window (GitHub-side runner starvation
  across many parallel session branches, reported independently by sessions b72154e1 and
  2ed65c56). A green code fix cannot publish if no runner starts; the deploy is confirmed below
  only once a run actually completes.

## 6. Addendum 08:35Z — the recovery gate, not only the code

The only publisher that *completed* between 06:09Z and 08:35Z was run
[40077233256](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40077233256) (head `9628581`,
merge subject `recovery: …`). It failed in `republish-last-verified` at
*Retire only publishers predating independently replayable sources* with
`Recovery queue safety not established: Obsolete publisher has not stopped; recovery cannot publish`
(job 120823116413), so `verify-and-deploy` was skipped by the workflow's own guard
(`needs['republish-last-verified'].outputs.queue_safe == 'true'`). The gate is
`scripts/be019782_release.py`: it cancels main-branch pages runs whose commit is behind `CORE_COMMIT`
and then waits 90 s for them to reach `completed`.

Ordinary push publishers target `ubuntu-24.04`; the recovery/catch-up path targets `macos-14`.
At 08:40Z the repository showed **3 queued / 2 pending / 0 in progress** main publishers, so a recovery
retry is legitimate rather than a shortcut: it reuses the project's own guarded path and every gate
(regression tests, replay, row-source audit, live verification) still runs before anything deploys.
