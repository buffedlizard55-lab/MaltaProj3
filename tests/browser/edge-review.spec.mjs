import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import { python } from './python.mjs';

/* The Day-4 refresh must stay readable on a phone: this is the page a user opens at 14:00 UTC to
   decide a card, so a horizontally clipped table or a percentage that only exists in JSON is a
   defect, not a cosmetic issue. */
const FIXTURE = '/_edge_review_fixture/';
const manifest = () => JSON.parse(fs.readFileSync('site/_edge_review_fixture/manifest.json', 'utf8'));

test.beforeAll(() => {
  execFileSync(python(), ['tests/browser/edge_review_fixture.py'], { stdio: 'inherit' });
});
test.afterAll(() => fs.rmSync('site/_edge_review_fixture', { recursive: true, force: true }));

for (const width of [320, 390, 768, 1440]) {
  test(`group stage, refresh, score slip and day-five card fit and agree with the data at ${width}px`, async ({ page }) => {
    const expected = manifest();
    await page.clock.install({ time: new Date('2026-10-17T06:00:00Z') });
    await page.setViewportSize({ width, height: 900 });
    await page.goto(FIXTURE);

    await expect(page.locator('#group-stage-record')).toBeVisible();
    await expect(page.locator('#day-four-refresh')).toBeVisible();
    await expect(page.locator('#score-slip')).toBeVisible();
    await expect(page.locator('#day-five-card')).toBeVisible();

    // Row counts are the data's row counts, so a dropped series cannot hide behind a fixed number.
    await expect(page.locator('#group-stage-series tbody tr')).toHaveCount(expected.group_series);
    await expect(page.locator('#group-stage-load tbody tr')).toHaveCount(4);
    await expect(page.locator('#day-four-refresh tbody tr')).toHaveCount(expected.refresh_rows);
    await expect(page.locator('#day-five-matches tbody tr')).toHaveCount(expected.day_five_rows);
    await expect(page.locator('#day-five-recap tbody tr')).toHaveCount(expected.day5_semifinal_rows);
    await expect(page.locator('#day-four-guidance li')).toHaveCount(expected.guidance_principles);

    // Displayed percentages are exactly the recorded, normalised readings - in order, on every width.
    const shown = await page.locator('#day-four-refresh .prob-line strong').allInnerTexts();
    expect(shown.map(t => t.trim())).toEqual(expected.displayed_probabilities.map(x => x.text));
    for (const entry of expected.displayed_probabilities) {
      await expect(page.locator('#day-four-refresh .prob-line').filter({ hasText: entry.team })).toContainText(entry.text);
    }

    // Unpriced fields stay visibly blank and no 50/50 fallback may appear anywhere in that section.
    const dayFive = await page.locator('#day-five-card').innerText();
    expect(dayFive).toContain('— unverified');
    expect(dayFive).not.toMatch(/50\.0%/);
    // Every resolved row shows its default pick and the label that keeps the
    // fallback estimate from being mistaken for betting odds.
    for (const pick of expected.day_five_picks) {
      expect(dayFive).toContain(pick);
    }
    expect(dayFive).toContain('Valve-model fallback');
    await expect(page.locator('#day-five-market-scan')).toBeVisible();
    await expect(page.locator('#day-five-guidance li')).toHaveCount(expected.day5_guidance_principles);

    // Nothing may force the document sideways; wide tables scroll inside their own wrapper.
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const scroller = page.locator('#group-stage-series').locator('xpath=ancestor::*[contains(@class,"table-scroll")][1]');
    expect(await scroller.evaluate(el => getComputedStyle(el).overflowX)).toBe('auto');
    expect(await scroller.evaluate(el => el.scrollWidth >= el.clientWidth)).toBe(true);

    // Every row of the verified record is anchored to its own official page - not just "an" HLTV link,
    // but the match page for that series, in the same order as the data.
    const rows = await page.locator('#group-stage-series tbody tr').all();
    expect(rows).toHaveLength(expected.series_urls.length);
    for (const [index, row] of rows.entries()) {
      const link = row.locator(`a[href="${expected.series_urls[index]}"]`);
      await expect(link.first()).toBeVisible();
      expect(await link.count()).toBeGreaterThanOrEqual(1);
    }
  });
}

test('the refresh reads as dated research with no JavaScript and at 320px', async ({ browser }) => {
  const expected = manifest();
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 900 } });
  const page = await context.newPage();
  await page.goto(FIXTURE);
  await expect(page.locator('#day-four-refresh .prob-line strong')).toHaveText(
    expected.displayed_probabilities.map(x => x.text));
  await expect(page.locator('#group-stage-series tbody tr')).toHaveCount(expected.group_series);
    await expect(page.locator('#group-stage-load tbody tr')).toHaveCount(4);
  // The section says out loud that it is dated research, not a live feed, and that one provider is not consensus.
  const intro = await page.locator('#day-four-refresh').innerText();
  // innerText follows the CSS text-transform on the eyebrow, so compare case-insensitively.
  expect(intro.toLowerCase()).toContain('dated refresh');
  expect(intro).toContain('One provider only');
  expect(intro.toLowerCase()).toContain('not consensus');
  // A provider field this session did not read is published as blank rather than as a plausible id.
  if (expected.single_provider_notes) {
    expect(await page.locator('#day-four-refresh').innerText()).toContain('not re-read: blank');
  }
  await expect(page.locator('#edge-refresh-note')).toBeVisible();
  await expect(page.locator('#edge-limitations li')).not.toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await context.close();
});

test('the new sections pass an automated accessibility scan at phone width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto(FIXTURE);
  const results = await new AxeBuilder({ page }).include('#group-stage-record').include('#day-four-refresh')
    .include('#score-slip').include('#day-five-card').include('#day-four-guidance').analyze();
  expect(results.violations).toEqual([]);
});
