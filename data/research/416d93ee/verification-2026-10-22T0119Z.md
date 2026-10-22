# Independent verification — 2026-10-22T01:19:44Z

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
- replayed exactly: **35**
- display-rounding only: **0**
- mismatches: **0**
- not replayable: **0**


## Method labels

- rows checked: **35**; labels naming a different method than the inputs: **4**

  - `1079188` label “Research model estimate (Valve official ratings)” but inputs are `Own network model (bo3.gg results graph)` (family network) — expected an own-network label
  - `1081597` label “Research model estimate (Valve official ratings)” but inputs are `Own network model (bo3.gg results graph)` (family network) — expected an own-network label
  - `1082769` label “Research model estimate (Valve official ratings)” but inputs are `Own network model (bo3.gg results graph)` (family network) — expected an own-network label
  - `1082858` label “Research model estimate (Valve official ratings)” but inputs are `Own network model (bo3.gg results graph)` (family network) — expected an own-network label

## Hotspawn inventory parity

- API records: **97** (future starts: **35**, past-start records still marked scheduled: **62**)
- published open fixtures: **35**
- missing from the published site: **0** []
- published but not in the API: **0** []
- teams match: **True**; starts within 60 s: **True**; competitions match: **True**

- rendered lobby counts: `{"all_tiers_count": 97, "fixture_ids_in_html": ["1079188", "1079189", "1079650", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081143", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081597", "1081600", "1081869", "1081870", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082882"], "fixture_links_in_html": 30, "matches_this_week": 170}`
- rendered CS2 lobby counts: `{"all_tiers_count": 97, "fixture_ids_in_html": ["1079188", "1079189", "1079650", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081143", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081597", "1081600", "1081869", "1081870", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082882"], "fixture_links_in_html": 30, "matches_this_week": 170}`
- coverage counts: `{"api_records": 97, "lobby_cs2_all_tiers": 97, "lobby_equals_api": true, "lobby_equals_published_inventory": true, "lobby_this_week": 170, "published_inventory": 97, "published_upcoming": 35}`

## Official model inputs

- Valve snapshots read: ['2026-10-05']
- HLTV ranking HTTP: 200 (253 rows parsed)

  - `1079188` Research model estimate (Valve official ratings): own-model - row None vs published None — not-an-official-rating-row
  - `1079650` Valve-rating research estimate: Valve GenOne row 1185 vs published 1185.0 — match
  - `1079650` Valve-rating research estimate: Valve Spirit Academy row 981 vs published 981.0 — match
  - `1081143` Valve-rating research estimate: Valve BAKS row 1044 vs published 1044.0 — match
  - `1081143` Valve-rating research estimate: Valve Azuolas row 863 vs published 863.0 — match
  - `1079651` Valve-rating research estimate: Valve Butterfly row 1082 vs published 1082.0 — match
  - `1079651` Valve-rating research estimate: Valve Lavked row 862 vs published 862.0 — match
  - `1081596` Valve-rating research estimate: Valve Falcons Force row 806 vs published 806.0 — match
  - `1081596` Valve-rating research estimate: Valve Phantom Academy row 783 vs published 783.0 — match
  - `1081597` Research model estimate (Valve official ratings): own-model - row None vs published None — not-an-official-rating-row
  - `1082767` Valve-rating research estimate: Valve Nemesis row 1455 vs published 1455.0 — match
  - `1082767` Valve-rating research estimate: Valve WW row 1023 vs published 1023.0 — match
  - `1081600` Valve-rating research estimate: Valve DONSTU row 732 vs published 732.0 — match
  - `1081600` Valve-rating research estimate: Valve Banda Chuya row 801 vs published None — ambiguous-name
  - `1079652` Research model estimate (Valve official ratings): Valve Acend row 1197 vs published 1197.0 — match
  - `1079652` Research model estimate (Valve official ratings): Valve 6666 row 923 vs published None — ambiguous-name
  - `1081145` Valve-rating research estimate: Valve Lavked row 862 vs published 862.0 — match
  - `1081145` Valve-rating research estimate: Valve HAVU row 937 vs published 937.0 — match
  - `1082882` Own results-based estimate (bo3.gg series results): own-model - row None vs published None — not-an-official-rating-row
  - `1079653` Valve-rating research estimate: Valve Rune Eaters row 1110 vs published 1110.0 — match
  - `1079653` Valve-rating research estimate: Valve FORZE Reload row 1100 vs published 1100.0 — match
  - `1081146` Own results-based estimate (bo3.gg series results): own-model - row None vs published None — not-an-official-rating-row
  - `1082769` Research model estimate (Valve official ratings): own-model - row None vs published None — not-an-official-rating-row
  - `1081871` Research model estimate (Valve official ratings): Valve Lynn Vision row 1190 vs published 1190.0 — match
  - `1081871` Research model estimate (Valve official ratings): Valve Chinggis Warriors row 1084 vs published None — ambiguous-name
  - `1079654` Valve-rating research estimate: Valve ex-Zero Tenacity row 1066 vs published 1066.0 — match
  - `1079654` Valve-rating research estimate: Valve ex-RUSTEC row 1066 vs published None — ambiguous-name
  - `1079655` Valve-rating research estimate: Valve Nuclear TigeRES row 1324 vs published 1324.0 — match
  - `1079655` Valve-rating research estimate: Valve Illyrians row 862 vs published 862.0 — match
  - `1081148` Valve-rating research estimate: Valve Inner Circle Academy row 1064 vs published 1064.0 — match
  - `1081148` Valve-rating research estimate: Valve Spirit Academy row 981 vs published 981.0 — match
  - `1081149` Research model estimate (HLTV world ranking): HLTV FORZE Reload row 11.0 vs published 11.0 — match
  - `1081149` Research model estimate (HLTV world ranking): HLTV LFO 10 row 4.0 vs published 4.0 — match
  - `1079657` Research model estimate (Valve official ratings): Valve BAKS row 1044 vs published 1044.0 — match
  - `1079657` Research model estimate (Valve official ratings): Valve BRUTE row 1116 vs published None — ambiguous-name
  - `1081150` Valve-rating research estimate: Valve ex-RUSTEC row 1066 vs published None — ambiguous-name
  - `1081150` Valve-rating research estimate: Valve Saint Sinners row 810 vs published 810.0 — match
  - `1082858` Research model estimate (Valve official ratings): own-model - row None vs published None — not-an-official-rating-row
  - `1082859` Valve-rating research estimate: Valve NEXVOID row 995 vs published 995.0 — match
  - `1082859` Valve-rating research estimate: Valve Alter Ego row 819 vs published 819.0 — match
  - `1082860` Research model estimate (HLTV world ranking · unranked floor): HLTV FlyQuest row 16.0 vs published 16.0 — match
  - `1082860` Research model estimate (HLTV world ranking · unranked floor): HLTV Staqued row 0.0 vs published None — not-in-top-listing
  - `1082861` Valve-rating research estimate: Valve Rooster row 718 vs published 718.0 — match
  - `1082861` Valve-rating research estimate: Valve Abyssal row 734 vs published 734.0 — match
  - `1082792` Research model estimate (Valve official ratings): Valve HOTU row 1437 vs published 1437.0 — match
  - `1082792` Research model estimate (Valve official ratings): Valve The Huns row 944 vs published None — ambiguous-name
  - `1082793` Valve-rating research estimate: Valve 5star row 1110 vs published 1110.0 — match
  - `1082793` Valve-rating research estimate: Valve 1win row 1383 vs published 1383.0 — match

## Phone findability

- viewport meta: **True**
- nav landmarks: **5**
- in-site pick links on the summary: ['./origination/#picks']
- unresolved section on the summary: **True**
- rows on the picks page: **35**

## Verdicts

- PASS — inventory_and_picks_cover_every_active_fixture
- FAIL — every_active_fixture_has_a_directional_pick
- PASS — every_published_probability_replays_from_its_own_inputs
- PASS — published_pick_is_the_published_argmax
- FAIL — every_published_label_names_the_evidence_it_uses
- PASS — every_future_dated_hotspawn_fixture_is_published
- PASS — published_fixture_teams_and_times_match_the_api
- PASS — phone_summary_links_the_picks_list

## Unreadable requests

- none
