# Rendered-output acceptance audit (brief line by line)

Generated 2026-10-23T07:38:50Z by `scripts/acceptance_audit.py` against `/tmp/pub2`.
Snapshot `2026-10-15T08:36:13Z`.

| # | Brief line | Check | Result | Evidence |
| --- | --- | --- | --- | --- |
| 1 | It should cover all matches listed on hotspawn and give probability to win for the team to win and be obvious what the pick is | Every listed fixture shows a pick and both win probabilities | **pass** — 32 glance rows: every one names a pick, shows both percentages summing to 100, and links an official/primary source (32/32). | /tmp/pub2/index.html#picks-at-a-glance |
| 2 | I want picks for every match listed on hotspawn for counterstrike 2 | The summary's coverage sentence matches the rendered list and the snapshot | **pass** — 32 active fixtures stated and 32 rows rendered. | /tmp/pub2/index.html#picks-at-a-glance |
| 3 | Create a separate section for any unresolved picks and the limitations for generating picks for them and include this in the executive summary | A separate unresolved/limitations section sits inside the executive summary | **pass** — Register "Unresolved picks & limitations" is inside the executive summary with 5 explicit limitations and 0 labelled pick-less card(s). | /tmp/pub2/index.html#unresolved-register |
| 4 | We should have an executive summary that provides links within our site to where an updated list of picks can be found | The executive summary links in-site to the updated list of picks | **pass** — In-site links to the complete picks list, the picks page and the unresolved section all resolve. | complete updated picks: ./origination/#picks<br>picks page: ./picks/<br>unresolved section: ./unresolved/ |
| 5 | It should be easily readable and accessible on phone and mobile device | Pages are phone-ready: viewport declared, glance is a list, small-screen rules exist | **pass** — 11 pages declare a device-width viewport; the glance list is styled by scout.css and has a small-screen media query. | /tmp/pub2/assets/scout.css |
| 6 | So that we have a full list of updated matches and picks for counter strike 2 from hotspawn every 4-8 hours | The refresh schedule stays inside the brief's 4-8 hour window | **pass** — 2 cron entries, largest gap 2.5 h, declared interval 4 h, stale bound 8 h. | 17 */4 * * *; 47 2-22/4 * * * |
| 7 | Every table row must have a source link to an official site. If a value can't be confirmed from an official source, leave it blank and flag it as unverified. | No rendered row is published without a source or an unverified label | **info** — data/row-source-audit.json is not in this tree (rendered-only root); run the audit against the full build output. | /tmp/pub2 |
| 8 | The hotspawn site regularly updates new matches so make sure that we have full coverage | The published snapshot is dated and its age is reported | **info** — Snapshot 2026-10-15T08:36:13Z is 191.0 h old; coverage_complete=True; refresh_interval_hours=4. The page is required to warn the reader; see #stale-warning. | /tmp/pub2/data/latest.json |
| 9 | It should be up to date and list the probabilities for each match based upon known betting lines | The rendered page and the downloadable snapshot are the same observation | **fail** — The page shows snapshot 2026-10-23T07:08:13Z but data/latest.json carries 2026-10-15T08:36:13Z (190.5 h apart): a reader who downloads the JSON sees a different observation from the one printed on the page. | /tmp/pub2/index.html<br>/tmp/pub2/data/latest.json |
| 10 | Create a separate section for any unresolved picks and the limitations | The dedicated unresolved page exists and lists limitations | **pass** — Dedicated page "Unresolved picks & limitations" with 5 stated limitations. | /tmp/pub2/unresolved/index.html |

**7 pass · 2 info · 1 fail** of 10 checks.

