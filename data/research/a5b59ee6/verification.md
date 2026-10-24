# Session arena-a5b59ee6 — verification record (2026-10-24)

Branch `arena/a5b59ee6-maltaproj3`, based on `main` `bdb4fc92a30989e93263d7ef3842cda045fe6571`
(PR #240 merge). Read the board first; the 13 open pull requests listed at claim time
touch `scripts/build.py`, `assets/*`, `data/research/<other session id>/**` and
`tests/browser/*` — none of them touches a file claimed here.

## What was wrong (both defects reproduced, neither inferred)

1. **The module was never imported.** `scripts/originate.py` called
   `egw_live.INDEX_URL`, `egw_live.EVIDENCE_NAME` and `egw_live.entries_for(...)`
   without importing `egw_live`.
   * Reproduced on `bdb4fc9` with the repository's own suite:
     `python -m unittest discover -s tests` errors in `tests/test_f9d0a5a2`,
     `tests/test_origination_upgrade` and `tests/test_source_integrity` with
     `NameError: name 'egw_live' is not defined`.
   * That is job step 5 of `.github/workflows/pages.yml`
     (`Regression tests (repository fixtures, before any cache restore)`), so every
     step after it — collect, build, deploy, verify — is skipped.
   * Source: <https://github.com/buffedlizard55-lab/MaltaProj3/blob/bdb4fc92a30989e93263d7ef3842cda045fe6571/scripts/originate.py>,
     workflow: <https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/pages.yml>.

2. **The capture had no consumer.** `egw_live.load_live` had no caller.
   `live_collect` writes `data/origination/evidence/live-egw-reference.json`;
   `originate.run` builds the reference rung from `reference_odds.load()`, whose
   `CAPTURE_PATHS` was a fixed three-item allowlist of hand-reviewed captures.
   Reproduced by replaying the ladder with the import fixed and the pool unchanged:
   `method None`, `pick_index None` for a fixture whose saved EGW anchor prices it.

## What this branch finally contains, and why it is small

Both defects were fixed on `main` by other sessions while this one was
reproducing them: PR #261 wired `egw_live.load_live` into the rung, PR #270 added
the strict evidence chain (source clock, exact named price, original HTML and
manifest must agree) and reproducibility-based replay selection in
`validate_origination`, and the import landed three times (#261, #270, `6cb7dbe`).
When this branch was rebased, its own versions of those two fixes were dropped in
favour of the stricter merged ones — keeping a second, weaker implementation
would have been worse than landing nothing.

What remains, and is not a duplicate of any merged work:

| File | Change |
| --- | --- |
| `tests/test_a5b59ee6_publisher_wiring.py` | new: integration cover for the merged rung (10 tests) |
| `requirements.txt` | `pyflakes==4.0.3` so the static undefined-name guard runs in CI instead of skipping |
| `data/research/a5b59ee6/**` | this record, the reproduction, and the five published findings |
| `COORDINATION.md` | this session's claim, results and the merge-resolution note |

Nothing in the ladder order, the provider label, the 1.8/1.8 placeholder rule, the
eight-hour freshness rule, the exact-start rule, the excerpt SHA-256 check or any
published probability was altered by hand.

## How it was verified

* `tests/test_a5b59ee6_publisher_wiring.py` — **10 tests, all pass** against the
  merged implementation: the rung is imported; `live_collect` reaches it under
  the real collector and writes the original HTML, the derived capture and the
  manifest; that chain replays to 26.5 % / 73.5 %; a missing original response, a
  failed or restamped manifest and a capture edited after the fact each price
  nothing; `originate.run()` publishes Off Chops 73.5 % from the chain and leaves
  the same fixture blank without it; a fresh reviewed capture outranks the
  automated row; `pyflakes` finds no undefined name in `scripts/`.
* The three modules that were red on `main` pass (81 tests).
* `python -m scripts.build` on the checked-in data: **PASS** — 80 source rows
  reconciled and replayed, row-source audit 775 rows / 0 without a source / 9
  flagged unverified, acceptance audit 9 pass / 1 info / 0 fail, 829 internal
  links and anchors OK.
* Executive summary contract re-checked in the built HTML: "Start here · where the
  picks are", `./origination/#picks`, `./unresolved/`, `id="picks-at-a-glance"`,
  the H2 "Unresolved picks & limitations" and
  `aria-labelledby="unresolved-register-title"` are all present; the unresolved
  page builds at 111,861 bytes. `/review/` renders the five new findings.
* Browser specs were **not** run here: Playwright browsers cannot be installed in
  this sandbox (egress). CI's `Validate dashboard` job runs them at 320/390/768/1440.

## Limitations stated plainly

* This sandbox reaches GitHub, PyPI and npm only. `play.hotspawn.com`,
  `www.hltv.org`, `egamersworld.com` and the public Pages host all failed at the
  TLS handshake, so this session could not read the live lobby, a live betting
  line or the rendered production page. The fix is proved by replay of saved
  evidence and by workflow results read through the GitHub API.
* The live collection that this session repaired runs on the Actions runner, which
  does reach Hotspawn and EGamersWorld. Its first post-merge result is recorded in
  `COORDINATION.md`.
* No probability, pick or team alias was written by hand.

## Index of the evidence in this directory

* `publisher-stall.json` — the four failing scheduled runs, their failing step,
  the job-step listing, and the last successful run.
* `wiring-reproduction.json` — the before/after ladder replay with the exact
  probabilities and the fail-closed cases proved.
* `flags.json` — the five findings published on `/review/` (three "needs review",
  two "notice").
