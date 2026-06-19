from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    'src/app/application/logs/__init__.py',
    'src/app/application/logs/models.py',
    'src/app/application/logs/store.py',
    'src/app/application/logs/tail.py',
    'src/app/application/history/__init__.py',
    'src/app/application/history/persistence.py',
    'src/app/presentation/desktop/panels/case_panel.py',
    'src/app/presentation/desktop/panels/node_overview_panel.py',
    'src/app/presentation/desktop/panels/assignments_panel.py',
    'src/app/presentation/desktop/components/background_strip.py',
]
CHECK_IGNORE_PATHS = [
    'src/app/application/logs/models.py',
    'src/app/application/history/persistence.py',
]


def main() -> int:
    failures: list[str] = []
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            failures.append(f'missing required file: {rel}')
        else:
            print(f'OK file {rel}')
    if (ROOT / '.git').exists():
        for rel in CHECK_IGNORE_PATHS:
            result = subprocess.run(['git', 'check-ignore', '-v', rel], cwd=ROOT, text=True, capture_output=True)
            if result.returncode == 0:
                failures.append(f'gitignore hides source file: {rel} :: {result.stdout.strip()}')
            else:
                print(f'OK git-visible {rel}')
    if failures:
        print('\nRelease integrity failed:')
        for failure in failures:
            print(f'  - {failure}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
