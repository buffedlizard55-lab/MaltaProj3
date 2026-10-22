# Independent verification — 2026-10-22T01:12:11Z

Read-only audit by session 416d93ee of `https://buffedlizard55-lab.github.io/MaltaProj3`.

## Published snapshot

- `generated_at`: 2026-10-22T01:06:32Z
- inventory observed: 2026-10-22T01:06:14Z
- published counts: `{"archived": 62, "bookmaker": 1, "inventory": 97, "market": 5, "model": 16, "no_edge": 1, "picks": 21, "unknown_schedule": 0, "unresolved": 13, "upcoming": 35}`
- origination counts: `{"active": 35, "alias_joined": 2, "bookmaker": 1, "consensus": 1, "guidance": 0, "market": 6, "model": 27, "network": 4, "reference": 0, "resolved": 35, "unresolved": 0, "with_pick": 34}`

## Pick coverage

- records in the complete list: **35**
- active fixtures: **35**
- active with probabilities: **35**
- active with a directional pick: **34**
- active without a pick: **1**

## Arithmetic replay

- rows with probabilities: **35**
- replayed exactly: **30**
- display-rounding only: **2**
- mismatches: **1**
- not replayable: **2**

  - `1082882` Own results-based estimate (bo3.gg series results): method 'model' has no replayable formula in this audit
  - `1081146` Own results-based estimate (bo3.gg series results): method 'model' has no replayable formula in this audit

## Hotspawn inventory parity

- rendered lobby counts: `{"all_tiers_count": 97, "fixture_ids_in_html": ["1079188", "1079189", "1079650", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081143", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081597", "1081600", "1081869", "1081870", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082882"], "fixture_links_in_html": 30, "matches_this_week": 170}`
- rendered CS2 lobby counts: `{"all_tiers_count": 97, "fixture_ids_in_html": ["1079188", "1079189", "1079650", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081143", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081597", "1081600", "1081869", "1081870", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082882"], "fixture_links_in_html": 30, "matches_this_week": 170}`

## Official model inputs

- Valve snapshots read: ['2026-10-05']
- HLTV ranking HTTP: 200 (253 rows parsed)

  - `1079188` Research model estimate (Valve official ratings): Valve Bushido Wildcats row 950.3 vs published None — missing-in-table
  - `1079188` Research model estimate (Valve official ratings): Valve ex-6666 row 940.1 vs published None — missing-in-table
  - `1079650` Valve-rating research estimate: Valve GenOne row 1185 vs published None — missing-in-table
  - `1079650` Valve-rating research estimate: Valve Spirit Academy row 981 vs published None — missing-in-table
  - `1081143` Valve-rating research estimate: Valve BAKS row 1044 vs published None — missing-in-table
  - `1081143` Valve-rating research estimate: Valve Azuolas row 863 vs published None — missing-in-table
  - `1079651` Valve-rating research estimate: Valve Butterfly row 1082 vs published None — missing-in-table
  - `1079651` Valve-rating research estimate: Valve Lavked row 862 vs published None — missing-in-table
  - `1081596` Valve-rating research estimate: Valve Falcons Force row 806 vs published None — missing-in-table
  - `1081596` Valve-rating research estimate: Valve Phantom Academy row 783 vs published None — missing-in-table
  - `1081597` Research model estimate (Valve official ratings): Valve benched gods row 777.8 vs published None — missing-in-table
  - `1081597` Research model estimate (Valve official ratings): Valve TitanFlow row 996.5 vs published None — missing-in-table
  - `1082767` Valve-rating research estimate: Valve Nemesis row 1455 vs published None — missing-in-table
  - `1082767` Valve-rating research estimate: Valve WW row 1023 vs published None — missing-in-table
  - `1081600` Valve-rating research estimate: Valve DONSTU row 732 vs published None — missing-in-table
  - `1081600` Valve-rating research estimate: Valve Banda Chuya row 801 vs published None — missing-in-table
  - `1079652` Research model estimate (Valve official ratings): Valve Acend row 1197 vs published None — missing-in-table
  - `1079652` Research model estimate (Valve official ratings): Valve 6666 row 923 vs published None — missing-in-table
  - `1081145` Valve-rating research estimate: Valve Lavked row 862 vs published None — missing-in-table
  - `1081145` Valve-rating research estimate: Valve HAVU row 937 vs published None — missing-in-table
  - `1079653` Valve-rating research estimate: Valve Rune Eaters row 1110 vs published None — missing-in-table
  - `1079653` Valve-rating research estimate: Valve FORZE Reload row 1100 vs published None — missing-in-table
  - `1082769` Research model estimate (Valve official ratings): Valve K27 row 1429.2 vs published None — missing-in-table
  - `1082769` Research model estimate (Valve official ratings): Valve NEXORA row 714.9 vs published None — missing-in-table
  - `1081871` Research model estimate (Valve official ratings): Valve Lynn Vision row 1190 vs published None — missing-in-table
  - `1081871` Research model estimate (Valve official ratings): Valve Chinggis Warriors row 1084 vs published None — missing-in-table
  - `1079654` Valve-rating research estimate: Valve ex-Zero Tenacity row 1066 vs published None — missing-in-table
  - `1079654` Valve-rating research estimate: Valve ex-RUSTEC row 1066 vs published None — missing-in-table
  - `1079655` Valve-rating research estimate: Valve Nuclear TigeRES row 1324 vs published None — missing-in-table
  - `1079655` Valve-rating research estimate: Valve Illyrians row 862 vs published None — missing-in-table
  - `1081148` Valve-rating research estimate: Valve Inner Circle Academy row 1064 vs published None — missing-in-table
  - `1081148` Valve-rating research estimate: Valve Spirit Academy row 981 vs published None — missing-in-table
  - `1081149` Research model estimate (HLTV world ranking): HLTV FORZE Reload row 11.0 vs published 11.0 — match
  - `1081149` Research model estimate (HLTV world ranking): HLTV LFO 10 row 4.0 vs published 4.0 — match
  - `1079657` Research model estimate (Valve official ratings): Valve BAKS row 1044 vs published None — missing-in-table
  - `1079657` Research model estimate (Valve official ratings): Valve BRUTE row 1116 vs published None — missing-in-table
  - `1081150` Valve-rating research estimate: Valve ex-RUSTEC row 1066 vs published None — missing-in-table
  - `1081150` Valve-rating research estimate: Valve Saint Sinners row 810 vs published None — missing-in-table
  - `1082858` Research model estimate (Valve official ratings): Valve Ground Zero row 866.5 vs published None — missing-in-table
  - `1082858` Research model estimate (Valve official ratings): Valve Off Chops row 904.6 vs published None — missing-in-table
  - `1082859` Valve-rating research estimate: Valve NEXVOID row 995 vs published None — missing-in-table
  - `1082859` Valve-rating research estimate: Valve Alter Ego row 819 vs published None — missing-in-table
  - `1082860` Research model estimate (HLTV world ranking · unranked floor): HLTV FlyQuest row 16.0 vs published 16.0 — match
  - `1082860` Research model estimate (HLTV world ranking · unranked floor): HLTV Staqued row 0.0 vs published None — not-in-top-listing
  - `1082861` Valve-rating research estimate: Valve Rooster row 718 vs published None — missing-in-table
  - `1082861` Valve-rating research estimate: Valve Abyssal row 734 vs published None — missing-in-table
  - `1082792` Research model estimate (Valve official ratings): Valve HOTU row 1437 vs published None — missing-in-table
  - `1082792` Research model estimate (Valve official ratings): Valve The Huns row 944 vs published None — missing-in-table
  - `1082793` Valve-rating research estimate: Valve 5star row 1110 vs published None — missing-in-table
  - `1082793` Valve-rating research estimate: Valve 1win row 1383 vs published None — missing-in-table

## Phone findability

- viewport meta: **True**
- nav landmarks: **5**
- in-site pick links on the summary: ['./origination/#picks']
- unresolved section on the summary: **True**
- rows on the picks page: **35**

## Verdicts

- PASS — inventory_and_picks_cover_every_active_fixture
- FAIL — every_active_fixture_has_a_directional_pick
- FAIL — every_published_probability_replays_from_its_own_inputs
- PASS — published_pick_is_the_published_argmax
- PASS — phone_summary_links_the_picks_list

## Unreadable requests

- `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1&cb=1792631531` — 400
