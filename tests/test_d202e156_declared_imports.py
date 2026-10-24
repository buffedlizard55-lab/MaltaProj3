"""Session arena-d202e156: every third-party import the suite makes must be installed by CI.

`pages.yml` installs exactly `requirements.txt` and then runs
`python -m unittest discover -s tests`. On 2026-10-24 that contract broke: PR #267
(commit `d29a5602`) added `tests/test_b97af12f_reconciliation.py`, whose module-level
`import pytest` is not declared anywhere. `unittest discover` imports every
`tests/test*.py` module, so the ImportError became a suite-wide ERROR and the
publisher's regression step went red again — the four-hour refresh died a second
time, one commit after the `egw_live` NameError was fixed.

The failure is invisible to a syntax check and to the module's own author (the
tests are pytest-style functions with fixtures, so they are never collected by the
unittest runner and never ran). These tests turn it into a build-time failure:

* every top-level third-party import in `tests/` and `scripts/` resolves to a
  distribution named in `requirements.txt`;
* every module the runner will import actually imports with only those
  distributions installed.
"""
from __future__ import annotations

import ast
import importlib
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STDLIB = set(sys.stdlib_module_names)
# Repository-local import roots: the scripts package, the tests package and every
# importable module directly inside them.
LOCAL = {'scripts', 'tests'} | {
    p.stem for p in (ROOT / 'scripts').glob('*.py') if p.stem.isidentifier()
} | {
    p.stem for p in (ROOT / 'tests').glob('test_*.py')
}


def declared_distributions() -> set[str]:
    out = set()
    for line in (ROOT / 'requirements.txt').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name = re.split(r'[=<>!~\[]', line, 1)[0].strip()
        out.add(name.replace('-', '_').lower())
    return out


# Distribution name -> import name(s). Only the mappings this repository needs.
IMPORT_TO_DISTRIBUTION = {
    'bs4': 'beautifulsoup4',
    'requests': 'requests',
    'pytest': 'pytest',
}


def top_level_imports(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split('.')[0])
    return names


class DeclaredDependencies(unittest.TestCase):
    def test_every_third_party_import_is_declared(self):
        declared = declared_distributions()
        self.assertTrue(declared, 'requirements.txt declares nothing')
        problems = []
        for folder in ('tests', 'scripts'):
            for path in sorted((ROOT / folder).glob('*.py')):
                for name in sorted(top_level_imports(path)):
                    if name in STDLIB or name in LOCAL:
                        continue
                    distribution = IMPORT_TO_DISTRIBUTION.get(name, name)
                    if distribution not in declared:
                        problems.append(f'{path.relative_to(ROOT)} imports {name} '
                                        f'(distribution {distribution}) which requirements.txt does not install')
        self.assertEqual(problems, [], '\n'.join(problems))

    def test_the_declared_distributions_are_importable_here(self):
        """CI installs requirements.txt; if an import still fails, the suite is red."""
        import_names = {n for folder in ('tests', 'scripts')
                        for path in (ROOT / folder).glob('*.py')
                        for n in top_level_imports(path)
                        if n not in STDLIB and n not in LOCAL}
        failures = []
        for name in sorted(import_names):
            try:
                importlib.import_module(name)
            except Exception as exc:  # noqa: BLE001 - report every failure
                failures.append(f'{name}: {type(exc).__name__}: {exc}')
        self.assertEqual(failures, [], '; '.join(failures))


class PytestStyleTestsAreVisible(unittest.TestCase):
    """A pytest-style module collects zero tests under the unittest runner CI uses.

    `unittest discover` ignores plain `def test_*` functions, so a module written
    for pytest contributes nothing to the runner that actually gates the
    publisher. `tests/test_b97af12f_reconciliation.py` was in exactly that state
    when PR #267 landed it (commit `d29a5602`): six pytest-style checks, one
    taking the `tmp_path` fixture, none of them ever collected, plus an
    undeclared `import pytest` that made `unittest discover` error on the module
    and turned the publisher's regression step red. Its owner converted it to
    `unittest.TestCase` in commit `6c051a73`, which cleared both defects. The
    allowlist below is therefore empty: a *second* such module fails this test.
    """

    KNOWN_PYTEST_ONLY: set[str] = set()

    def test_every_test_module_is_collected_by_the_unittest_runner(self):
        uncollected = []
        for path in sorted((ROOT / 'tests').glob('test_*.py')):
            try:
                module = importlib.import_module(f'tests.{path.stem}')
            except Exception:  # noqa: BLE001 - the import test reports this
                continue
            suite = unittest.TestLoader().loadTestsFromModule(module)
            if suite.countTestCases() == 0 and path.name not in self.KNOWN_PYTEST_ONLY:
                uncollected.append(path.name)
        self.assertEqual(uncollected, [],
                         'these modules define pytest-style tests the unittest runner '
                         'cannot collect: ' + ', '.join(uncollected))


if __name__ == '__main__':
    unittest.main()
