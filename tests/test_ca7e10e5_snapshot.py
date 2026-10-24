"""Session ca7e10e5: the published JSON must be the snapshot the page shows.

The site has two publishers. `pages.yml` deploys the built `site/` artifact;
GitHub's *legacy* Pages builder republishes the checked-in branch root on every
push to `main`. `scripts/root_publish.py` duplicates the rendered pages into the
root so both publishers serve current HTML, but it deliberately never copies
`data/` — `data/latest.json` is the repository's CI replay fixture, and rewriting
it would break `scripts.build` on `main`.

The consequence, observed from a GitHub runner at 2026-10-23T09:58Z:

    page data-snapshot-generated  2026-10-23T09:23:57Z
    /data/latest.json             2026-10-15T08:36:13Z   (192.8 h apart)

so every "Open data ↓" / "Full snapshot JSON ↓" link downloaded an eight-day-old
observation. The fix publishes a byte-identical build output, `snapshot.json`,
which the root publisher carries and every page links to.

Nothing here asserts a probability; it asserts file layout and link targets.
"""
from __future__ import annotations

import json
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import root_publish
from scripts.acceptance_audit import check_snapshot_consistency


class BuildPublishesTheDownloadableSnapshot(unittest.TestCase):
    def test_build_writes_a_top_level_snapshot_next_to_the_fixture(self):
        source = Path('scripts/build.py').read_text()
        self.assertIn("shutil.copyfile(output / 'data/latest.json', output / 'snapshot.json')", source)

    def test_pages_link_the_published_snapshot_not_the_fixture(self):
        source = Path('scripts/build.py').read_text()
        self.assertNotIn('data/latest.json">Open data', source)
        self.assertNotIn('data/latest.json">Full snapshot JSON', source)
        self.assertIn('data-data-url="{prefix}snapshot.json"', source)
        self.assertIn('{prefix}snapshot.json', source)

    def test_scripts_load_the_link_target_from_the_same_place(self):
        # The browser fetch and the download link must never disagree.
        source = Path('assets/scout.js').read_text()
        self.assertIn('body.dataset.dataUrl', source)


class RootPublisherCarriesTheSnapshot(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.output, self.root = base / 'site', base / 'root'
        self.output.mkdir()
        self.root.mkdir()
        # File layout and monotonic publication are tested at the fixture's
        # own observation time. Using the wall clock here broke every scheduled
        # refresh after 21:23Z on 23 October, before it could collect fresh data.
        # Production's 12-hour guard remains enabled and is tested below.
        self.now = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
        snapshot = {
            'schema_version': 1, 'generated_at': '2026-10-23T09:23:57Z',
            'counts': {'inventory': 30, 'upcoming': 30, 'picks': 30},
        }
        (self.output / 'data').mkdir()
        (self.output / 'data/latest.json').write_text(json.dumps(snapshot))
        (self.output / 'snapshot.json').write_text(json.dumps(snapshot))
        (self.output / 'index.html').write_text(
            '<html><body data-snapshot-generated="2026-10-23T09:23:57Z">'
            + 'x' * root_publish.MIN_INDEX_BYTES + '</body></html>')

    def tearDown(self):
        self.tmp.cleanup()

    # Session arena-43110640: pin the reference clock. These tests used the
    # wall clock against a fixed 2026-10-23 snapshot, so once that snapshot
    # became 12h old every scheduled pages.yml run failed its regression step
    # before collecting anything (runs 40037957529, 40048429858, 40063011446).
    def _plan(self):
        return root_publish.build_plan(self.output, self.root, now=self.now)

    def test_snapshot_json_is_published(self):
        plan = self._plan()
        self.assertIn('snapshot.json', plan.writes)

    def test_the_replay_fixture_is_still_never_published(self):
        plan = self._plan()
        self.assertFalse([p for p in plan.writes if p.startswith('data/')])

    def test_an_older_build_is_still_refused(self):
        self.root.joinpath('index.html').write_text(
            '<html><body data-snapshot-generated="2026-10-24T00:00:00Z">' + 'x' * 60000
            + '</body></html>')
        plan = self._plan()
        self.assertEqual(plan.writes, {})
        self.assertIn('refusing to move the published site backwards', plan.reason)

    def test_the_age_limit_still_rejects_a_stale_snapshot(self):
        with self.assertRaisesRegex(root_publish.PublishRefused, 'limit 12.0h'):
            root_publish.build_plan(self.output, self.root, now=self.now + timedelta(hours=13))

    def test_the_live_snapshot_url_is_the_published_file(self):
        self.assertTrue(root_publish.LIVE_SNAPSHOT_URL.endswith('/snapshot.json'))


class AcceptanceAuditComparesThePublishedFile(unittest.TestCase):
    """The consistency check must read the file the page actually links to."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / 'data').mkdir()
        (self.site / 'index.html').write_text(
            '<html><body data-snapshot-generated="2026-10-23T09:23:57Z"></body></html>')

    def tearDown(self):
        self.tmp.cleanup()

    def test_current_snapshot_json_passes(self):
        (self.site / 'snapshot.json').write_text(json.dumps({'generated_at': '2026-10-23T09:23:57Z'}))
        check = check_snapshot_consistency(self.site)
        self.assertEqual(check.status, 'pass')

    def test_a_stale_snapshot_json_fails_and_names_the_file(self):
        (self.site / 'snapshot.json').write_text(json.dumps({'generated_at': '2026-10-15T08:36:13Z'}))
        check = check_snapshot_consistency(self.site)
        self.assertEqual(check.status, 'fail')
        self.assertIn('192.8 h apart', check.detail)

    def test_a_stale_fixture_alone_does_not_fail_the_build(self):
        # Artifact builds keep data/latest.json in sync; once snapshot.json is
        # present it is the file a reader downloads, so that is what is checked.
        (self.site / 'data/latest.json').write_text(json.dumps({'generated_at': '2026-10-15T08:36:13Z'}))
        (self.site / 'snapshot.json').write_text(json.dumps({'generated_at': '2026-10-23T09:23:57Z'}))
        self.assertEqual(check_snapshot_consistency(self.site).status, 'pass')

    def test_an_older_tree_without_snapshot_json_still_uses_the_fixture(self):
        (self.site / 'data/latest.json').write_text(json.dumps({'generated_at': '2026-10-23T09:23:57Z'}))
        self.assertEqual(check_snapshot_consistency(self.site).status, 'pass')


class LiveVerificationFollowsTheSameFile(unittest.TestCase):
    def test_verify_live_prefers_snapshot_json_and_falls_back(self):
        source = Path('scripts/verify_live.py').read_text()
        self.assertIn("get('snapshot.json')", source)
        self.assertIn("get('data/latest.json')", source)
        self.assertLess(source.index("get('snapshot.json')"), source.index("get('data/latest.json')"))


class NoStaleFixtureIsLinkedFromAnyRenderedPage(unittest.TestCase):
    def test_built_pages_point_at_snapshot_json(self):
        site = Path('site/index.html')
        if not site.exists():
            self.skipTest('run python -m scripts.build first')
        html = site.read_text()
        self.assertNotIn('data/latest.json', html)
        self.assertIn('snapshot.json', html)
        self.assertRegex(html, r'data-data-url="\./snapshot\.json"')
        self.assertTrue(Path('site/snapshot.json').exists())
        published = json.loads(Path('site/snapshot.json').read_text())
        local = json.loads(Path('site/data/latest.json').read_text())
        self.assertEqual(published, local)


if __name__ == '__main__':
    unittest.main()


class ExecutiveSummaryCarriesTheDatedNoLineResearch(unittest.TestCase):
    """The brief's separate no-line section must be on the executive summary.

    `scripts/eea4c104_audit.py` requires `#no-line-research` on `index.html`, but
    the block was only rendered on `/unresolved/`. `tests.test_eea4c104_audit`
    therefore failed on `main` from 2026-10-23T11:31Z, which stopped the
    four-hour publisher at its regression step (run 39947461194). The block is
    now rendered in `summary()` as well; this pins it so the publisher cannot go
    red for the same reason again.
    """

    def test_summary_renders_the_block_next_to_the_unresolved_register(self):
        source = Path('scripts/build.py').read_text()
        summary_start = source.index('def summary(data, prefix, now=None):')
        summary_body = source[summary_start:source.index('\ndef ', summary_start + 10)]
        # The compact register owns the block. A direct call here duplicated
        # the nested block/ID even though this old source-text test passed.
        self.assertIn('unresolved_register(data, prefix, compact=True)', summary_body)
        self.assertNotIn('out += no_line_research_block(data, prefix)', summary_body)

    def test_the_built_executive_summary_contains_it_once(self):
        site = Path('site/index.html')
        if not site.exists():
            self.skipTest('run python -m scripts.build first')
        html = site.read_text()
        self.assertEqual(html.count('id="no-line-research"'), 1)
