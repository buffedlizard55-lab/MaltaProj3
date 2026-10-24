# Session arena-ec5083b9 — does every live Hotspawn card have a pick?

Claimed on Arena's fixed branch `arena/ec5083b9-maltaproj3` on **2026-10-24T06:30Z**,
based on `main` at `bdb4fc9` (PR #240). The brief for this session asked for three
things that this folder answers with evidence rather than prose:

1. **a pick for every match Hotspawn lists**, including low-tier matches no
   sportbook or prediction market prices;
2. **a separate, dated register of the unresolved ones and their limitations**,
   carried into the executive summary;
3. **a site that is easy to use on a phone**, where the list of picks is one tap
   from the landing page.

## What is in here

| File | What it is |
| --- | --- |
| `lobby-inventory-2026-10-24T0627Z.json` | Every future CS2 card the public [Hotspawn Pick'ems lobby](https://play.hotspawn.com/lobby) rendered on 2026-10-24 between 06:26Z and 06:33Z: 25 cards, their Hotspawn fixture URL, the competition and the start time exactly as the lobby printed it. No crowd percentage is copied and no UTC instant is asserted that the read did not confirm. |
| `coverage-2026-10-24T0640Z.json` / `.md` | The reconciliation of those 25 cards against the published pages (`main` branch root at `4a6c112`, snapshot stamp `2026-10-23T20:10:00Z`): which card has a pick, which one is a research model rather than a betting line, which card is missing, the exact defect, and the result of checking every in-site link on the four pick-bearing pages. |
| `flags.json` | The three source-linked findings, rendered on **Flagged for Review**: the nine unpublished live cards, the two-defect regression chain that stalled the publisher, and the in-site link audit. |

## How the reconciliation is produced

`scripts/ec5083b9_verify.py` (tests in `tests/test_ec5083b9_coverage_verify.py`)
parses the *published* markup — it never recomputes a probability, never fills a
blank and never calls a provider:

```
python -m scripts.ec5083b9_verify --site <published tree> \
    --write  data/research/ec5083b9/coverage-<stamp>.json \
    --markdown data/research/ec5083b9/coverage-<stamp>.md
# add --fail-on-gap to exit 1 when any live card is missing or unpicked
```

Every published row it reads carries `data-glance-id`, the pick label, both
percentages and the row's own source links, so the verdicts are reproducible from
the HTML alone. A row is reported as a defect when it has no directional pick, does
not publish both win probabilities, publishes probabilities that do not sum to one,
has no Hotspawn link, or has no official `https` source link.

## Result at the time of writing (2026-10-24T06:40Z)

* **25** cards rendered as future by the lobby, **16** published.
* **9** missing, all CCT Europe 2026 Series #11/#12: `1079658`, `1079659`,
  `1079660`, `1079661`, `1081152`, `1081153`, `1081154`, `1081156`, `1081158`.
  They are missing *inventory*, not missing analysis: the publisher has not
  completed a collect since run `40015434337` (2026-10-23T19:57:15Z).
* **0** published rows without a pick. Of the 16, **9** carry an external betting
  line and **7** are labelled research models (Valve Glicko with the documented
  fixed RD, or the bo3.gg results network), each with its own limitation.
* **1321** in-site links checked on `/`, `/unresolved/`, `/picks/` and
  `/origination/`: **0 broken**, 39 targets that only the deployed Pages artifact
  carries (`data/…`, which `scripts/root_publish.py` deliberately does not copy).

## Limitations of this verification, stated plainly

* The lobby read is a **dated observation**, not a live subscription: Hotspawn adds
  cards continuously and the four-hour refresh is what keeps the list current.
* The lobby prints card times in the visitor's own timezone. They are recorded
  verbatim and no UTC conversion is claimed.
* Only **relative and project-path** links are resolved by the tool. External
  provider URLs are listed, never fetched, so this is not an availability test of
  Polymarket, Kalshi, Thunderpick, Bovada, Pinnacle or EGamersWorld.
* The mobile checks here are static (viewport meta, DOM order, anchor resolution).
  The repository's Playwright specs are the browser measurement; this session could
  not run them because no browser binary is installed in its sandbox, and it says so
  instead of claiming a pixel measurement it did not make.
