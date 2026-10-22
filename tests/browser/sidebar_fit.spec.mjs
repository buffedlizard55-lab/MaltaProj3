import { test, expect } from '@playwright/test';

/* The sidebar's last link must stay inside the painted sidebar on a laptop.
 *
 * On 2026-10-22 the desktop accessibility scan failed on every page at 1440px:
 * "insufficient color contrast of 2.23 (foreground #96aab8, background #f4f7f8)"
 * for `.sidebar-repo`. The colour pair is fine on navy (about 6.4:1); axe was
 * reporting the page background because the link had overflowed the fixed
 * sidebar and was painted below the viewport, outside the sidebar's own box.
 * At 1440x844 the link sat at y=860 while the sidebar ended at 844, so it could
 * not be reached at all.
 *
 * These checks keep the fix honest: the sidebar scrolls when it cannot fit, and
 * on the standard laptop viewport its last link is inside the sidebar and above
 * the fold.
 */

for (const [width, height] of [[1440, 844], [1024, 844], [768, 844]]) {
  test(`the last sidebar link stays inside the sidebar at ${width}x${height}`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.goto('/');
    const box = await page.locator('.sidebar').boundingBox();
    const repo = await page.locator('.sidebar-repo').boundingBox();
    expect(box).not.toBeNull();
    expect(repo).not.toBeNull();
    expect(repo.y).toBeGreaterThanOrEqual(box.y);
    expect(repo.y + repo.height).toBeLessThanOrEqual(box.y + box.height + 1);
    expect(repo.y + repo.height).toBeLessThanOrEqual(height);
  });
}

test('a short viewport scrolls the sidebar instead of hiding its last link', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 600 });
  await page.goto('/');
  const overflow = await page.locator('.sidebar').evaluate(node => getComputedStyle(node).overflowY);
  expect(overflow).toBe('auto');
  await page.locator('.sidebar-repo').scrollIntoViewIfNeeded();
  await expect(page.locator('.sidebar-repo')).toBeVisible();
});
