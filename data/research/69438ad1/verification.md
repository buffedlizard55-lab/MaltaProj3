# arena-69438ad1 — published site vs live Hotspawn source

Observed: 2026-10-23T05:41:16Z (GitHub Actions runner)

- Published snapshot: generated 2026-10-22T14:05:35Z · inventory 2026-10-22T13:21:33Z · age 15.59h · coverage_complete False · run_status degraded
- Live source: 0 scheduled CS2 records, 0 still prematch
- Published active rows: 37 (37 with a directional pick, 0 explicit even, 0 failing the reading contract)
- Live prematch fixtures missing from the published active list: 0
- Published active fixtures absent from the live source: 37

## Live prematch fixtures not on the published site

- none: every live prematch fixture is on the published site

## Row contract

- every active row carries both probabilities, a pick (or an explicit even rule) and an https official source link

## Source reads

- published_latest: HTTP 200 · x-cache MISS · sha256 c275334fca51 · https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json?cb=1792734076
- published_origination: HTTP 200 · x-cache MISS · sha256 f33c2c94f466 · https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json?cb=1792734076
- published_row_audit: HTTP 200 · x-cache MISS · sha256 3bb352e17c76 · https://buffedlizard55-lab.github.io/MaltaProj3/data/row-source-audit.json?cb=1792734076
- live_lobby: HTTP 403 · x-cache None · sha256 269b3a43ad6c · https://play.hotspawn.com/lobby?cb=1792734076
- live_cs2_lobby: HTTP 403 · x-cache None · sha256 269b3a43ad6c · https://play.hotspawn.com/cs2-pickems?cb=1792734076
- live_fixtures_api: HTTP 403 · x-cache None · sha256 269b3a43ad6c · https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1
