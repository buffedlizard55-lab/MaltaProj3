// Session arena-5fbf5cd5 — the phone must reach a pick without hunting.
//
// These checks render the real built site and measure what a person sees at
// 320 px and 390 px: the one-tap picks action, the order of the blocks, the
// separate unresolved page, and a11y. They assert structure and reachability,
// never a probability or a pick value.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const width of [320, 390]) {
  test(`the picks action is above the first pick row on a ${width}px phone`, async ({ page }) => {
    await page.setViewportSize({ width, height: 760 });
    await page.goto('/');
    const action = page.locator('.exec-banner > a.primary');
    await expect(action).toBeVisible();
    await expect(action).toHaveAttribute('href', './origination/#picks');
    const [actionBox, firstRow] = await Promise.all([
      action.boundingBox(),
      page.locator('#picks-at-a-glance .glance-row').first().boundingBox(),
    ]);
    expect(actionBox).not.toBeNull();
    expect(firstRow).not.toBeNull();
    expect(actionBox.y).toBeLessThan(firstRow.y);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
  });

  test(`summary block order is banner, picks, register on a ${width}px phone`, async ({ page }) => {
    await page.setViewportSize({ width, height: 760 });
    await page.goto('/');
    const tops = [];
    for (const selector of ['.exec-banner', '#picks-at-a-glance', '#unresolved-register', '#start-here']) {
      const box = await page.locator(selector).first().boundingBox();
      expect(box, selector).not.toBeNull();
      tops.push(box.y);
    }
    expect(tops).toEqual([...tops].sort((a, b) => a - b));
  });

  test(`the unresolved page is one tap from the summary on a ${width}px phone`, async ({ page }) => {
    await page.setViewportSize({ width, height: 760 });
    await page.goto('/');
    const link = page.locator('.exec-banner a[href="./unresolved/"]');
    await expect(link).toBeVisible();
    const box = await link.boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
    await link.click();
    await expect(page).toHaveURL(/\/unresolved\/$/);
    await expect(page.locator('#unresolved-register')).toBeVisible();
    await expect(page.locator('#source-ladder')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
  });
}

test('the unresolved page works without JavaScript and states its rules', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const page = await context.newPage();
    await page.goto('/unresolved/');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Unresolved picks');
    await expect(page.locator('#source-ladder')).toBeVisible();
    const rules = (await page.locator('#unresolved-rules').innerText()).toLowerCase();
    expect(rules).toContain('% picked');
    expect(rules).toContain('never fills a missing value');
  } finally {
    await context.close();
  }
});

test('every mobile bar destination resolves, including unresolved picks', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const bar = page.getByRole('navigation', { name: 'Mobile navigation' });
  await expect(bar.getByRole('link', { name: 'Unresolved', exact: true })).toHaveAttribute('href', './unresolved/');
  for (const label of ['Summary', 'Picks', 'Unresolved', 'Sources', 'Methods', 'Review']) {
    const link = bar.getByRole('link', { name: label, exact: true });
    await expect(link).toBeVisible();
    const box = await link.boundingBox();
    expect(box.height, `${label} touch target`).toBeGreaterThanOrEqual(44);
  }
  await bar.getByRole('link', { name: 'Unresolved', exact: true }).click();
  await expect(page).toHaveURL(/\/unresolved\/$/);
  await expect(page.locator('nav.mobile-nav a[aria-current="page"]')).toHaveText('Unresolved');
});

test('the unresolved page passes the same accessibility route as the rest of the site', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/unresolved/');
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);
});

test('model-backed picks are visibly distinct from bookmaker-backed picks', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/unresolved/');
  const section = page.locator('#research-only');
  await expect(section).toBeVisible();
  await expect(section).toContainText('never presented as a betting line');
  const badges = await section.locator('tbody .badge').allTextContents();
  expect(badges.length).toBeGreaterThan(0);
  for (const badge of badges) {
    expect(['Research model', 'Low confidence']).toContain(badge.trim());
  }
});
