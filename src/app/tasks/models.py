"""Модели задач приложения Strategy Box."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from stratbox.base.filestore import FileStore

from app.core.paths import AppPaths
from app.core.version import VersionInfo
from app.profiles.models import DataProfile

ParamType = Literal["text", "int", "float", "bool", "select", "multiselect"]


@dataclass(frozen=True, slots=True)
class TaskParamSpec:
    """Описание одного пользовательского параметра задачи."""

    name: str
    title: str
    type: ParamType = "text"
    default: Any = None
    description: str = ""
    required: bool = False
    options: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskParamSpec":
        """Создает описание параметра из JSON."""
        return cls(
            name=str(data["name"]),
            title=str(data.get("title") or data["name"]),
            type=str(data.get("type") or "text"),  # type: ignore[arg-type]
            default=data.get("default"),
            description=str(data.get("description") or ""),
            required=bool(data.get("required", False)),
            options=tuple(str(x) for x in (data.get("options") or [])),
        )

    def to_dict(self) -> dict[str, Any]:
        """Преобразует параметр в словарь."""
        out = asdict(self)
        out["options"] = list(self.options)
        return out


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """Описание задачи, загружаемое из JSON."""

    id: str
    title: str
    description: str
    adapter: str
    category: str = "General"
    enabled: bool = True
    params: tuple[TaskParamSpec, ...] = ()
    input_dir: str = "input"
    output_dir: str = "output"
    links: tuple[dict[str, str], ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskSpec":
        """Создает задачу из JSON."""
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or data["id"]),
            description=str(data.get("description") or ""),
            adapter=str(data["adapter"]),
            category=str(data.get("category") or "General"),
            enabled=bool(data.get("enabled", True)),
            params=tuple(TaskParamSpec.from_dict(x) for x in (data.get("params") or [])),
            input_dir=str(data.get("input_dir") or "input"),
            output_dir=str(data.get("output_dir") or "output"),
            links=tuple(dict(x) for x in (data.get("links") or [])),
        )

    def default_params(self) -> dict[str, Any]:
        """Возвращает словарь значений параметров по умолчанию."""
        return {param.name: param.default for param in self.params}

    def to_dict(self) -> dict[str, Any]:
        """Преобразует задачу в словарь."""
        out = asdict(self)
        out["params"] = [param.to_dict() for param in self.params]
        out["links"] = list(self.links)
        return out


@dataclass(slots=True)
class TaskContext:
    """Контекст запуска задачи."""

    profile: DataProfile
    filestore: FileStore
    paths: AppPaths
    version: VersionInfo
    logger: logging.Logger
    task_log_path: Path


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Итог выполнения задачи."""

    ok: bool
    message: str
    outputs: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Преобразует итог задачи в JSON-совместимый словарь."""
        return {
            "ok": self.ok,
            "message": self.message,
            "outputs": list(self.outputs),
            "details": self.details,
        }
