# Stale PR reconciliation — 2026-10-23T10:23:13.063842+00:00
Main: origin/main @ 90e347d (90e347dfd36da4a6c429410680092d2af342c085)

Total stale heads (excluding live #214 and active sessions): 13

| PR | Session | Branch | Ahead | Behind | Verdict | Safe to close | Reason |
|---|---|---|---|---|---|---|---|
| #120 | 541cd43a | arena/541cd43a-maltaproj3 | 23 | 471 | merged-equivalent | True | data/research/541cd43a present on main and scripts/network_model.py present; build.py/originate.py evolved beyond this b |
| #139 | 6e92015a | arena/6e92015a-maltaproj3 | 57 | 409 | partially-merged-research-missing | False | Core 541cd43a part merged; additional research dirs 6e92015a/75de2710/3cf793ef not on main but their evidence is superse |
| #149 | 38f43834 | arena/38f43834-maltaproj3 | 3 | 370 | superseded-by-later-sessions | True | Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) pre |
| #154 | bd4f77c6 | arena/bd4f77c6-maltaproj3 | 9 | 370 | superseded-by-later-sessions | True | Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) pre |
| #165 | 3cf793ef | arena/3cf793ef-maltaproj3 | 21 | 270 | partially-merged-research-missing | False | Core 541cd43a part merged; additional research dirs 6e92015a/75de2710/3cf793ef not on main but their evidence is superse |
| #168 | ee27e097 | arena/ee27e097-maltaproj3 | 20 | 270 | superseded-by-later-sessions | True | Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) pre |
| #169 | 93ba7221 | arena/93ba7221-maltaproj3 | 9 | 268 | superseded-by-later-sessions | True | Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) pre |
| #171 | bdc084c1 | arena/bdc084c1-maltaproj3 | 21 | 264 | superseded-by-later-sessions | True | Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) pre |
| #177 | e5cc3d49 | arena/e5cc3d49-maltaproj3 | 15 | 264 | superseded-by-later-sessions | True | Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) pre |
| #180 | 8877b140 | arena/8877b140-maltaproj3 | 15 | 264 | superseded-by-later-sessions | True | Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) pre |
| #182 | e4f4c6bb | arena/e4f4c6bb-maltaproj3 | 6 | 256 | superseded-trivial | True | Only COORDINATION + test or single dated audit md; main's test suite is green and publisher recovered (f6bfc506) |
| #184 | 431fd4e7 | arena/431fd4e7-maltaproj3 | 3 | 264 | superseded-trivial | True | Only COORDINATION + test or single dated audit md; main's test suite is green and publisher recovered (f6bfc506) |
| #188 | 7293b310 | arena/7293b310-maltaproj3 | 1 | 251 | superseded-stale-snapshot | True | 43-fixture snapshot from 2026-10-22; main now serves 2026-10-23 30-fixture snapshot with fresher evidence; assets change |

## Details per PR
### PR #120 (541cd43a) — merged-equivalent
- Branch: `arena/541cd43a-maltaproj3` head date `2026-10-21 14:35:26 +0000`
- Merge-base: `263281e` main `90e347d` ahead 23 behind 471
- Files changed vs merge-base: 26
  - `.github/workflows/541cd43a-snapshot.yml`
  - `COORDINATION.md`
  - `assets/scout.css`
  - `data/research/541cd43a/build.json`
  - `data/research/541cd43a/external-research-2026-10-21.json`
  - `data/research/541cd43a/flags.json`
  - `data/research/541cd43a/identity-probe.json`
  - `data/research/541cd43a/live-snapshot.json`
  - `data/research/541cd43a/live/latest.json.gz`
  - `data/research/541cd43a/live/live-bo3-bindings.json.gz`
  - `data/research/541cd43a/live/origination.json.gz`
  - `data/research/541cd43a/live/sources.json.gz`
  - `data/research/541cd43a/provider-probe.json`
  - `data/research/541cd43a/row-source-audit.json`
  - `scripts/audit_rows.py`
  - `scripts/build.py`
  - `scripts/build_origination.py`
  - `scripts/network_model.py`
  - `scripts/originate.py`
  - `scripts/s541cd43a_probe.py`
  - ... and 6 more
- Research missing on main: ['data/research/541cd43a/build.json', 'data/research/541cd43a/live-snapshot.json', 'data/research/541cd43a/live/latest.json.gz', 'data/research/541cd43a/live/live-bo3-bindings.json.gz', 'data/research/541cd43a/live/origination.json.gz']
- Research same as main: ['data/research/541cd43a/external-research-2026-10-21.json', 'data/research/541cd43a/flags.json', 'data/research/541cd43a/identity-probe.json', 'data/research/541cd43a/row-source-audit.json']
- Code files: ['.github/workflows/541cd43a-snapshot.yml', 'assets/scout.css', 'scripts/audit_rows.py', 'scripts/build.py', 'scripts/build_origination.py', 'scripts/network_model.py', 'scripts/originate.py', 'scripts/s541cd43a_probe.py', 'scripts/s541cd43a_probe2.py', 'scripts/s541cd43a_snapshot.py']
- Safe to close: True — data/research/541cd43a present on main and scripts/network_model.py present; build.py/originate.py evolved beyond this branch
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/120, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/541cd43a-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/541cd43a-maltaproj3

### PR #139 (6e92015a) — partially-merged-research-missing
- Branch: `arena/6e92015a-maltaproj3` head date `2026-10-21 21:36:26 +0000`
- Merge-base: `3a6cc94` main `90e347d` ahead 57 behind 409
- Files changed vs merge-base: 115
  - `.github/workflows/541cd43a-snapshot.yml`
  - `.github/workflows/6e92015a-probe.yml`
  - `.github/workflows/75de2710-probe.yml`
  - `COORDINATION.md`
  - `README.md`
  - `assets/scout.css`
  - `data/research/541cd43a/build.json`
  - `data/research/541cd43a/external-research-2026-10-21.json`
  - `data/research/541cd43a/flags.json`
  - `data/research/541cd43a/identity-probe.json`
  - `data/research/541cd43a/live-snapshot.json`
  - `data/research/541cd43a/live/latest.json.gz`
  - `data/research/541cd43a/live/live-bo3-bindings.json.gz`
  - `data/research/541cd43a/live/origination.json.gz`
  - `data/research/541cd43a/live/sources.json.gz`
  - `data/research/541cd43a/provider-probe.json`
  - `data/research/541cd43a/row-source-audit.json`
  - `data/research/6e92015a/README.md`
  - `data/research/6e92015a/egw-urls.json`
  - `data/research/6e92015a/evidence/bovada.gz`
  - ... and 95 more
- Research missing on main: ['data/research/541cd43a/build.json', 'data/research/541cd43a/live-snapshot.json', 'data/research/541cd43a/live/latest.json.gz', 'data/research/541cd43a/live/live-bo3-bindings.json.gz', 'data/research/541cd43a/live/origination.json.gz']
- Research same as main: ['data/research/541cd43a/external-research-2026-10-21.json', 'data/research/541cd43a/flags.json', 'data/research/541cd43a/identity-probe.json', 'data/research/541cd43a/row-source-audit.json']
- Code files: ['.github/workflows/541cd43a-snapshot.yml', '.github/workflows/6e92015a-probe.yml', '.github/workflows/75de2710-probe.yml', 'README.md', 'assets/scout.css', 'scripts/audit_rows.py', 'scripts/build.py', 'scripts/build_origination.py', 'scripts/network_model.py', 'scripts/originate.py']
- Safe to close: False — Core 541cd43a part merged; additional research dirs 6e92015a/75de2710/3cf793ef not on main but their evidence is superseded by fresher 2026-10-23 snapshots; keep open until reviewer confirms no unique value
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/139, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/6e92015a-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/6e92015a-maltaproj3

### PR #149 (38f43834) — superseded-by-later-sessions
- Branch: `arena/38f43834-maltaproj3` head date `2026-10-22 01:52:04 +0000`
- Merge-base: `4ec225d` main `90e347d` ahead 3 behind 370
- Files changed vs merge-base: 6
  - `COORDINATION.md`
  - `assets/scout.css`
  - `scripts/build.py`
  - `scripts/network_model.py`
  - `tests/test_build.py`
  - `tests/test_network_model.py`
- Research missing on main: []
- Research same as main: []
- Code files: ['assets/scout.css', 'scripts/build.py', 'scripts/network_model.py', 'tests/test_build.py', 'tests/test_network_model.py']
- Safe to close: True — Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/149, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/38f43834-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/38f43834-maltaproj3

### PR #154 (bd4f77c6) — superseded-by-later-sessions
- Branch: `arena/bd4f77c6-maltaproj3` head date `2026-10-22 02:40:32 +0000`
- Merge-base: `4ec225d` main `90e347d` ahead 9 behind 370
- Files changed vs merge-base: 8
  - `COORDINATION.md`
  - `data/origination/aliases.json`
  - `data/research/bd4f77c6/flags.json`
  - `data/research/bd4f77c6/verification-2026-10-22.json`
  - `scripts/build.py`
  - `scripts/build_origination.py`
  - `scripts/originate.py`
  - `tests/test_bd4f77c6_provenance.py`
- Research missing on main: ['data/research/bd4f77c6/flags.json', 'data/research/bd4f77c6/verification-2026-10-22.json']
- Research same as main: []
- Code files: ['data/origination/aliases.json', 'scripts/build.py', 'scripts/build_origination.py', 'scripts/originate.py', 'tests/test_bd4f77c6_provenance.py']
- Safe to close: True — Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/154, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/bd4f77c6-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/bd4f77c6-maltaproj3

### PR #165 (3cf793ef) — partially-merged-research-missing
- Branch: `arena/3cf793ef-maltaproj3` head date `2026-10-22 09:40:39 +0000`
- Merge-base: `68e3c38` main `90e347d` ahead 21 behind 270
- Files changed vs merge-base: 18
  - `COORDINATION.md`
  - `data/research/3cf793ef/README.md`
  - `data/research/3cf793ef/details/0092--ex-rustec--brilliance-glowiing-shalfey-yiksrezo-youka.md`
  - `data/research/3cf793ef/details/0093--ex-zero_tenacity--brutmonster-cjoffo-dragon-kind0-vldn.md`
  - `data/research/3cf793ef/flags.json`
  - `data/research/3cf793ef/live/hotspawn-fixtures.json`
  - `data/research/3cf793ef/live/published-latest.json`
  - `data/research/3cf793ef/live/published-origination.json`
  - `data/research/3cf793ef/live/summary.json`
  - `data/research/3cf793ef/live/upcoming.json`
  - `data/research/3cf793ef/outside-lines-2026-10-22T0740Z.json`
  - `data/research/3cf793ef/valve-standings-2026-10-05.md`
  - `data/research/3cf793ef/valve-verification.json`
  - `data/research/3cf793ef/valve-verification.md`
  - `scripts/3cf793ef_ladder_report.py`
  - `scripts/3cf793ef_research.py`
  - `scripts/3cf793ef_valve_check.py`
  - `tests/test_review_flags.py`
- Research missing on main: ['data/research/3cf793ef/README.md', 'data/research/3cf793ef/details/0092--ex-rustec--brilliance-glowiing-shalfey-yiksrezo-youka.md', 'data/research/3cf793ef/details/0093--ex-zero_tenacity--brutmonster-cjoffo-dragon-kind0-vldn.md', 'data/research/3cf793ef/flags.json', 'data/research/3cf793ef/live/hotspawn-fixtures.json']
- Research same as main: []
- Code files: ['scripts/3cf793ef_ladder_report.py', 'scripts/3cf793ef_research.py', 'scripts/3cf793ef_valve_check.py', 'tests/test_review_flags.py']
- Safe to close: False — Core 541cd43a part merged; additional research dirs 6e92015a/75de2710/3cf793ef not on main but their evidence is superseded by fresher 2026-10-23 snapshots; keep open until reviewer confirms no unique value
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/165, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/3cf793ef-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/3cf793ef-maltaproj3

### PR #168 (ee27e097) — superseded-by-later-sessions
- Branch: `arena/ee27e097-maltaproj3` head date `2026-10-22 09:06:19 +0000`
- Merge-base: `68e3c38` main `90e347d` ahead 20 behind 270
- Files changed vs merge-base: 16
  - `COORDINATION.md`
  - `README.md`
  - `data/research/ee27e097/egamersworld-observation.json`
  - `data/research/ee27e097/flags.json`
  - `data/research/ee27e097/hotspawn-fixtures.json`
  - `data/research/ee27e097/line-sources.json`
  - `data/research/ee27e097/probe-2026-10-22T0732Z.json`
  - `data/research/ee27e097/probe-2026-10-22T0751Z.json`
  - `data/research/ee27e097/probe-summary.md`
  - `scripts/build.py`
  - `scripts/ee27e097_probe.py`
  - `scripts/ee27e097_research.py`
  - `tests/test_ee27e097_unresolved_page.py`
  - `tests/test_f4eb8ae3.py`
  - `tests/test_final_day.py`
  - `tests/test_review_flags.py`
- Research missing on main: ['data/research/ee27e097/egamersworld-observation.json', 'data/research/ee27e097/flags.json', 'data/research/ee27e097/hotspawn-fixtures.json', 'data/research/ee27e097/line-sources.json', 'data/research/ee27e097/probe-2026-10-22T0732Z.json']
- Research same as main: []
- Code files: ['README.md', 'scripts/build.py', 'scripts/ee27e097_probe.py', 'scripts/ee27e097_research.py', 'tests/test_ee27e097_unresolved_page.py', 'tests/test_f4eb8ae3.py', 'tests/test_final_day.py', 'tests/test_review_flags.py']
- Safe to close: True — Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/168, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/ee27e097-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/ee27e097-maltaproj3

### PR #169 (93ba7221) — superseded-by-later-sessions
- Branch: `arena/93ba7221-maltaproj3` head date `2026-10-22 09:07:55 +0000`
- Merge-base: `3f2dc79` main `90e347d` ahead 9 behind 268
- Files changed vs merge-base: 9
  - `COORDINATION.md`
  - `data/research/93ba7221/flags.json`
  - `data/research/93ba7221/live-inventory-recheck.json`
  - `data/research/93ba7221/probability-replay.json`
  - `data/research/93ba7221/row-verification.json`
  - `scripts/verify_93ba7221.py`
  - `tests/test_93ba7221_counts.py`
  - `tests/test_93ba7221_verify.py`
  - `tests/test_review_flags.py`
- Research missing on main: ['data/research/93ba7221/flags.json', 'data/research/93ba7221/live-inventory-recheck.json', 'data/research/93ba7221/probability-replay.json', 'data/research/93ba7221/row-verification.json']
- Research same as main: []
- Code files: ['scripts/verify_93ba7221.py', 'tests/test_93ba7221_counts.py', 'tests/test_93ba7221_verify.py', 'tests/test_review_flags.py']
- Safe to close: True — Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/169, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/93ba7221-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/93ba7221-maltaproj3

### PR #171 (bdc084c1) — superseded-by-later-sessions
- Branch: `arena/bdc084c1-maltaproj3` head date `2026-10-22 10:57:11 +0000`
- Merge-base: `49dd327` main `90e347d` ahead 21 behind 264
- Files changed vs merge-base: 8
  - `.github/workflows/checks.yml`
  - `COORDINATION.md`
  - `data/research/bdc084c1/flags.json`
  - `data/research/bdc084c1/probe-report.json`
  - `data/research/bdc084c1/probe-report.md`
  - `scripts/bdc084c1_probe.py`
  - `scripts/build.py`
  - `tests/test_bdc084c1_labels.py`
- Research missing on main: ['data/research/bdc084c1/flags.json', 'data/research/bdc084c1/probe-report.json', 'data/research/bdc084c1/probe-report.md']
- Research same as main: []
- Code files: ['.github/workflows/checks.yml', 'scripts/bdc084c1_probe.py', 'scripts/build.py', 'tests/test_bdc084c1_labels.py']
- Safe to close: True — Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/171, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/bdc084c1-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/bdc084c1-maltaproj3

### PR #177 (e5cc3d49) — superseded-by-later-sessions
- Branch: `arena/e5cc3d49-maltaproj3` head date `2026-10-22 10:36:28 +0000`
- Merge-base: `49dd327` main `90e347d` ahead 15 behind 264
- Files changed vs merge-base: 9
  - `COORDINATION.md`
  - `data/research/e5cc3d49/README.md`
  - `data/research/e5cc3d49/line-by-line-audit.json`
  - `data/research/e5cc3d49/live/mobile-check-local.txt`
  - `data/research/e5cc3d49/repo-review.json`
  - `scripts/coverage_audit.py`
  - `scripts/e5cc3d49_audit.py`
  - `scripts/review_register.py`
  - `tests/test_e5cc3d49.py`
- Research missing on main: ['data/research/e5cc3d49/README.md', 'data/research/e5cc3d49/line-by-line-audit.json', 'data/research/e5cc3d49/live/mobile-check-local.txt', 'data/research/e5cc3d49/repo-review.json']
- Research same as main: []
- Code files: ['scripts/coverage_audit.py', 'scripts/e5cc3d49_audit.py', 'scripts/review_register.py', 'tests/test_e5cc3d49.py']
- Safe to close: True — Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/177, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/e5cc3d49-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/e5cc3d49-maltaproj3

### PR #180 (8877b140) — superseded-by-later-sessions
- Branch: `arena/8877b140-maltaproj3` head date `2026-10-22 09:17:48 +0000`
- Merge-base: `49dd327` main `90e347d` ahead 15 behind 264
- Files changed vs merge-base: 10
  - `COORDINATION.md`
  - `data/research/8877b140/flags.json`
  - `data/research/8877b140/live-deployment-verification.json`
  - `data/research/8877b140/live-deployment-verification.md`
  - `data/research/8877b140/replay-verification.md`
  - `data/research/8877b140/verification-dossier.json`
  - `scripts/8877b140_live.py`
  - `scripts/8877b140_verify.py`
  - `tests/test_8877b140_contract.py`
  - `tests/test_review_flags.py`
- Research missing on main: ['data/research/8877b140/flags.json', 'data/research/8877b140/live-deployment-verification.json', 'data/research/8877b140/live-deployment-verification.md', 'data/research/8877b140/replay-verification.md', 'data/research/8877b140/verification-dossier.json']
- Research same as main: []
- Code files: ['scripts/8877b140_live.py', 'scripts/8877b140_verify.py', 'tests/test_8877b140_contract.py', 'tests/test_review_flags.py']
- Safe to close: True — Functional fixes (both-side probs, source labels, coverage sentences, unresolved page, line-by-line audit, CSP note) present on main via later PRs #191 #193 #194 #196 #199 #209 #212 #213; research is dated 2026-10-21/22 and superseded by 46ade650/38c53ece/f6bfc506/3149e7ae
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/180, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/8877b140-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/8877b140-maltaproj3

### PR #182 (e4f4c6bb) — superseded-trivial
- Branch: `arena/e4f4c6bb-maltaproj3` head date `2026-10-22 10:27:35 +0000`
- Merge-base: `cdfed10` main `90e347d` ahead 6 behind 256
- Files changed vs merge-base: 2
  - `COORDINATION.md`
  - `tests/test_review_flags.py`
- Research missing on main: []
- Research same as main: []
- Code files: ['tests/test_review_flags.py']
- Safe to close: True — Only COORDINATION + test or single dated audit md; main's test suite is green and publisher recovered (f6bfc506)
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/182, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/e4f4c6bb-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/e4f4c6bb-maltaproj3

### PR #184 (431fd4e7) — superseded-trivial
- Branch: `arena/431fd4e7-maltaproj3` head date `2026-10-22 09:35:20 +0000`
- Merge-base: `49dd327` main `90e347d` ahead 3 behind 264
- Files changed vs merge-base: 2
  - `COORDINATION.md`
  - `data/research/431fd4e7/publication-audit-2026-10-22.md`
- Research missing on main: ['data/research/431fd4e7/publication-audit-2026-10-22.md']
- Research same as main: []
- Code files: []
- Safe to close: True — Only COORDINATION + test or single dated audit md; main's test suite is green and publisher recovered (f6bfc506)
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/184, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/431fd4e7-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/431fd4e7-maltaproj3

### PR #188 (7293b310) — superseded-stale-snapshot
- Branch: `arena/7293b310-maltaproj3` head date `2026-10-22 11:30:17 +0000`
- Merge-base: `8f053e7` main `90e347d` ahead 1 behind 251
- Files changed vs merge-base: 190
  - `COORDINATION.md`
  - `assets/scout.css`
  - `assets/scout.js`
  - `coverage/index.html`
  - `data/evidence/hltv-page.json`
  - `data/evidence/hltv-research.json`
  - `data/evidence/hotspawn-context.json`
  - `data/evidence/hotspawn-fixtures.json`
  - `data/evidence/hotspawn-rules.json`
  - `data/evidence/polymarket-book-1224236-0.json`
  - `data/evidence/polymarket-book-1224236-1.json`
  - `data/evidence/polymarket-book-1224237-0.json`
  - `data/evidence/polymarket-book-1224237-1.json`
  - `data/evidence/polymarket-book-1231332-0.json`
  - `data/evidence/polymarket-book-1231332-1.json`
  - `data/evidence/polymarket-book-1231333-0.json`
  - `data/evidence/polymarket-book-1231333-1.json`
  - `data/evidence/polymarket-book-1231334-0.json`
  - `data/evidence/polymarket-book-1231334-1.json`
  - `data/evidence/polymarket-book-1231335-0.json`
  - ... and 170 more
- Research missing on main: ['data/research/7293b310/README.md', 'data/research/7293b310/verification.json', 'data/research/7293b310/verification.md']
- Research same as main: []
- Code files: ['assets/scout.css', 'assets/scout.js', 'coverage/index.html', 'data/evidence/hltv-page.json', 'data/evidence/hltv-research.json', 'data/evidence/hotspawn-context.json', 'data/evidence/hotspawn-fixtures.json', 'data/evidence/hotspawn-rules.json', 'data/evidence/polymarket-book-1224236-0.json', 'data/evidence/polymarket-book-1224236-1.json']
- Safe to close: True — 43-fixture snapshot from 2026-10-22; main now serves 2026-10-23 30-fixture snapshot with fresher evidence; assets changes superseded
- Sources: https://github.com/buffedlizard55-lab/MaltaProj3/pull/188, https://github.com/buffedlizard55-lab/MaltaProj3/tree/arena/7293b310-maltaproj3, https://github.com/buffedlizard55-lab/MaltaProj3/commits/arena/7293b310-maltaproj3

