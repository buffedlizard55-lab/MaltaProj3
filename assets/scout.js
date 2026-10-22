'use strict';

// All match content is server-rendered. JavaScript only enhances navigation,
// filtering, timezone presentation and honest freshness/lock status.
const body = document.body;
const storage = {
  get(key) { try { return localStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* Optional preference only. */ } },
};
const timezone = document.querySelector('#timezone');
const allowedZones = new Set(['Europe/Malta', 'UTC', 'local']);
let zone = storage.get('spawn-scout-timezone') || 'Europe/Malta';
if (!allowedZones.has(zone)) zone = 'Europe/Malta';
if (timezone) timezone.value = zone;

function validDate(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isFinite(d.getTime()) ? d : null;
}
function renderTimes() {
  const resolved = zone === 'local' ? Intl.DateTimeFormat().resolvedOptions().timeZone : zone;
  document.querySelectorAll('[data-time]').forEach(node => {
    const date = validDate(node.dataset.time);
    if (!date) return;
    const options = { day: '2-digit', month: 'short', year: 'numeric', timeZone: resolved };
    if (node.dataset.format !== 'date') Object.assign(options, { hour: '2-digit', minute: '2-digit', hour12: false });
    node.textContent = new Intl.DateTimeFormat('en-GB', options).format(date);
    node.title = `${date.toISOString()} · displayed in ${resolved}`;
  });
  document.querySelectorAll('[data-zone-label]').forEach(node => {
    node.textContent = zone === 'local' ? resolved : zone === 'UTC' ? 'UTC' : 'Europe/Malta';
  });
}
timezone?.addEventListener('change', () => {
  zone = allowedZones.has(timezone.value) ? timezone.value : 'Europe/Malta';
  storage.set('spawn-scout-timezone', zone);
  renderTimes();
});
renderTimes();

const inventoryDate = validDate(body.dataset.inventoryTime);
function ageOkay(date, now) {
  return date && now - date <= 8 * 3600000 && date - now <= 5 * 60000;
}
function liveStatus() {
  const now = new Date();
  const fresh = body.dataset.inventoryComplete === 'true' && ageOkay(inventoryDate, now);
  const warning = document.querySelector('#stale-warning');
  if (warning) warning.hidden = fresh;
  const freshness = document.querySelector('[data-freshness]');
  if (freshness) {
    freshness.classList.toggle('stale', !fresh);
    const dot = document.createElement('span');
    dot.className = 'status-dot';
    freshness.replaceChildren(dot, document.createTextNode(fresh ? 'Source snapshot available' : 'Snapshot needs attention'));
  }
  document.querySelectorAll('.match-row').forEach(row => {
    const start = validDate(row.dataset.start);
    const lock = validDate(row.dataset.lock);
    const quote = validDate(row.dataset.priceTime);
    const locked = (lock && lock <= now) || (start && start <= now);
    const label = row.querySelector('[data-availability]');
    if (label) {
      label.classList.toggle('locked', Boolean(locked));
      label.textContent = start && start <= now ? 'Past start · status unverified' : locked ? 'Closed for picks' : lock ? 'Open for picks' : 'Lock time unverified';
    }
    const choice = row.querySelector('[data-pick-choice]');
    const caption = row.querySelector('[data-pick-caption]');
    if (!choice || !caption) return;
    const name = choice.querySelector('strong');
    if (!name.dataset.original) name.dataset.original = name.textContent;
    if (!caption.dataset.original) caption.dataset.original = caption.textContent;
    const priceFresh = ageOkay(quote, now);
    const inactive = !fresh || !priceFresh || Boolean(locked) || !lock;
    choice.classList.toggle('inactive-pick', inactive);
    name.textContent = inactive ? `Snapshot: ${name.dataset.original}` : name.dataset.original;
    caption.textContent = !fresh || !priceFresh ? 'Stale / unverified freshness · not a current pick' : locked ? 'Closed for picks · estimate retained for audit' : !lock ? 'Lock unverified · confirm on Hotspawn' : caption.dataset.original;
  });
}
liveStatus();
setInterval(liveStatus, 30000);

const table = document.querySelector('#match-list');
if (table) {
  const rows = Array.from(table.querySelectorAll(':scope > tbody > .match-row'));
  const tbody = table.querySelector(':scope > tbody');
  const search = document.querySelector('#match-search');
  const tournament = document.querySelector('#tournament-filter');
  const sort = document.querySelector('#match-sort');
  const buttons = Array.from(document.querySelectorAll('[data-basis]'));
  const query = new URLSearchParams(location.search);
  let basis = ['market', 'model', 'unresolved'].includes(query.get('basis')) ? query.get('basis') : 'all';
  function applyFilters() {
    const term = search.value.trim().normalize('NFKC').toLowerCase();
    let visible = 0;
    const ordered = [...rows].sort((a, b) => {
      if (sort.value === 'confidence') return Number(b.dataset.confidence) - Number(a.dataset.confidence) || a.dataset.start.localeCompare(b.dataset.start);
      if (sort.value === 'team') return a.dataset.search.localeCompare(b.dataset.search);
      return a.dataset.start.localeCompare(b.dataset.start);
    });
    ordered.forEach(row => {
      const matchesBasis = basis === 'all' || (basis === 'market' ? ['market', 'bookmaker', 'consensus'].includes(row.dataset.method) : row.dataset.method === basis);
      row.hidden = !(matchesBasis && (tournament.value === 'all' || row.dataset.tournament === tournament.value) && row.dataset.search.includes(term));
      if (!row.hidden) visible += 1;
      tbody.append(row);
    });
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.basis === basis)));
    document.querySelector('#filter-count').textContent = `${visible} of ${rows.length} matches`;
    document.querySelector('#filter-empty').hidden = visible !== 0;
  }
  search.addEventListener('input', applyFilters);
  tournament.addEventListener('change', applyFilters);
  sort.addEventListener('change', applyFilters);
  buttons.forEach(button => button.addEventListener('click', () => {
    basis = button.dataset.basis;
    applyFilters();
    const url = new URL(location.href);
    if (basis === 'all') url.searchParams.delete('basis'); else url.searchParams.set('basis', basis);
    history.replaceState(null, '', url);
  }));
  document.querySelector('[data-reset]')?.addEventListener('click', () => {
    search.value = '';
    tournament.value = 'all';
    sort.value = 'start';
    basis = 'all';
    applyFilters();
    const url = new URL(location.href);
    url.searchParams.delete('basis');
    history.replaceState(null, '', url);
    search.focus();
  });
  applyFilters();

  // Evidence links from the briefing/review should actually reveal the research,
  // even when a bookmarked method filter would otherwise hide that match.
  function revealLinkedMatch() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    if (!id.startsWith('match-')) return;
    const row = document.getElementById(id);
    if (!row || !rows.includes(row)) return;
    if (row.hidden) {
      basis = 'all';
      search.value = '';
      tournament.value = 'all';
      applyFilters();
    }
    const details = row.querySelector('details');
    if (details) details.open = true;
    requestAnimationFrame(() => row.scrollIntoView({ block: 'start' }));
  }
  addEventListener('hashchange', revealLinkedMatch);
  revealLinkedMatch();
}

// A static Pages deploy can change while this tab remains open. Check the
// same-origin snapshot; never call localhost or a third-party API in the browser.
let updateInFlight = false;
async function checkForUpdate() {
  if (updateInFlight || document.visibilityState !== 'visible') return;
  updateInFlight = true;
  try {
    const response = await fetch(body.dataset.dataUrl, { cache: 'no-store', credentials: 'same-origin' });
    if (!response.ok) return;
    const data = await response.json();
    const next = validDate(data.generated_at);
    const current = validDate(body.dataset.snapshotGenerated);
    if (data.schema_version === 1 && next && current && next > current) document.querySelector('#new-snapshot').hidden = false;
  } catch { /* Never hide the current source timestamp or imply an update succeeded. */ }
  finally { updateInFlight = false; }
}
document.querySelector('#load-update')?.addEventListener('click', () => location.reload());
setInterval(checkForUpdate, 5 * 60000);
document.addEventListener('visibilitychange', () => { liveStatus(); checkForUpdate(); });
checkForUpdate();

// Executive-summary "find a pick" filter (session 3016b0c6): type a team or
// tournament name on the phone summary and only matching glance rows stay
// visible. Progressive enhancement — without this script every row is shown.
// It only hides rendered rows; it never recalculates a probability or pick.
(() => {
  const input = document.querySelector('#glance-search');
  const list = document.querySelector('#glance-list');
  if (!input || !list) return;
  const glance_rows = Array.from(list.querySelectorAll('.glance-row'));
  const count = document.querySelector('#glance-count');
  const empty = document.querySelector('#glance-empty');
  function applyGlanceFilter() {
    const term = input.value.trim().normalize('NFKC').toLowerCase();
    let visible = 0;
    glance_rows.forEach(row => {
      row.hidden = Boolean(term) && !(row.dataset.search || '').includes(term);
      if (!row.hidden) visible += 1;
    });
    if (count) count.textContent = term ? `${visible} of ${glance_rows.length} picks shown` : '';
    if (empty) empty.hidden = visible !== 0;
  }
  input.addEventListener('input', applyGlanceFilter);
  applyGlanceFilter();
})();

// Keep the active destination visible in the horizontally scrolling phone bar.
(() => {
  const nav = document.querySelector('.mobile-nav');
  const current = nav && nav.querySelector('a[aria-current="page"]');
  if (!nav || !current || nav.scrollWidth <= nav.clientWidth) return;
  const centre = current.offsetLeft - (nav.clientWidth - current.offsetWidth) / 2;
  nav.scrollLeft = Math.max(0, centre);
})();
