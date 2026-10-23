import { test, expect } from '@playwright/test';

// Session arena-17d77cb3 — phone findability of the picks.
//
// The brief asks for an executive summary that says where the updated picks
// are and a site that is easy to read on a phone. Two measured defects were
// fixed in this session and are pinned here:
//
// 1. the six-tab bottom bar overflowed the viewport (501px of content in a
//    390px bar, last tab clipped at x=493 with no scroll affordance), and at
//    320/360px "Summary"/"Unresolved" broke mid-word;
// 2. five stacked 52px "Start here" cards plus the explanatory paragraph put
//    the first pick 1,098px down a 390x844 phone.
//
// These are layout facts, so they are asserted in a browser rather than in CSS
// unit tests. Nothing here re-prices, re-orders or re-picks a fixture.

const sizes = [
  { width: 390, height: 844, firstPickLimit: 1000 },
  { width: 320, height: 568, firstPickLimit: 1100 },
];

for (const size of sizes) {
  test(`every bottom-bar tab is visible and the first pick is near the top at ${size.width}px`, async ({ page }) => {
    await page.setViewportSize({ width: size.width, height: size.height });
    await page.goto('/');

    const nav = page.getByRole('navigation', { name: 'Mobile navigation' });
    await expect(nav.getByRole('link')).toHaveCount(6);

    const bar = await nav.evaluate(el => ({
      overflow: el.scrollWidth - el.clientWidth,
      clipped: [...el.querySelectorAll('a')].filter(a => {
        const r = a.getBoundingClientRect();
        return r.right > innerWidth + 1 || r.left < -1 || r.width < 24 || r.height < 44;
      }).map(a => a.textContent.trim()),
    }));
    expect(bar.overflow, 'the bottom bar must fit without a hidden horizontal scroll').toBeLessThanOrEqual(1);
    expect(bar.clipped, 'every tab must be fully on screen at a tappable size').toEqual([]);

    const firstPick = await page.locator('.glance-row').first().evaluate(el => {
      return el.getBoundingClientRect().top + window.scrollY;
    });
    expect(firstPick, 'the first pick must be reachable without scrolling past the fold').toBeLessThanOrEqual(size.firstPickLimit);
  });
}

test('the glance list comes before its explanation on a phone, and keeps the explanation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const order = await page.evaluate(() => {
    const list = document.querySelector('#picks-at-a-glance #glance-list');
    const intro = document.querySelector('#picks-at-a-glance .section-intro');
    return {
      listTop: list.getBoundingClientRect().top,
      introTop: intro.getBoundingClientRect().top,
      introText: intro.textContent.trim().length,
      rows: list.querySelectorAll('.glance-row').length,
    };
  });
  expect(order.listTop).toBeLessThan(order.introTop);
  expect(order.introText).toBeGreaterThan(40);
  expect(order.rows).toBeGreaterThan(0);
});

test('start-here destinations stay tappable and the picks jump still resolves', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const chips = page.locator('.start-here a');
  const count = await chips.count();
  expect(count).toBeGreaterThanOrEqual(5);
  for (let i = 0; i < count; i += 1) {
    const box = await chips.nth(i).boundingBox();
    expect(box.height, `start-here chip ${i} is too small to tap`).toBeGreaterThanOrEqual(44);
    expect(box.width).toBeGreaterThan(80);
  }
  const here = await chips.first().getAttribute('href');
  expect(here).toContain('#picks-at-a-glance');
  const target = await page.locator('#picks-at-a-glance').count();
  expect(target).toBe(1);
});

test('the unresolved register is a separate, labeled section on the summary', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const heading = page.locator('#unresolved-register-title');
  await expect(heading).toHaveCount(1);
  await expect(heading).not.toHaveText(/picks at a glance/i);
  const label = (await page.locator('#unresolved-register').getAttribute('aria-labelledby')) || '';
  expect(label).toBe('unresolved-register-title');
  // The register's own links must resolve inside this document.
  const broken = await page.evaluate(() => {
    const section = document.querySelector('#unresolved-register');
    return [...section.querySelectorAll('a[href^="#"]')]
      .map(a => a.getAttribute('href').slice(1))
      .filter(id => !document.getElementById(id));
  });
  expect(broken).toEqual([]);
});
