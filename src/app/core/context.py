"""Контекст приложения Strategy Box."""

from __future__ import annotations

import logging
import os
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
from app.core.session_env import (
    ActiveSessionProjectionRecord,
    EnvironmentHealthSnapshotRecord,
    SessionEnvironmentClient,
    SessionEnvironmentSnapshot,
    SessionStateRecord,
    UserStateRecord,
)
from app.core.user_config import AppUserConfig, load_user_config
from app.core.version import VersionInfo, get_version_info
from app.workspace import (
    DataRootStatus,
    WorkspaceRegistry,
    WorkspaceSchema,
    WorkspaceRootStatus,
    build_filestore_for_workspace_root,
    load_workspace_registry,
    resolve_data_root_status,
    resolve_workspace_root,
)


@dataclass(slots=True)
class AppContext:
    """Единый объект состояния приложения."""

    paths: AppPaths
    user_config: AppUserConfig
    workspaces: WorkspaceRegistry
    workspace_schema: WorkspaceSchema
    launcher_handoff: LauncherHandoff | None
    session_env: SessionEnvironmentClient | None
    session_snapshot: SessionEnvironmentSnapshot | None
    run_mode: str
    data_root_selector_path: Path | None
    data_root_path: Path | None
    data_root_status: DataRootStatus
    workspace_root_path: Path | None
    workspace_status: WorkspaceRootStatus
    degraded_launch: bool
    filestore: FileStore | None
    version: VersionInfo
    logger: logging.Logger
    system_id: str | None = None
    system_created_at_utc: str | None = None
    session_id: str | None = None
    session_started_at_utc: str | None = None
    user_id: str | None = None
    account_name: str | None = None
    host_name: str | None = None
    session_state: SessionStateRecord | None = None
    user_state: UserStateRecord | None = None
    active_session: ActiveSessionProjectionRecord | None = None
    environment_health: EnvironmentHealthSnapshotRecord | None = None


def _resolve_run_contract(
    *,
    standalone_dev_root: str | None = None,
    override_data_root_path: Path | None = None,
) -> tuple[str, LauncherHandoff | None, Path | None]:
    handoff = load_launcher_handoff_from_env()
    if handoff is not None:
        if override_data_root_path is not None:
            return 'launcher_managed', handoff, override_data_root_path
        path = Path(handoff.data_root_path).expanduser() if handoff.data_root_path else None
        return 'launcher_managed', handoff, path

    if standalone_dev_root:
        return 'standalone_dev', None, Path(standalone_dev_root).expanduser()

    raise AppStartupError(
        'Launcher handoff is required for normal startup. Use Stratbox Launcher or pass --standalone-dev-root for development.'
    )


def build_app_context(
    *,
    standalone_dev_root: str | None = None,
    override_data_root_path: Path | None = None,
) -> AppContext:
    """Собирает контекст приложения для GUI или сервисного запуска."""
    run_mode, launcher_handoff, data_root_selector_path = _resolve_run_contract(
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

    session_env = SessionEnvironmentClient(launcher_handoff) if launcher_handoff is not None else None
    session_snapshot = session_env.snapshot() if session_env is not None and session_env.enabled else None
    session_state = session_snapshot.session_state if session_snapshot else None
    user_state = session_snapshot.user_state if session_snapshot else None
    active_session = session_snapshot.active_session if session_snapshot else None
    environment_health = session_snapshot.environment_health if session_snapshot else None

    if session_state is not None and session_state.effective_data_root_path:
        data_root_selector_path = Path(session_state.effective_data_root_path).expanduser()

    selected_schema_id = user_config.last_workspace_schema
    if not workspaces.has(selected_schema_id):
        logger.warning("Unknown workspace schema '%s'; fallback to default", selected_schema_id)
        selected_schema_id = 'default' if workspaces.has('default') else workspaces.items[0].id
    workspace_schema = workspaces.get(selected_schema_id)

    data_root_status = resolve_data_root_status(data_root_selector_path)
    workspace_resolution = resolve_workspace_root(
        workspace_schema,
        data_root_selector_path,
        run_mode=run_mode,
        create_missing=True,
    )
    workspace_root_path = workspace_resolution.workspace_root_path
    workspace_status = workspace_resolution.workspace_status
    filestore = build_filestore_for_workspace_root(workspace_root_path) if workspace_status.available and workspace_root_path else None
    version = get_version_info(paths.repo_dir)

    degraded_launch = (launcher_handoff.degraded_launch if launcher_handoff is not None else False) or (session_state.degraded_launch if session_state is not None and session_state.degraded_launch is not None else False) or (not data_root_status.available)

    logger.info(
        'App context initialized. RunMode=%s Selector=%s Workspace=%s Available=%s Schema=%s Session=%s',
        run_mode,
        data_root_selector_path,
        workspace_root_path,
        workspace_status.available,
        workspace_schema.id,
        session_state.session_id if session_state is not None else None,
    )

    return AppContext(
        paths=paths,
        user_config=user_config,
        workspaces=workspaces,
        workspace_schema=workspace_schema,
        launcher_handoff=launcher_handoff,
        session_env=session_env,
        session_snapshot=session_snapshot,
        run_mode=run_mode,
        data_root_selector_path=data_root_selector_path,
        data_root_path=workspace_root_path,
        data_root_status=data_root_status,
        workspace_root_path=workspace_root_path,
        workspace_status=workspace_status,
        degraded_launch=degraded_launch,
        filestore=filestore,
        version=version,
        logger=logger,
        system_id=(launcher_handoff.system_id if launcher_handoff else None),
        system_created_at_utc=(launcher_handoff.system_created_at_utc if launcher_handoff else None),
        session_id=(session_state.session_id if session_state else (launcher_handoff.session_id if launcher_handoff else None)),
        session_started_at_utc=(session_state.started_at_utc if session_state else (launcher_handoff.session_started_at_utc if launcher_handoff else None)),
        user_id=(user_state.user_id if user_state else (launcher_handoff.user_id if launcher_handoff else None)),
        account_name=(user_state.account_name if user_state else (launcher_handoff.account_name if launcher_handoff else None)),
        host_name=(user_state.host_name if user_state else (launcher_handoff.host_name if launcher_handoff else os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME'))),
        session_state=session_state,
        user_state=user_state,
        active_session=active_session,
        environment_health=environment_health,
    )
