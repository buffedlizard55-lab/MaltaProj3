# arena-69438ad1 — published site vs live Hotspawn source

Observed: 2026-10-23T07:27:12Z (GitHub Actions runner)

- Published snapshot: generated 2026-10-23T07:08:13Z · inventory 2026-10-23T07:07:52Z · age 0.32h · coverage_complete True · run_status partial-picks
- Live source: 93 scheduled CS2 records, 32 still prematch
- Published active rows: 32 (32 with a directional pick, 0 explicit even, 0 failing the reading contract)
- Live prematch fixtures missing from the published active list: 0
- Published active fixtures absent from the live source: 0

## Live prematch fixtures not on the published site

- none: every live prematch fixture is on the published site

## Row contract

- every active row carries both probabilities, a pick (or an explicit even rule) and an https official source link

## Source reads

- published_latest: HTTP 200 · x-cache MISS · sha256 e274b666897c · https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json?cb=1792740432
- published_origination: HTTP 200 · x-cache MISS · sha256 ef8201429043 · https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json?cb=1792740432
- published_row_audit: HTTP 200 · x-cache MISS · sha256 8f18e34407b4 · https://buffedlizard55-lab.github.io/MaltaProj3/data/row-source-audit.json?cb=1792740432
- live_lobby: HTTP 200 · x-cache MISS · sha256 d45eddf02077 · https://play.hotspawn.com/lobby?cb=1792740432
- live_cs2_lobby: HTTP 200 · x-cache MISS · sha256 be886b523704 · https://play.hotspawn.com/cs2-pickems?cb=1792740432
- live_fixtures_api: HTTP 200 · x-cache None · sha256 7309d2a1f6f4 · https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1
