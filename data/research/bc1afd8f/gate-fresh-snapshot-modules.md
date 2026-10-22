# arena-bc1afd8f — regression gate measurement: `fresh-snapshot-modules`

Observed **2026-10-22T11:39:28Z**. Command: `/opt/hostedtoolcache/Python/3.12.15/x64/bin/python -m unittest -v tests.test_build tests.test_origination tests.test_origination_upgrade tests.test_review_flags tests.test_bc1afd8f tests.test_coverage_audit tests.test_verify_live tests.test_freshness_determinism tests.test_twc tests.test_source_integrity tests.test_df80ab9f_audit tests.test_4c972a51_tiebreak tests.test_96fbe295`

- snapshot `data/latest.json`: `2026-10-22T11:24:41Z`
- snapshot `data/origination.json`: `2026-10-22T11:24:54Z` (live collection: `True`)
- `data/evidence/` files present: 83
- tests run: **293** in 732.589s · exit code `1`
- result: **FAIL** (failures=13, errors=13)

## 26 failing test(s) in 1 module(s)

Modules: `tests`

| Kind | Test | Module |
| --- | --- | --- |
| ERROR | `test_a_featured_bookmaker_tie_upgrades_end_to_end_and_passes_replay_validation` | `tests.test_origination_upgrade.EndToEnd.test_a_featured_bookmaker_tie_upgrades_end_to_end_and_passes_replay_validation` |
| ERROR | `test_a_marked_upgrade_cannot_hide_a_changed_non_model_featured_row` | `tests.test_origination_upgrade.EndToEnd.test_a_marked_upgrade_cannot_hide_a_changed_non_model_featured_row` |
| ERROR | `test_only_the_model_featured_fixture_with_a_verified_line_is_upgraded` | `tests.test_origination_upgrade.EndToEnd.test_only_the_model_featured_fixture_with_a_verified_line_is_upgraded` |
| ERROR | `test_rerunning_is_deterministic` | `tests.test_origination_upgrade.EndToEnd.test_rerunning_is_deterministic` |
| ERROR | `test_the_picks_page_and_the_plan_page_both_say_the_model_was_replaced` | `tests.test_origination_upgrade.EndToEnd.test_the_picks_page_and_the_plan_page_both_say_the_model_was_replaced` |
| ERROR | `test_the_replay_validator_accepts_the_upgrade_and_rejects_tampering` | `tests.test_origination_upgrade.EndToEnd.test_the_replay_validator_accepts_the_upgrade_and_rejects_tampering` |
| ERROR | `test_direction_and_fair_line_are_replayed_not_just_probability_sum` | `tests.test_origination_upgrade.OriginalBookReplay.test_direction_and_fair_line_are_replayed_not_just_probability_sum` |
| ERROR | `test_duplicate_or_map_original_markets_are_not_replayable` | `tests.test_origination_upgrade.OriginalBookReplay.test_duplicate_or_map_original_markets_are_not_replayable` |
| ERROR | `test_full_original_event_and_books_reproduce_the_summary` | `tests.test_origination_upgrade.OriginalBookReplay.test_full_original_event_and_books_reproduce_the_summary` |
| ERROR | `test_summary_cannot_hide_a_changed_original_bid` | `tests.test_origination_upgrade.OriginalBookReplay.test_summary_cannot_hide_a_changed_original_bid` |
| ERROR | `test_wrong_token_or_condition_is_not_replayable` | `tests.test_origination_upgrade.OriginalBookReplay.test_wrong_token_or_condition_is_not_replayable` |
| ERROR | `test_zero_size_original_levels_cannot_back_a_pick` | `tests.test_origination_upgrade.OriginalBookReplay.test_zero_size_original_levels_cannot_back_a_pick` |
| ERROR | `test_all_public_views_verify_for_the_generated_artifact` | `tests.test_verify_live.PublicArtifactParity.test_all_public_views_verify_for_the_generated_artifact` |
| FAIL | `test_filter_counts_match_the_rows_actually_rendered` | `tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered` |
| FAIL | `test_unresolved_cards_do_not_add_pick_cards` | `tests.test_origination.PublicContractTests.test_unresolved_cards_do_not_add_pick_cards` |
| FAIL | `test_checked_in_fixture_has_full_coverage` | `tests.test_coverage_audit.CoverageAudit.test_checked_in_fixture_has_full_coverage` |
| FAIL | `test_day4_cannot_invent_a_hotspawn_fixture` | `tests.test_verify_live.PublicArtifactParity.test_day4_cannot_invent_a_hotspawn_fixture` |
| FAIL | `test_day4_json_must_remain_the_same_in_both_exports` | `tests.test_verify_live.PublicArtifactParity.test_day4_json_must_remain_the_same_in_both_exports` |
| FAIL | `test_day4_section_must_not_be_missing_even_before_fixtures_arrive` | `tests.test_verify_live.PublicArtifactParity.test_day4_section_must_not_be_missing_even_before_fixtures_arrive` |
| FAIL | `test_even_blank_probability_cells_must_match_generated_json` | `tests.test_verify_live.PublicArtifactParity.test_even_blank_probability_cells_must_match_generated_json` |
| FAIL | `test_external_market_prices_must_come_from_the_published_json` | `tests.test_verify_live.PublicArtifactParity.test_external_market_prices_must_come_from_the_published_json` |
| FAIL | `test_external_market_table_cannot_drop_a_listed_fixture` | `tests.test_verify_live.PublicArtifactParity.test_external_market_table_cannot_drop_a_listed_fixture` |
| FAIL | `test_same_date_but_old_static_twc_template_is_rejected` | `tests.test_verify_live.PublicArtifactParity.test_same_date_but_old_static_twc_template_is_rejected` |
| FAIL | `test_twc_cannot_use_another_inventory_snapshot` | `tests.test_verify_live.PublicArtifactParity.test_twc_cannot_use_another_inventory_snapshot` |
| FAIL | `test_twc_json_cannot_silently_omit_both_deciders` | `tests.test_verify_live.PublicArtifactParity.test_twc_json_cannot_silently_omit_both_deciders` |
| FAIL | `test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times` | `tests.test_freshness_determinism.PinnedClockTests.test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times` |

## Last lines of the run

```
During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/runner/work/MaltaProj3/MaltaProj3/tests/test_verify_live.py", line 53, in test_twc_json_cannot_silently_omit_both_deciders
    with self.assertRaisesRegex(ValueError, 'omits or invents a decider'): self.verify()
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: "omits or invents a decider" does not match "Public complete-picks coverage audit failed: fixture 1082926: exactly even estimate must not name a pick; fixture 1082858: exactly even estimate must not name a pick"

======================================================================
FAIL: test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times (tests.test_freshness_determinism.PinnedClockTests.test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times)
A test whose outcome moves with the clock is a time bomb.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/runner/work/MaltaProj3/MaltaProj3/tests/test_freshness_determinism.py", line 212, in test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times
    self.assertFalse(problems, 'these tests expire against the wall clock:\n' + '\n'.join(problems))
AssertionError: ['2026-10-16T12:00:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22', '2026-10-17T05:30:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22', '2026-10-17T13:00:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22', '2026-10-20T12:00:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22'] is not false : these tests expire against the wall clock:
2026-10-16T12:00:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22
2026-10-17T05:30:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22
2026-10-17T13:00:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22
2026-10-20T12:00:00+00:00 · tests.test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered: AssertionError: 24 != 22

----------------------------------------------------------------------
Ran 293 tests in 732.589s

FAILED (failures=13, errors=13)
```

