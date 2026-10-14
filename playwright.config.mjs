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
  timeout: 30000,
  fullyParallel: false,
  workers: process.env.CI ? 2 : 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.PREVIEW_BASE_URL || 'http://127.0.0.1:8000',
    headless: true,
    launchOptions,
  },
  webServer: process.env.PREVIEW_BASE_URL ? undefined : {
    command: 'python -m http.server 8000 --bind 0.0.0.0 --directory site',
    url: 'http://127.0.0.1:8000',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
