"""Пути desktop surface Strategy Box.

Strategy Box поддерживает два разных режима размещения.

1. AppDock-managed
   Приложение использует install-root, который подготовил AppDock. Все собственные
   operational-файлы живут в одном app-owned system folder внутри install-root.
   Если AppDock явно передал install_root_system_dir, используется он. Иначе
   приложение создаёт и использует fallback-папку `install_root/AppDock`.

2. Standalone developer route
   Для локальной разработки и автономного запуска приложение использует свою
   user-level папку внутри LOCALAPPDATA / ~/.local/share.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.handoff import AppHandoff, HandoffSystemDir

APP_DIR_NAME = 'Stratbox'
APPDOCK_MANAGED_SYSTEM_DIR_NAME = 'AppDock'


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Набор основных путей приложения."""

    source_root: Path
    src_dir: Path
    app_storage_root: Path
    logs_dir: Path
    scenario_logs_dir: Path
    cache_dir: Path
    runtime_dir: Path
    app_config_path: Path
    user_root: Path | None = None
    config_dir: Path | None = None
    install_root: Path | None = None
    system_root: Path | None = None
    managed_system_root: Path | None = None
    session_dir: Path | None = None
    appdock_managed: bool = False
    handoff_path: Path | None = None
    appdock_config_path: Path | None = None
    user_state_path: Path | None = None
    session_state_path: Path | None = None
    active_session_path: Path | None = None
    health_snapshot_path: Path | None = None
    app_state_path: Path | None = None
    cleanup_registry_path: Path | None = None
    bundle_root: Path | None = None


def _local_app_data_root() -> Path:
    local_app_data = os.getenv('LOCALAPPDATA')
    if local_app_data:
        return Path(local_app_data).expanduser()
    return Path.home() / '.local' / 'share'


def _detect_source_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _resolve_managed_storage_root(*, install_root: Path, install_root_system_dir: HandoffSystemDir | None) -> Path:
    if install_root_system_dir is not None and str(install_root_system_dir.path).strip():
        return Path(install_root_system_dir.path).expanduser()
    return install_root / APPDOCK_MANAGED_SYSTEM_DIR_NAME


def _build_appdock_managed_paths(
    *,
    source_root: Path,
    src_dir: Path,
    appdock_handoff: AppHandoff,
    handoff_path: Path | None,
    appdock_config_path: Path | None,
) -> AppPaths:
    install_root = Path(appdock_handoff.workspace.install_root).expanduser()
    system_root = Path(appdock_handoff.workspace.system_root).expanduser()
    session_state_path = Path(appdock_handoff.refs.session_ref).expanduser() if appdock_handoff.refs.session_ref else None
    session_dir = session_state_path.parent if session_state_path is not None else None

    managed_system_root = _resolve_managed_storage_root(
        install_root=install_root,
        install_root_system_dir=appdock_handoff.provided_system_dirs.install_root_system_dir,
    )
    logs_dir = managed_system_root / 'logs'
    scenario_logs_dir = logs_dir / 'scenarios'
    cache_dir = managed_system_root / 'cache'
    runtime_dir = managed_system_root / 'runtime'
    app_config_path = managed_system_root / 'app.json'

    _ensure_directories(managed_system_root, logs_dir, scenario_logs_dir, cache_dir, runtime_dir)

    workspace = appdock_handoff.workspace
    bundle_root = Path(workspace.bundle_root).expanduser() if workspace.bundle_root else None

    user_state_path = Path(appdock_handoff.refs.user_state_ref).expanduser() if appdock_handoff.refs.user_state_ref else None
    active_session_path = Path(appdock_handoff.refs.active_session_ref).expanduser() if appdock_handoff.refs.active_session_ref else None
    health_snapshot_path = Path(appdock_handoff.refs.health_snapshot_ref).expanduser() if appdock_handoff.refs.health_snapshot_ref else None
    app_state_path = Path(appdock_handoff.refs.app_state_ref).expanduser() if appdock_handoff.refs.app_state_ref else None
    cleanup_registry_path = Path(appdock_handoff.refs.cleanup_registry_ref).expanduser() if appdock_handoff.refs.cleanup_registry_ref else None

    return AppPaths(
        source_root=source_root,
        src_dir=src_dir,
        app_storage_root=managed_system_root,
        logs_dir=logs_dir,
        scenario_logs_dir=scenario_logs_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        app_config_path=app_config_path,
        user_root=None,
        config_dir=None,
        install_root=install_root,
        system_root=system_root,
        managed_system_root=managed_system_root,
        session_dir=session_dir,
        appdock_managed=True,
        handoff_path=handoff_path,
        appdock_config_path=appdock_config_path,
        user_state_path=user_state_path,
        session_state_path=session_state_path,
        active_session_path=active_session_path,
        health_snapshot_path=health_snapshot_path,
        app_state_path=app_state_path,
        cleanup_registry_path=cleanup_registry_path,
        bundle_root=bundle_root,
    )


def _build_standalone_paths(
    *,
    source_root: Path,
    src_dir: Path,
    handoff_path: Path | None,
    appdock_config_path: Path | None,
) -> AppPaths:
    user_root = _local_app_data_root() / APP_DIR_NAME
    config_dir = user_root / 'config'
    logs_dir = user_root / 'logs'
    scenario_logs_dir = logs_dir / 'scenarios'
    cache_dir = user_root / 'cache'
    runtime_dir = user_root / 'runtime'
    app_config_path = config_dir / 'app.json'

    _ensure_directories(config_dir, logs_dir, scenario_logs_dir, cache_dir, runtime_dir)

    return AppPaths(
        source_root=source_root,
        src_dir=src_dir,
        app_storage_root=user_root,
        logs_dir=logs_dir,
        scenario_logs_dir=scenario_logs_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        app_config_path=app_config_path,
        user_root=user_root,
        config_dir=config_dir,
        install_root=None,
        system_root=None,
        managed_system_root=None,
        session_dir=None,
        appdock_managed=False,
        handoff_path=handoff_path,
        appdock_config_path=appdock_config_path,
        user_state_path=None,
        session_state_path=None,
        active_session_path=None,
        health_snapshot_path=None,
        app_state_path=None,
        cleanup_registry_path=None,
        bundle_root=None,
    )


def build_app_paths(
    *,
    appdock_handoff: AppHandoff | None = None,
    handoff_path: Path | None = None,
    appdock_config_path: Path | None = None,
) -> AppPaths:
    source_root = Path(appdock_handoff.workspace.source_root).expanduser() if appdock_handoff is not None else _detect_source_root()
    src_dir = source_root / 'src'
    if appdock_handoff is not None:
        return _build_appdock_managed_paths(
            source_root=source_root,
            src_dir=src_dir,
            appdock_handoff=appdock_handoff,
            handoff_path=handoff_path,
            appdock_config_path=appdock_config_path,
        )
    return _build_standalone_paths(
        source_root=source_root,
        src_dir=src_dir,
        handoff_path=handoff_path,
        appdock_config_path=appdock_config_path,
    )
