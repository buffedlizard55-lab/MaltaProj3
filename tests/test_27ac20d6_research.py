"""Session arena-27ac20d6: HLTV-first research dossier + executive-summary contract.

The brief asks for (1) picks for every Hotspawn CS2 match, with research into
HLTV and esportsbook lines for the matches the featured method cannot
resolve, (2) a separate section for unresolved picks and their limitations
inside the executive summary, and (3) an executive summary whose in-site
links make the updated picks findable on a phone.

These tests pin this session's contribution without ever writing a
probability: the dossier's reads all carry dated https sources, the two
raw-unresolved blockers reproduce from the committed official Valve
standings, the published model rows replay from that same evidence, and the
committed landing page carries the summary sections, links and sourced
glance rows. Figure-specific assertions live behind the verifier's snapshot
guard (they ``skip`` once a newer snapshot replaces 2026-10-25T05:12:25Z),
and freshness is informational only - a test that fails because time passed
is how earlier sessions froze the publisher.
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "data" / "research" / "27ac20d6"


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_27ac20d6", ROOT / "scripts" / "27ac20d6_verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = _load_verifier()
REPORT = VERIFIER.run(ROOT)
BY_NAME = {c["name"]: c for c in REPORT["checks"]}


class DossierTests(unittest.TestCase):
    def test_every_dossier_row_is_dated_and_sourced(self):
        self.assertEqual(BY_NAME["dossier-integrity"]["status"], "pass",
                         BY_NAME["dossier-integrity"]["detail"])

    def test_dossier_never_claims_to_write_a_pick(self):
        research = json.loads((DOSSIER / "research.json").read_text(encoding="utf-8"))
        self.assertIn("never as win probabilities", research["method"])
        for fixture in research["fixtures"]:
            self.assertTrue(fixture["reads"], fixture["fixture_id"])
            self.assertTrue(fixture["limitations"], fixture["fixture_id"])

    def test_flags_follow_the_register_shape(self):
        flags = json.loads((DOSSIER / "flags.json").read_text(encoding="utf-8"))
        self.assertTrue(flags)
        for flag in flags:
            self.assertTrue(flag["id"].startswith("27ac20d6-"), flag["id"])
            self.assertIn(flag["severity"], {"info", "warning", "error"})
            self.assertTrue(flag["source_urls"], flag["id"])


class ValveEvidenceTests(unittest.TestCase):
    def test_both_raw_blockers_reproduce_from_official_standings(self):
        self.assertEqual(BY_NAME["valve-evidence-identities"]["status"], "pass",
                         BY_NAME["valve-evidence-identities"]["detail"])

    def test_1082792_crosscheck_stays_inside_its_stated_bounds(self):
        self.assertEqual(BY_NAME["valve-crosscheck-1082792"]["status"], "pass",
                         BY_NAME["valve-crosscheck-1082792"]["detail"])
        # The dossier quotes 94.1% (verified core) and 98.4% (weaker core);
        # the replayed formula must keep saying so.
        self.assertAlmostEqual(VERIFIER.valve_probability(1437, 944) * 100, 94.1, delta=0.15)
        self.assertAlmostEqual(VERIFIER.valve_probability(1437, 701) * 100, 98.4, delta=0.15)


class ExecutiveSummaryContractTests(unittest.TestCase):
    def test_summary_sections_and_links_exist_on_the_landing_page(self):
        for name in ("exec-summary-sections", "exec-summary-links"):
            self.assertEqual(BY_NAME[name]["status"], "pass", BY_NAME[name]["detail"])

    def test_every_glance_row_is_marked_sourced_and_anchored(self):
        self.assertEqual(BY_NAME["glance-rows-sourced"]["status"], "pass",
                         BY_NAME["glance-rows-sourced"]["detail"])

    def test_snapshot_bound_checks_pass_or_skip_never_silently_absent(self):
        for name in ("glance-snapshot-parity", "unresolved-register-names",
                     "valve-replay-model-rows"):
            self.assertIn(name, BY_NAME)
            self.assertIn(BY_NAME[name]["status"], {"pass", "skip"}, BY_NAME[name]["detail"])

    def test_freshness_is_reported_not_failed(self):
        info = [c for c in REPORT["checks"] if c["status"] == "info"]
        self.assertTrue(info, "the verifier must surface snapshot age as information")


if __name__ == "__main__":
    unittest.main()
