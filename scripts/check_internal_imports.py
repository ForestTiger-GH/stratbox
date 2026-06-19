from __future__ import annotations

import importlib
import sys

CRITICAL_MODULES = [
    'app.platform.appdock.entry',
    'app.runtime.bootstrap',
    'app.presentation.desktop.main',
    'app.presentation.desktop.shell.main_window',
    'app.presentation.desktop.scenario_coordinator',
    'app.application.scenarios.runner',
    'app.application.logs',
    'app.application.artifacts',
    'app.application.cases',
    'app.application.events',
    'app.application.assignments',
    'app.application.background',
    'app.application.history',
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
