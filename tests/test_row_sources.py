"""Row-level official-source audit: unit tests on synthetic HTML only.

These deliberately do not read data/latest.json: production restores a live
snapshot over data/ before the regression tests run, and data-dependent tests
are what made that run brittle.  The real site is audited by
`python -m scripts.audit_rows --site site --strict` after a build.
"""
import unittest

from scripts import audit_rows as audit

OFFICIAL_ROW = '<tr><th scope="row">A vs B</th><td>55%</td><td><a href="https://www.hltv.org/matches/1/a-vs-b">HLTV</a></td></tr>'


def page(rows, caption='Picks'):
    return f'<table><caption>{caption}</caption><thead><tr><th>Match</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table>'


class OfficialHosts(unittest.TestCase):
    def test_primary_publishers_are_accepted(self):
        for url in [
            'https://www.hltv.org/results?event=8932',
            'https://hltv.org/news/45718/9z-beat-aurora-2-0-to-kick-off-twc-2026',
            'https://play.hotspawn.com/lobby',
            'https://www.hotspawn.com/matches/x-vs-y-1',
            'https://polymarket.com/event/cs2-aur1-9z-2026-10-16',
            'https://gamma-api.polymarket.com/markets?slug=cs2-aur1-9z-2026-10-16',
            'https://clob.polymarket.com/book?token_id=1',
            'https://thunderpick.io/esports/counter-strike',
            'https://github.com/ValveSoftware/counter-strike_regional_standings/blob/main/live/2026/standings_global_2026_10_05.md',
            'https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=cs2',
            'https://docs.github.com/en/actions',
        ]:
            self.assertTrue(audit.is_official(url), url)

    def test_look_alikes_and_unrelated_hosts_are_rejected(self):
        for url in [
            'https://hltv.org.evil.example/results',
            'https://evil.example/www.hltv.org/',
            'https://github.com/someone-else/counter-strike_regional_standings',
            'https://phpstack-1372681-6459848.cloudwaysapps.com/teams/58.svg',
            'https://twitter.com/hltvorg',
            'ftp://hltv.org/x',
            'javascript:alert(1)',
            './origination/#picks',
            '',
        ]:
            self.assertFalse(audit.is_official(url), url)


class RowVerdicts(unittest.TestCase):
    def test_row_with_official_link_is_ok(self):
        result = audit.audit_html(page(OFFICIAL_ROW), 'x/index.html')
        self.assertEqual((result['rows'], result['ok'], result['violation']), (1, 1, 0))

    def test_row_without_any_source_is_a_violation_and_lists_its_text(self):
        bad = '<tr><th scope="row">C vs D</th><td>61%</td><td><a href="https://random-blog.example/tips">tips</a></td></tr>'
        result = audit.audit_html(page(OFFICIAL_ROW + bad), 'x/index.html')
        self.assertEqual((result['rows'], result['ok'], result['violation']), (2, 1, 1))
        self.assertIn('C vs D', result['violations'][0]['text'])
        self.assertEqual(result['violations'][0]['links'], ['https://random-blog.example/tips'])

    def test_blank_values_may_be_flagged_instead_of_sourced(self):
        flagged = '<tr><th scope="row">E vs F</th><td>— <small>unverified</small></td></tr>'
        result = audit.audit_html(page(flagged), 'x/index.html')
        self.assertEqual((result['flagged'], result['violation']), (1, 0))

    def test_a_number_without_a_flag_or_a_source_is_not_rescued_by_internal_links(self):
        internal = '<tr><th scope="row"><a href="./picks/">G vs H</a></th><td>70%</td></tr>'
        result = audit.audit_html(page(internal), 'x/index.html')
        self.assertEqual(result['violation'], 1)
        self.assertTrue(result['violations'][0]['internal_only'])

    def test_site_map_exemption_is_keyed_to_the_table_caption(self):
        nav = '<tr><th scope="row"><a href="./picks/">Picks →</a></th><td>All matches</td></tr>'
        site_map = audit.audit_html(page(nav, caption='Every page on this site and what it contains'), 'x/index.html')
        self.assertEqual((site_map['navigation'], site_map['violation']), (1, 0))
        data_table = audit.audit_html(page(nav, caption='Picks'), 'x/index.html')
        self.assertEqual((data_table['navigation'], data_table['violation']), (0, 1))

    def test_site_map_row_with_an_external_unlisted_link_is_still_a_violation(self):
        nav = '<tr><th scope="row"><a href="https://random-blog.example/">Tips</a></th><td>All matches</td></tr>'
        result = audit.audit_html(page(nav, caption='Every page on this site and what it contains'), 'x/index.html')
        self.assertEqual(result['violation'], 1)

    def test_pick_cards_are_rows_too(self):
        good = '<article class="pick-card" id="match-1"><h3>A vs B</h3><a href="https://polymarket.com/event/x">Polymarket</a></article>'
        bad = '<article class="pick-card" id="match-2"><h3>C vs D</h3><p>63.5%</p></article>'
        result = audit.audit_html(good + bad, 'origination/index.html')
        self.assertEqual((result['rows'], result['ok'], result['violation']), (2, 1, 1))
        self.assertEqual(result['violations'][0]['row_id'], 'match-2')

    def test_header_and_footer_rows_and_scripts_are_ignored(self):
        html = ('<table><caption>T</caption><thead><tr><th>Only a header</th></tr></thead><tbody>' + OFFICIAL_ROW +
                '</tbody><tfoot><tr><td>Total 1</td></tr></tfoot></table><script>var x = "<tr><td>nope</td></tr>";</script>')
        result = audit.audit_html(html, 'x/index.html')
        self.assertEqual(result['rows'], 1)

    def test_nested_markup_inside_a_row_keeps_links_with_the_outer_row(self):
        nested = '<tr><th scope="row">A<small>vs</small>B</th><td><div><span><a href="https://thunderpick.io/esports/counter-strike">book</a></span></div></td></tr>'
        result = audit.audit_html(page(nested), 'x/index.html')
        self.assertEqual((result['ok'], result['violation']), (1, 0))


if __name__ == '__main__':
    unittest.main()


class UnresolvedCards(unittest.TestCase):
    def test_unresolved_cards_are_rows_too_so_renaming_the_class_cannot_hide_them(self):
        good = '<article class="unresolved-card" id="unresolved-1"><h3>A vs B</h3><p>— unverified</p><a href="https://www.hotspawn.com/matches/x-1">Hotspawn</a></article>'
        bad = '<article class="unresolved-card" id="unresolved-2"><h3>C vs D</h3><p>Looks fine</p></article>'
        result = audit.audit_html(good + bad, 'origination/index.html')
        self.assertEqual((result['rows'], result['ok'], result['violation']), (2, 1, 1))
        self.assertEqual(result['violations'][0]['row_id'], 'unresolved-2')


class SiteWalk(unittest.TestCase):
    def test_archives_and_underscore_test_directories_are_not_audited(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            bad = '<table><caption>T</caption><tbody><tr><td>no source here</td></tr></tbody></table>'
            for rel in ('index.html', 'docs/index.html', 'archive/root-session/index.html', '_fixture/strategy/index.html', 'picks.html'):
                target = site / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(bad)
            report = audit.audit_site(site)
            self.assertEqual([p['page'] for p in report['pages']], ['index.html'])
            self.assertEqual(report['totals']['violation'], 1)
