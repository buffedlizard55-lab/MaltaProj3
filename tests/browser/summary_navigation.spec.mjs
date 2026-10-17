// Dated generated fixture checks, not assertions about today's live inventory.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';

for (const width of [320, 390]) {
  test(`all summary pick entry points reach the complete feed on a ${width}px phone`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    const previewLink = page.locator('#next-matches-section .section-heading a');
    const heroLink = page.getByRole('link', { name: 'See all match picks' });
    const mobileLink = page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('link', { name: 'Picks', exact: true });
    for (const link of [previewLink, heroLink, mobileLink]) {
      await expect(link).toHaveAttribute('href', './origination/#picks');
    }
    await previewLink.click();
    await expect(page).toHaveURL(/\/origination\/#picks$/);
    const feed = JSON.parse(await fs.readFile('site/data/origination.json', 'utf8'));
    await expect(page.locator('.pick-card')).toHaveCount(feed.matches.length);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
  });
}

test('summary complete-pick and unresolved links work without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const page = await context.newPage();
    await page.goto('/');
    await page.locator('#next-matches-section .section-heading a').click();
    await expect(page).toHaveURL(/\/origination\/#picks$/);
    await expect(page.locator('.pick-card').first()).toBeVisible();
    await page.goto('/');
    await page.locator('[aria-label="Complete pick coverage"] a[href$="origination/#unresolved"]').click();
    await expect(page).toHaveURL(/\/origination\/#unresolved$/);
    await expect(page.locator('#unresolved')).toBeVisible();
  } finally {
    await context.close();
  }
});

test('coverage cadence includes catch-up slots and its official workflow on phones', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/coverage/');
  const cadence = page.locator('.coverage-summary');
  await expect(cadence).toContainText('02:47, 06:47, 10:47, 14:47, 18:47, 22:47 UTC');
  await expect(cadence).toContainText('may delay or drop runs');
  await expect(cadence.getByRole('link', { name: 'Official refresh workflow' })).toHaveAttribute('href', 'https://github.com/buffedlizard55-lab/MaltaProj3/blob/main/.github/workflows/pages.yml');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
  const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  expect(accessibility.violations).toEqual([]);
});
