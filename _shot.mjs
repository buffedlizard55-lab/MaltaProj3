import { chromium as pw } from '@playwright/test';
import chromium from '@sparticuz/chromium';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
const libraryRoot = path.resolve('/home/user/MaltaProj3/.cache/chromium-libs');
if (!fs.existsSync(path.join(libraryRoot, 'lib/libnspr4.so'))) {
  fs.mkdirSync(libraryRoot, { recursive: true });
  const archive = path.resolve('/home/user/MaltaProj3/.cache/chromium-libs.tar');
  fs.writeFileSync(archive, zlib.brotliDecompressSync(fs.readFileSync('/home/user/MaltaProj3/node_modules/@sparticuz/chromium/bin/al2023.tar.br')));
  execFileSync('tar', ['-xf', archive, '-C', libraryRoot]);
}
const browser = await pw.launch({ executablePath: await chromium.executablePath(), args: ['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'], env: { ...process.env, LD_LIBRARY_PATH: path.join(libraryRoot,'lib') } });
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
await page.screenshot({ path: '/tmp/mobile-top.png' });
const m = await page.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
  h1: document.querySelector('h1')?.textContent?.trim(),
  firstSections: [...document.querySelectorAll('main section')].slice(0,6).map(s => s.id || s.className),
  nav: document.querySelector('.mobile-nav')?.textContent?.replace(/\s+/g,' ').trim(),
  staleHidden: document.getElementById('stale-warning')?.hidden,
  linkCount: document.querySelectorAll('a').length,
}));
console.log(JSON.stringify(m, null, 1));
await page.screenshot({ path: '/tmp/mobile-full.png', fullPage: true });
await browser.close();
