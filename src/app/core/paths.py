"""Пути приложения Strategy Box.

Модуль отделяет пользовательские настройки и логи от Git-репозитория.
Репозиторий может обновляться, а локальный конфиг пользователя при этом остается на месте.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

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


def _local_app_data_root() -> Path:
    """Возвращает базовую пользовательскую папку для настроек приложения."""
    # На Windows используется LOCALAPPDATA. В Linux/Colab fallback остается безопасным.
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data).expanduser()
    return Path.home() / ".local" / "share"


def _detect_repo_dir() -> Path:
    """Определяет корень текущего репозитория по расположению src/app/core."""
    # Файл находится в <repo>/src/app/core/paths.py.
    return Path(__file__).resolve().parents[3]


def build_app_paths() -> AppPaths:
    """Создает структуру путей и гарантирует наличие служебных каталогов."""
    repo_dir = _detect_repo_dir()
    src_dir = repo_dir / "src"
    user_root = _local_app_data_root() / APP_DIR_NAME
    config_dir = user_root / "config"
    logs_dir = user_root / "logs"
    task_logs_dir = logs_dir / "tasks"
    cache_dir = user_root / "cache"
    runtime_dir = user_root / "runtime"

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
    )
