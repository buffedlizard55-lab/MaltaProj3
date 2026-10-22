# Session arena-e5cc3d49 — independent line-by-line audit of the published picks

The Arena sandbox has no egress to Hotspawn, HLTV, Polymarket, Kalshi or any esportsbook, so the
live inventory and every live line were read on a GitHub runner with the publisher's own collector,
through the session-only workflow `.github/workflows/e5cc3d49-live.yml` (deleted before this branch
merged). Nothing in this directory changes a probability, a pick, an alias or a page.

## Files

| File | What it is |
| --- | --- |
| `line-by-line-audit.json` | The audit report produced by `scripts/e5cc3d49_audit.py` on the live snapshot read by run [39742089707](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39742089707) (inventory observed 2026-10-22T07:44:00Z). Per-row checks, the violations it found, and the model rows it could not re-derive. |
| `repo-review.json` | The findings register published on the site's **Flagged for Review** page. |
| `live/mobile-check-local.txt` | 390 px and 320 px measurements produced locally on a build of this branch: per-page overflow, page height, pick-index offset and every section taller than 900 px. |

## What the audit re-derived, and what it could not

`scripts/e5cc3d49_audit.py` reads only the published payload, the saved first-party evidence and the
built site. Per row it re-derives the published number from the primary observation quoted beside it:

* **Polymarket rows** — from the saved CLOB order books (best bid, best ask) and from the bid/ask
  the row publishes, normalised.
* **Esportsbook rows** — from the quoted decimal odds, `1/o` normalised.
* **Consensus rows** — from the median of the independent providers named on the row.
* **Valve-model rows** — from the official published points on the documented fixed-RD-75 Glicko
  scaling.

It also enforces, per row: two probabilities in (0, 1) summing to 1, a pick that is the argmax, a
known ladder method, an https source link beside the number, and an ISO-8601 observation time no
older than eight hours for an active fixture. Across the payload it reconciles the inventory to the
rows, the rows to the published counts, and the rows to the built phone pages (the executive
summary's glance index must name every active fixture and its published pick; the complete list must
carry a `match-<id>` and `row-<id>` anchor for each).

**Not re-derivable, and therefore not marked verified:** the Bradley–Terry network fit, the
HLTV-world-ranking transform and the results-form fit. Their graph inputs are not part of the public
payload, so each such row is listed by fixture id and source under `not_recomputable`.

## Two runs, and one correction to the audit itself

| Run | Snapshot | Result |
| --- | --- | --- |
| [39742089707](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39742089707) | 2026-10-22T07:44Z | 46 active fixtures, 46 resolved, 0 unresolved; 29 of 46 numbers re-derived exactly; 17 model rows not re-derivable; **4 violations**, all on fixtures 1081596 and 1082769 ("saved order book does not reproduce the quoted bid/ask"). |
| [39744061339](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/39744061339) | 2026-10-22T07:56Z | Same audit **after** the correction below: 0 violations. |

The four violations were an artifact of the audit, not of the site. The first version paired each
published quote with the saved order book of the same *position*; the collector reorders the quotes
to Hotspawn's team order, and for those two fixtures Polymarket lists the teams in the reverse order
("Phantom Academy vs Falcons Force"). The audit now maps each team to its own book through the
published `source_outcomes`, and makes no book-level claim when the names cannot be mapped
(`tests/test_e5cc3d49.py::RecomputeTests::test_reversed_outcome_order_maps_books_by_name`).

The row was confirmed independently: Polymarket's own page for that fixture reports Falcons Force at
60¢ and Phantom Academy at 41¢, which matches the published 59.5% / 40.5% midpoint. A third queued
run (live snapshot plus runner-side mobile check) never left GitHub's queue while this session was
live and is not reported here.

## Reproduce

```bash
python -m unittest tests.test_e5cc3d49 -v
python -m scripts.build                              # rebuild site/ from the checked-in data
python -m scripts.e5cc3d49_audit --data data --site site
```

Against the checked-in repository snapshot the audit correctly fails with one staleness violation
per active row: the checked-in `data/latest.json` is the 15 October collection, seven days older
than the live artifact. That is the E5-04 finding on the Flagged for Review page, not a defect in
the picks.
