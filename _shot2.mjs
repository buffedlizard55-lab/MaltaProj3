import { chromium as pw } from '@playwright/test';
import chromium from '@sparticuz/chromium';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
const root='/home/user/MaltaProj3';
const libraryRoot = path.resolve(root+'/.cache/chromium-libs');
if (!fs.existsSync(path.join(libraryRoot, 'lib/libnspr4.so'))) {
  fs.mkdirSync(libraryRoot, { recursive: true });
  const archive = path.resolve(root+'/.cache/chromium-libs.tar');
  fs.writeFileSync(archive, zlib.brotliDecompressSync(fs.readFileSync(root+'/node_modules/@sparticuz/chromium/bin/al2023.tar.br')));
  execFileSync('tar', ['-xf', archive, '-C', libraryRoot]);
}
const browser = await pw.launch({ executablePath: await chromium.executablePath(), args: ['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'], env: { ...process.env, LD_LIBRARY_PATH: path.join(libraryRoot,'lib') } });
for (const width of [320, 390]) {
  const page = await browser.newPage({ viewport: { width, height: 800 }, deviceScaleFactor: 2 });
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  await page.locator('#picks-at-a-glance').scrollIntoViewIfNeeded();
  await page.waitForTimeout(200);
  await page.screenshot({ path: `/tmp/glance-${width}.png` });
  const m = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.glance-row')];
    const overflow = rows.filter(r => r.scrollWidth > r.clientWidth + 1).length;
    return { rows: rows.length, overflow,
      firstRow: rows[0]?.innerText.replace(/\n+/g,' | '),
      docOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      startHere: document.querySelector('#start-here')?.innerText.replace(/\n+/g,' | ').slice(0,300) };
  });
  console.log(width, JSON.stringify(m, null, 1));
  await page.close();
}
await browser.close();
