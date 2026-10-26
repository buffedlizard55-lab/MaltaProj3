# Session arena-b3e91409 — live evidence, independent replay, and the review register

Read this directory with the published artefacts it verifies. Nothing here is hand-written: every
figure is either an observed source value or a value re-derived by the scripts below.

| File | What it is | How to replay |
| --- | --- | --- |
| `live/manifest.json` | every HTTP request the probe made: URL, method, UTC time, status, bytes, SHA-256, cache headers | compare a row with the file named in its `evidence` field |
| `live/sources.json` | per-source summary (record counts, open fixtures, page ids, cache state) | open the URL at the recorded time |
| `live/hotspawn-fixtures-api.json`, `live/hotspawn-lobby.html.gz`, `live/hotspawn-cs2.html.gz` | the Hotspawn inventory that defines "every match" | gunzip and read the embedded fixture array |
| `live/hltv-cards.json`, `live/hltv-ranking.json`, `live/hltv-matches.html.gz`, `live/hltv-ranking.html.gz` | HLTV identities and the official world ranking | `https://www.hltv.org/matches`, `https://www.hltv.org/ranking/teams` |
| `live/polymarket-events.json`, `live/polymarket-page-*.json` | the official CS2-tag events read page by page, with the exact page URLs and hashes | `https://gamma-api.polymarket.com/events?tag_slug=counter-strike-2&limit=100&offset=N` |
| `live/thunderpick-matches.json` | the public Thunderpick match feed (47 rows at 00:51Z) | `POST https://thunderpick.io/api/matches` with `{"gameIds":[6]}` |
| `live/valve-standings.md`, `live/valve-directory.json` | the newest official Valve global standings on/before the observation date | `https://github.com/ValveSoftware/counter-strike_regional_standings` |
| `live/analysis.json`, `live/summary.md` | one documented line per open fixture: the identity join, every source tried, the observed quotes, the formula and the pick | `python -m scripts.b3e91409_research` (needs the live files above) |
| `published/origination.json`, `published/snapshot.json` | byte-for-byte copies of the published 2026-10-26T01:04:30Z build this session verified (sha256 in `verification.json`) | `python -m scripts.b3e91409_verify --origination data/research/b3e91409/published/origination.json --snapshot data/research/b3e91409/published/snapshot.json` |
| `verification.json`, `verification.md` | the replay result: one row per published fixture, the re-derived probabilities, the delta, and every finding | same command as above |
| `repo-review.json` | the register rendered on `/review/` (B3-R01..B3-R10) | `python -m scripts.build` then open `site/review/` |

## Rules this session applied

- **Identity** is exact Unicode/case/whitespace-equivalent naming plus a start time within 60 seconds.
  A near miss is recorded with its reason, never joined. Provider display names join only through the
  reviewed, competition-scoped registry in `data/origination/aliases.json` — this session added no alias.
- **Prices** are only ever observed two-way quotes: an exchange order book with both sides two-sided
  (and at most a 0.10 spread), or a bookmaker pair with a margin between 0.85 and 1.35. A midpoint from
  a one-sided or 0.90-wide book is refused and the refusal is published.
- **Models** print their formula and their published inputs (points, rating deviation, ranks). A fitted
  results model that does not publish its predictive formula is reported as not replayable.
- **Never used**: Hotspawn community `% picked`, HLTV fan votes, inferred or default values.

## What the two runs found

1. **00:51–00:54Z (before the refresh):** 19 open Hotspawn fixtures, 10 published rows. Nine fixtures
   had no row; every one of them could be priced from an observed source (6 Polymarket series books,
   3 Thunderpick two-way lines, the rest from printed rating points). Report: B3-R01.
2. **01:04–01:22Z (after the 00:43Z refresh):** 19 published rows, 19 picks, 0 unresolved. 18 of 19
   probabilities re-derive exactly from the row's own inputs; one fitted form model does not publish
   its formula (B3-R08). All 19 published picks agree with this session's independent side.

## Limitations of the checks themselves (found and fixed in this session)

- **The limitation text lives on the row, not in the nested analysis.** Rows publish
  `matches[].limitations` (a list) while the replay used to look only inside the nested `origination`
  object, so it reported three false "publishes no limitation text" notes on an artefact that discloses
  all three. The checker now reads both places and `tests/test_b3e91409_verification.py::LimitationTests`
  pins the behaviour in each direction. B3-R06 is closed as a checker defect, not a data gap.
- **A no-JS read of the HTML includes text from `hidden` nodes.** `#stale-warning` ("Do not treat these
  as current picks") and `#new-snapshot` are rendered with `hidden` unless the build is actually stale,
  and a text extractor that ignores HTML attributes shows both on a fresh page. They are not live
  defects; confirm against the element's `hidden` attribute or `site/assets/scout.js` (which toggles it)
  before filing a finding.
- **The committed `site/` directory is a build of the 2026-10-15 data** (`site/data/latest.json`). The
  four-hourly workflow collects, rebuilds and root-syncs the fresh site; a local `python -m scripts.build`
  reproduces the *committed* artefacts, not the deployed ones. Verify the deployed numbers against
  `https://buffedlizard55-lab.github.io/MaltaProj3/origination.json` and a freshly fetched `index.html`,
  which is what the probe workflow's served-site gate does.

## The served-site gate (`.github/workflows/b3e91409-probe.yml`)

Every probe run now also fetches `index.html`, `origination.json` and `snapshot.json` from the deployed
site, replays every published probability from its own inputs, checks the executive summary's phone
route (`origination/#picks`, `picks/`, `unresolved/`, `coverage/`, `methodology/`, `#picks-at-a-glance`,
`#unresolved-register`) and one `#match-<id>` deep link per published row, and commits the report to
`data/research/b3e91409/served/`. The gate step exits non-zero when a served number does not replay;
the evidence commit still runs (`if: always()`).
