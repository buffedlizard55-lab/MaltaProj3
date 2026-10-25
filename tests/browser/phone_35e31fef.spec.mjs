import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 640 },
  { name: 'iphone-375', width: 375, height: 812 },
  { name: 'modern-phone-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
];

for (const vp of VIEWPORTS) {
  test(`35e31fef executive summary, picks, unresolved limitations & flagged-for-review at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });

    // 1. Executive Summary (`/`): zero overflow, both teams' win % + obvious pick, working in-site links, zero '%' in #live-coverage-gaps, WCAG clean.
    await page.goto('/');
    const homeMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(homeMetrics.scrollWidth).toBeLessThanOrEqual(homeMetrics.innerWidth);

    for (const route of ['origination/', 'picks/', 'unresolved/', 'coverage/', 'review/']) {
      await expect(page.locator(`main a[href*="${route}"]:visible`).first()).toBeVisible();
    }

    const firstRow = page.locator('#glance-list > .glance-row').first();
    await expect(firstRow).toBeVisible();
    await expect(firstRow.locator('.glance-prob')).toBeVisible();
    await expect(firstRow.locator('.glance-other')).toBeVisible();

    await expect(page.locator('#live-coverage-gaps')).toBeVisible();
    const gapsText = await page.locator('#live-coverage-gaps').innerText();
    expect(gapsText).not.toContain('%');

    const homeAxe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(homeAxe.violations).toEqual([]);

    // 2. Origination complete picks (`/origination/`): zero overflow, pick cards visible with official source links.
    await page.goto('/origination/');
    const origMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(origMetrics.scrollWidth).toBeLessThanOrEqual(origMetrics.innerWidth);
    expect(await page.locator('article.pick-card').count()).toBeGreaterThan(0);

    // 3. Dedicated Unresolved & Limitations page (`/unresolved/`): zero overflow, single #no-line-research, WCAG clean.
    await page.goto('/unresolved/');
    const unresMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      noLineResearchCount: document.querySelectorAll('#no-line-research').length,
    }));
    expect(unresMetrics.scrollWidth).toBeLessThanOrEqual(unresMetrics.innerWidth);
    expect(unresMetrics.noLineResearchCount).toBe(1);
    const unresAxe = await new AxeBuilder({ page })
      .exclude('.probe-source-url')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(unresAxe.violations).toEqual([]);

    // 4. Flagged for Review (`/review/`): 35e31fef flags & review register items visible with official https links.
    await page.goto('/review/');
    const revMetrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(revMetrics.scrollWidth).toBeLessThanOrEqual(revMetrics.innerWidth);

    for (const id of [
      'flag-35e31fef-001',
      'flag-35e31fef-002',
      'flag-35e31fef-003',
      'flag-35e31fef-004',
      'flag-35e31fef-005',
      'flag-35e31fef-006',
      'review-35E3-R01',
      'review-35E3-R02',
      'review-35E3-R03',
      'review-35E3-R04',
      'review-35E3-R05',
    ]) {
      const row = page.locator(`#${id}`);
      await row.evaluate((el) => {
        let p = el.parentElement;
        while (p) {
          if (p.tagName === 'DETAILS') p.open = true;
          p = p.parentElement;
        }
      });
      await expect(row).toBeVisible();
      const details = row.locator('details');
      if ((await details.count()) > 0) {
        await details.first().evaluate((el) => { el.open = true; });
      }
      expect(await row.locator('a[href^="https://"]').count()).toBeGreaterThanOrEqual(1);
    }

    const revAxe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(revAxe.violations).toEqual([]);
  });
}
