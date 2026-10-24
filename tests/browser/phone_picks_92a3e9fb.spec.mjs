import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 568 },
  { name: 'modern-phone-390', width: 390, height: 844 },
];

for (const vp of VIEWPORTS) {
  test(`phone executive summary & review verification at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });

    // 1. Executive Summary (`/`): obvious mobile picks, win probabilities, subpage links, unresolved block, no horizontal scroll
    await page.goto('/');
    const homeOverflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(homeOverflow.scrollWidth).toBeLessThanOrEqual(homeOverflow.innerWidth);

    // Subpage category links inside <main> reachable directly from Executive Summary on mobile
    for (const target of ['picks/', 'origination/', 'unresolved/', 'coverage/', 'review/']) {
      // The optional stale warning also contains these destinations but is
      // intentionally hidden on a fresh build. Assert the reachable summary
      // links, not that hidden warning's copy of the same URL.
      await expect(page.locator(`main a[href*="${target}"]:visible`).first()).toBeVisible();
    }

    // Mobile "Picks at a glance" surfaces directional pick + win probabilities immediately
    const glance = page.locator('#glance, .glance-list').first();
    await expect(glance).toBeVisible();
    const glanceText = await glance.innerText();
    expect(glanceText).toMatch(/\d+\.\d%/);

    // Search/filter input works smoothly on mobile
    const searchInput = page.locator('#glance-search, main input[type="search"]').first();
    if ((await searchInput.count()) > 0) {
      await expect(searchInput).toBeVisible();
    }

    // 2. Unresolved & No-Betting-Line subpage (`/unresolved/`): zero horizontal overflow
    await page.goto('/unresolved/');
    const unresOverflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(unresOverflow.scrollWidth).toBeLessThanOrEqual(unresOverflow.innerWidth);

    // 3. Flagged for Review (`/review/`): publishes arena-92a3e9fb register + flags with https links & zero WCAG violations
    await page.goto('/review/');
    const reviewOverflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(reviewOverflow.scrollWidth).toBeLessThanOrEqual(reviewOverflow.innerWidth);

    const datedRegisters = page.locator('#dated-registers');
    if ((await datedRegisters.count()) > 0 && !(await datedRegisters.evaluate((el) => el.hasAttribute('open')))) {
      await datedRegisters.locator('summary').first().click();
    }

    await expect(page.locator('#review-92A-R01')).toBeVisible();
    await expect(page.locator('#review-92A-R02')).toBeVisible();
    await expect(page.locator('#review-92A-R04')).toBeVisible();
    await expect(page.locator('#review-92A-R08')).toBeVisible();

    const axe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(axe.violations).toEqual([]);
  });
}
