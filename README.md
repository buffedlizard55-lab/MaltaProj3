# MaltaProj3

Hotspawn CS2 Pick'em picks dashboard. Each Counter-Strike 2 match captured from the Hotspawn lobby gets a pick and a win probability per team, built from outside betting markets (Polymarket, Stake, Oddsportal) and HLTV world-ranking points. Hotspawn's own pick percentages are never used.

Published site: https://buffedlizard55-lab.github.io/MaltaProj3/

## Layout

- `docs/` — the GitHub Pages site (served from `main` at `/docs`)
  - `index.html` executive summary, links to every page
  - `picks.html` picks table (one row per resolved match, source links on every row)
  - `unresolved.html` matches without a usable outside line, with reasons and what would resolve them
  - `matches.html` every captured match with the raw prices used
  - `analysis.html` market vs model comparison and HLTV top 30
  - `methodology.html` how each number is produced
  - `sources.html` every source URL used
  - `flagged.html` Flagged for Review (irregularities; they do not block publishing)
- `data/matches.json` — raw inputs (Hotspawn match list, market prices, HLTV points), with source URLs
- `scripts/build_site.py` — computes the lines and regenerates `docs/`
- `COORDINATION.md` — shared task board, claim protocol and the irregularities log

## Rebuild

```bash
python3 scripts/build_site.py --check   # regenerates docs/ and checks internal links
```

Python 3.8+ with the standard library only. No dependencies.

## Refreshing the data

The data in `data/matches.json` is a dated snapshot (see the `snapshot` block). To refresh, update the raw inputs and rerun the build. A scheduled 4–8 hour refresh is not set up (see I-16 in `COORDINATION.md`).
