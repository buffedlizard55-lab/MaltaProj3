"""Session arena-d202e156: no module may reference a sibling module it never imports.

On 2026-10-23 session arena-43110640 merged PR #240, which wired the automated
EGamersWorld capture into ``scripts/originate.py``. The call sites referenced
``egw_live.EVIDENCE_NAME`` but the module was never imported, so every call to
``originate.live_collect`` raised ``NameError`` before it could write a single
row. That killed the four-hour refresh: runs 40037957529, 40048429858 and
40063011446 all failed at the regression step, and the live site stayed on the
2026-10-23T20:10:00Z snapshot for hours.

The failure is invisible to a syntax check and to ``python -m compileall`` — it
only appears when the code path runs. These tests make it a build-time failure
again by statically resolving every sibling-module name used in every
``scripts/*.py`` module, and by importing every module so a missing symbol
surfaces at collection time rather than three hours later in a scheduled run.
"""
from __future__ import annotations

import ast
import importlib
import pathlib
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / 'scripts'


def _module_names() -> dict[str, pathlib.Path]:
    return {p.stem: p for p in sorted(SCRIPTS.glob('*.py')) if p.stem.isidentifier()}


def _bound_names(tree: ast.AST) -> set[str]:
    """Every name a module binds locally: defs, classes, assignments, args."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            bound.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
            bound.add(node.optional_vars.id)
        elif isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
        elif isinstance(node, (ast.Import,)):
            bound.update(a.asname or a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            bound.update(a.asname or a.name for a in node.names)
        elif isinstance(node, ast.Global):
            bound.update(node.names)
        elif isinstance(node, ast.Nonlocal):
            bound.update(node.names)
    return bound


def _used_names(tree: ast.AST) -> set[str]:
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.value.id for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    return used


class SiblingModuleWiring(unittest.TestCase):
    def test_no_module_uses_a_sibling_module_it_does_not_import(self):
        modules = _module_names()
        self.assertTrue(modules, 'no scripts/*.py found')
        problems = []
        for name, path in modules.items():
            tree = ast.parse(path.read_text())
            missing = sorted(_used_names(tree) & set(modules) - _bound_names(tree))
            if missing:
                problems.append(f'{name}.py uses {missing} without importing it')
        self.assertEqual(problems, [], '; '.join(problems))

    def test_originate_wires_the_automated_egw_capture(self):
        from scripts import egw_live, originate
        self.assertIs(originate.egw_live, egw_live)
        # The live collector must be able to name the evidence file it deletes
        # and rewrites; a missing attribute would fail the same way a missing
        # import did.
        for attr in ('EVIDENCE_NAME', 'INDEX_URL', 'INDEX_EVIDENCE', 'entries_for'):
            self.assertTrue(hasattr(egw_live, attr), f'egw_live.{attr} missing')
        self.assertTrue(originate.egw_live.EVIDENCE_NAME.endswith('.json'))


class EveryModuleImports(unittest.TestCase):
    def test_every_script_module_imports(self):
        modules = _module_names()
        failures = []
        for name in modules:
            try:
                importlib.import_module(f'scripts.{name}')
            except Exception as exc:  # noqa: BLE001 - report every failure
                failures.append(f'scripts.{name}: {type(exc).__name__}: {exc}')
        self.assertEqual(failures, [], '; '.join(failures))


if __name__ == '__main__':
    unittest.main()
