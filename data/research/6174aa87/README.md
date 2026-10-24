# Session arena-6174aa87 — research of record

Dated, first-hand evidence for this session's work. Nothing here changes a pick,
a probability or an alias: the reviewed ladder in `scripts/originate.py` remains
the only path to a published number.

| File | What it is |
| - | - |
| `pick-provenance.json` | The machine-readable sweep: every active fixture, its published pick, every URL that pick cites, the HTTP answer for each, and the verdict. |
| `pick-provenance.md` | The same sweep as tables for manual review, including a per-URL citation table with page titles and the record that confirmed each one. |
| `flags.json` | The findings raised by that sweep, in the site's `review` schema, published on **Flagged for Review**. |
| `mobile-check.json` | Layout checks of the published pages at 390 px and 320 px (no horizontal overflow, tappable bottom bar, readable probability text, picks reachable inside one screen). |
| `screenshots/` | The screenshots those checks measured. |

## How a row is judged

* `verified` — every cited URL answered and at least one named both teams (or
  contained the exact event id the ladder bound), and the row's own two
  probabilities add up with the pick on the larger side.
* `verified-with-open-citations` — a price citation is confirmed, but a
  secondary citation (for example an HLTV identity page) was refused on this
  sweep. The refusal is recorded, not hidden.
* `needs-review` — no cited price could be confirmed, or the only citations are
  provider-wide endpoints that the read could not bind to this fixture.

A blocked request is never recorded as "no market exists", and a page answering
HTTP 200 is never treated as a price by itself.

## Sources this sweep reads first-hand

| Source | Role | Endpoint |
| - | - | - |
| Hotspawn | identity, schedule, lock time | `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2&status=scheduled&tenantId=1` |
| Polymarket | exchange order book | the cited `polymarket.com/event/…` page, then its Gamma record `gamma-api.polymarket.com/events?slug=…` |
| Kalshi | regulated exchange | the cited market page, then `api.elections.kalshi.com/trade-api/v2/markets/<ticker>` |
| Thunderpick | esportsbook | `thunderpick.io/api/matches` (POST `{"gameIds":[6]}`, the same call `scripts/collect.py` uses) |
| Bovada | esportsbook | the cited coupon page |
| Smarkets | exchange | the cited market page, then `api.smarkets.com/v3/events/` |
| bo3.gg | published bookmaker relay and results graph | `api.bo3.gg/api/v1/matches` |
| EGamersWorld | published bookmaker average | the cited match page |
| HLTV | identity and ranking only — **never a price** | `hltv.org/matches/<id>/…` |
| Valve | official regional standings (research model input) | `github.com/ValveSoftware/counter-strike_regional_standings` |

HLTV fan votes and Hotspawn "% picked" are popularity, not probability, and are
not read as lines anywhere in this repository.

## Reproducing it

The Arena coding sandbox has no egress to these hosts; a GitHub runner does. The
workflow `.github/workflows/6174aa87-probe.yml` refreshes the first-party
collection with the publisher's own commands and then runs:

```bash
python -m scripts.6174aa87_probe --out data/research/6174aa87
```

Offline unit cover (no network) is `tests/test_6174aa87_provenance.py`. The phone
evidence is `PREVIEW_BASE_URL=http://127.0.0.1:8000 node scripts/6174aa87_mobile_check.mjs`
against a served build.
