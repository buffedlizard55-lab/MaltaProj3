import { defineConfig } from '@playwright/test';
import chromium from '@sparticuz/chromium';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';

const localBrowser = !process.env.CI;
let launchOptions = {};
if (localBrowser) {
  // The coding sandbox cannot download browser binaries from CDN hosts. Use
  // the npm-packaged browser and its bundled NSS libraries for local QA only.
  const libraryRoot = path.resolve('.cache/chromium-libs');
  if (!fs.existsSync(path.join(libraryRoot, 'lib/libnspr4.so'))) {
    fs.mkdirSync(libraryRoot, { recursive: true });
    const archive = path.resolve('.cache/chromium-libs.tar');
    fs.writeFileSync(archive, zlib.brotliDecompressSync(fs.readFileSync('node_modules/@sparticuz/chromium/bin/al2023.tar.br')));
    execFileSync('tar', ['-xf', archive, '-C', libraryRoot]);
  }
  launchOptions = {
    executablePath: await chromium.executablePath(),
    // Do not use the bundle's single-process or disabled-web-security flags.
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    env: { ...process.env, LD_LIBRARY_PATH: [path.join(libraryRoot, 'lib'), process.env.LD_LIBRARY_PATH].filter(Boolean).join(':') },
  };
}
export default defineConfig({
  testDir: './tests/browser',
  timeout: 60000,
  fullyParallel: false,
  workers: process.env.CI ? 2 : 1,
  // The job log host is not always reachable, so a failing browser test must
  // name itself on the run page (main's annotation reporter) and also leave a
  // machine-readable report behind for later review.
  reporter: [['list'], ['./scripts/playwright-annotations.mjs'],
             ['json', { outputFile: 'test-results/results.json' }]],
  use: {
    // 8123, not the documented 8000 preview port: a leftover server bound to
    // the repository root answers on 8000 and is reused, which compares the
    // built pages against the older checked-in root HTML and fails for a
    // reason that has nothing to do with the code (seen 2026-10-24, when
    // tests/browser/summary_navigation.spec.mjs counted 17 built cards against
    // a 19-card root page). PREVIEW_BASE_URL still points the suite anywhere.
    baseURL: process.env.PREVIEW_BASE_URL || 'http://127.0.0.1:8123',
    headless: true,
    launchOptions,
  },
  webServer: process.env.PREVIEW_BASE_URL ? undefined : {
    command: 'python -m http.server 8123 --bind 0.0.0.0 --directory site',
    url: 'http://127.0.0.1:8123',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
