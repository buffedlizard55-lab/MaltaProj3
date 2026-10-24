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

test('an open phone tab retires an eight-hour-old pick without hiding either probability or source', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-24T00:00:00Z') });
  await page.setContent(`<!doctype html><html><body
    data-inventory-time="2026-10-24T00:00:00Z" data-inventory-complete="true">
    <ol id="glance-list"><li class="glance-row" data-glance-closed="false"
      data-glance-inactive="false" data-glance-observed="2026-10-24T00:00:00Z"
      data-glance-locks="2026-10-26T09:54:00Z" data-glance-starts="2026-10-26T10:00:00Z">
      <span data-glance-pick>Pick</span><strong>Synthetic A</strong>
      <span class="glance-prob">60.0%</span><span class="glance-other">Synthetic B 40.0%</span>
      <a href="https://polymarket.com/esports/cs2">Official source</a>
    </li></ol></body></html>`);
  await page.addScriptTag({ path: 'assets/glance-lock.js' });
  await expect(page.locator('[data-glance-pick]')).toHaveText('Pick');
  await page.clock.fastForward(8 * 3600000 + 30001);
  await expect(page.locator('[data-glance-pick]')).toHaveText('Snapshot');
  await expect(page.locator('.glance-row')).toContainText('60.0%');
  await expect(page.locator('.glance-row')).toContainText('Synthetic B 40.0%');
  await expect(page.getByRole('link', { name: 'Official source' })).toHaveAttribute('href', 'https://polymarket.com/esports/cs2');
  // A clock correction must not reopen a retired recommendation.
  await page.clock.setSystemTime(new Date('2026-10-24T01:00:00Z'));
  await page.clock.fastForward(30001);
  await expect(page.locator('[data-glance-pick]')).toHaveText('Snapshot');
});

test('missing line freshness is not made current by a fresh inventory', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-24T00:00:00Z') });
  await page.setContent(`<!doctype html><html><body
    data-inventory-time="2026-10-24T00:00:00Z" data-inventory-complete="true">
    <ol id="glance-list"><li class="glance-row" data-glance-closed="false"
      data-glance-observed="" data-glance-locks="2026-10-26T09:54:00Z"
      data-glance-starts="2026-10-26T10:00:00Z"><span data-glance-pick>Pick</span>
    </li></ol></body></html>`);
  await page.addScriptTag({ path: 'assets/glance-lock.js' });
  await expect(page.locator('[data-glance-pick]')).toHaveText('Snapshot');
});
