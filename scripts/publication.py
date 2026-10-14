"""Order Pages publishers safely and record repository-setting limitations.

GitHub may deny build-mode changes even when artifact deployment is permitted.
A setting restriction is a visible warning, not a reason to discard valid picks.
In legacy mode, finish the platform's build for this commit BEFORE deploying our
canonical artifact; scheduled runs reuse the already-completed legacy build.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.collect import flag, write_snapshot
from scripts.domain import iso


def configure(output, repository, sha, token, *, session=None, attempts=36, pause=5):
    session = session or requests.Session()
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    api = 'https://api.github.com/repos/' + repository
    url = api + '/pages'
    observed = iso(datetime.now(timezone.utc))
    response = session.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    initial = response.json()
    mode = initial.get('build_type')
    if mode not in {'legacy', 'workflow'}:
        raise ValueError('Unrecognized Pages build mode; publication ordering cannot be verified')
    audit = {'observed_at': observed, 'url': url, 'initial_build_type': mode, 'legacy_runs': [], 'update_http_status': None, 'update_error': None}
    if mode == 'legacy':
        for attempt in range(attempts):
            runs = session.get(api + '/actions/runs', headers=headers, params={'head_sha': sha, 'event': 'dynamic', 'per_page': 100}, timeout=20)
            runs.raise_for_status()
            legacy = [r for r in runs.json()['workflow_runs'] if r.get('name', '').replace(' ', '-').lower() in {'pages-build-deployment', 'pages-build-and-deployment'}]
            audit['legacy_runs'] = [{k: r.get(k) for k in ['id', 'status', 'conclusion', 'head_sha']} for r in legacy]
            if (legacy or initial.get('status') != 'building') and all(r['status'] == 'completed' for r in legacy):
                break
            if attempt == attempts - 1:
                raise TimeoutError('Legacy Pages publisher did not finish; refusing a competing deployment')
            time.sleep(pause)
        try:
            update = session.put(url, headers=headers, json={'build_type': 'workflow'}, timeout=20)
            audit['update_http_status'] = update.status_code
            if not 200 <= update.status_code < 300:
                try:
                    message = update.json().get('message', 'Build-mode update rejected')
                except ValueError:
                    message = 'Build-mode update rejected'
                audit['update_error'] = str(message).replace(token, '[redacted]')[:400]
        except requests.RequestException as exc:
            audit['update_error'] = str(exc).replace(token, '[redacted]')[:400]
        current = session.get(url, headers=headers, timeout=20)
        current.raise_for_status()
        mode = current.json().get('build_type')
        if mode not in {'legacy', 'workflow'}:
            raise ValueError('Pages mode could not be verified after configuration attempt')
    audit['final_build_type'] = mode
    root = Path(output)
    data = json.loads((root / 'latest.json').read_text())
    data['flags'] = [f for f in data['flags'] if f['id'] != 'pages-publication-mode']
    detail = 'GitHub Actions is the sole configured Pages publisher.'
    if mode == 'legacy':
        detail = f'Pages remains in legacy build mode after the configuration attempt (HTTP {audit["update_http_status"]}; error: {audit["update_error"]}). The platform still builds the main branch on pushes. This workflow waits for that legacy build to finish, then publishes the verified current artifact last. The old six-hour refresh writer is retired; four-hour refreshes need no user action. Repository-mode restriction is not a source-data verification failure.'
        data['flags'].append(flag('pages-publication-mode', 'Legacy Pages mode — publisher ordering enforced', detail, [url, 'https://github.com/' + repository + '/actions/workflows/pages.yml'], severity='notice'))
        print('::warning title=Legacy Pages mode retained::' + detail)
    data['sources'] = [s for s in data['sources'] if s['name'] != 'GitHub Pages publication']
    data['sources'].append({'name': 'GitHub Pages publication', 'url': url, 'status': 'ok' if mode == 'workflow' else 'limited', 'observed_at': observed, 'records': None, 'detail': detail, 'evidence': 'data/evidence/pages-configuration.json'})
    (root / 'evidence').mkdir(exist_ok=True)
    (root / 'evidence/pages-configuration.json').write_text(json.dumps(audit, indent=2) + '\n')
    data['evidence_files'] = sorted(set(data.get('evidence_files', [])) | {'data/evidence/pages-configuration.json'})
    write_snapshot(root, data)
    print('::notice title=Publication snapshot::' + json.dumps({'inventory_observed_at': data.get('inventory_observed_at'), 'coverage_complete': data.get('coverage_complete'), 'counts': data.get('counts'), 'pages_mode': mode}))
    return audit


if __name__ == '__main__':
    configure(Path('data'), os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_SHA'], os.environ['GH_TOKEN'])
