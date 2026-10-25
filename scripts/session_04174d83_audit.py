"""Dated, read-only runner verification; never changes probabilities or aliases."""
import json
import subprocess
import sys
from pathlib import Path

OUT = Path('data/research/04174d83')


def main():
    subprocess.run([sys.executable, '-m', 'scripts.current_coverage_audit',
                    '--data', 'data', '--out', str(OUT)], check=True)
    report = json.loads((OUT / 'audit.json').read_text())
    # The reused audit's default flag identifies its original session. Give this
    # independent observation its own ID so neither report hides the other.
    flags = json.loads((OUT / 'flags.json').read_text())
    for flag in flags:
        flag['id'] = '04174d83-current-coverage-audit'
        flag['title'] = '25 October runner coverage and HLTV-first no-line research'
        flag['source_urls'][-1] = ('https://github.com/buffedlizard55-lab/MaltaProj3/'
                                  'blob/main/data/research/04174d83/audit.json')
    (OUT / 'flags.json').write_text(json.dumps(flags, indent=2) + '\n')
    # State exactly what was audited: collected data is NOT proof of deployment.
    (OUT / 'README.md').write_text(
        '# Dated runner coverage audit\n\n' + flags[0]['detail'] + '\n\n'
        'The saved published-inventory and published-complete-picks filenames are '
        'inherited from the reusable auditor; these files contain the explicit '
        'runner-collected data, NOT a live Pages fetch. Original source URLs and '
        'per-fixture limitations are in audit.json. No new price is inferred '
        'from HTTP success, name mentions, fan votes or unavailable pages.\n\n'
        f'Independent inventory observation: {json.dumps(report.get("official_inventory_delta"))}\n')


if __name__ == '__main__':
    main()
