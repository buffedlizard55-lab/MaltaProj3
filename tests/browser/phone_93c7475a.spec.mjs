import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import { python } from './python.mjs';

// Session arena-93c7475a — the separate unresolved-picks section, on a phone.
//
// The brief asks for a separate section listing the picks that could not be
// resolved the way the featured picks are, with the limitations of generating
// them, reachable from the executive summary and readable on a phone. The
// renderer existed but was never wired in; these are layout and link facts, so
// they are asserted in a browser rather than in CSS unit tests.
//
// The page under test is a fixture site built with a pinned clock and a dossier
// dated at that clock (see unresolved_research_fixture.py), because the real
// site correctly skips a stale dossier and would render no section at all.
const BASE = '/_fixture/93c7475a/';   // built with a pinned clock: 2026-10-25T15:00:00Z

test.beforeAll(() => {
  execFileSync(python(), ['tests/browser/unresolved_research_fixture.py'], { stdio: 'inherit' });
});

test.afterAll(() => {
  fs.rmSync('site/_fixture/93c7475a', { recursive: true, force: true });
});

// No frozen clock here: the fixture site is built with a pinned build time, and
// installing a fake clock stops `scroll-behavior: smooth` from ever progressing,
// which made a cross-page fragment link look broken when it is not.

for (const width of [320, 390, 768, 1440]) {
  test(`the research dossier is readable with no page overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(BASE + 'unresolved/');
    await expect(page.locator('#unresolved-research')).toBeVisible();
    await expect(page.locator('#unresolved-limitations')).toBeVisible();

    // The page itself must never scroll sideways; a wide table scrolls inside
    // its own wrapper instead of pushing the layout past the viewport.
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, 'no horizontal page overflow').toBeLessThanOrEqual(1);

    const clipped = await page.locator('#unresolved-research').evaluate(el => {
      const limit = window.innerWidth + 1;
      return [...el.querySelectorAll('th, td, a, h2, h3')]
        .filter(n => {
          const r = n.getBoundingClientRect();
          return (r.width > 0 && (r.right > limit || r.left < -1));
        })
        .slice(0, 5)
        .map(n => n.textContent.trim().slice(0, 40));
    });
    expect(clipped, 'every cell and link stays inside the viewport').toEqual([]);

    // One row per researched fixture, each naming both teams.
    const rows = page.locator('#unresolved-research tbody tr');
    await expect(rows).toHaveCount(2);
    await expect(rows.nth(0)).toContainText('BESTIA');
    await expect(rows.nth(1)).toContainText('BORRACHEIROS');

    // Every source in the section is an https link; nothing is a bare hostname.
    const links = await page.locator('#unresolved-research a, #unresolved-limitations a').evaluateAll(
      els => els.map(a => a.getAttribute('href')));
    for (const href of links) {
      expect(href.startsWith('https://'), `source link must be absolute https: ${href}`).toBe(true);
    }
    expect(errors, 'no page errors').toEqual([]);
  });
}

test('the executive summary reaches the section in one tap', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(BASE);
  const link = page.locator('.unresolved-research-line a').first();
  await expect(link).toBeVisible();
  const href = await link.getAttribute('href');
  expect(href).toContain('unresolved/#unresolved-research');

  // The tap target must be a real size, and the anchor must resolve to the
  // section rather than to the top of the page.
  const box = await link.boundingBox();
  expect(box.height, 'a tappable link').toBeGreaterThanOrEqual(18);
  await link.click();
  await page.waitForURL('**/unresolved/**');
  await expect(page.locator('#unresolved-research')).toBeVisible();
  // The browser scrolls to the fragment after load, so poll rather than measure
  // once: a smooth scroll has not finished on the first frame.
  await expect
    .poll(async () => Math.abs(await page.locator('#unresolved-research')
      .evaluate(el => el.getBoundingClientRect().top)),
      { message: 'the anchor must land on the section, not the page top', timeout: 10000 })
    .toBeLessThan(200);
});

test('the summary states how many fixtures stay blank and how many are pending', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(BASE);
  const line = page.locator('.unresolved-research-line');
  await expect(line).toContainText('2 fixture');
  await expect(line).toContainText('1 stay blank');
  await expect(line).toContainText('1 expected at the next refresh');
});

test('the section meets WCAG A/AA at a phone width', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(BASE + 'unresolved/');
  const results = await new AxeBuilder({ page })
    .include('#unresolved-research')
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  expect(results.violations.map(v => `${v.id}: ${v.help}`)).toEqual([]);
});
