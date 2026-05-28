"""Точка входа для запуска приложения командой ``python -m app``."""

from __future__ import annotations

import argparse
import json
import sys

from app.core.context import build_app_context
from app.tasks.registry import load_task_registry
from app.tasks.runner import run_task_by_id


def _build_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов запуска приложения."""
    parser = argparse.ArgumentParser(prog="python -m app", description="Strategy Box desktop shell")
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run service command without opening GUI.",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Run environment diagnostics and print JSON result.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Override active profile id for current run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Запускает приложение или сервисную команду."""
    args = _build_parser().parse_args(argv)

    context = build_app_context(profile_id=args.profile)

    if args.diagnose or args.no_gui:
        registry = load_task_registry()
        result = run_task_by_id("environment_check", registry=registry, context=context, params={})
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.ok else 2

    from app.gui.main import run_gui

    return run_gui(context)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
