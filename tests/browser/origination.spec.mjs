import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const width of [320, 390, 768, 1440]) {
  test(`originated picks are readable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 });
    await page.goto('/origination/');
    await expect(page.locator('h1')).toHaveText(/Hotspawn CS2 match picks/);
    await expect(page.locator('#unresolved')).toContainText('Unresolved picks');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.locator('.quick a[href="#picks"]').click();
    await expect(page).toHaveURL(/#picks$/);
    await page.locator('.pick-card details').first().locator('summary').click();
    await expect(page.locator('.pick-card details').first()).toHaveAttribute('open', '');
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect(results.violations).toEqual([]);
  });
}

test('summary exposes the additional researched picks and limitations', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Briefing shortcuts' })
    .getByRole('link', { name: 'Complete researched picks' }).click();
  await expect(page).toHaveURL(/origination\/#picks$/);
  await expect(page.locator('.pick-card').first()).toBeVisible();
});
