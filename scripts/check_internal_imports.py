from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CRITICAL_MODULES = [
    'stratbox',
    'stratbox.base.runtime',
    'stratbox.base.ioapi',
    'stratbox.base.filestore',
    'stratbox.base.net',
    'stratbox.base.secrets',
    'stratbox.macrobanks.cbr_file_collector',
    'stratbox.macrobanks.cbr_forms',
    'stratbox.macrobanks.escrow',
    'stratbox.macrobanks.frg',
    'stratbox.registries',
    'stratbox.text.banks',
]


def main() -> int:
    failures: list[str] = []
    for module in CRITICAL_MODULES:
        try:
            importlib.import_module(module)
            print(f'OK   {module}')
        except Exception as exc:
            failures.append(f'{module}: {type(exc).__name__}: {exc}')
            print(f'FAIL {module}: {type(exc).__name__}: {exc}')
    if failures:
        print('\nBroken imports:')
        for failure in failures:
            print(f'  - {failure}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
