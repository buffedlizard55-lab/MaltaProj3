import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';

// Session arena-5927ab83: audit EVERY row of the complete-picks feed, not just
// the first card. Values are compared with the generated feed; the test never
// creates a pick, probability or source. It runs against the deterministic
// repository fixture in CI and against any freshly built site unchanged.
const feed = JSON.parse(await fs.readFile('site/data/origination.json', 'utf8'));
const moneyMethods = new Set(['market', 'bookmaker', 'consensus', 'reference']);

for (const width of [320, 390]) {
  test(`every complete pick is readable and source-linked on a ${width}px phone`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');

    const rows = page.locator('#glance-list .glance-row');
    await expect(rows).toHaveCount(feed.matches.length);

    for (const match of feed.matches) {
      const row = page.locator(`#glance-list .glance-row[data-glance-id="${match.id}"]`);
      await expect(row, `Hotspawn ${match.id} appears exactly once`).toHaveCount(1);
      const teams = match.teams.map(team => team.name);
      await expect(row.locator('.glance-match strong')).toContainText(teams[0]);
      await expect(row.locator('.glance-match strong')).toContainText(teams[1]);
      await expect(row.locator('a', { hasText: 'Full detail' }))
        .toHaveAttribute('href', `./origination/#match-${match.id}`);
      expect(await row.locator('.glance-links a[href^="https://"]').count(),
        `${match.id} has an external official-source link`).toBeGreaterThan(0);

      const estimate = match.origination;
      if (estimate && Array.isArray(estimate.probabilities) && match.pick_index !== null) {
        const pick = match.pick_index;
        await expect(row.locator('.glance-choice > strong')).toHaveText(teams[pick]);
        const primaryText = await row.locator('.glance-prob').innerText();
        const otherText = await row.locator('.glance-other').innerText();
        const primary = Number(primaryText.match(/([\d.]+)%/)[1]);
        const other = Number(otherText.match(/([\d.]+)%/)[1]);
        expect(Math.abs(primary - estimate.probabilities[pick] * 100),
          `${match.id} pick probability replays from the feed`).toBeLessThanOrEqual(0.051);
        expect(Math.abs(other - estimate.probabilities[1 - pick] * 100),
          `${match.id} opponent probability replays from the feed`).toBeLessThanOrEqual(0.051);
        expect(Math.abs(primary + other - 100)).toBeLessThanOrEqual(0.11);
      } else {
        await expect(row.locator('.unresolved-text')).toHaveCount(1);
      }

      if (!estimate || !moneyMethods.has(estimate.method)) {
        const limitation = page.locator(`#no-line-register #no-line-${match.id}`);
        await expect(limitation, `${match.id} has a separate no-line limitation`).toHaveCount(1);
        await expect(limitation).toContainText('Why no line:');
        await expect(limitation.locator('a', { hasText: 'Evidence & sources' }))
          .toHaveAttribute('href', `./unresolved/#no-line-${match.id}`);
      }
    }

    expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(width + 1);
    await expect(page.locator('#unresolved-register')).toBeVisible();
    await expect(page.locator('#no-line-research')).toHaveCount(1);
  });
}
