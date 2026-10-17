import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import { python } from './python.mjs';

const FIXTURE = '/_twc_fixture/';
test.beforeAll(() => {
  execFileSync(python(), ['tests/browser/twc_fixture.py'], { stdio: 'inherit' });
});
test.afterAll(() => fs.rmSync('site/_twc_fixture', { recursive: true, force: true }));

test('phone summary exposes the canonical Day 4 guide in one tap', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Briefing shortcuts' }).getByRole('link', { name: 'Day 4 pick guide' }).click();
  await expect(page).toHaveURL(/\/twc-picks\/$/);
  await expect(page.locator('main h1')).toHaveText('TWC Day 4: picks & review');
  await expect(page.locator('#day-three-picks .twc-card')).toHaveCount(2);
  const data = await (await page.request.get('/data/twc-day3-picks.json')).json();
  const canonical = await (await page.request.get('/data/origination.json')).json();
  expect(data.schema_version).toBe(2);
  expect(data.source_snapshot_at).toBe(canonical.source_snapshot_at);
  for (const row of data.day3_matches) {
    const origin = canonical.matches.find(m => m.id === row.id);
    if (origin) expect(row.analysis).toEqual(origin.origination);
    const values = row.analysis ? row.analysis.probabilities.map(p => `${(p*100).toFixed(1)}%`) : ['—', '—'];
    await expect(page.locator(`#twc-${row.label} .twc-prob strong`)).toHaveText(values);
  }
});

test('both source-backed defaults and optional switches stay distinct; lock and staleness are enforced', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-16T09:00:00Z') });
  await page.goto(FIXTURE);
  await expect(page.locator('[data-pick-choice]')).toHaveText(['Aurora', 'Legacy']);
  await expect(page.locator('#day-three-picks .twc-prob strong')).toHaveText(['69.0%', '31.0%', '36.0%', '64.0%']);
  await expect(page.locator('#day-three-picks .twc-watch')).toHaveCount(2);
  await expect(page.locator('#day-three-picks .twc-watch').first()).toContainText('0.380 expected points per 1 base point');
  await page.clock.fastForward(4 * 3600000 + 54 * 60000);
  await expect(page.locator('#day-three-picks .twc-card').first().locator('[data-pick-choice]')).toContainText('Snapshot: Aurora');
  await expect(page.locator('#day-three-picks .twc-card').first().locator('[data-pick-caption]')).toContainText('Closed for picks');
  await page.clock.fastForward(4 * 3600000);
  await expect(page.locator('#stale-warning')).toBeVisible();
  await expect(page.locator('#day-three-picks .twc-card').first().locator('[data-pick-caption]')).toContainText('not a current pick');
});

test('TWC results, probabilities and review links survive without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 844 } });
  const page = await context.newPage();
  await page.goto(FIXTURE);
  await expect(page.locator('#day-three-picks .twc-card')).toHaveCount(2);
  await expect(page.locator('#day-three-picks .twc-prob strong')).toHaveText(['69.0%', '31.0%', '36.0%', '64.0%']);
  await expect(page.locator('#day-one-results tbody tr')).toHaveCount(4);
  await expect(page.locator('#day-two-results tbody tr')).toHaveCount(4);
  for (const row of await page.locator('.twc-results tbody tr').all()) {
    expect(await row.locator('a[href*="hltv.org/matches/"]').count()).toBe(1);
  }
  await expect(page.locator('#roster-check')).toContainText('— unverified. Both playing on Day 2 does not establish equal rest hours.');
  await context.close();
});

test('capture final TWC mobile and desktop layout', async ({ page }) => {
  fs.mkdirSync('.cache/screenshots', { recursive: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/twc-picks/');
  await page.screenshot({ path: '.cache/screenshots/twc-phone.png', fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.screenshot({ path: '.cache/screenshots/twc-desktop.png', fullPage: true });
});
