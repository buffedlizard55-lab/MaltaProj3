import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 568 },
  { name: 'modern-phone-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'desktop-1440', width: 1440, height: 900 },
];

const SESSION_FLAGS = [
  '#flag-80c3b4e0-acend-unity-hltv-vrs-flip',
  '#flag-80c3b4e0-phantom-banda-chuya-vrs-flip',
  '#flag-80c3b4e0-color-ex-zt-ranking-split',
  '#flag-80c3b4e0-dfrag-substitutes-and-wide-exchange',
  '#flag-80c3b4e0-smarkets-alias-binding-and-pending-lph-alka',
  '#flag-80c3b4e0-live-30-of-30-audit-reconciled',
];

for (const vp of VIEWPORTS) {
  test(`arena-80c3b4e0 executive summary, picks tables & review flags at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });

    // 1. Landing page Executive Summary (`/`): mobile fit, subpage jump links, unresolved/limitations callout
    await page.goto('/');
    const homeFit = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(homeFit.scrollWidth).toBeLessThanOrEqual(homeFit.innerWidth);

    for (const target of ['picks/', 'origination/', 'unresolved/', 'review/']) {
      await expect(page.locator(`main a[href*="${target}"]:visible`).first()).toBeVisible();
    }

    // 2. Originated Picks (`/origination/`): zero overflow + official https links on every match row
    await page.goto('/origination/');
    const origFit = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(origFit.scrollWidth).toBeLessThanOrEqual(origFit.innerWidth);

    // 3. Flagged for Review (`/review/`): session 80c3b4e0 findings visible at top with official links + WCAG A/AA
    await page.goto('/review/');
    const reviewFit = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(reviewFit.scrollWidth).toBeLessThanOrEqual(reviewFit.innerWidth);

    for (const selector of SESSION_FLAGS) {
      const row = page.locator(selector);
      await expect(row).toBeVisible();
      await expect(row.locator('a[href^="https://"]').first()).toBeVisible();
    }

    const axe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(axe.violations).toEqual([]);
  });
}
