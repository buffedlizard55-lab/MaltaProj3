import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const width of [320, 390, 768, 1440]) {
  test(`complete picks finder and navigation work at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/origination/');
    const rows = page.locator('.picks-table tbody tr');
    const total = await rows.count();
    expect(total).toBeGreaterThan(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();

    const mobileNav = page.getByRole('navigation', { name: 'Mobile picks navigation' });
    if (width < 720) {
      await expect(mobileNav).toBeVisible();
      await expect(mobileNav.locator('a')).toHaveCount(4);
      for (const link of await mobileNav.locator('a').all()) {
        expect((await link.boundingBox()).height).toBeGreaterThanOrEqual(44);
      }
      expect(parseFloat(await rows.first().locator('.tbl-prob').first().evaluate(el => getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
      const quick = page.locator('.quick a');
      const primary = await quick.nth(0).boundingBox();
      const second = await quick.nth(1).boundingBox();
      expect(primary.width).toBeGreaterThan(second.width * 1.5);
      await expect(quick.nth(1).locator('small')).toBeHidden();
    } else {
      await expect(mobileNav).toBeHidden();
    }
    for (const button of await page.locator('.filter-btn').all()) {
      expect((await button.boundingBox()).height).toBeGreaterThanOrEqual(44);
    }

    const first = rows.first();
    const group = await first.getAttribute('data-filter-group');
    const matchText = await first.locator('th a').innerText();
    const team = matchText.split(/\s+vs\s+/)[0];
    const input = page.getByRole('searchbox', { name: 'Find a team or tournament' });
    await page.locator(`.filter-btn[data-filter="${group}"]`).click();
    await input.fill(team);
    const visible = page.locator('.picks-table tbody tr:visible');
    expect(await visible.count()).toBeGreaterThan(0);
    for (const row of await visible.all()) {
      expect(await row.getAttribute('data-filter-group')).toBe(group);
      expect((await row.getAttribute('data-search')).includes(team.toLowerCase())).toBeTruthy();
    }

    await input.fill('no-such-team-be27c3f6');
    await expect(page.locator('.picks-table tbody tr:visible')).toHaveCount(0);
    await expect(page.locator('[data-picks-empty]')).toBeVisible();
    await expect(page.locator('[data-picks-status]')).toHaveText(`0 of ${total} matches shown.`);
    await page.getByRole('button', { name: 'Clear', exact: true }).click();
    await expect(page.locator('.picks-table tbody tr:visible')).toHaveCount(total);
    await expect(page.locator('.filter-btn[data-filter="all"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(input).toBeFocused();
    await expect(page.locator('#evidence-cards')).toContainText('repeat the same fixtures');

    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    expect(results.violations).toEqual([]);
  });
}

test.describe('complete picks without JavaScript', () => {
  test.use({ javaScriptEnabled: false });

  test('search enhancement never hides the source list', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 900 });
    await page.goto('/origination/');
    const rows = page.locator('.picks-table tbody tr');
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeGreaterThan(0);
    await expect(page.locator('[data-clear-picks]')).toBeHidden();
    await expect(page.locator('.mobile-quick')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  });
});
