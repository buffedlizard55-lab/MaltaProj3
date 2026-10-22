# Session 416d93ee — independent verification of the published picks

Read-only audit. Nothing in this directory is an input to a published probability, and the
audit script (`scripts/416d93ee_audit.py`) never writes outside this folder.

| File | What it is |
| --- | --- |
| `verification-2026-10-22T0119Z.json` / `.md` | **The audit of a healthy snapshot.** Public site served `generated_at 2026-10-22T01:06:32Z`: 35 active fixtures, all 35 carrying a probability pair, **35/35 rows replayed from their own published inputs**, inventory identical to Hotspawn's API (0 missing, 0 extra), phone checks pass. The four rows whose method label names different evidence are listed here (VD-03). |
| `verification.json` / `verification.md` | **The latest run (2026-10-22T01:30:26Z)** and the evidence for VD-04: eleven minutes after PR #146 merged, the public `/data/latest.json` was still the checked-in **15 October** snapshot (`generated_at 2026-10-15T08:36:13Z`, 80 records, 17 upcoming). That run's 17 replayed rows are the rows of that older snapshot; it is retained as a dated observation, not as a report on the current site. |
| `live-latest.json`, `live-origination.json` | The exact bytes the audit fetched from the public site, for re-checking. |
| `hltv-ranking.html.txt`, `valve-standings-2026-10-05.html.txt`, `hotspawn-lobby.html.txt`, `hotspawn-cs2-lobby.html.txt` | The captured first-party pages the audit parsed. `.html.txt` on purpose: `scripts/build.py` publishes `data/` verbatim and validates every `.html` it finds, so a captured page must never look like one of our own pages (VD-06). |

Re-run it with:

```sh
python -m scripts.416d93ee_audit                 # audits the public site
python -m scripts.416d93ee_audit --source data   # audits a local snapshot
```

The findings register that ships with this evidence is `repo-review.json`, rendered on the
site's **Flagged for Review** page.
