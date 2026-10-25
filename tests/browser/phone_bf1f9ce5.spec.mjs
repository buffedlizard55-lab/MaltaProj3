import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 640 },
  { name: 'iphone-390', width: 390, height: 844 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'desktop-1440', width: 1440, height: 900 },
];

for (const vp of VIEWPORTS) {
  test(`bf1f9ce5 executive summary, unresolved register, and review layout at ${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height });

    for (const route of ['/', '/origination/', '/unresolved/', '/review/']) {
      const resp = await page.goto(route);
      expect(resp?.status(), `HTTP status for ${route}`).toBe(200);

      if (route === '/') {
        await expect(page.locator('#unresolved-register')).toBeVisible();
        await expect(page.locator('#no-line-register')).toBeVisible();

        const picksLink = page.locator('main a[href="./origination/#picks"]:visible').first();
        await expect(picksLink).toBeVisible();
        const box = await picksLink.boundingBox();
        expect(box).not.toBeNull();
        expect(box.height).toBeGreaterThanOrEqual(24);
        expect(box.width).toBeGreaterThanOrEqual(40);
      }

      if (route === '/origination/') {
        const pickBadges = page.locator('#picks .pick, #picks [class*="pick"]');
        expect(await pickBadges.count()).toBeGreaterThan(0);
        const pageText = await page.locator('main').innerText();
        expect(pageText).toMatch(/\d+\.\d%/);
      }

      if (route === '/review/') {
        const archiveSummary = page.locator('details#dated-registers > summary');
        if ((await archiveSummary.count()) > 0) {
          await expect(archiveSummary).toBeVisible();
          await archiveSummary.click();
        }
        await expect(page.locator('#review-BF1F-R01')).toBeVisible();
      }

      const overflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth - window.innerWidth;
      });
      expect(overflow, `horizontal overflow on ${route} at ${vp.width}px`).toBeLessThanOrEqual(1);
    }
  });
}
