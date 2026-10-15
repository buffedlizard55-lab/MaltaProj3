/* Marks fixtures as locked once their lock time passes. No network calls; the page is complete without it. */
(function () {
  'use strict';
  var cards = Array.prototype.slice.call(document.querySelectorAll('.pick-card[data-locks]'));
  var toggle = document.getElementById('hide-locked');
  function refresh() {
    var now = Date.now();
    cards.forEach(function (card) {
      var locks = Date.parse(card.getAttribute('data-locks') || '');
      var locked = isFinite(locks) && now >= locks;
      var status = card.querySelector('.status');
      card.classList.toggle('is-locked', locked);
      if (status) { status.hidden = !locked; }
      card.classList.toggle('is-hidden', locked && !!(toggle && toggle.checked));
    });
  }
  if (toggle) { toggle.addEventListener('change', refresh); }
  refresh();
  window.setInterval(refresh, 30000);
}());
