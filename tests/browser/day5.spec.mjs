import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import { python } from './python.mjs';

test.beforeAll(() => execFileSync(python(), ['tests/browser/day5_fixture.py'], { stdio: 'inherit' }));
test.afterAll(() => fs.rmSync('site/_day5_fixture', { recursive: true, force: true }));

for (const width of [320, 390, 768, 1440]) {
  test(`final-day entry, data parity and layout at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    // Session arena-5fbf5cd5 collapses the dated tournament block so today's
    // picks sit near the top of the phone summary; its links live behind the
    // labelled summary row.
    await page.locator('#archive-twc > summary').click();
    await page.locator('#final-day-summary a[href$="#day-five-picks"]').click();
    await expect(page).toHaveURL(/\/twc-picks\/#day-five-picks$/);
    const d = await (await page.request.get('/data/twc-day5-picks.json')).json();
    await expect(page.locator('.twc-day5-card')).toHaveCount(d.cards.length);
    for (const r of d.cards) {
      await expect(page.locator(`#twc-day5-${r.fixture.id} .twc-prob strong`)).toHaveText(
        r.analysis ? r.analysis.probabilities.map(p => `${(p * 100).toFixed(1)}%`) : ['—', '—']);
    }
    await expect(page.locator('#day-five-unresolved')).toContainText('HLTV is an independent reporter');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
  });
}

test('final-day default and optional underdog retire together after the freshness boundary', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-17T20:00:00Z') });
  await page.goto('/_day5_fixture/');
  const card = page.locator('.twc-day5-card').first();
  await expect(card.locator('[data-current-only]').first()).toContainText('Default pick: Aurora');
  await expect(card.locator('.twc-watch')).toBeVisible();
  await page.clock.fastForward(8 * 3600000 + 31000);
  await expect(card.locator('[data-current-only]').first()).toBeHidden();
  await expect(card.locator('.twc-watch')).toBeHidden();
  await expect(card.locator('[data-historical-only]')).toBeVisible();
  await expect(card.locator('[data-safety-message]')).toContainText('Snapshot needs refresh');
});

test('final-day sources and estimates remain usable without JS but current advice is hidden', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 844 } });
  try {
    const page = await context.newPage();
    await page.goto('/_day5_fixture/');
    const card = page.locator('.twc-day5-card').first();
    await expect(card.locator('.twc-prob strong')).toHaveText(['69.0%', '31.0%']);
    await expect(card.locator('[data-current-only]').first()).toBeHidden();
    await expect(card.locator('[data-historical-only]')).toBeVisible();
    await expect(card.locator('a[href*="hltv.org/"]')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(321);
  } finally { await context.close(); }
});

test('final-day phone cards and public page pass WCAG A/AA', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ['/twc-picks/', '/_day5_fixture/']) {
    await page.goto(route);
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    expect(result.violations).toEqual([]);
  }
});
