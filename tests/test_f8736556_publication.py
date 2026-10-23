"""Session f8736556 publication-order contract.

GitHub Pages remains in legacy mode for this repository. The interim
``republish-last-verified`` job is only protective if its artifact deployment
happens *after* the same commit's legacy build. On 2026-10-23 the interim job
finished at 09:54:58Z and the legacy build finished at 09:55:18Z, leaving
current HTML beside 15 October plain JSON at the next audit. These tests pin
that ordering without changing any pick, probability or data fixture.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from scripts.root_publish import wait_for_legacy_pages_build

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/pages.yml"


class PublicationOrderTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text()
        self.republish = self.text.split("  verify-and-deploy:", 1)[0]

    def test_interim_deploy_waits_for_this_commits_legacy_build(self):
        upload = self.republish.index("name: github-pages-interim")
        wait = self.republish.index(
            "name: Wait for this commit's legacy Pages build before interim deployment"
        )
        deploy = self.republish.index("artifact_name: github-pages-interim")
        self.assertLess(upload, wait)
        self.assertLess(wait, deploy)
        wait_block = self.republish[wait:deploy]
        self.assertIn("scripts.root_publish --wait-legacy-sha", wait_block)
        self.assertIn("${{ github.sha }}", wait_block)
        self.assertIn("continue-on-error: true", wait_block)

    def test_final_root_sync_still_redeploys_and_reverifies_after_its_legacy_build(self):
        publish = self.text.index("name: Publish the verified build into the branch root")
        wait = self.text.index("name: Wait for the root-sync commit's legacy Pages build")
        redeploy = self.text.index("name: Re-deploy the verified artifact over the legacy root build")
        verify = self.text.index("name: Verify the public site after root-sync re-deploy")
        self.assertLess(publish, wait)
        self.assertLess(wait, redeploy)
        self.assertLess(redeploy, verify)

    def test_root_sync_never_copies_deterministic_data_fixtures(self):
        publisher = (ROOT / "scripts/root_publish.py").read_text()
        self.assertIn('SKIP_DIRS = {"data", "docs", "archive"', publisher)
        self.assertIn('NEVER copied: ``data/*``', publisher)

    def test_deploy_verifier_checks_the_plain_json_paths(self):
        verifier = (ROOT / "scripts/verify_live.py").read_text()
        self.assertIn("get('data/latest.json')", verifier)
        self.assertIn("get('data/origination.json')", verifier)
        self.assertNotIn("data//latest.json", verifier)
        self.assertNotIn("data//origination.json", verifier)

    def test_building_pages_status_does_not_treat_delayed_run_listing_as_finished(self):
        class Response:
            def __init__(self, body):
                self._body = body

            def raise_for_status(self):
                return None

            def json(self):
                return self._body

        class Session:
            def __init__(self, pages_status):
                self.pages_status = pages_status
                self.dynamic_calls = 0

            def get(self, url, headers=None, params=None, timeout=20):
                if url.endswith("/pages"):
                    return Response(
                        {"build_type": "legacy", "status": self.pages_status}
                    )
                self.dynamic_calls += 1
                if self.dynamic_calls < 4:
                    return Response({"workflow_runs": []})
                return Response(
                    {
                        "workflow_runs": [
                            {
                                "id": 39935261124,
                                "name": "pages-build-deployment",
                                "status": "completed",
                                "conclusion": "success",
                                "head_sha": "abc123",
                            }
                        ]
                    }
                )

        building = Session("building")
        summary = wait_for_legacy_pages_build(
            "owner/repo",
            "abc123",
            "token",
            session=building,
            attempts=6,
            pause=0,
            initial_polls=2,
        )
        self.assertEqual(summary["pages_status"], "building")
        self.assertEqual(building.dynamic_calls, 4)
        self.assertEqual(summary["legacy_runs"][0]["status"], "completed")

        built = Session("built")
        summary = wait_for_legacy_pages_build(
            "owner/repo",
            "abc123",
            "token",
            session=built,
            attempts=6,
            pause=0,
            initial_polls=2,
        )
        self.assertEqual(summary["legacy_runs"], [])
        self.assertEqual(built.dynamic_calls, 3)

    def test_refresh_cadence_stays_inside_four_to_eight_hours(self):
        self.assertIn("- cron: '17 */4 * * *'", self.text)
        self.assertIn("- cron: '47 2-22/4 * * *'", self.text)


if __name__ == "__main__":
    unittest.main()
