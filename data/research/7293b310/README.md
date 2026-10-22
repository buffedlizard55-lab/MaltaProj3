# Session arena-7293b310 — a live site, one obvious pick route, one honest unresolved register

Read this with `COORDINATION.md` (the claim and the result block) and the machine records in this
folder. Nothing here writes a probability, a pick or an alias: every published value comes from
`scripts/collect.py` / `scripts/originate.py` running against a live source on a GitHub runner, and
every row keeps the URL of the source that produced it.

## What was wrong when this session started (08:55Z)

| Observation | Evidence |
| --- | --- |
| The public site served the checked-in branch root, whose `data/latest.json` was `generated_at 2026-10-15T08:36:13Z` — seventeen fixtures that had already started, every one marked "Locked". | `data/latest.json` on `main` at `1cab862`; the same file is what `scripts/root_publish.py` compares against. |
| The four-hour publisher had not completed since 07:46Z: run `39744284108` was queued from 07:58Z and run `39748055891` was pending from 08:29Z. | `gh run list --workflow pages.yml`. |
| One test failed on `main` (`tests/test_review_flags.py::…test_render_only_findings_do_not_rewrite_the_canonical_json`) because the published copy of `latest.json` was rewritten with reconciliation keys. | Full local suite: 924 tests, 1 failure. Fixed on `main` by PR #181 (session `df80ab9f`) before this branch merged; this branch now carries that fix. |
| The executive summary interleaved the current picks with the 18 October final-day blocks, the dated contrarian review, a second copy of the unresolved table and the featured-method metric cards — on a phone that put "Next matches" four screens down and made two different "unresolved" lists look like one contradictory list. | Rendered `/tmp/site/index.html` heading order at 09:00Z. |

## What this session changed

1. **`scripts/build.py` — the first block answers the phone's first question.** The executive-summary
   banner now opens with `Updated <observation time> · N fixtures · N with a pick · N unresolved`
   (`data-banner-status`). Every number is copied from the published snapshot; the block carries no
   probability and no team name (pinned by `tests/test_7293b310.py::BannerStatus`).
2. **One labelled archive instead of history in the middle.** The 18 October blocks, the dated 9z–Aurora
   review, the featured-method metric cards and the researched-fallback note are still published in full,
   with every source link, inside `<details class="archive-fold" id="archive">` after the current content.
   `assets/scout.js` opens the fold when a hash points inside it, so `#contrarian` and `#upset-watchlist`
   still land on visible content.
3. **No duplicate unresolved list.** `#unresolved-register` (the researched register, every blank with the
   sources tried) stays at the top; `#unresolved` now renders the featured exact-name method's own
   rejection record, which is a different list, and says so. Pinned by
   `tests/test_7293b310.py::SingleUnresolvedRegister`.
4. **Two dated reviews no longer share a near-identical heading.** "Contrarian, not careless" is now
   "Day-one upset review: 9z–Aurora"; "Contrarian, not reckless" is now "Market-backed upset watchlist".
5. **`scripts/verify_7293b310.py` — the line-by-line audit.** For every active fixture it prints the
   fixture id and Hotspawn permalink, both teams, the kick-off, the pick, both published probabilities,
   the method and the source URL, then fails on: a missing permalink, a missing estimate, a non-two-way
   or non-normalised probability, a missing side, a source that is not an https allow-listed official
   host, or a probability at exactly 0/1. It reproduces the published `origination.json` counts rather
   than inventing its own (`tests/test_7293b310.py::PublicationAudit`).
6. **`tests/test_review_flags.py`** — kept at `main`'s version after the rebase, because session
   `df80ab9f` fixed the underlying rewrite on `main` (the published copy is byte-identical again and the
   reconciliation is published separately as `data/reconciled-counts.json`).

## Live refresh mechanics

`.github/workflows/7293b310-live.yml` (session-only, removed before this branch is merged) runs
`collect` → `originate --live` → `validate` → `build --output site` → `root_publish` on this branch's
runner, then commits the refreshed `data/` and the published root with `[skip ci]`.

The artifact download host is blocked from the coding sandbox, so a failing build also commits the exact
snapshot it was given plus the tail of its log under `data/research/7293b310/live/` for local replay.
That capture is how the first live failure was identified:

> `AssertionError: Fallback pick differs from its probabilities` — raised by
> `scripts/build_origination.validate_origination` for an exactly 50/50 research-model row whose side was
> set by the published-rank tie-break (session `4c972a51`). Session `df80ab9f` fixed the same replay on
> `main` (PR #170, commit `1c1d87b`); this branch now carries that fix instead of a duplicate.

## What is *not* claimed here

* No value in the committed snapshot is hand-written; the numbers are whatever the runner's collectors
  produced, and every row keeps its source link.
* A source that refuses the runner is never treated as proof that no market exists; the refusal is
  published with its status code on `/unresolved/`.
* The site is read-only analysis: it places no bets and submits no picks to Hotspawn.

## Live result — 2026-10-22T09:43Z

`.github/workflows/7293b310-live.yml` completed the full pipeline on the runner and committed the
refreshed snapshot (`bac5d16`):

| Field | Published value |
| --- | --- |
| Hotspawn inventory | 104 records — `{"records": 104, "crosscheck": "complete", "verified_pages": ["lobby", "cs2"]}` |
| Inventory observed | `2026-10-22T09:42:38Z` |
| Featured snapshot | `2026-10-22T09:43:01Z`, `run_status` `partial-picks` |
| Active fixtures / archived | 43 / 61 |
| Featured method | 18 market · 3 bookmaker · 12 model → 33 picks, 10 rejected |
| Complete researched list | **43 of 43 with a pick, 0 unresolved** — 18 market · 5 bookmaker · 2 consensus · 18 model (2 network) · 4 alias-joined |
| Live collection | `true` |

`scripts/verify_7293b310.py` re-reads that snapshot row by row (`verification.md` / `verification.json`
here): **43 active fixtures, 43 two-way estimates, 43 directional picks, 0 rows with a rule problem**,
and every published probability carries an https source on an allow-listed official/primary host.

The site build over the same data: `104 source rows reconciled`, `838 rows / 819 with an official link /
9 flagged unverified / 0 without a source`, `1070 internal links/assets/anchors`, 9 views. Full local
suite: **948 tests, 0 failures, 13 skips** (12 describe the 15 October PARIVISION–BetBoom fixture that
this tournament-complete snapshot no longer lists; 1 is the contrarian watch, which has no current
fixture to watch). Every skip is a snapshot precondition, not a suppressed failure, and each one states
its reason in the test output.

### Integration defects this live run exposed (fixed here)

1. **`coverage_audit` / `verify_live` rejected a documented tie-break.** The public coverage audit
   asserted that an exactly even estimate must never name a pick. Session `4c972a51` deliberately lets
   an even *research model* take a direction from the provider's published order. On this snapshot
   fixture `1082926` (Isurus vs Hacha, HLTV publishes identical points) is exactly 50/50 with that
   documented rule, so the site's own post-deploy verifier failed. `documented_tie_break()` now accepts
   the side only with the rule name, the matching winner, two different positive ranks, `method=model`
   and an https source — and rejects everything else.
2. **The market filter tab and the row attribute disagreed.** The tab counted `reference` rows as
   market-backed while the row filter and `tests/test_build.py` did not; with two `consensus` rows in
   this snapshot the tab said 25 and the table showed 23. The tab, the row attribute and the phone
   filter now share one definition (`MONEY_METHODS`), and a `consensus` row's evidence link is labelled
   "Consensus" rather than "Bookmaker".
3. **Two snapshot-bound tests were re-pinned to invariants rather than to 15 October values.** The
   contrarian watch test now checks the underdog/override rules when a watch exists and the honest
   "no current exact-pair watch" state when none does; the origination-upgrade end-to-end fixtures skip
   with a stated reason when the historical fixture is no longer listed. Nothing was silently deleted.
