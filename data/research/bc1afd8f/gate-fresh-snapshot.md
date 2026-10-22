# arena-bc1afd8f — regression gate measurement: `fresh-snapshot`

Observed **2026-10-22T09:56:52Z**. Command: `/opt/hostedtoolcache/Python/3.12.15/x64/bin/python -m unittest discover -s tests -v`

- snapshot `data/latest.json`: `2026-10-22T09:45:12Z`
- snapshot `data/origination.json`: `2026-10-22T09:45:21Z` (live collection: `True`)
- `data/evidence/` files present: 92
- tests run: **945** in 581.192s · exit code `1`
- result: **FAIL** (failures=15, errors=19)

## 34 failing test(s) in 18 module(s)

Modules: `test_75aa5b56`, `test_8fa2b226`, `test_b1022dc2_coverage_and_mobile`, `test_bc1afd8f`, `test_build`, `test_contrarian`, `test_coverage_audit`, `test_deployment_audit`, `test_e6c0f47d`, `test_f392649f`, `test_freshness_determinism`, `test_origination_upgrade`, `test_review_flags`, `test_review_register`, `test_source_integrity`, `test_strategy`, `test_twc`, `test_verify_live`

| Kind | Test | Module |
| --- | --- | --- |
| ERROR | `setUpClass` | `test_75aa5b56.Session75aa5b56Tests` |
| ERROR | `setUpClass` | `test_8fa2b226.BuiltSiteTests` |
| ERROR | `setUpClass` | `test_b1022dc2_coverage_and_mobile.SessionB1022dc2VerificationTests` |
| ERROR | `test_changed_canonical_probability_cannot_pass_as_a_watch` | `test_contrarian.ContrarianReviewTests.test_changed_canonical_probability_cannot_pass_as_a_watch` |
| ERROR | `setUpClass` | `test_deployment_audit.DeploymentArtifactAuditTests` |
| ERROR | `test_a_featured_bookmaker_tie_upgrades_end_to_end_and_passes_replay_validation` | `test_origination_upgrade.EndToEnd.test_a_featured_bookmaker_tie_upgrades_end_to_end_and_passes_replay_validation` |
| ERROR | `test_a_marked_upgrade_cannot_hide_a_changed_non_model_featured_row` | `test_origination_upgrade.EndToEnd.test_a_marked_upgrade_cannot_hide_a_changed_non_model_featured_row` |
| ERROR | `test_only_the_model_featured_fixture_with_a_verified_line_is_upgraded` | `test_origination_upgrade.EndToEnd.test_only_the_model_featured_fixture_with_a_verified_line_is_upgraded` |
| ERROR | `test_rerunning_is_deterministic` | `test_origination_upgrade.EndToEnd.test_rerunning_is_deterministic` |
| ERROR | `test_the_picks_page_and_the_plan_page_both_say_the_model_was_replaced` | `test_origination_upgrade.EndToEnd.test_the_picks_page_and_the_plan_page_both_say_the_model_was_replaced` |
| ERROR | `test_the_replay_validator_accepts_the_upgrade_and_rejects_tampering` | `test_origination_upgrade.EndToEnd.test_the_replay_validator_accepts_the_upgrade_and_rejects_tampering` |
| ERROR | `test_direction_and_fair_line_are_replayed_not_just_probability_sum` | `test_origination_upgrade.OriginalBookReplay.test_direction_and_fair_line_are_replayed_not_just_probability_sum` |
| ERROR | `test_duplicate_or_map_original_markets_are_not_replayable` | `test_origination_upgrade.OriginalBookReplay.test_duplicate_or_map_original_markets_are_not_replayable` |
| ERROR | `test_full_original_event_and_books_reproduce_the_summary` | `test_origination_upgrade.OriginalBookReplay.test_full_original_event_and_books_reproduce_the_summary` |
| ERROR | `test_summary_cannot_hide_a_changed_original_bid` | `test_origination_upgrade.OriginalBookReplay.test_summary_cannot_hide_a_changed_original_bid` |
| ERROR | `test_wrong_token_or_condition_is_not_replayable` | `test_origination_upgrade.OriginalBookReplay.test_wrong_token_or_condition_is_not_replayable` |
| ERROR | `test_zero_size_original_levels_cannot_back_a_pick` | `test_origination_upgrade.OriginalBookReplay.test_zero_size_original_levels_cannot_back_a_pick` |
| ERROR | `setUpClass` | `test_review_flags.ReviewFlagsIntegration` |
| ERROR | `setUpClass` | `test_verify_live.PublicArtifactParity` |
| FAIL | `test_the_site_links_the_dossier_from_the_unresolved_section` | `test_8fa2b226.CoverageProbeDossierTests.test_the_site_links_the_dossier_from_the_unresolved_section` |
| FAIL | `test_the_gate_records_which_snapshot_it_ran_against` | `test_bc1afd8f.GateTests.test_the_gate_records_which_snapshot_it_ran_against` |
| FAIL | `test_filter_counts_match_the_rows_actually_rendered` | `test_build.ResearchedFallbackDisplayTests.test_filter_counts_match_the_rows_actually_rendered` |
| FAIL | `test_current_watch_is_an_underdog_context_not_a_pick_override` | `test_contrarian.ContrarianReviewTests.test_current_watch_is_an_underdog_context_not_a_pick_override` |
| FAIL | `test_homepage_section_has_sources_on_every_review_row` | `test_contrarian.ContrarianReviewTests.test_homepage_section_has_sources_on_every_review_row` |
| FAIL | `test_checked_in_fixture_has_full_coverage` | `test_coverage_audit.CoverageAudit.test_checked_in_fixture_has_full_coverage` |
| FAIL | `test_review_page_renders_the_new_flags` | `test_e6c0f47d.ReviewPagePublicationTests.test_review_page_renders_the_new_flags` |
| FAIL | `test_full_build_publishes_disambiguation_on_edge_and_review_pages` | `test_f392649f.LineupDisambiguationTests.test_full_build_publishes_disambiguation_on_edge_and_review_pages` |
| FAIL | `test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times` | `test_freshness_determinism.PinnedClockTests.test_the_suite_passes_with_the_clock_pinned_to_several_absolute_times` |
| FAIL | `test_no_element_id_is_repeated_on_the_review_page` | `test_review_register.EverySessionRegisterTests.test_no_element_id_is_repeated_on_the_review_page` |
| FAIL | `test_the_review_page_publishes_every_register_without_repeating_an_id` | `test_review_register.EverySessionRegisterTests.test_the_review_page_publishes_every_register_without_repeating_an_id` |
| FAIL | `test_flagged_for_review_page_publishes_the_register` | `test_review_register.ReviewRegisterTests.test_flagged_for_review_page_publishes_the_register` |
| FAIL | `test_dated_repository_snapshot_is_audited_without_being_restamped` | `test_source_integrity.RowRegister.test_dated_repository_snapshot_is_audited_without_being_restamped` |
| FAIL | `test_the_review_page_publishes_them_without_changing_the_snapshot_flags` | `test_strategy.PublishedFindings.test_the_review_page_publishes_them_without_changing_the_snapshot_flags` |
| FAIL | `test_generated_twc_is_not_overwritten_by_the_old_root_copy` | `test_twc.ArtifactIntegration.test_generated_twc_is_not_overwritten_by_the_old_root_copy` |

## Last lines of the run

```
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/build_origination.py", line 715, in validate_origination
    assert m['pick_index'] == expected_pick_for(o), 'Fallback pick differs from its probabilities'
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Fallback pick differs from its probabilities

======================================================================
FAIL: test_generated_twc_is_not_overwritten_by_the_old_root_copy (test_twc.ArtifactIntegration.test_generated_twc_is_not_overwritten_by_the_old_root_copy)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/home/runner/work/MaltaProj3/MaltaProj3/tests/test_twc.py", line 161, in test_generated_twc_is_not_overwritten_by_the_old_root_copy
    out = Path(tmp) / 'site'; build(ROOT / 'data', out)
                              ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/build.py", line 1811, in build
    build_originated(source, output)
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/build_origination.py", line 735, in build
    validate_origination(data, source)
  File "/home/runner/work/MaltaProj3/MaltaProj3/scripts/build_origination.py", line 715, in validate_origination
    assert m['pick_index'] == expected_pick_for(o), 'Fallback pick differs from its probabilities'
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Fallback pick differs from its probabilities

----------------------------------------------------------------------
Ran 945 tests in 581.192s

FAILED (failures=15, errors=19)
```

