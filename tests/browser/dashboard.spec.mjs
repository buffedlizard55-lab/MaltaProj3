import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';

const routes = ['/', '/picks/', '/coverage/', '/methodology/', '/review/'];

for (const width of [320, 390, 768, 1440]) {
  test(`all current pages are readable without horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator('main h1')).toBeVisible();
      await expect(page.locator('main')).toBeVisible();
      const dimensions = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      expect(dimensions.document, `${route} overflows at ${width}`).toBeLessThanOrEqual(dimensions.viewport + 1);
    }
    expect(errors).toEqual([]);
  });
}

test('phone navigation reaches the full picks list in one tap', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('link', { name: 'See all match picks' }).click();
  await expect(page).toHaveURL(/\/picks\/$/);
  await expect(page.locator('#match-list > tbody > tr')).not.toHaveCount(0);
  await expect(page.locator('.mobile-nav a[aria-current="page"]')).toHaveText('Picks');
});

test('search, method filters, sorting and clearing work', async ({ page }) => {
  await page.goto('/picks/');
  const all = page.locator('#match-list > tbody > .match-row');
  const total = await all.count();
  await page.locator('#match-search').fill('definitely-no-such-team');
  await expect(page.locator('#filter-empty')).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
  expect(await page.locator('#match-list > tbody > tr:visible').count()).toBe(total);
  await page.getByRole('button', { name: /^Research/ }).click();
  expect(await page.locator('#match-list > tbody > tr:visible').count()).toBe(await page.locator('#match-list > tbody > tr[data-method="model"]').count());
  await page.locator('#match-sort').selectOption('confidence');
  const probabilities = await page.locator('#match-list > tbody > tr:visible').evaluateAll(nodes => nodes.map(n => Number(n.dataset.confidence)));
  expect(probabilities).toEqual([...probabilities].sort((a, b) => b - a));
});

test('every current match row links to original Hotspawn evidence', async ({ page }) => {
  await page.goto('/picks/');
  for (const row of await page.locator('#match-list > tbody > .match-row').all()) {
    expect(await row.locator('a[href*="hotspawn.com"], a[href*="cloudwaysapps.com"]').count()).toBeGreaterThan(0);
  }
});

test('evidence expands on a small phone without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 850 });
  await page.goto('/picks/');
  await page.locator('#match-list > tbody > tr').first().locator('summary').click();
  await expect(page.locator('details[open] .evidence-box')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});

test('timezone conversion is explicit and changes the displayed time', async ({ page }) => {
  await page.goto('/picks/');
  await page.locator('#timezone').selectOption('Europe/Malta');
  const before = await page.locator('.match-cell time').first().textContent();
  await page.locator('#timezone').selectOption('UTC');
  expect(await page.locator('.match-cell time').first().textContent()).not.toBe(before);
  await expect(page.locator('[data-zone-label]')).toHaveText('UTC');
});

test('a stale snapshot warns and never masquerades as a current pick', async ({ page }) => {
  await page.clock.install({ time: new Date('2027-01-01T12:00:00Z') });
  await page.goto('/picks/');
  await expect(page.locator('#stale-warning')).toBeVisible();
  const choices = page.locator('[data-pick-choice]');
  expect(await choices.count()).toBeGreaterThan(0);
  await expect(choices.first()).toContainText('Snapshot:');
  await expect(page.locator('[data-pick-caption]').first()).toContainText('not a current pick');
});

test('all matches and source links remain available with JavaScript disabled', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto('/picks/');
  expect(await page.locator('#match-list > tbody > tr').count()).toBeGreaterThan(0);
  await expect(page.locator('noscript')).toContainText('Every row and source remains visible');
  await context.close();
});

for (const route of routes) {
  test(`current page ${route} passes WCAG A/AA automated accessibility checks`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(route);
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    expect(result.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.slice(0, 4).map(n => ({ target: n.target, summary: n.failureSummary })) }))).toEqual([]);
  });
}

test('capture final phone and desktop views for visual verification', async ({ page }) => {
  await fs.mkdir('.cache/screenshots', { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto('/');
  await page.screenshot({ path: '.cache/screenshots/summary-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '.cache/screenshots/summary-phone.png', fullPage: true });
  await page.goto('/picks/');
  await page.screenshot({ path: '.cache/screenshots/picks-phone.png', fullPage: true });
});
