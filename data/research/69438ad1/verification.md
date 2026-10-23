# arena-69438ad1 — published site vs live Hotspawn source

Observed: 2026-10-23T05:50:52Z (GitHub Actions runner)

- Published snapshot: generated 2026-10-22T14:05:35Z · inventory 2026-10-22T13:21:33Z · age 15.75h · coverage_complete False · run_status degraded
- Live source: 92 scheduled CS2 records, 30 still prematch
- Published active rows: 37 (37 with a directional pick, 0 explicit even, 0 failing the reading contract)
- Live prematch fixtures missing from the published active list: 10
- Published active fixtures absent from the live source: 17

## Live prematch fixtures not on the published site

- 1081605 — Phantom Academy vs Banda chuya — CCT Europe 2026 Challengers #8 — 2026-10-23T11:00:00Z — https://www.hotspawn.com/matches/phantom-academy-vs-banda-chuya-cct-europe-2026-challengers-8-1081605
- 1081606 — JiJieHao vs Eternal Fire — DraculaN Season 7 — 2026-10-23T13:00:00Z — https://www.hotspawn.com/matches/jijiehao-vs-eternal-fire-draculan-season-7-1081606
- 1083014 — K27 vs Virtus.pro — CIS LAN Championship #9 — 2026-10-23T13:00:00Z — https://www.hotspawn.com/matches/k27-vs-virtus-pro-cis-lan-championship-9-1083014
- 1082693 — BESTIA vs Galorys — Circuit X Curitiba #4 — 2026-10-23T18:00:00Z — https://www.hotspawn.com/matches/bestia-vs-galorys-circuit-x-curitiba-4-1082693
- 1079193 — FOKUS vs ex-6666 — NODWIN Clutch Series #13 — 2026-10-24T08:00:00Z — https://www.hotspawn.com/matches/fokus-vs-ex-6666-nodwin-clutch-series-13-1079193
- 1079195 — Nuclear TigeRES vs FORZE Reload — NODWIN Clutch Series #13 — 2026-10-24T14:00:00Z — https://www.hotspawn.com/matches/nuclear-tigeres-vs-forze-reload-nodwin-clutch-series-13-1079195
- 1082996 — Acend vs UNiTY — NODWIN Clutch Series #13 — 2026-10-25T09:00:00Z — https://www.hotspawn.com/matches/acend-vs-unity-nodwin-clutch-series-13-1082996
- 1079198 — Metizport vs BakS — NODWIN Clutch Series #13 — 2026-10-25T12:00:00Z — https://www.hotspawn.com/matches/metizport-vs-baks-nodwin-clutch-series-13-1079198
- 1079199 — Infinite vs BRUTE — NODWIN Clutch Series #13 — 2026-10-25T15:00:00Z — https://www.hotspawn.com/matches/infinite-vs-brute-nodwin-clutch-series-13-1079199
- 1079200 — Color vs ex-Zero Tenacity — NODWIN Clutch Series #13 — 2026-10-25T18:00:00Z — https://www.hotspawn.com/matches/color-vs-ex-zero-tenacity-nodwin-clutch-series-13-1079200

## Row contract

- every active row carries both probabilities, a pick (or an explicit even rule) and an https official source link

## Source reads

- published_latest: HTTP 200 · x-cache MISS · sha256 c275334fca51 · https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json?cb=1792734652
- published_origination: HTTP 200 · x-cache MISS · sha256 f33c2c94f466 · https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json?cb=1792734652
- published_row_audit: HTTP 200 · x-cache MISS · sha256 3bb352e17c76 · https://buffedlizard55-lab.github.io/MaltaProj3/data/row-source-audit.json?cb=1792734652
- live_lobby: HTTP 200 · x-cache MISS · sha256 89c796cb5e60 · https://play.hotspawn.com/lobby?cb=1792734652
- live_cs2_lobby: HTTP 200 · x-cache MISS · sha256 1ddbb2664812 · https://play.hotspawn.com/cs2-pickems?cb=1792734652
- live_fixtures_api: HTTP 200 · x-cache None · sha256 4341be819f04 · https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1
