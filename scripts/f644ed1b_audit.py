"""Snapshot safety checks independent of any dated fixture roster.

Checks captured evidence, not live provider availability or model calibration.
Run: python -m scripts.f644ed1b_audit --snapshot snapshot.json --output report.json
"""
import argparse
from datetime import datetime
import json
import math
from urllib.parse import urlsplit
from pathlib import Path


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('UTC offset required')
    return parsed


def external_source(url):
    try:
        u = urlsplit(url)
        host = (u.hostname or '').lower()
        return (u.scheme == 'https' and bool(host) and not u.username and not u.password
                and not any(host == h or host.endswith('.' + h) for h in
                            ('hotspawn.com', 'cloudwaysapps.com', 'localhost')))
    except (ValueError, TypeError):
        return False


def audit(snapshot):
    rows, errors = [], []
    clock = timestamp(snapshot['generated_at'])
    ids = [m['id'] for m in snapshot['matches']]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate fixture IDs')
    for m in snapshot['matches']:
        if m['availability'] == 'past':
            continue
        problems = []
        a = m.get('analysis')
        if not m.get('source_url', '').startswith('https://'):
            problems.append('Missing fixture source')
        if a:
            p = a.get('probabilities', [])
            if (len(p) != 2 or any(isinstance(x, bool) or not isinstance(x, (float, int))
                                  or not math.isfinite(x) or not 0 < x < 1 for x in p)
                    or not math.isclose(sum(p), 1, abs_tol=1e-6)):
                problems.append('Invalid probability pair')
            elif m.get('pick_index') != (0 if p[0] > p[1] else 1 if p[1] > p[0] else None):
                problems.append('Pick does not match favourite')
            if not external_source(a.get('source_url')):
                problems.append('Missing external probability source')
            try:
                observed = timestamp(a['observed_at'])
                if observed > clock:
                    problems.append('Evidence postdates snapshot')
            except (KeyError, ValueError, TypeError, AttributeError):
                problems.append('Invalid evidence timestamp')
            for q in a.get('quotes', []):
                if a.get('method') == 'market':
                    bid, ask = q.get('bid'), q.get('ask')
                    if (not isinstance(bid, (int, float)) or not isinstance(ask, (int, float))
                            or not 0 < bid <= ask < 1):
                        problems.append('Non-actionable exchange quote')
            if a.get('method') == 'model' and not a.get('limitations'):
                problems.append('Model lacks limitations')
        elif m.get('pick_index') is not None or not m.get('limitations') or not m.get('research'):
            problems.append('Unresolved fixture lacks blank pick, limitations or research')
        rows.append({'id': m['id'], 'teams': [t['name'] for t in m['teams']],
                     'method': a.get('method') if a else 'unresolved',
                     'source_url': a.get('source_url') if a else m['source_url'],
                     'probabilities': a.get('probabilities') if a else None,
                     'research': m.get('research', []) if not a else [],
                     'limitations': (a or m).get('limitations', []), 'errors': problems})
        errors.extend(f"{m['id']}: {e}" for e in problems)
    return {'snapshot': snapshot['generated_at'], 'scope': 'Captured evidence only; not live verification',
            'rows': rows, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', default='snapshot.json')
    parser.add_argument('--output')
    args = parser.parse_args()
    result = audit(json.loads(Path(args.snapshot).read_text()))
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(text)
    print(f"{len(result['rows'])} active rows; {len(result['errors'])} errors")
    for error in result['errors']:
        print(error)
    return bool(result['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
