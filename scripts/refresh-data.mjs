#!/usr/bin/env node
/**
 * Public-source refresh for the static GitHub Pages dashboard.
 *
 * Sources queried: Hotspawn's public Pick'ems lobby (scope check) and the
 * public Polymarket Gamma market feed (external match-winner prices). No
 * credentials, private endpoints, account login, or Hotspawn pick-percentages
 * are used in probability generation.
 */
import { readFile, writeFile } from 'node:fs/promises';

const DATA_FILE = new URL('../data/matches.json', import.meta.url);
const REVIEW_FILE = new URL('../data/review.json', import.meta.url);
const HOTSPAWN_LOBBY = 'https://play.hotspawn.com/lobby';
// Polymarket's public Counter Strike series id returns event records with their
// constituent Match Winner markets. Small paged requests are deliberate: a
// very large response can be rejected by a proxy before any audit data arrives.
const POLYMARKET_EVENTS = 'https://gamma-api.polymarket.com/events?series_id=10310&active=true&closed=false&limit=50&order=updatedAt&ascending=false';
const now = new Date().toISOString();

const aliases = new Map([
  ['ninjasinpyjamas', 'nip'], ['nip', 'nip'],
  ['aurora', 'auroragaming'], ['auroragaming', 'auroragaming'],
  ['bcgame', 'bcgameesports'], ['bcgameesports', 'bcgameesports'],
  ['betboom', 'betboomteam'], ['betboomteam', 'betboomteam'],
  // This source uses the official event label "Team Falcons" for the team
  // Hotspawn lists as "Falcons". The initial audit directly verified that
  // exact public market pair; no unverified roster/team aliases are accepted.
  ['falcons', 'teamfalcons'], ['teamfalcons', 'teamfalcons'],
  ['fnatic', 'fnatic'], ['sashi', 'sashi'], ['furia', 'furia']
]);

function normalizeTeam(name = '') {
  const compact = String(name).toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/g, '');
  return aliases.get(compact) || compact;
}

function parseMaybeJson(value) {
  if (Array.isArray(value)) return value;
  try { return JSON.parse(value); } catch { return []; }
}

async function fetchOrThrow(url, type = 'json') {
  const response = await fetch(url, { headers: { 'user-agent': 'CS2-Pick-Desk-Refresh/1.0 (+GitHub Pages public-source audit)' } });
  if (!response.ok) throw new Error(`${response.status} from ${url}`);
  return type === 'text' ? response.text() : response.json();
}

/** A conservative exact-pair matcher. It accepts only a two-team Match Winner market. */
function matchPolymarketLine(match, markets) {
  const wanted = [normalizeTeam(match.team1), normalizeTeam(match.team2)];
  for (const market of markets) {
    if (!/counter-strike/i.test(market.question || '') || !/match winner/i.test(market.groupItemTitle || '')) continue;
    const outcomes = parseMaybeJson(market.outcomes);
    const prices = parseMaybeJson(market.outcomePrices).map(Number);
    if (outcomes.length !== 2 || prices.length !== 2 || !prices.every(Number.isFinite)) continue;
    const normalizedOutcomes = outcomes.map(normalizeTeam);
    const first = normalizedOutcomes.indexOf(wanted[0]);
    const second = normalizedOutcomes.indexOf(wanted[1]);
    if (first === -1 || second === -1 || first === second) continue;
    const total = prices[first] + prices[second];
    if (total <= 0) continue;
    return {
      team1: Number((prices[first] / total * 100).toFixed(1)),
      team2: Number((prices[second] / total * 100).toFixed(1)),
      method: 'Polymarket match-winner price',
      sourceUrl: `https://polymarket.com/market/${market.slug}`,
      observedAt: market.updatedAt || now,
      sourceType: 'prediction market'
    };
  }
  return null;
}

function extractLinkedHotspawnPaths(html) {
  const paths = new Set();
  // The public lobby has used both literal and JSON-escaped hrefs. Accept only
  // canonical Hotspawn match paths, never construct a path from team names.
  const expression = /(?:https?:\\?\/\\?\/www\.hotspawn\.com|https?:\/\/www\.hotspawn\.com|)\/matches\/([a-z0-9-]+-\d+)/gi;
  for (const found of html.matchAll(expression)) paths.add(`https://www.hotspawn.com/matches/${found[1]}`);
  return paths;
}

function statFlag(total, covered, lobbyReachable) {
  return {
    title: 'Coverage snapshot',
    severity: covered === total ? 'watch' : 'review',
    detail: `${covered} of ${total} published rows currently have an exact external match-winner line. ${total - covered} rows remain unresolved with intentionally blank probabilities. Hotspawn lobby reachability on this refresh: ${lobbyReachable ? 'confirmed' : 'not confirmed; prior schedule retained'}.`,
    source: HOTSPAWN_LOBBY
  };
}

async function main() {
  const data = JSON.parse(await readFile(DATA_FILE, 'utf8'));
  const previousReview = JSON.parse(await readFile(REVIEW_FILE, 'utf8'));
  let lobbyReachable = false;
  let lobbyLinks = new Set();
  let lobbyError = null;

  try {
    const lobby = await fetchOrThrow(HOTSPAWN_LOBBY, 'text');
    lobbyReachable = true;
    lobbyLinks = extractLinkedHotspawnPaths(lobby);
  } catch (error) {
    lobbyError = error.message;
    console.warn(`Hotspawn scope check failed; preserving existing schedule: ${lobbyError}`);
  }

  let markets = [];
  try {
    const firstPage = await fetchOrThrow(`${POLYMARKET_EVENTS}&offset=0`);
    const firstEvents = Array.isArray(firstPage) ? firstPage : [];
    let events = firstEvents;
    // The active Counter Strike series currently fits in two 50-event pages.
    // Fetch a second page only when the first one is full.
    if (firstEvents.length === 50) {
      const secondPage = await fetchOrThrow(`${POLYMARKET_EVENTS}&offset=50`);
      const secondEvents = Array.isArray(secondPage) ? secondPage : [];
      events = events.concat(secondEvents);
    }
    markets = events.flatMap(event => Array.isArray(event.markets) ? event.markets : []);
  } catch (error) {
    console.warn(`External market refresh failed; preserving prior verified lines: ${error.message}`);
  }

  let newlyPriced = 0;
  let cleared = 0;
  for (const match of data.matches) {
    // Retain per-row Hotspawn source URLs. A lobby source is scope evidence, not
    // an input to the probability or recommendation.
    if (lobbyReachable && match.hotspawnUrl !== HOTSPAWN_LOBBY && !lobbyLinks.has(match.hotspawnUrl)) {
      match.sourceCheck = { checkedAt: now, note: 'Not present in the linked-match subset of this lobby response; retained pending next refresh.' };
    } else if (lobbyReachable) {
      match.sourceCheck = { checkedAt: now, note: 'Public Hotspawn lobby checked.' };
    }

    if (!markets.length) continue;
    const line = matchPolymarketLine(match, markets);
    if (line) {
      if (match.status !== 'verified-line') newlyPriced += 1;
      match.probability = line;
      match.recommendation = line.team1 > line.team2 ? match.team1 : match.team2;
      match.status = 'verified-line';
      match.limitation = 'External market price; it is not a guarantee and can move after capture.';
    } else if (match.probability?.sourceType === 'prediction market') {
      // Do not present an old exchange price as if it were still active.
      match.probability = null;
      match.recommendation = null;
      match.status = 'unresolved';
      match.limitation = 'No active exact external match-winner line was returned by the public resolver on this refresh. Probability and pick are blank rather than stale.';
      cleared += 1;
    }
  }

  data.generatedAt = now;
  data.scope = { ...data.scope, source: HOTSPAWN_LOBBY, sourceName: 'Hotspawn Pick’ems lobby', lastLobbyCheck: now, lobbyReachable, linkedMatchCount: lobbyLinks.size, refreshCadenceHours: 6 };
  data.snapshotNote = `Public-source refresh at ${now}. ${lobbyReachable ? `Hotspawn lobby checked (${lobbyLinks.size} linked match pages found).` : `Hotspawn lobby check failed (${lobbyError}); previously verified schedule retained.`} ${markets.length ? `Polymarket resolver examined ${markets.length} active esports markets.` : 'No new external-market payload was applied.'}`;

  const covered = data.matches.filter(match => match.status === 'verified-line').length;
  const remainingFlags = (previousReview.flags || []).filter(flag => flag.title !== 'Coverage snapshot');
  const review = { generatedAt: now, flags: [statFlag(data.matches.length, covered, lobbyReachable), ...remainingFlags] };

  await writeFile(DATA_FILE, `${JSON.stringify(data, null, 2)}\n`);
  await writeFile(REVIEW_FILE, `${JSON.stringify(review, null, 2)}\n`);
  console.log(JSON.stringify({ checkedAt: now, listedRows: data.matches.length, verifiedLines: covered, newlyPriced, cleared, lobbyReachable, linkedMatchCount: lobbyLinks.size }, null, 2));
}

main().catch(error => { console.error(error); process.exitCode = 1; });
