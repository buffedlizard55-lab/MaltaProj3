import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import { python } from './python.mjs';

const FIXTURE = '/_twc_day4_fixture/';
test.beforeAll(() => execFileSync(python(), ['tests/browser/twc_day4_fixture.py'], { stdio: 'inherit' }));
test.afterAll(() => fs.rmSync('site/_twc_day4_fixture', { recursive: true, force: true }));

for (const width of [320, 390, 768, 1440]) {
  test(`Day-4 choices and both probabilities fit at ${width}px`, async ({ page }) => {
    await page.clock.install({ time: new Date('2026-10-16T20:00:00Z') });
    await page.setViewportSize({ width, height: 900 });
    await page.goto(FIXTURE);
    await expect(page.locator('#day-four-picks .twc-day4-card')).toHaveCount(2);
    await expect(page.locator('#day-four-picks .twc-prob strong')).toHaveText(['69.0%', '31.0%', '36.0%', '64.0%']);
    await expect(page.locator('#day-four-picks [data-current-only].pick-choice')).toHaveText(['Default pick: Aurora', 'Default pick: Legacy']);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const box = await page.locator('#day-four-picks .twc-day4-card').first().boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0); expect(box.x + box.width).toBeLessThanOrEqual(width);
  });
}

test('Day-4 open-tab stale and resumed guards retire default and optional underdog together', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-16T20:00:00Z') });
  await page.goto(FIXTURE);
  await expect(page.locator('#day-four-picks .twc-watch').first()).toBeVisible();
  await page.clock.fastForward(9 * 3600000);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect(page.locator('#day-four-picks [data-current-only].pick-choice').first()).toBeHidden();
  await expect(page.locator('#day-four-picks .twc-watch').first()).toBeHidden();
  await expect(page.locator('#day-four-picks [data-historical-only]').first()).toContainText('Snapshot only: Aurora');
  await expect(page.locator('#day-four-picks [data-safety-message]').first()).toContainText('Not a current pick');
});

test('Day-4 source links, current defaults and blanks remain readable with no JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 900 } });
  const page = await context.newPage();
  await page.goto(FIXTURE);
  await expect(page.locator('#day-four-picks .twc-day4-card')).toHaveCount(2);
  await expect(page.locator('#day-four-picks .twc-prob strong')).toHaveText(['69.0%', '31.0%', '36.0%', '64.0%']);
  for (const card of await page.locator('#day-four-picks .twc-day4-card').all()) {
    await expect(card.getByRole('link', { name: 'Official Hotspawn fixture' })).toBeVisible();
    await expect(card.getByRole('link', { name: 'All source attempts & full pricing audit' })).toBeVisible();
  }
  await context.close();
});

for (const width of [390, 1440]) {
  test(`Day-4 WCAG A/AA automated scan at ${width}px`, async ({ page }) => {
    await page.clock.install({ time: new Date('2026-10-16T20:00:00Z') });
    await page.setViewportSize({ width, height: 1000 });
    await page.goto(FIXTURE);
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(result.violations).toEqual([]);
  });
}

test('published TWC source-table captions remain full-width rather than one-word columns on phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/twc-picks/');
  const captions = page.locator('caption:visible');
  expect(await captions.count()).toBeGreaterThan(0);
  for (const caption of await captions.all()) {
    const box = await caption.boundingBox();
    expect(box.width).toBeGreaterThan(250);
    expect(box.height).toBeLessThan(220);
  }
});


test('the source-listed fixture table publishes its dated read and movement on a phone', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-16T20:00:00Z') });
  await page.setViewportSize({ width: 320, height: 900 });
  await page.goto(FIXTURE);
  const table = page.locator('table.twc-day4-lines');
  await expect(table).toHaveCount(1);
  await expect(table.locator('tbody tr')).toHaveCount(2);
  const listed = table.locator('tbody tr').first();
  await expect(listed.locator('.twc-prob strong')).toHaveText(['52.4%', '47.6%']);
  await expect(listed).toContainText('Dated lean: FURIA');
  await expect(listed).toContainText("this session's own research capture");
  await expect(listed.locator('.twc-movement')).toContainText('Line movement:');
  await expect(listed).toContainText('no reprice since it opened');
  await expect(listed.locator('a[href*="hltv.org/matches/2399414"]')).toHaveCount(1);
  // A bracket placeholder stays unpriced and says why.
  const placeholder = table.locator('tbody tr').nth(1);
  await expect(placeholder).toContainText('bracket placeholder');
  await expect(placeholder.locator('.twc-prob strong')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
