# 96F — the published site was serving the 15 October root

Read `pages-root-verification.json` for the machine-readable record (URLs, timestamps, exact values).

## What was wrong

The site's four-hour refresh builds `site/` and publishes it with `actions/deploy-pages`. GitHub
Pages for this repository is configured `build_type: legacy`, `source: main/`, so **every push to
`main` also republishes the checked-in branch root** at the same paths. Whichever publisher lands
last wins.

On 2026-10-22 the legacy build for `2fb99b0` finished at **07:52:31Z**, after the artifact from the
previous run, and the public site reverted to the 15 October dashboard:

| Public URL | What it returned at 08:20Z | Why that proves the root was served |
| --- | --- | --- |
| `/data/latest.json` | `generated_at 2026-10-15T08:36:13Z`, 17 upcoming fixtures, all already started | the tracked root file has exactly that stamp |
| `/data/row-source-audit.json` | `rows 334, ok 326, flagged 0, violation 0` | byte-identical to the tracked file, and only a build writes that file |
| `/` | "17 active fixtures. 12 external-line estimates, 5 research-model estimates" | the checked-in 15 October page says exactly this |

`PUT /repos/.../pages {"build_type": "workflow"}` answers **403 Resource not accessible by
integration**, so the source cannot be switched from a workflow token (same finding as session
`c1fa150f`).

## Second, independent cause: the refresh run never started

GitHub cancels a **pending** run as soon as a newer run enters the same concurrency group (the
`cancel-in-progress` flag only governs the run already in progress). Every session branch that
merged into `main` created a new `pages` run, so the four-hour refresh was cancelled while still
pending — repeatedly:

| Run | Created | Outcome |
| --- | --- | --- |
| [39748026849](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39748026849) | 08:28:46Z | cancelled while pending |
| [39748055891](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39748055891) | 08:29:00Z | cancelled while pending |
| [39750182735](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39750182735) | 08:45:50Z | cancelled while pending |
| [39751657137](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39751657137) | 08:57:20Z | cancelled while pending |

The last successful publish before this session was **05:41Z**. `pages.yml` now uses
`group: pages-${{ github.event_name }}`, so a push can never cancel a scheduled refresh; push runs
still serialise among themselves.

## What this session changed

* `scripts/root_publish.py` — copies the verified build over the root: every rendered page,
  `assets/`, the data files the pages read, the alias registry, the two inventory-evidence files,
  and `.nojekyll` (~2 MB). It **refuses** a stub index, a missing/unparseable snapshot, a snapshot
  older than 12 h, or a snapshot older than the one already published, and it writes only files
  whose bytes changed.
* `.github/workflows/pages.yml` — `contents: write`, a per-event concurrency group (pushes can no
  longer cancel the four-hour refresh while pending), plus one appended step that runs after the
  public site has been verified, commits with `[skip ci]` and retries the push three times against
  a moving `main`.
* `tests/test_96fbe295.py` — 22 tests covering the copy scope, idempotency, drift repair, every
  refusal, the monotonic guard and the workflow wiring.

## What this does **not** do

* It does not remove the legacy publisher (needs repository admin).
* It does not publish `data/research/` (19 MB) or the bulk `data/evidence/` attachments (3 MB) every
  four hours. During a legacy-build window a row's *saved evidence* link can therefore point at an
  older response while the row's numbers are current. The artifact deploy still serves the current
  copies.
* It does not rebuild the 01:37Z snapshot in `data/research/15fc6bca/live/` by hand:
  `validate.py` refuses a snapshot whose `inventory_observed_at` does not match
  `data/evidence/hotspawn-context.json`, and that evidence is written by the collector on the
  runner. The workflow is the only correct builder, so the workflow publishes.

## How it is verified after the merge

1. `gh api repos/buffedlizard55-lab/MaltaProj3/actions/runs?per_page=5` — the `pages.yml` run for the
   merge commit must reach `success`.
2. The run's `verify-and-deploy` job must show the step *Publish the verified build into the branch
   root* green, and its summary must name the number of published files.
3. `GET https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json` must return today's
   `generated_at`, and `GET .../data/row-source-audit.json` must equal the **new** tracked file (proving
   the root, not just the artifact, carries the fresh build).
4. `GET https://buffedlizard55-lab.github.io/MaltaProj3/` must no longer show the
   *"Do not treat these as current picks"* banner, and must list the current fixtures with both
   teams' probabilities.
