from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stratbox.base.filestore import FileStore

from app.core.paths import AppPaths
from app.core.version import VersionInfo
from app.platform.appdock.runtime_contracts import AppActivationContext
from app.state.session_runtime import (
    ActiveSessionProjectionRecord,
    NodeHealthSnapshotRecord,
    SessionStateRecord,
    UserStateRecord,
)
from app.workspace import DataRootStatus, WorkspaceRootStatus, WorkspaceSchema


@dataclass(slots=True)
class ProductOperationContext:
    workspace_schema: WorkspaceSchema
    data_root_selector_path: Path | None
    data_root_status: DataRootStatus
    workspace_root_path: Path | None
    workspace_status: WorkspaceRootStatus
    filestore: FileStore | None
    paths: AppPaths
    version: VersionInfo
    logger: logging.Logger
    operation_log_path: Path
    appdock_activation: AppActivationContext | None = None
    run_mode: str = 'appdock_managed'
    launch_origin: str = 'standalone'
    node_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    account_name: str | None = None
    host_name: str | None = None
    session_state: SessionStateRecord | None = None
    user_state: UserStateRecord | None = None
    active_session: ActiveSessionProjectionRecord | None = None
    health_snapshot: NodeHealthSnapshotRecord | None = None


@dataclass(frozen=True, slots=True)
class ProductResult:
    ok: bool
    message: str
    outputs: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'ok': self.ok,
            'message': self.message,
            'outputs': list(self.outputs),
            'details': self.details,
        }


@dataclass(frozen=True, slots=True)
class ProductLaunchRequest:
    operation_id: str
    params: dict[str, Any]
    launch_origin: str
