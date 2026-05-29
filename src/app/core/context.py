
"""Контекст приложения Strategy Box."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from stratbox.base.filestore import FileStore

from app.core.errors import AppStartupError
from app.core.handoff import (
    LauncherHandoff,
    get_launcher_config_path_from_env,
    get_launcher_handoff_path_from_env,
    load_launcher_handoff_from_env,
)
from app.core.log_setup import setup_app_logger
from app.core.paths import AppPaths, build_app_paths
from app.core.user_config import AppUserConfig, load_user_config
from app.core.version import VersionInfo, get_version_info
from app.workspace import (
    DataRootStatus,
    WorkspaceRegistry,
    WorkspaceSchema,
    build_filestore_for_data_root,
    load_workspace_registry,
    resolve_data_root_status,
)


@dataclass(slots=True)
class AppContext:
    """Единый объект состояния приложения."""

    paths: AppPaths
    user_config: AppUserConfig
    workspaces: WorkspaceRegistry
    workspace_schema: WorkspaceSchema
    launcher_handoff: LauncherHandoff | None
    run_mode: str
    data_root_path: Path | None
    data_root_status: DataRootStatus
    degraded_launch: bool
    filestore: FileStore | None
    version: VersionInfo
    logger: logging.Logger


def _resolve_run_contract(
    *,
    standalone_dev_root: str | None = None,
    override_data_root_path: Path | None = None,
) -> tuple[str, LauncherHandoff | None, Path | None]:
    handoff = load_launcher_handoff_from_env()
    if handoff is not None:
        if override_data_root_path is not None:
            return "launcher_managed", handoff, override_data_root_path
        path = Path(handoff.data_root_path).expanduser() if handoff.data_root_path else None
        return "launcher_managed", handoff, path

    if standalone_dev_root:
        return "standalone_dev", None, Path(standalone_dev_root).expanduser()

    raise AppStartupError(
        "Launcher handoff is required for normal startup. Use Stratbox Launcher or pass --standalone-dev-root for development."
    )


def build_app_context(
    *,
    standalone_dev_root: str | None = None,
    override_data_root_path: Path | None = None,
) -> AppContext:
    """Собирает контекст приложения для GUI или сервисного запуска."""
    run_mode, launcher_handoff, data_root_path = _resolve_run_contract(
        standalone_dev_root=standalone_dev_root,
        override_data_root_path=override_data_root_path,
    )
    handoff_path = get_launcher_handoff_path_from_env()
    launcher_config_path = get_launcher_config_path_from_env()
    paths = build_app_paths(
        launcher_handoff=launcher_handoff,
        handoff_path=handoff_path,
        launcher_config_path=launcher_config_path,
    )
    logger = setup_app_logger(paths.logs_dir)
    user_config = load_user_config(paths.app_config_path)
    workspaces = load_workspace_registry()

    selected_schema_id = user_config.last_workspace_schema
    if not workspaces.has(selected_schema_id):
        logger.warning("Unknown workspace schema '%s'; fallback to default", selected_schema_id)
        selected_schema_id = "default" if workspaces.has("default") else workspaces.items[0].id
    workspace_schema = workspaces.get(selected_schema_id)

    data_root_status = resolve_data_root_status(data_root_path)
    filestore = build_filestore_for_data_root(data_root_path) if data_root_status.available and data_root_path else None
    version = get_version_info(paths.repo_dir)

    degraded_launch = (launcher_handoff.degraded_launch if launcher_handoff is not None else False) or (not data_root_status.available)

    logger.info(
        "App context initialized. RunMode=%s DataRoot=%s Available=%s Workspace=%s",
        run_mode,
        data_root_path,
        data_root_status.available,
        workspace_schema.id,
    )

    return AppContext(
        paths=paths,
        user_config=user_config,
        workspaces=workspaces,
        workspace_schema=workspace_schema,
        launcher_handoff=launcher_handoff,
        run_mode=run_mode,
        data_root_path=data_root_path,
        data_root_status=data_root_status,
        degraded_launch=degraded_launch,
        filestore=filestore,
        version=version,
        logger=logger,
    )
