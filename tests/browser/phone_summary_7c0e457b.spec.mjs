import { test, expect } from '@playwright/test';

// Session arena-7c0e457b — the executive summary is picks first, history on tap.
//
// Measured on the built page at 390x844 before this session: 29,667 px tall,
// with the separate unresolved/limitation register starting at 9,618 px and the
// hero at 16,428 px. Eight sessions of dated reviews, blind spots, probes and
// research trails were rendered open between the picks and everything else, so
// a phone reader scrolled roughly twenty screens of history to reach the page.
//
// Nothing was deleted. Those blocks are now <details class="fold"> elements,
// closed by default, with their text, ids and headings intact; assets/scout.js
// opens an enclosing block when a deep link points inside it. This spec pins
// the measured result, in a browser, because it is a layout fact:
//
//   page height      29,667 -> 16,250 px  (390px, stale-snapshot build)
//   register offset   9,618 ->  2,349 px
//   first glance row  1,006 ->    985 px  (limit in phone_summary_17d77cb3)
//
// The ceilings below are deliberately looser than today's numbers: they are a
// budget against a regression, not a snapshot of one data set.

const sizes = [
  { width: 390, height: 844, pageLimit: 20000 },
  { width: 320, height: 568, pageLimit: 24000 },
];

for (const size of sizes) {
  test(`background blocks stay folded at ${size.width}px`, async ({ page }) => {
    await page.setViewportSize({ width: size.width, height: size.height });
    await page.goto('/');

    const report = await page.evaluate(() => {
      const folds = [...document.querySelectorAll('details.fold')];
      const visibleText = (el) => el.getBoundingClientRect().height;
      const register = document.querySelector('#unresolved-register');
      const gaps = document.querySelector('#live-coverage-gaps');
      return {
        page: document.documentElement.scrollHeight,
        overflow: document.documentElement.scrollWidth - window.innerWidth,
        folds: folds.length,
        open: folds.filter(f => f.open).length,
        foldHeight: folds.reduce((sum, f) => sum + visibleText(f), 0),
        tallestFold: Math.max(0, ...folds.map(visibleText)),
        registerTop: register.getBoundingClientRect().top + window.scrollY,
        gapsTop: gaps.getBoundingClientRect().top + window.scrollY,
        registerInsideFold: !!register.closest('details'),
        foldText: folds.map(f => f.textContent.trim().length).reduce((a, b) => a + b, 0),
        emptyLabels: folds.filter(f => !f.querySelector('summary strong')?.textContent.trim()).length,
        headings: [...document.querySelectorAll('details.fold h2, details.fold h3')].length,
      };
    });

    expect(report.overflow, 'the page must never scroll sideways').toBeLessThanOrEqual(1);
    expect(report.folds, 'the dated blocks must still be on the page').toBeGreaterThanOrEqual(7);
    expect(report.open, 'nothing dated opens by itself').toBe(0);
    // Twelve folded blocks, each a single summary row (111-147 px): about two
    // screens of "open this if you want the history", where 9,000 px of it used
    // to be forced on the reader.
    expect(report.foldHeight, 'closed blocks must be one tap tall, not screens').toBeLessThan(2100);
    expect(report.foldHeight / report.folds, 'each closed block is one summary row').toBeLessThan(190);
    expect(report.tallestFold, 'no single closed block may dominate the page').toBeLessThan(320);
    expect(report.emptyLabels, 'every fold needs a visible title').toBe(0);
    expect(report.foldText, 'the folded text stays in the document').toBeGreaterThan(2000);
    expect(report.headings, 'folded sections keep their headings').toBeGreaterThan(3);
    expect(report.registerInsideFold, 'the register itself is never folded away').toBe(false);
    expect(report.registerTop, 'the register must be reachable early').toBeLessThan(report.gapsTop);
    expect(report.page, 'the summary must stay a page, not an archive').toBeLessThan(size.pageLimit);
  });
}

test('the picks, the register and the gaps keep their reading order', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const order = await page.evaluate(() => ['#picks-at-a-glance', '#unresolved-register', '#live-coverage-gaps', '#next-matches-section']
    .map(sel => document.querySelector(sel).getBoundingClientRect().top + window.scrollY));
  expect(order).toEqual([...order].sort((a, b) => a - b));
  await expect(page.locator('#unresolved-register-title')).toBeVisible();
  await expect(page.locator('#picks-at-a-glance .glance-row').first()).toBeVisible();
});

test('a deep link opens the closed block it points into', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#upset-watchlist');
  const state = await page.evaluate(() => {
    const target = document.querySelector('#upset-watchlist');
    const fold = target.closest('details');
    return {
      exists: !!fold,
      open: fold.open,
      targetVisible: target.getBoundingClientRect().height > 0,
      otherOpen: [...document.querySelectorAll('details.fold')].filter(f => f !== fold && f.open).length,
      action: fold.querySelector('summary .fold-action')?.textContent.trim(),
    };
  });
  expect(state.exists).toBe(true);
  expect(state.open, 'the deep link must reveal its own target').toBe(true);
  expect(state.targetVisible).toBe(true);
  expect(state.otherOpen, 'only the linked block opens').toBe(0);
  expect(state.action).toBe('Open');
});

test('an in-page click also unfolds its target', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('link', { name: 'Contrarian review', exact: true }).first().click();
  await expect.poll(async () => page.evaluate(() => {
    const fold = document.querySelector('#contrarian')?.closest('details');
    return fold ? fold.open : null;
  })).toBe(true);
});
