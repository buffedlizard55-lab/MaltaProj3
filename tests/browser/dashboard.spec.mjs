import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';

const routes = ['/', '/picks/', '/edge/', '/twc-picks/', '/coverage/', '/methodology/', '/review/'];

for (const width of [320, 390, 768, 1440]) {
  test(`all current pages are readable without horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator('main h1')).toBeVisible();
      await expect(page.locator('main')).toBeVisible();
      const dimensions = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      expect(dimensions.document, `${route} overflows at ${width}`).toBeLessThanOrEqual(dimensions.viewport + 1);
    }
    expect(errors).toEqual([]);
  });
}

test('phone navigation reaches the full picks list in one tap', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('link', { name: 'See all match picks' }).click();
  await expect(page).toHaveURL(/\/origination\/#picks$/);
  await expect(page.locator('.pick-card')).not.toHaveCount(0);
  await page.goto('/');
  const phoneNav = page.getByRole('navigation', { name: 'Mobile navigation' });
  await expect(phoneNav.getByRole('link')).toHaveCount(6);
  await phoneNav.getByRole('link', { name: 'Methods', exact: true }).click();
  await expect(page).toHaveURL(/\/methodology\/$/);
});

test('search, method filters, sorting and clearing work', async ({ page }) => {
  await page.goto('/picks/');
  const all = page.locator('#match-list > tbody > .match-row');
  const total = await all.count();
  await page.locator('#match-search').fill('definitely-no-such-team');
  await expect(page.locator('#filter-empty')).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
  expect(await page.locator('#match-list > tbody > tr:visible').count()).toBe(total);
  await page.getByRole('button', { name: /^Research/ }).click();
  expect(await page.locator('#match-list > tbody > tr:visible').count()).toBe(await page.locator('#match-list > tbody > tr[data-method="model"]').count());
  await page.locator('#match-sort').selectOption('confidence');
  const probabilities = await page.locator('#match-list > tbody > tr:visible').evaluateAll(nodes => nodes.map(n => Number(n.dataset.confidence)));
  expect(probabilities).toEqual([...probabilities].sort((a, b) => b - a));
});

test('every current match row links to original Hotspawn evidence', async ({ page }) => {
  await page.goto('/picks/');
  for (const row of await page.locator('#match-list > tbody > .match-row').all()) {
    expect(await row.locator('a[href*="hotspawn.com"], a[href*="cloudwaysapps.com"]').count()).toBeGreaterThan(0);
  }
});

test('evidence expands on a small phone without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 850 });
  await page.goto('/picks/');
  await page.locator('#match-list > tbody > tr').first().locator('summary').click();
  await expect(page.locator('details[open] .evidence-box')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});

test('timezone conversion is explicit and changes the displayed time', async ({ page }) => {
  await page.goto('/picks/');
  await page.locator('#timezone').selectOption('Europe/Malta');
  const before = await page.locator('.match-cell time').first().textContent();
  await page.locator('#timezone').selectOption('UTC');
  expect(await page.locator('.match-cell time').first().textContent()).not.toBe(before);
  await expect(page.locator('[data-zone-label]')).toHaveText('UTC');
});

test('a stale snapshot warns and never masquerades as a current pick', async ({ page }) => {
  await page.clock.install({ time: new Date('2027-01-01T12:00:00Z') });
  await page.goto('/picks/');
  await expect(page.locator('#stale-warning')).toBeVisible();
  const choices = page.locator('[data-pick-choice]');
  expect(await choices.count()).toBeGreaterThan(0);
  await expect(choices.first()).toContainText('Snapshot:');
  await expect(page.locator('[data-pick-caption]').first()).toContainText('not a current pick');
});

test('all matches and source links remain available with JavaScript disabled', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.goto('/picks/');
  expect(await page.locator('#match-list > tbody > tr').count()).toBeGreaterThan(0);
  await expect(page.locator('#match-list > tbody > tr').first().locator('.row-source-links a').first()).toBeVisible();
  await expect(page.locator('#match-list > tbody > tr').first().locator('.team-pair')).toBeVisible();
  await context.close();
});

for (const width of [390, 1440]) {
for (const route of routes) {
  test(`current page ${route} at ${width}px passes WCAG A/AA automated accessibility checks`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto(route);
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
    await fs.mkdir('.cache/a11y', { recursive: true });
    await fs.writeFile(`.cache/a11y/${`${width}-` + route.replaceAll('/', '_')}.json`, JSON.stringify(result.violations, null, 2));
    expect(result.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.slice(0, 4).map(n => ({ target: n.target, summary: n.failureSummary })) }))).toEqual([]);
  });
}
}

test('capture final phone and desktop views for visual verification', async ({ page }) => {
  await fs.mkdir('.cache/screenshots', { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.goto('/');
  await page.screenshot({ path: '.cache/screenshots/summary-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '.cache/screenshots/summary-phone.png', fullPage: true });
  await page.goto('/picks/');
  await page.screenshot({ path: '.cache/screenshots/picks-phone.png', fullPage: true });
});

test('phone briefing shortcuts and picks section expose unresolved limitations', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const shortcuts = page.getByRole('navigation', { name: 'Briefing shortcuts' });
  await shortcuts.getByRole('link', { name: 'Unresolved & limitations' }).click();
  // arena-3a5448de: one canonical register on the summary; the old duplicate
  // #unresolved H2 is now the featured-method audit trail below it.
  await expect(page).toHaveURL(/#unresolved-register$/);
  await expect(page.locator('#unresolved-register h2')).toHaveText('Unresolved picks & limitations');
  await expect(page.locator('#unresolved h2')).toHaveText('Featured-method gaps, before research fallback');
  await page.goto('/picks/');
  await page.getByRole('link', { name: /Jump to unresolved picks/ }).click();
  await expect(page.locator('#unresolved h2')).toBeVisible();
});

test('phone executive summary exposes the source-linked contrarian guardrail', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const shortcuts = page.getByRole('navigation', { name: 'Briefing shortcuts' });
  await shortcuts.getByRole('link', { name: 'Contrarian review' }).click();
  const review = page.locator('#contrarian');
  await expect(review).toBeVisible();
  await expect(review).toContainText('9z vs Aurora');
  await expect(review).toContainText('15.7%');
  await expect(review).toContainText('primary pick remains Falcons');
  expect(await review.locator('a[href^="https://"]').count()).toBeGreaterThan(8);
});

test('research deep link reveals evidence despite a contradictory bookmarked filter', async ({ page }) => {
  await page.goto('/picks/');
  const unresolved = page.locator('#match-list > tbody > tr[data-method="unresolved"]').first();
  if (await unresolved.count() === 0) return; // A completely resolved live feed is valid.
  const id = await unresolved.getAttribute('id');
  await page.goto(`/picks/?basis=market#${id}`);
  const row = page.locator(`#${id}`);
  await expect(row).toBeVisible();
  await expect(row.locator('details')).toHaveAttribute('open', '');
  await expect(row.locator('.evidence-box')).toBeVisible();
});

test('each supported probability shows a labeled calculated fair line', async ({ page }) => {
  await page.goto('/picks/');
  const supported = page.locator('#match-list > tbody > tr:not([data-method="unresolved"])');
  for (const row of await supported.all()) {
    await expect(row.locator('.fair-line')).toHaveCount(2);
    expect(await row.locator('.fair-line').allTextContents()).toEqual(expect.arrayContaining([expect.stringMatching(/^Fair line \d+\.\d{3}$/)]));
  }
});

test('clearing a method filter also clears the bookmarked URL state', async ({ page }) => {
  await page.goto('/picks/?basis=model');
  await page.locator('#match-search').fill('definitely-no-such-team');
  await page.getByRole('button', { name: 'Clear filters' }).click();
  expect(new URL(page.url()).searchParams.has('basis')).toBe(false);
  await page.reload();
  await expect(page.getByRole('button', { name: /^All matches/ })).toHaveAttribute('aria-pressed', 'true');
});

test('phone executive summary exposes original sources for unresolved picks', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Executive summary', exact: true })).toBeVisible();
  await page.locator('.hero-secondary').first().click();
  const details = page.locator('#unresolved .unresolved-table details');
  if (await details.count()) {
    await details.first().locator('summary').click();
    await expect(details.first().locator('.research-trail')).toBeVisible();
    expect(await details.first().locator('a[href^="https://"]').count()).toBeGreaterThan(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  }
});

test('the upset review is one tap from the phone summary and stays source-linked', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const shortcuts = page.getByRole('navigation', { name: 'Briefing shortcuts' });
  await shortcuts.getByRole('link', { name: 'Upset review & edge' }).click();
  await expect(page).toHaveURL(/\/edge\/$/);
  await expect(page.locator('.mobile-nav a[aria-current="page"]')).toHaveText('Edge');
  for (const anchor of ['day-one', 'rosters', 'rules', 'day-two', 'standings', 'edge-limitations']) {
    await expect(page.locator(`#${anchor}`)).toBeVisible();
  }
  await expect(page.locator('#day-one tbody tr')).toHaveCount(4);
  await expect(page.locator('#day-two tbody tr')).toHaveCount(4);
  expect(await page.locator('#day-one a[href^="https://www.hltv.org"]').count()).toBeGreaterThan(0);
  expect(await page.locator('#day-two a[href^="https://"]').count()).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test('every match row shows either a pick or an explicit blank, never a silent gap', async ({ page }) => {
  await page.goto('/picks/');
  const rows = page.locator('#match-list > tbody > tr');
  const total = await rows.count();
  expect(total).toBeGreaterThan(0);
  for (const row of await rows.all()) {
    const pick = row.locator('[data-pick-choice]');
    const blank = row.locator('.unresolved-text');
    expect(await pick.count() + await blank.count(), 'a row must resolve one way or the other').toBeGreaterThan(0);
  }
  const researched = page.locator('#match-list > tbody > tr[data-researched-fallback="true"]');
  for (const row of await researched.all()) {
    await expect(row.locator('.badge', { hasText: 'Researched fallback' })).toHaveCount(1);
    expect(await row.locator('a[href*="origination/#match-"]').count()).toBeGreaterThan(0);
  }
});

for (const width of [320, 390]) {
  test(`the phone summary lists picks and their sources above the fold at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    const glance = page.locator('#picks-at-a-glance');
    await expect(glance).toBeVisible();
    const rows = glance.locator('.glance-row');
    expect(await rows.count()).toBeGreaterThan(0);
    const first = rows.first();
    await expect(first.locator('.glance-choice')).toBeVisible();
    expect(await first.locator('a[href*="hotspawn.com"]').count()).toBeGreaterThan(0);
    await expect(first.locator('a', { hasText: 'Full detail' })).toHaveAttribute('href', /#match-\d+/);
    const box = await glance.boundingBox();
    expect(box.y).toBeLessThan(1500);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    const unresolved = glance.locator('.glance-pick-label.unresolved-text');
    for (let i = 0; i < await unresolved.count(); i += 1) {
      await expect(unresolved.nth(i).locator('xpath=..').locator('a[href*="origination/#unresolved"]')).toHaveCount(1);
    }
  });
}

test('the summary states complete pick coverage and maps every page', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('[aria-label="Complete pick coverage"]')).toContainText(/\d+ \/ \d+/);
  await expect(page.locator('#site-map')).toBeVisible();
  const links = await page.locator('#site-map a[href]').allTextContents();
  expect(links.join(' ')).toContain('Complete match picks');
  expect(links.join(' ')).toContain('Upset review');
  expect(links.join(' ')).toContain('Featured method picks');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
