"""Inventory replay from the rendered lobby when the fixture API is refused.

Evidence (2026-10-23T10:14Z, hosted runner): the scheduled-fixture API answered
HTTP 403 while both lobby pages still rendered the same public array in their
ng-state block. The refresh failed closed, kept a 29-minute-old snapshot, and
every page told readers not to treat 30 source-backed picks as current. These
tests pin the substituted surface to its own saved evidence so no published row
can be replayed from memory.
"""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate import check_inventory


def fixture(i, sport='cs2'):
    return {'id': str(i), 'sport_alias': sport, 'participants0_name': 'A', 'participants1_name': 'B'}


class InventoryFallbackReplay(unittest.TestCase):
    def tree(self, context, rendered_rows, requests, api_rows=None):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        evidence = Path(folder.name) / 'evidence'
        evidence.mkdir(parents=True)
        (evidence / 'hotspawn-context.json').write_text(json.dumps(context))
        (evidence / 'hotspawn-rendered-fixtures.json').write_text(json.dumps({
            'observed_at': '2026-10-23T10:14:05Z', 'pages': ['lobby', 'cs2'],
            'api_error': 'hotspawn-fixtures: 403 Client Error: Forbidden', 'rows': rendered_rows}))
        if api_rows is not None:
            (evidence / 'hotspawn-fixtures.json').write_text(json.dumps(api_rows))
        data = {'inventory_observed_at': '2026-10-23T10:14:05Z', 'requests': requests}
        return evidence, data

    def rendered_context(self, **overrides):
        context = {
            'observed_at': '2026-10-23T10:14:05Z', 'api_ids': [], 'rendered_ids': ['1', '2'],
            'lobby_ids': ['1', '2'], 'cs2_ids': ['1', '2'], 'verified_pages': ['lobby', 'cs2'],
            'crosscheck': 'rendered', 'inventory_source': 'rendered-lobby',
        }
        context.update(overrides)
        return context

    def requests(self, api_status='error'):
        return [{'id': 'hotspawn-fixtures', 'status': api_status, 'observed_at': '2026-10-23T10:14:05Z'},
                {'id': 'hotspawn-lobby', 'status': 'ok', 'observed_at': '2026-10-23T10:14:05Z'}]

    def test_a_rendered_snapshot_replays_from_the_saved_page_payload(self):
        evidence, data = self.tree(self.rendered_context(), [fixture(1), fixture(2)], self.requests())
        raw, context, _ = check_inventory(evidence, [{'id': '1'}, {'id': '2'}], data)
        self.assertEqual(sorted(raw), ['1', '2'])
        self.assertEqual(context['inventory_source'], 'rendered-lobby')

    def test_claiming_api_rows_in_rendered_mode_is_rejected(self):
        evidence, data = self.tree(self.rendered_context(api_ids=['1', '2']), [fixture(1), fixture(2)], self.requests())
        with self.assertRaisesRegex(ValueError, 'must not claim rows'):
            check_inventory(evidence, [{'id': '1'}, {'id': '2'}], data)

    def test_a_rendered_marker_without_the_failed_api_attempt_is_rejected(self):
        evidence, data = self.tree(self.rendered_context(), [fixture(1), fixture(2)], self.requests(api_status='ok'))
        with self.assertRaisesRegex(ValueError, 'refused API attempt'):
            check_inventory(evidence, [{'id': '1'}, {'id': '2'}], data)

    def test_a_rendered_marker_must_match_the_pages_actually_read(self):
        evidence, data = self.tree(self.rendered_context(crosscheck='complete'), [fixture(1), fixture(2)], self.requests())
        with self.assertRaisesRegex(ValueError, 'cross-check marker'):
            check_inventory(evidence, [{'id': '1'}, {'id': '2'}], data)

    def test_a_rendered_payload_must_cover_every_published_row(self):
        evidence, data = self.tree(self.rendered_context(), [fixture(1)], self.requests())
        with self.assertRaisesRegex(ValueError, 'omits or invents'):
            check_inventory(evidence, [{'id': '1'}, {'id': '2'}], data)

    def test_an_api_snapshot_still_replays_from_the_api_evidence(self):
        context = self.rendered_context(api_ids=['1'], rendered_ids=[], crosscheck='complete',
                                        inventory_source='fixture-api', lobby_ids=['1'], cs2_ids=['1'])
        evidence, data = self.tree(context, [fixture(9)], self.requests(api_status='ok'), api_rows=[fixture(1)])
        (evidence / 'hotspawn-rendered-fixtures.json').unlink()
        data['requests'][0]['evidence'] = 'data/evidence/hotspawn-fixtures.json'
        raw, _, _ = check_inventory(evidence, [{'id': '1'}], data)
        self.assertEqual(sorted(raw), ['1'])


if __name__ == '__main__':
    unittest.main()
