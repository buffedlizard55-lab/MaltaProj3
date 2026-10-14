# CS2 Pick Desk

A source-linked, mobile-first GitHub Pages dashboard for the public **Hotspawn Pick'ems** Counter-Strike 2 schedule. It puts the executive summary, full picks table, methodology, and unresolved records in the primary navigation.

> **Live site (after Pages deploy):** `https://buffedlizard55-lab.github.io/MaltaProj3/`

## What is published

- **[Executive summary](./index.html)** — direct links to the full list and the unresolved list, data timestamp, coverage count, and the key limitation.
- **[All picks](./picks.html)** — every captured Hotspawn Pick'ems CS2 row. Each row has an official Hotspawn source link. A populated probability also has an independent external-market source link.
- **[Methodology](./methodology.html)** — source rules, external price calculation, and explicit non-inference policy.
- **[Flagged for Review](./flagged.html)** — visible limitations and conditions that prevent a pick from being published.

The initial snapshot contains **28** public lobby match rows (captured 2026-10-14 04:42 UTC). Eight had an exact externally verified match-winner line at capture. The remaining rows are intentionally marked **Unresolved** with blank probabilities and blank picks rather than artificial values.

## Verification and source rules

1. **Schedule scope:** The public [Hotspawn Pick'ems lobby](https://play.hotspawn.com/lobby) determines the coverage scope. Every row links either to its public [Hotspawn match page](https://www.hotspawn.com/matches) or, when Hotspawn had not published a match detail page, to the official lobby itself.
2. **No Hotspawn probability input:** Hotspawn's “% picked” values are not used for any probability or pick.
3. **CS2 context first:** Exact [HLTV](https://www.hltv.org/matches) pages are linked where directly verified. They can establish match context (event, format, roster, ranking, stats), but their community voting percentages are not treated as probabilities.
4. **External market line:** An external match-winner line is only displayed after the exact two-team market was verified on a public source. The initial data uses public [Polymarket CS2](https://polymarket.com/esports/cs2) market pages and two directly checked [Stake](https://stake.dk/en/sports) match pages.
5. **No inference:** If a matching external line cannot be verified, the site does **not** turn team tier, past results, HLTV context, Hotspawn popularity, or an informal rating into a number. It leaves both the probability and pick blank and flags the row.

### Probability labels

- **Polymarket match-winner price:** the two published outcome prices from the exact public market, normalized only if the two prices do not total exactly 100 due to display precision.
- **De-vigged Stake decimal odds:** `1 / decimal odds` for each of the two sides, normalized across those two raw values. The linked page shows the original decimal odds.
- **Market pick:** the team with the higher displayed external probability. This is an evidence label, **not betting advice** or a guarantee.

## Automated refresh

`.github/workflows/refresh.yml` runs at **:17 every six hours** on `main` (and supports manual dispatch). It:

1. checks the public Hotspawn lobby is reachable and preserves each existing row's official source record;
2. checks public active Polymarket esports markets for an exact two-team CS2 **Match Winner** market;
3. updates only directly matched market probabilities and timestamps;
4. clears an old Polymarket line if that exact active market is no longer returned, rather than showing it as fresh;
5. validates the source schema; commits changed JSON; and deploys the static Pages artifact.

No login, account, private endpoint, scraping of user profiles, or Hotspawn pick percentage is required. The [Hotspawn robots file](https://play.hotspawn.com/robots.txt) permits crawling (`Allow: /`) as checked on 2026-10-14.

### Important automation limitation

The refresh can discover and enrich linked public lobby records, but a low-tier card without a public Hotspawn detail link may require Hotspawn to publish that detail record before it can be added automatically. It remains transparently documented as a coverage limitation, rather than being manufactured from a name or social pick percentage. The scheduled resolver is designed to add a line whenever a matching active public market appears.

## Local checks

No dependency installation is required.

```bash
node scripts/verify-site.mjs
```

The check verifies:

- required static files and local links;
- at least one match row exists;
- every row has an official Hotspawn source URL;
- verified lines contain a pick, HTTPS external source and probabilities summing to 100 (within display rounding);
- unresolved lines contain no probability or pick.

## Publishing

`pages.yml` validates and deploys the static site for pushes to `main`. `refresh.yml` performs the six-hour data refresh and deploy. Repository Settings → Pages must be set to **GitHub Actions** if it is not enabled already.

## Current review items

See **[Flagged for Review](./flagged.html)** for the live record. Current irregularities include:

- C-tier / academy match-winner markets are often absent even when a schedule is public;
- displayed odds are volatile and must be read with their capture time;
- Hotspawn's public schedule is explicitly UTC, while the lobby was observed displaying opening times four hours earlier in its UI at capture. This is documented in the review data and UTC is used where the public schedule provides it.

---

## Second build (session 83207e7b): `docs/`

A second, independent picks build lives in `docs/` (served by GitHub Pages at `/MaltaProj3/docs/` when Pages builds from `main`; the root site above is unchanged).

- Picks come from outside betting lines (Polymarket with a $50 volume rule, Stake and Oddsportal decimal odds, normalised) blended 70/30 with an HLTV world-ranking points model where both teams are in the top 30. Hotspawn pick percentages are not used.
- Result snapshot: 28 captured match cards, 14 picks, 14 unresolved (with reasons). The 68-match lobby header and the 88-tier total are flagged (I-03, I-04).
- Data: `data/picks-model.json` (raw inputs with source URLs). Build: `python3 scripts/build_site.py --check` (standard library only).
- Pages: `docs/index.html` (executive summary), `docs/picks.html`, `docs/unresolved.html`, `docs/matches.html`, `docs/analysis.html`, `docs/methodology.html`, `docs/sources.html`, `docs/flagged.html`.
- Coordination and irregularities: `COORDINATION.md` (session 83207e7b section).
