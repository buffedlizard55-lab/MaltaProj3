#!/usr/bin/env node
import { access, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';

const localPages = ['index.html', 'picks.html', 'methodology.html', 'flagged.html'];
const requiredFiles = [...localPages, 'assets/styles.css', 'assets/app.js', 'data/matches.json', 'data/review.json'];
const failures = [];
const warnings = [];

for (const file of requiredFiles) {
  try { await access(file, constants.R_OK); } catch { failures.push(`Missing required file: ${file}`); }
}

for (const file of localPages) {
  const html = await readFile(file, 'utf8');
  for (const found of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
    const target = found[1];
    if (/^(https?:|mailto:|#)/.test(target)) continue;
    try { await access(target.split('?')[0], constants.R_OK); } catch { failures.push(`${file} has a missing local asset/link: ${target}`); }
  }
}

const data = JSON.parse(await readFile('data/matches.json', 'utf8'));
if (!Array.isArray(data.matches) || !data.matches.length) failures.push('matches.json contains no match rows.');
for (const [index, match] of data.matches.entries()) {
  const label = `Row ${index + 1} (${match.team1} vs ${match.team2})`;
  if (!match.team1 || !match.team2 || !match.tournament) failures.push(`${label} is missing a match identity field.`);
  if (!/^https:\/\/play\.hotspawn\.com\/lobby|^https:\/\/www\.hotspawn\.com\/matches\//.test(match.hotspawnUrl || '')) failures.push(`${label} has no official Hotspawn source URL.`);
  if (match.status === 'verified-line') {
    if (!match.probability || !match.recommendation) failures.push(`${label} is marked verified but has no probability or pick.`);
    else {
      const sum = match.probability.team1 + match.probability.team2;
      if (Math.abs(sum - 100) > .2) failures.push(`${label} probabilities do not sum to 100 (got ${sum}).`);
      if (!/^https:\/\//.test(match.probability.sourceUrl || '')) failures.push(`${label} has no HTTPS external-line source URL.`);
    }
  } else if (match.probability || match.recommendation) {
    failures.push(`${label} is unresolved but contains a probability or pick.`);
  }
  if (!match.startsAt) warnings.push(`${label} has no verified UTC start time.`);
}

if (warnings.length) console.warn(`Warnings:\n- ${warnings.join('\n- ')}`);
if (failures.length) { console.error(`Verification failed:\n- ${failures.join('\n- ')}`); process.exit(1); }
console.log(`Verified ${data.matches.length} published match rows, ${data.matches.filter(m => m.status === 'verified-line').length} external lines, and ${localPages.length} HTML pages.`);
