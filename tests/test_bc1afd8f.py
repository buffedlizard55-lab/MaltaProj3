"""Regression tests for session arena-bc1afd8f's read-only modules and its publisher guard.

Nothing here touches the canonical feeds: the probe, the phone audit, the
root-publish risk reproduction and the gate measurement are all read-only, and
these tests exercise them on synthetic trees in temporary directories.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import bc1afd8f_gate as gate
from scripts import bc1afd8f_mobile_audit as mobile
from scripts import bc1afd8f_probe as probe
from scripts import bc1afd8f_root_risk as risk
from scripts.build_origination import expected_pick_for

ROOT = Path(__file__).resolve().parents[1]


def originated_row(method="bookmaker", probabilities=(0.55, 0.45), pick=0, quotes=None, label="No-vig bookmaker estimate"):
    return {
        "id": "1",
        "teams": [{"name": "Alpha"}, {"name": "Beta"}],
        "pick_index": pick,
        "origination": {
            "method": method,
            "label": label,
            "probabilities": list(probabilities),
            "source": "Thunderpick",
            "source_url": "https://thunderpick.io/api/matches",
            "observed_at": "2026-10-22T08:00:00Z",
            "quotes": quotes if quotes is not None else [{"provider": "Thunderpick"}],
        },
        "limitations": ["Hotspawn best-of format is unverified; left blank."],
        "research": [{"stage": "HLTV research", "status": "checked", "source_url": "https://www.hltv.org/matches", "detail": "identity only"}],
    }


def inventory_match(identifier="1", availability="open", analysis=None, pick=None):
    return {
        "id": identifier,
        "teams": [{"name": "Alpha"}, {"name": "Beta"}],
        "competition": "Test Cup",
        "starts_at": "2026-10-22T10:00:00Z",
        "locks_at": "2026-10-22T09:54:00Z",
        "availability": availability,
        "source_url": "https://www.hotspawn.com/matches/alpha-vs-beta-test-cup-1",
        "analysis": analysis,
        "pick_index": pick,
        "limitations": [],
    }


class ClassificationTests(unittest.TestCase):
    def test_a_bookmaker_row_with_a_pick_is_a_money_line(self):
        self.assertEqual(probe.classify(originated_row()), "money-line")

    def test_a_model_row_with_no_quotes_is_model_only(self):
        row = originated_row(method="model", quotes=[], label="Valve-rating research estimate")
        self.assertEqual(probe.classify(row), "model-only")

    def test_a_row_without_a_pick_is_blank_and_never_defaults_to_fifty_fifty(self):
        row = originated_row()
        row["pick_index"] = None
        self.assertEqual(probe.classify(row), "blank")

    def test_a_row_with_one_probability_is_blank(self):
        row = originated_row(probabilities=(0.6,))
        self.assertEqual(probe.classify(row), "blank")


class FixtureRowTests(unittest.TestCase):
    def test_the_originated_row_is_the_basis_when_it_exists(self):
        row = probe.fixture_row(inventory_match(), originated_row())
        self.assertEqual(row["basis"], "originated")
        self.assertEqual(row["classification"], "money-line")
        self.assertEqual(row["pick_team"], "Alpha")
        self.assertEqual(row["probabilities"], [0.55, 0.45])
        self.assertEqual(row["money_providers"], ["Thunderpick"])
        self.assertEqual(row["research_trail"][0]["stage"], "HLTV research")

    def test_the_inventory_analysis_is_the_basis_when_no_origination_row_exists(self):
        analysis = originated_row()["origination"]
        row = probe.fixture_row(inventory_match(analysis=analysis, pick=0), None)
        self.assertEqual(row["basis"], "featured-inventory")
        self.assertEqual(row["classification"], "money-line")

    def test_a_past_start_fixture_is_not_counted_as_active(self):
        row = probe.fixture_row(inventory_match(availability="past"), None)
        self.assertFalse(row["active"])
        self.assertEqual(row["classification"], "blank")

    def test_counts_separate_money_lines_from_model_only_picks_and_blanks(self):
        rows = [
            probe.fixture_row(inventory_match("1"), originated_row()),
            probe.fixture_row(inventory_match("2"), originated_row(method="model", quotes=[], label="Valve-rating research estimate")),
            probe.fixture_row(inventory_match("3", availability="past"), None),
            probe.fixture_row(inventory_match("4"), {"id": "4", "pick_index": None, "origination": None}),
        ]
        counts = probe.coverage_counts(rows)
        self.assertEqual(counts["inventory"], 4)
        self.assertEqual(counts["active"], 3)
        self.assertEqual(counts["archived_past_start"], 1)
        self.assertEqual(counts["active_with_pick"], 2)
        self.assertEqual(counts["active_money_line"], 1)
        self.assertEqual(counts["active_model_only"], 1)
        self.assertEqual(counts["active_blank"], 1)
        self.assertEqual(counts["active_without_betting_line"], 2)


class FakeResponse:
    def __init__(self, status=200, text="", url="https://example.test/"):
        self.status_code = status
        self.ok = 200 <= status < 400
        self.text = text
        self.content = text.encode()
        self.url = url


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses[url]

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses[url]


class SurfaceProbeTests(unittest.TestCase):
    def test_a_challenge_word_inside_a_large_successful_page_is_not_a_challenge(self):
        body = "<html><title>Bovada</title>" + ("x" * 40000) + "captcha" + "</html>"
        record = probe.fetch(FakeSession({"https://x.test/": FakeResponse(200, body)}), "https://x.test/")
        self.assertEqual(record["challenge_markers"], ["captcha"])
        self.assertFalse(record["challenge"])
        self.assertEqual(record["bytes"], len(body.encode()))

    def test_a_small_blocked_page_is_recorded_as_a_challenge(self):
        record = probe.fetch(FakeSession({"https://x.test/": FakeResponse(403, "<html>Just a moment...</html>")}), "https://x.test/")
        self.assertTrue(record["challenge"])
        self.assertEqual(record["status"], 403)

    def test_an_unreachable_host_is_evidence_not_a_crash(self):
        class Boom:
            def get(self, *args, **kwargs):
                raise OSError("egress blocked")

        record = probe.fetch(Boom(), "https://www.hltv.org/matches")
        self.assertFalse(record["ok"])
        self.assertIsNone(record.get("status"))
        self.assertIn("egress blocked", record["error"])

    def test_a_post_surface_sends_its_documented_body(self):
        session = FakeSession({"https://thunderpick.io/api/matches": FakeResponse(200, "{}")})
        probe.fetch(session, "https://thunderpick.io/api/matches", method="POST", payload={"gameIds": [6]})
        self.assertEqual(session.calls[0][0], "POST")
        self.assertEqual(session.calls[0][2]["json"], {"gameIds": [6]})


class ModelRowClassificationTests(unittest.TestCase):
    """A research-model row carries quote records too; they are not a betting line."""

    def test_an_hltv_ranking_row_with_quotes_is_still_model_only(self):
        row = {
            "pick_index": 0,
            "origination": {
                "method": "model",
                "probabilities": [0.5, 0.5],
                "quotes": [{"provider": "HLTV world ranking", "family": "model"}],
            },
        }
        self.assertEqual(probe.classify(row), "model-only")

    def test_the_row_records_its_own_tie_break_and_no_money_provider(self):
        tie = {"rule": "published-rank tie-break", "ranks": [215, 229], "winner": 0, "source": "HLTV world ranking"}
        originated = originated_row(method="model", probabilities=(0.5, 0.5), quotes=[{"provider": "HLTV world ranking", "family": "model", "tie_break": tie}])
        row = probe.fixture_row(inventory_match(), originated)
        self.assertEqual(row["classification"], "model-only")
        self.assertEqual(row["money_providers"], [])
        self.assertEqual(row["quote_providers"], ["HLTV world ranking"])
        self.assertEqual(row["tie_break"], tie)


class EvenTieBreakValidationTests(unittest.TestCase):
    """`scripts.build_origination.expected_pick_for` must replay the published tie-break.

    Without it the live 2026-10-22T09:15:53Z snapshot could not be built at all:
    fixture 1082926 is exactly 0.500/0.500 with the direction taken from HLTV's
    published positions, and the validator stopped the build with
    'Fallback pick differs from its probabilities'.
    """

    def even_row(self, ranks=(215, 229), winner=0, method="model", rule="published-rank tie-break", ties=1):
        quote = {"provider": "HLTV world ranking", "family": "model", "probabilities": [0.5, 0.5]}
        if ties:
            for _ in range(ties):
                quote = dict(quote)
                quote["tie_break"] = {"rule": rule, "ranks": list(ranks), "winner": winner, "source": "HLTV world ranking"}
        return {"method": method, "probabilities": [0.5, 0.5], "quotes": [quote]}

    def test_a_published_rank_tie_break_gives_the_even_row_its_documented_side(self):
        self.assertEqual(expected_pick_for(self.even_row()), 0)
        self.assertEqual(expected_pick_for(self.even_row(ranks=(229, 215), winner=1)), 1)

    def test_an_even_row_without_a_record_still_has_no_side(self):
        self.assertIsNone(expected_pick_for(self.even_row(ties=0)))

    def test_a_real_favourite_is_never_overridden_by_a_tie_break(self):
        row = self.even_row()
        row["probabilities"] = [0.62, 0.38]
        self.assertEqual(expected_pick_for(row), 0)

    def test_a_money_line_may_not_use_the_tie_break(self):
        with self.assertRaises(AssertionError):
            expected_pick_for(self.even_row(method="bookmaker"))

    def test_a_direction_that_contradicts_the_cited_order_is_refused(self):
        with self.assertRaises(AssertionError):
            expected_pick_for(self.even_row(ranks=(215, 229), winner=1))

    def test_equal_or_missing_published_positions_decide_nothing(self):
        for ranks in ((215, 215), (0, 229), ("215", 229), (215,)):
            with self.subTest(ranks=ranks), self.assertRaises(AssertionError):
                expected_pick_for(self.even_row(ranks=ranks, winner=0))

    def test_an_unknown_rule_is_refused(self):
        with self.assertRaises(AssertionError):
            expected_pick_for(self.even_row(rule="coin flip"))

    def test_more_than_one_tie_break_record_is_refused(self):
        row = self.even_row()
        row["quotes"].append(dict(row["quotes"][0]))
        with self.assertRaises(AssertionError):
            expected_pick_for(row)


class NameMatchingTests(unittest.TestCase):
    def test_a_short_tag_is_never_substring_matched(self):
        self.assertIsNone(probe.name_pattern("WW"))
        self.assertIsNone(probe.name_pattern(""))

    def test_an_exact_name_matches_only_on_a_word_boundary(self):
        pattern = probe.name_pattern("HOTU")
        self.assertTrue(pattern.search("HOTU vs The Huns"))
        self.assertFalse(pattern.search("PHOTU graphic"))

    def test_matching_ignores_case_and_repeated_space(self):
        pattern = probe.name_pattern("benched  gods")
        self.assertTrue(pattern.search("Benched Gods take the series"))


class FixtureResearchTests(unittest.TestCase):
    def test_research_covers_only_active_fixtures_without_a_betting_line(self):
        rows = [
            probe.fixture_row(inventory_match("1"), originated_row()),
            probe.fixture_row(inventory_match("2"), originated_row(method="model", quotes=[])),
            probe.fixture_row(inventory_match("3", availability="past"), originated_row(method="model", quotes=[])),
        ]
        research = probe.fixture_research(rows, {"HLTV match listing": "HOTU vs The Huns"})
        self.assertEqual([item["hotspawn_id"] for item in research], ["2"])

    def test_a_name_hit_is_identity_evidence_and_never_a_price(self):
        rows = [probe.fixture_row(inventory_match("2"), originated_row(method="model", quotes=[]))]
        research = probe.fixture_research(rows, {"HLTV match listing": "Alpha vs Beta listed", "bo3.gg matches": ""})
        item = research[0]
        self.assertEqual(item["names_matched_on"], [{"surface": "HLTV match listing", "names_matched": ["Alpha", "Beta"]}])
        self.assertFalse(item["two_sided_price_verified"])
        self.assertIn("No two-sided prematch series price", item["limitation"])

    def test_a_blank_fixture_says_it_stays_blank(self):
        rows = [probe.fixture_row(inventory_match("9"), {"id": "9", "pick_index": None, "origination": None})]
        research = probe.fixture_research(rows, {})
        self.assertEqual(research[0]["classification"], "blank")
        self.assertIn("stays blank and flagged", research[0]["limitation"])


class ReportTests(unittest.TestCase):
    def test_the_markdown_report_publishes_both_probabilities_and_the_snapshot_time(self):
        latest = {"generated_at": "2026-10-22T08:00:00Z", "matches": [inventory_match("1")]}
        origination = {"generated_at": "2026-10-22T08:05:00Z", "live_collection": True, "matches": [originated_row()]}
        report = probe.build_report(latest, origination, surfaces=[], research=[])
        text = probe.render_markdown(report)
        self.assertIn("55.0% / 45.0%", text)
        self.assertIn("2026-10-22T08:00:00Z", text)
        self.assertIn("Every active fixture in this snapshot carried an external betting line", text)

    def test_a_missing_snapshot_is_reported_not_guessed(self):
        report = probe.build_report({"__missing__": "data/latest.json"}, {})
        self.assertEqual(report["counts"]["inventory"], 0)
        self.assertEqual(report["snapshot"]["latest_missing"], "data/latest.json")


class CssReaderTests(unittest.TestCase):
    CSS = """
    .mobile-nav>a{min-height:43px}
    @media(max-width:700px){.mobile-nav>a{min-height:48px}.table-scroll{overflow-x:auto}}
    table{min-width:860px}
    .shell{width:1200px}
    """

    def setUp(self):
        self.rules = mobile.parse_css(self.CSS)

    def test_media_context_is_attached_to_the_rules_inside_it(self):
        phone = [rule for rule in self.rules if rule["media"]]
        self.assertEqual(len(phone), 2)
        self.assertTrue(all("max-width:700px" in rule["media"][-1] for rule in phone))

    def test_the_largest_declared_tap_target_is_found(self):
        height, sources = mobile.min_height_px(self.rules, ".mobile-nav>a")
        self.assertEqual(height, 48.0)
        self.assertTrue(any("max-width:700px" in source for source in sources))

    def test_scroll_wrappers_are_read_from_the_stylesheet(self):
        self.assertIn("table-scroll", mobile.overflow_auto_selectors(self.rules))

    def test_tables_are_excluded_from_the_failing_width_set_but_reported_on_request(self):
        self.assertEqual([item["selector"] for item in mobile.wide_fixed_widths(self.rules)], [".shell"])
        selectors = {item["selector"] for item in mobile.wide_fixed_widths(self.rules, include_tables=True)}
        self.assertEqual(selectors, {".shell", "table"})


def write_site(root: Path, *, banner: bool = True, glance_ids=("1", "2"), tables_wrapped=True) -> None:
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "origination").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "scout.css").write_text(
        ".table-scroll{overflow-x:auto;max-width:100%}\n"
        ".mobile-nav>a{min-height:43px}\n"
        ".exec-banner-actions a{min-height:48px}\n"
        "@media(max-width:700px){.mobile-nav>a{min-height:48px}.glance-prob,.glance-other{font-size:12px}}\n"
    )
    rows = "".join(
        f'<li class="glance-row" data-glance-id="{identifier}"><div class="glance-match"><strong>Alpha <span class="versus">vs</span> Beta</strong></div>'
        f'<div class="glance-choice"><span class="glance-pick-label" data-glance-pick>Pick</span><strong>Alpha</strong>'
        f'<span class="glance-prob">55.0%</span><span class="glance-other">Beta 45.0%</span></div></li>'
        for identifier in glance_ids
    )
    banner_html = (
        '<section class="exec-banner" aria-label="Where to find the updated picks">'
        '<a class="primary" href="./origination/#picks">Updated picks</a>'
        '<a class="secondary" href="./picks/">Featured picks feed</a>'
        '<a class="tertiary" href="./unresolved/">Unresolved &amp; limitations</a>'
        "</section>"
        if banner
        else ""
    )
    wrapper_open, wrapper_close = ('<div class="table-scroll">', "</div>") if tables_wrapped else ("", "")
    (root / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Scout</title></head><body>'
        '<h1>Executive summary</h1>' + banner_html +
        '<section id="picks-at-a-glance"><ol class="glance-list">' + rows + "</ol></section>"
        '<section id="unresolved-register"><h2>Unresolved picks &amp; limitations</h2></section>'
        + wrapper_open + '<table class="simple-table"><tbody><tr><td>x</td></tr></tbody></table>' + wrapper_close +
        '<nav class="mobile-nav" aria-label="Mobile navigation">'
        '<a href="./index.html"><span>Summary</span></a><a href="./origination/#picks"><span>Picks</span></a>'
        '<a href="./unresolved/"><span>Unresolved</span></a><a href="./edge/"><span>Edge</span></a>'
        '<a href="./coverage/"><span>Sources</span></a><a href="./review/"><span>Review</span></a></nav>'
        "</body></html>"
    )
    (root / "origination" / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Picks</title></head>'
        "<body><h1>Complete picks</h1></body></html>"
    )


def write_data(root: Path, identifiers=("1", "2")) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "latest.json").write_text(json.dumps({
        "generated_at": "2026-10-22T08:00:00Z",
        "matches": [inventory_match(identifier) for identifier in identifiers],
    }))


class PhoneAuditTests(unittest.TestCase):
    def audit(self, **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        site = root / "site"
        site.mkdir()
        write_site(site, **kwargs)
        write_data(root / "data")
        return mobile.build_report(site, root / "data")

    def test_a_phone_first_build_passes_every_current_check(self):
        report = self.audit()
        failed = [item["id"] for item in report["checks"] if not item["passed"] and item["scope"] == "current"]
        self.assertEqual(failed, [], msg=json.dumps(report["checks"], indent=1))
        self.assertEqual(report["counts"]["failed"], 0)

    def test_a_build_without_the_executive_banner_is_failed_not_excused(self):
        report = self.audit(banner=False)
        failed = {item["id"] for item in report["checks"] if not item["passed"]}
        self.assertIn("exec-banner", failed)
        self.assertIn("exec-link-complete", failed)

    def test_a_glance_index_that_omits_an_active_fixture_is_failed(self):
        report = self.audit(glance_ids=("1",))
        failed = {item["id"]: item["detail"] for item in report["checks"] if not item["passed"]}
        self.assertIn("glance-coverage", failed)
        self.assertIn("2", failed["glance-coverage"])

    def test_an_unwrapped_table_is_reported_with_its_page(self):
        report = self.audit(tables_wrapped=False)
        failed = {item["id"]: item["detail"] for item in report["checks"] if not item["passed"]}
        self.assertIn("table-scroll-wrappers", failed)
        self.assertIn("index.html", failed["table-scroll-wrappers"])

    def test_the_published_branch_root_is_audited_and_its_gaps_are_named(self):
        """The legacy Pages publisher serves the checked-in root, so audit it too.

        This does not assert that the root is stale — it asserts that the audit
        names whichever contract the root does not meet, which is what makes the
        finding reviewable instead of assumed.
        """
        report = mobile.build_report(ROOT, ROOT / "data")
        self.assertTrue(report["checks"])
        for item in report["checks"]:
            self.assertTrue(item["detail"], msg=f"{item['id']} reported no detail")


class RootRiskTests(unittest.TestCase):
    def test_publishing_the_snapshot_that_is_already_checked_in_still_replays(self):
        fresh = {"data/latest.json": ROOT / "data" / "latest.json", "data/origination.json": ROOT / "data" / "origination.json"}
        with tempfile.TemporaryDirectory() as temporary:
            result = risk.simulate_publish(ROOT / "data", fresh, Path(temporary))
        self.assertEqual(result["check_data"], "passed")

    def test_a_fresh_snapshot_over_frozen_evidence_breaks_the_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            source = work / "fresh"
            source.mkdir()
            payload = json.loads((ROOT / "data" / "latest.json").read_text())
            payload["inventory_observed_at"] = "2026-10-22T08:00:00Z"
            payload["generated_at"] = "2026-10-22T08:00:10Z"
            (source / "latest.json").write_text(json.dumps(payload))
            result = risk.simulate_publish(ROOT / "data", {"data/latest.json": source / "latest.json"}, work)
        self.assertEqual(result["check_data"], "failed")
        self.assertEqual(result["error"], "Inventory observation timestamp restamped")

    def test_the_report_counts_the_modules_that_read_the_snapshot_as_a_fixture(self):
        report = risk.count_snapshot_reading_tests(ROOT)
        self.assertGreater(report["count"], 10)
        self.assertTrue(all(module.startswith("tests/") for module in report["modules"]))

    def test_the_offline_reproduction_runs_and_writes_both_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            code = risk.main(["--repo", str(ROOT), "--out", str(out)])
            self.assertEqual(code, 0)
            report = json.loads((out / "root-publish-risk.json").read_text())
            self.assertIn(report["simulation"]["check_data"], {"passed", "failed"})
            self.assertTrue(report["conclusion"])
            self.assertIn("check_data", (out / "root-publish-risk.md").read_text())


class GateTests(unittest.TestCase):
    OUTPUT = """
    FAIL: test_current_watch (tests.test_contrarian.ContrarianReviewTests.test_current_watch)
    ERROR: setUpClass (tests.test_review_flags.ReviewFlagsIntegration)
    Ran 239 tests in 20.153s
    FAILED (failures=1, errors=1)
    """

    def test_failures_errors_and_the_summary_are_parsed(self):
        parsed = gate.parse_unittest_output(self.OUTPUT)
        self.assertEqual(parsed["ran"], 239)
        self.assertFalse(parsed["ok"])
        self.assertEqual(parsed["summary"], "failures=1, errors=1")
        self.assertEqual(
            parsed["failed"],
            [
                {"kind": "FAIL", "test": "test_current_watch", "suite": "tests.test_contrarian.ContrarianReviewTests.test_current_watch"},
                {"kind": "ERROR", "test": "setUpClass", "suite": "tests.test_review_flags.ReviewFlagsIntegration"},
            ],
        )

    def test_a_clean_run_is_reported_as_ok(self):
        parsed = gate.parse_unittest_output("Ran 12 tests in 0.4s\n\nOK\n")
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["failed"], [])

    def test_the_gate_records_which_snapshot_it_ran_against(self):
        report = gate.run_gate(
            command=["python3", "-m", "unittest", "-v", "tests.test_validation"],
            data_dir=ROOT / "data",
            label="stub",
            timeout=120,
            cwd=ROOT,
        )
        self.assertEqual(report["snapshot"]["latest.json"]["generated_at"], "2026-10-15T08:36:13Z")
        self.assertIsNotNone(report["returncode"])
        self.assertGreater(report["snapshot"]["evidence_files"], 0)


def workflow_text(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text()


def step_block(text: str, name_fragment: str) -> str:
    """The YAML block of one named step, up to the next ``- name:`` at the same indent."""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if name_fragment in line)
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip().startswith("- name:") and (len(line) - len(line.lstrip())) == indent:
            end = index
            break
        if line.strip().startswith("- uses:") and (len(line) - len(line.lstrip())) == indent:
            end = index
            break
    return "\n".join(lines[start:end])


class GuardWorkflowTests(unittest.TestCase):
    """The publisher guard must not share the starved concurrency group, and must not commit."""

    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / ".github" / "workflows" / "pages-artifact-guard.yml"
        cls.text = cls.path.read_text()

    def test_the_workflow_file_exists_on_this_branch(self):
        self.assertTrue(self.path.is_file())

    def test_it_runs_on_pushes_to_main_on_a_schedule_and_on_demand(self):
        self.assertIn("branches: [main]", self.text)
        self.assertIn("- cron: '23 */2 * * *'", self.text)
        self.assertIn("workflow_dispatch:", self.text)

    def test_it_never_shares_the_concurrency_group_that_starved_the_refresh(self):
        self.assertIn("group: verified-artifact-guard", self.text)
        self.assertNotIn("group: pages\n", self.text)
        self.assertIn("cancel-in-progress: false", self.text)

    def test_it_cannot_commit_to_the_repository(self):
        self.assertIn("contents: read", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("git commit", self.text)
        self.assertNotIn("scripts.root_publish", self.text)

    def test_it_verifies_the_public_site_against_the_artifacts_own_snapshot(self):
        self.assertIn("scripts.verify_live --url", self.text)
        self.assertIn("--data site/data/latest.json", self.text)

    def test_it_only_deploys_when_the_public_check_failed(self):
        block = step_block(self.text, "Re-deploy it")
        self.assertIn("steps.check.outcome == 'failure'", block)
        self.assertIn("actions/deploy-pages@v5", block)
        self.assertIn("continue-on-error: true", block)

    def test_it_nudges_the_refresh_only_past_the_eight_hour_bound(self):
        block = step_block(self.text, "Nudge the four-hour refresh")
        self.assertIn("steps.pick.outputs.age_minutes > 480", block)
        self.assertIn("continue-on-error: true", block)
        self.assertIn("gh workflow run pages.yml --ref main", block)

    def test_it_uses_an_isolated_artifact_name_so_it_cannot_collide_with_the_refresh(self):
        self.assertIn("name: github-pages-guard", self.text)
        self.assertIn("artifact_name: github-pages-guard", self.text)


@unittest.skipUnless(
    (ROOT / ".github" / "workflows" / "bc1afd8f-live.yml").is_file(),
    "session-only workflow is removed before the merge",
)
class SessionWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / ".github" / "workflows" / "bc1afd8f-live.yml"
        cls.text = cls.path.read_text()

    def test_it_is_scoped_to_this_session_branch_and_never_deploys(self):
        self.assertIn("branches: ['arena/bc1afd8f-maltaproj3']", self.text)
        self.assertNotIn("actions/deploy-pages", self.text)
        self.assertNotIn("schedule:", self.text)

    def test_it_commits_only_this_sessions_reports(self):
        self.assertIn("git add data/research/bc1afd8f/", self.text)
        self.assertIn("git checkout -- data/", self.text)

    def test_it_runs_the_repository_collectors_before_reporting(self):
        self.assertIn("python -m scripts.collect", self.text)
        self.assertIn("python -m scripts.originate --live", self.text)
        self.assertLess(self.text.index("python -m scripts.collect"), self.text.index("python -m scripts.bc1afd8f_probe"))

    def test_the_push_trigger_is_path_guarded_so_a_report_commit_cannot_retrigger_it(self):
        self.assertIn("paths:", self.text)
        self.assertIn("- 'scripts/bc1afd8f_probe.py'", self.text)
        self.assertNotIn("- 'data/", self.text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
