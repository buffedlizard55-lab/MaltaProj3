# Independent verification — 2026-10-22T02:05:00Z

Read-only audit by session 416d93ee of `https://buffedlizard55-lab.github.io/MaltaProj3`.

## Published snapshot

- `generated_at`: 2026-10-15T08:36:13Z
- inventory observed: 2026-10-15T08:36:04Z
- published counts: `{"archived": 63, "bookmaker": 1, "inventory": 80, "market": 7, "model": 5, "no_edge": 0, "picks": 13, "unknown_schedule": 0, "unresolved": 4, "upcoming": 17}`
- origination counts: `{"active": 17, "alias_joined": 4, "bookmaker": 5, "consensus": 0, "market": 7, "model": 5, "resolved": 17, "unresolved": 0, "with_pick": 17}`

## Pick coverage

- records in the complete list: **17**
- active fixtures: **17**
- active with probabilities: **17**
- active with a directional pick: **17**
- active without a pick: **0**

## Arithmetic replay

- rows with probabilities: **17**
- replayed exactly: **17**
- display-rounding only: **0**
- mismatches: **0**
- not replayable: **0**


## Method labels

- rows checked: **17**; labels naming a different method than the inputs: **0**


## Hotspawn inventory parity

- API records: **97** (future starts: **35**, past-start records still marked scheduled: **62**)
- published open fixtures: **17**
- missing from the published site: **35** ['1079188', '1079189', '1079650', '1079651', '1079652', '1079653', '1079654', '1079655', '1079657', '1081143', '1081145', '1081146', '1081148', '1081149', '1081150', '1081596', '1081597', '1081598', '1081600', '1081869', '1081870', '1081871', '1082180', '1082688', '1082689', '1082767', '1082769', '1082770', '1082792', '1082793', '1082858', '1082859', '1082860', '1082861', '1082882']
- published but not in the API: **17** ['1079440', '1079442', '1080202', '1080203', '1080204', '1080280', '1080281', '1080282', '1080283', '1080284', '1080285', '1080286', '1080287', '1080288', '1080289', '1080290', '1081120']
- teams match: **True**; starts within 60 s: **True**; competitions match: **True**

- rendered lobby counts: `{"all_tiers_count": 97, "fixture_ids_in_html": ["1079188", "1079189", "1079650", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081143", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081597", "1081600", "1081869", "1081870", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082882"], "fixture_links_in_html": 30, "matches_this_week": 170}`
- rendered CS2 lobby counts: `{"all_tiers_count": 97, "fixture_ids_in_html": ["1079188", "1079189", "1079650", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081143", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081597", "1081600", "1081869", "1081870", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082882"], "fixture_links_in_html": 30, "matches_this_week": 170}`
- coverage counts: `{"api_records": 97, "lobby_cs2_all_tiers": 97, "lobby_equals_api": true, "lobby_equals_published_inventory": false, "lobby_this_week": 170, "published_inventory": 80, "published_upcoming": 17}`

## Official model inputs

- Valve snapshots read: ['2026-10-05']
- HLTV ranking HTTP: 200 (253 rows parsed)

  - `1080202` Valve-rating research estimate: Valve 9z row 1543 vs published 1543.0 — match
  - `1080202` Valve-rating research estimate: Valve Falcons row 1843 vs published 1843.0 — match
  - `1080203` Valve-rating research estimate: Valve PARIVISION row 1411 vs published 1411.0 — match
  - `1080203` Valve-rating research estimate: Valve BETBOOM row 1596 vs published 1596.0 — match
  - `1080282` Valve-rating research estimate: Valve EAC row 1035 vs published 1035.0 — match
  - `1080282` Valve-rating research estimate: Valve BOJONG row 463 vs published 463.0 — match
  - `1080284` Valve-rating research estimate: Valve EAC row 1035 vs published 1035.0 — match
  - `1080284` Valve-rating research estimate: Valve ENCE row 1025 vs published 1025.0 — match
  - `1081120` Valve-rating research estimate: Valve mellren row 932 vs published 932.0 — match
  - `1081120` Valve-rating research estimate: Valve Privateer row 608 vs published 608.0 — match

## Phone findability

- viewport meta: **True**
- nav landmarks: **3**
- in-site pick links on the summary: ['./origination/#picks']
- unresolved section on the summary: **True**
- rows on the picks page: **17**

## Unresolved register

- register published on the summary: **True**


## Verdicts

- PASS — inventory_and_picks_cover_every_active_fixture
- PASS — every_active_fixture_shows_a_probability_on_the_summary
- PASS — every_active_fixture_has_a_pick_or_a_published_even_estimate
- PASS — every_side_less_row_is_listed_in_the_unresolved_register
- PASS — every_published_probability_replays_from_its_own_inputs
- PASS — published_pick_is_the_published_argmax
- PASS — every_published_label_names_the_evidence_it_uses
- FAIL — every_future_dated_hotspawn_fixture_is_published
- PASS — published_fixture_teams_and_times_match_the_api
- PASS — phone_summary_links_the_picks_list

## Unreadable requests

- none
