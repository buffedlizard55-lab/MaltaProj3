// CD37 candidate acceptance: real feed count, visible safety labels, sources and phones.
// Runs against site/data; freshness expectations follow the fixture clock, so an old
// checked-in snapshot must remain historical while a fresh candidate must be current.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';

const feed = JSON.parse(await fs.readFile('site/data/origination.json', 'utf8'));
const inventory = JSON.parse(await fs.readFile('site/data/latest.json', 'utf8'));
const rows = feed.matches;
const observedNow = Date.now();
const MAX_AGE_MS = 8 * 3600000;

function fresh(value) {
  const time = Date.parse(value || '');
  const age = observedNow - time;
  return Number.isFinite(time) && age >= -300000 && age <= MAX_AGE_MS;
}

function expectedCurrent(row) {
  const start = Date.parse(row.starts_at || '');
  const lock = Date.parse(row.locks_at || '');
  const probabilities = row.origination?.probabilities;
  const validPair = Array.isArray(probabilities) && probabilities.length === 2
    && probabilities.every((value) => Number.isFinite(value) && value > 0 && value < 1)
    && Math.abs(probabilities[0] + probabilities[1] - 1) < 0.0001;
  return validPair && Number.isFinite(start) && Number.isFinite(lock) && observedNow < start
    && observedNow < lock && lock <= start && row.availability === 'open'
    && inventory.coverage_complete === true && fresh(feed.source_snapshot_at)
    && fresh(row.origination.observed_at);
}

async function layout(page, width) {
  return page.evaluate((viewportWidth) => {
    const ids = [...document.querySelectorAll('[id]')].map((node) => node.id);
    const counts = ids.reduce((map, id) => map.set(id, (map.get(id) || 0) + 1), new Map());
    return {
      duplicateIds: [...counts].filter(([, count]) => count > 1).map(([id]) => id),
      scrollWidth: document.documentElement.scrollWidth,
      viewportWidth,
    };
  }, width);
}

async function expectSafetyLabel(card, row) {
  const current = expectedCurrent(row);
  await expect(card).toHaveAttribute('data-was-current', String(current));
  if (!row.origination) return;
  if (current) {
    await expect(card.locator('[data-historical-only]:visible')).toHaveCount(0);
  } else {
    await expect(card.locator('[data-current-only]:visible')).toHaveCount(0);
    await expect(card.locator('.line-time [data-historical-only]:visible')).toBeVisible();
  }
}

for (const width of [320, 390]) {
  test(`CD37 summary-to-${rows.length}-row complete list at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    const homeLayout = await layout(page, width);
    expect(homeLayout.duplicateIds).toEqual([]);
    expect(homeLayout.scrollWidth).toBeLessThanOrEqual(width + 1);

    const completeLink = page.getByRole('link', { name: 'See all match picks' });
    await expect(completeLink).toBeVisible();
    await expect(completeLink).toHaveAttribute('href', './origination/#picks');
    await expect(page.locator('#unresolved-register')).toBeVisible();
    await expect(page.locator('#no-line-register')).toBeVisible();
    await completeLink.click();
    await expect(page).toHaveURL(/\/origination\/#picks$/);
    await expect(page.locator('.pick-card')).toHaveCount(rows.length);

    for (const row of rows) {
      const card = page.locator(`#match-${row.id}`);
      await expect(card).toHaveCount(1);
      await expectSafetyLabel(card, row);
      const probabilities = card.locator('.probs > li > strong');
      await expect(probabilities).toHaveCount(2);
      const hrefs = await card.locator('.row-srcs a[href^="https://"]').evaluateAll((links) => links.map((link) => link.href));
      expect(hrefs).toContain(row.source_url);
      if (!row.origination) {
        await expect(card.locator('.pick-line')).toContainText('Unresolved');
        await expect(probabilities.nth(0)).toHaveText('—');
        await expect(probabilities.nth(1)).toHaveText('—');
        continue;
      }
      expect(hrefs).toContain(row.origination.source_url);
      for (let index = 0; index < 2; index += 1) {
        await expect(probabilities.nth(index)).toBeVisible();
        await expect(probabilities.nth(index)).toHaveText(`${(row.origination.probabilities[index] * 100).toFixed(1)}%`);
      }
      if (row.pick_index === null) {
        await expect(card.locator('.pick-line strong')).toHaveText('No directional edge');
      } else {
        await expect(card.locator('.pick-line strong')).toHaveText(row.teams[row.pick_index].name);
      }
    }

    await expect(page.locator('#unresolved')).toBeVisible();
    await expect(page.locator('#unresolved')).toContainText('Unresolved picks');
    const finalLayout = await layout(page, width);
    expect(finalLayout.duplicateIds).toEqual([]);
    expect(finalLayout.scrollWidth).toBeLessThanOrEqual(width + 1);
  });
}

test('CD37 summary, unresolved and review routes have unique IDs and no 390px overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ['/', '/unresolved/', '/review/']) {
    await page.goto(route);
    const routeLayout = await layout(page, 390);
    expect(routeLayout.duplicateIds, route).toEqual([]);
    expect(routeLayout.scrollWidth, route).toBeLessThanOrEqual(391);
  }
});

test('CD37 complete-list links and static safety labels work without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const page = await context.newPage();
    await page.goto('/');
    await page.getByRole('link', { name: 'See all match picks' }).click();
    await expect(page).toHaveURL(/\/origination\/#picks$/);
    await expect(page.locator('.pick-card')).toHaveCount(rows.length);
    const row = rows.find((candidate) => candidate.origination);
    if (row) await expectSafetyLabel(page.locator(`#match-${row.id}`), row);
  } finally {
    await context.close();
  }
});

test('CD37 390px complete list has no WCAG A/AA violations', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/origination/');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  expect(results.violations).toEqual([]);
});
