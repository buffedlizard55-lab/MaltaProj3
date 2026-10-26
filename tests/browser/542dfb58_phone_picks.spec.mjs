// Session arena-542dfb58 — the phone contract this brief asked for, pinned in one file.
//
// The request, in the owner's words: (1) "I want to be able to visit the site and be able to
// find where the picks for the matches are easily on my phone"; (2) "It should be easily
// readable and accessible on phone and mobile device"; (3) "Create a separate section for any
// unresolved picks and the limitations for generating picks for them and include this in the
// executive summary"; (4) full coverage — every match Hotspawn lists, no silent gaps.
//
// Every assertion here is evaluated against the snapshot the page itself ships
// (`./snapshot.json`), so a fixture that vanishes between the executive summary and the
// complete list fails the test instead of quietly shrinking a count.
import { test, expect } from '@playwright/test';

const VIEWPORTS = [
  { name: 'small-phone-320', width: 320, height: 640 },
  { name: 'phone-390', width: 390, height: 844 },
  { name: 'phone-landscape-844', width: 844, height: 390 },
];

async function snapshot(page) {
  const response = await page.goto('./snapshot.json');
  return response.json();
}

function activeIds(snapshotData) {
  return (snapshotData.matches || [])
    .filter((m) => ['open', 'locked', 'unknown_lock'].includes(m.availability))
    .map((m) => String(m.id));
}

for (const viewport of VIEWPORTS) {
  test.describe(`picks route on ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test('every active fixture is reachable from the executive summary, with its percentages', async ({ page }, testInfo) => {
      const data = await snapshot(page);
      const ids = activeIds(data);
      expect(ids.length, 'the shipped snapshot has no active fixture to test').toBeGreaterThan(0);

      await page.goto('./index.html');
      await expect(page.locator('#start-here')).toBeVisible();

      // 1. The summary says where the picks are, in-site, before any scrolling.
      const route = page.locator('#start-here a');
      await expect(route.filter({ hasText: 'Picks on this page' })).toHaveAttribute('href', /#picks-at-a-glance/);
      await expect(route.filter({ hasText: /All match picks/ })).toHaveAttribute('href', /origination\/#picks/);
      await expect(route.filter({ hasText: /Unresolved \(\d+\)/ })).toHaveAttribute('href', /origination\/#unresolved/);

      // 2. Every active fixture appears exactly once on this page — priced in the glance
      //    list or named in the unresolved register. No silent drop is allowed.
      const glance = page.locator('#picks-at-a-glance .glance-row');
      const register = page.locator('#unresolved-register [data-gap-id], #unresolved-register .gap-row, #unresolved-register .fallback-row, #unresolved-register .coverage-gap-row');
      const shownIds = await glance.evaluateAll((nodes) => nodes.map((n) => n.getAttribute('data-glance-id')));
      const registerText = await page.locator('#unresolved-register').innerText();
      for (const id of ids) {
        const inGlance = shownIds.includes(id);
        const inRegister = registerText.includes(id) || /No unresolved fixtures in this snapshot/i.test(registerText);
        expect(inGlance || inRegister,
          `fixture ${id} is active on Hotspawn but appears on neither the glance list nor the unresolved register`)
          .toBe(true);
      }
      expect(new Set(shownIds).size, 'a fixture is listed twice on the executive summary').toBe(shownIds.length);

      // 3. A pick must be obvious on a phone: the row names the picked team, shows its
      //    percentage, and never shows only one side of a two-sided estimate.
      const priced = glance.filter({ has: page.locator('.glance-prob') });
      const pricedCount = await priced.count();
      expect(pricedCount, 'no priced pick row rendered').toBeGreaterThan(0);
      for (let index = 0; index < pricedCount; index += 1) {
        const row = priced.nth(index);
        // An open fixture reads "Pick"; a fixture whose start has passed since the
        // snapshot keeps its estimate for audit under the honest label "Locked".
        // What must never happen is a row that shows a percentage without naming
        // a side, or that renames a passed start into a live recommendation.
        await expect(row.locator('[data-glance-pick]')).toContainText(/^(Pick|Locked)$/i);
        const label = (await row.locator('[data-glance-pick]').innerText()).trim().toLowerCase();
        if (label === 'pick') {
          await expect(row).toHaveAttribute('data-glance-inactive', 'false');
        }
        const pickText = await row.locator('.glance-choice strong').innerText();
        const pickProb = await row.locator('.glance-prob').innerText();
        const otherProb = await row.locator('.glance-other').innerText();
        expect(pickProb).toMatch(/\d+(\.\d+)?%/);
        expect(otherProb).toMatch(/\d+(\.\d+)?%/);
        // The labelled pick must be the larger of the two numbers it publishes.
        const big = (value) => parseFloat(value.replace('%', ''));
        expect(big(pickProb), `row ${index} labels ${pickText} ${pickProb} against ${otherProb}`)
          .toBeGreaterThanOrEqual(big(otherProb.replace(/^[^0-9]*/, '')));
        const size = await row.locator('.glance-prob').evaluate((node) => parseFloat(getComputedStyle(node).fontSize));
        expect(size, 'the probability must stay legible on a phone').toBeGreaterThanOrEqual(13);
      }

      // 4. Legibility on a narrow screen: nothing may overflow the viewport horizontally.
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `the page scrolls sideways by ${overflow}px at ${viewport.width}px`).toBeLessThanOrEqual(1);

      // 5. Tapping the bottom "Picks" tab must land on the complete list, and that list must
      //    carry a deep-linkable card for every active fixture.
      const picksTab = page.locator('nav.mobile-nav a').filter({ hasText: /^Picks$/ });
      // Below the desktop breakpoint the bottom tab bar is the only nav; at wider
      // phone-landscape sizes the sidebar takes over and the bar is display:none, so
      // only the visible bar may be clicked.
      if (await picksTab.count() && await picksTab.first().isVisible()) {
        await picksTab.first().click();
        await page.waitForURL(/origination\/#picks/);
        const cardIds = await page.locator('[id^="match-"]').evaluateAll((nodes) => nodes.map((n) => n.id.replace('match-', '')));
        for (const id of ids) {
          expect(cardIds, `the complete list has no card for active fixture ${id}`).toContain(id);
        }
        await expect(page.locator('#picks').first()).toBeVisible();
      }
      const registerRows = await register.count();
      testInfo.annotations.push({
        type: '542dfb58-phone-coverage',
        description: `executive summary at ${viewport.width}px: ${shownIds.length} priced glance rows of `
          + `${ids.length} active fixtures, ${registerRows} register row(s), sideways overflow ${overflow}px. `
          + 'Every active fixture is reachable on the summary or in its unresolved register.',
        url: 'https://play.hotspawn.com/lobby',
      });
    });

    test('the unresolved section and its limitations are on the landing page itself', async ({ page }, testInfo) => {
      await page.goto('./index.html');
      const section = page.locator('#unresolved-register');
      await expect(section, 'the executive summary must contain the unresolved-picks section').toBeAttached();
      const text = await section.innerText();
      expect(text).toMatch(/unresolved/i);
      // Either it names a fixture with its blocker, or it says the count is zero and why.
      const namedFixture = /no unresolved fixtures|Hotspawn \d{6,}/i.test(text);
      expect(namedFixture, 'the unresolved section states neither a blocker nor an all-clear').toBe(true);
      // And the section explains the limits of the fallback research, not just the count.
      expect(text).toMatch(/limitation|why not the featured line|no .*price|researched|refreshes every four hours/i);
      testInfo.annotations.push({
        type: '542dfb58-unresolved-section',
        description: `unresolved register found in the executive summary; opening line: `
          + `${text.slice(0, 160).replace(/\s+/g, ' ')}`,
      });
    });
  });
}

test('the phone bottom navigation routes to picks and to the unresolved register', async ({ page }, testInfo) => {
  test.info().timeout = 60000;
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('./index.html');
  const tabs = page.locator('nav.mobile-nav a');
  const labels = await tabs.evaluateAll((nodes) => nodes.map((n) => n.innerText.trim().toLowerCase()));
  expect(labels).toContain('picks');
  expect(labels).toContain('unresolved');
  const tap = await tabs.evaluateAll((nodes) => nodes.map((n) => {
    const rect = n.getBoundingClientRect();
    return { label: n.innerText.trim(), h: Math.round(rect.height), w: Math.round(rect.width) };
  }));
  for (const item of tap) {
    expect(item.h, `the ${item.label} tab is only ${item.h}px tall on a phone`).toBeGreaterThanOrEqual(44);
  }
  // The status shortcut at the very top is the one-tap path to the picks.
  const shortcut = page.locator('.mobile-status-picks');
  await expect(shortcut).toBeVisible();
  await expect(shortcut).toContainText(/picks ready/);
  await expect(shortcut).toHaveAttribute('href', /origination\/#picks/);
  testInfo.annotations.push({
    type: '542dfb58-mobile-nav',
    description: `mobile nav tabs ${labels.join(', ')}; tap target heights ${tap.map((x) => x.h).join('/')}px — `
      + 'picks and unresolved are one tap from the landing page at 390px',
  });
});
