# Independent verification of every published pick (session arena-3a010437)



Re-read started **2026-10-23T09:52:58Z** and finished **2026-10-23T09:53:03Z** against the snapshot collected at **2026-10-23T09:23:57Z** (30 active rows).

Each row is compared with the original source that row itself cites. Nothing is corrected here: the deltas are published so a reader can see them.

| Verdict | Rows |
| --- | --- |
| `confirmed` | 16 |
| `model_not_a_line` | 8 |
| `source_reachable` | 6 |

## Sources used for this re-read

- Official Hotspawn fixtures API: `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` — 92 records at 2026-10-23T09:52:58Z (HTTP 200). Every row's fixture id, both team names and scheduled start time are compared with this response.
- Price rows: the row's own published `source_api` (Polymarket Gamma event) or its cited URL. A reachable non-Polymarket surface is reported as reachability only; its price is not re-derived here.
- Rendered Hotspawn match page (one probe, `https://www.hotspawn.com/matches/nuclear-tigeres-vs-illyrians-cct-europe-2026-series-11-1079655`): HTTP 200, title "Nuclear TigeRES Vs ILLYRIANS Counter-Strike 2 Match At CCT Europe 2026 Series #11 - 1079655 - Hotspawn", readable. Identity therefore comes from the fixture API, not from the rendered page.
- Live inventory delta: 92 official records vs 92 in the audited snapshot; 0 id(s) in the API are not in the snapshot (observed 2026-10-23T09:53:05Z).

| # | Match | Method | Pick | Published | Identity (official API) | Re-read from the row's own source | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Nuclear TigeRES vs ILLYRIANS | market | Nuclear TigeRES | 0.845 / 0.155 | confirmed (id, both teams, start 2026-10-23T11:00:00Z) | Nuclear TigeRES 0.85 (+0.005 vs published); ILLYRIANS 0.15 (-0.005 vs published) · `https://gamma-api.polymarket.com/events/1233761` @ 2026-10-23T09:52:58Z | `confirmed` |
| 2 | Inner Circle Academy vs Spirit Academy | market | Spirit Academy | 0.445 / 0.555 | confirmed (id, both teams, start 2026-10-23T11:00:00Z) | Inner Circle Academy 0.445 (+0.000 vs published); Spirit Academy 0.555 (+0.000 vs published) · `https://gamma-api.polymarket.com/events/1232959` @ 2026-10-23T09:52:59Z | `confirmed` |
| 3 | Phantom Academy vs Banda chuya | model | Banda chuya | 0.475 / 0.525 | confirmed (id, both teams, start 2026-10-23T11:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 4 | JiJieHao vs Eternal Fire | market | Eternal Fire | 0.445 / 0.555 | confirmed (id, both teams, start 2026-10-23T13:00:00Z) | JiJieHao 0.445 (+0.000 vs published); Eternal Fire 0.555 (+0.000 vs published) · `https://gamma-api.polymarket.com/events/1237407` @ 2026-10-23T09:52:59Z | `confirmed` |
| 5 | Isurus vs Hacha | consensus | Isurus | 0.762 / 0.238 | confirmed (id, both teams, start 2026-10-23T13:00:00Z) | 200 reachability only · https://polymarket.com/event/cs2-isg-hachae-2026-10-23 @ 2026-10-23T09:52:59Z | `source_reachable` |
| 6 | LPH vs WBT Academy | bookmaker | WBT Academy | 0.378 / 0.622 | confirmed (id, both teams, start 2026-10-23T13:00:00Z) | 200 reachability only · https://bo3.gg/matches/lph-gaming-vs-wbt-academy-23-10-2026 @ 2026-10-23T09:52:59Z | `source_reachable` |
| 7 | K27 vs Virtus.pro | market | K27 | 0.555 / 0.445 | confirmed (id, both teams, start 2026-10-23T13:00:00Z) | K27 0.565 (+0.010 vs published); Virtus.pro 0.435 (-0.010 vs published) · `https://gamma-api.polymarket.com/events/1237740` @ 2026-10-23T09:53:00Z | `confirmed` |
| 8 | BORRACHEIROS vs QUINTESSÊNCIA | market | BORRACHEIROS | 0.640 / 0.360 | confirmed (id, both teams, start 2026-10-23T16:00:00Z) | BORRACHEIROS 0.635 (-0.005 vs published); QUINTESSÊNCIA 0.365 (+0.005 vs published) · `https://gamma-api.polymarket.com/events/1233764` @ 2026-10-23T09:53:00Z | `confirmed` |
| 9 | BakS vs BRUTE | consensus | BRUTE | 0.493 / 0.507 | confirmed (id, both teams, start 2026-10-23T17:00:00Z) | 200 reachability only · https://polymarket.com/event/cs2-brute-baks-2026-10-23 @ 2026-10-23T09:53:00Z | `source_reachable` |
| 10 | ex-RUSTEC vs Saint Sinners | market | ex-RUSTEC | 0.655 / 0.345 | confirmed (id, both teams, start 2026-10-23T17:00:00Z) | ex-RUSTEC 0.655 (+0.000 vs published); Saint Sinners 0.345 (+0.000 vs published) · `https://gamma-api.polymarket.com/events/1233765` @ 2026-10-23T09:53:01Z | `confirmed` |
| 11 | BESTIA vs Galorys | market | BESTIA | 0.565 / 0.435 | confirmed (id, both teams, start 2026-10-23T18:00:00Z) | BESTIA 0.565 (+0.000 vs published); Galorys 0.435 (+0.000 vs published) · `https://gamma-api.polymarket.com/events/1237874` @ 2026-10-23T09:53:01Z | `confirmed` |
| 12 | BESTIA Academy vs RED Canids Academy | market | RED Canids Academy | 0.410 / 0.590 | confirmed (id, both teams, start 2026-10-23T19:00:00Z) | BESTIA Academy 0.405 (-0.005 vs published); RED Canids Academy 0.595 (+0.005 vs published) · `https://gamma-api.polymarket.com/events/1233767` @ 2026-10-23T09:53:01Z | `confirmed` |
| 13 | paiN vs Imperial | market | Imperial | 0.360 / 0.640 | confirmed (id, both teams, start 2026-10-23T21:00:00Z) | paiN 0.335 (-0.025 vs published); Imperial 0.665 (+0.025 vs published) · `https://gamma-api.polymarket.com/events/1237875` @ 2026-10-23T09:53:01Z | `confirmed` |
| 14 | Alka vs LOS NINOS | bookmaker | Alka | 0.711 / 0.289 | confirmed (id, both teams, start 2026-10-23T22:00:00Z) | 200 reachability only · https://thunderpick.io/api/matches @ 2026-10-23T09:53:01Z | `source_reachable` |
| 15 | FOKUS vs ex-6666 | market | FOKUS | 0.770 / 0.230 | confirmed (id, both teams, start 2026-10-24T08:00:00Z) | FOKUS 0.765 (-0.005 vs published); ex-6666 0.235 (+0.005 vs published) · `https://gamma-api.polymarket.com/events/1237193` @ 2026-10-23T09:53:02Z | `confirmed` |
| 16 | Nuclear TigeRES vs FORZE Reload | market | Nuclear TigeRES | 0.590 / 0.410 | confirmed (id, both teams, start 2026-10-24T14:00:00Z) | Nuclear TigeRES 0.595 (+0.005 vs published); FORZE Reload 0.405 (-0.005 vs published) · `https://gamma-api.polymarket.com/events/1237195` @ 2026-10-23T09:53:02Z | `confirmed` |
| 17 | Acend vs UNiTY | model | Acend | 0.542 / 0.458 | confirmed (id, both teams, start 2026-10-25T09:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 18 | Metizport vs BakS | model | Metizport | 0.799 / 0.201 | confirmed (id, both teams, start 2026-10-25T12:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 19 | Infinite vs BRUTE | market | BRUTE | 0.445 / 0.555 | confirmed (id, both teams, start 2026-10-25T15:00:00Z) | Infinite 0.445 (+0.000 vs published); Brute 0.555 (+0.000 vs published) · `https://gamma-api.polymarket.com/events/1238706` @ 2026-10-23T09:53:02Z | `confirmed` |
| 20 | Color vs ex-Zero Tenacity | model | Color | 0.736 / 0.264 | confirmed (id, both teams, start 2026-10-25T18:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 21 | Ground Zero vs Off Chops | model | Off Chops | 0.445 / 0.555 | confirmed (id, both teams, start 2026-10-26T03:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 22 | NEXVOID vs Alter Ego | bookmaker | NEXVOID | 0.576 / 0.424 | confirmed (id, both teams, start 2026-10-26T03:00:00Z) | 200 reachability only · https://thunderpick.io/api/matches @ 2026-10-23T09:53:02Z | `source_reachable` |
| 23 | FlyQuest vs Staqued | bookmaker | FlyQuest | 0.923 / 0.077 | confirmed (id, both teams, start 2026-10-27T03:00:00Z) | 200 reachability only · https://thunderpick.io/api/matches @ 2026-10-23T09:53:02Z | `source_reachable` |
| 24 | Rooster vs Abyssal | model | Abyssal | 0.478 / 0.522 | confirmed (id, both teams, start 2026-10-27T03:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 25 | B8 vs K27 | market | B8 | 0.625 / 0.375 | confirmed (id, both teams, start 2026-10-27T08:00:00Z) | B8 0.62 (-0.005 vs published); K27 0.38 (+0.005 vs published) · `https://gamma-api.polymarket.com/events/1231333` @ 2026-10-23T09:53:02Z | `confirmed` |
| 26 | Alliance vs FaZe | market | FaZe | 0.345 / 0.655 | confirmed (id, both teams, start 2026-10-27T11:00:00Z) | Alliance 0.34 (-0.005 vs published); FaZe 0.66 (+0.005 vs published) · `https://gamma-api.polymarket.com/events/1231334` @ 2026-10-23T09:53:02Z | `confirmed` |
| 27 | Luminosity vs HOTU | market | Luminosity | 0.550 / 0.450 | confirmed (id, both teams, start 2026-10-27T17:00:00Z) | Luminosity 0.55 (+0.000 vs published); HOTU 0.45 (+0.000 vs published) · `https://gamma-api.polymarket.com/events/1231335` @ 2026-10-23T09:53:03Z | `confirmed` |
| 28 | Envy vs GamerLegion | market | GamerLegion | 0.465 / 0.535 | confirmed (id, both teams, start 2026-10-27T20:00:00Z) | Envy 0.465 (+0.000 vs published); GamerLegion 0.535 (+0.000 vs published) · `https://gamma-api.polymarket.com/events/1233851` @ 2026-10-23T09:53:03Z | `confirmed` |
| 29 | HOTU vs The Huns | model | HOTU | 0.941 / 0.059 | confirmed (id, both teams, start 2026-10-31T09:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |
| 30 | 5star vs 1WIN | model | 1WIN | 0.178 / 0.822 | confirmed (id, both teams, start 2026-10-31T13:00:00Z) | research-model estimate: there is no published price to re-read | `model_not_a_line` |

## Flagged for review

No row conflicts with a re-read of its own source in this window. This is a dated observation, not a guarantee: a research-model row has no price to re-read, and a non-Polymarket money row is confirmed only as reachable.
