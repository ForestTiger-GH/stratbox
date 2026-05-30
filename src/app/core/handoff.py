"""Launcher -> app handoff contract."""

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
    system_id: str | None = None
    system_created_at_utc: str | None = None
    user_id: str | None = None
    account_name: str | None = None
    host_name: str | None = None
    session_id: str | None = None
    session_started_at_utc: str | None = None
    user_state_path: str | None = None
    session_state_path: str | None = None
    active_session_path: str | None = None
    environment_health_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_launcher_handoff_path_from_env() -> Path | None:
    """Возвращает путь до handoff-файла из окружения launcher-а."""
    value = os.getenv('STRATBOX_LAUNCHER_HANDOFF_PATH', '').strip()
    return Path(value) if value else None


def get_launcher_config_path_from_env() -> Path | None:
    """Возвращает путь до launcher-конфига из окружения launcher-а."""
    value = os.getenv('STRATBOX_LAUNCHER_CONFIG', '').strip()
    return Path(value) if value else None


def load_launcher_handoff(path: Path) -> LauncherHandoff:
    """Читает и валидирует handoff-файл launcher-а."""
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise AppConfigError(f'Failed to read launcher handoff: {path}') from exc
    if not isinstance(payload, dict):
        raise AppConfigError(f'Launcher handoff must be a JSON object: {path}')
    try:
        return LauncherHandoff(
            system_root=str(payload['system_root']),
            data_locator=(payload.get('data_locator') if isinstance(payload.get('data_locator'), dict) else None),
            data_root_status=str(payload.get('data_root_status') or 'unavailable'),
            data_root_path=(str(payload['data_root_path']) if payload.get('data_root_path') else None),
            launcher_mode=str(payload.get('launcher_mode') or 'release_managed'),
            install_profile=str(payload.get('install_profile') or 'release_base'),
            trusted_repo_commit=(str(payload['trusted_repo_commit']) if payload.get('trusted_repo_commit') else None),
            repo_sync_mode=(str(payload['repo_sync_mode']) if payload.get('repo_sync_mode') else None),
            degraded_launch=bool(payload.get('degraded_launch', False)),
            system_id=(str(payload['system_id']) if payload.get('system_id') else None),
            system_created_at_utc=(str(payload['system_created_at_utc']) if payload.get('system_created_at_utc') else None),
            user_id=(str(payload['user_id']) if payload.get('user_id') else None),
            account_name=(str(payload['account_name']) if payload.get('account_name') else None),
            host_name=(str(payload['host_name']) if payload.get('host_name') else None),
            session_id=(str(payload['session_id']) if payload.get('session_id') else None),
            session_started_at_utc=(str(payload['session_started_at_utc']) if payload.get('session_started_at_utc') else None),
            user_state_path=(str(payload['user_state_path']) if payload.get('user_state_path') else None),
            session_state_path=(str(payload['session_state_path']) if payload.get('session_state_path') else None),
            active_session_path=(str(payload['active_session_path']) if payload.get('active_session_path') else None),
            environment_health_path=(str(payload['environment_health_path']) if payload.get('environment_health_path') else None),
        )
    except KeyError as exc:
        raise AppConfigError(f'Launcher handoff misses required field: {exc}') from exc


def load_launcher_handoff_from_env() -> LauncherHandoff | None:
    """Читает handoff launcher-а из переменной окружения, если она задана."""
    path = get_launcher_handoff_path_from_env()
    if path is None or not path.exists():
        return None
    return load_launcher_handoff(path)
