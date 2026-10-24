"""Read-only integration audit for the automated EGamersWorld reference rung.

Run against any repository tree (including an archived PR head)::

    python -m scripts.cd37caa0_egw_audit --root /tmp/candidate --out report.json

The process exits non-zero when a required safety/wiring check fails. It does
not edit the audited tree. A zero-price result for real sibling-price markup is
reported as a limitation, not disguised as a successful capture.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path


BEHAVIOUR_PROGRAM = r"""
import json
import sys
import types
from scripts.domain import name_key

# Isolate the EGW join from the heavyweight live collector. With an empty
# registry the real resolve_name contract is exact normalized identity.
originate_stub = types.ModuleType('scripts.originate')
def resolve_name(name, registry, competition=None):
    for entry in registry.get('aliases', []):
        if name_key(name) == name_key(entry.get('alias', '')):
            return name_key(entry.get('canonical', '')), [entry]
    return name_key(name), []
originate_stub.resolve_name = resolve_name
sys.modules['scripts.originate'] = originate_stub
from scripts import egw_live

OBSERVED = '2026-10-24T06:00:00Z'
START = '2026-10-26T03:00:00Z'
GZ = {'id': '1082858', 'competition': 'DFRAG Invitational 2026',
      'starts_at': START,
      'teams': [{'name': 'Ground Zero'}, {'name': 'Off Chops'}]}
SPIRIT = {'id': '1081156', 'competition': 'CCT Europe 2026 Series #12',
          'starts_at': '2026-10-25T12:00:00Z',
          'teams': [{'name': 'Spirit'}, {'name': 'LFO'}]}
NO_TIME = '''
<a href="https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d"
   title="Ground Zero VS Off Chops">Ground Zero 3.44 Off Chops 1.24</a>
'''
WRONG_TEAM = '''
<a href="https://egamersworld.com/counterstrike/match/HiXMAaC8L/spirit-academy-vs-lfo-10-example"
   title="Spirit Academy VS LFO 10"><time datetime="2026-10-25T12:00:00Z"></time>
   Spirit Academy 1.50 LFO 10 2.50</a>
'''
SIBLING_PRICES = '''
<div class="match">
<a href="https://egamersworld.com/counterstrike/match/4kaAQWgKEx/ground-zero-vs-off-chops-5mfkMFe7d"
   title="Ground Zero VS Off Chops">Ground Zero
   <time datetime="2026-10-26T03:00:00Z">25.10 23:00</time> Off Chops</a>
<a href="https://egamersworld.com/#">3.44</a>
<a href="https://egamersworld.com/#">Make a bet</a>
<a href="https://egamersworld.com/#">1.24</a>
</div>
'''

def entries(html, match):
    return egw_live.entries_for(html, [match], {'aliases': []}, OBSERVED)

print(json.dumps({
    'no_provider_time_entries': entries(NO_TIME, GZ),
    'substring_team_entries': entries(WRONG_TEAM, SPIRIT),
    'sibling_price_entries': entries(SIBLING_PRICES, GZ),
}))
"""


def function_source(source: str, function_name: str) -> str:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(source, node) or ''
    return ''


def source_checks(root: Path) -> list[dict]:
    originate_path = root / 'scripts/originate.py'
    egw_path = root / 'scripts/egw_live.py'
    if not originate_path.exists() or not egw_path.exists():
        return [{'id': 'source-files', 'status': 'fail', 'required': True,
                 'detail': 'scripts/originate.py and scripts/egw_live.py must both exist.'}]
    originate = originate_path.read_text(encoding='utf-8')
    egw = egw_path.read_text(encoding='utf-8')
    run_source = function_source(originate, 'run')
    loader_source = function_source(egw, 'load_live')
    loader_wired = 'egw_live.load_live(' in run_source and 'reference_rows' in run_source
    original_replay = (
        'live-collection-manifest.json' in loader_source
        and 'entries_for(' in loader_source
        and 'original' in loader_source
        and 'INDEX_EVIDENCE' in loader_source
    )
    return [
        {'id': 'live-reference-loaded', 'status': 'pass' if loader_wired else 'fail',
         'required': True,
         'detail': ('originate.run adds egw_live.load_live to the reference evidence.'
                    if loader_wired else
                    'originate.run never calls egw_live.load_live; collected entries are inert.')},
        {'id': 'original-response-replay', 'status': 'pass' if original_replay else 'fail',
         'required': True,
         'detail': ('load_live replays the original index and request manifest.'
                    if original_replay else
                    'load_live does not prove original-HTML/manifest replay; derived-only evidence is not sufficient.')},
    ]


def behaviour_checks(behaviour: dict) -> list[dict]:
    no_time = behaviour.get('no_provider_time_entries') or []
    wrong_team = behaviour.get('substring_team_entries') or []
    siblings = behaviour.get('sibling_price_entries') or []
    return [
        {'id': 'no-copied-provider-start', 'status': 'fail' if no_time else 'pass',
         'required': True,
         'detail': (f'{len(no_time)} entries were emitted without any provider timestamp.'
                    if no_time else 'No entry is emitted when the provider has no explicit start timestamp.'),
         'observed_entries': no_time},
        {'id': 'no-substring-team-identity', 'status': 'fail' if wrong_team else 'pass',
         'required': True,
         'detail': (f'{len(wrong_team)} entries confused Spirit/LFO with Spirit Academy/LFO 10.'
                    if wrong_team else 'Academy/sister-team slug substrings do not establish identity.'),
         'observed_entries': wrong_team},
        {'id': 'real-sibling-price-markup', 'status': 'info',
         'required': False,
         'detail': (f'{len(siblings)} entries captured from match anchor plus sibling price links.'
                    if siblings else
                    'No entry captured when prices are sibling links outside the match anchor; this fail-closed limitation must not be called a successful price capture.'),
         'observed_entries': siblings},
    ]


def behaviour_probe(root: Path) -> dict:
    env = dict(os.environ)
    existing_pythonpath = env.get('PYTHONPATH')
    env['PYTHONPATH'] = (str(root.resolve()) +
                         (os.pathsep + existing_pythonpath if existing_pythonpath else ''))
    completed = subprocess.run(
        [sys.executable, '-c', BEHAVIOUR_PROGRAM], cwd=root, env=env,
        text=True, capture_output=True, timeout=90, check=False)
    if completed.returncode:
        raise RuntimeError(f'behaviour probe failed ({completed.returncode}): {completed.stderr[-2000:]}')
    return json.loads(completed.stdout)


def audit(root: Path) -> dict:
    root = Path(root)
    checks = source_checks(root)
    behaviour_error = None
    try:
        checks.extend(behaviour_checks(behaviour_probe(root)))
    except (RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        behaviour_error = str(exc)
        checks.append({'id': 'behaviour-probe', 'status': 'fail', 'required': True,
                       'detail': behaviour_error})
    failed = [check['id'] for check in checks
              if check.get('required') and check.get('status') == 'fail']
    return {'schema_version': 1, 'session': 'arena-cd37caa0',
            'kind': 'read-only EGW integration and fail-closed behaviour audit',
            'root': str(root.resolve()), 'status': 'fail' if failed else 'pass',
            'failed_required_checks': failed, 'checks': checks}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--out', type=Path)
    parser.add_argument('--source-ref', help='Immutable audited commit/PR URL')
    parser.add_argument('--label', help='Human-readable audited tree label')
    args = parser.parse_args(argv)
    report = audit(args.root)
    if args.source_ref:
        report['source_ref'] = args.source_ref
    if args.label:
        report['label'] = args.label
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding='utf-8')
    print(text, end='')
    return 1 if report['status'] == 'fail' else 0


if __name__ == '__main__':
    raise SystemExit(main())
