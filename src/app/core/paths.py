"""Пути приложения Strategy Box.

Модуль отделяет пользовательские настройки GUI от AppDock-managed среды.
User config хранится в пользовательской папке, а operational refs приходят через
AppDock handoff и сессионный каталог.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.handoff import AppHandoff

APP_DIR_NAME = 'Stratbox'


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Набор основных путей приложения."""

    source_root: Path
    src_dir: Path
    user_root: Path
    config_dir: Path
    logs_dir: Path
    scenario_logs_dir: Path
    cache_dir: Path
    runtime_dir: Path
    app_config_path: Path
    install_root: Path | None = None
    system_root: Path | None = None
    session_dir: Path | None = None
    appdock_managed: bool = False
    handoff_path: Path | None = None
    appdock_config_path: Path | None = None
    user_state_path: Path | None = None
    session_state_path: Path | None = None
    active_session_path: Path | None = None
    health_snapshot_path: Path | None = None
    app_state_path: Path | None = None
    bundle_root: Path | None = None
    appdock_runtime_root: Path | None = None


def _local_app_data_root() -> Path:
    local_app_data = os.getenv('LOCALAPPDATA')
    if local_app_data:
        return Path(local_app_data).expanduser()
    return Path.home() / '.local' / 'share'


def _detect_source_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_app_paths(
    *,
    appdock_handoff: AppHandoff | None = None,
    handoff_path: Path | None = None,
    appdock_config_path: Path | None = None,
) -> AppPaths:
    source_root = Path(appdock_handoff.workspace.source_root).expanduser() if appdock_handoff is not None else _detect_source_root()
    src_dir = source_root / 'src'
    user_root = _local_app_data_root() / APP_DIR_NAME
    config_dir = user_root / 'config'

    if appdock_handoff is not None:
        install_root = Path(appdock_handoff.workspace.install_root).expanduser()
        system_root = Path(appdock_handoff.workspace.system_root).expanduser()
        logs_root = Path(appdock_handoff.workspace.logs_root).expanduser()
        logs_dir = logs_root / 'app'
        scenario_logs_dir = logs_dir / 'scenarios'
        session_state_path = Path(appdock_handoff.refs.session_ref).expanduser() if appdock_handoff.refs.session_ref else None
        session_dir = session_state_path.parent if session_state_path is not None else None
        cache_dir = (session_dir / 'cache') if session_dir is not None else (user_root / 'cache')
        runtime_dir = (session_dir / 'runtime') if session_dir is not None else (user_root / 'runtime')
        appdock_managed = True
        user_state_path = Path(appdock_handoff.refs.user_state_ref).expanduser() if appdock_handoff.refs.user_state_ref else None
        active_session_path = Path(appdock_handoff.refs.active_session_ref).expanduser() if appdock_handoff.refs.active_session_ref else None
        health_snapshot_path = Path(appdock_handoff.refs.health_snapshot_ref).expanduser() if appdock_handoff.refs.health_snapshot_ref else None
        app_state_path = Path(appdock_handoff.refs.app_state_ref).expanduser() if appdock_handoff.refs.app_state_ref else None
        bundle_root = Path(appdock_handoff.workspace.bundle_root).expanduser()
        appdock_runtime_root = Path(appdock_handoff.workspace.runtime_root).expanduser()
    else:
        install_root = None
        system_root = None
        session_dir = None
        logs_dir = user_root / 'logs'
        scenario_logs_dir = logs_dir / 'scenarios'
        cache_dir = user_root / 'cache'
        runtime_dir = user_root / 'runtime'
        appdock_managed = False
        user_state_path = None
        session_state_path = None
        active_session_path = None
        health_snapshot_path = None
        app_state_path = None
        bundle_root = None
        appdock_runtime_root = None

    for path in (config_dir, logs_dir, scenario_logs_dir, cache_dir, runtime_dir):
        path.mkdir(parents=True, exist_ok=True)

    return AppPaths(
        source_root=source_root,
        src_dir=src_dir,
        user_root=user_root,
        config_dir=config_dir,
        logs_dir=logs_dir,
        scenario_logs_dir=scenario_logs_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        app_config_path=config_dir / 'app.json',
        install_root=install_root,
        system_root=system_root,
        session_dir=session_dir,
        appdock_managed=appdock_managed,
        handoff_path=handoff_path,
        appdock_config_path=appdock_config_path,
        user_state_path=user_state_path,
        session_state_path=session_state_path,
        active_session_path=active_session_path,
        health_snapshot_path=health_snapshot_path,
        app_state_path=app_state_path,
        bundle_root=bundle_root,
        appdock_runtime_root=appdock_runtime_root,
    )
