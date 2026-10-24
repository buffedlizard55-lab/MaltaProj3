"""Session arena-f43dc4f1: an undefined module name broke the whole collection.

PR #240 (`7493ea8`) added the EGamersWorld fallback rung to `scripts/originate.py`
and `scripts/egw_live.py`, but never imported the module: `live_collect` reads
`egw_live.EVIDENCE_NAME`, `egw_live.INDEX_URL` and `egw_live.entries_for(...)`
while the import block above it only lists `form_model`, `hltv_ranking`,
`network_model`, `pinnacle_lines`, `smarkets_lines` and `reference_odds`.

The consequence was total, not cosmetic. `live_collect` is the first thing the
four-hour refresh runs, and its first statement after setup touches
`egw_live.EVIDENCE_NAME`, so **every** collection raised
`NameError: name 'egw_live' is not defined` — the same error that made seven
tests red on `main` (`tests.test_origination_upgrade.LiveModelResearch` × 4,
`tests.test_f9d0a5a2` × 1 and two more) and that would have failed the
publisher's regression step before it built or deployed anything.

These tests fail loudly if the import disappears again, and they pin the reason
(the names actually used) rather than the exact import line, so a future
refactor that imports the module differently still passes.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINATE = ROOT / 'scripts' / 'originate.py'


class TheCollectionEntryPointCanSeeEveryModuleItUses(unittest.TestCase):
    def setUp(self):
        self.source = ORIGINATE.read_text()
        self.tree = ast.parse(self.source)

    def imported_modules(self) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split('.')[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.update(alias.name for alias in node.names)
                if node.module:
                    names.add(node.module.split('.')[-1])
        return names

    def test_egw_live_is_imported_because_live_collect_uses_it(self):
        self.assertIn('egw_live.', self.source, 'the EGW rung was removed; delete this test too')
        self.assertIn('egw_live', self.imported_modules())

    def test_live_collect_imports_still_resolve(self):
        import importlib

        module = importlib.import_module('scripts.originate')
        for name in ('egw_live', 'form_model', 'hltv_ranking', 'network_model',
                     'pinnacle_lines', 'smarkets_lines', 'reference_odds'):
            self.assertTrue(hasattr(module, name), f'scripts.originate no longer binds {name}')

    def test_the_collection_runs_its_first_real_statement(self):
        """The regression itself: `live_collect` must not raise NameError."""
        import tempfile
        from scripts import originate

        with tempfile.TemporaryDirectory() as folder:
            try:
                originate.live_collect(Path(folder), [], {})
            except NameError as exc:  # pragma: no cover - only on the broken tree
                self.fail(f'live_collect raised NameError again: {exc}')
            except Exception:
                # A network or environment failure is not this test's subject;
                # the tree only has to get past name resolution.
                pass


if __name__ == '__main__':
    unittest.main()
