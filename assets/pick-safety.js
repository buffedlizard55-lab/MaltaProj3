/* Presentation guards only. No network calls, probability calculations or inferred deadlines.
 * Keep the decision order aligned with scripts/pick_safety.py; tested against shared vectors.
 */
(function () {
  'use strict';
  var messages = {
    current: ['Open for picks', 'Fresh source snapshot and line; submit before the confirmed lock.'],
    started: ['Past start', 'Scheduled start has passed; result unverified. Estimate retained for audit, not a current pick.'],
    locked: ['Locked', 'Closed for picks. Estimate retained for audit, not a current pick.'],
    'unknown-lock': ['Deadline unverified', 'A future lock/start and open status are not confirmed. No current pick is recommended.'],
    'inventory-unverified': ['Inventory unverified', 'Current coverage is not confirmed. Retained estimate only, not a current pick.'],
    'stale-inventory': ['Snapshot needs refresh', 'Inventory is older than eight hours or its observation time is unverified. Not a current pick.'],
    'unbound-snapshot': ['Snapshot mismatch', 'These lines are not bound to this inventory observation. Not a current pick.'],
    'stale-line': ['Line needs refresh', 'Line is older than eight hours or its observation time is unverified. Not a current pick.'],
    unresolved: ['Unresolved', 'No validated two-team estimate. Probabilities and pick stay blank; no default 50/50.']
  };
  function time(value) {
    // Reject timezone-less clocks rather than interpreting them in the device timezone.
    if (typeof value !== 'string' || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return NaN;
    return Date.parse(value);
  }
  function fresh(value, now, hours) {
    var observed = time(value);
    return Number.isFinite(observed) && now - observed >= -300000 && now - observed <= hours * 3600000;
  }
  function state(card, context, now) {
    var start = time(card.starts), lock = time(card.locks), hours = Number(context.maxAgeHours);
    if (!Number.isFinite(hours) || hours <= 0) hours = 8;
    if (card.lineValid !== 'true') return 'unresolved';
    if (Number.isFinite(start) && now >= start) return 'started';
    if ((Number.isFinite(lock) && now >= lock) || ['locked', 'past'].includes(card.availability)) return 'locked';
    if (!Number.isFinite(start) || !Number.isFinite(lock) || lock > start || card.availability !== 'open') return 'unknown-lock';
    if (context.inventoryComplete !== 'true') return 'inventory-unverified';
    if (!fresh(context.inventoryAt, now, hours)) return 'stale-inventory';
    if (context.snapshotBound !== 'true') return 'unbound-snapshot';
    if (!fresh(card.observed, now, hours)) return 'stale-line';
    return 'current';
  }
  function updateCard(card, context, now) {
    var next = state(card.dataset, context, now);
    // A client clock correction must not revive a retired server/browser recommendation.
    if (!card.dataset.safetyInitial) card.dataset.safetyInitial = card.dataset.safetyStatus || 'unresolved';
    if (next === 'current' && card.dataset.safetyInitial !== 'current') next = card.dataset.safetyInitial;
    if (next === 'current' && card.dataset.safetyRetired) next = card.dataset.safetyRetired;
    if (next !== 'current') card.dataset.safetyRetired = next;
    var current = next === 'current';
    card.dataset.safetyStatus = next;
    card.classList.toggle('is-historical', !current);
    card.querySelectorAll('[data-current-only]').forEach(function (node) { node.hidden = !current; });
    card.querySelectorAll('[data-historical-only]').forEach(function (node) { node.hidden = current; });
    var message = card.querySelector('[data-safety-message]');
    if (message) {
      if (message.dataset.safetyRendered !== next) {
        var label = document.createElement('strong');
        label.textContent = messages[next][0] + '. ';
        message.replaceChildren(label, document.createTextNode(messages[next][1]));
        message.dataset.safetyRendered = next;
      }
      message.hidden = current;
    }
    return current;
  }
  function refresh() {
    var body = document.body;
    if (!body || !body.hasAttribute('data-pick-safety')) return;
    var now = Date.now(), n = 0;
    var cards = document.querySelectorAll('[data-safety-card]');
    cards.forEach(function (card) { if (updateCard(card, body.dataset, now)) n += 1; });
    document.querySelectorAll('[data-current-count]').forEach(function (node) { node.textContent = String(n); });
    var currentSwaps = Array.from(document.querySelectorAll('[data-safety-card].swap')).filter(function (card) {
      return card.dataset.safetyStatus === 'current';
    });
    document.querySelectorAll('[data-current-swap-count]').forEach(function (node) { node.textContent = String(currentSwaps.length); });
    // Retire the hero/plan synopsis too, not just the individual card.
    document.querySelectorAll('[data-safety-synopsis]').forEach(function (node) {
      var retired = Array.from(document.querySelectorAll('[data-safety-card][data-was-current="true"]')).some(function (card) {
        return card.dataset.safetyStatus !== 'current';
      });
      if (retired) node.hidden = true;
    });
    document.querySelectorAll('[data-safety-link]').forEach(function (node) {
      var card = document.getElementById(node.dataset.safetyLink);
      node.hidden = !card || card.dataset.safetyStatus !== 'current';
    });
    var notice = document.querySelector('[data-runtime-safety-notice]');
    if (notice) {
      notice.hidden = n === cards.length;
      if (!notice.hidden) notice.textContent = n + ' currently usable line(s). Other cards are unresolved, closed or historical; their estimates and sources remain visible. No retired recommendation is automatically revived.';
    }
    document.dispatchEvent(new CustomEvent('spawn-pick-safety-updated'));
  }
  window.SpawnPickSafety = { state: state, fresh: fresh, refresh: refresh };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', refresh, { once: true });
  else refresh();
  window.setInterval(refresh, 30000);
  window.addEventListener('pageshow', refresh);
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });
}());
