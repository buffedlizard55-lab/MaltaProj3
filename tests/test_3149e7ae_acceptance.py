"""The brief-line acceptance audit must fail when a brief line stops being met.

Session arena-3149e7ae. Every test builds a small synthetic *rendered* tree, so
the audit is exercised exactly the way it runs against the real build: it reads
HTML, not the data model. Nothing here touches ``data/`` or a live source.
"""
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.acceptance_audit import audit, markdown, main

VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'

CSS = """
.glance-row { display: flex; }
.glance-match, .glance-choice { min-width: 0; }
@media (max-width: 700px) { .glance-row { display: block; } }
"""

PAGES_WORKFLOW = """name: Refresh
on:
  schedule:
    - cron: '17 */4 * * *'
"""


def glance_row(first='Alpha', second='Beta', pick='Alpha', probs=('61.5', '38.5'),
               source='https://www.hltv.org/matches/1', has_pick=True) -> str:
    choice = (f'<span class="glance-pick-label" data-glance-pick>Pick</span><strong>{pick}</strong>'
              f'<span class="glance-prob">{probs[0]}%</span><span class="glance-other">'
              f'{second} {probs[1]}%</span>' if has_pick else
              '<span class="glance-pick-label unresolved-text">Unresolved</span>')
    return (f'<li class="glance-row" data-search="alpha beta cs2"><div class="glance-match">'
            f'<strong>{first} vs {second}</strong></div><div class="glance-choice">{choice}</div>'
            f'<div class="glance-links">'
            f'<a class="source-link" href="https://www.hotspawn.com/matches/1">Hotspawn</a>'
            + (f'<a class="source-link" href="{source}">Source</a>' if source else '')
            + '</div></li>')


def summary_page(rows=None, active=1, register=True, limits=5, exec_link='./origination/#picks',
                 coverage_link='./picks/', unresolved_link='./unresolved/') -> str:
    rows = rows if rows is not None else glance_row()
    parts = ['<!doctype html><html><head>' + VIEWPORT + '<title>Summary</title></head><body>']
    parts.append('<section id="picks-at-a-glance"><h2>Picks at a glance</h2>'
                 f'<p class="section-intro"><strong>{active}</strong> active Hotspawn CS2 fixtures in this snapshot, '
                 '<strong>1</strong> with a directional pick.</p><ol class="glance-list">' + rows + '</ol></section>')
    if register:
        limit_items = ''.join(
            ['<li>Hotspawn participation percentages and HLTV fan votes are never inputs.</li>',
             '<li>A blank stays blank: a missing value is never filled with a default 50/50.</li>',
             '<li>Display names are joined only through the reviewed alias registry.</li>',
             '<li>Thin books are rejected as picks.</li>', '<li>Every refresh retries all sources.</li>'][:limits])
        parts.append('<section class="content-section" id="unresolved-register">'
                     '<h2 id="unresolved-register-title">Unresolved picks &amp; limitations</h2>'
                     f'<div class="limitations-callout unresolved-limits"><ul>{limit_items}</ul></div></section>')
    parts.append(f'<a href="{exec_link}">All match picks</a><a href="{coverage_link}">Picks page</a>'
                 f'<a href="{unresolved_link}">Unresolved</a>')
    parts.append('</body></html>')
    return ''.join(parts)


def simple_page(title='Page') -> str:
    return f'<!doctype html><html><head>{VIEWPORT}<title>{title}</title></head><body><h1>{title}</h1></body></html>'


SIMILAR_LIMITS = ('<ul class="unresolved-limits"><li>a</li><li>b</li><li>c</li><li>d</li><li>e</li></ul>')


class AcceptanceAuditTests(unittest.TestCase):
    def setUp(self):
        self.ctx = tempfile.TemporaryDirectory()
        self.root = Path(self.ctx.name)
        self.site = self.root / 'site'
        (self.site / 'assets').mkdir(parents=True)
        (self.site / 'assets/scout.css').write_text(CSS)
        (self.site / 'data').mkdir()
        (self.root / '.github/workflows').mkdir(parents=True)
        (self.root / '.github/workflows/pages.yml').write_text(PAGES_WORKFLOW)
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        (self.site / 'data/latest.json').write_text(json.dumps({
            'generated_at': now, 'coverage_complete': True,
            'refresh_interval_hours': 4, 'stale_after_hours': 8}))
        (self.site / 'data/row-source-audit.json').write_text(json.dumps(
            {'totals': {'rows': 10, 'ok': 9, 'flagged': 1, 'navigation': 0, 'violation': 0}}))
        (self.site / 'picks').mkdir()
        (self.site / 'picks/index.html').write_text(simple_page('Match picks'))
        (self.site / 'unresolved').mkdir()
        (self.site / 'unresolved/index.html').write_text(
            simple_page('Unresolved picks &amp; limitations')
            .replace('</body>', SIMILAR_LIMITS + '</body>'))
        (self.site / 'origination').mkdir()
        (self.site / 'origination/index.html').write_text(simple_page('All matches'))
        self.write_summary()

    def tearDown(self):
        self.ctx.cleanup()

    def write_summary(self, **kwargs):
        (self.site / 'index.html').write_text(summary_page(**kwargs))

    def check(self, report, key):
        found = [c for c in report['checks'] if c['key'] == key]
        self.assertTrue(found, f'{key} was not reported')
        return found[0]

    # ------------------------------------------------------------------ #
    def test_a_complete_tree_passes_every_check(self):
        report = audit(self.root, self.site)
        failures = [c for c in report['checks'] if c['status'] == 'fail']
        self.assertEqual(failures, [], failures)
        self.assertEqual(report['totals']['fail'], 0)
        self.assertGreaterEqual(report['totals']['pass'], 7)

    def test_a_row_without_a_pick_and_without_a_label_fails(self):
        self.write_summary(rows=glance_row(has_pick=False) + '<span class="glance-pick-label">Pick</span>',
                           active=1)
        # A pick label outside .glance-choice must not count for the row.
        self.write_summary(rows=glance_row(has_pick=False).replace('Unresolved', '&nbsp;'))
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'glance_rows')['status'], 'fail')

    def test_a_row_showing_only_one_percentage_fails(self):
        self.write_summary(rows=glance_row(probs=('61.5', '')))
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'glance_rows')['status'], 'fail')
        self.assertIn('both teams', self.check(report, 'glance_rows')['detail'])

    def test_percentages_that_do_not_sum_to_one_hundred_fail(self):
        self.write_summary(rows=glance_row(probs=('61.5', '20.0')))
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'glance_rows')['status'], 'fail')
        self.assertIn('sum to 100', self.check(report, 'glance_rows')['detail'])

    def test_a_row_without_an_official_source_link_fails(self):
        row = glance_row(source=None).replace('https://www.hotspawn.com/matches/1', './origination/#match-1')
        self.write_summary(rows=row)
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'glance_rows')['status'], 'fail')
        self.assertIn('source link', self.check(report, 'glance_rows')['detail'])

    def test_a_coverage_sentence_that_does_not_match_the_rows_fails(self):
        self.write_summary(active=7)
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'glance_counts')['status'], 'fail')

    def test_the_reconciled_snapshot_count_is_cross_checked(self):
        (self.site / 'data/reconciled-counts.json').write_text(json.dumps(
            {'generated_at': '2026-10-23T00:00:00Z',
             'complete_coverage_counts': {'active': 4, 'resolved': 4, 'with_pick': 4, 'unresolved': 0}}))
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'glance_counts')['status'], 'fail')
        self.assertIn('counts 4', self.check(report, 'glance_counts')['detail'])

    def test_a_missing_unresolved_register_fails(self):
        self.write_summary(register=False)
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'unresolved_register')['status'], 'fail')

    def test_a_register_with_too_few_limitations_fails(self):
        self.write_summary(limits=2)
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'unresolved_register')['status'], 'fail')
        self.assertIn('limitation', self.check(report, 'unresolved_register')['detail'])

    def test_limitations_must_exclude_votes_and_never_invent_a_value(self):
        self.write_summary()
        page = (self.site / 'index.html').read_text()
        page = page.replace('Hotspawn participation percentages and HLTV fan votes are never inputs.', 'x')
        page = page.replace('A blank stays blank: a missing value is never filled with a default 50/50.', 'y')
        (self.site / 'index.html').write_text(page)
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'unresolved_register')['status'], 'fail')

    def test_an_in_site_link_to_a_page_that_was_not_built_fails(self):
        # The link keeps the brief's own shape, but the page it names was not
        # produced by this build, so the audit must resolve the target rather
        # than trust the link text.
        (self.site / 'origination/index.html').unlink()
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'exec_links')['status'], 'fail')
        self.assertIn('not built', self.check(report, 'exec_links')['detail'])

    def test_a_link_that_leaves_the_site_fails(self):
        self.write_summary(exec_link='https://example.com/picks')
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'exec_links')['status'], 'fail')

    def test_a_page_without_a_mobile_viewport_fails(self):
        (self.site / 'picks/index.html').write_text('<!doctype html><html><head></head><body>x</body></html>')
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'mobile')['status'], 'fail')
        self.assertIn('viewport', self.check(report, 'mobile')['detail'])

    def test_a_stylesheet_without_a_small_screen_rule_fails(self):
        (self.site / 'assets/scout.css').write_text('.glance-row { display:flex; }')
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'mobile')['status'], 'fail')

    def test_a_schedule_with_a_gap_over_eight_hours_fails(self):
        (self.root / '.github/workflows/pages.yml').write_text(
            "on:\n  schedule:\n    - cron: '0 0 * * *'\n    - cron: '0 12 * * *'\n")
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'cadence')['status'], 'fail')
        self.assertIn('12.0 h', self.check(report, 'cadence')['detail'])

    def test_a_denser_catch_up_slot_is_not_a_failure(self):
        (self.root / '.github/workflows/pages.yml').write_text(
            "on:\n  schedule:\n    - cron: '17 */4 * * *'\n    - cron: '47 2-22/4 * * *'\n")
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'cadence')['status'], 'pass')

    def test_a_declared_interval_outside_the_window_fails(self):
        (self.site / 'data/latest.json').write_text(json.dumps({
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'coverage_complete': True, 'refresh_interval_hours': 12, 'stale_after_hours': 24}))
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'cadence')['status'], 'fail')

    def test_a_row_published_without_a_source_fails(self):
        (self.site / 'data/row-source-audit.json').write_text(json.dumps(
            {'totals': {'rows': 10, 'ok': 8, 'flagged': 1, 'navigation': 0, 'violation': 1}}))
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'row_sources')['status'], 'fail')

    def test_a_rendered_only_tree_reports_the_missing_audit_as_information(self):
        (self.site / 'data/row-source-audit.json').unlink()
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'row_sources')['status'], 'info')

    def test_a_stale_snapshot_is_reported_not_failed(self):
        (self.site / 'data/latest.json').write_text(json.dumps({
            'generated_at': '2026-10-01T00:00:00Z', 'coverage_complete': False,
            'refresh_interval_hours': 4, 'stale_after_hours': 8}))
        report = audit(self.root, self.site)
        self.assertEqual(self.check(report, 'freshness')['status'], 'info')

    def test_a_missing_build_is_a_single_loud_failure(self):
        (self.site / 'index.html').unlink()
        report = audit(self.root, self.site)
        self.assertEqual(report['totals']['checks'], 1)
        self.assertEqual(report['checks'][0]['status'], 'fail')

    def test_strict_mode_exits_non_zero_only_on_a_failure(self):
        with tempfile.TemporaryDirectory() as out, contextlib.redirect_stdout(io.StringIO()):
            good = main(['--repo', str(self.root), '--site', str(self.site),
                         '--json', str(Path(out) / 'r.json'), '--strict'])
            self.assertEqual(good, 0)
            self.write_summary(register=False)
            bad = main(['--repo', str(self.root), '--site', str(self.site),
                        '--json', str(Path(out) / 'r.json'), '--strict'])
            self.assertEqual(bad, 1)
            saved = json.loads((Path(out) / 'r.json').read_text())
            self.assertEqual(saved['totals']['fail'], 1)

    def test_the_markdown_report_quotes_each_brief_line(self):
        report = audit(self.root, self.site)
        text = markdown(report)
        self.assertIn('brief line by line'.lower(), text.lower())
        for check in report['checks']:
            self.assertIn(check['title'], text)

    def test_this_repository_schedule_satisfies_the_cadence_rule(self):
        report = audit(Path('.'), self.site)
        self.assertEqual(self.check(report, 'cadence')['status'], 'pass')


if __name__ == '__main__':
    unittest.main()
