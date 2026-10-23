# arena-69438ad1 — published site vs live Hotspawn source

Observed: 2026-10-23T06:21:09Z (GitHub Actions runner)

- Published snapshot: generated 2026-10-23T06:17:47Z · inventory 2026-10-23T06:17:26Z · age 0.06h · coverage_complete True · run_status partial-picks
- Live source: 94 scheduled CS2 records, 32 still prematch
- Published active rows: 32 (32 with a directional pick, 0 explicit even, 0 failing the reading contract)
- Live prematch fixtures missing from the published active list: 0
- Published active fixtures absent from the live source: 0

## Live prematch fixtures not on the published site

- none: every live prematch fixture is on the published site

## Row contract

- every active row carries both probabilities, a pick (or an explicit even rule) and an https official source link

## Source reads

- published_latest: HTTP 200 · x-cache MISS · sha256 cd7d1a47c4d6 · https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json?cb=1792736469
- published_origination: HTTP 200 · x-cache MISS · sha256 bdb73a0048c2 · https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json?cb=1792736469
- published_row_audit: HTTP 200 · x-cache MISS · sha256 72fbb62e25ee · https://buffedlizard55-lab.github.io/MaltaProj3/data/row-source-audit.json?cb=1792736469
- live_lobby: HTTP 200 · x-cache MISS · sha256 9c19e407e041 · https://play.hotspawn.com/lobby?cb=1792736469
- live_cs2_lobby: HTTP 200 · x-cache MISS · sha256 1feb09581ced · https://play.hotspawn.com/cs2-pickems?cb=1792736469
- live_fixtures_api: HTTP 200 · x-cache None · sha256 4f08ea11e16d · https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1
