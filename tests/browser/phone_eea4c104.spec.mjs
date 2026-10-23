import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 568 },
  { name: 'modern-phone-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'desktop-1440', width: 1440, height: 900 },
];

for (const vp of VIEWPORTS) {
  test(`eea4c104 executive summary, picks readability, unresolved & review at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });

    // 1. Executive Summary (`/`): internal links, both-team probabilities, unresolved & no-line blocks, no overflow
    await page.goto('/');
    const homeMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(homeMetrics.scrollWidth).toBeLessThanOrEqual(homeMetrics.innerWidth);

    for (const route of ['origination/', 'picks/', 'unresolved/', 'coverage/', 'review/']) {
      await expect(page.locator(`main a[href*="${route}"]:visible`).first()).toBeVisible();
    }

    const glance = page.locator('#glance, .glance-list').first();
    await expect(glance).toBeVisible();
    const glanceText = await glance.innerText();
    const pctHits = glanceText.match(/\d+\.\d%/g) || [];
    expect(pctHits.length).toBeGreaterThanOrEqual(2);

    await expect(page.locator('#unresolved-register, #unresolved').first()).toBeVisible();
    // arena-42bfa8ea (PR #218, merged) compacted the summary: the dated sweep
    // block `#no-line-research` now renders in full on /unresolved/ and the
    // executive summary carries the compact `#no-line-register` digest.
    // Assert each block on the page that intentionally renders it.
    await expect(page.locator('#no-line-register')).toBeVisible();

    const homeAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(homeAxe.violations).toEqual([]);

    // 2. Separate Unresolved & Limitations page (`/unresolved/`)
    await page.goto('/unresolved/');
    const unresMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(unresMetrics.scrollWidth).toBeLessThanOrEqual(unresMetrics.innerWidth);
    // The dated line-source sweep block lives here in full (see note above).
    await expect(page.locator('#no-line-research')).toBeVisible();

    // 3. Flagged for Review (`/review/`): all 5 eea4c104 flags + supersede link + WCAG A/AA
    await page.goto('/review/');
    const reviewMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(reviewMetrics.scrollWidth).toBeLessThanOrEqual(reviewMetrics.innerWidth);

    for (const fid of [
      'flag-eea4c104-kalshi-bo3-alias-banda-chuya-los-kogutos-1081605',
      'flag-eea4c104-lph-gaming-thunderpick-alias-1082980',
      'flag-eea4c104-abyssal-alias-evidence-drift-1082861',
      'flag-eea4c104-nodwin-oct25-promotion-and-kalshi-spreads',
      'flag-eea4c104-replayed-1083025-and-hotspawn-ssr-cdn-lag',
    ]) {
      const row = page.locator(`#${fid}`);
      await expect(row).toBeVisible();
      const linkCount = await row.locator('a[href^="https://"]').count();
      expect(linkCount).toBeGreaterThanOrEqual(1);
    }

    await expect(page.locator('#flag-f6bfc506-row-1083025-not-replayed')).toHaveClass(/superseded-flag/);

    const reviewAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(reviewAxe.violations).toEqual([]);
  });
}
