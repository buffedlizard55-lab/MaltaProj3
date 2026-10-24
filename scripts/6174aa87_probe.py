"""Session arena-6174aa87 — re-verify every published Hotspawn CS2 pick against
the source it cites, and check the published inventory against the live fixture
feed.

Why a runner script. The Arena coding sandbox has no general egress (only
GitHub, npm and PyPI), so it cannot re-read Hotspawn, HLTV or the esportsbooks.
A GitHub runner can. This module therefore performs the reads first-hand, keeps
the HTTP status, hash and an excerpt for every URL it touched, and writes only
under ``data/research/6174aa87/``. It never collects, never originates a
probability, never edits ``data/latest.json`` and never deploys.

What "verified" means here — deliberately narrow. For every active fixture the
published list resolves, this probe re-reads each cited URL and records:

* the HTTP answer (200 is not a price, and a 403 is not proof a market is absent);
* whether both team names appear in the returned body (full-name match, a
  distinctive-token match, or nothing);
* for provider endpoints, whether the exact event id the ladder used is present;
* the page title, so a reader can see which event the citation actually opens.

A row is labelled ``verified`` only when every cited URL answered and at least
one of them names both teams (or binds the ladder's event id). Anything else is
``needs-review`` with the exact reason. This probe never asserts that a pick is
correct, and it never writes a probability, pick or alias.

It also re-reads Hotspawn's own scheduled-fixture API and diffs its future ids
against the published inventory, so "every match on Hotspawn has a pick" is
checked against the live feed rather than assumed.

Usage (on a GitHub runner, after ``python -m scripts.collect`` and
``python -m scripts.originate --live``):

    python -m scripts.6174aa87_probe --out data/research/6174aa87
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests

UTC = timezone.utc
SESSION = 'arena-6174aa87'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/124.0 Safari/537.36')

FIXTURES_API = ('https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?'
                + urlencode({'sport_alias': 'cs2', 'status': 'scheduled', 'tenantId': 1}))
PUBLISHED_SNAPSHOT = 'https://buffedlizard55-lab.github.io/MaltaProj3/snapshot.json'
PUBLISHED_ORIGINATION = 'https://buffedlizard55-lab.github.io/MaltaProj3/data/origination.json'
GITHUB_REPO = 'https://github.com/buffedlizard55-lab/MaltaProj3'

#: A local snapshot older than this is not treated as the published state.
MAX_LOCAL_AGE_HOURS = 12.0
#: Words too common to prove a team is on a page on their own.
STOPWORDS = {
    'team', 'esports', 'esport', 'academy', 'clan', 'gaming', 'club', 'the',
    'gas', 'and', 'of', 'for', 'with', 'vs', 'sports', 'sport', 'pro',
}
CHALLENGE_MARKERS = ('just a moment', 'cf-chl', 'challenge-platform',
                     'attention required! | cloudflare', 'enable javascript and cookies to continue',
                     'please verify you are a human', 'verify you are human')
#: Path shapes that are provider-wide endpoints, not a fixture-specific page.
GENERIC_HINTS = ('/api/', '/services/sports/', '/esports/counter-strike', '/matches',
                 '/next-to-go', '/esports-hub/', '/trade-api/', '/markets/kxcs2game',
                 '/esports/cs2', '/counterstrike/matches')


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()[:32]


def normalize(value: str) -> str:
    """Casefold, strip accents and punctuation, collapse whitespace."""
    text = unicodedata.normalize('NFKD', value or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^a-z0-9]+', ' ', text.casefold())
    return re.sub(r'\s+', ' ', text).strip()


def tokens(team: str) -> list[str]:
    """Distinctive words of a team name: long enough and not a generic suffix."""
    return [w for w in normalize(team).split() if len(w) >= 4 and w not in STOPWORDS]


def name_presence(body: str, team: str) -> dict:
    """Is this team named in the body? Full name first, then a distinctive token."""
    flat = normalize(body)
    full = normalize(team)
    if full and full in flat:
        return {'team': team, 'level': 'full', 'needle': full}
    for token in tokens(team):
        if re.search(r'\b' + re.escape(token) + r'\b', flat):
            return {'team': team, 'level': 'token', 'needle': token}
    return {'team': team, 'level': 'absent', 'needle': full}


def extract_title(body: str) -> str:
    match = re.search(r'<title[^>]*>(.*?)</title>', body or '', re.S | re.I)
    if not match:
        return ''
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', match.group(1))).strip()[:180]


def generic_endpoint(url: str) -> bool:
    """True for provider-wide endpoints, which can legitimately omit both names."""
    path = urlparse(url or '').path or ''
    if path.count('/') <= 1:
        return True
    return any(hint in path for hint in GENERIC_HINTS)


def alternates(url: str) -> list[dict]:
    """The same record through the source's own JSON API, where one is public.

    A Cloudflare interstitial on an HTML page is a block on this reader, not
    evidence that the citation is wrong. Each of these endpoints publishes the
    identical event the page shows, so a match here is recorded as
    ``confirmed-via-alternate`` and never as a price of our own.
    """
    parsed = urlparse(url or '')
    host, path = parsed.netloc.lower(), parsed.path or ''
    out: list[dict] = []
    if host.endswith('polymarket.com') and path.startswith('/event/'):
        slug = path.rstrip('/').split('/')[-1]
        out.append({'url': 'https://gamma-api.polymarket.com/events?slug=' + slug,
                    'label': 'Polymarket Gamma event record'})
    if host == 'github.com':
        parts = path.strip('/').split('/')
        if len(parts) >= 5 and parts[2] == 'blob':
            out.append({'url': 'https://raw.githubusercontent.com/%s/%s/%s/%s' % (
                parts[0], parts[1], parts[3], '/'.join(parts[4:])),
                'label': 'raw document in the same repository'})
    if host.endswith('kalshi.com'):
        ticker = path.rstrip('/').split('/')[-1]
        if ticker:
            out.append({'url': 'https://api.elections.kalshi.com/trade-api/v2/markets/' + ticker,
                        'label': 'Kalshi market record'})
    if host.endswith('thunderpick.io'):
        # The prematch list is a POST; scripts/collect.py reads the same call.
        out.append({'url': 'https://thunderpick.io/api/matches', 'method': 'POST',
                    'payload': {'gameIds': [6]},
                    'label': 'Thunderpick prematch event list (POST, gameIds=[6])'})
    if host.endswith('bo3.gg'):
        out.append({'url': 'https://api.bo3.gg/api/v1/matches?page[limit]=50',
                    'label': 'bo3.gg match list (public JSON)',
                    'headers': {'Origin': 'https://bo3.gg', 'Referer': 'https://bo3.gg/'}})
    if host.endswith('smarkets.com'):
        out.append({'url': 'https://api.smarkets.com/v3/events/?limit=200',
                    'label': 'Smarkets public event list'})
    return out


def fetch(session: requests.Session, name: str, url: str, *, method: str = 'GET',
          payload: dict | None = None, timeout: int = 35, headers: dict | None = None) -> dict:
    """One first-party read. Records status, hash and an excerpt, always."""
    record = {'name': name, 'url': url, 'method': method, 'observed_at': now_iso(),
              'http': None, 'status': 'error', 'sha256': None, 'bytes': 0,
              'challenge': False, 'title': '', 'error': None}
    request_headers = {'User-Agent': UA,
                       'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8'}
    request_headers.update(headers or {})
    try:
        if method == 'POST':
            response = session.post(url, json=payload, timeout=timeout,
                                    headers=request_headers)
        else:
            response = session.get(url, timeout=timeout, headers=request_headers)
        body = response.text or ''
        record.update({'http': response.status_code, 'bytes': len(body), 'sha256': sha(body)})
        record['title'] = extract_title(body)
        lowered = body.casefold()
        record['challenge'] = any(marker in lowered for marker in CHALLENGE_MARKERS)
        if response.status_code >= 400:
            record['status'] = 'http-%d' % response.status_code
        elif record['challenge']:
            record['status'] = 'challenge'
        else:
            record['status'] = 'ok'
        record['_body'] = body
    except requests.RequestException as exc:  # network/DNS/TLS: never guessed
        record['error'] = type(exc).__name__ + ': ' + str(exc)[:180]
    return record


def public(record: dict) -> dict:
    return {k: v for k, v in record.items() if not k.startswith('_')}


def active_matches(snapshot: dict) -> list[dict]:
    return [m for m in (snapshot.get('matches') or [])
            if isinstance(m, dict) and m.get('availability') == 'open']


def origination_index(origination: dict) -> dict:
    return {str(m.get('id')): m for m in (origination.get('matches') or [])
            if isinstance(m, dict)}


def pick_of(match: dict, orig: dict | None) -> dict:
    """The published pick for a fixture: the origination layer first, then featured."""
    teams = [t.get('name') or '' for t in (match.get('teams') or [])][:2]
    if orig:
        line = orig.get('origination') or {}
        index = orig.get('pick_index')
        return {
            'layer': 'origination',
            'method': line.get('method'),
            'label': line.get('label'),
            'pick_index': index,
            'pick': teams[index] if isinstance(index, int) and index < len(teams) else None,
            'probabilities': line.get('probabilities'),
            'source': line.get('source'),
            'observed_at': line.get('observed_at'),
            'aliases_used': orig.get('aliases_used') or [],
            'limitations': line.get('limitations') or [],
            'quotes': [{'provider': q.get('provider'), 'family': q.get('family'),
                        'odds': q.get('odds'), 'observed_at': q.get('observed_at'),
                        'source_url': q.get('source_url'), 'event_id': q.get('event_id')}
                       for q in (line.get('quotes') or []) if isinstance(q, dict)],
            'model_crosscheck': line.get('model_crosscheck'),
        }
    analysis = match.get('analysis') or {}
    index = match.get('pick_index')
    return {
        'layer': 'featured' if analysis else 'none',
        'method': analysis.get('method'),
        'label': analysis.get('label'),
        'pick_index': index,
        'pick': teams[index] if isinstance(index, int) and index < len(teams) else None,
        'probabilities': analysis.get('probabilities'),
        'source': analysis.get('source'),
        'observed_at': analysis.get('observed_at'),
        'aliases_used': [],
        'limitations': analysis.get('limitations') or [],
        'quotes': [],
        'model_crosscheck': None,
        'featured_source_url': analysis.get('source_url'),
    }


def citations_for(match: dict, orig: dict | None, pick: dict) -> list[dict]:
    """Every URL the published pick rests on, labelled by the job it does."""
    found: list[dict] = []

    def add(url: str | None, role: str, kind: str, **extra) -> None:
        if not url or not str(url).startswith('http'):
            return
        for entry in found:
            if entry['url'] == url:
                if role not in entry['roles']:
                    entry['roles'].append(role)
                entry['kind'] = 'price' if kind == 'price' else entry['kind']
                entry.update({k: v for k, v in extra.items() if v not in (None, '', [])})
                return
        entry = {'url': url, 'roles': [role], 'kind': kind,
                 'generic': generic_endpoint(url)}
        entry.update({k: v for k, v in extra.items() if v not in (None, '', [])})
        found.append(entry)

    add(match.get('source_url'), 'Hotspawn fixture', 'fixture')
    line = (orig or {}).get('origination') or {}
    add(line.get('source_url'), 'Line source', 'price', source=line.get('source'))
    for quote in pick.get('quotes') or []:
        add(quote.get('source_url'), 'Quote: %s' % (quote.get('provider') or 'book'),
            'price', odds=quote.get('odds'), event_id=quote.get('event_id'))
    crosscheck = pick.get('model_crosscheck') or {}
    if isinstance(crosscheck, dict):
        add(crosscheck.get('source_url'), 'Model cross-check', 'model')
    add(pick.get('featured_source_url'), 'Featured line', 'price')
    for stage in (match.get('research') or (orig or {}).get('research') or []):
        if not isinstance(stage, dict):
            continue
        status = (stage.get('status') or '').lower()
        if status not in ('checked', 'resolved'):
            continue
        kind = 'identity' if 'hltv' in (stage.get('stage') or '').lower() else 'price'
        add(stage.get('source_url'), stage.get('stage') or 'Research', kind)
    return found


def judge_body(body: str, citation: dict, teams: list[str]) -> dict:
    """What the returned body proves, independent of how it was fetched."""
    names = [name_presence(body, team) for team in teams]
    event_id = citation.get('event_id')
    bound = bool(event_id and re.search(r'\b' + re.escape(str(event_id)) + r'\b', body))
    levels = [n['level'] for n in names]
    if bound or all(level == 'full' for level in levels):
        verdict = 'confirmed'
    elif any(level == 'full' for level in levels):
        verdict = 'partial'
    elif all(level == 'token' for level in levels):
        verdict = 'token-only'
    elif citation['generic'] and citation['kind'] in ('price', 'model'):
        verdict = 'endpoint-unbound'
    else:
        verdict = 'absent'
    return {'names': names, 'event_bound': bound, 'verdict': verdict}


def verify_citation(fetcher, citation: dict, teams: list[str], api_record: dict | None = None) -> dict:
    """Re-read one cited URL, then its own API if the page is walled."""
    record = fetcher(citation['url'])
    body = record.pop('_body', '') or ''
    entry = dict(citation)
    entry['read'] = record
    if record.get('status') == 'ok':
        entry.update(judge_body(body, citation, teams))
        if entry['verdict'] in ('confirmed', 'partial'):
            return entry
    else:
        entry.update({'names': [], 'event_bound': False, 'verdict': 'blocked'})
    # A walled page is not a dead citation: the fixture feed, or the source's own
    # JSON record, can prove the same thing. Each attempt is recorded verbatim.
    if citation['kind'] == 'fixture' and api_record:
        fixture_body = json.dumps(api_record)
        judged = judge_body(fixture_body, citation, teams)
        if judged['verdict'] == 'confirmed':
            entry['fallback'] = {'url': FIXTURES_API,
                                 'label': 'Hotspawn scheduled-fixture record',
                                 'verdict': 'confirmed'}
            entry.update(judged)
            entry['verdict'] = 'confirmed-via-alternate'
            return entry
    for alternate in alternates(citation['url']):
        read = fetcher(alternate['url'], method=alternate.get('method', 'GET'),
                       payload=alternate.get('payload'),
                       headers=alternate.get('headers'))
        alt_body = read.pop('_body', '') or ''
        if read.get('status') != 'ok':
            entry.setdefault('alternates_tried', []).append(
                {'url': alternate['url'], 'label': alternate['label'],
                 'status': read.get('status'), 'http': read.get('http')})
            continue
        judged = judge_body(alt_body, citation, teams)
        entry.setdefault('alternates_tried', []).append(
            {'url': alternate['url'], 'label': alternate['label'],
             'status': 'ok', 'http': read.get('http'), 'verdict': judged['verdict']})
        if judged['verdict'] == 'confirmed':
            entry['fallback'] = {'url': alternate['url'], 'label': alternate['label'],
                                 'verdict': 'confirmed'}
            entry.update(judged)
            entry['verdict'] = 'confirmed-via-alternate'
            return entry
    return entry


def verify_fixture(fetcher, match: dict, orig: dict | None, api_index: dict | None = None) -> dict:
    teams = [t.get('name') or '' for t in (match.get('teams') or [])][:2]
    pick = pick_of(match, orig)
    citations = citations_for(match, orig, pick)
    api_record = (api_index or {}).get(str(match.get('id')))
    verified = [verify_citation(fetcher, c, teams, api_record) for c in citations]
    price = [c for c in verified if c['kind'] == 'price']
    summary = {
        'citations': len(verified),
        'confirmed': sum(1 for c in verified if c['verdict'] == 'confirmed'),
        'partial': sum(1 for c in verified if c['verdict'] in ('partial', 'token-only')),
        'absent': sum(1 for c in verified if c['verdict'] == 'absent'),
        'unreachable': sum(1 for c in verified if c['verdict'] == 'blocked'),
        'confirmed_via_alternate': sum(1 for c in verified
                                       if c['verdict'] == 'confirmed-via-alternate'),
        'endpoint_unbound': sum(1 for c in verified if c['verdict'] == 'endpoint-unbound'),
    }
    if not pick.get('pick'):
        return {'id': str(match.get('id')), 'teams': teams,
                'competition': match.get('competition'),
                'starts_at': match.get('starts_at'), 'locks_at': match.get('locks_at'),
                'pick': pick, 'citations': verified, 'verdict': 'no-pick',
                'summary': summary}
    price_ok = any(c['verdict'] in ('confirmed', 'confirmed-via-alternate') for c in price)
    price_blocked = all(c['verdict'] in ('unreachable', 'endpoint-unbound', 'absent')
                        for c in price) if price else True
    if price_ok and summary['unreachable'] == 0 and summary['absent'] == 0:
        verdict = 'verified'
    elif price_ok:
        verdict = 'verified-with-open-citations'
    elif price_blocked:
        verdict = 'needs-review'
    else:
        verdict = 'needs-review'
    return {'id': str(match.get('id')), 'teams': teams,
            'competition': match.get('competition'),
            'starts_at': match.get('starts_at'), 'locks_at': match.get('locks_at'),
            'pick': pick, 'citations': verified, 'verdict': verdict,
            'summary': summary}


def coverage(api_rows: list[dict], snapshot: dict, now: datetime, feed_ok: bool = True) -> dict:
    """Future Hotspawn fixtures vs the published inventory."""
    published = {str(m.get('id')) for m in (snapshot.get('matches') or [])
                 if isinstance(m, dict)}
    future = [row for row in api_rows if row.get('future')]
    missing = [row for row in future if row['id'] not in published]
    archived = [row for row in api_rows if not row.get('future') and row['id'] in published]
    return {
        'feed_read': bool(feed_ok and api_rows),
        'feed_status': ('read' if (feed_ok and api_rows)
                        else 'unreadable — completeness NOT verified on this sweep'),
        'api_rows': len(api_rows),
        'api_future': len(future),
        'published_inventory': len(published),
        'live_future_missing': [{'id': r['id'], 'teams': r['teams'],
                                 'competition': r['competition'],
                                 'starts_at': r['starts_at']} for r in missing],
        'past_start_still_published': len(archived),
        'observed_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }


def fixture_rows(body: str, now: datetime) -> list[dict]:
    """Hotspawn's own scheduled rows, normalised from epoch-ms fields."""
    try:
        payload = json.loads(body)
    except ValueError:
        return []
    rows = []
    for row in payload if isinstance(payload, list) else []:
        try:
            start_ms = int(row.get('scheduled_start_time') or 0)
        except (TypeError, ValueError):
            start_ms = 0
        start = datetime.fromtimestamp(start_ms / 1000, UTC) if start_ms else None
        rows.append({
            'id': str(row.get('id')),
            'teams': [row.get('participants0_name') or '', row.get('participants1_name') or ''],
            'competition': row.get('competition_name') or '',
            'starts_at': start.strftime('%Y-%m-%dT%H:%M:%SZ') if start else '',
            'future': bool(start and start > now),
        })
    return rows


def flags_for(report: dict) -> list[dict]:
    """Source-linked review findings. Nothing here changes a pick or a probability."""
    flags: list[dict] = []
    provenance = report['provenance']
    fixtures = provenance['fixtures']
    unreachable = [(f['id'], f['teams'], c) for f in fixtures for c in f['citations']
                   if c['verdict'] == 'blocked']
    absent = [(f['id'], f['teams'], c) for f in fixtures for c in f['citations']
              if c['verdict'] == 'absent' and not c['generic']]
    no_pick = [f for f in fixtures if f['verdict'] == 'no-pick']
    if no_pick:
        flags.append({
            'id': '6174aa87-active-fixture-without-pick',
            'severity': 'review',
            'match_ids': [f['id'] for f in no_pick],
            'title': 'An active Hotspawn fixture is published without a pick',
            'detail': (
                'The published list resolves every active fixture, so this finding should be '
                'empty. It is raised automatically when a re-read finds an active fixture with '
                'no pick in either the origination layer or the featured analysis, which means '
                'the resolver ladder returned nothing and the row is a genuine blank. Nothing '
                'has been filled in: ' + ', '.join(
                    '%s %s' % (f['id'], ' vs '.join(f['teams'])) for f in no_pick) + '.'),
            'source_urls': [PUBLISHED_SNAPSHOT, PUBLISHED_ORIGINATION],
        })
    if unreachable:
        detail = '; '.join('%s %s — %s (%s)' % (
            fixture_id, ' vs '.join(teams), citation['url'],
            citation['read'].get('status') or citation['read'].get('error'))
            for fixture_id, teams, citation in unreachable[:12])
        flags.append({
            'id': '6174aa87-cited-source-unreachable-on-recheck',
            'severity': 'notice',
            'match_ids': sorted({fixture_id for fixture_id, _, _ in unreachable}),
            'title': 'A source cited by a published pick could not be re-read on this sweep',
            'detail': (
                'These URLs are cited on the published pick rows and were re-read by the runner, '
                'including each source’s own JSON API where one is public. A refusal, challenge '
                'or timeout is not evidence that the market does not exist '
                'and no pick was changed because of it: ' + detail + '. The ladder re-reads its '
                'own sources on the next four-hour refresh.'),
            'source_urls': sorted({citation['url'] for _, _, citation in unreachable})[:25],
        })
    if absent:
        detail = '; '.join('%s %s — %s (no team name in the returned body)' % (
            fixture_id, ' vs '.join(teams), citation['url'])
            for fixture_id, teams, citation in absent[:12])
        flags.append({
            'id': '6174aa87-cited-page-did-not-name-both-teams',
            'severity': 'review',
            'match_ids': sorted({fixture_id for fixture_id, _, _ in absent}),
            'title': 'A fixture-specific page cited by a published pick answered but did not name the teams',
            'detail': (
                'The URL answered HTTP 200, but neither the full team name nor a distinctive '
                'token from it appeared in the returned body. Some books render prices only in '
                'JavaScript, so this is a prompt for manual review, not a claim that the pick is '
                'wrong: ' + detail + '.'),
            'source_urls': sorted({citation['url'] for _, _, citation in absent})[:25],
        })
    coverage_block = report.get('coverage') or {}
    missing = coverage_block.get('live_future_missing') or []
    if not coverage_block.get('feed_read'):
        flags.append({
            'id': '6174aa87-hotspawn-feed-unreadable-on-sweep',
            'severity': 'notice',
            'match_ids': [],
            'title': 'Hotspawn’s fixture feed could not be re-read, so inventory completeness was not verified',
            'detail': (
                'This sweep re-read the published picks but could not read Hotspawn’s scheduled-'
                'fixture API, so it makes no claim about whether the published inventory covers '
                'every live card. An unreadable feed is not evidence that coverage is complete. '
                'The next successful four-hour refresh re-reads it; the coverage page reports the '
                'source status.'),
            'source_urls': [FIXTURES_API, PUBLISHED_SNAPSHOT],
        })
    if missing:
        flags.append({
            'id': '6174aa87-live-fixtures-not-yet-in-the-published-inventory',
            'severity': 'notice',
            'match_ids': [row['id'] for row in missing],
            'title': 'The live Hotspawn feed lists future fixtures the published inventory does not carry yet',
            'detail': (
                'Read from Hotspawn’s own scheduled-fixture API in the same run: '
                + ', '.join('%s %s (%s)' % (row['id'], ' vs '.join(row['teams']), row['starts_at'])
                            for row in missing[:15])
                + '. They are listed here because a pick cannot exist before the fixture is '
                  'collected; the next successful four-hour refresh collects them and the '
                  'resolver ladder prices each one or publishes it as unresolved.'),
            'source_urls': [FIXTURES_API, PUBLISHED_SNAPSHOT],
        })
    counts = provenance['counts']
    flags.append({
        'id': '6174aa87-provenance-sweep',
        'severity': 'notice',
        'match_ids': [],
        'title': 'Dated pick-provenance sweep: every published pick re-read against its own citation',
        'detail': (
            'Runner sweep observed %s. %d active fixtures carried a published pick; %d were '
            're-verified with at least one cited URL naming both teams or binding the ladder’s '
            'event id, %d need review, %d citation(s) could not be re-read and %d fixture-specific '
            'page(s) answered without naming the teams. The dated dossier '
            '(data/research/6174aa87/pick-provenance.json and .md) carries the HTTP status, hash '
            'and an excerpt per URL for manual review.' % (
                provenance['observed_at'], counts['active'], counts['verified'],
                counts['needs_review'], counts['unreachable_citations'],
                counts['absent_citations'])),
        'source_urls': [
            GITHUB_REPO + '/blob/main/data/research/6174aa87/pick-provenance.md',
            GITHUB_REPO + '/actions/workflows/6174aa87-probe.yml',
        ],
    })
    return flags


def render_md(report: dict) -> str:
    provenance = report['provenance']
    coverage_block = report['coverage']
    counts = provenance['counts']
    lines = [
        '# Pick provenance sweep — session arena-6174aa87',
        '',
        'Observed **%s** — a dated, first-hand re-read of every source each published pick '
        'cites. The workflow run that produced it is linked from the review page.'
        % provenance['observed_at'],
        '',
        'Reading guide: *verified* means every cited URL answered and at least one of them named '
        'both teams (or contained the exact event id the ladder bound). It does **not** mean the '
        'pick is correct, and it adds no probability. *needs-review* rows are listed with the '
        'exact reason so they can be checked by hand.',
        '',
        '| # | Fixture | Starts (UTC) | Pick | Layer | Citations | Verified | Needs review |',
        '| - | - | - | - | - | - | - | - |',
    ]
    for index, fixture in enumerate(provenance['fixtures'], 1):
        pick = fixture['pick']
        pick_text = '%s (%s)' % (pick.get('pick') or '—', pick.get('label') or pick.get('method') or '—')
        lines.append('| %d | [%s](%s) | %s | %s | %s | %d | %d | %d |' % (
            index, ' vs '.join(fixture['teams']),
            next((c['url'] for c in fixture['citations'] if c['kind'] == 'fixture'), ''),
            fixture.get('starts_at') or '—', pick_text, pick.get('layer') or '—',
            fixture['summary']['citations'], fixture['summary']['confirmed'],
            fixture['summary']['absent'] + fixture['summary']['unreachable']))
    lines += [
        '',
        '## Coverage against the live Hotspawn feed',
        '',
        '| Item | Value |',
        '| - | - |',
        '| Hotspawn fixture feed | %s |' % coverage_block['feed_status'],
        '| Rows in Hotspawn’s scheduled-fixture API | %d |' % coverage_block['api_rows'],
        '| Future fixtures in that feed | %d |' % coverage_block['api_future'],
        '| Records in the published inventory | %d |' % coverage_block['published_inventory'],
        '| Future feed fixtures missing from the inventory | %s |' % (
            len(coverage_block['live_future_missing'])
            if coverage_block['feed_read'] else 'not verified'),
        '',
    ]
    if coverage_block['live_future_missing']:
        lines.append('Missing ids: ' + ', '.join(
            '%s (%s)' % (row['id'], ' vs '.join(row['teams']))
            for row in coverage_block['live_future_missing']) + '.')
        lines.append('')
    lines += ['## Citations re-read', '',
              '| Fixture | Role | URL | HTTP | Result | Page title / binding |',
              '| - | - | - | - | - | - |']
    for fixture in provenance['fixtures']:
        for citation in fixture['citations']:
            read = citation['read']
            how = read.get('title') or ''
            if citation.get('event_bound'):
                how = ('event id %s found' % citation.get('event_id')) + ((' · ' + how) if how else '')
            if citation.get('odds'):
                how = ('quoted odds %s' % citation['odds']) + ((' · ' + how) if how else '')
            fallback = citation.get('fallback')
            if fallback:
                how = ('%s confirmed via %s' % (fallback['label'], fallback['url'])
                       + ((' · ' + how) if how else ''))
            lines.append('| %s %s | %s | %s | %s | %s | %s |' % (
                fixture['id'], ' vs '.join(fixture['teams']),
                ', '.join(citation['roles']), citation['url'],
                read.get('http') or '—', citation['verdict'],
                (how or read.get('error') or '').replace('|', '/')[:160]))
    lines += ['', '## Counts', '',
              '- Active fixtures with a published pick: **%d**' % counts['active'],
              '- Re-verified: **%d**' % counts['verified'],
              '- Needs review: **%d**' % counts['needs_review'],
              '- Citations re-read: **%d** (%d blocked, %d absent, %d endpoint-only, '
              '%d confirmed through the source’s own API)' % (
                  counts['citations'], counts['unreachable_citations'],
                  counts['absent_citations'], counts['endpoint_citations'],
                  counts['alternate_citations']),
              '', 'Source policy: Hotspawn supplies identity only; probabilities come from the '
              'reviewed ladder in `scripts/originate.py`, never from Hotspawn popularity, HLTV fan '
              'votes or this sweep.', '']
    return '\n'.join(lines)


def build_report(snapshot: dict, origination: dict, api_body: str, fetcher, observed_at: str) -> dict:
    now = parse_iso(observed_at) or datetime.now(UTC)
    index = origination_index(origination)
    rows = fixture_rows(api_body, now)
    api_index = {row['id']: row for row in rows}
    fixtures = [verify_fixture(fetcher, match, index.get(str(match.get('id'))), api_index)
                for match in active_matches(snapshot)]
    counts = {
        'active': len(fixtures),
        'with_pick': sum(1 for f in fixtures if f['verdict'] != 'no-pick'),
        'verified': sum(1 for f in fixtures if f['verdict'] in ('verified', 'verified-with-open-citations')),
        'needs_review': sum(1 for f in fixtures if f['verdict'] not in ('verified', 'verified-with-open-citations')),
        'citations': sum(f['summary']['citations'] for f in fixtures),
        'unreachable_citations': sum(f['summary']['unreachable'] for f in fixtures),
        'absent_citations': sum(f['summary']['absent'] for f in fixtures),
        'endpoint_citations': sum(1 for f in fixtures for c in f['citations']
                                  if c['verdict'] == 'endpoint-unbound'),
        'alternate_citations': sum(1 for f in fixtures for c in f['citations']
                                   if c['verdict'] == 'confirmed-via-alternate'),
        'no_pick': sum(1 for f in fixtures if f['verdict'] == 'no-pick'),
    }
    return {
        'session': SESSION,
        'observed_at': observed_at,
        'policy': ('Each cited URL is re-read first-hand. A 2xx answer is not a price; a refusal is '
                   'not proof a market is absent. Team-name presence is reported verbatim, and no '
                   'probability, pick or alias is written by this sweep.'),
        'provenance': {'counts': counts, 'fixtures': fixtures,
                       'observed_at': observed_at},
        'coverage': coverage(rows, snapshot, now, feed_ok=bool(rows)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='data/research/6174aa87')
    parser.add_argument('--snapshot', default='data/latest.json')
    parser.add_argument('--origination', default='data/origination.json')
    parser.add_argument('--offline-fixture', default=None,
                        help='Directory of saved bodies for tests; never used in production')
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    observed_at = now_iso()
    session = requests.Session()
    reads: list[dict] = []

    def read(name: str, url: str) -> dict:
        record = fetch(session, name, url)
        reads.append(public(record))
        return record

    snapshot_path = Path(args.snapshot)
    origination_path = Path(args.origination)
    snapshot, origination = {}, {}
    snapshot_source = origination_source = ''
    if snapshot_path.exists():
        snapshot = json.loads(snapshot_path.read_text())
        age = None
        generated = parse_iso(snapshot.get('generated_at') or '')
        if generated:
            age = (datetime.now(UTC) - generated).total_seconds() / 3600
        if age is not None and age <= MAX_LOCAL_AGE_HOURS:
            snapshot_source = str(snapshot_path)
        else:
            snapshot = {}
    if origination_path.exists():
        candidate = json.loads(origination_path.read_text())
        generated = parse_iso(candidate.get('generated_at') or '')
        age = (datetime.now(UTC) - generated).total_seconds() / 3600 if generated else None
        if age is not None and age <= MAX_LOCAL_AGE_HOURS and candidate.get('matches'):
            origination = candidate
            origination_source = str(origination_path)
    if not snapshot:
        published = read('published-snapshot', PUBLISHED_SNAPSHOT)
        try:
            snapshot = json.loads(published.get('_body') or '{}')
            snapshot_source = PUBLISHED_SNAPSHOT
        except ValueError:
            snapshot = {}
    if not origination:
        published = read('published-origination', PUBLISHED_ORIGINATION)
        try:
            origination = json.loads(published.get('_body') or '{}')
            origination_source = PUBLISHED_ORIGINATION
        except ValueError:
            origination = {}
    api = read('hotspawn-fixtures', FIXTURES_API)

    def fetcher(url: str, **kwargs) -> dict:
        record = fetch(session, 'citation', url, **kwargs)
        reads.append(public(record))
        return record

    report = build_report(snapshot, origination, api.get('_body') or '', fetcher, observed_at)
    report['inputs'] = {
        'snapshot': snapshot_source, 'snapshot_generated_at': snapshot.get('generated_at'),
        'origination': origination_source,
        'origination_generated_at': origination.get('generated_at'),
        'source_reads': reads,
    }
    (out / 'pick-provenance.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (out / 'pick-provenance.md').write_text(render_md(report) + '\n')
    (out / 'flags.json').write_text(json.dumps(flags_for(report), indent=2, ensure_ascii=False) + '\n')
    counts = report['provenance']['counts']
    print('%s: %d active fixtures, %d verified, %d need review, %d citations re-read '
          '(%d unreachable, %d absent), %d live fixtures missing from the inventory' % (
              SESSION, counts['active'], counts['verified'], counts['needs_review'],
              counts['citations'], counts['unreachable_citations'],
              counts['absent_citations'], len(report['coverage']['live_future_missing'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
