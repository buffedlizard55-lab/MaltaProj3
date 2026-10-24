"""Session 719a314a: the executive summary renders the dated no-line block once.

`pages.yml` runs its regression suite *before* it collects anything, so one
duplicated element id stops every scheduled refresh and the served site goes
stale. That is what happened between 2026-10-23T20:10Z and this session: runs
40037957529, 40048429858 and 40063011446 each failed the pre-collection
regression step, and `tests/test_ca7e10e5_snapshot.py` reproduces it locally on
this head with `AssertionError: 2 != 1`.

Cause: `summary()` appended `unresolved_register(..., compact=True)`, whose
compact branch already appends `no_line_research_block`, and then appended the
same block again — so `site/index.html` carried `id="no-line-research"` twice.

These tests pin the fix at function level (no build needed), keep the
cross-session contract that `#no-line-research` is present on the executive
summary for `scripts/eea4c104_audit.py`, and fail if any other duplicate id is
introduced by the same call path.
"""
from __future__ import annotations

import json
import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from scripts.build import summary, unresolved_register

ROOT = Path(__file__).resolve().parents[1]


def load_data() -> dict:
    """The repository's replay fixture, in the shape `scripts.build` consumes."""
    data = json.loads((ROOT / 'data/latest.json').read_text())
    origination = ROOT / 'data/origination.json'
    if origination.is_file():
        data['complete_picks'] = json.loads(origination.read_text())
    return data


# A retained dated sweep in the schema `scripts/build.py::load_no_line_research`
# accepts: an observation time, a record path and per-fixture rows.
DATED_RECORD = {
    'observed_at': '2026-10-24T05:41:00Z',
    'environment': 'github-actions-runner',
    '_record_path': 'research/719a314a/line-source-research.json',
    'per_fixture': [
        {'id': '1079198', 'teams': ['Metizport', 'BakS'], 'money_line_lead': None},
    ],
}


class _Ids(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == 'id' and value:
                self.ids.append(value)


def ids_in(html: str) -> Counter:
    parser = _Ids()
    parser.feed(html)
    return Counter(parser.ids)


class OneDatedBlockPerSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = load_data()

    def data(self, **overrides):
        data = json.loads(json.dumps(self.base))
        data.update(overrides)
        return data

    def test_a_retained_dated_record_renders_the_anchor_once(self):
        html = summary(self.data(_no_line_research=DATED_RECORD), './')
        self.assertEqual(html.count('id="no-line-research"'), 1)
        self.assertIn('latest dated research', html)

    def test_the_degraded_empty_record_path_renders_it_once(self):
        # A loader key present but empty renders the dated-records note; it must
        # not render twice either.
        html = summary(self.data(_no_line_research={}), './')
        self.assertEqual(html.count('id="no-line-research"'), 1)

    def test_no_duplicate_element_ids_anywhere_in_the_summary(self):
        for record in (DATED_RECORD, {}):
            counts = ids_in(summary(self.data(_no_line_research=record), './'))
            duplicated = {name: n for name, n in counts.items() if n > 1}
            self.assertEqual(duplicated, {}, f'duplicate ids with record={record!r}')

    def test_the_summary_is_the_only_copy_on_the_executive_summary(self):
        # main's e360f4c (PR #241) fixed the duplicate by dropping the block from
        # the compact register; the summary keeps exactly one. Pin both halves so
        # a future change cannot reintroduce the second copy.
        data = self.data(_no_line_research=DATED_RECORD)
        compact = unresolved_register(data, './', compact=True)
        self.assertNotIn('id="no-line-research"', compact)
        self.assertEqual(summary(data, './').count('id="no-line-research"'), 1)

    def test_a_summary_without_a_dated_record_publishes_no_such_anchor(self):
        # Documented, unchanged behaviour: no loader result key at all emits
        # nothing (session 3016b0c6's absence contract).
        data = self.data()
        data.pop('_no_line_research', None)
        self.assertNotIn('id="no-line-research"', unresolved_register(data, './', compact=True))
        self.assertNotIn('id="no-line-research"', summary(data, './'))

    def test_same_page_links_on_the_summary_all_resolve(self):
        html = summary(self.data(_no_line_research=DATED_RECORD), './')
        anchors = set(ids_in(html))
        fragments = set(re.findall(r'href="\./#([^"]+)"', html))
        self.assertTrue(fragments, 'the summary should deep-link to its own sections')
        self.assertEqual(fragments - anchors, set())


if __name__ == '__main__':
    unittest.main()
