import { defineConfig } from '@playwright/test';
import chromium from '@sparticuz/chromium';

const localBrowser = !process.env.CI;
export default defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  fullyParallel: false,
  workers: process.env.CI ? 2 : 1,
  reporter: [['list']],
  use: {
    baseURL: process.env.PREVIEW_BASE_URL || 'http://127.0.0.1:8000',
    headless: true,
    launchOptions: localBrowser ? { executablePath: await chromium.executablePath(), args: chromium.args } : {},
  },
  webServer: process.env.PREVIEW_BASE_URL ? undefined : {
    command: 'python -m http.server 8000 --bind 0.0.0.0 --directory site',
    url: 'http://127.0.0.1:8000',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
