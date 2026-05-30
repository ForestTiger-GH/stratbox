"""Модели задач пользовательского GUI слоя."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from stratbox.base.filestore import FileStore

from app.core.handoff import LauncherHandoff
from app.core.paths import AppPaths
from app.core.session_env import (
    ActiveSessionProjectionRecord,
    EnvironmentHealthSnapshotRecord,
    SessionStateRecord,
    UserStateRecord,
)
from app.core.version import VersionInfo
from app.workspace import DataRootStatus, WorkspaceSchema

ParamType = Literal['text', 'int', 'float', 'bool', 'path', 'select', 'multiselect']


@dataclass(frozen=True, slots=True)
class TaskParamSpec:
    """Описание одного пользовательского параметра задачи."""

    name: str
    title: str
    type: ParamType = 'text'
    default: Any = None
    description: str = ''
    required: bool = False
    options: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TaskParamSpec':
        return cls(
            name=str(data['name']),
            title=str(data.get('title') or data['name']),
            type=str(data.get('type') or 'text'),  # type: ignore[arg-type]
            default=data.get('default'),
            description=str(data.get('description') or ''),
            required=bool(data.get('required', False)),
            options=tuple(str(x) for x in (data.get('options') or [])),
        )

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['options'] = list(self.options)
        return out


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """Описание задачи, загружаемое из JSON."""

    id: str
    title: str
    description: str
    adapter: str
    category: str = 'General'
    enabled: bool = True
    requires_data_root: bool = True
    params: tuple[TaskParamSpec, ...] = ()
    input_dir: str = 'input'
    output_dir: str = 'output'
    links: tuple[dict[str, str], ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'TaskSpec':
        return cls(
            id=str(data['id']),
            title=str(data.get('title') or data['id']),
            description=str(data.get('description') or ''),
            adapter=str(data['adapter']),
            category=str(data.get('category') or 'General'),
            enabled=bool(data.get('enabled', True)),
            requires_data_root=bool(data.get('requires_data_root', True)),
            params=tuple(TaskParamSpec.from_dict(x) for x in (data.get('params') or [])),
            input_dir=str(data.get('input_dir') or 'input'),
            output_dir=str(data.get('output_dir') or 'output'),
            links=tuple(dict(x) for x in (data.get('links') or [])),
        )

    def default_params(self) -> dict[str, Any]:
        return {param.name: param.default for param in self.params}

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['params'] = [param.to_dict() for param in self.params]
        out['links'] = list(self.links)
        return out


@dataclass(slots=True)
class TaskContext:
    """Контекст запуска задачи."""

    workspace_schema: WorkspaceSchema
    data_root_path: Path | None
    data_root_status: DataRootStatus
    filestore: FileStore | None
    paths: AppPaths
    version: VersionInfo
    logger: logging.Logger
    task_log_path: Path
    launcher_handoff: LauncherHandoff | None = None
    run_mode: str = 'launcher_managed'
    system_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    account_name: str | None = None
    host_name: str | None = None
    session_state: SessionStateRecord | None = None
    user_state: UserStateRecord | None = None
    active_session: ActiveSessionProjectionRecord | None = None
    environment_health: EnvironmentHealthSnapshotRecord | None = None


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Итог выполнения задачи."""

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
