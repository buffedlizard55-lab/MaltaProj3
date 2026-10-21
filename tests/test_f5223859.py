"""Regression tests for session arena-f5223859 audit, review register and mobile summary checks."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import audit_rows, review_register

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / 'data/research/f5223859/unresolved-and-cadence-audit.json'
REVIEW_PATH = ROOT / 'data/research/f5223859/repo-review.json'
FLAGS_PATH = ROOT / 'data/research/f5223859/flags.json'


class SessionF5223859AuditTests(unittest.TestCase):
    def test_audit_dossier_records_cadence_and_three_unresolved_fixtures(self):
        self.assertTrue(AUDIT_PATH.exists())
        audit = json.loads(AUDIT_PATH.read_text())
        self.assertEqual(audit['session'], 'arena-f5223859')
        self.assertTrue(audit_rows.is_official(audit['production_cadence']['workflow_url']))
        self.assertTrue(audit_rows.is_official(audit['session_live_audit']['annotations_url']))
        unresolved_ids = [f['fixture_id'] for f in audit['session_live_audit']['unresolved_fixtures']]
        self.assertEqual(unresolved_ids, ['1082762', '1082763', '1082837'])
        for item in audit['session_live_audit']['unresolved_fixtures']:
            self.assertTrue(audit_rows.is_official(item['hotspawn_url']), item['fixture_id'])
        fallback_ids = [f['fixture_id'] for f in audit['session_live_audit']['fallback_resolutions_verified']]
        self.assertEqual(fallback_ids, ['1082831', '1082792', '1082836'])
        for item in audit['session_live_audit']['fallback_resolutions_verified']:
            self.assertTrue(audit_rows.is_official(item['source_url']), item['fixture_id'])

    def test_repo_review_register_is_declared_valid_and_official_linked(self):
        self.assertIn('research/f5223859/repo-review.json', review_register.REGISTERS)
        self.assertTrue(REVIEW_PATH.exists())
        register = json.loads(REVIEW_PATH.read_text())
        review_register.validate(register)
        self.assertEqual(register['session'], 'arena-f5223859')
        for item in register['items']:
            self.assertTrue(item['id'].startswith('f52-'), item['id'])
            for ev in item['evidence']:
                self.assertTrue(audit_rows.is_official(ev['url']), f"{item['id']}: {ev['url']}")
        rendered = review_register.render(register, '../', section_id='session-review-f52',
                                          register_path='research/f5223859/repo-review.json',
                                          include_shared=False)
        report = audit_rows.audit_html(rendered, 'review/index.html')
        self.assertEqual(report['violation'], 0, report['violations'])
        self.assertEqual(report['rows'], len(register['items']))

    def test_session_flags_have_unique_ids_and_official_sources(self):
        self.assertTrue(FLAGS_PATH.exists())
        flags = json.loads(FLAGS_PATH.read_text())
        self.assertGreaterEqual(len(flags), 3)
        seen = set()
        for flag in flags:
            self.assertTrue(flag['id'].startswith('f5223859-'), flag['id'])
            self.assertNotIn(flag['id'], seen)
            seen.add(flag['id'])
            self.assertIn(flag['severity'], {'notice', 'warning'})
            self.assertTrue(flag['source_urls'], flag['id'])
            for url in flag['source_urls']:
                self.assertTrue(audit_rows.is_official(url), f"{flag['id']}: {url}")


if __name__ == '__main__':
    unittest.main()
