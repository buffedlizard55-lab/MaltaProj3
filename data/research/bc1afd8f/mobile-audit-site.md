# arena-bc1afd8f — phone-first static audit

Observed **2026-10-22T09:17:33Z** against `/home/runner/work/MaltaProj3/MaltaProj3/site` (data `/home/runner/work/MaltaProj3/MaltaProj3/data`).
Static HTML/CSS contract only; the runtime 320/390/768/1440 px browser checks live in
`checks.yml` and `tests/browser/`. No page was edited and no value recalculated.

Result: **20/20 checks passed**

| Check | Result | What was found |
| --- | --- | --- |
| `viewport-meta` — Every current page declares `width=device-width, initial-scale=1` | PASS | all 9 current pages declare it |
| `executive-summary` — The landing page opens with an executive summary | PASS | h1 = 'Executive summary' |
| `exec-banner` — The landing page carries the `Start here on your phone` executive-summary banner | PASS | found section.exec-banner |
| `exec-link-complete` — The executive summary links inside this site to the complete picks list | PASS | links: ./origination/#picks |
| `exec-link-featured` — The executive summary links inside this site to the featured picks feed | PASS | links: ./picks/ |
| `exec-link-unresolved` — The executive summary links inside this site to the unresolved & limitations | PASS | links: ./origination/#unresolved, ./unresolved/ |
| `exec-links-internal` — The banner's own links stay inside this site (no reader is sent off-site to find a pick) | PASS | external links in the banner: none |
| `glance-coverage` — Every active fixture in the snapshot appears in the phone pick index | PASS | 43 rows for 43 active fixtures |
| `glance-both-probabilities` — Every pick row shows both teams' win probability, or is an explicit blank that links to its limitation | PASS | 43 rows show both percentages; 0 explicit blanks link to their limitation |
| `mobile-nav` — A fixed phone navigation bar with at least five labelled, internal destinations | PASS | 6 slots: Summary, Picks, Unresolved, Edge, Sources, Review |
| `mobile-nav-picks` — One phone-nav slot goes straight to the picks | PASS | href = ./origination/#picks |
| `unresolved-section` — The landing page carries a separate unresolved-picks section with its limitations | PASS | found #unresolved-register |
| `tap-target-mobile-nav-a` — phone navigation slots declare a ≥44px tap target | PASS | largest declared min-height 48px — .mobile-nav>a {min-height:46px} ; .mobile-nav>a {min-height:48px} in @media(max-width:700px) |
| `tap-target-exec-banner-actions-a` — executive-summary action buttons declare a ≥44px tap target | PASS | largest declared min-height 48px — .exec-banner-actions a {min-height:44px} in @media(max-width:620px); .exec-banner-actions a {min-height:44px} in @media(max-width:375px) |
| `table-scroll-wrappers` — Every table in a current view sits inside a wrapper that scrolls horizontally (no page-wide overflow at 320 px) | PASS | scroll wrappers in CSS: .matches-wrap, .mini-table-wrap, .table-scroll, .table-wrap, .top-nav; unwrapped tables: none |
| `no-wide-fixed-widths` — No non-table layout rule declares a fixed width wider than 320px | PASS | none found |
| `table-min-widths` — Tables wider than a phone scroll inside their own wrapper rather than stretching the page (informational) | PASS | table min-widths: table.simple min-width:520px; table min-width:860px — every one of them is inside a wrapper that declares overflow-x:auto |
| `phone-breakpoints` — The stylesheet carries max-width phone breakpoints | PASS | 11 distinct phone media queries: @media (max-width: 430px), @media (max-width: 719px), @media (max-width: 800px), @media (max-width:620px), @media(max-width:1000px), @media(max-width:1200px) |
| `probability-type-size` — The probability text declares a readable phone size (informational — the cascade decides the effective size) | PASS | /* ---- Session arena-c1fa150f: both-team probabilities on the phone summary and the "picks without a betting line" register. Append-only; no existing rule is redefined, so other sessions' styles are untouched. ---- */ .glance-other {font-size:10.5px}; .glance-other {font-size:9.5px} in @media(max-width:375px); .glance-other {font-size:11px} in @media(max-width:700px); .glance-prob,.glance-other {font-size:12px} in @media(max-width:375px) |
| `archived-views` — Archived session views are reported separately from the current pages | PASS | 12 archived page(s); without a viewport meta: none |
