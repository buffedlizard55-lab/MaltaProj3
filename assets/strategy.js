/* Marks fixtures as locked once their lock time passes. No network calls; the page is complete without it. */
(function () {
  'use strict';
  var cards = Array.prototype.slice.call(document.querySelectorAll('.pick-card[data-locks]'));
  var toggle = document.getElementById('hide-locked');
  function refresh() {
    var now = Date.now();
    cards.forEach(function (card) {
      var locks = Date.parse(card.getAttribute('data-locks') || '');
      var starts = Date.parse(card.getAttribute('data-starts') || '');
      var locked = (isFinite(locks) && now >= locks) || (isFinite(starts) && now >= starts) || card.getAttribute('data-availability') === 'locked';
      var status = card.querySelector('.status');
      card.classList.toggle('is-locked', locked);
      if (status) { status.hidden = !locked; }
      card.classList.toggle('is-hidden', locked && !!(toggle && toggle.checked));
    });
  }
  if (toggle) { toggle.addEventListener('change', refresh); }
  document.addEventListener('spawn-pick-safety-updated', refresh);
  window.addEventListener('pageshow', refresh);
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) refresh(); });
  refresh();
  window.setInterval(refresh, 30000);
}());
