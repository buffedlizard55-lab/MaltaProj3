/* Session arena-3a010437: the dated re-read must be reachable and readable on a phone.

Measured on the built site at 390 x 844 and 320 x 720 in Chromium:

* the executive-summary strip and the coverage-page table both render inside a
  valid section — never nested inside another table (that happened once when the
  section was appended before the ledger's closing tags);
* the strip's one in-prose link to the row-by-row record is a 44 px target;
* the page never scrolls horizontally;
* every row of the table still shows team names, both probabilities and a
  source link.

The site is built by the suite's own build step (see ``tests/browser/python.mjs``
usage elsewhere), so this test reads whatever ``site/`` currently contains; it
asserts structure, not values. */
import { test, expect } from '@playwright/test';

const PHONES = [
  { name: 'iPhone 12-ish', width: 390, height: 844 },
  { name: 'small Android', width: 320, height: 720 },
];

for (const { name, width, height } of PHONES) {
  test.describe(`dated re-read on ${name}`, () => {
    test.use({ viewport: { width, height } });

    test('executive-summary strip renders, is tappable and does not overflow', async ({ page }) => {
      await page.goto('/index.html', { waitUntil: 'networkidle' });
      const section = page.locator('#independent-verification');
      await expect(section).toHaveCount(1);
      // Not nested inside a table cell or another section of the same id.
      const nested = await section.evaluate((el) => Boolean(el.closest('td')) || el.parentElement.tagName === 'TBODY');
      expect(nested).toBe(false);
      const link = section.locator('a.internal-link', { hasText: 'Row-by-row record' });
      await expect(link).toHaveCount(1);
      const box = await link.boundingBox();
      expect(Math.round(box.height)).toBeGreaterThanOrEqual(44);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(0);
    });

    test('coverage table keeps every published row readable', async ({ page }) => {
      await page.goto('/coverage/index.html', { waitUntil: 'networkidle' });
      const section = page.locator('#independent-verification');
      await expect(section).toHaveCount(1);
      const rows = section.locator('tbody tr');
      const count = await rows.count();
      expect(count).toBeGreaterThan(0);
      for (let index = 0; index < count; index += 1) {
        const row = rows.nth(index);
        // Each row has the match, the published pick, identity and a source link.
        await expect(row.locator('th')).toHaveCount(1);
        await expect(row.locator('td')).toHaveCount(4);
        const links = await row.locator('a').count();
        expect(links).toBeGreaterThan(0);
      }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(0);
    });
  });
}
