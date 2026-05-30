"""Точка входа для запуска приложения командой ``python -m app``."""

from __future__ import annotations

import argparse
import json
import sys

from app.core.context import build_app_context
from app.core.errors import AppStartupError
from app.tasks.registry import load_task_registry
from app.tasks.runner import run_task_by_id


def _build_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов запуска приложения."""
    parser = argparse.ArgumentParser(prog='python -m app', description='Strategy Box desktop shell')
    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run service command without opening GUI.',
    )
    parser.add_argument(
        '--diagnose',
        action='store_true',
        help='Run launcher preflight diagnostics and print JSON result.',
    )
    parser.add_argument(
        '--standalone-dev-root',
        default=None,
        help='Explicit business-root for standalone developer launch outside launcher handoff.',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Запускает приложение или сервисную команду."""
    args = _build_parser().parse_args(argv)

    try:
        context = build_app_context(standalone_dev_root=args.standalone_dev_root)
    except AppStartupError as exc:
        print(f'ERROR: {exc}')
        return 2

    if args.diagnose:
        registry = load_task_registry()
        result = run_task_by_id('environment_check', registry=registry, context=context, params={'mode': 'launcher_preflight'})
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.ok else 2

    if args.no_gui:
        registry = load_task_registry()
        result = run_task_by_id('environment_check', registry=registry, context=context, params={})
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.ok else 2

    from app.gui.main import run_gui

    return run_gui(context)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
