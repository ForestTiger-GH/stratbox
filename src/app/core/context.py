"""Strategy Box application context."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from stratbox.base.filestore import FileStore

from app.core.errors import AppStartupError
from app.core.log_setup import setup_app_logger
from app.core.paths import AppPaths, build_app_paths
from app.state.session_runtime import (
    ActiveSessionProjectionRecord,
    AppSessionClient,
    AppSessionSnapshot,
    NodeHealthSnapshotRecord,
    SessionStateRecord,
    UserStateRecord,
)
from app.core.user_config import AppUserConfig, load_user_config
from app.core.version import VersionInfo, get_version_info
from app.platform.appdock.runtime_contracts import (
    AppActivationContext,
    get_activation_context_path_from_env,
    get_appdock_config_path_from_env,
    load_activation_context_from_env,
)
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
    """Unified runtime state for GUI and service commands."""

    paths: AppPaths
    user_config: AppUserConfig
    workspaces: WorkspaceRegistry
    workspace_schema: WorkspaceSchema
    appdock_activation: AppActivationContext | None
    session_client: AppSessionClient | None
    session_snapshot: AppSessionSnapshot | None
    run_mode: str
    launch_origin: str
    data_root_selector_path: Path | None
    data_root_status: DataRootStatus
    workspace_root_path: Path | None
    workspace_status: WorkspaceRootStatus
    degraded_launch: bool
    filestore: FileStore | None
    version: VersionInfo
    logger: logging.Logger
    node_id: str | None = None
    node_created_at_utc: str | None = None
    session_id: str | None = None
    session_started_at_utc: str | None = None
    user_id: str | None = None
    account_name: str | None = None
    host_name: str | None = None
    session_state: SessionStateRecord | None = None
    user_state: UserStateRecord | None = None
    active_session: ActiveSessionProjectionRecord | None = None
    health_snapshot: NodeHealthSnapshotRecord | None = None


def _selector_path_from_activation(context: AppActivationContext) -> Path | None:
    if context.workspace.data_root_path:
        return Path(context.workspace.data_root_path).expanduser()
    return None


def _selector_override_from_session(snapshot: AppSessionSnapshot | None) -> Path | None:
    if snapshot is None:
        return None
    runtime_state = snapshot.runtime_state
    if runtime_state is not None and runtime_state.selected_data_root_path:
        return Path(str(runtime_state.selected_data_root_path)).expanduser()
    session_state = snapshot.session_state
    if session_state is not None and session_state.effective_data_root_path:
        return Path(session_state.effective_data_root_path).expanduser()
    return None


def _resolve_run_contract(
    *,
    standalone_dev_root: str | None = None,
    override_data_root_path: Path | None = None,
) -> tuple[str, AppActivationContext | None, Path | None]:
    appdock_activation = load_activation_context_from_env()
    if appdock_activation is not None:
        if override_data_root_path is not None:
            return 'appdock_managed', appdock_activation, override_data_root_path
        return 'appdock_managed', appdock_activation, _selector_path_from_activation(appdock_activation)

    if standalone_dev_root:
        return 'standalone_dev', None, Path(standalone_dev_root).expanduser()

    raise AppStartupError(
        'AppDock activation context is required for normal startup. '
        'Use AppDock or pass --standalone-dev-root for development.'
    )


def build_app_context(
    *,
    standalone_dev_root: str | None = None,
    override_data_root_path: Path | None = None,
    launch_origin: str = 'standalone',
) -> AppContext:
    run_mode, appdock_activation, data_root_selector_path = _resolve_run_contract(
        standalone_dev_root=standalone_dev_root,
        override_data_root_path=override_data_root_path,
    )
    activation_context_path = get_activation_context_path_from_env()
    appdock_config_path = get_appdock_config_path_from_env()
    paths = build_app_paths(
        appdock_activation=appdock_activation,
        activation_context_path=activation_context_path,
        appdock_config_path=appdock_config_path,
        standalone_dev_root=(Path(standalone_dev_root).expanduser() if standalone_dev_root else None),
    )
    logger = setup_app_logger(paths.logs_dir)
    user_config = load_user_config(paths.app_config_path)
    workspaces = load_workspace_registry()

    session_client = AppSessionClient(appdock_activation) if appdock_activation is not None else None
    session_snapshot = session_client.snapshot() if session_client is not None and session_client.enabled else None
    session_state = session_snapshot.session_state if session_snapshot else None
    user_state = session_snapshot.user_state if session_snapshot else None
    active_session = session_snapshot.active_session if session_snapshot else None
    health_snapshot = session_snapshot.health_snapshot if session_snapshot else None

    session_selector_override = _selector_override_from_session(session_snapshot)
    if override_data_root_path is None and session_selector_override is not None:
        data_root_selector_path = session_selector_override

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
    version = get_version_info(paths.source_root)

    degraded_launch = (
        (appdock_activation.degraded_launch if appdock_activation is not None else False)
        or (session_state.degraded_launch if session_state is not None and session_state.degraded_launch is not None else False)
        or (not data_root_status.available)
    )

    logger.info(
        'App context initialized. RunMode=%s LaunchOrigin=%s Selector=%s Workspace=%s Available=%s Schema=%s Session=%s',
        run_mode,
        launch_origin,
        data_root_selector_path,
        workspace_root_path,
        workspace_status.available,
        workspace_schema.id,
        session_state.session_id if session_state is not None else None,
    )

    resolved_host_name = (
        user_state.host_name if user_state is not None else None
    ) or (
        appdock_activation.host_name if appdock_activation is not None else None
    ) or os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME')

    return AppContext(
        paths=paths,
        user_config=user_config,
        workspaces=workspaces,
        workspace_schema=workspace_schema,
        appdock_activation=appdock_activation,
        session_client=session_client,
        session_snapshot=session_snapshot,
        run_mode=run_mode,
        launch_origin=launch_origin,
        data_root_selector_path=data_root_selector_path,
        data_root_status=data_root_status,
        workspace_root_path=workspace_root_path,
        workspace_status=workspace_status,
        degraded_launch=degraded_launch,
        filestore=filestore,
        version=version,
        logger=logger,
        node_id=(session_state.node_id if session_state else (appdock_activation.node_id if appdock_activation else None)),
        node_created_at_utc=(appdock_activation.node_created_at_utc if appdock_activation else None),
        session_id=(session_state.session_id if session_state else (appdock_activation.session_id if appdock_activation else None)),
        session_started_at_utc=(session_state.started_at_utc if session_state else (appdock_activation.session_started_at_utc if appdock_activation else None)),
        user_id=(user_state.user_id if user_state else (appdock_activation.user_id if appdock_activation else None)),
        account_name=(user_state.account_name if user_state else (appdock_activation.account_name if appdock_activation else None)),
        host_name=resolved_host_name,
        session_state=session_state,
        user_state=user_state,
        active_session=active_session,
        health_snapshot=health_snapshot,
    )
