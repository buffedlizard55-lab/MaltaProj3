# Session 9e0e601d — live audit of the deployed dashboard (25 October 2026)

Everything here was read from the live host or the repository from a GitHub
Actions runner, because this session's sandbox cannot open a TCP connection to
`play.hotspawn.com`, `hltv.org`, `buffedlizard55-lab.github.io` or any
esportsbook (`curl` fails with `SSL_ERROR_SYSCALL` before a status line). The
dossiers are replayable offline:

```
python -m scripts.9e0e601d_audit --replay \
  --output data/research/9e0e601d/replay --raw data/research/9e0e601d/raw
```

## What the third-party surfaces published

| Surface | Observation | Result |
| --- | --- | --- |
| Hotspawn scheduled-fixture API | 2026-10-25T15:01:35Z | HTTP 200, 77 records, **15** starting in the future |
| Hotspawn rendered lobby | 2026-10-25T15:01:35Z | **15** fixture ids, identical to the API set both ways |
| HLTV upcoming matches | 2026-10-25T15:01:36Z | HTTP 200, parsed cards available for identity joins |
| HLTV world ranking 19 Oct | 2026-10-25T15:01:37Z | HTTP 200 |
| Polymarket CS2 tag | 2026-10-25T15:01:38Z | HTTP 200 |
| Thunderpick public match feed | 2026-10-25T15:01:38Z | HTTP 200, two-way Match Winner prices for 5 of the researched fixtures |
| EGamersWorld match directory | 2026-10-25T15:01:39Z | HTTP **403** to the runner |

Every response body is archived under `raw/` with its byte count and SHA-256 in
`audit.json`, so no number below depends on a memory of a page.

## The deployed dashboard, measured rather than assumed

| Artefact | Observation it serves |
| --- | --- |
| `index.html` | inventory checked **2026-10-25T14:31:56Z**, 16 glance rows, 16 deep links |
| `snapshot.json` | generated **2026-10-25T14:32:11Z** |
| `data/origination.json` | generated **2026-10-15T09:31:24Z** |
| `data/latest.json` | generated **2026-10-15T08:36:13Z** |

The served page is byte-identical to the branch-root `index.html`
(SHA-256 `b5db80d4ec3c945483f1d23541a6a843c74bf0ec6aa9df7eed17c6aa4b365466`), so
GitHub Pages is serving the branch root. That single fact explains two defects
at once: the two downloads the page links under `data/` are the checked-in
replay fixtures (245 h older than the page), and the per-row evidence files the
fresh build refers to were never carried into the root.

Of the 24 local `data/...` downloads the summary links, **9 answered 200 and 15
answered 404** at 15:04:56Z — every saved Polymarket order book and event
capture for the current fixtures (events 1238706, 1238707, 1243020, 1248800,
1249433).

## Every published number re-derived

| Population | Re-derived | Not replayable | Structural violations |
| --- | --- | --- | --- |
| Complete picks list (`data/origination.json`) | **17/17** | 0 | 0 |
| Featured snapshot (`snapshot.json`) | **13/13** | 0 | 0 |

The earlier replay covered the three featured methods only. This one also
re-derives consensus medians, relayed and aggregated bookmaker prices, and the
Valve, HLTV, network and form research models:

* `market` — the two-sided midpoints, proportionally normalised;
* `bookmaker` / `reference` — `(1/oᵢ) / Σ(1/o)`, including the single-quote
  `odds: [a, b]` shape an esportsbook uses;
* `consensus` — the median of the contributing providers' first side, mirrored
  and normalised;
* `model` — Valve's logistic expectation from the published points, RD and `g`;
  HLTV ranking points on the 400 scale; the network Bradley–Terry expectation;
  the form model's `150 + 300/√n` RD against the published `n_series`.

A row that cannot be reproduced from its own published inputs is reported as
"not replayed" with the reason, never as a pass.

## What was fixed in this session

1. **The four-hour publisher was red again.** The 14:34Z refresh
   ([run 40202907756](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40202907756))
   failed at *Regression tests* because a dossier assertion required fixture
   `1081156` to exist in the checked-in replay snapshot. That fixture predates
   the snapshot by days, so the assertion could never hold. The rule now matches
   the contract its own docstring states: compare only what a dossier actually
   attributes to the board, and require an https evidence URL plus a UTC
   observation time when the row is absent. Three tests pin it, including a
   mutation case that still fails closed.
2. **The downloads a page links are published with it.** The build writes
   `origination.json` and `picks.csv` at the site root and the pages link those;
   the branch-root publisher now carries every local download the published
   pages reference, and skips (and prints) any path git already tracks so a
   publish can never overwrite the deterministic replay fixture.

## What remains open (published on *Flagged for Review*)

* **9E-R02 / 9E-R03** — the 15 dead evidence links and the page/download parity
  gap disappear on the first root sync after this merge; both are re-checked by
  every audit run, so the next dossier shows whether they cleared.
* **9E-R06** — Hotspawn schedules fixture `1086696` at 16:00Z; HLTV lists the
  same pairing one hour earlier. Outside the 60-second identity window, so the
  two are not joined.
* **9E-R07** — `1086697` carries a team name HLTV does not list against the same
  opponent. No alias was invented.
* **9E-R08** — EGamersWorld answers 403 to runners, and the Hotspawn fixture API
  answers 400 when an unknown query parameter is appended (a cache-buster empties
  the inventory instead of failing loudly).
* **9E-R09** — Thunderpick's `1.001 / 12.0` for `1082860` is recorded as an
  observation, not as a usable probability.

Hotspawn `% picked` and HLTV fan votes were never read as inputs. This session
wrote no probability, pick or alias.
