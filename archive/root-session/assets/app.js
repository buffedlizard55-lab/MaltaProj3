const DATA_URL = 'data/matches.json';
const REVIEW_URL = 'data/review.json';

const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[char]));

const utc = value => value
  ? `${new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(new Date(value))} UTC`
  : 'Time not verified';

const shortUtc = value => value
  ? new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC', timeZoneName: 'short' }).format(new Date(value))
  : 'Time not verified';

const sourceLinks = match => {
  const links = [`<a href="${escapeHtml(match.hotspawnUrl)}" target="_blank" rel="noopener noreferrer">Hotspawn listing <span aria-hidden="true">↗</span></a>`];
  if (match.probability?.sourceUrl) links.push(`<a href="${escapeHtml(match.probability.sourceUrl)}" target="_blank" rel="noopener noreferrer">Market line <span aria-hidden="true">↗</span></a>`);
  if (match.hltvUrl) links.push(`<a href="${escapeHtml(match.hltvUrl)}" target="_blank" rel="noopener noreferrer">HLTV context <span aria-hidden="true">↗</span></a>`);
  return links.join('');
};

const probabilityHtml = match => {
  if (!match.probability) {
    return `<div class="unresolved-block"><b>Unresolved:</b> probability blank. ${escapeHtml(match.limitation)}</div>`;
  }
  const { team1, team2 } = match.probability;
  const oneWins = team1 > team2;
  return `<div class="probability" aria-label="External win probabilities">
    <div class="prob ${oneWins ? 'winner' : ''}"><span>${escapeHtml(match.team1)}</span><b>${team1.toFixed(1)}%</b></div>
    <div class="prob ${!oneWins ? 'winner' : ''}"><span>${escapeHtml(match.team2)}</span><b>${team2.toFixed(1)}%</b></div>
  </div>`;
};

const matchCard = match => `<article class="card match-card" data-status="${match.status}">
  <div class="match-card-top">
    <div><div class="match-meta">${escapeHtml(match.tournament)} · Tier ${escapeHtml(match.tier)}</div></div>
    <time class="match-time" datetime="${escapeHtml(match.startsAt || '')}">${shortUtc(match.startsAt)}</time>
  </div>
  <div class="teams"><div class="team">${escapeHtml(match.team1)}</div><div class="vs">VS</div><div class="team">${escapeHtml(match.team2)}</div></div>
  ${probabilityHtml(match)}
  <div class="card-foot">
    ${match.recommendation ? `<span class="pick-label">Market pick: ${escapeHtml(match.recommendation)}</span>` : '<span class="badge unresolved">Pick unavailable</span>'}
    <span class="source-links">${sourceLinks(match)}</span>
  </div>
</article>`;

const tableRow = match => {
  const probability = match.probability
    ? `<b>${match.probability.team1.toFixed(1)}%</b> <span class="tiny">${escapeHtml(match.team1)}</span><br><b>${match.probability.team2.toFixed(1)}%</b> <span class="tiny">${escapeHtml(match.team2)}</span>`
    : '<span aria-label="Unverified probability">—</span>';
  const pick = match.recommendation
    ? `<b>${escapeHtml(match.recommendation)}</b><br><span class="tiny">External-market favorite</span>`
    : '<span class="badge unresolved">Unresolved</span>';
  const evidence = match.probability
    ? `<span class="badge verified">Verified line</span><br><span class="tiny">${escapeHtml(match.probability.method)}</span>`
    : `<span class="badge unresolved">Line unavailable</span><br><span class="tiny">${escapeHtml(match.limitation)}</span>`;
  return `<tr>
    <td><time datetime="${escapeHtml(match.startsAt || '')}">${shortUtc(match.startsAt)}</time></td>
    <td><span class="match-name">${escapeHtml(match.team1)} <span class="tiny">vs</span> ${escapeHtml(match.team2)}</span><br><span class="tiny">${escapeHtml(match.tournament)} · Tier ${escapeHtml(match.tier)}</span></td>
    <td>${probability}</td><td>${pick}</td><td>${evidence}</td><td><span class="source-links">${sourceLinks(match)}</span></td>
  </tr>`;
};

function updateSummary(data) {
  const matches = data.matches || [];
  const lines = matches.filter(match => match.status === 'verified-line');
  const unresolved = matches.filter(match => match.status !== 'verified-line');
  document.querySelectorAll('[data-total]').forEach(node => node.textContent = matches.length);
  document.querySelectorAll('[data-lines]').forEach(node => node.textContent = lines.length);
  document.querySelectorAll('[data-unresolved]').forEach(node => node.textContent = unresolved.length);
  document.querySelectorAll('[data-asof]').forEach(node => node.textContent = utc(data.generatedAt));
  document.querySelectorAll('[data-refresh-hours]').forEach(node => node.textContent = data.scope?.refreshCadenceHours || '6');
}

function renderIndex(data) {
  const target = document.querySelector('#featured-picks');
  if (!target) return;
  const items = data.matches.filter(match => match.status === 'verified-line').slice(0, 5);
  target.innerHTML = items.length ? items.map(matchCard).join('') : '<p class="empty">No independently verified market lines are currently available.</p>';
}

function renderPicks(data) {
  const target = document.querySelector('#picks-table-body');
  const count = document.querySelector('#filter-result');
  if (!target) return;
  const tier = document.querySelector('#tier-filter');
  const status = document.querySelector('#status-filter');
  const requestedStatus = new URLSearchParams(window.location.search).get('status');
  if (requestedStatus && [...status.options].some(option => option.value === requestedStatus)) status.value = requestedStatus;
  const draw = () => {
    const output = data.matches.filter(match => (tier.value === 'all' || match.tier === tier.value) && (status.value === 'all' || match.status === status.value));
    target.innerHTML = output.map(tableRow).join('') || '<tr><td colspan="6" class="empty">No matches match the selected filters.</td></tr>';
    count.textContent = `${output.length} of ${data.matches.length} matches`;
  };
  tier.addEventListener('change', draw);
  status.addEventListener('change', draw);
  draw();
}

function renderReview(review, data) {
  const target = document.querySelector('#flag-list');
  if (!target) return;
  const lines = data.matches.filter(match => match.status === 'verified-line').length;
  const unresolved = data.matches.length - lines;
  const coverage = `<article class="card flag watch"><div class="flag-header"><h3>Coverage snapshot</h3><span class="badge review">Needs review</span></div><p><b>${lines} of ${data.matches.length}</b> listed matches had a directly verified external match-winner line in this snapshot. <b>${unresolved}</b> are published below as unresolved with blank probabilities, not guesses.</p><a href="picks.html?status=unresolved">Open the unresolved rows</a></article>`;
  target.innerHTML = coverage + (review.flags || []).map(flag => `<article class="card flag ${escapeHtml(flag.severity)}"><div class="flag-header"><h3>${escapeHtml(flag.title)}</h3><span class="badge ${flag.severity === 'review' ? 'review' : 'unresolved'}">${escapeHtml(flag.severity)}</span></div><p>${escapeHtml(flag.detail)}</p><a href="${escapeHtml(flag.source)}" target="_blank" rel="noopener noreferrer">Review source <span aria-hidden="true">↗</span></a></article>`).join('');
}

async function boot() {
  try {
    const [dataResponse, reviewResponse] = await Promise.all([fetch(DATA_URL, { cache: 'no-store' }), fetch(REVIEW_URL, { cache: 'no-store' })]);
    if (!dataResponse.ok) throw new Error(`Data request failed: ${dataResponse.status}`);
    const data = await dataResponse.json();
    const review = reviewResponse.ok ? await reviewResponse.json() : { flags: [] };
    updateSummary(data);
    renderIndex(data);
    renderPicks(data);
    renderReview(review, data);
  } catch (error) {
    console.error(error);
    document.querySelectorAll('[data-loading]').forEach(node => {
      node.innerHTML = '<p class="empty">The published data file could not be loaded. Please refresh or review the repository data directly.</p>';
    });
  }
}

document.addEventListener('DOMContentLoaded', boot);
