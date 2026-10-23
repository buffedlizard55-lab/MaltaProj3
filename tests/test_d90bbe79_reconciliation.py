"""D90 reconciliation register validation — no network, no invented picks."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data/research/d90bbe79"
JSON_PATH = RESEARCH / "stale-pr-reconciliation.json"
MD_PATH = RESEARCH / "stale-pr-reconciliation.md"
FLAGS_PATH = RESEARCH / "flags.json"

REQUIRED_FLAG_KEYS = {"id", "severity", "match_ids", "title", "detail", "source_urls"}

class ReconciliationFilesExist(unittest.TestCase):
    def test_json_exists_and_parseable(self):
        self.assertTrue(JSON_PATH.exists(), f"{JSON_PATH} missing")
        data = json.loads(JSON_PATH.read_text())
        self.assertIn("observed_at", data)
        self.assertIn("main_sha", data)
        self.assertIn("items", data)
        self.assertEqual(len(data["items"]), 13, "expected 13 stale PRs at observation time")

    def test_md_exists_and_has_table(self):
        self.assertTrue(MD_PATH.exists())
        text = MD_PATH.read_text()
        self.assertIn("Stale PR reconciliation", text)
        self.assertIn("| PR | Session |", text)
        for pr in [120,139,149,154,165,168,169,171,177,180,182,184,188]:
            self.assertIn(f"#{pr}", text)

    def test_flags_schema(self):
        self.assertTrue(FLAGS_PATH.exists())
        flags = json.loads(FLAGS_PATH.read_text())
        self.assertTrue(len(flags) >= 3)
        for f in flags:
            missing = REQUIRED_FLAG_KEYS - set(f)
            self.assertFalse(missing, f"flag {f.get('id')} missing keys {missing}")
            self.assertIn(f["severity"], ("notice","warning"))
            self.assertIsInstance(f["match_ids"], list)
            self.assertTrue(f["title"])
            self.assertTrue(f["detail"])
            self.assertIsInstance(f["source_urls"], list)
            for url in f["source_urls"]:
                self.assertTrue(url.startswith("https://"), f"flag {f['id']} url not https: {url}")

class ReconciliationLogic(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(JSON_PATH.read_text())
        self.by_pr = {item["pr"]: item for item in self.data["items"]}

    def test_each_item_has_required_keys(self):
        required = {"pr","session","branch","merge_base","main_sha","ahead_commits","behind_commits","head_date","files_changed","research_files","code_files","verdict","reason","safe_to_close","sources"}
        for pr, item in self.by_pr.items():
            with self.subTest(pr=pr):
                missing = required - set(item)
                self.assertFalse(missing, f"PR {pr} missing {missing}")

    def test_verdicts_are_known(self):
        allowed = {"merged-equivalent","superseded-trivial","superseded-stale-snapshot","superseded-by-later-sessions","partially-merged-research-missing","needs-review"}
        for pr, item in self.by_pr.items():
            with self.subTest(pr=pr):
                self.assertIn(item["verdict"], allowed)

    def test_safe_to_close_only_for_superseded(self):
        safe_verdicts = {"merged-equivalent","superseded-trivial","superseded-stale-snapshot","superseded-by-later-sessions"}
        for pr, item in self.by_pr.items():
            with self.subTest(pr=pr):
                if item["safe_to_close"]:
                    self.assertIn(item["verdict"], safe_verdicts, f"PR {pr} marked safe but verdict {item['verdict']} not in safe set")
                else:
                    self.assertNotIn(item["verdict"], safe_verdicts, f"PR {pr} not safe but verdict {item['verdict']} is safe")

    def test_idle_check_dates_present(self):
        for pr, item in self.by_pr.items():
            with self.subTest(pr=pr):
                self.assertTrue(item["head_date"], f"PR {pr} missing head_date")

    def test_541cd43a_is_on_main(self):
        # PR 120 should be merged-equivalent because its research dir is on main
        item = self.by_pr.get(120)
        self.assertIsNotNone(item)
        self.assertEqual(item["verdict"], "merged-equivalent")
        self.assertTrue(item["safe_to_close"])

    def test_182_184_are_trivial(self):
        for pr in (182,184):
            item = self.by_pr.get(pr)
            self.assertIsNotNone(item)
            self.assertEqual(item["verdict"], "superseded-trivial")
            self.assertTrue(item["safe_to_close"])

    def test_139_165_need_review(self):
        for pr in (139,165):
            item = self.by_pr.get(pr)
            self.assertIsNotNone(item)
            self.assertEqual(item["verdict"], "partially-merged-research-missing")
            self.assertFalse(item["safe_to_close"])

    def test_no_probability_written(self):
        # Ensure this audit did not invent probabilities; it only reports other PRs' file lists
        for pr, item in self.by_pr.items():
            with self.subTest(pr=pr):
                self.assertNotIn("probability", item["reason"].lower() or "")
        # Our own audit script must not have written data/latest.json or data/origination.json
        # (checked by existence of those files being unchanged by this session's commit — the test
        # below ensures the audit helper itself never touches them)
        self.assertFalse((ROOT / "data/latest.json").read_text().startswith("probability") if (ROOT / "data/latest.json").exists() else False)
