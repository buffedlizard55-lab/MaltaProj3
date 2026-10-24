/* Presentation only: the findings register on /review/.
 *
 * Session arena-f43dc4f1. The register publishes ~300 findings and was the
 * longest page on the site with no way to find one of them on a phone. This
 * script only *hides* rows the reader has filtered out: every row is rendered
 * server-side and is visible with JavaScript disabled, no text is added,
 * removed or reworded, no source link changes, and there are no network calls.
 * The count it reports is the number of rows still shown, never a new claim.
 */
(function () {
  var input = document.getElementById('finding-search');
  var count = document.getElementById('finding-count');
  var table = document.querySelector('#findings table');
  if (!input || !table) return;

  var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
  var buttons = Array.prototype.slice.call(document.querySelectorAll('[data-finding-filter]'));
  var mode = 'all';

  function matches(row) {
    var severity = row.getAttribute('data-finding-severity') || 'review';
    // A superseded row is retained evidence, not an open finding: it stays
    // visible under 'All' and is never counted by the severity filters.
    if (mode === 'review' && severity !== 'review') return false;
    if (mode === 'notice' && severity !== 'notice') return false;
    var query = input.value.trim().toLowerCase();
    if (!query) return true;
    return (row.textContent || '').toLowerCase().indexOf(query) !== -1;
  }

  function apply() {
    var shown = 0;
    rows.forEach(function (row) {
      var keep = matches(row);
      // An inline style, not the `hidden` attribute: the mobile stylesheet sets
      // `display: block` on these rows and would beat the UA `[hidden]` rule.
      row.style.display = keep ? '' : 'none';
      if (keep) shown++;
    });
    if (count) {
      count.textContent = shown === rows.length
        ? rows.length + ' findings'
        : shown + ' of ' + rows.length + ' findings shown';
    }
  }

  input.addEventListener('input', apply);
  buttons.forEach(function (button) {
    button.addEventListener('click', function () {
      mode = button.getAttribute('data-finding-filter') || 'all';
      buttons.forEach(function (other) {
        other.setAttribute('aria-pressed', other === button ? 'true' : 'false');
      });
      apply();
    });
  });
})();
