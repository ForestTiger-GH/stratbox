from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    # Knowledge consolidation bootstrap and content-preserved legacy sources.
    'docs/README.md',
    'docs/science/README.md',
    'docs/what/README.md',
    'docs/current-how/README.md',
    'docs/how/README.md',
    'docs/architecture/README.md',
    'docs/ldd/README.md',
    'docs_old/README.md',
    '_mw/epochs-001-strategy-box-development/consolidation/README.md',
    '_mw/epochs-001-strategy-box-development/consolidation/CYCLE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/STATE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/BASELINE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/ARCHITECTURE.md',
    '_mw/epochs-001-strategy-box-development/consolidation/sources/SEED.md',
    'docs_old/cbr_sors_restoration/crosswalk.md',
    'docs_old/cbr_sors_restoration/diagnostics.md',
    'docs_old/cbr_sors_restoration/execution_modes.md',
    'docs_old/cbr_sors_restoration/implementation_report_2026-08-07.md',
    'docs_old/cbr_sors_restoration/methodology.md',
    'docs_old/cbr_sors_restoration/pivot_and_export.md',
    'docs_old/cbr_sors_restoration/result_grids.md',
    'docs_old/cbr_sors_restoration/source_contracts.md',
    'docs_old/files_catalog_methods.md',
    'docs_old/frg_stage1.md',
    'README.md',
    'pyproject.toml',
    'src/stratbox/__init__.py',
    'src/stratbox/README.md',
    'docs_old/architecture.md',
    'docs_old/development.md',
    'docs_old/plugin-integration.md',
    'docs_old/examples.md',
    'examples/cbr_file_collector_example.py',
    'tests/smoke/test_core_imports.py',
    'tests/unit/test_runtime_providers.py',
    'src/stratbox/macrobanks/cbr_sors_restoration/README.md',
    'docs_old/cbr_sors_restoration/architecture.md',
    'docs_old/cbr_sors_restoration/acceptance.md',
    'docs_old/cbr_sors_restoration/implementation_report_2026-08-05.md',
    'docs_old/cbr_sors_restoration/implementation_report_2026-08-06.md',
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
            ignored_path = rel.rstrip('/') + '/'
            result = subprocess.run(
                ['git', 'check-ignore', '-v', '--no-index', ignored_path],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
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
