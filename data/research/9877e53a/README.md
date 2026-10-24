# Independent acceptance check — 24 October 2026

## Verified results and scope

- Official GitHub scheduled publisher [40101099651](https://github.com/buffedlizard55-lab/MaltaProj3/actions/runs/40101099651) concluded **success**. The API reports successful collection/build/deployment jobs, including **Verify the public site, its complete data and category pages** and **Verify the public site after root-sync re-deploy**. Saved API response: `publisher-run.json`.
- GitHub deployment [7299921850](https://api.github.com/repos/buffedlizard55-lab/MaltaProj3/deployments/7299921850/statuses) reports success at **2026-10-24T14:29:23Z**, with environment URL https://buffedlizard55-lab.github.io/MaltaProj3/ . This verifies GitHub's deployment result, not an independent browser visit from this sandbox.
- Local `python -m scripts.build`: all 80 fixture source records replayed; **836 internal links/assets/anchors** passed. Source audit: **907 rows**, 887 linked to an official source, 10 explicitly unverified, 10 site-map rows, **0 sourceless**.
- Local rendered acceptance: **9 pass, 1 freshness information notice, 0 fail**. Saved report: `local-acceptance.json`. All 32 tests in `test_mobile_picks_nav`, `test_summary_navigation`, `test_unresolved_summary`, and `test_summary` passed. These are structural/unit checks, not a new visual browser accessibility audit.

## Where to find picks

- [Executive summary](https://buffedlizard55-lab.github.io/MaltaProj3/)
- [Complete picks](https://buffedlizard55-lab.github.io/MaltaProj3/origination/#picks)
- [Featured picks](https://buffedlizard55-lab.github.io/MaltaProj3/picks/)
- [Unresolved picks and limitations](https://buffedlizard55-lab.github.io/MaltaProj3/unresolved/)
- [Flagged for Review](https://buffedlizard55-lab.github.io/MaltaProj3/review/)

## Limitations — do not conflate these observations

The local reproducibility snapshot is dated **2026-10-15T08:36:13Z**, 223.8 hours old at this audit. Its 17 active entries and local rendered picks are **not today's verified coverage**. This report adds no current match count, probability, price, roster or pick. The scheduled publisher collects its own fresh source evidence; its successful public verification is recorded above, but its artifact could not be independently downloaded here because GitHub redirects artifact downloads to an Azure host outside the sandbox egress allowlist. Direct Hotspawn/HLTV/bookmaker/browser verification is likewise outside this sandbox's permitted hosts. No denied request is interpreted as evidence that a bookmaker lacks a market.

The existing workflow schedules a nominal four-hour collection plus catch-up slots; GitHub scheduling is best-effort, not a guarantee. Unsupported probabilities must remain blank. Model-derived estimates must retain their uncalibrated research labels, and never be described as executable betting prices. Linked source availability and structural audit success do not independently verify every external factual claim. No historical dossier was relabeled as fresh, and no probability was manually inserted in this session.
