"""Задача проверки рабочей среды приложения."""

from __future__ import annotations

import importlib.util
import sys
from typing import Any

from app.profiles.diagnostics import run_profile_diagnostics
from app.tasks.models import TaskContext, TaskResult, TaskSpec


def _package_available(name: str) -> bool:
    """Проверяет доступность Python-пакета без его импорта."""
    return importlib.util.find_spec(name) is not None


def run(*, context: TaskContext, params: dict[str, Any], spec: TaskSpec) -> TaskResult:
    """Выполняет диагностику активного профиля и базовых зависимостей."""
    context.logger.info("Environment check started")
    profile_report = run_profile_diagnostics(context.profile)

    package_checks = {
        "stratbox": _package_available("stratbox"),
        "pandas": _package_available("pandas"),
        "openpyxl": _package_available("openpyxl"),
        "requests": _package_available("requests"),
        "PySide6": _package_available("PySide6"),
    }

    for item in profile_report.items:
        level = "OK" if item.ok else "FAIL"
        context.logger.info("%s | %s | %s", level, item.title, item.details)

    for package_name, ok in package_checks.items():
        context.logger.info("Package %s: %s", package_name, "OK" if ok else "missing")

    details = {
        "profile": context.profile.to_dict(),
        "profile_diagnostics": profile_report.to_dict(),
        "packages": package_checks,
        "python": sys.version,
        "version": context.version.to_dict(),
        "task_log": str(context.task_log_path),
    }

    ok = profile_report.ok and package_checks["stratbox"]
    message = "Environment check finished" if ok else "Environment check finished with issues"
    return TaskResult(ok=ok, message=message, outputs=(str(context.task_log_path),), details=details)
