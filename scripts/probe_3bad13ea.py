"""Session-only probe (arena-3bad13ea): which alternate models exist per fixture.

Runs inside the session capture workflow, after ``scripts.collect`` and
``scripts.originate --live``, so every input is the runner's own first-party
evidence. It answers one question and writes no probability to the site: for
each active fixture, is there a *second*, independent, already-audited model
(HLTV world ranking, own results model, own network model) that could give a
side to a fixture whose primary estimate is an exact 50/50 tie?

Deleted before the merge; the JSON it writes stays as dated evidence.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import form_model, hltv_ranking, network_model
from scripts.originate import load_registry, valve_rows

UTC = timezone.utc
OUT = Path('data/research/3bad13ea/model-probe.json')


def brief(quote: dict | None, reason: str) -> dict:
    if not quote:
        return {'available': False, 'reason': reason}
    return {'available': True, 'probabilities': quote.get('probabilities'),
            'source_url': quote.get('source_url'), 'low_confidence': quote.get('low_confidence'),
            'inputs': [{k: row.get(k) for k in ('name', 'points', 'series', 'anchored')}
                       for row in quote.get('inputs') or []],
            'graph_matches': quote.get('graph_matches'), 'graph_anchors': quote.get('graph_anchors')}


def run(data: Path = Path('data')) -> dict:
    evidence = data / 'origination' / 'evidence'
    registry = load_registry(data / 'origination' / 'aliases.json')
    snapshot = json.loads((data / 'latest.json').read_text())
    origination = json.loads((data / 'origination.json').read_text())
    now = datetime.now(UTC)
    document = network_model.load(evidence)
    bindings = form_model.load_bindings(evidence)
    hltv_rows, hltv_meta = hltv_ranking.load(evidence)
    ratings, valve_meta = valve_rows(data, None)
    rows = {str(m['id']): m for m in origination.get('matches') or []}
    out = {'captured_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
           'network_evidence': bool(document), 'hltv_ranking_meta': hltv_meta,
           'valve_meta': valve_meta, 'fixtures': []}
    for match in snapshot.get('matches') or []:
        if match.get('availability') == 'past':
            continue
        row = rows.get(str(match['id'])) or {}
        probs = (row.get('origination') or {}).get('probabilities')
        network, network_reason = network_model.estimate_fixture(
            match, bindings.get(str(match['id'])), document, now)
        form, form_reason = form_model.estimate_fixture(
            match, bindings.get(str(match['id'])), ratings, registry, now)
        hltv, hltv_reason = hltv_ranking.estimate(match, hltv_rows, registry, now, meta=hltv_meta)
        out['fixtures'].append({
            'id': match['id'],
            'fixture': ' vs '.join((t.get('name') or '') for t in match.get('teams') or []),
            'starts_at': match.get('starts_at'),
            'featured_probabilities': probs,
            'originated_pick_index': row.get('pick_index'),
            'exact_tie': bool(probs and abs(probs[0] - probs[1]) < 1e-9),
            'network': brief(network, network_reason),
            'form': brief(form, form_reason),
            'hltv_ranking': brief(hltv, hltv_reason),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    ties = [f for f in out['fixtures'] if f['exact_tie']]
    print(f'probe: {len(out["fixtures"])} active fixtures, {len(ties)} exact ties')
    for f in ties:
        print(json.dumps(f, ensure_ascii=False)[:800])
    return out


if __name__ == '__main__':
    run()
