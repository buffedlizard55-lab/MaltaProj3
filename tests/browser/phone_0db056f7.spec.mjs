import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Session arena-0db056f7: the executive summary must make the updated picks
// findable in one tap on a phone, and must carry its own clearly labelled
// unresolved/limitations section. Verified against a locally built site.

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 640 },
  { name: 'modern-phone-390', width: 390, height: 844 },
  { name: 'large-phone-430', width: 430, height: 932 },
];

for (const vp of VIEWPORTS) {
  test(`0db056f7 executive summary is phone-usable at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto('/');

    // No horizontal overflow at phone widths.
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.innerWidth);

    // One-tap status bar: picks-ready count and unresolved shortcut.
    const status = page.locator('nav.mobile-status');
    await expect(status).toBeVisible();
    await expect(status.locator('a.mobile-status-picks')).toBeVisible();
    await expect(status.locator('a.mobile-status-blank')).toBeVisible();

    // Start-here links point at the picks, on this page and the full list.
    await expect(page.locator('#start-here a[href$="#picks-at-a-glance"]').first()).toBeVisible();
    await expect(page.locator('#start-here a[href*="origination/#picks"]').first()).toBeVisible();
    await expect(page.locator('#start-here a[href$="#unresolved-register"]').first()).toBeVisible();

    // Picks at a glance: first row shows both teams and an obvious pick.
    const firstRow = page.locator('#glance-list > .glance-row').first();
    await expect(firstRow).toBeVisible();
    await expect(firstRow.locator('.glance-prob')).toBeVisible();
    await expect(firstRow.locator('.glance-other')).toBeVisible();

    // The executive summary itself carries the unresolved section with
    // limitations, plus the no-line and fallback registers.
    for (const id of ['unresolved-register', 'no-line-register', 'fallback-register']) {
      await expect(page.locator(`#${id}`)).toHaveCount(1);
    }
    await expect(page.locator('#unresolved-register-title')).toContainText(/Unresolved/i);

    // Bottom mobile nav links are real tap targets (>= 44px tall).
    const navHeights = await page.locator('nav.mobile-nav > a').evaluateAll(
      (els) => els.map((el) => el.getBoundingClientRect().height));
    expect(navHeights.length).toBeGreaterThan(0);
    for (const h of navHeights) expect(h).toBeGreaterThanOrEqual(44);

    // WCAG A/AA clean on the landing page.
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(axe.violations).toEqual([]);
  });

  test(`0db056f7 flagged-for-review rows render at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.goto('/review/');
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.innerWidth);
    for (const id of ['review-0DB0-R01', 'review-0DB0-R02', 'review-0DB0-R03',
                      'review-0DB0-R04', 'review-0DB0-R05']) {
      const row = page.locator(`#${id}`);
      await expect(row).toHaveCount(1);
      const links = row.locator('a.source-link[href^="https://"]');
      expect(await links.count()).toBeGreaterThan(0);
    }
  });
}
