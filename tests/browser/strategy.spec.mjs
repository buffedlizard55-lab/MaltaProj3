import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';

// The page under test is a synthetic fixture built with a pinned clock (see strategy_fixture.py),
// so these checks never depend on live data or on the time they run.
const PAGE = '/_fixture/strategy/';
const BUILD_TIME = '2026-10-16T09:00:00Z';

test.beforeAll(() => {
  execFileSync(process.env.PYTHON || 'python', ['tests/browser/strategy_fixture.py'], { stdio: 'inherit' });
});

test.afterAll(() => {
  fs.rmSync('site/_fixture', { recursive: true, force: true });
});

test.beforeEach(async ({ page }) => {
  await page.clock.install({ time: new Date(BUILD_TIME) });
});

for (const width of [320, 390, 768, 1440]) {
  test(`leaderboard plan has no horizontal overflow and a clear pick at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(PAGE);
    await expect(page.locator('main h1')).toBeVisible();
    const size = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
    expect(size.document).toBeLessThanOrEqual(size.viewport + 1);
    const cards = page.locator('#slate .pick-card');
    await expect(cards).toHaveCount(5); // 6 open fixtures minus the unresolved one; the locked one is hidden
    for (const card of await cards.all()) {
      await expect(card.locator('.pickline strong')).toBeVisible();
      await expect(card.locator('.prob.default')).toHaveCount(1);
      expect(await card.locator('a[href*="hotspawn.com"]').count()).toBeGreaterThan(0);
    }
    expect(errors).toEqual([]);
  });
}

test('only the qualifying underdogs carry the upset ribbon and name the underdog as the plan pick', async ({ page }) => {
  await page.goto(PAGE);
  const swaps = page.locator('#slate .pick-card.swap');
  await expect(swaps).toHaveCount(2);
  await expect(page.locator('#match-2001 .pickline strong')).toHaveText('9z');
  await expect(page.locator('#match-2001 .pickline small')).toContainText('Most likely winner: Aurora 69.0%');
  await expect(page.locator('#match-2002 .pickline strong')).toHaveText('Envy');
  // The crowd is already on BC.Game, the model-only and the lock stay with the most likely winner.
  await expect(page.locator('#match-2003 .pickline strong')).toHaveText('MIBR');
  await expect(page.locator('#match-2003 .chip.note')).toContainText('the field is already on this side');
  await expect(page.locator('#match-2005 .pickline strong')).toHaveText('EAC');
  await expect(page.locator('#match-2004 .pickline strong')).toHaveText('Phantom');
});

test('the Thunderpick World Championship card shows the team-plus-score slip with its model caveat', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(PAGE);
  const slip = page.locator('#match-2001 .scoreblock');
  await expect(slip).toBeVisible();
  await expect(slip).toContainText("Tournament pick'em slip: team + score (7 + 5 points)");
  await expect(slip.locator('.scores li')).toHaveCount(4);
  await expect(slip).toContainText('the best score to enter is 9z 2-1');
  await expect(slip).toContainText('Model-derived from the series line, not a source fact');
  // Only the researched best-of-three tournament fixture gets a slip.
  await expect(page.locator('.scoreblock')).toHaveCount(1);
  const box = await slip.boundingBox();
  expect(box.x + box.width).toBeLessThanOrEqual(390);
});

test('the tournament section states scoring and prizes with a source link and a read time on every card', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(PAGE);
  const cards = page.locator('#tournament .def');
  await expect(cards).toHaveCount(6);
  for (const card of await cards.all()) {
    expect(await card.locator('a[href^="https://"]').count()).toBeGreaterThan(0);
    await expect(card).toContainText('read 2026-');
  }
  await expect(page.locator('#tournament')).toContainText('7 points for the correct team and 5 more for the correct score');
  await expect(page.locator('#tournament .unverified')).toHaveCount(2);
});

test('hero buttons reach the slate and the unresolved section, which names its limits', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(PAGE);
  await page.getByRole('link', { name: 'See the picks' }).click();
  await expect(page).toHaveURL(/#slate$/);
  await page.getByRole('link', { name: /Unresolved & limitations \(1\)/ }).click();
  await expect(page).toHaveURL(/#unresolved$/);
  const card = page.locator('#unresolved .pick-card');
  await expect(card).toHaveCount(1);
  await expect(card).toContainText('Infinite');
  await expect(card).toContainText('no pick · unverified');
  await expect(card.locator('a[href*="hotspawn.com"]')).toHaveCount(1);
});

test('locked fixtures are hidden by default and can be shown, labelled as locked', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-16T10:30:00Z') });
  await page.goto(PAGE);
  // Heroic/MIBR locked at 09:54Z and the 2007 fixture earlier; the toggle hides them.
  await expect(page.locator('#match-2002')).toBeHidden();
  await expect(page.locator('#match-2001')).toBeVisible();
  await page.getByLabel('Hide fixtures that have locked').uncheck();
  await expect(page.locator('#match-2002')).toBeVisible();
  await expect(page.locator('#match-2002 .status')).toBeVisible();
  await expect(page.locator('#match-2002 .status')).toContainText('Locked');
});

test('on a phone every results row shows its source link without horizontal scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(PAGE);
  const links = page.locator('#lessons td[data-label="Source"] a');
  expect(await links.count()).toBeGreaterThanOrEqual(8);
  for (const link of await links.all()) {
    await link.scrollIntoViewIfNeeded();
    const box = await link.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(390);
  }
  for (const link of await page.locator('#hotspawn td[data-label="Source"] a').all()) {
    const box = await link.boundingBox();
    expect(box.x + box.width).toBeLessThanOrEqual(390);
  }
});

for (const width of [390, 1440]) {
  test(`leaderboard plan passes automated WCAG A/AA checks at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 });
    await page.goto(PAGE);
    await page.locator('#match-2001 details.more summary').click();
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(results.violations.map(v => `${v.id}: ${v.nodes.map(n => n.target.join(' ')).join(' | ')}`)).toEqual([]);
  });
}
