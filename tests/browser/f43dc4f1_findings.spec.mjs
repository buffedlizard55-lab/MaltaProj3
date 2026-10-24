import { test, expect } from '@playwright/test';

/**
 * Session arena-f43dc4f1: the findings register on /review/ must be usable on a
 * phone. It is the longest page on the site (305 findings, 417 table rows,
 * ~1 MB of HTML on 2026-10-24) and had no way to find one finding inside it.
 *
 * The filter only hides rows: every row is rendered server-side and visible by
 * default, which is what the existing assertions on individual `#flag-…` rows
 * rely on. These checks therefore assert (a) nothing is hidden on load, (b) a
 * query that matches nothing hides everything and the count says so, (c) the
 * severity buttons narrow to exactly the rows carrying that severity, and
 * (d) the page still does not scroll sideways at 320 px.
 */
for (const width of [320, 390]) {
  test(`findings register is searchable and fits at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/review/');

    const rows = page.locator('#findings table tbody tr');
    const total = await rows.count();
    expect(total).toBeGreaterThan(50);

    // Nothing is hidden before the reader filters anything.
    await expect(page.locator('#findings tbody tr[style]')).toHaveCount(0);
    await expect(page.locator('#finding-count')).toContainText(`${total} findings`);

    // A query that cannot match hides every row and says how many are shown.
    await page.fill('#finding-search', 'zzzz-no-such-finding');
    await expect(page.locator('#findings tbody tr:visible')).toHaveCount(0);
    await expect(page.locator('#finding-count')).toContainText('0 of');

    // Clearing the query restores every row.
    await page.fill('#finding-search', '');
    await expect(page.locator('#findings tbody tr:visible')).toHaveCount(total);

    // Each severity button narrows to exactly the rows carrying that severity.
    for (const severity of ['notice', 'review']) {
      const expected = await page.locator(`#findings tbody tr[data-finding-severity="${severity}"]`).count();
      await page.getByRole('button', { name: new RegExp(`^${severity === 'notice' ? 'Notice' : 'Needs review'}`) }).click();
      await expect(page.locator('#findings tbody tr:visible')).toHaveCount(expected);
      await expect(page.locator(`#finding-count`)).toContainText(`${expected} of ${total}`);
    }
    await page.getByRole('button', { name: /^All/ }).click();
    await expect(page.locator('#findings tbody tr:visible')).toHaveCount(total);

    // The one-tap destination the brief asks about still reaches the picks.
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
    }));
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.innerWidth);
  });
}
