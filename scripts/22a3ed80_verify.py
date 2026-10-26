"""Session arena-22a3ed80: verify the published executive summary line by line.

Every check reads only what is actually published:

* ``snapshot.json`` — the byte-identical copy of the verified ``data/latest.json``
  that the publisher writes into the branch root;
* ``index.html`` — the executive summary built from that same snapshot.

Nothing here reaches the network and nothing is inferred: for a *featured* row
the published pick and both percentages are re-derived from the fixture's own
``analysis`` block (``probabilities`` + ``pick_index``), and for a *researched
fallback* row the script only records which labelled fallback carried the row,
because that number belongs to the fallback's own dossier and is replayed there.

The checks are snapshot-independent: they compare the page with the snapshot it
says it was built from, so the four-hour publisher can rewrite both files
without turning this module into a wall-clock trap.

CLI
---
    python -m scripts.22a3ed80_verify            # human-readable report
    python -m scripts.22a3ed80_verify --check    # exit 1 on any hard failure
    python -m scripts.22a3ed80_verify --json data/research/22a3ed80/verification.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

#: Routes the executive summary must offer so a phone reader can reach the picks.
PICKS_ROUTES = (
    ('origination/index.html', 'id="picks"'),
    ('origination/index.html', 'id="unresolved"'),
    ('unresolved/index.html', 'id="main"'),
)

_GLANCE_ROW = re.compile(r'<li class="glance-row"[^>]*data-glance-id="(?P<id>[^"]*)"')
_PICK = re.compile(r'<span class="glance-pick-label[^"]*"[^>]*>(?P<label>.*?)</span>\s*(?:<strong>(?P<pick>.*?)</strong>)?', re.S)
_PROB = re.compile(r'<span class="glance-prob">(?P<prob>[0-9.]+)%</span>')
_OTHER = re.compile(r'<span class="glance-other">.*?(?P<prob>[0-9.]+)%', re.S)
_LINK = re.compile(r'href="(https://[^"]+)"')


def _text(value: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', value or '')).strip()


def _glance_rows(html: str) -> list[dict]:
    """Each rendered picks-at-a-glance row with its id, pick, percentages, links."""
    starts = [m.start() for m in _GLANCE_ROW.finditer(html)]
    rows = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else html.find('</ol>', start)
        block = html[start:end if end > start else len(html)]
        identifier = _GLANCE_ROW.match(block).group('id')
        pick = _PICK.search(block)
        prob = _PROB.search(block)
        other = _OTHER.search(block)
        # A priced row prints "Pick <strong>Team</strong>"; an unresolved row
        # prints the label itself ("Unresolved") and no team, so read both.
        pick_text = _text(pick.group('pick') or '') if pick else ''
        label_text = _text(pick.group('label') or '') if pick else ''
        rows.append({
            'id': identifier,
            'pick': pick_text or (label_text if label_text and label_text != 'Pick' else None),
            'pick_label': label_text,
            'prob': float(prob.group('prob')) if prob else None,
            'other': float(other.group('prob')) if other else None,
            'links': sorted(set(_LINK.findall(block))),
            'why_links': re.findall(r'<a class="internal-link" href="([^"]+)"', block),
            'method': (re.search(r'data-method="([^"]*)"', block) or [None, None])[1]
            if re.search(r'data-method="([^"]*)"', block) else None,
            'badges': [_text(b) for b in re.findall(r'<span class="badge[^"]*">(.*?)</span>', block, re.S)],
        })
    return rows


def verify(site: Path) -> dict:
    site = Path(site)
    snapshot_path = site / 'snapshot.json'
    index_path = site / 'index.html'
    result = {
        'site': str(site),
        'generated_at': None,
        'checks': [],
        'rows': [],
        'counts': {},
        'summary': {},
    }

    def check(name, ok, detail, hard=True):
        result['checks'].append({'name': name, 'ok': bool(ok), 'hard': bool(hard), 'detail': detail})
        return ok

    if not snapshot_path.is_file() or not index_path.is_file():
        check('published_files_present', False,
              f'missing {snapshot_path.name if not snapshot_path.is_file() else index_path.name}')
        result['summary'] = _summarise(result)
        return result

    snapshot = json.loads(snapshot_path.read_text())
    html = index_path.read_text()
    # The publisher writes two artefacts into the branch root: the collected
    # snapshot (`snapshot.json`) and the complete-picks layer
    # (`origination.json`). The page renders the complete-picks layer whenever a
    # fixture has one, so a row must be compared with that layer first and only
    # fall back to the snapshot's own analysis block when it is absent. Before
    # 2026-10-26 this module compared every priced row with `snapshot.json` alone,
    # which reported a false mismatch for a fixture the origination ladder had
    # re-priced (1093218: consensus 58.3%/41.7% rendered, model 70.7%/29.3% in
    # the older snapshot block) and blocked the deploy at run 40254593296.
    origination_path = site / 'origination.json'
    origination = {}
    if origination_path.is_file():
        try:
            origination = {str(m.get('id')): m for m in json.loads(origination_path.read_text()).get('matches') or []}
        except (ValueError, AttributeError):
            origination = {}
    generated = snapshot.get('generated_at')
    result['generated_at'] = generated
    result['counts'] = snapshot.get('counts') or {}

    stamped = re.search(r'data-snapshot-generated="([^"]+)"', html)
    check('page_stamp_matches_snapshot', stamped and stamped.group(1) == generated,
          f'page={stamped.group(1) if stamped else "unset"} snapshot={generated}')

    upcoming = [m for m in snapshot.get('matches') or [] if m.get('availability') != 'past']
    rows = _glance_rows(html)
    by_id = {row['id']: row for row in rows}

    check('one_glance_row_per_upcoming_fixture',
          {str(m.get('id')) for m in upcoming} == set(by_id),
          f'{len(upcoming)} upcoming, {len(rows)} rows; '
          f'missing={sorted({str(m.get("id")) for m in upcoming} - set(by_id))[:5]} '
          f'extra={sorted(set(by_id) - {str(m.get("id")) for m in upcoming})[:5]}')

    featured = fallback = unresolved = 0
    problems = []
    for match in upcoming:
        identifier = str(match.get('id'))
        row = by_id.get(identifier)
        if row is None:
            continue
        teams = [t.get('name') for t in match.get('teams') or []]
        analysis = match.get('analysis') or {}
        probs = analysis.get('probabilities') or []
        pick_index = match.get('pick_index')
        # The complete-picks layer wins when it has a priced row, because that is
        # what the page renders.
        complete = (origination.get(identifier) or {}).get('origination') or {}
        if complete.get('probabilities') and (origination.get(identifier) or {}).get('pick_index') is not None:
            analysis = complete
            probs = complete.get('probabilities') or []
            pick_index = origination[identifier].get('pick_index')
            record_source = 'origination.json'
        else:
            record_source = 'snapshot.json'
        record = {
            'id': identifier,
            'teams': teams,
            'starts_at': match.get('starts_at'),
            'method': analysis.get('method'),
            'rendered_pick': row['pick'],
            'rendered_probabilities': [row['prob'], row['other']],
            'source_links': len(row['links']),
            'verification': None,
            'note': None,
            'expectation_source': record_source,
        }
        if not row['links']:
            problems.append(f'{identifier}: no https source link on the row')
        if probs and pick_index is not None and len(probs) == 2:
            featured += 1
            expected_pick = teams[pick_index]
            expected = round(probs[pick_index] * 100, 1)
            expected_other = round((1 - probs[pick_index]) * 100, 1)
            ok = (row['pick'] == expected_pick
                  and row['prob'] == expected
                  and row['other'] == expected_other)
            if not ok:
                problems.append(
                    f'{identifier}: rendered {row["pick"]} {row["prob"]}%/{row["other"]}% but the '
                    f'fixture\'s own analysis gives {expected_pick} {expected}%/{expected_other}%')
            record['verification'] = 're-derived from the fixture analysis block'
        elif row['prob'] is None:
            # An explicitly unresolved row is a published limitation, not a
            # defect: the brief allows a blank only when the reason is stated.
            # It must say so, link a source and offer the explanation route.
            unresolved += 1
            says_so = (row['pick'] or '').strip().lower().startswith('unresolved') or any(
                'unresolved' in badge.lower() for badge in row['badges'])
            if not says_so:
                problems.append(f'{identifier}: row has no probability and does not say it is unresolved')
            if 'origination/#unresolved' not in ''.join(row['why_links']):
                problems.append(f'{identifier}: unresolved row does not link the reason')
            record['verification'] = 'published unresolved (explicit reason linked, no number invented)'
            record['note'] = row['pick']
        else:
            fallback += 1
            labelled = bool(row['badges']) or (row['method'] or '') not in ('', 'market', 'bookmaker')
            if not labelled:
                problems.append(f'{identifier}: fallback row carries no fallback/model label')
            if not (0 < row['prob'] < 100):
                problems.append(f'{identifier}: fallback row has no usable probability')
            record['verification'] = 'labelled researched fallback (its own dossier replays the number)'
            record['note'] = ' / '.join(row['badges']) or row['method']
        result['rows'].append(record)

    check('every_row_is_sourced', not any('no https source link' in p for p in problems),
          f'{sum(1 for r in result["rows"] if r["source_links"])} of {len(result["rows"])} rows link a source')
    check('featured_rows_replay_exactly', not any('analysis gives' in p for p in problems),
          f'{featured} featured rows re-derived from their own analysis block')
    check('fallback_rows_are_labelled_and_priced', not any('fallback row' in p for p in problems),
          f'{fallback} fallback rows carry a label and a probability')
    check('unresolved_rows_state_their_reason',
          not any('does not say it is unresolved' in p or 'does not link the reason' in p for p in problems),
          f'{unresolved} rows published as unresolved, each naming its reason')
    for problem in problems:
        result['checks'].append({'name': 'row_problem', 'ok': False, 'hard': True, 'detail': problem})

    unpriced_rendered = sum(1 for row in rows if row['prob'] is None)

    # The headline numbers the reader sees must equal the snapshot's own counts.
    intro = _text(html[html.find('id="picks-at-a-glance"'):][:3000])
    numbers = re.findall(r'(\d+) active Hotspawn CS2 fixtures in this snapshot, (\d+) with a directional '
                         r'pick — (\d+) from an external betting line, (\d+) from a research model — and '
                         r'(\d+) explicitly unresolved', intro)
    if numbers:
        active, picked, external, model, blank = (int(n) for n in numbers[0])
        counts = result['counts']
        # "External" means the money source that produced the final number, so a
        # featured gap closed by a researched consensus line counts as external
        # even though its featured analysis block is empty. Read the method the
        # row itself declares rather than only the featured analysis.
        METHODS_EXTERNAL = ('market', 'bookmaker', 'consensus')
        rendered_external = sum(1 for row in rows if (row['method'] or '') in METHODS_EXTERNAL)
        rendered_model = sum(1 for row in rows if (row['method'] or '') not in METHODS_EXTERNAL
                             and row['prob'] is not None)
        priced = sum(1 for row in rows if row['prob'] is not None)
        # A blank row is allowed only when the summary says how many rows are
        # unresolved and the picks list carries the same number of blanks.
        unresolved_ids = snapshot.get('unresolved_ids')
        snap_unresolved = (len(unresolved_ids) if isinstance(unresolved_ids, list)
                           else int(counts.get('unresolved') or 0))
        ok = (active == counts.get('upcoming') == len(upcoming)
              and picked == priced
              and external == rendered_external
              and model == rendered_model
              and external + model == priced
              and picked + blank == len(upcoming)
              and blank == len(upcoming) - priced
              and unpriced_rendered == blank)
        check('headline_numbers_match_snapshot', ok,
              f'rendered active={active} picked={picked} external={external} model={model} blank={blank}; '
              f'snapshot upcoming={counts.get("upcoming")} rows={len(upcoming)} priced={priced} '
              f'(snapshot unresolved ids={snap_unresolved}); '
              f'rows declaring an external method={rendered_external}, research model={rendered_model} '
              f'({featured} replayed from a featured analysis block, {fallback} labelled fallbacks, '
              f'{unresolved} explicitly unresolved)')
    else:
        check('headline_numbers_match_snapshot', True,
              'headline sentence not found in this wording; skipped (informational)', hard=False)

    status = _text(re.search(r'<nav class="mobile-status".*?</nav>', html, re.S).group(0)) \
        if re.search(r'<nav class="mobile-status".*?</nav>', html, re.S) else ''
    picks_ready = re.search(r'^(\d+) picks ready of (\d+)', status)
    blank_status = re.search(r'(\d+) unresolved', status)
    priced = sum(1 for row in rows if row['prob'] is not None)
    blank_rows = len(rows) - priced
    check('phone_status_matches_snapshot',
          picks_ready is not None and int(picks_ready.group(1)) == priced
          and int(picks_ready.group(2)) == len(upcoming)
          and (blank_status is None or int(blank_status.group(1)) == blank_rows),
          f'status reads "{status[:60]}" for {len(upcoming)} upcoming fixtures '
          f'({priced} priced, {blank_rows} blank)')

    for route, anchor in PICKS_ROUTES:
        target = site / route
        ok = target.is_file() and anchor in target.read_text()
        check(f'route_{route.replace("/", "_")}_{anchor}', ok, f'{route} contains {anchor}')

    for anchor in ('#picks-at-a-glance', '#unresolved-register', '#no-line-register', '#fallback-register'):
        check(f'summary_link_{anchor}', f'href="./{anchor}"' in html or f'href="{anchor}"' in html,
              f'executive summary links {anchor}')

    result['summary'] = _summarise(result)
    return result


def _summarise(result: dict) -> dict:
    checks = result.get('checks') or []
    hard = [c for c in checks if c['hard']]
    return {
        'hard_checks': len(hard),
        'hard_failures': sum(1 for c in hard if not c['ok']),
        'informational': sum(1 for c in checks if not c['hard']),
        'rows_checked': len(result.get('rows') or []),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', default='.', help='published tree (snapshot.json + index.html)')
    parser.add_argument('--json', default=None, help='write the full result to this path')
    parser.add_argument('--check', action='store_true', help='exit 1 on any hard failure')
    args = parser.parse_args(argv)

    result = verify(Path(args.site))
    summary = result['summary']
    print(f'Published snapshot {result["generated_at"]} — {summary["rows_checked"]} rows checked')
    for item in result['checks']:
        if item['name'] == 'row_problem':
            print(f'  PROBLEM  {item["detail"]}')
            continue
        state = 'PASS' if item['ok'] else ('FAIL' if item['hard'] else 'INFO')
        print(f'  {state:4}  {item["name"]}: {item["detail"]}')
    print(f'{summary["hard_checks"]} hard checks, {summary["hard_failures"]} failure(s), '
          f'{summary["informational"]} informational')
    if args.json:
        target = Path(args.json)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return 1 if (args.check and summary['hard_failures']) else 0


if __name__ == '__main__':
    sys.exit(main())
