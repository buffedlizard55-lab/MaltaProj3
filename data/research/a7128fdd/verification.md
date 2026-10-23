# Line-by-line verification of the published snapshot (arena-a7128fdd)

> Generated from `verification.json` by `python -m scripts.a7128fdd_render_evidence`.

Verified **2026-10-23T10:45:00Z**. Every arithmetic result below is re-derivable from the linked source with the repository's own de-vig rule.

## 1. The published page and the downloadable snapshot are one observation

- Live root `data/latest.json` `generated_at`: `2026-10-23T09:23:57Z`
- Live root page stamp: `2026-10-23T09:23:57Z`
- Agree: **True**

Acceptance-audit check #9 (page stamp == downloadable data/latest.json) was the last standing FAIL in session 3149e7ae's published-root audits at 05:05Z, 07:25Z and 08:20Z on 2026-10-23. Read back from the live published root at 09:45Z both carry 2026-10-23T09:23:57Z, so that FAIL is closed on main. Re-verified locally: scripts.acceptance_audit --site site reports 9 pass / 1 info / 0 fail; the single info is the checked-in 15 October replay fixture's age, not a live defect.

Sources: <https://buffedlizard55-lab.github.io/MaltaProj3/data/latest.json> · <https://buffedlizard55-lab.github.io/MaltaProj3/>

## 2. The published inventory count equals what the source API returned

- Read `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` directly at 2026-10-23T09:46:00Z: **92** records
- Published counts: inventory **92**, upcoming **30**
- Agree: **True**

The published inventory count equals the number of records the source API returned when read directly, and the published upcoming count equals the active rows in the runner manifest taken from the same feed (run 39934809201).

## 3. Published probabilities re-derived from independent surfaces

Each independent price was de-vigged with the repository's own documented rule p_i = (1/o_i) / sum(1/o), then aligned to Hotspawn's team order by resolving BOTH sides through scripts.originate.resolve_name against data/origination/aliases.json (69 reviewed, competition-scoped entries) - not through an ad-hoc normaliser. That matters: scripts.domain.name_key deliberately keeps diacritics ('Los Niños' != 'LOS NINOS'), so a naive fold-free comparison silently fails to bind names the registry has already reviewed and scoped. A row is reported as an exact match only when both sides agree to within 5e-5. Nothing here changed a published value; it only re-derives it from a second surface.

| Hotspawn id | Fixture | Published | Independent source | Odds as published | Re-derived | Exact |
| --- | --- | --- | --- | --- | --- | --- |
| 1082923 | Alka vs LOS NINOS | 0.7111 / 0.2889 (bookmaker) | [bo3.gg relay board](https://bo3.gg/matches/alka-vs-los-ninos-23-10-2026) | ALKA 1.3 / Los Niños 3.2 | 0.7111 / 0.2889 | **yes** |
| 1082980 | LPH vs WBT Academy | 0.3782 / 0.6218 (bookmaker) | [bo3.gg relay board](https://bo3.gg/matches/lph-gaming-vs-wbt-academy-23-10-2026) | WBT Academy 1.49 / LPH 2.45 | 0.3782 / 0.6218 | **yes** |
| 1081148 | Inner Circle Academy vs Spirit Academy | 0.4450 / 0.5550 (market) | [bo3.gg relay board](https://bo3.gg/matches/inner-circle-academy-vs-spirit-academy-23-10-2026) | Inner Circle Academy 2.1 / Spirit Academy 1.65 | 0.4400 / 0.5600 | no (delta 0.005) |
| 1081148 | Inner Circle Academy vs Spirit Academy | 0.4450 / 0.5550 (market) | [esports-news.co.uk](https://esports-news.co.uk/matches/cs2/inner-circle-academy-vs-spirit-academy-1746765/) | Inner Circle Academy 2.17 / Spirit Academy 1.72 | 0.4422 / 0.5578 | no (delta 0.0028) |
| 1083014 | K27 vs Virtus.pro | 0.5650 / 0.4350 (market) | [esports-news.co.uk](https://esports-news.co.uk/matches/cs2/k27-vs-virtus-pro-75b4744b-43d9-4ebd-a8dc-f1e0f9be69b3-1759614/) | K27 1.76 / Virtus.pro 2.05 | 0.5381 / 0.4619 | no (delta 0.0269) |
| 1079655 | Nuclear TigeRES vs ILLYRIANS | 0.8500 / 0.1500 (market) | [esports-news.co.uk](https://esports-news.co.uk/matches/cs2/nuclear-tigres-vs-illyrians-1733090/) | Nuclear TigeRES 1.11 / ILLYRIANS 6.5 | 0.8541 / 0.1459 | no (delta 0.0041) |

- Rows checked: **6**
- Exact four-decimal reproductions: **2**
- Directionally agreeing but from a different surface: **4**
- Name bindings left unresolved: **0**
- Published values changed by this verification: **0**

2 of 6 independently re-derived probabilities reproduce the published value to four decimal places once both sides are bound through the reviewed alias registry. Those rows prove the ladder is reading its relay board and de-vigging it exactly as documented. The other 4 agree in direction and differ only slightly because they come from a different surface than the one that priced the row (a Polymarket CLOB midpoint rather than a bo3.gg relay, or one aggregator's book rather than another's), which is expected and is not a defect. No published probability, pick or alias was changed by this verification.
