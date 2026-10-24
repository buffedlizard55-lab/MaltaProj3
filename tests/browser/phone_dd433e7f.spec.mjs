import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 568 },
  { name: 'modern-phone-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'desktop-1440', width: 1440, height: 900 },
];

for (const vp of VIEWPORTS) {
  test(`dd433e7f mobile/desktop executive summary, unresolved & flagged-for-review at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });

    // 1. Executive Summary (`/`): zero horizontal overflow, single #no-line-research at most,
    //    both-team probabilities visible on phone, clear internal links, WCAG 2A/2AA clean.
    await page.goto('/');
    const homeBox = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      noLineResearchCount: document.querySelectorAll('#no-line-research').length,
    }));
    expect(homeBox.scrollWidth).toBeLessThanOrEqual(homeBox.innerWidth);
    expect(homeBox.noLineResearchCount).toBeLessThanOrEqual(1);

    for (const route of ['origination/', 'picks/', 'unresolved/', 'coverage/', 'review/']) {
      await expect(page.locator(`main a[href*="${route}"]:visible`).first()).toBeVisible();
    }

    const firstOpenRow = page.locator('.glance-row[data-glance-closed="false"], .glance-row').first();
    await expect(firstOpenRow).toBeVisible();
    await expect(firstOpenRow.locator('.glance-prob')).toBeVisible();
    await expect(firstOpenRow.locator('.glance-other')).toBeVisible();
    await expect(page.locator('#unresolved-register, #unresolved').first()).toBeVisible();
    await expect(page.locator('#no-line-register')).toBeVisible();

    const homeAxe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(homeAxe.violations).toEqual([]);

    // 2. Unresolved & Limitations (`/unresolved/`): zero overflow, single #no-line-research, WCAG clean.
    await page.goto('/unresolved/');
    const unresBox = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      noLineResearchCount: document.querySelectorAll('#no-line-research').length,
    }));
    expect(unresBox.scrollWidth).toBeLessThanOrEqual(unresBox.innerWidth);
    expect(unresBox.noLineResearchCount).toBe(1);

    const unresAxe = await new AxeBuilder({ page })
      .exclude('.probe-source-url')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(unresAxe.violations).toEqual([]);

    // 3. Flagged for Review (`/review/`): dd433e7f flags & line-by-line review rows carry official https links.
    await page.goto('/review/');
    const revBox = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(revBox.scrollWidth).toBeLessThanOrEqual(revBox.innerWidth);

    for (const id of [
      'flag-dd433e7f-hltv-25-active-verified-no-us-odds',
      'flag-dd433e7f-wide-polymarket-and-smarkets-books-refused',
      'review-DD43-R01',
      'review-DD43-R02',
      'review-DD43-R03',
      'review-DD43-R04',
      'review-DD43-R05',
      'review-DD43-R06',
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
