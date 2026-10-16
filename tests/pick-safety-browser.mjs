/* Independent runtime/no-JS/mobile regression audit. Synthetic pages are served
 * from an OS temporary directory, never the Pages artifact or real data/.
 * Kept outside tests/browser/ to respect the concurrent integration owner's scope.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import config from '../playwright.config.mjs';

const now = '2026-10-16T09:00:00Z';
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'spawn-pick-safety-'));
const python = process.env.PYTHON || (fs.existsSync('.venv/bin/python') ? '.venv/bin/python' : 'python');
execFileSync(python, ['-m', 'tests.test_pick_presentation_safety', '--fixtures', root], { stdio: 'inherit' });
const mime = { '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
  let file;
  try { file = path.resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://test').pathname)); }
  catch { res.writeHead(400).end(); return; }
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
  if (!fs.existsSync(file)) { res.writeHead(404).end(); return; }
  res.setHeader('Content-Type', mime[path.extname(file)] || 'text/html');
  fs.createReadStream(file).pipe(res);
});
await new Promise(resolve => server.listen(0, '0.0.0.0', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
let browser;
let checks = 0;
const errors = [];
try {
  browser = await chromium.launch(config.use.launchOptions || {});
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  console.log('Safety audit: browser launched; checking pinned-clock transitions.');
  page.on('pageerror', e => errors.push(e.message));
  await page.clock.install({ time: new Date('2026-10-16T08:59:59Z') });
  await page.clock.pauseAt(new Date(now));
  await page.goto(base + '/origination/');
  assert.equal(await page.evaluate(() => Boolean(window.SpawnPickSafety)), true);

  const vectors = JSON.parse(fs.readFileSync(path.join(root, 'vectors.json')));
  const results = await page.evaluate(vs => vs.map(v => window.SpawnPickSafety.state(v.card, v.context, v.now)), vectors);
  assert.deepEqual(results, vectors.map(v => v.expected), 'browser and Python safety decisions must agree');
  checks += vectors.length;
  console.log('Safety audit: Python/JS parity passed.');

  assert.equal(await page.locator('[data-current-count]').textContent(), '3');
  assert.equal(await page.locator('.pick-card').count(), 5);
  assert.equal(await page.locator('#match-unknown').getAttribute('data-safety-status'), 'unknown-lock');
  assert.equal(await page.locator('#match-unresolved .probs strong').first().textContent(), '—');
  checks += 4;

  await page.clock.fastForward(30001);
  assert.equal(await page.locator('#match-edge').getAttribute('data-safety-status'), 'stale-line');
  assert.equal(await page.locator('[data-current-count]').textContent(), '2');
  assert.equal(await page.locator('#match-edge [data-current-only]').first().isVisible(), false);
  assert.equal(await page.locator('#match-edge .pick-line [data-historical-only]').isVisible(), true);
  assert.equal(await page.locator('#match-edge .probs strong').first().textContent(), '65.0%');
  checks += 5;

  await page.clock.fastForward(60000);
  assert.equal(await page.locator('#match-close').getAttribute('data-safety-status'), 'locked');
  assert.equal(await page.locator('#match-close [data-current-only]').first().isVisible(), false);
  assert.equal(await page.locator('.pick-card').count(), 5, 'lock must not silently drop a Hotspawn fixture');
  checks += 3;

  await page.clock.setSystemTime(new Date('2026-10-16T16:00:01Z'));
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  assert.equal(await page.locator('#match-ready').getAttribute('data-safety-status'), 'stale-line');
  assert.equal(await page.locator('[data-current-count]').textContent(), '0');
  await page.clock.setSystemTime(new Date(now));
  await page.evaluate(() => window.SpawnPickSafety.refresh());
  assert.notEqual(await page.locator('#match-ready').getAttribute('data-safety-status'), 'current', 'clock rollback must not revive a retired pick');
  checks += 3;

  await page.goto(base + '/strategy/');
  assert.equal(await page.evaluate(() => Boolean(window.SpawnPickSafety)), true);
  assert.equal(await page.locator('[data-current-swap-count]').first().textContent(), '2');
  await page.clock.fastForward(30001);
  assert.equal(await page.locator('#match-edge').getAttribute('data-safety-status'), 'stale-line');
  assert.equal(await page.locator('#match-edge .verdict').isVisible(), false);
  assert.equal(await page.locator('#match-edge .snapshot-plan').isVisible(), true);
  assert.equal(await page.locator('[data-safety-link="match-edge"]').isVisible(), false);
  assert.equal(await page.locator('[data-current-swap-count]').first().textContent(), '1');
  assert.equal(await page.locator('[data-safety-synopsis]').isVisible(), false, 'aggregate build-time advice must retire too');
  checks += 7;

  // A phone returning from a sleeping/background tab must refresh before showing advice.
  await page.clock.setSystemTime(new Date('2026-10-16T16:31:00Z'));
  await page.evaluate(() => window.dispatchEvent(new Event('pageshow')));
  assert.equal(await page.locator('#match-ready').getAttribute('data-safety-status'), 'stale-inventory');
  assert.equal(await page.locator('#match-ready .verdict').isVisible(), false);
  checks += 2;

  console.log('Safety audit: live expiry, locks and clock rollback passed.');
  await page.clock.resume();
  // Both fresh and historical presentation states must remain usable at phone/tablet/desktop widths.
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 850 });
    console.log(`Safety audit: layout and accessibility at ${width}px.`);
    for (const route of ['origination', 'stale-origination', 'incomplete-origination', 'strategy', 'stale-strategy', 'mismatch-strategy']) {
      await page.clock.setFixedTime(new Date(now));
      await page.goto(`${base}/${route}/`);
      const size = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
      assert.ok(size.document <= size.viewport + 1, `${route} overflow at ${width}px`);
      if (width === 390 || width === 1440) {
        const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
        assert.deepEqual(axe.violations.map(v => v.id), [], `${route} accessibility at ${width}px`);
        checks += 1;
      }
      checks += 1;
    }
  }
  await context.close();

  const nojs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const staticPage = await nojs.newPage();
  for (const route of ['stale-origination', 'incomplete-origination', 'stale-strategy', 'mismatch-strategy']) {
    await staticPage.goto(`${base}/${route}/`);
    assert.equal(await staticPage.locator('[data-current-only]:visible').count(), 0, `${route} must be safe without JS`);
    assert.ok(await staticPage.locator('[data-safety-message]:visible').count() > 0);
    assert.ok(await staticPage.locator('.probs').first().textContent(), 'source estimates must remain visible');
    assert.ok((await staticPage.locator('noscript').textContent()).includes('JavaScript is off'));
    checks += 4;
  }
  await nojs.close();
  assert.deepEqual(errors, [], 'no browser runtime errors');
  console.log(`PASS: ${checks} pick-presentation safety assertions (Python/JS parity, open-tab expiry, lock, clock rollback, no-JS, four widths and axe A/AA).`);
} finally {
  if (browser) await browser.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  fs.rmSync(root, { recursive: true, force: true });
}
