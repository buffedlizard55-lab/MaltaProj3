"""Live-collect import guard for the automated EGamersWorld rung (session arena-da8067f5).

Why this file exists
--------------------
The scheduled publisher was down from 2026-10-23T19:57Z. Its `pages.yml`
"Regression tests" step failed on run 40063011446, and the failure was not a
flaky data problem: `scripts/originate.py::live_collect` called
`egw_live.EVIDENCE_NAME`, `egw_live.INDEX_URL`, `egw_live.INDEX_EVIDENCE` and
`egw_live.entries_for` while the module was never imported, so every call raised

    NameError: name 'egw_live' is not defined      (scripts/originate.py:1044)

Nine unittest cases that drive `live_collect` therefore errored, the workflow
stopped before it collected anything, and no fresh snapshot could be published.

These tests are deliberately cheap and network-free:

* the module identity guard fails the moment the import is dropped again;
* the offline smoke test runs the whole `live_collect` body with every fetch
  raising, and proves the EGW rung fails *open* (a recorded reason, no price)
  rather than aborting the refresh;
* the static scope guard catches the same class of mistake anywhere in
  `scripts/originate.py`: a name that is read inside a function but is neither
  bound there, imported, defined at module level, nor a builtin.
"""
from __future__ import annotations

import ast
import builtins
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import egw_live, originate

REPO = Path(__file__).resolve().parents[1]
ORIGINATE = REPO / 'scripts' / 'originate.py'


class EgwRungImportTests(unittest.TestCase):
    def test_originate_and_egw_live_are_the_same_module(self):
        """The rung must be reachable from the module that calls it."""
        self.assertIs(originate.egw_live, egw_live)
        self.assertTrue(originate.egw_live.EVIDENCE_NAME)
        self.assertTrue(originate.egw_live.INDEX_URL.startswith('https://'))

    def test_live_collect_survives_every_source_failing(self):
        """Offline: the EGW rung records a reason and prices nothing."""
        fixture = {
            'id': '1079658', 'teams': [{'id': '239293', 'name': 'Acend'},
                                       {'id': '172275', 'name': 'FORZE Reload'}],
            'competition': 'CCT Europe 2026 Series #11', 'starts_at': '2026-10-24T08:00:00Z',
            'locks_at': '2026-10-24T07:54:00Z', 'source_status': 'scheduled',
            'best_of': None, 'series_format': None, 'tier': 'b', 'availability': 'open',
            'analysis': None, 'pick_index': None, 'research': [], 'limitations': [],
        }

        def refuse(*_args, **_kwargs):
            raise RuntimeError('no egress in this test')

        with TemporaryDirectory() as tmp, \
                patch.object(originate.Collector, 'get_json', new=refuse), \
                patch.object(originate.Collector, 'fetch_html', new=refuse):
            out = originate.live_collect(Path(tmp), [dict(fixture)], {'aliases': []})

        self.assertIn('egw_live_error', out)
        self.assertNotIn('egw_live', out)
        # A refused index must not leave a stale derived entry behind.
        self.assertFalse((Path(tmp) / egw_live.EVIDENCE_NAME).exists())
        json.dumps(out)  # the record stays JSON-serialisable


def _bound_names(node):
    """Every name bound anywhere inside a function (heuristic, over-inclusive)."""
    bound = set()
    for child in ast.walk(node):
        if isinstance(child, ast.arg):
            bound.add(child.arg)
        elif isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            bound.add(child.id)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(child.name)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            bound.add(child.name)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            for alias in child.names:
                bound.add((alias.asname or alias.name).split('.')[0])
        elif isinstance(child, ast.Global) or isinstance(child, ast.Nonlocal):
            bound.update(child.names)
    return bound


class StaticScopeTests(unittest.TestCase):
    """A read that resolves to nothing is a NameError waiting for a refresh."""

    def test_every_name_read_in_originate_resolves(self):
        tree = ast.parse(ORIGINATE.read_text())
        module_names = set()
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    module_names.add((alias.asname or alias.name).split('.')[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                module_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    module_names.update(n.id for n in ast.walk(target)
                                        if isinstance(n, ast.Name))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                module_names.add(node.target.id)

        allowed = module_names | set(dir(builtins)) | {'__file__', '__name__', '__doc__'}
        problems = []

        def visit(node, inherited):
            """Check one function body; nested defs inherit the enclosing scope."""
            local = inherited | _bound_names(node)
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    if child.id not in local and child.id not in allowed:
                        problems.append(f'{node.name}: {child.id} (line {child.lineno})')
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                    visit(child, local)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(node, set())
        self.assertEqual(problems, [], 'unresolved names in scripts/originate.py: '
                         + ', '.join(sorted(set(problems))))


if __name__ == '__main__':
    unittest.main()
