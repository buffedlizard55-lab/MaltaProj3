# arena-bc1afd8f — would publishing a fresh snapshot into the branch root break the build?

Observed **2026-10-22T09:47:00Z**. Reproduced offline in a temporary directory; the
repository's own `data/` tree was not modified and no value was invented.

**Question.** If the verified build were published into the branch root the way scripts/root_publish.py does it (fresh data files, frozen data/evidence), would the repository's own replay validator still accept the tree that checks.yml and pages.yml build from?

## Candidate

- checked-in `data/latest.json`: `2026-10-22T09:45:12Z`
- candidate snapshot directory: `/home/runner/work/MaltaProj3/MaltaProj3/data/research/fbdc97d6/live`
- candidate `generated_at`: `2026-10-22T02:08:59Z`
- files overwritten: `data/latest.json`, `data/origination.json`, `data/row-source-audit.json`, `data/sources.json`
- `data/evidence/` files left frozen: 92

## Result of `scripts.validate.check_data` on the published root

- **failed**
- `ValueError: Inventory observation timestamp restamped`

```
           ^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/validate.py", line 47, in check_data
    require(data['inventory_observed_at'] == context['observed_at'], 'Inventory observation timestamp restamped')
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/validate.py", line 24, in require
    raise ValueError(message)
ValueError: Inventory observation timestamp restamped
```

## Same test using `scripts.root_publish`'s own plan on a real build

- built site: `site` (present: True)
- files the publisher would write into the root: 25
- data files among them: `data/latest.json`
- `data/evidence/` files left in the root afterwards: 92
- published `generated_at`: `2026-10-22T09:45:12Z` (frozen: `2026-10-22T09:45:12Z`)
- `scripts.validate.check_data` on that root: **passed**

## Conclusion

A root publish of this candidate snapshot still replays: the checked-in evidence matches it.

- Publishing the verified build into the branch root is safe for this candidate.
- The checked-in test modules that read data/latest.json were counted but not run here.

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
