import { test, expect } from '@playwright/test';

for (const width of [320, 390]) {
  test(`one research anchor, both probabilities, official sources and one-tap navigation at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    for (const route of ['/', '/unresolved/']) {
      await page.goto(route);
      const duplicateIds = await page.locator('[id]').evaluateAll(nodes => {
        const seen = new Set();
        return nodes.map(n => n.id).filter(id => seen.has(id) || !seen.add(id));
      });
      expect(duplicateIds, `${route} must not have ambiguous phone anchors`).toEqual([]);
      await expect(page.locator('#no-line-research')).toHaveCount(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    }
    await page.goto('/');
    const rows = page.locator('#glance-list > .glance-row');
    expect(await rows.count()).toBeGreaterThan(0);
    for (const row of await rows.all()) {
      // Historical estimates stay readable too; the safety label may say Locked.
      const percentages = (await row.innerText()).match(/\d+\.\d%/g) || [];
      const unresolved = await row.locator('.glance-pick-label.unresolved-text').count();
      if (!unresolved) expect(percentages.length).toBeGreaterThanOrEqual(2);
      expect(await row.locator('a[href*="hotspawn.com"], a[href*="cloudwaysapps.com"]').count()).toBeGreaterThan(0);
      await expect(row.getByRole('link', { name: 'Full detail' })).toHaveAttribute('href', /origination\/#match-/);
    }
    const nav = page.getByRole('navigation', { name: 'Mobile navigation' });
    await nav.getByRole('link', { name: 'Picks', exact: true }).click();
    await expect(page).toHaveURL(/\/origination\/#picks$/);
    await expect(page.locator('.pick-card').first()).toBeVisible();
    await page.goto('/');
    await nav.getByRole('link', { name: 'Unresolved', exact: true }).click();
    await expect(page).toHaveURL(/\/unresolved\/$/);
    await expect(page.locator('#unresolved-register')).toBeVisible();
  });
}
