"""Session arena-fc985c7b: a missing module-level name must never reach `main`.

What happened. PR #240 (session arena-43110640) added `scripts/egw_live.py` and
called it from `scripts/originate.py::live_collect`, but never imported it. The
first statement of that rung is

    (evidence_dir / egw_live.EVIDENCE_NAME).unlink(missing_ok=True)

which sits *before* the `try:` that was supposed to make an aggregator outage
non-fatal, so the whole Hotspawn/line collection step raised
`NameError: name 'egw_live' is not defined`. Because `pages.yml` runs
`python -m unittest discover -s tests` as a pre-collection regression gate, the
nine tests that exercise `live_collect()` (in `test_f9d0a5a2`,
`test_origination_upgrade` and `test_source_integrity`) failed and every
four-hour refresh died. Observed locally on `bdb4fc9` at 2026-10-24T06:30Z.

This guard is deliberately **static**: it never imports the modules under test
(several of them issue live HTTP requests at import time) and never needs the
network. For every module in `scripts/` it asks the standard library's
`symtable` which identifiers resolve to module scope, and fails if any of them
is referenced but never bound at module level, never imported, and not a
builtin.
"""
from __future__ import annotations

import builtins
import pathlib
import symtable
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'

# Names Python binds implicitly in every module, plus the ones this repository
# uses at module level without an explicit assignment.
IMPLICIT = frozenset({
    '__name__', '__doc__', '__file__', '__package__', '__spec__', '__loader__',
    '__builtins__', '__path__', '__all__', '__debug__', '__dict__',
})


def module_level_names(table: symtable.SymbolTable) -> set[str]:
    """Every identifier the module scope binds (assignment, import, def, class)."""
    bound = set(IMPLICIT)
    for symbol in table.get_symbols():
        if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace():
            bound.add(symbol.get_name())
    return bound


def unresolved_globals(source: str, filename: str) -> list[tuple[str, str]]:
    """Identifiers that resolve to module scope but are never bound there."""
    table = symtable.symtable(source, filename, 'exec')
    bound = module_level_names(table)
    missing: list[tuple[str, str]] = []
    seen: set[str] = set()

    def walk(node: symtable.SymbolTable) -> None:
        for symbol in node.get_symbols():
            name = symbol.get_name()
            if not symbol.is_referenced():
                continue
            if symbol.is_local() or symbol.is_free() or symbol.is_parameter():
                continue
            if not symbol.is_global():
                continue
            if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace():
                continue
            if name in bound or hasattr(builtins, name):
                continue
            if name in seen:
                continue
            seen.add(name)
            missing.append((name, type(node).__name__))
        for child in node.get_children():
            walk(child)

    walk(table)
    return missing


class ScriptsModuleNameGuard(unittest.TestCase):
    """No script may reference a name it never defines or imports."""

    def test_every_script_module_references_only_bound_names(self):
        self.assertTrue(SCRIPTS.is_dir(), f'expected a scripts directory at {SCRIPTS}')
        found: dict[str, list[tuple[str, str]]] = {}
        for path in sorted(SCRIPTS.glob('*.py')):
            source = path.read_text(encoding='utf-8')
            try:
                missing = unresolved_globals(source, str(path))
            except SyntaxError as exc:  # a syntax error is its own failure
                self.fail(f'{path.name} does not parse: {exc}')
            if missing:
                found[path.name] = missing
        self.assertEqual(
            {}, found,
            'modules reference identifiers that are never imported or assigned '
            '(this is the class of defect that broke live_collect on 2026-10-24): '
            + '; '.join(f'{name}: {names}' for name, names in sorted(found.items())))

    def test_the_guard_would_have_caught_the_egw_live_regression(self):
        """Self-check: the guard fires on the exact defect it was written for."""
        broken = (
            'from scripts import reference_odds\n'
            '\n'
            'def live_collect(evidence_dir):\n'
            '    (evidence_dir / egw_live.EVIDENCE_NAME).unlink(missing_ok=True)\n'
            '    return egw_live.INDEX_URL\n'
        )
        names = {name for name, _ in unresolved_globals(broken, 'broken.py')}
        self.assertIn('egw_live', names)

        fixed = 'from scripts import egw_live\n' + broken
        self.assertEqual([], unresolved_globals(fixed, 'fixed.py'))


if __name__ == '__main__':
    unittest.main()
