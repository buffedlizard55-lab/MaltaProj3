/* Presentation only, executive summary "Picks at a glance".
 * A row built while its fixture was still open keeps the label "Pick" until the next
 * rebuild. Once the viewer's clock passes that fixture's lock or start time, the label
 * becomes "Locked". The script can only close a pick, never reopen one, and it adds no
 * probability, pick, source link or fixture; the estimate and its links stay visible.
 * No network calls.
 */
(function () {
  'use strict';

  function time(value) {
    // Reject timezone-less clocks rather than interpreting them in the device timezone.
    if (typeof value !== 'string' || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) return NaN;
    return Date.parse(value);
  }

  function refresh() {
    var now = Date.now();
    var list = document.querySelector('#glance-list');
    document.querySelectorAll('li.glance-row[data-glance-locks]').forEach(function (row) {
      var label = row.querySelector('[data-glance-pick]');
      if (!label) return;
      var lock = time(row.getAttribute('data-glance-locks'));
      var start = time(row.getAttribute('data-glance-starts'));
      var closed = row.getAttribute('data-glance-closed') === 'true' ||
        (Number.isFinite(lock) && now >= lock) ||
        (Number.isFinite(start) && now >= start);
      if (!closed) return;
      label.textContent = 'Locked';
      label.classList.add('is-closed');
      row.classList.add('is-closed');
      row.setAttribute('data-glance-closed', 'true');
    });
    // Presentation only: after a snapshot ages, locked cards would otherwise
    // sit at the top of a phone. Move closed rows after still-open ones.
    // No probability, pick, source or fixture is changed.
    if (list) {
      Array.from(list.querySelectorAll('li.glance-row')).forEach(function (row) {
        if (row.classList.contains('is-closed') || row.getAttribute('data-glance-closed') === 'true') {
          list.appendChild(row);
        }
      });
    }
  }

  refresh();
  window.setInterval(refresh, 30000);
  window.addEventListener('pageshow', refresh);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) refresh();
  });
}());
