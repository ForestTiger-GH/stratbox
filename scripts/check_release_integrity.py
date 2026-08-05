from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    'README.md',
    'pyproject.toml',
    'src/stratbox/__init__.py',
    'src/stratbox/README.md',
    'docs/architecture.md',
    'docs/development.md',
    'docs/plugin-integration.md',
    'docs/examples.md',
    'examples/cbr_file_collector_example.py',
    'tests/smoke/test_core_imports.py',
    'tests/unit/test_runtime_providers.py',
    'src/stratbox/macrobanks/cbr_sors_restoration/README.md',
    'docs/cbr_sors_restoration/architecture.md',
    'docs/cbr_sors_restoration/acceptance.md',
    'docs/cbr_sors_restoration/implementation_report_2026-08-05.md',
    'examples/cbr_sors_restoration_colab.py',
    'tests/cbr_sors_restoration/test_publication.py',
]

FORBIDDEN_PATHS = [
    'src/app',
    'appdock',
    '.tmp',
]

CHECK_IGNORE_PATHS = [
    '.tmp',
    '.venv',
    '.venv-build',
]


def main() -> int:
    failures: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            failures.append(f'missing required path: {rel}')
        else:
            print(f'OK required {rel}')

    for rel in FORBIDDEN_PATHS:
        if (ROOT / rel).exists():
            failures.append(f'forbidden path still exists: {rel}')
        else:
            print(f'OK absent {rel}')

    if (ROOT / '.git').exists():
        for rel in CHECK_IGNORE_PATHS:
            result = subprocess.run(['git', 'check-ignore', '-v', rel], cwd=ROOT, text=True, capture_output=True)
            if result.returncode != 0:
                failures.append(f'gitignore does not hide path: {rel}')
            else:
                print(f'OK ignored {rel}')

    generated = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob('*')
        if path.is_file()
        and (path.suffix == '.pyc' or '__pycache__' in path.parts)
        and not any(ignored in path.parts for ignored in CHECK_IGNORE_PATHS)
    ]
    if generated:
        failures.append(
            'generated Python bytecode is present: ' + ', '.join(generated[:20])
        )
    else:
        print('OK no generated Python bytecode')

    if failures:
        print('\nRelease integrity failed:')
        for failure in failures:
            print(f'  - {failure}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
