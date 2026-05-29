
"""Пути приложения Strategy Box.

Модуль отделяет пользовательские настройки GUI от launcher-managed среды.
User config хранится в пользовательской папке, а operational logs и runtime
могут жить внутри system_root, если приложение запущено launcher-ом.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.handoff import LauncherHandoff

APP_DIR_NAME = "Stratbox"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Набор основных путей приложения."""

    repo_dir: Path
    src_dir: Path
    user_root: Path
    config_dir: Path
    logs_dir: Path
    task_logs_dir: Path
    cache_dir: Path
    runtime_dir: Path
    app_config_path: Path
    system_root: Path | None = None
    launcher_managed: bool = False
    handoff_path: Path | None = None
    launcher_config_path: Path | None = None


def _local_app_data_root() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data).expanduser()
    return Path.home() / ".local" / "share"


def _detect_repo_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def build_app_paths(
    *,
    launcher_handoff: LauncherHandoff | None = None,
    handoff_path: Path | None = None,
    launcher_config_path: Path | None = None,
) -> AppPaths:
    """Создает структуру путей приложения."""
    repo_dir = _detect_repo_dir()
    src_dir = repo_dir / "src"
    user_root = _local_app_data_root() / APP_DIR_NAME
    config_dir = user_root / "config"

    if launcher_handoff is not None:
        system_root = Path(launcher_handoff.system_root).expanduser()
        bootstrap_root = system_root / "bootstrap"
        logs_dir = bootstrap_root / "logs" / "app"
        task_logs_dir = logs_dir / "tasks"
        cache_dir = bootstrap_root / "state" / "app_cache"
        runtime_dir = bootstrap_root / "state" / "app_runtime"
        launcher_managed = True
    else:
        system_root = None
        logs_dir = user_root / "logs"
        task_logs_dir = logs_dir / "tasks"
        cache_dir = user_root / "cache"
        runtime_dir = user_root / "runtime"
        launcher_managed = False

    for path in (config_dir, logs_dir, task_logs_dir, cache_dir, runtime_dir):
        path.mkdir(parents=True, exist_ok=True)

    return AppPaths(
        repo_dir=repo_dir,
        src_dir=src_dir,
        user_root=user_root,
        config_dir=config_dir,
        logs_dir=logs_dir,
        task_logs_dir=task_logs_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        app_config_path=config_dir / "app.json",
        system_root=system_root,
        launcher_managed=launcher_managed,
        handoff_path=handoff_path,
        launcher_config_path=launcher_config_path,
    )
