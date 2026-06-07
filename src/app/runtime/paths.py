"""Filesystem roots for Strategy Box desktop surface."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.platform.appdock.runtime_contracts import ActivationSystemDir, AppActivationContext

APP_DIR_NAME = 'Strategy Box'
APPDOCK_MANAGED_SYSTEM_DIR_NAME = 'stratbox-system'
APP_STORAGE_DEV_DIR_NAME = '.strategy_box'
StorageMode = Literal['appdock_managed', 'standalone_user_profile', 'standalone_dev_root']


@dataclass(frozen=True, slots=True)
class AppPaths:
    source_root: Path
    src_dir: Path
    app_storage_root: Path
    logs_dir: Path
    operation_logs_dir: Path
    cache_dir: Path
    runtime_dir: Path
    app_config_path: Path
    storage_mode: StorageMode
    user_root: Path | None = None
    config_dir: Path | None = None
    install_root: Path | None = None
    system_root: Path | None = None
    managed_system_root: Path | None = None
    session_dir: Path | None = None
    appdock_managed: bool = False
    activation_context_path: Path | None = None
    appdock_config_path: Path | None = None
    user_state_path: Path | None = None
    session_state_path: Path | None = None
    active_session_path: Path | None = None
    health_snapshot_path: Path | None = None
    runtime_state_path: Path | None = None
    cleanup_registry_path: Path | None = None
    bundle_root: Path | None = None
    dev_root: Path | None = None


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


def _resolve_managed_storage_root(*, install_root: Path, install_root_system_dir: ActivationSystemDir | None) -> Path:
    if install_root_system_dir is not None and str(install_root_system_dir.path).strip():
        return Path(install_root_system_dir.path).expanduser()
    return install_root / APPDOCK_MANAGED_SYSTEM_DIR_NAME


def _build_storage_roots(app_storage_root: Path) -> tuple[Path, Path, Path, Path]:
    logs_dir = app_storage_root / 'logs'
    operation_logs_dir = logs_dir / 'operations'
    cache_dir = app_storage_root / 'cache'
    runtime_dir = app_storage_root / 'runtime'
    _ensure_directories(app_storage_root, logs_dir, operation_logs_dir, cache_dir, runtime_dir)
    return logs_dir, operation_logs_dir, cache_dir, runtime_dir


def _build_appdock_managed_paths(
    *,
    source_root: Path,
    src_dir: Path,
    appdock_activation: AppActivationContext,
    activation_context_path: Path | None,
    appdock_config_path: Path | None,
) -> AppPaths:
    install_root = Path(appdock_activation.workspace.install_root).expanduser()
    system_root = Path(appdock_activation.workspace.system_root).expanduser()
    session_state_path = Path(appdock_activation.refs.session_ref).expanduser() if appdock_activation.refs.session_ref else None
    session_dir = session_state_path.parent if session_state_path is not None else None

    managed_system_root = _resolve_managed_storage_root(
        install_root=install_root,
        install_root_system_dir=appdock_activation.provided_system_dirs.install_root_system_dir,
    )
    logs_dir, operation_logs_dir, cache_dir, runtime_dir = _build_storage_roots(managed_system_root)
    app_config_path_resolved = managed_system_root / 'app.json'

    workspace = appdock_activation.workspace
    bundle_root = Path(workspace.bundle_root).expanduser() if workspace.bundle_root else None

    user_state_path = Path(appdock_activation.refs.user_state_ref).expanduser() if appdock_activation.refs.user_state_ref else None
    active_session_path = Path(appdock_activation.refs.active_session_ref).expanduser() if appdock_activation.refs.active_session_ref else None
    health_snapshot_path = Path(appdock_activation.refs.health_snapshot_ref).expanduser() if appdock_activation.refs.health_snapshot_ref else None
    runtime_state_path = Path(appdock_activation.refs.runtime_state_ref).expanduser() if appdock_activation.refs.runtime_state_ref else None
    cleanup_registry_path = Path(appdock_activation.refs.cleanup_registry_ref).expanduser() if appdock_activation.refs.cleanup_registry_ref else None

    return AppPaths(
        source_root=source_root,
        src_dir=src_dir,
        app_storage_root=managed_system_root,
        logs_dir=logs_dir,
        operation_logs_dir=operation_logs_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        app_config_path=app_config_path_resolved,
        storage_mode='appdock_managed',
        user_root=None,
        config_dir=None,
        install_root=install_root,
        system_root=system_root,
        managed_system_root=managed_system_root,
        session_dir=session_dir,
        appdock_managed=True,
        activation_context_path=activation_context_path,
        appdock_config_path=appdock_config_path,
        user_state_path=user_state_path,
        session_state_path=session_state_path,
        active_session_path=active_session_path,
        health_snapshot_path=health_snapshot_path,
        runtime_state_path=runtime_state_path,
        cleanup_registry_path=cleanup_registry_path,
        bundle_root=bundle_root,
    )


def _build_standalone_user_paths(
    *,
    source_root: Path,
    src_dir: Path,
    activation_context_path: Path | None,
    appdock_config_path: Path | None,
) -> AppPaths:
    user_root = _local_app_data_root() / APP_DIR_NAME
    config_dir = user_root / 'config'
    app_storage_root = user_root
    logs_dir, operation_logs_dir, cache_dir, runtime_dir = _build_storage_roots(app_storage_root)
    _ensure_directories(config_dir)
    app_config_path_resolved = config_dir / 'app.json'
    return AppPaths(
        source_root=source_root,
        src_dir=src_dir,
        app_storage_root=app_storage_root,
        logs_dir=logs_dir,
        operation_logs_dir=operation_logs_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        app_config_path=app_config_path_resolved,
        storage_mode='standalone_user_profile',
        user_root=user_root,
        config_dir=config_dir,
        appdock_managed=False,
        activation_context_path=activation_context_path,
        appdock_config_path=appdock_config_path,
    )


def _build_standalone_dev_paths(
    *,
    source_root: Path,
    src_dir: Path,
    activation_context_path: Path | None,
    appdock_config_path: Path | None,
    dev_root: Path,
) -> AppPaths:
    dev_root_resolved = dev_root.expanduser()
    app_storage_root = dev_root_resolved / APP_STORAGE_DEV_DIR_NAME / 'system'
    config_dir = app_storage_root
    logs_dir, operation_logs_dir, cache_dir, runtime_dir = _build_storage_roots(app_storage_root)
    app_config_path_resolved = config_dir / 'app.json'
    return AppPaths(
        source_root=source_root,
        src_dir=src_dir,
        app_storage_root=app_storage_root,
        logs_dir=logs_dir,
        operation_logs_dir=operation_logs_dir,
        cache_dir=cache_dir,
        runtime_dir=runtime_dir,
        app_config_path=app_config_path_resolved,
        storage_mode='standalone_dev_root',
        user_root=dev_root_resolved,
        config_dir=config_dir,
        appdock_managed=False,
        activation_context_path=activation_context_path,
        appdock_config_path=appdock_config_path,
        dev_root=dev_root_resolved,
    )


def build_app_paths(
    *,
    appdock_activation: AppActivationContext | None = None,
    activation_context_path: Path | None = None,
    appdock_config_path: Path | None = None,
    standalone_dev_root: Path | None = None,
) -> AppPaths:
    source_root = Path(appdock_activation.workspace.source_root).expanduser() if appdock_activation is not None else _detect_source_root()
    src_dir = source_root / 'src'
    if appdock_activation is not None:
        return _build_appdock_managed_paths(
            source_root=source_root,
            src_dir=src_dir,
            appdock_activation=appdock_activation,
            activation_context_path=activation_context_path,
            appdock_config_path=appdock_config_path,
        )
    if standalone_dev_root is not None:
        return _build_standalone_dev_paths(
            source_root=source_root,
            src_dir=src_dir,
            activation_context_path=activation_context_path,
            appdock_config_path=appdock_config_path,
            dev_root=standalone_dev_root,
        )
    return _build_standalone_user_paths(
        source_root=source_root,
        src_dir=src_dir,
        activation_context_path=activation_context_path,
        appdock_config_path=appdock_config_path,
    )
