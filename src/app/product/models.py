from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from stratbox.base.filestore import FileStore

from app.core.paths import AppPaths
from app.core.session_env import (
    ActiveSessionProjectionRecord,
    NodeHealthSnapshotRecord,
    SessionStateRecord,
    UserStateRecord,
)
from app.core.version import VersionInfo
from app.integrations.appdock.runtime_contracts import AppActivationContext
from app.workspace import DataRootStatus, WorkspaceRootStatus, WorkspaceSchema

ParamType = Literal['text', 'int', 'bool', 'select', 'path_dir', 'path_file']
FieldSection = Literal['basic', 'advanced']


@dataclass(frozen=True, slots=True)
class ProductParamSpec:
    name: str
    title: str
    type: ParamType = 'text'
    default: Any = None
    description: str = ''
    required: bool = False
    options: tuple[tuple[str, str], ...] = ()
    section: FieldSection = 'basic'
    placeholder: str = ''
    min_value: int | None = None
    max_value: int | None = None


@dataclass(frozen=True, slots=True)
class ProductOperationSpec:
    id: str
    title: str
    description: str
    handler: str
    group: str = 'General'
    kind: str = 'business'
    tags: tuple[str, ...] = ()
    enabled: bool = True
    requires_workspace: bool = True
    params: tuple[ProductParamSpec, ...] = ()
    icon: str | None = None
    order: int = 100
    group_order: int = 100
    search_aliases: tuple[str, ...] = ()
    submit_label: str = 'Запустить'
    supports_repeat: bool = True
    result_preview_kind: str = 'artifacts'

    def default_params(self) -> dict[str, Any]:
        return {param.name: param.default for param in self.params}


@dataclass(frozen=True, slots=True)
class ProductRegistry:
    items: tuple[ProductOperationSpec, ...]

    def enabled(self) -> tuple[ProductOperationSpec, ...]:
        return tuple(item for item in self.items if item.enabled)

    def has(self, operation_id: str) -> bool:
        return any(item.id == operation_id for item in self.items)

    def get(self, operation_id: str) -> ProductOperationSpec:
        for item in self.items:
            if item.id == operation_id:
                return item
        raise KeyError(f'Unknown product operation: {operation_id}')


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
