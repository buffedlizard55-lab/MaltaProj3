"""Regression (session c07e1b40): the publisher's snapshot cache must actually be restorable.

actions/cache derives a cache *version* from the exact `path:` list. PR #34 made the
restore list end with `data/origination/` while the save list ended with
`data/origination/evidence/`, so no saved snapshot could ever be restored and the
outage fallback silently degraded to the old checked-in data. A restore of
`data/origination/` would also have overlaid the reviewed alias registry.
"""
import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'pages.yml'


def cache_paths(text: str, action: str) -> list[str]:
    match = re.search(r'uses: actions/cache/' + action + r'@[^\n]+\n\s+with:\n\s+path: \|\n((?:\s{12}\S[^\n]*\n)+)', text)
    if not match:
        raise AssertionError(f'actions/cache/{action} step with a path block not found')
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


class PublisherCacheTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text()

    def test_restore_and_save_use_the_identical_path_list(self):
        self.assertEqual(cache_paths(self.text, 'restore'), cache_paths(self.text, 'save'))

    def test_reviewed_alias_registry_is_never_cached(self):
        for action in ('restore', 'save'):
            paths = cache_paths(self.text, action)
            self.assertNotIn('data/origination/', paths)
            self.assertFalse(any(p.endswith('aliases.json') for p in paths), paths)


if __name__ == '__main__':
    unittest.main()
