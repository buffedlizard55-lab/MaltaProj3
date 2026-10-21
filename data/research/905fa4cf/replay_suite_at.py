"""Forensic clock replay: run the full regression suite at one pinned instant.

Session arena-905fa4cf diagnostic, 2026-10-21.

Why this exists: production runs 39371739014 (2026-10-20T04:50:59Z) and
39389855311 (2026-10-20T07:56:14Z) failed at "Regression tests (repository
fixtures, before any cache restore)" on the identical head SHA
(89bfa277bad9874a439b3e54117d8e31a5354cf9) as the neighbouring successful runs
(39352634388 at 01:17:47Z, 39431428827 at 13:33:30Z). Same code, same checked-in
fixtures — so the failure was clock- or environment-dependent, not code-diff
dependent. The runner's log host is outside the diagnosing sandbox's egress
allowlist, so the failing assertion is not directly readable. This harness
reruns the exact suite command with the whole process clock frozen at the
failed instant; a test that passes at the control instant and fails at the
failed instant is the reproduced bomb (the same failure class as the
2026-10-17 wall-clock freeze documented in tests/test_freshness_determinism.py).

Manual tool, never wired into CI: .venv/bin/python
data/research/905fa4cf/replay_suite_at.py 2026-10-20T04:50:59+00:00

Requires the dev-only `freezegun` package (not part of requirements.txt; the
production suite never sees it). Results are recorded as JSON lines to stdout's
final line and to the sibling file named in --out.
"""
import argparse
import io
import json
import sys
import unittest
from pathlib import Path

try:
    from freezegun import freeze_time
except ImportError:  # pragma: no cover - manual tool guard
    sys.exit("freezegun is required for this manual diagnostic: pip install freezegun")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('instant', help='ISO-8601 instant to freeze, e.g. 2026-10-20T04:50:59+00:00')
    parser.add_argument('--out', help='write the JSON result next to the standard output')
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root))

    stream = io.StringIO()
    with freeze_time(args.instant):
        suite = unittest.TestLoader().discover(str(root / 'tests'))
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)

    failures = [f'{case}: {tb.splitlines()[-1] if tb.splitlines() else ""}' for case, tb in result.failures]
    errors = [f'{case}: {tb.splitlines()[-1] if tb.splitlines() else ""}' for case, tb in result.errors]
    tail = [line for line in stream.getvalue().splitlines() if line.startswith(('FAILED', 'OK', 'Ran '))]
    report = {
        'frozen_instant': args.instant,
        'tests_run': result.testsRun,
        'failure_count': len(failures),
        'error_count': len(errors),
        'failures': failures,
        'errors': errors,
        'summary_lines': tail,
        'success': result.wasSuccessful(),
    }
    print(json.dumps(report, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + '\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
