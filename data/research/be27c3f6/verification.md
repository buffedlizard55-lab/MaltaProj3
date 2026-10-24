# Complete-picks presentation and source audit — be27c3f6

Audit date: 2026-10-24. This session changed presentation, accessibility, navigation, search/filter behavior and read-only audits only. It did not change a fixture, probability, pick, alias, source rule, runtime data file, publisher or workflow.

## Official live inventory check

At `2026-10-24T05:44:04Z`, the [official CS2 lobby](https://play.hotspawn.com/cs2-pickems) and [official scheduled-fixture API](https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1) agreed on 25 current fixture IDs. The [deployed snapshot](https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json), observed at `2026-10-23T20:09:44Z`, had 19 active rows. Sixteen IDs overlap, all 16 API/snapshot start times agree, nine current fixtures are missing from the deployed list, and three deployed rows have since left the live lobby. Hotspawn `% picked` values were ignored and are not retained in the audit.

These nine fixtures require the normal collector/HLTV/external-line research ladder. No probability or pick is supplied by this presentation audit.

| Fixture | Teams | Official UTC start | Official source |
| --- | --- | --- | --- |
| 1079658 | Acend vs FORZE Reload | 2026-10-24 08:00 | [Hotspawn 1079658](https://www.hotspawn.com/matches/acend-vs-forze-reload-cct-europe-2026-series-11-1079658) |
| 1081152 | HAVU vs Azuolas | 2026-10-24 11:00 | [Hotspawn 1081152](https://www.hotspawn.com/matches/havu-vs-azuolas-cct-europe-2026-series-12-1081152) |
| 1079659 | Spirit Academy vs Lavked | 2026-10-24 11:00 | [Hotspawn 1079659](https://www.hotspawn.com/matches/spirit-academy-vs-lavked-cct-europe-2026-series-11-1079659) |
| 1081153 | Saint Sinners vs 6yuBoJlbl | 2026-10-24 14:00 | [Hotspawn 1081153](https://www.hotspawn.com/matches/saint-sinners-vs-6yubojlbl-cct-europe-2026-series-12-1081153) |
| 1079660 | INOX Division vs BRUTE | 2026-10-24 14:00 | [Hotspawn 1079660](https://www.hotspawn.com/matches/inox-division-vs-brute-cct-europe-2026-series-11-1079660) |
| 1081154 | BakS vs ILLYRIANS | 2026-10-24 17:00 | [Hotspawn 1081154](https://www.hotspawn.com/matches/baks-vs-illyrians-cct-europe-2026-series-12-1081154) |
| 1079661 | Nuclear TigeRES vs ex-Zero Tenacity | 2026-10-24 17:00 | [Hotspawn 1079661](https://www.hotspawn.com/matches/nuclear-tigeres-vs-ex-zero-tenacity-cct-europe-2026-series-11-1079661) |
| 1081156 | Spirit Academy vs LFO 10 | 2026-10-25 12:00 | [Hotspawn 1081156](https://www.hotspawn.com/matches/spirit-academy-vs-lfo-10-cct-europe-2026-series-12-1081156) |
| 1081158 | FORZE Reload vs ex-RUSTEC | 2026-10-25 18:00 | [Hotspawn 1081158](https://www.hotspawn.com/matches/forze-reload-vs-ex-rustec-cct-europe-2026-series-12-1081158) |

The three deployed active IDs no longer in the live lobby are [1083025 paiN–Imperial](https://www.hotspawn.com/matches/imperial-vs-pain-circuit-x-curitiba-4-1083025), [1082923 Alka–LOS NINOS](https://www.hotspawn.com/matches/alka-vs-los-ninos-cct-south-america-2026-series-7-1082923), and [1083045 Chinggis Warriors–Rare Atom](https://www.hotspawn.com/matches/chinggis-warriors-vs-rare-atom-void-autumn-cup-2026-1083045). Their scheduled starts have passed; no result is inferred.

Machine-readable record: `live-inventory-audit.json`. The warning is auto-published from `flags.json` on Flagged for Review. Live collection and probability repair remain with the sessions that own those files.

## Last published artifact consistency check

`scripts/audit_be27c3f6_published.py` independently compared the checked-in root [complete-picks page](https://buffedlizard55-lab.github.io/MaltaProj3/origination/) with its [snapshot](https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json). Result: **pass** for the old snapshot's internal consistency—19 active snapshot IDs, 19 overview rows, 19 evidence cards, exact team/probability/pick agreement, official Hotspawn and analysis links, correct featured-analysis comparisons, and no row-source violations. The row-source audit covered 50 rows on that page.

This pass is deliberately narrow: it does **not** mean the old page covers the current lobby, that an old betting line remains available, or that the probabilities were freshly re-derived. Those limitations are explicit in `published-complete-audit.json`.

## Presentation irregularities and resolutions

1. Phone users crossed eight large quick links, 13.6px probabilities, 40px filter targets and repeated evidence cards without persistent navigation or search. The canonical page now has compact quick links, combined team/tournament search, method filters, counts/reset, direct limitation/evidence links, 16px phone probabilities, 44px targets and fixed mobile navigation.
2. The evidence cards retired a pick when its snapshot/lock expired, but the overview check mark was static. Overview labels now render in the same initial safety state and follow the existing `spawn-pick-safety-updated` event. Retired rows say `Snapshot`, keep the estimate for audit, and are never automatically revived.
3. The complete-picks heading and evidence cards repeat fixtures intentionally: the table is the searchable list and the cards are its per-match evidence. A labelled evidence heading and direct anchor links preserve that relationship rather than hiding either source view.

## Final local verification

- `python -m unittest tests.test_be27c3f6_mobile_complete_picks tests.test_origination tests.test_origination_upgrade`: **88 tests passed**.
- A 1,277-test pre-integration run exposed the three known publisher-clock errors and duplicate landmark already repaired in PR #237, plus one new parser compatibility failure in this session's initial two-hidden-span label markup. The markup now uses one server-correct label updated from explicit attributes; `python -m unittest tests.test_be27c3f6_mobile_complete_picks tests.test_eea4c104_audit` passes **10/10**, including the formerly failing audit. The pre-integration run is not counted as a final green result; the full combined suite remains required after #237 is integrated.
- `npx playwright test tests/browser/be27c3f6_complete_picks.spec.mjs tests/browser/origination.spec.mjs`: **11 tests passed**, including 320/390/768/1440px, search/filter/reset, dynamic safety retirement, no-JavaScript behavior and axe checks.
- Full pre-integration `npm test`: **110/110 Playwright tests passed**. This is a strong regression result but will still be rerun on the final integrated tree.
- `python -m scripts.build`: 80 replayed source rows; 770 audited rows, 751 with official links, 9 explicitly flagged unverified, 10 site-map rows, **0 sourceless**; acceptance **9 pass / 1 info / 0 fail**; **833** internal links/assets/anchors passed.
- `mobile-after.json`: no horizontal overflow at 320/390/768/1440px; 16px probabilities and 44px filter targets on phones; one search input; four mobile navigation links; no duplicate IDs; every replay row has an HTTPS source; zero axe violations at 390px. The first row starts 401px earlier at 320px and 320px earlier at 390px than baseline. The replay fixture has 17 rows and zero unresolved rows; this is not represented as current production coverage.
- `python -m scripts.audit_be27c3f6_published`: **pass**, 19/19 old published active IDs reconciled with no consistency violations.

Integration checkpoint: the branch was rebased onto `main@bdb4fc9` (PR #240), preserving its EGW/source-rule work and publisher-clock test repair. Only the shared board conflicted; both session sections were preserved. The combined build passed with 773 audited rows and zero sourceless rows, but a 103-test targeted run exposed six `live_collect` errors because PR #240 uses `egw_live` without importing it. PR #237's 06:14–06:15Z integration comments and 06:13Z board entry explicitly claim the missing import/replay wiring plus fail-closed independent provider-time/outcome validation. This session left those files untouched and will rerun the full suite only after that repair is integrated; the failed targeted run is not a green result.

Latest-main update: rebased onto `main@a0c08fa` (including PRs #241, #250, #251, #252 and #257). The import crash is fixed: 67 targeted publisher/EGW/origination/strict-audit/mobile tests pass, and the build passes with 801 rows, zero sourceless rows, acceptance 9 pass / 1 info / 0 fail and 831 internal links. The EGW adapter still lacks independent provider-time and exact team binding; PR #237's `ced36cb` fail-closed rewrite remains a release-blocking integration requirement.

Final integrated candidate at 08:06Z: PR #237 merged upstream as `275771b` (head `e08537b`), and this branch was rebased onto `main@746118c`; the temporary duplicate integration merge is absent from the final PR. On that exact tree, 172 targeted tests passed with one expected skip, the full unit suite passed **1,497 tests with one expected skip**, and the full Playwright suite passed **118/118**. Build/replay passed with 80 source rows, 841 audited rows / 0 sourceless, acceptance 9 pass / 1 info / 0 fail and 833 internal links. These are local results; PR checks, production refresh and Pages deployment are verified separately.

PR, merge, workflow and live-Pages results are recorded separately on `COORDINATION.md` after they occur; this dossier does not claim them in advance.
