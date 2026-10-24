"""Session 719a314a: `originate.live_collect` must be able to import its EGW rung.

The EGamersWorld reference rung was added to `scripts/originate.py::live_collect`
with the `scripts/egw_live.py` module, but the import was never added. Every live
collection therefore raised `NameError: name 'egw_live' is not defined` at the
evidence-cleanup line *before* the ladder ran, so the four-hour refresh could not
collect at all — visible as nine ERRORs in the full suite
(`tests/test_f9d0a5a2.py`, `tests/test_origination_upgrade.py`,
`tests/test_source_integrity.py`) and reproduced here without any network access.

These tests pin the import at the module boundary, so the failure cannot come
back silently: they fail if the import disappears, if it is added only inside a
function, or if the module loses the names `live_collect` uses.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

from scripts import egw_live, originate

ROOT = Path(__file__).resolve().parents[1]
ORIGINATE = ROOT / 'scripts/originate.py'


class EgwRungIsImportable(unittest.TestCase):
    def test_the_module_exposes_what_live_collect_uses(self):
        self.assertTrue(originate.egw_live is egw_live)
        for name in ('INDEX_URL', 'INDEX_EVIDENCE', 'EVIDENCE_NAME', 'entries_for'):
            self.assertTrue(hasattr(egw_live, name), name)

    def test_the_import_is_at_module_scope(self):
        tree = ast.parse(ORIGINATE.read_text())
        module_level = {alias.name for node in tree.body
                        if isinstance(node, ast.ImportFrom) and node.module == 'scripts'
                        for alias in node.names}
        self.assertIn('egw_live', module_level,
                      'scripts/originate.py must import egw_live at module scope')

    def test_live_collect_references_the_names_the_import_provides(self):
        source = ORIGINATE.read_text()
        start = source.index('def live_collect(')
        body = source[start:source.index('\ndef ', start + 10)]
        used = {name for name in ('INDEX_URL', 'INDEX_EVIDENCE', 'EVIDENCE_NAME', 'entries_for')
                if f'egw_live.{name}' in body}
        self.assertTrue(used, 'live_collect() should use the EGW rung it imports')
        for name in used:
            self.assertTrue(hasattr(egw_live, name), name)


if __name__ == '__main__':
    unittest.main()
