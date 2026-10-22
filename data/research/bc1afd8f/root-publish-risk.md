# arena-bc1afd8f — would publishing a fresh snapshot into the branch root break the build?

Observed **2026-10-22T11:27:12Z**. Reproduced in a temporary directory; the
repository's own `data/` tree was not modified and no value was invented.

**Question.** If the verified build were published into the branch root the way scripts/root_publish.py does it (fresh data files, frozen data/evidence), would the repository's own replay validator still accept the tree that checks.yml and pages.yml build from?

## Base tree (what a root-sync commit would be applied to)

- provenance: git HEAD (the committed data/ tree)
- committed `data/latest.json`: `2026-10-15T08:36:13Z`
- committed `data/origination.json`: `2026-10-15T09:31:24Z`
- committed `data/evidence/`: 38 files, 3.0 MB
- working-tree `data/latest.json` at the time of this run: `2026-10-22T11:24:41Z` (83 evidence files) — **differs from the commit**, so the working tree was not used as the base

## Simulation 1 — a saved live snapshot over the committed tree

- candidate snapshot directory: `/home/runner/work/MaltaProj3/MaltaProj3/data/research/fbdc97d6/live`
- candidate `generated_at`: `2026-10-22T02:08:59Z`
- files overwritten: `data/latest.json`, `data/origination.json`, `data/row-source-audit.json`, `data/sources.json`
- `data/evidence/` files left frozen: 38
- `scripts.validate.check_data`: **failed**
- `ValueError: Inventory observation timestamp restamped`

```
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/validate.py", line 47, in check_data
    require(data['inventory_observed_at'] == context['observed_at'], 'Inventory observation timestamp restamped')
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/validate.py", line 24, in require
    raise ValueError(message)
ValueError: Inventory observation timestamp restamped
```

## Simulation 2 — `scripts.root_publish`'s own plan against a real build

- built site: `site` (present: True)
- base root: git HEAD (the committed data/ tree)
- site `data/latest.json`: `2026-10-22T11:24:41Z`
- site `data/evidence/`: 83 files, 26.6 MB — this is what the change request asks the publisher to copy
- files the publisher would write into the root: 32
- data files among them: `data/evidence/hotspawn-context.json`, `data/evidence/hotspawn-fixtures.json`, `data/latest.json`, `data/origination.json`, `data/row-source-audit.json`, `data/sources.json`
- `data/evidence/` in the root afterwards: 38 files, 3.0 MB (committed: 38)
- published `generated_at`: `2026-10-22T11:24:41Z`
- `scripts.validate.check_data` on that root: **failed** — `ValueError: HLTV observation timestamp restamped`

```
    check_data(root_copy / "data")
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/validate.py", line 70, in check_data
    require(request.get('status') == 'ok' and request.get('observed_at') == page['observed_at'], 'HLTV observation timestamp restamped')
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/validate.py", line 24, in require
    raise ValueError(message)
ValueError: HLTV observation timestamp restamped
```

## Conclusion

A root publish of a fresh snapshot would break the repository's own build: ValueError: HLTV observation timestamp restamped.

- Decisive measurement: simulation 2 (`scripts.root_publish`'s own plan over a build that was fresher than the committed root); simulation 1 measured a different, older candidate.
- scripts.build calls scripts.validate.check_data first, so the build - and therefore checks.yml on every pull request and the pages.yml refresh - would fail on the published root.
- The cause is the pairing root_publish.py documents: a fresh data/latest.json with the frozen data/evidence/ tree (its inventory observation timestamp no longer matches).
- This is why the publisher shipped by this session re-deploys the verified artifact instead of committing fresh data to main: it makes the public site current without changing the frozen fixture that CI builds from.
- 34 checked-in test modules read data/latest.json or ROOT/'data' directly, so a committed fresh snapshot also moves their fixture underneath them.

## Checked-in test modules that read the snapshot directly

34 module(s):

- `tests/test_4c972a51_unresolved_page.py`
- `tests/test_75aa5b56.py`
- `tests/test_8fa2b226.py`
- `tests/test_941ff196.py`
- `tests/test_96fbe295.py`
- `tests/test_9866e1ba.py`
- `tests/test_b1022dc2_coverage_and_mobile.py`
- `tests/test_bc1afd8f.py`
- `tests/test_briefing.py`
- `tests/test_build.py`
- `tests/test_contrarian.py`
- `tests/test_day3.py`
- `tests/test_day5_card.py`
- `tests/test_deployment_audit.py`
- `tests/test_df80ab9f_audit.py`
- `tests/test_e6c0f47d.py`
- `tests/test_edge.py`
- `tests/test_f392649f.py`
- `tests/test_f4eb8ae3.py`
- `tests/test_final_day.py`
- `tests/test_lineups.py`
- `tests/test_mobile_picks_nav.py`
- `tests/test_origination.py`
- `tests/test_origination_upgrade.py`
- `tests/test_reference_odds.py`
- `tests/test_review_flags.py`
- `tests/test_review_register.py`
- `tests/test_row_sources.py`
- `tests/test_strategy.py`
- `tests/test_summary_navigation.py`
- `tests/test_twc.py`
- `tests/test_unresolved_research.py`
- `tests/test_unresolved_summary.py`
- `tests/test_verify_live.py`
