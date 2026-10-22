/* Publish Playwright failures as GitHub Actions error annotations.
 *
 * Why: on 2026-10-22 every branch's `checks.yml` run since 08:28Z failed at
 * "Phone, desktop, no-JS, staleness and WCAG A/AA checks" and the only public
 * trace was "Process completed with exit code 1". The job log download host is
 * intermittently unreachable, so nobody could read which assertion failed and
 * the whole pipeline stayed red. The Python step already publishes its
 * FAIL/ERROR lines as annotations; this reporter gives the browser step the
 * same visibility.
 *
 * It prints one ::error per failed or flaky test, plus the first line of the
 * error, so the run page itself names the failing spec. It never changes a
 * test's status: Playwright still reports it, and the exit code is untouched.
 */

const ESCAPE = new Map([['%', '%25'], ['\r', '%0D'], ['\n', '%0A']]);
const escape = value => String(value).replace(/[%\r\n]/g, ch => ESCAPE.get(ch));

export default class AnnotationsReporter {
  constructor() {
    this.failures = [];
  }

  onTestEnd(test, result) {
    if (result.status !== 'failed' && result.status !== 'timedOut' && result.status !== 'interrupted') return;
    const error = result.error?.message || result.errors?.[0]?.message || 'no error message';
    this.failures.push({
      title: `${result.status}: ${test.title}`.slice(0, 250),
      message: error.split('\n').map(line => line.trim()).filter(Boolean)[0] || 'no error message',
      location: `${test.location.file}:${test.location.line}`,
    });
  }

  onEnd() {
    if (!this.failures.length) return;
    for (const failure of this.failures) {
      console.log(`::error title=${escape(failure.title)}::${escape(failure.message)} (${escape(failure.location)})`);
    }
    const summary = this.failures.map(f => `- ${f.title} — ${f.message} (${f.location})`).join('\n');
    console.log(`::notice title=${escape(`playwright: ${this.failures.length} failing test(s)`)}::${escape(summary)}`);
  }
}
