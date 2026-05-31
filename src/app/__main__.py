"""Точка входа для запуска приложения командой ``python -m app``."""

from __future__ import annotations

import argparse
import json
import sys

from app.core.context import build_app_context
from app.core.errors import AppStartupError
from app.scenarios.registry import load_scenario_registry
from app.scenarios.runner import run_scenario_by_id


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='python -m app', description='Strategy Box desktop shell')
    parser.add_argument('--no-gui', action='store_true', help='Run service command without opening GUI.')
    parser.add_argument('--diagnose', action='store_true', help='Run AppDock preflight diagnostics and print JSON result.')
    parser.add_argument('--standalone-dev-root', default=None, help='Explicit selector path for standalone developer launch outside AppDock handoff.')
    return parser


def main(argv: list[str] | None = None, *, launch_origin: str = 'standalone') -> int:
    args = _build_parser().parse_args(argv)
    try:
        context = build_app_context(standalone_dev_root=args.standalone_dev_root, launch_origin=launch_origin)
    except AppStartupError as exc:
        print(f'ERROR: {exc}')
        return 2

    if args.diagnose:
        registry = load_scenario_registry()
        result = run_scenario_by_id('environment_check', registry=registry, context=context, params={'mode': 'appdock_preflight'})
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.ok else 2

    if args.no_gui:
        registry = load_scenario_registry()
        result = run_scenario_by_id('environment_check', registry=registry, context=context, params={})
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.ok else 2

    from app.gui.main import run_gui
    return run_gui(context)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
