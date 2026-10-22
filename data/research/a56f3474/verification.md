# Independent verification — 2026-10-22T08:05:14Z

Read-only audit by session 416d93ee of `data`.

## Published snapshot

- `generated_at`: 2026-10-22T08:02:47Z
- inventory observed: 2026-10-22T08:02:22Z
- published counts: `{"archived": 64, "bookmaker": 3, "inventory": 107, "market": 15, "model": 14, "no_edge": 1, "picks": 31, "unknown_schedule": 0, "unresolved": 11, "upcoming": 43}`
- origination counts: `{"active": 43, "alias_joined": 5, "bookmaker": 6, "consensus": 3, "guidance": 0, "market": 15, "model": 19, "network": 2, "reference": 0, "relay": 1, "resolved": 43, "unresolved": 0, "with_pick": 42}`

## Pick coverage

- records in the complete list: **43**
- active fixtures: **43**
- active with probabilities: **43**
- active with a directional pick: **42**
- active without a pick: **1**

## Arithmetic replay

- rows with probabilities: **43**
- replayed exactly: **43**
- display-rounding only: **0**
- mismatches: **0**
- not replayable: **0**


## Method labels

- rows checked: **43**; labels naming a different method than the inputs: **0**


## Hotspawn inventory parity

- API records: **107** (future starts: **43**, past-start records still marked scheduled: **64**)
- published open fixtures: **43**
- missing from the published site: **0** []
- published but not in the API: **0** []
- teams match: **True**; starts within 60 s: **True**; competitions match: **True**

- rendered lobby counts: `{"all_tiers_count": 107, "fixture_ids_in_html": ["1079189", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081600", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082858", "1082859", "1082860", "1082861", "1082882", "1082897", "1082898", "1082900", "1082901", "1082919", "1082920", "1082921", "1082922", "1082923", "1082924", "1082925", "1082926"], "fixture_links_in_html": 40, "matches_this_week": 180}`
- rendered CS2 lobby counts: `{"all_tiers_count": 107, "fixture_ids_in_html": ["1079189", "1079651", "1079652", "1079653", "1079654", "1079655", "1079657", "1081145", "1081146", "1081148", "1081149", "1081150", "1081596", "1081600", "1081871", "1082180", "1082688", "1082689", "1082767", "1082769", "1082770", "1082792", "1082793", "1082858", "1082859", "1082860", "1082861", "1082882", "1082897", "1082898", "1082900", "1082901", "1082919", "1082920", "1082921", "1082922", "1082923", "1082924", "1082925", "1082926"], "fixture_links_in_html": 40, "matches_this_week": 180}`
- coverage counts: `{"api_records": 107, "lobby_cs2_all_tiers": 107, "lobby_equals_api": true, "lobby_equals_published_inventory": true, "lobby_this_week": 180, "published_inventory": 107, "published_upcoming": 43}`

## Official model inputs

- Valve snapshots read: ['2026-10-05']
- HLTV ranking HTTP: 403 (0 rows parsed)

  - `1079651` Valve-rating research estimate: Valve Butterfly row 1082 vs published 1082.0 — match
  - `1079651` Valve-rating research estimate: Valve Lavked row 862 vs published 862.0 — match
  - `1082919` Research model estimate (HLTV world ranking · unranked floor): HLTV Projeto do KinGui row 0.0 vs published None — not-in-top-listing
  - `1082919` Research model estimate (HLTV world ranking · unranked floor): HLTV Martians row 1.0 vs published None — not-in-top-listing
  - `1081600` Valve-rating research estimate: Valve DONSTU row 732 vs published 732.0 — match
  - `1081600` Valve-rating research estimate: Valve Banda Chuya row 801 vs published None — ambiguous-name
  - `1082922` Valve-rating research estimate: Valve Low Cortisol BR row 774 vs published 774.0 — match
  - `1082922` Valve-rating research estimate: Valve Grêmio row 654 vs published 654.0 — match
  - `1081871` Research model estimate (Valve official ratings): Valve Lynn Vision row 1190 vs published 1190.0 — match
  - `1081871` Research model estimate (Valve official ratings): Valve Chinggis Warriors row 1084 vs published None — ambiguous-name
  - `1079654` Valve-rating research estimate: Valve ex-Zero Tenacity row 1065.6 vs published 1066.0 — mismatch
  - `1079654` Valve-rating research estimate: Valve ex-RUSTEC row 1066.4 vs published None — ambiguous-name
  - `1079655` Valve-rating research estimate: Valve Nuclear TigeRES row 1324 vs published 1324.0 — match
  - `1079655` Valve-rating research estimate: Valve Illyrians row 862 vs published 862.0 — match
  - `1081149` Research model estimate (HLTV world ranking): HLTV FORZE Reload row 11.0 vs published None — not-in-top-listing
  - `1081149` Research model estimate (HLTV world ranking): HLTV LFO 10 row 4.0 vs published None — not-in-top-listing
  - `1082924` Valve-rating research estimate: Valve BORRACHEIROS row 706 vs published 706.0 — match
  - `1082924` Valve-rating research estimate: Valve QUINTESSÊNCIA row 723 vs published 723.0 — match
  - `1079657` Research model estimate (Valve official ratings): Valve BAKS row 1044 vs published 1044.0 — match
  - `1079657` Research model estimate (Valve official ratings): Valve BRUTE row 1116 vs published None — ambiguous-name
  - `1081150` Valve-rating research estimate: Valve ex-RUSTEC row 1066 vs published None — ambiguous-name
  - `1081150` Valve-rating research estimate: Valve Saint Sinners row 810 vs published 810.0 — match
  - `1082925` Own network estimate (bo3.gg results graph): own-model - row None vs published None — not-an-official-rating-row
  - `1082926` Research model estimate (HLTV world ranking): HLTV Isurus row 2.0 vs published None — not-in-top-listing
  - `1082926` Research model estimate (HLTV world ranking): HLTV Hacha row 2.0 vs published None — not-in-top-listing
  - `1082858` Own network estimate (bo3.gg results graph): own-model - row None vs published None — not-an-official-rating-row
  - `1082859` Valve-rating research estimate: Valve NEXVOID row 995 vs published 995.0 — match
  - `1082859` Valve-rating research estimate: Valve Alter Ego row 819 vs published 819.0 — match
  - `1082860` Research model estimate (HLTV world ranking · unranked floor): HLTV FlyQuest row 16.0 vs published None — not-in-top-listing
  - `1082860` Research model estimate (HLTV world ranking · unranked floor): HLTV Staqued row 0.0 vs published None — not-in-top-listing
  - `1082861` Valve-rating research estimate: Valve Rooster row 718 vs published 718.0 — match
  - `1082861` Valve-rating research estimate: Valve Abyssal row 734 vs published 734.0 — match
  - `1082792` Research model estimate (Valve official ratings): Valve HOTU row 1437 vs published 1437.0 — match
  - `1082792` Research model estimate (Valve official ratings): Valve The Huns row 944 vs published None — ambiguous-name
  - `1082793` Valve-rating research estimate: Valve 5star row 1110 vs published 1110.0 — match
  - `1082793` Valve-rating research estimate: Valve 1win row 1383 vs published 1383.0 — match

## Unresolved register

- register published on the summary: **False**

  - `1082926` Isurus vs Hacha: probabilities True, listed in the register False

## Verdicts

- PASS — inventory_and_picks_cover_every_active_fixture
- PASS — every_active_fixture_shows_a_probability_on_the_summary
- PASS — every_active_fixture_has_a_pick_or_a_published_even_estimate
- FAIL — every_side_less_row_is_listed_in_the_unresolved_register
- PASS — every_published_probability_replays_from_its_own_inputs
- PASS — published_pick_is_the_published_argmax
- PASS — every_published_label_names_the_evidence_it_uses
- PASS — every_future_dated_hotspawn_fixture_is_published
- PASS — published_fixture_teams_and_times_match_the_api

## Unreadable requests

- `https://www.hltv.org/ranking/teams` — 403
