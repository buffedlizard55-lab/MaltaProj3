import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

// E474-1 (arena-e4744710): phone-readability measurements for the published
// pages. Runs against the built site (default web server) and, when
// PREVIEW_BASE_URL is set, against any other served copy of the same build
// (the deployed branch-root HTML was measured this way). Measurements are
// written to data/research/e4744710/ only when E474_OUT is set, so the suite
// stays side-effect free in CI.

const PAGES = ['/', '/picks/', '/origination/', '/unresolved/', '/review/', '/methodology/'];
const WIDTHS = [320, 390];
const results = [];

async function measure(page, url, width) {
  await page.setViewportSize({ width, height: 800 });
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  const m = await page.evaluate(() => {
    const de = document.documentElement;
    const nav = document.querySelector('.mobile-nav, nav[aria-label="Mobile navigation"]');
    const targets = nav ? [...nav.querySelectorAll('a')].map((a) => {
      const r = a.getBoundingClientRect();
      return { h: Math.round(r.height), w: Math.round(r.width) };
    }) : [];
    return {
      scrollWidth: de.scrollWidth,
      innerWidth: window.innerWidth,
      overflow: de.scrollWidth - window.innerWidth,
      navTargets: targets,
      glanceRows: document.querySelectorAll('.glance-row').length,
      hasGlance: !!document.getElementById('picks-at-a-glance'),
      hasUnresolved: !!document.getElementById('unresolved-register'),
      snapshot: de.querySelector('[data-snapshot-generated]')?.getAttribute('data-snapshot-generated') || document.querySelector('[data-snapshot-generated]')?.getAttribute('data-snapshot-generated') || null,
    };
  });
  results.push({ url, width, ...m });
  return m;
}

test('deployed pages have no horizontal overflow at 320 and 390 px', async ({ page }) => {
  for (const url of PAGES) {
    for (const width of WIDTHS) {
      const m = await measure(page, url, width);
      expect(m.overflow, `${url} @${width}px overflows by ${m.overflow}px`).toBeLessThanOrEqual(0);
    }
  }
});

test('executive summary offers a one-tap route to the picks on phone', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  // In-site links to the updated list of picks must exist on the summary.
  const hrefs = await page.$$eval('a', (as) => as.map((a) => a.getAttribute('href') || ''));
  expect(hrefs.some((h) => h.includes('origination/#picks') || h.includes('#picks-at-a-glance') || h.endsWith('/picks/'))).toBe(true);
  expect(hrefs.some((h) => h.includes('unresolved'))).toBe(true);
  // The glance section must carry at least one fixture row.
  await expect(page.locator('#picks-at-a-glance')).toHaveCount(1);
  expect(await page.locator('.glance-row').count()).toBeGreaterThan(0);
  // Mobile navigation landmark present with tap targets >= 44 px high.
  const nav = page.locator('.mobile-nav a');
  expect(await nav.count()).toBeGreaterThanOrEqual(4);
  for (let i = 0; i < await nav.count(); i += 1) {
    const box = await nav.nth(i).boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
  }
});

test.afterAll(() => {
  if (process.env.E474_OUT && results.length) {
    const out = path.resolve(process.env.E474_OUT);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    const payload = {
      measured_at: new Date().toISOString(),
      base: process.env.PREVIEW_BASE_URL || 'local-webserver',
      results,
    };
    fs.writeFileSync(out, JSON.stringify(payload, null, 2));
  }
});
