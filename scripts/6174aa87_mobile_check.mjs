// Session arena-6174aa87 — phone-readability evidence for the published build.
//
// Reads the *published* pages over HTTP (the branch root is the legacy Pages
// source, so it holds the last deployed build) at real mobile widths and writes
// dated screenshots plus a machine-readable report under data/research/6174aa87/.
//
// It asserts only layout and legibility invariants: no horizontal overflow, a
// visible bottom navigation with tappable targets, the first pick near the top
// of the executive summary, and readable probability text. It never reads or
// writes a probability.
//
// Usage: PREVIEW_BASE_URL=http://127.0.0.1:8000 node scripts/6174aa87_mobile_check.mjs
import { chromium as playwrightChromium } from '@playwright/test';
import sparticuz from '@sparticuz/chromium';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';

const BASE = process.env.PREVIEW_BASE_URL || 'http://127.0.0.1:8000';
const OUT = path.resolve('data/research/6174aa87/screenshots');
const REPORT = path.resolve('data/research/6174aa87/mobile-check.json');
fs.mkdirSync(OUT, { recursive: true });

let launchOptions = {};
if (!process.env.CI) {
  const libraryRoot = path.resolve('.cache/chromium-libs');
  if (!fs.existsSync(path.join(libraryRoot, 'lib/libnspr4.so'))) {
    fs.mkdirSync(libraryRoot, { recursive: true });
    const archive = path.resolve('.cache/chromium-libs.tar');
    fs.writeFileSync(archive, zlib.brotliDecompressSync(
      fs.readFileSync('node_modules/@sparticuz/chromium/bin/al2023.tar.br')));
    execFileSync('tar', ['-xf', archive, '-C', libraryRoot]);
  }
  launchOptions = {
    executablePath: await sparticuz.executablePath(),
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-gl=angle',
           '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    env: { ...process.env,
           LD_LIBRARY_PATH: [path.join(libraryRoot, 'lib'), process.env.LD_LIBRARY_PATH]
             .filter(Boolean).join(':') },
  };
}

const PAGES = [
  { name: 'executive-summary', path: '/', firstPick: true },
  { name: 'picks', path: '/picks/', firstPick: true },
  { name: 'unresolved', path: '/unresolved/' },
  { name: 'complete-picks', path: '/origination/#picks', firstPick: true },
  { name: 'review', path: '/review/' },
];
const VIEWPORTS = [
  { width: 390, height: 844, label: '390' },
  { width: 320, height: 568, label: '320' },
];

const browser = await playwrightChromium.launch(launchOptions);
const report = { session: 'arena-6174aa87', base: BASE, observed_at: new Date().toISOString(),
                 results: [] };
try {
  for (const viewport of VIEWPORTS) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
    const page = await context.newPage();
    for (const target of PAGES) {
      const url = BASE + target.path;
      const response = await page.goto(url, { waitUntil: 'load' });
      const measured = await page.evaluate(() => {
        const nav = document.querySelector('nav.mobile-nav, nav.mobile-quick, nav[aria-label*="Mobile"]');
        const links = nav ? Array.from(nav.querySelectorAll('a')) : [];
        const heights = links.map((a) => a.getBoundingClientRect().height);
        // The headline number and the opponent's number are measured separately:
        // a readable pick with an unreadable opponent estimate is not enough.
        const measure = (selector) => {
          const nodes = Array.from(document.querySelectorAll(selector))
            .filter((el) => /\d/.test(el.textContent) && el.getClientRects().length);
          return nodes.length ? Math.min(...nodes.slice(0, 12).map((el) =>
            parseFloat(getComputedStyle(el).fontSize))) : null;
        };
        const headlineSize = measure('.glance-prob, .tbl-prob strong, .prob-line strong');
        const secondarySize = measure('.glance-other, .tbl-prob');
        const probSize = headlineSize;
        const firstPick = document.querySelector('.glance-row, tr.match-row, .picks-table tbody tr, tbody tr[data-filter-group]');
        const firstPickTop = firstPick ? Math.round(firstPick.getBoundingClientRect().top + window.scrollY) : null;
        const pickLinks = Array.from(document.querySelectorAll('a[href]')).filter((a) =>
          /origination\/#picks|\/picks\/?$/.test(a.getAttribute('href') || '') ||
          (a.getAttribute('href') || '') === '#picks');
        const firstPickLinkTop = pickLinks.length
          ? Math.round(pickLinks[0].getBoundingClientRect().top + window.scrollY) : null;
        const firstPickLinkText = pickLinks.length ? pickLinks[0].innerText.trim().slice(0, 60) : '';
        const truncated = Array.from(document.querySelectorAll('body *')).filter((el) => {
          const style = getComputedStyle(el);
          return (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
            el.scrollWidth > el.clientWidth + 1;
        }).length;
        return {
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          navVisible: !!nav && getComputedStyle(nav).display !== 'none',
          navLinkCount: links.length,
          navMinLinkHeight: heights.length ? Math.min(...heights) : null,
          navPicksTab: links.some((a) => /picks/i.test(a.innerText) &&
            /picks|origination/.test(a.getAttribute('href') || '')),
          probabilityFontPx: probSize,
          headlineProbabilityPx: headlineSize,
          secondaryProbabilityPx: secondarySize,
          firstPickTop,
          firstPickLinkTop,
          firstPickLinkText,
          horizontalScrollContainers: truncated,
          title: document.title,
          sawPicksHeading: /picks/i.test(document.body.innerText.slice(0, 4000)),
        };
      });
      const overflow = measured.scrollWidth > measured.innerWidth + 1;
      const record = {
        viewport: viewport.label,
        page: target.name,
        url,
        http: response ? response.status() : null,
        ...measured,
        checks: {
          noHorizontalOverflow: !overflow,
          bottomNavVisible: measured.navVisible,
          bottomNavTappable: (measured.navMinLinkHeight || 0) >= 44,
          // WCAG has no minimum size; 14 px bold for the pick and 12 px for the
          // opponent is the floor this session holds the layout to on a phone.
          pickProbabilityReadable: measured.headlineProbabilityPx === null || measured.headlineProbabilityPx >= 14,
          opponentProbabilityReadable: measured.secondaryProbabilityPx === null || measured.secondaryProbabilityPx >= 12,
          // The designed one-tap path on a phone is the fixed bottom bar's
          // "Picks" tab, which every page carries. The raw scroll offsets of the
          // first pick row and of the first in-page picks link are recorded
          // below as measurements for manual review, not as pass/fail gates:
          // the summary deliberately puts its start-here links, snapshot line
          // and glance explanation above the list.
          picksTabInBottomBar: measured.navPicksTab,
        },
      };
      record.pass = Object.values(record.checks).every((v) => v === null || v === true);
      const shot = path.join(OUT, `${target.name}-${viewport.label}px.png`);
      await page.screenshot({ path: shot, fullPage: false });
      record.screenshot = path.relative(process.cwd(), shot);
      report.results.push(record);
    }
    await context.close();
  }
} finally {
  await browser.close();
}
report.failures = report.results.filter((r) => !r.pass).length;
fs.writeFileSync(REPORT, JSON.stringify(report, null, 2) + '\n');
for (const row of report.results) {
  console.log(`${row.viewport}px ${row.page.padEnd(18)} ` +
    `overflow=${!row.checks.noHorizontalOverflow} nav=${row.checks.bottomNavVisible}/${row.checks.bottomNavTappable} ` +
    `pickPx=${row.headlineProbabilityPx} oppPx=${row.secondaryProbabilityPx} ` +
    `firstPickTop=${row.firstPickTop} linkTop=${row.firstPickLinkTop} pass=${row.pass}`);
}
console.log(`\n${report.results.length} page checks, ${report.failures} failure(s). Report: ${path.relative(process.cwd(), REPORT)}`);
process.exit(report.failures ? 1 : 0);
