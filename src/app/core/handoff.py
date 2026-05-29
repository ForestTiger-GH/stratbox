
"""Launcher -> app handoff and launcher-managed session helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from app.core.errors import AppConfigError


@dataclass(frozen=True, slots=True)
class LauncherHandoff:
    """Контракт запуска приложения из launcher-проекта."""

    system_root: str
    data_locator: dict[str, Any] | None
    data_root_status: str
    data_root_path: str | None
    launcher_mode: str
    install_profile: str
    trusted_repo_commit: str | None = None
    repo_sync_mode: str | None = None
    degraded_launch: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_launcher_handoff_path_from_env() -> Path | None:
    """Возвращает путь до handoff-файла из окружения launcher-а."""
    value = os.getenv("STRATBOX_LAUNCHER_HANDOFF_PATH", "").strip()
    return Path(value) if value else None


def get_launcher_config_path_from_env() -> Path | None:
    """Возвращает путь до launcher-конфига из окружения launcher-а."""
    value = os.getenv("STRATBOX_LAUNCHER_CONFIG", "").strip()
    return Path(value) if value else None


def load_launcher_handoff(path: Path) -> LauncherHandoff:
    """Читает и валидирует handoff-файл launcher-а."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AppConfigError(f"Failed to read launcher handoff: {path}") from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f"Launcher handoff must be a JSON object: {path}")
    try:
        return LauncherHandoff(
            system_root=str(payload["system_root"]),
            data_locator=payload.get("data_locator") if isinstance(payload.get("data_locator"), dict) else None,
            data_root_status=str(payload.get("data_root_status") or "unavailable"),
            data_root_path=(str(payload["data_root_path"]) if payload.get("data_root_path") else None),
            launcher_mode=str(payload.get("launcher_mode") or "release_managed"),
            install_profile=str(payload.get("install_profile") or "release_base"),
            trusted_repo_commit=(str(payload["trusted_repo_commit"]) if payload.get("trusted_repo_commit") else None),
            repo_sync_mode=(str(payload["repo_sync_mode"]) if payload.get("repo_sync_mode") else None),
            degraded_launch=bool(payload.get("degraded_launch", False)),
        )
    except KeyError as exc:
        raise AppConfigError(f"Launcher handoff misses required field: {exc}") from exc


def load_launcher_handoff_from_env() -> LauncherHandoff | None:
    """Читает handoff launcher-а из переменной окружения, если она задана."""
    path = get_launcher_handoff_path_from_env()
    if path is None or not path.exists():
        return None
    return load_launcher_handoff(path)


def patch_launcher_config_data_root(config_path: Path, data_locator: dict[str, Any]) -> None:
    """Обновляет data_locator в launcher-конфиге внешнего контура."""
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AppConfigError(f"Failed to read launcher config: {config_path}") from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f"Launcher config must be a JSON object: {config_path}")
    payload["data_locator"] = dict(data_locator)
    payload["setup_completed"] = True
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_launcher_handoff_data_root(handoff_path: Path, data_locator: dict[str, Any], data_root_path: Path, *, available: bool) -> None:
    """Обновляет текущий handoff-файл после смены business-root внутри app."""
    try:
        payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AppConfigError(f"Failed to read launcher handoff: {handoff_path}") from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f"Launcher handoff must be a JSON object: {handoff_path}")
    payload["data_locator"] = dict(data_locator)
    payload["data_root_path"] = str(data_root_path)
    payload["data_root_status"] = "available" if available else "unavailable"
    payload["degraded_launch"] = not available
    handoff_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
